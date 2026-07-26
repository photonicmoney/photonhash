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

## Construction lineage

PhotonHash is an experimental proof-of-work construction in the lineage of
[HeavyHash](https://arxiv.org/abs/1911.05193) and
[LightHash](https://doi.org/10.1364/OPTICA.476173). It adopts their
family-level idea of placing low-precision matrix-vector work between digital
hashing stages; it does not claim that hash-matrix-hash proof of work or
photonic proof of work is new. PhotonHash defines a distinct, incompatible
byte-level pipeline and parameter profile. See the
[related-work comparison](docs/spec-v0.2.md#21-related-work-and-construction-lineage).

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

`make bench` measures each scalar stage directly over batches of distinct
nonces. Scratch buffers are allocated once, outside the measured nonce loop,
and the staged benchmark must reproduce `ph_hash` before timing begins. It
reports SHAKE generation, nibble decoding, exact matvec, requantization and
packing, final hashing, scalar MAC throughput, and effective matrix-read
bandwidth separately.

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

The 90% matrix-share figure is a design target, not a measured property.
Earlier scalar estimates spanning roughly 80–95% used subtraction against a
hash-only baseline that omitted allocation, vector decoding, requantization,
and packing costs. Those estimates are historical context, not stage-level
evidence. Use the direct benchmark in this tree and record the CPU, compiler,
flags, dimension, and batch size with every result.

The economically relevant comparison is an exact, aggressively optimized
electronic miner—at minimum batched INT8 inputs with `int32` accumulation,
plus packed INT4 kernels where the target exposes a suitable exact path—
against a complete photonic system including modulation, detection, ADC,
guard-band classification, digital row recomputation, SHAKE generation, and
candidate rechecking. No such end-to-end comparison is claimed here.

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
