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
