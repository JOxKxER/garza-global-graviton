[CmdletBinding()]
param(
    [Parameter()]
    [string]$ProjectRoot = (Join-Path $PSScriptRoot "android-app"),

    [Parameter()]
    [string]$PackageName = "com.garza.globalgraviton",

    [Parameter()]
    [string]$MainActivity = "",

    [Parameter()]
    [string]$VpnServiceClass = "com.garza.globalgraviton.network.GravitonVpnService",

    [Parameter()]
    [string]$ApkPath = "",

    [Parameter()]
    [string]$Serial = "",

    [Parameter()]
    [string]$GatewayUrl = "http://10.238.126.142:5000/api/v1/sensory/telemetry",

    [Parameter()]
    [switch]$SkipVpnService
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Adb {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & adb @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "ADB command failed: adb $($Arguments -join ' ')"
    }
}

function Get-AdbOutput {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = & adb @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "ADB command failed: adb $($Arguments -join ' ')"
    }
    return @($output)
}

function Resolve-Apk {
    param([Parameter(Mandatory = $true)][string]$Root)
    if ($ApkPath) {
        $candidate = (Resolve-Path $ApkPath -ErrorAction Stop).Path
        if (-not $candidate.EndsWith(".apk", [StringComparison]::OrdinalIgnoreCase)) {
            throw "-ApkPath must point to an APK file."
        }
        return $candidate
    }

    if (-not (Test-Path $Root -PathType Container)) {
        throw "Android project root was not found: $Root. Supply -ProjectRoot or -ApkPath."
    }

    $wrapper = Join-Path $Root "gradlew.bat"
    if (Test-Path $wrapper) {
        Write-Host "Building debug APK with Gradle wrapper..."
        Push-Location $Root
        try { & $wrapper "assembleDebug" } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw "Gradle assembleDebug failed." }
    } elseif (Get-Command gradle -ErrorAction SilentlyContinue) {
        Write-Host "Building debug APK with system Gradle..."
        Push-Location $Root
        try { & gradle "assembleDebug" } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw "Gradle assembleDebug failed." }
    } else {
        Write-Warning "Gradle is unavailable; searching for a prebuilt debug APK."
    }

    $apk = Get-ChildItem -Path $Root -Filter "*.apk" -File -Recurse |
        Where-Object { $_.FullName -match "[\\/]build[\\/]outputs[\\/]apk[\\/]" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $apk) {
        throw "No APK found. Supply -ApkPath or install Gradle/Android tooling."
    }
    return $apk.FullName
}

Write-Host "=== Garza Global Graviton Android Deployment ==="
Write-Host "Gateway: $GatewayUrl"

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    throw "ADB was not found on PATH. Install Android platform-tools first."
}

$devices = @(Get-AdbOutput @("devices") |
    Where-Object { $_ -match "^(\S+)\s+device$" } |
    ForEach-Object { ($_ -split "\s+")[0] })

if ($Serial) {
    if ($devices -notcontains $Serial) {
        throw "Requested device '$Serial' is not connected and authorized."
    }
} elseif ($devices.Count -eq 1) {
    $Serial = $devices[0]
} elseif ($devices.Count -eq 0) {
    throw "No authorized Android device found. Enable USB debugging and accept the device prompt."
} else {
    throw "Multiple devices found. Re-run with -Serial <device-id>."
}

Write-Host "Using device: $Serial"
$apk = Resolve-Apk -Root $ProjectRoot
Write-Host "Installing APK: $apk"
Invoke-Adb @("-s", $Serial, "install", "-r", "-d", $apk)

Write-Host "Requesting applicable runtime permissions..."
$grantable = @(
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION"
)
foreach ($permission in $grantable) {
    & adb "-s" $Serial "shell" "pm" "grant" $PackageName $permission 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Granted $permission"
    } else {
        Write-Host "Skipped $permission (not declared, not runtime-grantable, or already handled)."
    }
}

if ($MainActivity) {
    Write-Host "Launching application activity..."
    Invoke-Adb @("-s", $Serial, "shell", "am", "start", "-n", "$PackageName/$MainActivity")
}

if (-not $SkipVpnService) {
    Write-Host "Starting VPN service component..."
    Write-Warning "VpnService still requires user consent through VpnService.prepare(context)."
    & adb "-s" $Serial "shell" "am" "start-foreground-service" "-n" "$PackageName/$VpnServiceClass" "--es" "gateway_url" $GatewayUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The service did not start directly; launch the app and approve the VPN consent dialog."
    }
}

Write-Host "Verifying installed package..."
$installed = @(Get-AdbOutput @("-s", $Serial, "shell", "pm", "list", "packages", $PackageName))
if (-not ($installed -match "package:$([regex]::Escape($PackageName))")) {
    throw "Package verification failed for $PackageName."
}

Write-Host "Deployment complete."
Write-Host "The app must obtain VPN consent before TUN capture begins."
Write-Host "Telemetry target: $GatewayUrl"
