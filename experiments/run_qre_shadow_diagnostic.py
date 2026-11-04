#!/usr/bin/env python3
"""
run_qre_shadow_diagnostic.py - Diagnostic Evaluation of QRE Shadow Telemetry
Step 38: Quantitative Risk Engine Feasibility and Shadow Implementation

Runs a 16-benchmark development-only diagnostic suite comparing:
  - Inactive / trivial vs difficult instances.
  - Signal activation rates: Sharpe vs VaR vs V3 Drawdown.
  - Overlap between Sharpe and VaR.
  - Cooldown and startup suppression dynamics.
  - CPU runtime overhead of telemetry instrumentation.
"""

import os
import sys
import subprocess
import time
import re
import csv
import json

SOLVER_BIN = os.path.join("src", "glucose_windows", "glucose-qre-shadow.exe")
RESULTS_DIR = os.path.join("experiments", "results", "qre_shadow")
os.makedirs(RESULTS_DIR, exist_ok=True)

DIAGNOSTIC_BENCHMARKS = [
    # 1. Trivial / Root Simplification Instances (< 10 conflicts)
    {"id": "DEV_01", "name": "test_sat.cnf", "path": "benchmarks/smoke_test/test_sat.cnf", "category": "Trivial"},
    {"id": "DEV_02", "name": "test_unsat.cnf", "path": "benchmarks/smoke_test/test_unsat.cnf", "category": "Trivial"},
    {"id": "DEV_03", "name": "planted3sat_n60_c256_s501.cnf", "path": "benchmarks/pilot/planted3sat_n60_c256_s501.cnf", "category": "Trivial"},
    {"id": "DEV_04", "name": "gcol_sat_n30_k3_m90_s3001.cnf", "path": "benchmarks/expanded/gcol_sat_n30_k3_m90_s3001.cnf", "category": "Trivial"},

    # 2. Medium Instances (10 to 500 conflicts)
    {"id": "DEV_05", "name": "rand3sat_n50_c213_s101.cnf", "path": "benchmarks/pilot/rand3sat_n50_c213_s101.cnf", "category": "Medium_Random"},
    {"id": "DEV_06", "name": "rand3sat_n75_c320_s201.cnf", "path": "benchmarks/pilot/rand3sat_n75_c320_s201.cnf", "category": "Medium_Random"},
    {"id": "DEV_07", "name": "php_6p_5h.cnf", "path": "benchmarks/pilot/php_6p_5h.cnf", "category": "Medium_Pigeonhole"},
    {"id": "DEV_08", "name": "gcol_unsat_grotzsch_k3.cnf", "path": "benchmarks/expanded/gcol_unsat_grotzsch_k3.cnf", "category": "Medium_GraphColoring"},

    # 3. Hard Structured UNSAT (> 500 conflicts)
    {"id": "DEV_09", "name": "php_7p_6h.cnf", "path": "benchmarks/pilot/php_7p_6h.cnf", "category": "Hard_Pigeonhole"},
    {"id": "DEV_10", "name": "php_8p_7h.cnf", "path": "benchmarks/pilot/php_8p_7h.cnf", "category": "Hard_Pigeonhole"},
    {"id": "DEV_11", "name": "php_9p_7h.cnf", "path": "benchmarks/expanded/php_9p_7h.cnf", "category": "Hard_Pigeonhole"},
    {"id": "DEV_12", "name": "php_10p_8h.cnf", "path": "benchmarks/expanded/php_10p_8h.cnf", "category": "Hard_Pigeonhole"},

    # 4. Hard Random Phase-Transition 3-SAT (> 500 conflicts)
    {"id": "DEV_13", "name": "rand3sat_n100_c426_s301.cnf", "path": "benchmarks/pilot/rand3sat_n100_c426_s301.cnf", "category": "Hard_Random"},
    {"id": "DEV_14", "name": "rand3sat_n125_c532_s401.cnf", "path": "benchmarks/pilot/rand3sat_n125_c532_s401.cnf", "category": "Hard_Random"},
    {"id": "DEV_15", "name": "rand3sat_n150_c639_s1001.cnf", "path": "benchmarks/expanded/rand3sat_n150_c639_s1001.cnf", "category": "Hard_Random"},
    {"id": "DEV_16", "name": "rand3sat_n175_c735_s1003.cnf", "path": "benchmarks/expanded/rand3sat_n175_c735_s1003.cnf", "category": "Hard_Random"}
]

def run_solver(cmd):
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t1 = time.perf_counter()
    wall_time = t1 - t0

    out = proc.stdout
    metrics = {
        "status": "UNKNOWN",
        "wall_time_s": round(wall_time, 4),
        "cpu_time_s": 0.0,
        "conflicts": 0,
        "decisions": 0,
        "propagations": 0,
        "restarts": 0,
        "genuine_restarts": 0,
        "reduce_db": 0,
        # QRE metrics
        "qre_dec_obs": 0,
        "qre_cfc_obs": 0,
        "qre_total_shocks": 0,
        "qre_raw_sharpe": 0,
        "qre_raw_var": 0,
        "qre_raw_both": 0,
        "qre_supp_sharpe_start": 0,
        "qre_supp_var_start": 0,
        "qre_supp_sharpe_cd": 0,
        "qre_supp_var_cd": 0,
        "qre_elig_sharpe": 0,
        "qre_elig_var": 0,
        "qre_elig_either": 0,
        "qre_elig_both": 0,
        "qre_min_sharpe": 0.0,
        "qre_max_var95": 0.0,
        "qre_final_sharpe": 0.0,
        "qre_final_var95": 0.0,
        "qre_final_median_shock": 0.0,
        "qre_final_cmin": 14,
        # V3 Shadow metrics
        "v3_hyp_events_total": 0,
        "v3_hyp_events_drawdown": 0,
        "v3_hyp_events_trend": 0,
        "v3_hyp_events_ceiling": 0,
        "v3_max_drawdown": 0.0
    }

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("s "):
            metrics["status"] = line.split()[1]
        elif line.startswith("c CPU time"):
            m = re.search(r"c CPU time\s*:\s*([0-9\.]+)", line)
            if m: metrics["cpu_time_s"] = float(m.group(1))
        elif line.startswith("c conflicts"):
            m = re.search(r"c conflicts\s*:\s*(\d+)", line)
            if m: metrics["conflicts"] = int(m.group(1))
        elif line.startswith("c decisions"):
            m = re.search(r"c decisions\s*:\s*(\d+)", line)
            if m: metrics["decisions"] = int(m.group(1))
        elif line.startswith("c propagations"):
            m = re.search(r"c propagations\s*:\s*(\d+)", line)
            if m: metrics["propagations"] = int(m.group(1))
        elif line.startswith("c restarts"):
            m = re.search(r"c restarts\s*:\s*(\d+)", line)
            if m: metrics["restarts"] = int(m.group(1))
        elif line.startswith("c genuine restarts"):
            m = re.search(r"c genuine restarts\s*:\s*(\d+)", line)
            if m: metrics["genuine_restarts"] = int(m.group(1))
        elif line.startswith("c nb ReduceDB"):
            m = re.search(r"c nb ReduceDB\s*:\s*(\d+)", line)
            if m: metrics["reduce_db"] = int(m.group(1))
        # QRE parsed fields
        elif "qre decisions obs" in line:
            metrics["qre_dec_obs"] = int(line.split(":")[-1].strip())
        elif "qre conflicts obs" in line:
            metrics["qre_cfc_obs"] = int(line.split(":")[-1].strip())
        elif "qre total shocks" in line:
            metrics["qre_total_shocks"] = int(line.split(":")[-1].strip())
        elif "qre raw sharpe trig" in line:
            metrics["qre_raw_sharpe"] = int(line.split(":")[-1].strip())
        elif "qre raw var trig" in line:
            metrics["qre_raw_var"] = int(line.split(":")[-1].strip())
        elif "qre raw both trig" in line:
            metrics["qre_raw_both"] = int(line.split(":")[-1].strip())
        elif "qre supp sharpe start" in line:
            metrics["qre_supp_sharpe_start"] = int(line.split(":")[-1].strip())
        elif "qre supp var start" in line:
            metrics["qre_supp_var_start"] = int(line.split(":")[-1].strip())
        elif "qre supp sharpe cd" in line:
            metrics["qre_supp_sharpe_cd"] = int(line.split(":")[-1].strip())
        elif "qre supp var cd" in line:
            metrics["qre_supp_var_cd"] = int(line.split(":")[-1].strip())
        elif "qre elig sharpe req" in line:
            metrics["qre_elig_sharpe"] = int(line.split(":")[-1].strip())
        elif "qre elig var req" in line:
            metrics["qre_elig_var"] = int(line.split(":")[-1].strip())
        elif "qre elig either req" in line:
            metrics["qre_elig_either"] = int(line.split(":")[-1].strip())
        elif "qre elig both req" in line:
            metrics["qre_elig_both"] = int(line.split(":")[-1].strip())
        elif "qre min sharpe obs" in line:
            metrics["qre_min_sharpe"] = float(line.split(":")[-1].strip())
        elif "qre max var95 obs" in line:
            metrics["qre_max_var95"] = float(line.split(":")[-1].strip())
        elif "qre final sharpe" in line:
            metrics["qre_final_sharpe"] = float(line.split(":")[-1].strip())
        elif "qre final var95" in line:
            metrics["qre_final_var95"] = float(line.split(":")[-1].strip())
        elif "qre final median shock" in line:
            metrics["qre_final_median_shock"] = float(line.split(":")[-1].strip())
        elif "qre final cmin" in line:
            metrics["qre_final_cmin"] = int(line.split(":")[-1].strip())
        # V3 Shadow parsed fields
        elif "v3 shadow max drawdown" in line:
            metrics["v3_max_drawdown"] = float(line.split(":")[-1].strip())
        elif "v3 hyp event total" in line:
            metrics["v3_hyp_events_total"] = int(line.split(":")[-1].strip())
        elif "v3 hyp event drawdown" in line:
            metrics["v3_hyp_events_drawdown"] = int(line.split(":")[-1].strip())
        elif "v3 hyp event trend" in line:
            metrics["v3_hyp_events_trend"] = int(line.split(":")[-1].strip())
        elif "v3 hyp event ceiling" in line:
            metrics["v3_hyp_events_ceiling"] = int(line.split(":")[-1].strip())

    return metrics

def main():
    print("=" * 80)
    print("STEP 38: QUANTITATIVE RISK ENGINE (QRE) DIAGNOSTIC EXPERIMENT")
    print("=" * 80)
    print(f"Solver Binary : {SOLVER_BIN}")
    print(f"Benchmarks    : {len(DIAGNOSTIC_BENCHMARKS)} instances (Pilot & Expanded Development Suites)")
    print("Objective     : Evaluate Sharpe & VaR trigger rates, suppression, and overhead\n")

    results = []

    print(f"{'ID':6s} | {'Benchmark':30s} | {'Cat':15s} | {'Cfc':6s} | {'Shk':6s} | {'RawShp':6s} | {'RawVaR':6s} | {'ElgShp':6s} | {'ElgVaR':6s} | {'ElgBoth':7s} | {'V3_Hyp':6s} | {'Wall(s)':7s}")
    print("-" * 125)

    for item in DIAGNOSTIC_BENCHMARKS:
        bid = item["id"]
        bname = item["name"]
        bpath = item["path"]
        bcat = item["category"]

        if not os.path.exists(bpath):
            print(f"Missing file: {bpath}")
            continue

        # Run with both -qre-shadow and -v3-shadow enabled on baseline restart strategy
        cmd_shadow = [SOLVER_BIN, "-qre-shadow", "-v3-shadow", bpath]
        m_shadow = run_solver(cmd_shadow)

        # Run baseline without shadow for overhead measurement
        cmd_clean = [SOLVER_BIN, bpath]
        m_clean = run_solver(cmd_clean)

        overhead_pct = 0.0
        if m_clean["wall_time_s"] > 0.005:
            overhead_pct = ((m_shadow["wall_time_s"] - m_clean["wall_time_s"]) / m_clean["wall_time_s"]) * 100.0

        row = {
            "id": bid,
            "benchmark": bname,
            "category": bcat,
            "path": bpath,
            "status": m_shadow["status"],
            "conflicts": m_shadow["conflicts"],
            "decisions": m_shadow["decisions"],
            "shocks_observed": m_shadow["qre_total_shocks"],
            "raw_sharpe": m_shadow["qre_raw_sharpe"],
            "raw_var": m_shadow["qre_raw_var"],
            "raw_both": m_shadow["qre_raw_both"],
            "supp_sharpe_startup": m_shadow["qre_supp_sharpe_start"],
            "supp_var_startup": m_shadow["qre_supp_var_start"],
            "supp_sharpe_cd": m_shadow["qre_supp_sharpe_cd"],
            "supp_var_cd": m_shadow["qre_supp_var_cd"],
            "eligible_sharpe": m_shadow["qre_elig_sharpe"],
            "eligible_var": m_shadow["qre_elig_var"],
            "eligible_either": m_shadow["qre_elig_either"],
            "eligible_both": m_shadow["qre_elig_both"],
            "min_sharpe": m_shadow["qre_min_sharpe"],
            "max_var95": m_shadow["qre_max_var95"],
            "final_cmin": m_shadow["qre_final_cmin"],
            "v3_hyp_events_total": m_shadow["v3_hyp_events_total"],
            "v3_hyp_events_drawdown": m_shadow["v3_hyp_events_drawdown"],
            "v3_max_drawdown": m_shadow["v3_max_drawdown"],
            "clean_wall_time_s": m_clean["wall_time_s"],
            "shadow_wall_time_s": m_shadow["wall_time_s"],
            "overhead_pct": round(overhead_pct, 2)
        }
        results.append(row)

        print(f"{bid:6s} | {bname:30s} | {bcat:15s} | {row['conflicts']:6d} | {row['shocks_observed']:6d} | {row['raw_sharpe']:6d} | {row['raw_var']:6d} | {row['eligible_sharpe']:6d} | {row['eligible_var']:6d} | {row['eligible_both']:7d} | {row['v3_hyp_events_total']:6d} | {row['shadow_wall_time_s']:7.4f}")

    # Save to CSV
    csv_path = os.path.join(RESULTS_DIR, "qre_diagnostic_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[+] Wrote diagnostic summary CSV: {csv_path}")

    # Summary analysis
    tot_cfc = sum(r["conflicts"] for r in results)
    tot_raw_s = sum(r["raw_sharpe"] for r in results)
    tot_raw_v = sum(r["raw_var"] for r in results)
    tot_elg_s = sum(r["eligible_sharpe"] for r in results)
    tot_elg_v = sum(r["eligible_var"] for r in results)
    tot_elg_either = sum(r["eligible_either"] for r in results)
    tot_elg_both = sum(r["eligible_both"] for r in results)
    tot_v3_hyp = sum(r["v3_hyp_events_total"] for r in results)

    print("\n" + "=" * 80)
    print("KEY DIAGNOSTIC FINDINGS:")
    print("=" * 80)
    print(f"Total Conflicts across Suite      : {tot_cfc:,}")
    print(f"Raw Sharpe Triggers (S < -0.35)   : {tot_raw_s:,} ({tot_raw_s/tot_cfc*100:.1f}% of conflicts)")
    print(f"Raw VaR Triggers (VaR95 >= 3.2)   : {tot_raw_v:,} ({tot_raw_v/tot_cfc*100:.1f}% of conflicts)")
    print(f"Eligible Sharpe Requests          : {tot_elg_s:,}")
    print(f"Eligible VaR Requests             : {tot_elg_v:,}")
    print(f"Eligible Either (Union)           : {tot_elg_either:,} ({tot_elg_either/tot_cfc*100:.1f}% of conflicts)")
    print(f"Eligible Both (Intersection)      : {tot_elg_both:,} ({tot_elg_both/max(1, tot_elg_either)*100:.1f}% of either)")
    print(f"V3 Drawdown Hyp Events (Comparator): {tot_v3_hyp:,}")

    # Overhead analysis on non-trivial instances (clean_wall_time >= 0.05s)
    nontrivial = [r for r in results if r["clean_wall_time_s"] >= 0.05]
    if nontrivial:
        mean_clean = sum(r["clean_wall_time_s"] for r in nontrivial) / len(nontrivial)
        mean_shadow = sum(r["shadow_wall_time_s"] for r in nontrivial) / len(nontrivial)
        mean_ovh = ((mean_shadow - mean_clean) / mean_clean) * 100.0
        print(f"\nMean Non-Trivial Runtime (Clean)  : {mean_clean:.4f}s")
        print(f"Mean Non-Trivial Runtime (Shadow) : {mean_shadow:.4f}s")
        print(f"Estimated QRE Telemetry Overhead  : {mean_ovh:+.2f}%")

if __name__ == "__main__":
    main()

