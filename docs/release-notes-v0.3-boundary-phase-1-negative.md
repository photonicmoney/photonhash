# PhotonHash v0.3 boundary phase one: negative result

Release tag: `v0.3-boundary-phase-1-negative`
Date: 2026-07-26
Status: frozen non-consensus research artifact

## Result

PhotonHash v0.3 boundary phase one did not identify an experimentally grounded
nonlinear regeneration class that clears the charter's conservative 3x
complete-system survival gate after byte-exact trajectory yield is charged.

R1 remains archived as a conditional architecture. The feed-forward family
does not advance as a superior alternative. No v0.3 specification is defined,
and this release makes no change to Laser consensus.

## Decisive measurements and models

- The exact fused RTX 5090 recurrence recovered 93--94% conditional
  photonic-accelerable electronic share at an approximately 134-million-MAC
  equal-work frontier.
- Unassisted low-resolution regeneration at `n=8192`, two rounds, produced a
  median exact-trajectory yield of `2.16e-10`.
- Selective assistance restored median yield to `0.999978`, but reached only
  `1.86x` at the conservative fifth percentile and `3.11x` at the median.
- A modeled full ADC/digital/remodulation roundtrip preserved exactness but
  reached only `1.10x` conservatively and `1.74x` at the median.
- Three full redundant matrix lanes reached only `0.60x` conservatively.
- All-optical feed-forward nonlinear stages lost effectively every byte-exact
  linked trajectory under the tested analog-error ranges.
- A projected selective-assistance envelope reached `7.17x` conservatively,
  but depends on unmeasured R1-scale matrix, control, correction, and boundary
  assumptions. It is retained only as a device target.

## Missing physical primitive

The phase isolates one missing invention:

> An experimentally demonstrated, consensus-exact, ultra-low-energy nonlinear
> regeneration primitive whose complete detector-through-remodulator path
> remains economical after noise, drift, calibration, correction, control,
> and failed trajectories are counted.

For the most favorable tested R1 corner (`n=8192`, two rounds), a representative
device must plausibly demonstrate:

- the exact 4-bit wrap transition with deterministic tie behavior;
- residual undetected error below approximately `3e-6` per logical decision;
- complete photonic energy below `82.33 uJ` for 3x survival and below
  `49.40 uJ` for a 5x serious-candidate result at the stated comparison point;
- at least 2x valid throughput at equal board power; and
- a grounded route to 8,192 state symbols and 134,217,728 MACs without omitting
  fanout, loss, area, storage, conversion, or calibration.

## Included evidence

- [`docs/v0.3-charter.md`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/docs/v0.3-charter.md): frozen admission gates.
- [`docs/v0.3-boundary-model.md`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/docs/v0.3-boundary-model.md): physical boundary
  taxonomy and kill criteria.
- [`docs/v0.3-r1-first-pass.md`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/docs/v0.3-r1-first-pass.md): electronic and
  structural first pass.
- [`docs/v0.3-boundary-phase-1.md`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/docs/v0.3-boundary-phase-1.md): final boundary
  decision and complete tables.
- [`research/v0.3/evidence/boundary-evidence.json`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/research/v0.3/evidence/boundary-evidence.json):
  machine-readable evidence ledger.
- [`research/v0.3/results/boundary-phase-1-20260726.json`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/research/v0.3/results/boundary-phase-1-20260726.json):
  5,000-sample main result.
- [`research/v0.3/results/boundary-sensitivity-grid-20260726.json`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/research/v0.3/results/boundary-sensitivity-grid-20260726.json):
  2,000-sample sensitivity grid.
- [`research/v0.3/results/SHA256SUMS`](https://github.com/photonicmoney/photonhash/blob/v0.3-boundary-phase-1-negative/research/v0.3/results/SHA256SUMS):
  evidence integrity manifest.

## Reproduction

~~~sh
make clean all test check-vectors
make v03-test

python3 tools/ph_v03_boundary_sim.py \
  research/v0.3/scenarios/boundary-phase-1.json \
  --samples 5000 --seed 17 \
  --output research/v0.3/results/boundary-phase-1-20260726.json

python3 tools/ph_v03_boundary_sim.py \
  research/v0.3/scenarios/boundary-sensitivity-grid.json \
  --samples 2000 --seed 23 \
  --output research/v0.3/results/boundary-sensitivity-grid-20260726.json
~~~

The CUDA source and measurements use ordinary user-space workloads and
read-only GPU telemetry. This research did not change GPU firmware, drivers,
clocks, voltage, power limits, fans, BIOS, or operating-system settings.

## Research posture

PhotonHash construction work is paused. The program should reopen only when a
measured physical primitive, rather than another optimistic component model,
plausibly fits the published boundary budget. This result does not prove that
photonic proof of work or light money is impossible. It establishes that the
tested architectures and current component evidence are insufficient.
