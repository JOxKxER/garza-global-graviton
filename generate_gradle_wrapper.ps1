[CmdletBinding()]
param(
    [Parameter()]
    [string]$ProjectRoot = "V:\03_Source_Code\android",

    [Parameter()]
    [string]$GradleVersion = "8.10.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $ProjectRoot -PathType Container)) {
    throw "Android project root not found: $ProjectRoot"
}

$gradlewBat = Join-Path $ProjectRoot "gradlew.bat"
if (Test-Path $gradlewBat) {
    Write-Host "Gradle wrapper already present at $gradlewBat; skipping generation."
    exit 0
}

if (Get-Command gradle -ErrorAction SilentlyContinue) {
    Write-Host "=== System Gradle found; generating wrapper via 'gradle wrapper' ==="
    Push-Location $ProjectRoot
    try {
        & gradle wrapper --gradle-version $GradleVersion
        if ($LASTEXITCODE -ne 0) { throw "'gradle wrapper' failed with exit code $LASTEXITCODE." }
    } finally {
        Pop-Location
    }
} else {
    Write-Warning "System 'gradle' command not found; downloading wrapper files directly."

    $tag = "v$GradleVersion"
    $base = "https://raw.githubusercontent.com/gradle/gradle/$tag"
    $wrapperDir = Join-Path $ProjectRoot "gradle\wrapper"
    New-Item -ItemType Directory -Force -Path $wrapperDir | Out-Null

    $files = @{
        "gradlew"                                    = (Join-Path $ProjectRoot "gradlew")
        "gradlew.bat"                                = (Join-Path $ProjectRoot "gradlew.bat")
        "gradle/wrapper/gradle-wrapper.properties"   = (Join-Path $wrapperDir "gradle-wrapper.properties")
        "gradle/wrapper/gradle-wrapper.jar"          = (Join-Path $wrapperDir "gradle-wrapper.jar")
    }

    foreach ($entry in $files.GetEnumerator()) {
        $url = "$base/$($entry.Key)"
        Write-Host "Downloading $url"
        Invoke-WebRequest -Uri $url -OutFile $entry.Value -UseBasicParsing
    }

    Write-Host "Wrapper files written under $ProjectRoot."
}

if (-not (Test-Path $gradlewBat)) {
    throw "Wrapper generation completed but $gradlewBat is still missing."
}
Write-Host "Gradle wrapper ready: $gradlewBat"
