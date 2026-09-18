"""Minimal client for a local Ollama model service."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import LocalAISettings, local_ai_settings


class LocalAIError(RuntimeError):
    """Raised when the local model service cannot complete a request."""


class LocalAI:
    def __init__(self, settings: LocalAISettings = local_ai_settings) -> None:
        self.settings = settings

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Generate a response through the Ollama loopback API."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        payload: dict[str, Any] = {
            "model": self.settings.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        request = Request(
            f"{self.settings.base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(
                request, timeout=self.settings.timeout_seconds
            ) as response:
                body = json.load(response)
        except (
            HTTPError, URLError, TimeoutError, json.JSONDecodeError
        ) as error:
            message = f"Local Ollama request failed: {error}"
            raise LocalAIError(message) from error

        response_text = body.get("response")
        if not isinstance(response_text, str):
            raise LocalAIError("Local Ollama returned no response text")
        return response_text


local_ai = LocalAI()
