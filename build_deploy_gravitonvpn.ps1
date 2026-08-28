[CmdletBinding()]
param(
    [Parameter()]
    [string]$SearchRoot = "V:\03_Source_Code",

    [Parameter()]
    [string]$GradleTask = "assembleDebug",

    [Parameter()]
    [string]$PackageName = "com.garza.globalgraviton",

    [Parameter()]
    [string]$VpnServiceClass = "com.garza.globalgraviton.network.GravitonVpnService",

    [Parameter()]
    [string]$Serial = "R5CN202TSKN",

    [Parameter()]
    [string]$GatewayUrl = "http://10.238.126.142:5000/api/v1/sensory/telemetry",

    [Parameter()]
    [string]$AdbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- 1. Locate the Android project root -----------------------------------
Write-Host "=== Locating Android project root under $SearchRoot ==="

$wrapper = Get-ChildItem -Path $SearchRoot -Filter "gradlew.bat" -File -Recurse -ErrorAction SilentlyContinue |
    Sort-Object { $_.FullName.Length } |
    Select-Object -First 1

if ($wrapper) {
    $ProjectRoot = $wrapper.Directory.FullName
} else {
    # No wrapper; fall back to a directory containing a Gradle build/settings file.
    $buildFile = Get-ChildItem -Path $SearchRoot -Include "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts" -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object { $_.FullName.Length } |
        Select-Object -First 1

    if (-not $buildFile) {
        throw "No gradlew.bat or Gradle build file was found under $SearchRoot. Confirm the Android project has been checked out."
    }
    $ProjectRoot = $buildFile.Directory.FullName
    $wrapper = Get-ChildItem -Path $ProjectRoot -Filter "gradlew.bat" -File -ErrorAction SilentlyContinue | Select-Object -First 1
}

Write-Host "Project root: $ProjectRoot"

# --- 2. Run the Gradle build ------------------------------------------------
Write-Host "=== Building ($GradleTask) ==="
Push-Location $ProjectRoot
try {
    if ($wrapper) {
        & (Join-Path $ProjectRoot "gradlew.bat") $GradleTask
    } elseif (Get-Command gradle -ErrorAction SilentlyContinue) {
        Write-Warning "gradlew.bat not found in $ProjectRoot; falling back to system Gradle."
        & gradle $GradleTask
    } else {
        throw "Neither gradlew.bat nor a system 'gradle' command is available."
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle task '$GradleTask' failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$apk = Get-ChildItem -Path $ProjectRoot -Filter "*.apk" -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "[\\/]build[\\/]outputs[\\/]apk[\\/]" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $apk) {
    throw "Gradle build succeeded but no APK was found under $ProjectRoot\**\build\outputs\apk."
}
Write-Host "Built APK: $($apk.FullName)"

# --- 3. Verify the device is detected ---------------------------------------
if (-not (Test-Path $AdbPath)) {
    throw "adb.exe was not found at $AdbPath. Pass -AdbPath to override."
}

Write-Host "=== Verifying device $Serial ==="
& $AdbPath start-server | Out-Null

$deviceLines = & $AdbPath devices
Write-Host ($deviceLines -join "`n")

$matchLine = $deviceLines | Where-Object { $_ -match "^$([regex]::Escape($Serial))\s+(\w+)" }
if (-not $matchLine) {
    throw "Device '$Serial' was not found by adb. Check the USB cable/connection and that USB debugging is authorized."
}

$state = ($matchLine -split "\s+")[1]
if ($state -ne "device") {
    throw "Device '$Serial' is present but in state '$state' (expected 'device'). Accept the USB-debugging authorization prompt on the phone and retry."
}
Write-Host "Device '$Serial' detected and authorized."

# --- 4. Install the APK and start GravitonVpnService ------------------------
Write-Host "=== Installing APK ==="
& $AdbPath -s $Serial install -r -d $apk.FullName
if ($LASTEXITCODE -ne 0) {
    throw "adb install failed for $($apk.FullName)."
}

Write-Host "=== Starting $VpnServiceClass ==="
Write-Warning "VpnService still requires user consent through VpnService.prepare(context) on first run."
& $AdbPath -s $Serial shell am start-foreground-service -n "$PackageName/$VpnServiceClass" --es gateway_url $GatewayUrl
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Service did not start directly; launch the app manually and approve the VPN consent dialog."
}

Write-Host "=== Done ==="
Write-Host "Gateway: $GatewayUrl"
