# C20 exact arithmetic: mapped-area follow-up

**Status: REVISE. Experimental evidence, not a candidate freeze.** This study
changes no hash, domain tag, Laser software or activation rule. It advances the
[earlier hardware proxy](../lf3-c20-security-2026-10-30/README.md) from a hand
gate-count estimate to reproducible RTL synthesis and formal equivalence. It
does **not** establish an ASIC energy advantage or photonic competitiveness.

## Result and interpretation

All ratios in this paragraph are **inferred from synthesis**, not measured
silicon: the 13-bit combinational multiply-accumulate maps to **0.5790 times**
the cell area of the 32-bit version, and **0.7918 times** the 20-bit version.
With accumulator registers, reset and enable, the corresponding ratios are
**0.4995** and **0.7320**. Complete cell counts and unrounded ratios are in
[the machine-readable summary](evidence/mapped-area-summary.json) and
[tables](mapped-area-tables.md).

This is an exact cheaper arithmetic representation, a hardware-economics
finding under the owner's clarified stop rule. It retains every int4 product
and every accumulation. No work-skipping shortcut, measured energy saving or
new full-hash implementation is claimed. An ASIC's competitor should be an
optimized exact digital implementation, rather than a generic GPU accumulator.

## Why the narrower arithmetic is exact

For the configured eight passes and 4096 rows per pass, each row sum has 4096
signed int4 products. A product lies between -56 and 64, so every partial sum
lies within [-229376, 262144], inside signed 20-bit range. The quantizer's
four-bit result uses bits 12 through 9 of the sum's two's-complement residue:
`floor(y / 512) mod 16`. Retaining the accumulator modulo 8192 therefore
preserves the required nibble, even though it does not retain the full sum.
The following are formal/model results, not silicon measurements:

- The SAT proof covers every signed int4 input pair and every 20-bit incoming
  accumulator: the next 13-bit residue equals the low 13 bits of the 20-bit
  result. Induction from zero gives the same residue after any sequence of
  products. The row bound connects that residue to the unoverflowed sum.
- Six mapped-netlist equivalence checks pass: combinational and registered
  versions, each configured at 13, 20 and 32 accumulator bits. The checks use
  the library's Boolean cell models; the registered checks include induction.
- **Measured test count:** 262,144 accumulation comparisons, from 64 deterministic
  rows of 4096 terms. The simulation checks 32-bit gold, signed 20-bit gold,
  13-bit residue and each row's final quantizer bits. Edge rows include the
  largest positive and negative products; remaining rows use a fixed PRNG.

These checks strengthen arithmetic correctness under the RTL/tool/library
models. They neither replace the published full-fold vectors nor increase
the count of independent full-hash implementations.

## Mapping method and limits

The source is [mac.v](src/mac.v); all accumulation output bits remain observable
in each width comparison. Otherwise a tool could delete the unused upper bits
of the wide baseline and obscure the arithmetic-width comparison. Both
combinational and registered mappings use the same Yosys/ABC flow, typical
cell library and no clock-period target. Hierarchical cell counts include the
registered module's combinational child. Raw synthesis, proof and simulation
logs, process receipts, JSON netlists and [mapped Verilog](mapped/) are retained.

The **measured tool version** is Yosys 0.33, git sha1 2584903a060. The external
Nangate45 library is pinned to OpenROAD-flow-scripts commit
`75cd896b6d1ea33d2e8cdc3046b55cfd34ed963b`; its **measured artifact SHA256** is
`8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`.
Its upstream [README](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/75cd896b6d1ea33d2e8cdc3046b55cfd34ed963b/flow/platforms/nangate45/README.md)
explicitly describes it as a deliberately non-manufacturable research library.
The [upstream license](upstream-LICENSE) and [README](upstream-README.md) are
preserved. The library body is fetched by the reproducer, not bundled here.
Own RTL and tooling are MIT under the repository license.

Cell area is an **inferred arithmetic proxy**. This experiment excludes memory,
bank distribution, SHAKE, ChaCha, fold/control, I/O, physical routing, clock
trees, switching activity, capacitance, leakage, timing closure, process
variation and packaging. There is no fabricated chip, power simulation,
frequency-normalized comparison or measurement of energy per correct attempt.
It cannot establish a whole-miner ASIC/GPU/photonic energy ratio. Library area
units and ratios should not be promoted to a physical die-size forecast.

## Reproduce remotely

Run on a disposable remote CPU machine with Python 3, Yosys/ABC and Icarus
Verilog installed. This opt-in command performs finite synthesis/proof work;
it was not executed on the owner's local computer.

```sh
python3 src/reproduce.py /absolute/new/results-directory --ack-research
```

The output directory must not already exist. The script checks the pinned
library digest, records raw logs and finite process timeouts, and refuses
qualification if a proof, mapping, simulation or equivalence process fails.
Tool versions can affect area mapping; reproduce with the recorded version
for comparison. A clean invocation from this selected public source passed
before publication, independently of the initial script orchestration.

`SHA256SUMS` is a transport/integrity manifest of this evidence selection. It
is **not** a candidate freeze manifest. There were no failed proof, mapping,
simulation or equivalence runs in this workstream; setup/provenance receipts
are retained separately in the remote campaign ledger. Earlier failed or
invalid GPU runs remain in their original published evidence packages.

## Remaining decision work

A hardware reviewer still needs a manufacturable process, useful throughput
target, memory architecture and post-layout power/timing analysis. Grinding,
precomputation and sparse-execution economics need separate cryptographic and
hardware scrutiny. Physical photonic noise and complete-system energy remain
unmeasured. This result closes neither of those reviews and does not authorize
activation or selection of block time, difficulty or header serialization.
