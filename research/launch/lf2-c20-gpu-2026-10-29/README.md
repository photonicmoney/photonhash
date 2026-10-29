# LF2 packing / C20: published synthetic evidence

29 October 2026. This directory supports the
[comparison report](../../../docs/lf2-gpu-comparison-2026-10-29.md) and
[ChaCha20 experiment](../../../docs/lf3-k8-c20-experiment-1.md).
It contains public synthetic inputs and measurement records, with no wallets,
live-chain data, credentials, private wrapper configuration or host paths.

## Records

Eight completed runs from the final benchmark binary are published as JSONL:

| File | Purpose | Paired rounds |
| --- | --- | ---: |
| [gpu-comparison-b4096-h184-p0.jsonl](gpu-comparison-b4096-h184-p0.jsonl) | Batch 4096, 184-byte header, zero parent | 7 |
| [gpu-comparison-b8192-h80-p0.jsonl](gpu-comparison-b8192-h80-p0.jsonl) | Batch 8192, 80-byte header, zero parent | 3 |
| [gpu-comparison-b8192-h80-p1.jsonl](gpu-comparison-b8192-h80-p1.jsonl) | Batch 8192, 80-byte header, all-FF parent | 3 |
| [gpu-comparison-b8192-h184-p0.jsonl](gpu-comparison-b8192-h184-p0.jsonl) | Batch 8192, 184-byte header, zero parent | 3 |
| [gpu-comparison-b8192-h184-p1.jsonl](gpu-comparison-b8192-h184-p1.jsonl) | Batch 8192, 184-byte header, all-FF parent | 3 |
| [gpu-boundary-empty-p0.jsonl](gpu-boundary-empty-p0.jsonl) | Batch 128, empty header, zero parent; frozen LF2 anchor | 0 |
| [gpu-boundary-one-p1.jsonl](gpu-boundary-one-p1.jsonl) | Batch 128, one-byte header, all-FF parent; frozen LF2 anchor | 0 |
| [gpu-boundary-long-p0.jsonl](gpu-boundary-long-p0.jsonl) | Batch 128, 4096-byte header, zero parent | 0 |

Every run contains all 24 equally validated variants. Five timing conditions
provide 456 measured graph samples; eight runs provide 312 variant validation
records. Expected first-nonce CPU traces are reused across variants. This is
not 312 independent full CPU matrix evaluations. Timed cases validate before
and after collection; the boundary cases perform correctness checks only.

[manifest.json](manifest.json) records published/original log SHA-256 values,
the tested binary/source hashes and each run's arguments. The only log
conversion is LF line endings; every original JSON record is retained. The
implementation source checkpoint is local `441e4f7`, not a published kernel
release. The final helper differs from the tested helper only by removal of
an extra trailing blank line. These records permit analysis of the reported
measurements; the GPU implementation cannot be rebuilt from this update.

[attempt-ledger.json](attempt-ledger.json) accounts for all 15 GPU attempts,
including earlier pilots and incomplete trials. Those entries are excluded
from the headline comparison. The ledger retains the allocation failure,
event-window threshold aborts and final initialization stop. Original private
wrapper metadata and failed-process logs remain local; this is their selected
public measurement/status ledger.

## Recompute the analysis without GPU work

On a shell that expands wildcards, from the repository root:

```sh
python3 tools/analyze_lf2_gpu.py \
  research/launch/lf2-c20-gpu-2026-10-29/*.jsonl \
  --output /tmp/lf2-c20-summary.json
node tools/check-lf3-c20-vector.mjs
```

On other shells, pass the eight explicit JSONL filenames to the Python tool.
Run without Python `-O`; the analyzer rejects that mode. Neither command
launches a GPU or performs full matrix evaluation.

[summary.json](summary.json) contains the generated per-variant medians, total
time MAD/extrema, paired ratios, selected paths, matched epilogue controls and
fixture anchors. The analyzer checks variant/round/validation coverage, stage
sums and published fixture/bank values. It selects the fastest tested int32
LF2, fastest packed LF2 and fastest C20 per condition. Selection and comparison
use the same small samples. No outlier filtering or independent confidence
claim is applied. Stage medians need not sum to the median total.

The [C20 fixture](../lf3-k8-c20-experiment-1-vector.json) was generated before
GPU timing. Its CPU-only generation flags remain historical. The checker
recomputes binding, all expansion bytes and final hashing using Node/OpenSSL,
including the RFC 8439 primitive check. It does not recompute its full fold
from matrix products or provide an independent composite security review.

## Boundaries of the measurements

- Shared RTX 5090 / Windows WDDM, ambient clocks, serial CUDA graphs, common
  primers, randomized paired order, 75 ms pauses and capped host CPU.
- Device stage timings exclude parent setup, copies, host scheduling,
  validation, warmup, primers and pauses. They are not sustained full-miner
  throughput or parent-transition latency.
- GEMM-plus-epilogue includes quantization and output stores. Matrix-only
  time/energy and optical advantage were not measured.
- The eight accepted runs contain 23.806 seconds of event windows. All
  attempts contain 44.371 seconds observed and 54.371 seconds conservatively
  reserved. Event windows can include stalls; they are not hardware-busy time.
- The extra LF2 binding-rate-boundary run stalled before its first metadata
  record. Its benchmark child was stopped after 94.6 wall seconds / 87.95
  CPU-seconds; cause remains unresolved. Further GPU work ended. Exact
  rate-boundary checks and preselected-choice timing confirmation remain
  incomplete. A new 15-second startup watchdog was tested on tiny CPU-only
  children, without a later GPU trial.
- Before/after temperature snapshots, power snapshots and private job receipts
  are not energy attribution. No public network or real-money readiness
  conclusion follows from this data.
