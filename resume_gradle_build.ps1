[CmdletBinding()]
param(
    [Parameter()]
    [string]$GradleVersion = "8.9",

    [Parameter()]
    [string]$ZipPath = "V:\03_Source_Code\gradle-8.9-bin.zip",

    [Parameter()]
    [string]$ExtractRoot = "V:\03_Source_Code\.gradle-local",

    [Parameter()]
    [string]$ProjectRoot = "V:\03_Source_Code\android",

    [Parameter()]
    [string]$Serial = "R5CN202TSKN",

    [Parameter()]
    [string]$GatewayUrl = "http://10.238.126.142:5000/api/v1/sensory/telemetry"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $env:JAVA_HOME -or -not (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
    $jbr = "C:\Program Files\Android\Android Studio1\jbr"
    if (Test-Path (Join-Path $jbr "bin\java.exe")) {
        $env:JAVA_HOME = $jbr
        $env:Path = "$jbr\bin;$env:Path"
        Write-Host "JAVA_HOME set to $jbr"
    } else {
        throw "No valid JAVA_HOME found. Set it manually before running this script."
    }
}

# --- 1. Verify connectivity and fetch the zip directly (bypasses the wrapper's own stalling downloader) ---
$distUrl = "https://services.gradle.org/distributions/gradle-$GradleVersion-bin.zip"

$conn = Test-NetConnection -ComputerName "services.gradle.org" -Port 443 -WarningAction SilentlyContinue
if (-not $conn.TcpTestSucceeded) {
    throw "Cannot reach services.gradle.org:443. Check network/proxy/firewall settings."
}

if (-not (Test-Path $ZipPath) -or (Get-Item $ZipPath).Length -lt 50MB) {
    Write-Host "=== Downloading $distUrl ==="
    $ProgressPreference = "Continue"
    Invoke-WebRequest -Uri $distUrl -OutFile $ZipPath -UseBasicParsing
} else {
    Write-Host "Reusing existing archive: $ZipPath"
}

$zipInfo = Get-Item $ZipPath
Write-Host "Archive size: $([math]::Round($zipInfo.Length / 1MB, 1)) MB"

# --- 2. Extract locally and point the project's wrapper at it ---
$extractedHome = Join-Path $ExtractRoot "gradle-$GradleVersion"
if (-not (Test-Path (Join-Path $extractedHome "bin\gradle.bat"))) {
    Write-Host "=== Extracting to $ExtractRoot ==="
    New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractRoot -Force
} else {
    Write-Host "Already extracted: $extractedHome"
}

if (-not (Test-Path (Join-Path $extractedHome "bin\gradle.bat"))) {
    throw "Extraction did not produce $extractedHome\bin\gradle.bat"
}

$env:GRADLE_HOME = $extractedHome
$env:Path = "$extractedHome\bin;$env:Path"

# The wrapper's own downloader is what stalled; sidestep it by disabling gradlew.bat
# so build_deploy_gravitonvpn.ps1 falls back to the extracted 'gradle' now on PATH.
$wrapperBat = Join-Path $ProjectRoot "gradlew.bat"
$wrapperDisabled = "$wrapperBat.disabled"
if ((Test-Path $wrapperBat) -and -not (Test-Path $wrapperDisabled)) {
    Rename-Item -Path $wrapperBat -NewName (Split-Path $wrapperDisabled -Leaf)
    Write-Host "Disabled $wrapperBat; will build with local Gradle $GradleVersion from $extractedHome"
}

# --- 3. Resume the build/deploy pipeline ---
Write-Host "=== Resuming build_deploy_gravitonvpn.ps1 ==="
& "V:\03_Source_Code\build_deploy_gravitonvpn.ps1" -GatewayUrl $GatewayUrl -Serial $Serial
