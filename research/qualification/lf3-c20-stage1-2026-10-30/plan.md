# C20 Stage 1: remote, isolated software qualification

Authorized 30 October 2026. No Shadownet/live node/miner, hash/tag, consensus,
activation or release changes. No local research execution. Local source editing,
Git, read-only review and transport/control only. New goal is active.

## Network design and acceptance fixed before samples

Standalone IPv4 TCP binary service; trusted startup-only parent/target registry.
Clients supply no target, identity, time or parent-admission operation. Per-source
identity comes from the socket, with no trusted forwarded address. Same protocol,
queues and scheduling for attack and legitimate clients. Labels exist in the
test driver only. Fairness is conditional on bounded admitted sources/connections
and a functioning OS/backend, not unlimited Sybils or a saturated link.

Use at most 16 source buckets, 4 connections per source, 64 globally. Fixed frame
size at most 4144 bytes, fixed small response, one outstanding request/connection.
Round robin between sources and FIFO round robin between pending connections of
each source. A single native worker owns exactly two cache slots. Free a victim
before deriving a replacement; never derive in the network event loop. No
unbounded executor, frame, admission, response or logging queue. Server-monotonic
read/queue/lifetime deadlines. Record fixed application bounds, kernel socket
buffers and measured RSS separately; a bank is 64 MiB packed / 128 MiB expanded.

Native cache/canonical conformance and sanitizer checks precede load evidence.
Test cold coalescence and eviction, OOM cleanup and target handling. Every full
hash uses the unchanged reference. A genuine h/fold/digest mismatch stops work.

Fixed network phases: baseline, junk/unknown-parent-only rejection, concurrent
junk plus legitimate clients, incomplete slow clients, admitted-parent churn,
and shared-source queued fairness. At least 60 seconds per mixed phase, with
four nonprivileged legitimate clients. Configured liveness: every continuously
pending legitimate client completes a correct valid verification in every
20-second interior window; measured p99 end-to-end latency <= 20 seconds, with
explicit offered/rejected/completed counts and retries. Do not silently shorten
or drop failed phases. Churn attacks use admitted parents and cannot be dismissed
as merely malformed input. Record the source-admission/Sybil limitation.

Exercise actual TCP between two owned rented machines, as well as controlled
loopback source-address scenarios. All load targets are explicitly task-owned;
bounded load, no scans or unrelated destinations. Test independent fresh clients
and refusal conditions. Verify all returned legitimate digests against frozen
fixtures. Do not mark service robust by rejecting all clients.

## Matrix attribution

Inspect the actual packed/fused kernels. Predeclare paired timing controls before
GPU samples. Preserve operands, dimensions, mainloop arithmetic and correctness
of complete hash paths. Separate minimally perturbed CUDA-event timing from
instrumented phase spans and hardware counters. Quantify observer overhead,
register/spill/resource changes, load/barrier inclusion and overlapping execution.
Do not relabel a loop span as pure tensor utilization or use profiler-inflated
CUDA events as unperturbed timings. If additive pure multiplication time is not
identifiable in a fused/overlapped kernel, provide the measured bounds/proxies
and state that limitation explicitly rather than inventing a percentage.

## Rentals and publication

At most two simultaneous CPU pods (planned four + two vCPUs); four-hour stop
guards, advertised prices checked before provisioning. GPU only after artifacts
are ready; one full Blackwell server GPU, two-hour stop guard, no local GPU,
unchanged board power/clocks, 80 C and two-second telemetry aborts. A different
board is a separate cohort. No idle speculative GPU rental.

All observations measured, extrapolations/models inferred, limits configured.
Keep failures. Publish completed docs, native/network lab sources and evidence
through reviewed explicit PhotonHash selections; GPU bodies stay private before
eligible freeze. Verify actual pushed manifests and public reproductions remotely.
Back up useful private sources/logs; verify downloads remotely; delete task pods
and verify absence before completing the goal. External hardware/security and
activation decisions are outside Stage 1.
