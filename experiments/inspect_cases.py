#!/usr/bin/env python3
"""
inspect_cases.py - Deep Inspection of Regression and Improvement Cases
"""

import csv
from pathlib import Path

target_bmarks = [
    ("rand3sat_n250_c1065_s1010.cnf", "REGRESSION"),
    ("rand3sat_n235_c999_s1009.cnf", "REGRESSION"),
    ("rand3sat_n200_c840_s1005.cnf", "REGRESSION"),
    ("planted3sat_n240_c1022_s2009.cnf", "REGRESSION"),
    ("gcol_unsat_k10_c9.cnf", "IMPROVEMENT"),
    ("gcol_unsat_k9_c8.cnf", "IMPROVEMENT"),
    ("php_10p_8h.cnf", "IMPROVEMENT"),
]

def load_inst(path):
    d = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            d[r['benchmark_name']] = r
    return d

cfg1 = load_inst('experiments/results/expanded_cfg1_base_base.csv')
cfg2 = load_inst('experiments/results/expanded_cfg2_adapt_base.csv')
cfg3 = load_inst('experiments/results/expanded_cfg3_base_adapt.csv')
cfg4 = load_inst('experiments/results/expanded_cfg4_adapt_adapt.csv')

print(f"{'Benchmark':<33} | {'Type':<11} | {'Cfg':<4} | {'Status':<7} | {'Time':<7} | {'Conflicts':<10} | {'Decisions':<10} | {'Props':<11} | {'Rst':<5} | {'Blk':<5} | {'Red':<4} | {'Scores (W / Glob)':<18}")
print("-" * 145)

for b, category in target_bmarks:
    for cid, cdata in [('CFG1', cfg1), ('CFG2', cfg2), ('CFG3', cfg3), ('CFG4', cfg4)]:
        r = cdata.get(b, {})
        if not r: continue
        st = r['status']
        wt = f"{float(r['wall_time_s']):.3f}s"
        cfc = r['conflicts']
        dec = r['decisions']
        prp = r['propagations']
        rst = r['genuine_restarts']
        blk = r['blocked_restarts']
        red = r['reduce_db_count']
        sw = r.get('last_adaptive_score_w', '')
        sg = r.get('last_adaptive_score_global', '')
        score_str = f"{float(sw):.2f} / {float(sg):.2f}" if sw and sg else "N/A"
        print(f"{b:<33} | {category:<11} | {cid:<4} | {st:<7} | {wt:<7} | {cfc:>10} | {dec:>10} | {prp:>11} | {rst:>5} | {blk:>5} | {red:>4} | {score_str:<18}")
    print("-" * 145)

