#!/usr/bin/env python3
"""
run_v3_component_evaluation.py - Finance-Inspired Adaptive Restart V3: Component Validation

Executes 6 solver configurations across 8 representative development instances
(48 runs total) with 15.0s external timeout under balanced cyclic rotation order:

  1. cfg1_baseline:          Baseline Glucose (restart=baseline, reduce=baseline)
  2. cfg2_v1:                Adaptive V1 (restart=adaptive, reduce=baseline)
  3. cfg3_v3_trend_only:     Active V3 Trend Only (restart=adaptive-v3, v3-trend=1, v3-dd=0, v3-ceil=0)
  4. cfg4_v3_drawdown_only:  Active V3 Drawdown Only (restart=adaptive-v3, v3-trend=0, v3-dd=1, v3-ceil=0)
  5. cfg5_v3_ceiling_only:   Active V3 Ceiling Only (restart=adaptive-v3, v3-trend=0, v3-dd=0, v3-ceil=1)
  6. cfg6_v3_combined:       Active V3 Combined (restart=adaptive-v3, v3-trend=1, v3-dd=1, v3-ceil=1)

Outputs:
  - experiments/results/v3_component_evaluation.csv
  - experiments/results/v3_component_evaluation/<cfg_id>.csv
  - experiments/results/v3_component_logs/<cfg_id>/...
"""

import sys
import os
import csv
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES

WORKSPACE = Path(r"D:\DAC_203@Project")
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "v3_component_evaluation"
MASTER_CSV = WORKSPACE / "experiments" / "results" / "v3_component_evaluation.csv"
LOGS_DIR = WORKSPACE / "experiments" / "results" / "v3_component_logs"
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-simp.exe"
BENCHMARK_DIR = WORKSPACE / "benchmarks" / "expanded"
TIMEOUT_S = 15.0

CONFIGURATIONS = [
    {
        "id": "cfg1_baseline",
        "name": "Baseline Glucose",
        "extra_args": [
            "-restart-strategy=baseline",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg2_v1",
        "name": "Adaptive V1",
        "extra_args": [
            "-restart-strategy=adaptive",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg3_v3_trend_only",
        "name": "Active V3 (Trend Only)",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=1",
            "-v3-drawdown=0",
            "-v3-ceiling=0",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg4_v3_drawdown_only",
        "name": "Active V3 (Drawdown Only)",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg5_v3_ceiling_only",
        "name": "Active V3 (Ceiling Only)",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=0",
            "-v3-ceiling=1",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg6_v3_combined",
        "name": "Active V3 (Combined: Trend + DD + Ceil)",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=1",
            "-v3-drawdown=1",
            "-v3-ceiling=1",
            "-reduce-strategy=baseline"
        ]
    }
]

TARGET_INSTANCES = [
    ("rand3sat_n250_c1065_s1010.cnf", "rand3sat", "SAT"),
    ("rand3sat_n200_c840_s1005.cnf", "rand3sat", "UNSAT"),
    ("php_10p_9h.cnf", "php", "UNSAT"),
    ("php_10p_8h.cnf", "php", "UNSAT"),
    ("gcol_unsat_k10_c9.cnf", "gcol", "UNSAT"),
    ("gcol_unsat_k9_c8.cnf", "gcol", "UNSAT"),
    ("planted3sat_n240_c1022_s2009.cnf", "planted3sat", "SAT"),
    ("planted3sat_n200_c852_s2005.cnf", "planted3sat", "SAT"),
]

def compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    if not SOLVER_PATH.exists():
        print(f"ERROR: Solver executable not found at {SOLVER_PATH}")
        sys.exit(1)

    solver_hash = compute_file_hash(SOLVER_PATH)

    # Check benchmarks
    for fname, fam, st in TARGET_INSTANCES:
        p = BENCHMARK_DIR / fname
        if not p.exists():
            print(f"ERROR: Benchmark file not found at {p}")
            sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Individual CSV writers
    individual_handles = {}
    individual_writers = {}
    for cfg in CONFIGURATIONS:
        c_id = cfg["id"]
        c_path = RESULTS_DIR / f"{c_id}.csv"
        f = open(c_path, "w", newline="", encoding="utf-8")
        individual_handles[c_id] = f
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        f.flush()
        individual_writers[c_id] = w

    # Master CSV writer
    master_fieldnames = ["run_order", "config_id", "config_name", "family"] + CSV_FIELDNAMES
    master_f = open(MASTER_CSV, "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_f, fieldnames=master_fieldnames)
    master_writer.writeheader()
    master_f.flush()

    total_instances = len(TARGET_INSTANCES)
    total_configs = len(CONFIGURATIONS)
    total_runs = total_instances * total_configs

    print("=" * 85)
    print("FINANCE-INSPIRED ADAPTIVE RESTART V3: COMPONENT VALIDATION EVALUATION")
    print(f"Solver: {SOLVER_PATH} (SHA-256: {solver_hash[:16]}...)")
    print(f"Benchmarks: {total_instances} development instances | Timeout: {TIMEOUT_S}s")
    print(f"Configurations: {total_configs} | Total runs: {total_runs}")
    print(f"Execution Order: Balanced Cyclic Permutation across configurations")
    print("=" * 85)

    run_counter = 0
    t_start_global = time.time()

    try:
        for idx, (bname, family, known_status) in enumerate(TARGET_INSTANCES):
            cnf_path = BENCHMARK_DIR / bname

            # Balanced cyclic rotation order:
            shift = idx % total_configs
            ordered_cfgs = CONFIGURATIONS[shift:] + CONFIGURATIONS[:shift]

            print(f"\n[{idx + 1:2d}/{total_instances:2d}] Benchmark: {bname} (Family: {family}, Known: {known_status})")

            for cfg in ordered_cfgs:
                run_counter += 1
                cfg_id = cfg["id"]
                cfg_name = cfg["name"]
                cfg_log_dir = LOGS_DIR / cfg_id

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
                red = record["reduce_db_count"]
                v_model = record["model_verified"]

                # Write individual CSV
                individual_writers[cfg_id].writerow(record)
                individual_handles[cfg_id].flush()

                # Write master CSV
                master_row = {
                    "run_order": run_counter,
                    "config_id": cfg_id,
                    "config_name": cfg_name,
                    "family": family,
                    **record
                }
                master_writer.writerow(master_row)
                master_f.flush()

                v_info = f" [Model: {v_model}]" if st == "SAT" else ""
                req_info = ""
                if "adaptive-v3" in " ".join(cfg["extra_args"]):
                    req_info = f" | V3req(T={record.get('v3_req_trend', '')},DD={record.get('v3_req_drawdown', '')},C={record.get('v3_req_ceiling', '')})"
                print(f"  ({run_counter:2d}/{total_runs:2d}) {cfg_name:38s} -> {st:7s} in {wall_time:6.3f}s | Cfc: {str(cfc):>7s} | Rst: {str(gen_rst):>4s}{v_info}{req_info}")

    finally:
        for f in individual_handles.values():
            f.close()
        master_f.close()

    total_time = time.time() - t_start_global
    print("\n" + "=" * 85)
    print(f"EXPERIMENT COMPLETED in {total_time:.2f}s ({total_time / 60:.1f}m)")
    print(f"Master results written to: {MASTER_CSV}")
    print(f"Configuration CSVs in:    {RESULTS_DIR}")
    print("=" * 85)

if __name__ == "__main__":
    main()
