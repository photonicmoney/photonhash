# CPU and loading tables

All timing medians and MAD below are **measured**; bracketed 95% median intervals and projections are **inferred**. Units are seconds unless stated. These are conditional shared-host observations, not hardware or latency bounds.

| CPU path | Samples measured | Measured median / MAD [inferred 95% CI] |
|---|---:|---:|
| portable_C: bank | 31 | 0.977996 / 0.007353 [0.973958, 0.986046] |
| portable_C: cached_verify | 64 | 0.013318 / 0.000152 [0.013233, 0.013417] |
| portable_C: cold_verify | 15 | 0.975660 / 0.012008 [0.963652, 0.982059] |
| independent_BLAS: bank | 15 | 0.504270 / 0.005745 [0.499595, 0.533148] |
| independent_BLAS: cached_verify | 64 | 0.018725 / 0.000173 [0.018659, 0.018896] |
| independent_BLAS: cold_verify | 15 | 0.521273 / 0.001657 [0.520185, 0.522316] |
| Two-worker C within current parent: bank_wall_s_measured | 31 | 0.496127 / 0.005884 [0.491408, 0.499493] |
| Two-worker C within current parent: cold_verify_wall_s_measured | 31 | 0.522835 / 0.005685 [0.517428, 0.528520] |
| Two-worker C within current parent: process_cpu_s_measured | 31 | 1.025391 / 0.009431 [1.015960, 1.032870] |
| 128 MiB parent upload, host wall **milliseconds** | 31 | 7.359809 / 0.061571 [7.316248, 7.563511] |

Bank derivation and cached-hash medians are separate measurements; do not add them and relabel the result a measured cold median. The two-worker fixture preserves serial parent dependencies; it is not the earlier independent-parent throughput test.

## One chain-year of core header hash evaluation

All days in this table are **inferred**, from cold hash evaluation and a configured 365-day year. Confidence intervals do not include host variability, network, disk or complete node verification.

| Configured block seconds | Headers/year inferred | C one-core elapsed days inferred [95% CI] | Python/BLAS one-core elapsed days inferred | C two-core dependent-parent elapsed days inferred [95% CI] | C two-core CPU core-days inferred |
|---:|---:|---:|---:|---:|---:|
| 10 | 3,153,600 | 35.61160 [35.17329, 35.84514] | 19.02646 | 19.08349 [18.88614, 19.29099] | 37.42677 |
| 30 | 1,051,200 | 11.87053 [11.72443, 11.94838] | 6.34215 | 6.36116 [6.29538, 6.43033] | 12.47559 |
| 60 | 525,600 | 5.93527 [5.86222, 5.97419] | 3.17108 | 3.18058 [3.14769, 3.21516] | 6.23780 |
| 150 | 210,240 | 2.37411 [2.34489, 2.38968] | 1.26843 | 1.27223 [1.25908, 1.28607] | 2.49512 |

## Miner parent turnover

Bank-plus-upload times and percentages are **inferred sums/projections of separately measured medians**. Host bank derivation and initialized-context upload are serialized in this calculation.

| CPU bank path | Bank plus upload seconds inferred | Fraction of 10 / 30 / 60 / 150 second blocks inferred |
|---|---:|---:|
| portable_C_one_core | 0.985356 | 9.8536% / 3.2845% / 1.6423% / 0.6569% |
| portable_C_two_core | 0.503487 | 5.0349% / 1.6783% / 0.8391% / 0.3357% |
| independent_BLAS_one_core | 0.511630 | 5.1163% / 1.7054% / 0.8527% / 0.3411% |

## Full-bank photonic loading requirements

These are **inferred minimum logical throughput requirements**, not measured optical hardware. The configured 1% turnover allowance is illustrative, not a consensus decision. Physical signed representation, calibration, settling and repeated programming are additional.

| Configured block seconds | Logical weights/s if whole block spent loading, inferred | Logical weights/s for 1% turnover, inferred | Packed four-bit MB/s for 1% turnover, inferred | Full LF3 optical compatibility |
|---:|---:|---:|---:|---|
| 10 | 13,421,773 | 1,342,177,280 | 671.089 | OPEN |
| 30 | 4,473,924 | 447,392,427 | 223.696 | OPEN |
| 60 | 2,236,962 | 223,696,213 | 111.848 | OPEN |
| 150 | 894,785 | 89,478,485 | 44.739 | OPEN |
