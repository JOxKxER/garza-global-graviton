"""Shared configuration for local Joker AI integrations."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LocalAISettings:
    """Connection settings for a loopback-only Ollama service."""

    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))


local_ai_settings = LocalAISettings()
