@echo off
title Compiling Game Server Integrity Suite to Executable
echo =======================================================
echo    BUILDING STANDALONE WINDOWS EXECUTABLE (.EXE)
echo =======================================================
echo.

cd /d "%~dp0"

:: Ensure PyInstaller is installed via Python
echo [1/3] Installing/Verifying PyInstaller...
python -m pip install -q pyinstaller

:: Compile using python -m PyInstaller so Windows finds it
echo [2/3] Compiling Python modules...
python -m PyInstaller --noconfirm --onedir --clean ^
    --name="ServerVaultNode" ^
    --add-data "db_manager.py;." ^
    --add-data "integrity_worker.py;." ^
    vault_dashboard.py

echo [3/3] Build complete! 
echo Executable output located in: V:\03_Source_Code\dist\ServerVaultNode\
echo.
pause