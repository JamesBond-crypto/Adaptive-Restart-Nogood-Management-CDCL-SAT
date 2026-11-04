#!/usr/bin/env python3
"""
run_v3_low_frequency_control.py - Step 32: Frequency-Controlled Restart Baselines for Finance-Inspired V3

Executes a 10-configuration comparative evaluation across the 8 Step 29 diagnostic benchmarks
(80 planned solver executions total) under a 15.0s uniform external timeout:

Configurations (Baseline Clause Retention):
  1. cfg01_baseline_base:       Original Glucose Baseline (-restart-strategy=baseline -reduce-strategy=baseline)
  2. cfg02_v1_base:             Adaptive V1 Restart (-restart-strategy=adaptive -reduce-strategy=baseline)
  3. cfg03_v3dd_base:           V3 Drawdown-Only Restart (-restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=baseline)
  4. cfg04_fixed10k_base:       Fixed Interval 10,000 (-restart-strategy=fixed-interval -fixed-restart-interval=10000 -reduce-strategy=baseline)
  5. cfg05_fixed20k_base:       Fixed Interval 20,000 (-restart-strategy=fixed-interval -fixed-restart-interval=20000 -reduce-strategy=baseline)
  6. cfg06_noheuristic_base:    No Heuristic Restarts (-restart-strategy=no-heuristic-restart -reduce-strategy=baseline)

Configurations (Adaptive-Fixed Clause Retention):
  7. cfg07_v3dd_adaptfix:       V3 Drawdown-Only + Adaptive-Fixed (-restart-strategy=adaptive-v3 -v3-trend=0 -v3-drawdown=1 -v3-ceiling=0 -reduce-strategy=adaptive-fixed)
  8. cfg08_fixed10k_adaptfix:   Fixed Interval 10,000 + Adaptive-Fixed (-restart-strategy=fixed-interval -fixed-restart-interval=10000 -reduce-strategy=adaptive-fixed)
  9. cfg09_fixed20k_adaptfix:   Fixed Interval 20,000 + Adaptive-Fixed (-restart-strategy=fixed-interval -fixed-restart-interval=20000 -reduce-strategy=adaptive-fixed)
 10. cfg10_noheuristic_adaptfix: No Heuristic Restarts + Adaptive-Fixed (-restart-strategy=no-heuristic-restart -reduce-strategy=adaptive-fixed)

Diagnostic Benchmarks (8 instances):
  - rand3sat_n250_c1065_s1010.cnf (Rand 3-SAT, SAT)
  - rand3sat_n200_c840_s1005.cnf (Rand 3-SAT, UNSAT)
  - php_10p_9h.cnf (PHP, UNSAT)
  - php_10p_8h.cnf (PHP, UNSAT)
  - gcol_unsat_k10_c9.cnf (Graph Col, UNSAT)
  - gcol_unsat_k9_c8.cnf (Graph Col, UNSAT)
  - planted3sat_n240_c1022_s2009.cnf (Planted SAT, SAT)
  - planted3sat_n200_c852_s2005.cnf (Planted SAT, SAT)

Protocol:
  - Sequential execution (no concurrency).
  - Balanced cyclic configuration rotation.
  - Full SHA-256 binary hash verification.
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
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "v3_low_frequency_control"
MASTER_CSV = RESULTS_DIR / "master_results.csv"
LOGS_DIR = RESULTS_DIR / "logs"
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-simp.exe"
EXPANDED_DIR = WORKSPACE / "benchmarks" / "expanded"
TIMEOUT_S = 15.0

DIAGNOSTIC_BENCHMARKS = [
    "rand3sat_n250_c1065_s1010.cnf",
    "rand3sat_n200_c840_s1005.cnf",
    "php_10p_9h.cnf",
    "php_10p_8h.cnf",
    "gcol_unsat_k10_c9.cnf",
    "gcol_unsat_k9_c8.cnf",
    "planted3sat_n240_c1022_s2009.cnf",
    "planted3sat_n200_c852_s2005.cnf"
]

CONFIGURATIONS = [
    {
        "id": "cfg01_baseline_base",
        "name": "Baseline Restart + Baseline Reduction",
        "restart_strategy": "baseline",
        "reduce_strategy": "baseline",
        "fixed_interval": 0,
        "extra_args": [
            "-restart-strategy=baseline",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg02_v1_base",
        "name": "Adaptive V1 Restart + Baseline Reduction",
        "restart_strategy": "adaptive",
        "reduce_strategy": "baseline",
        "fixed_interval": 0,
        "extra_args": [
            "-restart-strategy=adaptive",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg03_v3dd_base",
        "name": "V3 Drawdown-Only Restart + Baseline Reduction",
        "restart_strategy": "adaptive-v3",
        "reduce_strategy": "baseline",
        "fixed_interval": 0,
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg04_fixed10k_base",
        "name": "Fixed Interval 10,000 + Baseline Reduction",
        "restart_strategy": "fixed-interval",
        "reduce_strategy": "baseline",
        "fixed_interval": 10000,
        "extra_args": [
            "-restart-strategy=fixed-interval",
            "-fixed-restart-interval=10000",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg05_fixed20k_base",
        "name": "Fixed Interval 20,000 + Baseline Reduction",
        "restart_strategy": "fixed-interval",
        "reduce_strategy": "baseline",
        "fixed_interval": 20000,
        "extra_args": [
            "-restart-strategy=fixed-interval",
            "-fixed-restart-interval=20000",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg06_noheuristic_base",
        "name": "No Heuristic Restarts + Baseline Reduction",
        "restart_strategy": "no-heuristic-restart",
        "reduce_strategy": "baseline",
        "fixed_interval": 0,
        "extra_args": [
            "-restart-strategy=no-heuristic-restart",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg07_v3dd_adaptfix",
        "name": "V3 Drawdown-Only + Adaptive-Fixed Reduction",
        "restart_strategy": "adaptive-v3",
        "reduce_strategy": "adaptive-fixed",
        "fixed_interval": 0,
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=adaptive-fixed"
        ]
    },
    {
        "id": "cfg08_fixed10k_adaptfix",
        "name": "Fixed Interval 10,000 + Adaptive-Fixed Reduction",
        "restart_strategy": "fixed-interval",
        "reduce_strategy": "adaptive-fixed",
        "fixed_interval": 10000,
        "extra_args": [
            "-restart-strategy=fixed-interval",
            "-fixed-restart-interval=10000",
            "-reduce-strategy=adaptive-fixed"
        ]
    },
    {
        "id": "cfg09_fixed20k_adaptfix",
        "name": "Fixed Interval 20,000 + Adaptive-Fixed Reduction",
        "restart_strategy": "fixed-interval",
        "reduce_strategy": "adaptive-fixed",
        "fixed_interval": 20000,
        "extra_args": [
            "-restart-strategy=fixed-interval",
            "-fixed-restart-interval=20000",
            "-reduce-strategy=adaptive-fixed"
        ]
    },
    {
        "id": "cfg10_noheuristic_adaptfix",
        "name": "No Heuristic Restarts + Adaptive-Fixed Reduction",
        "restart_strategy": "no-heuristic-restart",
        "reduce_strategy": "adaptive-fixed",
        "fixed_interval": 0,
        "extra_args": [
            "-restart-strategy=no-heuristic-restart",
            "-reduce-strategy=adaptive-fixed"
        ]
    }
]

EXTRA_FIELDNAMES = [
    "config_id",
    "config_name",
    "restart_policy",
    "reduction_policy",
    "fixed_interval_target",
    "family",
    "genuine_restarts",
    "solver_binary_sha256"
]

FULL_FIELDNAMES = EXTRA_FIELDNAMES + [f for f in CSV_FIELDNAMES if f not in EXTRA_FIELDNAMES]

def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def load_existing_completed_runs(csv_path: Path) -> Set[Tuple[str, str]]:
    completed = set()
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                completed.add((row["config_id"], row["benchmark_name"]))
    return completed

def build_execution_schedule() -> List[Tuple[Dict[str, Any], Path, str]]:
    """Builds a balanced cyclic execution schedule across the 8 benchmarks and 10 configs."""
    num_configs = len(CONFIGURATIONS)
    schedule = []
    
    for inst_idx, b_name in enumerate(DIAGNOSTIC_BENCHMARKS):
        cnf_path = EXPANDED_DIR / b_name
        # Determine family
        if "php" in b_name:
            family = "PHP"
        elif "gcol" in b_name:
            family = "Graph Coloring"
        elif "planted" in b_name:
            family = "Planted Satisfiable"
        else:
            family = "Random 3-SAT"
            
        # Balanced cyclic rotation: offset = inst_idx % num_configs
        for cfg_offset in range(num_configs):
            cfg_idx = (inst_idx + cfg_offset) % num_configs
            cfg = CONFIGURATIONS[cfg_idx]
            schedule.append((cfg, cnf_path, family))
            
    return schedule

def main():
    print("=" * 80)
    print("STEP 32: FREQUENCY-CONTROLLED RESTART BASELINES EVALUATION")
    print("=" * 80)
    
    assert SOLVER_PATH.exists(), f"Solver binary not found: {SOLVER_PATH}"
    solver_sha256 = get_file_sha256(SOLVER_PATH)
    print(f"[*] Solver Binary   : {SOLVER_PATH}")
    print(f"[*] SHA-256 Hash    : {solver_sha256}")
    print(f"[*] Configurations  : {len(CONFIGURATIONS)}")
    print(f"[*] Benchmarks      : {len(DIAGNOSTIC_BENCHMARKS)}")
    print(f"[*] Planned Runs    : {len(CONFIGURATIONS) * len(DIAGNOSTIC_BENCHMARKS)}")
    print(f"[*] Timeout per run : {TIMEOUT_S}s")
    print(f"[*] Results Dir     : {RESULTS_DIR}")
    print("=" * 80)
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    completed_runs = load_existing_completed_runs(MASTER_CSV)
    if completed_runs:
        print(f"[*] Found {len(completed_runs)} already completed runs. Resuming...")
        
    schedule = build_execution_schedule()
    total_runs = len(schedule)
    
    # Open master CSV
    master_file_exists = MASTER_CSV.exists()
    master_file = open(MASTER_CSV, "a" if master_file_exists else "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_file, fieldnames=FULL_FIELDNAMES)
    if not master_file_exists:
        master_writer.writeheader()
        master_file.flush()
        
    start_time = time.time()
    runs_executed = 0
    runs_skipped = 0
    
    for run_idx, (cfg, cnf_path, family) in enumerate(schedule, 1):
        cfg_id = cfg["id"]
        b_name = cnf_path.name
        
        if (cfg_id, b_name) in completed_runs:
            runs_skipped += 1
            continue
            
        cfg_log_dir = LOGS_DIR / cfg_id
        cfg_log_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[{run_idx}/{total_runs}] Running {cfg_id} on {b_name} ... ", end="", flush=True)
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
        elapsed = time.time() - t0
        
        # Populate extra metadata fields
        starts_val = int(record.get("restarts", 0)) if record.get("restarts") else 0
        genuine_rsts = max(0, starts_val - 1) if starts_val > 0 else 0
        
        record["config_id"] = cfg_id
        record["config_name"] = cfg["name"]
        record["restart_policy"] = cfg["restart_strategy"]
        record["reduction_policy"] = cfg["reduce_strategy"]
        record["fixed_interval_target"] = cfg["fixed_interval"]
        record["family"] = family
        record["genuine_restarts"] = genuine_rsts
        record["solver_binary_sha256"] = solver_sha256
        
        # Write to master CSV
        master_writer.writerow(record)
        master_file.flush()
        
        # Write to per-config CSV
        cfg_csv = RESULTS_DIR / f"{cfg_id}.csv"
        cfg_exists = cfg_csv.exists()
        with open(cfg_csv, "a" if cfg_exists else "w", newline="", encoding="utf-8") as cf:
            cw = csv.DictWriter(cf, fieldnames=FULL_FIELDNAMES)
            if not cfg_exists:
                cw.writeheader()
            cw.writerow(record)
            
        completed_runs.add((cfg_id, b_name))
        runs_executed += 1
        
        # Status print
        status = record.get("status", "UNKNOWN")
        cfc = record.get("conflicts", "N/A")
        w_time = record.get("wall_time_s", elapsed)
        fixed_req = record.get("fixed_restart_requests", "")
        adapt_rst = record.get("strategy_adaptation_restarts", "")
        
        diag_str = f"R={genuine_rsts}"
        if cfg["restart_strategy"] == "fixed-interval":
            diag_str += f", FReq={fixed_req}, Adapt={adapt_rst}"
            
        print(f"{status} in {w_time:.3f}s (C={cfc}, {diag_str})")
        
    master_file.close()
    total_elapsed = time.time() - start_time
    print("=" * 80)
    print(f"[+] All runs completed in {total_elapsed:.1f}s.")
    print(f"[*] Executed: {runs_executed}, Skipped: {runs_skipped}, Total: {total_runs}")
    print(f"[*] Master dataset written to: {MASTER_CSV}")
    print("=" * 80)

if __name__ == "__main__":
    main()

