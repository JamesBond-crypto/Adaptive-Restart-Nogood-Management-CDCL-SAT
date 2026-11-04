#!/usr/bin/env python3
"""
analyze_expanded_results.py - Detailed Analysis of Expanded Benchmark Characterization
"""

import csv
from collections import defaultdict
from pathlib import Path

def analyze():
    csv_path = Path("experiments/results/expanded_baseline_characterization.csv")
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Total instances evaluated: {len(rows)}")

    by_family = defaultdict(list)
    for r in rows:
        bname = r["benchmark_name"]
        if bname.startswith("rand3sat"):
            fam = "Random 3-SAT"
        elif bname.startswith("planted3sat"):
            fam = "Planted 3-SAT"
        elif bname.startswith("php"):
            fam = "Pigeonhole Principle"
        elif bname.startswith("gcol"):
            fam = "Graph Coloring"
        else:
            fam = "Other"
        by_family[fam].append(r)

    max_conflicts = 0
    max_conflicts_inst = ""
    max_genuine_restarts = 0
    max_genuine_restarts_inst = ""
    max_reductions = 0
    max_reductions_inst = ""
    max_removed = 0
    max_removed_inst = ""

    status_counts = defaultdict(int)

    # Classification categories:
    # - Too easy: minimal conflicts (< 100), no meaningful restart or clause reduction activity.
    # - Moderate: useful conflict-driven search (100 - 5000 conflicts) but limited restarts or reduction (< 2 genuine restarts, <= 1 reduction).
    # - Challenging: exercises repeated restarts (>= 2 genuine restarts) or learned-clause reductions (>= 2 reductions) or >= 5000 conflicts.
    # - Timeout: exceeds evaluation limit.
    # - Error: crash/error.
    categories = {"Too easy": [], "Moderate": [], "Challenging": [], "Timeout": [], "Error": []}

    for r in rows:
        status = r["status"]
        status_counts[status] += 1
        cfc = int(r["conflicts"]) if r["conflicts"] != "" else 0
        gen_rst = int(r["genuine_restarts"]) if r["genuine_restarts"] != "" else 0
        red = int(r["reduce_db_count"]) if r["reduce_db_count"] != "" else 0
        rem = int(r["removed_clauses"]) if r["removed_clauses"] != "" else 0

        if cfc > max_conflicts:
            max_conflicts = cfc
            max_conflicts_inst = r["benchmark_name"]
        if gen_rst > max_genuine_restarts:
            max_genuine_restarts = gen_rst
            max_genuine_restarts_inst = r["benchmark_name"]
        if red > max_reductions:
            max_reductions = red
            max_reductions_inst = r["benchmark_name"]
        if rem > max_removed:
            max_removed = rem
            max_removed_inst = r["benchmark_name"]

        if status == "TIMEOUT":
            categories["Timeout"].append(r["benchmark_name"])
        elif status in ("ERROR", "CRASH_OR_ERROR"):
            categories["Error"].append(r["benchmark_name"])
        elif cfc < 100 and gen_rst == 0 and red == 0:
            categories["Too easy"].append(r["benchmark_name"])
        elif cfc >= 5000 or gen_rst >= 2 or red >= 2:
            categories["Challenging"].append(r["benchmark_name"])
        else:
            categories["Moderate"].append(r["benchmark_name"])

    print("\n=== OVERALL STATUS COUNTS ===")
    for st, cnt in sorted(status_counts.items()):
        print(f"  {st}: {cnt}")

    print("\n=== DIFFICULTY CLASSIFICATION ===")
    for cat, insts in categories.items():
        print(f"  {cat}: {len(insts)}")
        for inst in insts:
            print(f"    - {inst}")

    print("\n=== PEAK METRICS ===")
    print(f"  Max conflicts: {max_conflicts} ({max_conflicts_inst})")
    print(f"  Max genuine restarts: {max_genuine_restarts} ({max_genuine_restarts_inst})")
    print(f"  Max clause reductions: {max_reductions} ({max_reductions_inst})")
    print(f"  Max clauses removed: {max_removed} ({max_removed_inst})")

    print("\n=== FAMILY STATISTICS ===")
    for fam, flist in by_family.items():
        f_cfc = [int(x["conflicts"]) for x in flist if x["conflicts"] != ""]
        f_rst = [int(x["genuine_restarts"]) for x in flist if x["genuine_restarts"] != ""]
        f_red = [int(x["reduce_db_count"]) for x in flist if x["reduce_db_count"] != ""]
        f_rem = [int(x["removed_clauses"]) for x in flist if x["removed_clauses"] != ""]
        f_time = [float(x["wall_time_s"]) for x in flist]
        sat_n = sum(1 for x in flist if x["status"] == "SAT")
        unsat_n = sum(1 for x in flist if x["status"] == "UNSAT")
        to_n = sum(1 for x in flist if x["status"] == "TIMEOUT")
        err_n = sum(1 for x in flist if x["status"] in ("ERROR", "CRASH_OR_ERROR"))
        print(f"\nFamily: {fam} (N={len(flist)})")
        print(f"  Outcomes: SAT={sat_n}, UNSAT={unsat_n}, TIMEOUT={to_n}, ERROR={err_n}")
        if f_cfc:
            print(f"  Conflicts: min={min(f_cfc)}, median={sorted(f_cfc)[len(f_cfc)//2]}, max={max(f_cfc)}, mean={sum(f_cfc)/len(f_cfc):.1f}")
            print(f"  Genuine Restarts: min={min(f_rst)}, median={sorted(f_rst)[len(f_rst)//2]}, max={max(f_rst)}, mean={sum(f_rst)/len(f_rst):.1f}")
            print(f"  Reductions: min={min(f_red)}, median={sorted(f_red)[len(f_red)//2]}, max={max(f_red)}, mean={sum(f_red)/len(f_red):.1f}")
            print(f"  Removed Clauses: min={min(f_rem)}, median={sorted(f_rem)[len(f_rem)//2]}, max={max(f_rem)}, mean={sum(f_rem)/len(f_rem):.1f}")
        print(f"  Wall Time: min={min(f_time):.3f}s, median={sorted(f_time)[len(f_time)//2]:.3f}s, max={max(f_time):.3f}s, sum={sum(f_time):.3f}s")

    # Top demanding instances
    print("\n=== TOP 10 MOST DEMANDING INSTANCES BY WALL TIME ===")
    sorted_by_time = sorted(rows, key=lambda x: float(x["wall_time_s"]), reverse=True)
    for i, r in enumerate(sorted_by_time[:10], start=1):
        print(f"  {i}. {r['benchmark_name']}: status={r['status']}, time={float(r['wall_time_s']):.3f}s, conflicts={r['conflicts']}, restarts={r['genuine_restarts']}, reductions={r['reduce_db_count']}")

if __name__ == "__main__":
    analyze()
