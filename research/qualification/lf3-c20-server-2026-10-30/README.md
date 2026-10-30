# C20 sustained server-GPU and CPU follow-up

**30 October 2026. REVISE; no candidate freeze, activation or release.** This
completed measurement workstream follows the
[verifier/telemetry repair](../lf3-c20-verifier-2026-10-30/README.md) and
[exact-arithmetic mapping](../lf3-c20-mapped-arithmetic-2026-10-30/README.md).
It retains LF3-K8-C20-experiment.1 and the existing LF2 construction. It changes
no Laser consensus, miner, chain, difficulty, timestamps, issuance or genesis.

The [nine direct answers](final-answers.md) give the recommendation and remaining
gaps. [Measurement tables](measurement-tables.md) retain medians, MAD, inferred
intervals and block-time projections; JSON summaries retain every block.
Observations are labeled measured, calculations/models are inferred, and test
sizes/limits are configured. A passed experimental run is not an activation vote.

## Hardware and fair comparison

The configured fallback was selected before performance samples, after the
requested secure-cloud RTX 5090 placement returned no capacity. This is a full
**RTX PRO 4500 Blackwell Server Edition**, with an unchanged **165 W measured
reported board limit**. No clock or power setters were used. It is a separate
hardware cohort. It cannot replace the specifically requested cooled RTX 5090
retry or be pooled with its earlier paced measurements.

Fixed order: LF2 int32, packed LF2, packed C20, fused C20, fused LF2. All use
the same configured all-zero parent bank, batch 8192, 184-byte deterministic
header and starting nonce `0x19f8d3a5620c7b40`. Header byte `i` is
`(17*i + 9) mod 256`. Full attempts advance nonces rather than reusing fixed
digests. These are benchmark fixtures, not live-chain or wallet data. This
single-bank performance cohort is not a parent-grinding energy study.

Each variant has at least **600 measured GPU-event seconds** in each of two
configured conditions. A fresh process starts after **15 configured consecutive
seconds** at or below **42 C** and **75 W**, then warms naturally through its
cold-start series. The warm series follows in the same context. The label
`cold_start` does not mean the GPU stays cold throughout its configured ten
minutes. Processes run sequentially; the later CPU scaling and isolated-stage
jobs do not overlap the primary GPU energy work. Configurations were not chosen
from these confirmation samples.

This is one fixed-order pass, without randomized crossover or multiple-host
replication. Within-run intervals do not cover run-order effects or a population
of machines. Temperature and clock records help describe this cohort, not remove
those limitations.

The primary run reuses the preserved unpaced research binary, with its measured
digest and prior build/checkpoint provenance. The later isolated-stage binary
is rebuilt with the pinned CUTLASS revision; only its host pacing is removed.
[Selected platform metadata](evidence/server-platform.json) distinguishes
configured template tags from measured compiler, driver and artifact identities.
An image digest was not independently measured for this pod; the old cohort's
digest is not substituted. Kernel bodies remain outside this pre-freeze export,
so full GPU-source reproduction is still pending their authorized publication.

## Correctness scope

The new GPU passes the existing **560 measured C20 canonical cases** through
packed and fused paths (**1120 measured kernel checks**). Its separate SHAKE
boundary check compares bindings and vectors in both profiles; it does not alone
compare full folds. Original four-way conformance and the million-case C/GPU
replay remain in the [established package](../lf3-c20-2026-10-30/README.md) and
were not repeated as new independent-implementation work.

At initialization and after every timing block, the harness compares a complete
batch of folds with the GPU int32 path and one complete h/fold/digest with C.
These checks are outside integrated energy windows. The denominator is complete
evaluations counted by a conformance-validated implementation; it is not a claim
that every timed attempt was individually C-replayed. CUDA still receives the
bank from C. The OpenSSL backend is byte-checked separately.

## Energy and reliability

Continuous NVML sampling runs at a configured nominal **10 Hz**. A permanent
failure latch rejects an overdue query/sample before refreshing its heartbeat;
the fixed sampling bound is **2 seconds** and thermal abort is **80 C**. Independent
analysis rechecks raw sensor validity, timestamps, full window coverage,
denominators, completion and cold/conformance receipts. Passed process status
alone cannot qualify a run. The same repaired guard rejects the historical
fused-LF2 telemetry gap; that old run stays invalid.

Board energy integrates instantaneous power over host timing blocks. Continuously
sampled energy-counter and average-power readings provide cross-checks. Boundary
interpolation, block medians/MAD and inferred circular moving-block bootstrap
intervals are reproducible. A separate standard-library trapezoid integrator
checks the primary point estimates. It is an independent calculation of the
same sensors, not a separately calibrated instrument. CPU, PSU, bank setup and
validation outside the blocks are excluded; within-block launch/idle gaps remain.

NVML's [field timestamp](https://docs.nvidia.com/deploy/nvml-api/api/structnvmlFieldValue__t.html)
is a CPU timestamp. Additional acceptance checks reject field metadata older
than the configured two-second bound or substantially in the future. This does
not prove physical ADC freshness or accuracy. NVIDIA documents
[average and instantaneous power APIs](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)
separately; a small difference between them does not calibrate either sensor.
The old paced-5090 discrepancy is not explained by agreement on a different
board and workload regime. Statistical intervals exclude systematic sensor
bias and uncertainty across hosts.

## Isolated matrix-stage experiment

After confirmation, all fixed variants receive an exploratory **30 configured
GPU-event seconds** with previously validated, fixed vectors and no host pacing.
The measured stage includes GEMM and its epilogue. Packed/int32 paths exclude
the separate fold; fused paths necessarily include XOR. It excludes binding,
expansion and final hashing. Full-batch fold checks and one C trace follow each
block. This is neither a second ten-minute confirmation nor complete-attempt
energy. The stage's gross board joules cannot be divided by full-pipeline joules
to assign physical arithmetic energy. Pure GEMM-only time remains OPEN.

## CPU scaling and parent transition

The separate shared-server CPU cohort selects distinct allowed physical cores
and checks observed OpenMP worker placement. The fixed order is portable, then
OpenSSL at configured one, two, four and eight workers. It retains every seed,
audit checksum and expanded coefficient, and includes allocation. Parent
dependencies remain serial; only streams inside the current bank parallelize.
The configured tests contain **31 serial parent-dependent cold samples** and
**64 cached samples** per variant. Full-bank/canonical and cross-variant fold
checks precede any performance interpretation.

This is not a dedicated modest or low-power physical computer. The earlier
small CPU-only allocation is a separate cohort, with two SMT threads on one
physical core; its figures are not blended into these results. Aggregate CPU
time and elapsed time are both retained. Header-sync days are inferred hash-only
projections; actual sync also includes network, storage, state, signatures and
fork work. Block interval stays a team decision.

The transfer microbenchmark measures **31 configured repeats** of the same
pageable expanded bank, eight copies totaling **128 MiB configured**. It excludes
context startup and is not GPU-native bank generation. Adding its median to a
CPU-bank median gives an inferred turnover estimate, not a directly measured
production miner handover or overlap strategy. Physical full-bank photonic
reload and complete-system noise/energy remain open.

## Reproduce the evidence

On an authorized analysis machine, unpack the raw samples and verify both
transport manifests before analysis:

```sh
sha256sum -c SHA256SUMS
tar -xzf energy-telemetry.tar.gz
sha256sum -c telemetry-SHA256SUMS
python3 analysis/test_telemetry_guard.py
python3 analysis/test_field_freshness.py
python3 analysis/analyze_server_energy.py
python3 analysis/crosscheck_energy_stdlib.py --complete
python3 analysis/analyze_secondaries.py
```

The numerical analyzers use NumPy; the recorded version is in platform metadata.
They read stored files and make no GPU calls. No analysis or test was run on the
owner's local machine. The earlier system-Python NumPy import failure is retained
as a failed pre-analysis attempt; the later remote environment is separate.
The first publication selection also failed because its sampler-copy path was
wrong. That failed log, receipt and a repair ledger are retained. Packaging was
repeated from the completed data using the actual checkpoint sampler; no timing
sample, hash computation or acceptance threshold was changed.

For an opt-in CPU-only reproduction from this public checkout, on a Linux
research machine with at least eight distinct allowed physical cores, GCC,
OpenMP, OpenSSL development headers and Python:

```sh
python3 src/reproduce_cpu_scale.py /absolute/new/results-directory --ack-research
```

It refuses an existing output directory and applies finite process limits.
Reproduction measurements are kept separate from the primary timing cohort.
Smaller CPU machines can use the one/two-worker
[verifier reproduction](../lf3-c20-verifier-2026-10-30/README.md); actual modest
and low-power physical qualification is still needed.

## Disposition

The historical invalid/aborted runs remain in their original packages; this
cohort does not retroactively qualify them. Current preflight, pilot, build,
failed dependency, telemetry, conformance and timing records are preserved.
SHA256SUMS is a publication transport manifest, not a candidate freeze manifest.

The [review scope](review-scope.md) identifies outside cryptographic, hardware
and integration work. Production C20 network admission and fairness are not
established by the standalone function-call laboratory. Windows crash diagnosis,
independent metrology, general grinding/precomputation/sparse economics and
mapped physical ASIC/photonic energy remain open. Final domain tags, candidate
vectors/spec, kernel publication and the conditional candidate freeze are
withheld. Header serialization, difficulty/work, initial difficulty, timestamps,
block time and activation remain OPEN team integration items.
