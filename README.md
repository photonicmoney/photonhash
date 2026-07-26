# PhotonHash

PhotonHash is an experimental proof-of-work construction built around a dense,
deterministic matrix-vector product. This repository contains the portable C11
reference implementation and the materials needed to review or independently
reimplement it.

> **FALSIFIED PROFILE — FROZEN RESEARCH ARTIFACT.** The active n=1024 profile
> failed its R3 hardware-economic requirement and MUST NOT be activated in
> Laser consensus. This release is preserved for reproduction, independent
> review, and successor-design work. Do not use it to secure assets of value.

Successor research now lives on the non-consensus v0.3 research branch. It
starts from a frozen [hardware-economics charter](docs/v0.3-charter.md), an
explicit [inter-round boundary model](docs/v0.3-boundary-model.md), and a
an exact-yield-aware complete-system energy model.

> **V0.3 BOUNDARY PHASE: NEGATIVE RESULT.** R1 recovered 93--94% conditional
> electronic headroom, but no evaluated nonlinear boundary is an
> evidence-qualified 3x complete-system survivor. R1 is archived as a
> conditional architecture, feed-forward does not advance, and no v0.3
> specification will be written from these probes. Research reopens only if a
> measured physical primitive plausibly fits the published exactness, energy,
> latency, and scaling budget.

See the [boundary-phase decision](docs/v0.3-boundary-phase-1.md),
[machine-readable evidence](research/v0.3/evidence/boundary-evidence.json),
and [v0.3 workspace](research/v0.3/README.md).

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
| [`tools/ph_cuda_bench.cu`](tools/ph_cuda_bench.cu) | Exact batched CUDA pipeline and power benchmark |
| [`tools/ph_matrix_analysis.py`](tools/ph_matrix_analysis.py) | Independent matrix corpus and approximation experiments |
| [`docs/spec-v0.2.md`](docs/spec-v0.2.md) | Working technical specification |
| [`docs/test-vectors.txt`](docs/test-vectors.txt) | Golden end-to-end vectors |
| [`docs/adversarial-brief.md`](docs/adversarial-brief.md) | Claims, attack surfaces, and review targets |
| [`docs/cuda-rtx5090-baseline.md`](docs/cuda-rtx5090-baseline.md) | RTX 5090 methodology, results, and limitations |
| [`docs/v0.2-profile-decision.md`](docs/v0.2-profile-decision.md) | Evidence-based non-activation decision |
| [`docs/v0.3-charter.md`](docs/v0.3-charter.md) | Frozen successor admission gates |
| [`docs/v0.3-boundary-phase-1.md`](docs/v0.3-boundary-phase-1.md) | Boundary-phase evidence and negative decision |
| [`docs/release-notes-v0.3-boundary-phase-1-negative.md`](docs/release-notes-v0.3-boundary-phase-1-negative.md) | Frozen boundary-phase release summary |
| [`tools/ph_v03_model.py`](tools/ph_v03_model.py) | Uncertainty-aware complete-system economics model |
| [`tools/ph_v03_boundary_sim.py`](tools/ph_v03_boundary_sim.py) | Exact-yield boundary and failed-trajectory simulator |
| [`tools/ph_v03_recurrent_fused_cutlass.cu`](tools/ph_v03_recurrent_fused_cutlass.cu) | Exact fused electronic adversary for R1 and F1 |
| [`tools/ph_v03_recurrence_analysis.py`](tools/ph_v03_recurrence_analysis.py) | Independent cycle, diffusion, margin, and approximation probe |

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

With CUDA, cuBLAS, and a configured host C++ compiler:

~~~sh
make cuda-bench
~~~

The CUDA benchmark differentially checks the complete device path against the
C oracle before timing. Pass batch and iteration counts directly to
`ph_cuda_bench` for sustained measurements.

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

The 90% matrix-share figure was a design target, not an established property.
Earlier scalar estimates spanning roughly 80–95% used subtraction against a
hash-only baseline that omitted allocation, vector decoding, requantization,
and packing costs. Those estimates are historical context, not stage-level
evidence. Use the direct benchmark in this tree and record the CPU, compiler,
flags, dimension, and batch size with every result.

A balanced exact end-to-end GPU baseline falsifies that target on an RTX 5090
at n=1024. Across 75 sustained samples, exact GEMM consumed 11.06-12.21% of
sequential device time; the best mean overlapped pipeline reached 33.43
million attempts/s. The final path uses register-resident SHAKE, cuBLAS
autotuning, and an eight-stream pipeline selected after a depth sweep. See the
[measurement report](docs/cuda-rtx5090-baseline.md) and
[profile decision](docs/v0.2-profile-decision.md).

The economically relevant comparison is an exact, aggressively optimized
electronic miner—at minimum batched INT8 inputs with `int32` accumulation,
plus packed INT4 kernels where the target exposes a suitable exact path—
against a complete photonic system including modulation, detection, ADC,
guard-band classification, digital row recomputation, SHAKE generation, and
candidate rechecking. No photonic advantage is claimed here.

The active profile must not be activated or frozen into Laser consensus. This
repository does **not** demonstrate an optical energy advantage, prove
resistance to every cross-nonce amortization strategy, establish analog
correctness under real correlated noise, claim memory-hardness, claim ASIC
resistance, or provide a formal random-oracle proof. Those questions are
explicit review targets in the
[adversarial review brief](docs/adversarial-brief.md).

No published independent audit is claimed for this release. Passing build,
sanitizer, and vector-reproduction checks—when recorded by CI—are
implementation-validation evidence, not cryptographic validation.

The v0.3 boundary phase also does not establish a photonic advantage. Its best
evidence-informed R1 selective-assistance profile reaches 1.86x at the
conservative tail and 3.11x at the median. A full digital regeneration loop
reaches about 1.10x conservatively. Unassisted and all-optical paths lose
byte-exact trajectories. A projected 7.17x envelope is retained only as a
device target because its decisive scaling and boundary assumptions are not
experimentally demonstrated.

## Review posture

The most valuable contributions are attacks, independent implementations,
hardware cost models, boundary vectors, and corrections to unstated
assumptions. Start with the
[adversarial review brief](docs/adversarial-brief.md), which defines claims,
severity tiers, and reporting expectations.

The v0.2 profile and vectors are frozen only as a falsified research artifact.
The v0.3 boundary phase is frozen as a second negative research artifact.
Construction work is paused: successor research requires a measured,
consensus-exact nonlinear boundary that fits the published complete energy and
scaling budget before another hash construction or specification is justified.

Implementation vulnerabilities should follow the [security policy](SECURITY.md);
normal research findings and changes should follow the
[contribution guide](CONTRIBUTING.md).

## Contact

Research correspondence and independent implementation results may be sent to
[lightman-laser@proton.me](mailto:lightman-laser@proton.me). Please use
GitHub private vulnerability reporting for exploitable implementation issues.

## Versioning

- construction/specification: v0.2 falsified research profile;
- reference release: v0.2.3-falsified;
- reference profile: fixed `n = 1024`;
- successor research freeze: v0.3-boundary-phase-1-negative;
- successor consensus status: no specification and no Laser activation;
- release date: 2026-07-26.

Any change to consensus-visible output requires a new version and new vectors.
See the [changelog](CHANGELOG.md) for the history of this release line.

## License

MIT. See the [license](LICENSE).
