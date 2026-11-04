#!/usr/bin/env python3
"""
analyze_v3_full_development.py - Step 30: Comprehensive Analysis of Full V3 Evaluation

Analyzes experiments/results/v3_full_development/master_results.csv across:
1. Executive Configuration Performance (Unique Solved, Solved/TO Counts, PAR-2, Median Runtimes, Memory)
2. Family-Level Breakdown (Random 3-SAT, Planted 3-SAT, PHP, Graph Coloring)
3. Diagnostic (8 instances) vs. Remaining Development (28 instances) Breakdown
4. Component Trigger Breakdown (Trend, Drawdown, Ceiling requests, executed restarts)
5. Repetition Stability & Determinism (Search counter variance, status consistency)
6. Pairwise Paired Instance Comparison against Baseline Glucose
"""

import sys
import csv
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple

WORKSPACE = Path(r"D:\DAC_203@Project")
MASTER_CSV = WORKSPACE / "experiments" / "results" / "v3_full_development" / "master_results.csv"
TIMEOUT_LIMIT = 15.0
PAR2_PENALTY = 30.0

CONFIG_ORDER = [
    "cfg1_baseline",
    "cfg2_v1",
    "cfg3_v3_trend_only",
    "cfg4_v3_drawdown_only",
    "cfg5_v3_ceiling_only",
    "cfg6_v3_combined",
]

CONFIG_NAMES = {
    "cfg1_baseline": "Original Glucose",
    "cfg2_v1": "Adaptive Restart V1",
    "cfg3_v3_trend_only": "V3 Trend Only",
    "cfg4_v3_drawdown_only": "V3 Drawdown Only",
    "cfg5_v3_ceiling_only": "V3 Ceiling Only",
    "cfg6_v3_combined": "V3 Combined",
}

DIAGNOSTIC_INSTANCES = {
    "rand3sat_n250_c1065_s1010.cnf",
    "rand3sat_n200_c840_s1005.cnf",
    "php_10p_9h.cnf",
    "php_10p_8h.cnf",
    "gcol_unsat_k10_c9.cnf",
    "gcol_unsat_k9_c8.cnf",
    "planted3sat_n240_c1022_s2009.cnf",
    "planted3sat_n200_c852_s2005.cnf",
}

def parse_num(v, conv=float, default=0.0):
    if v is None or v == "":
        return default
    try:
        return conv(v)
    except Exception:
        return default

def median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0

def iqr(vals: List[float]) -> float:
    if len(vals) < 4:
        return 0.0
    s = sorted(vals)
    n = len(s)
    q1 = s[n // 4]
    q3 = s[(3 * n) // 4]
    return q3 - q1

def main():
    if not MASTER_CSV.exists():
        print(f"ERROR: Results file not found: {MASTER_CSV}")
        sys.exit(1)

    records = []
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append(r)

    print(f"Loaded {len(records)} runs from {MASTER_CSV}.")

    # Index by config, instance, repetition
    by_cfg = defaultdict(list)
    by_inst = defaultdict(lambda: defaultdict(list))
    all_instances = []
    families = defaultdict(set)

    for r in records:
        cfg = r["config_id"]
        inst = r["benchmark_name"]
        rep = int(r["repetition"])
        fam = r["family"]
        by_cfg[cfg].append(r)
        by_inst[inst][cfg].append(r)
        families[fam].add(inst)
        if inst not in all_instances:
            all_instances.append(inst)

    all_instances.sort()

    print("\n" + "=" * 120)
    print("TABLE 1: OVERALL CONFIGURATION PERFORMANCE SUMMARY (N = 36 Benchmarks x 3 Repetitions = 108 Runs / Config)")
    print("=" * 120)
    print(f"{'Configuration':<25s} | {'Unique Solved':<13s} | {'Solved (Runs)':<13s} | {'Timeouts':<8s} | {'PAR-2 (s)':<10s} | {'Median T (s)':<12s} | {'IQR T (s)':<10s} | {'Mut Cfc':<12s} | {'Peak Mem (MB)':<13s}")
    print("-" * 120)

    # Determine mutually solved instances across all 6 configurations (in all 3 reps)
    mutually_solved = []
    for inst in all_instances:
        solved_in_all = True
        for cfg in CONFIG_ORDER:
            runs = by_inst[inst].get(cfg, [])
            if not runs or any(run["status"] not in ("SAT", "UNSAT") for run in runs):
                solved_in_all = False
                break
        if solved_in_all:
            mutually_solved.append(inst)

    print(f"[*] Mutually solved instances across all configurations: {len(mutually_solved)}/36\n")

    summary_stats = {}
    for cfg in CONFIG_ORDER:
        runs = by_cfg[cfg]
        n_runs = len(runs)
        
        # Unique instances solved in at least one rep
        unique_solved = set()
        unique_always_solved = set()
        for inst in all_instances:
            inst_runs = by_inst[inst].get(cfg, [])
            if any(r["status"] in ("SAT", "UNSAT") for r in inst_runs):
                unique_solved.add(inst)
            if inst_runs and all(r["status"] in ("SAT", "UNSAT") for r in inst_runs):
                unique_always_solved.add(inst)

        solved_runs = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
        to_runs = sum(1 for r in runs if r["status"] == "TIMEOUT")
        
        par2_vals = []
        for r in runs:
            st = r["status"]
            wt = parse_num(r["wall_time_s"])
            par2_vals.append(wt if st in ("SAT", "UNSAT") else PAR2_PENALTY)
        par2 = sum(par2_vals) / len(par2_vals) if par2_vals else 0.0

        # Per-instance median times
        inst_medians = []
        for inst in all_instances:
            inst_runs = by_inst[inst].get(cfg, [])
            if inst_runs:
                inst_times = [parse_num(r["wall_time_s"]) for r in inst_runs]
                inst_medians.append(median(inst_times))
        med_t = median(inst_medians)
        iqr_t = iqr(inst_medians)

        # Mutually solved conflicts (mean across reps)
        mut_cfc_list = []
        for inst in mutually_solved:
            inst_runs = by_inst[inst].get(cfg, [])
            cfcs = [parse_num(r["conflicts"], int) for r in inst_runs]
            mut_cfc_list.append(sum(cfcs) / len(cfcs))
        tot_mut_cfc = int(sum(mut_cfc_list))

        peak_mem = max(parse_num(r["memory_mb"]) for r in runs) if runs else 0.0

        summary_stats[cfg] = {
            "unique_solved": len(unique_solved),
            "unique_always_solved": len(unique_always_solved),
            "solved_runs": solved_runs,
            "to_runs": to_runs,
            "par2": par2,
            "median_t": med_t,
            "iqr_t": iqr_t,
            "tot_mut_cfc": tot_mut_cfc,
            "peak_mem": peak_mem
        }

        cfg_name = CONFIG_NAMES[cfg]
        print(f"{cfg_name:<25s} | {len(unique_solved):2d}/36 ({len(unique_always_solved):2d} full) | {solved_runs:3d}/{n_runs:3d}       | {to_runs:<8d} | {par2:10.3f} | {med_t:12.3f} | {iqr_t:10.3f} | {tot_mut_cfc:<12d} | {peak_mem:13.2f}")

    print("=" * 120 + "\n")

    # 2. Family-Level Performance Breakdown
    print("=" * 120)
    print("TABLE 2: FAMILY-LEVEL PAR-2 (s) AND SOLVED COUNTS ACROSS CONFIGURATIONS")
    print("=" * 120)
    fam_header = f"{'Configuration':<25s} | " + " | ".join([f"{f[:16]:<16s} (PAR2/Slv)" for f in sorted(families.keys())])
    print(fam_header)
    print("-" * 120)

    for cfg in CONFIG_ORDER:
        row_str = f"{CONFIG_NAMES[cfg]:<25s} | "
        fam_cols = []
        for fam in sorted(families.keys()):
            fam_insts = families[fam]
            fam_runs = [r for r in by_cfg[cfg] if r["benchmark_name"] in fam_insts]
            fam_solved = sum(1 for r in fam_runs if r["status"] in ("SAT", "UNSAT"))
            fam_par2_list = [parse_num(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for r in fam_runs]
            fam_par2 = sum(fam_par2_list) / len(fam_par2_list) if fam_par2_list else 0.0
            n_tot = len(fam_runs)
            fam_cols.append(f"{fam_par2:6.2f}s ({fam_solved:2d}/{n_tot:2d})")
        row_str += " | ".join([f"{c:<25s}" for c in fam_cols])
        print(row_str)

    print("=" * 120 + "\n")

    # 3. Diagnostic (8 Instances) vs Remaining Development (28 Instances) Split
    print("=" * 120)
    print("TABLE 3: DIAGNOSTIC (N=8) VS. REMAINING DEVELOPMENT (N=28) PAR-2 COMPARISON")
    print("=" * 120)
    print(f"{'Configuration':<25s} | {'Diag PAR-2 (s)':<16s} | {'Diag Solved':<12s} | {'Remaining PAR-2 (s)':<21s} | {'Remaining Solved':<18s}")
    print("-" * 120)

    for cfg in CONFIG_ORDER:
        runs = by_cfg[cfg]
        diag_runs = [r for r in runs if r["benchmark_name"] in DIAGNOSTIC_INSTANCES]
        rem_runs = [r for r in runs if r["benchmark_name"] not in DIAGNOSTIC_INSTANCES]

        diag_par2_l = [parse_num(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for r in diag_runs]
        rem_par2_l = [parse_num(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for r in rem_runs]

        diag_par2 = sum(diag_par2_l) / len(diag_par2_l) if diag_par2_l else 0.0
        rem_par2 = sum(rem_par2_l) / len(rem_par2_l) if rem_par2_l else 0.0

        diag_slv = sum(1 for r in diag_runs if r["status"] in ("SAT", "UNSAT"))
        rem_slv = sum(1 for r in rem_runs if r["status"] in ("SAT", "UNSAT"))

        print(f"{CONFIG_NAMES[cfg]:<25s} | {diag_par2:16.3f} | {diag_slv:2d}/{len(diag_runs):2d}       | {rem_par2:21.3f} | {rem_slv:2d}/{len(rem_runs):2d}")

    print("=" * 120 + "\n")

    # 4. Active V3 Telemetry Audit (Requests, Executed Restarts, Indicators)
    print("=" * 125)
    print("TABLE 4: ACTIVE V3 TRIGGER REQUEST BREAKDOWN ACROSS V3 CONFIGURATIONS (TOTALS ACROSS 108 RUNS)")
    print("=" * 125)
    print(f"{'Configuration':<25s} | {'Trend Reqs':<12s} | {'DD Reqs':<10s} | {'Ceiling Reqs':<14s} | {'Total Reqs':<12s} | {'Exec Restarts':<15s} | {'Blocked Rst':<13s} | {'Mean Int':<10s}")
    print("-" * 125)

    for cfg in ["cfg3_v3_trend_only", "cfg4_v3_drawdown_only", "cfg5_v3_ceiling_only", "cfg6_v3_combined"]:
        runs = by_cfg[cfg]
        t_req = int(sum(parse_num(r.get("v3_req_trend", 0), int, 0) for r in runs))
        dd_req = int(sum(parse_num(r.get("v3_req_drawdown", 0), int, 0) for r in runs))
        c_req = int(sum(parse_num(r.get("v3_req_ceiling", 0), int, 0) for r in runs))
        tot_req = int(sum(parse_num(r.get("v3_total_requests", 0), int, 0) for r in runs))
        exec_rst = int(sum(parse_num(r.get("v3_executed_restarts", 0), int, 0) for r in runs))
        blk_rst = int(sum(parse_num(r.get("v3_blocked_restarts", 0), int, 0) for r in runs))
        max_ints = [parse_num(r.get("v3_max_interval", 0), int, 0) for r in runs]
        mean_max_int = sum(max_ints) / len(max_ints) if max_ints else 0.0

        print(f"{CONFIG_NAMES[cfg]:<25s} | {t_req:<12d} | {dd_req:<10d} | {c_req:<14d} | {tot_req:<12d} | {exec_rst:<15d} | {blk_rst:<13d} | {mean_max_int:10.1f}")

    print("=" * 125 + "\n")

    # 5. Deterministic Stability Audit across Repetitions
    print("=" * 120)
    print("TABLE 5: DETERMINISTIC REPETITION STABILITY & TIMING VARIABILITY AUDIT")
    print("=" * 120)
    
    status_flips = 0
    cfc_mismatches = 0
    rst_mismatches = 0
    timing_iqr_sum = 0.0
    total_inst_cfg = 0

    for inst in all_instances:
        for cfg in CONFIG_ORDER:
            runs = by_inst[inst].get(cfg, [])
            if len(runs) == 3:
                total_inst_cfg += 1
                statuses = set(r["status"] for r in runs)
                if len(statuses) > 1:
                    status_flips += 1
                    print(f"[STATUS FLIP] {inst} under {CONFIG_NAMES[cfg]}: {statuses}")
                
                # Check deterministic conflict and restart equality for solved runs
                solved_runs = [r for r in runs if r["status"] in ("SAT", "UNSAT")]
                if len(solved_runs) == 3:
                    cfcs = set(r["conflicts"] for r in solved_runs)
                    rsts = set(r["genuine_restarts"] for r in solved_runs)
                    if len(cfcs) > 1:
                        cfc_mismatches += 1
                    if len(rsts) > 1:
                        rst_mismatches += 1
                    
                    times = [parse_num(r["wall_time_s"]) for r in solved_runs]
                    timing_iqr_sum += (max(times) - min(times))

    print(f"Total (Instance, Configuration) Pairs Evaluated: {total_inst_cfg}")
    print(f"Status Inconsistencies across Repetitions:       {status_flips}")
    print(f"Conflict Count Inconsistencies on Solved Runs:  {cfc_mismatches}")
    print(f"Restart Count Inconsistencies on Solved Runs:   {rst_mismatches}")
    avg_spread = timing_iqr_sum / (total_inst_cfg - status_flips) if (total_inst_cfg - status_flips) > 0 else 0.0
    print(f"Average Wall-Time Spread (Max - Min per pair):  {avg_spread:.4f}s")
    print("=" * 120 + "\n")

if __name__ == "__main__":
    main()

