@echo off
title Garza Global Graviton - Live Cluster
start http://127.0.0.1:8000
python -m src.main --all-in-one
pause
