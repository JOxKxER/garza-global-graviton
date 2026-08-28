Rationale for container/seccomp-hardened.json
================================================

This profile uses defaultAction "SCMP_ACT_ALLOW" plus an explicit deny-list
(SCMP_ACT_ERRNO) for every network-related syscall. That is a deliberate,
conservative choice over hand-authoring a full default-deny allowlist:

- A full default-deny (SCMP_ACT_ERRNO) profile with a hand-built allowlist is
  the stronger control in principle, but a wrong or incomplete allowlist will
  either silently under-restrict (false sense of security) or break the
  Python runtime outright (crashes before the job even starts). Docker's own
  default.json allowlist runs to several hundred entries and is only trusted
  because it has been fuzzed and validated against real container workloads
  over years.
- This repo has no way to build/run the container locally to validate a
  hand-written allowlist (no Docker daemon in this environment), so shipping
  an unvalidated default-deny profile would be worse than not shipping one.

What this profile *does* guarantee: even if `--network none` were somehow
misconfigured or bypassed, every syscall needed to create a socket, bind,
connect, or send/receive data over one is hard-denied at the kernel level for
this container, independent of the container's network namespace state.

Before production use:
1. Keep `--network none` as the PRIMARY control (this profile is defense in
   depth, not a replacement for it).
2. Once the real job workload is finalized, generate a proper default-deny
   allowlist from an audited run, e.g. with `oci-seccomp-bpf-hook` or by
   tracing a full test run with `strace -f -c` / `perf trace` and folding the
   observed syscalls into a `defaultAction: SCMP_ACT_ERRNO` profile.
3. Re-run the deny-list version in parallel with the new allowlist during a
   canary period and diff any surprises before switching over.
