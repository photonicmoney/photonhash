# Fixed secondary measurements, declared before samples

These execute only after all five unpaced full-attempt confirmations qualify.
No concurrent GPU workload. All remote only, same pod stop deadline and 80 C
guard. A real mismatch sets STOP immediately; no replacement result is selected.

Matrix-stage microbenchmark: all five unchanged configurations, batch 8192,
header 184, fixed previously validated vectors, 30 GPU-event seconds each,
five-second blocks, no pacing. This is exploratory isolated-stage energy, not
600-second confirmation or complete-attempt energy. Packed/int32 stages exclude
the separate fold; fused stages necessarily include quantization and XOR fold.
None isolates pure GEMM arithmetic or assigns GPU board energy to tensor cores.
Use the old stage source with only the host sleep removed, a new filename and
binary, the same pinned CUTLASS revision and compiler flags. Keep old binary and
source intact. Before and after each block check all 8192 folds against int32
and one complete C h/fold/digest, as in the existing stage harness.

CPU scaling: a separate server CPU cohort after GPU energy work. Record CPU
model, quota, allowed affinity and physical topology. Select the first eight
distinct allowed physical cores; refuse this measurement if unavailable. Fixed
order portable, OpenSSL 1, 2, 4, 8 workers; 31 serial parent-dependent cold
verifications and 64 cached samples per variant. Retain audit checksums and
allocation. Compare every optimized cold fold/digest with the portable chain.
This is not modest-machine, low-power or CPU-energy qualification. Preserve
serial parent dependencies; parallelize only the eight streams within a bank.
Set OpenMP dynamic teams off, spread workers over the selected physical cores,
and park waiting workers (`OMP_WAIT_POLICY=PASSIVE`, `GOMP_SPINCOUNT=0`). Verify
actual worker placement with a separate probe before measuring. These choices
are fixed before this cohort's samples, not selected from benchmark results.

Parent transfer: same existing pageable 128 MiB/eight-copy upload executable,
31 samples, CUDA context startup excluded. Combining its median with bank
medians is an inferred turnover projection, not a directly timed production
miner parent transition. No GPU-native bank derivation claim.

Use within-run circular moving-block bootstrap, span three, 4000 resamples for
energy and 2000 for CPU; report median, MAD and 95% inferred intervals. Independent
sensor bias, physical power and host-population uncertainty remain outside them.
Any insufficient deadline, unavailable dependency, failed process or guard abort
is retained as ineligible rather than shortening confirmation or relaxing guards.
