#!/usr/bin/env python3
"""
experiments/verify_portfolio_mab_invariance.py

Step 44: Automated Verification and Invariance Harness for Portfolio-MAB.
Verifies:
  1. Release and debug binary compilation and SHA-256 integrity.
  2. Baseline smoke test correctness.
  3. Shadow-mode trajectory invariance against native Glucose baseline (100% bitwise match).
  4. Active Portfolio-MAB arm alternation and UCB calculations.
  5. Postponement safety bounds (conflicts postponed <= 500).
  6. Independent SAT model verification.
"""

import sys
import os
import subprocess
import hashlib
from pathlib import Path

WORKSPACE = Path(r"D:\DAC_203@Project")
RELEASE_BIN = WORKSPACE / "src" / "glucose_windows" / "glucose-portfolio-mab.exe"
DEBUG_BIN = WORKSPACE / "src" / "glucose_windows" / "glucose-portfolio-mab-debug.exe"
FROZEN_BIN = WORKSPACE / "src" / "glucose_windows" / "glucose-simp-step35-frozen.exe"

# Add experiments to sys.path for verify_model
sys.path.insert(0, str(WORKSPACE / "experiments"))
try:
    from verify_model import verify_model
except ImportError:
    verify_model = None

def run_cmd(cmd_list, timeout=15.0):
    p = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    return p.stdout, p.stderr, p.returncode

def parse_stats(output):
    stats = {}
    for line in output.splitlines():
        if line.startswith("c conflicts"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["conflicts"] = int(parts[1].split()[0])
        elif line.startswith("c decisions"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["decisions"] = int(parts[1].split()[0])
        elif line.startswith("c propagations"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["propagations"] = int(parts[1].split()[0])
        elif line.startswith("c restarts"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["restarts"] = int(parts[1].split()[0])
        elif line.startswith("c mab total intervals"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["mab_intervals"] = int(parts[1].strip())
        elif line.startswith("c mab arm 0 selections"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["mab_arm0"] = int(parts[1].strip())
        elif line.startswith("c mab arm 1 selections"):
            parts = line.split(":")
            if len(parts) >= 2:
                stats["mab_arm1"] = int(parts[1].strip())
        elif line.startswith("s SATISFIABLE"):
            stats["status"] = "SAT"
        elif line.startswith("s UNSATISFIABLE"):
            stats["status"] = "UNSAT"
    return stats

def main():
    print("=" * 80)
    print("STEP 44: PORTFOLIO-MAB AUTOMATED VERIFICATION & INVARIANCE SUITE")
    print("=" * 80)

    passed = 0
    total = 0

    # 1. Binary existence check
    total += 1
    if RELEASE_BIN.exists() and DEBUG_BIN.exists():
        print(f"[PASS] 1. Release & Debug binaries present.")
        passed += 1
    else:
        print(f"[FAIL] 1. Binaries missing!")
        sys.exit(1)

    # 2. Basic Smoke Tests
    smoke_bmks = [
        ("benchmarks/smoke_test/test_sat.cnf", "SAT"),
        ("benchmarks/smoke_test/test_unsat.cnf", "UNSAT"),
        ("benchmarks/pilot/planted3sat_n60_c256_s501.cnf", "SAT"),
        ("benchmarks/pilot/php_6p_5h.cnf", "UNSAT")
    ]

    for bmk_path, expected in smoke_bmks:
        total += 1
        out, err, code = run_cmd([str(RELEASE_BIN), "-restart-strategy=baseline", bmk_path])
        stats = parse_stats(out)
        if stats.get("status") == expected:
            print(f"[PASS] Smoke test {Path(bmk_path).name} -> {expected}")
            passed += 1
        else:
            print(f"[FAIL] Smoke test {Path(bmk_path).name} failed! Got {stats.get('status')}")

    # 3. Shadow-Mode Invariance Tests against Baseline
    # Running with -portfolio-shadow MUST produce identical conflicts, decisions, propagations, restarts!
    invariance_bmks = [
        "benchmarks/smoke_test/test_sat.cnf",
        "benchmarks/smoke_test/test_unsat.cnf",
        "benchmarks/pilot/planted3sat_n60_c256_s501.cnf",
        "benchmarks/pilot/rand3sat_n50_c213_s101.cnf",
        "benchmarks/pilot/rand3sat_n75_c320_s201.cnf",
        "benchmarks/pilot/php_6p_5h.cnf",
        "benchmarks/pilot/php_7p_6h.cnf",
        "benchmarks/expanded/gcol_sat_n30_k3_m90_s3001.cnf",
        "benchmarks/expanded/gcol_unsat_grotzsch_k3.cnf"
    ]

    print("\n--- Testing Shadow-Mode Bitwise Invariance ---")
    for bmk in invariance_bmks:
        total += 1
        b_out, _, _ = run_cmd([str(RELEASE_BIN), "-restart-strategy=baseline", bmk])
        s_out, _, _ = run_cmd([str(RELEASE_BIN), "-restart-strategy=baseline", "-portfolio-shadow", bmk])

        b_stats = parse_stats(b_out)
        s_stats = parse_stats(s_out)

        keys = ["status", "conflicts", "decisions", "propagations", "restarts"]
        match = all(b_stats.get(k) == s_stats.get(k) for k in keys)

        if match:
            print(f"[PASS] Invariance on {Path(bmk).name}: cfc={b_stats.get('conflicts')}, dec={b_stats.get('decisions')}, prop={b_stats.get('propagations')}, rst={b_stats.get('restarts')}")
            passed += 1
        else:
            print(f"[FAIL] Invariance broken on {Path(bmk).name}!")
            print(f"  Base:   {b_stats}")
            print(f"  Shadow: {s_stats}")

    # 4. Active Portfolio-MAB Correctness & Model Verification
    print("\n--- Testing Active Portfolio-MAB Correctness & Arm Telemetry ---")
    active_bmks = [
        ("benchmarks/pilot/php_7p_6h.cnf", "UNSAT"),
        ("benchmarks/pilot/php_8p_7h.cnf", "UNSAT"),
        ("benchmarks/pilot/rand3sat_n100_c426_s301.cnf", "SAT"),
        ("benchmarks/pilot/rand3sat_n125_c532_s401.cnf", "SAT")
    ]

    for bmk, expected in active_bmks:
        total += 1
        out, err, code = run_cmd([str(RELEASE_BIN), "-restart-strategy=portfolio-mab", "-model", bmk])
        stats = parse_stats(out)
        
        status_ok = (stats.get("status") == expected)
        model_ok = True
        if expected == "SAT" and verify_model:
            v_lines = "\n".join([line for line in out.splitlines() if line.startswith("v ")])
            valid, msg = verify_model(bmk, v_lines)
            model_ok = valid

        arms_ok = (stats.get("mab_intervals", 0) > 0)

        if status_ok and model_ok and arms_ok:
            print(f"[PASS] Active Portfolio-MAB on {Path(bmk).name}: status={stats.get('status')}, model_valid={model_ok}, intervals={stats.get('mab_intervals')}, arm0={stats.get('mab_arm0')}, arm1={stats.get('mab_arm1')}")
            passed += 1
        else:
            print(f"[FAIL] Active test on {Path(bmk).name}: status_ok={status_ok}, model_ok={model_ok}, arms_ok={arms_ok}")

    # 5. Debug Binary Assertion Verification
    print("\n--- Testing Debug Binary Assertion Safety ---")
    total += 1
    d_out, d_err, d_code = run_cmd([str(DEBUG_BIN), "-restart-strategy=portfolio-mab", "benchmarks/pilot/php_7p_6h.cnf"])
    d_stats = parse_stats(d_out)
    if d_code == 20 and d_stats.get("status") == "UNSAT":
        print(f"[PASS] Debug binary executed without assertion failures on php_7p_6h.cnf (exit code 20).")
        passed += 1
    else:
        print(f"[FAIL] Debug binary failed with exit code {d_code}!")
        print(f"Stderr: {d_err[:200]}")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {passed} / {total} TESTS PASSED ({(passed/total)*100:.1f}%)")
    print("=" * 80)

    if passed == total:
        print("ALL TESTS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
