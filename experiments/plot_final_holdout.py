#!/usr/bin/env python3
"""
plot_final_holdout.py - Generate Academic Visualizations for Final Holdout Evaluation
Step 37: Adaptive Restart and Nogood Reuse for Constraint Satisfaction

Generates 7 publication-quality figures:
  1. fig01_par2_cputime_comparison.png
  2. fig02_paired_runtime_vs_glucose.png
  3. fig03_per_family_runtimes.png
  4. fig04_conflict_counts_informative.png
  5. fig05_genuine_restarts_by_strategy.png
  6. fig06_clause_reductions_and_memory.png
  7. fig07_benchmark_difficulty_distribution.png
"""

import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Ensure output directory exists
OUT_DIR = os.path.join("docs", "figures", "final_holdout")
os.makedirs(OUT_DIR, exist_ok=True)

# Set global matplotlib style
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# Color palette
PALETTE = {
    "cfg01_baseline_base": "#1f77b4",       # Blue
    "cfg02_v1_base": "#ff7f0e",             # Orange
    "cfg03_v3dd_base": "#2ca02c",           # Green
    "cfg04_noheuristic_base": "#d62728",    # Red
    "cfg05_baseline_adaptfix": "#9467bd",   # Purple
    "cfg06_v1_adaptfix": "#8c564b",         # Brown
    "cfg07_v3dd_adaptfix": "#e377c2",       # Pink
    "cfg08_noheuristic_adaptfix": "#7f7f7f" # Grey
}

CONFIG_SHORT_NAMES = {
    "cfg01_baseline_base": "Baseline (Orig.)",
    "cfg02_v1_base": "V1 Adaptive",
    "cfg03_v3dd_base": "V3 Drawdown",
    "cfg04_noheuristic_base": "No-Heuristic",
    "cfg05_baseline_adaptfix": "Baseline + AdaptFix",
    "cfg06_v1_adaptfix": "V1 + AdaptFix",
    "cfg07_v3dd_adaptfix": "V3 DD + AdaptFix",
    "cfg08_noheuristic_adaptfix": "No-Heur + AdaptFix"
}

CONFIG_ORDER = [
    "cfg01_baseline_base",
    "cfg02_v1_base",
    "cfg03_v3dd_base",
    "cfg04_noheuristic_base",
    "cfg05_baseline_adaptfix",
    "cfg06_v1_adaptfix",
    "cfg07_v3dd_adaptfix",
    "cfg08_noheuristic_adaptfix"
]

def load_master_data():
    master_path = os.path.join("experiments", "results", "final_holdout", "master_results.csv")
    rows = []
    with open(master_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def load_aggregated_data():
    agg_path = os.path.join("experiments", "results", "final_holdout", "benchmark_aggregated_summary.csv")
    rows = []
    with open(agg_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

# -------------------------------------------------------------
# Figure 1: PAR-2 and CPU Time Comparison Across 8 Configurations
# -------------------------------------------------------------
def plot_fig01(master_rows):
    print("Generating Figure 1: PAR-2 & CPU Time Comparison...")
    
    cfg_data = {cfg: {"wall": [], "cpu": []} for cfg in CONFIG_ORDER}
    for r in master_rows:
        cfg = r["config_id"]
        cfg_data[cfg]["wall"].append(float(r["wall_time_s"]))
        cfg_data[cfg]["cpu"].append(float(r["process_cpu_time_s"]))
        
    labels = [CONFIG_SHORT_NAMES[c] for c in CONFIG_ORDER]
    wall_means = [np.mean(cfg_data[c]["wall"]) for c in CONFIG_ORDER]
    cpu_means = [np.mean(cfg_data[c]["cpu"]) for c in CONFIG_ORDER]
    wall_errs = [np.std(cfg_data[c]["wall"]) / np.sqrt(len(cfg_data[c]["wall"])) for c in CONFIG_ORDER]
    cpu_errs = [np.std(cfg_data[c]["cpu"]) / np.sqrt(len(cfg_data[c]["cpu"])) for c in CONFIG_ORDER]
    
    x = np.arange(len(CONFIG_ORDER))
    width = 0.38
    
    fig, ax = plt.subplots(figsize=(10, 5))
    rects1 = ax.bar(x - width/2, wall_means, width, yerr=wall_errs, label="Mean PAR-2 Wall Time (s)",
                    color="#2b5c8f", capsize=4, edgecolor="black", linewidth=0.8, alpha=0.9)
    rects2 = ax.bar(x + width/2, cpu_means, width, yerr=cpu_errs, label="Mean Process CPU Time (s)",
                    color="#48a9a6", capsize=4, edgecolor="black", linewidth=0.8, alpha=0.9)
    
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Configuration Performance: Mean PAR-2 Wall Time vs Process CPU Time\n(1,152 Total Executions, 48 Benchmarks × 3 Reps)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.legend(frameon=True, facecolor="white", edgecolor="none")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    
    # Value annotations on top of bars
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}s", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}s", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8, color="#005f5f")
        
    ax.set_ylim(0, max(wall_means) * 1.25)
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig01_par2_cputime_comparison.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 2: Paired Runtime Comparison: V3 Drawdown vs Native Glucose
# -------------------------------------------------------------
def plot_fig02(agg_rows):
    print("Generating Figure 2: Paired Runtime vs Native Glucose...")
    
    benchmarks = {}
    for r in agg_rows:
        bid = r["benchmark_id"]
        cfg = r["config_id"]
        if bid not in benchmarks:
            benchmarks[bid] = {"name": r["benchmark_name"], "family": r["family"]}
        benchmarks[bid][cfg] = float(r["wall_time_mean"])
        
    glucose_times = []
    v3_times = []
    names = []
    families = []
    
    for bid, data in sorted(benchmarks.items()):
        if "cfg01_baseline_base" in data and "cfg03_v3dd_base" in data:
            glucose_times.append(data["cfg01_baseline_base"])
            v3_times.append(data["cfg03_v3dd_base"])
            names.append(data["name"])
            families.append(data["family"])
            
    glucose_times = np.array(glucose_times)
    v3_times = np.array(v3_times)
    
    fig, (ax_scatter, ax_delta) = plt.subplots(1, 2, figsize=(13, 5.5))
    
    # Panel A: Log-Log Scatter Plot
    # Add minimal epsilon for log display (0.001s minimum)
    eps = 0.001
    g_plot = np.maximum(glucose_times, eps)
    v_plot = np.maximum(v3_times, eps)
    
    family_colors = {
        "circuit_equivalence": "#1f77b4",
        "hanoi_towers": "#e377c2",
        "pigeonhole_hard": "#d62728",
        "qg_quasi_groups": "#2ca02c",
        "random_3sat_uf": "#ff7f0e"
    }
    
    for fam, color in family_colors.items():
        mask = [f == fam for f in families]
        ax_scatter.scatter(g_plot[mask], v_plot[mask], label=fam, color=color, alpha=0.85, s=45, edgecolors="k", linewidth=0.5)
        
    min_val = min(g_plot.min(), v_plot.min()) * 0.7
    max_val = max(g_plot.max(), v_plot.max()) * 1.5
    ax_scatter.plot([min_val, max_val], [min_val, max_val], "k--", alpha=0.6, label="Parity (y = x)")
    
    ax_scatter.set_xscale("log")
    ax_scatter.set_yscale("log")
    ax_scatter.set_xlabel("Native Glucose Baseline Mean Wall Time (s)")
    ax_scatter.set_ylabel("V3 Drawdown Mean Wall Time (s)")
    ax_scatter.set_title("A: Per-Benchmark Runtime Scatter (Log-Log Scale)", fontweight="bold")
    ax_scatter.grid(True, which="both", linestyle=":", alpha=0.5)
    ax_scatter.legend(loc="upper left", frameon=True, fontsize=8)
    
    # Annotate outlier instances
    for i, name in enumerate(names):
        if name in ["hanoi5.cnf", "php_10p_8h.cnf", "php_10p_9h.cnf", "hanoi4.cnf"]:
            ax_scatter.annotate(name, (g_plot[i], v_plot[i]),
                                xytext=(6, -6), textcoords="offset points", fontsize=8, fontweight="bold")
            
    # Panel B: Delta Bar Plot (V3 - Glucose)
    deltas = v3_times - glucose_times
    # Filter to non-trivial deltas (|delta| > 0.001) for readability
    sorted_indices = np.argsort(deltas)
    
    # Show informative benchmarks with non-zero deltas
    sub_idx = [i for i in sorted_indices if abs(deltas[i]) >= 0.005]
    if len(sub_idx) == 0:
        sub_idx = sorted_indices[-15:]
        
    sub_names = [names[i].replace(".cnf", "") for i in sub_idx]
    sub_deltas = [deltas[i] for i in sub_idx]
    colors = ["#2ca02c" if d < 0 else "#d62728" for d in sub_deltas]
    
    y_pos = np.arange(len(sub_names))
    ax_delta.barh(y_pos, sub_deltas, color=colors, edgecolor="black", linewidth=0.6)
    ax_delta.set_yticks(y_pos)
    ax_delta.set_yticklabels(sub_names, fontsize=8)
    ax_delta.axvline(0, color="black", linewidth=0.8, linestyle="-")
    ax_delta.set_xlabel("Runtime Difference: V3 Drawdown - Baseline Glucose (s)")
    ax_delta.set_title("B: Benchmark Runtime Difference (Informative Instances)\n(Green = V3 Faster, Red = Baseline Faster)", fontweight="bold")
    ax_delta.grid(axis="x", linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig02_paired_runtime_vs_glucose.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 3: Per-Family Runtimes Across Configurations
# -------------------------------------------------------------
def plot_fig03(master_rows):
    print("Generating Figure 3: Per-Family Runtimes...")
    
    families = sorted(list(set(r["family"] for r in master_rows)))
    family_labels = [f.replace("_", " ").title() for f in families]
    
    # Calculate mean runtime per (family, config)
    fam_cfg_means = {fam: {} for fam in families}
    for fam in families:
        for cfg in CONFIG_ORDER:
            times = [float(r["wall_time_s"]) for r in master_rows if r["family"] == fam and r["config_id"] == cfg]
            fam_cfg_means[fam][cfg] = np.mean(times)
            
    fig, ax = plt.subplots(figsize=(12, 6))
    
    n_fam = len(families)
    n_cfg = len(CONFIG_ORDER)
    x = np.arange(n_fam)
    bar_width = 0.85 / n_cfg
    
    for i, cfg in enumerate(CONFIG_ORDER):
        means = [fam_cfg_means[fam][cfg] for fam in families]
        offset = (i - n_cfg / 2 + 0.5) * bar_width
        ax.bar(x + offset, means, bar_width, label=CONFIG_SHORT_NAMES[cfg],
               color=PALETTE[cfg], edgecolor="black", linewidth=0.5)
        
    ax.set_ylabel("Mean Wall Time (s)")
    ax.set_title("Holdout Benchmark Performance by Family and Configuration", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(family_labels, rotation=15, ha="right", fontweight="medium")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    
    # Use log scale on y because hanoi_towers is ~1.7s while circuit_equivalence is ~0.003s
    ax.set_yscale("log")
    ax.set_ylabel("Mean Wall Time (s, Log Scale)")
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
    
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig03_per_family_runtimes.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 4: Conflict Counts on Informative Benchmarks
# -------------------------------------------------------------
def plot_fig04(agg_rows):
    print("Generating Figure 4: Conflict Counts on Informative Benchmarks...")
    
    # Identify benchmarks with > 0 conflicts in at least one config
    benchmarks = {}
    for r in agg_rows:
        bid = r["benchmark_id"]
        if bid not in benchmarks:
            benchmarks[bid] = {"name": r["benchmark_name"], "conflicts": {}}
        benchmarks[bid]["conflicts"][r["config_id"]] = float(r["conflicts_mean"])
        
    informative_bids = [bid for bid, data in benchmarks.items() if any(c > 0 for c in data["conflicts"].values())]
    trivial_bids = [bid for bid, data in benchmarks.items() if all(c == 0 for c in data["conflicts"].values())]
    
    # Sum of conflicts on informative benchmarks per configuration
    cfg_conflicts = {cfg: sum(benchmarks[bid]["conflicts"].get(cfg, 0) for bid in informative_bids) for cfg in CONFIG_ORDER}
    
    labels = [CONFIG_SHORT_NAMES[c] for c in CONFIG_ORDER]
    values = [cfg_conflicts[c] for c in CONFIG_ORDER]
    colors = [PALETTE[c] for c in CONFIG_ORDER]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1, 2]})
    
    # Left: Pie chart of benchmark breakdown (Trivial 0-conflict vs Informative)
    counts = [len(trivial_bids), len(informative_bids)]
    pie_labels = [f"0-Conflict Trivial\n({len(trivial_bids)} / 48 = {len(trivial_bids)/48*100:.1f}%)",
                  f"Informative (>0 Conflicts)\n({len(informative_bids)} / 48 = {len(informative_bids)/48*100:.1f}%)"]
    ax1.pie(counts, labels=pie_labels, autopct="%1.1f%%", startangle=140,
            colors=["#aec7e8", "#1f77b4"], wedgeprops={"edgecolor": "k", "linewidth": 0.8})
    ax1.set_title("A: Benchmark Partition (48 Total)", fontweight="bold")
    
    # Right: Total Conflicts on Informative Instances
    x = np.arange(len(CONFIG_ORDER))
    bars = ax2.bar(x, [v / 1000 for v in values], color=colors, edgecolor="black", linewidth=0.8)
    ax2.set_ylabel("Total Conflicts (Thousands, across 33 instances × 3 reps)")
    ax2.set_title("B: Cumulative Conflicts on 33 Informative Benchmarks", fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=30, ha="right")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    
    for bar in bars:
        h = bar.get_height()
        ax2.annotate(f"{h:,.0f}k", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig04_conflict_counts_informative.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 5: Genuine Restarts by Strategy
# -------------------------------------------------------------
def safe_int(val, default=0):
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default

def safe_float(val, default=0.0):
    if val is None or val == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default

def plot_fig05(master_rows):
    print("Generating Figure 5: Genuine Restarts by Strategy...")
    
    cfg_restarts = {cfg: [] for cfg in CONFIG_ORDER}
    cfg_v3_restarts = {cfg: [] for cfg in CONFIG_ORDER}
    
    for r in master_rows:
        cfg = r["config_id"]
        cfg_restarts[cfg].append(safe_int(r["genuine_restarts"]))
        cfg_v3_restarts[cfg].append(safe_int(r["v3_executed_restarts"]))
        
    total_restarts = [sum(cfg_restarts[c]) for c in CONFIG_ORDER]
    mean_restarts = [np.mean(cfg_restarts[c]) for c in CONFIG_ORDER]
    total_v3_restarts = [sum(cfg_v3_restarts[c]) for c in CONFIG_ORDER]
    
    labels = [CONFIG_SHORT_NAMES[c] for c in CONFIG_ORDER]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    
    x = np.arange(len(CONFIG_ORDER))
    
    # Left: Total Restarts (Log Scale because Glucose has ~20k while V3 has 15 and No-Heuristic has 0)
    # Add +0.1 for log display
    plot_vals = [max(v, 0.1) for v in total_restarts]
    bars1 = ax1.bar(x, plot_vals, color=[PALETTE[c] for c in CONFIG_ORDER], edgecolor="black", linewidth=0.8)
    ax1.set_yscale("log")
    ax1.set_ylabel("Total Genuine Restarts (Log Scale)")
    ax1.set_title("A: Total Genuine Restarts Across Entire Holdout Suite (144 runs/cfg)", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=30, ha="right")
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    
    for i, bar in enumerate(bars1):
        real_val = total_restarts[i]
        ax1.annotate(f"{real_val:,}", xy=(bar.get_x() + bar.get_width() / 2, max(real_val, 0.1)),
                     xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    # Right: Per-Benchmark Restart Breakdown for V3 Drawdown (cfg03)
    # Highlight that restarts occurred ONLY on hanoi5.cnf
    v3_runs = [r for r in master_rows if r["config_id"] == "cfg03_v3dd_base"]
    b_restarts = {}
    for r in v3_runs:
        b = r["benchmark_name"]
        b_restarts[b] = b_restarts.get(b, 0) + safe_int(r["v3_executed_restarts"])
        
    # Top 5 benchmarks by V3 restarts
    top_b = sorted(b_restarts.items(), key=lambda x: x[1], reverse=True)[:6]
    b_names = [b[0].replace(".cnf", "") for b in top_b]
    b_counts = [b[1] for b in top_b]
    
    ax2.bar(b_names, b_counts, color="#2ca02c", edgecolor="black", linewidth=0.8, width=0.5)
    ax2.set_ylabel("V3 Executed Drawdown Restarts (Sum across 3 reps)")
    ax2.set_title("B: V3 Drawdown Restart Selectivity by Benchmark\n(15 total in hanoi5.cnf, exactly 0 across other 47 benchmarks)", fontweight="bold")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    for i, count in enumerate(b_counts):
        ax2.annotate(f"{count}", xy=(i, count), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
        
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig05_genuine_restarts_by_strategy.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 6: Clause Reductions and Memory Footprint
# -------------------------------------------------------------
def plot_fig06(master_rows):
    print("Generating Figure 6: Clause Reductions & Memory Footprint...")
    
    # Compare Baseline reduction vs Adaptive-Fixed across the 4 paired strategies:
    pairs = [
        ("Baseline (Orig)", "cfg01_baseline_base", "cfg05_baseline_adaptfix"),
        ("V1 Adaptive", "cfg02_v1_base", "cfg06_v1_adaptfix"),
        ("V3 Drawdown", "cfg03_v3dd_base", "cfg07_v3dd_adaptfix"),
        ("No-Heuristic", "cfg04_noheuristic_base", "cfg08_noheuristic_adaptfix")
    ]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    
    x = np.arange(len(pairs))
    width = 0.35
    
    # Left: Database Reductions Count
    base_reductions = [sum(safe_int(r["reduce_db_count"]) for r in master_rows if r["config_id"] == p[1]) for p in pairs]
    adapt_reductions = [sum(safe_int(r["reduce_db_count"]) for r in master_rows if r["config_id"] == p[2]) for p in pairs]
    
    rects1 = ax1.bar(x - width/2, base_reductions, width, label="Baseline Reduction", color="#3b528b", edgecolor="black", linewidth=0.8)
    rects2 = ax1.bar(x + width/2, adapt_reductions, width, label="Adaptive-Fixed Retention", color="#5dc863", edgecolor="black", linewidth=0.8)
    ax1.set_ylabel("Total Database Reductions (across 144 runs/cfg)")
    ax1.set_title("A: Total Clause DB Reductions Triggered", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels([p[0] for p in pairs])
    ax1.legend(frameon=True)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    
    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:,}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    for r in rects2:
        h = r.get_height()
        ax1.annotate(f"{h:,}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        
    # Right: Peak Process RSS Memory (MB)
    base_mem = [np.mean([safe_float(r["process_peak_rss_mb"]) for r in master_rows if r["config_id"] == p[1]]) for p in pairs]
    adapt_mem = [np.mean([safe_float(r["process_peak_rss_mb"]) for r in master_rows if r["config_id"] == p[2]]) for p in pairs]
    
    rects3 = ax2.bar(x - width/2, base_mem, width, label="Baseline Reduction", color="#3b528b", edgecolor="black", linewidth=0.8)
    rects4 = ax2.bar(x + width/2, adapt_mem, width, label="Adaptive-Fixed Retention", color="#5dc863", edgecolor="black", linewidth=0.8)
    ax2.set_ylabel("Mean Peak Process RSS Memory (MB)")
    ax2.set_title("B: Mean Peak Memory Footprint (MB)", fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([p[0] for p in pairs])
    ax2.legend(frameon=True)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    
    for r in rects3:
        h = r.get_height()
        ax2.annotate(f"{h:.1f}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    for r in rects4:
        h = r.get_height()
        ax2.annotate(f"{h:.1f}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    
    rects1 = ax1.bar(x - width/2, base_reductions, width, label="Baseline Reduction", color="#3b528b", edgecolor="black", linewidth=0.8)
    rects2 = ax1.bar(x + width/2, adapt_reductions, width, label="Adaptive-Fixed Retention", color="#5dc863", edgecolor="black", linewidth=0.8)
    ax1.set_ylabel("Total Database Reductions (across 144 runs/cfg)")
    ax1.set_title("A: Total Clause DB Reductions Triggered", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels([p[0] for p in pairs])
    ax1.legend(frameon=True)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    
    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:,}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    for r in rects2:
        h = r.get_height()
        ax1.annotate(f"{h:,}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        
    # Right: Peak Process RSS Memory (MB)
    base_mem = [np.mean([float(r["process_peak_rss_mb"]) for r in master_rows if r["config_id"] == p[1]]) for p in pairs]
    adapt_mem = [np.mean([float(r["process_peak_rss_mb"]) for r in master_rows if r["config_id"] == p[2]]) for p in pairs]
    
    rects3 = ax2.bar(x - width/2, base_mem, width, label="Baseline Reduction", color="#3b528b", edgecolor="black", linewidth=0.8)
    rects4 = ax2.bar(x + width/2, adapt_mem, width, label="Adaptive-Fixed Retention", color="#5dc863", edgecolor="black", linewidth=0.8)
    ax2.set_ylabel("Mean Peak Process RSS Memory (MB)")
    ax2.set_title("B: Mean Peak Memory Footprint (MB)", fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([p[0] for p in pairs])
    ax2.legend(frameon=True)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    
    for r in rects3:
        h = r.get_height()
        ax2.annotate(f"{h:.1f}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    for r in rects4:
        h = r.get_height()
        ax2.annotate(f"{h:.1f}", xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        
    ax2.set_ylim(0, max(max(base_mem), max(adapt_mem)) * 1.25)
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig06_clause_reductions_and_memory.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 7: Benchmark Difficulty Cumulative Distribution (CDF)
# -------------------------------------------------------------
def plot_fig07(master_rows):
    print("Generating Figure 7: Benchmark Difficulty CDF...")
    
    all_times = sorted([float(r["wall_time_s"]) for r in master_rows])
    n = len(all_times)
    y_cdf = np.arange(1, n + 1) / n * 100.0
    
    fig, ax = plt.subplots(figsize=(9, 5.5))
    
    ax.plot(all_times, y_cdf, color="#1f77b4", linewidth=2.2, label="All 1,152 Holdout Executions")
    
    # Add individual CDF curves for top configs
    for cfg in ["cfg01_baseline_base", "cfg03_v3dd_base", "cfg05_baseline_adaptfix", "cfg04_noheuristic_base"]:
        times = sorted([float(r["wall_time_s"]) for r in master_rows if r["config_id"] == cfg])
        m = len(times)
        y = np.arange(1, m + 1) / m * 100.0
        ax.plot(times, y, linestyle="--", linewidth=1.5, color=PALETTE[cfg], label=CONFIG_SHORT_NAMES[cfg])
        
    ax.set_xscale("log")
    ax.set_xlabel("Solve Wall Time (seconds, Log Scale)")
    ax.set_ylabel("Cumulative Solved Percentage (%)")
    ax.set_title("Benchmark Hardness Cumulative Distribution (CDF)\n(Demonstrating Suite Skew Toward Low-Latency Instances)", fontweight="bold")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    
    # Threshold reference lines
    t_50ms = np.searchsorted(all_times, 0.05) / n * 100.0
    t_100ms = np.searchsorted(all_times, 0.10) / n * 100.0
    t_500ms = np.searchsorted(all_times, 0.50) / n * 100.0
    t_1000ms = np.searchsorted(all_times, 1.00) / n * 100.0
    
    ax.axvline(0.05, color="red", linestyle=":", alpha=0.7)
    ax.axvline(0.10, color="orange", linestyle=":", alpha=0.7)
    ax.axvline(1.00, color="purple", linestyle=":", alpha=0.7)
    
    ax.annotate(f"<= 50 ms: {t_50ms:.1f}%", xy=(0.05, t_50ms), xytext=(0.015, 55),
                arrowprops=dict(facecolor="black", arrowstyle="->", lw=0.8), fontsize=8, fontweight="bold")
    ax.annotate(f"<= 100 ms: {t_100ms:.1f}%", xy=(0.10, t_100ms), xytext=(0.12, 70),
                arrowprops=dict(facecolor="black", arrowstyle="->", lw=0.8), fontsize=8, fontweight="bold")
    ax.annotate(f"<= 1.0 s: {t_1000ms:.1f}%", xy=(1.00, t_1000ms), xytext=(0.3, 85),
                arrowprops=dict(facecolor="black", arrowstyle="->", lw=0.8), fontsize=8, fontweight="bold")
    
    ax.set_ylim(0, 105)
    ax.legend(loc="lower right", frameon=True)
    
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "fig07_benchmark_difficulty_distribution.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def main():
    print("Starting generation of Step 37 holdout evaluation figures...")
    master_rows = load_master_data()
    agg_rows = load_aggregated_data()
    print(f"Loaded {len(master_rows)} master rows and {len(agg_rows)} aggregated rows.")
    
    plot_fig01(master_rows)
    plot_fig02(agg_rows)
    plot_fig03(master_rows)
    plot_fig04(agg_rows)
    plot_fig05(master_rows)
    plot_fig06(master_rows)
    plot_fig07(master_rows)
    
    print("All 7 figures generated successfully in docs/figures/final_holdout/!")

if __name__ == "__main__":
    main()
