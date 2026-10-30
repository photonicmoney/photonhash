# Stage 1 ledger

30 October 2026 UTC. Preserve failures; observations below are measured unless
marked configured or inferred. Experimental tags remain unchanged. No actual
hash mismatch or tested work-avoiding shortcut was observed in this workstream.
This is not a proof that no shortcut exists.

| Trial | Outcome | Interpretation |
|---|---|---|
| First CPU server placement | FAIL before container startup: OCI/runc session-keyring creation, disk quota exceeded | Provider-host initialization failure; no test ran. Original system log retained privately; failed pod deleted and absence verified. |
| Replacement CPU server bootstrap/native build | PASS | Four configured vCPUs, shared EPYC allocation; not dedicated modest hardware. |
| Native canonical cache check | PASS, 560 full traces and target decisions | No unknown-parent native work; actual h/fold/digest exactness checked. |
| ASAN/UBSAN allocation-fault suite | PASS, 16 configured failure positions | Deliberate allocation failures are expected control outcomes, not hash mismatches; recovery traces agree. Sanitized times excluded from performance claims. |
| TCP cold coalescence | PASS, 32 valid clients, one derivation | One native owner prevents concurrent duplicate bank creation. |
| Junk-only TCP | PASS, 5024 pre-hash refusals, zero native work | Does not establish availability by itself; mixed tests follow. |
| Baseline, junk, slow, churn and shared-source phases | PASS | Four ordinary legitimate clients meet the configured 20-second service criterion in each phase. |
| First cross-pod trial, same datacenter | FAIL, zero legitimate completions | Neither forwarded SSH nor service port was reachable from that client; server saw only eight local hostile clients. Failed latency/service result retained, not pooled with success. |
| Direct private-address reachability diagnostic | FAIL, timeout | No private-network connectivity was assumed or used. No unrelated destination was tested. |
| Different-datacenter reachability diagnostic | PASS for owned forwarded SSH and service | Permits a genuine external TCP repeat without a local relay. |
| Second cross-pod trial, different datacenters | PASS, 107 legitimate valid completions | Four external clients share one source; eight local sources churn admitted banks. Maximum client p99 2.726690 s; every interior 20-second window served. |
| Slot-exhaustion negative control | Universal newcomer liveness FAILS as expected in three cycles | Cache/memory stays bounded; newcomer correctly verifies after attackers release slots. This is a real admission limitation, not evidence of complete DoS resistance. |
| Canonical TCP framing and strict target decisions | PASS, 560 canonical responses plus 16 coalesced frames | Known-invalid and valid PoW responses both checked; full fold checked separately in native path. |
| Full-capacity admitted-client stress | PASS, 64 slots / 16 sources, 120 configured seconds | 60 hostile + four ordinary legitimate clients; 204 correct legitimate completions. No reserved lane; includes 90-second connection expiry. |
| Remote server-GPU build and phase experiment | PASS | Four exact paths, fixed ABBA configuration, correctness prerequisites and continuous thermal/telemetry guard pass. These are short timing diagnostics, not sustained-energy confirmation. |
| Hardware metric discovery on server GPU | FAIL, ERR_NVGPUCTRPERM despite process exit 0 | No tensor activity measurement; no permission/driver/clock workaround. Pure multiplication activity OPEN. |
| First alternate Community RTX4090 placement | FAIL, HTTP 400/no capacity | No resource created and no workload ran. Predeclared single permission probe could not be obtained. |
| Owner-requested retry of same placement | FAIL, HTTP 400/no capacity | Explicit new instruction authorized one retry. No resource created. Further profiling-host choice requested separately. |
| Peer evidence download/round-trip checks | PASS | Complete GPU/client archives restored and every selected file hash verified on the CPU server before deleting those rentals. |

The same-datacenter symptoms are consistent with the provider's published
[cross-pod public-port issue](https://github.com/runpod/runpod-python/issues/337).
That is supporting context, not proof of the provider's internal root cause.
We directly measured refusal of both owned forwarded ports from the first
client and successful reachability from the different datacenter.

No qualification run was silently replaced. The second cross-pod run changes
the transport location after the failed reachability checks; workload and
service criterion remain fixed. Full-capacity stress was declared before its
own samples as an additional stronger test, not selected to rescue a failure.
No current result resolves the historical Windows CUDA stall/display loss,
sensor calibration, external cryptographic review or whole photonic/ASIC economics.
