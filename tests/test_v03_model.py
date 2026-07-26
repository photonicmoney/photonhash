import copy
import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ph_v03_model", ROOT / "tools" / "ph_v03_model.py"
)
MODEL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODEL)


def evidence(evidence_class="placeholder"):
    return {
        "class": evidence_class,
        "source": "test fixture",
        "basis": "Synthetic unit-test value.",
    }


def component(energy, evidence_class="placeholder"):
    return {"energy": energy, "evidence": evidence(evidence_class)}


def scenario(evidence_class="placeholder"):
    photonic = {
        name: component(0.1, evidence_class) for name in MODEL.PHOTONIC_COMPONENTS
    }
    return {
        "schema_version": 1,
        "name": "unit test scenario",
        "candidate_family": "test",
        "energy_unit": "normalized",
        "electronic_components": {
            "matrix": {
                "energy": 90.0,
                "photonic_accelerable": True,
                "evidence": evidence(evidence_class),
            },
            "fixed": {
                "energy": 10.0,
                "photonic_accelerable": False,
                "evidence": evidence(evidence_class),
            },
        },
        "photonic_components": photonic,
        "amdahl_acceleration": 20.0,
        "equal_power_throughput_ratio": 3.0,
        "physical_path_evidence": evidence_class,
        "consensus_suitability": {
            key: True for key in MODEL.CONSENSUS_CHECKS
        },
    }


class ModelTests(unittest.TestCase):
    def test_placeholder_can_win_numeric_screen_but_not_gate(self):
        result = MODEL.evaluate(scenario(), samples=200, seed=7)
        gate2 = result["gates"]["gate2_system_economics"]
        self.assertTrue(gate2["strong_10x_and_2x_throughput_numeric"])
        self.assertFalse(gate2["evidence_eligible"])
        self.assertFalse(gate2["strong_pass"])
        self.assertEqual(result["disposition"], "research_only")

    def test_component_grounded_fixture_passes_numeric_and_evidence_gates(self):
        fixture = scenario("representative_prototype")
        result = MODEL.evaluate(fixture, samples=200, seed=7)
        self.assertTrue(
            result["gates"]["gate1_electronic_headroom"]["serious_90_percent"]
        )
        self.assertTrue(result["gates"]["gate2_system_economics"]["strong_pass"])
        self.assertTrue(result["gates"]["gate3_physical_grounding"])
        self.assertTrue(result["gates"]["gate4_consensus_suitability"])

    def test_missing_photonic_component_is_rejected(self):
        fixture = scenario()
        del fixture["photonic_components"]["conversion"]
        with self.assertRaisesRegex(MODEL.ScenarioError, "missing photonic"):
            MODEL.validate_scenario(fixture)

    def test_bad_distribution_is_rejected(self):
        fixture = scenario()
        fixture["electronic_components"]["matrix"]["energy"] = {
            "low": 5,
            "mode": 4,
            "high": 6,
        }
        with self.assertRaisesRegex(MODEL.ScenarioError, "must satisfy"):
            MODEL.validate_scenario(fixture)

    def test_seed_is_deterministic(self):
        fixture = scenario()
        fixture["photonic_components"]["conversion"]["energy"] = {
            "low": 0.1,
            "mode": 0.3,
            "high": 1.0,
        }
        first = MODEL.evaluate(fixture, samples=500, seed=19)
        second = MODEL.evaluate(fixture, samples=500, seed=19)
        self.assertEqual(
            first["complete_system_advantage"],
            second["complete_system_advantage"],
        )
        self.assertEqual(first["sensitivity"], second["sensitivity"])

    def test_v02_calibration_matches_amdahl_equation(self):
        path = (
            ROOT
            / "research"
            / "v0.3"
            / "scenarios"
            / "v02-optimistic-calibration.json"
        )
        with path.open(encoding="utf-8") as handle:
            fixture = json.load(handle)
        result = MODEL.evaluate(fixture, samples=200, seed=3)
        p = 0.1212138792
        expected = 1.0 / ((1.0 - p) + p / 20.0)
        self.assertTrue(
            math.isclose(
                result["complete_system_advantage"]["median"],
                expected,
                rel_tol=1e-10,
            )
        )
        self.assertTrue(
            math.isclose(
                result["optimistic_amdahl_upper_bound"]["median"],
                expected,
                rel_tol=1e-10,
            )
        )
        self.assertFalse(
            result["gates"]["gate1_electronic_headroom"]["survival_80_percent"]
        )

    def test_consensus_check_must_be_boolean(self):
        fixture = copy.deepcopy(scenario())
        fixture["consensus_suitability"]["frozen_vectors"] = "later"
        with self.assertRaisesRegex(MODEL.ScenarioError, "must be boolean"):
            MODEL.validate_scenario(fixture)


if __name__ == "__main__":
    unittest.main()
