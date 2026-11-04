#!/usr/bin/env python3
"""
analyze_v3_adaptive_fixed_interaction.py - Step 31: Factorial Analysis of V3 Drawdown x Adaptive-Fixed Retention

Analyzes experiments/results/v3_adaptive_fixed_interaction/master_results.csv across:
1. Executive Factorial Performance Summary (3 Restarts x 2 Reductions = 6 Configs)
2. Main Factorial Effects & Interaction (PAR-2, Runtime, Conflicts)
3. Six Core Paired Comparisons (A through F)
4. Family-Level Breakdown (Random 3-SAT, Planted SAT, PHP, Graph Coloring)
5. Deep-Dive on Focal Instances (rand3sat_n250, rand3sat_n235, php_10p_9h, gcol_unsat_k10)
6. Reduction Dynamics (Database Reductions, Clause Removals, Spared Clauses)
7. Low-Frequency Restart Confounding (V3 Drawdown vs. Adaptive V1)
8. Deterministic Stability & Repetition Variance
"""

import sys
import csv
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple

WORKSPACE = Path(r"D:\DAC_203@Project")
MASTER_CSV = WORKSPACE / "experiments" / "results" / "v3_adaptive_fixed_interaction" / "master_results.csv"
TIMEOUT_LIMIT = 15.0
PAR2_PENALTY = 30.0

CONFIG_ORDER = [
    "cfg1_base_base",
    "cfg2_v1_base",
    "cfg3_v3dd_base",
    "cfg4_base_adaptfix",
    "cfg5_v1_adaptfix",
    "cfg6_v3dd_adaptfix",
]

CONFIG_NAMES = {
    "cfg1_base_base": "Baseline + Baseline Red",
    "cfg2_v1_base": "Adaptive V1 + Baseline Red",
    "cfg3_v3dd_base": "V3 Drawdown + Baseline Red",
    "cfg4_base_adaptfix": "Baseline + Adaptive-Fixed",
    "cfg5_v1_adaptfix": "Adaptive V1 + Adaptive-Fixed",
    "cfg6_v3dd_adaptfix": "V3 Drawdown + Adaptive-Fixed",
}

FOCAL_INSTANCES = [
    "rand3sat_n250_c1065_s1010.cnf",
    "rand3sat_n235_c999_s1009.cnf",
    "php_10p_9h.cnf",
    "gcol_unsat_k10_c9.cnf",
]

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

    print(f"Loaded {len(records)} runs from {MASTER_CSV}.\n")

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

    # Determine 6-way mutually solved instances across all 3 reps
    mutually_solved_6way = []
    for inst in all_instances:
        solved_all = True
        for cfg in CONFIG_ORDER:
            runs = by_inst[inst].get(cfg, [])
            if len(runs) != 3 or any(run["status"] not in ("SAT", "UNSAT") for run in runs):
                solved_all = False
                break
        if solved_all:
            mutually_solved_6way.append(inst)

    print("=" * 125)
    print("TABLE 1: FACTORIAL CONFIGURATION PERFORMANCE SUMMARY (N = 36 Benchmarks x 3 Repetitions = 108 Runs / Config)")
    print("=" * 125)
    print(f"{'Configuration':<32s} | {'Unique Slv':<11s} | {'Runs Slv':<9s} | {'Timeouts':<8s} | {'PAR-2 (s)':<10s} | {'Med T (s)':<10s} | {'IQR T (s)':<10s} | {'Mut Cfc (6-way)':<15s} | {'Peak Mem (MB)':<13s}")
    print("-" * 125)

    summary_stats = {}
    for cfg in CONFIG_ORDER:
        runs = by_cfg[cfg]
        n_runs = len(runs)
        
        unique_solved = set()
        unique_full = set()
        for inst in all_instances:
            inst_runs = by_inst[inst].get(cfg, [])
            if any(r["status"] in ("SAT", "UNSAT") for r in inst_runs):
                unique_solved.add(inst)
            if inst_runs and all(r["status"] in ("SAT", "UNSAT") for r in inst_runs):
                unique_full.add(inst)

        slv_runs = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
        to_runs = sum(1 for r in runs if r["status"] == "TIMEOUT")

        par2_vals = [parse_num(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for r in runs]
        par2 = sum(par2_vals) / len(par2_vals) if par2_vals else 0.0

        # Per-instance median times
        inst_medians = []
        for inst in all_instances:
            inst_runs = by_inst[inst].get(cfg, [])
            if inst_runs:
                inst_medians.append(median([parse_num(r["wall_time_s"]) for r in inst_runs]))
        med_t = median(inst_medians)
        iqr_t = iqr(inst_medians)

        # Mutually solved conflicts
        mut_cfc_list = []
        for inst in mutually_solved_6way:
            cfcs = [parse_num(r["conflicts"], int) for r in by_inst[inst][cfg]]
            mut_cfc_list.append(sum(cfcs) / len(cfcs))
        tot_mut_cfc = int(sum(mut_cfc_list))

        peak_mem = max(parse_num(r["memory_mb"]) for r in runs) if runs else 0.0

        summary_stats[cfg] = {
            "unique_solved": len(unique_solved),
            "unique_full": len(unique_full),
            "slv_runs": slv_runs,
            "to_runs": to_runs,
            "par2": par2,
            "med_t": med_t,
            "iqr_t": iqr_t,
            "tot_mut_cfc": tot_mut_cfc,
            "peak_mem": peak_mem
        }

        cfg_name = CONFIG_NAMES[cfg]
        print(f"{cfg_name:<32s} | {len(unique_solved):2d}/36 ({len(unique_full):2d}) | {slv_runs:3d}/{n_runs:3d}   | {to_runs:<8d} | {par2:10.3f} | {med_t:10.3f} | {iqr_t:10.3f} | {tot_mut_cfc:<15d} | {peak_mem:13.2f}")

    print("=" * 125)
    print(f"[*] Mutually solved instances across all 6 configurations (all 3 reps): {len(mutually_solved_6way)}/36\n")

    # 2. Main Factorial Effects & Interaction Analysis
    print("=" * 100)
    print("TABLE 2: 3x2 FACTORIAL PAR-2 MATRIX & INTERACTION CALCULATION")
    print("=" * 100)
    print(f"{'Restart Policy':<25s} | {'Baseline Retention':<20s} | {'Adaptive-Fixed Retention':<25s} | {'Retention Diff (Fixed - Base)':<28s}")
    print("-" * 100)

    p_base_base = summary_stats["cfg1_base_base"]["par2"]
    p_base_fix  = summary_stats["cfg4_base_adaptfix"]["par2"]
    diff_base   = p_base_fix - p_base_base

    p_v1_base   = summary_stats["cfg2_v1_base"]["par2"]
    p_v1_fix    = summary_stats["cfg5_v1_adaptfix"]["par2"]
    diff_v1     = p_v1_fix - p_v1_base

    p_v3_base   = summary_stats["cfg3_v3dd_base"]["par2"]
    p_v3_fix    = summary_stats["cfg6_v3dd_adaptfix"]["par2"]
    diff_v3     = p_v3_fix - p_v3_base

    print(f"{'Baseline Glucose':<25s} | {p_base_base:10.3f}s          | {p_base_fix:10.3f}s               | {diff_base:+10.3f}s")
    print(f"{'Adaptive Restart V1':<25s} | {p_v1_base:10.3f}s          | {p_v1_fix:10.3f}s               | {diff_v1:+10.3f}s")
    print(f"{'V3 Drawdown-Only':<25s} | {p_v3_base:10.3f}s          | {p_v3_fix:10.3f}s               | {diff_v3:+10.3f}s")
    print("-" * 100)

    # Interaction: [(V3dd + adaptfix) - (V3dd + base)] - [(base + adaptfix) - (base + base)]
    interaction_v3_vs_base = diff_v3 - diff_base
    interaction_v1_vs_base = diff_v1 - diff_base

    print(f"\n[+] FACTORIAL INTERACTION RESULTS:")
    print(f"  * Baseline Retention Effect (Holding Baseline Restart):       {diff_base:+.3f}s")
    print(f"  * Baseline Retention Effect (Holding V3 Drawdown Restart):    {diff_v3:+.3f}s")
    print(f"  * Factorial Interaction [ (V3dd x Fix) vs (Base x Base) ]:     {interaction_v3_vs_base:+.3f}s")
    print(f"    -> Interpretation: {'Negative (Synergistic / Favorable)' if interaction_v3_vs_base < 0 else 'Positive (Antagonistic / Unfavorable)'}")
    print(f"  * Factorial Interaction [ (V1 x Fix) vs (Base x Base) ]:       {interaction_v1_vs_base:+.3f}s")
    print("=" * 100 + "\n")

    # 3. Six Core Paired Comparisons (A through F)
    print("=" * 110)
    print("TABLE 3: SIX CORE PAIRED COMPARISONS (A THROUGH F)")
    print("=" * 110)
    
    comparisons = [
        ("A. Baseline vs V3 Drawdown (Baseline Reduction)", "cfg1_base_base", "cfg3_v3dd_base"),
        ("B. Baseline vs V3 Drawdown (Adaptive-Fixed Reduction)", "cfg4_base_adaptfix", "cfg6_v3dd_adaptfix"),
        ("C. Adaptive V1 vs V3 Drawdown (Baseline Reduction)", "cfg2_v1_base", "cfg3_v3dd_base"),
        ("D. Adaptive V1 vs V3 Drawdown (Adaptive-Fixed Reduction)", "cfg5_v1_adaptfix", "cfg6_v3dd_adaptfix"),
        ("E1. Baseline vs Adaptive-Fixed (Baseline Restarts)", "cfg1_base_base", "cfg4_base_adaptfix"),
        ("E2. Baseline vs Adaptive-Fixed (Adaptive V1 Restarts)", "cfg2_v1_base", "cfg5_v1_adaptfix"),
        ("E3. Baseline vs Adaptive-Fixed (V3 Drawdown Restarts)", "cfg3_v3dd_base", "cfg6_v3dd_adaptfix"),
        ("F. V3 Drawdown+Base vs V3 Drawdown+Adaptive-Fixed", "cfg3_v3dd_base", "cfg6_v3dd_adaptfix"),
    ]

    print(f"{'Comparison':<52s} | {'Config 1 PAR2':<14s} | {'Config 2 PAR2':<14s} | {'Diff (C2 - C1)':<15s} | {'Advantage'}")
    print("-" * 110)

    for label, c1, c2 in comparisons:
        par1 = summary_stats[c1]["par2"]
        par2 = summary_stats[c2]["par2"]
        diff = par2 - par1
        adv = CONFIG_NAMES[c2] if diff < 0 else CONFIG_NAMES[c1]
        print(f"{label:<52s} | {par1:10.3f}s    | {par2:10.3f}s    | {diff:+10.3f}s     | Favors {adv}")

    print("=" * 110 + "\n")

    # 4. Family-Level Factorial Breakdown
    print("=" * 125)
    print("TABLE 4: FAMILY-LEVEL PAR-2 (s) AND SOLVED RUN COUNTS ACROSS FACTORIAL CONFIGURATIONS")
    print("=" * 125)
    header = f"{'Configuration':<30s} | " + " | ".join([f"{f[:16]:<16s} (PAR2/Slv)" for f in sorted(families.keys())])
    print(header)
    print("-" * 125)

    for cfg in CONFIG_ORDER:
        row_str = f"{CONFIG_NAMES[cfg]:<30s} | "
        fam_cols = []
        for fam in sorted(families.keys()):
            fam_insts = families[fam]
            fam_runs = [r for r in by_cfg[cfg] if r["benchmark_name"] in fam_insts]
            fam_slv = sum(1 for r in fam_runs if r["status"] in ("SAT", "UNSAT"))
            fam_par2_list = [parse_num(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for r in fam_runs]
            fam_par2 = sum(fam_par2_list) / len(fam_par2_list) if fam_par2_list else 0.0
            n_tot = len(fam_runs)
            fam_cols.append(f"{fam_par2:6.2f}s ({fam_slv:2d}/{n_tot:2d})")
        row_str += " | ".join([f"{c:<25s}" for c in fam_cols])
        print(row_str)

    print("=" * 125 + "\n")

    # 5. Deep-Dive on Focal Benchmarks
    print("=" * 125)
    print("TABLE 5: FOCAL BENCHMARK PER-INSTANCE RUNTIME & CONFLICT PROFILES")
    print("=" * 125)
    focal_header = f"{'Benchmark':<32s} | {'Metric':<10s} | " + " | ".join([f"{CONFIG_NAMES[c][:12]:<12s}" for c in CONFIG_ORDER])
    print(focal_header)
    print("-" * 125)

    for inst in FOCAL_INSTANCES:
        row_t = f"{inst:<32s} | {'Time (s)':<10s} | "
        row_c = f"{'':<32s} | {'Conflicts':<10s} | "
        row_r = f"{'':<32s} | {'Restarts':<10s} | "
        row_d = f"{'':<32s} | {'Reduces':<10s} | "

        t_list, c_list, r_list, d_list = [], [], [], []
        for cfg in CONFIG_ORDER:
            runs = by_inst[inst].get(cfg, [])
            if not runs:
                t_list.append("N/A"); c_list.append("N/A"); r_list.append("N/A"); d_list.append("N/A")
                continue
            to_cnt = sum(1 for r in runs if r["status"] == "TIMEOUT")
            if to_cnt == 3:
                t_list.append("TO (3/3)")
                c_list.append("TO")
                r_list.append("TO")
                d_list.append("TO")
            else:
                slv_runs = [r for r in runs if r["status"] in ("SAT", "UNSAT")]
                m_t = sum(parse_num(r["wall_time_s"]) for r in slv_runs) / len(slv_runs)
                m_c = int(sum(parse_num(r["conflicts"], int) for r in slv_runs) / len(slv_runs))
                m_r = int(sum(parse_num(r["genuine_restarts"], int) for r in slv_runs) / len(slv_runs))
                m_d = int(sum(parse_num(r["reduce_db_count"], int) for r in slv_runs) / len(slv_runs))
                to_tag = f" ({to_cnt}TO)" if to_cnt > 0 else ""
                t_list.append(f"{m_t:.2f}s{to_tag}")
                c_list.append(f"{m_c}")
                r_list.append(f"{m_r}")
                d_list.append(f"{m_d}")

        row_t += " | ".join([f"{x:<12s}" for x in t_list])
        row_c += " | ".join([f"{x:<12s}" for x in c_list])
        row_r += " | ".join([f"{x:<12s}" for x in r_list])
        row_d += " | ".join([f"{x:<12s}" for x in d_list])

        print(row_t)
        print(row_c)
        print(row_r)
        print(row_d)
        print("-" * 125)

    # 6. Clause Database Reduction & Nogood Dynamics
    print("\n" + "=" * 120)
    print("TABLE 6: CLAUSE DATABASE REDUCTION DYNAMICS ACROSS FACTORIAL CONFIGURATIONS (TOTALS ACROSS 108 RUNS)")
    print("=" * 120)
    print(f"{'Configuration':<32s} | {'ReduceDB Calls':<15s} | {'Clauses Removed':<16s} | {'Spared Binary':<14s} | {'Spared Glue':<13s} | {'Spared CanBeDel':<16s}")
    print("-" * 120)

    for cfg in CONFIG_ORDER:
        runs = by_cfg[cfg]
        tot_red = int(sum(parse_num(r["reduce_db_count"], int) for r in runs))
        tot_rem = int(sum(parse_num(r["removed_clauses"], int) for r in runs))
        tot_bin = int(sum(parse_num(r.get("adapt_spared_binary", 0), int) for r in runs))
        tot_glue = int(sum(parse_num(r.get("adapt_spared_glue", 0), int) for r in runs))
        tot_can = int(sum(parse_num(r.get("adapt_spared_canbedel", 0), int) for r in runs))

        print(f"{CONFIG_NAMES[cfg]:<32s} | {tot_red:<15d} | {tot_rem:<16d} | {tot_bin:<14d} | {tot_glue:<13d} | {tot_can:<16d}")

    print("=" * 120 + "\n")

    # 7. Low-Frequency Restart Confounding Audit
    print("=" * 110)
    print("TABLE 7: RESTART FREQUENCY CONFOUNDING AUDIT: V3 DRAWDOWN VS. ADAPTIVE V1")
    print("=" * 110)
    print(f"{'Configuration':<32s} | {'Total Restarts (108 runs)':<26s} | {'Mean Descent Interval':<22s} | {'PAR-2 (s)':<10s}")
    print("-" * 110)
    for cfg in ["cfg1_base_base", "cfg2_v1_base", "cfg3_v3dd_base", "cfg5_v1_adaptfix", "cfg6_v3dd_adaptfix"]:
        runs = by_cfg[cfg]
        tot_rst = int(sum(parse_num(r["genuine_restarts"], int) for r in runs))
        # compute mean interval across runs
        intervals = []
        for r in runs:
            c = parse_num(r["conflicts"], int)
            rst = parse_num(r["genuine_restarts"], int)
            intervals.append(c / (rst + 1))
        mean_int = sum(intervals) / len(intervals) if intervals else 0.0
        par2 = summary_stats[cfg]["par2"]
        print(f"{CONFIG_NAMES[cfg]:<32s} | {tot_rst:<26d} | {mean_int:<22.1f} | {par2:10.3f}")
    print("=" * 110 + "\n")

    # 8. Deterministic Stability Audit
    print("=" * 110)
    print("TABLE 8: REPETITION STABILITY & DETERMINISM AUDIT")
    print("=" * 110)
    status_flips = 0
    cfc_mismatches = 0
    rst_mismatches = 0
    red_mismatches = 0
    total_pairs = 0

    for inst in all_instances:
        for cfg in CONFIG_ORDER:
            runs = by_inst[inst].get(cfg, [])
            if len(runs) == 3:
                total_pairs += 1
                statuses = set(r["status"] for r in runs)
                if len(statuses) > 1:
                    status_flips += 1
                    print(f"  [STATUS FLIP] {inst} under {CONFIG_NAMES[cfg]}: {statuses}")
                
                slv_runs = [r for r in runs if r["status"] in ("SAT", "UNSAT")]
                if len(slv_runs) == 3:
                    cfcs = set(r["conflicts"] for r in slv_runs)
                    rsts = set(r["genuine_restarts"] for r in slv_runs)
                    reds = set(r["reduce_db_count"] for r in slv_runs)
                    if len(cfcs) > 1:
                        cfc_mismatches += 1
                    if len(rsts) > 1:
                        rst_mismatches += 1
                    if len(reds) > 1:
                        red_mismatches += 1

    print(f"Total (Instance, Config) Evaluated:      {total_pairs}")
    print(f"Status Inconsistencies (Timeout Flips): {status_flips}")
    print(f"Conflict Count Inconsistencies:         {cfc_mismatches}")
    print(f"Restart Count Inconsistencies:          {rst_mismatches}")
    print(f"Reduction Count Inconsistencies:        {red_mismatches}")
    print("=" * 110 + "\n")

if __name__ == "__main__":
    main()

