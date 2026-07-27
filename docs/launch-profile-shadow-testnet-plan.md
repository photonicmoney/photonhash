# LF2-K8 non-consensus shadow-testnet plan

Status: **required before any consensus proposal**

Release identity: **PhotonHash v0.4.0-shadow.1**

Canonical transport and work IDs are defined by
[the shadownet protocol](shadownet-protocol.md). The live pass/fail state is
maintained in [the readiness ledger](shadownet-readiness.md).

LF2-K8 must first run beside Laser, never inside its acceptance path. The
existing Laser proof of work remains authoritative. A sidecar receives each
public testnet parent and block template, derives the frozen LF2-K8 matrix
bank, distributes shadow work, and records candidate solutions. No LF2 result
can accept, reject, delay, or reorganize a Laser block during this phase.

## Evidence to collect

For every parent transition record:

- time from parent receipt to a usable CPU and GPU matrix bank;
- matrix derivation, packing, transfer, and cache-residency time separately;
- the miner's first LF2 attempt and first shadow solution;
- work lost to a competing parent, reorg, or late template;
- cached verification latency and verifier queue depth;
- malformed-work and stale-parent rejection;
- CPU, GPU, driver, compiler, memory, and power-boundary metadata; and
- exact agreement between the C, Rust, and CUDA implementations.

The run must include at least two commodity GPU families, one non-NVIDIA
implementation, ordinary verifier CPUs, forced short reorgs, network delay,
rapid template replacement, malformed messages, and verifier-flood tests.
Difficulty must be low enough to observe many shadow solutions without
changing the real testnet difficulty.

## Admission criteria

The shadow run is evidence-qualified only if:

1. no cross-implementation digest disagreement occurs;
2. no stale matrix bank is accepted for a new parent;
3. matrix setup does not create an unexplained or hardware-exclusive outage;
4. cached verification remains within the charter under sustained load;
5. no tested omission or approximation strategy identifies valid work more
   efficiently than exact evaluation;
6. commodity mining remains practical on the tested devices; and
7. all raw logs and scripts are published with a reproducible summary.

## Local harness result

tools/ph_lf2_shadow_soak.c is only a local transition harness. On 2026-07-26,
a strict GCC build exercised 12 deterministic parent banks with two cached
attempts per bank:

| Measurement | Result |
|---|---:|
| Mean cold setup | 480.417 ms |
| Maximum cold setup | 493.000 ms |
| Mean cached attempt | 2.625 ms |
| Stale-parent digest collisions | 0 |

The harness also reproduced the same transcript in a second run. This checks
basic lifecycle mechanics; it is not public-testnet evidence, a networking
test, or a consensus integration.

No Laser source or consensus rule is changed by this plan. The adapter must be
read-only, the collector must run outside block acceptance, and every
deployment review must demonstrate that a shadow failure cannot delay or
alter Laser validation.
