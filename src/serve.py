"""Minimal production server launcher for Render and local execution."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
