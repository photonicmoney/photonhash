#!/usr/bin/env python3
"""Structural, approximation, and amortization attacks on frozen LF2-K8."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import zlib

import numpy as np

N = 4096
PASSES = 8
TAG_MATRIX = b"LASER/PhotonHash/v1/matrix"
TAG_VECTOR = b"LASER/PhotonHash/v1/vector"
TAG_BANK = b"LASER/PhotonHash/launch-LF2/matrix"


def shake(data: bytes, length: int) -> bytes:
    return hashlib.shake_256(data).digest(length)


def unpack(packed: bytes) -> np.ndarray:
    source = np.frombuffer(packed, dtype=np.uint8)
    output = np.empty(source.size * 2, dtype=np.int8)
    output[0::2] = (source & 15).astype(np.int8) - 8
    output[1::2] = (source >> 4).astype(np.int8) - 8
    return output


def matrix_parent(parent: bytes, index: int) -> bytes:
    if index == 0:
        return parent
    return shake(TAG_BANK + parent + index.to_bytes(4, "little"), 32)


def derive_matrix(parent: bytes) -> tuple[np.ndarray, bytes]:
    seed = shake(TAG_MATRIX + parent, 64)
    packed = shake(seed, N * N // 2)
    return unpack(packed).reshape(N, N), packed


def derive_vectors(header: bytes, count: int) -> np.ndarray:
    output = np.empty((N, count), dtype=np.int8)
    for nonce in range(count):
        h = shake(TAG_VECTOR + header + nonce.to_bytes(8, "little"), 32)
        output[:, nonce] = unpack(shake(h, N // 2))
    return output


def buckets(product: np.ndarray) -> np.ndarray:
    return (((product.astype(np.int64) + 64 * N) >> 9) & 15).astype(np.uint8)


def score(predicted: np.ndarray, exact: np.ndarray) -> dict:
    correct = predicted == exact
    whole = np.all(correct, axis=0)
    accuracy = float(np.mean(correct))
    return {
        "nibble_accuracy": accuracy,
        "whole_vector_exact": int(np.sum(whole)),
        "vectors": int(whole.size),
        "independent_log2_exact_estimate": N * math.log2(max(accuracy, 1e-300)),
    }


def analyze(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    parent = shake(b"PhotonHash LF2 adversarial parent v1", 32)
    header = shake(b"PhotonHash LF2 adversarial header v1", 80)
    x = derive_vectors(header, args.vectors)
    x32 = x.astype(np.int32)

    matrices: list[np.ndarray] = []
    packed_matrices: list[bytes] = []
    exact_passes = np.empty((PASSES, N, args.vectors), dtype=np.uint8)
    hist = np.zeros(16, dtype=np.int64)
    compression = []
    for index in range(PASSES):
        matrix, packed = derive_matrix(matrix_parent(parent, index))
        matrices.append(matrix)
        packed_matrices.append(packed)
        hist += np.bincount(matrix.astype(np.int16).ravel() + 8, minlength=16)
        compression.append(len(zlib.compress(packed, 1)) / len(packed))
        exact_passes[index] = buckets(matrix.astype(np.int32) @ x32)
    exact_fold = np.bitwise_xor.reduce(exact_passes, axis=0)

    # Cross-matrix correlation over the same deterministic entry sample.
    rng = np.random.default_rng(args.seed)
    sample_indices = rng.choice(N * N, size=args.correlation_entries, replace=False)
    samples = np.stack([
        matrix.ravel()[sample_indices].astype(np.float64)
        for matrix in matrices
    ])
    correlations = np.corrcoef(samples)
    off_diagonal = correlations[np.triu_indices(PASSES, 1)]

    # Selected-column approximation: give the attacker each matrix's
    # highest-energy columns and a row-mean correction for omitted columns.
    column_attacks = []
    for fraction in args.column_fractions:
        count = max(1, min(N, int(round(fraction * N))))
        approximate_passes = np.empty_like(exact_passes)
        per_pass_accuracy = []
        for index, matrix in enumerate(matrices):
            matrix64 = matrix.astype(np.int64)
            order = np.argsort(np.sum(matrix64 * matrix64, axis=0))[::-1]
            selected = order[:count]
            omitted = order[count:]
            predicted = matrix64[:, selected] @ x32[selected, :].astype(np.int64)
            if omitted.size:
                row_mean = np.mean(matrix64[:, omitted], axis=1, keepdims=True)
                predicted = predicted + row_mean * np.sum(
                    x32[omitted, :].astype(np.int64), axis=0
                )
            predicted_buckets = buckets(np.floor(predicted).astype(np.int64))
            approximate_passes[index] = predicted_buckets
            per_pass_accuracy.append(float(np.mean(
                predicted_buckets == exact_passes[index]
            )))
        predicted_fold = np.bitwise_xor.reduce(approximate_passes, axis=0)
        result = score(predicted_fold, exact_fold)
        result.update({
            "column_fraction": fraction,
            "columns": count,
            "mean_per_pass_bucket_accuracy": float(np.mean(per_pass_accuracy)),
        })
        column_attacks.append(result)

    # Lower-precision coefficient attacks. Arithmetic right-shift then left
    # shift is deliberately favorable to a simple bit-dropping circuit.
    coefficient_attacks = []
    for dropped_bits in (1, 2, 3):
        approximate_passes = np.empty_like(exact_passes)
        for index, matrix in enumerate(matrices):
            reduced = (
                (matrix.astype(np.int16) >> dropped_bits) << dropped_bits
            ).astype(np.int32)
            approximate_passes[index] = buckets(reduced @ x32)
        predicted_fold = np.bitwise_xor.reduce(approximate_passes, axis=0)
        result = score(predicted_fold, exact_fold)
        result["dropped_coefficient_bits"] = dropped_bits
        coefficient_attacks.append(result)

    # Entire-pass omission with the optimal constant bucket guess for each
    # omitted pass. A guessed fold is useful only when the complete state is
    # exact before SHAKE.
    pass_omission = []
    for missing in range(1, PASSES):
        retained = np.bitwise_xor.reduce(exact_passes[:PASSES - missing], axis=0)
        missing_fold = np.bitwise_xor.reduce(exact_passes[PASSES - missing:], axis=0)
        histogram = np.bincount(missing_fold.ravel(), minlength=16)
        best_guess = int(np.argmax(histogram))
        predicted = retained ^ np.uint8(best_guess)
        result = score(predicted, exact_fold)
        result.update({
            "missing_passes": missing,
            "work_fraction": (PASSES - missing) / PASSES,
            "best_constant_guess": best_guess,
            "efficiency_upper_bound_from_exact_guess": (
                2 ** min(0.0, result["independent_log2_exact_estimate"])
                / ((PASSES - missing) / PASSES)
            ),
        })
        pass_omission.append(result)

    # Skipping a small number of output rows gives almost no work reduction.
    # Use the observed modal folded-nibble probability as a favorable bound.
    fold_histogram = np.bincount(exact_fold.ravel(), minlength=16)
    modal_probability = float(np.max(fold_histogram) / np.sum(fold_histogram))
    row_omission = []
    for missing_rows in (1, 2, 4, 8, 16, 64, 256):
        work_fraction = (N - missing_rows) / N
        log2_exact = missing_rows * math.log2(modal_probability)
        row_omission.append({
            "missing_rows": missing_rows,
            "work_fraction": work_fraction,
            "modal_nibble_probability": modal_probability,
            "log2_exact_guess": log2_exact,
            "efficiency_upper_bound": 2 ** log2_exact / work_fraction,
        })

    # Sampled minors are a cheap structural tripwire, not a proof of full rank.
    minor_results = []
    rows = rng.choice(N, size=args.minor_dimension, replace=False)
    columns = rng.choice(N, size=args.minor_dimension, replace=False)
    for index in range(min(2, PASSES)):
        minor = matrices[index][np.ix_(rows, columns)].astype(np.float64)
        singular = np.linalg.svd(minor, compute_uv=False)
        tolerance = singular[0] * args.minor_dimension * np.finfo(np.float64).eps
        minor_results.append({
            "matrix": index,
            "dimension": args.minor_dimension,
            "rank": int(np.sum(singular > tolerance)),
            "condition_number": float(singular[0] / singular[-1]),
            "top_to_median_singular": float(singular[0] / np.median(singular)),
            "top_quarter_frobenius_energy": float(
                np.sum(singular[:args.minor_dimension // 4] ** 2)
                / np.sum(singular ** 2)
            ),
        })

    expected = int(np.sum(hist)) / 16
    chi_square = float(np.sum((hist - expected) ** 2 / expected))
    setup_intervals = {}
    for seconds in (10, 30, 60, 120, 600):
        setup_intervals[str(seconds)] = {
            "rust_0.227s_fraction": 0.227 / seconds,
            "portable_c_0.497s_fraction": 0.497 / seconds,
            "bitslice_pack_1.276s_fraction": 1.276 / seconds,
        }

    return {
        "tool": "ph_lf2_adversarial.py",
        "profile": {
            "n": N,
            "passes": PASSES,
            "vectors": args.vectors,
            "exact_macs_per_attempt": PASSES * N * N,
            "packed_matrix_bank_bytes": PASSES * N * N // 2,
            "unpacked_int8_bank_bytes": PASSES * N * N,
        },
        "matrix_bank": {
            "entry_histogram_-8_to_7": hist.tolist(),
            "chi_square_15df": chi_square,
            "packed_zlib_ratio_mean": float(np.mean(compression)),
            "packed_zlib_ratio_min": float(np.min(compression)),
            "cross_matrix_correlation_sample_entries": args.correlation_entries,
            "cross_matrix_correlation_abs_mean": float(np.mean(np.abs(off_diagonal))),
            "cross_matrix_correlation_abs_max": float(np.max(np.abs(off_diagonal))),
            "sampled_minors": minor_results,
        },
        "fold": {
            "histogram": fold_histogram.tolist(),
            "entropy_bits_per_nibble": float(-np.sum(
                (fold_histogram / np.sum(fold_histogram))
                * np.log2(fold_histogram / np.sum(fold_histogram))
            )),
            "modal_probability": modal_probability,
        },
        "selected_column_attacks": column_attacks,
        "coefficient_bit_drop_attacks": coefficient_attacks,
        "pass_omission": pass_omission,
        "row_omission": row_omission,
        "cold_setup_amortization": {
            "matrix_is_parent_dependent": True,
            "future_parent_precomputation": "not available under SHAKE preimage assumption",
            "setup_fraction_by_block_interval_seconds": setup_intervals,
            "note": "Setup is paid once after a new parent and approaches zero per nonce at mining batch scale. It must not be charged per attempt."
        },
        "elapsed_seconds": time.perf_counter() - started,
        "limitations": [
            "No finite corpus proves SHAKE-derived matrices are random.",
            "Sampled minors are structural tripwires, not full 4096-rank proofs.",
            "The independence exponents are estimates and are not used as formal security bounds.",
            "Custom GPU, FPGA, or ASIC circuits may improve exact evaluation even when these approximations fail."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", type=int, default=32)
    parser.add_argument(
        "--column-fractions", type=float, nargs="+",
        default=[0.5, 0.75, 0.875, 0.9375, 0.96875, 0.984375, 0.9921875],
    )
    parser.add_argument("--correlation-entries", type=int, default=1_000_000)
    parser.add_argument("--minor-dimension", type=int, default=512)
    parser.add_argument("--seed", type=int, default=0x4C46324B38)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.vectors < 1:
        parser.error("vectors must be positive")
    if not all(0 < fraction <= 1 for fraction in args.column_fractions):
        parser.error("column fractions must be in (0, 1]")
    result = analyze(args)
    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
