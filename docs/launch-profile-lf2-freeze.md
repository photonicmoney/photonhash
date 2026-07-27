# LF2-K8 candidate freeze

Status: **frozen for hardening; non-consensus**  
Date: 2026-07-26

The unchanged construction received the non-consensus release identity
PhotonHash v0.4.0-shadow.1 on 2026-07-27. That release adds shadownet
lifecycle and evidence tooling around the candidate; it does not alter any
frozen matrix, fold, or digest byte.

LF2-K8 is frozen at `n=4096` and eight independently parent-derived matrix
passes. Parameter tuning is closed. The admission phase may optimize
implementations and attack the construction, but it may not change any
consensus-visible byte, domain tag, matrix derivation, requantization rule,
fold rule, or digest rule under the LF2-K8 name.

The machine-readable freeze manifest is
`research/launch/lf2-k8-freeze-20260726.json`. It records the parameters,
domain tags, candidate-file hashes, and change policy.

This freeze means "hold the target still while trying to break it." It does
not mean that LF2-K8 is approved, specified for Laser, or ready for activation.
Any semantic repair creates a new candidate and restarts exactness,
performance, security, independent-implementation, and testnet gates.

The public claim boundary remains:

- measured RTX 5090 evidence supports calling LF2-K8 matrix-centric; and
- no complete photonic miner or photonic energy advantage has been
  demonstrated.
