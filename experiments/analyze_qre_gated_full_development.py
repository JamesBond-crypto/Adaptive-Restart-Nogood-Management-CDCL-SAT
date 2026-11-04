#!/usr/bin/env python3
"""
analyze_qre_gated_full_development.py - Statistical and Algorithmic Analysis of Step 41

Analyzes the full 36-benchmark x 6-configuration x 3-repetition (648 runs) evaluation.
Outputs comprehensive markdown and terminal tables for:
  1. Global 6-Configuration Performance
  2. Family-Level Disaggregation (Random 3-SAT, Planted SAT, PHP, Graph Coloring)
  3. Paired Comparisons against identical-retention baselines
  4. Per-Benchmark Detailed Trajectory Analysis (Wins, Losses, Ties)
  5. Telemetry & Stagnation Gating Dynamics
"""

import sys
import os
import csv
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "qre_gated_full_development"
MASTER_CSV = RESULTS_DIR / "master_results.csv"

def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def median(vals):
    if not vals: return 0.0
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0

def stddev(vals):
    if len(vals) < 2: return 0.0
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))

def main():
    if not MASTER_CSV.is_file():
        print(f"ERROR: Results file not found: {MASTER_CSV}")
        sys.exit(1)

    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Total Rows Loaded: {len(rows)}")

    by_config = defaultdict(list)
    for r in rows:
        by_config[r["config_id"]].append(r)

    config_order = [
        "cfg01_baseline_base",
        "cfg05_baseline_adaptfix",
        "cfg_active_adaptfix",
        "cfg_gated_base",
        "cfg_gated_adaptfix",
        "cfg_v3dd_adaptfix"
    ]

    config_names = {
        "cfg01_baseline_base": "Original Glucose + Base Reduction",
        "cfg05_baseline_adaptfix": "Original Glucose + AdaptFix",
        "cfg_active_adaptfix": "Ungated Active QRE + AdaptFix",
        "cfg_gated_base": "Gated QRE + Base Reduction",
        "cfg_gated_adaptfix": "Gated QRE + AdaptFix",
        "cfg_v3dd_adaptfix": "V3 Drawdown + AdaptFix"
    }

    # 1. Global Performance Summary
    print("\n" + "=" * 120)
    print("TABLE 1: GLOBAL CONFIGURATION SUMMARY (36 Benchmarks x 3 Reps = 108 Runs / Config, 648 Runs Total)")
    print("=" * 120)
    print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean CPU':10s} | {'Mean Cfc':10s} | {'Gen Rst':8s} | {'Extra Rst':9s}")
    print("-" * 120)

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

        extra_rst = 0
        if "qre" in cid or "gated" in cid or "active" in cid:
            extra_rst = sum(int(r["qre_executed_restarts"]) for r in runs)
        elif "v3" in cid:
            extra_rst = sum(int(r["v3_executed_restarts"]) for r in runs)

        summary_stats[cid] = {
            "solved": solved, "total": n,
            "par2": mean(par2_vals),
            "wall": mean(wall_vals),
            "cpu": mean(cpu_vals),
            "cfc": mean(cfc_vals),
            "gen_rst": mean(gen_rst_vals),
            "extra_rst": extra_rst
        }
        print(f"{cid:24s} | {solved:2d}/{n:2d}   | {mean(par2_vals):10.4f} | {mean(wall_vals):10.4f} | {mean(cpu_vals):10.4f} | {mean(cfc_vals):10.1f} | {mean(gen_rst_vals):8.2f} | {extra_rst:9d}")

    # 2. Same-Retention Policy Comparisons
    print("\n" + "=" * 120)
    print("TABLE 2: CONTROLLED SAME-RETENTION POLICY ABLATIONS")
    print("=" * 120)
    if "cfg_gated_adaptfix" in summary_stats and "cfg05_baseline_adaptfix" in summary_stats:
        g = summary_stats["cfg_gated_adaptfix"]
        b = summary_stats["cfg05_baseline_adaptfix"]
        d_p2 = ((g["par2"] - b["par2"]) / b["par2"]) * 100.0
        d_cfc = ((g["cfc"] - b["cfc"]) / b["cfc"]) * 100.0
        print(f"1. Gated QRE + AdaptFix vs Glucose + AdaptFix (Direct Algorithmic Innovation):")
        print(f"   PAR-2     : {b['par2']:.4f}s -> {g['par2']:.4f}s ({d_p2:+.2f}%)")
        print(f"   Conflicts : {b['cfc']:.1f} -> {g['cfc']:.1f} ({d_cfc:+.2f}%)")
        print(f"   Extra QRE Restarts: {g['extra_rst']}")

    if "cfg_gated_base" in summary_stats and "cfg01_baseline_base" in summary_stats:
        g = summary_stats["cfg_gated_base"]
        b = summary_stats["cfg01_baseline_base"]
        d_p2 = ((g["par2"] - b["par2"]) / b["par2"]) * 100.0
        d_cfc = ((g["cfc"] - b["cfc"]) / b["cfc"]) * 100.0
        print(f"\n2. Gated QRE + Base Reduction vs Glucose + Base Reduction:")
        print(f"   PAR-2     : {b['par2']:.4f}s -> {g['par2']:.4f}s ({d_p2:+.2f}%)")
        print(f"   Conflicts : {b['cfc']:.1f} -> {g['cfc']:.1f} ({d_cfc:+.2f}%)")
        print(f"   Extra QRE Restarts: {g['extra_rst']}")

    if "cfg_gated_adaptfix" in summary_stats and "cfg_active_adaptfix" in summary_stats:
        g = summary_stats["cfg_gated_adaptfix"]
        a = summary_stats["cfg_active_adaptfix"]
        d_p2 = ((g["par2"] - a["par2"]) / a["par2"]) * 100.0
        d_cfc = ((g["cfc"] - a["cfc"]) / a["cfc"]) * 100.0
        print(f"\n3. Gated QRE + AdaptFix vs Ungated Active QRE + AdaptFix (Gate Mitigation Effect):")
        print(f"   PAR-2     : {a['par2']:.4f}s -> {g['par2']:.4f}s ({d_p2:+.2f}%)")
        print(f"   Conflicts : {a['cfc']:.1f} -> {g['cfc']:.1f} ({d_cfc:+.2f}%)")
        print(f"   Extra Restarts Reduced: {a['extra_rst']} -> {g['extra_rst']} ({g['extra_rst'] - a['extra_rst']:+d})")

    if "cfg_gated_adaptfix" in summary_stats and "cfg_v3dd_adaptfix" in summary_stats:
        g = summary_stats["cfg_gated_adaptfix"]
        v = summary_stats["cfg_v3dd_adaptfix"]
        d_p2 = ((g["par2"] - v["par2"]) / v["par2"]) * 100.0
        d_cfc = ((g["cfc"] - v["cfc"]) / v["cfc"]) * 100.0
        print(f"\n4. Gated QRE + AdaptFix vs V3 Drawdown-Only + AdaptFix:")
        print(f"   PAR-2     : {v['par2']:.4f}s -> {g['par2']:.4f}s ({d_p2:+.2f}%)")
        print(f"   Conflicts : {v['cfc']:.1f} -> {g['cfc']:.1f} ({d_cfc:+.2f}%)")

    # 3. Family-Level Breakdown
    families = sorted(list(set(r["family"] for r in rows)))
    print("\n" + "=" * 120)
    print("TABLE 3: PERFORMANCE BY BENCHMARK FAMILY")
    print("=" * 120)
    for fam in families:
        print(f"\n--- Benchmark Family: {fam} ---")
        print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean Cfc':10s} | {'Gen Rst':8s} | {'Extra Rst':9s}")
        print("-" * 105)
        for cid in config_order:
            runs = [r for r in by_config[cid] if r["family"] == fam]
            if not runs: continue
            n = len(runs)
            solved = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
            par2_vals = [float(r["par2_s"]) for r in runs]
            wall_vals = [float(r["wall_time_s"]) for r in runs]
            cfc_vals = [int(r["conflicts"]) for r in runs]
            gen_rst_vals = [int(r["genuine_restarts"]) for r in runs]
            extra_rst = sum(int(r["qre_executed_restarts"]) for r in runs) if ("qre" in cid or "gated" in cid or "active" in cid) else sum(int(r["v3_executed_restarts"]) for r in runs) if "v3" in cid else 0
            print(f"{cid:24s} | {solved:2d}/{n:2d}   | {mean(par2_vals):10.4f} | {mean(wall_vals):10.4f} | {mean(cfc_vals):10.1f} | {mean(gen_rst_vals):8.2f} | {extra_rst:9d}")

    # 4. Per-Benchmark Analysis & Paired Statistics (cfg05 vs cfg_gated_adaptfix)
    print("\n" + "=" * 120)
    print("TABLE 4: PER-BENCHMARK PAIRED ANALYSIS (Original Glucose+AdaptFix vs Gated QRE+AdaptFix)")
    print("=" * 120)
    bmk_groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        bmk_groups[r["benchmark_name"]][r["config_id"]].append(r)

    wins = 0
    losses = 0
    ties = 0

    print(f"{'Benchmark':34s} | {'Base Cfc':10s} | {'Gated Cfc':10s} | {'Diff Cfc':10s} | {'Base Wall':10s} | {'Gated Wall':10s} | {'QRE Rst':7s} | {'Verdict':8s}")
    print("-" * 120)

    for bname, cdata in sorted(bmk_groups.items()):
        b_runs = cdata.get("cfg05_baseline_adaptfix", [])
        g_runs = cdata.get("cfg_gated_adaptfix", [])
        if not b_runs or not g_runs: continue

        b_cfc = mean([int(x["conflicts"]) for x in b_runs])
        g_cfc = mean([int(x["conflicts"]) for x in g_runs])
        b_wall = mean([float(x["wall_time_s"]) for x in b_runs])
        g_wall = mean([float(x["wall_time_s"]) for x in g_runs])
        qre_rst = sum(int(x["qre_executed_restarts"]) for x in g_runs)

        diff_cfc = g_cfc - b_cfc
        diff_wall = g_wall - b_wall

        if b_cfc == g_cfc:
            verdict = "TIE (Identical)"
            ties += 1
        elif g_cfc < b_cfc:
            verdict = "WIN (Fewer Cfc)"
            wins += 1
        else:
            verdict = "LOSS (More Cfc)"
            losses += 1

        print(f"{bname:34s} | {b_cfc:10.1f} | {g_cfc:10.1f} | {diff_cfc:+10.1f} | {b_wall:10.4f} | {g_wall:10.4f} | {qre_rst:7d} | {verdict:8s}")

    print("-" * 120)
    print(f"Paired Benchmark Outcomes (Search Work): {wins} Wins, {losses} Losses, {ties} Ties (Total {len(bmk_groups)})")

    # 5. Model Verification Check
    sat_runs = [r for r in rows if r["status"] == "SAT"]
    all_models_valid = all(r["model_valid"] == "PASS" for r in sat_runs)
    print(f"\nModel Verification: {len(sat_runs)} SAT runs, All Models Valid: {all_models_valid}")

if __name__ == "__main__":
    main()

