import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ph_v03_boundary_sim", ROOT / "tools" / "ph_v03_boundary_sim.py"
)
SIM = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SIM)


def profile():
    return {
        "id": "fixture",
        "architecture": "test",
        "n": 16,
        "rounds": 2,
        "boundary_count": 2,
        "residue_steps": 256,
        "electronic_energy_uJ": 100.0,
        "electronic_latency_us": 1.0,
        "matrix_energy_uJ": 10.0,
        "matrix_latency_us": 0.1,
        "matrix_lane_multiplier": 1.0,
        "boundary_energy_fJ_per_lane_decision": 100.0,
        "boundary_latency_ps": 10.0,
        "fixed_energy_uJ": 10.0,
        "fixed_latency_us": 0.1,
        "assist_energy_pJ_per_lane": 1.0,
        "guard_band_buckets": 0.0,
        "assist_success_probability": 1.0,
        "redundancy": 1,
        "noise": {
            "independent_sigma_buckets": 0.0,
            "common_sigma_buckets": 0.0,
            "drift_sigma_per_boundary_buckets": 0.0,
            "temperature_sigma_buckets": 0.0,
            "component_offset_sigma_buckets": 0.0,
            "decision_threshold_bias_buckets": -0.001,
            "residual_lane_error_floor": 0.0,
        },
        "calibration_failure_probability_per_boundary": 0.0,
        "evidence": [{"source": "synthetic test"}],
        "evidence_blockers": [],
    }


class BoundarySimulatorTests(unittest.TestCase):
    def test_zero_noise_with_tie_bias_is_exact(self):
        result = SIM.evaluate_profile(profile(), samples=50, seed=1)
        self.assertEqual(result["exact_output_yield"]["median"], 1.0)
        self.assertTrue(math.isclose(
            result["joules_per_valid_exact_attempt_uJ"]["median"],
            result["nominal_energy_uJ"]["median"],
        ))

    def test_unbiased_noisy_threshold_collapses_whole_state_yield(self):
        fixture = profile()
        fixture["n"] = 1024
        fixture["noise"]["decision_threshold_bias_buckets"] = 0.0
        fixture["noise"]["independent_sigma_buckets"] = 0.0001
        result = SIM.evaluate_profile(fixture, samples=50, seed=2)
        self.assertLess(result["exact_output_yield"]["median"], 0.1)
        self.assertGreater(
            result["joules_per_valid_exact_attempt_uJ"]["median"],
            result["nominal_energy_uJ"]["median"],
        )

    def test_selective_assistance_restores_exactness_when_it_catches_edges(self):
        fixture = profile()
        fixture["n"] = 1024
        fixture["noise"]["independent_sigma_buckets"] = 0.0005
        fixture["guard_band_buckets"] = 0.01
        result = SIM.evaluate_profile(fixture, samples=50, seed=3)
        self.assertGreater(result["exact_output_yield"]["median"], 0.999)
        self.assertGreater(
            result["assist_fraction_of_lane_decisions"]["median"], 0.0
        )

    def test_failed_assistance_is_charged_through_yield(self):
        fixture = profile()
        fixture["n"] = 1024
        fixture["guard_band_buckets"] = 0.01
        fixture["assist_success_probability"] = 0.99
        result = SIM.evaluate_profile(fixture, samples=50, seed=4)
        self.assertLess(result["exact_output_yield"]["median"], 1.0)
        self.assertGreater(
            result["joules_per_valid_exact_attempt_uJ"]["median"],
            result["nominal_energy_uJ"]["median"],
        )

    def test_even_redundancy_is_rejected(self):
        fixture = profile()
        fixture["redundancy"] = 2
        with self.assertRaisesRegex(SIM.ScenarioError, "must be odd"):
            SIM.validate_profile(fixture)

    def test_suite_seed_is_deterministic(self):
        fixture = profile()
        fixture["noise"]["common_sigma_buckets"] = {
            "low": 0.0, "mode": 0.001, "high": 0.002
        }
        suite = {"schema_version": 1, "profiles": [fixture]}
        first = SIM.evaluate_suite(suite, samples=100, seed=9)
        second = SIM.evaluate_suite(suite, samples=100, seed=9)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
