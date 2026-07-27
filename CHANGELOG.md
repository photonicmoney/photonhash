# Changelog

## v0.4.0-shadow.1 — 2026-07-27

- Gave the frozen LF2-K8 construction a distinct non-consensus shadownet
  version without changing the archived v0.2 oracle or v0.3 negative result.
- Added a byte-exact candidate specification and made the root README describe
  the current shadow candidate instead of presenting v0.2 as current.
- Added a bounded two-parent verifier cache, known-parent-only matrix
  preparation, unknown-parent fast rejection, eviction tests, and explicit
  concurrency rules.
- Added compact multi-parent vectors covering zero, maximum, patterned, and
  SHAKE-derived parents; headers from zero through 4096 bytes; bank and fold
  commitments; and nonce boundaries.
- Extended the independently structured Rust implementation to reproduce both
  the original full-state and v0.4 compact vector suites.
- Added deterministic API fuzz smoke, an LLVM libFuzzer target, canonical
  shadownet work and solution validation, and a frozen work-ID vector.
- Extended Make and CI coverage across the legacy and shadow C suites, Rust,
  protocol tests, Linux, macOS, Windows, GCC, Clang, ASan, and UBSan.
- Documented shadownet isolation, roles, logging, reorgs, stale work, rate
  limits, readiness gates, evidence requirements, and remaining electronic
  adversaries.
- Preserved the distinction between measured RTX 5090 GEMM-time share and any
  unmeasured photonic energy advantage. Laser consensus remains unchanged.

## Unreleased launch-profile research

- Opened a separate non-consensus launch charter that requires substantial
  matrix centrality but reserves 3x and 5x for measured complete-system
  photonic-superiority claims.
- Rejected the LF1 dimension-only family after its RTX 5090 GEMM share peaked
  below 40%.
- Implemented LF2 as one nonce vector evaluated by a stacked bank of
  independently parent-derived matrices, followed by exact requantization,
  XOR folding, and one final SHAKE256.
- Selected `n=4096, K=8` as the provisional engineering point after a `K=4`
  through `K=16` sweep. Three sustained parent datasets measured
  61.55--61.98% exact GEMM time.
- Measured 2.14 ms cached verification and 497 ms cold matrix-bank setup on an
  AMD Ryzen 7 9800X3D.
- Added an independent fold screen; tested omission and simple aggregate
  collapse strategies produced no exact 4096-nibble states.
- Added a separate portable allocation-reusing LF2 research API, deterministic
  matrix/fold/digest vectors, strict target and malformed-input tests, and a
  CUDA differential adversary. Frozen v0.2 behavior and Laser consensus remain
  unchanged.
- Froze LF2-K8 for hardening and closed parameter tuning.
- Added an independently structured RustCrypto implementation that reproduces
  every frozen matrix checksum, intermediate state, fold, digest, and target
  rule without linking the C implementation.
- Expanded adversarial coverage to matrix compression and correlation,
  sampled rank, pass/row/column omission, coefficient truncation, and an exact
  64 MiB bit-sliced CPU circuit.
- Added a transparent FPGA roofline and ASIC sensitivity model plus a local
  parent-transition soak. These are not hardware benchmarks or public-testnet
  evidence.
- Recorded an explicit no-go for consensus and go only for a public
  non-consensus shadow testnet. RTX 5090 GEMM-time share remains distinct from
  any unmeasured photonic energy advantage.

## v0.3-boundary-phase-1-negative - 2026-07-26

- Opened the non-consensus v0.3 hardware-economics research branch with a
  frozen four-gate charter and explicit inter-round boundary taxonomy.
- Added an uncertainty-aware component-complete energy model that separates
  Amdahl screening from complete photonic-system advantage and blocks
  placeholder scenarios from admission.
- Implemented exact cuBLAS and fused CUTLASS recurrent electronic adversaries,
  CPU differential checks, read-only NVML board-energy measurements, and
  reproducible parameter sweeps.
- Measured a roughly 134-million-MAC equal-work frontier across n=1024 to
  n=8192. Conditional electronic headroom reached about 93--94%, while the
  first complete-system uncertainty screen remained below the 3x survival
  gate.
- Added independent recurrence vectors, cycle, diffusion, decision-margin,
  additive-noise, compressibility, and partial-column probes.
- Added an exact-residue boundary simulator that charges nominal energy through
  complete byte-exact trajectory yield and sweeps independent noise, shared
  offset, drift, temperature, component variation, guard bands, selective
  assistance, redundancy, full digital regeneration, and feed-forward stages.
- Evaluated 5,000-sample boundary profiles and a 2,000-sample sensitivity grid.
  The best evidence-informed R1 selective-assistance profile reached 1.86x
  conservatively and 3.11x at the median; a full digital roundtrip reached
  1.10x conservatively.
- Rejected unassisted and all-optical boundaries because exact trajectory yield
  collapses, and rejected three-lane replication because matrix-energy
  multiplication erases the advantage.
- Preserved a projected 7.17x R1 envelope strictly as an unproven device target,
  not an admission result.
- Archived R1 as a conditional architecture, rejected feed-forward as a
  superior alternative, paused construction work, and confirmed that no v0.3
  specification or Laser consensus change begins from this phase.

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
