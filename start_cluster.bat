@echo off
title Garza Global Graviton - Cluster Engine
echo ====================================================
echo Starting GGG Engine & Ngrok Public Gateway
echo ====================================================

:: Find ngrok.exe
for /f "delims=" %%i in ('where ngrok.exe 2^>nul') do set NGROK_EXE=%%i
if "%NGROK_EXE%"=="" (
    if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" set NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe
    if exist "%USERPROFILE%\Downloads\ngrok.exe" set NGROK_EXE=%USERPROFILE%\Downloads\ngrok.exe
)

:: Launch ngrok tunnel in independent window
start "GGG-Ngrok-Gateway" "%NGROK_EXE%" http 8000 --url=stamp-dangling-dugout.ngrok-free.dev

:: Start Python backend engine in primary window
python -m src.main
