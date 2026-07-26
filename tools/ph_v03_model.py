#!/usr/bin/env python3
"""Uncertainty-aware hardware-economics model for PhotonHash v0.3 research.

This tool is a rejection and comparison instrument. It does not validate a
candidate architecture and it does not produce consensus parameters.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable


PHOTONIC_COMPONENTS = (
    "optical_matrix",
    "laser",
    "modulation",
    "detection",
    "conversion",
    "feedback",
    "digital_assist",
    "hashing",
    "recheck",
    "control_and_calibration",
)

EVIDENCE_RANK = {
    "placeholder": 0,
    "literature_model": 1,
    "measured_component": 2,
    "representative_prototype": 3,
    "independent_reproduction": 4,
}

CONSENSUS_CHECKS = (
    "bounded_verification",
    "gpu_accessible_genesis",
    "bounded_memory",
    "two_independent_implementations",
    "frozen_vectors",
    "non_consensus_testnet",
)


class ScenarioError(ValueError):
    """Raised when a scenario cannot be evaluated without inventing data."""


def _distribution(spec: Any, path: str) -> tuple[float, float, float]:
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        value = float(spec)
        values = (value, value, value)
    elif isinstance(spec, dict) and set(spec) >= {"low", "mode", "high"}:
        values = (float(spec["low"]), float(spec["mode"]), float(spec["high"]))
    else:
        raise ScenarioError(
            f"{path} must be a number or an object with low, mode, and high"
        )
    low, mode, high = values
    if not all(math.isfinite(value) for value in values):
        raise ScenarioError(f"{path} values must be finite")
    if low < 0 or not low <= mode <= high:
        raise ScenarioError(f"{path} must satisfy 0 <= low <= mode <= high")
    return low, mode, high


def _sample(spec: Any, rng: random.Random, path: str) -> float:
    low, mode, high = _distribution(spec, path)
    if low == high:
        return low
    return rng.triangular(low, high, mode)


def _validate_evidence(component: dict[str, Any], path: str) -> tuple[str, str]:
    evidence = component.get("evidence")
    if not isinstance(evidence, dict):
        raise ScenarioError(f"{path}.evidence must be an object")
    evidence_class = evidence.get("class")
    if evidence_class not in EVIDENCE_RANK:
        allowed = ", ".join(EVIDENCE_RANK)
        raise ScenarioError(f"{path}.evidence.class must be one of: {allowed}")
    source = evidence.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ScenarioError(f"{path}.evidence.source must be a non-empty string")
    return evidence_class, source


def validate_scenario(scenario: dict[str, Any]) -> None:
    if scenario.get("schema_version") != 1:
        raise ScenarioError("schema_version must be 1")
    name = scenario.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ScenarioError("name must be a non-empty string")
    unit = scenario.get("energy_unit")
    if unit not in {"J", "mJ", "uJ", "nJ", "pJ", "fJ", "normalized"}:
        raise ScenarioError(
            "energy_unit must be J, mJ, uJ, nJ, pJ, fJ, or normalized"
        )

    electronic = scenario.get("electronic_components")
    if not isinstance(electronic, dict) or not electronic:
        raise ScenarioError("electronic_components must be a non-empty object")
    accelerable_count = 0
    for name, component in electronic.items():
        path = f"electronic_components.{name}"
        if not isinstance(component, dict):
            raise ScenarioError(f"{path} must be an object")
        _distribution(component.get("energy"), f"{path}.energy")
        _validate_evidence(component, path)
        if not isinstance(component.get("photonic_accelerable"), bool):
            raise ScenarioError(f"{path}.photonic_accelerable must be boolean")
        accelerable_count += int(component["photonic_accelerable"])
    if accelerable_count == 0:
        raise ScenarioError("at least one electronic component must be accelerable")

    photonic = scenario.get("photonic_components")
    if not isinstance(photonic, dict):
        raise ScenarioError("photonic_components must be an object")
    missing = sorted(set(PHOTONIC_COMPONENTS) - set(photonic))
    extra = sorted(set(photonic) - set(PHOTONIC_COMPONENTS))
    if missing:
        raise ScenarioError("missing photonic components: " + ", ".join(missing))
    if extra:
        raise ScenarioError("unknown photonic components: " + ", ".join(extra))
    for name, component in photonic.items():
        path = f"photonic_components.{name}"
        if not isinstance(component, dict):
            raise ScenarioError(f"{path} must be an object")
        _distribution(component.get("energy"), f"{path}.energy")
        _validate_evidence(component, path)

    throughput = scenario.get("equal_power_throughput_ratio")
    if throughput is None:
        raise ScenarioError("equal_power_throughput_ratio is required")
    _distribution(throughput, "equal_power_throughput_ratio")

    acceleration = scenario.get("amdahl_acceleration")
    if acceleration is not None:
        low, _, _ = _distribution(acceleration, "amdahl_acceleration")
        if low <= 0:
            raise ScenarioError("amdahl_acceleration must be greater than zero")

    physical = scenario.get("physical_path_evidence")
    if physical not in EVIDENCE_RANK:
        raise ScenarioError("physical_path_evidence is missing or invalid")

    consensus = scenario.get("consensus_suitability")
    if not isinstance(consensus, dict):
        raise ScenarioError("consensus_suitability must be an object")
    missing_checks = [key for key in CONSENSUS_CHECKS if key not in consensus]
    if missing_checks:
        raise ScenarioError("missing consensus checks: " + ", ".join(missing_checks))
    for key in CONSENSUS_CHECKS:
        if not isinstance(consensus[key], bool):
            raise ScenarioError(f"consensus_suitability.{key} must be boolean")


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a quantile of an empty list")
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "p05": _quantile(values, 0.05),
        "median": _quantile(values, 0.50),
        "p95": _quantile(values, 0.95),
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    delta_x = [value - mean_x for value in xs]
    delta_y = [value - mean_y for value in ys]
    denominator = math.sqrt(
        sum(value * value for value in delta_x)
        * sum(value * value for value in delta_y)
    )
    if denominator == 0:
        return 0.0
    return sum(x * y for x, y in zip(delta_x, delta_y)) / denominator


def _all_components(scenario: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for name, component in scenario["electronic_components"].items():
        yield f"electronic.{name}", component
    for name, component in scenario["photonic_components"].items():
        yield f"photonic.{name}", component


def evaluate(
    scenario: dict[str, Any], samples: int = 50_000, seed: int = 3
) -> dict[str, Any]:
    validate_scenario(scenario)
    if samples < 100:
        raise ScenarioError("samples must be at least 100")

    rng = random.Random(seed)
    advantages: list[float] = []
    headrooms: list[float] = []
    throughput_ratios: list[float] = []
    amdahl_bounds: list[float] = []
    electronic_totals: list[float] = []
    photonic_totals: list[float] = []
    component_samples: dict[str, list[float]] = {
        name: [] for name, _ in _all_components(scenario)
    }

    for _ in range(samples):
        electronic_total = 0.0
        accelerable_total = 0.0
        for name, component in scenario["electronic_components"].items():
            value = _sample(component["energy"], rng, f"electronic_components.{name}.energy")
            electronic_total += value
            if component["photonic_accelerable"]:
                accelerable_total += value
            component_samples[f"electronic.{name}"].append(value)

        photonic_total = 0.0
        for name, component in scenario["photonic_components"].items():
            value = _sample(component["energy"], rng, f"photonic_components.{name}.energy")
            photonic_total += value
            component_samples[f"photonic.{name}"].append(value)

        if electronic_total <= 0:
            raise ScenarioError("sampled electronic total must be greater than zero")
        if photonic_total <= 0:
            raise ScenarioError("sampled photonic total must be greater than zero")

        headroom = accelerable_total / electronic_total
        electronic_totals.append(electronic_total)
        photonic_totals.append(photonic_total)
        headrooms.append(headroom)
        advantages.append(electronic_total / photonic_total)
        throughput_ratios.append(
            _sample(scenario["equal_power_throughput_ratio"], rng, "equal_power_throughput_ratio")
        )
        if scenario.get("amdahl_acceleration") is not None:
            acceleration = _sample(
                scenario["amdahl_acceleration"], rng, "amdahl_acceleration"
            )
            amdahl_bounds.append(1.0 / ((1.0 - headroom) + headroom / acceleration))

    evidence_classes = [
        component["evidence"]["class"] for _, component in _all_components(scenario)
    ]
    placeholders = [
        name
        for name, component in _all_components(scenario)
        if component["evidence"]["class"] == "placeholder"
    ]
    source_count = len(
        {component["evidence"]["source"] for _, component in _all_components(scenario)}
    )

    advantage = _summary(advantages)
    headroom = _summary(headrooms)
    throughput = _summary(throughput_ratios)
    minimum_evidence_rank = min(EVIDENCE_RANK[item] for item in evidence_classes)
    gate1_survival = headroom["p05"] >= 0.80
    gate1_serious = headroom["p05"] >= 0.90
    gate2_evidence_eligible = not placeholders
    gate2_survival_numeric = advantage["p05"] >= 3.0 and throughput["p05"] >= 2.0
    gate2_credible_numeric = advantage["p05"] >= 5.0 and throughput["p05"] >= 2.0
    gate2_strong_numeric = advantage["p05"] >= 10.0 and throughput["p05"] >= 2.0
    physical_rank = EVIDENCE_RANK[scenario["physical_path_evidence"]]
    gate3_grounded = (
        minimum_evidence_rank >= EVIDENCE_RANK["literature_model"]
        and physical_rank >= EVIDENCE_RANK["representative_prototype"]
    )
    consensus = scenario["consensus_suitability"]
    gate4_suitable = all(consensus[key] for key in CONSENSUS_CHECKS)

    sensitivity = [
        {
            "component": name,
            "pearson_r_with_system_advantage": _pearson(values, advantages),
        }
        for name, values in component_samples.items()
    ]
    sensitivity.sort(
        key=lambda item: abs(item["pearson_r_with_system_advantage"]), reverse=True
    )

    result: dict[str, Any] = {
        "scenario": scenario["name"],
        "candidate_family": scenario.get("candidate_family", "unspecified"),
        "energy_unit": scenario["energy_unit"],
        "samples": samples,
        "seed": seed,
        "electronic_attempt_energy": _summary(electronic_totals),
        "photonic_attempt_energy": _summary(photonic_totals),
        "electronic_headroom": headroom,
        "complete_system_advantage": advantage,
        "equal_power_throughput_ratio": throughput,
        "threshold_probabilities": {
            "headroom_ge_0_80": sum(value >= 0.80 for value in headrooms) / samples,
            "headroom_ge_0_90": sum(value >= 0.90 for value in headrooms) / samples,
            "advantage_ge_3": sum(value >= 3.0 for value in advantages) / samples,
            "advantage_ge_5": sum(value >= 5.0 for value in advantages) / samples,
            "advantage_ge_10": sum(value >= 10.0 for value in advantages) / samples,
            "throughput_ge_2": sum(value >= 2.0 for value in throughput_ratios) / samples,
        },
        "evidence": {
            "minimum_component_class": min(
                evidence_classes, key=lambda item: EVIDENCE_RANK[item]
            ),
            "physical_path_class": scenario["physical_path_evidence"],
            "placeholder_components": placeholders,
            "distinct_sources": source_count,
        },
        "gates": {
            "gate1_electronic_headroom": {
                "survival_80_percent": gate1_survival,
                "serious_90_percent": gate1_serious,
            },
            "gate2_system_economics": {
                "evidence_eligible": gate2_evidence_eligible,
                "survival_3x_and_2x_throughput_numeric": gate2_survival_numeric,
                "credible_5x_and_2x_throughput_numeric": gate2_credible_numeric,
                "strong_10x_and_2x_throughput_numeric": gate2_strong_numeric,
                "survival_pass": gate2_evidence_eligible and gate2_survival_numeric,
                "credible_pass": gate2_evidence_eligible and gate2_credible_numeric,
                "strong_pass": gate2_evidence_eligible and gate2_strong_numeric,
            },
            "gate3_physical_grounding": gate3_grounded,
            "gate4_consensus_suitability": gate4_suitable,
        },
        "consensus_checks": {key: consensus[key] for key in CONSENSUS_CHECKS},
        "sensitivity": sensitivity,
        "component_energy": {
            name: _summary(values) for name, values in component_samples.items()
        },
        "photonic_energy_budgets": {
            "for_3x": _summary([value / 3.0 for value in electronic_totals]),
            "for_5x": _summary([value / 5.0 for value in electronic_totals]),
            "for_10x": _summary([value / 10.0 for value in electronic_totals]),
        },
        "disposition": "research_only",
    }
    if amdahl_bounds:
        result["optimistic_amdahl_upper_bound"] = _summary(amdahl_bounds)
    return result


def _format_percent(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def print_report(result: dict[str, Any]) -> None:
    headroom = result["electronic_headroom"]
    advantage = result["complete_system_advantage"]
    throughput = result["equal_power_throughput_ratio"]
    electronic_energy = result["electronic_attempt_energy"]
    photonic_energy = result["photonic_attempt_energy"]
    evidence = result["evidence"]
    gates = result["gates"]
    print(f"Scenario: {result['scenario']}")
    print(f"Family: {result['candidate_family']}")
    print(f"Monte Carlo: {result['samples']} samples, seed {result['seed']}")
    print(
        "Electronic headroom: "
        f"p05 {_format_percent(headroom['p05'])}, "
        f"median {_format_percent(headroom['median'])}, "
        f"p95 {_format_percent(headroom['p95'])}"
    )
    print(
        "Complete-system advantage: "
        f"p05 {advantage['p05']:.3f}x, median {advantage['median']:.3f}x, "
        f"p95 {advantage['p95']:.3f}x"
    )
    print(
        f"Attempt energy ({result['energy_unit']}): "
        f"electronic median {electronic_energy['median']:.6f}, "
        f"photonic median {photonic_energy['median']:.6f}"
    )
    print(
        "Equal-power throughput: "
        f"p05 {throughput['p05']:.3f}x, median {throughput['median']:.3f}x"
    )
    if "optimistic_amdahl_upper_bound" in result:
        amdahl = result["optimistic_amdahl_upper_bound"]
        print(
            "Optimistic Amdahl upper bound: "
            f"p05 {amdahl['p05']:.3f}x, median {amdahl['median']:.3f}x"
        )
    print(
        "Evidence: minimum component class "
        f"{evidence['minimum_component_class']}; physical path "
        f"{evidence['physical_path_class']}"
    )
    if evidence["placeholder_components"]:
        print("Admission blocked by placeholders:")
        for component in evidence["placeholder_components"]:
            print(f"  - {component}")
    print("Gate outcomes:")
    print(
        "  Gate 1: "
        f"80%={'PASS' if gates['gate1_electronic_headroom']['survival_80_percent'] else 'FAIL'}, "
        f"90%={'PASS' if gates['gate1_electronic_headroom']['serious_90_percent'] else 'FAIL'}"
    )
    gate2 = gates["gate2_system_economics"]
    print(
        "  Gate 2: "
        f"3x={'PASS' if gate2['survival_pass'] else 'FAIL'}, "
        f"5x={'PASS' if gate2['credible_pass'] else 'FAIL'}, "
        f"10x={'PASS' if gate2['strong_pass'] else 'FAIL'}"
    )
    print(f"  Gate 3: {'PASS' if gates['gate3_physical_grounding'] else 'FAIL'}")
    print(f"  Gate 4: {'PASS' if gates['gate4_consensus_suitability'] else 'FAIL'}")
    print("Disposition: research only; this output cannot select consensus parameters")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path, help="JSON scenario to evaluate")
    parser.add_argument("--samples", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        with args.scenario.open("r", encoding="utf-8") as handle:
            scenario = json.load(handle)
        result = evaluate(scenario, samples=args.samples, seed=args.seed)
    except (OSError, json.JSONDecodeError, ScenarioError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print_report(result)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with args.json_out.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
