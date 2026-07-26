# Exact electronic-miner baseline: RTX 5090

**Measurement date:** 2026-07-26

**Status:** published evidence for frozen falsified profile

**Protocol verdict:** the active n=1024 profile falsifies R3 on this hardware

This report measures an exact, end-to-end electronic PhotonHash miner. It is
not a GPU-versus-photonic comparison: no complete photonic implementation has
yet been measured. It does answer the narrower design question that matters
first: an aggressively batched electronic miner makes the active matrix stage
only about 11-12% of device time, not the >=90% target.

## Result

Seventy-five sustained samples covered three batch sizes, five independently
derived parent matrices, and five repeats. Every sample processed at least
100 million attempts. Before timing, the sequential path and all eight
pipeline slots were checked against the portable C trace oracle for 16
nonces each: 10,800 complete h_in, x, y, digest, and target comparisons across
the final sweep.

| Batch | Samples | Sequential attempts/s | CV | GEMM share | 8-stream attempts/s | CV | Sequential uJ/attempt | Pipeline uJ/attempt |
|------:|--------:|----------------------:|---:|-----------:|--------------------:|---:|----------------------:|--------------------:|
| 8,192 | 25 | 22.470 M | 0.90% | 11.061% | 31.485 M | 4.76% | 10.296 | 10.130 |
| 32,768 | 25 | 30.453 M | 1.01% | 12.121% | **33.429 M** | 1.91% | **9.570** | 10.789 |
| 131,072 | 25 | 32.044 M | 1.48% | 12.207% | 31.849 M | 1.67% | 9.737 | 10.927 |

At batch 32,768 the mean sequential stage costs were:

| Stage | us/attempt | Share |
|-------|-----------:|------:|
| register-resident SHAKE + vector decode | 0.020556 | 62.59% |
| exact INT8 x INT8 -> INT32 GEMM | 0.003981 | 12.12% |
| requantization + final SHAKE + target | 0.008304 | 25.28% |

Parent choice did not produce a meaningful favorable-matrix effect in this
sample: mean sequential rates across the five parent datasets ranged from
28.127 M/s to 28.477 M/s when all batch sizes were pooled.

As a methodology control, the corrected allocation-free scalar benchmark was
also run for three seconds on an AMD Ryzen 7 9800X3D with MSYS2 GCC 16.1.0
(`-O2`, batch 32). It measured 46.976 us/attempt, with the exact scalar
matvec at 38.228 us or 81.38%. This confirms why scalar-only evidence looked
promising while also demonstrating that it does not predict optimized
electronic mining economics.

The active profile therefore fails R3 on this electronic implementation. An
otherwise free replacement for a 12.12% stage can improve end-to-end speed by
at most 1/(1-0.1212) = 1.138x before modulation, conversion, guard-band,
digital-assist, or verification costs are included.

## Hardware and software

- GPU: NVIDIA GeForce RTX 5090, compute capability 12.0, 32,606 MiB
- Driver: 595.79
- CUDA compiler/runtime/driver API: 13.2 / 13.2 / 13.2
- Matrix: n=1024, 1 MiB unpacked signed INT8 storage
- Exact GEMM: cuBLAS cublasGemmEx, CUDA_R_8I inputs,
  CUBLAS_COMPUTE_32I, CUBLAS_GEMM_AUTOTUNE
- CUDA target: sm_120
- SHAKE block size: 128 threads
- Overlap depth: eight independent streams and scratch sets

No firmware, driver, clock, voltage, power-limit, fan, BIOS, permission, or
system setting was changed. The experiment used user-space CUDA workloads and
read-only NVIDIA telemetry.

## Optimization performed

The timed path is not the original first-pass baseline:

1. Keccak-f[1600] state is fully register-resident. The sm_120 build reports
   no local-memory stack or spills for the derive and final kernels.
2. The exact GEMM uses cuBLAS autotuning.
3. One through sixteen independent pipeline depths were tested in randomized,
   repeated sustained runs. Depths at and above roughly three saturated the
   overlap benefit; eight is the reproducible default.
4. A signed packed-INT4 CUTLASS probe was implemented and checked exactly.
   Its best tested kernel reached about 30.1 TMAC/s, far below the
   approximately 260-281 TMAC/s exact cuBLAS INT8 path, so it was not used to
   inflate the final result.
5. NVIDIA Compute Sanitizer memcheck reports zero errors on the final
   eight-stream binary.
6. Matrix, header, and target remain resident. Allocation, validation, matrix
   derivation, and one-time upload are excluded from marginal nonce timing.
7. Sequential CUDA events report stage times. Host wall time reports the
   overlapped pipeline.

## Energy method

Primary energy values use mean read-only NVML board-power samples multiplied
by the exact host-observed timed interval. The independent NVML cumulative
energy counter is retained in the raw CSV. It read about 20-30% higher in
these short windows because its update boundary does not align reliably with
the timed interval, so it is not mixed into the headline values.

The reported energy is GPU-board energy, not chip-only or wall-plug system
energy. Across the final sweep the maximum post-run temperature was 60 C.

## Matrix and approximation evidence

The independent Python analysis first reproduces a published matrix checksum,
then derives matrices with hashlib rather than the C implementation.

- 1,000 parent hashes / 1,048,576,000 entries analyzed
- aggregate signed-nibble chi-square: 14.03 with 15 degrees of freedom
- mean entry: -0.4999896 (the expected nibble mean is -0.5)
- mean zlib ratio on packed matrices: 1.0003166
- all five deeply analyzed 1024x1024 matrices had floating-point rank 1024
- the uncentered matrices have an expected mean-bias singular outlier; after
  adding 0.5, the largest singular values were about 292-297

No tested approximation produced one exact 1,024-bucket output among 1,280
vectors:

| Approximation | Mean bucket accuracy | Exact whole outputs |
|---------------|---------------------:|--------------------:|
| rank 128 | 18.68% | 0 / 1,280 |
| rank 256 | 23.79% | 0 / 1,280 |
| rank 512 | 41.60% | 0 / 1,280 |
| rank 768 | 75.91% | 0 / 1,280 |
| rank 992 | 98.98% | 0 / 1,280 |
| best-norm 75% of columns + omitted-row mean | 29.20% | 0 / 1,280 |
| best-norm 99.22% of columns + omitted-row mean | 83.25% | 0 / 1,280 |

These experiments do not prove approximation attacks impossible. They do show
that high component accuracy is not enough: one wrong bucket changes the
final SHAKE input, and even approximations retaining almost all matrix work
failed to produce a complete exact vector in this corpus.

## Reproduction

From an x64 Visual C++ environment:

~~~bat
nvcc -Iinclude -O3 -std=c++17 -arch=sm_120 ^
  -DPH_CUBLAS_ALGO=CUBLAS_GEMM_AUTOTUNE ^
  -DPH_PIPELINE_DEPTH=8 ^
  tools\ph_cuda_bench.cu src\photonhash.c ^
  -o ph_cuda_bench.exe -lcublas

powershell -File tools\run_cuda_sweep.ps1 ^
  -Executable .\ph_cuda_bench.exe ^
  -Batches 8192,32768,131072 ^
  -Datasets 0,1,2,3,4 ^
  -TargetAttempts 100000000 -Repeats 5

py -3 tools\ph_matrix_analysis.py ^
  --matrices 1000 --deep-matrices 5 --vectors 256 ^
  --output matrix-analysis.json
~~~

Raw and summarized evidence is stored under research/results.

## Design implication

At batch 32,768 the measured non-matrix work is 0.028859 us/attempt and one
exact GEMM is 0.003981 us/attempt. A simple cost model needs at least 66
non-redundant matrix-equivalent units per attempt to reach a 90% matrix share:

~~~text
ceil(9 * 0.028859 / 0.003981) = 66
~~~

Repeating the identical product is optimizable away and is not a construction.
Sixty-six distinct matrices would destroy the load-once premise; scaling n
alone suggests a dimension on the order of 65,536 and a packed matrix around
2 GiB. Replacing SHAKE would need roughly a 65x reduction in all surrounding
work to meet the same target. None is a credible patch to v0.2.

The evidence supports a clean decision: retain v0.2 as a falsified
experimental profile, do not freeze it into Laser consensus, and require a
new construction to pass a balanced electronic baseline and a complete
photonic measurement before activation.
