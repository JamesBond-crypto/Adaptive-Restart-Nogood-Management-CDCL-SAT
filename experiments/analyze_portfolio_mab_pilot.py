#!/usr/bin/env python3
"""
Analysis script for the Step 44 Duration-Aware Restart Portfolio MAB Pilot.
Reads experiments/results/portfolio_mab_pilot/master_results.csv
and produces aggregated statistics, tables, and diagnostics.
"""

import csv
import math
from collections import defaultdict

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def median(lst):
    if not lst:
        return 0.0
    sorted_lst = sorted(lst)
    n = len(sorted_lst)
    mid = n // 2
    if n % 2 == 1:
        return sorted_lst[mid]
    else:
        return (sorted_lst[mid - 1] + sorted_lst[mid]) / 2.0

def get_family(bid):
    num = int(bid.replace('DEV_', ''))
    if 1 <= num <= 4:
        return 'Trivial'
    elif 5 <= num <= 8:
        return 'Medium'
    elif 9 <= num <= 12:
        return 'Hard Structured UNSAT'
    elif 13 <= num <= 16:
        return 'Hard Random SAT'
    return 'Other'

def main():
    csv_path = 'experiments/results/portfolio_mab_pilot/master_results.csv'
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows loaded: {len(rows)}")

    configs = [
        'cfg01_baseline_base',
        'cfg05_baseline_adaptfix',
        'cfg_v3dd_adaptfix',
        'cfg_mab_base',
        'cfg_mab_adaptfix'
    ]

    cfg_names = {
        'cfg01_baseline_base': 'Native Glucose + Baseline Reduction',
        'cfg05_baseline_adaptfix': 'Native Glucose + Adaptive-Fixed',
        'cfg_v3dd_adaptfix': 'V3 Drawdown + Adaptive-Fixed',
        'cfg_mab_base': 'Portfolio-MAB + Baseline Reduction',
        'cfg_mab_adaptfix': 'Portfolio-MAB + Adaptive-Fixed'
    }

    by_cfg = {cfg: [] for cfg in configs}
    for r in rows:
        cfg = r['config_id']
        if cfg in by_cfg:
            by_cfg[cfg].append(r)

    # 1. Overall Performance Table
    print("\n" + "="*80)
    print("1. OVERALL 5-CONFIGURATION PERFORMANCE TABLE (N=48 runs each, 15s timeout)")
    print("="*80)

    print(f"{'Configuration':<35} | {'Solved':<7} | {'PAR-2':<8} | {'Mean Wall':<9} | {'Mean CPU':<8} | {'Mean Cfc':<10} | {'Med Cfc':<8} | {'Mean Dec':<9} | {'Mean Rest':<9} | {'RedDB':<6} | {'Mem MB':<6}")
    print("-" * 130)

    stats_by_cfg = {}

    for cfg in configs:
        c_rows = by_cfg[cfg]
        n_total = len(c_rows)
        solved_rows = [r for r in c_rows if r['status'] in ('SAT', 'UNSAT') and r['timed_out'] == 'False']
        n_solved = len(solved_rows)
        
        par2_times = [safe_float(r['par2_s']) for r in c_rows]
        mean_par2 = sum(par2_times) / len(par2_times) if par2_times else 0.0

        solved_wall = [safe_float(r['wall_time_s']) for r in solved_rows]
        mean_wall = sum(solved_wall) / len(solved_wall) if solved_wall else 0.0

        solved_cpu = [safe_float(r['cpu_time_s']) for r in solved_rows]
        mean_cpu = sum(solved_cpu) / len(solved_cpu) if solved_cpu else 0.0

        solved_cfc = [safe_int(r['conflicts']) for r in solved_rows]
        mean_cfc = sum(solved_cfc) / len(solved_cfc) if solved_cfc else 0.0
        med_cfc = median(solved_cfc)

        solved_dec = [safe_int(r['decisions']) for r in solved_rows]
        mean_dec = sum(solved_dec) / len(solved_dec) if solved_dec else 0.0

        solved_prop = [safe_int(r['propagations']) for r in solved_rows]
        mean_prop = sum(solved_prop) / len(solved_prop) if solved_prop else 0.0

        solved_rest = [safe_int(r['restarts']) for r in solved_rows]
        mean_rest = sum(solved_rest) / len(solved_rest) if solved_rest else 0.0

        solved_red = [safe_int(r['reduce_db']) for r in solved_rows]
        mean_red = sum(solved_red) / len(solved_red) if solved_red else 0.0

        mem_mb = [safe_float(r['memory_mb']) for r in solved_rows]
        mean_mem = sum(mem_mb) / len(mem_mb) if mem_mb else 0.0

        stats_by_cfg[cfg] = {
            'n_solved': n_solved,
            'n_total': n_total,
            'mean_par2': mean_par2,
            'mean_wall': mean_wall,
            'mean_cpu': mean_cpu,
            'mean_cfc': mean_cfc,
            'med_cfc': med_cfc,
            'mean_dec': mean_dec,
            'mean_prop': mean_prop,
            'mean_rest': mean_rest,
            'mean_red': mean_red,
            'mean_mem': mean_mem,
            'total_cfc': sum(solved_cfc),
            'total_dec': sum(solved_dec),
            'total_prop': sum(solved_prop),
            'total_rest': sum(solved_rest),
            'total_red': sum(solved_red),
        }

        print(f"{cfg_names[cfg]:<35} | {n_solved}/{n_total:<5} | {mean_par2:<8.4f} | {mean_wall:<9.4f} | {mean_cpu:<8.4f} | {mean_cfc:<10.1f} | {med_cfc:<8.0f} | {mean_dec:<9.1f} | {mean_rest:<9.1f} | {mean_red:<6.1f} | {mean_mem:<6.2f}")

    # 2. Per-Family Analysis
    print("\n" + "="*80)
    print("2. PER-FAMILY BREAKDOWN (PAR-2, Solved, Mean Conflicts)")
    print("="*80)

    families = ['Trivial', 'Medium', 'Hard Structured UNSAT', 'Hard Random SAT']
    for fam in families:
        print(f"\n--- Family: {fam} (12 runs per config) ---")
        print(f"{'Configuration':<35} | {'Solved':<7} | {'PAR-2 (s)':<9} | {'Mean Wall (s)':<13} | {'Mean Conflicts':<14} | {'Median Conflicts':<16}")
        print("-" * 105)
        for cfg in configs:
            f_rows = [r for r in by_cfg[cfg] if get_family(r['benchmark_id']) == fam]
            f_solved = [r for r in f_rows if r['status'] in ('SAT', 'UNSAT') and r['timed_out'] == 'False']
            n_sol = len(f_solved)
            f_par2 = sum(safe_float(r['par2_s']) for r in f_rows) / len(f_rows) if f_rows else 0.0
            f_wall = sum(safe_float(r['wall_time_s']) for r in f_solved) / len(f_solved) if f_solved else 0.0
            f_cfc = [safe_int(r['conflicts']) for r in f_solved]
            mean_c = sum(f_cfc) / len(f_cfc) if f_cfc else 0.0
            med_c = median(f_cfc)
            print(f"{cfg_names[cfg]:<35} | {n_sol}/{len(f_rows):<5} | {f_par2:<9.4f} | {f_wall:<13.4f} | {mean_c:<14.1f} | {med_c:<16.0f}")

    # 3. Instance-by-Instance Breakdown
    print("\n" + "="*80)
    print("3. INSTANCE-BY-INSTANCE MEAN WALL-CLOCK TIME & CONFLICTS (Mean over 3 reps)")
    print("="*80)
    bmks = []
    seen = set()
    for r in rows:
        bid = r['benchmark_id']
        bname = r['benchmark_name']
        cat = get_family(bid)
        if bid not in seen:
            seen.add(bid)
            bmks.append((bid, bname, cat))

    print(f"{'ID':<7} | {'Benchmark Name':<28} | {'Base Base (s)':<13} | {'Base AdFix (s)':<14} | {'V3DD AdFix (s)':<14} | {'MAB Base (s)':<12} | {'MAB AdFix (s)':<13}")
    print("-" * 115)
    for bid, bname, cat in bmks:
        times_per_cfg = {}
        for cfg in configs:
            b_rows = [r for r in by_cfg[cfg] if r['benchmark_id'] == bid]
            w_times = [safe_float(r['wall_time_s']) for r in b_rows]
            times_per_cfg[cfg] = sum(w_times) / len(w_times) if w_times else 0.0
        
        print(f"{bid:<7} | {bname:<28} | {times_per_cfg['cfg01_baseline_base']:<13.4f} | {times_per_cfg['cfg05_baseline_adaptfix']:<14.4f} | {times_per_cfg['cfg_v3dd_adaptfix']:<14.4f} | {times_per_cfg['cfg_mab_base']:<12.4f} | {times_per_cfg['cfg_mab_adaptfix']:<13.4f}")

    print("\nInstance Conflicts:")
    print(f"{'ID':<7} | {'Benchmark Name':<28} | {'Base Base':<10} | {'Base AdFix':<11} | {'V3DD AdFix':<11} | {'MAB Base':<10} | {'MAB AdFix':<10}")
    print("-" * 100)
    for bid, bname, cat in bmks:
        cfc_per_cfg = {}
        for cfg in configs:
            b_rows = [r for r in by_cfg[cfg] if r['benchmark_id'] == bid]
            c_vals = [safe_int(r['conflicts']) for r in b_rows]
            cfc_per_cfg[cfg] = sum(c_vals) / len(c_vals) if c_vals else 0.0
        print(f"{bid:<7} | {bname:<28} | {cfc_per_cfg['cfg01_baseline_base']:<10.0f} | {cfc_per_cfg['cfg05_baseline_adaptfix']:<11.0f} | {cfc_per_cfg['cfg_v3dd_adaptfix']:<11.0f} | {cfc_per_cfg['cfg_mab_base']:<10.0f} | {cfc_per_cfg['cfg_mab_adaptfix']:<10.0f}")

    # 4. Bandit Diagnostics
    print("\n" + "="*80)
    print("4. PORTFOLIO-MAB BANDIT DIAGNOSTICS")
    print("="*80)
    mab_cfgs = ['cfg_mab_base', 'cfg_mab_adaptfix']
    for mcfg in mab_cfgs:
        print(f"\n--- Diagnostics for {cfg_names[mcfg]} ({mcfg}) ---")
        m_rows = by_cfg[mcfg]
        
        tot_arm0_sel = sum(safe_int(r['mab_arm0_selections']) for r in m_rows)
        tot_arm1_sel = sum(safe_int(r['mab_arm1_selections']) for r in m_rows)
        tot_intervals = sum(safe_int(r['mab_total_intervals']) for r in m_rows)
        tot_postp = sum(safe_int(r['mab_postponed_requests']) for r in m_rows)
        tot_exec_postp = sum(safe_int(r['mab_executed_postp_restarts']) for r in m_rows)
        tot_canc_postp = sum(safe_int(r['mab_canceled_postp_restarts']) for r in m_rows)
        
        print(f"Total Intervals across 48 runs: {tot_intervals}")
        print(f"Arm 0 (Native Glucose) Selections: {tot_arm0_sel} ({tot_arm0_sel / tot_intervals * 100:.2f}%)" if tot_intervals else "Arm 0: 0")
        print(f"Arm 1 (Bounded Descent) Selections: {tot_arm1_sel} ({tot_arm1_sel / tot_intervals * 100:.2f}%)" if tot_intervals else "Arm 1: 0")
        print(f"Postponed Restart Requests: {tot_postp}")
        print(f"Executed Postponed Restarts: {tot_exec_postp}")
        print(f"Canceled Postponed Restarts: {tot_canc_postp}")

        print(f"\n{'ID':<7} | {'Benchmark Name':<28} | {'Intervals':<10} | {'Arm 0':<6} | {'Arm 1':<6} | {'Postp':<6} | {'ExecPostp':<10} | {'R_bar0':<8} | {'R_bar1':<8} | {'UCB0':<8} | {'UCB1':<8}")
        print("-" * 115)
        for bid, bname, cat in bmks:
            b_rows = [r for r in m_rows if r['benchmark_id'] == bid]
            interv = sum(safe_int(r['mab_total_intervals']) for r in b_rows)
            a0 = sum(safe_int(r['mab_arm0_selections']) for r in b_rows)
            a1 = sum(safe_int(r['mab_arm1_selections']) for r in b_rows)
            postp = sum(safe_int(r['mab_postponed_requests']) for r in b_rows)
            ex_postp = sum(safe_int(r['mab_executed_postp_restarts']) for r in b_rows)
            mean_r0 = sum(safe_float(r['mab_arm0_mean_reward']) for r in b_rows) / len(b_rows)
            mean_r1 = sum(safe_float(r['mab_arm1_mean_reward']) for r in b_rows) / len(b_rows)
            mean_ucb0 = sum(safe_float(r['mab_arm0_final_ucb']) for r in b_rows) / len(b_rows)
            mean_ucb1 = sum(safe_float(r['mab_arm1_final_ucb']) for r in b_rows) / len(b_rows)
            print(f"{bid:<7} | {bname:<28} | {interv:<10} | {a0:<6} | {a1:<6} | {postp:<6} | {ex_postp:<10} | {mean_r0:<8.4f} | {mean_r1:<8.4f} | {mean_ucb0:<8.4f} | {mean_ucb1:<8.4f}")

    # 5. Paired Comparisons
    print("\n" + "="*80)
    print("5. PAIRED COMPARISONS")
    print("="*80)
    print("Comparison A: cfg_mab_adaptfix vs cfg05_baseline_adaptfix")
    diff_wall_a = []
    for bid, bname, cat in bmks:
        m_rows = [r for r in by_cfg['cfg_mab_adaptfix'] if r['benchmark_id'] == bid]
        b_rows = [r for r in by_cfg['cfg05_baseline_adaptfix'] if r['benchmark_id'] == bid]
        m_wall = sum(safe_float(r['wall_time_s']) for r in m_rows) / len(m_rows)
        b_wall = sum(safe_float(r['wall_time_s']) for r in b_rows) / len(b_rows)
        m_cfc = sum(safe_int(r['conflicts']) for r in m_rows) / len(m_rows)
        b_cfc = sum(safe_int(r['conflicts']) for r in b_rows) / len(b_rows)
        w_delta = ((m_wall - b_wall) / b_wall * 100) if b_wall > 0.001 else 0.0
        c_delta = ((m_cfc - b_cfc) / b_cfc * 100) if b_cfc > 0 else 0.0
        diff_wall_a.append((bid, bname, cat, b_wall, m_wall, w_delta, b_cfc, m_cfc, c_delta))

    print(f"{'ID':<7} | {'Benchmark Name':<28} | {'Base Wall':<10} | {'MAB Wall':<10} | {'Delta Wall %':<12} | {'Base Cfc':<10} | {'MAB Cfc':<10} | {'Delta Cfc %':<12}")
    print("-" * 110)
    for d in diff_wall_a:
        print(f"{d[0]:<7} | {d[1]:<28} | {d[3]:<10.4f} | {d[4]:<10.4f} | {d[5]:>+11.2f}% | {d[6]:<10.0f} | {d[7]:<10.0f} | {d[8]:>+11.2f}%")

    print("\nComparison B: cfg_mab_base vs cfg01_baseline_base")
    diff_wall_b = []
    for bid, bname, cat in bmks:
        m_rows = [r for r in by_cfg['cfg_mab_base'] if r['benchmark_id'] == bid]
        b_rows = [r for r in by_cfg['cfg01_baseline_base'] if r['benchmark_id'] == bid]
        m_wall = sum(safe_float(r['wall_time_s']) for r in m_rows) / len(m_rows)
        b_wall = sum(safe_float(r['wall_time_s']) for r in b_rows) / len(b_rows)
        m_cfc = sum(safe_int(r['conflicts']) for r in m_rows) / len(m_rows)
        b_cfc = sum(safe_int(r['conflicts']) for r in b_rows) / len(b_rows)
        w_delta = ((m_wall - b_wall) / b_wall * 100) if b_wall > 0.001 else 0.0
        c_delta = ((m_cfc - b_cfc) / b_cfc * 100) if b_cfc > 0 else 0.0
        diff_wall_b.append((bid, bname, cat, b_wall, m_wall, w_delta, b_cfc, m_cfc, c_delta))

    print(f"{'ID':<7} | {'Benchmark Name':<28} | {'Base Wall':<10} | {'MAB Wall':<10} | {'Delta Wall %':<12} | {'Base Cfc':<10} | {'MAB Cfc':<10} | {'Delta Cfc %':<12}")
    print("-" * 110)
    for d in diff_wall_b:
        print(f"{d[0]:<7} | {d[1]:<28} | {d[3]:<10.4f} | {d[4]:<10.4f} | {d[5]:>+11.2f}% | {d[6]:<10.0f} | {d[7]:<10.0f} | {d[8]:>+11.2f}%")

    print("\nComparison C: cfg_mab_adaptfix vs cfg_v3dd_adaptfix")
    diff_wall_c = []
    for bid, bname, cat in bmks:
        m_rows = [r for r in by_cfg['cfg_mab_adaptfix'] if r['benchmark_id'] == bid]
        v_rows = [r for r in by_cfg['cfg_v3dd_adaptfix'] if r['benchmark_id'] == bid]
        m_wall = sum(safe_float(r['wall_time_s']) for r in m_rows) / len(m_rows)
        v_wall = sum(safe_float(r['wall_time_s']) for r in v_rows) / len(v_rows)
        m_cfc = sum(safe_int(r['conflicts']) for r in m_rows) / len(m_rows)
        v_cfc = sum(safe_int(r['conflicts']) for r in v_rows) / len(v_rows)
        w_delta = ((m_wall - v_wall) / v_wall * 100) if v_wall > 0.001 else 0.0
        c_delta = ((m_cfc - v_cfc) / v_cfc * 100) if v_cfc > 0 else 0.0
        diff_wall_c.append((bid, bname, cat, v_wall, m_wall, w_delta, v_cfc, m_cfc, c_delta))

    print(f"{'ID':<7} | {'Benchmark Name':<28} | {'V3DD Wall':<10} | {'MAB Wall':<10} | {'Delta Wall %':<12} | {'V3DD Cfc':<10} | {'MAB Cfc':<10} | {'Delta Cfc %':<12}")
    print("-" * 110)
    for d in diff_wall_c:
        print(f"{d[0]:<7} | {d[1]:<28} | {d[3]:<10.4f} | {d[4]:<10.4f} | {d[5]:>+11.2f}% | {d[6]:<10.0f} | {d[7]:<10.0f} | {d[8]:>+11.2f}%")

if __name__ == '__main__':
    main()
