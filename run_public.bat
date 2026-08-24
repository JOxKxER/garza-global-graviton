@echo off
title Game Server Integrity Platform
echo =======================================================
echo    INITIALIZING GAME INTEGRITY PLATFORM & TUNNEL
echo =======================================================
echo.

cd /d "%~dp0"

:: Start Background Worker
echo [1/3] Launching Security Telemetry Daemon...
start "Integrity Daemon" /min python integrity_worker.py

:: Start Streamlit Dashboard
echo [2/3] Launching Web Dashboard...
start "Streamlit Dashboard" /min python -m streamlit run vault_dashboard.py

:: Open Secure Public Tunnel
echo [3/3] Opening Public Web Tunnel...
echo.
echo =======================================================
echo   Your live public URL will display below in a moment:
echo   (Keep this window open to maintain the web link)
echo =======================================================
echo.
ssh -o StrictHostKeyChecking=no -R 80:localhost:8501 nokey@localhost.run

pause