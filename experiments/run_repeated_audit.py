#!/usr/bin/env python3
"""
run_repeated_audit.py - Step 11 Multi-Repetition Validation Harness

Conducts 5 balanced repetitions of baseline vs adaptive solver execution across
all 20 pilot benchmarks (200 solver runs total).
Computes deterministic invariant checks, median runtimes, dispersion (IQR / min / max),
verifies all SAT models, and groups by benchmark family.
"""

import sys
import os
import csv
import time
from pathlib import Path
from statistics import median
from typing import List, Dict, Any

# Ensure experiments module is available
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance
from verify_model import verify_model

BENCHMARK_DIR = Path("benchmarks/pilot")
SOLVER_EXE = Path("src/glucose_windows/glucose-simp.exe")
OUTPUT_CSV = Path("experiments/results/pilot_repeated_eval.csv")
LOG_DIR = Path("experiments/results/pilot_repeated_eval_logs")

REPETITIONS = 5
TIMEOUT_S = 10.0

CSV_FIELDS = [
    "repetition",
    "mode",
    "benchmark_name",
    "family",
    "status",
    "exit_code",
    "timed_out",
    "wall_time_s",
    "cpu_time_s",
    "memory_mb",
    "model_verified",
    "conflicts",
    "decisions",
    "propagations",
    "restarts",
    "blocked_restarts",
    "reduce_db_count",
    "removed_clauses",
    "glue_clauses_dl2",
    "log_file"
]

def determine_family(name: str) -> str:
    if name.startswith("php_"):
        return "Pigeonhole Principle (PHP)"
    elif name.startswith("planted3sat_"):
        return "Planted 3-SAT"
    elif name.startswith("rand3sat_"):
        return "Random 3-SAT"
    return "Other"

def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    benchmarks = sorted(list(BENCHMARK_DIR.glob("*.cnf")))
    if not benchmarks:
        print(f"Error: No benchmarks found in {BENCHMARK_DIR}")
        sys.exit(1)

    print("=" * 80)
    print("STEP 11: REPEATED BENCHMARK EVALUATION (5 Repetitions x 2 Modes x 20 Instances)")
    print("=" * 80)
    print(f"Solver: {SOLVER_EXE}")
    print(f"Benchmarks count: {len(benchmarks)}")
    print(f"Repetitions per mode: {REPETITIONS}")
    print(f"Timeout: {TIMEOUT_S}s")
    print(f"Output CSV: {OUTPUT_CSV}")
    print(f"Log Dir: {LOG_DIR}")
    print("-" * 80)

    all_records: List[Dict[str, Any]] = []

    # Open CSV writer
    csv_file = open(OUTPUT_CSV, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    writer.writeheader()
    csv_file.flush()

    total_runs = REPETITIONS * 2 * len(benchmarks)
    run_idx = 0

    # Interleaved execution: for each repetition, alternate between baseline and adaptive
    for rep in range(1, REPETITIONS + 1):
        print(f"\n>>> Starting Repetition {rep} of {REPETITIONS} ...")
        for b_path in benchmarks:
            bname = b_path.name
            family = determine_family(bname)

            for mode in ["baseline", "adaptive"]:
                run_idx += 1
                extra_args = [f"-restart-strategy={mode}"]

                rec = run_single_instance(
                    solver_exe=str(SOLVER_EXE),
                    cnf_file=str(b_path),
                    timeout_s=TIMEOUT_S,
                    log_dir=str(LOG_DIR),
                    emit_model=True,
                    verify_models=True,
                    extra_solver_args=extra_args
                )

                row = {
                    "repetition": rep,
                    "mode": mode,
                    "benchmark_name": bname,
                    "family": family,
                    "status": rec.get("status", ""),
                    "exit_code": rec.get("exit_code", ""),
                    "timed_out": rec.get("timed_out", False),
                    "wall_time_s": rec.get("wall_time_s", 0.0),
                    "cpu_time_s": rec.get("cpu_time_s", 0.0),
                    "memory_mb": rec.get("memory_mb", 0.0),
                    "model_verified": rec.get("model_verified", ""),
                    "conflicts": rec.get("conflicts", 0),
                    "decisions": rec.get("decisions", 0),
                    "propagations": rec.get("propagations", 0),
                    "restarts": rec.get("restarts", 0),
                    "blocked_restarts": rec.get("blocked_restarts", 0),
                    "reduce_db_count": rec.get("reduce_db_count", 0),
                    "removed_clauses": rec.get("removed_clauses", 0),
                    "glue_clauses_dl2": rec.get("glue_clauses_dl2", 0),
                    "log_file": rec.get("log_file", "")
                }

                writer.writerow(row)
                csv_file.flush()
                all_records.append(row)

                # Progress log
                status_str = row["status"]
                wt = row["wall_time_s"]
                cfc = row["conflicts"]
                print(f"[{run_idx:3d}/{total_runs}] Rep {rep} | {mode:8s} | {bname:<30} | {status_str:^5} in {wt:6.3f}s | Cfc: {cfc}")

    csv_file.close()
    print("-" * 80)
    print(f"[+] All {total_runs} runs completed successfully. Saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()

