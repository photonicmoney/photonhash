# PhotonHash v0.4.0-shadow.1 candidate specification

Status: **frozen non-consensus shadownet candidate**

Profile name: **LF2-K8**

This document defines the byte-exact PhotonHash candidate used by the public
shadownet program. It is normative for shadownet differential testing only.
It is not a Laser consensus specification and cannot activate itself.

## 1. Version boundary

PhotonHash v0.2.3-falsified remains an archived, incompatible profile.
PhotonHash v0.3 was a hardware-boundary research program and produced no
candidate specification. Version 0.4.0-shadow.1 gives the frozen LF2-K8
construction its own identity without changing either historical result.

Any change that alters a matrix byte, binding digest, folded state, final
digest, nonce encoding, or target decision requires a new candidate version
and new vectors.

## 2. Fixed parameters

| Parameter | Value |
|---|---:|
| Matrix dimension n | 4096 |
| Matrix count K | 8 |
| Matrix entries | signed integers from -8 through 7 |
| Vector entries | signed integers from -8 through 7 |
| Accumulator | exact signed 32-bit integer |
| Requantization shift | 9 |
| Requantization offset | 262144 |
| Requantized symbol | 4 bits |
| Folded-state length | 2048 bytes |
| Final digest | 32 bytes |
| Nonce | unsigned 64-bit little-endian |

The exact work per attempt is 8 times 4096 times 4096, or 134,217,728
signed multiply-accumulates. An unpacked signed-byte matrix bank occupies
128 MiB. A packed nibble representation occupies 64 MiB.

## 3. Notation

SHAKE256(input, length) means SHAKE256 XOF output of exactly length bytes.
Concatenation is written with two vertical bars. LE32 and LE64 are fixed-width
unsigned little-endian encodings. ASCII tags are absorbed exactly as shown,
without a terminating zero byte.

Packed nibbles are decoded low nibble first, then high nibble. Each nibble u
becomes the signed integer u minus 8.

## 4. Domain tags

| Purpose | Exact ASCII bytes |
|---|---|
| Base matrix | LASER/PhotonHash/v1/matrix |
| Nonce vector | LASER/PhotonHash/v1/vector |
| Additional LF2 matrix parent | LASER/PhotonHash/launch-LF2/matrix |
| LF2 final digest | LASER/PhotonHash/launch-LF2/final |

These tags are inherited from the frozen research candidate. Renaming the
release does not change them.

## 5. Parent matrix bank

The input parent hash P is exactly 32 bytes.

For pass zero, define P_0 = P.

For passes j from one through seven:

    P_j = SHAKE256(
        "LASER/PhotonHash/launch-LF2/matrix" || P || LE32(j),
        32)

For every pass j:

    seed_j = SHAKE256(
        "LASER/PhotonHash/v1/matrix" || P_j,
        64)

    packed_matrix_j = SHAKE256(seed_j, 4096 * 4096 / 2)

Decode packed_matrix_j low nibble first into 4096 times 4096 signed entries,
row-major. Matrix checksums in the vectors are:

    SHAKE256(packed_matrix_j, 32)

The checksum is a test artifact and is not an extra mining input.

## 6. Per-nonce vector

The header H is an opaque byte string supplied by the surrounding protocol.
The v0.4 shadownet transport limits H to 4096 bytes; a future Laser proposal
must separately freeze the real block-header serialization and length.

For nonce N:

    nonce_le = LE64(N)

    h = SHAKE256(
        "LASER/PhotonHash/v1/vector" || H || nonce_le,
        32)

    packed_x = SHAKE256(h, 2048)

Decode packed_x low nibble first to obtain 4096 signed entries x_i in the
range -8 through 7.

## 7. Exact matrix evaluation and requantization

For every pass j and row r:

    y_j,r = sum from i=0 through 4095 of M_j[r,i] * x_i

The exact bound is -262144 through 262144, so signed 32-bit accumulation
cannot overflow.

Define:

    q_j,r = ((unsigned32(y_j,r + 262144) >> 9) AND 15)

No saturation or floating-point arithmetic is permitted. The low four bits
after the shift are intentional, including wrap at the upper bound.

## 8. Fold and final digest

For each row r:

    f_r = q_0,r XOR q_1,r XOR ... XOR q_7,r

Pack f_0 in the low nibble and f_1 in the high nibble of the first byte,
continuing in row order. The resulting folded state F is 2048 bytes.

The final digest is:

    D = SHAKE256(
        "LASER/PhotonHash/launch-LF2/final" || h || F,
        32)

All eight exact requantized pass outputs affect F. There is no recurrent
feedback and no nonlinear boundary between matrix passes.

## 9. Target comparison

Digest and target are unsigned 256-bit little-endian integers. A nonce is a
solution only when:

    integer_le(D) < integer_le(target)

Equality is rejected. No byte-lexicographic comparison is permitted.

## 10. Verification lifecycle

A verifier derives a matrix bank only after the surrounding chain logic has
admitted the parent as known. Untrusted solution messages must never trigger
arbitrary 128 MiB allocations or matrix derivations.

The reference shadow cache:

- holds at most two parents and therefore at most approximately 256 MiB of
  unpacked matrices;
- evicts before replacement derivation so it never intentionally owns a third
  bank; allocation failure leaves the evicted slot empty;
- returns a distinct cache-miss result for an unknown parent;
- requires external serialization during cache mutation;
- permits concurrent hashing of immutable prepared contexts only when each
  thread owns a separate workspace; and
- invalidates borrowed context pointers on cache mutation or destruction.

Nodes may implement a different cache, but shadownet evidence must state its
memory bound, admission order, concurrency policy, and eviction behavior.

## 11. Shadownet transport

The transport protocol is PhotonHash shadow protocol version 1, documented in
docs/shadownet-protocol.md. Transport work IDs and compact vector commitments
are testing artifacts. They are not additional consensus hashes.

The shadownet is observational. A shadow result cannot accept, reject, delay,
or reorganize a Laser block.

## 12. Conformance

A conforming implementation must:

1. reproduce docs/launch-profile-lf2-vectors.txt byte for byte;
2. reproduce docs/v0.4-shadow-vectors.txt;
3. reject equality at the target boundary;
4. reject a null header with nonzero length;
5. use exact accumulation and requantization;
6. bind all folded bytes into the final digest; and
7. identify itself as a non-consensus shadow implementation.

The C, CUDA, and independently structured Rust implementations are differential
oracles. Agreement does not turn this candidate into consensus.

## 13. Claims and non-claims

The measured RTX 5090 implementation placed 61.55 to 61.98 percent of
serialized device time in exact GEMM. That supports the claim that LF2-K8 is
matrix-centric on that implementation.

It does not establish:

- matrix-stage energy share;
- performance on another GPU, FPGA, or ASIC;
- a complete photonic miner;
- any photonic energy or throughput advantage;
- resistance to every structural shortcut; or
- readiness for Laser activation.
