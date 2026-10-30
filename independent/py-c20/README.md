# Independent LF2 / C20 checker

`ph_indep.py` is the outside reviewer's specification-only implementation,
provided by the project owner on 29 October 2026. It is imported **byte for
byte**, SHA-256 `78f120cae14bfd7cc60dad75da877e796b9e56a6b33c7cfc08760e01e4000f39`.
Its reported prior reproduction of the frozen LF2 vectors and the complete
C20 fixture is established evidence, not a new result claimed by this import.

The checker implements ChaCha20 from [RFC 8439](https://www.rfc-editor.org/rfc/rfc8439)
and uses Python `hashlib` SHAKE256 and NumPy matrix products. It imports no
project C, Rust or CUDA implementation. SHAKE still binds header and nonce and
produces the final digest. ChaCha20 supplies only the C20 vector expansion.

The matrices and vector contain small integers. Every product and intermediate
sum has absolute value at most the specified conservative bound 262144, below
the exact-integer range of binary32. CPU float32 BLAS therefore suffices here;
this argument does not authorize TF32, BF16, approximate optical arithmetic,
or an unchecked GPU BLAS configuration.

Set `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` and `MKL_NUM_THREADS=1` before
starting Python on a shared machine. Install NumPy in your own environment.

```sh
python independent/py-c20/check_vectors.py path/to/c20-experiment-vectors.txt
```

`check_vectors.py` supplies strict failure handling for the new full-fold
vector format. It calls the original checker's functions and compares all
binding, fold and digest bytes. Any disagreement exits immediately with a
`STOP` record. This wrapper is project integration, not a second independent
cryptographic implementation. Do not use Python's `-O` flag: the unmodified
reviewer module includes assertions.

The original script can still reproduce its earlier fixture/statistics report:

```sh
python independent/py-c20/ph_indep.py .
```

Those checks are not automatically rerun by the new vector wrapper. None of
these tools activates a profile, admits a chain parent or mines blocks.
