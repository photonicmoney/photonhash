# CPU and admission measurements

All numeric observations below are **measured** on the recorded CPU-only cloud rental. Projections and bootstrap intervals are **inferred**. Two workers share a physical core; this is not a low-power laptop qualification.

| Implementation | Bank s median / MAD [inferred 95% CI] | Cached verify s median | Cold verify s median |
|---|---:|---:|---:|
| portable | 0.635505 / 0.004935 [0.633832, 0.640071] | 0.015347 | 0.651375 |
| OpenSSL-1-worker | 0.283790 / 0.002356 [0.280637, 0.285682] | 0.015879 | 0.299594 |
| OpenSSL-2-workers | 0.258326 / 0.001422 [0.257292, 0.260097] | 0.015764 | 0.274384 |

Every bank includes 64 MiB of SHAKE matrix streams, their retained audit checksums, and expansion into 128 MiB of signed coefficients. The checksum calculation also reads/hashes the full 64 MiB. Parent-pass tags and matrix seeds are unchanged.

| Implementation | 10 s blocks | 30 s blocks | 60 s blocks | 150 s blocks |
|---|---:|---:|---:|---:|
| portable | 23.7752 | 7.9251 | 3.9625 | 1.5850 |
| OpenSSL-1-worker | 10.9352 | 3.6451 | 1.8225 | 0.7290 |
| OpenSSL-2-workers | 10.0150 | 3.3383 | 1.6692 | 0.6677 |

Entries are **inferred elapsed days per chain-year**, using each measured median cold verify time and a 365-day year. Serial parent dependence is preserved. Excludes networking, storage, signatures, chain state, forks and scheduling. CPU-work projections and all intervals are in `evidence/cpu-statistics.json`.

The benchmark uses 31 successive parent-dependent cold steps and 64 cached samples per implementation. Implementations ran in the predeclared fixed order: portable, OpenSSL single worker, OpenSSL two workers. Fixed order, shared hardware, one session and no external frequency control limit causal claims. CIs describe within-run variation only.

The two OpenSSL variants matched the portable chain digest and **all 2048 fold bytes** at each of their 31 steps (62 measured comparisons), in addition to 560 canonical vectors and eight complete bank comparisons.
