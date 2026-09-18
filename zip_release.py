"""GGG Release Manager - package daemon binaries for GitHub Releases.

Collects the compiled ggg-daemon artifacts from dist/release/, verifies or
generates their SHA256 checksums, emits a single SHA256SUMS manifest plus
release notes, and stages a versioned payload directory ready to push with
the GitHub CLI (`gh release create`).

The community download button on index.html points at the repo's
/releases/latest URL, so publishing this payload makes it functional.

Usage:
    python zip_release.py --version 1.4.5
    python zip_release.py --version 1.4.5 --publish   # runs gh release create
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RELEASE_DIR = REPO_ROOT / "dist" / "release"

PLATFORMS = ("windows", "macos", "linux")

RELEASE_NOTES_TEMPLATE = """# Global Graviton Gauntlet - Sovereign Edge Daemon v{version}

**Garza Global Graviton LLC** - Sovereign. Air-gapped. Locally owned.

## What's in this release

Standalone, zero-telemetry background daemon binaries:

| Platform | Artifact |
|---|---|
{artifact_table}

Every binary passes the on-board self-test (pi-engine admission gate,
non-zero-sum vault balancer, HMAC-SHA256 cryptographic brand) before packaging.

## Verify authenticity

Download `SHA256SUMS.txt` alongside your binary, then:

```powershell
# Windows (PowerShell)
Get-FileHash .\\ggg-daemon_v{version}_windows.zip -Algorithm SHA256
```

```bash
# macOS / Linux
shasum -a 256 -c SHA256SUMS.txt --ignore-missing
```

Each zip extracts to a single `ggg-daemon(.exe)` executable. Run it with no
arguments to execute the self-test and print the node's signed heartbeat.

## Community license

Free forever for personal, hobbyist, and academic use under the
GGG Source-Available Non-Commercial License (see LICENSE.md). Commercial
deployment requires a signed license - see ENTERPRISE_PARTNERSHIPS.md.

Built {build_date}.
"""


def sha256_of(path: Path) -> str:
    """Stream a file's SHA256 without loading it into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def discover_artifacts(version: str) -> dict[str, Path]:
    """Find per-platform daemon archives produced by build_ggg_daemon.ps1."""
    found: dict[str, Path] = {}
    for platform in PLATFORMS:
        for ext in (".zip", ".tar.gz"):
            candidate = RELEASE_DIR / f"ggg-daemon_v{version}_{platform}{ext}"
            if candidate.exists():
                found[platform] = candidate
                break
    return found


def write_checksums(artifacts: dict[str, Path], out_path: Path) -> list[str]:
    """Write SHA256SUMS.txt covering every artifact; returns table rows."""
    lines: list[str] = []
    rows: list[str] = []
    for platform, path in sorted(artifacts.items()):
        digest = sha256_of(path)
        lines.append(f"{digest}  {path.name}")
        size_mb = path.stat().st_size / (1024 * 1024)
        rows.append(f"| {platform.title()} | `{path.name}` ({size_mb:.1f} MB) |")
        # Per-file sidecar, matching build_ggg_daemon.ps1 conventions.
        path.with_suffix(path.suffix + ".sha256").write_text(digest + "\n", encoding="ascii")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def stage_payload(version: str, artifacts: dict[str, Path], rows: list[str]) -> Path:
    """Copy artifacts + manifest + notes into a versioned payload directory."""
    payload_dir = RELEASE_DIR / f"payload_v{version}"
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True)

    for path in artifacts.values():
        shutil.copy2(path, payload_dir / path.name)
    shutil.copy2(RELEASE_DIR / "SHA256SUMS.txt", payload_dir / "SHA256SUMS.txt")

    notes = RELEASE_NOTES_TEMPLATE.format(
        version=version,
        artifact_table="\n".join(rows),
        build_date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    (payload_dir / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    return payload_dir


def publish(version: str, payload_dir: Path) -> int:
    """Push the payload to GitHub Releases via the gh CLI."""
    if not shutil.which("gh"):
        print("[FAIL] GitHub CLI (gh) not found. Install from https://cli.github.com")
        return 1

    tag = f"v{version}"
    files = [str(p) for p in sorted(payload_dir.iterdir()) if p.name != "RELEASE_NOTES.md"]
    cmd = [
        "gh", "release", "create", tag,
        *files,
        "--title", f"GGG Sovereign Edge Daemon {tag}",
        "--notes-file", str(payload_dir / "RELEASE_NOTES.md"),
        "--latest",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Package GGG daemon release payload.")
    parser.add_argument("--version", default="1.4.5", help="Release version (default: 1.4.5)")
    parser.add_argument("--publish", action="store_true", help="Push to GitHub Releases via gh CLI")
    args = parser.parse_args()
    version: str = args.version

    artifacts = discover_artifacts(version)
    if not artifacts:
        print(f"[FAIL] No ggg-daemon v{version} artifacts found in {RELEASE_DIR}.")
        print("       Run build_ggg_daemon.ps1 on each target OS first.")
        return 1

    missing = [p for p in PLATFORMS if p not in artifacts]
    if missing:
        print(f"[WARN] Missing platform binaries: {', '.join(missing)} (payload will be partial)")

    print(f"Packaging v{version} payload:")
    for platform, path in sorted(artifacts.items()):
        print(f"  + {platform:8s} {path.name}")

    rows = write_checksums(artifacts, RELEASE_DIR / "SHA256SUMS.txt")
    payload_dir = stage_payload(version, artifacts, rows)

    print(f"\n[OK] Payload staged at {payload_dir}")
    print(f"[OK] SHA256SUMS.txt written ({len(artifacts)} artifact(s))")

    if args.publish:
        return publish(version, payload_dir)

    print("\nTo publish (makes the index.html community download live):")
    print(f"  python zip_release.py --version {version} --publish")
    print("or manually:")
    print(f"  gh release create v{version} \"{payload_dir}\\*\" --notes-file \"{payload_dir}\\RELEASE_NOTES.md\" --latest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
