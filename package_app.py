"""GGG Synthetic Data Center - Phase 3 standalone distribution packager.

Bundles the core engine (the whole `src/` package tree, which includes
`organs/`, `c2/`, `llm/`, and every other subsystem `run_benchmarks.py`
depends on) plus the root `index.html` platform file into a clean,
self-contained release folder under `dist/`. Only the engine source tree
and explicitly whitelisted root files are copied -- no credentials,
databases, or unrelated root-level scripts are pulled into the bundle.
"""

from __future__ import annotations

import compileall
import py_compile
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RELEASE_NAME = "ggg_synthetic_datacenter_v1.4"
DIST_DIR = REPO_ROOT / "dist" / RELEASE_NAME

# Only these root-level files are ever copied into the bundle.
ROOT_FILES_TO_BUNDLE = ["index.html", "run_benchmarks.py", "requirements.txt"]

# Directory names to skip everywhere while copying the src/ tree.
EXCLUDED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git", "venv", ".venv"}


def _ignore_unwanted(directory: str, names: list[str]) -> set[str]:
    """shutil.copytree ignore-callback: skip caches, venvs, and bytecode."""
    return {
        name
        for name in names
        if name in EXCLUDED_DIR_NAMES or name.endswith((".pyc", ".pyo"))
    }


def clean_dist() -> None:
    """Remove any previous build of this release so packaging is idempotent."""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)


def bundle_core_engine() -> None:
    """Copy the full src/ engine tree (organs, c2, llm, etc.) into the bundle."""
    source_src = REPO_ROOT / "src"
    if not source_src.exists():
        raise FileNotFoundError(f"Expected core engine at {source_src}, but it does not exist.")
    shutil.copytree(source_src, DIST_DIR / "src", ignore=_ignore_unwanted)


def bundle_root_files() -> None:
    """Copy the whitelisted root-level platform files into the bundle."""
    for filename in ROOT_FILES_TO_BUNDLE:
        source_path = REPO_ROOT / filename
        if source_path.exists():
            shutil.copy2(source_path, DIST_DIR / filename)
        else:
            print(f"[WARN] Skipping missing root file: {filename}")

    # Bundle the benchmark video alongside index.html so the page renders as-is.
    video_source = REPO_ROOT / "ggg-edge-benchmark.mp4"
    if video_source.exists():
        shutil.copy2(video_source, DIST_DIR / "ggg-edge-benchmark.mp4")


def write_launcher() -> None:
    """Write run_node.py, which boots the organ core and opens the local UI."""
    launcher_source = '''"""GGG Synthetic Data Center - offline node launcher.

Initializes the SyntheticOrganCore for one warm-up cycle (confirming the
engine is alive) and opens the bundled index.html in the default browser.
No network access is required; everything runs from local files.
"""

import sys
import webbrowser
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BUNDLE_ROOT))

from src.organs.synthetic_organ_core import SyntheticOrganCore  # noqa: E402


def main() -> None:
    core = SyntheticOrganCore(capacity_bytes=1 << 20, target_hz=1000.0)
    print("Booting Synthetic Data Center organ core...")
    for sample in core.run_cycle():
        print(f"  [{sample.organ_name}] {sample.as_dict()}")

    index_path = BUNDLE_ROOT / "index.html"
    if index_path.exists():
        print(f"Opening local interface: {index_path}")
        webbrowser.open(index_path.as_uri())
    else:
        print("[WARN] index.html not found in bundle; skipping browser launch.")


if __name__ == "__main__":
    main()
'''
    (DIST_DIR / "run_node.py").write_text(launcher_source, encoding="utf-8")

    # Windows double-click convenience wrapper around the Python launcher.
    batch_source = "@echo off\r\npython \"%~dp0run_node.py\"\r\npause\r\n"
    (DIST_DIR / "run_node.bat").write_text(batch_source, encoding="utf-8")


def write_readme() -> None:
    """Write a quick-start README.md into the distribution folder."""
    readme_source = f"""# {RELEASE_NAME}

Garza Global Graviton (GGG) Synthetic Data Center -- standalone offline release.

## What's in this bundle

- `src/` -- the full core engine (`organs/`, `c2/`, `llm/`, and every other
  subsystem module used by the benchmark suite and the organ core).
- `index.html` -- the local platform UI (retro plaque, #GGG manifesto,
  physics benchmark table, and the local Ollama bridge).
- `run_benchmarks.py` -- the 61-module benchmark suite.
- `run_node.py` / `run_node.bat` -- launcher that boots the organ core and
  opens the local interface.

## Quick start (100% offline)

1. Install Python 3.10+ and the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Launch the node:

   ```
   python run_node.py
   ```

   (Windows users can instead double-click `run_node.bat`.)

   This boots the `SyntheticOrganCore`, runs one warm-up cycle across the
   Heart/Liver/Lungs/Immune System daemons, and opens `index.html` in your
   default browser -- no server or internet connection required.

## Optional: local Ollama bridge

The bundled `index.html` includes a hardened local Ollama bridge (chat +
live benchmark widgets). To use it:

1. Install [Ollama](https://ollama.com) and start it locally.
2. Pull a lightweight model, e.g.:

   ```
   ollama pull llama3.2:3b
   ```

3. In the page, confirm the endpoint reads `http://localhost:11434` and
   click **Check Status** -- the badge should turn **ONLINE**.

The bridge only ever talks to `localhost` / `127.0.0.1` / `[::1]`; any other
host is rejected client-side before a request is sent, keeping the platform
fully air-gapped by construction.

## Running the 61-module benchmark suite

```
python run_benchmarks.py
```

This exercises every subsystem module (aerodynamics, astrodynamics, c2,
comms, cryptography, distributed, estimation, guidance, hardware, physics,
power, quantum, robotics, routing, security, swarm, telemetry, and the
organ core) and prints a per-module timing report.
"""
    (DIST_DIR / "README.md").write_text(readme_source, encoding="utf-8")


def verify_dist_compiles() -> bool:
    """Byte-compile every .py file in the bundle to confirm it's valid Python."""
    print("\nVerifying bundle compiles...")
    ok = compileall.compile_dir(str(DIST_DIR), quiet=1, force=True)
    if not ok:
        print("[FAIL] One or more modules in the bundle failed to compile.")
        return False

    # Double-check the launcher itself in isolation.
    try:
        py_compile.compile(str(DIST_DIR / "run_node.py"), doraise=True)
    except py_compile.PyCompileError as exc:
        print(f"[FAIL] Launcher failed to compile: {exc}")
        return False

    print("[OK] All bundled modules compiled successfully.")
    return True


def clean_compile_artifacts() -> None:
    """Remove __pycache__ dirs left behind by the compile-verification step."""
    for cache_dir in DIST_DIR.rglob("__pycache__"):
        shutil.rmtree(cache_dir)


def main() -> int:
    print(f"Packaging {RELEASE_NAME} -> {DIST_DIR}")
    clean_dist()
    bundle_core_engine()
    bundle_root_files()
    write_launcher()
    write_readme()

    success = verify_dist_compiles()
    clean_compile_artifacts()
    print(f"\nRelease folder: {DIST_DIR}")
    print("Status:", "SUCCESS" if success else "FAILED")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
