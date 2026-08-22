@echo off
title Garza Global Graviton - Production Cluster
echo ===============================================================
echo GARZA GLOBAL GRAVITON: LIVE PRODUCTION RUNTIME
echo ===============================================================

:: Kill any residual processes
taskkill /F /IM python.exe 2>nul
taskkill /F /IM ngrok.exe 2>nul

:: Launch Supervisor in Background
start "GGG-Supervisor" python run_live_cluster.py

:: Small buffer for socket allocation
timeout /t 3 /nobreak >nul

:: Launch Main Engine in Foreground
python -m src.main
