@echo off
title Garza Global Graviton - Modular Suite Master Launcher
echo =======================================================
echo    INITIALIZING MODULAR PLATFORM SUITE (PORTS 8501-8504)
echo =======================================================
cd /d "%~dp0"

:: 1. Start Gaming Telemetry & Fleet Portal (Port 8501)
echo [1/4] Launching Gaming Telemetry Portal (Port 8501)...
start "Gaming Telemetry" python -m streamlit run portals/gaming_telemetry.py --server.port 8501

:: 2. Start Human Data Crunch Task Broker Portal (Port 8502)
echo [2/4] Launching Data Crunch Portal (Port 8502)...
start "Data Crunch" python -m streamlit run portals/data_crunch.py --server.port 8502

:: 3. Start Illinois LLC Compliance Vault Portal (Port 8503)
echo [3/4] Launching Compliance Vault Portal (Port 8503)...
start "Compliance Vault" python -m streamlit run portals/illinois_compliance_vault.py --server.port 8503

:: 4. Start NDA Concept Preview Portal (Port 8504)
echo [4/4] Launching NDA Preview Portal (Port 8504)...
start "NDA Portal" python -m streamlit run portals/nda_portal.py --server.port 8504

echo.
echo =======================================================
echo    ALL MICRO-PORTALS DEPLOYED INDEPENDENTLY
echo =======================================================
echo - Gaming Telemetry:      http://localhost:8501
echo - Data Crunch Broker:    http://localhost:8502
echo - Compliance Vault:      http://localhost:8503
echo - NDA Concept Preview:   http://localhost:8504
echo =======================================================
pause