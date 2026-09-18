"""Central configuration for the offline Joker application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    temperature: float = 0.0
    context_window: int = 8192
    request_timeout_seconds: float = 120.0
    system_prompt: str = (
        "You are Joker, a concise and capable local AI business partner and "
        "coding assistant. Work only with the information provided by the "
        "user. State uncertainty clearly and do not claim to have accessed "
        "cloud services, files, or tools unless the application provided them."
    )

    def validate(self) -> None:
        parsed = urlparse(self.ollama_host)
        if parsed.scheme != "http" or parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                "OLLAMA_HOST must use a loopback HTTP address; "
                "cloud endpoints "
                "are intentionally unsupported"
            )
        if not self.model.strip():
            raise ValueError("OLLAMA_MODEL cannot be empty")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        if self.context_window < 256:
            raise ValueError("context_window must be at least 256 tokens")


SETTINGS = Settings()
SETTINGS.validate()
