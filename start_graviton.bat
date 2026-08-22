@echo off
title Garza Global Graviton - Mission Control Engine
cd /d "V:\03_Source_Code"
echo [*] Launching Garza Global Graviton Cluster...
start http://localhost:8000
python -m src.main
pause
