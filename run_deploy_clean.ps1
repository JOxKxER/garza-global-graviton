<#
    Sets up the local JDK/Gradle environment, builds the debug APK, verifies the
    Galaxy S20+ (R5CN202TSKN), installs the APK, and starts GravitonVpnService.
#>

$JdkHome = "V:\03_Source_Code\.jdk-local\jdk-17.0.20.1+1"
$ProjectRoot = "V:\03_Source_Code\android"
$ApkPath = "V:\03_Source_Code\android\app\build\outputs\apk\debug\app-debug.apk"
$Adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$Serial = "R5CN202TSKN"
$PackageName = "com.garza.globalgraviton"
$VpnServiceClass = "com.garza.globalgraviton.network.GravitonVpnService"
$GatewayUrl = "http://10.238.126.142:5000/api/v1/sensory/telemetry"

# --- 1. JDK environment ---
if (-not $env:JAVA_HOME -or $env:JAVA_HOME -ne $JdkHome) {
    $env:JAVA_HOME = $JdkHome
    $env:Path = "${env:JAVA_HOME}\bin;${env:Path}"
}
& "$env:JAVA_HOME\bin\java.exe" -version

# --- 2. Navigate to the project root ---
Set-Location -Path $ProjectRoot

# --- 3. Build the debug APK ---
& .\gradlew.bat assembleDebug
if ($LASTEXITCODE -ne 0) {
    throw "Gradle build failed with exit code $LASTEXITCODE."
}

# --- 4. Verify device, install, and start the VPN service ---
& $Adb kill-server
& $Adb start-server

$matchLine = $null
$maxAttempts = 3
$retryDelaySeconds = 2

for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $deviceLines = & $Adb devices
    Write-Host ($deviceLines -join "`n")

    $matchLine = $deviceLines | Where-Object { $_ -match "^$([regex]::Escape($Serial))\s+(\w+)" }
    if ($matchLine) {
        break
    }

    if ($attempt -lt $maxAttempts) {
        Write-Host "Device '$Serial' not seen yet (attempt $attempt/$maxAttempts); retrying in $retryDelaySeconds s..."
        Start-Sleep -Seconds $retryDelaySeconds
    }
}

if (-not $matchLine) {
    Write-Warning "Device '$Serial' was not found by adb after $maxAttempts attempts."
    Write-Host @"

Troubleshooting steps:
  1. Check the USB cable and port; try a different cable/port (prefer a rear/motherboard USB port over a front-panel hub).
  2. On the phone: Settings > Developer options > USB debugging must be ON, and USB debugging (Security settings) reset if previously revoked.
  3. Unlock the phone screen and accept the "Allow USB debugging?" RSA key prompt if it appears.
  4. Set the USB connection mode notification to "File Transfer/Android Auto" (MTP) rather than "Charging only".
  5. On Windows, check Device Manager for the phone under "Portable Devices" or "Other devices". If it shows a warning icon,
     reinstall the Samsung USB driver (or the Google USB driver via Android SDK Manager > SDK Tools).
  6. Run '$Adb kill-server' followed by '$Adb start-server' again after fixing the above, then re-run this script.
"@
    throw "Device '$Serial' was not found by adb. Check the USB cable/connection and authorization."
}

$state = ($matchLine -split "\s+")[1]
if ($state -ne "device") {
    throw "Device '$Serial' is present but in state '$state'. Accept the USB debugging prompt on the phone."
}
Write-Host "Device '$Serial' detected and authorized."

if (-not (Test-Path $ApkPath)) {
    throw "APK not found at $ApkPath. Run the build step first."
}

Write-Host "Installing $ApkPath..."
& $Adb -s $Serial install -r -d $ApkPath
if ($LASTEXITCODE -ne 0) {
    throw "adb install failed."
}

# GravitonVpnService is exported=false and requires BIND_VPN_SERVICE, so it can only
# be started by this app's own process. Launch MainActivity (exported=true) instead;
# it forwards gateway_url to the service internally after VPN consent is granted.
Write-Host "Launching MainActivity to start $VpnServiceClass..."
& $Adb -s $Serial shell am start -n "$PackageName/.MainActivity" --es "gateway_url" "$GatewayUrl"
Write-Warning "If this is the first run, accept the VPN consent dialog on the device to let the tunnel start."

Write-Host "Done. Gateway: $GatewayUrl"
