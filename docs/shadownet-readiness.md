# PhotonHash v0.4 shadownet readiness

Version: **0.4.0-shadow.1**

This is the live readiness ledger for LF2-K8. Passing it means the candidate
may enter an observational public shadownet. It does not mean the candidate is
ready for Laser consensus.

## Completed locally

- LF2-K8 parameters and output bytes are frozen.
- The v0.4 candidate specification defines every matrix, vector,
  requantization, fold, digest, and target byte.
- The historical v0.2 falsification and v0.3 boundary result remain intact.
- Portable C, exact CUDA, and independently structured Rust agree on the
  original frozen vectors.
- Four compact v0.4 vectors add all-zero, all-one, incremental, and
  SHAKE-derived parents; empty, one-byte, 80-byte, and 4096-byte headers; zero,
  maximum, patterned, and unit nonces.
- A two-parent verifier cache bounds unpacked matrix memory near 256 MiB and
  will not derive from an unknown solution parent.
- Strict target, malformed input, cache eviction, stale-parent separation,
  deterministic fuzz-smoke, and canonical protocol tests exist.
- The Makefile and CI definition cover C, Rust, legacy vectors, both shadow
  vector sets, protocol tests, GCC, Clang, Windows, Linux, macOS, ASan, and
  UBSan.
- Expanded structural, omission, approximation, compression, and exact
  bit-sliced probes found no useful shortcut in the tested corpus.
- The aggregate shadow-ci target passes locally on Windows with UCRT64 GCC,
  Python protocol tests, release-mode Rust vectors, legacy regression, cache
  lifecycle, compact vectors, and deterministic fuzz smoke.

## Must pass before a public shadownet starts

- The updated CI workflow must pass from a clean public revision on Linux,
  macOS, and Windows.
- A second human author must implement the specification without reading the
  C control flow and publish any disagreements.
- The shadownet adapter and collector must receive a security review proving
  that shadow failure cannot affect Laser validation.
- Raw evidence storage, privacy policy, retention, clocks, and reproducibility
  metadata must be operational.
- Rate limits must be set for unknown work IDs, stale solutions, and exact
  verifier queues.
- At least one commodity mining implementation must package reproducibly
  without machine-specific binaries in the repository.

## Electronic-adversary work that remains open

- LF2-specific packed-INT4 tensor implementation.
- Fused exact GEMM, requantization, XOR, and digest epilogue.
- AMD or other non-NVIDIA commodity GPU implementation.
- Benchmarks on older and mid-range GPUs.
- Synthesized FPGA resource, timing, and power report.
- ASIC post-layout or defensible component-level model.
- GPU-native matrix derivation and measured parent-transition overlap.

These do not all have to be complete to begin observational traffic, but
unresolved results block a final consensus-readiness decision.

## Public shadownet evidence required

The run must demonstrate:

1. zero digest disagreement across independently built implementations;
2. bounded memory and stable verifier queues under malformed and stale work;
3. safe bank turnover at ten-second parent intervals;
4. measured winner-head-start, propagation, and reorg effects;
5. practical mining on multiple commodity devices;
6. sustained difficulty and solution accounting;
7. exact replay from published raw messages; and
8. no path from a shadow fault into Laser acceptance or chain selection.

## Current decision

The repository is locally ready to publish as a shadownet release candidate.
It is not yet evidence-qualified for public operation until the clean hosted
Linux, macOS, and Windows CI run and the adapter/collector deployment review
pass.

Laser consensus remains unchanged.
