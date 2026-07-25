# PhotonHash v0.2.2-experimental

PhotonHash is an experimental proof-of-work construction built around a dense,
deterministic matrix-vector product. This repository contains the portable C11
reference implementation and the materials needed to review or independently
reimplement it.

> **Research release — open for cryptanalysis.** PhotonHash is a candidate,
> not a frozen protocol commitment. Its security and hardware-economics
> hypotheses have not been established by a published independent audit. Do
> not use this release to secure assets of value.

This release's reference profile uses a fixed 1024 × 1024 matrix at every
height. The larger-dimension schedule discussed in the specification is
deferred research and is not active consensus behavior.

## Research question

Can proof-of-work place most marginal per-nonce cost in an exact dense
matrix-vector product—while preserving deterministic verification—and can a
photonic implementation retain a meaningful advantage after digital assist,
cross-nonce amortization, and optimized electronic batching are considered?
This release defines a falsifiable candidate; it does not establish that the
answer is yes.

## What is included

| Path | Purpose |
|---|---|
| [`include/photonhash.h`](include/photonhash.h) | Public C API |
| [`src/photonhash.c`](src/photonhash.c) | Self-contained SHAKE256 and PhotonHash reference |
| [`tests/ph_selftest.c`](tests/ph_selftest.c) | Known-answer and pipeline invariant tests |
| [`tests/ph_vectors.c`](tests/ph_vectors.c) | Deterministic vector generator |
| [`tests/ph_bench.c`](tests/ph_bench.c) | Scalar reference benchmark |
| [`docs/spec-v0.2.md`](docs/spec-v0.2.md) | Working technical specification |
| [`docs/test-vectors.txt`](docs/test-vectors.txt) | Golden end-to-end vectors |
| [`docs/adversarial-brief.md`](docs/adversarial-brief.md) | Claims, attack surfaces, and review targets |

The implementation has no runtime dependencies beyond a C11 implementation
and the C standard library. The repository expects a POSIX-style `make`;
Windows CI uses MSYS2/UCRT64.

## Build and verify

```sh
make
make test
make check-vectors
make bench
```

For a strict Clang sanitizer run on a supported Unix host:

```sh
make CC=clang sanitize
```

`make check-vectors` regenerates the complete Appendix A file and requires a
byte-for-byte match, including release metadata. CI is configured to perform
the same check with GCC and Clang on Linux, Clang on macOS, UCRT64 GCC on
Windows, and an ASan/UBSan job on Linux.

## Construction summary

For each block template, PhotonHash derives a signed 4-bit matrix `M` from the
parent block hash. Each nonce binds the header into `h_in`, expands a fresh
signed 4-bit vector `x`, computes the exact product `y = Mx`, requantizes `y`
into packed nibbles `r`, and hashes `h_in || r` to obtain the final digest.
All integer serialization is explicitly little-endian.

The fixed reference profile is:

- matrix dimension: `n = 1024`;
- matrix entries and vector entries: signed 4-bit values in `[-8, 7]`;
- exact accumulator: `int32_t`;
- final target comparison: strict less-than over little-endian 256-bit values.

The source is deliberately scalar and audit-oriented. Any optimized
implementation claiming conformance must match the golden vectors exactly;
`ph_hash_trace` exposes intermediate values for differential testing.

## Evidence and non-claims

Scalar measurements reported in the
[specification](docs/spec-v0.2.md#6-cost-profile-why-the-matrix-dominates) place
the matrix stage at roughly 80–95% of attempt cost depending on compiler, CPU,
and dimension. A July 2026 UCRT64 measurement gave 82.7% at `n = 1024` and
92.0% at `n = 2048`. The 90% figure is a design target, not a universal
measured property. Reproduce the benchmark on the hardware being evaluated;
these figures are context, not portable evidence.

This repository does **not** demonstrate an optical energy advantage, prove
resistance to cross-nonce amortization, establish analog correctness under
real correlated noise, claim memory-hardness, claim ASIC resistance, or
provide a formal random-oracle proof. Those questions are explicit review
targets in the [adversarial review brief](docs/adversarial-brief.md).

No published independent audit is claimed for this release. Passing build,
sanitizer, and vector-reproduction checks—when recorded by CI—are
implementation-validation evidence, not cryptographic validation.

## Review posture

The most valuable contributions are attacks, independent implementations,
hardware cost models, boundary vectors, and corrections to unstated
assumptions. Start with the
[adversarial review brief](docs/adversarial-brief.md), which defines claims,
severity tiers, and reporting expectations.

Before any parameter freeze, the project requires resolution of the listed
high-priority questions plus at least two independent implementations matching
an expanded, frozen vector set. Publication of this repository is intended to
make that external review possible.

Implementation vulnerabilities should follow the [security policy](SECURITY.md);
normal research findings and changes should follow the
[contribution guide](CONTRIBUTING.md).

## Contact

Research correspondence and independent implementation results may be sent to
[lightman-laser@proton.me](mailto:lightman-laser@proton.me). Please use
GitHub private vulnerability reporting for exploitable implementation issues.

## Versioning

- construction/specification: v0.2 working draft;
- reference release: v0.2.2-experimental;
- reference profile: fixed `n = 1024`;
- release date: 2026-07-25.

Any change to consensus-visible output requires a new version and new vectors.
See the [changelog](CHANGELOG.md) for the history of this release line.

## License

MIT. See the [license](LICENSE).
