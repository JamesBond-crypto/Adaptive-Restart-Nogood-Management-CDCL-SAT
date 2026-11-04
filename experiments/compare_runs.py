import csv
from pathlib import Path
import re

re_adaptive_restarts = re.compile(r"c\s+adaptive restarts\s*:\s*(\d+)")
re_genuine_restarts = re.compile(r"c\s+genuine restarts\s*:\s*(\d+)")
re_last_score = re.compile(r"c\s+last adaptive score\s*:\s*([\d\.]+)\s*\(global:\s*([\d\.]+)\)")

def parse_log(log_path):
    txt = Path(log_path).read_text(encoding="utf-8", errors="replace")
    m_ar = re_adaptive_restarts.search(txt)
    m_gr = re_genuine_restarts.search(txt)
    m_sc = re_last_score.search(txt)
    return {
        "adaptive_restarts": int(m_ar.group(1)) if m_ar else 0,
        "genuine_restarts": int(m_gr.group(1)) if m_gr else 0,
        "last_w_score": float(m_sc.group(1)) if m_sc else 0.0,
        "last_glob_score": float(m_sc.group(2)) if m_sc else 0.0
    }

def load_csv(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["benchmark_name"]] = r
    return rows

base = load_csv("experiments/results/pilot_baseline.csv")
adapt = load_csv("experiments/results/pilot_adaptive_v1.csv")

header = f"{'Benchmark':<30} | {'Status':<5} | {'Base Cfc':<8} | {'Adapt Cfc':<9} | {'Base Rst':<8} | {'Adapt Rst':<9} | {'Adapt Evts':<10} | {'Base Red':<8} | {'Adapt Red':<9} | {'Base Sec':<8} | {'Adapt Sec':<9}"
print(header)
print("-" * len(header))

total_base_cfc = 0
total_adapt_cfc = 0
total_base_rst = 0
total_adapt_rst = 0
total_adapt_events = 0
total_base_sec = 0.0
total_adapt_sec = 0.0

for bname in sorted(base.keys()):
    b = base[bname]
    a = adapt[bname]
    b_cfc = int(b["conflicts"])
    a_cfc = int(a["conflicts"])
    total_base_cfc += b_cfc
    total_adapt_cfc += a_cfc
    b_rst = int(b["restarts"])
    a_rst = int(a["restarts"])
    total_base_rst += b_rst
    total_adapt_rst += a_rst
    b_red = int(b["reduce_db_count"])
    a_red = int(a["reduce_db_count"])
    b_sec = float(b["wall_time_s"])
    a_sec = float(a["wall_time_s"])
    total_base_sec += b_sec
    total_adapt_sec += a_sec
    log_info = parse_log(a["log_file"])
    total_adapt_events += log_info["adaptive_restarts"]
    st = b["status"]
    print(f"{bname:<30} | {st:^5} | {b_cfc:<8} | {a_cfc:<9} | {b_rst:<8} | {a_rst:<9} | {log_info['adaptive_restarts']:^10} | {b_red:<8} | {a_red:<9} | {b_sec:<8.3f} | {a_sec:<9.3f}")

print("-" * len(header))
print(f"{'TOTAL':<30} | {'-':^5} | {total_base_cfc:<8} | {total_adapt_cfc:<9} | {total_base_rst:<8} | {total_adapt_rst:<9} | {total_adapt_events:^10} | {'-':<8} | {'-':<9} | {total_base_sec:<8.3f} | {total_adapt_sec:<9.3f}")

