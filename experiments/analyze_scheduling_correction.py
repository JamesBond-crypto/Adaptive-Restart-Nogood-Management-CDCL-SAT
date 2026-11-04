#!/usr/bin/env python3
"""
analyze_scheduling_correction.py - Comprehensive Analysis of Reduction Scheduling Correction
Analyzes 6-configuration ablation on 36 expanded SAT benchmarks.
"""

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

CFG_FILES = {
    "cfg1": ("Base_Base", Path("experiments/results/scheduling_correction_ablation/cfg1_base_base.csv")),
    "cfg2": ("V1_Base", Path("experiments/results/scheduling_correction_ablation/cfg2_v1_base.csv")),
    "cfg3": ("Base_AdaptHist", Path("experiments/results/scheduling_correction_ablation/cfg3_base_adapt.csv")),
    "cfg4": ("Base_AdaptFixed", Path("experiments/results/scheduling_correction_ablation/cfg4_base_adapt_fixed.csv")),
    "cfg5": ("V1_AdaptHist", Path("experiments/results/scheduling_correction_ablation/cfg5_v1_adapt.csv")),
    "cfg6": ("V1_AdaptFixed", Path("experiments/results/scheduling_correction_ablation/cfg6_v1_adapt_fixed.csv")),
}

MANIFEST_FILE = Path("benchmarks/expanded_manifest.csv")
TIMEOUT_LIMIT = 15.0
PAR2_PENALTY = 2.0 * TIMEOUT_LIMIT  # 30.0s


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_family(bname: str) -> str:
    if bname.startswith("rand3sat"):
        return "Random 3-SAT"
    elif bname.startswith("planted3sat"):
        return "Planted 3-SAT"
    elif bname.startswith("php"):
        return "Pigeonhole Principle"
    elif bname.startswith("gcol"):
        return "Graph Coloring"
    return "Other"


def compute_median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    else:
        return (s[mid - 1] + s[mid]) / 2.0


def to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def to_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def main():
    manifest = {r["filename"]: r for r in load_csv(MANIFEST_FILE)}
    cfg_data = {cfg_id: {r["benchmark_name"]: r for r in load_csv(path)} for cfg_id, (_, path) in CFG_FILES.items()}
    all_benchmarks = list(manifest.keys())

    print("=" * 80)
    print("SCHEDULING CORRECTION ABLATION: COMPREHENSIVE EXPERIMENTAL ANALYSIS")
    print("=" * 80)

    # 1. Correctness Audit
    print("\n--- 1. CORRECTNESS AND GROUND-TRUTH AUDIT ---")
    correctness_errors = []
    for cfg_id, (cfg_name, _) in CFG_FILES.items():
        data = cfg_data[cfg_id]
        for bname in all_benchmarks:
            r = data[bname]
            st = r["status"]
            known = manifest[bname]["known_status"]
            v_model = r.get("model_verified", "")

            if st == "SAT":
                if known == "UNSAT":
                    correctness_errors.append(f"[{cfg_id}] {bname}: Reported SAT on known UNSAT!")
                if v_model not in ("VERIFIED", "True", True):
                    correctness_errors.append(f"[{cfg_id}] {bname}: SAT model verification failed ({v_model})!")
            elif st == "UNSAT":
                if known == "SAT":
                    correctness_errors.append(f"[{cfg_id}] {bname}: Reported UNSAT on known SAT!")
            elif st not in ("TIMEOUT", "ERROR"):
                correctness_errors.append(f"[{cfg_id}] {bname}: Unknown status string '{st}'")

    if correctness_errors:
        print("[!] CRITICAL CORRECTNESS ERRORS:")
        for err in correctness_errors:
            print("   ", err)
        return
    else:
        print(f"[+] 100% Correctness: Zero contradictions across all {len(CFG_FILES) * len(all_benchmarks)} runs.")
        print("[+] 100% SAT Model Verification: All reported models independently verified.")

    # 2. Overall Summary Table
    print("\n--- 2. OVERALL BENCHMARK PERFORMANCE (N = 36) ---")
    print(f"{'Configuration':<18} | {'Solved':<7} | {'SAT':<5} | {'UNSAT':<5} | {'Timeout':<7} | {'PAR-2 (s)':<9} | {'Mean Time':<9} | {'Med Time':<8} | {'Mean Cfc':<9} | {'Total Red':<9} | {'Mean Mem':<8}")
    print("-" * 125)

    cfg_stats = {}
    for cfg_id, (cfg_name, _) in CFG_FILES.items():
        data = cfg_data[cfg_id]
        solved = [r for r in data.values() if r["status"] in ("SAT", "UNSAT")]
        sat_cnt = sum(1 for r in data.values() if r["status"] == "SAT")
        unsat_cnt = sum(1 for r in data.values() if r["status"] == "UNSAT")
        to_cnt = sum(1 for r in data.values() if r["status"] == "TIMEOUT")

        times = [to_float(r["wall_time_s"]) for r in data.values()]
        par2_times = [to_float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for r in data.values()]
        par2 = sum(par2_times) / len(par2_times)

        cfcs = [to_int(r["conflicts"]) for r in solved]
        mean_cfc = sum(cfcs) / len(cfcs) if cfcs else 0.0
        total_cfc = sum(cfcs)

        reductions = [to_int(r["reduce_db_count"]) for r in data.values()]
        total_red = sum(reductions)

        mems = [to_float(r["memory_mb"]) for r in data.values() if r.get("memory_mb")]
        mean_mem = sum(mems) / len(mems) if mems else 0.0

        post_evals = sum(to_int(r.get("adapt_postpone_evals", 0)) for r in data.values())
        post_sats = sum(to_int(r.get("adapt_postpone_sat", 0)) for r in data.values())

        cfg_stats[cfg_id] = {
            "name": cfg_name,
            "solved": len(solved),
            "sat": sat_cnt,
            "unsat": unsat_cnt,
            "timeout": to_cnt,
            "par2": par2,
            "mean_time": sum(times) / len(times),
            "med_time": compute_median(times),
            "mean_cfc": mean_cfc,
            "total_cfc": total_cfc,
            "total_red": total_red,
            "mean_mem": mean_mem,
            "post_evals": post_evals,
            "post_sats": post_sats
        }

        print(f"{cfg_name:<18} | {len(solved):<7} | {sat_cnt:<5} | {unsat_cnt:<5} | {to_cnt:<7} | {par2:<9.3f} | {sum(times)/len(times):<9.3f} | {compute_median(times):<8.3f} | {mean_cfc:<9.0f} | {total_red:<9} | {mean_mem:<8.2f}")

    # 3. Postponement Telemetry Summary
    print("\n--- 3. REDUCTION POSTPONEMENT TELEMETRY ---")
    print(f"{'Configuration':<18} | {'Total Reductions':<16} | {'Postpone Evals':<14} | {'Postpone Satisfied':<18} | {'Postpone Ratio':<14}")
    print("-" * 86)
    for cfg_id, (cfg_name, _) in CFG_FILES.items():
        st = cfg_stats[cfg_id]
        p_eval = st["post_evals"]
        p_sat = st["post_sats"]
        ratio_str = f"{p_sat / p_eval:.2%}" if p_eval > 0 else "N/A"
        print(f"{cfg_name:<18} | {st['total_red']:<16} | {p_eval:<14} | {p_sat:<18} | {ratio_str:<14}")

    # 4. Diagnostic Instances Analysis
    focus_instances = [
        "rand3sat_n250_c1065_s1010.cnf",
        "rand3sat_n235_c999_s1009.cnf",
        "php_10p_9h.cnf",
        "gcol_unsat_k10_c9.cnf"
    ]

    print("\n--- 4. TARGETED REGRESSION / DIAGNOSTIC INSTANCES ---")
    for inst in focus_instances:
        print(f"\nBenchmark: {inst} (Known: {manifest[inst]['known_status']})")
        print(f"  {'Configuration':<18} | {'Status':<7} | {'WallTime (s)':<12} | {'Conflicts':<10} | {'Reductions':<10} | {'Removed Clauses':<15} | {'Peak Mem (MB)':<13} | {'Postponed':<10}")
        print("  " + "-" * 105)
        for cfg_id, (cfg_name, _) in CFG_FILES.items():
            r = cfg_data[cfg_id][inst]
            st = r["status"]
            wt = to_float(r["wall_time_s"])
            cfc = r["conflicts"] if r["conflicts"] != "" else "N/A"
            red = r["reduce_db_count"] if r["reduce_db_count"] != "" else "N/A"
            rem = r["removed_clauses"] if r["removed_clauses"] != "" else "N/A"
            mem = to_float(r.get("memory_mb", 0))
            mem_str = f"{mem:.2f}" if mem > 0 else "N/A"
            p_sat = r.get("adapt_postpone_sat", "")
            p_eval = r.get("adapt_postpone_evals", "")
            post_str = f"{p_sat}/{p_eval}" if p_eval != "" else "N/A"
            print(f"  {cfg_name:<18} | {st:<7} | {wt:<12.3f} | {str(cfc):<10} | {str(red):<10} | {str(rem):<15} | {mem_str:<13} | {post_str:<10}")

    # 5. Direct Controlled Pairwise Comparisons
    pairs = [
        ("cfg3", "cfg4", "Effect of Correction under Baseline Restart (Base_AdaptHist vs Base_AdaptFixed)"),
        ("cfg5", "cfg6", "Effect of Correction under Adaptive V1 Restart (V1_AdaptHist vs V1_AdaptFixed)"),
        ("cfg1", "cfg4", "Baseline vs Corrected Adaptive Retention (Base_Base vs Base_AdaptFixed)"),
        ("cfg2", "cfg6", "Adaptive Restart vs Combined Corrected (V1_Base vs V1_AdaptFixed)")
    ]

    print("\n--- 5. DIRECT CONTROLLED PAIRWISE COMPARISONS ---")
    for c1_id, c2_id, desc in pairs:
        c1_name = CFG_FILES[c1_id][0]
        c2_name = CFG_FILES[c2_id][0]
        c1_data = cfg_data[c1_id]
        c2_data = cfg_data[c2_id]

        print(f"\nComparison: {desc}")
        # Mutually solved
        mutual = [b for b in all_benchmarks if c1_data[b]["status"] in ("SAT", "UNSAT") and c2_data[b]["status"] in ("SAT", "UNSAT")]
        print(f"  Mutually Solved Instances: {len(mutual)} / {len(all_benchmarks)}")

        if mutual:
            cfc1 = sum(to_int(c1_data[b]["conflicts"]) for b in mutual)
            cfc2 = sum(to_int(c2_data[b]["conflicts"]) for b in mutual)
            cfc_ratio = cfc2 / cfc1 if cfc1 > 0 else 1.0

            time1 = sum(to_float(c1_data[b]["wall_time_s"]) for b in mutual)
            time2 = sum(to_float(c2_data[b]["wall_time_s"]) for b in mutual)
            time_ratio = time2 / time1 if time1 > 0 else 1.0

            red1 = sum(to_int(c1_data[b]["reduce_db_count"]) for b in mutual)
            red2 = sum(to_int(c2_data[b]["reduce_db_count"]) for b in mutual)

            print(f"  Mutual Conflicts:  {c1_name}={cfc1:,} vs {c2_name}={cfc2:,} (Ratio {c2_name}/{c1_name} = {cfc_ratio:.4f}, change = {(cfc_ratio-1)*100:+.2f}%)")
            print(f"  Mutual Wall Time:  {c1_name}={time1:.2f}s vs {c2_name}={time2:.2f}s (Ratio {c2_name}/{c1_name} = {time_ratio:.4f}, change = {(time_ratio-1)*100:+.2f}%)")
            print(f"  Mutual Reductions: {c1_name}={red1:,} vs {c2_name}={red2:,}")

        # Solved differential
        s1 = set(b for b in all_benchmarks if c1_data[b]["status"] in ("SAT", "UNSAT"))
        s2 = set(b for b in all_benchmarks if c2_data[b]["status"] in ("SAT", "UNSAT"))
        only_c1 = s1 - s2
        only_c2 = s2 - s1
        print(f"  Solved only by {c1_name}: {sorted(list(only_c1)) if only_c1 else 'None'}")
        print(f"  Solved only by {c2_name}: {sorted(list(only_c2)) if only_c2 else 'None'}")

    # 6. Family Breakdown Table
    print("\n--- 6. BENCHMARK FAMILY BREAKDOWN (PAR-2 in seconds) ---")
    families = ["Random 3-SAT", "Planted 3-SAT", "Pigeonhole Principle", "Graph Coloring"]
    fam_benchmarks = defaultdict(list)
    for b in all_benchmarks:
        fam_benchmarks[get_family(b)].append(b)

    hdr = f"{'Family':<22} | " + " | ".join(f"{CFG_FILES[cid][0]:<14}" for cid in CFG_FILES)
    print(hdr)
    print("-" * len(hdr))

    for fam in families:
        b_list = fam_benchmarks[fam]
        row_vals = []
        for cid in CFG_FILES:
            data = cfg_data[cid]
            p2_list = [to_float(data[b]["wall_time_s"]) if data[b]["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for b in b_list]
            fam_p2 = sum(p2_list) / len(p2_list) if p2_list else 0.0
            row_vals.append(f"{fam_p2:<14.3f}")
        print(f"{fam + f' (N={len(b_list)})':<22} | " + " | ".join(row_vals))


if __name__ == "__main__":
    main()

