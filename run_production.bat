@echo off
title Garza Global Graviton - Production Cluster Supervisor
echo ===============================================================
echo GARZA GLOBAL GRAVITON - SUPERVISED SYSTEM RUNNER
echo ===============================================================

:: 1. Kill stale instances
taskkill /F /IM ngrok.exe 2>nul
taskkill /F /IM python.exe 2>nul

:: 2. Locate ngrok executable
for /f "delims=" %%i in ('where ngrok.exe 2^>nul') do set NGROK_EXE=%%i
if "%NGROK_EXE%"=="" (
    if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" set NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe
    if exist "%USERPROFILE%\Downloads\ngrok.exe" set NGROK_EXE=%USERPROFILE%\Downloads\ngrok.exe
)

:: 3. Spawn ngrok in isolated background terminal
start "GGG-Public-Gateway" "%NGROK_EXE%" http 8000 --url=stamp-dangling-dugout.ngrok-free.dev

:: 4. Small delay to let network stack bind
timeout /t 2 /nobreak >nul

:: 5. Launch Traffic Daemon in separate background terminal
start "GGG-Traffic-Daemon" python traffic_daemon.py

:: 6. Launch Main Coordinator Engine in Foreground
echo Ingress API starting on port 8000...
python -m src.main
