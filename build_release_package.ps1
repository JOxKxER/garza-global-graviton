$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$releaseZip = "GGG_MissionControl_v0.1.0_$timestamp.zip"
$auditDir = "audit_snapshots"

if (!(Test-Path $auditDir)) { New-Item -ItemType Directory -Path $auditDir | Out-Null }

Write-Host ">>> Freezing SQLite ledger snapshot..." -ForegroundColor Cyan
python archive_snapshot.py

Write-Host ">>> Bundling repository into $releaseZip..." -ForegroundColor Green
Compress-Archive -Path "src", "cluster_ledger.db", "*.py", "*.bat", "*.ps1" -DestinationPath $releaseZip -Force

Write-Host "===========================================================" -ForegroundColor Yellow
Write-Host "RELEASE PACKAGE READY: $releaseZip" -ForegroundColor Yellow
Write-Host "===========================================================" -ForegroundColor Yellow
