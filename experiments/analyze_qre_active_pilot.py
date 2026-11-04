#!/usr/bin/env python3
"""
analyze_qre_active_pilot.py - Statistical Analysis of Step 39 Active Pilot Experiment

Reads master_results.csv from experiments/results/qre_active_pilot/
Computes:
  1. Global Configuration Performance (Solved, PAR-2, CPU, Wall, Conflicts, Genuine Restarts)
  2. Telemetry Breakdown for Active QRE (Raw, Sustained, Suppressed, Executed)
  3. Family-Specific Performance (Structured UNSAT vs Random SAT)
  4. Instrumentation Overhead Analysis (Baseline vs Optimized Shadow vs Active)
  5. Per-Benchmark Trajectory Comparison across Repetitions
"""

import sys
import os
import csv
import math
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "qre_active_pilot"
MASTER_CSV = RESULTS_DIR / "master_results.csv"

def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def median(vals):
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0

def stddev(vals):
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))

def main():
    if not MASTER_CSV.exists():
        print(f"ERROR: {MASTER_CSV} does not exist.")
        sys.exit(1)

    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total Rows Loaded: {len(rows)}")

    # Group by config_id
    by_config = defaultdict(list)
    for r in rows:
        by_config[r["config_id"]].append(r)

    # 1. Global Performance Table
    print("\n" + "=" * 110)
    print("TABLE 1: GLOBAL CONFIGURATION SUMMARY (16 Benchmarks x 3 Repetitions = 48 Runs / Config)")
    print("=" * 110)
    print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean CPU':10s} | {'Mean Cfc':10s} | {'Gen Rst':8s} | {'QRE Rst':8s}")
    print("-" * 110)

    summary_stats = {}
    for cid, runs in by_config.items():
        n = len(runs)
        solved = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
        par2_vals = [float(r["par2_s"]) for r in runs]
        wall_vals = [float(r["wall_time_s"]) for r in runs]
        cpu_vals = [float(r["cpu_time_s"]) for r in runs]
        cfc_vals = [int(r["conflicts"]) for r in runs]
        gen_rst_vals = [int(r["genuine_restarts"]) for r in runs]
        qre_rst_vals = [int(r["qre_executed_restarts"]) for r in runs]

        summary_stats[cid] = {
            "solved": solved,
            "total": n,
            "par2_mean": mean(par2_vals),
            "wall_mean": mean(wall_vals),
            "cpu_mean": mean(cpu_vals),
            "cfc_mean": mean(cfc_vals),
            "gen_rst_mean": mean(gen_rst_vals),
            "qre_rst_total": sum(qre_rst_vals),
            "runs": runs
        }

        print(f"{cid:24s} | {solved:2d}/{n:2d}   | {mean(par2_vals):10.4f} | {mean(wall_vals):10.4f} | {mean(cpu_vals):10.4f} | {mean(cfc_vals):10.1f} | {mean(gen_rst_vals):8.2f} | {sum(qre_rst_vals):8d}")

    # 2. Telemetry Breakdown for Active QRE
    active_runs = by_config.get("cfg_active_adaptfix", [])
    if active_runs:
        print("\n" + "=" * 110)
        print("TABLE 2: ACTIVE QRE TELEMETRY BREAKDOWN (cfg_active_adaptfix, 48 runs)")
        print("=" * 110)
        tot_cfc = sum(int(r["conflicts"]) for r in active_runs)
        tot_native_req = sum(int(r["qre_native_requests"]) for r in active_runs)
        tot_raw_sharpe = sum(int(r["qre_raw_sharpe_events"]) for r in active_runs)
        tot_raw_var = sum(int(r["qre_raw_var_events"]) for r in active_runs)
        tot_raw_both = sum(int(r["qre_raw_both_events"]) for r in active_runs)
        tot_sustained = sum(int(r["qre_sustained_events"]) for r in active_runs)
        tot_eligible = sum(int(r["qre_eligible_requests"]) for r in active_runs)
        tot_executed = sum(int(r["qre_executed_restarts"]) for r in active_runs)
        tot_cd_supp = sum(int(r["qre_cooldown_supp"]) for r in active_runs)
        tot_cap_supp = sum(int(r["qre_cap_supp"]) for r in active_runs)
        tot_adapt_rst = sum(int(r["qre_strategy_adapt_rst"]) for r in active_runs)
        tot_genuine_rst = sum(int(r["genuine_restarts"]) for r in active_runs)

        print(f"Total Conflicts Observed         : {tot_cfc:,}")
        print(f"Glucose Native Restart Requests  : {tot_native_req:,}")
        print(f"Raw Sharpe Events (S < -0.35)    : {tot_raw_sharpe:,} ({tot_raw_sharpe/max(1, tot_cfc)*100:.2f}% of conflicts)")
        print(f"Raw VaR Events (VaR95 >= 3.2&med): {tot_raw_var:,} ({tot_raw_var/max(1, tot_cfc)*100:.2f}% of conflicts)")
        print(f"Raw Simultaneous Events (Both)   : {tot_raw_both:,} ({tot_raw_both/max(1, tot_cfc)*100:.2f}% of conflicts)")
        print(f"Sustained Events (>= 8 consec)   : {tot_sustained:,}")
        print(f"Eligible Requests (at Quiescence): {tot_eligible:,}")
        print(f"Cooldown Suppressions (< 500 cfc): {tot_cd_supp:,}")
        print(f"Frequency Cap Suppressions (>5/10k): {tot_cap_supp:,}")
        print(f"Executed QRE Restarts            : {tot_executed:,}")
        print(f"Glucose 100k Adaptation Restarts : {tot_adapt_rst:,}")
        print(f"Total Genuine Restarts (Native+QRE): {tot_genuine_rst:,}")

    # 3. Family-Specific Breakdown
    print("\n" + "=" * 110)
    print("TABLE 3: PERFORMANCE BY BENCHMARK FAMILY (Structured UNSAT vs Random SAT)")
    print("=" * 110)
    families = ["UNSAT_Structured", "SAT_Random", "Trivial"]
    for fam in families:
        print(f"\n--- Family: {fam} ---")
        print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean Cfc':10s} | {'Gen Rst':8s}")
        print("-" * 80)
        for cid in ["cfg01_baseline_base", "cfg05_baseline_adaptfix", "cfg_shadow_adaptfix", "cfg_active_adaptfix"]:
            runs = [r for r in by_config[cid] if r["family_type"] == fam]
            if not runs:
                continue
            n = len(runs)
            solved = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
            par2_vals = [float(r["par2_s"]) for r in runs]
            wall_vals = [float(r["wall_time_s"]) for r in runs]
            cfc_vals = [int(r["conflicts"]) for r in runs]
            rst_vals = [int(r["genuine_restarts"]) for r in runs]
            print(f"{cid:24s} | {solved:2d}/{n:2d}   | {mean(par2_vals):10.4f} | {mean(wall_vals):10.4f} | {mean(cfc_vals):10.1f} | {mean(rst_vals):8.2f}")

    # 4. Instrumentation Overhead Analysis
    # Compare cfg05_baseline_adaptfix (clean) vs cfg_shadow_adaptfix (optimized shadow)
    # on non-trivial instances (wall_time >= 0.05s)
    clean_runs = {f"{r['benchmark_id']}_rep{r['repetition']}": r for r in by_config["cfg05_baseline_adaptfix"]}
    shadow_runs = {f"{r['benchmark_id']}_rep{r['repetition']}": r for r in by_config["cfg_shadow_adaptfix"]}
    active_runs_map = {f"{r['benchmark_id']}_rep{r['repetition']}": r for r in by_config["cfg_active_adaptfix"]}

    print("\n" + "=" * 110)
    print("TABLE 4: INSTRUMENTATION OVERHEAD ON NON-TRIVIAL INSTANCES (Clean Wall >= 0.05s)")
    print("=" * 110)
    print(f"{'Benchmark':28s} | {'Rep':4s} | {'Clean (s)':10s} | {'Shadow (s)':10s} | {'Ovh (%)':8s} | {'Active (s)':10s} | {'Active Ovh':10s}")
    print("-" * 110)

    ovh_list = []
    act_ovh_list = []
    for k, c_rec in sorted(clean_runs.items()):
        s_rec = shadow_runs.get(k)
        a_rec = active_runs_map.get(k)
        if not s_rec or not a_rec:
            continue
        c_wall = float(c_rec["wall_time_s"])
        s_wall = float(s_rec["wall_time_s"])
        a_wall = float(a_rec["wall_time_s"])

        if c_wall >= 0.05:
            ovh = ((s_wall - c_wall) / c_wall) * 100.0
            act_ovh = ((a_wall - c_wall) / c_wall) * 100.0
            ovh_list.append(ovh)
            act_ovh_list.append(act_ovh)
            print(f"{c_rec['benchmark_name']:28s} | rep{c_rec['repetition']:1s} | {c_wall:10.4f} | {s_wall:10.4f} | {ovh:+7.2f}% | {a_wall:10.4f} | {act_ovh:+8.2f}%")

    if ovh_list:
        print("-" * 110)
        print(f"Mean Optimized Shadow Overhead vs Clean Baseline : {mean(ovh_list):+6.2f}% (vs Step 38 shadow: +14.9%)")
        print(f"Mean Active QRE Overhead vs Clean Baseline       : {mean(act_ovh_list):+6.2f}%")

    # 5. Model Verification Check
    sat_runs = [r for r in rows if r["status"] == "SAT"]
    all_models_valid = all(r["model_valid"] == "PASS" for r in sat_runs)
    print(f"\nModel Verification: {len(sat_runs)} SAT runs, All Models Valid: {all_models_valid}")

if __name__ == "__main__":
    main()

