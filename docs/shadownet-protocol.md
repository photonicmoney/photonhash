# PhotonHash v0.4 shadownet protocol

Status: **non-consensus protocol version 1**

The shadownet runs LF2-K8 beside a public Laser test network. It observes real
parents, templates, timing, reorgs, and miner behavior without participating
in Laser block acceptance.

## Safety invariant

No shadownet component may:

- change the Laser proof-of-work function;
- change real difficulty or chain selection;
- delay block validation while waiting for shadow work;
- reject a real block because LF2 data is absent or invalid; or
- submit an LF2 result as a Laser consensus solution.

The safest deployment uses separate processes and storage. The Laser adapter
is read-only and emits already-admitted parents and templates.

## Roles

| Role | Responsibility |
|---|---|
| Read-only adapter | Observes a known Laser parent and opaque header template |
| Coordinator | Creates canonical shadow work and sets an observational target |
| Miner | Prepares the parent bank, evaluates LF2-K8, and returns solutions |
| Collector | Recomputes every solution exactly and records timing |
| Auditor | Replays raw messages with C and Rust implementations |

One process may hold several roles during initial testing, but raw boundaries
and timestamps must remain visible.

## Canonical encoding

Messages are UTF-8 JSON objects transported as one complete record. Protocol
version is the exact string:

    photonhash-shadow/1

Hex strings are lowercase. Digests, parent hashes, work IDs, and targets are
exactly 32 bytes. Nonces and timestamps are JSON integers within unsigned
64-bit range. Messages are at most 16384 UTF-8 bytes. Duplicate, unknown, or
additional fields are rejected so that collected
evidence has one replayable interpretation.

## Work message

Required fields:

| Field | Meaning |
|---|---|
| protocol | photonhash-shadow/1 |
| type | work |
| network | 1 to 64 ASCII characters |
| work_id | canonical 32-byte identifier |
| parent_hash | known 32-byte parent |
| height_hint | observational unsigned 64-bit height |
| header_hex | opaque header, at most 4096 bytes |
| shadow_target_le | unsigned 256-bit little-endian target |
| issued_at_ms | coordinator timestamp |

The work ID is SHAKE256-256 of:

    "LASER/PhotonHash/shadownet/work"
    || LE32(network byte length)
    || network ASCII bytes
    || parent_hash
    || LE64(height_hint)
    || LE32(header byte length)
    || header bytes
    || shadow_target_le

The timestamp is intentionally excluded so identical work has an identical
identifier across collectors.

## Solution message

Required fields:

| Field | Meaning |
|---|---|
| protocol | photonhash-shadow/1 |
| type | solution |
| work_id | exact identifier of accepted work |
| nonce | unsigned 64-bit nonce |
| digest | miner-reported 32-byte LF2 digest |
| miner_id | non-empty test identifier |
| received_at_ms | collector timestamp |

The collector must ignore the reported digest for trust purposes. It looks up
the immutable work message, requires a prepared known-parent cache entry,
recomputes LF2-K8, checks digest equality, and then checks the shadow target.

Unknown work IDs are rejected before matrix work. Expired or stale work is
recorded separately from malformed work.

Miner identifiers are limited to 128 printable ASCII characters. They are
test labels, not authentication. Transport authentication and authorization
must be supplied by the deployment.

## Required event log

For each parent and solution, retain:

- raw canonical message;
- receive, admission, bank-ready, first-attempt, and solution timestamps;
- matrix derivation, packing, upload, and eviction timing;
- implementation revision and vector-set hashes;
- CPU, GPU, compiler, runtime, driver, memory, and power boundary;
- whether the bank was a hit, cold setup, or reorg replacement;
- exact verification result from each implementation; and
- reason for every rejected message.

Clock sources and synchronization error must be documented.

## Difficulty

Shadow difficulty exists only to generate statistically useful solutions.
It must not be copied into Laser consensus. The coordinator should target
enough solutions to measure latency and disagreement while rate-limiting
verification load.

## Reorg and stale-work tests

The coordinator must deliberately exercise:

- replacement by a sibling parent;
- return to a recently cached parent;
- eviction of the oldest parent;
- delayed solutions for stale work;
- rapid template replacement under one parent; and
- a short burst of unknown work IDs and malformed messages.

The two-parent reference cache supports a current parent and one competitor.
Implementations using more memory must publish and justify the bound.

## Reference tooling

tools/ph_shadow_protocol.py validates canonical messages and freezes the work
ID encoding. tests/test_shadow_protocol.py supplies boundary cases. The
tooling never contacts Laser or mutates chain state. A canonical work example
is stored in docs/shadownet-work-example.json.
