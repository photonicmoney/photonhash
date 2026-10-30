# Fixed confirmation measurement tables

**FINAL REVIEW CORRECTION: FUSED LF2 CONFIRMATION INVALID.** Its measured maximum sampling gap is 9.370326 seconds, exceeding the configured two-second limit. All five processes completed, but only the other four variants have eligible telemetry. Neither the live guard nor the original aggregator rejected this gap. Fused-LF2 timing and energy rows are retained as INVALID observations, excluded from qualification. Cause remains OPEN; no retry was made. See [post-review-qualification.json](post-review-qualification.json).

The unchanged original statistics and original validation receipt are retained in `energy-statistics-before-review.json` and `publication-validation-before-review.json`. Their former pass flags are superseded. The current summary marks confirmation incomplete. The portable energy analyzer reproduces the original raw statistics, not qualification; its old `confirmation_complete` field is insufficient. No corrected analyzer execution or new benchmark is claimed. Transport checksums below are file-maintenance checks, not a repeat of research computation.

Medians and MAD labeled measured are observations; bracketed 95% intervals and ceilings are inferred. These are nominal 50% GPU-event-duty measurements, including inter-window idle, not sustained unpaced mining or wall-socket energy. Sensor-method disagreement is separate from the intervals.

## Whole-attempt gross GPU-board energy

| Variant | Condition | GPU event seconds measured | Complete attempts counted | Instant-power uJ/attempt: measured median / MAD [inferred 95% CI] | Energy-counter uJ/attempt: measured median / MAD [inferred 95% CI] | Average-power uJ/attempt: measured median / MAD [inferred 95% CI] |
|---|---|---:|---:|---:|---:|---:|
| lf2_warp_cublas_autotune | cold_start | 600.080 | 1,073,217,536 | 375.4950 / 0.9323 [375.1029, 375.8103] | 353.8183 / 1.3455 [352.9822, 354.8177] | 374.4649 / 0.9709 [373.5725, 375.0709] |
| lf2_warp_cublas_autotune | warm | 600.137 | 1,073,217,536 | 374.7380 / 1.7134 [373.2783, 375.6950] | 353.9030 / 1.2738 [353.2495, 354.1870] | 374.2419 / 0.9025 [373.8453, 375.1049] |
| lf2_register_cutlass256_q4 | cold_start | 600.186 | 1,328,545,792 | 300.1408 / 9.7920 [298.1581, 308.0879] | 286.9973 / 0.6751 [286.6164, 287.5872] | 303.8105 / 0.9644 [303.1957, 304.6041] |
| lf2_register_cutlass256_q4 | warm | 600.007 | 1,327,497,216 | 303.9796 / 10.9571 [299.5306, 308.8762] | 287.2670 / 0.9428 [286.6402, 287.6987] | 304.0257 / 0.8759 [303.7982, 304.2344] |
| c20_two_stage_cutlass256_q4 | cold_start | 600.095 | 1,623,719,936 | 268.2745 / 1.9795 [266.9527, 269.1006] | 252.1208 / 0.8075 [251.4095, 252.4109] | 267.8868 / 0.7015 [267.3196, 268.3528] |
| c20_two_stage_cutlass256_q4 | warm | 600.123 | 1,621,622,784 | 268.0892 / 1.4679 [267.1569, 268.7727] | 252.4555 / 0.7067 [252.1859, 252.7415] | 268.5868 / 0.7446 [268.0320, 269.0092] |
| c20_two_stage_cutlass256_fused_fold | cold_start | 600.070 | 1,584,922,624 | 264.0039 / 1.9203 [262.9042, 264.9020] | 248.7820 / 0.6657 [248.2322, 249.2104] | 263.4846 / 0.7625 [263.0033, 264.1488] |
| c20_two_stage_cutlass256_fused_fold | warm | 600.104 | 1,583,874,048 | 265.0175 / 1.8587 [263.3982, 265.9176] | 249.2051 / 0.7492 [248.6176, 249.5687] | 263.9454 / 0.7344 [263.2836, 264.4584] |
| INVALID lf2_register_cutlass256_fused_fold | cold_start | 600.235 | 1,286,602,752 | 295.8143 / 23.4027 [282.9538, 307.6134] | 279.5494 / 1.0151 [278.7083, 280.1274] | 295.0609 / 1.8298 [293.8584, 295.7457] |
| INVALID lf2_register_cutlass256_fused_fold | warm | 600.057 | 1,285,029,888 | 290.4179 / 30.8973 [280.0757, 309.5447] | 280.2337 / 0.5993 [279.7984, 280.3944] | 295.4877 / 1.6676 [294.4693, 296.6814] |

## Device-stage timing and time ceilings

Each block summarizes the last graph in each 64-replay window. Times are measured milliseconds per configured batch of 8192, not per single attempt. Composite shares are measured; ceilings assume the whole composite stage becomes free. No energy share is inferred from these time shares.

| Variant / condition | Binding+expansion ms measured median / MAD [inferred CI] | GEMM+epilogue ms measured median / MAD [inferred CI] | Separate fold ms measured median / MAD [inferred CI] | Final ms measured median / MAD [inferred CI] | Composite percent measured median / MAD [inferred CI] | Composite Amdahl ceiling inferred |
|---|---:|---:|---:|---:|---:|---:|
| lf2_warp_cublas_autotune / cold_start | 0.8424 / 0.0000 [0.8424, 0.8424] | 2.9102 / 0.0026 [2.9072, 2.9112] | 0.6779 / 0.0000 [0.6779, 0.6779] | 0.1556 / 0.0000 [0.1556, 0.1556] | 63.4504 / 0.0305 [63.4424, 63.4757] | 2.7360x [2.7354, 2.7379] |
| lf2_warp_cublas_autotune / warm | 0.8434 / 0.0000 [0.8424, 0.8434] | 2.9076 / 0.0026 [2.9061, 2.9102] | 0.6779 / 0.0000 [0.6779, 0.6779] | 0.1556 / 0.0000 [0.1556, 0.1556] | 63.4380 / 0.0162 [63.4277, 63.4509] | 2.7351x [2.7343, 2.7360] |
| lf2_register_cutlass256_q4 / cold_start | 0.7902 / 0.0000 [0.7902, 0.7902] | 2.6675 / 0.0020 [2.6675, 2.6696] | 0.0901 / 0.0000 [0.0901, 0.0901] | 0.1536 / 0.0000 [0.1536, 0.1536] | 72.0522 / 0.0086 [72.0433, 72.0555] | 3.5781x [3.5770, 3.5785] |
| lf2_register_cutlass256_q4 / warm | 0.7902 / 0.0000 [0.7902, 0.7902] | 2.6676 / 0.0020 [2.6675, 2.6696] | 0.0901 / 0.0000 [0.0901, 0.0901] | 0.1536 / 0.0000 [0.1536, 0.1536] | 72.0522 / 0.0086 [72.0441, 72.0588] | 3.5781x [3.5771, 3.5789] |
| c20_two_stage_cutlass256_q4 / cold_start | 0.0529 / 0.0000 [0.0529, 0.0529] | 2.8181 / 0.0033 [2.8140, 2.8201] | 0.0922 / 0.0000 [0.0922, 0.0922] | 0.1536 / 0.0000 [0.1536, 0.1536] | 90.4457 / 0.0064 [90.4393, 90.4499] | 10.4665x [10.4595, 10.4711] |
| c20_two_stage_cutlass256_q4 / warm | 0.0529 / 0.0000 [0.0529, 0.0529] | 2.8211 / 0.0041 [2.8183, 2.8273] | 0.0922 / 0.0000 [0.0922, 0.0922] | 0.1536 / 0.0000 [0.1536, 0.1536] | 90.4559 / 0.0089 [90.4474, 90.4648] | 10.4776x [10.4683, 10.4875] |
| c20_two_stage_cutlass256_fused_fold / cold_start | 0.0508 / 0.0000 [0.0508, 0.0508] | 2.9194 / 0.0020 [2.9194, 2.9215] | 0.0004 / 0.0000 [0.0004, 0.0004] | 0.1532 / 0.0000 [0.1532, 0.1532] | 93.4520 / 0.0043 [93.4482, 93.4558] | 15.2718x [15.2630, 15.2807] |
| c20_two_stage_cutlass256_fused_fold / warm | 0.0508 / 0.0000 [0.0508, 0.0508] | 2.9215 / 0.0020 [2.9195, 2.9235] | 0.0004 / 0.0000 [0.0004, 0.0004] | 0.1532 / 0.0000 [0.1532, 0.1532] | 93.4563 / 0.0043 [93.4520, 93.4596] | 15.2819x [15.2719, 15.2896] |
| INVALID lf2_register_cutlass256_fused_fold / cold_start | 0.7892 / 0.0000 [0.7892, 0.7892] | 2.8805 / 0.0041 [2.8764, 2.8836] | 0.0004 / 0.0000 [0.0004, 0.0004] | 0.1553 / 0.0000 [0.1553, 0.1553] | 75.3097 / 0.0183 [75.2881, 75.3278] | 4.0502x [4.0466, 4.0531] |
| INVALID lf2_register_cutlass256_fused_fold / warm | 0.7892 / 0.0000 [0.7892, 0.7892] | 2.8826 / 0.0020 [2.8805, 2.8846] | 0.0004 / 0.0000 [0.0004, 0.0004] | 0.1553 / 0.0000 [0.1553, 0.1553] | 75.3213 / 0.0118 [75.3146, 75.3330] | 4.0521x [4.0510, 4.0540] |

## Throughput and telemetry

Rates below are measured. Event-window rate includes the device window; paced elapsed rate includes inter-window host idle within measured blocks. Neither is a full miner with parent turnover/networking. Power limit remained 575 W measured for every variant.

| Variant / condition | Event-window attempts/s measured median / MAD [inferred CI] | Paced elapsed attempts/s measured median / MAD [inferred CI] | Temperature C measured range | SM MHz measured range | Memory MHz measured range | Largest sampling gap seconds measured | Instant minus counter energy percent measured median / MAD [inferred CI] | Average minus counter energy percent measured median / MAD [inferred CI] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| lf2_warp_cublas_autotune / cold_start | 1787453.0765 / 935.4022 [1786947.6550, 1788625.7106] | 893247.8279 / 468.5924 [892970.7089, 893599.6427] | [36, 67] | [2400, 2925] | [13801, 13801] | 0.345686 | 6.0468 / 0.4591 [5.8899, 6.2036] | 5.8474 / 0.3245 [5.5253, 5.9881] |
| lf2_warp_cublas_autotune / warm | 1788575.0376 / 867.3889 [1787306.6672, 1789199.8023] | 893727.5803 / 501.6920 [893187.5996, 894138.3866] | [55, 67] | [2640, 2917] | [13801, 13801] | 0.345686 | 5.9406 / 0.5027 [5.6655, 6.3977] | 5.7423 / 0.3774 [5.6263, 6.0598] |
| lf2_register_cutlass256_q4 / cold_start | 2212734.3805 / 841.1456 [2212085.0261, 2213785.0330] | 1105693.3504 / 485.9114 [1105254.7016, 1106254.5358] | [41, 68] | [2400, 2910] | [13801, 13801] | 0.362896 | 4.8264 / 3.5836 [4.3513, 6.8064] | 5.8846 / 0.5116 [5.5399, 6.3235] |
| lf2_register_cutlass256_q4 / warm | 2212551.3405 / 615.7210 [2212176.0194, 2213094.3062] | 1105558.6702 / 244.2747 [1105186.7948, 1105623.4986] | [55, 69] | [2700, 2902] | [13801, 13801] | 0.362896 | 5.9437 / 3.7277 [4.0725, 7.3803] | 5.8924 / 0.3200 [5.7306, 6.0222] |
| c20_two_stage_cutlass256_q4 / cold_start | 2705018.2565 / 1746.7323 [2703226.1039, 2706387.4051] | 1351123.1987 / 889.5933 [1350312.4775, 1351822.2930] | [41, 70] | [2400, 2857] | [13801, 13801] | 0.330804 | 6.4306 / 0.7690 [5.9280, 6.6407] | 6.2762 / 0.4262 [6.0717, 6.5916] |
| c20_two_stage_cutlass256_q4 / warm | 2702663.9250 / 2480.0762 [2699213.7344, 2704705.8242] | 1350157.4341 / 1230.8708 [1348367.8939, 1351033.7267] | [57, 71] | [2617, 2857] | [13801, 13801] | 0.330804 | 6.1971 / 0.6891 [5.9073, 6.5558] | 6.4095 / 0.3022 [6.2310, 6.4933] |
| c20_two_stage_cutlass256_fused_fold / cold_start | 2641081.0297 / 1412.1054 [2639528.0571, 2641961.8053] | 1318948.6604 / 722.3202 [1318447.4947, 1319890.4515] | [41, 70] | [2400, 2887] | [13801, 13801] | 0.571710 | 6.0461 / 0.5602 [5.8395, 6.4429] | 5.9117 / 0.3567 [5.7438, 6.2764] |
| c20_two_stage_cutlass256_fused_fold / warm | 2639054.3238 / 1548.6065 [2637672.6888, 2640366.3090] | 1318307.9802 / 689.4035 [1317644.5223, 1318989.5860] | [57, 70] | [2677, 2865] | [13801, 13801] | 0.571710 | 6.3954 / 0.9697 [5.6237, 6.7675] | 5.9521 / 0.3741 [5.6361, 6.0737] |
| INVALID lf2_register_cutlass256_fused_fold / cold_start | 2142749.5532 / 1744.0501 [2141280.7275, 2144636.5433] | 1070214.1747 / 1583.4602 [1068848.0124, 1071806.1177] | [47, 68] | [2400, 2917] | [13801, 13801] | 9.370326 | 6.2082 / 7.7779 [1.7662, 10.4740] | 5.4506 / 0.8033 [4.7112, 5.7988] |
| INVALID lf2_register_cutlass256_fused_fold / warm | 2141812.5357 / 1091.7424 [2140542.6582, 2142635.3694] | 1069876.3130 / 563.0136 [1069444.8104, 1070454.1873] | [55, 68] | [2700, 2910] | [13801, 13801] | 9.370326 | 3.3558 / 10.7293 [-0.0358, 10.1718] | 5.4785 / 0.6432 [5.0872, 5.7398] |

## Separate instrumented matrix-loop observer

Thirty measured paired trials per mapping, 491,520 measured full-fold checks. Cycle spans are measured warp-zero observations. Mma-attributed device wall milliseconds are **inferred**, include loads/synchronization and instrumentation effects, and are not pure unperturbed GEMM time.

| Passes per CTA configured | Instrumented kernel ms measured median / MAD [inferred CI] | Mma cycles per pass measured median / MAD [inferred CI] | Mma cycle fraction measured median / MAD [inferred CI] | Mma-attributed kernel ms inferred median / MAD [inferred CI] |
|---:|---:|---:|---:|---:|
| 1 | 2.633984 / 0.003632 [2.631552, 2.637408] | 134344.500000 / 6.000000 [134341.500000, 134348.500000] | 0.950731 / 0.000008 [0.950727, 0.950733] | 2.504241 / 0.003446 [2.502033, 2.507533] |
| 8 | 2.862384 / 0.003440 [2.861456, 2.865680] | 134406.500000 / 9.000000 [134404.000000, 134416.500000] | 0.986916 / 0.000007 [0.986913, 0.986923] | 2.824890 / 0.003401 [2.824020, 2.828195] |

Paired measured fused/control instrumented-kernel ratio: 1.086798 / 0.000847 [1.086014, 1.087415]. Paired measured per-pass Mma-cycle ratio: 1.000473 / 0.000108 [1.000406, 1.000558].

Compiler resource observations: production fused kernel 246 measured registers/thread; instrumented eight-pass kernel 252; instrumented one-pass control 224. All three report zero static stack/local spill bytes. Static shared-memory metadata does not include dynamic shared allocation. These observations do not prove the cause of a wall-time difference.

The optional isolated C20 stage pair did not complete within the safety/deadline conditions. No stage-only energy result is claimed. Bare unperturbed MMA energy remains unmeasured.
