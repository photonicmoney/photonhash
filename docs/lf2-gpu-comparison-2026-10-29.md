# Exact LF2 packing and LF3-C20 on RTX 5090

29 October 2026. Experimental, non-consensus research. Both results below
are published with [synthetic benchmark records and analysis](../research/launch/lf2-c20-gpu-2026-10-29/README.md).
No chain or miner was changed by this work.

The measured CPU/CUDA prototype remains local at source checkpoint
`441e4f7197517f68883823ab2bc55b5fcb097434`. This documentation publication
contains its byte rules, reference vector, measurement records and CPU-only
analysis tools. The kernel sources and executable are not included, so these
records support auditing the reported measurements, not rebuilding the GPU
implementation from this checkout.

## Implemented changes

1. **Unchanged LF2-K8:** a CUTLASS epilogue quantizes each complete int32 dot
   product and packs two adjacent row buckets into a byte before global stores.
   The subsequent kernel XORs the eight packed pass outputs. It retains the
   frozen matrix, vector, quantizer, fold and digest bytes.
2. **LF3-K8-C20-experiment.1:** a GPU implementation of the separately named
   [ChaCha20 experiment](lf3-k8-c20-experiment-1.md). SHAKE still binds the header
   and nonce; ChaCha20 blocks 1 through 32 expand that public binding into the
   vector. Matrices, exact quantization and the complete 2048-byte fold remain.
   Its distinct domains and expansion produce a different hash. It cannot be
   substituted into LF2 consensus without a separate protocol decision.

The local prototype uses separate comparison, CUTLASS epilogue and Keccak
helpers. The public frozen `tools/ph_cuda_bench.cu` and all six freeze-manifest
files remain unchanged.

The original optimized synthetic benchmark binds an 80-byte header in one
SHAKE rate block. Reusing that shortcut for a 184-byte header would be wrong.
The new register and warp implementations absorb multiple binding blocks.
Exact rate-boundary GPU testing remains incomplete, as recorded below.

## Arithmetic and memory

For the frozen inputs, products range from -56 to 64. No partial 4096-term sum
can overflow int32 or reach saturating-MMA limits. The packed epilogue uses
`(uint32_t(sum) >> 9) & 15`, exactly equivalent to the frozen offset rule.
Split-K is disabled: quantizing partial sums before reduction would be wrong.
CUTLASS owns complete packed output fragments, avoiding competing nibble writes.
Output order is attempt, pass, adjacent row pair, with the lower row in the low
nibble. XORing complete packed bytes preserves the per-row XOR fold.

At batch 8192, the GEMM intermediate falls from **1 GiB int32 to 128 MiB q4**:
an **8x reduction in that buffer**, not an 8x speedup or whole-program memory
reduction. The harness deliberately allocates both representations plus an
int32 reference buffer for validation. It does not measure the peak footprint
of a packed-only production miner.

The GEMM timer includes the epilogue and stores. It is called
**GEMM-plus-epilogue** throughout this report. Moving quantization into that
timer does not establish a corresponding increase in pure matrix arithmetic,
matrix energy or optical advantage.

## Fair comparison

Each profile receives the same six GEMM choices: cuBLAS default, cuBLAS
autotune, CUTLASS 128/256-column int32, and the corresponding packed epilogues.
LF2 receives register-per-nonce and warp-per-nonce SHAKE implementations. C20
receives a two-kernel register-binding/parallel-expansion implementation and a
fused warp-binding/parallel-expansion implementation. This is **24 variants**,
including matched int32 controls for both packed tile shapes.

Banks, dimensions, pass count, opaque header bytes, nonce sequence and strict
target semantics match within each case. LF2 and C20 intentionally derive
different vectors because they are different profiles. Every round uses the
same first nonce for every variant. All variants warm up; a fixed-seed shuffle
randomizes their order within each paired round. Every measured variant gets
two identical LF2/cuBLAS primer graph replays immediately beforehand. Primers
are charged to the resource budget, outside the candidate timing.

All four stages run serially in one captured CUDA graph: binding/expansion,
GEMM-plus-epilogue, fold, and final SHAKE. External event-record graph nodes
provide timestamps around actual device stages. The budget end event is queued
before the host waits. Blocking synchronization avoids CPU polling. Graph
replays prevent intentionally capped host scheduling from inserting launch
gaps between the measured stages. Desktop/driver preemption can still interrupt
a graph and appears as timing outliers; no samples are silently removed.

The baseline is the **fastest tested LF2 int32 configuration for that case**,
including cuBLAS autotuning and both CUTLASS shapes, rather than a convenient
slow implementation. Packed LF2 and C20 also get their fastest tested choices.
The analysis reports C20 against **already packed LF2** as well as the int32
baseline. Choice selection and comparison use the same limited samples, so
these are exploratory measurements rather than independent confirmation or
proof of globally optimal kernels.

Parent derivation, host/device transfer, allocation, CPU checking, graph
construction, warmup, primers and 75 ms pauses are excluded from marginal
device timings. There is no overlap between stages or multiple streams. These
numbers are **not full-miner sustained throughput**, host throughput, parent
turnover/reorg latency, energy efficiency or a comparison against a fully
tuned Blackwell-specific adversary. Sm80 INT8 MMA kernels are compiled for
sm_120; native Blackwell, exact alternative representations and wider tuning
remain available to an adversary.

## Correctness evidence

- Every uploaded 128 MiB parent bank is read back in full and compared byte for
  byte. Its seed/checksum commitment must match the frozen compact case.
- For every variant, the whole batch of int32 outputs or packed buckets is
  checked against exact cuBLAS output. Timed cases repeat this after timing on
  the last measured nonce family, in addition to initial wraparound inputs.
- A portable CPU trace checks the complete first nonce's binding, vector,
  2048-byte fold and digest for both profiles. Positions 1, 15 and the last
  batch position additionally check binding and every vector coefficient.
  This is not an independent CPU matrix evaluation of every batch nonce.
- The completed corpus includes zero and all-FF parents, 80/184-byte headers, empty and
  one-byte headers, a 4096-byte header and maximum/wrapping nonces. Binding-rate
  boundary checks were not completed, as explained below.
- Target tests reject digest equality and zero, and accept digest plus one
  under the defined little-endian strict comparison, for each profile.
- The empty/one-byte cases anchor LF2 to the existing frozen full-size vectors.
  The zero-parent 184-byte maximum-nonce C20 case anchors to the earlier
  generated fixture, whose expansion/final hash were independently checked
  using OpenSSL. CUDA is a second matrix execution path for C20, but shares
  the portable bank implementation; it is not a fully independent composite
  implementation or cryptographic review.

`tools/analyze_lf2_gpu.py` rejects incomplete performance runs, missing variant
or round coverage, failed validation, nonpositive timing, inconsistent stage
sums, and fixture/bank mismatches. Run it without Python `-O`.

## Collected results

Five completed timing cases contain **456 measured graph samples** across
24 equally validated variants. The table gives medians in **device
microseconds per attempt**. Uplifts are median paired-round throughput
ratios minus one; a ratio of separate medians can differ. Parent 00/FF
means 32 repeated bytes. Choices are selected separately in each case.

| Batch | Header bytes | Parent | Rounds | LF2 int32 us | LF2 packed us | C20 us | Packing uplift | C20 over packed LF2 |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4096 | 184 | 00 | 7 | 0.664 | 0.497 | 0.395 | +30.5% | +25.3% |
| 8192 | 80 | 00 | 3 | 0.524 | 0.452 | 0.380 | +15.4% | +19.1% |
| 8192 | 80 | FF | 3 | 0.592 | 0.451 | 0.362 | +34.3% | +24.4% |
| 8192 | 184 | 00 | 3 | 0.525 | 0.457 | 0.367 | +14.6% | +24.5% |
| 8192 | 184 | FF | 3 | 0.597 | 0.455 | 0.365 | +31.3% | +24.7% |

Across these cases, packing improves paired device throughput **14.6-34.3%**
over the fastest tested int32 LF2. C20 improves it a further **19.1-25.3%**
over the fastest tested packed LF2, and **41.5-63.7%** over int32 LF2.
Packing wins 19/19 paired rounds across the selected case winners; C20
beats packed LF2 in 18/19. These round counts are descriptive, not an
independent statistical confidence statement. A retained timing outlier
produces a roughly 10x paired ratio. Desktop/driver interference is plausible;
its cause was not isolated.

The best C20 composite GEMM-plus-epilogue stage occupies **84.4-87.2%**
of sampled device time by median per-sample ratio. This includes packed
quantization and output stores. It must not be compared directly with the
old GEMM-stage percentage as if timing boundaries were identical, or as proof
of an optical or energy advantage.

The exact selected configurations are:

| Batch/header/parent | LF2 int32 | LF2 packed | C20 |
| --- | --- | --- | --- |
| 4096/184/00 | `lf2_warp_cutlass256_i32` | `lf2_warp_cutlass128_q4` | `c20_fused_cutlass256_q4` |
| 8192/80/00 | `lf2_register_cutlass256_i32` | `lf2_warp_cutlass256_q4` | `c20_fused_cutlass128_q4` |
| 8192/80/FF | `lf2_warp_cublas` | `lf2_warp_cutlass256_q4` | `c20_two_stage_cutlass256_q4` |
| 8192/184/00 | `lf2_warp_cublas_autotune` | `lf2_register_cutlass256_q4` | `c20_two_stage_cutlass256_q4` |
| 8192/184/FF | `lf2_register_cublas_autotune` | `lf2_register_cutlass256_q4` | `c20_two_stage_cutlass256_q4` |

For the primary 8192/184/00 case, stage medians per attempt are:

| Selected path | Binding/vector us | GEMM+epilogue us | Fold us | Final SHAKE us | Total us |
| --- | ---: | ---: | ---: | ---: | ---: |
| LF2 int32 | 0.101 | 0.323 | 0.083 | 0.019 | 0.525 |
| LF2 packed | 0.097 | 0.319 | 0.022 | 0.019 | 0.457 |
| C20 packed | 0.007 | 0.319 | 0.022 | 0.019 | 0.367 |

Separate stage medians need not sum to the median total. The [published analysis](../research/launch/lf2-c20-gpu-2026-10-29/summary.json)
retains every recorded sample, total-time MAD, extrema, matched epilogue controls,
paired ratios and fixture anchors. No outlier filter is applied.

**Limits of collection:** the extra LF2 binding-rate-boundary process
stalled before its first metadata record, during CUDA initialization.
Its cause is unresolved. This benchmark child was verified by
executable path and start time, then stopped after 94.6 wall seconds and
87.95 CPU-seconds. No hash result or timed window was produced. Further GPU
work ended. Exact rate-boundary GPU checks and a preselected-choice
confirmation run were therefore **not completed**. The five completed
timing cases and empty/one-byte/4096-byte correctness cases remain valid.
The local wrapper now has a 15-second no-initial-output watchdog; normal,
silent-start and wall-time termination were tested using tiny CPU-only
children. That wrapper change received no additional GPU trial.

Completed final-binary runs account for **23.806 seconds** of event windows.
Across all GPU attempts, including pilots and incomplete trials, observed
windows sum to **44.371 seconds**; conservative reservations sum to
**54.371 seconds**, below the 60-second session budget. Before/after GPU
temperature snapshots span **38-56 C**; they are not continuous peak
measurements. Snapshot power is not benchmark energy attribution.

## Environment and resource boundaries

RTX 5090, compute capability 12.0, shared Windows desktop/WDDM. Ambient clocks;
no power, frequency, driver, persistence or application settings changed.
The device was checked for low existing utilization, temperature and adequate
free VRAM before every process. It was not reserved exclusively for this work.

The compiler is CUDA **13.2/V13.2.78**, with MSVC **14.44.35207**, `-O3`, C++17,
`sm_120`, one compilation thread and one split-compile thread. C sources pass
`/W4 /WX`; all Windows objects use `/MT`. CUTLASS is the external NVIDIA
**v3.9.2** checkout at `ad7b2f5e84fcfa124cb02b91d5bd26d238c0459e`
(BSD-3-Clause); it is neither patched nor vendored. Upstream deprecated-vector
warnings remain; no build error or CRT conflict remains in the final build.

Runtime queries return CUDA runtime/driver **13040** and cuBLAS **130400**,
despite compiler/header versions 13.2/13020. Inspection of the running process
records toolkit cuBLAS DLLs and the driver's `nvcudart_hybrid64.dll` reporting
13040. These returned runtime versions are recorded separately from the
compiler; all variants within a case use the same executable and loaded stack.
The executable SHA-256 is
`41617d7fe1e96343978fb868044c0d28663a8db239e89e5e228204c0e8440fe1`.
After measurement, only an extra trailing blank line was removed from the
Keccak helper. The exact tested header is archived and its complete C++ body
is byte-identical to the final header; no kernel changed and no GPU rerun was
performed for that whitespace cleanup.

Child jobs are assigned before resuming: idle priority, one processor affinity,
**1.00% system CPU cap**, 2 GiB memory for compilation and 6 GiB for GPU jobs.
Each GPU process has a conservative 5000 ms cumulative event-window threshold,
an external 240-second wall watchdog, and the total-work deadline. There is a
75 ms pause after every window. The finite last window may overshoot before
the threshold is checked. Windows can include host/driver stalls, so event
window accounting is not a hardware-busy or energy counter. The session budget
is 60 seconds, conservatively reserving at least 5 seconds for incomplete runs.

Failed attempts are retained: Windows build setup/preprocessor/template issues,
an early CRT mismatch later corrected, a 2 GiB job allocation failure despite
ample GPU memory, and event-window threshold aborts. An early outer timer
queued its end marker after a host wait and counted idle CPU gaps. Corrected
collection queues it before waiting. Earlier pilot/build timings are separate;
incomplete runs supply no headline performance result. No unrelated process
was stopped or altered to make a run succeed.

## Reproduction and remaining work

The [evidence README](../research/launch/lf2-c20-gpu-2026-10-29/README.md)
lists all eight completed final-binary logs and the command to regenerate the
summary using `tools/analyze_lf2_gpu.py`. That analysis uses Python's standard
library and launches no GPU work. The
[C20 vector checker](../tools/check-lf3-c20-vector.mjs) uses Node/OpenSSL to
check the RFC primitive, binding, expansion and final hash without recomputing
the full matrix bank or products.

The local GPU build used strict separate `cl` C objects and `nvcc`, with
`/Zc:preprocessor` and `/Zc:__cplusplus` for CUTLASS. Its opt-in Make target was
only dry-run checked. Linux GPU builds and a second device were not executed.
The public record includes tested binary/source hashes, compile environment,
exact run arguments, all completed sample records, a ledger of earlier and
incomplete attempts, and the uncompleted checks. No new benchmark was run for
this documentation publication.

Packing is a useful unchanged-hash optimization candidate. C20 is a separately
named performance experiment. Neither GPU result establishes the cost of the
best partial/approximate attack, resistance to public-seed/parent/header
selection, weak/related seeds or specialized hardware. Next useful evidence is
independent composite implementation and adversarial review, broader exact
GPU/hardware comparisons, dedicated stable-device confirmation, measured energy
and full-miner parent turnover/cancellation behavior. A higher composite GEMM
percentage alone is insufficient to promote a consensus construction.

Technical references: [CUTLASS v3.9.2](https://github.com/NVIDIA/cutlass/tree/v3.9.2),
[CUDA event API](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__EVENT.html),
[cuBLAS](https://docs.nvidia.com/cuda/cublas/index.html),
[RFC 8439](https://www.rfc-editor.org/rfc/rfc8439.html).
