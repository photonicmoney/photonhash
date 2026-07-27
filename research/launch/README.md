# PhotonHash v0.4 shadownet evidence workspace

Status: **LF2-K8 frozen as v0.4.0-shadow.1; non-consensus**

This workspace is separate from the frozen v0.2 profile and the v0.3
photonic-superiority boundary program.

The governing documents are the
[v0.4 specification](../../docs/spec-v0.4-shadow.md),
[shadownet protocol](../../docs/shadownet-protocol.md), and
[launch-profile charter](../../docs/launch-profile-charter.md).

## Current result

LF1 tested whether dimension alone could rescue matrix centrality. It could
not: the strongest point in the initial RTX 5090 sweep was about 30% GEMM time.
LF1 is rejected.

LF2-K8 is a frozen provisional launch candidate:

~~~text
h = SHAKE256(header || nonce)
x = low_nibbles(SHAKE256-XOF(h))
y[j] = M[j](parent) * x                  j = 0..7
q[j] = exact_requantize(y[j])
r = q[0] XOR q[1] XOR ... XOR q[7]
d = SHAKE256(LF2-final-tag || h || r)
~~~

The eight parent matrices are stacked into one tall matrix for the adversarial
GPU implementation. This permits one cuBLAS call across all nonce vectors and
does not rely on inefficient separate launches.

At `n=4096`, batch 8192, LF2-K8 measured 61.55--61.98% exact GEMM time across
three parent datasets. Cached scalar verification was 2.14 ms and cold matrix
setup was 497 ms on a Ryzen 7 9800X3D. Initial omission and simple-collapse
experiments produced no exact folded vectors.

See the [first-pass report](../../docs/launch-profile-lf2-first-pass.md) and
machine-readable evidence in this directory.

LF2-K8 now has the non-consensus version identity v0.4.0-shadow.1. This is a
shadownet protocol version, not a Laser consensus version. The first
hardening phase reproduced the frozen vectors in an independently structured
Rust implementation and found no useful shortcut in the tested omission,
partial-column, coefficient-bit, compression, or exact bit-sliced attacks.

The explicit decision remains **no-go for consensus, go for a public
non-consensus shadow testnet**. See the
[hardening decision](../../docs/launch-profile-lf2-hardening-decision.md) and
[readiness ledger](../../docs/shadownet-readiness.md).

The remaining questions are:

1. Can a packed-INT4 path, fused custom epilogue, FPGA, or ASIC implementation
   materially change the electronic baseline?
2. Do commodity GPUs from multiple vendors retain practical mining?
3. Does a public shadow testnet survive bank turnover, reorgs, stale work, and
   verifier floods without cross-implementation disagreement?
4. Does an eight-pass physical optical path retain any advantage after every
   detector, exact conversion, matrix-programming, and modulation cost?

Raw measurements and generated summaries belong here. Every result
must record source revision, commands, CUDA and driver versions, batch size,
power boundary, and whether the number is time share or energy share.

No result in this directory changes Laser consensus.
