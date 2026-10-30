# Approximation results: measured probabilities, inferred energy models

Configured sample: 1,024 nonces on each of two nonzero parents, zero skips. Each P column is measured; pooled Wilson intervals are inferred from those measured counts, conditional on these two parents. They do not cover arbitrary-parent variation or physical energy uncertainty.

| Error model | Measured P, parent 0 | Measured P, parent 1 | Measured pooled P [inferred 95% CI] | Inferred E/E_exact | Criterion |
|---|---:|---:|---:|---:|---|
| `pm1_rate_0.001` | 0.928711 | 0.929688 | 0.929199 [0.917268, 0.939523] | 1 | no gain under stated model |
| `pm1_rate_0.00164625805715` | 0.896484 | 0.903320 | 0.899902 [0.886146, 0.912162] | 1 | no gain under stated model |
| `pm1_rate_0.005` | 0.735352 | 0.716797 | 0.726074 [0.706350, 0.744952] | 1 | no gain under stated model |
| `pm1_rate_0.01` | 0.490234 | 0.542969 | 0.516602 [0.494948, 0.538193] | 1 | no gain under stated model |
| `pm1_rate_0.0108304246962` | 0.458984 | 0.505859 | 0.482422 [0.460834, 0.504076] | 1 | no gain under stated model |
| `pm1_rate_0.02` | 0.245117 | 0.287109 | 0.266113 [0.247425, 0.285678] | 1 | no gain under stated model |
| `pm1_rate_0.035977892078` | 0.109375 | 0.101562 | 0.105469 [0.092897, 0.119518] | 1 | no gain under stated model |
| `pm1_rate_0.05` | 0.032227 | 0.062500 | 0.047363 [0.038981, 0.057441] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_0.158851996408` | 0.882812 | 0.904297 | 0.893555 [0.879453, 0.906183] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_0.196222859239` | 0.493164 | 0.511719 | 0.502441 [0.480803, 0.524071] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_0.238415713889` | 0.115234 | 0.109375 | 0.112305 [0.099349, 0.126712] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_0.25` | 0.050781 | 0.052734 | 0.051758 [0.042975, 0.062219] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_0.5` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_1` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 1 | no gain under stated model |
| `gaussian_nearest_integer_sigma_2` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 1 | no gain under stated model |
| `gaussian_raw_floor_threshold_sigma_0.01` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 1 | no gain under stated model |
| `gaussian_raw_floor_threshold_sigma_0.25` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 1 | no gain under stated model |
| `truncate_final_sum_low_bits_1` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | 1 | no gain under stated model |
| `truncate_final_sum_low_bits_4` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | 1 | no gain under stated model |
| `truncate_final_sum_low_bits_8` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | 1 | no gain under stated model |
| `truncate_final_sum_low_bits_9` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | 1 | no gain under stated model |
| `truncate_final_sum_low_bits_10` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 1 | no gain under stated model |
| `drop_nonzero_products_abs_le_1` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 0.984358–0.984369 | no gain under stated model |
| `drop_nonzero_products_abs_le_2` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 0.953102–0.953117 | no gain under stated model |
| `drop_nonzero_products_abs_le_4` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | 0.874917–0.874957 | no gain under stated model |
| `fp16_round_each_64_terms` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | unmeasured | physical energy OPEN |
| `signed12_saturate_each_64_terms` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | unmeasured | physical energy OPEN |
| `signed13_saturate_each_64_terms` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | unmeasured | physical energy OPEN |
| `exact_signed_wrap_accumulator_12` | 0.000000 | 0.000000 | 0.000000 [0.000000, 0.001872] | unmeasured | physical energy OPEN |
| `exact_signed_wrap_accumulator_13` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | unmeasured | hardware economics; exact |
| `exact_signed_wrap_accumulator_16` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | unmeasured | hardware economics; exact |
| `exact_signed_wrap_accumulator_20` | 1.000000 | 1.000000 | 1.000000 [0.998128, 1.000000] | unmeasured | hardware economics; exact |

`E/E_exact = 1` models injection after the same exact work, optimistically ignoring injection overhead. It is not a measured analog energy ratio. Dropped-term ratios assume all energy scales with retained scalar MACs and free pruning. FP16/saturating accumulation and wrapping datapaths have no measured mapped-device energy.

For every method the physical break-even condition is E_method/E_exact < P(exact fold). Zero observed successes means an interval upper bound, not mathematical impossibility. No tested method demonstrates a physical energy advantage. A different physical method could win if its energy falls below its probability threshold.

Low-bit truncation here occurs AFTER computing the exact sum. Removing up to nine final low bits preserves q exactly but saves no work in this harness; discarding partial-product low bits is a different algorithm because carries matter. Wrapping accumulators of at least 13 bits preserve the required residue exactly and belong to hardware economics. FP16 rounding was applied after each exact 64-term chunk; it is not a test of FP16 multiplication with exact FP32 accumulation.

The exponential model is a small, approximately phase-independent error heuristic. It is not applicable to exact modular wrap, phase-correlated low-bit masking, or uncalibrated raw analog thresholds. Structured dropping/saturation values in the raw ledger are illustrative extrapolations, not validated bounds.

## Photonic tolerance

All threshold and sigma values below are inferred from the rounded-integer noise model, in integer dot-product-sum units. The confirmation P columns are measured at the stated settings. Target independence is assumed when interpreting fold survival as retained winning blocks. No optical hardware was tested.

| Inferred winning-block loss | Inferred ±1 error rate per sum | Measured P, parents 0 / 1 | Inferred rounded Gaussian sigma | Measured P, parents 0 / 1 |
|---:|---:|---:|---:|---:|
| 10% | 0.1646258% | 0.896484 / 0.903320 | 0.158851996 | 0.882812 / 0.904297 |
| 50% | 1.0830425% | 0.458984 / 0.505859 | 0.196222859 | 0.493164 / 0.511719 |
| 90% | 3.5977892% | 0.109375 / 0.101562 | 0.238415714 | 0.115234 / 0.109375 |

Calibration matters: nearest-integer recovery and a raw floor threshold at 512k are different error models. Uncalibrated raw-threshold Gaussian sigma 0.01 produced zero measured exact folds on either parent. Integer sums can lie exactly at a bin boundary; the rounded-noise tolerance cannot be applied to that hardware without a demonstrated decision calibration.
