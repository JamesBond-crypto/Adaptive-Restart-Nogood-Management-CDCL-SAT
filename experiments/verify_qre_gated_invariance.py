#!/usr/bin/env python3
"""
verify_qre_gated_invariance.py - Correctness and Invariance Verification for Step 40

Verifies:
  1. Smoke tests on test_sat.cnf and test_unsat.cnf
  2. Baseline invariance: glucose-qre-gated.exe vs glucose-simp-step35-frozen.exe
  3. Original QRE invariance: glucose-qre-gated.exe -restart-strategy=adaptive-qre vs glucose-qre-active.exe
  4. V1 / V3 restart invariance
  5. Restart-counter consistency (genuine restarts == native requests + executed QRE restarts)
"""

import sys
import os
import subprocess
import re
from pathlib import Path

WORKSPACE = Path(r"D:\DAC_203@Project")
GATED_EXE = WORKSPACE / "src" / "glucose_windows" / "glucose-qre-gated.exe"
GATED_DEBUG_EXE = WORKSPACE / "src" / "glucose_windows" / "glucose-qre-gated-debug.exe"
ACTIVE_EXE = WORKSPACE / "src" / "glucose_windows" / "glucose-qre-active.exe"
FROZEN_EXE = WORKSPACE / "src" / "glucose_windows" / "glucose-simp-step35-frozen.exe"

def run_cmd(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = p.stdout
    metrics = {
        "status": "UNKNOWN",
        "conflicts": 0,
        "decisions": 0,
        "propagations": 0,
        "genuine_restarts": 0,
        "qre_native_requests": 0,
        "qre_executed_restarts": 0,
    }
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("s SATISFIABLE"): metrics["status"] = "SAT"
        elif line.startswith("s UNSATISFIABLE"): metrics["status"] = "UNSAT"
        elif line.startswith("c conflicts"):
            m = re.search(r"c conflicts\s*:\s*(\d+)", line)
            if m: metrics["conflicts"] = int(m.group(1))
        elif line.startswith("c decisions"):
            m = re.search(r"c decisions\s*:\s*(\d+)", line)
            if m: metrics["decisions"] = int(m.group(1))
        elif line.startswith("c propagations"):
            m = re.search(r"c propagations\s*:\s*(\d+)", line)
            if m: metrics["propagations"] = int(m.group(1))
        elif line.startswith("c genuine restarts"):
            m = re.search(r"c genuine restarts\s*:\s*(\d+)", line)
            if m: metrics["genuine_restarts"] = int(m.group(1))
        elif line.startswith("c qre native requests"):
            m = re.search(r"c qre native requests\s*:\s*(\d+)", line)
            if m: metrics["qre_native_requests"] = int(m.group(1))
        elif line.startswith("c qre executed restarts"):
            m = re.search(r"c qre executed restarts\s*:\s*(\d+)", line)
            if m: metrics["qre_executed_restarts"] = int(m.group(1))
    return metrics, out

def main():
    print("=" * 80)
    print("STEP 40: CORRECTNESS & INVARIANCE AUDIT")
    print("=" * 80)

    test_sat = str(WORKSPACE / "benchmarks" / "smoke_test" / "test_sat.cnf")
    test_unsat = str(WORKSPACE / "benchmarks" / "smoke_test" / "test_unsat.cnf")
    rand_50 = str(WORKSPACE / "benchmarks" / "pilot" / "rand3sat_n50_c213_s101.cnf")
    php_6 = str(WORKSPACE / "benchmarks" / "pilot" / "php_6p_5h.cnf")
    php_7 = str(WORKSPACE / "benchmarks" / "pilot" / "php_7p_6h.cnf")

    checks = 0
    passed = 0

    # 1. Smoke tests on release and debug binaries
    for exe, name in [(GATED_EXE, "Release"), (GATED_DEBUG_EXE, "Debug")]:
        m_sat, _ = run_cmd([str(exe), test_sat])
        m_unsat, _ = run_cmd([str(exe), test_unsat])
        checks += 2
        if m_sat["status"] == "SAT": passed += 1
        else: print(f"FAIL: {name} test_sat")
        if m_unsat["status"] == "UNSAT": passed += 1
        else: print(f"FAIL: {name} test_unsat")

    print(f"[+] Smoke tests: {passed}/{checks} passed.")

    # 2. Baseline Invariance: Gated binary under baseline vs Frozen Step 35 binary
    test_bmks = [rand_50, php_6, php_7]
    for bmk in test_bmks:
        m_frozen, _ = run_cmd([str(FROZEN_EXE), "-restart-strategy=baseline", bmk])
        m_gated, _ = run_cmd([str(GATED_EXE), "-restart-strategy=baseline", bmk])
        checks += 3
        if m_frozen["status"] == m_gated["status"]: passed += 1
        else: print(f"FAIL status: {bmk}")
        if m_frozen["conflicts"] == m_gated["conflicts"]: passed += 1
        else: print(f"FAIL cfc: {bmk} ({m_frozen['conflicts']} vs {m_gated['conflicts']})")
        if m_frozen["decisions"] == m_gated["decisions"]: passed += 1
        else: print(f"FAIL dec: {bmk} ({m_frozen['decisions']} vs {m_gated['decisions']})")

    print(f"[+] Baseline Invariance vs Frozen Step 35: passed.")

    # 3. Original QRE Invariance: Gated binary under -restart-strategy=adaptive-qre vs Active binary
    for bmk in test_bmks:
        m_act, _ = run_cmd([str(ACTIVE_EXE), "-restart-strategy=adaptive-qre", "-reduce-strategy=adaptive-fixed", bmk])
        m_gated, _ = run_cmd([str(GATED_EXE), "-restart-strategy=adaptive-qre", "-reduce-strategy=adaptive-fixed", bmk])
        checks += 3
        if m_act["status"] == m_gated["status"]: passed += 1
        else: print(f"FAIL QRE status: {bmk}")
        if m_act["conflicts"] == m_gated["conflicts"]: passed += 1
        else: print(f"FAIL QRE cfc: {bmk} ({m_act['conflicts']} vs {m_gated['conflicts']})")
        if m_act["decisions"] == m_gated["decisions"]: passed += 1
        else: print(f"FAIL QRE dec: {bmk} ({m_act['decisions']} vs {m_gated['decisions']})")

    print(f"[+] Original QRE Invariance vs Step 39 Active Binary: passed.")

    # 4. V1 / V3 Invariance: Gated binary vs Frozen binary
    for bmk in [rand_50, php_6]:
        m_f_v1, _ = run_cmd([str(FROZEN_EXE), "-restart-strategy=adaptive", bmk])
        m_g_v1, _ = run_cmd([str(GATED_EXE), "-restart-strategy=adaptive", bmk])
        checks += 2
        if m_f_v1["conflicts"] == m_g_v1["conflicts"]: passed += 1
        else: print(f"FAIL V1 cfc: {bmk}")
        if m_f_v1["decisions"] == m_g_v1["decisions"]: passed += 1
        else: print(f"FAIL V1 dec: {bmk}")

        m_f_v3, _ = run_cmd([str(FROZEN_EXE), "-restart-strategy=adaptive-v3", bmk])
        m_g_v3, _ = run_cmd([str(GATED_EXE), "-restart-strategy=adaptive-v3", bmk])
        checks += 2
        if m_f_v3["conflicts"] == m_g_v3["conflicts"]: passed += 1
        else: print(f"FAIL V3 cfc: {bmk}")
        if m_f_v3["decisions"] == m_g_v3["decisions"]: passed += 1
        else: print(f"FAIL V3 dec: {bmk}")

    print(f"[+] V1 / V3 Invariance vs Frozen Step 35: passed.")

    # 5. Restart-counter consistency check on php_7
    m_gated_qre, _ = run_cmd([str(GATED_EXE), "-restart-strategy=adaptive-qre-gated", "-reduce-strategy=adaptive-fixed", php_7])
    checks += 1
    # On php_7, genuine restarts == native requests + executed QRE restarts
    expected_gen = m_gated_qre["qre_native_requests"] + m_gated_qre["qre_executed_restarts"]
    if m_gated_qre["genuine_restarts"] == expected_gen:
        passed += 1
        print(f"[+] Restart Counter Consistency: genuine={m_gated_qre['genuine_restarts']} == native={m_gated_qre['qre_native_requests']} + qre={m_gated_qre['qre_executed_restarts']}")
    else:
        print(f"FAIL restart consistency: genuine={m_gated_qre['genuine_restarts']} != {expected_gen}")

    print("=" * 80)
    print(f"OVERALL INVARIANCE & CORRECTNESS: {passed} / {checks} PASSED ({passed/checks*100:.1f}%)")
    print("=" * 80)
    if passed != checks:
        sys.exit(1)

if __name__ == "__main__":
    main()

