import csv
from collections import defaultdict
from statistics import median
from typing import List

def iqr(vals: List[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n < 4:
        return max(s) - min(s)
    mid = n // 2
    if n % 2 == 0:
        lower = s[:mid]
        upper = s[mid:]
    else:
        lower = s[:mid]
        upper = s[mid+1:]
    return median(upper) - median(lower)

data = list(csv.DictReader(open("experiments/results/pilot_repeated_eval.csv", encoding="utf-8")))

# Group by family, benchmark, mode
table = defaultdict(dict)

for r in data:
    bname = r["benchmark_name"]
    mode = r["mode"]
    fam = r["family"]
    if mode not in table[bname]:
        table[bname][mode] = {
            "family": fam,
            "status": r["status"],
            "conflicts": int(r["conflicts"]),
            "starts": int(r["restarts"]),
            "reductions": int(r["reduce_db_count"]),
            "wall_times": []
        }
    table[bname][mode]["wall_times"].append(float(r["wall_time_s"]))

print("=" * 130)
print(f"{'Benchmark':<30} | {'Fam':<7} | {'St':<5} | {'Base Cfc':<8} | {'Adapt Cfc':<9} | {'Base Rst':<8} | {'Adapt Rst':<9} | {'Base Med(s)':<11} | {'Adapt Med(s)':<12} | {'Base IQR':<9} | {'Adapt IQR':<10}")
print("=" * 130)

families = ["Pigeonhole Principle (PHP)", "Planted 3-SAT", "Random 3-SAT"]

for fam in families:
    print(f"\n--- {fam} ---")
    fam_bnames = sorted([b for b in table if table[b]["baseline"]["family"] == fam])
    for b in fam_bnames:
        base_info = table[b]["baseline"]
        adapt_info = table[b]["adaptive"]
        b_cfc = base_info["conflicts"]
        a_cfc = adapt_info["conflicts"]
        b_rst = base_info["starts"]
        a_rst = adapt_info["starts"]
        st = base_info["status"]
        b_times = base_info["wall_times"]
        a_times = adapt_info["wall_times"]
        b_med = median(b_times)
        a_med = median(a_times)
        b_iqr = iqr(b_times)
        a_iqr = iqr(a_times)
        fam_abbr = "PHP" if "PHP" in fam else "Planted" if "Planted" in fam else "Random"
        print(f"{b:<30} | {fam_abbr:<7} | {st:^5} | {b_cfc:<8} | {a_cfc:<9} | {b_rst:<8} | {a_rst:<9} | {b_med:<11.4f} | {a_med:<12.4f} | {b_iqr:<9.4f} | {a_iqr:<10.4f}")

print("=" * 130)

