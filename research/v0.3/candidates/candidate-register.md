# PhotonHash v0.3 candidate register

Status: boundary phase one complete; no candidate is selected

| ID | Family | Nonlinear boundary | Optical amortization hypothesis | Primary electronic attack | Primary physical kill test |
|---|---|---|---|---|---|
| R1 | recurrent same-matrix | exact low-bit wrap regeneration; round variation remains open | program one matrix once and reuse it across many rounds | persistent batched GEMM with fused requantization; short-cycle and state-reuse analysis | measured detection-to-regeneration-to-remodulation loop |
| F1 | tiled feed-forward | low-bit regeneration between passive or amortized stages | cross many optical stages before one full digital conversion | persistent fused GEMM sequence; stage collapse and layout fusion | accumulated loss, noise, nonlinear-device energy, and calibration across depth |
| B1 | block-structured transform | nonlinear reduction between blocks or passes | map a large logical transform onto reusable physical tiles | tensor-friendly block batching, sparse/layout optimization, multi-pass fusion | programming and movement energy per tile plus physical scale |

The identifiers name experiments, not protocol versions.

## Boundary-phase status (2026-07-26)

- **R1:** archived as a conditional architecture and does not advance. Its
  best evidence-informed selective-assistance profile reaches 1.86x at the
  conservative tail, below the 3x survival gate. Unassisted regeneration loses
  exact yield; a full digital roundtrip loses energy. A projected target
  envelope reaches 7.17x but has no admission weight.
- **F1:** rejected as a superior alternative. Distinct matrices do not slow
  the fused GPU baseline, and measured all-optical nonlinearities do not
  supply consensus-exact linked state regeneration. The modeled exact yield
  is effectively zero before the physical stage-bank cost is established.
- **B1:** parked and outside the narrowed boundary program. The n=8192,
  two-round electronic point remains only a dense upper-level proxy, not a
  tiled architecture result or a v0.3 design.

The decision record is
[v0.3 boundary phase one](../../../docs/v0.3-boundary-phase-1.md). No v0.3
specification work begins from these probes.

## Shared seed and wrapper

To make electronic results comparable, the first experiments share a minimal
wrapper:

1. One SHAKE expansion binds the parent, header, and nonce to an initial
   signed low-bit state.
2. The candidate performs its matrix-domain work.
3. One final SHAKE binds the initial digest, final state, and candidate
   parameters.

Intermediate SHAKE calls are excluded unless an attack demonstrates that a
cheaper boundary is structurally inadequate. The wrapper is not frozen and
does not define consensus behavior.

## R1: recurrent same-matrix probe

Provisional transition:

~~~text
s[0] = expand(parent, header, nonce)
y[t] = M(parent) * s[t]
s[t+1] = low_bits((y[t] + offset) >> shift)
digest = final_hash(s[0], s[R], R, parameters)
~~~

Questions to answer before any specification:

- What is the cheapest exact symbolic regeneration alphabet: sign, ternary,
  2-bit, or 4-bit?
- Does the state enter short cycles or biased attractors?
- Can round masks be realized without an active full-width control update?
- How much of requantization and layout work disappears into a GPU kernel?
- Does every physical round require conversion and remodulation?

R1 is eliminated if its complete measured or component-grounded feedback loop
cannot clear the 3x fifth-percentile gate, regardless of its matrix share.

## F1: tiled feed-forward probe

Provisional structure:

~~~text
s[0] = expand(parent, header, nonce)
s[t+1] = local_nonlinearity(M[t] * route[t](s[t]))
digest = final_hash(s[0], s[R], R, parameters)
~~~

The matrices may be parent-derived tiles, repeated programmed tiles with
passive route changes, or a block factorization. Purely linear stages are
assumed collapsible and receive no credit.

Questions:

- Can the nonlinear stage produce consensus-stable symbols without a full
  ADC/DAC boundary?
- How many stages survive optical loss and accumulated error?
- How much active calibration and routing is required per parent?
- Is the fabricated depth or tile count physically credible?
- Can an electronic miner fuse all stages while retaining tensor utilization?

F1 is eliminated if exactness requires per-stage high-resolution digital
correction or if stage depth cannot scale under a measured noise and loss
budget.

## B1: block-structured transform probe

Provisional structure:

~~~text
s[0] = expand(parent, header, nonce)
for each pass:
    for each programmed tile:
        accum[block] += tile * routed_block(s)
    s = nonlinear_reduce(accum)
digest = final_hash(s[0], s[passes], parameters)
~~~

Questions:

- Does block structure expose sparsity, separability, or low-rank shortcuts?
- Can electronic miners batch across blocks and nonces without idle tensor
  resources?
- How often must optical weights be programmed per parent?
- Does movement and accumulation outside the optical tile dominate?
- Can verification sample or commit to work without weakening proof-of-work
  soundness?

B1 is eliminated if the block schedule moves or converts more energy than it
saves, or if a GPU obtains an equivalent locality advantage.

## Parameter sweep

The first electronic sweep spans:

- dimensions: 256, 512, 1024, and 2048 where memory permits;
- rounds or stages: 1, 2, 4, 8, 16, 32, 64, and 128;
- alphabets: sign, 2-bit, and 4-bit signed states;
- batch sizes chosen around tensor saturation and memory limits;
- fused and deliberately materialized boundaries;
- fixed-matrix and round-varied layouts.

The first structural sweep measures:

- per-coordinate entropy and bias;
- cycle and repeated-state incidence;
- decision-margin distributions;
- avalanche from one-bit seed changes;
- exact full-output rate under partial-row, partial-column, low-rank, and
  relaxed-boundary approximations.

## Advancement record

Each candidate receives a dated decision record with:

- exact source revision and commands;
- best electronic configuration and raw data;
- complete energy scenario with evidence classes;
- sensitivity and conservative uncertainty output;
- attack results and unresolved attacks;
- pass/fail for each charter gate;
- explicit disposition: eliminate, continue research, or request independent
  reproduction.
