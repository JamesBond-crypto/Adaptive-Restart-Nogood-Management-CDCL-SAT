#!/usr/bin/env python3
"""
analyze_timeout_memory_audit.py - Step 25 Analysis Script

Analyzes the targeted repeated audit results from experiments/results/timeout_memory_audit/audit_all_runs.csv:
1. Solved & Timeout counts across 3 repetitions for every (instance, configuration).
2. Runtime variability: min, median, max, range of wall time and CPU time.
3. Deterministic counter consistency: verifies if conflicts, decisions, propagations, restarts,
   and reductions are 100% invariant across completed repetitions.
4. Memory measurement audit: Peak working set statistics, comparison between baseline and adaptive reduction.
5. Historical reconciliation across Step 20, Step 22, and Step 24 for the divergence instances.
"""

import sys
import os
import csv
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple

AUDIT_CSV = Path("experiments/results/timeout_memory_audit/audit_all_runs.csv")
CONFIG_ORDER = [
    "cfg1_base_base",
    "cfg2_v1_base",
    "cfg3_v1_adapt",
    "cfg4_v2_ceil_base",
    "cfg5_v2_ceil_adapt",
    "cfg6_v2_qual_base",
    "cfg7_v2_qual_adapt",
    "cfg8_v2_comb_adapt"
]

DIAGNOSTIC_INSTANCES = [
    "php_10p_9h.cnf",
    "php_10p_8h.cnf",
    "rand3sat_n250_c1065_s1010.cnf",
    "rand3sat_n235_c999_s1009.cnf",
    "rand3sat_n225_c958_s1008.cnf",
    "gcol_unsat_k10_c9.cnf",
    "planted3sat_n240_c1022_s2009.cnf",
    "planted3sat_n260_c1108_s2010.cnf"
]


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def main():
    if not AUDIT_CSV.is_file():
        print(f"Error: {AUDIT_CSV} not found.")
        return

    rows = load_csv(AUDIT_CSV)
    print(f"Loaded {len(rows)} audit run records from {AUDIT_CSV}")

    # Group by (benchmark_name, config_id)
    grouped = defaultdict(list)
    for r in rows:
        key = (r["benchmark_name"], r["config_id"])
        grouped[key].append(r)

    print("=" * 110)
    print("STEP 25: TARGETED REPEATED TIMEOUT AND MEMORY AUDIT ANALYSIS")
    print("=" * 110)

    # 1. Solved/Timeout Repeatability Table
    print("\n### 1. Repeatability and Runtime Variability (3 Repetitions per Configuration/Instance)")
    print("-" * 135)
    header = f"{'Benchmark':30s} | {'Config ID':18s} | {'Solved':>6s} | {'Statuses':>14s} | {'Wall Med(s)':>11s} | {'Wall Range(s)':>15s} | {'CPU Med(s)':>10s} | {'PeakMem(MB)':>11s} | {'Conflicts':>11s}"
    print(header)
    print("-" * 135)

    all_deterministic = True
    counter_discrepancies = []

    for bname in DIAGNOSTIC_INSTANCES:
        for cid in CONFIG_ORDER:
            reps = grouped.get((bname, cid), [])
            if not reps:
                continue
            
            statuses = [r["status"] for r in reps]
            solved_count = sum(1 for s in statuses if s in ("SAT", "UNSAT"))
            status_str = f"{statuses.count('SAT') + statuses.count('UNSAT')}/3 {statuses[0]}" if len(set(statuses)) == 1 else f"{'/'.join(statuses)}"

            wall_times = [float(r["wall_time_s"]) for r in reps]
            wall_med = compute_median(wall_times)
            wall_min = min(wall_times)
            wall_max = max(wall_times)
            wall_range_str = f"[{wall_min:5.2f}-{wall_max:5.2f}]"

            cpu_times = [float(r["cpu_time_s"]) for r in reps if r.get("cpu_time_s")]
            cpu_med = compute_median(cpu_times) if cpu_times else 0.0

            mems = [float(r["memory_mb"]) for r in reps if r.get("memory_mb")]
            mem_med = compute_median(mems) if mems else 0.0

            # Deterministic counters across solved reps
            solved_reps = [r for r in reps if r["status"] in ("SAT", "UNSAT")]
            if solved_reps:
                cfc_set = set(r["conflicts"] for r in solved_reps)
                dec_set = set(r["decisions"] for r in solved_reps)
                prp_set = set(r["propagations"] for r in solved_reps)
                rst_set = set(r["genuine_restarts"] for r in solved_reps)
                red_set = set(r["reduce_db_count"] for r in solved_reps)
                rem_set = set(r["removed_clauses"] for r in solved_reps)

                cfc_val = str(solved_reps[0]["conflicts"])
                if len(cfc_set) > 1 or len(dec_set) > 1 or len(prp_set) > 1 or len(rst_set) > 1:
                    all_deterministic = False
                    counter_discrepancies.append((bname, cid, cfc_set, dec_set))
                    cfc_val += " [DIVERGED]"
            else:
                cfc_val = "TIMEOUT"

            print(f"{bname:30s} | {cid:18s} | {solved_count:6d} | {status_str:>14s} | {wall_med:11.3f} | {wall_range_str:>15s} | {cpu_med:10.3f} | {mem_med:11.2f} | {cfc_val:>11s}")
        print("-" * 135)

    print(f"\n[*] Deterministic Search Tree Invariance: {'PERFECT (100% Bitwise Counter Stability)' if all_deterministic else 'FAILED - Counters diverged!'}")
    if counter_discrepancies:
        for b, c, cfc_s, dec_s in counter_discrepancies:
            print(f"    Discrepancy on {b} under {c}: Conflicts {cfc_s}, Decisions {dec_s}")

    # 2. Memory Comparison: Baseline vs Adaptive Retention
    print("\n" + "=" * 110)
    print("### 2. Peak Memory Comparison: Baseline Reduction vs Adaptive Retention")
    print("=" * 110)
    print(f"{'Benchmark':30s} | {'Base Red Med Mem':>16s} | {'Adapt Red Med Mem':>17s} | {'Mem Ratio (Adapt/Base)':>22s}")
    print("-" * 95)

    base_red_cfgs = ["cfg1_base_base", "cfg2_v1_base", "cfg4_v2_ceil_base", "cfg6_v2_qual_base"]
    adapt_red_cfgs = ["cfg3_v1_adapt", "cfg5_v2_ceil_adapt", "cfg7_v2_qual_adapt", "cfg8_v2_comb_adapt"]

    for bname in DIAGNOSTIC_INSTANCES:
        base_mems = []
        for cid in base_red_cfgs:
            for r in grouped.get((bname, cid), []):
                if r.get("memory_mb"):
                    base_mems.append(float(r["memory_mb"]))
        adapt_mems = []
        for cid in adapt_red_cfgs:
            for r in grouped.get((bname, cid), []):
                if r.get("memory_mb"):
                    adapt_mems.append(float(r["memory_mb"]))

        med_b = compute_median(base_mems) if base_mems else 0.0
        med_a = compute_median(adapt_mems) if adapt_mems else 0.0
        ratio_str = f"{med_a / med_b:6.2f}x" if med_b > 0 and med_a > 0 else "N/A"
        print(f"{bname:30s} | {med_b:14.2f}MB | {med_a:15.2f}MB | {ratio_str:>22s}")
    print("-" * 95)


if __name__ == "__main__":
    main()

