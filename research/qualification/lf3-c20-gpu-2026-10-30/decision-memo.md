# LF3-K8-C20 qualification decision memo

**FINAL REVIEW CORRECTION: FUSED LF2 CONFIRMATION INVALID.** Its measured maximum sampling gap is 9.370326 seconds, exceeding the configured two-second limit. All five processes completed, but only the other four variants have eligible telemetry. Neither the live guard nor the original aggregator rejected this gap. Fused-LF2 timing and energy rows are retained as INVALID observations, excluded from qualification. Cause remains OPEN; no retry was made. See [post-review-qualification.json](post-review-qualification.json).

The unchanged original statistics and original validation receipt are retained in `energy-statistics-before-review.json` and `publication-validation-before-review.json`. Their former pass flags are superseded. The current summary marks confirmation incomplete. The portable energy analyzer reproduces the original raw statistics, not qualification; its old `confirmation_complete` field is insufficient. No corrected analyzer execution or new benchmark is claimed. Transport checksums below are file-maintenance checks, not a repeat of research computation.

30 October 2026 UTC. **Recommendation: REVISE. No activation or release.**
This is an assessment of the experimental construction, not the conditional
PhotonHash v0.5.0-candidate.1 freeze package. The team retains the qualification
and activation decisions.

**Established by finite tests and exact identities.** The measured C-generated
vector set has 560 cases; C, CUDA, the unchanged outside Python checker and the
extended Rust implementation agree on h, every fold byte and final digest.
The measured GPU/C random replay reached 1,048,576 full-fold cases with zero
mismatches or skips. Boundary, deterministic fuzz and the existing adversarial
corpus passed their stated finite checks. SHAKE still binds the header/nonce
and final fold; ChaCha20 changes only expansion. Exact mod-8192 arithmetic is
sufficient for the quantizer. Neither that identity nor conformance proves a
lower bound on mining work.

**Provisional economics.** The fixed remote confirmation measures paced GPU
execution, not sustained full-power mining or wall-socket energy. Continuous
power integrals and the cumulative energy counter disagree; narrow statistical
intervals do not resolve their systematic difference. Pure unperturbed matrix
arithmetic time/energy is not independently isolated by a warp-cycle observer.
CPU timing includes bank derivation for each parent, with a serial dependency
preserved in the two-worker test. Dedicated modest and low-power machine
qualification is unavailable. The inferred ASIC datapath proxy favors exact
13-bit residues over full int32; it is not mapped silicon. Photonic reload
capacity, noise calibration and energy per correct fold remain unmeasured at
the full bank size.

**What failed.** The final fused-LF2 run additionally exceeded the two-second sampling limit despite a passed process receipt; its confirmation is invalid. The local GPU incident ended local workload authorization;
Windows initialization/crash causes remain unresolved. The remote unpaced run
hit its thermal guard. A paced attempt lost timely telemetry and was discarded;
a fresh run does not establish the cause of that delay. One instrumented
control had a layout mismatch; its timings were discarded and its corrected
replacement passed. Failed runs remain in the ledger.

**Security interpretation.** No tested work-avoiding method demonstrates an
energy-per-correct-fold advantage under the stated models. Small errors can
preserve the fold: an imperfect device wins economically if its measured
energy ratio is below its measured exact-fold survival. Unmeasured physical
devices are not ruled out. Parent statistics and adversarial regressions do
not close general grinding, sparse execution or specialized-circuit economics.
Existing LF2 cache-miss tests do not qualify an absent C20 network admission
implementation.

**Required next evidence.** Resolve host/telemetry reliability and energy
metrology, qualify a safely cooled sustained configuration, and obtain modest
CPU and hostile-admission measurements. Review vector/parent grinding and
sparse economics externally; map the exact modular datapath before claiming
an ASIC or photonic advantage. Publish the packed and fused reference paths
with conformance evidence at the eventual freeze. If these checks support
freezing, finalize the candidate domain tags, regenerate vectors and rate
boundaries, and publish the normative spec, sources and immutable manifest.

Header serialization/length, difficulty adjustment/work score, genesis
difficulty, timestamp rules, block time and activation remain **OPEN team
integration decisions**. This report does not choose them or change Laser.
