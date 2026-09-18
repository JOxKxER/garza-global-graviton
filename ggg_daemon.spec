# -*- mode: python ; coding: utf-8 -*-
# GGG Sovereign Edge Daemon - PyInstaller spec
# Standalone, zero-telemetry background executable.
# ggg_daemon.py is stdlib-only (hashlib/hmac/json/math/os/time/dataclasses),
# so the binary carries no third-party packages and no runtime network stack.

import sys

# strip is POSIX-only (no strip binary on Windows); PyInstaller warns per-DLL otherwise.
_strip = sys.platform != 'win32'

a = Analysis(
    ['ggg_daemon.py'],
    pathex=[],
    binaries=[],
    datas=[],          # zero bundled data: no DBs, no test payloads, no logs
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[         # belt-and-suspenders: never pull these even if imported later
        'numpy', 'scipy', 'pandas', 'matplotlib',
        'sqlite3', 'pytest', 'tkinter',
    ],
    noarchive=False,
    optimize=2,        # strip asserts + docstrings from the shipped bytecode
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ggg-daemon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=_strip,      # strip symbols on macOS/Linux; skipped on Windows
    upx=False,         # no UPX: keeps binaries AV-quiet and reproducible
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,      # background CLI daemon — headless, logs to stdout
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
