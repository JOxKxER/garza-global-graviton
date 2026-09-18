$ErrorActionPreference = 'Stop'
$sourceRoot = 'V:\03_Source_Code'
$python = Join-Path $sourceRoot '.venv\Scripts\python.exe'
$dashboardUrl = 'http://127.0.0.1:8090'

if (-not (Test-Path $python)) {
    throw "Virtual environment Python not found: $python"
}

$pythonProcesses = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'"
$dashboardRunning = $pythonProcesses | Where-Object {
    $_.CommandLine -match 'uvicorn sports_analytics_dashboard:app'
}
$feederRunning = $pythonProcesses | Where-Object {
    $_.CommandLine -match 'feed_dashboard.py'
}

if (-not $dashboardRunning) {
    Start-Process -FilePath $python -WorkingDirectory $sourceRoot -ArgumentList @(
        '-m', 'uvicorn', 'sports_analytics_dashboard:app',
        '--host', '127.0.0.1', '--port', '8090'
    ) -WindowStyle Minimized
}

if (-not $feederRunning) {
    Start-Process -FilePath $python -WorkingDirectory $sourceRoot -ArgumentList @(
        (Join-Path $sourceRoot 'feed_dashboard.py'), '--interval', '15'
    ) -WindowStyle Minimized
}

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "$dashboardUrl/health" -TimeoutSec 2
        if ($health.status -eq 'ok') {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ready) {
    throw "Sports dashboard did not become ready at $dashboardUrl"
}

$chromePaths = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)
$chrome = $chromePaths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($chrome) {
    Start-Process -FilePath $chrome -ArgumentList $dashboardUrl
} else {
    Start-Process $dashboardUrl
}
