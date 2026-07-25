# PhotonHash: Adversarial Review Brief

**Version:** 1.0
**Author:** Lightman
**Targets:** *PhotonHash: Technical Specification* v0.2 · `photonhash-ref` 0.2.2-experimental
**Status:** OPEN — this document is an invitation to break the design

---

## 1. Purpose

PhotonHash is the proof-of-work function of the Laser blockchain. Its
parameters will not be frozen, and no mainnet will launch, until the design
has survived serious adversarial attention. This brief exists to make that
attention efficient: it states precisely what the design claims, what would
falsify each claim, how severe each falsification would be, and where we
ourselves believe the softest tissue lies.

A note on posture: findings against this design are contributions to it.
Prior pre-publication implementation work materially changed the construction (the v0.1→v0.2
requantization retuning and analog-model replacement arose from
implementation findings; an undefined-behavior edge and a spec transcription
error were corrected, and the A6 surface was made explicit). The
fastest way to be acknowledged in this project's history is to wound it.

## 2. Artifacts under review

| Artifact | Contents | Role |
|----------|----------|------|
| [`docs/spec-v0.2.md`](spec-v0.2.md) | Lineage §2.1, construction §5, cost model §6, analog model §7, schedule §8, security analysis §9 | The claims |
| [`src/photonhash.c`](../src/photonhash.c) and tests | Portable C11 implementation, self-tests, benchmark | Shared review oracle; not yet normative |
| [`docs/test-vectors.txt`](test-vectors.txt) | Five end-to-end vectors at n = 1024 | The ground truth for reimplementation |
| [HeavyHash](https://arxiv.org/abs/1911.05193) and [LightHash](https://doi.org/10.1364/OPTICA.476173) | Prior optical proof-of-work constructions | Related-work and comparison baseline; not inherited security |

The release CI rebuilds the reference with GCC and Clang, exercises ASan/UBSan,
and reproduces its vectors byte-for-byte. These checks validate implementation
consistency, not the construction. No published independent audit or conforming
reimplementation is claimed. Reviewers should attack both the *design* and the
code; implementation bugs remain in scope as the lowest tier below.

## 3. The claims, stated falsifiably

The design rests on five claims. Each is paired with what its falsification
looks like.

**C1 — Hash-bound security.** Producing a valid block requires an expected
number of full pipeline evaluations proportional to difficulty; any cheaper
strategy implies a distinguisher or (second-)preimage attack against
SHAKE256 as used with the specified domain separation.
*Falsified by:* any method producing valid digests d below a target with
expected cost measurably under one full pipeline evaluation per attempt,
without breaking SHAKE256 generically.

**C2 — Matrix-stage dominance.** The matrix–vector product accounts for the
overwhelming majority of marginal per-attempt cost (design target ≥ 90% on
mining-relevant hardware; measured 89–95% on commodity CPUs at genesis
parameters).
*Falsified by:* a conforming evaluation strategy on plausible hardware in
which the matrix stage falls materially below the claimed share — e.g., a
hash-stage bottleneck inversion, or a matvec shortcut (see A1).

**C3 — Exact-consensus compatibility of analog mining.** The
boundary-flagged hybrid discipline (spec §7) lets an analog evaluator with
relative precision ρ produce bit-exact solutions at digital-assist fraction
δ predicted by the model to be approximately 32·ρ; validation on real
hardware remains open.
*Falsified by:* demonstration that realistic (correlated, non-Gaussian,
drifting) analog error models break the δ formula badly enough to overturn
the economic conclusions, or that the guard-band discipline admits silent
consensus-relevant errors at non-negligible rates.

**C4 — Substrate neutrality outside linear algebra.** No hardware class
other than linear-algebra accelerators holds an asymptotic advantage, and the
era schedule (§8) erodes cache-resident electronic implementations over time.
*Falsified by:* a concrete electronic (or other) architecture argument that
retains an advantage across era growth — e.g., an in-memory-compute design
whose cost per attempt scales better than photonic meshes as n doubles.

**C5 — Genericity of derived matrices.** SHAKE-derived M is structurally and
spectrally generic: it admits no property that is (a) efficiently testable
and (b) exploitable for faster evaluation or favorable-hardware bias.
*Falsified by:* any efficiently detectable non-generic structure in M
(rank deficiency at non-negligible rates, exploitable spectral concentration,
low-dimensional approximability) usable in an attack (see A1, A6).

## 4. Severity tiers

| Tier | Name | Definition | Consequence |
|------|------|------------|-------------|
| T0 | Consensus break | Valid blocks cheaper than C1 allows; verifier/miner divergence on any input; two conforming implementations disagreeing on a vector | Design returns to the drawing board |
| T1 | Economic break | C2, C4, or C5 falsified in a way that redirects mining economics (e.g., sub-quadratic amortized evaluation, permanent electronic advantage) | PhotonHash redesign before freeze |
| T2 | Thesis wound | C3 falsified: analog/hybrid discipline unrealizable at any plausible ρ, or advantage cap far below spec table | Photonic thesis weakened; parameters or model revised |
| T3 | Parameter weakness | Attacks meaningfully easier than intended at current ⚠ parameters but fixable by retuning (shift table, entry width, guard multiplier, era cadence) | Parameter revision, new vectors |
| T4 | Implementation defect | Reference-implementation bugs: UB, portability divergence, vector mismatch, DoS in verification paths | Point release + regression test |

Anything in T0–T2 halts parameter freezing outright. T3 findings are the
expected, welcome steady state of this phase.

## 5. Attack surfaces, with starting points

Each surface below names the target claim, the current defense, a concrete
first move for an attacker, and our honest confidence. Surfaces are ordered
by the payoff of a success, not by our estimate of its likelihood.

### A1 — Cross-nonce matrix amortization (primary target)

- **Threatens:** C1, C2, C5. **Best-case severity:** T1.
- **Setup.** M is fixed for an entire block template (spec §5.1, chosen so
  photonic meshes load once and stream nonces — spec R5). Only x changes per
  nonce. An attacker may therefore pay an arbitrary one-time precomputation
  cost on M and amortize it across the whole nonce search.
- **Defense as designed.** The per-attempt work is already only n² 4-bit
  MACs; any amortized strategy must beat that *and* reproduce exact
  requantization buckets, not approximate products. SHAKE-derived M is
  conjectured generic (C5), so structure-based speedups (low rank, sparsity,
  factorization) should not apply.
- **Concrete first moves for an attacker:**
  1. Exhibit a preprocessing-then-query scheme for fixed random 4-bit M and
     streamed 4-bit x that computes the *exact* requantized r in amortized
     o(n²) per query. (Note: approximate MX is insufficient — see the guard
     band; the output buckets must be exact for accepted components.)
  2. Show that the v0.2 bucket width (W ≈ 0.37σ) is coarse enough that an
     amortized *approximate* evaluator lands in correct buckets often enough
     to beat honest miners after accounting for the digital re-check of
     candidate wins. This is the sharpest version and directly attacks the
     §7 economics.
  3. Batched-nonce MX as matrix–matrix: demonstrate that Strassen-family or
     better exponents yield a *real* per-attempt advantage after the exact-r
     constraint, rather than merely improving constant factors equally for
     all miners.
- **Our confidence:** MODERATE. We know of no exact sub-quadratic algorithm
  for dense unstructured matrix–vector products, and Strassen-type gains are
  matrix–matrix and available to everyone. But move (2) — exploiting bucket
  coarseness — is genuinely unsettled and is the single result we most want
  found or ruled out. This is priority 1.

### A2 — Requantization structure leakage

- **Threatens:** C1. **Best-case severity:** T0 if severe, else T3.
- **Setup.** r is a deterministic, *non-uniform* function of (M, x): the
  mod-16 wrap of an approximately-Gaussian y. The design claims uniformity of
  the final digest d is supplied by the enclosing SHAKE, so r's non-uniformity
  is harmless.
- **Concrete first moves:**
  1. Show that the r distribution (measured ≈ 3.47 bits/component entropy)
     leaks enough about (M, x) that d becomes predictable or biased faster
     than generic search — i.e., that "SHAKE fixes it" is false at these
     parameters.
  2. Find inputs producing degenerate r (near-constant nibble vectors) at
     non-negligible rates, and show they cluster d.
- **Our confidence:** HIGH that this is safe (h_in independently binds each
  attempt into the final hash), but the argument is asserted in the spec, not
  proved. A formal statement is wanted.

### A3 — Guard-band / precision cheating

- **Threatens:** C3. **Best-case severity:** T2.
- **Setup.** §7 recomputes digitally only components within G = 6σ_a of a
  bucket boundary; the rest are trusted from analog. Silent wrong-bucket
  acceptance is a ≥6σ event (~1e-6 per attempt), caught on winning attempts by
  the mandatory digital re-check before broadcast.
- **Concrete first moves:**
  1. Construct a correlated or heavy-tailed analog error model (realistic for
     photonic crosstalk / thermal drift) under which the 6σ guard admits
     consensus-relevant silent errors at rates the candidate re-check does
     not catch.
  2. Show δ ≈ 32·ρ collapses (advantage cap far below the spec table) once
     error correlation across components is included — the simulation that
     confirmed the formula assumed independence.
- **Our confidence:** MODERATE. The independence assumption is the weak joint;
  see open question OQ-2.

### A4 — Verification asymmetry / DoS

- **Threatens:** C1 (verify side). **Best-case severity:** T4, T1 at large n.
- **Setup.** Verifying an invalid block costs one matvec (~1 ms at n=1024,
  growing ×4 per era). Header-first ordering and parent checks bound exposure.
- **Concrete first moves:**
  1. At era ≥ 3 dimensions, show a flood of cheaply-generated
     almost-valid headers imposing asymmetric verifier cost that outpaces
     mitigations.
  2. Break the claim that a succinct-proof verification path can be shipped
     before the working set exceeds on-die memory (spec §5 note).
- **Our confidence:** MODERATE at genesis, LOWER at high eras; OI-5 tracks it.

### A5 — Electronic substrate capture

- **Threatens:** C4. **Best-case severity:** T1.
- **Setup.** The hardness schedule (§8) grows n to push electronic matvec
  off-die into bandwidth-bound territory where optical meshes widen their lead.
- **Concrete first moves:**
  1. Present an in-memory-compute or analog-electronic matvec architecture
     whose energy-per-attempt tracks or beats photonic meshes across era
     growth — i.e., electronics that is *also* bandwidth-native.
  2. Show the era cadence (2 years) is too slow relative to plausible
     electronic progress, so the electronic era never actually ends.
- **Our confidence:** MODERATE. The whole thesis is that light wins this race;
  a credible electronic architecture that keeps pace is a direct T1 hit.

### A6 — Parent-hash grinding / future-matrix bias

- **Threatens:** C5. **Best-case severity:** T1 if C5 falls, else negligible.
- **Setup.** M(k+1) derives from block k's hash. A miner finding multiple
  valid solutions for block k may choose among resulting parent hashes, or
  withhold and re-search, to bias the next matrix. Each additional candidate
  costs a full block's expected PoW.
- **Concrete first move:** Exhibit an efficiently testable
  "hardware-favorable matrix" predicate on SHAKE-derived M whose expected
  value of biasing exceeds the c× cost of producing c candidate parents.
  (This is C5/A1 move-1 wearing a different hat: no exploitable predicate ⇒
  no grinding gain.)
- **Our confidence:** HIGH that this is non-economic, *conditional on C5*.
  It collapses to the genericity question.

## 6. Open questions we most want answered

- **OQ-1 (priority 1).** Is there an amortized-exact or
  amortized-approximate evaluator that beats honest per-attempt cost at
  W ≈ 0.37σ? (A1 moves 1–2.) A rigorous no is the result that most
  stabilizes the design; a yes is the result that most changes it.
- **OQ-2.** Does the δ ≈ 32·ρ advantage cap survive realistic *correlated*
  analog noise, or does crosstalk change the conclusion? (A3.)
- **OQ-3.** A formal statement and proof (ROM) that non-uniform r does not
  bias d beyond generic search. (A2, and spec OI-2.)
- **OQ-4.** Distributional analysis of SHAKE-derived M — rank, spectrum,
  low-rank approximability — settling C5 and thereby A1-structure, A6. (Spec
  OI-3.)
- **OQ-5.** A concrete electronic architecture that keeps pace across the era
  schedule, or an argument that none can. (A5, C4.)

## 7. Success criteria and reporting

A finding is **in scope** if it targets any claim C1–C5 or any surface
A1–A6, or exhibits a T4 implementation defect. To be actionable a report
should include: the tier claimed; the claim/surface targeted; a reproducible
artifact (script, patch, or vector) demonstrating the effect; and, for
economic/thesis findings (T1–T2), an explicit cost comparison against honest
mining under stated hardware assumptions.

The reference implementation's determinism is the shared oracle: any T0
claim of implementation divergence must be accompanied by an input on which
two conforming implementations disagree, or on which the reference violates
the spec. The bundled test vectors are the anchor; a new vector that the
reference mis-handles is itself a finding.

**Out of scope** (for now): the post-quantum signature layer, consensus/fork
choice above PoW, the entropy beacon, and economics beyond mining — each has
its own review surface and is not part of PhotonHash.

## 8. What a clean bill of health would require

Before parameter freeze, we want: OQ-1 resolved (no amortization advantage at
frozen parameters, or parameters chosen to eliminate it); OQ-2 resolved under
a correlated-noise model; OQ-3 proved; OQ-4 characterized; OQ-5 argued; and
independent reimplementation from the frozen spec by at least two parties
matching a frozen, expanded vector set including boundary cases. Until then,
every parameter marked ⚠ is provisional, and PhotonHash is a candidate, not a
commitment.

---

*This brief accompanies the PhotonHash specification and reference
implementation. It will be revised as surfaces are closed or opened.
Contributions — proofs, attacks, or hardware arguments — are the point.*
