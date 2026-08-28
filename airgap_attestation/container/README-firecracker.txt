Firecracker microVM notes for the air-gapped execution harness
================================================================

Why Firecracker instead of (or in addition to) the Docker container:

- `network-interfaces: []` means Firecracker never creates a virtio-net
  device for the guest at all. There is no NIC for the guest kernel to see,
  configure, or misuse -- this is a hardware/VMM-level guarantee, stronger
  than a container network namespace (which still has a loopback device and
  a kernel networking stack present, just with `--network none` disconnecting
  it from the outside).
- No vsock device is declared either, so there is no host<->guest control
  channel available to the job process beyond the two block devices
  (job_input, read-only; job_output, read-write). Data enters and leaves
  the microVM only via those disk images, moved by the host operator between
  runs -- there is no live channel while the VM is executing.
- The root filesystem drive is `is_read_only: true`; only job_output is
  writable, mirroring the container's `--read-only` + tmpfs-output pattern.

Boot flow:
  1. Host builds `rootfs-airgap-runner.ext4` from the same application code
     as the Docker image (this project's `container/entrypoint.py` +
     `airgap_attestation/` package), using `virt-make-fs` or a loopback mount.
  2. Host writes `job_input.ext4` containing job.json + the payload for this run.
  3. Host starts Firecracker, PUTs this config to the API socket:
       curl --unix-socket /tmp/firecracker.socket -X PUT \
         'http://localhost/machine-config' -d @firecracker_config.json
     (split across the standard /boot-source, /drives/{id}, /network-interfaces,
     /machine-config endpoints per the Firecracker API spec; a single
     config-file boot via `--config-file firecracker_config.json` is also
     supported by recent Firecracker versions.)
  4. Guest init runs entrypoint.py, seals the manifest, writes
     AttestationBundle.json onto the job_output drive, then the guest halts.
  5. Host mounts job_output.ext4 read-only and extracts the bundle for
     upload to the ingest API (nonce_service.py's internal endpoint).

This file intentionally has no vendor-specific kernel/rootfs build steps --
those depend on your base distro choice and are out of scope for this
protocol design.
