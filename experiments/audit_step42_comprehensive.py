#!/usr/bin/env python3
"""
experiments/audit_step42_comprehensive.py

Comprehensive independent audit script for Step 42:
- Recomputes all Step 41 performance calculations.
- Evaluates PAR-2, solved counts, timeouts, wall time, CPU time, conflicts, decisions, propagations, restarts, reductions, memory.
- Distinguishes:
    1) Overall metrics (all 108 runs)
    2) Completed-solve metrics (solved runs only)
    3) Mutually solved common benchmark set metrics
- Performs benchmark-by-benchmark paired audits:
    A. V3 Drawdown + AdaptFix vs Original Glucose Baseline
    B. Gated QRE + AdaptFix vs Glucose + AdaptFix
    C. Gated QRE + Base vs Original Glucose Baseline
    D. Gated QRE + AdaptFix vs Ungated QRE + AdaptFix
- Audits specific benchmark trajectories:
    gcol_unsat_k10_c9.cnf, php_10p_9h.cnf, rand3sat_n175_c735_s1003.cnf, planted3sat_n200_c852_s2005.cnf
- Reconciles development dataset with Step 37 holdout results.
"""

import os
import sys
import csv
import math
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path(r"D:\DAC_203@Project")
DEV_CSV = WORKSPACE / "experiments" / "results" / "qre_gated_full_development" / "master_results.csv"
HOLDOUT_CSV = WORKSPACE / "experiments" / "results" / "final_holdout" / "master_results.csv"

def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def stddev(vals):
    if len(vals) < 2: return 0.0
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))

def compute_par2(wall_time, timed_out, timeout_cutoff=15.0):
    if timed_out:
        return 2.0 * timeout_cutoff
    return min(wall_time, 2.0 * timeout_cutoff)

def load_data(filepath):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    print("=" * 100)
    print("STEP 42: INDEPENDENT PERFORMANCE AUDIT & VERIFICATION")
    print("=" * 100)
    
    dev_rows = load_data(DEV_CSV)
    print(f"Loaded {len(dev_rows)} development runs from {DEV_CSV.name}")
    
    configs = [
        "cfg01_baseline_base",
        "cfg05_baseline_adaptfix",
        "cfg_active_adaptfix",
        "cfg_gated_base",
        "cfg_gated_adaptfix",
        "cfg_v3dd_adaptfix"
    ]
    
    config_labels = {
        "cfg01_baseline_base": "Original Glucose Baseline",
        "cfg05_baseline_adaptfix": "Glucose + AdaptFix",
        "cfg_active_adaptfix": "Ungated QRE + AdaptFix",
        "cfg_gated_base": "Gated QRE + Baseline",
        "cfg_gated_adaptfix": "Gated QRE + AdaptFix",
        "cfg_v3dd_adaptfix": "V3 Drawdown + AdaptFix"
    }

    # Group by config
    by_config = defaultdict(list)
    for r in dev_rows:
        by_config[r["config_id"]].append(r)
        
    print("\n--- SECTION 1: GLOBAL METRICS INDEPENDENT RECOMPUTATION ---")
    print(f"{'Config ID':24s} | {'Solved':7s} | {'Timeout':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean CPU':10s} | {'Solved Wall':11s} | {'Solved Cfc':10s} | {'Mem MB':7s}")
    print("-" * 115)
    
    stats_all = {}
    stats_solved = {}
    
    for cid in configs:
        runs = by_config[cid]
        n_total = len(runs)
        solved_runs = [r for r in runs if r["status"] in ("SAT", "UNSAT")]
        timeout_runs = [r for r in runs if r["timed_out"] == "True" or r["status"] == "TIMEOUT"]
        
        n_solved = len(solved_runs)
        n_timeout = len(timeout_runs)
        
        # PAR-2 recomputation
        par2_vals = [compute_par2(float(r["wall_time_s"]), r["timed_out"] == "True" or r["status"] == "TIMEOUT", 15.0) for r in runs]
        wall_all = [float(r["wall_time_s"]) for r in runs]
        cpu_all = [float(r["cpu_time_s"]) for r in runs]
        
        wall_solved = [float(r["wall_time_s"]) for r in solved_runs]
        cfc_solved = [int(r["conflicts"]) for r in solved_runs]
        dec_solved = [int(r["decisions"]) for r in solved_runs]
        prop_solved = [int(r["propagations"]) for r in solved_runs]
        
        mem_all = [float(r["memory_mb"]) for r in runs]
        
        # Restarts
        gen_rst = [int(r["genuine_restarts"]) for r in runs]
        if "qre" in cid or "gated" in cid or "active" in cid:
            extra_rst = sum(int(r["qre_executed_restarts"]) for r in runs)
        elif "v3" in cid:
            extra_rst = sum(int(r["v3_executed_restarts"]) for r in runs)
        else:
            extra_rst = 0
            
        stats_all[cid] = {
            "n_total": n_total,
            "n_solved": n_solved,
            "n_timeout": n_timeout,
            "par2": mean(par2_vals),
            "wall_mean": mean(wall_all),
            "cpu_mean": mean(cpu_all),
            "mem_mean": mean(mem_all),
            "gen_rst_mean": mean(gen_rst),
            "extra_rst": extra_rst
        }
        
        stats_solved[cid] = {
            "wall_mean": mean(wall_solved),
            "cfc_mean": mean(cfc_solved),
            "dec_mean": mean(dec_solved),
            "prop_mean": mean(prop_solved),
        }
        
        print(f"{cid:24s} | {n_solved:2d}/{n_total:2d}   | {n_timeout:2d}/{n_total:2d}   | {mean(par2_vals):10.4f} | {mean(wall_all):10.4f} | {mean(cpu_all):10.4f} | {mean(wall_solved):11.4f} | {mean(cfc_solved):10.1f} | {mean(mem_all):6.2f}")
        
    print("\n--- SECTION 2: MUTUALLY SOLVED COMMON BENCHMARK SET ANALYSIS ---")
    # Identify benchmarks solved across ALL 6 configs in all 3 repetitions
    bmk_names = sorted(list(set(r["benchmark_name"] for r in dev_rows)))
    
    # Check per benchmark per config if all 3 reps solved
    bmk_solve_counts = defaultdict(lambda: defaultdict(int))
    for r in dev_rows:
        if r["status"] in ("SAT", "UNSAT"):
            bmk_solve_counts[r["benchmark_name"]][r["config_id"]] += 1
            
    # Universally solved benchmarks (3/3 solved in all 6 configs)
    universal_solved = []
    for b in bmk_names:
        if all(bmk_solve_counts[b][cid] == 3 for cid in configs):
            universal_solved.append(b)
            
    print(f"Total benchmarks: {len(bmk_names)}")
    print(f"Universally 3/3 solved by all 6 configurations: {len(universal_solved)} benchmarks ({len(universal_solved)*3} runs/config)")
    
    print(f"\nMean Conflicts & PAR-2 on Universal Mutually Solved Set ({len(universal_solved)} benchmarks, 3 reps = {len(universal_solved)*3} runs):")
    print(f"{'Config ID':24s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean Conflicts':14s} | {'Mean Decisions':14s} | {'Mean Propagations':17s}")
    print("-" * 105)
    for cid in configs:
        u_runs = [r for r in by_config[cid] if r["benchmark_name"] in universal_solved]
        u_par2 = mean([compute_par2(float(r["wall_time_s"]), False, 15.0) for r in u_runs])
        u_wall = mean([float(r["wall_time_s"]) for r in u_runs])
        u_cfc = mean([int(r["conflicts"]) for r in u_runs])
        u_dec = mean([int(r["decisions"]) for r in u_runs])
        u_prop = mean([int(r["propagations"]) for r in u_runs])
        print(f"{cid:24s} | {u_par2:10.4f} | {u_wall:10.4f} | {u_cfc:14.1f} | {u_dec:14.1f} | {u_prop:17.1f}")

    print("\n" + "=" * 100)
    print("--- SECTION 3: AUDIT OF PAIRED COMPARISONS (BENCHMARK-BY-BENCHMARK) ---")
    print("=" * 100)
    
    def run_paired_audit(cid1, cid2, title):
        print(f"\n=======================================================")
        print(f"PAIRED AUDIT: {title}")
        print(f"Config 1: {cid1} ({config_labels[cid1]})")
        print(f"Config 2: {cid2} ({config_labels[cid2]})")
        print(f"=======================================================")
        
        # Per benchmark aggregation (mean of 3 reps)
        b_data = defaultdict(lambda: {cid1: [], cid2: []})
        for r in dev_rows:
            if r["config_id"] in (cid1, cid2):
                b_data[r["benchmark_name"]][r["config_id"]].append(r)
                
        wins = 0      # Config 1 wins over Config 2
        losses = 0    # Config 1 loses to Config 2
        ties = 0      # Identical search work or universal timeout
        
        par2_diffs = []
        cfc_diffs_mutually_solved = []
        
        print(f"{'Benchmark':34s} | {'Sol1':4s} | {'Sol2':4s} | {'P2_1':8s} | {'P2_2':8s} | {'DiffP2':8s} | {'Cfc_1':10s} | {'Cfc_2':10s} | {'DiffCfc':10s} | {'Verdict':12s}")
        print("-" * 125)
        
        special_focus = ["gcol_unsat_k10_c9.cnf", "php_10p_9h.cnf", "rand3sat_n175_c735_s1003.cnf", "planted3sat_n200_c852_s2005.cnf"]
        
        for b in sorted(bmk_names):
            runs1 = b_data[b][cid1]
            runs2 = b_data[b][cid2]
            
            s1 = sum(1 for r in runs1 if r["status"] in ("SAT", "UNSAT"))
            s2 = sum(1 for r in runs2 if r["status"] in ("SAT", "UNSAT"))
            
            p2_1 = mean([compute_par2(float(r["wall_time_s"]), r["timed_out"] == "True" or r["status"] == "TIMEOUT", 15.0) for r in runs1])
            p2_2 = mean([compute_par2(float(r["wall_time_s"]), r["timed_out"] == "True" or r["status"] == "TIMEOUT", 15.0) for r in runs2])
            diff_p2 = p2_1 - p2_2
            par2_diffs.append(diff_p2)
            
            cfc1 = mean([int(r["conflicts"]) for r in runs1])
            cfc2 = mean([int(r["conflicts"]) for r in runs2])
            diff_cfc = cfc1 - cfc2
            
            # Determine verdict based on solved count first, then conflicts / runtime
            if s1 > s2:
                verdict = f"WIN (+{s1-s2} solve)"
                wins += 1
            elif s1 < s2:
                verdict = f"LOSS (-{s2-s1} solve)"
                losses += 1
            elif s1 == 0 and s2 == 0:
                verdict = "TIE (timeout)"
                ties += 1
            else:
                # Mutually solved
                cfc_diffs_mutually_solved.append(diff_cfc)
                if cfc1 == cfc2:
                    verdict = "TIE (exact)"
                    ties += 1
                elif cfc1 < cfc2:
                    verdict = "WIN (-cfc)"
                    wins += 1
                else:
                    verdict = "LOSS (+cfc)"
                    losses += 1
                    
            highlight = " *** FOCUS ***" if b in special_focus else ""
            print(f"{b:34s} | {s1}/3  | {s2}/3  | {p2_1:8.3f} | {p2_2:8.3f} | {diff_p2:+8.3f} | {cfc1:10.1f} | {cfc2:10.1f} | {diff_cfc:+10.1f} | {verdict:12s}{highlight}")
            
        print("-" * 125)
        print(f"Summary for {cid1} vs {cid2}:")
        print(f"Wins: {wins}, Losses: {losses}, Ties: {ties} (out of {len(bmk_names)})")
        print(f"Mean Paired PAR-2 Diff: {mean(par2_diffs):+.4f}s (negative indicates Config 1 is faster)")
        if cfc_diffs_mutually_solved:
            print(f"Mean Paired Conflict Diff on Mutually Solved ({len(cfc_diffs_mutually_solved)} bmks): {mean(cfc_diffs_mutually_solved):+.1f} cfc")
            
    # A. V3 Drawdown + AdaptFix vs Original Glucose Baseline
    run_paired_audit("cfg_v3dd_adaptfix", "cfg01_baseline_base", "V3 Drawdown+AdaptFix vs Original Glucose Baseline")
    
    # B. Gated QRE + AdaptFix vs Glucose + AdaptFix
    run_paired_audit("cfg_gated_adaptfix", "cfg05_baseline_adaptfix", "Gated QRE+AdaptFix vs Glucose+AdaptFix")
    
    # C. Gated QRE + Baseline vs Original Glucose Baseline
    run_paired_audit("cfg_gated_base", "cfg01_baseline_base", "Gated QRE+Base vs Original Glucose Baseline")
    
    # D. Gated QRE + AdaptFix vs Ungated QRE + AdaptFix
    run_paired_audit("cfg_gated_adaptfix", "cfg_active_adaptfix", "Gated QRE+AdaptFix vs Ungated QRE+AdaptFix")

    print("\n" + "=" * 100)
    print("--- SECTION 4: RECONCILIATION WITH FINAL HOLDOUT FINDINGS ---")
    print("=" * 100)
    
    if os.path.exists(HOLDOUT_CSV):
        holdout_rows = load_data(HOLDOUT_CSV)
        print(f"Loaded {len(holdout_rows)} holdout runs from {HOLDOUT_CSV.name}")
        
        h_by_config = defaultdict(list)
        for r in holdout_rows:
            h_by_config[r["config_id"]].append(r)
            
        print(f"\nHoldout Performance (48 Benchmarks x 3 Reps = 144 Runs/Config, 30s Cutoff, 60s PAR-2 Timeout Penalty):")
        print(f"{'Config ID':24s} | {'Solved':7s} | {'PAR-2 (s)':10s} | {'Mean Wall':10s} | {'Mean Cfc':10s}")
        print("-" * 75)
        for cid in sorted(h_by_config.keys()):
            runs = h_by_config[cid]
            n = len(runs)
            s = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
            # On holdout timeout cutoff was 30s, PAR-2 penalty was 60s
            p2 = [float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 60.0 for r in runs]
            w = [float(r["wall_time_s"]) for r in runs]
            c = [int(r["conflicts"]) for r in runs]
            print(f"{cid:24s} | {s:2d}/{n:2d}   | {mean(p2):10.4f} | {mean(w):10.4f} | {mean(c):10.1f}")
    else:
        print("Holdout results CSV not found.")

if __name__ == "__main__":
    main()

