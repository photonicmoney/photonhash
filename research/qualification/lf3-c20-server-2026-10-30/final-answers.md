# Nine direct answers: remote C20 follow-up

30 October 2026 UTC. **REVISE. No candidate freeze, activation or release.**
All new builds, tests, measurements and statistics ran remotely. This is a
separate RTX PRO 4500 Blackwell Server Edition cohort at its unchanged
**165 W measured reported limit**, not a repeat on an RTX 5090. Integration
and activation remain the team's decisions. Numerical observations below are
measured; ratios, extrapolations, intervals and circuit area are inferred.

## 1. Fused C20 matrix share and Amdahl

Measured warm fused GEMM-plus-epilogue share: **96.7091%**;
measured composite time **7.4435 ms**
per configured batch of 8192. Unfused C20 measures
**94.0664%** and
**7.6196 ms**.
These are last-graph samples, summarized over blocks, and include quantization,
stores and, for fused, XOR. **Pure GEMM-only time remains OPEN.**

The inferred zero-cost-entire-composite time bound is
**30.3872 times**, assuming
that entire stage disappears with no added conversion, transfer or coordination.
It is a time-replacement identity, not an energy or photonic performance claim.
The earlier instrumented observer covers a loop span including memory and
synchronization; it is not a tensor-core-utilization measurement.

## 2. Energy per correct attempt

The table gives measured warm **GPU-board** instantaneous-power integrals,
with measured MAD and inferred sampling intervals. Each variant has at least
600 measured GPU-event seconds in each cold-start/warm condition. Both conditions,
counter/average cross-checks, clocks and temperatures are in
[measurement-tables.md](measurement-tables.md) and the raw summaries.

| Variant | Measured median, µJ / counted evaluation | Measured MAD, µJ | Inferred within-run 95% CI, µJ |
|---|---:|---:|---:|
| lf2_warp_cublas_autotune | 244.8543 | 0.2787 | [244.6373, 245.1474] |
| lf2_register_cutlass256_q4 | 180.4162 | 0.1742 | [180.2743, 180.5534] |
| c20_two_stage_cutlass256_q4 | 163.3168 | 0.0785 | [163.2931, 163.3576] |
| c20_two_stage_cutlass256_fused_fold | 155.1123 | 0.0624 | [155.0886, 155.1523] |
| lf2_register_cutlass256_fused_fold | 172.1250 | 0.1740 | [171.9103, 172.2596] |

Counts come from a conformance-validated complete implementation. Every block
has an outside-window full-batch GPU fold comparison and a C h/fold/digest
comparison; timed attempts are not individually C-replayed. Board integration
excludes CPU, PSU, bank setup and outside-block validation. Independent physical
calibration remains OPEN even if NVML methods agree. The old paced 5090 figures
and its invalid fused-LF2 run are not pooled with this cohort. Exploratory isolated
stage energy is reported separately; it is not an internal matrix-energy share.

## 3. Four-way agreement

**Yes: 560/560 canonical C20 cases** agree in C, CUDA, the outside Python checker
and Rust in the established corpus. The new GPU passed **1120 measured packed/fused
kernel checks** on those cases. The established random replay remains
**1,048,576 full h/fold/digest cases, zero skips or mismatches**; it was not rerun.
It uses one fixed nonzero parent and every header length from zero through the
configured maximum, with the [published distribution](../lf3-c20-2026-10-30/README.md).
The new OpenSSL backend passed the published canonical set and whole-bank checks;
the server worker-scaling cohort also checks all configured workers against
portable C. CUDA still receives its bank from C: these are not four independent
GPU bank derivations or four independent authors.

## 4. Shortcut result

**No work-avoiding energy shortcut has been demonstrated.** This follow-up adds
exact implementation/backend checks, not a universal work lower bound. Packing,
fusion and faster SHAKE implementations retain the required result. The residue
representation is reported as hardware economics. General grinding,
precomputation and sparse-execution economics still need outside review.

## 5. ASIC datapath cost

The separate [mapped RTL workstream](../lf3-c20-mapped-arithmetic-2026-10-30/README.md)
formally proves the residue step and passes six mapped-netlist equivalence checks
and 262,144 measured accumulation comparisons. **Inferred** 13/32 cell-area ratios
are **0.5790 combinational** and **0.4995 registered**; versus a sufficient signed
20-bit accumulator they are **0.7918** and **0.7320**. The research library is
non-manufacturable. These are not measured energy ratios, timing-normalized chip
costs or complete-miner ASIC/GPU/photonic comparisons. Physical mapping and power
remain OPEN.

## 6. CPU verification, bank setup and header sync

On the separate shared EPYC server, measured single-worker OpenSSL bank/cached/cold
medians are **0.260646 /
0.015216 /
0.276005 seconds**. With eight configured workers
on selected distinct physical cores, bank/cold medians are
**0.037534 /
0.053420 seconds**. Worker placement is checked.
All audit checksums, coefficients and allocation are retained. This is not
dedicated modest-machine or low-power physical-hardware qualification.

| Block interval configured, s | Single-worker elapsed days / chain-year, inferred | Eight-worker elapsed days / chain-year, inferred |
|---|---:|---:|
| 10 | 10.0742 | 1.9498 |
| 30 | 3.3581 | 0.6499 |
| 60 | 1.6790 | 0.3250 |
| 150 | 0.6716 | 0.1300 |

These are hash-only projections from medians with a configured 365-day year,
preserving serial parent dependencies. Parallelism is within one bank, not
across unknown future parents. Aggregate CPU days, uncertainty, all worker
counts and bank-plus-upload projections appear in the measurement tables.
Network, state, disk, signatures, forks and production overlap are excluded.
The standalone admission lab rejects its hostile function-call batches before
bank work; real network admission, concurrent ownership and fairness remain OPEN.

## 7. CUDA stall/crash cause

**Unresolved.** This Linux pod's init process completed in a measured
**0.425477 seconds**, including process overhead. It cannot diagnose the owner's
Windows initialization stall/display loss or clear the Windows miner path.
No local research retest was performed.

## 8. Recommendation and blockers

**REVISE; continue qualification, withhold candidate freeze.** Correctness and
implementation evidence are stronger. Sustained success on this server does
not resolve old 5090 metrology or replace a cooled 5090 confirmation. Independent
power calibration, physical modest/low-power CPU evidence, production network
admission and hostile tests, Windows diagnosis, outside grinding/sparse-work
review and complete mapped ASIC/photonic economics remain open. The
[review scope](review-scope.md) gives concrete deliverables.

The team still owns header serialization/length, difficulty adjustment/work
score, genesis difficulty, timestamps, block time and activation. Domain tags
retain experiment.1. Candidate-tag vectors, normative candidate spec, kernel
publication and candidate freeze manifest are not issued here.

## 9. Approximation criterion

**No tested error model demonstrates an advantage under the stated energy
assumptions.** The established study covers 32 configured settings, 1024 measured
nonces on each of two nonzero parents; it was not repeated. Validity requires
the exact final fold, not every exact internal sum. A real method wins if its
measured energy divided by its measured exact-fold probability beats exact
evaluation. Existing injection/pruning energy figures are explicitly inferred
models, not physical analog-device measurements. Correlated noise, calibration,
screening and untested devices remain open; see the
[approximation table](../lf3-c20-security-2026-10-30/approximation-tables.md).
