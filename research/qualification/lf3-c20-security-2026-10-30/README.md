# LF3-K8-C20 security review checkpoint

30 October 2026 UTC. **Experimental assessment; no candidate freeze or activation.**
The [construction](../../../docs/lf3-k8-c20-experiment-1.md) retains SHAKE
binding and final hashing; ChaCha20 replaces only the vector expander.
[Four-way conformance](../lf3-c20-2026-10-30/README.md) is separate from
cryptographic security and mining economics. Every numerical observation below
is labeled measured; calculations, assumptions and projections are inferred.

## Disposition of the requested checks

| Item | Status | What the evidence establishes; what remains open |
|---|---|---|
| Header/nonce binding and key derivation | PASS construction/conformance; OPEN grinding economics | ChaCha keys are SHAKE outputs of the tagged header and nonce. Selecting among trial outputs is possible; freely prescribing a key is not supplied by the API. No universal grinding lower bound is proved. |
| Parent grinding | PASS finite screening; OPEN general claim | Full statistics on 1,024 measured banks reveal no demonstrated cheap-bank shortcut. Full-matrix ranks and mapped sparse/grinding energy remain unmeasured. |
| Partial work and early abort | PASS tested corpus; OPEN lower bound | Final SHAKE consumes the entire fold. Every tested column/bit/pass omission produced zero measured complete-fold successes. This does not rule out every exact algebraic or amortized algorithm. |
| Exact modular arithmetic | PASS identity; hardware economics | Only the residue modulo 8192 is necessary. Narrow wrapping arithmetic is valid; its physical implementation cost is provisional. |
| Approximation/noise | PASS finite probability tests; OPEN physical energy | No tested method demonstrates an energy-per-correct-fold advantage. A real device can win if its energy ratio is below its measured fold-survival probability. |
| Existing adversarial corpus | PASS finite regression | The full existing analysis was adapted only to the C20 expander; original attack configurations were retained. |
| Cache admission | PASS existing LF2 library separation; OPEN C20 caller integration | A prepared-cache miss does not derive a bank. C20 currently accepts a supplied bank; chain admission, scheduling and anti-thrash policy are not integrated. |

PASS means the stated finite check passed. It does not turn an OPEN claim into
a proof. No energy-saving work-avoiding shortcut has been demonstrated by this
study. Exact packing/fusion is an implementation gain; exact narrower arithmetic
is a hardware-economics finding under the reviewer's clarified rule.

## Grinding: what SHAKE does and does not guarantee

The configured binding is
`h = SHAKE256(tag || opaque_header || LE64(nonce), 32)`. The C, CUDA, Python
and Rust paths agree on it. The public `h` is the ChaCha key; the ChaCha nonce
and block counters follow [RFC 8439](https://www.rfc-editor.org/rfc/rfc8439).
There is no caller-supplied direct-key bypass in the hash construction.

Under a SHAKE preimage assumption, prescribing one particular key costs an
inferred search over its preimages. That does **not** prohibit a miner from
trying many headers/nonces, then choosing a favorable SHAKE output or vector.
Public-key use of ChaCha here is an expander, not a secret-key security claim.
Neither the RFC nor full-fold agreement proves the resulting matrix workload
has an optimal mining cost. The team needs external review of key/vector
screening, batching, precomputation and amortization before asserting that
grinding offers no structural advantage.

The parent bank is derived through SHAKE domains distinct from the C20
header/nonce binding. A miner can choose block contents and search block hashes;
it cannot simply pass an arbitrary cheap bank as a valid parent to a correctly
integrated chain. Searching valid parents, withholding winners, screening
partial bank statistics and choosing vectors nevertheless require an economic
analysis. This checkpoint does not assume that every bank has identical cost.

An opaque header is not a block-header consensus contract. Agreement between
the passed parent and the serialized header, parent admission, header length
and canonical serialization remain integration items for the team.

## Parent-bank screening

[parent-screen.json](parent-screen.json) records the configured deterministic
parent derivation and every measured parent statistic; the
[summary](parent-screen-summary.json) preserves ranges and medians. The screen
covered **1,024 measured parents**, each with **134,217,728 measured
coefficients** and all row sums. These are screening data, not live-chain data.

| Statistic across banks | Measured result |
|---|---:|
| Zero-coefficient fraction, minimum / median / maximum | 0.06242181 / 0.06250004 / 0.06257459 |
| Two's-complement int4 one-bits per coefficient, minimum / maximum | 1.99970985 / 2.00026451 |
| Mean row sum, minimum / maximum | -2053.74487 / -2043.12683 |
| Within-bank row-sum standard deviation, minimum / maximum | 291.57991 / 298.03028 |
| Largest coefficient-bin probability deviation from 1/16 | 0.00008312 |

Rank checks sampled four configured 64-by-64 GF(2) minors in each matrix.
Measured counts were: rank 61, 181 minors; rank 62, 4,240; rank 63, 18,908;
rank 64, 9,439. These **32,768 measured minors** do not establish the ranks of
the full matrices. Separately, the existing adversarial analysis measured
rank 512 for each of two sampled real 512-by-512 minors. Neither observation
is a whole-bank rank proof.

The measured sparsity spread supplies no demonstrated large cheap-parent
effect. It also does not measure the cost of exploiting the ordinary zeros
present in every bank or vector. Sparse scheduling, zero gating, vector
screening and their overhead must be compared in energy per correct attempt;
coefficient counts alone are not joules. Constant-cost dense GPU kernels
cannot establish the economics of a specialized sparse device. These remain
OPEN rather than being dismissed using the average bank statistics.

Screening CPU times were collected under contention and are **not** the
authoritative parent-turnover or verification timings.

## Complete fold, partial work and entropy

The final hash absorbs `h` and all **2048 configured fold bytes**, representing
**4096 configured nibbles**. An implementation must produce the correct entire
fold, or an equivalent final computation. It need not materialize the packed
intermediate. Under an idealized SHAKE assumption, there is no exposed final
target prefix on which to base a profitable early abort before the required
fold information is available. This is an assumption about the final binding,
not a proved lower bound on computing that information.

[c20-adversarial.json](c20-adversarial.json) retains the complete existing
analysis. Configured attack coverage used 32 vectors per setting, seven
column-retention fractions, three coefficient-bit drops and seven omitted-pass
counts. Every setting had **zero measured complete-fold successes out of 32**.
Some nibbles survived; that is not a valid complete fold. Correlation, spectral,
compression and sampled-minor analyses were retained rather than dropping
unfavorable tests.

The larger noise study used **1,024 measured nonces on each of two nonzero
parents**, with zero skipped cases. Measured per-pass marginal entropy ranged
from **3.46787 to 3.47023 bits per nibble**; measured folded marginal entropies
were **3.99991688** and **3.99993574**. Measured sum standard deviations were
**1376.23491** and **1375.86976**, much wider than the configured 512-unit bins.
The eight-pass XOR flattens the observed marginal bias. Marginal entropy does
not establish independence, a joint entropy equal to the fold length, or a
cryptographic work lower bound. The expanded vector and fold are deterministic
functions of a 256-bit binding and a parent bank.

## Approximation criterion and photonic tolerance

The earlier statement that every approximate sum changes the fold is false.
Quantization is many-to-one, and errors between passes can cancel in the XOR.
The requirement is the **exact final fold**. With `P` denoting its survival
probability, the relevant criterion is

```text
E_method / P(exact fold) < E_exact
```

[The complete table](approximation-tables.md) covers **32 configured settings**:
random ±1 errors, rounded and raw-threshold Gaussian noise, final low-bit
truncation, dropped small nonzero products, chunked reduced-precision/saturating
accumulation and modular wrapping controls. Each setting has **1,024 measured
nonces per parent**. [Raw observations](approximation-extended.jsonl) include
per-parent probabilities, inferred Wilson intervals, inferred energy models,
all zero-success settings and applicability limitations.

Measured pooled survival was **0.929199** for ±1 on a configured 0.1% of sums,
**0.516602** for ±1 on 1%, and **0.047363** for ±1 on 5%. Rounded Gaussian noise
with configured sigma 0.25 gave **0.051758 measured survival**. These are
probabilities, not measured analog-device energy savings.

For injecting errors after doing the exact work, the explicitly optimistic
inferred energy ratio is 1, excluding injection overhead: no energy advantage
is established. The dropped-product models removed measured MAC fractions of
about **1.56%, 4.69% and 12.51%**. Even a favorable inferred model with free
pruning and all energy proportional to retained MACs gave ratios about
**0.9844, 0.9531 and 0.8750**, with **zero measured exact folds out of 2,048**
for each setting. Physical FP16, saturating and narrow-ASIC energy was not
measured. Zero observed successes is not a mathematical zero probability.

The inferred small-error heuristic is
`P ≈ exp(-sum(E|e_i|)/512)` across the configured 32,768 sums. All pooled
small-noise predictions fell inside their inferred Wilson intervals in this
study; **four measured parent/setting comparisons** did not. The
[model-check ledger](approximation-model-check.json) retains those deviations.
This supports an approximate conditional model, not a formal guarantee or a
bound for phase-correlated, structured or large errors.

The photonic table includes inferred tolerances for losing 10%, 50% and 90%
of winning blocks, with measured confirmation probabilities on both parents.
For the rounded-integer model, inferred ±1 error rates per sum are
**0.1646258%, 1.0830425% and 3.5977892%** respectively. Inferred Gaussian sigmas
are **0.158851996, 0.196222859 and 0.238415714** integer dot-sum units.
Those thresholds do not establish optical precision or energy at scale.

Calibration is consequential: raw floor-threshold Gaussian noise with
configured sigma 0.01 produced **zero measured exact folds on either parent**.
An integer sum can sit exactly at a bin boundary. A calibrated nearest-integer
decision and an unshifted analog threshold are different physical systems;
the more favorable rounded-noise table cannot be silently assigned to either.
Actual photonic energy, calibration stability and correction overhead remain
OPEN. No physical photonic miner was measured.

## Exact arithmetic and ASIC economics

The quantizer is `q = (y >> 9) & 15` with the specified unsigned/modular
interpretation. Adding the existing bias does not change those bits.
Reduction modulo **8192** commutes with exact integer multiplication and
addition, so **13 residue bits** suffice. The remote identity check covered
**491,521 measured integer values** across the entire inferred conservative
sum range **[-229376, 262144]**, with zero mod-8192 disagreements. This is a
superset of the sums actually reachable from the generated banks, not a claim
that every integer is reachable. Covering the worst-case coefficient-domain
bound needs **20 inferred signed bits**: 19 signed bits miss its positive
endpoint. Wrapping 13-bit arithmetic and saturating 13-bit arithmetic are
different; the latter failed the measured noise study.

[additional-checks.json](additional-checks.json) retains the full-range identity
record, the expected insufficient 12-bit negative control, the prepared-cache
miss batches and the portable-harness smoke receipt. The prepared-cache check
used **1,015,808 measured misses** against a populated two-parent LF2 cache,
with no measured generation or occupancy change. It proves that API path does
not prepare an unknown bank; it does not prove C20 network admission safety.

The extension to the working `ph_lf2_hardware_model.py` is exported here as the
isolated [modular datapath model](modular-datapath-model.json), avoiding unrelated
historical hardware baselines. It is an **inferred sensitivity model**, not
synthesis, a cell-library mapping or silicon energy measurement.

The assumed cost is `shared_int4_product_cost + accumulator_bits × (9 + 6)`
NAND equivalents, where both adder and clocked-bit costs are explicit proxies.
With assumed shared product cost 140, inferred counts are **335** for 13 bits,
**440** for 20 bits and **620** for 32 bits. The inferred 13/32 ratio is
**0.5403**; varying the assumed product cost from 60 to 220 gives an inferred
range **0.4722–0.5929**. The central inferred 13/20 ratio is **0.7614**.

Equal switching activity/capacitance would give the same inferred datapath
energy ratio; neither equality nor the ratio is measured. SRAM/HBM, SHAKE,
vector expansion, folding, I/O, routing, voltage, clock gating, leakage and
bank reload costs are excluded. GPU matrix-time share cannot be substituted
for their energy share. A smaller exact electronic ASIC datapath can change
mining economics substantially; it is not an approximation attack or a reason
to stop under the clarified rule. Actual mapped ASIC cost and energy ratios,
and any photonic advantage over that ASIC, remain OPEN.

## Reproduction and publication limits

`reviewer-approx.py` is the original supplied experiment, with measured SHA-256
`3619c29ebb7c530df596fa45fb205063a2578a55e282edd4eaf9f8e67307e64a`.
Its previously reported zero-parent run is not rerun or counted here.
`approximation-study.py` is a portable adaptation of the remote extended
harness: checker/output paths and sample count are arguments; the arithmetic,
noise generation and energy assumptions are unchanged. A remote four-nonce
smoke run exercised its code paths; that small run is ineligible as a new
qualification probability estimate. The published authoritative measurements
remain the two-parent extended run above.

The default study requires substantial CPU time and several GB of memory.
Run it only on authorized hardware; the owner's local research execution is
disabled. With the measured NumPy version installed:

```sh
python -m pip install numpy==2.5.4
python research/qualification/lf3-c20-security-2026-10-30/approximation-study.py \
  --output /tmp/c20-noise-new-run.jsonl
```

The default configured count is 1024 nonces per parent. Existing output files
are never overwritten. A demonstrated work-avoiding advantage prints STOP and
exits immediately. Full C/CUDA kernels remain outside this completed
documentation/evidence workstream pending the conditional candidate freeze.
No integration contract or activation decision is made by this review.

[security-SHA256SUMS](security-SHA256SUMS) records these public evidence files;
it is not a candidate freeze manifest. Original logs and unsuccessful runs
remain in the qualification ledger and retained raw evidence.
