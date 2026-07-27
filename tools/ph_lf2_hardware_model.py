#!/usr/bin/env python3
"""Transparent LF2-K8 electronic-hardware bounds.

This is a roofline and sensitivity model, not an FPGA/ASIC benchmark. Vendor
peak numbers are kept separate from PhotonHash measurements and every
conversion from operations to MACs is explicit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

N = 4096
PASSES = 8
MACS = N * N * PASSES
PACKED_BANK_BYTES = MACS // 2
UNPACKED_BANK_BYTES = MACS
BLOCK_INTERVAL_S = 10.0


def attempts_per_second(tmac_s: float) -> float:
    return tmac_s * 1e12 / MACS


def bank_stream_limit(gb_s: float, reuse: int) -> float:
    return gb_s * 1e9 * reuse / PACKED_BANK_BYTES


def asic_matrix_energy_uj(pj_per_mac: float) -> float:
    return MACS * pj_per_mac / 1e6


def build_model() -> dict:
    gpu_attempts_s = 1_801_994.897
    gpu_energy_interval_uj = [253.602270, 306.523561]
    gpu_logical_tmac_s = gpu_attempts_s * MACS / 1e12
    fpga_cases = []
    for name, tops, bandwidth in (
        ("Altera Agilex 7 M vendor peak", 88.6, 1000.0),
        ("AMD Versal HBM bandwidth envelope", None, 819.0),
    ):
        case = {
            "name": name,
            "evidence_class": "vendor_peak_not_lf2_measurement",
            "hbm_gb_s": bandwidth,
            "no_weight_reuse_attempts_s": bank_stream_limit(bandwidth, 1),
            "weight_reuse_attempts_s": {
                str(reuse): bank_stream_limit(bandwidth, reuse)
                for reuse in (8, 64, 512, 8192)
            },
        }
        if tops is not None:
            case["published_int8_tops"] = tops
            case["compute_ceiling_attempts_s"] = {
                "if_one_mac_is_two_vendor_ops": attempts_per_second(tops / 2),
                "if_one_mac_is_one_vendor_op": attempts_per_second(tops),
            }
        fpga_cases.append(case)

    asic_sensitivity = []
    for pj in (0.01, 0.03, 0.1, 0.3, 1.0):
        matrix_uj = asic_matrix_energy_uj(pj)
        asic_sensitivity.append({
            "assumed_pj_per_exact_int8_mac": pj,
            "matrix_only_uj_per_attempt": matrix_uj,
            "fraction_of_measured_rtx5090_board_energy_interval": [
                matrix_uj / gpu_energy_interval_uj[1],
                matrix_uj / gpu_energy_interval_uj[0],
            ],
            "warning": "assumption sweep only; excludes SRAM/HBM, SHAKE, fold, control, I/O, cooling, and yield",
        })

    setup = {
        "rust_matrix_derivation_ms": 227.0,
        "portable_c_matrix_derivation_ms": 497.0,
        "cpu_bitslice_pack_ms": 1276.0,
    }
    for key, value in list(setup.items()):
        setup[key.replace("_ms", "_fraction_of_10s_tip_lifetime")] = (
            value / 1000.0 / BLOCK_INTERVAL_S
        )

    return {
        "status": "roofline_and_sensitivity_model_not_hardware_benchmark",
        "profile": {
            "candidate": "LF2-K8", "n": N, "passes": PASSES,
            "exact_macs_per_attempt": MACS,
            "packed_matrix_bank_mib": PACKED_BANK_BYTES / 2**20,
            "unpacked_matrix_bank_mib": UNPACKED_BANK_BYTES / 2**20,
            "assumed_parent_lifetime_s": BLOCK_INTERVAL_S,
        },
        "measured_reference": {
            "hardware": "RTX 5090",
            "serialized_attempts_s": gpu_attempts_s,
            "logical_exact_tmac_s_end_to_end": gpu_logical_tmac_s,
            "board_energy_uj_per_attempt_interval": gpu_energy_interval_uj,
            "scope": "measured LF2 pipeline; logical MAC rate is not a vendor peak",
        },
        "fpga_rooflines": fpga_cases,
        "asic_energy_sensitivity": asic_sensitivity,
        "matrix_lifetime": setup,
        "interpretation": [
            "A 64 MiB packed bank must be streamed, cached in HBM, or tiled into on-chip memory.",
            "Without weight reuse, HBM bandwidth caps attempts far below the RTX 5090 result.",
            "With batched vector reuse, compute and routing become the likely FPGA limits.",
            "Vendor INT8 TOPS do not prove exact LF2 accumulation and epilogue sustain that peak.",
            "A purpose-built electronic ASIC could plausibly undercut GPU energy; post-layout evidence is required.",
            "Security does not rely on ASIC resistance, but accessibility and photonic comparisons must include ASICs.",
        ],
        "sources": [
            {"claim": "Agilex 7 M advertises up to 88.6 INT8 TOPS and 1 TB/s HBM bandwidth",
             "url": "https://www.intel.com/content/www/us/en/products/details/fpga/agilex/7/m-series.html"},
            {"claim": "Versal HBM advertises up to 819 GB/s and 32 GB HBM2e",
             "url": "https://www.amd.com/en/products/adaptive-socs-and-fpgas/versal/hbm-series.html"},
            {"claim": "Versal DSP INT8 mode provides a three-element dot-product unit",
             "url": "https://docs.amd.com/r/en-US/am004-versal-dsp-engine/Dot-Product-Unit"},
        ],
        "reproducibility": {
            "command": "python tools/ph_lf2_hardware_model.py --output research/launch/lf2-k8-hardware-model-20260726.json"
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(build_model(), indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
