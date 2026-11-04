#!/usr/bin/env python3
"""
analyze_qre_gated_pilot.py - Step 40: Stagnation-Gated QRE Pilot Analysis

Reads master_results.csv from experiments/results/qre_gated_pilot/
Computes:
  1. Global Performance Summary (5 Configurations, 240 runs total)
  2. Same-Retention Policy Comparisons:
     - Gated QRE + AdaptFix vs Glucose + AdaptFix
     - Gated QRE + Baseline vs Glucose + Baseline
  3. Gated vs Ungated Active QRE Comparison (measuring mitigation of Random SAT regression)
  4. Benchmark Family Breakdown (Structured UNSAT vs Random SAT vs Trivial)
  5. Per-Benchmark Detailed Trajectory Comparison
  6. Gated Telemetry & Suppression Breakdown
"""

import sys
import os
import csv
import math
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "qre_gated_pilot"
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

def main():
    if not MASTER_CSV.exists():
        print(f"ERROR: {MASTER_CSV} does not exist.")
        sys.exit(1)

    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total Rows Loaded: {len(rows)}")

    by_config = defaultdict(list)
    for r in rows:
        by_config[r["config_id"]].append(r)

    config_order = [
        "cfg01_baseline_base",
        "cfg05_baseline_adaptfix",
        "cfg_active_adaptfix",
        "cfg_gated_adaptfix",
        "cfg_gated_base"
    ]

    # 1. Global Performance Summary
    print("\n" + "=" * 115)
    print("TABLE 1: GLOBAL CONFIGURATION SUMMARY (16 Benchmarks x 3 Repetitions = 48 Runs / Config)")
    print("=" * 115)
    print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean CPU':10s} | {'Mean Cfc':10s} | {'Gen Rst':8s} | {'QRE Rst':8s}")
    print("-" * 115)

    summary_stats = {}
    for cid in config_order:
        runs = by_config.get(cid, [])
        if not runs: continue
        n = len(runs)
        solved = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
        par2_vals = [float(r["par2_s"]) for r in runs]
        wall_vals = [float(r["wall_time_s"]) for r in runs]
        cpu_vals = [float(r["cpu_time_s"]) for r in runs]
        cfc_vals = [int(r["conflicts"]) for r in runs]
        gen_rst_vals = [int(r["genuine_restarts"]) for r in runs]
        qre_rst_vals = [int(r["qre_executed_restarts"]) for r in runs]

        summary_stats[cid] = {
            "solved": solved, "total": n,
            "par2": mean(par2_vals),
            "wall": mean(wall_vals),
            "cpu": mean(cpu_vals),
            "cfc": mean(cfc_vals),
            "gen_rst": mean(gen_rst_vals),
            "qre_rst": sum(qre_rst_vals)
        }
        print(f"{cid:24s} | {solved:2d}/{n:2d}   | {mean(par2_vals):10.4f} | {mean(wall_vals):10.4f} | {mean(cpu_vals):10.4f} | {mean(cfc_vals):10.1f} | {mean(gen_rst_vals):8.2f} | {sum(qre_rst_vals):8d}")

    # 2. Same-Retention Policy Comparisons
    print("\n" + "=" * 115)
    print("TABLE 2: SAME-RETENTION POLICY COMPARISONS (Ablations against Identical Clause Retention)")
    print("=" * 115)
    # Comparison 1: Gated AdaptFix vs Baseline AdaptFix
    if "cfg_gated_adaptfix" in summary_stats and "cfg05_baseline_adaptfix" in summary_stats:
        g_af = summary_stats["cfg_gated_adaptfix"]
        b_af = summary_stats["cfg05_baseline_adaptfix"]
        delta_p2 = ((g_af["par2"] - b_af["par2"]) / b_af["par2"]) * 100.0
        delta_cfc = ((g_af["cfc"] - b_af["cfc"]) / b_af["cfc"]) * 100.0
        print(f"1. Gated QRE + AdaptFix vs Glucose + AdaptFix:")
        print(f"   PAR-2     : {b_af['par2']:.4f}s -> {g_af['par2']:.4f}s ({delta_p2:+.2f}%)")
        print(f"   Conflicts : {b_af['cfc']:.1f} -> {g_af['cfc']:.1f} ({delta_cfc:+.2f}%)")
        print(f"   QRE Restarts Executed: {g_af['qre_rst']}")

    # Comparison 2: Gated Base vs Baseline Base
    if "cfg_gated_base" in summary_stats and "cfg01_baseline_base" in summary_stats:
        g_b = summary_stats["cfg_gated_base"]
        b_b = summary_stats["cfg01_baseline_base"]
        delta_p2 = ((g_b["par2"] - b_b["par2"]) / b_b["par2"]) * 100.0
        delta_cfc = ((g_b["cfc"] - b_b["cfc"]) / b_b["cfc"]) * 100.0
        print(f"\n2. Gated QRE + Baseline vs Glucose + Baseline:")
        print(f"   PAR-2     : {b_b['par2']:.4f}s -> {g_b['par2']:.4f}s ({delta_p2:+.2f}%)")
        print(f"   Conflicts : {b_b['cfc']:.1f} -> {g_b['cfc']:.1f} ({delta_cfc:+.2f}%)")
        print(f"   QRE Restarts Executed: {g_b['qre_rst']}")

    # Comparison 3: Gated AdaptFix vs Ungated Active QRE AdaptFix
    if "cfg_gated_adaptfix" in summary_stats and "cfg_active_adaptfix" in summary_stats:
        g_af = summary_stats["cfg_gated_adaptfix"]
        a_af = summary_stats["cfg_active_adaptfix"]
        delta_p2 = ((g_af["par2"] - a_af["par2"]) / a_af["par2"]) * 100.0
        delta_cfc = ((g_af["cfc"] - a_af["cfc"]) / a_af["cfc"]) * 100.0
        print(f"\n3. Gated QRE + AdaptFix vs Ungated Active QRE + AdaptFix:")
        print(f"   PAR-2     : {a_af['par2']:.4f}s -> {g_af['par2']:.4f}s ({delta_p2:+.2f}%)")
        print(f"   Conflicts : {a_af['cfc']:.1f} -> {g_af['cfc']:.1f} ({delta_cfc:+.2f}%)")
        print(f"   QRE Restarts Reduced: {a_af['qre_rst']} -> {g_af['qre_rst']} ({g_af['qre_rst'] - a_af['qre_rst']:+d})")

    # 3. Benchmark Family Breakdown
    print("\n" + "=" * 115)
    print("TABLE 3: PERFORMANCE BY BENCHMARK FAMILY (Structured UNSAT vs Random SAT vs Trivial)")
    print("=" * 115)
    for fam in ["UNSAT_Structured", "SAT_Random", "Trivial"]:
        print(f"\n--- Family: {fam} ---")
        print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean Cfc':10s} | {'Gen Rst':8s} | {'QRE Rst':8s}")
        print("-" * 100)
        for cid in config_order:
            runs = [r for r in by_config[cid] if r["family_type"] == fam]
            if not runs: continue
            n = len(runs)
            solved = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
            par2_vals = [float(r["par2_s"]) for r in runs]
            wall_vals = [float(r["wall_time_s"]) for r in runs]
            cfc_vals = [int(r["conflicts"]) for r in runs]
            gen_rst_vals = [int(r["genuine_restarts"]) for r in runs]
            qre_rst_vals = [int(r["qre_executed_restarts"]) for r in runs]
            print(f"{cid:24s} | {solved:2d}/{n:2d}   | {mean(par2_vals):10.4f} | {mean(wall_vals):10.4f} | {mean(cfc_vals):10.1f} | {mean(gen_rst_vals):8.2f} | {sum(qre_rst_vals):8d}")

    # 4. Telemetry Breakdown for Gated Configurations
    for cid in ["cfg_gated_adaptfix", "cfg_gated_base"]:
        runs = by_config.get(cid, [])
        if not runs: continue
        print("\n" + "=" * 115)
        print(f"TABLE 4: TELEMETRY & SUPPRESSION BREAKDOWN ({cid}, 48 runs)")
        print("=" * 115)
        tot_cfc = sum(int(r["conflicts"]) for r in runs)
        tot_native = sum(int(r["qre_native_requests"]) for r in runs)
        tot_sharpe = sum(int(r["qre_raw_sharpe_events"]) for r in runs)
        tot_var = sum(int(r["qre_raw_var_events"]) for r in runs)
        tot_both = sum(int(r["qre_raw_both_events"]) for r in runs)
        tot_sustained = sum(int(r["qre_sustained_events"]) for r in runs)
        tot_eligible = sum(int(r["qre_eligible_requests"]) for r in runs)
        tot_executed = sum(int(r["qre_executed_restarts"]) for r in runs)
        tot_cd_supp = sum(int(r["qre_cooldown_supp"]) for r in runs)
        tot_cap_supp = sum(int(r["qre_cap_supp"]) for r in runs)

        print(f"Total Conflicts Observed             : {tot_cfc:,}")
        print(f"Glucose Native Restart Requests      : {tot_native:,}")
        print(f"Raw Sharpe Events (S < -0.35)        : {tot_sharpe:,} ({tot_sharpe/max(1, tot_cfc)*100:.2f}%)")
        print(f"Raw VaR Events (VaR95 >= 3.2&med)    : {tot_var:,} ({tot_var/max(1, tot_cfc)*100:.2f}%)")
        print(f"Raw Simultaneous Events (Both)       : {tot_both:,} ({tot_both/max(1, tot_cfc)*100:.2f}%)")
        print(f"Sustained Events (>= 8 consec)       : {tot_sustained:,}")
        print(f"Stagnation Gate Suppressions (<1500) : {tot_cd_supp:,}")
        print(f"Frequency Budget Suppressions (>2/10k): {tot_cap_supp:,}")
        print(f"Eligible Requests Reaching Budget    : {tot_eligible:,}")
        print(f"Executed Extra QRE Restarts          : {tot_executed:,}")

    # 5. Per-Benchmark Comparison Table (cfg05 vs cfg_active vs cfg_gated_adaptfix)
    print("\n" + "=" * 115)
    print("TABLE 5: PER-BENCHMARK TRAJECTORY COMPARISON (Adaptive-Fixed Retention Variants)")
    print("=" * 115)
    bmk_groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        bmk_groups[f"{r['benchmark_id']} {r['benchmark_name']}"][r["config_id"]].append(r)

    print(f"{'Benchmark':32s} | {'Status':6s} | {'AdaptFix Cfc':12s} | {'Active Cfc':12s} | {'Gated Cfc':12s} | {'Act QRE':7s} | {'Gat QRE':7s}")
    print("-" * 115)
    for bname, cdata in sorted(bmk_groups.items()):
        status = cdata["cfg05_baseline_adaptfix"][0]["status"]
        af_cfc = mean([int(x["conflicts"]) for x in cdata["cfg05_baseline_adaptfix"]])
        act_cfc = mean([int(x["conflicts"]) for x in cdata["cfg_active_adaptfix"]])
        gat_cfc = mean([int(x["conflicts"]) for x in cdata["cfg_gated_adaptfix"]])
        act_qre = sum(int(x["qre_executed_restarts"]) for x in cdata["cfg_active_adaptfix"])
        gat_qre = sum(int(x["qre_executed_restarts"]) for x in cdata["cfg_gated_adaptfix"])
        print(f"{bname:32s} | {status:6s} | {af_cfc:12.1f} | {act_cfc:12.1f} | {gat_cfc:12.1f} | {act_qre:7d} | {gat_qre:7d}")

    # 6. Model Verification Check
    sat_runs = [r for r in rows if r["status"] == "SAT"]
    all_models_valid = all(r["model_valid"] == "PASS" for r in sat_runs)
    print(f"\nModel Verification: {len(sat_runs)} SAT runs, All Models Valid: {all_models_valid}")

if __name__ == "__main__":
    main()

