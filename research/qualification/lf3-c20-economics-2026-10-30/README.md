# LF3-K8-C20 CPU verification and parent-turnover economics

30 October 2026 UTC. **Experimental measurements; no freeze or activation.**
This checkpoint measures CPU-only hash evaluation and bank preparation, then
calculates their implications for proposed block intervals. It does not choose
a block interval or integrate the hash into Laser.

## Measurement scope

The measured host was an AMD EPYC 7543 in a RunPod GPU server. The verification
programs use CPU software only, with one or two selected CPU cores. No GPU
workload ran during these timings. The advertised allocation was 15 vCPU; the
observed container quota was 12.75 CPU equivalents. This is **not** a dedicated
modest CPU or a measured low-power physical machine. Two small CPU-only pod
attempts failed to provide reachable SSH and were deleted. That qualification
gap remains OPEN rather than being replaced by an invented laptop estimate.

The portable C path evaluates the exact C20 hash with an explicitly supplied
bank. The independent Python path uses the imported spec-only checker and
single-thread CPU NumPy/BLAS. It stores float32 banks; the coefficient products
and partial sums stay in the exact integer range of that format. No GPU BLAS
or tensor-float approximation is used by the CPU checker.

“Cached verify” below means core hash evaluation with an already derived bank;
it excludes node parsing, admission, scheduling and target policy. “Cold verify”
derives a logical new parent bank and computes one hash. OS caches are not
flushed. Cached verification is not the cost of syncing a chain with a new
parent at every header. Measurements include allocator effects in the stated
path; separately measured stage medians need not sum to the cold median.

[Measured records](cpu-economics-records.json), the
[summary and inferred projections](cpu-economics-summary.json), and
[tables](economics-tables.md) retain sample counts, medians, MAD and inferred
95% intervals. Intervals use 4,000 configured circular moving-block bootstrap
resamples, span three neighboring samples. They describe this run, not
between-machine variability, worst-case latency or an upper bound.

## Header dependencies and parallel verification

An initial throughput measurement forked two processes to work on independent
parents. Those observations are retained, but **are not a validated header-sync
algorithm**: a node must preserve its admission rules while following parent
dependencies.

The replacement C timing keeps a serial synthetic parent dependency: the next
parent is the previous digest. Two CPU workers derive different matrices
inside the bank of the current selected parent. Before timing, three complete
128 MiB banks were byte-compared with serial C, and their complete h/F/D
outputs agreed. The timing then covers 31 measured dependent-parent steps.
It does not validate a Laser chain, admit speculative unknown parents, or
claim unlimited multicore scaling.

The tables project a configured 365-day chain-year at configured 10, 30, 60 and
150 second block intervals. Single-core projections use cold verification;
two-core projections use this within-parent implementation. Elapsed days and
CPU core-days are separate. These are inferred hash-evaluation costs,
excluding networking, disk, transactions, signatures and chain policy.

## Miner parent turnover

The bank has eight configured 4096-by-4096 signed int4 matrices. The current
host/GPU representation is 128 MiB of int8; a packed representation needs
64 MiB. The upload measurement uses eight pageable-host 16 MiB copies after
CUDA context initialization. It is an observed implementation, not a PCIe
bandwidth limit or an optimized pinned-memory transfer.

Bank derivation plus upload is calculated as a fraction of each proposed block
time. Addition of separately measured medians is explicitly inferred. A miner
can perform useful work only after the new admitted parent is known; previous
parent work and optical weights do not automatically transfer to the new bank.
Faster exact SHAKE/bank implementations, more workers and pinned uploads are
possible implementation improvements, not consensus changes or proven bounds.

## What an attacker can make a verifier spend

The measured cached-hash and cold-bank paths quantify the core work a caller
can be induced to perform. A bad nonce for a cached parent generally requires
the complete hash before target rejection. Treating its cost as the cached
hash cost is an inference here: a C20 network-facing reject/admission wrapper
does not yet exist. If a caller derives banks for unauthenticated arbitrary
parents, cold-bank work and allocations can dominate. This is a real integration
requirement, not a spam-resistance property inferred from the hash alone.

The existing LF2 prepared-parent API was tested with 1,015,808 measured unknown
parent misses against a populated two-parent cache. Misses returned without
changing cache generation or occupancy. The full records are in the
[security checkpoint](../lf3-c20-security-2026-10-30/additional-checks.json).
That check establishes separation of lookup and preparation in that API.
C20 currently accepts an explicitly supplied bank; it has no integrated
network admission policy to qualify. A caller must authenticate/admit parents
before costly preparation, bound total resident and in-flight banks, prevent
untrusted cache promotion/eviction, and budget per-peer and global verification
work. Those production rules remain OPEN for team integration and testing.

## Photonic weights must turn over with the parent

Published device timing is not a measurement of an LF3 bank loader:

- Meyer et al. report **62 ms measured full-array reprogramming** in a
  **9-by-3 prototype**, with host/control-path overhead. This is not 62 ms for
  eight 4096-by-4096 matrices. [Nature Communications (2026)](https://doi.org/10.1038/s41467-026-71599-2)
- Zhou et al. report **282 ns write and 556 ns erase measured operation times**
  for their GST memory cell, including post-excitation settling. A cell cycle
  is not an arbitrary multilevel whole-array weight load. [Nature Communications (2023)](https://doi.org/10.1038/s41467-023-38473-x)
- The hybrid optical processor paper reports microheater weight refresh at
  **tens of kilohertz**. That is the authors' device-level capability, not a
  measured full LF3 reload rate. [Nature Communications (2025)](https://doi.org/10.1038/s41467-025-62586-0)

The loading table calculates required throughput for all 134,217,728 configured
logical weights, both for spending a whole block loading and for a configured
1% turnover budget. Packed byte rates assume four bits per logical weight;
physical signed encoding, addressing, calibration, repeated programming,
settling, transfer and redundancy can require more. Retaining weights once
per block also requires sufficient on-device bank storage; a smaller tiled
machine can incur additional reloads while computing attempts.

**Full LF3 photonic compatibility is OPEN at all four proposed block times.**
The cited small-device times are shorter than the block intervals, but do not
establish the required aggregate loading throughput, exact-fold survival,
energy or capacity. No block interval is selected from those publications.
The [photonic tolerance study](../lf3-c20-security-2026-10-30/approximation-tables.md)
uses integer dot-sum noise models; neural-network accuracy or a device SNR
cannot be substituted for LF3 exact-fold correctness.

## Limits and next evidence

Repeat CPU measurements on a dedicated modest machine and, if available, a
low-power machine. Qualify the C20 caller's reject/cache/admission paths under
hostile traffic. Optimize exact bank derivation and test its complete bytes
and outputs before using new performance claims. A full-size photonic loader
and a measured energy-per-correct-fold device are needed for photonic claims.

The C/CUDA research sources remain outside this evidence publication pending
the conditional candidate freeze. Raw measured timing records are public;
this does not yet make the unpublished C prototype independently reproducible
from public source. [economics-SHA256SUMS](economics-SHA256SUMS) is an evidence
transport manifest, not a consensus freeze manifest.
