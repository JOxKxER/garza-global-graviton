"""Joker-Builder: an offline CLI that plans and writes GGG-grounded apps.

Run with:
    python joker_cli.py

Requires a local Ollama server (`ollama serve`) with a model already
pulled (default: `qwen2.5-coder:latest`, via `ollama pull
qwen2.5-coder:latest`). No cloud API is ever contacted; this tool is
fully offline.
"""

from __future__ import annotations

import sys

from src.app_builder.joker_compiler_bridge import JokerCompilerBridge
from src.app_builder.local_ollama_client import (
    LocalOllamaClient,
    OfflineModelUnavailableError,
)


def build_prompt(user_request: str, grounding_context: str) -> str:
    """Combine the user's request with any detected GGG grounding context."""
    if not grounding_context:
        return user_request
    return (
        f"{grounding_context}\n\n"
        f"USER PROJECT REQUEST:\n{user_request}\n\n"
        "Plan the application architecture first, then write the "
        "application code, wiring in the GGG modules listed above for "
        "any matching functionality."
    )


def run_cli() -> None:
    """Run the interactive Joker-Builder offline planning/codegen loop."""
    client = LocalOllamaClient()
    bridge = JokerCompilerBridge()

    print("Joker-Builder: offline architect (Ctrl+C to exit)")
    while True:
        try:
            user_request = input("\nDescribe the project you want built: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Joker-Builder.")
            return

        if not user_request.strip():
            continue

        grounding_context = bridge.build_grounding_context(user_request)
        full_prompt = build_prompt(user_request, grounding_context)

        try:
            response_text = client.generate(full_prompt)
        except OfflineModelUnavailableError as error:
            print(f"\n[Joker-Builder offline error] {error}")
            continue

        print("\n--- Joker's Plan & Code ---\n")
        print(response_text)


if __name__ == "__main__":
    sys.exit(run_cli() or 0)
