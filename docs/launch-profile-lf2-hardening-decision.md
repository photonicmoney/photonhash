# LF2-K8 hardening decision

Date: 2026-07-26
Candidate: frozen LF2-K8  
Decision: **not launch-ready; advance only to a public non-consensus shadow
testnet**

The surviving construction is now identified as PhotonHash
v0.4.0-shadow.1. This version assignment does not change the frozen output
bytes or the decision below.

## Executive result

LF2-K8 remains a serious provisional launch candidate. An independently
structured Rust implementation reproduced the frozen matrix seeds, complete
matrix checksums, intermediate h values, 2048-byte folded states, final
digests, and target semantics without linking the C implementation. Strict C
tests and vectors also pass.

The expanded attacks found no useful omission, truncation, compression,
sampled-column, coefficient-bit, or simple bit-sliced shortcut. The strongest
measured RTX 5090 path still places 61.55--61.98% of serialized device time in
one exact stacked GEMM.

That is enough to preserve LF2-K8 and start public shadow testing. It is not
enough to activate consensus. Cross-hardware mining, a real public testnet,
energy attribution, an LF2-specific FPGA implementation, and post-layout ASIC
analysis do not yet exist.

The result supports this narrow claim:

> LF2-K8 is an exact, feed-forward, matrix-centric proof-of-work candidate on
> the measured RTX 5090 implementation.

It does not support a claim that any photonic miner is currently faster or
more energy efficient.

## Frozen construction

The candidate is frozen by
research/launch/lf2-k8-freeze-20260726.json. Parameter tuning is closed.
Any semantic change creates a new candidate identifier and reruns every gate.
The frozen profile uses n=4096, eight independently parent-derived matrices,
exact signed 4-bit inputs and int32_t accumulation, exact requantization,
XOR folding, and one final SHAKE256.

## Independent implementation

independent/rust-lf2 is a clean RustCrypto-based implementation. It consumes
only the published construction and vector file. Its iterator/chunk
organization is not copied from the C control flow and it does not call C.

On the Ryzen 7 9800X3D host:

- all Rust tests passed;
- all four frozen cases and all intermediate artifacts matched;
- complete matrix derivation took 0.228 seconds; and
- hashing the four cases took 0.056 seconds, or 13.906 ms per case in the
  independent audit implementation.

This satisfies the implementation-diversity part of L1 on one platform. It
does not replace Linux, macOS, big-endian, alternate-compiler, and independent
GPU evidence.

## Structural and partial-work attacks

The principal attack corpus used 32 nonce vectors and the complete 4096 by
4096 by eight bank.

| Probe | Result |
|---|---|
| Matrix entry distribution | chi-square 10.87 with 15 degrees of freedom |
| Packed-bank compression | mean zlib ratio 1.000305 |
| Cross-matrix sampled correlation | maximum absolute 0.00291 over 1,000,000 entries |
| Sampled 512 by 512 minors | both full rank |
| Folded-state entropy | 3.999832 bits per nibble |
| Omit one whole pass | 14.58% nibble accuracy; 0/32 exact states |
| Keep best 99.22% of columns | 81.81% pass-bucket accuracy; 30.31% folded-nibble accuracy; 0/32 exact states |
| Drop one coefficient bit | 7.18% folded-nibble accuracy; 0/32 exact states |
| Guess one omitted output row | about 6.41% exact-nibble probability for only 1/4096 work saved |

The final SHAKE binds the entire folded state. Under the standard random-oracle
model, one wrong folded bit makes a partial evaluator unable to identify a
valid nonce. It may submit guesses to a full verifier, but that externalizes
the missing work as a denial-of-service attempt rather than creating valid
mining work. Verifier admission and rate limiting still require testnet study.

These experiments are tripwires, not a proof that no stronger algebraic or
statistical attack exists.

## Exact electronic alternatives

An exact two's-complement bit-sliced CPU implementation stores the bank in
64 MiB and replaces the products with 33,554,432 64-bit AND-popcount
reductions per attempt. It matched the reference fold and digest.

Across two runs it was 0.97x to 1.05x the speed of the optimized portable
int8_t CPU path, after a 1.27-second one-time packing step. This is not a
practical CPU shortcut. It is, however, a concrete circuit decomposition that
an FPGA or ASIC could exploit, so the electronic baseline cannot stop at
cuBLAS.

Still untested are a packed-INT4 tensor path, an LF2-specific CUTLASS epilogue,
and a post-route FPGA design.

## Matrix-bank lifetime and amortization

Laser's intended block interval is ten seconds. The parent hash prevents
precomputation of the next bank before the parent is known under SHAKE's
preimage assumption, but the full bank is reusable across every nonce for that
parent. This reuse is intended and is already granted to the RTX 5090
adversary through a resident stacked matrix and large batches.

Measured cold derivation consumes:

| Path | Setup | Fraction of a 10 s parent lifetime |
|---|---:|---:|
| Independent Rust derivation | 0.228 s | 2.28% |
| Portable C derivation | 0.48--0.50 s | 4.8--5.0% |
| CPU bit-slice packing after derivation | 1.27 s | 12.7% |

Setup approaches zero per attempt at mining scale, so it must not be charged
to every nonce. It remains important at every tip transition. A miner that
finds the parent learns the next bank first, and a slow setup path compounds
the normal propagation advantage. Before launch, matrix derivation and device
transfer must be measured on every mining backend, overlapped where possible,
and included in orphan and centralization simulations.

No cross-parent matrix reuse or useful compression was found. The absence of a
shortcut in this corpus is not a proof against incremental SHAKE hardware or a
future related-parent attack.

## FPGA and ASIC screen

tools/ph_lf2_hardware_model.py makes the assumptions explicit. LF2 performs
134,217,728 exact MACs per attempt and needs a 64 MiB packed or 128 MiB
unpacked resident bank.

Vendor peaks are only ceilings. An Agilex 7 M claim of 88.6 INT8 TOPS maps to
roughly 330,000--660,000 LF2 attempts per second depending on whether one MAC
is counted as two vendor operations or one, before SHAKE, folding, routing,
and utilization losses. The measured RTX 5090 pipeline reaches about
1.80 million serialized attempts per second.

Without reuse, a 64 MiB bank limits 1 TB/s HBM to about 14,901 attempts per
second. Batched reuse removes that simple bandwidth bottleneck, leaving exact
accumulation, routing, and the epilogue as the FPGA questions.

The ASIC model is intentionally a sensitivity sweep, not a forecast. At an
assumed 0.01--1 pJ per exact MAC, matrix arithmetic alone spans 1.34--134.22
microjoules per attempt, excluding memory, SHAKE, control, I/O, cooling, and
yield. This wide range shows why a purpose-built electronic ASIC must be the
eventual photonic comparison target. It does not establish an ASIC result.

Official parameter sources:

- Altera Agilex 7 M:
  https://www.intel.com/content/www/us/en/products/details/fpga/agilex/7/m-series.html
- AMD Versal HBM:
  https://www.amd.com/en/products/adaptive-socs-and-fpgas/versal/hbm-series.html
- AMD Versal INT8 DSP mode:
  https://docs.amd.com/r/en-US/am004-versal-dsp-engine/Dot-Product-Unit

## Gate decision

| Gate | Status | Reason |
|---|---|---|
| L1 exactness | partial pass | C, CUDA, and independent Rust agree; platform diversity and supported sanitizer evidence remain incomplete |
| L2 matrix centrality | provisional pass | 61.55--61.98% RTX 5090 GEMM-time share; no matrix-stage energy attribution and no cross-GPU result |
| L3 work integrity | provisional pass | expanded attacks are negative; no proof, FPGA synthesis, packed-INT4, or fused LF2 epilogue |
| L4 practicality | fail/incomplete | CPU verification passes targets, but no public testnet or commodity cross-hardware mining corpus |
| L5 review and activation | fail/incomplete | no public hardening review and no separate Laser activation process |
| Photonic superiority | not evaluated | no complete photonic miner measurement; not a launch prerequisite and no claim is allowed |

## Explicit launch-readiness decision

**NO-GO for Laser consensus or genesis activation.**

**GO for publishing the frozen candidate and running a non-consensus public
shadow testnet.**

LF2-K8 may return for a launch decision only after:

1. the same frozen vectors pass on independent Linux, macOS, and Windows
   builds and on at least two commodity GPU families;
2. packed-INT4, fused-epilogue, FPGA, and ASIC adversaries are either measured
   or conservatively bounded;
3. matrix setup, propagation, reorg, stale-work, and verifier-flood behavior
   survive a public shadow testnet;
4. board energy is measured across the full valid-attempt pipeline and is not
   described as photonic energy advantage; and
5. public reviewers receive the construction, vectors, raw logs, and attack
   code before any separate Laser consensus proposal.

Laser consensus remains untouched.
