Write-Host "====================================================" -ForegroundColor Cyan
Write-Host " GARZA GLOBAL GRAVITON: MASTER CLUSTER LAUNCHER" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Clean stale processes
Write-Host "[1/3] Terminating any stale background instances..." -ForegroundColor Yellow
Stop-Process -Name "python", "ngrok" -Force -ErrorAction SilentlyContinue

# 2. Locate ngrok and launch gateway
Write-Host "[2/3] Initializing ngrok TLS public tunnel..." -ForegroundColor Yellow
$ngrok = (Get-ChildItem -Path "$env:LOCALAPPDATA", "$env:USERPROFILE\Downloads", "$env:ProgramFiles" -Filter "ngrok.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$ngrok' http 8000 --url=stamp-dangling-dugout.ngrok-free.dev"

# 3. Launch background traffic generator
Write-Host "[3/3] Starting Autonomous Enterprise Traffic Streamer..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python traffic_daemon.py"

Write-Host "
>>> Starting Main Engine & Ingress Coordinator..." -ForegroundColor Green
python -m src.main
