@echo off
title Game Server Integrity Vault Launcher
echo =======================================================
echo   STARTING FULL GAME INTEGRITY VAULT STACK
echo   - REST API Gateway (Port 8000)
echo   - Telemetry Background Worker
echo   - Streamlit Dashboard (Port 8501)
echo =======================================================
echo.

:: Start REST API Gateway
start "Vault REST API Gateway" cmd /k "python vault_api.py"

:: Start background integrity worker daemon
start "Integrity Telemetry Worker" cmd /k "python integrity_worker.py"

:: Launch Streamlit dashboard
echo Starting Streamlit Vault Dashboard...
python -m streamlit run vault_dashboard.py

pause