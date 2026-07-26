#!/usr/bin/env python3
"""Structural probe for the provisional PhotonHash v0.3 R1 recurrence.

The transition matches the fused CUTLASS probe: exact INT32 matrix products
followed by low-bit wrap requantization. It is not a consensus specification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import zlib
from pathlib import Path

import numpy as np


TAG_MATRIX = b"LASER/PhotonHash/v1/matrix"
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
    source = np.frombuffer(packed, dtype=np.uint8)
    result = np.empty(source.size * 2, dtype=np.int8)
    result[0::2] = (source & 15).astype(np.int8) - 8
    result[1::2] = (source >> 4).astype(np.int8) - 8
    return result


def derive_matrix(parent: bytes, n: int) -> tuple[np.ndarray, bytes]:
    seed = shake(TAG_MATRIX + parent, 64)
    packed = shake(seed, n * n // 2)
    return unpack_signed_nibbles(packed).reshape(n, n), packed


def initial_states(n: int, vectors: int, seed: bytes) -> np.ndarray:
    packed = shake(seed, n * vectors // 2)
    return unpack_signed_nibbles(packed).reshape(vectors, n).T.copy()


def quantization_parameters(n: int) -> tuple[int, int]:
    log2n = n.bit_length() - 1
    return 8 + (log2n - 9) // 2, 64 * n


def transition(matrix32: np.ndarray, state: np.ndarray,
               shift: int, offset: int) -> tuple[np.ndarray, np.ndarray]:
    product = matrix32 @ state.astype(np.int32)
    buckets = (((product.astype(np.int64) + offset) >> shift) & 15)
    return (buckets.astype(np.int8) - 8), product


def entropy(histogram: np.ndarray) -> float:
    probabilities = histogram[histogram != 0] / histogram.sum()
    return float(-np.sum(probabilities * np.log2(probabilities)))


def state_hash(state: np.ndarray) -> bytes:
    return hashlib.sha256(state.tobytes(order="C")).digest()


def pack_signed_nibbles(state: np.ndarray) -> bytes:
    flat = ((state.astype(np.int16).ravel(order="C") + 8) & 15).astype(np.uint8)
    return (flat[0::2] | (flat[1::2] << 4)).tobytes()


def analyze(args: argparse.Namespace) -> dict:
    if args.n < 1024 or args.n & (args.n - 1):
        raise ValueError("n must be a power of two at least 1024")
    if args.vectors < 4 or args.vectors % 2:
        raise ValueError("vectors must be an even integer at least 4")
    if args.rounds < 1:
        raise ValueError("rounds must be positive")

    parent = KNOWN_PARENT if args.n == 1024 else shake(
        b"PhotonHash/v0.3/recurrence-analysis/" + args.n.to_bytes(4, "little"),
        32,
    )
    matrix, packed = derive_matrix(parent, args.n)
    checksum = shake(packed, 32).hex()
    if args.n == 1024 and checksum != KNOWN_CHECKSUM:
        raise RuntimeError("independent matrix derivation failed known checksum")
    matrix32 = matrix.astype(np.int32)
    shift, offset = quantization_parameters(args.n)
    scale = 1 << shift
    state = initial_states(
        args.n, args.vectors, b"PhotonHash/v0.3/R1/analysis-seed"
    )

    pair_count = args.vectors // 2
    state[:, pair_count:] = state[:, :pair_count]
    for pair in range(pair_count):
        coordinate = pair % args.n
        value = int(state[coordinate, pair_count + pair])
        state[coordinate, pair_count + pair] = -8 if value == 7 else value + 1

    seen: list[dict[bytes, int]] = [
        {state_hash(state[:, vector]): 0} for vector in range(args.vectors)
    ]
    repeats: list[dict[str, int]] = []
    round_metrics: list[dict[str, float | int]] = []
    minimum_margin = 1.0
    t0 = time.perf_counter()
    first_product = None
    first_next = None
    for round_index in range(1, args.rounds + 1):
        previous = state
        state, product = transition(matrix32, previous, shift, offset)
        if first_product is None:
            first_product = product.copy()
            first_next = state.copy()

        residue = (product.astype(np.int64) + offset) & (scale - 1)
        distance = np.minimum(residue, scale - residue).astype(np.float64)
        normalized_margin = distance / scale
        minimum_margin = min(minimum_margin, float(normalized_margin.min()))
        histogram = np.bincount(
            state.astype(np.int16).ravel() + 8, minlength=16
        )
        avalanche = np.mean(
            state[:, :pair_count] != state[:, pair_count:], axis=0
        )
        fixed = np.all(state == previous, axis=0)
        unique_states = len({
            state_hash(state[:, vector]) for vector in range(args.vectors)
        })
        round_metrics.append({
            "round": round_index,
            "symbol_entropy_bits": entropy(histogram),
            "symbol_mean": float(np.mean(state)),
            "symbol_stddev": float(np.std(state)),
            "decision_margin_p01_scale": float(
                np.quantile(normalized_margin, 0.01)
            ),
            "decision_margin_median_scale": float(
                np.quantile(normalized_margin, 0.50)
            ),
            "decision_margin_min_scale": float(normalized_margin.min()),
            "paired_avalanche_mean": float(np.mean(avalanche)),
            "paired_avalanche_min": float(np.min(avalanche)),
            "fixed_vectors": int(np.sum(fixed)),
            "unique_vector_states": unique_states,
        })
        for vector in range(args.vectors):
            digest = state_hash(state[:, vector])
            if digest in seen[vector]:
                repeats.append({
                    "vector": vector,
                    "first_round": seen[vector][digest],
                    "repeat_round": round_index,
                    "period": round_index - seen[vector][digest],
                })
            else:
                seen[vector][digest] = round_index

    assert first_product is not None and first_next is not None
    approximation = []
    norms = np.sum(matrix32.astype(np.int64) ** 2, axis=0)
    order = np.argsort(norms)[::-1]
    initial = initial_states(
        args.n, args.vectors, b"PhotonHash/v0.3/R1/analysis-seed"
    )
    initial[:, pair_count:] = initial[:, :pair_count]
    for pair in range(pair_count):
        coordinate = pair % args.n
        value = int(initial[coordinate, pair_count + pair])
        initial[coordinate, pair_count + pair] = (
            -8 if value == 7 else value + 1
        )
    for fraction in args.column_fractions:
        count = max(1, min(args.n, int(round(fraction * args.n))))
        columns = order[:count]
        predicted_product = (
            matrix32[:, columns] @ initial[columns, :].astype(np.int32)
        )
        predicted = (
            (((predicted_product.astype(np.int64) + offset) >> shift) & 15)
            .astype(np.int8) - 8
        )
        correct = predicted == first_next
        approximation.append({
            "column_fraction": fraction,
            "columns": count,
            "bucket_accuracy": float(np.mean(correct)),
            "whole_states_exact": int(np.sum(np.all(correct, axis=0))),
            "vectors": args.vectors,
        })

    noise = []
    rng = np.random.default_rng(args.seed)
    for sigma_scale in args.noise_sigma_scales:
        perturbation = rng.normal(
            0.0, sigma_scale * scale, size=first_product.shape
        )
        noisy_product = np.rint(
            first_product.astype(np.float64) + perturbation
        ).astype(np.int64)
        noisy = (
            (((noisy_product + offset) >> shift) & 15).astype(np.int8) - 8
        )
        correct = noisy == first_next
        noise.append({
            "sigma_in_quantization_scales": sigma_scale,
            "bucket_accuracy": float(np.mean(correct)),
            "whole_states_exact": int(np.sum(np.all(correct, axis=0))),
            "vectors": args.vectors,
        })

    packed_state = pack_signed_nibbles(state)
    selected_rounds = sorted(set(
        [1, args.rounds]
        + [value for value in (2, 4, 8, 16, 32, 64, 128)
           if value <= args.rounds]
    ))
    selected_metrics = [
        round_metrics[index - 1] for index in selected_rounds
    ]
    return {
        "tool": "ph_v03_recurrence_analysis.py",
        "status": "research_only",
        "candidate": "R1-F provisional wrap-requantized recurrence",
        "profile": {
            "n": args.n,
            "vectors": args.vectors,
            "rounds": args.rounds,
            "shift": shift,
            "offset": offset,
            "quantization_scale": scale,
        },
        "independent_matrix_derivation": {
            "parent": parent.hex(),
            "checksum": checksum,
            "known_v02_checksum_match": (
                checksum == KNOWN_CHECKSUM if args.n == 1024 else None
            ),
        },
        "recurrence": {
            "elapsed_seconds": time.perf_counter() - t0,
            "repeat_events": repeats,
            "repeat_event_count": len(repeats),
            "minimum_decision_margin_scale": minimum_margin,
            "selected_round_metrics": selected_metrics,
            "final_symbol_histogram_-8_to_7": np.bincount(
                state.astype(np.int16).ravel() + 8, minlength=16
            ).tolist(),
            "final_packed_zlib_ratio": (
                len(zlib.compress(packed_state, 1)) / len(packed_state)
            ),
        },
        "one_round_partial_column_attack": approximation,
        "one_round_additive_noise_probe": noise,
        "limitations": [
            "No short repeat in a finite sample is not proof of a long cycle.",
            "Gaussian integer perturbation is not a physical photonic noise model.",
            "Partial-column results cover one round; adaptive recurrence attacks remain open.",
            "The transition is provisional and has no consensus status."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1024)
    parser.add_argument("--vectors", type=int, default=64)
    parser.add_argument("--rounds", type=int, default=128)
    parser.add_argument(
        "--column-fractions", type=float, nargs="+",
        default=[0.50, 0.75, 0.90, 0.99]
    )
    parser.add_argument(
        "--noise-sigma-scales", type=float, nargs="+",
        default=[0.001, 0.005, 0.01, 0.05]
    )
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    recurrence = result["recurrence"]
    last = recurrence["selected_round_metrics"][-1]
    print(
        f"R1-F n={args.n}, vectors={args.vectors}, rounds={args.rounds}: "
        f"entropy={last['symbol_entropy_bits']:.6f} bits, "
        f"avalanche={last['paired_avalanche_mean']:.6f}, "
        f"repeats={recurrence['repeat_event_count']}, "
        f"minimum_margin={recurrence['minimum_decision_margin_scale']:.6f} scale"
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
