# Nine direct qualification answers

Experiment tags remain unchanged. No consensus freeze, activation or release. Measured observations and inferred calculations are distinguished below.

## 1. Fused C20 matrix share and Amdahl ceiling

Warm fused C20 GEMM-plus-epilogue share: **93.4563% measured median**, MAD 0.0043 percentage points; **[93.4520, 93.4596]% inferred 95% median CI**. The measured composite median is 2.921504 ms per configured 8192-attempt batch. Removing that entire stage gives an **inferred 15.2819x time ceiling**, with no conversion, loading, communication or correction overhead.

Pure unperturbed GEMM wall time was **not independently isolated**. The separate instrumented Mma observer includes operand loads and synchronization; its wall attribution is inferred. Its measured paired fused/control kernel ratio and per-pass cycle ratio are retained in the tables. Do not call that observer bare arithmetic time or energy. Both cold-start and warm production data appear in [the full tables](measurement-tables.md).

For scale, the separate observer's eight-pass Mma-attributed kernel time is **2.824890 ms inferred median**, MAD 0.003401 ms, with **[2.824020, 2.828195] ms inferred 95% median CI** per configured 8192-attempt batch. This derives from instrumented cycle fractions, includes loads/synchronization and is not the production pure-GEMM time.

## 2. Energy per correct attempt and intervals

The following are **measured gross paced GPU-board medians**, including inter-window idle. Bracketed intervals are **inferred 95% conditional median CIs** from measured blocks. They exclude sensor bias. These are not sustained unpaced or wall-socket results.

| Variant | Condition | Instant-power uJ/complete attempt measured median [inferred CI] | Continuous energy-counter uJ/complete attempt measured median [inferred CI] |
|---|---|---:|---:|
| lf2_warp_cublas_autotune | cold_start | 375.4950 [375.1029, 375.8103] | 353.8183 [352.9822, 354.8177] |
| lf2_warp_cublas_autotune | warm | 374.7380 [373.2783, 375.6950] | 353.9030 [353.2495, 354.1870] |
| lf2_register_cutlass256_q4 | cold_start | 300.1408 [298.1581, 308.0879] | 286.9973 [286.6164, 287.5872] |
| lf2_register_cutlass256_q4 | warm | 303.9796 [299.5306, 308.8762] | 287.2670 [286.6402, 287.6987] |
| c20_two_stage_cutlass256_q4 | cold_start | 268.2745 [266.9527, 269.1006] | 252.1208 [251.4095, 252.4109] |
| c20_two_stage_cutlass256_q4 | warm | 268.0892 [267.1569, 268.7727] | 252.4555 [252.1859, 252.7415] |
| c20_two_stage_cutlass256_fused_fold | cold_start | 264.0039 [262.9042, 264.9020] | 248.7820 [248.2322, 249.2104] |
| c20_two_stage_cutlass256_fused_fold | warm | 265.0175 [263.3982, 265.9176] | 249.2051 [248.6176, 249.5687] |
| lf2_register_cutlass256_fused_fold | cold_start | 295.8143 [282.9538, 307.6134] | 279.5494 [278.7083, 280.1274] |
| lf2_register_cutlass256_fused_fold | warm | 290.4179 [280.0757, 309.5447] | 280.2337 [279.7984, 280.3944] |

The full tables also retain MAD, one-second-average power integration, measured sensor-method spread, clocks, temperatures, power limits and sampling gaps. Method disagreement remains an unresolved systematic limitation; no favorable method is selected. Optional isolated matrix-stage measurements, if completed, are explicitly composite-stage microbenchmarks, not bare MMA or complete-attempt energy.

## 3. Four implementations and vector counts

**Yes: 560/560 measured canonical cases agree in C, CUDA, Python and Rust on h, full 2048-byte F and D.** CUDA checks both packed and fused paths, for 1120 measured canonical checks. The measured random full-fold GPU/C replay is 1,048,576/1,048,576 with zero skips and mismatches; its complete distribution is in the [conformance checkpoint](../lf3-c20-2026-10-30/README.md). CUDA receives its banks from C, so this is not four independent bank derivations. A separate instrumented control initially mismatched because of a layout bug; that failed run was discarded, and its corrected replacement passed 491,520 measured full-fold checks.

## 4. Shortcuts

**No demonstrated work-avoiding energy shortcut was found in the tested corpus.** Finite omission/noise tests do not establish an optimal-work lower bound. General key/vector/parent grinding and mapped sparse execution remain open economic claims. Exact packing/fusion is an implementation improvement; exact narrower arithmetic is a hardware-economics finding under the clarified stop rule.

## 5. ASIC cost ratio

The **inferred** mod-8192/full-int32 NAND-equivalent datapath ratio is **0.5403**, with assumed product-cost sensitivity **0.4722-0.5929**. The central inferred 13/20-bit ratio is **0.7614**; 20 signed bits cover the conservative full sum domain. These are explicit product/adder/register proxies, not synthesis, measured ASIC energy or whole-machine ratios. Memory, SHAKE, I/O, routing and loading are excluded.

## 6. CPU verification, bank time and header-sync days

Measured shared-EPYC C medians: bank **0.977996 s**, cached hash **0.013318 s**, cold hash **0.975660 s**. Two workers inside one parent: bank **0.496127 s**, dependent-parent cold hash **0.522835 s**. Measured 128 MiB host upload median: **7.359809 ms**.
Measured independent one-thread Python/BLAS medians: bank **0.504270 s**, cached hash **0.018725 s**, cold hash **0.521273 s**.

All following days are **inferred** core-hash costs for a configured 365-day chain-year, including a bank for every header. These exclude full-node work.

| Configured block seconds | C one-core elapsed days inferred | C two-core serial-dependent elapsed days inferred | Two-core CPU core-days inferred |
|---:|---:|---:|---:|
| 10 | 35.61160 | 19.08349 | 37.42677 |
| 30 | 11.87053 | 6.36116 | 12.47559 |
| 60 | 5.93527 | 3.18058 | 6.23780 |
| 150 | 2.37411 | 1.27223 | 2.49512 |

[CPU tables](../lf3-c20-economics-2026-10-30/economics-tables.md) provide MAD, inferred intervals, parent-turnover fractions, BLAS projections and photonic loading requirements. This is not dedicated modest/low-power hardware qualification. Existing LF2 prepared-cache misses avoid bank derivation; C20 network-facing admission/reject rules remain unintegrated.

## 7. CUDA stall cause

**Unresolved on Windows.** The owner-reported display-loss incident ended local research authorization, and no local retry was made. The measured Linux remote initialization process completed in 0.949595 s; that whole-process observation does not diagnose or rule out the Windows stall/crash. The separate remote NVML sampling delay also remains unexplained.

## 8. Recommendation and blockers

**REVISE; withhold the conditional candidate freeze.** Correctness evidence is strong within the tested construction. Sustained-power/telemetry reliability and sensor metrology remain provisional; pure unperturbed arithmetic attribution, dedicated modest CPU evidence and C20 hostile-admission integration remain incomplete. Grinding/sparse economics, mapped modular ASIC costs and full-size exact-fold photonic energy/loading need further evidence. The [decision memo](decision-memo.md) distinguishes these findings from the team's intentionally OPEN integration choices: header serialization/length, difficulty/work score, genesis difficulty, timestamps, block time and activation. No new tags, normative v0.5.0 package, kernel publication or reference-miner integration is claimed.

## 9. Approximation criterion

**No tested work-avoiding error model comes out ahead under its stated energy model.** Measured pooled exact-fold survival was 0.929199 for configured +/-1 errors on 0.1% of sums, 0.516602 at 1%, 0.047363 at 5%, and 0.051758 for rounded Gaussian sigma 0.25. Injecting errors after exact work has inferred optimistic energy ratio 1, so it gains nothing. Dropping small nonzero products had zero measured full-fold successes out of 2048 per setting, even under a favorable inferred MAC-proportional energy model.

Physical analog, reduced-precision and narrow-ASIC energy was not measured. A future device can still win if **E_method/E_exact < P(exact fold)**; this experiment does not rule that out. Exact 13-bit wrapping is not an approximate/work-avoiding failure. The [complete approximation and photonic-tolerance table](../lf3-c20-security-2026-10-30/approximation-tables.md) retains every setting, nonzero-parent results, confidence intervals and heuristic deviations.
