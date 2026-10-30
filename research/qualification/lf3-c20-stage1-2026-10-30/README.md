# C20 Stage 1: isolated network verifier and matrix timing

**30 October 2026. Experimental LF3-K8-C20-experiment.1; REVISE. No candidate
freeze, activation, release or Laser node/miner/chain changes.** All compilation,
tests, statistics, decompression and research hashing ran on rented machines.
The owner's computer performed editing, review, Git and transport/control only.

The standalone verifier now handles actual concurrent TCP traffic, rather than
only direct function calls. This closes the earlier laboratory transport and
admitted-client scheduling gap within the explicit finite threat model below.
It does not implement Laser's network protocol or decide which chain parents
are admissible. The matrix experiment measures the quantize/fold/store phases
separately; **pure multiplication activity remains OPEN** because this rental
denied hardware counters and the single planned alternate had no capacity.

Observations are **measured**, calculations and statistical intervals **inferred**,
and limits/test sizes **configured**. No new energy or photonic advantage is
claimed. Failed runs and negative controls are retained in [ledger.md](ledger.md).

## Network architecture and bounds

`src/verifier_server.py` is an isolated IPv4 TCP service. Its wire format is
`L3N1 || body_length_u32_BE || parent[32] || nonce_u64_LE || header[0..4096]`.
The configured body range is 40..4136 bytes, hence at most 4144 bytes/frame.
The response is a status byte plus a 32-byte digest; pre-hash refusals return
zero digest bytes. Statuses are documented in the source. They are service
responses, not Laser consensus-invalid block decisions. No TLS, HTTP or Laser
P2P handshake is claimed.

Trusted startup configuration supplies four canonical parents and their
strict little-endian targets. Clients cannot set targets, admit parents,
choose their identity or advance the clock. Source identity is the socket's
IPv4 address, with no trusted forwarded-address field. Test-driver role labels
never appear on the wire. Legitimate clients get no authentication secret,
priority flag, reserved connection or separate worker.

The configured limits are **64 connections**, **16 source buckets**, **4
connections/source**, one outstanding frame/connection, a preallocated
**4144-byte input buffer/connection** and fixed **33-byte response**. The native
worker's input and result queues each have capacity one. Pending connection
IDs are bounded by the connection table; one source-round-robin deque and
per-source FIFO queues govern expensive work. No unbounded executor, frame,
response or per-request logging queue exists. Accept processing is bounded
per event-loop iteration. Monotonic deadlines are configured at **3 s** for
reading/writing, **20 s** queued and **90 s** connection lifetime. Every lab
server has a finite configured process lifetime.

The network loop rejects bad framing, oversized lengths and unknown parents
before native work. A dedicated single owner performs exact bank derivation
and hashing outside that loop. It releases the GIL while in C. There is no
concurrent bank-reader/eviction race or duplicate simultaneous cold derivation.

`src/network_cache.c` owns two configured cache slots. It destroys a victim
before deriving its replacement. During derivation there is at most one older
expanded bank and one new bank under construction: **256 MiB configured maximum
live coefficient storage**. OpenSSL's per-pass packed scratch is additional;
one configured derivation worker needs up to **8 MiB inferred packed scratch**,
plus allocator/library/hash workspace. The successful bank context is moved
into the empty slot without a coefficient copy. Failure frees its partial
allocations. The unchanged reference computes every required matrix product,
quantizer, full fold and final digest.

The server sets **768 MiB configured virtual-address limit**, **160 configured
file-descriptor limit** and no core dumps. These are process controls, not a
whole-host memory proof. Kernel socket buffers, listen/SYN state, network
capacity and other processes are separate. Requested socket buffers are
8192 bytes each direction; Linux reported **16384 measured bytes** each after
its accounting adjustment. **512 MiB configured RSS acceptance gate** is a
test criterion, not an RSS rlimit. See raw summaries for observed peaks.

## Correctness, concurrency and liveness

The native cache passes **560 measured canonical h/full-2048-byte-fold/digest
comparisons**, including strict target decisions, before traffic tests. The
unknown-parent native precheck leaves all counters unchanged. AddressSanitizer
and UndefinedBehaviorSanitizer then pass **16 configured large-allocation fault
positions** spanning a complete bank derivation: the freed victim remains gone,
partial allocations are cleaned up, and a recovery request reproduces the exact
trace. Sanitized timings are not performance evidence.

Actual TCP transport passes all **560 measured canonical digest/target
responses**, covering the configured 28 header lengths including SHAKE rate
boundaries, zero and 4096 bytes, and all five nonce edges. Binding/fold bytes
are checked by the native test, not transmitted by the network protocol.
The wire suite also passes **16 measured coalesced valid frames** on one
connection. Fragmented prefixes/bodies are exercised. Known-invalid PoW is
distinguished from valid work with real targets, rather than making every
digest valid. Load tests repeat one canonical valid fixture per selected parent;
the service deliberately has no duplicate suppression. These are verification
service tests, not newly mined unique blocks.

The configured mixed-phase service criterion is: each continuously submitting
legitimate client completes a correct valid verification in every interior
**20-second configured window**, has measured per-client p99 logical latency
at most **20 s configured**, and has no logical submission deadline misses.
Logical latency includes transport retries, not just successful socket RTT.
Offered/retried/completed requests and per-client timestamps remain in evidence.
The driver checks a one-second grid of window starts. The separate
[continuous-window checker](analysis/continuous_liveness.py) additionally checks
all real-valued interior window starts from the raw completion gaps; all
successful mixed scenarios pass, while the failed cross-pod run remains false.
The phases include malformed traffic, unknown parents, slow incomplete frames,
valid-format admitted-parent cache churn and legitimate/hostile connections
sharing one source address. The latter does not grant newcomers an identity.

For admitted, continuously queued work, source round robin prevents another
admitted source from monopolizing the worker; same-source pending connections
join its FIFO. This is a scheduling argument under finite backend execution,
not a universal numerical latency proof. The observed 20-second criterion is
evidence for the declared loads and hardware. It is not a guarantee for every
possible parent distribution, CPU, network or fault. [measurement-tables.md](measurement-tables.md)
reports measured completions, latency, derivations, evictions and RSS.

The cross-datacenter test uses four legitimate TCP clients sharing one external
source plus eight hostile sources on the server. Traffic reaches the actual
public forwarded TCP port without a local relay. All four legitimate clients
pass the same criterion. Controlled multi-source stress uses distinct loopback
addresses on the rented server, not a claimed Internet botnet. The failed
same-datacenter connection attempt is preserved separately. No source-address
spoofing or attack against an unrelated endpoint occurs.

## The admission limit is a real failure boundary

An explicit negative control occupies all **64 configured slots** across all
**16 configured sources**. A newcomer is refused in **three measured cycles**,
then verified correctly after attack connections close. Thus **universal
newcomer liveness FAILS**. Bounded memory alone does not solve denial of service.
The successful mixed tests establish service for admitted finite-source work;
they do not establish resistance to an unlimited Sybil attacker, physical-link
saturation, host failure, or attackers occupying all connections behind a shared
NAT before a legitimate newcomer arrives.

Production work still needs a reviewed identity/admission and connection-budget
policy, trusted chain-parent admission, reorg/target handling, adversarial
peer discovery and operational testing. Those decisions remain OPEN for the
team; this lab does not install an incomplete policy in Laser. An arbitrary
client-selected parent cannot force bank work in this laboratory, while
admitted-parent churn can and does consume the bounded allowed work.

## Matrix attribution and limits

Read [matrix-timing.md](matrix-timing.md) for the predeclared ABBA comparison,
full-fold checks, observer overhead and hardware-counter denial. The observed
fused CTA span is about **98.57% measured inclusive matrix mainloop**, **0.71%
measured quantize/fold** and **0.56% measured final epilogue/store**. These are
medians of per-CTA clock64 ratios, not additive GPU wall-time shares.

The matrix mainloop includes global/shared loads, synchronization and waiting.
The earlier approximately 98.7% observer must be described the same way; it is
not a tensor-core utilization measurement. Pure multiply activity and a
photonic-removable wall-time fraction remain unmeasured. No photonic Amdahl
ceiling follows from these phase ratios. CUDA kernel bodies remain private
until an eligible freeze; no candidate source freeze is issued here.

## Reproduction

The public CPU lab requires Linux, GCC/OpenMP, OpenSSL development headers,
Python 3 and GNU timeout. Use an isolated authorized research machine, with
port 19090 available; the test service binds all IPv4 interfaces for finite
phases. It does not run a Laser node. Explicit opt-in:

```sh
LF3_RESEARCH_ACK=1 bash research/qualification/lf3-c20-stage1-2026-10-30/run.sh /absolute/new/results-directory
```

This builds, runs canonical/native sanitizer/fault checks and reproduces the
controlled TCP scenarios, wire and capacity controls. It can consume several
minutes on the rented CPU. Cross-machine reproduction additionally requires a
second owned machine and an explicitly authorized reachable service endpoint;
`control/network_cross.py` and `src/network_load.py --mode remote` expose that
bounded orchestration. Provider provisioning, credentials and private operations
files are excluded. No claim that a single-host replay reproduces Internet
transport is made.

The numerical reducer accepts `matrix` or `network` and writes deterministic
summaries in the configured evidence root. Published raw telemetry is a safety
record, not a new energy study. SHA256SUMS is a research evidence manifest,
not a consensus freeze. Failed runs must remain in any reproduction ledger.
