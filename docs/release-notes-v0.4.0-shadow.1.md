# PhotonHash v0.4.0-shadow.1

This prerelease gives the frozen LF2-K8 candidate a distinct identity and
prepares it for non-consensus public shadownet review.

## Candidate

- 4096 by 4096 matrices;
- eight independently parent-derived matrix passes;
- one nonce-derived signed 4-bit vector;
- exact signed 32-bit accumulation;
- exact 4-bit requantization;
- XOR fold across passes; and
- one final SHAKE256 digest.

The strongest measured RTX 5090 implementation reported 61.55 to 61.98
percent exact GEMM time. This is matrix-time evidence, not photonic-energy
evidence.

## Readiness additions

- byte-exact v0.4 shadow specification;
- explicit release version separate from the falsified v0.2 oracle;
- bounded two-parent verifier cache and unknown-parent fast rejection;
- compact multi-parent and maximum-header vectors;
- independent Rust reproduction of both vector sets;
- deterministic smoke fuzzing and an LLVM libFuzzer entry point;
- canonical work and solution protocol with frozen work-ID vector;
- Linux, macOS, Windows, GCC, Clang, Rust, ASan, and UBSan CI coverage;
- shadownet safety, logging, reorg, rate-limit, and evidence requirements; and
- an explicit readiness ledger.

## Status

This is not a consensus release. It does not change Laser, activate LF2-K8,
or claim measured photonic superiority.

The next permitted step after clean CI and deployment review is an
observational public shadownet.
