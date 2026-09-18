[CmdletBinding()]
param(
    [string]$Action = "Start",
    [string]$SourceRoot = "V:\03_Source_Code",
    [string]$BotPath = "V:\03_Source_Code\bot.py"
)

$ErrorActionPreference = "Stop"
$StateFile = Join-Path $SourceRoot ".server_state.json"
$VenvPython = Join-Path $SourceRoot ".venv\Scripts\python.exe"

function Read-State {
    if (Test-Path $StateFile) {
        try {
            $json = Get-Content $StateFile -Raw
            if ($json) {
                return @(ConvertFrom-Json $json)
            }
        } catch {}
    }
    return @()
}

function Write-State($stateData) {
    $stateData | ConvertTo-Json -Depth 5 | Set-Content $StateFile -Encoding utf8
}

function Test-Ollama {
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

if ($Action -eq "Cleanup") {
    Write-Host "=== Cleaning up managed servers ===" -ForegroundColor Cyan
    $pids = Read-State
    foreach ($item in $pids) {
        $targetPid = if ($item.pid) { $item.pid } else { $item.Pid }
        if ($targetPid) {
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped process ID: $targetPid" -ForegroundColor Green
            } catch {}
        }
    }
    if (Test-Path $StateFile) { Remove-Item $StateFile -Force }
    Write-Host "Cleanup complete." -ForegroundColor Green
    return
}

if ($Action -eq "Status") {
    Write-Host "=== Service Status ===" -ForegroundColor Cyan
    $ollamaActive = Test-Ollama
    Write-Host "Ollama API: $(if ($ollamaActive) { 'Running (http://127.0.0.1:11434)' } else { 'Not Responding' })"
    
    $pids = Read-State
    $activeCount = 0
    foreach ($item in $pids) {
        $targetPid = if ($item.pid) { $item.pid } else { $item.Pid }
        $name = if ($item.name) { $item.name } else { $item.Name }
        if ($targetPid) {
            $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "[$name] PID $targetPid is Running" -ForegroundColor Green
                $activeCount++
            } else {
                Write-Host "[$name] PID $targetPid is Stopped" -ForegroundColor Yellow
            }
        }
    }
    if ($activeCount -eq 0) { Write-Host "No active launcher-managed services recorded." -ForegroundColor Gray }
    return
}

Write-Host "=== Validating local services ===" -ForegroundColor Cyan
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment python not found at $VenvPython"
}
Write-Host "Python: $VenvPython"

if (-not (Test-Path $BotPath)) {
    throw "bot.py was not found under $SourceRoot. Supply -BotPath when available."
}
Write-Host "Bot: $BotPath"

function Invoke-PythonQuietly {
    param(
        [string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $VenvPython @Arguments 2>&1 | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

# Validate packages
$requiredPackages = @("uvicorn", "fastapi", "httpx", "beautifulsoup4", "feedparser")
foreach ($pkg in $requiredPackages) {
    $importExitCode = Invoke-PythonQuietly -Arguments @("-c", "import $pkg")
    if ($importExitCode -ne 0) {
        Write-Host "Installing missing dependency: $pkg" -ForegroundColor Yellow
        $installExitCode = Invoke-PythonQuietly -Arguments @("-m", "pip", "install", $pkg)
        if ($installExitCode -ne 0) {
            throw "Failed to install dependency: $pkg (python exit code $installExitCode)"
        }
    }
}

# Check Ollama
$ollamaRunning = Test-Ollama
if (-not $ollamaRunning) {
    Write-Host "Starting Ollama service..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 3
} else {
    Write-Host "Ollama API is already ready; no duplicate instance needed." -ForegroundColor Green
}

$runningState = @()

# Start RapidAPI Scraper
Write-Host "Launching RapidAPI Scraper (Port 8000)..." -ForegroundColor Cyan
$scraperArgs = "-NoProfile -Command `"cd '$SourceRoot'; & '$VenvPython' -m uvicorn rapidapi_scraper.app:app --reload --port 8000; Read-Host 'Press Enter to exit...'`""
$scraperProc = Start-Process powershell -ArgumentList $scraperArgs -PassThru
$runningState += @{ name = "RapidAPI Scraper"; pid = $scraperProc.Id }

# Start Gig Tracker Bot
Write-Host "Launching Gig Tracker Bot..." -ForegroundColor Cyan
$botArgs = "-NoProfile -Command `"cd '$SourceRoot'; & '$VenvPython' '$BotPath'; Read-Host 'Press Enter to exit...'`""
$botProc = Start-Process powershell -ArgumentList $botArgs -PassThru
$runningState += @{ name = "Gig Tracker Bot"; pid = $botProc.Id }

Write-State $runningState

Write-Host @"

=== Started ===
RapidAPI: http://127.0.0.1:8000
Ollama:   http://127.0.0.1:11434
Use -Action Status or -Action Cleanup to manage services.
"@ -ForegroundColor Green
