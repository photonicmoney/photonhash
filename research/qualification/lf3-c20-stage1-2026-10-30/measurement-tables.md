# Network measurements

30 October 2026. All numeric entries in the table are **measured**. Durations and
client limits were configured before each phase. Latency is the maximum of the
per-legitimate-client p99 logical submission latencies; retries remain included.
A dash means no successful legitimate latency exists, not zero latency. RSS is
process peak KiB, not just coefficients or a whole-host memory measurement.

| Scenario | Legitimate completions | Hostile responses | Bank derivations | Evictions | Max client p99 s | Peak RSS KiB |
|---|---:|---:|---:|---:|---:|---:|
| cold | 32 | 0 | 1 | 0 | 0.779573 | 154832 |
| junk_only | 0 | 5024 | 0 | 0 | — | 15368 |
| baseline | 3721 | 0 | 2 | 0 | 0.066702 | 285408 |
| junk | 3676 | 30016 | 2 | 0 | 0.066993 | 286552 |
| slow | 3701 | 0 | 2 | 0 | 0.066689 | 285820 |
| churn | 257 | 512 | 193 | 191 | 1.016247 | 302684 |
| shared | 326 | 108 | 218 | 216 | 1.237739 | 302176 |
| cross-001 | 0 | 3701 | 2 | 0 | — | 285824 |
| cross-002 | 107 | 737 | 186 | 184 | 2.726690 | 300556 |
| saturated | 204 | 3022 | 288 | 286 | 3.320362 | 303748 |

Cold and junk-only run for **10 configured seconds** each; baseline and other
mixed phases run for **60 configured seconds** each. Full-capacity saturated
stress runs for **120 configured seconds**, with 60 hostile plus four ordinary
legitimate clients. It reaches **64 measured simultaneous connections**,
**16 measured source buckets**, and **63 measured queued connections** plus one
in-flight job. All successful mixed phases pass each client’s configured
20-second interior-window service criterion and have no logical deadline misses.
Cross-001 fails that criterion and remains in the ledger.

Counts can differ between clients and the server: a completed hash may lose its
response when a connection expires or closes. Both sides are retained. Slow
clients send incomplete frames and have no completed response count. Junk-only
pre-hash refusals cause zero native work. Capacity and wire conformance are
reported separately because they do not use the mixed-phase service criterion.

Native conformance: **560 measured full h/fold/digest/target path checks**.
Canonical TCP conformance: **560 measured digest/target responses**, of which
**4 measured valid** and **556 measured invalid**, plus **16 measured coalesced
valid frames**. The cold concurrency control completes 32 clients using one
bank derivation. The three deliberate newcomer-exclusion cycles recover in
**0.288240, 0.016106 and 0.016771 measured seconds** after releasing hostile slots.
The first recovery includes a cold bank; the latter two are cached.

No observed cache exceeds **two configured banks / 268435456 configured expanded
coefficient bytes**. The single-owner/free-before-derive allocation argument
covers intermediate construction, which periodic counters alone cannot prove.
No result proves unlimited-Sybil or saturated-link liveness. Production chain
admission and peer identity remain OPEN.
