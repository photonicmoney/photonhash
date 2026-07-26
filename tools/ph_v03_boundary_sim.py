#!/usr/bin/env python3
"""PhotonHash v0.3 boundary yield and energy simulator.

This research-only tool evaluates a physical boundary against the exact
integer bucket rule used by the provisional R1 recurrence.  It deliberately
counts failed analog trajectories through joules per valid exact attempt.
It does not specify a consensus construction.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


class ScenarioError(ValueError):
    pass


def _distribution(value: Any, path: str) -> tuple[float, float, float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number):
            raise ScenarioError(f"{path} must be finite")
        return number, number, number
    if not isinstance(value, dict) or set(value) != {"low", "mode", "high"}:
        raise ScenarioError(
            f"{path} must be a number or low/mode/high distribution"
        )
    low, mode, high = (float(value[key]) for key in ("low", "mode", "high"))
    if not all(math.isfinite(item) for item in (low, mode, high)):
        raise ScenarioError(f"{path} must be finite")
    if not low <= mode <= high:
        raise ScenarioError(f"{path} must satisfy low <= mode <= high")
    return low, mode, high


def _sample(value: Any, rng: np.random.Generator, size: int, path: str) -> np.ndarray:
    low, mode, high = _distribution(value, path)
    if low == high:
        return np.full(size, low, dtype=np.float64)
    return rng.triangular(low, mode, high, size=size)


def _positive(value: Any, path: str, allow_zero: bool = True) -> None:
    low, _, _ = _distribution(value, path)
    if low < 0 or (not allow_zero and low == 0):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ScenarioError(f"{path} must be {qualifier}")


def _probability(value: Any, path: str) -> None:
    low, _, high = _distribution(value, path)
    if low < 0 or high > 1:
        raise ScenarioError(f"{path} must stay in [0, 1]")


def validate_profile(profile: dict[str, Any]) -> None:
    required = {
        "id", "architecture", "n", "rounds", "boundary_count",
        "residue_steps", "electronic_energy_uJ", "electronic_latency_us",
        "matrix_energy_uJ", "matrix_latency_us", "matrix_lane_multiplier",
        "boundary_energy_fJ_per_lane_decision", "boundary_latency_ps",
        "fixed_energy_uJ", "fixed_latency_us", "assist_energy_pJ_per_lane",
        "guard_band_buckets", "assist_success_probability", "redundancy",
        "noise", "calibration_failure_probability_per_boundary",
        "evidence", "evidence_blockers",
    }
    missing = sorted(required - set(profile))
    if missing:
        raise ScenarioError(f"profile missing fields: {', '.join(missing)}")
    if not isinstance(profile["id"], str) or not profile["id"]:
        raise ScenarioError("profile.id must be a non-empty string")
    for name in ("n", "rounds", "boundary_count", "residue_steps", "redundancy"):
        if not isinstance(profile[name], int) or isinstance(profile[name], bool):
            raise ScenarioError(f"profile.{name} must be an integer")
        if profile[name] <= 0:
            raise ScenarioError(f"profile.{name} must be positive")
    if profile["redundancy"] % 2 == 0:
        raise ScenarioError("profile.redundancy must be odd")
    for name in (
        "electronic_energy_uJ", "electronic_latency_us", "matrix_energy_uJ",
        "matrix_latency_us", "matrix_lane_multiplier",
        "boundary_energy_fJ_per_lane_decision", "boundary_latency_ps",
        "fixed_energy_uJ", "fixed_latency_us", "assist_energy_pJ_per_lane",
    ):
        _positive(profile[name], f"profile.{name}")
    _positive(profile["guard_band_buckets"], "profile.guard_band_buckets")
    if _distribution(profile["guard_band_buckets"], "guard")[2] >= 0.5:
        raise ScenarioError("profile.guard_band_buckets must be below 0.5")
    _probability(profile["assist_success_probability"], "assist success")
    _probability(
        profile["calibration_failure_probability_per_boundary"],
        "calibration failure",
    )
    noise = profile["noise"]
    required_noise = {
        "independent_sigma_buckets", "common_sigma_buckets",
        "drift_sigma_per_boundary_buckets", "temperature_sigma_buckets",
        "component_offset_sigma_buckets", "decision_threshold_bias_buckets",
        "residual_lane_error_floor",
    }
    if not isinstance(noise, dict) or required_noise - set(noise):
        raise ScenarioError("profile.noise is incomplete")
    for name in required_noise - {"decision_threshold_bias_buckets", "residual_lane_error_floor"}:
        _positive(noise[name], f"profile.noise.{name}")
    _distribution(
        noise["decision_threshold_bias_buckets"],
        "profile.noise.decision_threshold_bias_buckets",
    )
    _probability(noise["residual_lane_error_floor"], "residual lane floor")
    if not isinstance(profile["evidence"], list) or not profile["evidence"]:
        raise ScenarioError("profile.evidence must be a non-empty list")
    if not isinstance(profile["evidence_blockers"], list):
        raise ScenarioError("profile.evidence_blockers must be a list")


def validate_suite(suite: dict[str, Any]) -> None:
    if suite.get("schema_version") != 1:
        raise ScenarioError("schema_version must be 1")
    profiles = suite.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ScenarioError("profiles must be a non-empty list")
    identifiers: set[str] = set()
    for profile in _expanded_profiles(suite):
        if not isinstance(profile, dict):
            raise ScenarioError("each profile must be an object")
        validate_profile(profile)
        if profile["id"] in identifiers:
            raise ScenarioError(f"duplicate profile id: {profile['id']}")
        identifiers.add(profile["id"])


def _expanded_profiles(suite: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = suite.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ScenarioError("defaults must be an object")
    expanded = []
    for override in suite.get("profiles", []):
        if not isinstance(override, dict):
            raise ScenarioError("each profile must be an object")
        profile = copy.deepcopy(defaults)
        for key, value in override.items():
            if key == "noise" and isinstance(value, dict):
                base_noise = profile.setdefault("noise", {})
                if not isinstance(base_noise, dict):
                    raise ScenarioError("defaults.noise must be an object")
                base_noise.update(copy.deepcopy(value))
            else:
                profile[key] = copy.deepcopy(value)
        expanded.append(profile)
    return expanded


def _erf(values: np.ndarray) -> np.ndarray:
    """Vectorized erf approximation with maximum error around 1.5e-7."""
    sign = np.sign(values)
    x = np.abs(values)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
             - 0.284496736) * t + 0.254829592) * t
    return sign * (1.0 - poly * np.exp(-(x * x)))


def _normal_cdf(values: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + _erf(values / math.sqrt(2.0)))


def _interval_probability(
    lower: np.ndarray,
    upper: np.ndarray,
    mean: np.ndarray,
    sigma: np.ndarray,
) -> np.ndarray:
    safe_sigma = np.maximum(sigma, 1e-15)
    probability = _normal_cdf((upper - mean) / safe_sigma) - _normal_cdf(
        (lower - mean) / safe_sigma
    )
    deterministic = sigma <= 1e-15
    if np.any(deterministic):
        probability = np.where(
            deterministic,
            ((mean >= lower) & (mean < upper)).astype(np.float64),
            probability,
        )
    return np.clip(probability, 0.0, 1.0)


def _lane_probabilities(
    residue_steps: int,
    independent_sigma: np.ndarray,
    common_offset: np.ndarray,
    threshold_bias: np.ndarray,
    guard: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return correct-unassisted, assisted, and wrong-unassisted probabilities.

    Accumulator residues are discrete and uniformly enumerated.  Assistance is
    triggered when the noisy observation falls within guard distance of any
    physical bucket threshold.  Assisted decisions are handled by the caller.
    """
    residues = np.arange(residue_steps, dtype=np.float64) / residue_steps
    rows = independent_sigma.size
    correct = np.zeros(rows, dtype=np.float64)
    assisted = np.zeros(rows, dtype=np.float64)
    chunk = 256
    for start in range(0, rows, chunk):
        stop = min(rows, start + chunk)
        mean = residues[None, :] + common_offset[start:stop, None]
        sigma = independent_sigma[start:stop, None]
        bias = threshold_bias[start:stop, None]
        band = guard[start:stop, None]
        correct_chunk = _interval_probability(
            bias + band, bias + 1.0 - band, mean, sigma
        )
        assist_chunk = np.zeros_like(correct_chunk)
        # Seven adjacent thresholds cover the admitted noise ranges while all
        # omitted tail mass is conservatively classified as wrong.
        for threshold in range(-3, 4):
            center = bias + float(threshold)
            assist_chunk += _interval_probability(
                center - band, center + band, mean, sigma
            )
        correct[start:stop] = np.mean(correct_chunk, axis=1)
        assisted[start:stop] = np.mean(np.minimum(assist_chunk, 1.0), axis=1)
    wrong = np.maximum(0.0, 1.0 - correct - assisted)
    return correct, assisted, wrong


def _majority_success(probability: np.ndarray, lanes: int) -> np.ndarray:
    if lanes == 1:
        return probability
    threshold = lanes // 2 + 1
    result = np.zeros_like(probability)
    for successes in range(threshold, lanes + 1):
        result += (
            math.comb(lanes, successes)
            * np.power(probability, successes)
            * np.power(1.0 - probability, lanes - successes)
        )
    return np.clip(result, 0.0, 1.0)


def _summary(values: np.ndarray) -> dict[str, float]:
    admitted = values[~np.isnan(values)]
    if admitted.size == 0:
        return {"p05": math.inf, "median": math.inf, "p95": math.inf}
    return {
        "p05": float(np.quantile(admitted, 0.05, method="nearest")),
        "median": float(np.quantile(admitted, 0.50, method="nearest")),
        "p95": float(np.quantile(admitted, 0.95, method="nearest")),
    }


def evaluate_profile(
    profile: dict[str, Any], samples: int, seed: int
) -> dict[str, Any]:
    validate_profile(profile)
    rng = np.random.default_rng(seed)
    n = profile["n"]
    boundaries = profile["boundary_count"]
    lanes = profile["redundancy"]

    def take(name: str) -> np.ndarray:
        return _sample(profile[name], rng, samples, f"profile.{name}")

    electronic = take("electronic_energy_uJ")
    electronic_latency = take("electronic_latency_us")
    matrix = take("matrix_energy_uJ") * take("matrix_lane_multiplier")
    matrix_latency = take("matrix_latency_us")
    boundary_fj = take("boundary_energy_fJ_per_lane_decision")
    boundary_ps = take("boundary_latency_ps")
    fixed = take("fixed_energy_uJ")
    fixed_latency = take("fixed_latency_us")
    assist_pj = take("assist_energy_pJ_per_lane")
    guard = take("guard_band_buckets")
    assist_success = take("assist_success_probability")
    calibration_failure = take("calibration_failure_probability_per_boundary")

    noise = profile["noise"]
    independent = _sample(
        noise["independent_sigma_buckets"], rng, samples, "independent sigma"
    )
    common = _sample(noise["common_sigma_buckets"], rng, samples, "common sigma")
    drift = _sample(
        noise["drift_sigma_per_boundary_buckets"], rng, samples, "drift sigma"
    )
    temperature = _sample(
        noise["temperature_sigma_buckets"], rng, samples, "temperature sigma"
    )
    variation = _sample(
        noise["component_offset_sigma_buckets"], rng, samples, "variation sigma"
    )
    threshold_bias = _sample(
        noise["decision_threshold_bias_buckets"], rng, samples, "threshold bias"
    )
    residual_floor = _sample(
        noise["residual_lane_error_floor"], rng, samples, "residual floor"
    )

    log_exact = np.zeros(samples, dtype=np.float64)
    assist_fraction_sum = np.zeros(samples, dtype=np.float64)
    raw_wrong_sum = np.zeros(samples, dtype=np.float64)
    for boundary in range(boundaries):
        drift_age = float(boundary + 1)
        common_sigma = np.sqrt(
            common * common
            + temperature * temperature
            + variation * variation
            + (drift_age * drift) ** 2
        )
        common_offset = rng.normal(0.0, common_sigma)
        correct, assisted, wrong = _lane_probabilities(
            profile["residue_steps"],
            independent,
            common_offset,
            threshold_bias,
            guard,
        )
        lane_exact = np.clip(
            (correct + assisted * assist_success) * (1.0 - residual_floor),
            0.0,
            1.0,
        )
        logical_exact = _majority_success(lane_exact, lanes)
        boundary_exact = np.power(logical_exact, n) * (1.0 - calibration_failure)
        log_exact += np.log(np.maximum(boundary_exact, 1e-300))
        assist_fraction_sum += assisted
        raw_wrong_sum += wrong

    exact_yield = np.exp(np.maximum(log_exact, -745.0))
    assist_fraction = assist_fraction_sum / boundaries
    raw_wrong = raw_wrong_sum / boundaries
    lane_decisions = float(n * boundaries * lanes)
    boundary_energy = boundary_fj * lane_decisions / 1e9
    assist_energy = assist_pj * lane_decisions * assist_fraction / 1e6
    nominal_energy = matrix + boundary_energy + assist_energy + fixed
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        valid_energy = nominal_energy / np.maximum(exact_yield, 5e-324)
    advantage = electronic / valid_energy
    nominal_latency = (
        matrix_latency
        + boundary_ps * boundaries / 1e6
        + fixed_latency
    )
    valid_throughput_m_s = exact_yield / nominal_latency
    latency_ratio = electronic_latency / nominal_latency

    result = {
        "id": profile["id"],
        "architecture": profile["architecture"],
        "status": "research_only",
        "profile": {
            "n": n,
            "rounds": profile["rounds"],
            "boundary_count": boundaries,
            "logical_decisions": n * boundaries,
            "residue_steps": profile["residue_steps"],
            "redundancy": lanes,
        },
        "samples": samples,
        "exact_output_yield": _summary(exact_yield),
        "nominal_energy_uJ": _summary(nominal_energy),
        "joules_per_valid_exact_attempt_uJ": _summary(valid_energy),
        "complete_system_advantage": _summary(advantage),
        "equal_power_valid_throughput_ratio": _summary(advantage),
        "single_lane_latency_ratio": _summary(latency_ratio),
        "valid_throughput_m_attempts_s": _summary(valid_throughput_m_s),
        "assist_fraction_of_lane_decisions": _summary(assist_fraction),
        "raw_wrong_unassisted_lane_probability": _summary(raw_wrong),
        "energy_components_uJ": {
            "matrix": _summary(matrix),
            "boundary": _summary(boundary_energy),
            "selective_assist": _summary(assist_energy),
            "fixed_control_hash_recheck": _summary(fixed),
        },
        "evidence": profile["evidence"],
        "evidence_blockers": profile["evidence_blockers"],
    }
    conservative = result["complete_system_advantage"]["p05"]
    result["decision"] = {
        "numeric_survival_3x": conservative >= 3.0,
        "numeric_serious_5x": conservative >= 5.0,
        "evidence_qualified": not profile["evidence_blockers"],
        "survives_boundary_phase": (
            conservative >= 3.0 and not profile["evidence_blockers"]
        ),
        "credible_serious_path": (
            conservative >= 5.0 and not profile["evidence_blockers"]
        ),
    }
    return result


def evaluate_suite(
    suite: dict[str, Any], samples: int, seed: int
) -> dict[str, Any]:
    validate_suite(suite)
    results = [
        evaluate_profile(profile, samples, seed + index * 1009)
        for index, profile in enumerate(_expanded_profiles(suite))
    ]
    survivors = [
        item["id"] for item in results
        if item["decision"]["survives_boundary_phase"]
    ]
    serious = [
        item["id"] for item in results
        if item["decision"]["credible_serious_path"]
    ]
    return {
        "schema_version": 1,
        "tool": "ph_v03_boundary_sim.py",
        "status": "research_only",
        "name": suite.get("name", "unnamed boundary suite"),
        "governing_metric": (
            "nominal complete energy divided by byte-exact trajectory yield"
        ),
        "samples_per_profile": samples,
        "seed": seed,
        "results": results,
        "decision_summary": {
            "evidence_qualified_3x_survivors": survivors,
            "evidence_qualified_5x_paths": serious,
            "resolved": not survivors,
            "interpretation": (
                "No evaluated boundary is evidence-qualified for the 3x gate."
                if not survivors else
                "At least one evaluated boundary survives the evidence-qualified 3x gate."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.samples <= 0:
        raise SystemExit("--samples must be positive")
    with args.scenario.open(encoding="utf-8") as handle:
        suite = json.load(handle)
    result = evaluate_suite(suite, args.samples, args.seed)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
        print(f"Wrote {args.output}")
    else:
        print(payload, end="")
    for item in result["results"]:
        advantage = item["complete_system_advantage"]
        exact = item["exact_output_yield"]
        print(
            f"{item['id']}: A05={advantage['p05']:.6g}x, "
            f"A50={advantage['median']:.6g}x, "
            f"P_exact50={exact['median']:.6g}, "
            f"survives={item['decision']['survives_boundary_phase']}"
        )


if __name__ == "__main__":
    main()
