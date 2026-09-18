#Requires -Version 5.1
<#
.SYNOPSIS
    build_ggg_daemon.ps1 - Compile ggg_daemon.py into a standalone, zero-telemetry
    background executable for Windows, macOS, or Linux.

.DESCRIPTION
    PyInstaller builds are per-OS: this script must run ON the target platform
    (or in its CI runner). It:
      1. Verifies the toolchain and entry point.
      2. Stages a CLEAN build context - only ggg_daemon.py + the spec - so no
         local databases, test payloads, logs, or credentials can leak in.
      3. Compiles via ggg_daemon.spec (console, stripped, optimize=2).
      4. Verifies the artifact launches and passes the daemon self-test.
      5. Packages dist/ into a versioned archive in dist/release/.

.PARAMETER Version
    Release version string stamped into the output archive name.

.PARAMETER SkipTest
    Skip the post-build launch verification (not recommended).

.EXAMPLE
    pwsh ./build_ggg_daemon.ps1 -Version 1.4.5
#>
[CmdletBinding()]
param(
    [string]$Version = "1.4.5",
    [switch]$SkipTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Resolve paths -----------------------------------------------------------
$RepoRoot   = Split-Path -Parent $MyInvocation.MyCommand.Path
$EntryPoint = Join-Path $RepoRoot 'ggg_daemon.py'
$SpecFile   = Join-Path $RepoRoot 'ggg_daemon.spec'
# Stage OUTSIDE the repo: the V: drive exhibits stale handle locking on fresh
# executables, and an in-repo stage would also risk the brand key or caches
# leaking into the tree. A per-run GUID dir under %TEMP% is disposable.
$StageDir   = Join-Path $env:TEMP ("ggg-daemon-build-" + [guid]::NewGuid().ToString('N'))
$DistDir    = Join-Path $StageDir 'dist'
$ReleaseDir = Join-Path $RepoRoot 'dist\release'

# --- Platform detection ------------------------------------------------------
$IsWin = $env:OS -eq 'Windows_NT'
$OSName = if ($IsWin) { 'windows' } elseif ($IsMacOS) { 'macos' } else { 'linux' }
$ExeName = if ($IsWin) { 'ggg-daemon.exe' } else { 'ggg-daemon' }

Write-Host "=== GGG Daemon Build ===" -ForegroundColor DarkYellow
Write-Host "Platform : $OSName"
Write-Host "Version  : $Version"

# --- 1. Pre-flight checks ----------------------------------------------------
if (-not (Test-Path $EntryPoint)) { throw "Entry point missing: $EntryPoint" }
if (-not (Test-Path $SpecFile))   { throw "Spec file missing:  $SpecFile" }

python --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "python not found on PATH." }

python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller missing - installing into user site..." -ForegroundColor Yellow
    python -m pip install --user pyinstaller
}

# --- 2. Stage a CLEAN build context ------------------------------------------
# Only the entry point + spec are copied. No .db, .dat, .log, .env, creds,
# zips, vaults, or caches can hitchhike into the binary.
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

Copy-Item $EntryPoint (Join-Path $StageDir 'ggg_daemon.py')
Copy-Item $SpecFile   (Join-Path $StageDir 'ggg_daemon.spec')

Write-Host "`nStaged clean context (outside repo, disposable):" -ForegroundColor DarkYellow
Get-ChildItem $StageDir | ForEach-Object { Write-Host "  + $($_.Name)" }

# --- 3. Compile ---------------------------------------------------------------
Push-Location $StageDir
try {
    Write-Host "`nCompiling with PyInstaller..." -ForegroundColor DarkYellow
    $pyArgs = @('-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', $DistDir, '--workpath', (Join-Path $StageDir 'build'), 'ggg_daemon.spec')
    # cmd /c isolates stderr so PowerShell strict-mode never treats PyInstaller's
    # INFO stream as a NativeCommandError; exit code still propagates.
    cmd /c "python $($pyArgs -join ' ') 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller exited with code $LASTEXITCODE" }
}
finally { Pop-Location }

$ExePath = Join-Path $DistDir $ExeName
if (-not (Test-Path $ExePath)) { throw "Expected artifact not produced: $ExePath" }

# --- 4. Verify the binary ------------------------------------------------------
$SizeMB = [math]::Round((Get-Item $ExePath).Length / 1MB, 2)
Write-Host ("`nArtifact: {0} ({1} MB)" -f $ExePath, $SizeMB) -ForegroundColor DarkYellow

if (-not $SkipTest) {
    Write-Host "Running daemon self-test inside the compiled binary..." -ForegroundColor DarkYellow
    # Isolate the brand key the self-test forges so it never lands in the repo/stage tree.
    $TestVault = Join-Path $env:TEMP ("ggg-selftest-" + [guid]::NewGuid().ToString('N'))
    $env:GGG_VAULT_DIR = $TestVault
    try {
        $TestOut = & $ExePath 2>&1 | Out-String
    }
    finally {
        Remove-Item Env:GGG_VAULT_DIR -ErrorAction SilentlyContinue
        Remove-Item $TestVault -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($TestOut -notmatch 'SELF-TEST OK') {
        throw "Compiled daemon failed self-test:`n$TestOut"
    }
    Write-Host "Self-test PASSED (pi gate, non-zero-sum balancer, HMAC brand)." -ForegroundColor Green
}

# --- 5. Package the release ----------------------------------------------------
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
$ArchiveName = "ggg-daemon_v${Version}_${OSName}"
if ($IsWin) {
    $ArchivePath = Join-Path $ReleaseDir "$ArchiveName.zip"
}
else {
    $ArchivePath = Join-Path $ReleaseDir "$ArchiveName.tar.gz"
}

# The freshly self-tested exe can hold an OS handle for a while; reads are
# still permitted, so package a byte-copy instead of the locked original.
$PackageCopy = Join-Path $DistDir ("pkg_" + $ExeName)
Copy-Item $ExePath $PackageCopy -Force

$packaged = $false
foreach ($attempt in 1..5) {
    try {
        if ($IsWin) {
            Compress-Archive -Path $PackageCopy -DestinationPath $ArchivePath -Force -ErrorAction Stop
        }
        else {
            tar -czf $ArchivePath -C $DistDir $ExeName
        }
        $packaged = $true
        break
    }
    catch {
        Write-Host "Packaging attempt $attempt/5 waiting on exe handle release..." -ForegroundColor Yellow
        Start-Sleep -Milliseconds (500 * $attempt)
    }
}
if (-not $packaged) { throw "Could not package $ExePath - file lock persisted through 5 attempts." }

# Normalize the archive entry name back to ggg-daemon(.exe) inside the zip.
if ($IsWin) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::Open($ArchivePath, 'Update')
    try {
        $entry = $zip.Entries | Where-Object { $_.Name -eq ("pkg_" + $ExeName) }
        if ($entry) {
            $bytes = [byte[]]::new($entry.Length)
            $stream = $entry.Open(); $stream.Read($bytes, 0, $bytes.Length) | Out-Null; $stream.Close()
            $entry.Delete()
            $newEntry = $zip.CreateEntry($ExeName)
            $ns = $newEntry.Open(); $ns.Write($bytes, 0, $bytes.Length); $ns.Close()
        }
    }
    finally { $zip.Dispose() }
}

$Hash = (Get-FileHash $ArchivePath -Algorithm SHA256).Hash
$Hash | Out-File "$ArchivePath.sha256" -Encoding ascii

# --- 6. Clean up the disposable stage -----------------------------------------
Remove-Item $StageDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`n=== BUILD COMPLETE ===" -ForegroundColor Green
Write-Host "Archive : $ArchivePath"
Write-Host "SHA-256 : $Hash"
Write-Host "Ship it : upload the archive + .sha256 to GitHub Releases."
Write-Host "Note    : macOS/Linux binaries must be built on their own OS (or CI runner)."
