# PhotonHash v0.2.3-falsified

This release freezes PhotonHash v0.2 as a falsified research artifact.
It MUST NOT be activated in Laser consensus.

## Finding

The implementation remains bit-exact and reproducible, but the active n=1024
profile fails its central R3 hardware-economic requirement. Across 75
sustained RTX 5090 samples, exact GEMM consumed only 11.06-12.21% of
sequential device time rather than the targeted 90%. The best mean
eight-stream pipeline reached 33.43 million complete attempts per second.

The final path includes register-resident SHAKE, autotuned exact
INT8-by-INT8-to-INT32 GEMM, cross-batch overlap, read-only power telemetry,
per-stream differential validation, and zero-error NVIDIA Compute Sanitizer
memcheck.

## Structural analysis

A 1,000-parent corpus covering 1,048,576,000 matrix entries found no useful
compression. Five deeply analyzed matrices were full rank. Tested low-rank,
partial-row, and column-skipping approximations produced zero exact complete
outputs across 1,280 vectors, including approximations retaining nearly all
matrix work.

This is evidence against the tested shortcuts, not a general security proof.
Independent implementation and a complete photonic-system measurement remain
open.

## Decision

The failure is economic rather than an implementation failure or demonstrated
consensus break. Restoring 90% dominance would require roughly 66
nonredundant matrix-equivalent operations under the measured balance, so v0.2
cannot be repaired by routine parameter tuning.

The specification, vectors, tools, raw measurements, and checksums are frozen
here for reproduction. Any v0.3 successor must be a new construction and pass
optimized electronic, complete photonic, verifier-cost, and approximation
gates before consensus consideration.
