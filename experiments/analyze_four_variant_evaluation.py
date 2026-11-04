#!/usr/bin/env python3
"""
analyze_four_variant_evaluation.py - Four-Variant Comprehensive Evaluation & Interaction Analysis
"""

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

CFG_FILES = {
    "cfg1": ("Baseline", Path("experiments/results/expanded_cfg1_base_base.csv")),
    "cfg2": ("Adaptive Restart Only", Path("experiments/results/expanded_cfg2_adapt_base.csv")),
    "cfg3": ("Adaptive Retention Only", Path("experiments/results/expanded_cfg3_base_adapt.csv")),
    "cfg4": ("Combined Adaptive", Path("experiments/results/expanded_cfg4_adapt_adapt.csv")),
}

BASELINE_CHAR_FILE = Path("experiments/results/expanded_baseline_characterization.csv")
MANIFEST_FILE = Path("benchmarks/expanded_manifest.csv")
TIMEOUT_LIMIT = 15.0
PAR2_PENALTY = 2.0 * TIMEOUT_LIMIT  # 30.0s


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
    return "Other"


def compute_median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    else:
        return (s[mid - 1] + s[mid]) / 2.0


def main():
    manifest = {r["filename"]: r for r in load_csv(MANIFEST_FILE)}
    cfg_data = {cfg_id: {r["benchmark_name"]: r for r in load_csv(path)} for cfg_id, (_, path) in CFG_FILES.items()}
    all_benchmarks = list(manifest.keys())

    print("=" * 80)
    print("FOUR-VARIANT COMPREHENSIVE EXPERIMENTAL EVALUATION AUDIT")
    print("=" * 80)

    # 1. Correctness Audit
    print("\n--- 1. CORRECTNESS AND GROUND-TRUTH AUDIT ---")
    correctness_errors = []
    for cfg_id, (cfg_name, _) in CFG_FILES.items():
        data = cfg_data[cfg_id]
        for bname in all_benchmarks:
            r = data[bname]
            st = r["status"]
            known = manifest[bname]["known_status"]
            v_model = r["model_verified"]

            if st == "SAT":
                if known == "UNSAT":
                    correctness_errors.append(f"[{cfg_id}] {bname}: Reported SAT on known UNSAT!")
                if v_model not in ("VERIFIED", "True", True):
                    correctness_errors.append(f"[{cfg_id}] {bname}: SAT model verification failed ({v_model})!")
            elif st == "UNSAT":
                if known == "SAT":
                    correctness_errors.append(f"[{cfg_id}] {bname}: Reported UNSAT on known SAT!")
            elif st not in ("TIMEOUT", "ERROR"):
                correctness_errors.append(f"[{cfg_id}] {bname}: Unknown status string '{st}'")

    if correctness_errors:
        print("[!] CRITICAL CORRECTNESS ERRORS FOUND:")
        for err in correctness_errors:
            print("   ", err)
        return
    else:
        print("[+] 100% Correctness Verified: Zero ground-truth contradictions across all 144 runs.")
        print("[+] 100% SAT Model Verification: All reported satisfying models independently verified.")

    # 2. Solved, Timeout, Error Counts
    print("\n--- 2. OVERALL SOLVED, TIMEOUT, AND ERROR COUNTS ---")
    print(f"{'Configuration':<28} | {'Solved':<8} | {'SAT':<6} | {'UNSAT':<6} | {'Timeout':<8} | {'PAR-2 (s)':<10}")
    print("-" * 75)

    cfg_par2 = {}
    for cfg_id, (cfg_name, _) in CFG_FILES.items():
        data = cfg_data[cfg_id]
        solved = sum(1 for r in data.values() if r["status"] in ("SAT", "UNSAT"))
        sat_cnt = sum(1 for r in data.values() if r["status"] == "SAT")
        unsat_cnt = sum(1 for r in data.values() if r["status"] == "UNSAT")
        to_cnt = sum(1 for r in data.values() if r["status"] == "TIMEOUT")

        par2_total = 0.0
        for r in data.values():
            if r["status"] in ("SAT", "UNSAT"):
                par2_total += float(r["wall_time_s"])
            else:
                par2_total += PAR2_PENALTY
        par2_mean = par2_total / len(data)
        cfg_par2[cfg_id] = par2_mean

        print(f"{cfg_name:<28} | {solved:<8} | {sat_cnt:<6} | {unsat_cnt:<6} | {to_cnt:<8} | {par2_mean:<10.3f}")

    # 3. Family-by-Family Breakdown
    print("\n--- 3. DETAILED METRICS BY BENCHMARK FAMILY ---")
    families = ["Random 3-SAT", "Planted 3-SAT", "Pigeonhole Principle", "Graph Coloring"]

    for fam in families:
        fam_bmarks = [b for b in all_benchmarks if get_family(b) == fam]
        n_fam = len(fam_bmarks)
        print(f"\n================================================================================")
        print(f"FAMILY: {fam} (N = {n_fam})")
        print(f"================================================================================")

        # Mutually solved instances in this family
        mut_solved = [
            b for b in fam_bmarks
            if all(cfg_data[c][b]["status"] in ("SAT", "UNSAT") for c in CFG_FILES)
        ]

        print(f"Mutually solved instances by all 4 configurations: {len(mut_solved)} / {n_fam}")

        print(f"\n{'Metric':<25} | {'Cfg 1 (Baseline)':<16} | {'Cfg 2 (Adpt Rst)':<16} | {'Cfg 3 (Adpt Ret)':<16} | {'Cfg 4 (Combined)':<16}")
        print("-" * 96)

        # Outcomes
        outcomes_row = []
        for c in CFG_FILES:
            sol = sum(1 for b in fam_bmarks if cfg_data[c][b]["status"] in ("SAT", "UNSAT"))
            to = sum(1 for b in fam_bmarks if cfg_data[c][b]["status"] == "TIMEOUT")
            outcomes_row.append(f"{sol} S / {to} TO")
        print(f"{'Solved / Timeouts':<25} | {outcomes_row[0]:<16} | {outcomes_row[1]:<16} | {outcomes_row[2]:<16} | {outcomes_row[3]:<16}")

        # PAR-2
        par2_row = []
        for c in CFG_FILES:
            p2 = sum(float(cfg_data[c][b]["wall_time_s"]) if cfg_data[c][b]["status"] in ("SAT", "UNSAT") else PAR2_PENALTY for b in fam_bmarks) / n_fam
            par2_row.append(f"{p2:.3f}s")
        print(f"{'PAR-2 Score':<25} | {par2_row[0]:<16} | {par2_row[1]:<16} | {par2_row[2]:<16} | {par2_row[3]:<16}")

        # Median wall time on solved
        med_time_row = []
        for c in CFG_FILES:
            times = [float(cfg_data[c][b]["wall_time_s"]) for b in fam_bmarks if cfg_data[c][b]["status"] in ("SAT", "UNSAT")]
            med_time_row.append(f"{compute_median(times):.3f}s")
        print(f"{'Median Time (Solved)':<25} | {med_time_row[0]:<16} | {med_time_row[1]:<16} | {med_time_row[2]:<16} | {med_time_row[3]:<16}")

        # Conflicts (mutually solved)
        if mut_solved:
            mean_cfc_row = []
            tot_cfc_row = []
            for c in CFG_FILES:
                cfcs = [int(cfg_data[c][b]["conflicts"]) for b in mut_solved]
                mean_cfc_row.append(f"{sum(cfcs)/len(cfcs):.1f}")
                tot_cfc_row.append(f"{sum(cfcs):,}")
            print(f"{'Mean Conflicts (Paired)':<25} | {mean_cfc_row[0]:<16} | {mean_cfc_row[1]:<16} | {mean_cfc_row[2]:<16} | {mean_cfc_row[3]:<16}")
            print(f"{'Total Conflicts (Paired)':<25} | {tot_cfc_row[0]:<16} | {tot_cfc_row[1]:<16} | {tot_cfc_row[2]:<16} | {tot_cfc_row[3]:<16}")

            # Genuine restarts
            mean_rst_row = []
            for c in CFG_FILES:
                rsts = [int(cfg_data[c][b]["genuine_restarts"]) for b in mut_solved]
                mean_rst_row.append(f"{sum(rsts)/len(rsts):.1f}")
            print(f"{'Mean Genuine Restarts':<25} | {mean_rst_row[0]:<16} | {mean_rst_row[1]:<16} | {mean_rst_row[2]:<16} | {mean_rst_row[3]:<16}")

            # Clause database reductions
            mean_red_row = []
            for c in CFG_FILES:
                reds = [int(cfg_data[c][b]["reduce_db_count"]) for b in mut_solved]
                mean_red_row.append(f"{sum(reds)/len(reds):.1f}")
            print(f"{'Mean DB Reductions':<25} | {mean_red_row[0]:<16} | {mean_red_row[1]:<16} | {mean_red_row[2]:<16} | {mean_red_row[3]:<16}")

            # Removed clauses
            mean_rem_row = []
            for c in CFG_FILES:
                rems = [int(cfg_data[c][b]["removed_clauses"]) for b in mut_solved]
                mean_rem_row.append(f"{sum(rems)/len(rems):.1f}")
            print(f"{'Mean Removed Clauses':<25} | {mean_rem_row[0]:<16} | {mean_rem_row[1]:<16} | {mean_rem_row[2]:<16} | {mean_rem_row[3]:<16}")

            # Peak Memory
            max_mem_row = []
            for c in CFG_FILES:
                mems = [float(cfg_data[c][b]["memory_mb"]) for b in mut_solved if cfg_data[c][b]["memory_mb"] != ""]
                max_mem_row.append(f"{max(mems):.2f} MB" if mems else "N/A")
            print(f"{'Peak Memory':<25} | {max_mem_row[0]:<16} | {max_mem_row[1]:<16} | {max_mem_row[2]:<16} | {max_mem_row[3]:<16}")

    # 4. Interaction Effect Analysis
    print("\n================================================================================")
    print("4. INTERACTION EFFECT ANALYSIS (I = Y_comb - Y_restart - Y_retention + Y_baseline)")
    print("================================================================================")
    print("Formula: I = Conflicts(cfg4) - Conflicts(cfg2) - Conflicts(cfg3) + Conflicts(cfg1)")
    print("Interpretation:")
    print("  I < 0: Super-additive synergy (combined algorithms reduce conflicts by more than sum of parts)")
    print("  I = 0: Additive independence (effects combine linearly)")
    print("  I > 0: Sub-additive / antagonistic interaction (combined algorithms overlap or interfere)")

    all_mut_solved = [
        b for b in all_benchmarks
        if all(cfg_data[c][b]["status"] in ("SAT", "UNSAT") for c in CFG_FILES)
    ]
    print(f"\nTotal mutually completed instances across entire suite: {len(all_mut_solved)} / {len(all_benchmarks)}")

    # Overall interaction
    total_cfc = {c: sum(int(cfg_data[c][b]["conflicts"]) for b in all_mut_solved) for c in CFG_FILES}
    I_overall = total_cfc["cfg4"] - total_cfc["cfg2"] - total_cfc["cfg3"] + total_cfc["cfg1"]

    print(f"\nOverall Totals on {len(all_mut_solved)} Paired Instances:")
    print(f"  Cfg 1 (Baseline):      {total_cfc['cfg1']:,} conflicts")
    print(f"  Cfg 2 (Adaptive Rst):  {total_cfc['cfg2']:,} conflicts (Diff = {total_cfc['cfg2'] - total_cfc['cfg1']:+,})")
    print(f"  Cfg 3 (Adaptive Ret):  {total_cfc['cfg3']:,} conflicts (Diff = {total_cfc['cfg3'] - total_cfc['cfg1']:+,})")
    print(f"  Cfg 4 (Combined):      {total_cfc['cfg4']:,} conflicts (Diff = {total_cfc['cfg4'] - total_cfc['cfg1']:+,})")
    print(f"  Interaction I:         {I_overall:+,} conflicts")

    # Family-by-family interaction
    print("\nFamily Interaction Breakdown:")
    print(f"{'Family':<22} | {'Paired N':<8} | {'Cfg 1':<10} | {'Cfg 2':<10} | {'Cfg 3':<10} | {'Cfg 4':<10} | {'Interaction I':<14} | {'Effect':<15}")
    print("-" * 110)

    for fam in families:
        fam_mut = [b for b in all_mut_solved if get_family(b) == fam]
        if not fam_mut:
            continue
        c1 = sum(int(cfg_data["cfg1"][b]["conflicts"]) for b in fam_mut)
        c2 = sum(int(cfg_data["cfg2"][b]["conflicts"]) for b in fam_mut)
        c3 = sum(int(cfg_data["cfg3"][b]["conflicts"]) for b in fam_mut)
        c4 = sum(int(cfg_data["cfg4"][b]["conflicts"]) for b in fam_mut)
        I_fam = c4 - c2 - c3 + c1
        effect = "Synergistic" if I_fam < 0 else "Antagonistic" if I_fam > 0 else "Neutral"
        print(f"{fam:<22} | {len(fam_mut):<8} | {c1:<10,d} | {c2:<10,d} | {c3:<10,d} | {c4:<10,d} | {I_fam:<+14,d} | {effect:<15}")

    # Paired instance-level interaction distribution
    per_inst_I = []
    for b in all_mut_solved:
        c1 = int(cfg_data["cfg1"][b]["conflicts"])
        c2 = int(cfg_data["cfg2"][b]["conflicts"])
        c3 = int(cfg_data["cfg3"][b]["conflicts"])
        c4 = int(cfg_data["cfg4"][b]["conflicts"])
        inst_I = c4 - c2 - c3 + c1
        per_inst_I.append((b, get_family(b), c1, c2, c3, c4, inst_I))

    synergistic_n = sum(1 for x in per_inst_I if x[6] < 0)
    neutral_n = sum(1 for x in per_inst_I if x[6] == 0)
    antagonistic_n = sum(1 for x in per_inst_I if x[6] > 0)

    print(f"\nPer-Instance Interaction Distribution (N = {len(all_mut_solved)}):")
    print(f"  Synergistic (I < 0):   {synergistic_n} instances ({synergistic_n/len(all_mut_solved)*100:.1f}%)")
    print(f"  Neutral (I = 0):       {neutral_n} instances ({neutral_n/len(all_mut_solved)*100:.1f}%)")
    print(f"  Antagonistic (I > 0):  {antagonistic_n} instances ({antagonistic_n/len(all_mut_solved)*100:.1f}%)")

    # 5. Baseline Reproducibility Audit
    print("\n================================================================================")
    print("5. BASELINE REPRODUCIBILITY AUDIT (Cfg 1 vs Baseline Characterization)")
    print("================================================================================")
    base_char_data = {r["benchmark_name"]: r for r in load_csv(BASELINE_CHAR_FILE)}
    diff_count = 0
    match_count = 0

    print(f"{'Benchmark':<35} | {'Metric':<15} | {'Characterization':<18} | {'Cfg 1 (Current)':<18} | {'Status':<10}")
    print("-" * 105)

    for bname in all_benchmarks:
        r_char = base_char_data[bname]
        r_cfg1 = cfg_data["cfg1"][bname]

        st_char = r_char["status"]
        st_cfg1 = r_cfg1["status"]

        if st_char in ("SAT", "UNSAT") and st_cfg1 in ("SAT", "UNSAT"):
            # Compare deterministic CDCL search metrics
            c_char = int(r_char["conflicts"])
            c_cfg1 = int(r_cfg1["conflicts"])
            d_char = int(r_char["decisions"])
            d_cfg1 = int(r_cfg1["decisions"])
            p_char = int(r_char["propagations"])
            p_cfg1 = int(r_cfg1["propagations"])

            if (c_char, d_char, p_char) == (c_cfg1, d_cfg1, p_cfg1):
                match_count += 1
            else:
                diff_count += 1
                print(f"{bname:<35} | {'conflicts':<15} | {c_char:<18} | {c_cfg1:<18} | {'DIFF':<10}")
                print(f"{bname:<35} | {'decisions':<15} | {d_char:<18} | {d_cfg1:<18} | {'DIFF':<10}")
                print(f"{bname:<35} | {'propagations':<15} | {p_char:<18} | {p_cfg1:<18} | {'DIFF':<10}")
        elif st_char != st_cfg1:
            diff_count += 1
            print(f"{bname:<35} | {'status':<15} | {st_char:<18} | {st_cfg1:<18} | {'STATUS DIFF':<10}")

    print(f"\nBaseline Reproducibility Summary:")
    print(f"  Exact Bitwise Matching Search Runs: {match_count} / 33 solved instances ({match_count/33*100:.1f}%)")
    print(f"  Mismatched Solved Runs:              {diff_count}")

    # 6. Regressions Audit
    print("\n================================================================================")
    print("6. REGRESSIONS AUDIT (Where Adaptive Performed Worse than Baseline)")
    print("================================================================================")
    print("Looking for instances where Cfg 2, Cfg 3, or Cfg 4 timed out while Cfg 1 solved,")
    print("or where conflict counts increased substantially (>50% increase over baseline).")

    regressions = []
    for bname in all_mut_solved:
        c1 = int(cfg_data["cfg1"][bname]["conflicts"])
        for cid in ["cfg2", "cfg3", "cfg4"]:
            c_other = int(cfg_data[cid][bname]["conflicts"])
            if c1 > 1000 and c_other > 1.5 * c1:
                pct = ((c_other - c1) / c1) * 100.0
                regressions.append((bname, get_family(bname), cid, c1, c_other, pct))

    if regressions:
        print(f"Found {len(regressions)} instances with >50% conflict increases over baseline (min baseline 1,000 cfc):")
        for bname, fam, cid, c1, co, pct in sorted(regressions, key=lambda x: x[5], reverse=True):
            print(f"  - [{cid.upper()}] {bname} ({fam}): {c1:,} -> {co:,} conflicts (+{pct:.1f}%)")
    else:
        print("No significant conflict regressions (>50% increase) found.")

    # Timeouts comparison
    print("\nTimeout Comparisons:")
    for bname in all_benchmarks:
        statuses = {c: cfg_data[c][bname]["status"] for c in CFG_FILES}
        if any(s == "TIMEOUT" for s in statuses.values()):
            print(f"  {bname:<35}: " + " | ".join(f"{c.upper()}={statuses[c]}" for c in CFG_FILES))


if __name__ == "__main__":
    main()
