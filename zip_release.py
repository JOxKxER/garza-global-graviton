"""GGG Release Manager - package daemon binaries for GitHub Releases.

Collects the compiled ggg-daemon artifacts from dist/release/, verifies or
generates their SHA256 checksums, emits a single SHA256SUMS manifest plus
release notes, and stages a versioned payload directory ready to push with
the GitHub CLI (`gh release create`).

For Windows it rebuilds ggg-daemon_v<version>_windows.zip as a self-contained
bundle staged in dist/release/stage_windows_v<version>/:

  1. ggg-daemon.exe      - the compiled daemon binary
  2. index.html          - the local web dashboard
  3. install-startup.bat - registers `ggg-daemon.exe --serve` in the Windows
                           Startup folder (shell:startup)

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
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RELEASE_DIR = REPO_ROOT / "dist" / "release"

PLATFORMS = ("windows", "macos", "linux")

REPO = "JOxKxER/garza-global-graviton"

# --- Self-contained Windows bundle -------------------------------------------
# The windows zip ships three files: the daemon binary, the local web
# dashboard, and a startup installer that registers `ggg-daemon.exe --serve`
# in the Windows Startup folder (shell:startup).
DASHBOARD_HTML = REPO_ROOT / "index.html"
WINDOWS_EXE_NAME = "ggg-daemon.exe"
STARTUP_BAT_NAME = "install-startup.bat"

STARTUP_BAT_TEMPLATE = r"""@echo off
rem ============================================================
rem  GGG Sovereign Edge Daemon v{version} - startup installer
rem  Installs ggg-daemon.exe + index.html to %LOCALAPPDATA%\GGG
rem  and registers the daemon (with the --serve flag) in the
rem  Windows Startup folder - the folder `shell:startup` opens -
rem  so the loopback dashboard/API starts at every logon.
rem ============================================================
setlocal EnableExtensions

set "INSTALL_DIR=%LOCALAPPDATA%\GGG"
rem shell:startup resolves to this folder:
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER=%STARTUP_DIR%\ggg-daemon-startup.bat"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"

echo Installing ggg-daemon to %INSTALL_DIR% ...
copy /y "%~dp0ggg-daemon.exe" "%INSTALL_DIR%\ggg-daemon.exe" >nul
if errorlevel 1 (
    echo [FAIL] ggg-daemon.exe was not found next to this installer.
    echo        Extract the full zip, then run install-startup.bat again.
    exit /b 1
)
copy /y "%~dp0index.html" "%INSTALL_DIR%\index.html" >nul

echo Registering daemon in shell:startup ...
> "%LAUNCHER%" echo @start "" /min "%INSTALL_DIR%\ggg-daemon.exe" --serve

echo.
echo [OK] GGG daemon v{version} installed and registered in shell:startup.
echo      Install dir : %INSTALL_DIR%
echo      Startup     : %LAUNCHER%
echo      Dashboard   : %INSTALL_DIR%\index.html
echo      API         : http://127.0.0.1:11834 (loopback only)
echo.
echo To start it right now without logging off:
echo     "%INSTALL_DIR%\ggg-daemon.exe" --serve
endlocal
"""

RELEASE_NOTES_TEMPLATE = """# Global Graviton Gauntlet - Sovereign Edge Daemon v{version}

**Garza Global Graviton LLC** - Sovereign. Air-gapped. Locally owned.

## What's in this release

Standalone, zero-telemetry background daemon binaries:

| Platform | Download |
|---|---|
{artifact_table}

**Checksum manifest:** [SHA256SUMS.txt](https://github.com/{repo}/releases/download/v{version}/SHA256SUMS.txt)

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

## Windows quick start (self-contained bundle)

`ggg-daemon_v{version}_windows.zip` contains:

| File | Purpose |
|---|---|
| `ggg-daemon.exe` | The daemon binary |
| `index.html` | Local web dashboard |
| `install-startup.bat` | Registers `ggg-daemon.exe --serve` in `shell:startup` |

Extract the zip and run `install-startup.bat`: the daemon installs to
`%LOCALAPPDATA%\\GGG` and auto-starts at every logon, serving the loopback
API on http://127.0.0.1:11834. Open `index.html` for the local dashboard.

macOS / Linux archives extract to a single `ggg-daemon` executable. Run any
binary with no arguments to execute the self-test and print the node's
signed heartbeat.

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


def write_startup_installer(out_path: Path, version: str) -> None:
    """Emit install-startup.bat (CRLF) registering the daemon in shell:startup."""
    with open(out_path, "w", encoding="ascii", newline="\r\n") as fh:
        fh.write(STARTUP_BAT_TEMPLATE.format(version=version))


def build_windows_bundle(
    version: str,
    artifacts: dict[str, Path],
    exe_override: str | None,
) -> Path | None:
    """Stage the Windows bundle in the release folder, then compress it.

    Stages ggg-daemon.exe + index.html + install-startup.bat into
    dist/release/stage_windows_v<version>/ and zips them into
    ggg-daemon_v<version>_windows.zip.

    The exe comes from --exe when given; otherwise it is extracted from the
    existing (exe-only) windows archive produced by build_ggg_daemon.ps1.
    Returns the rebuilt zip path, or None when no windows exe is available.
    """
    if not DASHBOARD_HTML.exists():
        print(f"[WARN] Dashboard not found at {DASHBOARD_HTML}; windows bundle skipped.")
        return None

    tmp_dir: Path | None = None
    if exe_override:
        exe_src = Path(exe_override)
        if not exe_src.is_file():
            print(f"[WARN] --exe not found: {exe_src}; windows bundle skipped.")
            return None
    else:
        win_zip = artifacts.get("windows")
        if win_zip is None or not zipfile.is_zipfile(win_zip):
            return None
        with zipfile.ZipFile(win_zip) as zf:
            member = next(
                (n for n in zf.namelist() if Path(n).name == WINDOWS_EXE_NAME), None
            )
            if member is None:
                return None
            # Extract to disposable %TEMP% (matches build_ggg_daemon.ps1's
            # out-of-repo staging convention for disposable artifacts).
            tmp_dir = Path(tempfile.mkdtemp(prefix="ggg-win-exe-"))
            zf.extract(member, tmp_dir)
        exe_src = tmp_dir / member

    try:
        stage_dir = RELEASE_DIR / f"stage_windows_v{version}"
        if stage_dir.exists():
            shutil.rmtree(stage_dir)
        stage_dir.mkdir(parents=True)

        shutil.copy2(exe_src, stage_dir / WINDOWS_EXE_NAME)
        shutil.copy2(DASHBOARD_HTML, stage_dir / "index.html")
        write_startup_installer(stage_dir / STARTUP_BAT_NAME, version)

        zip_path = RELEASE_DIR / f"ggg-daemon_v{version}_windows.zip"
        zip_path.unlink(missing_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(stage_dir.iterdir()):
                zf.write(item, arcname=item.name)

        print(
            f"  + windows  {zip_path.name}  <- "
            f"{WINDOWS_EXE_NAME} + index.html + {STARTUP_BAT_NAME}"
        )
        return zip_path
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)


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


def write_checksums(version: str, artifacts: dict[str, Path], out_path: Path) -> list[str]:
    """Write SHA256SUMS.txt covering every artifact; returns table rows."""
    lines: list[str] = []
    rows: list[str] = []
    for platform, path in sorted(artifacts.items()):
        digest = sha256_of(path)
        lines.append(f"{digest}  {path.name}")
        size_mb = path.stat().st_size / (1024 * 1024)
        # Absolute download URL so the release-notes table links work publicly.
        dl_url = f"https://github.com/{REPO}/releases/download/v{version}/{path.name}"
        rows.append(f"| {platform.title()} | [{path.name}]({dl_url}) ({size_mb:.1f} MB) |")
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
        repo=REPO,
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
    parser.add_argument(
        "--exe",
        help="Path to a freshly compiled ggg-daemon.exe for the windows bundle. "
             "Default: reuse the exe inside the existing windows zip.",
    )
    args = parser.parse_args()
    version: str = args.version

    artifacts = discover_artifacts(version)
    if not artifacts and not args.exe:
        print(f"[FAIL] No ggg-daemon v{version} artifacts found in {RELEASE_DIR}.")
        print("       Run build_ggg_daemon.ps1 on each target OS first.")
        return 1

    # Windows: stage ggg-daemon.exe + index.html + install-startup.bat in the
    # release folder, then rebuild ggg-daemon_v<version>_windows.zip from them.
    print("Building self-contained Windows bundle:")
    bundle = build_windows_bundle(version, artifacts, args.exe)
    if bundle is not None:
        artifacts["windows"] = bundle
    elif "windows" in artifacts:
        print("[WARN] Bundle inputs unavailable; keeping exe-only windows archive.")
    else:
        print("[WARN] No ggg-daemon.exe available; windows bundle skipped.")

    missing = [p for p in PLATFORMS if p not in artifacts]
    if missing:
        print(f"[WARN] Missing platform binaries: {', '.join(missing)} (payload will be partial)")

    print(f"\nPackaging v{version} payload:")
    for platform, path in sorted(artifacts.items()):
        print(f"  + {platform:8s} {path.name}")

    rows = write_checksums(version, artifacts, RELEASE_DIR / "SHA256SUMS.txt")
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
