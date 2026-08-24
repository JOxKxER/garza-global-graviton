@echo off
title Garza Global Graviton - Stakeholder & Investor Portal Launch
echo =======================================================
echo    INITIALIZING INVESTOR & AGENCY EVALUATION PORTAL
echo =======================================================
echo.

cd /d "%~dp0"

:: Start Investor Portal on Port 8502
echo [1/2] Launching Read-Only Investor Portal (Port 8502)...
start "Investor Portal" /min python -m streamlit run investor_portal.py --server.port 8502

:: Open Secure Public Tunnel for Investors
echo [2/2] Opening Secure Public Tunnel for Stakeholders...
echo =======================================================
echo   Your live public investor URL will display below:
echo =======================================================
echo.
ssh -o StrictHostKeyChecking=no -R 80:localhost:8502 nokey@localhost.run

pause