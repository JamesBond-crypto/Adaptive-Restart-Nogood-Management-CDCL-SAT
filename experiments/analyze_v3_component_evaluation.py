#!/usr/bin/env python3
"""
analyze_v3_component_evaluation.py - Analysis of V3 Component Validation Experiment

Reads experiments/results/v3_component_evaluation.csv and generates:
1. Executive Configuration Summary (Solved, Timeouts, PAR-2, Conflicts, Runtimes)
2. Per-Instance Comparative Matrix across all 6 configurations
3. Component Trigger Breakdown (Trend vs. Drawdown vs. Ceiling)
4. Family-Level Performance Analysis (Random 3-SAT, Planted 3-SAT, PHP, Graph Coloring)
5. Algorithmic Synergy and Regression Resolution Assessment
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_CSV = WORKSPACE / "experiments" / "results" / "v3_component_evaluation.csv"
TIMEOUT_LIMIT = 15.0
PAR2_PENALTY = 2.0 * TIMEOUT_LIMIT # 30.0s

CONFIG_ORDER = [
    "cfg1_baseline",
    "cfg2_v1",
    "cfg3_v3_trend_only",
    "cfg4_v3_drawdown_only",
    "cfg5_v3_ceiling_only",
    "cfg6_v3_combined",
]

CONFIG_NAMES = {
    "cfg1_baseline": "Baseline Glucose",
    "cfg2_v1": "Adaptive V1",
    "cfg3_v3_trend_only": "Active V3 (Trend Only)",
    "cfg4_v3_drawdown_only": "Active V3 (Drawdown Only)",
    "cfg5_v3_ceiling_only": "Active V3 (Ceiling Only)",
    "cfg6_v3_combined": "Active V3 (Combined: Trend+DD+Ceil)",
}

def parse_val(v, conv=float, default=0.0):
    if v is None or v == "":
        return default
    try:
        return conv(v)
    except Exception:
        return default

def main():
    if not RESULTS_CSV.exists():
        print(f"ERROR: Results file not found: {RESULTS_CSV}")
        sys.exit(1)

    records = []
    with open(RESULTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append(r)

    print(f"Loaded {len(records)} run records from {RESULTS_CSV}.\n")

    # Group by config
    by_config = defaultdict(list)
    by_instance = defaultdict(dict)
    all_instances = []

    for r in records:
        cfg = r["config_id"]
        inst = r["benchmark_name"]
        by_config[cfg].append(r)
        by_instance[inst][cfg] = r
        if inst not in all_instances:
            all_instances.append(inst)

    # 1. Executive Configuration Summary
    print("=" * 110)
    print("TABLE 1: EXECUTIVE CONFIGURATION SUMMARY (N = 8 Development Instances, Timeout = 15.0s)")
    print("=" * 110)
    print(f"{'Configuration':<35s} | {'Solved':<7s} | {'Timeouts':<8s} | {'PAR-2 (s)':<10s} | {'Mean Time (s)':<13s} | {'Total Conflicts':<15s} | {'Total Restarts':<14s}")
    print("-" * 110)

    summary_stats = {}
    for cfg in CONFIG_ORDER:
        runs = by_config.get(cfg, [])
        if not runs:
            continue
        n = len(runs)
        solved = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
        timeouts = sum(1 for r in runs if r["status"] == "TIMEOUT")
        
        # PAR-2 calculation
        par2_times = []
        solved_times = []
        solved_conflicts = []
        restarts = []
        for r in runs:
            wtime = parse_val(r["wall_time_s"])
            rst = parse_val(r["genuine_restarts"], int, 0)
            restarts.append(rst)
            if r["status"] in ("SAT", "UNSAT"):
                par2_times.append(wtime)
                solved_times.append(wtime)
                solved_conflicts.append(parse_val(r["conflicts"], int, 0))
            else:
                par2_times.append(PAR2_PENALTY)

        par2 = sum(par2_times) / n if n > 0 else 0.0
        mean_time = sum(solved_times) / solved if solved > 0 else 0.0
        tot_confl = sum(solved_conflicts)
        tot_rst = sum(restarts)

        summary_stats[cfg] = {
            "solved": solved,
            "timeouts": timeouts,
            "par2": par2,
            "mean_time": mean_time,
            "tot_confl": tot_confl,
            "tot_rst": tot_rst
        }

        cfg_label = CONFIG_NAMES.get(cfg, cfg)
        print(f"{cfg_label:<35s} | {solved:2d}/{n:2d}   | {timeouts:<8d} | {par2:10.3f} | {mean_time:13.3f} | {tot_confl:<15d} | {tot_rst:<14d}")

    print("=" * 110 + "\n")

    # 2. Per-Instance Comparison Matrix
    print("=" * 125)
    print("TABLE 2: PER-INSTANCE DETAILED RUNTIMES, CONFLICTS, AND RESTARTS ACROSS CONFIGURATIONS")
    print("=" * 125)
    header = f"{'Instance':<32s} | {'Family':<10s} | {'Metric':<10s} | " + " | ".join([f"{CONFIG_NAMES[c][:14]:<14s}" for c in CONFIG_ORDER])
    print(header)
    print("-" * 125)

    for inst in all_instances:
        runs_for_inst = by_instance[inst]
        sample = next(iter(runs_for_inst.values()))
        family = sample.get("family", "")

        row_time = f"{inst:<32s} | {family:<10s} | {'Time (s)':<10s} | "
        row_cfc  = f"{'':<32s} | {'':<10s} | {'Conflicts':<10s} | "
        row_rst  = f"{'':<32s} | {'':<10s} | {'Restarts':<10s} | "

        times = []
        cfcs = []
        rsts = []

        for cfg in CONFIG_ORDER:
            r = runs_for_inst.get(cfg)
            if r:
                st = r["status"]
                wtime = parse_val(r["wall_time_s"])
                c = parse_val(r["conflicts"], int, 0)
                rst = parse_val(r["genuine_restarts"], int, 0)
                if st == "TIMEOUT":
                    times.append("TO (15s)")
                    cfcs.append(f"{c}*")
                else:
                    times.append(f"{wtime:.3f}")
                    cfcs.append(f"{c}")
                rsts.append(f"{rst}")
            else:
                times.append("N/A")
                cfcs.append("N/A")
                rsts.append("N/A")

        row_time += " | ".join([f"{t:<14s}" for t in times])
        row_cfc  += " | ".join([f"{c:<14s}" for c in cfcs])
        row_rst  += " | ".join([f"{r:<14s}" for r in rsts])

        print(row_time)
        print(row_cfc)
        print(row_rst)
        print("-" * 125)

    # 3. Active V3 Telemetry and Trigger Breakdown
    print("\n" + "=" * 120)
    print("TABLE 3: ACTIVE V3 TRIGGER EVENT BREAKDOWN & INDICATOR DISTRIBUTIONS")
    print("=" * 120)
    print(f"{'Instance':<32s} | {'Config':<20s} | {'Req Trend':<10s} | {'Req DD':<8s} | {'Req Ceil':<10s} | {'Total Req':<10s} | {'Exec Rst':<9s} | {'Max Int':<8s} | {'Fast EWMA':<10s} | {'Slow EWMA':<10s} | {'Max DD':<8s}")
    print("-" * 120)

    for inst in all_instances:
        runs_for_inst = by_instance[inst]
        for cfg in ["cfg3_v3_trend_only", "cfg4_v3_drawdown_only", "cfg5_v3_ceiling_only", "cfg6_v3_combined"]:
            r = runs_for_inst.get(cfg)
            if not r:
                continue
            req_t = parse_val(r.get("v3_req_trend", ""), int, 0)
            req_dd = parse_val(r.get("v3_req_drawdown", ""), int, 0)
            req_c = parse_val(r.get("v3_req_ceiling", ""), int, 0)
            tot_req = parse_val(r.get("v3_total_requests", ""), int, 0)
            exec_rst = parse_val(r.get("v3_executed_restarts", ""), int, 0)
            max_int = parse_val(r.get("v3_max_interval", ""), int, 0)
            fast = parse_val(r.get("v3_active_final_fast", ""), float, 0.0)
            slow = parse_val(r.get("v3_active_final_slow", ""), float, 0.0)
            mdd = parse_val(r.get("v3_active_max_dd", ""), float, 0.0)

            cfg_short = cfg.replace("cfg3_", "").replace("cfg4_", "").replace("cfg5_", "").replace("cfg6_", "")
            print(f"{inst:<32s} | {cfg_short:<20s} | {req_t:<10d} | {req_dd:<8d} | {req_c:<10d} | {tot_req:<10d} | {exec_rst:<9d} | {max_int:<8d} | {fast:<10.4f} | {slow:<10.4f} | {mdd:<8.4f}")

    print("=" * 120 + "\n")

if __name__ == "__main__":
    main()

