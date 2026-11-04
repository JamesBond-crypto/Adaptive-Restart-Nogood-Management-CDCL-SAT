#!/usr/bin/env python3
"""
analyze_v3_low_frequency_control.py - Step 32 Analysis Script

Analyzes the 10-configuration comparative evaluation across the 8 Step 29 diagnostic benchmarks:
1. Executive Performance Summary: Solved/8, Timeouts, PAR-2, Median Time, Conflicts, Restarts, Memory.
2. Grouped Comparison:
   - Part A: Baseline Clause Reduction (Baseline, V1, V3dd, Fixed 10k, Fixed 20k, No-Heuristic)
   - Part B: Adaptive-Fixed Clause Reduction (V3dd, Fixed 10k, Fixed 20k, No-Heuristic)
3. Frequency Confound Analysis:
   - Restart counts and actual descent lengths across configurations.
   - V3 Drawdown vs Fixed-Interval vs No-Heuristic.
4. Problem-Family Breakdown (Graph Coloring, PHP, Planted SAT, Random 3-SAT).
5. Focal Instance Deep-Dive across all 8 benchmarks.
"""

import sys
import csv
import math
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_CSV = WORKSPACE / "experiments" / "results" / "v3_low_frequency_control" / "master_results.csv"
TIMEOUT_LIMIT = 15.0
PAR2_PENALTY = 30.0

CONFIG_ORDER = [
    "cfg01_baseline_base",
    "cfg02_v1_base",
    "cfg03_v3dd_base",
    "cfg04_fixed10k_base",
    "cfg05_fixed20k_base",
    "cfg06_noheuristic_base",
    "cfg07_v3dd_adaptfix",
    "cfg08_fixed10k_adaptfix",
    "cfg09_fixed20k_adaptfix",
    "cfg10_noheuristic_adaptfix"
]

CONFIG_NAMES = {
    "cfg01_baseline_base": "Baseline + Base Red",
    "cfg02_v1_base": "Adaptive V1 + Base Red",
    "cfg03_v3dd_base": "V3 Drawdown + Base Red",
    "cfg04_fixed10k_base": "Fixed 10k + Base Red",
    "cfg05_fixed20k_base": "Fixed 20k + Base Red",
    "cfg06_noheuristic_base": "No-Heuristic + Base Red",
    "cfg07_v3dd_adaptfix": "V3 Drawdown + AdaptFix",
    "cfg08_fixed10k_adaptfix": "Fixed 10k + AdaptFix",
    "cfg09_fixed20k_adaptfix": "Fixed 20k + AdaptFix",
    "cfg10_noheuristic_adaptfix": "No-Heuristic + AdaptFix"
}

def load_data():
    records = []
    with open(RESULTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append(r)
    return records

def compute_par2(wall_time, timed_out):
    if timed_out or wall_time is None or wall_time >= TIMEOUT_LIMIT:
        return PAR2_PENALTY
    return wall_time

def main():
    records = load_data()
    print("=" * 110)
    print("STEP 32: FREQUENCY-CONTROLLED RESTART BASELINES FOR FINANCE-INSPIRED V3 ANALYSIS")
    print("=" * 110)
    
    # Group by config
    by_cfg = defaultdict(list)
    by_inst = defaultdict(dict)
    
    for r in records:
        cfg = r["config_id"]
        inst = r["benchmark_name"]
        by_cfg[cfg].append(r)
        by_inst[inst][cfg] = r
        
    all_instances = sorted(list(by_inst.keys()))
    
    # Find mutually solved across ALL 10 configs
    mutually_solved_all = []
    for inst in all_instances:
        solved_all = True
        for cfg in CONFIG_ORDER:
            row = by_inst[inst].get(cfg)
            if not row or row["timed_out"] == "True" or row["status"] not in ("SAT", "UNSAT"):
                solved_all = False
                break
        if solved_all:
            mutually_solved_all.append(inst)
            
    print(f"\n[*] Mutually Solved across ALL 10 configurations: {len(mutually_solved_all)} / {len(all_instances)} instances")
    for m in mutually_solved_all:
        print(f"    - {m}")
        
    # --- TABLE 1: Executive Performance Summary ---
    print("\n" + "=" * 110)
    print("TABLE 1: Executive Performance Summary across 8 Diagnostic Benchmarks")
    print("=" * 110)
    header = f"{'Configuration':<26} | {'Solved':<8} | {'Timeouts':<8} | {'PAR-2 (s)':<10} | {'Mean Time':<10} | {'Median':<8} | {'Total Cfc':<11} | {'Mut Cfc':<9} | {'Rsts':<6} | {'Peak Mem'}"
    print(header)
    print("-" * 110)
    
    cfg_summary = {}
    for cfg in CONFIG_ORDER:
        rows = by_cfg[cfg]
        solved_cnt = sum(1 for r in rows if r["timed_out"] == "False" and r["status"] in ("SAT", "UNSAT"))
        to_cnt = sum(1 for r in rows if r["timed_out"] == "True")
        
        times = [float(r["wall_time_s"]) for r in rows]
        par2_vals = [compute_par2(float(r["wall_time_s"]), r["timed_out"] == "True") for r in rows]
        mean_par2 = sum(par2_vals) / len(par2_vals)
        mean_time = sum(times) / len(times)
        sorted_times = sorted(times)
        median_time = (sorted_times[len(sorted_times)//2 - 1] + sorted_times[len(sorted_times)//2]) / 2.0
        
        # Conflicts
        solved_cfcs = [int(r["conflicts"]) for r in rows if r["conflicts"] and r["timed_out"] == "False"]
        tot_cfc = sum(solved_cfcs)
        
        # Mutually solved conflicts
        mut_cfcs = [int(by_inst[m][cfg]["conflicts"]) for m in mutually_solved_all if by_inst[m][cfg]["conflicts"]]
        tot_mut_cfc = sum(mut_cfcs)
        
        # Restarts
        rsts = [int(r["genuine_restarts"]) for r in rows if r["genuine_restarts"] != ""]
        tot_rsts = sum(rsts)
        
        # Memory
        mems = [float(r["memory_mb"]) for r in rows if r["memory_mb"]]
        peak_mem = max(mems) if mems else 0.0
        
        cfg_summary[cfg] = {
            "solved": solved_cnt,
            "to": to_cnt,
            "par2": mean_par2,
            "mean_time": mean_time,
            "median_time": median_time,
            "tot_cfc": tot_cfc,
            "mut_cfc": tot_mut_cfc,
            "rsts": tot_rsts,
            "peak_mem": peak_mem
        }
        
        cfg_label = CONFIG_NAMES[cfg]
        print(f"{cfg_label:<26} | {solved_cnt:>2}/8      | {to_cnt:>2}/8      | {mean_par2:>8.3f}s  | {mean_time:>8.3f}s  | {median_time:>6.3f}s | {tot_cfc:>11,d} | {tot_mut_cfc:>9,d} | {tot_rsts:>6d} | {peak_mem:>6.2f} MB")
    print("=" * 110)
    
    # --- TABLE 2: Strategy Component & Telemetry Breakdown ---
    print("\n" + "=" * 110)
    print("TABLE 2: Detailed Restart Telemetry & Descent Interval Characteristics")
    print("=" * 110)
    h2 = f"{'Configuration':<26} | {'Genuine Rsts':<12} | {'Fixed Reqs':<10} | {'Fixed Exec':<10} | {'100k Adapt':<10} | {'Max Interval':<12} | {'Reductions':<10} | {'Clauses Del'}"
    print(h2)
    print("-" * 110)
    for cfg in CONFIG_ORDER:
        rows = by_cfg[cfg]
        tot_rsts = sum(int(r["genuine_restarts"]) for r in rows if r["genuine_restarts"])
        tot_freq = sum(int(r["fixed_restart_requests"]) for r in rows if r.get("fixed_restart_requests"))
        tot_fexec = sum(int(r["fixed_executed_restarts"]) for r in rows if r.get("fixed_executed_restarts"))
        tot_adapt = sum(int(r["strategy_adaptation_restarts"]) for r in rows if r.get("strategy_adaptation_restarts"))
        max_intvs = [int(r["fixed_max_interval"]) for r in rows if r.get("fixed_max_interval")]
        peak_max_intv = max(max_intvs) if max_intvs else 0
        tot_red = sum(int(r["reduce_db_count"]) for r in rows if r.get("reduce_db_count"))
        tot_del = sum(int(r["removed_clauses"]) for r in rows if r.get("removed_clauses"))
        
        cfg_label = CONFIG_NAMES[cfg]
        print(f"{cfg_label:<26} | {tot_rsts:>12d} | {tot_freq:>10d} | {tot_fexec:>10d} | {tot_adapt:>10d} | {peak_max_intv:>12,d} | {tot_red:>10d} | {tot_del:>11,d}")
    print("=" * 110)
    
    # --- TABLE 3: Family Breakdown ---
    print("\n" + "=" * 110)
    print("TABLE 3: Problem Family Performance Breakdown (PAR-2 & Solved Count)")
    print("=" * 110)
    families = {
        "Random 3-SAT": ["rand3sat_n250_c1065_s1010.cnf", "rand3sat_n200_c840_s1005.cnf"],
        "Pigeonhole Principle": ["php_10p_9h.cnf", "php_10p_8h.cnf"],
        "Graph Coloring": ["gcol_unsat_k10_c9.cnf", "gcol_unsat_k9_c8.cnf"],
        "Planted 3-SAT": ["planted3sat_n240_c1022_s2009.cnf", "planted3sat_n200_c852_s2005.cnf"]
    }
    
    h3 = f"{'Configuration':<26} | {'Rand 3-SAT (2)':<16} | {'PHP (2)':<16} | {'Graph Col (2)':<16} | {'Planted SAT (2)':<16}"
    print(h3)
    print("-" * 110)
    for cfg in CONFIG_ORDER:
        fam_scores = []
        for fam_name, insts in families.items():
            f_par2s = [compute_par2(float(by_inst[i][cfg]["wall_time_s"]), by_inst[i][cfg]["timed_out"] == "True") for i in insts]
            f_slv = sum(1 for i in insts if by_inst[i][cfg]["timed_out"] == "False" and by_inst[i][cfg]["status"] in ("SAT", "UNSAT"))
            avg_par2 = sum(f_par2s) / len(f_par2s)
            fam_scores.append(f"{avg_par2:>6.2f}s ({f_slv}/2)")
        cfg_label = CONFIG_NAMES[cfg]
        print(f"{cfg_label:<26} | {fam_scores[0]:<16} | {fam_scores[1]:<16} | {fam_scores[2]:<16} | {fam_scores[3]:<16}")
    print("=" * 110)
    
    # --- TABLE 4: Benchmark-by-Benchmark Breakdown ---
    print("\n" + "=" * 110)
    print("TABLE 4: Benchmark-by-Benchmark Matrix (Runtime in Seconds | Conflicts)")
    print("=" * 110)
    for inst in all_instances:
        print(f"\n--- {inst} ---")
        print(f"{'Configuration':<26} | {'Status':<6} | {'Wall Time':<10} | {'Conflicts':<11} | {'Restarts':<8} | {'Reduces':<8}")
        print("-" * 80)
        for cfg in CONFIG_ORDER:
            row = by_inst[inst][cfg]
            st = row["status"]
            wt = f"{float(row['wall_time_s']):.3f}s"
            cf = f"{int(row['conflicts']):,d}" if row["conflicts"] else "TIMEOUT"
            rs = str(row["genuine_restarts"]) if row["genuine_restarts"] != "" else "0"
            rd = str(row["reduce_db_count"]) if row["reduce_db_count"] else "0"
            cfg_label = CONFIG_NAMES[cfg]
            print(f"{cfg_label:<26} | {st:<6} | {wt:<10} | {cf:<11} | {rs:<8} | {rd:<8}")

if __name__ == "__main__":
    main()

