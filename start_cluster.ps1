$RepoDir = (Get-Location).Path

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  GARZA GLOBAL GRAVITON - DISTRIBUTED NODE NETWORK LAUNCHER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Kill lingering Python processes
Write-Host "[1/4] Clearing old processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Launch FastAPI REST Server
Write-Host "[2/4] Starting REST API on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process python -ArgumentList "-m src.main --api --api-port 8000" -WorkingDirectory $RepoDir -WindowStyle Hidden

Start-Sleep -Seconds 2

# 3. Launch Workers
Write-Host "[3/4] Launching Compute Nodes (node_alpha & node_beta)..." -ForegroundColor Green
Start-Process python -ArgumentList "-m src.main --worker --worker-id node_alpha" -WorkingDirectory $RepoDir -WindowStyle Hidden
Start-Process python -ArgumentList "-m src.main --worker --worker-id node_beta" -WorkingDirectory $RepoDir -WindowStyle Hidden

Start-Sleep -Seconds 1

# 4. Launch Master Coordinator in foreground
Write-Host "[4/4] Starting Master Coordinator with live monitor..." -ForegroundColor Cyan
python -m src.main --master --min-workers 2
