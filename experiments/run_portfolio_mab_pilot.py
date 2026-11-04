#!/usr/bin/env python3
"""
experiments/run_portfolio_mab_pilot.py - Step 44: Duration-Aware Portfolio-MAB Pilot Evaluation

Executes a 5-configuration controlled ablation across the 16 development diagnostic
instances with 3 independent repetitions (240 solver runs total) under a 15.0s timeout:

Configurations:
  A. cfg01_baseline_base:     Native Glucose + Baseline Reduction
  B. cfg05_baseline_adaptfix: Native Glucose + Adaptive-Fixed Reduction
  C. cfg_v3dd_adaptfix:       V3 Drawdown + Adaptive-Fixed Reduction
  D. cfg_mab_adaptfix:        Portfolio-MAB + Adaptive-Fixed Reduction
  E. cfg_mab_base:            Portfolio-MAB + Baseline Reduction

Protocol:
  - 15.0 second external timeout per execution (30.0s PAR-2 penalty).
  - 3 repetitions per configuration and benchmark (balanced sequential order).
  - Independent SAT model verification.
  - Full telemetry capture: conflicts, decisions, propagations, restarts,
    mab arm selections, rewards, UCB scores, postponements, memory, CPU time, wall time.
  - Target binary: src/glucose_windows/glucose-portfolio-mab.exe
  - Master CSV: experiments/results/portfolio_mab_pilot/master_results.csv
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
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-portfolio-mab.exe"
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "portfolio_mab_pilot"
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

# The 16 Step 39 diagnostic instances
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
        "id": "cfg_v3dd_adaptfix",
        "name": "V3 Drawdown + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=adaptive-v3", "-v3-trend=0", "-v3-drawdown=1", "-v3-ceiling=0", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_mab_adaptfix",
        "name": "Portfolio-MAB + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=portfolio-mab", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_mab_base",
        "name": "Portfolio-MAB + Baseline Reduction",
        "args": ["-restart-strategy=portfolio-mab", "-reduce-strategy=baseline", "-model"]
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
    # Portfolio-MAB telemetry
    "mab_arm0_selections", "mab_arm1_selections", "mab_total_intervals",
    "mab_postponed_requests", "mab_executed_postp_restarts", "mab_canceled_postp_restarts",
    "mab_arm0_mean_reward", "mab_arm1_mean_reward",
    "mab_arm0_final_ucb", "mab_arm1_final_ucb", "mab_next_arm",
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
    except subprocess.TimeoutExpired as e:
        timed_out = True
        wall_time = TIMEOUT_S
        stdout_txt = e.stdout.decode("utf-8", errors="replace") if e.stdout else ""
        stderr_txt = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""

    # Parse stdout
    status = "TIMEOUT" if timed_out else "UNKNOWN"
    for line in stdout_txt.splitlines():
        if line.startswith("s SATISFIABLE"):
            status = "SAT"
        elif line.startswith("s UNSATISFIABLE"):
            status = "UNSAT"

    result_match = (status == bmk["expected"])

    # Model checking for SAT
    model_valid = "N/A"
    if status == "SAT":
        if verify_model is not None:
            v_lines = "\n".join([line for line in stdout_txt.splitlines() if line.startswith("v ")])
            is_valid, msg = verify_model(str(cnf_full_path), v_lines if v_lines else stdout_txt)
            model_valid = "PASS" if is_valid else f"FAIL: {msg}"
        else:
            model_valid = "NOT_CHECKED"

    par2 = 2.0 * TIMEOUT_S if timed_out else wall_time

    # Helper regex parser
    def get_val(pattern, default=0, is_float=False):
        m = re.search(pattern, stdout_txt)
        if m:
            try:
                return float(m.group(1)) if is_float else int(m.group(1))
            except ValueError:
                return default
        return default

    conflicts = get_val(r"c conflicts\s*:\s*(\d+)")
    decisions = get_val(r"c decisions\s*:\s*(\d+)")
    props = get_val(r"c propagations\s*:\s*(\d+)")
    restarts = get_val(r"c restarts\s*:\s*(\d+)")
    genuine_restarts = get_val(r"c genuine restarts\s*:\s*(\d+)")
    blocked_restarts = get_val(r"c blocked restarts\s*:\s*(\d+)")
    reduce_db = get_val(r"c nb ReduceDB\s*:\s*(\d+)")
    removed_clauses = get_val(r"c nb removed Clauses\s*:\s*(\d+)")
    cpu_time = get_val(r"c CPU time\s*:\s*([\d\.]+)\s*s", is_float=True, default=wall_time)
    mem_mb = get_val(r"c Memory used\s*:\s*([\d\.]+)\s*MB", is_float=True, default=0.0)

    # Portfolio-MAB telemetry
    mab_arm0 = get_val(r"c mab arm 0 selections\s*:\s*(\d+)")
    mab_arm1 = get_val(r"c mab arm 1 selections\s*:\s*(\d+)")
    mab_intervals = get_val(r"c mab total intervals\s*:\s*(\d+)")
    mab_postp_req = get_val(r"c mab postponed requests\s*:\s*(\d+)")
    mab_exec_postp = get_val(r"c mab executed postp rst\s*:\s*(\d+)")
    mab_canc_postp = get_val(r"c mab canceled postp rst\s*:\s*(\d+)")
    mab_r0 = get_val(r"c mab arm 0 mean reward\s*:\s*([\d\.\-]+)", is_float=True, default=0.0)
    mab_r1 = get_val(r"c mab arm 1 mean reward\s*:\s*([\d\.\-]+)", is_float=True, default=0.0)
    mab_ucb0 = get_val(r"c mab arm 0 final ucb\s*:\s*([\d\.\-]+)", is_float=True, default=0.0)
    mab_ucb1 = get_val(r"c mab arm 1 final ucb\s*:\s*([\d\.\-]+)", is_float=True, default=0.0)
    mab_next = get_val(r"c mab next arm\s*:\s*(\d+)", default=0)

    # Reduction telemetry
    adapt_calls = get_val(r"c adapt reduce calls\s*:\s*(\d+)")
    adapt_ranked = get_val(r"c adapt clauses ranked\s*:\s*(\d+)")
    adapt_eligible = get_val(r"c adapt clauses eligible\s*:\s*(\d+)")
    adapt_removed = get_val(r"c adapt clauses removed\s*:\s*(\d+)")
    adapt_time = get_val(r"c adapt reduce time\s*:\s*([\d\.]+)\s*s", is_float=True, default=0.0)

    # Save log file
    log_name = f"run_{run_idx:04d}_{cfg['id']}_{bmk['id']}_rep{rep}.log"
    log_path = LOGS_DIR / log_name
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"=== COMMAND: {' '.join(cmd)} ===\n")
        f.write(f"=== EXIT STATUS: {'TIMEOUT' if timed_out else 'COMPLETE'} ===\n")
        f.write(stdout_txt)
        if stderr_txt:
            f.write("\n=== STDERR ===\n")
            f.write(stderr_txt)

    return {
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
        "wall_time_s": f"{wall_time:.4f}",
        "cpu_time_s": f"{cpu_time:.4f}",
        "par2_s": f"{par2:.4f}",
        "conflicts": conflicts,
        "decisions": decisions,
        "propagations": props,
        "restarts": restarts,
        "genuine_restarts": genuine_restarts,
        "blocked_restarts": blocked_restarts,
        "reduce_db": reduce_db,
        "removed_clauses": removed_clauses,
        "memory_mb": f"{mem_mb:.2f}",
        "mab_arm0_selections": mab_arm0,
        "mab_arm1_selections": mab_arm1,
        "mab_total_intervals": mab_intervals,
        "mab_postponed_requests": mab_postp_req,
        "mab_executed_postp_restarts": mab_exec_postp,
        "mab_canceled_postp_restarts": mab_canc_postp,
        "mab_arm0_mean_reward": f"{mab_r0:.6f}",
        "mab_arm1_mean_reward": f"{mab_r1:.6f}",
        "mab_arm0_final_ucb": f"{mab_ucb0:.6f}",
        "mab_arm1_final_ucb": f"{mab_ucb1:.6f}",
        "mab_next_arm": mab_next,
        "adapt_reduce_calls": adapt_calls,
        "adapt_clauses_ranked": adapt_ranked,
        "adapt_clauses_eligible": adapt_eligible,
        "adapt_clauses_removed": adapt_removed,
        "adapt_reduce_time_s": f"{adapt_time:.4f}"
    }

def main():
    print("=" * 100)
    print("STEP 44: DURATION-AWARE PORTFOLIO-MAB CONTROLLED DEVELOPMENT PILOT")
    print(f"Configurations : {len(CONFIGURATIONS)}")
    print(f"Benchmarks     : {len(DIAGNOSTIC_BENCHMARKS)} (16 diagnostic development instances)")
    print(f"Repetitions    : {REPETITIONS}")
    print(f"Total Runs     : {len(CONFIGURATIONS) * len(DIAGNOSTIC_BENCHMARKS) * REPETITIONS} solver executions")
    print(f"Timeout        : {TIMEOUT_S}s per run (PAR-2: {TIMEOUT_S*2.0}s)")
    print(f"Binary         : {SOLVER_PATH}")
    print("=" * 100)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Check for resume
    completed_runs = {}
    if MASTER_CSV.exists():
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (int(row["repetition"]), row["config_id"], row["benchmark_id"])
                completed_runs[key] = row
        print(f"Resuming experiment: {len(completed_runs)} runs already completed.")

    # Plan balanced sequential order: rep -> bmk -> cfg
    run_plan = []
    run_idx = 1
    for rep in range(1, REPETITIONS + 1):
        for bmk in DIAGNOSTIC_BENCHMARKS:
            for cfg in CONFIGURATIONS:
                run_plan.append((run_idx, rep, bmk, cfg))
                run_idx += 1

    total_planned = len(run_plan)
    print(f"Total planned runs in sequential schedule: {total_planned}")

    csv_file = open(MASTER_CSV, "a" if completed_runs else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
    if not completed_runs:
        writer.writeheader()
        csv_file.flush()

    try:
        for idx, rep, bmk, cfg in run_plan:
            key = (rep, cfg["id"], bmk["id"])
            if key in completed_runs:
                continue

            print(f"[{idx:03d}/{total_planned:03d}] Rep {rep} | {cfg['id'][:20]:20s} | {bmk['id']:6s} ({bmk['name'][:24]:24s})... ", end="", flush=True)

            res = run_single(cfg, bmk, rep, idx)
            writer.writerow(res)
            csv_file.flush()

            status_str = res["status"]
            if res["status"] == "SAT":
                status_str += f" (Model: {res['model_valid']})"
            print(f"{status_str:18s} | Wall: {res['wall_time_s']:>7s}s | Cfc: {res['conflicts']:>7d} | MAB Int: {res['mab_total_intervals']:>3d} (A0:{res['mab_arm0_selections']} A1:{res['mab_arm1_selections']})")

    finally:
        csv_file.close()

    print("\n" + "=" * 100)
    print("PORTFOLIO-MAB PILOT EXECUTION COMPLETE")
    print(f"Results written to: {MASTER_CSV}")
    print("=" * 100)

if __name__ == "__main__":
    main()

