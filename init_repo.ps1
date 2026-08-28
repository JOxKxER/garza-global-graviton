<#
  Repository release-packaging script.

  NOTE: This repo already has git history and a remote (origin ->
  github.com/JOxKxER/garza-global-graviton). This script does NOT wipe or
  reinitialize that history. It:
    1. Runs `git init` only if no .git directory exists yet (safe/no-op here).
    2. Stages the current working tree (respecting the just-hardened
       .gitignore -- large local toolchains, build output, and machine-
       specific files are excluded; see .gitignore for the full list).
    3. Creates ONE commit for this milestone (not a repo "first commit").
    4. Creates an annotated tag `v1.0.0-release` (skips if it already exists).

  It never pushes to the remote automatically -- that step is printed for you
  to run explicitly once you've reviewed `git status` / `git show --stat`.
#>

param(
    [string]$CommitMessage = "Release v1.0.0: air-gapped attestation platform",
    [string]$Tag = "v1.0.0-release",
    [switch]$Push
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE" }
}

# --- 1. Initialize git only if this truly is not a repo yet ---------------
if (-not (Test-Path ".git")) {
    Write-Host "=== No .git found; running 'git init' ==="
    Invoke-Git init
} else {
    Write-Host "=== Existing git repository detected; skipping 'git init' ==="
}

# --- 2. Show what would be staged, then stage it ---------------------------
Write-Host "`n=== Files that will be staged (dry run) ==="
& git add -A -n

Write-Host "`n=== Staging all tracked changes and new files ==="
Invoke-Git add -A

Write-Host "`n=== git status after staging ==="
& git status

# --- 3. Commit (only if there is something to commit) ----------------------
$diffCheck = & git diff --cached --quiet; $hasStagedChanges = ($LASTEXITCODE -ne 0)
if ($hasStagedChanges) {
    Write-Host "`n=== Creating commit ==="
    Invoke-Git commit -m $CommitMessage
} else {
    Write-Host "`n=== Nothing staged to commit (working tree already matches HEAD) ==="
}

# --- 4. Tag the release (idempotent) ---------------------------------------
$existingTag = & git tag -l $Tag
if ($existingTag) {
    Write-Host "`n=== Tag '$Tag' already exists; leaving it as-is ==="
} else {
    Write-Host "`n=== Creating annotated tag '$Tag' ==="
    Invoke-Git tag -a $Tag -m $CommitMessage
}

# --- 5. Push only if explicitly requested -----------------------------------
if ($Push) {
    Write-Host "`n=== Pushing branch and tag to origin (requested via -Push) ==="
    Invoke-Git push origin HEAD
    Invoke-Git push origin $Tag
} else {
    Write-Host "`n=== Not pushing automatically. Review the commit/tag above, then run: ==="
    Write-Host "    git push origin HEAD"
    Write-Host "    git push origin $Tag"
}

Write-Host "`n=== Done ==="
