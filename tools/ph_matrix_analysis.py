#!/usr/bin/env python3
"""PhotonHash matrix corpus and approximation-attack experiment.

This independently derives the frozen n=1024 construction with hashlib,
checks a published matrix checksum, then measures cheap corpus statistics and
deep SVD/approximation results. It is an analysis tool, not consensus code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import zlib

import numpy as np

N = 1024
TAG_MATRIX = b"LASER/PhotonHash/v1/matrix"
TAG_VECTOR = b"LASER/PhotonHash/v1/vector"
KNOWN_PARENT = bytes.fromhex(
    "b192df942126d485d17d689f0b22d0ee"
    "eb63e27e2102c50e6baa89b16f2d0d9d"
)
KNOWN_CHECKSUM = (
    "e2493d9a3fe8b30f7710e3f9991e0420"
    "ef740dafeed5aad96148f1b6679b0acf"
)


def shake(data: bytes, length: int) -> bytes:
    return hashlib.shake_256(data).digest(length)


def unpack_signed_nibbles(packed: bytes) -> np.ndarray:
    raw = np.frombuffer(packed, dtype=np.uint8)
    out = np.empty(raw.size * 2, dtype=np.int8)
    out[0::2] = (raw & 15).astype(np.int8) - 8
    out[1::2] = (raw >> 4).astype(np.int8) - 8
    return out


def derive_matrix(parent: bytes) -> tuple[np.ndarray, bytes]:
    seed = shake(TAG_MATRIX + parent, 64)
    packed = shake(seed, N * N // 2)
    return unpack_signed_nibbles(packed).reshape(N, N), packed


def derive_vectors(header: bytes, count: int) -> np.ndarray:
    result = np.empty((N, count), dtype=np.int8)
    for nonce in range(count):
        h_in = shake(TAG_VECTOR + header + nonce.to_bytes(8, "little"), 32)
        result[:, nonce] = unpack_signed_nibbles(shake(h_in, N // 2))
    return result


def buckets(y: np.ndarray) -> np.ndarray:
    return (((y.astype(np.int64) + 64 * N) >> 8) & 15).astype(np.uint8)


def approximation_score(predicted_y: np.ndarray,
                        exact_buckets: np.ndarray) -> dict[str, float | int]:
    predicted = buckets(np.floor(predicted_y).astype(np.int64))
    correct = predicted == exact_buckets
    per_vector = np.all(correct, axis=0)
    return {
        "bucket_accuracy": float(np.mean(correct)),
        "whole_vector_exact": int(np.sum(per_vector)),
        "vectors": int(per_vector.size),
    }


def corpus_parent(index: int) -> bytes:
    return shake(b"PhotonHash matrix corpus v1" + index.to_bytes(8, "little"),
                 32)


def analyze(args: argparse.Namespace) -> dict:
    known_m, known_packed = derive_matrix(KNOWN_PARENT)
    checksum = shake(known_packed, 32).hex()
    if checksum != KNOWN_CHECKSUM:
        raise RuntimeError(
            f"independent derivation mismatch: {checksum} != {KNOWN_CHECKSUM}"
        )

    histogram = np.zeros(16, dtype=np.int64)
    means: list[float] = []
    stddevs: list[float] = []
    compression: list[float] = []
    max_row_mean_abs: list[float] = []
    max_row_norm_z: list[float] = []
    t0 = time.perf_counter()
    deep_matrices: list[np.ndarray] = []
    for index in range(args.matrices):
        matrix, packed = derive_matrix(corpus_parent(index))
        histogram += np.bincount(
            matrix.astype(np.int16).ravel() + 8, minlength=16
        )
        means.append(float(np.mean(matrix)))
        stddevs.append(float(np.std(matrix)))
        compression.append(len(zlib.compress(packed, 1)) / len(packed))
        row_means = np.mean(matrix, axis=1)
        max_row_mean_abs.append(float(np.max(np.abs(row_means + 0.5))))
        row_norms = np.linalg.norm(matrix.astype(np.float32), axis=1)
        max_row_norm_z.append(float(
            np.max(np.abs(row_norms - row_norms.mean())) / row_norms.std()
        ))
        if index < args.deep_matrices:
            deep_matrices.append(matrix)

    expected = int(np.sum(histogram)) / 16.0
    chi_square = float(np.sum((histogram - expected) ** 2 / expected))
    corpus = {
        "matrices": args.matrices,
        "entries": int(np.sum(histogram)),
        "entry_histogram_-8_to_7": histogram.tolist(),
        "chi_square_15df": chi_square,
        "matrix_mean_mean": float(np.mean(means)),
        "matrix_mean_stddev": float(
            np.std(means, ddof=1) if len(means) > 1 else 0.0
        ),
        "entry_stddev_mean": float(np.mean(stddevs)),
        "zlib_ratio_mean": float(np.mean(compression)),
        "zlib_ratio_min": float(np.min(compression)),
        "max_centered_row_mean_abs_max": float(np.max(max_row_mean_abs)),
        "max_row_norm_z_max": float(np.max(max_row_norm_z)),
        "elapsed_seconds": time.perf_counter() - t0,
    }

    header = shake(b"PhotonHash approximation header v1", 80)
    x = derive_vectors(header, args.vectors)
    xf = x.astype(np.float64)
    ranks = sorted(set(args.ranks))
    fractions = sorted(set(args.column_fractions))
    deep: list[dict] = []
    for index, matrix in enumerate(deep_matrices):
        mf = matrix.astype(np.float64)
        exact_y = matrix.astype(np.int32) @ x.astype(np.int32)
        exact_buckets = buckets(exact_y)
        svd_start = time.perf_counter()
        u, singular, vt = np.linalg.svd(mf, full_matrices=False)
        svd_seconds = time.perf_counter() - svd_start
        tol = singular[0] * N * np.finfo(np.float64).eps
        frob2 = float(np.sum(singular * singular))
        centered = mf + 0.5
        centered_top = float(np.linalg.svd(
            centered, compute_uv=False, full_matrices=False
        )[0])

        low_rank = []
        for rank in ranks:
            if rank > N:
                continue
            predicted_y = u[:, :rank] @ (
                singular[:rank, None] * (vt[:rank, :] @ xf)
            )
            score = approximation_score(predicted_y, exact_buckets)
            score.update({
                "rank": rank,
                "frobenius_energy_fraction": float(
                    np.sum(singular[:rank] ** 2) / frob2
                ),
            })
            low_rank.append(score)

        column_sampling = []
        column_norm2 = np.sum(mf * mf, axis=0)
        order = np.argsort(column_norm2)[::-1]
        for fraction in fractions:
            count = max(1, min(N, int(round(fraction * N))))
            selected = order[:count]
            omitted = order[count:]
            predicted_y = mf[:, selected] @ xf[selected, :]
            if omitted.size:
                row_mean = np.mean(mf[:, omitted], axis=1, keepdims=True)
                predicted_y += row_mean * np.sum(xf[omitted, :], axis=0)
            score = approximation_score(predicted_y, exact_buckets)
            score.update({
                "column_fraction": fraction,
                "columns": count,
            })
            column_sampling.append(score)

        deep.append({
            "index": index,
            "rank_float64": int(np.sum(singular > tol)),
            "condition_number": float(singular[0] / singular[-1]),
            "singular_max": float(singular[0]),
            "singular_median": float(np.median(singular)),
            "singular_min": float(singular[-1]),
            "top_to_median": float(singular[0] / np.median(singular)),
            "centered_singular_max": centered_top,
            "mean_bias_outlier_ratio": float(singular[0] / centered_top),
            "svd_seconds": svd_seconds,
            "low_rank": low_rank,
            "column_sampling": column_sampling,
        })

    unknown_rows = [N - rows for rows in (128, 256, 512, 768, 896)]
    partial_rows = [{
        "computed_rows": N - missing,
        "work_fraction": (N - missing) / N,
        "unknown_rows": missing,
        "random_guess_log2_success": -4 * missing,
    } for missing in unknown_rows]

    return {
        "tool": "ph_matrix_analysis.py",
        "profile": {"n": N, "vectors_per_deep_matrix": args.vectors},
        "independent_derivation": {
            "published_checksum": KNOWN_CHECKSUM,
            "computed_checksum": checksum,
            "match": True,
            "known_matrix_mean": float(np.mean(known_m)),
        },
        "corpus": corpus,
        "deep_analysis": deep,
        "partial_row_attack": partial_rows,
        "interpretation": {
            "whole_vector_exact_required_before_final_hash": True,
            "random_missing_bucket_probability": "2^(-4 * unknown_rows)",
            "note": (
                "Bucket accuracy is not a partial proof: one wrong bucket "
                "changes the final SHAKE input. Whole-vector exact counts are "
                "therefore the attack-relevant empirical field."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrices", type=int, default=1000)
    parser.add_argument("--deep-matrices", type=int, default=3)
    parser.add_argument("--vectors", type=int, default=256)
    parser.add_argument("--ranks", type=int, nargs="+",
                        default=[1, 8, 16, 32, 64, 128, 256])
    parser.add_argument("--column-fractions", type=float, nargs="+",
                        default=[0.125, 0.25, 0.5, 0.75, 0.875])
    parser.add_argument("--output")
    args = parser.parse_args()
    if not (1 <= args.deep_matrices <= args.matrices):
        parser.error("deep-matrices must be in 1..matrices")
    if args.vectors < 1:
        parser.error("vectors must be positive")
    result = analyze(args)
    encoded = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
