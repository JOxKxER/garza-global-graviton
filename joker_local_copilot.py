"""Joker: local-first executive co-pilot for a single trusted workstation.

Run only after setting JOKER_DB_KEY and JOKER_MESH_TOKEN, for example:
    uvicorn joker_local_copilot:app --host 127.0.0.1 --port 8765

The API is deliberately loopback-bound by default. A mesh gateway may forward
authenticated traffic to it, but this process never exposes arbitrary shell
execution: command names map to a small, read-only local command catalog.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    from sqlcipher3 import dbapi2 as sqlcipher
except ImportError as error:  # Never silently downgrade sensitive data to plain SQLite.
    raise RuntimeError(
        "SQLCipher is required. Install dependencies from requirements-joker.txt."
    ) from error


APP_ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("JOKER_DB_PATH", APP_ROOT / "data" / "joker.db"))
DB_KEY_ENV = "JOKER_DB_KEY"
MESH_TOKEN_ENV = "JOKER_MESH_TOKEN"
MAX_OUTPUT_CHARS = 16_000
COMMAND_TIMEOUT_SECONDS = 60
bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> str:
    """Use an unambiguous timestamp for local auditing and memory recall."""
    return datetime.now(UTC).isoformat()


def configured_secret(name: str) -> str:
    value = os.environ.get(name)
    if not value or len(value) < 32:
        raise RuntimeError(f"{name} must be set to a random value of at least 32 characters.")
    return value


def db_connection():
    """Open a short-lived encrypted connection so concurrent requests do not share cursors.

    SQLCipher encrypts database pages at rest; WAL permits concurrent readers and a
    single efficient writer for the workstation's telemetry and working memory.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlcipher.connect(str(DB_PATH), timeout=10, isolation_level=None)
    key = configured_secret(DB_KEY_ENV).replace("'", "''")
    connection.execute(f"PRAGMA key = '{key}'")
    connection.execute("PRAGMA cipher_memory_security = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlcipher.Row
    return connection


def initialize_database() -> None:
    with db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS command_logs (
                id TEXT PRIMARY KEY,
                requested_at TEXT NOT NULL,
                completed_at TEXT,
                command_name TEXT NOT NULL,
                arguments_json TEXT NOT NULL,
                status TEXT NOT NULL,
                exit_code INTEGER,
                stdout TEXT NOT NULL DEFAULT '',
                stderr TEXT NOT NULL DEFAULT '',
                caller_fingerprint TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id TEXT PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_telemetry_recorded_at ON telemetry(recorded_at DESC);
            CREATE TABLE IF NOT EXISTS habit_history (
                id TEXT PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                category TEXT NOT NULL,
                note TEXT NOT NULL,
                energy_level INTEGER,
                focus_level INTEGER
            );
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS goal_steps (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
                step_order INTEGER NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL,
                status TEXT NOT NULL,
                completed_at TEXT,
                UNIQUE(goal_id, step_order)
            );
            """
        )


def write_telemetry(event_type: str, payload: dict[str, Any]) -> None:
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO telemetry (id, recorded_at, event_type, payload_json) VALUES (?, ?, ?, ?)",
            (secrets.token_urlsafe(18), utc_now(), event_type, json.dumps(payload, sort_keys=True)),
        )


def caller_fingerprint(token: str) -> str:
    """Audit callers without retaining their bearer secret in the encrypted database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


async def require_mesh_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    expected = configured_secret(MESH_TOKEN_ENV)
    if not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mesh token rejected")
    return credentials.credentials


class CommandName(str, Enum):
    OLLAMA_LIST = "ollama_list"
    OLLAMA_PS = "ollama_ps"
    GIT_STATUS = "git_status"
    PYTHON_VERSION = "python_version"


@dataclass(frozen=True)
class CommandSpec:
    executable: str
    fixed_arguments: tuple[str, ...]


COMMAND_CATALOG: dict[CommandName, CommandSpec] = {
    CommandName.OLLAMA_LIST: CommandSpec("ollama", ("list",)),
    CommandName.OLLAMA_PS: CommandSpec("ollama", ("ps",)),
    CommandName.GIT_STATUS: CommandSpec("git", ("status", "--short")),
    CommandName.PYTHON_VERSION: CommandSpec("python", ("--version",)),
}


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: CommandName


class HabitEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=1, max_length=2_000)
    energy_level: int | None = Field(default=None, ge=1, le=5)
    focus_level: int | None = Field(default=None, ge=1, le=5)


class GoalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=3, max_length=4_000)
    context: str | None = Field(default=None, max_length=2_000)

    @field_validator("prompt")
    @classmethod
    def disallow_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 and character not in "\n\t" for character in value):
            raise ValueError("prompt contains control characters")
        return value.strip()


def break_goal_into_steps(prompt: str, context: str | None) -> list[tuple[str, str]]:
    """Create a bounded local plan; no cloud service or personal state leaves the Acer.

    The deterministic planner is intentionally predictable. It can later be replaced
    with a local Ollama planner, but model output must remain data, never shell input.
    """
    subject = prompt.rstrip(".?! ")
    context_note = f" Consider this context: {context.strip()}." if context else ""
    return [
        ("Make the task concrete", f"Write one sentence defining the desired result: {subject}."),
        ("Choose the next physical action", "Identify an action that takes 10 minutes or less and needs no further planning."),
        ("Prepare only what is needed", f"Open the minimum files, tools, or notes needed for the next action.{context_note}"),
        ("Complete one focused interval", "Work on that action for one short interval, then stop to review progress."),
        ("Record the outcome", "Mark what changed, capture the next action, and defer everything else to a later step."),
    ]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="Joker Local Executive Co-Pilot", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RuntimeError)
async def configuration_error(_: Request, error: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok", "storage": "sqlcipher-wal"}


@app.post("/command")
async def run_command(request: CommandRequest, token: str = Depends(require_mesh_token)) -> dict[str, Any]:
    """Execute one approved local diagnostic without invoking a shell interpreter."""
    spec = COMMAND_CATALOG[request.command]
    executable = shutil.which(spec.executable)
    if executable is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"{spec.executable} is unavailable")

    command_id = secrets.token_urlsafe(18)
    requested_at = utc_now()
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO command_logs (id, requested_at, command_name, arguments_json, status, caller_fingerprint) VALUES (?, ?, ?, ?, ?, ?)",
            (command_id, requested_at, request.command.value, json.dumps(spec.fixed_arguments), "RUNNING", caller_fingerprint(token)),
        )

    try:
        process = await asyncio.create_subprocess_exec(
            executable, *spec.fixed_arguments,
            cwd=str(APP_ROOT),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), COMMAND_TIMEOUT_SECONDS)
        result_status = "SUCCEEDED" if process.returncode == 0 else "FAILED"
        exit_code = process.returncode
        stdout = stdout_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_CHARS]
        stderr = stderr_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_CHARS]
    except TimeoutError:
        process.kill()
        await process.communicate()
        result_status, exit_code, stdout, stderr = "TIMED_OUT", None, "", "Command exceeded 60-second limit."
    except OSError as error:
        result_status, exit_code, stdout, stderr = "FAILED", None, "", str(error)[:MAX_OUTPUT_CHARS]

    completed_at = utc_now()
    with db_connection() as connection:
        connection.execute(
            "UPDATE command_logs SET completed_at = ?, status = ?, exit_code = ?, stdout = ?, stderr = ? WHERE id = ?",
            (completed_at, result_status, exit_code, stdout, stderr, command_id),
        )
    write_telemetry("command_completed", {"command_id": command_id, "status": result_status})
    return {"id": command_id, "status": result_status, "exit_code": exit_code, "stdout": stdout, "stderr": stderr}


@app.post("/habits", status_code=status.HTTP_201_CREATED)
async def record_habit(entry: HabitEntry, _: str = Depends(require_mesh_token)) -> dict[str, str]:
    entry_id = secrets.token_urlsafe(18)
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO habit_history (id, recorded_at, category, note, energy_level, focus_level) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, utc_now(), entry.category, entry.note, entry.energy_level, entry.focus_level),
        )
    return {"id": entry_id, "status": "recorded"}


@app.post("/goal", status_code=status.HTTP_201_CREATED)
async def create_goal(request: GoalRequest, _: str = Depends(require_mesh_token)) -> dict[str, Any]:
    """Persist and sequence a cognitive-load-reducing plan for local execution."""
    goal_id = secrets.token_urlsafe(18)
    steps = break_goal_into_steps(request.prompt, request.context)
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO goals (id, created_at, prompt, status) VALUES (?, ?, ?, ?)",
            (goal_id, utc_now(), request.prompt, "IN_PROGRESS"),
        )
        for step_order, (title, detail) in enumerate(steps, start=1):
            connection.execute(
                "INSERT INTO goal_steps (id, goal_id, step_order, title, detail, status) VALUES (?, ?, ?, ?, ?, ?)",
                (secrets.token_urlsafe(18), goal_id, step_order, title, detail, "READY" if step_order == 1 else "QUEUED"),
            )
    write_telemetry("goal_planned", {"goal_id": goal_id, "step_count": len(steps)})
    return {
        "goal_id": goal_id,
        "status": "IN_PROGRESS",
        "steps": [{"order": index, "title": title, "detail": detail, "status": "READY" if index == 1 else "QUEUED"} for index, (title, detail) in enumerate(steps, start=1)],
    }
