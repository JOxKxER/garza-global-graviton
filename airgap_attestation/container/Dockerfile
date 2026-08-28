# syntax=docker/dockerfile:1
#
# Hardened air-gapped execution harness image.
#
# Network isolation is layered, not single-point-of-failure:
#   1. Runtime flag `--network none` (see docker-compose.yml / runbook)
#      -- the container gets NO network namespace peer, not even a veth pair.
#   2. This image ships no shell utilities capable of raw sockets beyond the
#      Python interpreter itself, and no DNS/resolver config is baked in.
#   3. `--cap-drop=ALL` + `--read-only` + non-root user are enforced at run
#      time (documented in the deployment runbook) since Dockerfile alone
#      cannot force the invoking `docker run`/compose flags.

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements-runner.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements-runner.txt

# ---------------------------------------------------------------------------
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

# distroless "nonroot" images run as uid=65532 (user "nonroot") by default
# and contain no shell, no package manager, and no coreutils -- this alone
# eliminates most post-exploitation living-off-the-land techniques even if
# an attacker achieved code execution inside the job.
COPY --from=builder /deps /deps
ENV PYTHONPATH=/deps

COPY . /app/airgap_attestation/
WORKDIR /app

# The root filesystem is made read-only at `docker run` time (--read-only);
# only /job/output and /tmp are writable, and both are tmpfs-mounted so
# nothing persists past the container's lifetime.
ENV JOB_INPUT_DIR=/job/input \
    JOB_OUTPUT_DIR=/job/output \
    JOB_SECRETS_DIR=/job/secrets

USER nonroot
ENTRYPOINT ["python3", "/app/airgap_attestation/container/entrypoint.py"]
