"""Lightweight offline HTTP client for a local Ollama LLM backend.

Tactical use: Joker-Builder must operate fully offline with zero cloud
dependencies. This client talks only to a local Ollama server (default
http://localhost:11434) using the standard library's urllib, so no
third-party HTTP package is required and no request ever leaves the
workstation.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:latest"
DEFAULT_TIMEOUT_SECONDS = 120.0

JOKER_SYSTEM_PROMPT = (
    "You are Joker, an expert software architect operating fully "
    "offline on a single workstation. When a task involves heavy "
    "computation -- spatial calculations, optimization, simulation, "
    "signal processing, or matrix math -- you MUST use the provided "
    "Garza Global Graviton (GGG) engine modules from `src/` instead of "
    "writing your own procedural math or approximations. Only write "
    "original code for application structure, I/O, and orchestration "
    "logic that the GGG engine does not already provide."
)


class OfflineModelUnavailableError(RuntimeError):
    """Raised when the local Ollama backend cannot be reached or errors."""


class LocalOllamaClient:
    """Minimal offline client for a local Ollama model server."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Set the local Ollama endpoint, model name, and request timeout."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def check_availability(self) -> bool:
        """Verify the local Ollama server is reachable before use.

        Tactical advantage: fails fast with an actionable message instead
        of hanging deep inside a generation request when the offline
        model server simply isn't running yet.
        """
        request = Request(f"{self.base_url}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=5.0):
                return True
        except (HTTPError, URLError, TimeoutError, OSError):
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = JOKER_SYSTEM_PROMPT,
    ) -> str:
        """Send a prompt to the local model and return its full response.

        Tactical advantage: a single offline call gets Joker's full
        architectural response with no cloud round-trip and no
        dependency beyond the Python standard library.
        """
        if not self.check_availability():
            raise OfflineModelUnavailableError(
                f"Cannot reach local Ollama server at {self.base_url}. "
                "Start it with `ollama serve` and ensure the model is "
                f"pulled with `ollama pull {self.model}`."
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
        }
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                body = json.load(response)
        except (
            HTTPError, URLError, TimeoutError, json.JSONDecodeError
        ) as error:
            raise OfflineModelUnavailableError(
                f"Local Ollama request failed: {error}"
            ) from error

        response_text = body.get("response")
        if not isinstance(response_text, str):
            raise OfflineModelUnavailableError(
                "Local Ollama returned no response text."
            )
        return response_text
