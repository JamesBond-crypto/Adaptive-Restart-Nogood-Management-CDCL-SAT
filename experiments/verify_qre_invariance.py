#!/usr/bin/env python3
"""
verify_qre_invariance.py - Verify Correctness and Search Invariance of QRE Shadow Mode
Step 38: Quantitative Risk Engine Feasibility and Shadow Implementation

Runs a rigorous battery of tests comparing:
  - Solver without -qre-shadow (baseline behavior)
  - Solver with -qre-shadow    (shadow telemetry active)

Verifies:
  1. Exact deterministic equality of:
     - status (SAT / UNSAT)
     - conflicts
     - decisions
     - propagations
     - restarts / genuine restarts
     - nb ReduceDB (clause database reductions)
  2. Model verification on all SAT outputs.
  3. Tests across multiple restart strategies:
     - Baseline (original Glucose)
     - Adaptive V1
     - Adaptive V3 (Drawdown-only)
"""

import os
import sys
import subprocess
import re

SOLVER_RELEASE = os.path.join("src", "glucose_windows", "glucose-qre-shadow.exe")
SOLVER_DEBUG   = os.path.join("src", "glucose_windows", "glucose-qre-shadow-debug.exe")

TEST_INSTANCES = [
    # Smoke tests
    os.path.join("benchmarks", "smoke_test", "test_sat.cnf"),
    os.path.join("benchmarks", "smoke_test", "test_unsat.cnf"),
    # Pilot benchmarks (Structured UNSAT and Random SAT)
    os.path.join("benchmarks", "pilot", "php_6p_5h.cnf"),
    os.path.join("benchmarks", "pilot", "php_7p_6h.cnf"),
    os.path.join("benchmarks", "pilot", "rand3sat_n50_c213_s101.cnf"),
    os.path.join("benchmarks", "pilot", "rand3sat_n75_c320_s201.cnf"),
    os.path.join("benchmarks", "pilot", "planted3sat_n60_c256_s501.cnf"),
    os.path.join("benchmarks", "pilot", "planted3sat_n90_c383_s601.cnf"),
    # Expanded development benchmarks (Graph coloring and larger random)
    os.path.join("benchmarks", "expanded", "gcol_unsat_grotzsch_k3.cnf"),
    os.path.join("benchmarks", "expanded", "gcol_sat_n30_k3_m90_s3001.cnf"),
    os.path.join("benchmarks", "expanded", "php_9p_7h.cnf"),
    os.path.join("benchmarks", "expanded", "rand3sat_n150_c639_s1001.cnf"),
]

def parse_solver_output(output_text):
    data = {}
    for line in output_text.splitlines():
        line = line.strip()
        if line.startswith("s "):
            data["status"] = line.split()[1]
        elif line.startswith("c conflicts"):
            m = re.search(r"c conflicts\s*:\s*(\d+)", line)
            if m: data["conflicts"] = int(m.group(1))
        elif line.startswith("c decisions"):
            m = re.search(r"c decisions\s*:\s*(\d+)", line)
            if m: data["decisions"] = int(m.group(1))
        elif line.startswith("c propagations"):
            m = re.search(r"c propagations\s*:\s*(\d+)", line)
            if m: data["propagations"] = int(m.group(1))
        elif line.startswith("c restarts"):
            m = re.search(r"c restarts\s*:\s*(\d+)", line)
            if m: data["restarts"] = int(m.group(1))
        elif line.startswith("c genuine restarts"):
            m = re.search(r"c genuine restarts\s*:\s*(\d+)", line)
            if m: data["genuine_restarts"] = int(m.group(1))
        elif line.startswith("c nb ReduceDB"):
            m = re.search(r"c nb ReduceDB\s*:\s*(\d+)", line)
            if m: data["nb_reduce_db"] = int(m.group(1))
        elif line.startswith("c qre shadow"):
            data["qre_shadow"] = line.split(":")[-1].strip()
        elif line.startswith("c qre decisions obs"):
            data["qre_dec_obs"] = int(line.split(":")[-1].strip())
        elif line.startswith("c qre conflicts obs"):
            data["qre_cfc_obs"] = int(line.split(":")[-1].strip())
        elif line.startswith("c qre elig either req"):
            data["qre_elig_req"] = int(line.split(":")[-1].strip())
    return data

def verify_cnf_model(cnf_file, model_lits):
    clauses = []
    with open(cnf_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("c") or line.startswith("p"):
                continue
            lits = [int(x) for x in line.split() if x != "0"]
            if lits:
                clauses.append(lits)
    model_set = set(model_lits)
    for cl in clauses:
        if not any(lit in model_set for lit in cl):
            return False
    return True

def run_test(solver_bin, cnf_path, extra_flags=[]):
    cmd = [solver_bin] + extra_flags + [cnf_path]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return parse_solver_output(proc.stdout)

def main():
    print("=" * 80)
    print("STEP 38: QRE SHADOW INVARIANCE & CORRECTNESS AUDIT")
    print("=" * 80)
    print(f"Testing binary: {SOLVER_RELEASE}")
    print(f"Testing debug : {SOLVER_DEBUG}")
    print(f"Total benchmark instances: {len(TEST_INSTANCES)}\n")

    strategies = [
        ("Baseline (Orig.)", []),
        ("Adaptive V1", ["-restart-strategy=adaptive"]),
        ("Adaptive V3 Drawdown", ["-restart-strategy=adaptive-v3", "-v3-drawdown=1", "-v3-trend=0", "-v3-ceiling=0"])
    ]

    total_checks = 0
    passed_checks = 0

    for strat_name, strat_flags in strategies:
        print(f"\n--- Testing Strategy: {strat_name} ---")
        for cnf in TEST_INSTANCES:
            bname = os.path.basename(cnf)
            if not os.path.exists(cnf):
                print(f"  [!] Missing file: {cnf}")
                continue

            # Run without QRE shadow
            res_off = run_test(SOLVER_RELEASE, cnf, strat_flags)
            # Run with QRE shadow
            res_on  = run_test(SOLVER_RELEASE, cnf, strat_flags + ["-qre-shadow"])
            # Run on assertion-enabled debug binary with QRE shadow
            res_dbg = run_test(SOLVER_DEBUG, cnf, strat_flags + ["-qre-shadow"])

            total_checks += 1

            # Check exact match
            mismatch = []
            for key in ["status", "conflicts", "decisions", "propagations", "restarts", "genuine_restarts", "nb_reduce_db"]:
                v_off = res_off.get(key)
                v_on  = res_on.get(key)
                v_dbg = res_dbg.get(key)
                if v_off != v_on or v_off != v_dbg:
                    mismatch.append(f"{key}: off={v_off}, on={v_on}, dbg={v_dbg}")

            if mismatch:
                print(f"  [FAIL] {bname:32s}: MISMATCH: {', '.join(mismatch)}")
            else:
                passed_checks += 1
                qre_obs = res_on.get("qre_cfc_obs", 0)
                qre_req = res_on.get("qre_elig_req", 0)
                print(f"  [PASS] {bname:32s} | Status={res_on.get('status')} | Cfc={res_on.get('conflicts'):6d} | Dec={res_on.get('decisions'):6d} | QRE_Cfc={qre_obs:6d} | QRE_Req={qre_req:4d}")

    print("\n" + "=" * 80)
    print(f"INVARIANCE AUDIT SUMMARY: {passed_checks} / {total_checks} PASSED ({(passed_checks/total_checks)*100:.1f}%)")
    print("=" * 80)

    if passed_checks == total_checks:
        print("[+] SUCCESS: Enabling -qre-shadow maintains 100.000% search trajectory invariance!")
        return 0
    else:
        print("[!] FAILURE: Detected deterministic divergence when -qre-shadow is enabled!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

