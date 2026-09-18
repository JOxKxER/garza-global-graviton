"""Offline Ollama engine wrapper for Joker."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
import socket
from typing import Any
from urllib.parse import urlparse

import ollama

from config import Settings


class JokerEngineError(RuntimeError):
    """Raised when the local Ollama engine cannot complete a request."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class JokerEngine:
    """Small, synchronous wrapper around the official Ollama Python client."""

    def __init__(self, settings: Settings) -> None:
        settings.validate()
        self.settings = settings
        self.client = ollama.Client(
            host=settings.ollama_host,
            timeout=settings.request_timeout_seconds,
        )

    def check_connection(self) -> bool:
        """Confirm the loopback Ollama socket is accepting traffic."""
        parsed = urlparse(self.settings.ollama_host)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        try:
            with socket.create_connection(
                (host, port),
                timeout=min(self.settings.request_timeout_seconds, 3.0),
            ):
                return True
        except (OSError, TimeoutError) as error:
            raise JokerEngineError(
                "Joker cannot reach Ollama at "
                f"{self.settings.ollama_host}. Ensure the Ollama background "
                "service is running and the requested model is installed "
                f"with `ollama pull {self.settings.model}`."
            ) from error

    def _ensure_connection(self) -> None:
        self.check_connection()

    def _friendly_error(self, error: Exception) -> JokerEngineError:
        return JokerEngineError(
            "Joker could not complete the local Ollama request. Confirm the "
            f"Ollama service is running at {self.settings.ollama_host} and "
            f"that `{self.settings.model}` is installed: {error}"
        )

    def available_models(self) -> list[str]:
        try:
            self._ensure_connection()
            response = self.client.list()
            models = response.get("models", [])
            return [str(model.get("name", "")) for model in models]
        except Exception as error:
            if isinstance(error, JokerEngineError):
                raise
            raise self._friendly_error(error) from error

    def stream_chat(
        self,
        messages: Sequence[ChatMessage],
    ) -> Iterator[str]:
        """Yield response text chunks from the local Ollama model."""
        if not messages or messages[-1].role != "user":
            raise ValueError("the final chat message must be from the user")

        payload = [message.as_dict() for message in messages]
        try:
            self._ensure_connection()
            stream = self.client.chat(
                model=self.settings.model,
                messages=payload,
                stream=True,
                options={
                    "temperature": self.settings.temperature,
                    "num_ctx": self.settings.context_window,
                },
            )
            for chunk in stream:
                if content := _chunk_content(chunk):
                    yield content
        except Exception as error:
            if isinstance(error, JokerEngineError):
                raise
            raise self._friendly_error(error) from error


def _chunk_content(chunk: Any) -> str:
    if isinstance(chunk, dict):
        message = chunk.get("message", {})
        return str(message.get("content", ""))
    message = getattr(chunk, "message", None)
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(getattr(message, "content", ""))
