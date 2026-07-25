# Contributing

PhotonHash is published to invite attempts to disprove its security and
hardware-economics hypotheses. Reproducible attacks, independent
implementations, specification clarifications, portability fixes, and new
boundary vectors are welcome.

Before opening a pull request:

1. Run `make test check-vectors`.
2. Compile with the warning flags used by CI.
3. Add a regression test for behavior changes.
4. State whether the change alters consensus-visible bytes. If it does, update
   the specification and vectors and propose a new version; do not silently
   change the v0.2 vector set.

For cryptanalytic findings, identify the claim or attack surface from
`docs/adversarial-brief.md`, state the claimed severity, document the hardware
and cost model, and attach code or data sufficient to reproduce the result.

Implementation vulnerabilities should follow `SECURITY.md`.
