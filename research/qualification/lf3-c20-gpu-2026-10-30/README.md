# LF3-K8-C20 fixed GPU confirmation and energy assessment

30 October 2026 UTC. **Experiment-tagged research; no candidate freeze,
activation or release.** This report follows the
[four-way conformance checkpoint](../lf3-c20-2026-10-30/README.md),
[security review](../lf3-c20-security-2026-10-30/README.md) and
[CPU economics](../lf3-c20-economics-2026-10-30/README.md).
Measured observations and inferred projections are labeled separately.

## Requested workstream disposition

| Workstream | Completed evidence and remaining qualification |
|---|---|
| 1. Open gaps | Rate-boundary checks passed. Fixed cold-start/warm confirmation is paced. Windows stall/crash cause and sustained unpaced qualification remain OPEN. |
| 2. Fused fold | Exact packed/fused paths implemented for both profiles and compared. Unperturbed pure-GEMM wall time remains unisolated; the separate cycle observer is explicitly instrumented. |
| 3. Energy | Continuous board measurements, medians, MAD and inferred intervals are retained. Sensor-method disagreement and wall-socket/physical-device energy remain OPEN. |
| 4. Conformance | 560 measured canonical vectors agree four ways; 1,048,576 measured full-fold GPU/C random cases, zero skips/mismatches. Boundary and deterministic fuzz coverage are linked above. |
| 5. Security | Finite adversarial, parent-screening and approximation tests completed. General grinding/sparse economics and mapped ASIC/photonic energy remain OPEN. |
| 6. Verification economics | Shared-EPYC CPU and upload measurements, dependent-parent projections and public photonic references are published. Dedicated modest/low-power hardware and C20 hostile-admission qualification remain OPEN. |
| 7. Conditional package | WITHHELD: no new domain tags, normative v0.5.0 candidate, kernel publication, reference-miner integration or activation. The team receives a REVISE recommendation. |

## What was fixed before confirmation

The five configured implementations are LF2 int32 cuBLAS, packed LF2, packed
C20, fused C20 and fused LF2. Their vector mappings and GEMM configurations
were selected before the confirmation samples. All use configured batches of
8192, the same deterministic 184-byte header, zero parent and initial nonce.
Every timed graph advances to fresh nonce batches. No winner is selected and
retuned from these samples. The cuBLAS AUTOTUNE policy is fixed; its internal
algorithm choice is the pinned vendor library's choice rather than a manually
selected algorithm identifier. CUTLASS configurations are fixed directly.

The measured remote platform is an RTX 5090, driver 595.91.07, CUDA 13.0 in a
pinned RunPod image. The reported power limit remains **575 W measured**.
Neither a power limit nor a clock setting was changed. This does not establish
behavior on another board, driver, cooling system or operating system.
[platform-and-plan.json](platform-and-plan.json) records the observed image
digest, dependency revisions and configured header/parent/nonce recipe.

The requested confirmation uses **600 configured GPU-event seconds for each
cold-start and warm condition per variant**. After every configured 64-replay
event window, the controller sleeps for that window's measured event duration.
This is nominal 50% event duty, with the same pacing rule for every variant.
The run records complete event windows, approximately 20-event-second blocks,
continuous 10 Hz configured NVML sampling and the actual achieved durations.
Temperature and sampling-heartbeat guards remain at configured 80 C and two
seconds. The fixed ordering and single-host run limit causal comparisons;
statistical intervals do not establish between-day or between-board stability.

A cold-start series records a bounded cooldown attempt: qualification requires 15 configured
consecutive seconds at no more than 42 C and 75 W instantaneous power, with
a bounded wait. It then warms naturally. The warm series continues in the
same context and paced thermal cycle. Neither label means ten minutes of
continuously cold silicon or uninterrupted full-power production mining.
The raw cooldown qualification flags remain part of the evidence.

## Correctness during measurement

Before and after each measured block, the complete 8192-case fold is checked
against an exact cuBLAS control, and one full h/F/D case is checked against C.
Those checks supplement the million-case replay and canonical vectors; the
timed evaluations are not individually replayed in C. The final
GPU stage computes the digest and strict little-endian target comparison.
The all-FF test target is a workload fixture, not a network difficulty choice.

Bank derivation, upload and validation occur outside the measured energy
blocks. Inside each block, the gross energy includes inter-window idle.
This denominator is complete attempts by a conformance-tested implementation,
not only winning nonces, matrix products or approximate attempts.

## Energy and uncertainty

[measurement-tables.md](measurement-tables.md) reports measured medians and
MAD, with inferred 95% confidence intervals, for every variant and condition.
[energy-confirmation-summary.json](energy-confirmation-summary.json) retains
every block, counts, durations, stage subsamples, temperature, SM/memory clocks,
power limit and sampling gaps.

The prespecified primary measurement integrates continuously sampled NVML
instantaneous power with trapezoids, interpolating block endpoints. The
continuously sampled cumulative energy counter and the one-second-average
power integral are both reported as cross-checks. Their disagreement is
retained. The cause is not established; no favorable sensor method is selected.
The reported statistical intervals **do not include that systematic metrology
uncertainty** or establish absolute energy accuracy on this board.

NVIDIA documents power usage and the available instantaneous/averaged fields,
and exposes a cumulative energy counter. Its documentation does not establish
that these measurements have identical component coverage or a calibrated
absolute error on this particular RTX 5090. Do not import an accuracy figure
for a different GPU generation. [NVIDIA NVML device queries](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)

Intervals use a configured 4,000 circular moving-block bootstrap resamples,
with three neighboring blocks per resampled span. They quantify conditional
within-run sampling variation. Event-window attempt rates and paced elapsed
rates are reported separately. These are gross GPU-board measurements;
CPU, wall-socket/PSU, bank setup and external optical hardware energy are not
measured here. No energy saving is inferred from a time share alone.

## Fused fold and matrix-stage interpretation

The packed implementation writes a configured 128 MiB intermediate per batch,
then launches a separate XOR fold. The fused kernel assigns the same row tile
across all eight matrices to a CTA and XORs the quantized nibble results in
registers before writing the final fold. It performs all required exact
products and quantization. Both LF2 and C20 use the same implementation change.
The fused kernel does not require that packed intermediate or separate fold
launch. The validation harness still allocates oracle/intermediate buffers;
this is not a measured reduction in its total VRAM allocation.

The production events measure **GEMM plus its epilogue**, including fused XOR
where applicable. Stage events sample the last graph in each 64-replay window;
they do not instrument every replay. The tables report that composite stage
separately from binding/expansion, separate fold, final SHAKE and total time.
The earlier expected approximately 92% composite share is a hypothesis, not
a substituted result.

A separate diagnostic used warp-zero cycle spans around the CUTLASS Mma loop,
with configured 30 alternating paired trials of one-pass and eight-pass CTAs.
The corrected diagnostic passed **491,520 measured full-fold checks**.
[mma-probe-records.json](mma-probe-records.json) and
[mma-probe-summary.json](mma-probe-summary.json) retain the observations.
The Mma span includes operand loads and synchronization. Attributing device
wall time by that cycle fraction is **inferred**, not an independently
isolated pure-GEMM wall-time measurement. Instrumentation changes register use
and scheduling, so its elapsed times do not replace the production timings.
An unperturbed pure arithmetic time or energy must remain unmeasured when it
cannot be isolated honestly.

The composite Amdahl ceiling is inferred as `1 / (1 - measured_time_share)`.
It assumes the entire composite stage becomes free without extra conversion,
transfer, loading, error correction or coordination. It is a conditional time
ceiling, not a predicted photonic speedup, energy ratio or security bound.

## Failed and incomplete attempts

All failures remain in [run-ledger.json](run-ledger.json) and retained raw
evidence. In particular:

- The owner's local GPU incident ended local research execution. It does not
  establish the cause of the earlier Windows CUDA initialization stall. No
  local GPU retry was made for this report. A fast Linux remote initialization
  does not rule out a Windows failure.
- The initial remote unpaced stock-power confirmation reached the configured
  80 C guard after approximately **110 measured seconds** and was invalidated.
  A 350 W request was outside the supported range; a supported 400 W request
  was denied by container permissions. Neither request changed the limit.
- The first paced confirmation aborted after **2097.652 measured seconds**:
  a **6.422-second measured NVML query/sample gap** exceeded the unchanged
  heartbeat guard. Maximum recorded temperature was **68 C measured**, with
  no recorded sampler exception or production hash mismatch. Its samples are
  not recycled into a passed confirmation. The subsequent fresh run assigns
  launch, controller and sampling to separate CPU cores. The cause of the
  driver/host delay remains OPEN; affinity does not prove it resolved.
- A separate instrumented one-pass control initially wrote pass-major data
  while its fold reader expected nonce-major layout. That run mismatched and
  all its timings were discarded. The original failed source and diagnosis
  were retained; after the layout correction, the full checks above passed.
  Production kernels and the million-case corpus were unchanged.

There is no claim that every attempted diagnostic or every deployment passed.
No demonstrated work-avoiding energy shortcut was worked around.

## Reproduction and qualification disposition

[energy-telemetry.tar.gz](energy-telemetry.tar.gz) contains the explicitly
selected raw successful and failed measurement logs, continuous telemetry,
cooldown records and receipts, without kernel sources or private operations
configuration. [analyze-energy.py](analyze-energy.py) is the portable CPU-only
analysis of those files. Extract into a fresh directory, install the measured
NumPy version in an isolated environment, then run on authorized hardware:

```sh
mkdir /tmp/lf3-energy-replay
tar -xzf energy-telemetry.tar.gz -C /tmp/lf3-energy-replay
python -m pip install numpy==2.5.4
python analyze-energy.py --evidence /tmp/lf3-energy-replay --output /tmp/lf3-energy-summary.json
```

This is data analysis, not a GPU benchmark. The owner's local research
restriction remains in force. The portable analyzer's replay comparison is
recorded in [publication-validation.json](publication-validation.json).
The C/CUDA kernel sources remain unpublished pending the conditional freeze;
raw telemetry reproduction does not independently reproduce those kernels.
The separate diagnostic summary can also be replayed without a GPU:

```sh
python analyze-mma-probe.py --records mma-probe-records.json --output /tmp/lf3-mma-summary.json
```

[analyze-mma-probe.py](analyze-mma-probe.py) replays the instrumented observations
and inferred attribution; it does not turn them into an unperturbed timing.

The [decision memo](decision-memo.md) and [nine direct answers](final-answers.md)
distinguish completed finite tests from provisional economics and remaining
qualification gaps. [measurement-SHA256SUMS](measurement-SHA256SUMS) is an
evidence transport manifest, not PhotonHash v0.5.0-candidate.1. Experiment tags
remain unchanged. Team decisions on header serialization/length, difficulty
and work score, genesis difficulty, timestamps, block time and activation
remain OPEN. No Laser consensus, chain, miner or release changes are made.
