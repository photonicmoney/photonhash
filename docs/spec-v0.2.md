# PhotonHash: Technical Specification

**Version:** 0.2 (frozen falsified research profile)
**Author:** Lightman
**Status:** FALSIFIED — frozen for reproduction; MUST NOT activate in Laser consensus
**Reference release:** 0.2.3-falsified
**Review status:** no published independent audit or independent conforming implementation is claimed

**Changes in v0.2** (driven by findings from the reference implementation,
`photonhash-ref`): (1) requantization shift retuned to the measured product
distribution — genesis bucket width is now 256 (≈ 0.37σ), not 4096 (≈ 6σ),
restoring ~3.5 bits of requantization entropy per component; shift now
follows a defined per-era table (§5.3). (2) Section 7's analog model
replaced: the v0.1 all-components-exact target (χ ≥ 0.85) is unsatisfiable
for any physical error level, since P(all n safe) ≈ exp(−2nE/W); v0.2
specifies boundary-flagged hybrid evaluation, in which the digital-assist
fraction δ, set by analog hardware precision, caps the photonic advantage.
(3) OI-6 updated; OI-1 restated in terms of measuring δ. Test vectors are
regenerated; v0.1 vectors are obsolete.

---

## 1. Scope

This document specifies the frozen PhotonHash v0.2 proof-of-work candidate
evaluated for the Laser blockchain. This profile is not a Laser consensus
rule and must not be activated. It defines the mining and verification pipeline, genesis
parameters, the requantization rule that bridges analog optical computation and
exact digital verification, the scheduled hardness evolution, and the security
arguments and known attack surfaces. It is written to be sufficient for an
independent, bit-compatible implementation.

Non-goals: consensus rules above the PoW function (fork choice, difficulty
retargeting policy), block serialization, and the economics of emission are
specified elsewhere.

## 2. Design goals and hypotheses

PhotonHash was intended to satisfy the following properties. R1 and R5 are
directly testable construction properties; R2, R4, and R6 remain research
hypotheses unless accompanied by the evidence requested in Sections 9 and 12.
R3 is now falsified for the active n=1024 profile by the balanced exact RTX
5090 baseline. This profile must not be activated in Laser consensus.

- **R1 (Asymmetry).** Verification requires exactly one pipeline evaluation;
  mining requires an expected number of evaluations proportional to difficulty.
- **R2 (Uniformity).** Output is computationally indistinguishable from uniform
  for any adversary that cannot break the underlying hash.
- **R3 (Optical dominance; FALSIFIED for n=1024).** The matrix stage targets ≥ 90% ⚠ of
  marginal mining cost on all known hardware classes, and must map natively to
  programmable photonic linear-algebra hardware (MZI meshes, crossbar arrays).
- **R4 (Analog realizability).** A miner computing the matrix stage in analog
  hardware with bounded relative error ε ≤ ε_max (Section 7) should produce
  bit-identical final outputs to an exact digital implementation, for all but a
  negligible-and-detectable fraction of attempts.
- **R5 (Load-once, stream-many).** The expensive-to-load component (the matrix)
  MUST be fixed across the nonce search of a block template, so that
  reconfiguration cost amortizes to zero. Per-attempt data MUST be cheap to
  generate and stream.
- **R6 (No hidden substrate).** The design aims to prevent hardware classes
  other than linear-algebra accelerators (photonic or electronic) from holding
  an asymptotic
  advantage; the hardness schedule (Section 8) exists to erode electronic
  cache-resident implementations over time.

### 2.1 Related work and construction lineage

PhotonHash belongs to the line of optical proof-of-work constructions
introduced by HeavyHash and developed further by LightHash. It does not claim
the generic hash-matrix-hash pattern, low-precision photonic matrix-vector
work, or photonic proof of work as novel.

HeavyHash was introduced by Dubrovsky, Ball, and Penkovsky in
[*Optical Proof of Work*](https://arxiv.org/abs/1911.05193). Its stated design
deliberately avoids inventing an all-optical cryptographic hash: it composes an
existing digital hash with a low-precision vector-matrix weighting function
whose evaluation cost is intended to be dominated by a sufficiently large
matrix-vector product suitable for photonic acceleration.

LightHash was introduced by Pai et al. in
[*Experimental evaluation of digitally verifiable photonic computing for
blockchain and cryptocurrency*](https://doi.org/10.1364/OPTICA.476173). The
paper explicitly presents LightHash as an improvement on the HeavyHash line.
Its published construction uses SHA3-256 around a photonic matrix-vector stage,
a 256 by 256 block-diagonal integer operator assembled from tunable `N` by `N`
blocks, optical photodetection followed by binary thresholding, and an explicit
batch-size parameter `S`. It also analyzes systematic photonic error and states
a photonic-advantage criterion.

PhotonHash adopts the family-level placement of matrix-vector work between
digital hashing stages, but not either prior byte-level algorithm. The frozen
v0.2.3-falsified profile instead specifies domain-separated SHAKE256, a
parent-derived full dense 1024 by 1024 matrix, signed 4-bit matrix and vector
entries, exact `int32_t` accumulation, a 4-bit requantized value per output
component, and a final hash over both the input-binding digest and packed
requantized output. Its boundary-flagged hybrid model makes digital assist and
candidate rechecking explicit, while cross-nonce batching and amortization are
treated as attack surfaces rather than excluded by assumption.

These differences define PhotonHash's concrete review target; they do not
establish cryptographic security, hardware advantage, or novelty of the broader
construction family. PhotonHash is not wire-compatible with HeavyHash,
LightHash, or network-specific descendants such as kHeavyHash, and it inherits
no security result from them.

## 3. Notation and primitives

- `SHAKE256(m, L)` — the SHA-3 extendable-output function, first L bytes.
- `H256(m)` = `SHAKE256(m, 32)`.
- `||` — byte concatenation. Integers little-endian unless stated.
- `n` — matrix dimension for the current era (Section 8). Genesis: n = 1024 ⚠.
- All arithmetic in the matrix stage is exact signed integer arithmetic in the
  digital reference; analog implementations must meet the error budget of
  Section 7.

## 4. Pipeline overview

Two derivation domains, deliberately separated per R5:

```
                    (per block template)                (per nonce)
 chain tip hash ──► SHAKE256 ──► matrix M (n×n)   header ── nonce
                                        │                 │
                                        │          SHAKE256(header||nonce)
                                        │                 │
                                        │            vector x (n)
                                        ▼                 ▼
                                   y = M · x   ◄──── stream x through mesh
                                        │
                                requantize: r = Q(y)
                                        │
                    d = SHAKE256( h_in || r , 32 )
                                        │
                              valid iff d < target
```

- **Matrix domain.** M is derived from the previous block's hash (the chain
  tip), NOT from the nonce. It is therefore fixed for the entire nonce search
  of a block template, unpredictable before the parent block exists, and
  identical for every miner working on the same tip. Photonic miners program
  their mesh once per block (~ms-scale reconfiguration) and stream nonces
  (~ns-scale) thereafter: reconfiguration cost amortizes to zero (R5).
- **Vector domain.** x is derived from the full header including the nonce, so
  every attempt is a fresh, unpredictable input (R2), and grinding the vector
  is exactly as hard as grinding the hash.

## 5. Formal specification

### 5.1 Matrix derivation

```
seed_M   = SHAKE256( "LASER/PhotonHash/v1/matrix" || prev_block_hash, 64 )
stream   = SHAKE256( seed_M, n*n/2 )            # 4 bits per entry
M[i][j]  = nibble(stream, i*n + j) - 8          # entries in [-8, +7]
```

Entries are signed 4-bit integers ⚠. The domain-separation tag is mandatory.
Implementations MUST derive M identically; M is consensus-critical.

**Rank / degeneracy check.** With entries i.i.d. near-uniform over [-8,7], the
probability of rank-deficient M at n = 1024 is cryptographically negligible; no
regeneration rule is required. (Open item OI-3 requests independent analysis.)

### 5.2 Vector derivation

```
h_in = SHAKE256( "LASER/PhotonHash/v1/vector" || header_without_nonce || nonce, 32 )
xs   = SHAKE256( h_in, n/2 )                    # 4 bits per entry
x[i] = nibble(xs, i) - 8                        # entries in [-8, +7]
```

`h_in` doubles as the binding digest carried into the final hash (5.4), so the
matrix-stage output cannot be transplanted between attempts.

### 5.3 Matrix stage and requantization

Exact reference computation:

```
y[i] = Σ_j  M[i][j] * x[j]           # exact integer; |y[i]| ≤ 64n  (≤ 2^16 at n=1024)
```

Requantization Q keeps a 4-bit bucket index at a per-era granularity tuned to
the product distribution ⚠:

```
shift_e  = 8 + floor((era + 1) / 2)             # draft table below
r[i]  = ( (y[i] + 64n) >> shift_e ) & 0xF       # 4-bit bucket index
r     = pack_nibbles(r[0..n-1])                 # n/2 bytes
```

| Era | n     | shift_e | bucket width W | σ = √(462·n) | W/σ  |
|-----|-------|---------|----------------|--------------|------|
| 0   | 1024  | 8       | 256            | ≈ 688        | 0.37 |
| 1   | 2048  | 9       | 512            | ≈ 973        | 0.53 |
| 2   | 4096  | 9       | 512            | ≈ 1376       | 0.37 |
| 3   | 8192  | 10      | 1024           | ≈ 1946       | 0.53 |
| 4   | 16384 | 10      | 1024           | ≈ 2752       | 0.37 |

Rationale (v0.2): with entries i.i.d. on [-8,7], y[i] is approximately
Gaussian with mean n/4 and σ = √(462·n). The v0.1 width (2^(log2(n)+2), i.e.
4096 at genesis ≈ 6σ) concentrated nearly all mass into the two buckets
adjacent to zero, reducing r to ≈ 1 bit per component — confirmed empirically
by the reference implementation's test vectors. Holding W within
[0.37σ, 0.53σ] across eras yields ≈ 3.4–3.7 bits per component under the
mod-16 wrap, and materially raises the accuracy bar for approximate-evaluation
strategies (§9.2/A1). The mod-16 aliasing of a ±3σ Gaussian across ~16–32
buckets is deliberate and harmless: r need not be uniform, only expensive to
produce without the matvec; uniformity of d is supplied by the final hash.

The `+64n` offset maps y into [0, 128n], making the shift well-defined for
negative values without implementation-defined behavior.

### 5.4 Final digest and validity

```
d = SHAKE256( "LASER/PhotonHash/v1/final" || h_in || r, 32 )
valid  ⟺  little_endian_uint256(d) < target
```

### 5.5 Verification

Verification is the pipeline run once: derive M from the claimed parent (or
reuse the cached M for that parent — verifiers at a given tip cache M exactly
like miners), derive x, compute y = Mx exactly, requantize, hash, compare.
The reference API exposes `ph_verify_with_matrix` for the cached path and
`ph_verify` as a one-shot convenience function that derives and frees M.
Cost after matrix setup is one n×n integer matrix–vector product plus three
SHAKE256 calls.
Light-client note: because M depends only on the parent hash, a verifier
checking k blocks in a chain performs k matvecs; batch verification across
blocks sharing a parent (uncles) reuses M.

## 6. Cost profile (why the matrix dominates)

Per attempt at genesis parameters:

| Stage                  | Work                                      |
|------------------------|-------------------------------------------|
| Input binding          | tagged SHAKE256 over header and nonce     |
| Vector expansion       | n/2 = 512 SHAKE256 output bytes           |
| Nibble decoding        | n signed entries                          |
| Matrix–vector          | n² = 1,048,576 exact signed MACs          |
| Requantize and pack    | n components into n/2 bytes               |
| Final digest           | tagged SHAKE256 over 32 + n/2 bytes       |

R3 targets a matvec share ≥ 90% on mining-relevant hardware. The balanced
CUDA result below falsifies that target for the active profile. Earlier
scalar estimates spanning roughly 80–95% inferred matrix cost by subtracting
a hash-only baseline from the full pipeline. That baseline omitted allocation,
vector decoding, requantization, and packing, so the inferred value
overattributed cost to the matvec.

The reference benchmark now allocates scratch buffers once and times input
binding, vector expansion, decoding, the exact scalar matvec loop,
requantization and packing, and final hashing directly over batches of
distinct nonces. Results must identify CPU, compiler, flags, dimension, and
batch size. Even a correct scalar stage share does not establish mining
economics or optical advantage.

The balanced exact end-to-end CUDA baseline uses register-resident SHAKE,
autotuned exact INT8-by-INT8-to-INT32 GEMM, and cross-batch overlap. Across 75
sustained samples, GEMM consumed 11.06-12.21% of sequential device time and
the best mean eight-stream pipeline reached 33.43 million attempts/s. This
result is reproducible from `tools/ph_cuda_bench.cu` and documented in
[the RTX 5090 report](cuda-rtx5090-baseline.md). It falsifies R3 for n=1024
but does not resolve the full electronic-versus-photonic energy comparison.
The resulting non-activation decision is recorded in
[the profile decision](v0.2-profile-decision.md).

## 7. Analog evaluation: boundary-flagged hybrid discipline

This section is the heart of the design: the precise sense in which a noisy
analog computation can participate in an exact consensus system. It replaces
the v0.1 model, whose stated target (all-components-exact with probability
χ ≥ 0.85) is unsatisfiable: with per-component boundary-flip probability
p ≈ 2E/W, the all-safe probability is (1−p)^n ≈ exp(−2nE/W), which vanishes
for every physically realistic error level E at every sane bucket width W.
The reference implementation's distributional measurements forced this
correction; the v0.2 model below is both realizable and analyzable.

**Signal and noise model.** y[i] is approximately Gaussian with mean n/4 and
σ = √(462·n) (§5.3). An analog evaluator produces ỹ[i] = y[i] + e[i] with
noise e[i] of standard deviation σ_a; define the relative precision
ρ = σ_a / σ. Published silicon-photonics matvec demonstrations correspond to
ρ on the order of 0.5–1% ⚠; the analysis below is parametric in ρ.

**Boundary-flagged hybrid evaluation (reference rule for analog miners, invisible
to consensus).** The evaluator computes all n components in analog, then:

1. For each i, compute the distance g̃_i from ỹ[i] to the nearest bucket
   boundary (boundaries are at multiples of W in offset y-space; this is a
   shift and mask, not a search).
2. If g̃_i > G, accept the analog bucket. The guard band G = 6·σ_a makes a
   silent wrong-bucket acceptance a ≥ 6σ event (≈ 10⁻⁹ per component,
   ≈ 10⁻⁶ per attempt at n = 1024) — negligible and, when it occurs on a
   would-be winning attempt, caught by the standard digital re-check of
   candidate wins before broadcast.
3. If g̃_i ≤ G, recompute component i exactly in digital: one row — n MACs —
   not the full matrix.

**The digital-assist fraction δ.** The expected fraction of components
flagged for digital recomputation is

```
δ ≈ 2G / W = 12·σ_a / W = 12·ρ·(σ / W)
```

At the v0.2 operating point W ≈ 0.37σ: **δ ≈ 32·ρ**. Representative values:

| analog precision ρ | δ (digital assist) | photonic advantage cap ≈ 1/δ |
|--------------------|--------------------|-------------------------------|
| 1.0%               | ~32%               | ~3×                           |
| 0.5%               | ~16%               | ~6×                           |
| 0.2%               | ~6.4%              | ~16×                          |
| 0.1%               | ~3.2%              | ~31×                          |

Since flagged rows are recomputed digitally at full cost, Amdahl's law caps
the end-to-end photonic advantage near 1/δ even if the optical stage is free.
This is the design's honest hardware dial: δ converts analog precision
directly into economic advantage, and the reference-miner program's first
empirical task (OI-1) is measuring ρ — hence δ — on real devices. The v0.1
requirement R4 is restated accordingly: a conforming analog miner MUST
produce bit-exact broadcast solutions via the hybrid discipline plus
candidate re-check; precision affects only its private δ.

Consequences:
- **Consensus never depends on analog precision.** Every broadcast solution
  is digitally exact by construction; verifiers are oblivious to how miners
  searched.
- **The bucket-width tension is now explicit.** Narrow W (this version)
  buys requantization entropy and a higher approximation-attack bar (§9.2)
  at the price of a larger δ for a given ρ; the per-era table of §5.3 fixes
  W/σ in [0.37, 0.53], and OI-6 tracks whether a different operating point
  better balances the two against measured hardware.
- Boundary-hunting adversaries gain nothing: bucket positions are determined
  by SHAKE output and cannot be steered.

## 8. Deferred hardness evolution research

The active v0.2 experimental profile is `n = 1024` at every block height.
No dynamic era is active. The schedule below is retained only as a
research proposal; activating any part of it requires work-discontinuity and
retarget analysis, boundary vectors, independent review, and an explicitly
announced future consensus activation.

A future protocol could grow matrix dimension on a height-triggered schedule
fixed at its activation boundary ⚠:

| Era | Height range        | n     | Matrix size (4-bit) | Working set  |
|-----|---------------------|-------|---------------------|--------------|
| 0   | 0 – 6,307,199       | 1024  | 512 KiB             | L2-resident  |
| 1   | 6,307,200 – (+2 yr) | 2048  | 2 MiB               | L2/L3 edge   |
| 2   | next 2 years        | 4096  | 8 MiB               | L3-resident  |
| 3   | next 2 years        | 8192  | 32 MiB              | exceeds SRAM |
| 4+  | every 2 years       | ×2    | ×4                  | DRAM-bound   |

(6,307,200 blocks = 2 years at 10 s.) Proposed rationale: electronic implementations
are progressively pushed off-die — the matvec becomes memory-bandwidth-bound,
which is precisely the regime where optical meshes and photonic crossbars,
whose "memory" is the physical configuration of the interconnect, widen their
advantage. If activated, era transitions would be consensus-critical, known
from the activation boundary, involve
no governance action, and difficulty retargeting resets its window at each
boundary. The schedule is explicitly capped at era 10 (n = 2^20) ⚠;
the reference implementation rejects dimensions outside [1024, 2^20], and
extension beyond the cap requires a protocol revision. σ, s, and the guard analysis of Section 7 rescale with n as
would need to be specified in a future activation appendix with boundary
vectors.

## 9. Security analysis

### 9.1 Reduction skeleton

Claim: finding a valid block with fewer expected pipeline evaluations than
target/2^256 implies distinguishing SHAKE256 output from uniform or finding
structure in it. Sketch: the final digest d is SHAKE256 over (h_in || r) with
domain separation; h_in binds the exact header and nonce; r is a deterministic
function of (M, x) which are themselves SHAKE outputs of disjoint domains. Any
strategy that beats brute force must either (a) predict d without evaluating
the pipeline — a distinguisher against SHAKE256; (b) find (nonce, r′) with
r′ ≠ PhotonHash matrix output but identical d — a collision/second-preimage;
or (c) exploit structure in the M/x distributions — addressed in 9.2. A full
formal treatment in the random-oracle model is open item OI-2.

### 9.2 Attack surfaces

**A1 — Cross-nonce amortization.** M is fixed per template, so an attacker may
precompute structure on M (factorizations, low-rank approximations, sketches)
once per block and reuse it per nonce. This is the price of R5, and it is the
single most important cryptanalytic target of this specification. Defenses:
(i) an exact matvec is already only n² 4-bit MACs — approximation algorithms
(sampling, sketching) that undercut it must beat a very low bar while achieving
*bit-exact bucket outputs*, not approximate ones; the requantization tolerance
they could exploit is bounded by the same guard analysis of Section 7, and any
approximation with per-component error above E fails buckets at detectable
rates; (ii) low-rank structure in SHAKE-derived M occurs with negligible
probability; an adversary cannot choose M. Residual risk: sub-quadratic exact
algorithms for dense unstructured 4-bit matvec — none known; Strassen-family
gains apply to matrix–matrix, not matrix–vector. Status: OPEN, priority 1.

**A2 — Batched nonces as matrix–matrix.** A miner evaluating k nonces batches
X = [x₁…x_k] and computes MX, converting the workload to matrix–matrix where
Strassen-type methods, tensor-core kernels, and better hardware utilization
may apply. GPUs and photonic systems can both batch in principle, but that
fact does not establish equal constant factors, energy costs, or end-to-end
economics. The required comparison is an exact optimized electronic pipeline
(at minimum INT8 inputs with int32 accumulation, plus packed INT4 where an
exact native path exists) against a complete photonic pipeline including
modulation, detection, ADC, guard-band classification, digital row
recomputation, SHAKE generation, and candidate rechecking. Status: R3
FALSIFIED for n=1024; the full substrate comparison remains open. The
balanced exact RTX 5090 baseline reached 33.43 million mean overlapped
attempts/s and placed 11.06-12.21% of sequential device time in GEMM.
Register-resident SHAKE, packed-INT4 exploration, pipeline-depth sweeps, and
initial approximation attacks are complete. Independent reproduction and the
complete photonic comparison remain open.

**A3 — Precision cheating.** Covered by Section 7: consensus admits only
digitally exact solutions, so under-precision strategies are self-punishing
(a higher private δ under the hybrid discipline of Section 7), not
consensus-relevant.

**A4 — Era-boundary games.** At an era transition, difficulty resets its
window and hardware fleets turn over; an adversary might stockpile
next-era-optimal hardware to seize a transient hashrate majority. Mitigation:
transitions are known years in advance (symmetric information), and the
retarget reset uses a conservative initial difficulty carried over by a fixed
scaling law (Appendix A). Status: economic modeling required, OI-4.

**A5 — Verifier DoS.** Invalid blocks cost the verifier one matvec (~1 ms).
Standard header-first validation ordering (check target on the claimed d
before recomputing, check parent existence, rate-limit by peer) bounds
exposure. At era 4+ dimensions the verification matvec grows; the schedule
caps verification cost growth at ×4 per era, and OI-5 tracks whether a
succinct-proof verification path should ship before era 3.

**A6 — Parent-hash grinding / future-matrix bias.** Because M derives from
the parent block hash, the miner of block k has limited influence over the
matrix faced at block k+1: if it finds multiple valid solutions before
broadcasting, it may choose among the resulting parent hashes; it could also
withhold a found block while searching for an alternative. Exploitation
requires (i) paying full PoW cost per additional candidate parent — choice
among c candidates costs c× the expected block cost — and (ii) the existence
of an efficiently testable "hardware-favorable matrix" property of
SHAKE-derived matrices, which is conjecturally absent (the same conjecture as
OI-3: SHAKE-derived M is spectrally and structurally generic). The expected
economic gain per candidate is therefore bounded by the marginal advantage of
one generic random matrix over another, which the design conjectures to be
nil. Named here so the conjecture is explicit; distributional analysis under
OI-3 covers it. Status: OPEN, priority 3.

### 9.3 Explicit non-claims

PhotonHash does not claim memory-hardness in the Argon2 sense, ASIC-proofness
(a photonic ASIC is the *goal*), or quantum-hardness beyond Grover-limited
generic search (target sizing accounts for the quadratic speedup).

## 10. Reference implementation profile

- **Digital reference (shared review oracle):** portable C, exact integer
  matvec, constant output across platforms; disagreements between prose and
  implementation are review findings to resolve before any future freeze.
- **Measured GPU baseline:** the bundled exact CUDA path uses batched INT8
  inputs with `int32` accumulation and includes on-device SHAKE, decoding,
  requantization, final hashing, and target comparison. Its RTX 5090 result is
  documented in [the measurement report](cuda-rtx5090-baseline.md). Packed
  INT4 kernels remain an optimization target where the device exposes a
  suitable exact path (A2).
- **Photonic target profile:** matrix programmed to mesh once per template
  (per R5); vectors modulated at line rate; candidate-check discipline of
  Section 7 implemented in the driver, not the device.

## 11. Test vectors

Appendix A vectors are bundled with the frozen reference implementation
(`photonhash-ref` 0.2.3-falsified): five end-to-end vectors (parent hash → M checksum →
h_in → x → y → r → d) at n = 1024, generated deterministically from fixed
ASCII labels. They reproduce byte-for-byte from the bundled generator. No
published independent conforming implementation is claimed yet. The vectors
freeze the nibble convention, domain tags, offsets, and the v0.2 shift rule.
They are normative only for reproducing this falsified research profile and
have no Laser consensus status.

## 12. Open items for cryptanalysis

| ID   | Question                                                             | Priority |
|------|----------------------------------------------------------------------|----------|
| OI-1 | Measure ρ and δ (Section 7) on real photonic matvec hardware          | High     |
| OI-2 | Formal ROM security proof of the sandwich construction                | High     |
| OI-3 | Independently reproduce and extend the bundled matrix corpus          | Medium   |
| OI-4 | Era-transition economic/game-theoretic modeling                       | Medium   |
| OI-5 | Succinct verification path for large-n eras                           | Medium   |
| OI-6 | W/σ operating point: entropy & attack bar vs δ, against measured ρ    | High     |

Adversarial analysis of A1 in particular is solicited: a sub-quadratic exact
strategy for fresh-vector, fixed-random-matrix products would break the
design's economics and must be investigated before any successor activation.

---

*This specification and its vectors are frozen as the reproduction oracle for
the falsified v0.2 profile. They are not Laser consensus rules. Parameters
marked ⚠ identify the provisional assumptions that failed or remain open for
successor research.*
