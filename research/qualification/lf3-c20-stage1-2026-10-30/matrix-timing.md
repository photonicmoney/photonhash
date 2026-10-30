# Matrix loop versus quantize/fold/store

30 October 2026. **Pure multiplication activity remains OPEN.** This completed
bounded diagnostic separates explicit kernel phases; it cannot assign
overlapped GPU wall time or energy solely to multiplication. No hash, tag,
arithmetic representation, chain or miner selection changes.

## Fixed experiment

The rented device reports RTX PRO 4500 Blackwell Server Edition. This is a new
short diagnostic on the same model as the earlier sustained cohort, not an
RTX 5090 retry or another sustained energy confirmation. Driver clocks and
power limits remain unchanged. Continuous NVML monitoring uses configured
80 C thermal and two-second sampling-gap guards. The run passes, with
**52 C measured maximum temperature**. It completes in **14.6513 measured
wall seconds**, including preparation, CPU conformance and all timing windows.
Telemetry is not integrated into a new energy-per-attempt claim.

Configured batch **8192**, tile **128x256x64**, eight complete passes of
4096-term sums. Parent byte `i` is `(11+7*i) mod 256`; header length is
**80 configured bytes**, byte `i` is `(19+13*i) mod 256`. Starting nonce is
`0x12345678abcdef00`. Operands are fixed for attribution. This is not a
random-parent, grinding or steady mining throughput experiment.

The unchanged packed and fused kernels are compared with exact phase-observer
counterparts. The latter use the same tile, CUTLASS Mma and complete int32
arithmetic, placing clock64 observations and CTA barriers around the inclusive
mainloop, register quantize/XOR work, and final epilogue/store. The one-pass
observer writes packed per-pass nibbles; the eight-pass observer writes the full
fold. The one-pass observer moves quantization into accumulator fragments, so it
is a paired exact control, not byte-identical code to the stock packed epilogue.
Its overhead is measured rather than assumed away.

Before measurements, **16 configured unique nonces** under the nonzero parent
pass portable C h, full 2048-byte fold and digest comparisons in each of the
four paths: **64 measured path checks, 16 unique attempts**. Each path also
matches all **8192 measured batch folds** against exact GPU int32 GEMM:
**32768 measured path/fold comparisons, the same 8192 unique attempts**.
The GPU receives the bank from C; this is not a new independent bank derivation.
No mismatch occurred. The established four-way vectors and million-case corpus
are not counted again as new work.

After eight configured warmup launches/path, ten configured cycles repeat
packed/fused/fused/packed, followed by observer-one/observer-eight/observer-eight/
observer-one. Each window has **20 configured kernel launches**. There are
**20 measured windows/path**, each over **100 configured minimum ms**. No
configuration or winner is selected from these samples. Events span only the
matrix/epilogue kernel, excluding vector expansion, separate folding for packed
output, final SHAKE, setup, validation and CPU work. These are short exploratory
phase measurements, not another ten-minute confirmation run.

## Measurements

All times below are **measured median milliseconds/batch** and **measured MAD**.
Intervals are **inferred within-run 95% percentile bootstrap intervals** from
ten ABBA cycle clusters, fixed seed, 10000 resamples. They do not cover different
hosts, thermal states, parents, run order or systematic instrumentation bias.

| Kernel/control | Median ms, measured | MAD ms, measured | 95% CI ms, inferred | Event seconds, measured |
|---|---:|---:|---:|---:|
| Packed C20, unchanged | 7.631587 | 0.015569 | [7.615810, 7.647853] | 3.051517 |
| Fused C20, unchanged | 7.420618 | 0.014589 | [7.406928, 7.436110] | 2.968410 |
| Exact one-pass phase observer | 7.640323 | 0.013931 | [7.626830, 7.655389] | 3.056595 |
| Exact eight-pass phase observer | 7.443777 | 0.016478 | [7.426192, 7.456535] | 2.976175 |

Observer event overhead from these medians is **0.1145% inferred** for one-pass
and **0.3121% inferred** for eight-pass. Small end-to-end overhead does not prove
that every individual observer phase is unbiased.

The [compiler resource records](evidence/matrix-resources.json) report **224
measured registers/thread** for both stock packed and its one-pass observer,
**246 measured** for stock fused and **254 measured** for its eight-pass observer.
All four report **zero measured stack/spill-store/spill-load bytes**. These are
ptxas resource reports, not runtime memory-traffic counters. The reported single
barrier is a barrier identifier count, not the number of executed synchronizations.
Observer barriers, register pressure and timestamp instructions can affect
execution. Thread-zero clocks and CTA barriers do not make each phase an
unbiased hardware-unit stopwatch; warp scheduling and compiler instruction
placement remain possible phase biases. No SASS-ordering proof is claimed.

The following are **measured medians of per-CTA clock64 span ratios**. There
are **8192 measured CTA records** for the one-pass observer and **1024 measured
CTA records** for the eight-pass observer, from one fixed launch each. CTAs
overlap, share resources and are not independent wall-time samples. Medians of
separate ratios need not sum to exactly 100%; iterator setup, reconstruction,
barriers and clock instructions account for additional span.

| Observer | Inclusive matrix mainloop, measured | Quantize/fold, measured | Final epilogue/store, measured |
|---|---:|---:|---:|
| One pass | 94.8008% | 0.6000% | 4.3391% |
| Eight passes/fused | 98.5725% | 0.7122% | 0.5618% |

Raw per-CTA clocks, event windows, receipts and deterministic reduction are
published. The kernel bodies remain private pending an eligible source freeze,
so this is numerical reproducibility, not full public GPU source reproduction.

## What remains unresolved

The mainloop's Mma call includes global/shared operand loading, synchronization,
pipeline waiting and arithmetic. It is not a stopwatch around bare tensor-core
instructions. The earlier roughly 98.7% observer has the same scope and must
not be described as measured tensor-core cycles or pure multiplication share.
This study makes quantize/store overhead separately visible without turning the
remaining span into an unsupported hardware claim.

Nsight Compute **2025.3.0.0 measured version** reports **ERR_NVGPUCTRPERM** on
metric discovery. Its query exits **0 measured**, despite the error; that exit
status is not treated as a successful profile. No profiling measurements are
claimed. The predeclared alternate Community Cloud RTX4090 request and its
owner-requested retry both return HTTP **400 measured**, no capacity, before
resource creation. Both are retained in the ledger. These failures are not hash
mismatches or evidence for a work-avoiding shortcut. No driver/module permissions,
privileges or clock controls were changed.

On an explicitly profiling-enabled remote host, collect actual tensor-pipeline
activity/instruction counters on unchanged kernels separately from event timing.
Report operand-delivery/stall counters and observer effects. Counters describe
overlapping activity; even then, an exact additive wall-time fraction removable
by photonics is not automatic. A photonic replacement must include data loading,
conversion, quantization and reload costs. A whole-stage-free Amdahl ceiling
cannot be relabeled as a pure multiplication speedup.

These interpretations follow NVIDIA's [profiling guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)
and [counter-permission guidance](https://developer.nvidia.com/ERR_NVGPUCTRPERM).
Profiler replay/instrumentation can perturb execution; profiler-run event times
must remain separate from unprofiled times. The raw denial, rather than a
successful-looking process receipt, controls the result here.
