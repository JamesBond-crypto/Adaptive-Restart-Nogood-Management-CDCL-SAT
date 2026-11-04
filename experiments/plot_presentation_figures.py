#!/usr/bin/env python3
"""
experiments/plot_presentation_figures.py

Generates five clean, presentation-ready, publication-grade figures for the
final academic defense / presentation:
  1. fig_pres01_overall_strategy_comparison.png: Overall PAR-2 & Solved Count
  2. fig_pres02_dev_vs_holdout_comparison.png: Development vs Holdout Context
  3. fig_pres03_qre_gating_mitigation.png: Gated vs Ungated QRE Thrashing Mitigation
  4. fig_pres04_genuine_restart_wins.png: Genuine Restart Wins on Hard Instances
  5. fig_pres05_nogood_retention_impact.png: Nogood Retention Impact Ablation
"""

import os
import csv
import math
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WORKSPACE = Path(r"D:\DAC_203@Project")
DEV_CSV = WORKSPACE / "experiments" / "results" / "qre_gated_full_development" / "master_results.csv"
HOLDOUT_CSV = WORKSPACE / "experiments" / "results" / "final_holdout" / "master_results.csv"
OUT_DIR = WORKSPACE / "docs" / "figures" / "presentation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Styling configuration
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    dev_rows = load_data(DEV_CSV)
    holdout_rows = load_data(HOLDOUT_CSV)

    # -------------------------------------------------------------
    # Figure 1: Overall Strategy Comparison (Development Suite)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))
    
    cfg_order = [
        "cfg_v3dd_adaptfix",
        "cfg01_baseline_base",
        "cfg_active_adaptfix",
        "cfg_gated_adaptfix",
        "cfg05_baseline_adaptfix",
        "cfg_gated_base"
    ]
    cfg_labels = [
        "V3 Drawdown\n+ AdaptFix",
        "Original\nGlucose Base",
        "Ungated QRE\n+ AdaptFix",
        "Gated QRE\n+ AdaptFix",
        "Glucose\n+ AdaptFix",
        "Gated QRE\n+ Base"
    ]
    colors = ["#2b8a3e", "#1971c2", "#e03131", "#f08c00", "#7950f2", "#868e96"]

    par2_scores = []
    solved_counts = []
    
    by_cfg_dev = defaultdict(list)
    for r in dev_rows:
        by_cfg_dev[r["config_id"]].append(r)

    for cid in cfg_order:
        runs = by_cfg_dev[cid]
        s = sum(1 for r in runs if r["status"] in ("SAT", "UNSAT"))
        p2 = sum(float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 30.0 for r in runs) / len(runs)
        par2_scores.append(p2)
        solved_counts.append(s)

    # Subplot 1: PAR-2
    bars1 = ax1.bar(range(len(cfg_order)), par2_scores, color=colors, width=0.6, edgecolor="black", linewidth=0.8)
    ax1.set_xticks(range(len(cfg_order)))
    ax1.set_xticklabels(cfg_labels)
    ax1.set_ylabel("PAR-2 Time (seconds, lower is better)")
    ax1.set_title("Overall PAR-2 Runtime (15s Cutoff, 30s Penalty)")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 4.2)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.08, f"{yval:.2f}s", ha="center", va="bottom", fontweight="bold", fontsize=10)

    # Subplot 2: Solved Count
    bars2 = ax2.bar(range(len(cfg_order)), solved_counts, color=colors, width=0.6, edgecolor="black", linewidth=0.8)
    ax2.set_xticks(range(len(cfg_order)))
    ax2.set_xticklabels(cfg_labels)
    ax2.set_ylabel("Solved Runs (out of 108, higher is better)")
    ax2.set_title("Total Solved Runs (36 Benchmarks × 3 Repetitions)")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(90, 105)
    for bar in bars2:
        yval = bar.get_height()
        pct = (yval / 108.0) * 100
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f"{yval}/108\n({pct:.1f}%)", ha="center", va="bottom", fontweight="bold", fontsize=9)

    plt.suptitle("Figure 1: Full Development Suite Strategy Evaluation (648 Total Runs)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig1_path = OUT_DIR / "fig_pres01_overall_strategy_comparison.png"
    plt.savefig(fig1_path)
    plt.close()
    print(f"Generated: {fig1_path.name}")

    # -------------------------------------------------------------
    # Figure 2: Development vs Holdout Context
    # -------------------------------------------------------------
    # Shared configurations between Development and Holdout:
    # 1. cfg01_baseline_base
    # 2. cfg05_baseline_adaptfix
    # 3. cfg_v3dd_adaptfix (cfg07 in holdout)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.0))

    shared_dev_cids = ["cfg01_baseline_base", "cfg05_baseline_adaptfix", "cfg_v3dd_adaptfix"]
    shared_holdout_cids = ["cfg01_baseline_base", "cfg05_baseline_adaptfix", "cfg07_v3dd_adaptfix"]
    shared_labels = ["Native Glucose\nBaseline", "Glucose\n+ AdaptFix", "V3 Drawdown\n+ AdaptFix"]

    # Holdout data
    by_cfg_h = defaultdict(list)
    for r in holdout_rows:
        by_cfg_h[r["config_id"]].append(r)

    h_par2 = [sum(float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 60.0 for r in by_cfg_h[cid]) / len(by_cfg_h[cid]) for cid in shared_holdout_cids]
    d_par2 = [sum(float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 30.0 for r in by_cfg_dev[cid]) / len(by_cfg_dev[cid]) for cid in shared_dev_cids]

    # Holdout subplot
    bars_h = ax1.bar(range(3), h_par2, color=["#1971c2", "#2b8a3e", "#f08c00"], width=0.55, edgecolor="black")
    ax1.set_xticks(range(3))
    ax1.set_xticklabels(shared_labels)
    ax1.set_ylabel("Holdout PAR-2 Time (seconds, 30s cutoff)")
    ax1.set_title("Holdout Suite (48 Benchmarks, 1,152 Runs)\nFast / Easy Benchmark Horizon (Mean < 0.35s)")
    ax1.set_ylim(0, 0.42)
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    for bar in bars_h:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.01, f"{yval:.4f}s", ha="center", va="bottom", fontweight="bold")
    ax1.text(1, 0.36, "Champion: Glucose + AdaptFix\n(Lowest PAR-2 & Conflicts)", ha="center", bbox=dict(boxstyle="round,pad=0.3", fc="#d3f9d8", ec="#2b8a3e"))

    # Development subplot
    bars_d = ax2.bar(range(3), d_par2, color=["#1971c2", "#7950f2", "#2b8a3e"], width=0.55, edgecolor="black")
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(shared_labels)
    ax2.set_ylabel("Development PAR-2 Time (seconds, 15s cutoff)")
    ax2.set_title("Development Suite (36 Benchmarks, 648 Runs)\nHard / Long Search Horizon (Timeouts > 0)")
    ax2.set_ylim(0, 4.2)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    for bar in bars_d:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f"{yval:.4f}s", ha="center", va="bottom", fontweight="bold")
    ax2.text(2, 3.7, "Champion: V3 Drawdown + AdaptFix\n(Fastest on Hard Structured Formulas)", ha="center", bbox=dict(boxstyle="round,pad=0.3", fc="#d3f9d8", ec="#2b8a3e"))

    plt.suptitle("Figure 2: Reconciliation of Development vs Quarantined Holdout Results", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig2_path = OUT_DIR / "fig_pres02_dev_vs_holdout_comparison.png"
    plt.savefig(fig2_path)
    plt.close()
    print(f"Generated: {fig2_path.name}")

    # -------------------------------------------------------------
    # Figure 3: Gated vs Ungated QRE Thrashing Mitigation
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.0))

    # Subplot 1: Total Extra Restarts Executed (Active vs Gated)
    qre_rst_active = sum(int(r["qre_executed_restarts"]) for r in by_cfg_dev["cfg_active_adaptfix"])
    qre_rst_gated = sum(int(r["qre_executed_restarts"]) for r in by_cfg_dev["cfg_gated_adaptfix"])
    
    bars_rst = ax1.bar([0, 1], [qre_rst_active, qre_rst_gated], color=["#e03131", "#2b8a3e"], width=0.5, edgecolor="black")
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(["Ungated Active QRE\n(1,458 Restarts)", "Stagnation-Gated QRE\n(316 Restarts)"])
    ax1.set_ylabel("Total Extra Restarts Executed (108 Runs)")
    ax1.set_title("Suppression of Extraneous Restarts\n(-78.3% Drop via 1,500-Conflict Gate)")
    ax1.set_ylim(0, 1700)
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    for bar in bars_rst:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 35, f"{int(yval)}", ha="center", va="bottom", fontweight="bold", fontsize=11)
    ax1.text(0.5, 1450, "15,724 Sustained Volatility\nEvents Suppressed (76.6%)", ha="center", bbox=dict(boxstyle="round,pad=0.3", fc="#fff3bf", ec="#f08c00"))

    # Subplot 2: Random 3-SAT Thrashing Case Study (rand3sat_n175_c735_s1003)
    target_bmk = "rand3sat_n175_c735_s1003.cnf"
    b_runs = [r for r in dev_rows if r["benchmark_name"] == target_bmk]
    cfc_dict = defaultdict(list)
    for r in b_runs:
        cfc_dict[r["config_id"]].append(int(r["conflicts"]))

    plot_cids = ["cfg01_baseline_base", "cfg05_baseline_adaptfix", "cfg_active_adaptfix", "cfg_gated_adaptfix"]
    plot_labels = ["Native\nGlucose", "Glucose\n+ AdaptFix", "Ungated QRE\n(Thrashing Spike!)", "Gated QRE\n(Stabilized)"]
    plot_colors = ["#1971c2", "#7950f2", "#e03131", "#2b8a3e"]
    mean_cfcs = [sum(cfc_dict[c])/len(cfc_dict[c]) for c in plot_cids]

    bars_cfc = ax2.bar(range(4), mean_cfcs, color=plot_colors, width=0.55, edgecolor="black")
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(plot_labels)
    ax2.set_ylabel("Search Conflicts to Solution (lower is better)")
    ax2.set_title(f"Conflict Explosion Elimination\n({target_bmk})")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, 18500)
    for bar in bars_cfc:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 350, f"{int(yval):,}", ha="center", va="bottom", fontweight="bold")
    ax2.text(2, 16800, "+192.6% Explosion", ha="center", color="#e03131", fontweight="bold")
    ax2.text(3, 4000, "-80.4% Cfc Collapse", ha="center", color="#2b8a3e", fontweight="bold")

    plt.suptitle("Figure 3: Stagnation Gating Solves High-Frequency QRE Restart Thrashing", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig3_path = OUT_DIR / "fig_pres03_qre_gating_mitigation.png"
    plt.savefig(fig3_path)
    plt.close()
    print(f"Generated: {fig3_path.name}")

    # -------------------------------------------------------------
    # Figure 4: Specific Genuine Restart Wins on Hard Instances
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.0))

    # Benchmark 1: gcol_unsat_k10_c9.cnf (Graph Coloring, Hard UNSAT)
    bmk1 = "gcol_unsat_k10_c9.cnf"
    runs_b1 = [r for r in dev_rows if r["benchmark_name"] == bmk1]
    b1_cfc = defaultdict(list)
    b1_time = defaultdict(list)
    for r in runs_b1:
        b1_cfc[r["config_id"]].append(int(r["conflicts"]))
        b1_time[r["config_id"]].append(float(r["wall_time_s"]))

    cids_hard = ["cfg01_baseline_base", "cfg05_baseline_adaptfix", "cfg_gated_adaptfix", "cfg_v3dd_adaptfix"]
    labels_hard = ["Native Glucose", "Glucose+AdaptFix", "Gated QRE+AdaptFix", "V3 Drawdown+AdaptFix"]
    colors_hard = ["#1971c2", "#7950f2", "#f08c00", "#2b8a3e"]

    mean_cfc_b1 = [sum(b1_cfc[c])/len(b1_cfc[c]) for c in cids_hard]
    mean_time_b1 = [sum(b1_time[c])/len(b1_time[c]) for c in cids_hard]

    bars_b1 = ax1.bar(range(4), [c/1000.0 for c in mean_cfc_b1], color=colors_hard, width=0.55, edgecolor="black")
    ax1.set_xticks(range(4))
    ax1.set_xticklabels(labels_hard, rotation=15)
    ax1.set_ylabel("Conflicts to UNSAT Proof (×1,000, lower is better)")
    ax1.set_title(f"Graph Coloring Hard UNSAT\n({bmk1})")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 650)
    for i, bar in enumerate(bars_b1):
        yval = bar.get_height()
        tval = mean_time_b1[i]
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 12, f"{yval:.1f}k cfc\n({tval:.2f}s)", ha="center", va="bottom", fontweight="bold", fontsize=9)

    # Benchmark 2: php_10p_9h.cnf (Pigeonhole Principle, Hard UNSAT)
    bmk2 = "php_10p_9h.cnf"
    runs_b2 = [r for r in dev_rows if r["benchmark_name"] == bmk2]
    b2_time = defaultdict(list)
    b2_par2 = defaultdict(list)
    for r in runs_b2:
        b2_time[r["config_id"]].append(float(r["wall_time_s"]))
        b2_par2[r["config_id"]].append(float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 30.0)

    mean_par2_b2 = [sum(b2_par2[c])/len(b2_par2[c]) for c in cids_hard]
    solves_b2 = [sum(1 for r in runs_b2 if r["config_id"] == c and r["status"] in ("SAT", "UNSAT")) for c in cids_hard]

    bars_b2 = ax2.bar(range(4), mean_par2_b2, color=colors_hard, width=0.55, edgecolor="black")
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(labels_hard, rotation=15)
    ax2.set_ylabel("PAR-2 Time (seconds, lower is better)")
    ax2.set_title(f"Pigeonhole Principle Hard UNSAT\n({bmk2})")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, 26)
    for i, bar in enumerate(bars_b2):
        yval = bar.get_height()
        s_cnt = solves_b2[i]
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.6, f"{yval:.2f}s\n({s_cnt}/3 Solved)", ha="center", va="bottom", fontweight="bold", fontsize=9)

    plt.suptitle("Figure 4: Genuine Restart Interventions on Hard Combinatorial UNSAT Workloads", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig4_path = OUT_DIR / "fig_pres04_genuine_restart_wins.png"
    plt.savefig(fig4_path)
    plt.close()
    print(f"Generated: {fig4_path.name}")

    # -------------------------------------------------------------
    # Figure 5: Nogood Retention Impact (Adaptive-Fixed vs Baseline)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.2))

    # Compare Baseline reduction vs Adaptive-Fixed retention across 4 families in development
    family_map = [
        ("Graph Coloring", "Graph Coloring"),
        ("Pigeonhole Principle (PHP)", "Pigeonhole (PHP)"),
        ("Planted Satisfiable 3-SAT", "Planted 3-SAT"),
        ("Random 3-SAT", "Random 3-SAT")
    ]
    base_fam_p2 = []
    adapt_fam_p2 = []
    display_labels = []

    for fam_key, label in family_map:
        fam_runs_base = [r for r in by_cfg_dev["cfg01_baseline_base"] if r["family"] == fam_key]
        fam_runs_adapt = [r for r in by_cfg_dev["cfg05_baseline_adaptfix"] if r["family"] == fam_key]
        p2_b = sum(float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 30.0 for r in fam_runs_base) / len(fam_runs_base)
        p2_a = sum(float(r["wall_time_s"]) if r["status"] in ("SAT", "UNSAT") else 30.0 for r in fam_runs_adapt) / len(fam_runs_adapt)
        base_fam_p2.append(p2_b)
        adapt_fam_p2.append(p2_a)
        display_labels.append(label)

    x = np.arange(len(family_map))
    width = 0.35

    rects1 = ax.bar(x - width/2, base_fam_p2, width, label="Baseline Retention (cfg01)", color="#1971c2", edgecolor="black")
    rects2 = ax.bar(x + width/2, adapt_fam_p2, width, label="Adaptive-Fixed Retention (cfg05)", color="#7950f2", edgecolor="black")

    ax.set_ylabel("PAR-2 Time (seconds, log scale)")
    ax.set_yscale("log")
    ax.set_title("Nogood Retention Ablation by Benchmark Family (PAR-2 Log Scale)")
    ax.set_xticks(x)
    ax.set_xticklabels(display_labels)
    ax.legend(loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for i in range(len(family_map)):
        b_val = base_fam_p2[i]
        a_val = adapt_fam_p2[i]
        diff_pct = ((a_val - b_val) / b_val) * 100.0
        color = "#2b8a3e" if diff_pct < 0 else "#e03131"
        ax.text(i, max(b_val, a_val) * 1.25, f"{diff_pct:+.1f}%", ha="center", va="bottom", fontweight="bold", color=color, fontsize=10)

    plt.suptitle("Figure 5: Systematic Evaluation of Adaptive-Fixed Nogood Retention", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig5_path = OUT_DIR / "fig_pres05_nogood_retention_impact.png"
    plt.savefig(fig5_path)
    plt.close()
    print(f"Generated: {fig5_path.name}")

if __name__ == "__main__":
    main()
