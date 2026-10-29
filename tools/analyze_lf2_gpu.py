#!/usr/bin/env python3
"""Analyze paced paired GPU samples. Standard library; no GPU/benchmarks.

Reports device graph timings, not unpaced host throughput, energy, hardware
security or active-network evidence. Fused GEMM time includes its epilogue.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def parse(path):
    rows = []
    other = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("{"):
            rows.append(json.loads(line))
        elif line.strip():
            other.append(line)
    return rows, other


def summarize(paths):
    files, cases = [], []
    gpu_ms = 0.0
    root = Path(__file__).resolve().parents[1]
    frozen = dict(line.split("=",1) for line in
        (root / "docs/v0.4-shadow-vectors.txt").read_text().splitlines() if "=" in line)
    c20_fixture = json.loads((root / "research/launch/lf3-k8-c20-experiment-1-vector.json").read_text())
    anchors = []
    for path in paths:
        rows, other = parse(path)
        metadata = next((r for r in rows if r["type"] == "metadata"), None)
        complete = next((r for r in rows if r["type"] == "complete"), None)
        budgets = [r for r in rows if r["type"] == "budget"]
        counted_ms = max((r["cumulative_ms"] for r in budgets), default=0.0)
        gpu_ms += counted_ms
        validations = [r for r in rows if r["type"] == "validation"]
        banks = [r for r in rows if r["type"] == "bank"]
        if banks:
            assert all(row["complete_upload_readback_equal"] for row in banks)
            assert all(row["commitment"] == frozen[f"case[{metadata['parent']}].bank_commitment"] for row in banks)
        for r in validations:
            which = None
            if r["name"].startswith("lf2_"):
                if metadata["parent"] == 0 and r["header_bytes"] == 0 and r["first_nonce"] == "0":
                    which = 0
                elif metadata["parent"] == 1 and r["header_bytes"] == 1 and r["first_nonce"] == str(2**64-1):
                    which = 1
                if which is not None:
                    assert r["digest"] == frozen[f"case[{which}].digest"]
                    assert r["fold_shake256"] == frozen[f"case[{which}].fold_digest"]
                    anchors.append({"file":path.as_posix(),"name":r["name"],"frozenLf2Case":which})
            elif metadata["parent"] == 0 and r["header_bytes"] == 184 and r["first_nonce"] == str(2**64-1):
                assert r["digest"] == c20_fixture["digest"]
                assert r["fold_shake256"] == hashlib.shake_256(bytes.fromhex(c20_fixture["folded"])).hexdigest(32)
                anchors.append({"file":path.as_posix(),"name":r["name"],"generatedC20Fixture":True})
        file_info = {"file": path.as_posix(), "complete": bool(complete),
            "gpuEventWindowsMs": counted_ms, "metadata": metadata,
            "validationCount": len(validations), "otherOutput": other}
        files.append(file_info)
        if not complete:
            continue
        assert complete["passed"] is True
        assert validations and all(r["passed"] and r["all_gemm_outputs_checked"] for r in validations)
        expected_names = {
            f"{profile}_{vector}_{gemm}"
            for profile, vectors in (("lf2", ("register", "warp")),
                                     ("c20", ("two_stage", "fused")))
            for vector in vectors
            for gemm in ("cublas", "cublas_autotune", "cutlass128_i32",
                         "cutlass256_i32", "cutlass128_q4", "cutlass256_q4")
        }
        assert len(banks) == 1
        assert {r["name"] for r in validations} == expected_names
        repetitions = 2 if metadata["rounds"] else 1
        assert all(sum(r["name"] == name for r in validations) == repetitions
                   for name in expected_names)
        samples = [r for r in rows if r["type"] == "sample"]
        if not samples:
            continue
        names = sorted({r["name"] for r in samples})
        assert set(names) == expected_names
        expected_rounds = set(range(metadata["rounds"]))
        by_name = {}
        for name in names:
            group = [r for r in samples if r["name"] == name]
            assert {r["round"] for r in group} == expected_rounds
            assert len(group) == len(expected_rounds)
            for r in group:
                assert min(r[k] for k in ("vector_ms","gemm_with_epilogue_ms","fold_ms","final_hash_ms","total_ms")) > 0
                assert abs(sum(r[k] for k in ("vector_ms","gemm_with_epilogue_ms","fold_ms","final_hash_ms")) - r["total_ms"]) < 0.002
            med = {k: statistics.median(r[k] for r in group) for k in (
                "vector_ms","gemm_with_epilogue_ms","fold_ms","final_hash_ms","total_ms")}
            by_name[name] = {"rounds": len(group), "medianMs": med,
                "medianDeviceUsPerAttempt": 1000 * med["total_ms"] / metadata["batch"],
                "medianDeviceAttemptsPerSecond": 1000 * metadata["batch"] / med["total_ms"],
                "medianAbsoluteDeviationTotalMs": statistics.median(abs(r["total_ms"]-med["total_ms"]) for r in group),
                "minTotalMs": min(r["total_ms"] for r in group),
                "maxTotalMs": max(r["total_ms"] for r in group),
                "medianCompositeGemmStagePercent": statistics.median(100*r["gemm_with_epilogue_ms"]/r["total_ms"] for r in group),
                "includesPackingInGemmStage": group[0]["packed"]}
        # Selection is explicitly among tested configurations, not a proof of
        # globally optimal kernels. Same options are granted to both profiles.
        lf2_exact = [n for n in names if n.startswith("lf2_") and not n.endswith("_q4")]
        lf2_packed = [n for n in names if n.startswith("lf2_") and n.endswith("_q4")]
        c20 = [n for n in names if n.startswith("c20_")]
        fastest = lambda options: min(options,key=lambda n: by_name[n]["medianMs"]["total_ms"])
        baseline, packed, successor = fastest(lf2_exact), fastest(lf2_packed), fastest(c20)
        comparisons = []
        for base_name, candidate in ((baseline, packed), (baseline, successor),
                                     (packed, successor)):
            paired = []
            for round in sorted(expected_rounds):
                a = next(r for r in samples if r["name"] == base_name and r["round"] == round)
                b = next(r for r in samples if r["name"] == candidate and r["round"] == round)
                assert a["first_nonce"] == b["first_nonce"]
                paired.append(a["total_ms"] / b["total_ms"])
            comparisons.append({"candidate": candidate, "baseline": base_name,
                "medianPairedDeviceSpeedup": statistics.median(paired),
                "pairedSpeedups": paired,
                "candidateFasterRounds": sum(r > 1 for r in paired),
                "roundCount": len(paired),
                "selectionAndComparisonUseSameSamples": True})
        # Matched controls isolate practical epilogue changes without calling
        # the entire composite kernel time pure matrix arithmetic.
        controls = []
        for name in names:
            if not name.endswith("_q4"):
                continue
            control = name[:-3] + "_i32"
            if control not in by_name:
                continue
            controls.append({"packed": name, "control": control,
                "medianTotalSpeedup": by_name[control]["medianMs"]["total_ms"] / by_name[name]["medianMs"]["total_ms"],
                "medianGemmEpilogueTimeRatio": by_name[name]["medianMs"]["gemm_with_epilogue_ms"] / by_name[control]["medianMs"]["gemm_with_epilogue_ms"]})
        cases.append({"metadata": metadata, "variants": by_name,
            "fastestTestedLf2Int32Baseline": baseline,
            "fastestTestedLf2Packed": packed, "fastestTestedC20": successor,
            "comparisons": comparisons, "matchedEpilogueControls": controls})
    return {"files": files, "cases": cases, "summedGpuEventWindowsMs": gpu_ms,
        "fixtureAnchors": anchors,
        "limits": ["Shared desktop GPU, paced short bursts, ambient clocks; no exclusive stable laboratory conditions",
            "Device graph throughput only; setup, transfer, host launch, validation and pacing are separate",
            "Composite GEMM stage includes epilogue and output stores, not matrix-only energy or time",
            "Best choices selected from same limited samples; small differences require independent confirmation",
            "No optical, energy, full multistream-miner or consensus-security qualification"]}


def main():
    if not __debug__:
        raise RuntimeError("Evidence checks require Python without -O")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = summarize(args.logs)
    args.output.write_bytes((json.dumps(report,indent=2)+"\n").encode("utf-8"))
    print(json.dumps({"passed": True,"cases": len(report["cases"]),
        "summedGpuEventWindowsMs": report["summedGpuEventWindowsMs"],"output": str(args.output)}))


if __name__ == "__main__":
    main()
