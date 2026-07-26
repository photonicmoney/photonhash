# Changelog

## Unreleased

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
