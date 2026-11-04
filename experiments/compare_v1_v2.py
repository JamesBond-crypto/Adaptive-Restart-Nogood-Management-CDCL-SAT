import csv

def load_data(csv_path):
    rows = {}
    with open(csv_path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows[r['benchmark_name']] = r
    return rows

v1 = load_data('experiments/results/pilot_adaptive_v1.csv')
v2 = load_data('experiments/results/pilot_adaptive_stabilized.csv')

header = f"{'Benchmark':<30} | {'V1 Cfc':<8} | {'V2 Cfc':<8} | {'V1 Starts':<9} | {'V2 Starts':<9} | {'V2 AdReq':<8} | {'V2 AdRst':<8} | {'V2 ScoreW':<10} | {'V2 ScoreG':<10}"
print(header)
print("-" * len(header))

differences = []
for bname in sorted(v1.keys()):
    r1 = v1[bname]
    r2 = v2[bname]
    c1, c2 = int(r1['conflicts']), int(r2['conflicts'])
    rst1 = int(r1['restarts'])
    rst2 = int(r2.get('starts') or r2['restarts'])
    ad_req = r2.get('adaptive_restart_requests', '')
    ad_rst = r2.get('adaptive_restarts', '')
    sc_w = r2.get('last_adaptive_score_w', '')
    sc_g = r2.get('last_adaptive_score_global', '')
    
    if c1 != c2 or rst1 != rst2:
        differences.append((bname, c1, c2, rst1, rst2))
    
    print(f"{bname:<30} | {c1:<8} | {c2:<8} | {rst1:<9} | {rst2:<9} | {str(ad_req):<8} | {str(ad_rst):<8} | {str(sc_w):<10} | {str(sc_g):<10}")

print("-" * len(header))
if not differences:
    print("ALL CONFLICTS AND RESTARTS ARE 100% IDENTICAL BETWEEN V1 AND STABILIZED V1!")
else:
    print(f"Differences detected in {len(differences)} benchmarks:")
    for d in differences:
        print("  ", d)

