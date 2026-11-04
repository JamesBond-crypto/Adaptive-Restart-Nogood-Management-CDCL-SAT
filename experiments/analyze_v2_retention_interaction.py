#!/usr/bin/env python3
"""
analyze_v2_retention_interaction.py - Comprehensive Analysis for Adaptive Restart V2 x Nogood Retention

Analyzes the 8 configurations across all 36 expanded instances:
- Solved counts, timeouts, wall time, PAR-2 (30.0s penalty)
- Mutually solved instance conflicts, decisions, propagations
- Family-level breakdowns (Random 3-SAT, Planted 3-SAT, Pigeonhole, Graph Coloring)
- Five explicit paired comparisons:
    1. V1 Base vs V1 Adapt
    2. V2 Ceil Base vs V2 Ceil Adapt
    3. V2 Qual Base vs V2 Qual Adapt
    4. V2 Ceil Adapt vs V1 Adapt
    5. V2 Both Adapt vs V2 Ceil Adapt
- Telemetry audits: restart request breakdown, reduction metrics, clause protection counters
"""

import sys
import os
import csv
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple

RESULTS_DIR = Path("experiments/results/v2_retention_interaction")
MANIFEST_PATH = Path("benchmarks/expanded_manifest.csv")
TIMEOUT_S = 15.0
PAR2_PENALTY = 30.0

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

CONFIG_NAMES = {
    "cfg1_base_base": "Baseline Restart + Baseline Reduction",
    "cfg2_v1_base": "Adaptive V1 Restart + Baseline Reduction",
    "cfg3_v1_adapt": "Adaptive V1 Restart + Adaptive Reduction",
    "cfg4_v2_ceil_base": "V2 Ceiling Only + Baseline Reduction",
    "cfg5_v2_ceil_adapt": "V2 Ceiling Only + Adaptive Reduction",
    "cfg6_v2_qual_base": "V2 Quality Only + Baseline Reduction",
    "cfg7_v2_qual_adapt": "V2 Quality Only + Adaptive Reduction",
    "cfg8_v2_comb_adapt": "V2 Combined + Adaptive Reduction"
}


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_family(bname: str) -> str:
    if bname.startswith("rand3sat"):
        return "Random 3-SAT"
    elif bname.startswith("planted3sat"):
        return "Planted 3-SAT"
    elif bname.startswith("php"):
        return "Pigeonhole Principle"
    elif bname.startswith("gcol"):
        return "Graph Coloring"
    return "Unknown"


def compute_median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def analyze():
    if not (RESULTS_DIR / "master_interaction_results.csv").is_file():
        print(f"Results not found at {RESULTS_DIR}")
        return

    manifest = {r["filename"]: r for r in load_csv(MANIFEST_PATH)}
    benchmarks = sorted(list(manifest.keys()))
    
    cfg_data = {}
    for cid in CONFIG_ORDER:
        csv_file = RESULTS_DIR / f"{cid}.csv"
        rows = load_csv(csv_file)
        cfg_data[cid] = {r["benchmark_name"]: r for r in rows}

    print("=" * 90)
    print("STEP 24: ADAPTIVE RESTART V2 x ADAPTIVE NOGOOD RETENTION INTERACTION ANALYSIS")
    print("=" * 90)

    # 1. Overall Summary Table
    print("\n### 1. Overall Performance Summary (36 Instances, 15.0s Timeout, PAR-2 Penalty = 30.0s)")
    print("-" * 125)
    header = f"{'Config ID':19s} | {'Solved':>6s} | {'Timeouts':>8s} | {'Tot Wall (s)':>12s} | {'PAR-2 (s)':>10s} | {'Median T(s)':>11s} | {'Mean T(s)':>10s} | {'Max Mem(MB)':>11s}"
    print(header)
    print("-" * 125)

    all_solved = {}
    for cid in CONFIG_ORDER:
        data = cfg_data[cid]
        solved = 0
        timeouts = 0
        tot_wall = 0.0
        par2_times = []
        wall_times = []
        max_mem = 0.0
        solved_benchmarks = set()

        for b in benchmarks:
            r = data[b]
            st = r["status"]
            wt = float(r["wall_time_s"])
            tot_wall += wt
            wall_times.append(wt)
            mem = float(r["memory_mb"]) if r.get("memory_mb") else 0.0
            if mem > max_mem:
                max_mem = mem

            if st == "TIMEOUT":
                timeouts += 1
                par2_times.append(PAR2_PENALTY)
            elif st in ("SAT", "UNSAT"):
                solved += 1
                par2_times.append(wt)
                solved_benchmarks.add(b)

        par2 = sum(par2_times) / len(par2_times)
        med_t = compute_median(wall_times)
        mean_t = sum(wall_times) / len(wall_times)
        all_solved[cid] = solved_benchmarks

        print(f"{cid:19s} | {solved:6d} | {timeouts:8d} | {tot_wall:12.2f} | {par2:10.3f} | {med_t:11.3f} | {mean_t:10.3f} | {max_mem:11.2f}")

    print("-" * 125)

    # Mutually solved instances across all 8 configurations
    mutual_8 = set(benchmarks)
    for cid in CONFIG_ORDER:
        mutual_8 &= all_solved[cid]
    print(f"\n[*] Mutually solved instances across ALL 8 configurations: {len(mutual_8)} of 36")
    timed_out_in_any = sorted(list(set(benchmarks) - mutual_8))
    print(f"    Excluded instances with timeouts in at least one config: {timed_out_in_any}")

    # Check timeout patterns per config
    print("\n### 2. Timeout Distribution by Configuration")
    for cid in CONFIG_ORDER:
        data = cfg_data[cid]
        to_list = [b for b in benchmarks if data[b]["status"] == "TIMEOUT"]
        print(f"  {cid:19s} ({len(to_list)} timeouts): {to_list}")

    # 3. Conflicts and Telemetry on Mutually Solved Instances (mutual_8)
    print(f"\n### 3. Cumulative Telemetry on Mutually Solved Instances (N = {len(mutual_8)})")
    print("-" * 140)
    t_header = f"{'Config ID':19s} | {'Conflicts':>11s} | {'Decisions':>11s} | {'Propagations':>14s} | {'Restarts':>9s} | {'ReduceDB':>9s} | {'Removed Cls':>12s} | {'Mutual Wall':>11s}"
    print(t_header)
    print("-" * 140)

    for cid in CONFIG_ORDER:
        data = cfg_data[cid]
        c_cfc = sum(int(data[b]["conflicts"]) for b in mutual_8 if data[b]["conflicts"])
        c_dec = sum(int(data[b]["decisions"]) for b in mutual_8 if data[b]["decisions"])
        c_prp = sum(int(data[b]["propagations"]) for b in mutual_8 if data[b]["propagations"])
        c_rst = sum(int(data[b]["genuine_restarts"]) for b in mutual_8 if data[b]["genuine_restarts"])
        c_red = sum(int(data[b]["reduce_db_count"]) for b in mutual_8 if data[b]["reduce_db_count"])
        c_rem = sum(int(data[b]["removed_clauses"]) for b in mutual_8 if data[b]["removed_clauses"])
        c_wt = sum(float(data[b]["wall_time_s"]) for b in mutual_8)

        print(f"{cid:19s} | {c_cfc:11,d} | {c_dec:11,d} | {c_prp:14,d} | {c_rst:9,d} | {c_red:9,d} | {c_rem:12,d} | {c_wt:11.2f}s")
    print("-" * 140)

    # 4. Per-Family Breakdown
    families = ["Random 3-SAT", "Planted 3-SAT", "Pigeonhole Principle", "Graph Coloring"]
    fam_benchmarks = defaultdict(list)
    for b in benchmarks:
        fam_benchmarks[get_family(b)].append(b)

    print("\n### 4. Per-Family Detailed Breakdown")
    for fam in families:
        f_bms = fam_benchmarks[fam]
        print(f"\n--- Family: {fam} (N = {len(f_bms)}) ---")
        f_mutual = [b for b in f_bms if b in mutual_8]
        print(f"Mutually solved instances in family: {len(f_mutual)} of {len(f_bms)}")
        print(f"{'Config ID':19s} | {'Solved':>6s} | {'PAR-2 (s)':>10s} | {'Mutual Conflicts':>16s} | {'Mutual Wall (s)':>15s} | {'Restarts':>9s} | {'ReduceDB':>9s}")
        print("-" * 95)
        for cid in CONFIG_ORDER:
            data = cfg_data[cid]
            f_solved = sum(1 for b in f_bms if data[b]["status"] in ("SAT", "UNSAT"))
            f_par2_times = [float(data[b]["wall_time_s"]) if data[b]["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for b in f_bms]
            f_par2 = sum(f_par2_times) / len(f_par2_times)
            f_cfc = sum(int(data[b]["conflicts"]) for b in f_mutual if data[b]["conflicts"])
            f_wt = sum(float(data[b]["wall_time_s"]) for b in f_mutual)
            f_rst = sum(int(data[b]["genuine_restarts"]) for b in f_mutual if data[b]["genuine_restarts"])
            f_red = sum(int(data[b]["reduce_db_count"]) for b in f_mutual if data[b]["reduce_db_count"])
            print(f"{cid:19s} | {f_solved:6d} | {f_par2:10.3f} | {f_cfc:16,d} | {f_wt:15.2f} | {f_rst:9,d} | {f_red:9,d}")

    # 5. The Five Explicit Paired Comparisons
    print("\n" + "=" * 90)
    print("### 5. The Five Required Paired Comparisons")
    print("=" * 90)

    paired_comparisons = [
        ("Pair 1: V1 Base vs V1 Adapt", "cfg2_v1_base", "cfg3_v1_adapt"),
        ("Pair 2: V2 Ceil Base vs V2 Ceil Adapt", "cfg4_v2_ceil_base", "cfg5_v2_ceil_adapt"),
        ("Pair 3: V2 Qual Base vs V2 Qual Adapt", "cfg6_v2_qual_base", "cfg7_v2_qual_adapt"),
        ("Pair 4: V2 Ceil Adapt vs V1 Adapt", "cfg5_v2_ceil_adapt", "cfg3_v1_adapt"),
        ("Pair 5: V2 Comb Adapt vs V2 Ceil Adapt", "cfg8_v2_comb_adapt", "cfg5_v2_ceil_adapt")
    ]

    for title, cA, cB in paired_comparisons:
        print(f"\n=======================================================")
        print(f"{title} ({cA} vs {cB})")
        print(f"=======================================================")
        dataA = cfg_data[cA]
        dataB = cfg_data[cB]

        # Mutually solved between pair
        pair_mutual = [b for b in benchmarks if dataA[b]["status"] in ("SAT", "UNSAT") and dataB[b]["status"] in ("SAT", "UNSAT")]
        print(f"Mutually solved instances between {cA} and {cB}: {len(pair_mutual)} of {len(benchmarks)}")

        cfc_A = sum(int(dataA[b]["conflicts"]) for b in pair_mutual)
        cfc_B = sum(int(dataB[b]["conflicts"]) for b in pair_mutual)
        cfc_delta = cfc_B - cfc_A
        cfc_pct = (cfc_delta / cfc_A * 100.0) if cfc_A > 0 else 0.0

        wt_A = sum(float(dataA[b]["wall_time_s"]) for b in pair_mutual)
        wt_B = sum(float(dataB[b]["wall_time_s"]) for b in pair_mutual)
        wt_delta = wt_B - wt_A
        wt_pct = (wt_delta / wt_A * 100.0) if wt_A > 0 else 0.0

        rst_A = sum(int(dataA[b]["genuine_restarts"]) for b in pair_mutual)
        rst_B = sum(int(dataB[b]["genuine_restarts"]) for b in pair_mutual)

        red_A = sum(int(dataA[b]["reduce_db_count"]) for b in pair_mutual)
        red_B = sum(int(dataB[b]["reduce_db_count"]) for b in pair_mutual)

        rem_A = sum(int(dataA[b]["removed_clauses"]) for b in pair_mutual)
        rem_B = sum(int(dataB[b]["removed_clauses"]) for b in pair_mutual)

        print(f"Conflicts ({cA} -> {cB}): {cfc_A:,} -> {cfc_B:,} (Delta: {cfc_delta:+,} | {cfc_pct:+.2f}%)")
        print(f"Wall Time ({cA} -> {cB}): {wt_A:.2f}s -> {wt_B:.2f}s (Delta: {wt_delta:+.2f}s | {wt_pct:+.2f}%)")
        print(f"Restarts  ({cA} -> {cB}): {rst_A:,} -> {rst_B:,} (Delta: {rst_B - rst_A:+,})")
        print(f"ReduceDB  ({cA} -> {cB}): {red_A:,} -> {red_B:,} (Delta: {red_B - red_A:+,})")
        print(f"RemovedCls({cA} -> {cB}): {rem_A:,} -> {rem_B:,} (Delta: {rem_B - rem_A:+,})")

        # Top 3 wins and losses in conflicts
        deltas = []
        for b in pair_mutual:
            c1 = int(dataA[b]["conflicts"])
            c2 = int(dataB[b]["conflicts"])
            t1 = float(dataA[b]["wall_time_s"])
            t2 = float(dataB[b]["wall_time_s"])
            d_cfc = c2 - c1
            pct = (d_cfc / c1 * 100.0) if c1 > 0 else 0.0
            deltas.append((b, c1, c2, d_cfc, pct, t1, t2))

        # Best improvements for B (most negative delta)
        deltas.sort(key=lambda x: x[3])
        print("  Top 3 conflict reductions in B vs A:")
        for b, c1, c2, d_cfc, pct, t1, t2 in deltas[:3]:
            print(f"    - {b:35s}: {c1:7,d} -> {c2:7,d} ({d_cfc:+7,d} | {pct:+6.1f}%) | Time: {t1:5.2f}s -> {t2:5.2f}s")

        # Worst regressions in B (most positive delta)
        print("  Top 3 conflict regressions in B vs A:")
        for b, c1, c2, d_cfc, pct, t1, t2 in deltas[-3:][::-1]:
            print(f"    - {b:35s}: {c1:7,d} -> {c2:7,d} ({d_cfc:+7,d} | {pct:+6.1f}%) | Time: {t1:5.2f}s -> {t2:5.2f}s")

    # 6. Telemetry and Conservation Audit
    print("\n" + "=" * 90)
    print("### 6. Telemetry and Conservation Audit")
    print("=" * 90)

    print("\n--- V2 Restart Request vs Execution Conservation ---")
    for cid in ["cfg4_v2_ceil_base", "cfg5_v2_ceil_adapt", "cfg6_v2_qual_base", "cfg7_v2_qual_adapt", "cfg8_v2_comb_adapt"]:
        data = cfg_data[cid]
        mismatch_req = 0
        tot_prog = 0
        tot_qual = 0
        tot_ceil = 0
        tot_req = 0
        tot_exec = 0
        tot_gen = 0
        max_seen_interval = 0

        for b in benchmarks:
            r = data[b]
            if r["v2_total_requests"] != "":
                prog = int(r["v2_req_progress"]) if r["v2_req_progress"] else 0
                qual = int(r["v2_req_quality"]) if r["v2_req_quality"] else 0
                ceil = int(r["v2_req_ceiling"]) if r["v2_req_ceiling"] else 0
                req = int(r["v2_total_requests"])
                ex = int(r["v2_executed_restarts"])
                gen = int(r["genuine_restarts"]) if r["genuine_restarts"] else 0
                inv = int(r["v2_max_interval"]) if r["v2_max_interval"] else 0

                if req != ex:
                    mismatch_req += 1
                tot_prog += prog
                tot_qual += qual
                tot_ceil += ceil
                tot_req += req
                tot_exec += ex
                tot_gen += gen
                if inv > max_seen_interval:
                    max_seen_interval = inv

        print(f"{cid:19s} | Requests: {tot_req:5d} (Prog:{tot_prog:4d}, Qual:{tot_qual:4d}, Ceil:{tot_ceil:4d}) | Executed:{tot_exec:5d} | Genuine:{tot_gen:5d} | Mismatches:{mismatch_req} | MaxInterval:{max_seen_interval}")

    print("\n--- Adaptive Retention Telemetry Audit ---")
    for cid in ["cfg3_v1_adapt", "cfg5_v2_ceil_adapt", "cfg7_v2_qual_adapt", "cfg8_v2_comb_adapt"]:
        data = cfg_data[cid]
        calls = 0
        ranked = 0
        eligible = 0
        removed = 0
        locked = 0
        binary = 0
        glue = 0
        canbedel = 0

        for b in benchmarks:
            r = data[b]
            if r["adapt_reduce_calls"] != "":
                calls += int(r["adapt_reduce_calls"]) if r["adapt_reduce_calls"] else 0
                ranked += int(r["adapt_clauses_ranked"]) if r["adapt_clauses_ranked"] else 0
                eligible += int(r["adapt_clauses_eligible"]) if r["adapt_clauses_eligible"] else 0
                removed += int(r["adapt_clauses_removed"]) if r["adapt_clauses_removed"] else 0
                locked += int(r["adapt_spared_locked"]) if r["adapt_spared_locked"] else 0
                binary += int(r["adapt_spared_binary"]) if r["adapt_spared_binary"] else 0
                glue += int(r["adapt_spared_glue"]) if r["adapt_spared_glue"] else 0
                canbedel += int(r["adapt_spared_canbedel"]) if r["adapt_spared_canbedel"] else 0

        print(f"{cid:19s} | Calls:{calls:4d} | Ranked:{ranked:8,d} | Eligible:{eligible:8,d} | Removed:{removed:8,d} | Spared(Locked:{locked:6,d}, Bin:{binary:6,d}, Glue:{glue:6,d}, CanBeDel:{canbedel:6,d})")


if __name__ == "__main__":
    analyze()

