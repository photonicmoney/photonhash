# Contributing

PhotonHash v0.4.0-shadow.1 is published to invite attempts to disprove its
security, operational, and hardware-economics hypotheses. Reproducible
attacks, independent implementations, portability fixes, protocol hardening,
and boundary vectors are welcome.

Before opening a pull request:

1. Run make shadow-ci.
2. Compile with the strict warning flags used by CI.
3. Add a regression test for behavior changes.
4. State whether the change alters candidate-visible bytes.
5. State whether the change can affect Laser validation.

The required answer to item five in this repository is no. Any adapter or
deployment that cannot demonstrate strict shadownet separation is ineligible
for public operation.

Do not silently change either historical v0.2 vectors or v0.4 shadow vectors.
An output-changing change requires a new candidate version, specification,
vectors, differential run, and gate review.

Independent implementations should be written from
docs/spec-v0.4-shadow.md. Please disclose whether the author inspected an
existing implementation before completing the first differential run.

For cryptanalytic findings:

- identify the affected construction step or readiness gate;
- state the claimed work or energy advantage;
- include exact hardware, compiler, batch, and power boundaries;
- distinguish time share, board energy, and modeled energy;
- compare valid exact attempts rather than nominal operations; and
- attach code and raw data sufficient to reproduce the result.

High-value electronic adversaries include packed INT4, fused epilogues,
selective exact recheck, FPGA synthesis, ASIC estimates, GPU-native bank
derivation, and cross-parent amortization.

Implementation vulnerabilities should follow SECURITY.md.
