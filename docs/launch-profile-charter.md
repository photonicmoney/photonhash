# PhotonHash launch-profile research charter

Status: **active non-consensus engineering charter, revision 2**
Date: 2026-07-26
Scope: a possible Laser genesis proof of work

## Purpose

This program asks whether Laser can launch with an exact, secure,
matrix-centric proof of work that is electronically mineable today and
naturally addressable by future photonic hardware.

It does **not** require a photonic miner to outperform GPUs before launch and
does not claim that current photonic hardware has demonstrated an end-to-end
mining advantage.

PhotonHash v0.2 remains frozen as a falsified profile. Its optimized RTX 5090
pipeline placed only about 11--12 percent of device time in the matrix stage.
The approximately 1.14 figure was the optimistic whole-system ceiling if that
matrix stage became free, not the measured matrix share.

This charter defines a different objective openly. It does not reinterpret the
v0.2 result or weaken the separate standard for claiming photonic superiority.

## Launch objective

Place a substantial, measured fraction of every optimized electronic mining
attempt in exact low-precision matrix work while preserving:

- deterministic CPU and GPU execution;
- practical commodity-GPU mining;
- bounded memory and inexpensive ordinary-node verification;
- cryptographic binding of the parent, header, nonce, matrix work, and output;
- resistance to batching, fusion, partial-work, approximation, and state-reuse
  shortcuts; and
- a physical workload that a future photonic matrix engine can execute without
  recurrent exact-regeneration loops.

The launch family is feed-forward with no recurrent state boundary:

~~~text
parent, header, nonce
        |
cryptographic expansion
        |
one large parent matrix or a parent-derived matrix bank
        |
exact output conversion and combination
        |
final cryptographic digest
~~~

## Launch gates

All gates are required before a profile can be proposed for consensus.

### L1: exactness and reproducibility

- A portable integer reference and an optimized GPU implementation agree on
  frozen normal, boundary, malformed, and maximum-nonce vectors.
- At least one independent implementation reproduces every vector.
- Sanitizers, differential tests, and cross-platform tests pass.

### L2: measured matrix centrality

The strongest electronic implementation must report separately:

- cryptographic expansion and vector generation;
- exact matrix work;
- output conversion and final hashing;
- overlapped end-to-end throughput; and
- board energy per attempt.

Decision bands:

- below 40 percent matrix share: reject as insufficiently matrix-centric;
- 40--50 percent: research-only;
- at least 50 percent: eligible for launch consideration;
- at least 60 percent: strong launch result;
- at least 80 percent: desirable, not required.

Time share is an early screen. Launch evidence requires energy attribution or a
conservative energy model tied to measured board power and stage utilization.
The comparison target is the best batched and fused GPU implementation found,
not a scalar oracle.

### L3: security and work integrity

No practical advantage may arise from:

- precomputing or compressing the parent matrix;
- deriving only selected rows or columns;
- low-rank, sparse, sampled, sketched, or approximate products;
- omitting outputs and relying on final-hash luck;
- reusing work across nonces beyond intended matrix residency;
- algebraic collapse between independent passes;
- relaxed quantization followed by selective recheck; or
- short cycles, biased outputs, or structurally related nonce vectors.

The final digest must bind every required matrix output so that a valid attempt
requires the declared work.

### L4: launch practicality

- Genesis mining remains viable on commodity GPUs.
- Miner and verifier memory are explicitly bounded.
- A verifier caches the parent matrix and performs only the work needed for one
  claimed block.
- Cached verification should target less than 250 ms on a representative
  ordinary modern CPU; cold parent setup should target less than 2 seconds.
  Measured results, not these targets alone, decide practicality.
- A non-consensus public testnet completes sustained operation, difficulty
  adjustment, reorg, malformed-block, and denial-of-service testing.

### L5: review and activation

- Two independently written exact implementations exist.
- The construction, vectors, electronic benchmark, shortcut analysis, and
  verification measurements receive public review.
- Activation requires a separate Laser consensus decision. Passing this
  charter does not activate a profile automatically.

## Separate photonic-superiority gates

Matrix share is photonic headroom, not proof of photonic advantage. Laser may
claim measured photonic mining superiority only after a complete system is
measured over the same valid attempt:

~~~text
A_system = J_electronic_valid_attempt / J_photonic_valid_attempt
~~~

The photonic denominator includes matrix computation, light sources,
modulation, detection, conversion, control, calibration, digital assistance,
hashing, correction, rechecks, and failed trajectories.

- at least 3x: credible research superiority;
- about 5x: strong commercial or consensus-transition result;
- 10x: exceptional light-money result.

These claims are not prerequisites for the launch-profile research program.
They remain prerequisites for the corresponding public claims.

Each physical matrix output and its exact conversion must be counted. "No
recurrent boundary" does not mean that a multi-matrix optical implementation
gets free detection or conversion.

## Candidate sequence

LF1 retains the v0.2 one-boundary byte pipeline as an instrumented starting
point but increases the parent-matrix dimension. It is not a specification.

The initial sweep covers dimensions 1024, 2048, 4096, 8192, and 16384 where
memory and verification cost permit. It measures the best batched GPU pipeline,
matrix share, board energy, resident matrix size, throughput, and cached CPU
verification cost.

Only after the dimension sweep will the program decide whether multiple
independently derived vectors are necessary. Extra vectors receive no credit if
their expansion and output hashing scale proportionally or if their relation
admits shared-work shortcuts.

LF1 was rejected after the 2026-07-26 dimension sweep peaked below 40% matrix
share. LF2-K8 now advances as the first provisional candidate: one nonce vector
is evaluated against eight independently parent-derived 4096 by 4096 matrices,
the exact requantized outputs are XOR-folded, and one final SHAKE256 binds the
fold. Its first RTX 5090 screen measured about 61.7% matrix time. This result
opens L2 continuation only; it does not satisfy L1, L3, L5, or activate a
consensus profile. See `docs/launch-profile-lf2-first-pass.md`.

## Change control

This charter may be revised while the launch program is non-consensus, but each
change must identify the affected gate, preserve the frozen v0.2 and v0.3
results, and re-evaluate all surviving launch candidates. Thresholds must not be
lowered merely because a favored candidate failed.
