# PhotonHash v0.4.0-shadow.1

<img src="lasercoin-regnet.png" alt="Laser regnet" width="150">

PhotonHash is an experimental, exact, matrix-centric proof-of-work candidate
for Laser. This repository contains the frozen LF2-K8 shadownet candidate,
portable and optimized implementations, independent vectors, adversarial
tools, and the historical experiments that led to it.

> **SHADOWNET CANDIDATE — NOT LASER CONSENSUS**
>
> Version 0.4.0-shadow.1 may be evaluated beside a public Laser test network.
> It cannot accept or reject Laser blocks, change chain selection, or secure
> assets. Activation would require a later public review and separate Laser
> consensus decision.

> **CLAIM BOUNDARY**
>
> The frozen historical LF2-K8 pipeline measured 61.55 to 61.98 percent GEMM
> time on RTX 5090. This supports a matrix-centric implementation claim. It is
> not matrix-energy attribution and does not demonstrate that a photonic miner
> currently beats a GPU.

## New research results: LF2 packing and ChaCha20

**30 October qualification checkpoint:** all four C20 implementations agree on
**560 measured full-fold vectors**; **1,048,576 measured random GPU/C cases**
agree with zero skips. The [conformance package and limits](research/qualification/lf3-c20-2026-10-30/README.md)
include the unchanged outside Python checker and an extended Rust checker.
These use experiment tags. No candidate freeze or activation is implied.

The **29 October 2026** comparison evaluates unchanged LF2-K8 packing beside
**LF3-K8-C20-experiment.1**, a separately named experimental hash that uses
ChaCha20 to expand each header/nonce binding into the matrix input vector.
C20 retains the eight matrices, exact quantizer and full 2048-byte fold.

| Result on RTX 5090 | Observed paired device-throughput gain |
|---|---:|
| Packed LF2 versus fastest tested int32 LF2 | **14.6-34.3%** |
| Experimental C20 versus fastest tested already-packed LF2 | **A further 19.1-25.3%** |
| Experimental C20 versus fastest tested int32 LF2 | **41.5-63.7%** |

Packing preserves LF2's hash and cuts the GEMM output buffer **8x**: 1 GiB to
128 MiB at batch 8192. C20 changes the hash. Its GEMM-plus-epilogue stage takes
**84.4-87.2%** of sampled device time, including quantization and stores.
That percentage is not pure matrix time or energy attribution.

These are **exploratory device timings**, using 24 configurations and five
completed conditions on a shared Windows desktop GPU. Choices were selected
from the same three/seven-round samples, with outliers retained. Extra
padding-boundary tests and independent timing confirmation remain incomplete
after a CUDA initialization stall. No sustained miner, energy, optical
advantage or consensus-security result is claimed. Neither change is activated.

Read the [ChaCha20 construction and reference vector](docs/lf3-k8-c20-experiment-1.md),
the [complete comparison and limitations](docs/lf2-gpu-comparison-2026-10-29.md),
and the [published synthetic records and analysis](research/launch/lf2-c20-gpu-2026-10-29/README.md).
The measured kernel implementation currently remains local; this publication
provides the byte rule, measurement evidence and CPU-only checking tools.

## What changed

The old top-level release was PhotonHash v0.2.3-falsified. Its 1024 by 1024
profile placed only about 11 to 12 percent of optimized RTX 5090 device time
in matrix work, so even a free matrix stage offered only about 1.14 times
whole-pipeline headroom. That result remains frozen and is not reinterpreted.

PhotonHash v0.3 explored recurrent designs capable of restoring more than 90
percent matrix headroom. It found that exact nonlinear regeneration and
optical-electronic conversion erased the modeled advantage. No v0.3
construction advanced.

Version 0.4 starts from a different and explicitly narrower launch objective:
provide secure, reproducible, commodity-mineable proof of work in which
matrix computation is already a substantial part of every attempt, without
claiming current photonic superiority.

LF2-K8 met the provisional matrix-time threshold and is now frozen for
shadownet hardening.

## LF2-K8 in one minute

For each admitted parent block, miners derive and cache eight deterministic
4096 by 4096 signed 4-bit matrices.

For every header and nonce:

    header + nonce
          |
          v
    SHAKE256 binding digest
          |
          v
    one signed 4-bit vector x
          |
          +--> M0 x -- exact requantization --+
          +--> M1 x -- exact requantization --+
          |                 ...               +--> XOR fold
          +--> M7 x -- exact requantization --+       |
                                                       v
                                                final SHAKE256

The eight products are independent but share the same nonce vector. A GPU may
stack all matrices into one tall matrix and batch many nonce vectors in one
exact GEMM. That optimization is intentional and is already granted to the
electronic adversary.

There is one digital output boundary after the feed-forward matrix bank, not
dozens of recurrent optical feedback boundaries.

Fixed parameters:

| Parameter | Value |
|---|---:|
| Dimension | 4096 |
| Matrix passes | 8 |
| Exact MACs per attempt | 134,217,728 |
| Unpacked resident matrix bank | 128 MiB |
| Packed matrix bank | 64 MiB |
| Folded state | 2048 bytes |
| Accumulator | signed 32-bit exact integer |
| Final digest | SHAKE256-256 |

The complete byte construction is in the
[v0.4 candidate specification](docs/spec-v0.4-shadow.md).

## Current evidence

### Exactness

- The portable C, CUDA, and independently structured Rust implementations
  reproduce the frozen LF2 vectors.
- The Rust implementation does not link the C implementation and derives the
  complete matrix bank itself with RustCrypto SHAKE256.
- Compact v0.4 vectors cover four parent classes, header lengths from zero to
  4096 bytes, zero and maximum nonces, matrix-bank commitments, folded-state
  commitments, and final digests.
- Target comparison is strict unsigned little-endian: equality is rejected.

### Electronic performance

In the frozen historical RTX 5090 pipeline, batch 8192:

| Measurement | Result |
|---|---:|
| Exact GEMM time share | 61.55–61.98% |
| Mean serialized attempts per second | about 1.80 million |
| Complete board-energy interval | 253.6–306.5 microjoules per attempt |

Board energy covers the measured electronic pipeline. It is not a matrix-only
measurement or a photonic comparison.

On the Ryzen 7 9800X3D reference host:

| Measurement | Result |
|---|---:|
| Portable C cold matrix-bank setup | about 0.48–0.50 seconds |
| Independent Rust matrix-bank setup | about 0.23 seconds |
| Cached portable verification | about 2–3 milliseconds |

Against Laser's intended ten-second block interval, setup time is operationally
important even though it amortizes over millions of nonce attempts.

### Adversarial work

The current corpus tests:

- matrix entry bias, compression, sampled rank, singular values, and
  cross-matrix correlation;
- whole-pass, row, selected-column, and coefficient-bit omission;
- approximate products and exact-state survival;
- XOR-fold output distribution;
- an exact 64 MiB bit-sliced AND-popcount implementation; and
- cold setup, parent lifetime, and precomputation assumptions.

No tested approximation produced a useful exact-state shortcut. The exact
bit-sliced CPU path was roughly equal to the portable integer path, but it
defines a credible FPGA or ASIC circuit and therefore remains an important
electronic threat model.

These experiments are evidence, not a proof that no shortcut exists.

## Shadownet

The PhotonHash shadownet is an observational system that evaluates LF2-K8
beside Laser without entering the Laser validation path.

Its safety invariant is simple:

> A shadownet failure must be unable to change Laser block acceptance, chain
> selection, propagation, difficulty, or availability.

Version 0.4 adds:

- canonical work and solution messages;
- deterministic work IDs;
- strict field and integer bounds;
- a two-parent verifier cache bounded near 256 MiB;
- unknown-parent rejection before matrix derivation;
- explicit cache mutation and workspace concurrency rules;
- stale-work, reorg, malformed-message, rate-limit, and evidence requirements;
- deterministic smoke fuzzing and an LLVM libFuzzer target; and
- cross-platform CI for both historical and shadow vector sets.

Read:

- [Shadownet protocol](docs/shadownet-protocol.md)
- [Readiness ledger](docs/shadownet-readiness.md)
- [Operations and evidence plan](docs/launch-profile-shadow-testnet-plan.md)
- [Hardening decision](docs/launch-profile-lf2-hardening-decision.md)

No Laser consensus source is modified by this repository state.

## Build and test

The portable build requires a C11 compiler, Make, Python 3, and Rust for the
independent implementation.

    make shadow-ci

That target runs:

- the frozen v0.2 self-tests and vectors;
- LF2 API and original frozen vectors;
- v0.4 compact multi-parent vectors;
- bounded verifier-cache tests;
- deterministic fuzz smoke;
- canonical shadownet protocol tests; and
- the independent Rust test suite.

Individual targets:

    make launch-test
    make check-launch-vectors
    make check-shadow-vectors
    make shadow-cache-test
    make shadow-fuzz-smoke
    make shadow-protocol-test
    make shadow-rust-test

On a Unix host with Clang:

    make CC=clang sanitize
    make CC=clang sanitize-shadow

The libFuzzer entry point is tests/ph_shadow_fuzz_target.c. It is intentionally
excluded from ordinary production builds.

On a Unix host with Clang, build and run it explicitly:

    make CC=clang ph_shadow_fuzzer
    ./ph_shadow_fuzzer -max_total_time=300

CUDA benchmarking requires CUDA, cuBLAS, and a configured host compiler:

    make cuda-bench

The CUDA path differentially validates exact device results against the C
oracle before timing.

## Repository map

| Path | Purpose |
|---|---|
| [include/photonhash_launch.h](include/photonhash_launch.h) | Frozen LF2-K8 attempt API |
| [src/photonhash_launch.c](src/photonhash_launch.c) | Portable exact LF2-K8 oracle |
| [include/photonhash_shadow.h](include/photonhash_shadow.h) | v0.4 shadow identity and bounded verifier cache |
| [src/photonhash_shadow.c](src/photonhash_shadow.c) | Known-parent preparation, eviction, and prepared verification |
| [independent/rust-lf2](independent/rust-lf2) | Independently structured Rust implementation |
| [docs/spec-v0.4-shadow.md](docs/spec-v0.4-shadow.md) | Byte-exact candidate specification |
| [docs/lf3-k8-c20-experiment-1.md](docs/lf3-k8-c20-experiment-1.md) | Separate ChaCha20 experiment and exact byte rule |
| [docs/lf2-gpu-comparison-2026-10-29.md](docs/lf2-gpu-comparison-2026-10-29.md) | Packed LF2 / C20 results, methods and limitations |
| [research/launch/lf2-c20-gpu-2026-10-29](research/launch/lf2-c20-gpu-2026-10-29/README.md) | Synthetic benchmark records, manifest and analysis |
| [docs/launch-profile-lf2-vectors.txt](docs/launch-profile-lf2-vectors.txt) | Original full folded-state LF2 vectors |
| [docs/v0.4-shadow-vectors.txt](docs/v0.4-shadow-vectors.txt) | Compact multi-parent shadow vectors |
| [docs/shadownet-protocol.md](docs/shadownet-protocol.md) | Non-consensus work and solution protocol |
| [docs/shadownet-readiness.md](docs/shadownet-readiness.md) | Live readiness gates and unresolved work |
| [tools/ph_cuda_bench.cu](tools/ph_cuda_bench.cu) | Exact batched CUDA adversary and power benchmark |
| [tools/ph_lf2_adversarial.py](tools/ph_lf2_adversarial.py) | Structural, omission, and approximation probes |
| [tools/ph_lf2_bitslice_bench.c](tools/ph_lf2_bitslice_bench.c) | Exact packed bit-sliced electronic adversary |
| [tools/ph_shadow_protocol.py](tools/ph_shadow_protocol.py) | Canonical message and work-ID validator |
| [tests/ph_shadow_fuzz_target.c](tests/ph_shadow_fuzz_target.c) | LLVM libFuzzer entry point |
| [research/launch](research/launch) | Raw LF2 measurements and machine-readable evidence |
| [research/v0.3](research/v0.3) | Archived photonic-boundary research |

The legacy v0.2 C API, specification, vectors, and negative decision remain in
the repository for reproduction.

## Version history

| Version | Meaning |
|---|---|
| v0.2.3-falsified | Exact 1024 profile; hardware-economic hypothesis failed |
| v0.3 boundary phase | Recurrent research; no exact economical boundary survived |
| v0.4.0-shadow.1 | Frozen LF2-K8 candidate prepared for observational shadownet review |

The legacy ph_version function continues to identify the v0.2 oracle so its
historical vector generator stays reproducible. The new ph_shadow_version
function and the root VERSION file identify v0.4.0-shadow.1.

## What remains before consensus consideration

At minimum:

1. clean public CI across Linux, macOS, and Windows;
2. an implementation written by a separate human reviewer;
3. broader packed-INT4/native-Blackwell tuning and independent fused-GPU reproduction;
4. AMD and mid-range commodity GPU measurements;
5. FPGA synthesis and stronger ASIC analysis;
6. GPU-native matrix setup and parent-transition measurements;
7. sustained public shadownet operation, reorgs, stale work, verifier floods,
   and complete replay; and
8. a separate, explicit Laser activation proposal.

Passing the shadownet would permit a launch-readiness review. It would not
automatically activate PhotonHash.

## Photonic claim policy

Matrix share is only Amdahl headroom. Laser may claim photonic superiority
only after a complete valid-attempt system measurement includes light
sources, matrix operations, modulation, detection, conversion, calibration,
control, digital hashing, rechecks, and failed trajectories.

The separate thresholds remain:

- at least 3 times complete-system advantage for a credible research result;
- about 5 times for a strong commercial claim; and
- 10 times for an exceptional light-money result.

Version 0.4 does not claim any of them.

## Security

PhotonHash has not received a published independent cryptographic or
implementation audit. Report implementation vulnerabilities under
[SECURITY.md](SECURITY.md). Reproducible public cryptanalysis and optimized
electronic attacks are encouraged under [CONTRIBUTING.md](CONTRIBUTING.md).

License: MIT.
