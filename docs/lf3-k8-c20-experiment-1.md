# LF3-K8-C20-experiment.1: ChaCha20 vector expansion

29 October 2026. **Experimental, unselected and non-consensus.** This is a
separately named hash construction. Frozen LF2-K8 remains unchanged.

LF3-K8-C20 asks whether parallel ChaCha20 expansion can reduce the digital
vector overhead around LF2's matrix workload. It retains the eight matrices,
exact quantizer and complete 2048-byte fold. It changes the vector expander and
binding/final domains, so its hashes differ from LF2. No chain or miner selects
this profile as a result of this publication.

## Construction

Notation and the parent-derived matrix bank follow the
[frozen LF2 specification](spec-v0.4-shadow.md). SHAKE256(input, length) means
exactly that many output bytes. Tags below are exact ASCII without a trailing
zero. Concatenation is `||`; nonce encoding is unsigned `LE64`.

Fixed parameters are n=4096 and K=8. Matrix coefficients and vector entries are
signed integers in [-8,7]. For a 32-byte parent P, derive the same eight
4096-by-4096 matrices M0 through M7 as LF2, with its unchanged matrix domains,
seeds and row order. No compressed F256 fold is used.

First bind the opaque header and nonce:

```text
h = SHAKE256("LASER/PhotonHash/LF3-K8-C20-experiment.1/vector"
             || opaque_header || LE64(nonce), 32)
```

Use h as the 256-bit ChaCha20 key, a twelve-byte zero ChaCha nonce, and RFC 8439
block counters **1 through 32**. Concatenate the 32 complete 64-byte block
outputs in counter order, giving 2048 bytes S. This is the standard 20-round
block function, including feed-forward and little-endian output words.

```text
x[2t]   = (S[t] & 15) - 8
x[2t+1] = (S[t] >> 4) - 8             for t = 0..2047
```

All eight matrix products share this one 4096-entry vector. Compute exact dot
products before quantization:

```text
y[j,r] = sum(Mj[r,c] * x[c], c=0..4095)
q[j,r] = ((y[j,r] + 262144) >> 9) & 15
z[r]   = q[0,r] XOR q[1,r] XOR ... XOR q[7,r]
F[t]   = z[2t] | (z[2t+1] << 4)

D = SHAKE256("LASER/PhotonHash/LF3-K8-C20-experiment.1/final" || h || F, 32)
```

Use exact signed-int32 sums or a demonstrated byte-equivalent method. Applying
q before a complete split-K reduction is wrong. F contains all 2048 bytes;
there is no truncation or stripe compression. A straightforward evaluation
performs 134,217,728 multiply-accumulates. This count is not a lower bound on
the cheapest adversarial evaluation.

ChaCha20 serves as a deterministic public expander here. Its key h is public;
there is no secret-key encryption. Counters never approach wrap. OpenSSL's raw
ChaCha20 API has a different counter/nonce layout; the supplied checker maps
the initial state words explicitly and checks the RFC block vector.

This construction defines a digest, not a chain identity, canonical block
header, difficulty adjustment, work score, issuance or activation rule. The
benchmark uses LF2's strict unsigned little-endian target comparison, rejecting
equality. A chain integration would need its own complete consensus contract.

## Results beside unchanged LF2 packing

The [RTX 5090 comparison](lf2-gpu-comparison-2026-10-29.md) offers both profiles
the same GEMM tuning choices and packed epilogues:

| Result | Observed paired device-throughput change |
| --- | ---: |
| Packed LF2 versus fastest tested int32 LF2 | +14.6-34.3% |
| C20 versus fastest tested already-packed LF2 | a further +19.1-25.3% |
| C20 versus fastest tested int32 LF2 | +41.5-63.7% |

The C20 GEMM-plus-epilogue stage accounts for 84.4-87.2% of device time by the
median per-sample ratio. That stage includes quantization and stores; it is
not pure matrix time or energy attribution. Packing alone reduces the GEMM
intermediate buffer 8x and preserves the LF2 hash. C20 is the distinct hash.

These are exploratory paced measurements on a shared Windows desktop GPU:
24 configurations, five completed timing conditions, three or seven paired
rounds, and winners selected from those same samples. No outlier was removed.
An extra CUDA initialization stall ended further collection; exact binding-rate
GPU boundary checks and independent fixed-choice timing confirmation remain
incomplete. No energy or sustained full-miner result is claimed.

## Reference vector and checks

The [full reference vector](../research/launch/lf3-k8-c20-experiment-1-vector.json)
uses a zero parent, a synthetic 184-byte header and nonce 18446744073709551615.
It contains the complete folded state, plus these checkpoints:

```text
h = a98fccd1f7e6508ab87af467c7eeacccee1bfa8d7155a7119bafb7b632dc81c9
bank commitment = ad3f5934570af927c1ecebc452d912db1a450894d93c0bec04821bcaa8e8ae6b
D = a32368927eae44559966cf67a647ac861053af6ceacaf94b4b0899354a07aa42
```

The initial local C prototype passed the RFC 8439 block vector and full-size
int32/modulo-8192 differential evaluation. Node/OpenSSL independently checked
expansion and final hashing. The later CUDA implementation matches that fold
and digest and adds the documented GPU differential cases. It shares portable
bank derivation, so this is not a fully independent composite implementation.

The public checker recomputes binding, all expansion bytes and final hashing
with Node/OpenSSL, and checks the RFC primitive and frozen bank commitment:

```sh
node tools/check-lf3-c20-vector.mjs
```

It does **not** recompute the matrix bank or products. The fixture's
`gpuWork:false` and `performanceMeasured:false` fields describe its earlier
CPU-only generation, not the later separately published GPU measurement run.
The measured CPU/CUDA prototype sources currently remain local; this
documentation update publishes the byte rule, fixture, synthetic measurement
records and analysis/checking tools.

## Remaining research

Parallel expansion reduces observed overhead, but a standard primitive does
not prove the composite proof of work secure. Public-seed selection, related
or weak seeds, parent/header/nonce grinding, partial-work and approximation
attacks, specialized exact circuits and verification economics need review.
An independent full implementation, stable-device timing confirmation,
broader GPU tuning, measured energy and actual miner parent-turnover/reorg
cancellation behavior remain necessary. No dominance or real-money readiness
claim follows from the measured speedup.

References: [RFC 8439](https://www.rfc-editor.org/rfc/rfc8439.html),
[frozen LF2 bytes](spec-v0.4-shadow.md),
[complete measurement methods and limitations](lf2-gpu-comparison-2026-10-29.md),
[published synthetic evidence](../research/launch/lf2-c20-gpu-2026-10-29/README.md).
