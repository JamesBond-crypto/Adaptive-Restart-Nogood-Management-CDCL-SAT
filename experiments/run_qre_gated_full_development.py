#!/usr/bin/env python3
"""
run_qre_gated_full_development.py - Step 41: Full 36-Instance Validation of Stagnation-Gated QRE

Executes a 6-configuration controlled ablation across all 36 benchmarks from
benchmarks/expanded_manifest.csv with 3 independent repetitions (648 planned runs total)
under a uniform 15.0s wall-clock timeout:

Configurations:
  A. cfg01_baseline_base:     Original Glucose + Baseline Reduction
  B. cfg05_baseline_adaptfix: Original Glucose + Adaptive-Fixed Reduction
  C. cfg_active_adaptfix:     Ungated Active QRE + Adaptive-Fixed Reduction
  D. cfg_gated_base:          Stagnation-Gated QRE + Baseline Reduction
  E. cfg_gated_adaptfix:      Stagnation-Gated QRE + Adaptive-Fixed Reduction
  F. cfg_v3dd_adaptfix:       V3 Drawdown-Only + Adaptive-Fixed Reduction

Protocol:
  - 15.0 second external wall-clock timeout per execution.
  - 30.0 second PAR-2 penalty for timeouts.
  - 3 repetitions per (configuration, benchmark) pair (balanced sequential order).
  - Independent SAT model verification.
  - Full telemetry capture: conflicts, decisions, propagations, restarts,
    genuine restarts, QRE triggers/restarts/suppressions, V3 stats, reductions, memory, runtime.
  - Checkpoint / resume capability to safely resume if interrupted.
  - Target binary: src/glucose_windows/glucose-qre-gated.exe
  - Master CSV: experiments/results/qre_gated_full_development/master_results.csv
"""

import sys
import os
import csv
import time
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

WORKSPACE = Path(r"D:\DAC_203@Project")
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-qre-gated.exe"
MANIFEST_PATH = WORKSPACE / "benchmarks" / "expanded_manifest.csv"
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "qre_gated_full_development"
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

CONFIGURATIONS = [
    {
        "id": "cfg01_baseline_base",
        "name": "Original Glucose + Baseline Reduction",
        "args": ["-restart-strategy=baseline", "-reduce-strategy=baseline", "-model"]
    },
    {
        "id": "cfg05_baseline_adaptfix",
        "name": "Original Glucose + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=baseline", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_active_adaptfix",
        "name": "Ungated Active QRE + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=adaptive-qre", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_gated_base",
        "name": "Stagnation-Gated QRE + Baseline Reduction",
        "args": ["-restart-strategy=adaptive-qre-gated", "-reduce-strategy=baseline", "-model"]
    },
    {
        "id": "cfg_gated_adaptfix",
        "name": "Stagnation-Gated QRE + Adaptive-Fixed Reduction",
        "args": ["-restart-strategy=adaptive-qre-gated", "-reduce-strategy=adaptive-fixed", "-model"]
    },
    {
        "id": "cfg_v3dd_adaptfix",
        "name": "V3 Drawdown-Only + Adaptive-Fixed Reduction",
        "args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=adaptive-fixed",
            "-model"
        ]
    }
]

CSV_HEADERS = [
    "run_id", "repetition", "config_id", "config_name",
    "benchmark_name", "benchmark_path", "family", "parameters", "sha256",
    "expected_status", "status", "result_match", "model_valid", "timed_out",
    "wall_time_s", "cpu_time_s", "par2_s",
    "conflicts", "decisions", "propagations",
    "restarts", "genuine_restarts", "blocked_restarts",
    "reduce_db", "removed_clauses", "memory_mb",
    # Active & Gated QRE telemetry
    "qre_native_requests", "qre_raw_sharpe_events", "qre_raw_var_events", "qre_raw_both_events",
    "qre_sustained_events", "qre_eligible_requests", "qre_executed_restarts",
    "qre_cooldown_supp", "qre_cap_supp", "qre_strategy_adapt_rst",
    # V3 Drawdown telemetry
    "v3_req_trend", "v3_req_drawdown", "v3_req_ceiling", "v3_total_requests",
    "v3_executed_restarts", "v3_blocked_restarts", "v3_max_drawdown", "v3_mean_return",
    # Reduction telemetry
    "adapt_reduce_calls", "adapt_clauses_ranked", "adapt_clauses_eligible", "adapt_clauses_removed",
    "adapt_reduce_time_s"
]

def load_manifest() -> List[Dict[str, Any]]:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")
    benchmarks = []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            benchmarks.append({
                "filename": row["filename"],
                "filepath": row["filepath"],
                "family": row["family"],
                "parameters": row["parameters"],
                "sha256": row["sha256"],
                "known_status": row["known_status"]
            })
    return benchmarks

def run_single(cfg: Dict[str, Any], bmk: Dict[str, Any], rep: int, run_idx: int) -> Dict[str, Any]:
    cnf_full_path = WORKSPACE / bmk["filepath"]
    cmd = [str(SOLVER_PATH)] + cfg["args"] + [str(cnf_full_path)]

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

    # Status detection
    status = "TIMEOUT" if timed_out else "UNKNOWN"
    for line in stdout_txt.splitlines():
        line_s = line.strip()
        if line_s == "s SATISFIABLE":
            status = "SAT"
            break
        elif line_s == "s UNSATISFIABLE":
            status = "UNSAT"
            break

    # Result matching against known status
    expected = bmk["known_status"]
    if expected == "UNKNOWN":
        result_match = True  # Random SAT instances where oracle was not predefined
    else:
        result_match = (status == expected)

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

    # Helper extractors
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

    # QRE telemetry
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

    # V3 Drawdown telemetry
    v3_req_trend = get_int(r"^c\s+v3 req trend\s*:\s*(\d+)")
    v3_req_drawdown = get_int(r"^c\s+v3 req drawdown\s*:\s*(\d+)")
    v3_req_ceiling = get_int(r"^c\s+v3 req ceiling\s*:\s*(\d+)")
    v3_total_requests = get_int(r"^c\s+v3 total requests\s*:\s*(\d+)")
    v3_executed_restarts = get_int(r"^c\s+v3 executed restarts\s*:\s*(\d+)")
    v3_blocked_restarts = get_int(r"^c\s+v3 blocked restarts\s*:\s*(\d+)")
    v3_max_drawdown = get_float(r"^c\s+v3 max observed dd\s*:\s*([\d\.\-]+)")
    v3_mean_return = get_float(r"^c\s+v3 mean return\s*:\s*([\d\.\-]+)")

    # Reduction telemetry
    adapt_reduce_calls = get_int(r"^c\s+adapt reduce calls\s*:\s*(\d+)")
    adapt_clauses_ranked = get_int(r"^c\s+adapt clauses ranked\s*:\s*(\d+)")
    adapt_clauses_eligible = get_int(r"^c\s+adapt clauses eligible\s*:\s*(\d+)")
    adapt_clauses_removed = get_int(r"^c\s+adapt clauses removed\s*:\s*(\d+)")
    adapt_reduce_time_s = get_float(r"^c\s+adapt reduce time\s*:\s*([\d\.]+)")

    # PAR-2 score
    par2 = (2.0 * TIMEOUT_S) if timed_out else wall_time

    # Save log file
    log_dir = LOGS_DIR / cfg["id"] / f"rep{rep}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{bmk['filename']}.log"
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
        "benchmark_name": bmk["filename"],
        "benchmark_path": bmk["filepath"],
        "family": bmk["family"],
        "parameters": bmk["parameters"],
        "sha256": bmk["sha256"],
        "expected_status": expected,
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
        "v3_req_trend": v3_req_trend,
        "v3_req_drawdown": v3_req_drawdown,
        "v3_req_ceiling": v3_req_ceiling,
        "v3_total_requests": v3_total_requests,
        "v3_executed_restarts": v3_executed_restarts,
        "v3_blocked_restarts": v3_blocked_restarts,
        "v3_max_drawdown": v3_max_drawdown,
        "v3_mean_return": v3_mean_return,
        "adapt_reduce_calls": adapt_reduce_calls,
        "adapt_clauses_ranked": adapt_clauses_ranked,
        "adapt_clauses_eligible": adapt_clauses_eligible,
        "adapt_clauses_removed": adapt_clauses_removed,
        "adapt_reduce_time_s": round(adapt_reduce_time_s, 4)
    }
    return record


def main():
    print("=" * 80)
    print("STEP 41: FULL 36-INSTANCE VALIDATION OF STAGNATION-GATED QRE")
    print("=" * 80)
    print(f"Solver Binary : {SOLVER_PATH}")
    print(f"Configurations: {len(CONFIGURATIONS)} configs")
    benchmarks = load_manifest()
    print(f"Benchmarks    : {len(benchmarks)} instances from {MANIFEST_PATH.name}")
    print(f"Repetitions   : {REPETITIONS}")
    total_runs = len(CONFIGURATIONS) * len(benchmarks) * REPETITIONS
    print(f"Total Runs    : {total_runs} planned runs")
    print(f"Timeout       : {TIMEOUT_S}s per run\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if not SOLVER_PATH.is_file():
        print(f"ERROR: Solver binary not found: {SOLVER_PATH}")
        sys.exit(1)

    # Checkpoint / Resume logic: Load existing completed runs
    completed_keys: Set[str] = set()
    existing_rows: List[Dict[str, Any]] = []
    if MASTER_CSV.is_file():
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['repetition']}_{row['config_id']}_{row['benchmark_name']}"
                completed_keys.add(key)
                existing_rows.append(row)
        print(f"[+] Loaded {len(completed_keys)} completed runs from checkpoint: {MASTER_CSV}")

    # Open CSV for append if exists, or write new header
    file_mode = "a" if completed_keys else "w"
    with open(MASTER_CSV, file_mode, newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        if not completed_keys:
            writer.writeheader()

        run_idx = len(completed_keys) + 1

        # Balanced cyclic execution: Repetition -> Benchmark -> Configuration
        for rep in range(1, REPETITIONS + 1):
            print(f"\n>>> Starting Repetition {rep} / {REPETITIONS} <<<")
            for bmk in benchmarks:
                for cfg in CONFIGURATIONS:
                    key = f"{rep}_{cfg['id']}_{bmk['filename']}"
                    if key in completed_keys:
                        continue

                    sys.stdout.write(f"[{run_idx:3d}/{total_runs:3d}] Rep {rep} | {cfg['id']:24s} | {bmk['filename']:32s} ... ")
                    sys.stdout.flush()

                    rec = run_single(cfg, bmk, rep, run_idx)
                    writer.writerow(rec)
                    csv_file.flush()
                    completed_keys.add(key)

                    extra_rst = ""
                    if "qre" in cfg["id"]:
                        extra_rst = f"QRE_rst={rec['qre_executed_restarts']}"
                    elif "v3" in cfg["id"]:
                        extra_rst = f"V3_rst={rec['v3_executed_restarts']}"

                    print(f"[{rec['status']:7s}] Wall={rec['wall_time_s']:6.3f}s Cfc={rec['conflicts']:7d} Rst={rec['genuine_restarts']:3d} {extra_rst}")

                    run_idx += 1

    print("\n" + "=" * 80)
    print("FULL DEVELOPMENT VALIDATION COMPLETE")
    print(f"Master CSV written to: {MASTER_CSV}")
    print("=" * 80)

if __name__ == "__main__":
    main()

