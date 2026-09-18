"""Integration checks for SQLite WAL telemetry and the local Joker LLM."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


JOKER_URL = "http://127.0.0.1:8011/v1/chat/completions"
JOKER_MODEL = "ggml-org/Qwen2.5-Coder-7B-Instruct-Q8_0-GGUF"


def check_sqlite_wal_persistence() -> None:
    """Verify WAL mode, write telemetry, close the DB, and read it back."""
    with tempfile.TemporaryDirectory(prefix="joker_integration_") as temp_dir:
        database_path = Path(temp_dir) / "telemetry.db"
        event_id = str(uuid.uuid4())
        event_payload = json.dumps({"source": "integration_test"})

        connection = sqlite3.connect(database_path)
        try:
            journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if str(journal_mode).lower() != "wal":
                raise AssertionError(f"Expected WAL mode, got {journal_mode!r}")
            connection.execute(
                "CREATE TABLE telemetry (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO telemetry (id, payload) VALUES (?, ?)",
                (event_id, event_payload),
            )
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()

        connection = sqlite3.connect(database_path)
        try:
            persisted = connection.execute(
                "SELECT payload FROM telemetry WHERE id = ?", (event_id,)
            ).fetchone()
            if persisted is None or json.loads(persisted[0]) != {
                "source": "integration_test"
            }:
                raise AssertionError("Telemetry row was not persisted across reopen")
        finally:
            connection.close()

    print("PASS: SQLite WAL telemetry persisted across connection reopen")


def check_joker_inference() -> None:
    """Verify the local Joker server returns an OpenAI-compatible completion."""
    payload = {
        "model": JOKER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Joker, a specialized local AI business partner and "
                    "coding assistant."
                ),
            },
            {"role": "user", "content": "Reply with exactly: JOKER_INTEGRATION_OK"},
        ],
        "stream": False,
        "max_tokens": 16,
        "temperature": 0,
    }
    request = Request(
        JOKER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Joker server request failed: {error}") from error

    try:
        reply = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as error:
        raise AssertionError(f"Unexpected Joker response: {result!r}") from error

    if not reply:
        raise AssertionError("Joker returned an empty response")

    print(f"PASS: Joker inference returned a response ({len(reply)} chars)")
    print(f"      Response: {reply}")


def main() -> int:
    print("=== Joker Integration Test Suite ===")
    try:
        check_sqlite_wal_persistence()
        check_joker_inference()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
