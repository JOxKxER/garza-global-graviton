@echo off
title Garza Global Graviton - Topology Orchestrator
echo ===============================================================
echo GARZA GLOBAL GRAVITON: INITIALIZING ARCHITECTURAL TOPOLOGY
echo ===============================================================

taskkill /F /IM ngrok.exe 2>nul
taskkill /F /IM python.exe 2>nul

for /f "delims=" %%i in ('where ngrok.exe 2^>nul') do set NGROK_EXE=%%i
if "%NGROK_EXE%"=="" (
    if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" set NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe
    if exist "%USERPROFILE%\Downloads\ngrok.exe" set NGROK_EXE=%USERPROFILE%\Downloads\ngrok.exe
)

echo [1/4] Spawning TLS Gateway (:8000)...
start "GGG-TLS-Gateway" "%NGROK_EXE%" http 8000 --url=stamp-dangling-dugout.ngrok-free.dev

timeout /t 2 /nobreak >nul

echo [2/4] Spawning Multi-Core Compute Shards...
start "GGG-Worker-Core-01" python shard_worker.py
start "GGG-Worker-Core-02" python shard_worker.py

echo [3/4] Spawning Traffic Simulation Engine...
start "GGG-Traffic-Daemon" python traffic_daemon.py

echo [4/4] Starting Master Ingress & Non-Blocking Shard Coordinator...
python -m src.main
