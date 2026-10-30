# Measurement tables

Medians and MAD below are **measured** from blocks/samples; bracketed 95% intervals are **inferred** within-run moving-block bootstrap intervals. They exclude calibration error and hardware-population uncertainty. Configured sizes are identified separately.

## Full unpaced GPU board energy

| Variant | Condition | Instantaneous integral: measured median / MAD / inferred CI, µJ per counted evaluation | Counter: measured median / MAD / inferred CI, µJ |
|---|---|---:|---:|
| lf2_warp_cublas_autotune | cold_start | 244.719941 / 0.235962 / [244.483979, 244.866010] | 244.353559 / 0.127666 / [244.216838, 244.430455] |
| lf2_warp_cublas_autotune | warm | 244.854270 / 0.278705 / [244.637282, 245.147425] | 244.413133 / 0.108038 / [244.321200, 244.496154] |
| lf2_register_cutlass256_q4 | cold_start | 180.582525 / 0.094396 / [180.482777, 180.636837] | 180.303997 / 0.064116 / [180.239881, 180.348799] |
| lf2_register_cutlass256_q4 | warm | 180.416222 / 0.174170 / [180.274288, 180.553449] | 180.287059 / 0.054047 / [180.254768, 180.362503] |
| c20_two_stage_cutlass256_q4 | cold_start | 163.434554 / 0.112269 / [163.326904, 163.499014] | 163.287659 / 0.073560 / [163.204399, 163.337179] |
| c20_two_stage_cutlass256_q4 | warm | 163.316782 / 0.078457 / [163.293096, 163.357567] | 163.152948 / 0.045489 / [163.113604, 163.167329] |
| c20_two_stage_cutlass256_fused_fold | cold_start | 155.170716 / 0.092058 / [155.092809, 155.227992] | 155.019077 / 0.056975 / [154.968191, 155.068870] |
| c20_two_stage_cutlass256_fused_fold | warm | 155.112301 / 0.062381 / [155.088571, 155.152251] | 154.972470 / 0.050674 / [154.952949, 155.001034] |
| lf2_register_cutlass256_fused_fold | cold_start | 172.155870 / 0.191934 / [171.958862, 172.292555] | 172.058176 / 0.079060 / [171.981207, 172.097512] |
| lf2_register_cutlass256_fused_fold | warm | 172.124954 / 0.174035 / [171.910289, 172.259633] | 172.045469 / 0.042426 / [172.017726, 172.132151] |

The denominator is complete evaluations counted by a conformance-validated implementation, not individual C replay of every timed attempt. Per-block validation is outside the integrated window. CPU/PSU/setup energy is excluded.

## Warm throughput and sampled matrix composite

Each stage observation is the last graph in a configured 64-replay window. GEMM includes its quantizing epilogue, plus XOR in fused variants. Pure GEMM time is OPEN.

| Variant | Event throughput: measured median / MAD / inferred CI, attempts/s | Matrix composite: measured median / MAD / inferred CI, ms/batch | Composite share: measured median / MAD / inferred CI, % |
|---|---:|---:|---:|
| lf2_warp_cublas_autotune | 674554.715378 / 351.354985 / [674222.860590, 674906.560863] | 8.546368 / 0.006144 / [8.540224, 8.551488] | 70.374994 / 0.017217 / [70.361488, 70.389953] |
| lf2_register_cutlass256_q4 | 914716.878673 / 311.406087 / [914405.472585, 914956.622883] | 7.455776 / 0.003072 / [7.453232, 7.459360] | 83.284735 / 0.010438 / [83.276174, 83.293315] |
| c20_two_stage_cutlass256_q4 | 1011099.896663 / 145.066653 / [1010981.338888, 1011220.723820] | 7.619632 / 0.001040 / [7.619616, 7.620656] | 94.066398 / 0.002078 / [94.064138, 94.067532] |
| c20_two_stage_cutlass256_fused_fold | 1064342.111891 / 218.553540 / [1064219.293587, 1064521.865435] | 7.443456 / 0.002048 / [7.441408, 7.445504] | 96.709142 / 0.001750 / [96.707608, 96.710684] |
| lf2_register_cutlass256_fused_fold | 958742.027982 / 177.397528 / [958494.418000, 958879.686634] | 7.275264 / 0.001792 / [7.273472, 7.278080] | 85.157760 / 0.008399 / [85.151636, 85.165339] |

## Exploratory isolated stage

Configured 30 event seconds per variant, fixed validated vectors, no pacing; not sustained full-attempt confirmation. Counts are stage evaluations. Isolated board energy is not an attribution of arithmetic energy inside the full pipeline.

| Variant | Board integral: measured median / MAD / inferred CI, µJ/stage evaluation | Counter: measured median / MAD / inferred CI, µJ |
|---|---:|---:|
| lf2_warp_cublas_autotune | 180.600068 / 0.451763 / [179.589497, 180.929542] | 180.287040 / 0.382002 / [179.869840, 180.633845] |
| lf2_register_cutlass256_q4 | 153.864814 / 0.202338 / [153.615330, 154.020006] | 153.432906 / 0.206081 / [153.228534, 153.640695] |
| c20_two_stage_cutlass256_q4 | 153.612322 / 0.338125 / [152.530311, 153.813704] | 153.541637 / 0.237649 / [153.405761, 153.881060] |
| c20_two_stage_cutlass256_fused_fold | 149.664601 / 0.311651 / [148.768516, 149.748729] | 149.268859 / 0.142551 / [149.135793, 149.420895] |
| lf2_register_cutlass256_fused_fold | 149.416080 / 0.623145 / [148.990380, 150.236671] | 149.154232 / 0.274794 / [148.626445, 149.390447] |

## Separate shared-server CPU cohort

All seeds, audit checksums and expanded coefficients retained; allocation included. One configured worker for portable, then OpenSSL at configured one, two, four and eight workers. Selected cores and observed placement are in the design/probe records. This is not a dedicated modest or low-power computer.

| Backend / workers configured | Bank: measured median / MAD / inferred CI, s | Cached verify: measured median / MAD / inferred CI, s | Cold verify: measured median / MAD / inferred CI, s |
|---|---:|---:|---:|
| portable / 1 | 0.642345 / 0.003615 / [0.638775, 0.645038] | 0.015165 / 0.000033 / [0.015149, 0.015196] | 0.657458 / 0.003800 / [0.653865, 0.660185] |
| OpenSSL / 1 | 0.260646 / 0.000727 / [0.260277, 0.261386] | 0.015216 / 0.000040 / [0.015193, 0.015237] | 0.276005 / 0.000521 / [0.275572, 0.276657] |
| OpenSSL / 2 | 0.140599 / 0.003987 / [0.137372, 0.142509] | 0.015127 / 0.000037 / [0.015106, 0.015233] | 0.156031 / 0.003857 / [0.152615, 0.157822] |
| OpenSSL / 4 | 0.072829 / 0.002128 / [0.070179, 0.074175] | 0.015164 / 0.000068 / [0.015125, 0.015282] | 0.088117 / 0.001941 / [0.087096, 0.089692] |
| OpenSSL / 8 | 0.037534 / 0.004583 / [0.035712, 0.038571] | 0.015184 / 0.000071 / [0.015156, 0.015236] | 0.053420 / 0.004652 / [0.051431, 0.054131] |

## Hash-only header sync and turnover projections

Every value below is **inferred from measured medians**, not a measured chain sync. A configured 365-day chain-year and serial parent dependency are preserved. Elapsed days and aggregate CPU days are different. Upload uses a separate pageable-copy median; no production miner overlap is assumed. Network/storage/signatures/state/forks are excluded.

| Backend / workers configured | Block time configured, s | Elapsed days / chain-year inferred | CPU days / chain-year inferred | Bank + upload fraction of block time inferred, % |
|---|---:|---:|---:|---:|
| portable / 1 | 10 | 23.997202 | 23.997158 | 6.470885 |
| portable / 1 | 30 | 7.999067 | 7.999053 | 2.156962 |
| portable / 1 | 60 | 3.999534 | 3.999526 | 1.078481 |
| portable / 1 | 150 | 1.599813 | 1.599811 | 0.431392 |
| OpenSSL / 1 | 10 | 10.074177 | 10.072820 | 2.653887 |
| OpenSSL / 1 | 30 | 3.358059 | 3.357607 | 0.884629 |
| OpenSSL / 1 | 60 | 1.679030 | 1.678803 | 0.442315 |
| OpenSSL / 1 | 150 | 0.671612 | 0.671521 | 0.176926 |
| OpenSSL / 2 | 10 | 5.695119 | 10.453822 | 1.453418 |
| OpenSSL / 2 | 30 | 1.898373 | 3.484607 | 0.484473 |
| OpenSSL / 2 | 60 | 0.949186 | 1.742304 | 0.242236 |
| OpenSSL / 2 | 150 | 0.379675 | 0.696921 | 0.096895 |
| OpenSSL / 4 | 10 | 3.216263 | 10.788715 | 0.775723 |
| OpenSSL / 4 | 30 | 1.072088 | 3.596238 | 0.258574 |
| OpenSSL / 4 | 60 | 0.536044 | 1.798119 | 0.129287 |
| OpenSSL / 4 | 150 | 0.214418 | 0.719248 | 0.051715 |
| OpenSSL / 8 | 10 | 1.949826 | 10.348915 | 0.422768 |
| OpenSSL / 8 | 30 | 0.649942 | 3.449638 | 0.140923 |
| OpenSSL / 8 | 60 | 0.324971 | 1.724819 | 0.070461 |
| OpenSSL / 8 | 150 | 0.129988 | 0.689928 | 0.028185 |

The raw summaries also retain elapsed-throughput statistics, cold-start series, clocks, temperature, sampling gaps, field timestamps, sensor-method differences and the explicitly hypothetical composite-stage Amdahl calculation. No absolute sensor calibration or photonic speedup is established.
