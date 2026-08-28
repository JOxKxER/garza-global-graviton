<#
  Deployment runbook for the air-gapped execution harness container.
  Run each section manually and inspect output before proceeding to the
  next -- this is a runbook, not a "just execute the whole file" script.
  Requires Docker Desktop (Linux containers) on the host running this.
#>

param(
    [string]$ImageName = "airgap-runner:latest",
    [string]$JobDir = "V:\03_Source_Code\airgap_attestation\container\job_input",
    [string]$SecretsDir = "V:\03_Source_Code\airgap_attestation\container\job_secrets",
    [string]$OutputDir = "V:\03_Source_Code\airgap_attestation\container\job_output"
)

# --- Step 1: Build the hardened image -------------------------------------
Write-Host "=== Step 1: Build ==="
docker build -f "V:\03_Source_Code\airgap_attestation\container\Dockerfile" `
    -t $ImageName "V:\03_Source_Code\airgap_attestation"
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

# --- Step 2: Prepare read-only job input + secrets mounts ------------------
Write-Host "=== Step 2: Prepare mounts ==="
New-Item -ItemType Directory -Force -Path $JobDir, $SecretsDir, $OutputDir | Out-Null

# Platform signing keypair (generate once, keep the private key offline/HSM-backed in production)
python -c @"
from airgap_attestation import signing
priv, pub = signing.generate_keypair()
open(r'$SecretsDir\platform_private_key.hex', 'w').write(priv.hex())
open(r'$SecretsDir\platform_public_key.hex', 'w').write(pub.hex())
print('platform pubkey:', pub.hex())
"@

# job.json: commitment_id + nonce come from the nonce_service /v1/submissions
# response for this specific client submission -- never invent them locally
# in production.
@'
{
  "commitment_id": "REPLACE_WITH_REAL_COMMITMENT_ID",
  "nonce": "REPLACE_WITH_REAL_NONCE_HEX",
  "job_label": "acme-corp-sample-run",
  "job_cmd": ["python3", "-c", "print('job executed inside the sealed harness')"]
}
'@ | Out-File -Encoding utf8 "$JobDir\job.json"

# --- Step 3: Run the hardened, network-isolated container -----------------
Write-Host "=== Step 3: Run (hardened, --network none) ==="
docker run --rm `
    --network none `
    --read-only `
    --tmpfs /tmp:rw,noexec,nosuid,size=64m `
    --tmpfs /job/output:rw,nosuid,size=256m `
    --cap-drop=ALL `
    --security-opt no-new-privileges:true `
    --security-opt "seccomp=V:\03_Source_Code\airgap_attestation\container\seccomp-hardened.json" `
    --pids-limit=256 `
    --memory=2g --cpus=2 `
    -v "${JobDir}:/job/input:ro" `
    -v "${SecretsDir}:/job/secrets:ro" `
    -v "${OutputDir}:/job/output_extract" `
    $ImageName
# Note: /job/output is tmpfs (ephemeral); the line above additionally bind-mounts
# a host extraction directory so `docker cp`-style extraction isn't needed if the
# entrypoint is adjusted to also copy the bundle to /job/output_extract. As shipped,
# entrypoint.py writes only to /job/output (tmpfs); for a `--rm` container that means
# you must either (a) drop --rm and `docker cp` before removing, or (b) mount
# /job/output directly to a host path instead of tmpfs if you need host-side
# persistence without an extra cp step. Choose based on whether tmpfs-only output
# (safer: never touches host disk unencrypted) matters more than convenience.

# --- Step 4: Independently confirm zero network syscalls occurred ---------
Write-Host "=== Step 4: Independent syscall audit (recommended before trusting any run) ==="
Write-Host @"
Run once against a debug build with --security-opt seccomp=unconfined and:
  strace -f -c -e trace=network -o audit.trace <same job_cmd>
Confirm audit.trace shows zero calls to socket/connect/bind/sendto/etc.
This is the evidence that should feed record_syscall_category_counts() in
a real (non-reference) monitor integration.
"@

# --- Step 5: Ingest the resulting bundle into the submission service ------
Write-Host "=== Step 5: Ingest bundle (adjust host/port/key for your deployment) ==="
Write-Host @"
`$bundle = Get-Content "$OutputDir\AttestationBundle.json" -Raw | ConvertFrom-Json
Invoke-RestMethod -Method Post \`
  -Uri "https://internal-ingest.example.internal/v1/internal/submissions/`$(`$bundle... )/bundle" \`
  -Headers @{ "X-Internal-Ingest-Key" = `$env:AIRGAP_INTERNAL_INGEST_KEY } \`
  -Body (@{ bundle = `$bundle } | ConvertTo-Json -Depth 20) -ContentType "application/json"
"@

# --- Step 6: Client-side verification (buyer's machine, fully offline) ----
Write-Host "=== Step 6: Client verification (run on the BUYER's machine) ==="
Write-Host @"
python airgap_attestation\cli\verify_cli.py ``
  --bundle AttestationBundle.json ``
  --platform-pubkey <vendor's published pubkey hex> ``
  --nonce <the nonce this client originally received from /v1/submissions> ``
  --ak-pubkey <vendor's published AK pubkey/cert hex>
"@

Write-Host "=== Runbook complete ==="
