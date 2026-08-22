@echo off
title Garza Global Graviton - Engine
cd /d "%~dp0"
start http://localhost:8000
python -m src.main
pause
