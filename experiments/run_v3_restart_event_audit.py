#!/usr/bin/env python3
"""
run_v3_restart_event_audit.py - Step 33: V3 Drawdown vs No-Heuristic Restart Audit

Conducts controlled repeated timing and restart-event measurements on the 8 diagnostic
benchmarks across 4 core configurations (3 repetitions each, 96 runs total):

Configurations:
  1. cfg01_v3dd_base:           V3 Drawdown-Only + Baseline Reduction
  2. cfg02_noheuristic_base:    No-Heuristic Restarts + Baseline Reduction
  3. cfg03_v3dd_adaptfix:       V3 Drawdown-Only + Adaptive-Fixed Reduction
  4. cfg04_noheuristic_adaptfix: No-Heuristic Restarts + Adaptive-Fixed Reduction

Protocol:
  - 8 diagnostic instances x 4 configurations x 3 repetitions = 96 runs.
  - Uniform 15.0s external timeout.
  - Sequential execution.
  - Balanced cyclic configuration and repetition interleaving.
  - Opt-in -restart-trace enabled for event logging.
  - Independent SAT model verification.
  - Preserves results in experiments/results/v3_restart_event_audit/
"""

import sys
import os
import re
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
RESULTS_DIR = WORKSPACE / "experiments" / "results" / "v3_restart_event_audit"
MASTER_CSV = RESULTS_DIR / "master_results.csv"
LOGS_DIR = RESULTS_DIR / "logs"
SOLVER_PATH = WORKSPACE / "src" / "glucose_windows" / "glucose-simp.exe"
EXPANDED_DIR = WORKSPACE / "benchmarks" / "expanded"
TIMEOUT_S = 15.0
REPETITIONS = 3

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
        "id": "cfg01_v3dd_base",
        "name": "V3 Drawdown + Baseline Reduction",
        "restart_strategy": "adaptive-v3",
        "reduce_strategy": "baseline",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=baseline",
            "-restart-trace"
        ]
    },
    {
        "id": "cfg02_noheuristic_base",
        "name": "No-Heuristic + Baseline Reduction",
        "restart_strategy": "no-heuristic-restart",
        "reduce_strategy": "baseline",
        "extra_args": [
            "-restart-strategy=no-heuristic-restart",
            "-reduce-strategy=baseline",
            "-restart-trace"
        ]
    },
    {
        "id": "cfg03_v3dd_adaptfix",
        "name": "V3 Drawdown + Adaptive-Fixed Reduction",
        "restart_strategy": "adaptive-v3",
        "reduce_strategy": "adaptive-fixed",
        "extra_args": [
            "-restart-strategy=adaptive-v3",
            "-v3-trend=0",
            "-v3-drawdown=1",
            "-v3-ceiling=0",
            "-reduce-strategy=adaptive-fixed",
            "-restart-trace"
        ]
    },
    {
        "id": "cfg04_noheuristic_adaptfix",
        "name": "No-Heuristic + Adaptive-Fixed Reduction",
        "restart_strategy": "no-heuristic-restart",
        "reduce_strategy": "adaptive-fixed",
        "extra_args": [
            "-restart-strategy=no-heuristic-restart",
            "-reduce-strategy=adaptive-fixed",
            "-restart-trace"
        ]
    }
]

EXTRA_FIELDNAMES = [
    "repetition",
    "config_id",
    "config_name",
    "restart_policy",
    "reduction_policy",
    "family",
    "genuine_restarts",
    "trace_restart_events",
    "trace_reasons",
    "solver_binary_sha256"
]

FULL_FIELDNAMES = EXTRA_FIELDNAMES + [f for f in CSV_FIELDNAMES if f not in EXTRA_FIELDNAMES]

RE_TRACE_LINE = re.compile(r"^c\s+\[RESTART_TRACE\]\s+(.*)$", re.MULTILINE)

def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def load_existing_completed_runs(csv_path: Path) -> Set[Tuple[int, str, str]]:
    completed = set()
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rep = int(row["repetition"])
                    completed.add((rep, row["config_id"], row["benchmark_name"]))
                except (ValueError, KeyError):
                    continue
    return completed

def build_execution_schedule() -> List[Tuple[int, Dict[str, Any], Path, str]]:
    """
    Builds a balanced interleaved execution schedule across repetitions, benchmarks, and configs.
    Order: For each repetition, iterate through benchmarks with rotated config ordering.
    """
    num_configs = len(CONFIGURATIONS)
    schedule = []
    
    for rep in range(1, REPETITIONS + 1):
        for inst_idx, b_name in enumerate(DIAGNOSTIC_BENCHMARKS):
            cnf_path = EXPANDED_DIR / b_name
            if "php" in b_name:
                family = "PHP"
            elif "gcol" in b_name:
                family = "Graph Coloring"
            elif "planted" in b_name:
                family = "Planted Satisfiable"
            else:
                family = "Random 3-SAT"
                
            offset = (inst_idx + rep - 1) % num_configs
            for cfg_offset in range(num_configs):
                cfg_idx = (offset + cfg_offset) % num_configs
                cfg = CONFIGURATIONS[cfg_idx]
                schedule.append((rep, cfg, cnf_path, family))
                
    return schedule

def extract_trace_events(log_path: Path) -> Tuple[int, str]:
    if not log_path.exists():
        return 0, ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        matches = RE_TRACE_LINE.findall(text)
        reasons = []
        for m in matches:
            r_match = re.search(r"reason=([A-Za-z0-9_\+]+)", m)
            if r_match:
                reasons.append(r_match.group(1))
            else:
                reasons.append("UNKNOWN")
        return len(matches), ";".join(reasons)
    except Exception:
        return 0, ""

def main():
    print("=" * 80)
    print("STEP 33: V3 DRAWDOWN VS NO-HEURISTIC RESTART AUDIT")
    print("=" * 80)
    
    assert SOLVER_PATH.exists(), f"Solver binary not found: {SOLVER_PATH}"
    solver_sha256 = get_file_sha256(SOLVER_PATH)
    print(f"[*] Solver Binary   : {SOLVER_PATH}")
    print(f"[*] SHA-256 Hash    : {solver_sha256}")
    print(f"[*] Configurations  : {len(CONFIGURATIONS)}")
    print(f"[*] Benchmarks      : {len(DIAGNOSTIC_BENCHMARKS)}")
    print(f"[*] Repetitions     : {REPETITIONS}")
    print(f"[*] Planned Runs    : {len(CONFIGURATIONS) * len(DIAGNOSTIC_BENCHMARKS) * REPETITIONS}")
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
    
    master_file_exists = MASTER_CSV.exists()
    master_file = open(MASTER_CSV, "a" if master_file_exists else "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_file, fieldnames=FULL_FIELDNAMES)
    if not master_file_exists:
        master_writer.writeheader()
        master_file.flush()
        
    start_time = time.time()
    runs_executed = 0
    runs_skipped = 0
    
    for run_idx, (rep, cfg, cnf_path, family) in enumerate(schedule, 1):
        cfg_id = cfg["id"]
        b_name = cnf_path.name
        
        if (rep, cfg_id, b_name) in completed_runs:
            runs_skipped += 1
            continue
            
        cfg_log_dir = LOGS_DIR / cfg_id
        cfg_log_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[{run_idx}/{total_runs}] [Rep {rep}] Running {cfg_id} on {b_name} ... ", end="", flush=True)
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
        
        # Trace events
        log_file_p = Path(record.get("log_file", ""))
        trace_cnt, trace_reasons = extract_trace_events(log_file_p)
        
        record["repetition"] = rep
        record["config_id"] = cfg_id
        record["config_name"] = cfg["name"]
        record["restart_policy"] = cfg["restart_strategy"]
        record["reduction_policy"] = cfg["reduce_strategy"]
        record["family"] = family
        record["genuine_restarts"] = genuine_rsts
        record["trace_restart_events"] = trace_cnt
        record["trace_reasons"] = trace_reasons
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
            
        completed_runs.add((rep, cfg_id, b_name))
        runs_executed += 1
        
        status = record.get("status", "UNKNOWN")
        cfc = record.get("conflicts", "N/A")
        w_time = record.get("wall_time_s", elapsed)
        c_time = record.get("cpu_time_s", "N/A")
        v3_req_dd = record.get("v3_req_drawdown", "0")
        
        diag_str = f"R={genuine_rsts}, Trace={trace_cnt}"
        if trace_reasons:
            diag_str += f" ({trace_reasons})"
        diag_str += f", V3dd={v3_req_dd}"
            
        print(f"{status} in {w_time:.3f}s (CPU: {c_time}s, C={cfc}, {diag_str})")
        
    master_file.close()
    total_elapsed = time.time() - start_time
    print("=" * 80)
    print(f"[+] All runs completed in {total_elapsed:.1f}s.")
    print(f"[*] Executed: {runs_executed}, Skipped: {runs_skipped}, Total: {total_runs}")
    print(f"[*] Master dataset written to: {MASTER_CSV}")
    print("=" * 80)

if __name__ == "__main__":
    main()

