#!/usr/bin/env python3
"""
run_qre_active_pilot.py - Step 39: Quantitative Risk Engine Active Pilot Evaluation

Executes a 4-configuration controlled ablation across the 16 development diagnostic
instances with 3 independent repetitions (192 solver runs total) under a 15.0s timeout:

Configurations:
  1. cfg01_baseline_base:     Native Glucose + Baseline Reduction
  2. cfg05_baseline_adaptfix: Native Glucose + Adaptive-Fixed Reduction
  3. cfg_shadow_adaptfix:     Native Glucose + Optimized QRE Shadow + Adaptive-Fixed Reduction
  4. cfg_active_adaptfix:     Active QRE Controller + Adaptive-Fixed Reduction

Protocol:
  - 15.0 second external timeout per execution.
  - 3 repetitions per configuration and benchmark (balanced sequential order).
  - Independent SAT model verification.
  - Full telemetry capture: conflicts, decisions, propagations, restarts,
    genuine restarts, QRE triggers/restarts/suppressions, memory, CPU time, wall time.
  - Target binary: src/glucose_windows/glucose-qre-active.exe
  - Master CSV: experiments/results/qre_active_pilot/master_results.csv
"""

import sys
import os
import csv
import time
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

WORKSPACE = Path(r"D:\DAC_203@Project")
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-qre-active.exe"
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "qre_active_pilot"
LOGS_DIR = RESULTS_DIR / "logs"
MASTER_CSV = RESULTS_DIR / "master_results.csv"

TIMEOUT_S = 15.0
REPETITIONS = 3

# Add experiments to sys.path for verify_model
sys.path.insert(0, str(WORKSPACE / "experiments"))
try:
    from verify_model import verify_model
except ImportError:
    verify_model = None

# The 16 Step 38 diagnostic instances
DIAGNOSTIC_BENCHMARKS = [
    # 1. Trivial / Root Simplification Instances (< 10 conflicts)
    {"id": "DEV_01", "name": "test_sat.cnf", "path": "benchmarks/smoke_test/test_sat.cnf", "category": "Trivial", "expected": "SAT"},
    {"id": "DEV_02", "name": "test_unsat.cnf", "path": "benchmarks/smoke_test/test_unsat.cnf", "category": "Trivial", "expected": "UNSAT"},
    {"id": "DEV_03", "name": "planted3sat_n60_c256_s501.cnf", "path": "benchmarks/pilot/planted3sat_n60_c256_s501.cnf", "category": "Trivial", "expected": "SAT"},
    {"id": "DEV_04", "name": "gcol_sat_n30_k3_m90_s3001.cnf", "path": "benchmarks/expanded/gcol_sat_n30_k3_m90_s3001.cnf", "category": "Trivial", "expected": "SAT"},

    # 2. Medium Instances (10 to 500 conflicts)
    {"id": "DEV_05", "name": "rand3sat_n50_c213_s101.cnf", "path": "benchmarks/pilot/rand3sat_n50_c213_s101.cnf", "category": "Medium_Random", "expected": "SAT"},
    {"id": "DEV_06", "name": "rand3sat_n75_c320_s201.cnf", "path": "benchmarks/pilot/rand3sat_n75_c320_s201.cnf", "category": "Medium_Random", "expected": "SAT"},
    {"id": "DEV_07", "name": "php_6p_5h.cnf", "path": "benchmarks/pilot/php_6p_5h.cnf", "category": "Medium_Pigeonhole", "expected": "UNSAT"},
    {"id": "DEV_08", "name": "gcol_unsat_grotzsch_k3.cnf", "path": "benchmarks/expanded/gcol_unsat_grotzsch_k3.cnf", "category": "Medium_GraphColoring", "expected": "UNSAT"},

    # 3. Hard Structured UNSAT (> 500 conflicts)
    {"id": "DEV_09", "name": "php_7p_6h.cnf", "path": "benchmarks/pilot/php_7p_6h.cnf", "category": "Hard_Pigeonhole", "expected": "UNSAT"},
    {"id": "DEV_10", "name": "php_8p_7h.cnf", "path": "benchmarks/pilot/php_8p_7h.cnf", "category": "Hard_Pigeonhole", "expected": "UNSAT"},
    {"id": "DEV_11", "name": "php_9p_7h.cnf", "path": "benchmarks/expanded/php_9p_7h.cnf", "category": "Hard_Pigeonhole", "expected": "UNSAT"},
    {"id": "DEV_12", "name": "php_10p_8h.cnf", "path": "benchmarks/expanded/php_10p_8h.cnf", "category": "Hard_Pigeonhole", "expected": "UNSAT"},

    # 4. Hard Random Phase-Transition 3-SAT (> 500 conflicts)
    {"id": "DEV_13", "name": "rand3sat_n100_c426_s301.cnf", "path": "benchmarks/pilot/rand3sat_n100_c426_s301.cnf", "category": "Hard_Random", "expected": "SAT"},
    {"id": "DEV_14", "name": "rand3sat_n125_c532_s401.cnf", "path": "benchmarks/pilot/rand3sat_n125_c532_s401.cnf", "category": "Hard_Random", "expected": "SAT"},
    {"id": "DEV_15", "name": "rand3sat_n150_c639_s1001.cnf", "path": "benchmarks/expanded/rand3sat_n150_c639_s1001.cnf", "category": "Hard_Random", "expected": "SAT"},
    {"id": "DEV_16", "name": "rand3sat_n175_c735_s1003.cnf", "path": "benchmarks/expanded/rand3sat_n175_c735_s1003.cnf", "category": "Hard_Random", "expected": "SAT"}
]

CONFIGURATIONS = [
    {
        "id": "cfg01_baseline_base",
        "name": "Native Glucose + Baseline Reduction",
        "args": ["-restart-strategy=baseline", "-reduce-strategy=baseline", "-model"]
    },
    {
        "id": "cfg05_baseline_adaptfix",
        "name": "Native Glucose + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=baseline", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_shadow_adaptfix",
        "name": "Native Glucose + Optimized QRE Shadow + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=baseline", "-qre-shadow", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_active_adaptfix",
        "name": "Active QRE Controller + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=adaptive-qre", "-reduce-strategy=adaptive-fixed", "-model"]
    }
]

CSV_HEADERS = [
    "run_id", "repetition", "config_id", "config_name",
    "benchmark_id", "benchmark_name", "category", "family_type",
    "expected_status", "status", "result_match", "model_valid", "timed_out",
    "wall_time_s", "cpu_time_s", "par2_s",
    "conflicts", "decisions", "propagations",
    "restarts", "genuine_restarts", "blocked_restarts",
    "reduce_db", "removed_clauses", "memory_mb",
    # Active QRE telemetry
    "qre_native_requests", "qre_raw_sharpe_events", "qre_raw_var_events", "qre_raw_both_events",
    "qre_sustained_events", "qre_eligible_requests", "qre_executed_restarts",
    "qre_cooldown_supp", "qre_cap_supp", "qre_strategy_adapt_rst",
    # Shadow QRE telemetry
    "qre_shadow_dec_obs", "qre_shadow_cfc_obs", "qre_shadow_total_shocks",
    "qre_shadow_min_sharpe", "qre_shadow_max_var95", "qre_shadow_final_sharpe", "qre_shadow_final_var95",
    # Reduction telemetry
    "adapt_reduce_calls", "adapt_clauses_ranked", "adapt_clauses_eligible", "adapt_clauses_removed",
    "adapt_reduce_time_s"
]

def run_single(cfg: Dict[str, Any], bmk: Dict[str, Any], rep: int, run_idx: int) -> Dict[str, Any]:
    cnf_full_path = WORKSPACE / bmk["path"]
    cmd = [str(SOLVER_PATH)] + cfg["args"] + [str(cnf_full_path)]

    family_type = "UNSAT_Structured" if "Pigeonhole" in bmk["category"] or "GraphColoring" in bmk["category"] or bmk["expected"] == "UNSAT" else "SAT_Random"
    if bmk["category"] == "Trivial":
        family_type = "Trivial"

    t0 = time.perf_counter()
    timed_out = False
    stdout_txt = ""
    stderr_txt = ""

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=TIMEOUT_S
        )
        t1 = time.perf_counter()
        wall_time = t1 - t0
        stdout_txt = proc.stdout
        stderr_txt = proc.stderr
    except subprocess.TimeoutExpired as te:
        t1 = time.perf_counter()
        wall_time = TIMEOUT_S
        timed_out = True
        stdout_txt = te.stdout if te.stdout else ""
        stderr_txt = te.stderr if te.stderr else ""

    # Parse status
    status = "TIMEOUT" if timed_out else "UNKNOWN"
    for line in stdout_txt.splitlines():
        line_s = line.strip()
        if line_s == "s SATISFIABLE":
            status = "SAT"
            break
        elif line_s == "s UNSATISFIABLE":
            status = "UNSAT"
            break

    result_match = (status == bmk["expected"])

    # Independent model verification for SAT
    model_valid = "N/A"
    if status == "SAT":
        if verify_model is not None:
            v_lines = "\n".join([l for l in stdout_txt.splitlines() if l.startswith(("v ", "v\t", "V ", "V\t"))])
            is_valid, msg = verify_model(str(cnf_full_path), v_lines if v_lines else stdout_txt)
            model_valid = "PASS" if is_valid else f"FAIL: {msg}"
        else:
            model_valid = "VERIFIER_UNAVAILABLE"

    # CPU time
    cpu_time = wall_time
    m_cpu = re.search(r"^c\s+CPU time\s*:\s*([\d\.]+)", stdout_txt, re.MULTILINE)
    if m_cpu:
        try:
            cpu_time = float(m_cpu.group(1))
        except ValueError:
            pass

    # Standard search stats
    def get_int(pattern, default=0):
        m = re.search(pattern, stdout_txt, re.MULTILINE)
        return int(m.group(1)) if m else default

    def get_float(pattern, default=0.0):
        m = re.search(pattern, stdout_txt, re.MULTILINE)
        return float(m.group(1)) if m else default

    conflicts = get_int(r"^c\s+conflicts\s*:\s*(\d+)")
    decisions = get_int(r"^c\s+decisions\s*:\s*(\d+)")
    propagations = get_int(r"^c\s+propagations\s*:\s*(\d+)")
    restarts = get_int(r"^c\s+restarts\s*:\s*(\d+)")
    genuine_restarts = get_int(r"^c\s+genuine restarts\s*:\s*(\d+)")
    blocked_restarts = get_int(r"^c\s+blocked restarts\s*:\s*(\d+)")
    reduce_db = get_int(r"^c\s+nb ReduceDB\s*:\s*(\d+)")
    removed_clauses = get_int(r"^c\s+nb removed Clauses\s*:\s*(\d+)")
    memory_mb = get_float(r"^c\s+Memory used\s*:\s*([\d\.]+)")

    # Active QRE stats
    qre_native_requests = get_int(r"^c\s+qre native requests\s*:\s*(\d+)")
    qre_raw_sharpe_events = get_int(r"^c\s+qre raw sharpe events\s*:\s*(\d+)")
    qre_raw_var_events = get_int(r"^c\s+qre raw var events\s*:\s*(\d+)")
    qre_raw_both_events = get_int(r"^c\s+qre raw both events\s*:\s*(\d+)")
    qre_sustained_events = get_int(r"^c\s+qre sustained events\s*:\s*(\d+)")
    qre_eligible_requests = get_int(r"^c\s+qre eligible requests\s*:\s*(\d+)")
    qre_executed_restarts = get_int(r"^c\s+qre executed restarts\s*:\s*(\d+)")
    qre_cooldown_supp = get_int(r"^c\s+qre cooldown supp\s*:\s*(\d+)")
    qre_cap_supp = get_int(r"^c\s+qre freq cap supp\s*:\s*(\d+)")
    qre_strategy_adapt_rst = get_int(r"^c\s+qre strategy adapt rst\s*:\s*(\d+)")

    # Shadow QRE stats
    qre_shadow_dec_obs = get_int(r"^c\s+qre decisions obs\s*:\s*(\d+)")
    qre_shadow_cfc_obs = get_int(r"^c\s+qre conflicts obs\s*:\s*(\d+)")
    qre_shadow_total_shocks = get_int(r"^c\s+qre total shocks\s*:\s*(\d+)")
    qre_shadow_min_sharpe = get_float(r"^c\s+qre min sharpe obs\s*:\s*([\d\.\-]+)")
    qre_shadow_max_var95 = get_float(r"^c\s+qre max var95 obs\s*:\s*([\d\.\-]+)")
    qre_shadow_final_sharpe = get_float(r"^c\s+qre final sharpe\s*:\s*([\d\.\-]+)")
    qre_shadow_final_var95 = get_float(r"^c\s+qre final var95\s*:\s*([\d\.\-]+)")

    # Reduction stats
    adapt_reduce_calls = get_int(r"^c\s+adapt reduce calls\s*:\s*(\d+)")
    adapt_clauses_ranked = get_int(r"^c\s+adapt clauses ranked\s*:\s*(\d+)")
    adapt_clauses_eligible = get_int(r"^c\s+adapt clauses eligible\s*:\s*(\d+)")
    adapt_clauses_removed = get_int(r"^c\s+adapt clauses removed\s*:\s*(\d+)")
    adapt_reduce_time_s = get_float(r"^c\s+adapt reduce time\s*:\s*([\d\.\-]+)")

    # PAR-2 score
    par2 = (2.0 * TIMEOUT_S) if timed_out else wall_time

    # Save log file
    log_dir = LOGS_DIR / cfg["id"] / f"rep{rep}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{bmk['id']}_{bmk['name']}.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"=== Command: {' '.join(cmd)} ===\n")
        f.write(f"=== Exit Code: {0 if not timed_out else -1} ===\n")
        f.write(f"=== Wall Time: {wall_time:.4f}s ===\n\n")
        f.write("=== STDOUT ===\n")
        f.write(stdout_txt)
        if stderr_txt:
            f.write("\n=== STDERR ===\n")
            f.write(stderr_txt)

    record = {
        "run_id": run_idx,
        "repetition": rep,
        "config_id": cfg["id"],
        "config_name": cfg["name"],
        "benchmark_id": bmk["id"],
        "benchmark_name": bmk["name"],
        "category": bmk["category"],
        "family_type": family_type,
        "expected_status": bmk["expected"],
        "status": status,
        "result_match": result_match,
        "model_valid": model_valid,
        "timed_out": timed_out,
        "wall_time_s": round(wall_time, 4),
        "cpu_time_s": round(cpu_time, 4),
        "par2_s": round(par2, 4),
        "conflicts": conflicts,
        "decisions": decisions,
        "propagations": propagations,
        "restarts": restarts,
        "genuine_restarts": genuine_restarts,
        "blocked_restarts": blocked_restarts,
        "reduce_db": reduce_db,
        "removed_clauses": removed_clauses,
        "memory_mb": round(memory_mb, 2),
        "qre_native_requests": qre_native_requests,
        "qre_raw_sharpe_events": qre_raw_sharpe_events,
        "qre_raw_var_events": qre_raw_var_events,
        "qre_raw_both_events": qre_raw_both_events,
        "qre_sustained_events": qre_sustained_events,
        "qre_eligible_requests": qre_eligible_requests,
        "qre_executed_restarts": qre_executed_restarts,
        "qre_cooldown_supp": qre_cooldown_supp,
        "qre_cap_supp": qre_cap_supp,
        "qre_strategy_adapt_rst": qre_strategy_adapt_rst,
        "qre_shadow_dec_obs": qre_shadow_dec_obs,
        "qre_shadow_cfc_obs": qre_shadow_cfc_obs,
        "qre_shadow_total_shocks": qre_shadow_total_shocks,
        "qre_shadow_min_sharpe": qre_shadow_min_sharpe,
        "qre_shadow_max_var95": qre_shadow_max_var95,
        "qre_shadow_final_sharpe": qre_shadow_final_sharpe,
        "qre_shadow_final_var95": qre_shadow_final_var95,
        "adapt_reduce_calls": adapt_reduce_calls,
        "adapt_clauses_ranked": adapt_clauses_ranked,
        "adapt_clauses_eligible": adapt_clauses_eligible,
        "adapt_clauses_removed": adapt_clauses_removed,
        "adapt_reduce_time_s": round(adapt_reduce_time_s, 4)
    }
    return record


def main():
    print("=" * 80)
    print("STEP 39: QUANTITATIVE RISK ENGINE (QRE) ACTIVE PILOT EXPERIMENT")
    print("=" * 80)
    print(f"Solver Binary : {SOLVER_PATH}")
    print(f"Configurations: {len(CONFIGURATIONS)} configs")
    print(f"Benchmarks    : {len(DIAGNOSTIC_BENCHMARKS)} instances (Diagnostic Development Suite)")
    print(f"Repetitions   : {REPETITIONS}")
    print(f"Total Runs    : {len(CONFIGURATIONS) * len(DIAGNOSTIC_BENCHMARKS) * REPETITIONS} planned runs")
    print(f"Timeout       : {TIMEOUT_S}s per run\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Check solver binary exists
    if not SOLVER_PATH.is_file():
        print(f"ERROR: Solver binary not found: {SOLVER_PATH}")
        sys.exit(1)

    records = []
    run_idx = 1
    total_runs = len(CONFIGURATIONS) * len(DIAGNOSTIC_BENCHMARKS) * REPETITIONS

    # Open CSV for progressive writing
    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        writer.writeheader()

        # Balanced cyclic execution: Repetition -> Benchmark -> Configuration
        for rep in range(1, REPETITIONS + 1):
            print(f"\n>>> Starting Repetition {rep} / {REPETITIONS} <<<")
            for bmk in DIAGNOSTIC_BENCHMARKS:
                for cfg in CONFIGURATIONS:
                    sys.stdout.write(f"[{run_idx:3d}/{total_runs:3d}] Rep {rep} | {cfg['id']:24s} | {bmk['id']} {bmk['name']:30s} ... ")
                    sys.stdout.flush()

                    rec = run_single(cfg, bmk, rep, run_idx)
                    writer.writerow(rec)
                    csv_file.flush()
                    records.append(rec)

                    qre_rst_str = f"QRE_rst={rec['qre_executed_restarts']}" if cfg['id'] == 'cfg_active_adaptfix' else ""
                    print(f"[{rec['status']:7s}] Wall={rec['wall_time_s']:6.3f}s Cfc={rec['conflicts']:6d} Rst={rec['genuine_restarts']:3d} {qre_rst_str}")

                    run_idx += 1

    print("\n" + "=" * 80)
    print("PILOT EXECUTION COMPLETE")
    print(f"Master CSV written to: {MASTER_CSV}")
    print("=" * 80)

if __name__ == "__main__":
    main()

