import sys
import os
import shutil
from pathlib import Path
import PyInstaller.__main__

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "assets" / "graviton.ico"

# Clean previous build artifacts
for folder in ["build", "dist"]:
    p = BASE_DIR / folder
    if p.exists():
        try:
            shutil.rmtree(p)
        except Exception:
            pass

spec_file = BASE_DIR / "Garza_Global_Graviton.spec"
if spec_file.exists():
    try:
        spec_file.unlink()
    except Exception:
        pass

build_args = [
    str(BASE_DIR / 'src' / 'main.py'),
    '--name=Garza_Global_Graviton',
    '--onefile',
    '--noconfirm',
    f'--add-data={str(BASE_DIR / "src")};src',
    f'--distpath={str(BASE_DIR / "dist")}',
    f'--workpath={str(BASE_DIR / "build")}',
]

if ICON_PATH.exists():
    build_args.append(f'--icon={str(ICON_PATH)}')
    print(f"[*] Bundling icon: {ICON_PATH}")

PyInstaller.__main__.run(build_args)
print("\n[+] Standalone build complete: dist/Garza_Global_Graviton.exe")
