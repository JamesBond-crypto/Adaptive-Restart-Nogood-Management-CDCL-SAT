#!/usr/bin/env python3
"""
plot_qre_gated_full_development.py - Generates Publication-Quality Visualizations for Step 41

Figures generated:
  1. fig_qre_gated_par2_comparison.png: Overall PAR-2 across 6 configurations
  2. fig_qre_gated_family_performance.png: PAR-2 disaggregated across 4 benchmark families
  3. fig_qre_gated_conflict_differences.png: Conflict differences (Gated vs Baseline AdaptFix) per benchmark
  4. fig_qre_gated_restart_counts.png: Gated vs Ungated QRE restart counts
  5. fig_qre_gated_runtime_memory.png: Runtime and memory scaling across configurations
"""

import sys
import os
import csv
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "qre_gated_full_development"
MASTER_CSV = RESULTS_DIR / "master_results.csv"
FIG_DIR = WORKSPACE / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["axes.labelsize"] = 11
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9

def mean(vals): return sum(vals) / len(vals) if vals else 0.0

def main():
    if not MASTER_CSV.is_file():
        print(f"Error: {MASTER_CSV} does not exist yet.")
        sys.exit(1)

    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows for plotting.")

    by_config = defaultdict(list)
    for r in rows:
        by_config[r["config_id"]].append(r)

    config_keys = [
        "cfg01_baseline_base",
        "cfg05_baseline_adaptfix",
        "cfg_active_adaptfix",
        "cfg_gated_base",
        "cfg_gated_adaptfix",
        "cfg_v3dd_adaptfix"
    ]

    labels = [
        "Glucose Base",
        "Glucose AdaptFix",
        "Ungated QRE",
        "Gated QRE Base",
        "Gated QRE AdaptFix",
        "V3 Drawdown"
    ]

    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#64B5CD"]

    # -------------------------------------------------------------
    # Figure 1: Overall PAR-2 Comparison
    # -------------------------------------------------------------
    par2_means = [mean([float(r["par2_s"]) for r in by_config[k]]) for k in config_keys]

    plt.figure(figsize=(9, 5), dpi=300)
    bars = plt.bar(labels, par2_means, color=colors, width=0.55, edgecolor="black", linewidth=0.8)
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., h + 0.03, f"{h:.4f}s", ha="center", va="bottom", fontweight="bold", fontsize=9)

    plt.ylabel("Mean PAR-2 Score (seconds, lower is better)")
    plt.title("Step 41: Global PAR-2 Comparison (36 Benchmarks x 3 Reps = 108 Runs / Config)")
    plt.ylim(0, max(par2_means) * 1.18)
    plt.tight_layout()
    fig1_path = FIG_DIR / "fig_qre_gated_par2_comparison.png"
    plt.savefig(fig1_path)
    plt.close()
    print(f"[+] Saved: {fig1_path}")

    # -------------------------------------------------------------
    # Figure 2: Per-Family Performance (PAR-2)
    # -------------------------------------------------------------
    families = sorted(list(set(r["family"] for r in rows)))
    n_fams = len(families)
    x = np.arange(n_fams)
    width = 0.13

    plt.figure(figsize=(11, 5.5), dpi=300)
    for i, (k, label, col) in enumerate(zip(config_keys, labels, colors)):
        fam_par2 = []
        for fam in families:
            runs = [r for r in by_config[k] if r["family"] == fam]
            fam_par2.append(mean([float(r["par2_s"]) for r in runs]))
        plt.bar(x + (i - 2.5) * width, fam_par2, width, label=label, color=col, edgecolor="black", linewidth=0.6)

    plt.xticks(x, [f.replace(" ", "\n") for f in families], rotation=0)
    plt.ylabel("Mean PAR-2 (s)")
    plt.title("Step 41: PAR-2 Comparison Across Benchmark Families")
    plt.legend(frameon=True, fontsize=8.5, loc="upper right")
    plt.tight_layout()
    fig2_path = FIG_DIR / "fig_qre_gated_family_performance.png"
    plt.savefig(fig2_path)
    plt.close()
    print(f"[+] Saved: {fig2_path}")

    # -------------------------------------------------------------
    # Figure 3: Per-Benchmark Conflict Differences (Gated vs Baseline AdaptFix)
    # -------------------------------------------------------------
    bmk_names = sorted(list(set(r["benchmark_name"] for r in rows)))
    diffs = []
    short_names = []
    for b in bmk_names:
        b_base = mean([int(r["conflicts"]) for r in by_config["cfg05_baseline_adaptfix"] if r["benchmark_name"] == b])
        b_gated = mean([int(r["conflicts"]) for r in by_config["cfg_gated_adaptfix"] if r["benchmark_name"] == b])
        d = b_gated - b_base
        diffs.append(d)
        short_names.append(b.replace(".cnf", ""))

    plt.figure(figsize=(13, 6), dpi=300)
    bar_cols = ["#55A868" if d < 0 else "#C44E52" if d > 0 else "#888888" for d in diffs]
    plt.bar(range(len(diffs)), diffs, color=bar_cols, width=0.6, edgecolor="black", linewidth=0.5)
    plt.axhline(0, color="black", linestyle="--", linewidth=0.8)
    plt.xticks(range(len(diffs)), short_names, rotation=90, fontsize=7.5)
    plt.ylabel(r"$\Delta$ Search Conflicts (Gated AdaptFix - Baseline AdaptFix)")
    plt.title("Step 41: Per-Benchmark Conflict Differences (Green = Fewer Conflicts, Red = More Conflicts)")
    plt.tight_layout()
    fig3_path = FIG_DIR / "fig_qre_gated_conflict_differences.png"
    plt.savefig(fig3_path)
    plt.close()
    print(f"[+] Saved: {fig3_path}")

    # -------------------------------------------------------------
    # Figure 4: Gated vs Ungated QRE Restart Counts
    # -------------------------------------------------------------
    act_rsts = []
    gat_rsts = []
    for b in bmk_names:
        act_r = sum(int(r["qre_executed_restarts"]) for r in by_config["cfg_active_adaptfix"] if r["benchmark_name"] == b)
        gat_r = sum(int(r["qre_executed_restarts"]) for r in by_config["cfg_gated_adaptfix"] if r["benchmark_name"] == b)
        act_rsts.append(act_r)
        gat_rsts.append(gat_r)

    idx = np.arange(len(bmk_names))
    plt.figure(figsize=(13, 5), dpi=300)
    plt.bar(idx - 0.18, act_rsts, width=0.35, label="Ungated Active QRE", color="#C44E52", edgecolor="black", linewidth=0.5)
    plt.bar(idx + 0.18, gat_rsts, width=0.35, label="Stagnation-Gated QRE", color="#55A868", edgecolor="black", linewidth=0.5)
    plt.xticks(idx, short_names, rotation=90, fontsize=7.5)
    plt.ylabel("Total QRE Restarts Across 3 Repetitions")
    plt.title("Step 41: Extra QRE Restarts Executed (Ungated vs Stagnation-Gated)")
    plt.legend(frameon=True, fontsize=9)
    plt.tight_layout()
    fig4_path = FIG_DIR / "fig_qre_gated_restart_counts.png"
    plt.savefig(fig4_path)
    plt.close()
    print(f"[+] Saved: {fig4_path}")

    # -------------------------------------------------------------
    # Figure 5: Runtime and Peak Memory Scaling
    # -------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
    wall_means = [mean([float(r["wall_time_s"]) for r in by_config[k]]) for k in config_keys]
    mem_means = [mean([float(r["memory_mb"]) for r in by_config[k]]) for k in config_keys]

    ax2 = ax1.twinx()
    b1 = ax1.bar(np.arange(len(labels)) - 0.18, wall_means, width=0.35, label="Wall Time (s)", color="#4C72B0", edgecolor="black", linewidth=0.6)
    b2 = ax2.bar(np.arange(len(labels)) + 0.18, mem_means, width=0.35, label="Peak Memory (MB)", color="#8172B2", edgecolor="black", linewidth=0.6)

    ax1.set_ylabel("Mean Wall-Clock Time (s)", color="#4C72B0")
    ax2.set_ylabel("Mean Peak Memory (MB)", color="#8172B2")
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=15, ha="right")
    ax1.set_title("Step 41: Mean Runtime and Peak Memory Scaling")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True)
    plt.tight_layout()
    fig5_path = FIG_DIR / "fig_qre_gated_runtime_memory.png"
    plt.savefig(fig5_path)
    plt.close()
    print(f"[+] Saved: {fig5_path}")

if __name__ == "__main__":
    main()

