# PhotonHash LF2 launch-profile first pass

Status: **provisional non-consensus candidate**  
Date: 2026-07-26  
Selected engineering point: `n = 4096`, `K = 8`

## Decision

The dimension-only LF1 family is rejected. Merely increasing the square
matrix peaked at about 30% exact GEMM time in the tested RTX 5090 pipeline and
then regressed as vector expansion and finalization grew.

LF2-K8 advances as the first provisional launch-profile candidate. It places a
mean 61.74% of serialized device time in exact tensor-core GEMM across three
parent datasets while retaining about 1.97 million attempts per second in the
eight-stream screen. A cached scalar verification took 2.14 ms on a Ryzen 7
9800X3D, and all eight matrices were derived in 497 ms.

This is a successful first engineering screen with a portable research API
and deterministic intermediate vectors. It is not a specification, security
proof, photonic-energy result, or consensus proposal.

## Construction under test

For a parent hash `P`, header `H`, nonce `N`, dimension `n`, and matrix count
`K`:

~~~text
M[0] = Matrix(P)
P[j] = SHAKE256("LASER/PhotonHash/launch-LF2/matrix" || P || LE32(j))
M[j] = Matrix(P[j])                                      for j = 1..K-1

h = SHAKE256("LASER/PhotonHash/v1/vector" || H || LE64(N))
x = signed_nibbles(SHAKE256-XOF(h, n/2))

y[j] = M[j] * x                                         exact int32
q[j] = requantize(y[j])                                 4 bits per row
r[i] = q[0][i] XOR q[1][i] XOR ... XOR q[K-1][i]

d = SHAKE256("LASER/PhotonHash/launch-LF2/final" || h || pack(r))
~~~

All matrices are fixed for a parent and can be cached. An electronic miner
stacks them into one `K*n` by `n` matrix and computes all products in one
batched cuBLAS call. This gives the GPU the strongest simple fusion strategy;
LF2 receives no credit from forcing separate GEMM launches.

The fold is nonlinear with respect to the matrix products because exact
requantization occurs before XOR. The final SHAKE input changes if any folded
nibble changes.

## Electronic adversary

The CUDA 13.2 implementation uses:

- register-resident SHAKE256 vector expansion;
- a single exact cuBLAS INT8 by INT8 to INT32 tall GEMM;
- a coalesced parallel requantize-and-XOR kernel;
- register-resident final SHAKE256 and target comparison;
- eight independent streams for cross-batch overlap; and
- byte-for-byte differential checks of `h`, `x`, every `y[j]`, the final
  digest, and the target result against a scalar oracle before timing.

The first permutation-based LF2 probe was discarded because materializing
permuted vectors consumed enough bandwidth to leave only 32.7% in GEMM. The
matrix-bank result below is therefore not based on that weaker electronic
implementation.

### LF1 dimension-only rejection

| `n` | Matrix bytes | Exact GEMM share |
|---:|---:|---:|
| 1024 | 1 MiB | 11.62% |
| 2048 | 4 MiB | 19.33% |
| 4096 | 16 MiB | 24.77% |
| 8192 | 64 MiB | 29.79% |
| 16384 | 256 MiB | 26.71% |

These were short dimension-screen runs. They are sufficient to reject the
family, not to serve as final power measurements.

### LF2 matrix-count sweep

All rows below use `n=4096`, batch 8192, one tall GEMM, and the exact folded
pipeline.

| `K` | Matrix bank | GEMM share | Device attempts/s | Decision |
|---:|---:|---:|---:|---|
| 4 | 64 MiB | 50.38% | 2.87 M | threshold only; too little margin |
| 6 | 96 MiB | 57.48% | 2.25 M | viable fallback |
| 8 | 128 MiB | 61.82% | 1.83 M | selected provisional point |
| 12 | 192 MiB | 66.82% | 1.32 M | more boundaries than needed |
| 16 | 256 MiB | 69.78% | 1.05 M | strong headroom, unnecessary cost |

### Sustained K8 result

Across three 256-iteration parent datasets:

- matrix share: 61.55% to 61.98%, mean 61.74%;
- serialized device rate: mean 1.806 million attempts/s;
- eight-stream rate: mean 1.965 million attempts/s; and
- logical work: 134,217,728 exact low-precision MACs per attempt.

Two longer 1024-iteration runs reproduced a 61.79% mean matrix share. Board
energy landed between 253.6 and 306.5 microjoules per attempt across sampled
power integration and the independent NVML energy counter. This interval is
reported because the two NVML methods did not agree closely enough to justify
a single precise energy number. It is complete GPU-board energy, not an
attribution of energy to GEMM alone.

At the measured mean share, the optimistic free-matrix Amdahl ceiling is
2.61x. A future 10x matrix-stage improvement would imply about 2.25x total
speedup before adding any photonic conversion or support overhead. These are
headroom calculations, not photonic-advantage claims.

## Ordinary-node cost

The portable LF2 cost screen was compiled with GCC `-O3 -march=native` on an
AMD Ryzen 7 9800X3D:

| Measurement | Result |
|---|---:|
| Cached matrix-bank memory | 128 MiB |
| Cold derivation of eight matrices | 497 ms |
| Cached exact verification | 2.140 ms/attempt |
| Matrix-plus-fold share on CPU | 99.24% |

This clears the charter's initial targets of less than 2 seconds for parent
setup and less than 250 ms for cached verification. Independent builds on
slower ordinary hardware are still required.

## Fold and shortcut screen

An independent Python implementation using `hashlib.shaKE_256` evaluated 16
nonce vectors at the selected parameters.

- folded entropy was 3.99989 bits per nibble;
- packed folded output had a mean zlib ratio of 1.0054;
- omitting one of eight matrices gave 12.70% nibble accuracy and zero exact
  4096-nibble vectors;
- the observed one-matrix-omission accuracy corresponds to roughly
  `2^-12195` for an exact full vector under an independence estimate;
- omitting two, four, or seven matrices also produced zero exact vectors; and
- three simple attempts to requantize the summed products instead of computing
  the folded products reached at most 6.56% nibble accuracy and zero exact
  vectors.

The individual requantized buckets are biased, so the one-missing-pass success
rate is not the idealized 1/16. The report uses the observed rate rather than
hiding that bias. After eight-pass XOR folding, the output histogram was close
to uniform in this sample.

These experiments reject the tested omission and simple algebraic-collapse
strategies. They do not prove that no specialized circuit, bit-sliced method,
or correlated approximation can compute the folded output more cheaply.
Deeper cryptanalysis remains an admission gate.

## Photonic interpretation

LF2 avoids recurrent state and therefore avoids R1's exact nonlinear feedback
problem. It does not make conversion free.

A future optical miner would need either a resident bank of eight matrix
engines or sequentially program/process the eight parent matrices over a large
nonce batch. Every matrix output must still be detected and exactly
requantized before the fold. The same nonce vector may be remodulated for each
matrix, but no quantized output is fed back as the next optical input.

Consequently, LF2 is naturally photonic-addressable but has not demonstrated
photonic superiority. Its complete optical path must charge eight matrix
passes, detection, exact low-bit conversion, folding, modulation or routing,
matrix programming, control, and the digital hashes. The separate 3x and 5x
claim gates remain unchanged.

## Gate status

| Gate | Status | Reason |
|---|---|---|
| L1 exactness | partial | portable/CUDA differential checks and frozen research vectors pass; no independently written implementation yet |
| L2 matrix centrality | pass for continuation | 61.74% mean serialized time share; energy attribution still incomplete |
| L3 work integrity | partial | initial omission and collapse screens are negative; broader attacks remain |
| L4 practicality | preliminary pass | commodity GPU path and 2.14 ms cached CPU verification demonstrated on one machine |
| L5 review/activation | fail | no public review, second implementation, testnet, or activation decision |

## Next engineering work

1. Review and stabilize the separate allocation-reusing portable research API
   and expand its vectors beyond the current normal, empty-header,
   maximum-nonce, target-boundary, malformed-input, and matrix-bank coverage.
2. Build an independently written Rust or Zig implementation from the byte
   description and require every intermediate vector to match.
3. Attack the fold with bit-sliced, partial-row, partial-column, aggregate,
   approximation, and selective-recheck implementations.
4. Re-run GPU tuning with a fused custom tall-GEMM epilogue and test other
   high-end and commodity GPUs.
5. Measure verifier cost on slower CPUs and memory-constrained nodes.
6. Only after those gates pass, define a non-consensus testnet profile.
7. Model the eight-pass optical path honestly; do not claim photonic
   superiority without complete measured hardware evidence.

Raw data and machine-readable summaries are under `research/launch/`.
