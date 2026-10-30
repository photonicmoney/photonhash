# LF3-K8-C20 experimental qualification: conformance checkpoint

30 October 2026 UTC. **Experiment tags, not a candidate freeze or activation.**
This completed correctness workstream follows the
[published construction](../../../docs/lf3-k8-c20-experiment-1.md).
All counts and timings called **measured** are observations; configured sizes,
coverage design and extrapolations are identified separately. No Laser chain,
miner selection, difficulty, issuance or release changes accompany this work.

## Measured agreement

| Check | Measured result | Scope |
|---|---:|---|
| Canonical C-generated vectors | 560/560 agree in C, CUDA, Python and Rust | Binding h, every byte of the 2048-byte fold F, final digest D |
| CUDA canonical checks | 1,120/1,120 | Packed and fused implementations on every vector |
| Random GPU versus C replay | 1,048,576/1,048,576 | Full h/F/D; zero skipped records |
| SHAKE boundary checks, both profiles | 40,960/40,960 | Binding h and all 4096 signed vector entries; these checks alone do not compare folds |
| Deterministic C20 fuzz | 128/128 cases | Cached/cold/mod-8192 equivalence, incremental state, cancellation, invalid budgets and target ordering |

The C implementation generates the expected vector file. The outside Python
checker derives its own banks, implements RFC 8439 ChaCha20 and uses hashlib
SHAKE256 plus exact-range CPU NumPy products. Rust separately derives its banks
with RustCrypto SHAKE and a direct RFC 8439 block function. CUDA independently
implements binding, vector expansion, GEMM, quantization/fold and final hashing,
but **receives its matrix bank from C**. Four implementations agree; this is
not four independent matrix-bank derivations or four independent authors.

[conformance-SHA256SUMS](conformance-SHA256SUMS) identifies this reviewed
publication selection. It is a transport record, **not** the conditional
v0.5.0 candidate freeze manifest. Later completed workstreams have their own
evidence identities.

The reviewer checker is imported unchanged at
[independent/py-c20](../../../independent/py-c20/README.md), with measured SHA-256
`78f120cae14bfd7cc60dad75da877e796b9e56a6b33c7cfc08760e01e4000f39`.
Its previously established reproduction of frozen LF2 vectors and the original
C20 fixture is not counted as new work here.

## Canonical cases

[c20-experiment-vectors.txt](c20-experiment-vectors.txt) contains h, full F and D
for each case. Configured coverage is the Cartesian product of:

- Four parents: all zero, all FF, and two deterministic SHAKE-generated parents.
- Twenty-eight header lengths: 0, 1, 79, 80, 81, 100, 101, 102, 184, 215,
  216, 217, 236, 237, 238, 351, 352, 353, 372, 373, 374, 487, 488, 489,
  508, 509, 510 and 4096 bytes.
- Five nonces: 0, 1, 4294967295, 4294967296 and 18446744073709551615.

The configured count is 4 × 28 × 5 = 560. Non-empty headers and the two
pseudorandom parents are deterministic fixtures, not wallet or chain data.
The file retains the exact `LF3-K8-C20-experiment.1` profile. Replacing those
domain tags later changes the hash and requires a new vector set.

The separate binding tests use the required C20 lengths 79/80/81,
215/216/217, 351/352/353, 487/488/489 and LF2 lengths 100/101/102,
236/237/238, 372/373/374, 508/509/510. Both add 0, 1, 184 and 4096.
Configured vector tags are 47 bytes for C20 and 26 bytes for LF2; each
binding also contains an 8-byte little-endian nonce. The C20 80-byte-header
binding is therefore 135 bytes, one byte short of SHAKE256's 136-byte rate.
Two GPU mappings, five first-nonce values and batches of 128 are checked per
length/profile. Boundary nonce batches wrap modulo 2^64 as unsigned integers.

## Million-case replay and distribution

The measured final count is **1,048,576**, indices 0 through 1,048,575,
zero skipped records and zero repeated nonces. Every header length from
0 through 4096 occurs: measured 200–315 cases per length, median 256.
Full length histograms and nonce-bit counts are in
[random-coverage.json](random-coverage.json).

One fixed, nonzero parent is used:
`94b5cbbc10a2ae594eda1305602c9ed036987f387cecd1885622b9488373af0b`.
Case generation uses deterministic SHAKE-derived bytes with seed
`2a75f908365227afeff277b10a5f29172c24b7d2584db26b10ea0d5029dab93e`.
The 16-bit length value is reduced modulo 4097: lengths 0–4080 have 16
preimages and lengths 4081–4096 have 15. This slight configured bias is
explicit; this is not an exactly uniform-length corpus. No extreme nonce
appeared randomly; the canonical vectors cover those separately.

GPU output was replayed by an exact C AVX2 engine using int16 products and
int32 sums, eight attempts together. The first 128 cases were additionally
checked against the scalar C path. There is no saturating byte multiply-add
or approximate accumulation. The measured C replay used 1124.671 seconds
elapsed and 8208.492 process CPU seconds; these are contended batch-corpus
costs, not single-header verification economics.

Raw records contain h (32 bytes), F (2048 bytes) and D (32 bytes), plus an
80-byte corpus header. Measured file length is 2,214,592,592 bytes. Its
measured SHA-256 is
`578ed62c31c1715722c5ea36020a9e93055dafcbcbbea761af195397a39491a7`.
The C reader checked the record count, final EOF and the SHAKE256 stream
commitment
`d595202b4501a597ffd957ad08a0afd21f404beef61896648e76dce7e0c21c14`.
The raw corpus is retained outside Git because of its size; it is not a
download supplied by this checkpoint. Generator and CUDA benchmark sources
remain outside this publication pending the conditional freeze. Independent
CPU reproduction of the canonical vectors is available now; the complete
GPU benchmark is not yet publicly reproducible from this selection.

## Recheck the published vectors

Use a remote or otherwise explicitly authorized machine. These commands
derive large matrix banks and must not be mistaken for trivial text checks.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python independent/py-c20/check_vectors.py \
  research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt

cargo run --release --locked \
  --manifest-path independent/rust-lf2/Cargo.toml --bin c20-vectors -- \
  research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt
```

The Rust executable checks the RFC 8439 primitive vector before evaluating
the file. Python compares every h/F/D byte and rejects execution with `-O`.
Neither checker decides activation or admits a parent into a verifier cache.

## Failures and limits

The [run ledger](ledger.json) preserves failed and interrupted work, including
the local crash, initial setup/build failures and a diagnostic timing-control
layout mismatch. That mismatch affected the newly instrumented single-pass
control, not the production kernels or this million-case corpus. Its timing
is invalid and excluded. The corrected control subsequently passed 491,520
measured full-fold checks; this is diagnostic evidence, not extra independent
canonical vectors.

An initial remote stock-power energy confirmation hit the retained 80°C
thermal guard and was stopped; it supplies no valid confirmation estimate.
The driver rejected a 350 W request and denied permission for its supported
400 W minimum. Subsequent confirmation uses a predeclared nominal 50% event
duty cycle, with the original 575 W limit and thermal guard unchanged.
Those paced energy results will include inter-window idle board energy;
sustained unpaced qualification remains open.

The previous local partial random run and the reviewer's earlier 108,800-case
checkpoint are **not added** to the final remote million-case count. No
failed sample is silently replaced. Local execution is disabled after the
owner's machine lost display and required reboot. The Windows CUDA stall and
crash causes remain unresolved; a successful remote Linux initialization
does not resolve them. Performance, security economics and any freeze are
separate decisions. Statistical screening and finite conformance do not
prove a work lower bound or monetary safety.
