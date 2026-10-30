# C20 verifier and telemetry follow-up

30 October 2026 UTC. **Experimental research, not Laser consensus. REVISE;
candidate freeze remains withheld.** Construction, domain tags, vectors, active
network and miner selection are unchanged. GPU kernel sources are not included.

This work follows the [CPU economics](../lf3-c20-economics-2026-10-30/README.md)
and [invalidated fused-LF2 telemetry](../lf3-c20-gpu-2026-10-30/README.md).
Builds, tests, statistics and benchmarks ran on a separate RunPod CPU-only
machine. The owner's Windows computer performed control and transport only.

## Exact optimized bank generation

`src/bank_openssl.c` uses OpenSSL SHAKE256 instead of portable C Keccak and
optionally derives independent passes on two workers. It retains every seed,
raw-stream audit checksum and signed coefficient. There is no approximate
arithmetic, changed domain tag or omitted bank work.

Measured conformance: **560/560 canonical h/fold/digest cases**, **8 complete
bank comparisons** (four canonical parents, one/two workers), and **62** further
full-fold/digest comparisons along parent-dependent timing chains. Each bank
comparison covers all **134,217,728 coefficient bytes**, eight seeds and eight
checksums. No mismatch was observed. These checks do not add a fourth independent
bank generator to the earlier C/Python/Rust implementations: this is an optimized
C/OpenSSL implementation of the same construction.

The CPU-only allocation exposes two SMT threads on one physical AMD EPYC 9655
core. It is a useful small allocation, not dedicated modest-machine or low-power
hardware qualification. OpenSSL **3.0.13** and GCC **13.3.0** versions are measured
inventory, not recommendations to install those versions elsewhere.

Measured bank medians: portable **0.635505 s**, single-worker OpenSSL **0.283790 s**,
two-worker OpenSSL **0.258326 s**. The two workers share a core; do not extrapolate
to eight physical cores. All medians/MAD, inferred bootstrap intervals, CPU time,
cached/cold verification and block-time projections are in
[measurement-tables.md](measurement-tables.md) and the raw evidence. The timings
include audit checksums and allocation. They are not just SHAKE stream throughput.

## Standalone admission laboratory

`src/admission_lab.c` is a serialized, single-owner example contract. Trusted
harness operations admit at most **16 configured parents**, assign at most
**16 configured peer slots**, set each parent's target, and advance a monotonic
server clock. Untrusted verification requests cannot invoke those operations.
Parents are checked before bank work. There are **2 configured bank slots** with
LRU replacement, bounding coefficient storage to **256 MiB configured** plus
temporary derivation/workspace/library memory. Measured unsanitized peak RSS was
**290,776 KiB**; this is an observation, not a hard RSS ceiling.

Illustrative limits are **4 hashes globally**, **2 per peer**, and **1 cold-bank
derivation** per fixed server-controlled second. Adjacent windows can burst;
these are not sliding-window limits. Rejected malformed, unknown or exhausted
requests do not allocate a bank, hash or mutate cache occupancy. Quotas are
reserved before expensive work. A single owner controls admission and verification;
the `busy` field is not a thread-safe concurrent locking primitive.

Measured hostile batches: **1,048,576 unknown-parent**, **1,048,576 oversized-input**
and **1,048,576 exhausted-quota requests**, with **zero bank derivations and zero
hashes** in each batch. Positive checks cover cached reuse, independent peer/global
limits, cold limits, clock rollback, duplicate admissions, eviction and reentry.
Ten admitted-parent churn steps demonstrate that known-parent attackers can
still force the allowed cold work. The measured expensive path is not zero:
first cold verification took **0.272822 s**, cached **0.015431 s** in this lab run.
AddressSanitizer and UndefinedBehaviorSanitizer completed the same suite without
reported errors; sanitized timings are retained but excluded from performance
claims.

These are function-call measurements. No packet parser, network transport,
handshake, peer identity/Sybil resistance or live Laser node was tested. Fair
scheduling and starvation under exhausted quotas remain open. Choosing admissible
parents/targets requires the team's chain rules; this lab does not establish them.
Unknown-parent/backpressure responses must not be mistaken for consensus-invalid
block decisions. Actual C20 network integration and its hostile tests remain OPEN.

## Fail-closed measurement acceptance

`src/telemetry_guard.py` latches a failure before an overdue sample can refresh
the heartbeat. Sampling and supervisory checks share that permanent latch.
Independent retrospective acceptance rejects excessive gaps, invalid sensor
fields, non-monotonic time, thermal violations, missing coverage, overlapping or
incomplete event windows and unqualified cold/process/conformance receipts.
A successful process exit cannot override these conditions.

Measured validation: **10 deterministic test methods**, including injected
subcases, passed. The actual historical fused-LF2 raw telemetry is rejected for
its **9.370326 s measured maximum gap**, despite its old passed process receipt.
Its cold/warm durations are preserved in `evidence/historical-telemetry-replay.json`.
The regression assumes the other requirements satisfied to isolate the known
gap; it cannot certify the historical run. It does not diagnose why the driver
or host delayed sampling, and does not calibrate NVML power sensors.

## Reproduction and limits

On a separate Linux research machine with GCC, OpenMP, OpenSSL development
headers and Python 3, explicitly opt in:

```sh
LF3_RESEARCH_ACK=1 bash research/qualification/lf3-c20-verifier-2026-10-30/run.sh /absolute/new/results-directory
```

The script refuses an existing results directory, retains raw outputs and
applies process timeouts. It does not run through normal repository tests.
Published portable C20/stream source under `reference/` is the explicit research
oracle needed to reproduce the lab, not an activated production path. Existing
MIT notices remain applicable; OpenSSL is an external dependency.

A clean public checkout plus this exact selection completed the opt-in
reproduction, including vectors, hostile admission and both sanitizers. Original
measurements remain the primary timing cohort; reproduction results are retained
separately and are not used to choose faster configurations. SHA256SUMS identifies
the selected files, not a candidate freeze manifest.

Remaining qualification includes sustained GPU energy/metrology, isolated
matrix-stage costs, an RTX 5090 retry, physical modest/low-power CPU evidence,
production admission integration, Windows stall/crash diagnosis, general
grinding/precomputation/sparse-work economics, mapped ASIC/photonic energy and
outside human review. Faster bank generation and the admission lab do not settle
these. No candidate version, new tags, release, activation or block-time decision
is made here.
