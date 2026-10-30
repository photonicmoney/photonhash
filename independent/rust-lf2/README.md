# Independent Rust PhotonHash v0.4 shadow implementation

This crate is an independently structured, non-consensus implementation of
the frozen LF2-K8 candidate identified as v0.4.0-shadow.1. It uses RustCrypto
SHAKE256 and derives the complete 128 MiB matrix bank itself.

It verifies:

- every original frozen matrix seed and checksum;
- binding digests and complete 2048-byte folded states;
- original final digests;
- compact v0.4 vectors across four distinct parents;
- header lengths from zero through 4096 bytes;
- bank and folded-state commitments; and
- strict little-endian target ordering.

It does not link to the C implementation or use C-generated matrices at
runtime. The shared inputs are the published candidate specification and
vector files.

    cargo test --release --locked \
      --manifest-path independent/rust-lf2/Cargo.toml

    cargo run --release --locked \
      --manifest-path independent/rust-lf2/Cargo.toml -- \
      docs/launch-profile-lf2-vectors.txt

Passing this crate is implementation-diversity evidence. It is not a
cryptographic audit, independent human authorship, public-shadownet evidence,
or a Laser activation decision.

## C20 experimental extension

The `c20-vectors` executable adds the separately named
`LF3-K8-C20-experiment.1` vector expander and final domains. It implements the
RFC 8439 ChaCha20 block function directly in Rust, checks the RFC primitive
fixture, and compares h, the complete 2048-byte fold and the final digest.
Matrix derivation remains this crate's independent Rust implementation.
The existing LF2 construction and vectors are unchanged.

```sh
cargo run --release --locked \
  --manifest-path independent/rust-lf2/Cargo.toml --bin c20-vectors -- \
  research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt
```

See the [measured four-way results and distribution](../../research/qualification/lf3-c20-2026-10-30/README.md).
This is an experimental checker, not an activated miner or a normative
v0.5.0 candidate package.
