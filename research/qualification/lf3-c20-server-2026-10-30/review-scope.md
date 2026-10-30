# Outside qualification review: LF3-K8-C20

This is a review scope, not an audit result, bounty commitment, candidate
freeze or activation proposal. The construction under review retains the
`LF3-K8-C20-experiment.1` tags. The team's integration decisions remain open.

The existing [construction](../../../docs/lf3-k8-c20-experiment-1.md),
[conformance package](../lf3-c20-2026-10-30/README.md),
[security evidence](../lf3-c20-security-2026-10-30/README.md),
[verifier laboratory](../lf3-c20-verifier-2026-10-30/README.md), and
[mapped arithmetic](../lf3-c20-mapped-arithmetic-2026-10-30/README.md)
provide the starting material. CPU research sources are public; the current
CUDA research kernels remain outside this pre-freeze evidence selection.
That limits independent GPU reproduction until the source publication step.

## Cryptographic and work-economics review

Assess whether a miner can lower energy per exact final fold through key/vector
screening, parent selection, precomputation, batching, partial evaluation or
structure in the fixed bank. SHAKE binding prevents a caller from simply
prescribing the ChaCha key; it does not by itself prove that selecting among
many generated keys has no advantage. Full-fold agreement and high marginal
nibble entropy are correctness/statistical evidence, not work lower bounds.

Separate one-time work per parent from work per nonce. State the expected
number of attempts over which a table, circuit configuration or bank conversion
is amortized; sweep that parameter rather than selecting a difficulty policy.
Include preprocessing, memory capacity/bandwidth, transfers, control, filtering,
failed trials and discarded blocks in the energy comparison. Parent grinding
must respect whatever valid-parent/header relationship the team eventually
adopts, including the opportunity cost of withholding a valid block.

Ordinary zero coefficients and small vector terms need an execution-cost
analysis, not just a sparsity histogram. Test algebraic/lookup/bitsliced schemes
against full folds on multiple parents. Distinguish an exact cheaper arithmetic
representation from skipping required work by exploiting banks or vectors.
If approximation is proposed, compare `E_method / P(exact fold)` with exact
evaluation. Correlated errors, calibration shifts, XOR cancellation, vector
selection and rare favorable inputs are outside the simple independent-error
heuristic and deserve explicit treatment.

Deliver a reproducible attack or a clearly bounded negative result, with the
attack model, hardware, sample coverage, preprocessing lifetime, exact-fold
successes, failures and energy uncertainty retained. No finite unsuccessful
corpus should be described as proving that all shortcuts are absent.

## Digital hardware review

The residue identity is exact. What remains is useful-throughput, full-system
economics. Map both the 13-bit residue datapath and a minimally sufficient full
signed accumulator, as well as the GPU's general 32-bit baseline. Compare at a
common throughput and physical process, including timing closure, voltage,
clock gating, routing, memory, bank distribution, SHAKE/ChaCha/folding, I/O and
idle/turnover. Include switching activity, leakage and sensitivity to activity
patterns. A research-library cell-area ratio is not a joule ratio.

Investigate the cost of exploiting constant-per-parent weights versus a generic
variable-coefficient multiplier. Explain configuration amortization and storage
rather than treating a bank as either free ROM or free reloadable SRAM. Report
capacity/energy for the chosen packed or expanded representation. The bank has
134,217,728 configured int4 weights: 64 MiB packed or 128 MiB in the current
expanded-byte GPU representation. Those representations are different costs.

Deliver RTL/netlist and verification artifacts, a manufacturable-process and
memory proposal, timing/power methodology, complete-system energy estimates
with sensitivity ranges, and a statement of what still needs silicon measurement.
Do not compare an arithmetic-only ASIC estimate with a complete GPU board or
claim a photonic advantage from the fraction of time spent in a matrix kernel.

## Photonic hardware review

Demonstrate complete valid attempts, accounting for sources, modulation,
detection, conversions, calibration, control, digital hashing, rechecks and
failed folds. The measured software noise-survival curve is not a device-energy
measurement. State the actual decision thresholds and whether nearest-integer
rounding is physically implemented and stable; unshifted analog thresholds
cannot inherit the more favorable rounded-error table.

Measure full-bank loading/retention and simultaneous lane count. A published
single-weight update time does not establish loading of the entire configured
bank within a block interval. Sweep the team's prospective block intervals;
do not choose one through this review. Compare against optimized exact digital
hardware, including modular accumulators, rather than only a general GPU.

## Integration and decision boundaries

Before production admission can be qualified, the team must define the block
header, its relationship to the supplied parent, admissible parents, target/work
rules, timestamps, initial difficulty and block interval. The lab's trusted
registry and synthetic target are deliberately not those decisions. A real
network path must add bounded parsing/queueing, concurrent ownership, peer
identity/fairness, fork handling and hostile network tests. Backpressure or a
cache miss is not a consensus-invalid block verdict.

Qualification should identify each claim as passed, failed or open and state
its exact scope. Any implementation mismatch or non-bit-exact result requires
an immediate stop and report. A demonstrated work-avoiding shortcut with at
least 5% measured energy-per-correct-attempt savings also requires that stop.
Exact implementation improvements are expected; cheaper exact arithmetic is
reported as hardware economics. Neither a successful audit nor this scope
authorizes Laser activation.
