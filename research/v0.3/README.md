# PhotonHash v0.3 research workspace

Status: **phase one frozen as a negative result; Q.ANT platform evaluation queued**

This directory is deliberately separate from the frozen v0.2 profile. Nothing
here is a consensus proposal.

PhotonHash v0.4.0-shadow.1 does not supersede or reinterpret this result. It
uses the feed-forward LF2-K8 launch objective and makes no claim that a
photonic miner already passes the v0.3 complete-system superiority gates.
Current shadownet work lives in
[research/launch](../launch/README.md).

## Research order

1. Keep [the charter](../../docs/v0.3-charter.md) fixed.
2. Define and cost the [inter-round boundary](../../docs/v0.3-boundary-model.md).
3. Measure the strongest electronic implementation across dimension, rounds,
   alphabet, transform layout, and batch size.
4. Populate every photonic component from traceable physical evidence with
   uncertainty ranges.
5. Eliminate candidates that fail the charter before writing a specification.
6. Only then commission an independent implementation, vectors, and a
   non-consensus testnet profile.

## Economics model

The tools/ph_v03_model.py program samples electronic and complete photonic
component costs independently and reports:

- electronic photonic-accelerable headroom;
- complete-system energy advantage;
- equal-board-power throughput;
- the optimistic Amdahl upper bound, when requested;
- probabilities and conservative fifth percentiles at the 3x, 5x, and 10x
  gates;
- evidence maturity and placeholder blockers;
- component sensitivity;
- consensus-readiness checks.

Run the v0.2 calibration:

~~~powershell
py -3 tools/ph_v03_model.py research/v0.3/scenarios/v02-optimistic-calibration.json --samples 50000 --seed 3
~~~

The calibration intentionally assumes that matrix acceleration adds zero
physical overhead. It reproduces the Amdahl upper bound of about 1.13x and
still fails Gate 1. This proves that the simulator does not silently convert
the old matrix percentage into a photonic claim.

Run the tests:

~~~powershell
py -3 -m unittest tests.test_v03_model -v
~~~

## Boundary yield model

The tools/ph_v03_boundary_sim.py program evaluates the provisional exact R1
bucket map over its discrete accumulator residues. It composes independent
noise, shared offset, drift, temperature, component variation, threshold
bias, selective assistance, calibration failures, and redundancy across the
complete linked trajectory. Nominal energy is divided by byte-exact output
yield, so failed optical trajectories cannot disappear from the economics.

Run the main screen and focused sensitivity grid:

~~~powershell
py -3 tools/ph_v03_boundary_sim.py research/v0.3/scenarios/boundary-phase-1.json --samples 5000 --seed 17 --output research/v0.3/results/boundary-phase-1-20260726.json
py -3 tools/ph_v03_boundary_sim.py research/v0.3/scenarios/boundary-sensitivity-grid.json --samples 2000 --seed 23 --output research/v0.3/results/boundary-sensitivity-grid-20260726.json
py -3 -m unittest tests.test_v03_boundary_sim -v
~~~

## Scenario rules

- Every electronic component declares whether it is photonic-accelerable.
- All ten complete photonic-system components are mandatory, including zero
  values. A zero is an assumption that needs evidence, not a missing cost.
- A scalar value is fixed. An object with low, mode, and high is sampled as a
  triangular distribution.
- Every component has an evidence class and a non-empty source.
- Any placeholder blocks Gate 2 even if the numeric thought experiment wins.
- physical_path_evidence must reach representative_prototype for Gate 3.
- Simulator output is always marked research_only.

The evidence ladder is:

~~~text
placeholder
  < literature_model
  < measured_component
  < representative_prototype
  < independent_reproduction
~~~

## Current artifacts

- scenarios/v02-optimistic-calibration.json: deterministic regression
  scenario derived from the published RTX 5090 time-share result.
- scenarios/r1-literature-boundary-budget.json: component-complete R1
  uncertainty screen; placeholders deliberately block admission.
- scenarios/boundary-phase-1.json: recurrent, full-digital, redundancy, and
  feed-forward boundary comparison with exact-yield accounting.
- scenarios/boundary-sensitivity-grid.json: noise, guard-band, assistance,
  precision, round-count, and correlated-drift sensitivity.
- evidence/boundary-evidence.json: machine-readable primary-evidence table.
- candidates/: construction descriptions and kill tests; parameters are not
  consensus values.
- results/: generated reports and raw benchmark evidence. Generated result
  files should include their source revision and command.

The current decision is
[boundary phase one](../../docs/v0.3-boundary-phase-1.md): no evaluated
boundary is an evidence-qualified 3x survivor. R1 remains an archived
conditional architecture; feed-forward is rejected as a superior alternative.
No v0.3 specification work has started.

## External platform evaluation

Q.ANT is the primary external candidate for the next boundary experiment. The
[Q.ANT audit and existing-NPU protocol](../../docs/v0.3-qant-boundary-audit.md)
requires direct evaluation of its native matrix and nonlinear operations,
detector/CMOS path, chaining boundary, and complete optical-electronic-optical
energy before any custom laboratory build is proposed.

This queue does not promote R1. Public evidence supports an existing NPU,
matrix-vector access, and a weighted sinusoidal optical nonlinearity, but does
not establish an exact wrap transition or show that recurrent state avoids a
general conversion loop.

## Safety boundary

GPU research in this workspace uses ordinary user-space CUDA workloads and
read-only telemetry. It does not modify firmware, drivers, clocks, voltage,
power limits, fans, BIOS, or system configuration.
