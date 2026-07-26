# Changelog

## Unreleased

## v0.2.3-falsified — 2026-07-26

- Added an exact end-to-end CUDA baseline with on-device SHAKE, signed-vector
  expansion, cuBLAS INT8-by-INT8-to-INT32 GEMM, requantization, final hashing,
  target comparison, differential validation, stage timing, and NVML energy
  measurement.
- Optimized the electronic path with register-resident Keccak, autotuned exact
  GEMM, and configurable multi-stream overlap.
- Completed 75 sustained RTX 5090 samples across three batch sizes and five
  parent matrices. GEMM remained at 11.06-12.21% of sequential device time;
  the best mean overlapped result was 33.43 million attempts/s.
- Added a 1,000-parent matrix corpus, deep SVD analysis, and low-rank,
  partial-row, and column-skipping approximation experiments.
- Marked the active n=1024 profile's R3 target falsified and recorded a
  non-activation decision for Laser consensus.
- Replaced the subtraction-derived matrix-share estimate with direct,
  allocation-free stage timing over batches of distinct nonces.
- Added `ph_verify_with_matrix` for callers that cache a parent-derived matrix.
- Expanded self-tests for target boundaries, little-endian ordering, empty
  headers, the maximum nonce, cached verification, and malformed arguments.
- Made optimized exact GPU batching and full-system photonic accounting an
  explicit evidence requirement rather than assuming substrate symmetry.

## v0.2.2-experimental — 2026-07-25

- Prepared the reference implementation as a standalone public-review
  repository.
- Declared the active matrix dimension fixed at 1024; the growth schedule is
  retained only as deferred research.
- Aligned implementation, vector, and review-document version labels.
- Added checked allocation arithmetic and public-API argument validation.
- Added standalone strict-warning builds, vector reproduction, sanitizers, and
  Linux, macOS, and Windows CI.
- Reframed unproven hardware and security properties as research hypotheses.
- Removed an unattributed external-review claim; no published independent
  audit is claimed by this release.

## v0.2.1

- Rejected dimensions below 1024, fixing a shift-underflow edge.
- Documented the maximum proposed research dimension.

## v0.2.0

- Retuned requantization after the v0.1 output distribution collapsed into too
  few buckets.
- Replaced the original analog-exactness model with a boundary-flagged hybrid
  model.
