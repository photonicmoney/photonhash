#!/usr/bin/env python3
"""Adversarial screen for the LF2 requantize-and-XOR fold.

This independently derives the LF2 matrix bank with hashlib, evaluates exact
integer products, and tests whether omitted passes or a collapsed aggregate
predict the final folded nibble vector. It is evidence, not a security proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import zlib

import numpy as np

TAG_MATRIX = b"LASER/PhotonHash/v1/matrix"
TAG_VECTOR = b"LASER/PhotonHash/v1/vector"
TAG_LF2_MATRIX = b"LASER/PhotonHash/launch-LF2/matrix"


def shake(data: bytes, length: int) -> bytes:
    return hashlib.shake_256(data).digest(length)


def unpack_signed_nibbles(packed: bytes) -> np.ndarray:
    raw = np.frombuffer(packed, dtype=np.uint8)
    result = np.empty(raw.size * 2, dtype=np.int8)
    result[0::2] = (raw & 15).astype(np.int8) - 8
    result[1::2] = (raw >> 4).astype(np.int8) - 8
    return result


def derive_matrix(parent: bytes, n: int) -> np.ndarray:
    seed = shake(TAG_MATRIX + parent, 64)
    packed = shake(seed, n * n // 2)
    return unpack_signed_nibbles(packed).reshape(n, n)


def pass_parent(parent: bytes, pass_index: int) -> bytes:
    if pass_index == 0:
        return parent
    return shake(
        TAG_LF2_MATRIX + parent + pass_index.to_bytes(4, "little"), 32
    )


def derive_vectors(header: bytes, n: int, count: int) -> np.ndarray:
    result = np.empty((n, count), dtype=np.int8)
    for nonce in range(count):
        h_in = shake(TAG_VECTOR + header + nonce.to_bytes(8, "little"), 32)
        result[:, nonce] = unpack_signed_nibbles(shake(h_in, n // 2))
    return result


def quantize(y: np.ndarray, n: int) -> np.ndarray:
    shift = 8 + (int(math.log2(n)) - 9) // 2
    return (((y.astype(np.int64) + 64 * n) >> shift) & 15).astype(np.uint8)


def entropy(histogram: np.ndarray) -> float:
    probabilities = histogram[histogram != 0] / np.sum(histogram)
    return float(-np.sum(probabilities * np.log2(probabilities)))


def pack_nibbles(values: np.ndarray) -> bytes:
    packed = values[0::2] | (values[1::2] << 4)
    return packed.astype(np.uint8).tobytes()


def match_score(predicted: np.ndarray, exact: np.ndarray) -> dict:
    correct = predicted == exact
    whole = np.all(correct, axis=0)
    return {
        "nibble_accuracy": float(np.mean(correct)),
        "whole_vector_exact": int(np.sum(whole)),
        "vectors": int(whole.size),
    }


def analyze(args: argparse.Namespace) -> dict:
    parent = shake(b"PhotonHash LF2 fold parent v1", 32)
    header = shake(b"PhotonHash LF2 fold header v1", 80)
    vectors = derive_vectors(header, args.n, args.vectors)
    vectors_i32 = vectors.astype(np.int32)
    pass_buckets = np.empty(
        (args.passes, args.n, args.vectors), dtype=np.uint8
    )
    sum_y = np.zeros((args.n, args.vectors), dtype=np.int64)
    started = time.perf_counter()
    for pass_index in range(args.passes):
        matrix = derive_matrix(pass_parent(parent, pass_index), args.n)
        y = matrix.astype(np.int32) @ vectors_i32
        pass_buckets[pass_index] = quantize(y, args.n)
        sum_y += y

    folded = np.bitwise_xor.reduce(pass_buckets, axis=0)
    folded_histogram = np.bincount(folded.ravel(), minlength=16)
    pass_histogram = np.bincount(pass_buckets.ravel(), minlength=16)

    omission = []
    for missing in sorted(set(args.missing_passes)):
        if missing <= 0 or missing >= args.passes:
            continue
        predicted = np.bitwise_xor.reduce(
            pass_buckets[: args.passes - missing], axis=0
        )
        score = match_score(predicted, folded)
        score.update({
            "missing_passes": missing,
            "work_fraction": (args.passes - missing) / args.passes,
            "random_exact_log2_probability": -4 * args.n,
            "empirical_independent_log2_probability": (
                args.n * math.log2(score["nibble_accuracy"])
            ),
        })
        omission.append(score)

    collapsed_candidates = []
    shift = 8 + (int(math.log2(args.n)) - 9) // 2
    offsets = {
        "single_offset": 64 * args.n,
        "summed_offsets": 64 * args.n * args.passes,
        "zero_offset": 0,
    }
    for name, offset in offsets.items():
        collapsed = (((sum_y + offset) >> shift) & 15).astype(np.uint8)
        score = match_score(collapsed, folded)
        score["candidate"] = name
        collapsed_candidates.append(score)

    pair_equal = []
    for left in range(args.passes):
        for right in range(left + 1, args.passes):
            pair_equal.append(float(np.mean(
                pass_buckets[left] == pass_buckets[right]
            )))

    compressed = []
    for vector_index in range(args.vectors):
        packed = pack_nibbles(folded[:, vector_index])
        compressed.append(len(zlib.compress(packed, 9)) / len(packed))

    return {
        "tool": "ph_launch_fold_analysis.py",
        "profile": {
            "n": args.n,
            "passes": args.passes,
            "vectors": args.vectors,
            "logical_macs": args.passes * args.n * args.n,
        },
        "independent_derivation": "hashlib.shaKE256",
        "pass_bucket_histogram": pass_histogram.tolist(),
        "folded_bucket_histogram": folded_histogram.tolist(),
        "folded_entropy_bits_per_nibble": entropy(folded_histogram),
        "folded_zlib_ratio_mean": float(np.mean(compressed)),
        "pairwise_bucket_equality": {
            "mean": float(np.mean(pair_equal)),
            "minimum": float(np.min(pair_equal)),
            "maximum": float(np.max(pair_equal)),
            "uniform_expectation": 1 / 16,
        },
        "pass_omission": omission,
        "linear_collapse_candidates": collapsed_candidates,
        "elapsed_seconds": time.perf_counter() - started,
        "interpretation": {
            "exact_fold_required_before_final_shake": True,
            "one_unknown_uniform_nibble_probability": "2^-4",
            "whole_vector_guess_probability": f"2^-{4 * args.n}",
            "limitation": (
                "This tests omission and simple aggregate-collapse attacks. "
                "It does not prove that no circuit can compute the folded "
                "quantized products more cheaply than separate products."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1024)
    parser.add_argument("--passes", type=int, default=16)
    parser.add_argument("--vectors", type=int, default=32)
    parser.add_argument(
        "--missing-passes", type=int, nargs="+", default=[1, 2, 4, 8, 15]
    )
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.n < 1024 or args.n & (args.n - 1):
        parser.error("n must be a power of two at least 1024")
    if args.passes < 2 or args.passes > 32:
        parser.error("passes must be in 2..32")
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
