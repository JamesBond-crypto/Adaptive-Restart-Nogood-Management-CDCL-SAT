#!/usr/bin/env python3
"""
run_v3_adaptive_fixed_interaction.py - Step 31: V3 Drawdown x Adaptive-Fixed Nogood Retention Factorial Evaluation

Executes a 3x2 factorial design (3 restart policies x 2 clause reduction policies)
across all 36 expanded development benchmark instances with 3 independent repetitions
(648 planned solver executions total) under a 15.0s external timeout:

Factorial Configurations:
  1. cfg1_base_base:       Baseline Restart + Baseline Reduction
  2. cfg2_v1_base:         Adaptive V1 Restart + Baseline Reduction
  3. cfg3_v3dd_base:       V3 Drawdown-Only Restart + Baseline Reduction
  4. cfg4_base_adaptfix:   Baseline Restart + Adaptive-Fixed Reduction
  5. cfg5_v1_adaptfix:     Adaptive V1 Restart + Adaptive-Fixed Reduction
  6. cfg6_v3dd_adaptfix:   V3 Drawdown-Only Restart + Adaptive-Fixed Reduction

Outputs:
  - experiments/results/v3_adaptive_fixed_interaction/master_results.csv
  - experiments/results/v3_adaptive_fixed_interaction/<config_id>.csv
  - experiments/results/v3_adaptive_fixed_interaction/logs/<config_id>/rep<R>/...

Safety & Protocol:
  - Sequential execution (no concurrency).
  - Balanced cyclic configuration rotation.
  - Full SHA-256 integrity recording.
  - Independent SAT model verification.
  - Safe resume logic.
"""

import sys
import os
import csv
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "v3_adaptive_fixed_interaction"
MASTER_CSV = RESULTS_DIR / "master_results.csv"
LOGS_DIR = RESULTS_DIR / "logs"
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-simp.exe"
MANIFEST_PATH = WORKSPACE / "benchmarks" / "expanded_manifest.csv"
TIMEOUT_S = 15.0
REPETITIONS = 3
SCHEDULE_SEED = 20261031

CONFIGURATIONS = [
    {
        "id": "cfg1_base_base",
        "name": "Baseline Restart + Baseline Reduction",
        "restart_strategy": "baseline",
        "reduce_strategy": "baseline",
        "extra_args": [
            "-restart-strategy=baseline",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg2_v1_base",
        "name": "Adaptive V1 Restart + Baseline Reduction",
        "restart_strategy": "adaptive",
        "reduce_strategy": "baseline",
        "extra_args": [
            "-restart-strategy=adaptive",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg3_v3dd_base",
        "name": "V3 Drawdown-Only Restart + Baseline Reduction",
        "restart_strategy": "adaptive-v3",
        "reduce_strategy": "baseline",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg4_base_adaptfix",
        "name": "Baseline Restart + Adaptive-Fixed Reduction",
        "restart_strategy": "baseline",
        "reduce_strategy": "adaptive-fixed",
        "extra_args": [
            "-restart-strategy=baseline",
            "-reduce-strategy=adaptive-fixed"
        ]
    },
    {
        "id": "cfg5_v1_adaptfix",
        "name": "Adaptive V1 Restart + Adaptive-Fixed Reduction",
        "restart_strategy": "adaptive",
        "reduce_strategy": "adaptive-fixed",
        "extra_args": [
            "-restart-strategy=adaptive",
            "-reduce-strategy=adaptive-fixed"
        ]
    },
    {
        "id": "cfg6_v3dd_adaptfix",
        "name": "V3 Drawdown-Only Restart + Adaptive-Fixed Reduction",
        "restart_strategy": "adaptive-v3",
        "reduce_strategy": "adaptive-fixed",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=adaptive-fixed"
        ]
    }
]

DIAGNOSTIC_INSTANCES = {
    "rand3sat_n250_c1065_s1010.cnf",
    "rand3sat_n200_c840_s1005.cnf",
    "php_10p_9h.cnf",
    "php_10p_8h.cnf",
    "gcol_unsat_k10_c9.cnf",
    "gcol_unsat_k9_c8.cnf",
    "planted3sat_n240_c1022_s2009.cnf",
    "planted3sat_n200_c852_s2005.cnf",
}

EXTRA_MASTER_FIELDS = [
    "run_order",
    "repetition",
    "config_id",
    "config_name",
    "restart_strategy_mode",
    "reduce_strategy_mode",
    "family",
    "is_diagnostic_instance",
    "solver_hash",
    "benchmark_hash",
    "exact_args",
]

def compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def load_manifest() -> List[Dict[str, str]]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_completed_runs() -> Set[Tuple[int, str, str]]:
    completed = set()
    if MASTER_CSV.exists():
        with open(MASTER_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rep = int(r["repetition"])
                cfg = r["config_id"]
                bench = r["benchmark_name"]
                completed.add((rep, cfg, bench))
    return completed

def main():
    if not SOLVER_PATH.exists():
        print(f"ERROR: Solver executable not found at {SOLVER_PATH}")
        sys.exit(1)

    solver_hash = compute_file_hash(SOLVER_PATH)
    manifest = load_manifest()
    total_benchmarks = len(manifest)
    total_configs = len(CONFIGURATIONS)
    total_planned_runs = total_benchmarks * total_configs * REPETITIONS

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Precompute benchmark hashes
    bench_hashes = {}
    for item in manifest:
        bp = WORKSPACE / item["filepath"]
        if not bp.exists():
            print(f"ERROR: Benchmark file missing: {bp}")
            sys.exit(1)
        bench_hashes[item["filename"]] = compute_file_hash(bp)

    completed_runs = load_completed_runs()
    already_done = len(completed_runs)

    master_fieldnames = EXTRA_MASTER_FIELDS + CSV_FIELDNAMES

    # Initialize master CSV if not present
    write_header = not MASTER_CSV.exists()
    master_f = open(MASTER_CSV, "a", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_f, fieldnames=master_fieldnames)
    if write_header:
        master_writer.writeheader()
        master_f.flush()

    # Individual CSV writers
    individual_handles = {}
    individual_writers = {}
    for cfg in CONFIGURATIONS:
        c_id = cfg["id"]
        c_path = RESULTS_DIR / f"{c_id}.csv"
        c_write_header = not c_path.exists()
        f = open(c_path, "a", newline="", encoding="utf-8")
        individual_handles[c_id] = f
        w = csv.DictWriter(f, fieldnames=["repetition"] + CSV_FIELDNAMES)
        if c_write_header:
            w.writeheader()
            f.flush()
        individual_writers[c_id] = w

    print("=" * 95)
    print("STEP 31: V3 DRAWDOWN x ADAPTIVE-FIXED RETENTION CONTROLLED FACTORIAL EVALUATION")
    print(f"Solver Executable: {SOLVER_PATH} (SHA-256: {solver_hash})")
    print(f"Benchmark Suite:   36 instances across 4 families (from {MANIFEST_PATH})")
    print(f"Design:            3 Restart Policies x 2 Retention Policies = 6 Factorial Configurations")
    print(f"Repetitions:       {REPETITIONS} independent runs per instance/config pair")
    print(f"Timeout:           {TIMEOUT_S}s per run | Planned Total Runs: {total_planned_runs}")
    print(f"Resumed Progress:  {already_done}/{total_planned_runs} completed")
    print("=" * 95)

    run_counter = already_done
    t_start_global = time.time()

    try:
        for rep in range(1, REPETITIONS + 1):
            print(f"\n{'='*40} REPETITION {rep}/{REPETITIONS} {'='*40}")

            for idx, item in enumerate(manifest):
                bname = item["filename"]
                family = item["family"]
                known_st = item["known_status"]
                is_diag = "1" if bname in DIAGNOSTIC_INSTANCES else "0"
                cnf_path = WORKSPACE / item["filepath"]
                b_hash = bench_hashes[bname]

                # Balanced cyclic rotation order:
                shift = (idx + (rep - 1) * 2) % total_configs
                ordered_cfgs = CONFIGURATIONS[shift:] + CONFIGURATIONS[:shift]

                for cfg in ordered_cfgs:
                    cfg_id = cfg["id"]
                    cfg_name = cfg["name"]

                    if (rep, cfg_id, bname) in completed_runs:
                        continue

                    run_counter += 1
                    cfg_log_dir = LOGS_DIR / cfg_id / f"rep{rep}"

                    t0 = time.time()
                    record = run_single_instance(
                        solver_exe=str(SOLVER_PATH),
                        cnf_file=str(cnf_path),
                        timeout_s=TIMEOUT_S,
                        log_dir=str(cfg_log_dir),
                        emit_model=True,
                        verify_models=True,
                        extra_solver_args=cfg["extra_args"]
                    )
                    wall_time = record["wall_time_s"]
                    st = record["status"]
                    cfc = record["conflicts"]
                    gen_rst = record["genuine_restarts"]
                    v_model = record["model_verified"]

                    # Check for correctness failure
                    if st == "SAT" and v_model == "FAILED":
                        print(f"\n[FATAL ERROR] Model verification failed for {bname} under {cfg_name}!")
                        sys.exit(1)

                    # Write individual CSV
                    indiv_row = {"repetition": rep, **record}
                    individual_writers[cfg_id].writerow(indiv_row)
                    individual_handles[cfg_id].flush()

                    # Write master CSV
                    master_row = {
                        "run_order": run_counter,
                        "repetition": rep,
                        "config_id": cfg_id,
                        "config_name": cfg_name,
                        "restart_strategy_mode": cfg["restart_strategy"],
                        "reduce_strategy_mode": cfg["reduce_strategy"],
                        "family": family,
                        "is_diagnostic_instance": is_diag,
                        "solver_hash": solver_hash,
                        "benchmark_hash": b_hash,
                        "exact_args": " ".join(cfg["extra_args"]),
                        **record
                    }
                    master_writer.writerow(master_row)
                    master_f.flush()
                    completed_runs.add((rep, cfg_id, bname))

                    v_info = f" [Model: {v_model}]" if st == "SAT" else ""
                    diag_tag = "[DIAG]" if bname in DIAGNOSTIC_INSTANCES else "      "
                    print(f"[{run_counter:3d}/{total_planned_runs:3d}] Rep {rep} | {diag_tag} {bname:<32s} | {cfg_name:<38s} -> {st:<7s} {wall_time:6.3f}s | Cfc: {str(cfc):>7s} | Rst: {str(gen_rst):>4s}{v_info}")

    finally:
        for f in individual_handles.values():
            f.close()
        master_f.close()

    total_elapsed = time.time() - t_start_global
    print("\n" + "=" * 95)
    print(f"FACTORIAL CAMPAIGN COMPLETED: {run_counter}/{total_planned_runs} runs recorded in {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)")
    print(f"Master results written to: {MASTER_CSV}")
    print(f"Individual CSVs stored in: {RESULTS_DIR}")
    print("=" * 95)

if __name__ == "__main__":
    main()

