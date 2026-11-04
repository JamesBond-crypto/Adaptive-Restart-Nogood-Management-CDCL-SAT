#!/usr/bin/env python3
"""
run_timeout_memory_audit.py - Step 25: Targeted Repeated Timeout & Memory Measurement Audit

Executes 3 independent repetitions of all 8 Step 24 configurations across 8 diagnostic instances
(192 runs total) under a strictly controlled, deterministic balanced execution order (seed=20261031).
Captures:
- Status (SAT/UNSAT/TIMEOUT)
- Precise Wall time and CPU time
- Peak Working Set memory (Windows PeakWorkingSetSize in MB)
- Complete CDCL search and adaptive retention telemetry
- SAT model verification against source CNF

Results saved to experiments/results/timeout_memory_audit/
"""

import sys
import os
import csv
import json
import time
import random
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES

AUDIT_RESULTS_DIR = Path("experiments/results/timeout_memory_audit")
AUDIT_LOGS_DIR = AUDIT_RESULTS_DIR / "logs"
SOLVER_PATH = Path("src/glucose_windows/glucose-simp.exe")
MANIFEST_PATH = Path("benchmarks/expanded_manifest.csv")
TIMEOUT_S = 15.0
RANDOM_SEED = 20261031
NUM_REPETITIONS = 3

# Documented selection criteria for 8 diagnostic instances:
# 1. php_10p_9h.cnf               : Primary timeout divergence instance (solved under V2 Ceil / Comb, timed out under V1 Adapt & V2 Qual Adapt)
# 2. php_10p_8h.cnf               : Family control instance (moderately hard pigeonhole, mutually solved across all configs)
# 3. rand3sat_n250_c1065_s1010.cnf: Primary timeout divergence instance (solved under all baseline-reduction configs, timed out under all adaptive-reduction configs)
# 4. rand3sat_n235_c999_s1009.cnf : Random 3-SAT variance control (large conflict divergence between baseline, V1, and V2 Ceil)
# 5. rand3sat_n225_c958_s1008.cnf : Random 3-SAT sensitivity instance (large delta between V2 Ceil and V2 Comb)
# 6. gcol_unsat_k10_c9.cnf        : Graph Coloring hardest solved instance (high conflict reduction vs high runtime overhead; timed out in Step 18 baseline characterization)
# 7. planted3sat_n240_c1022_s2009.cnf : Planted 3-SAT starvation control (instance where V1 struggled with starvation)
# 8. planted3sat_n260_c1108_s2010.cnf : Planted 3-SAT scaling control (largest planted instance)
DIAGNOSTIC_INSTANCES = [
    "php_10p_9h.cnf",
    "php_10p_8h.cnf",
    "rand3sat_n250_c1065_s1010.cnf",
    "rand3sat_n235_c999_s1009.cnf",
    "rand3sat_n225_c958_s1008.cnf",
    "gcol_unsat_k10_c9.cnf",
    "planted3sat_n240_c1022_s2009.cnf",
    "planted3sat_n260_c1108_s2010.cnf"
]

CONFIGURATIONS = [
    {
        "id": "cfg1_base_base",
        "name": "Baseline Restart + Baseline Reduction",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=baseline"]
    },
    {
        "id": "cfg2_v1_base",
        "name": "Adaptive V1 Restart + Baseline Reduction",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=baseline"]
    },
    {
        "id": "cfg3_v1_adapt",
        "name": "Adaptive V1 Restart + Adaptive Reduction",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=adaptive"]
    },
    {
        "id": "cfg4_v2_ceil_base",
        "name": "V2 Ceiling Only + Baseline Reduction",
        "extra_args": [
            "-restart-strategy=adaptive-v2",
            "-v2-quality-fallback=0",
            "-v2-conflict-ceiling=1",
            "-v2-max-conflicts=2500",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg5_v2_ceil_adapt",
        "name": "V2 Ceiling Only + Adaptive Reduction",
        "extra_args": [
            "-restart-strategy=adaptive-v2",
            "-v2-quality-fallback=0",
            "-v2-conflict-ceiling=1",
            "-v2-max-conflicts=2500",
            "-reduce-strategy=adaptive"
        ]
    },
    {
        "id": "cfg6_v2_qual_base",
        "name": "V2 Quality Only + Baseline Reduction",
        "extra_args": [
            "-restart-strategy=adaptive-v2",
            "-v2-quality-fallback=1",
            "-v2-conflict-ceiling=0",
            "-reduce-strategy=baseline"
        ]
    },
    {
        "id": "cfg7_v2_qual_adapt",
        "name": "V2 Quality Only + Adaptive Reduction",
        "extra_args": [
            "-restart-strategy=adaptive-v2",
            "-v2-quality-fallback=1",
            "-v2-conflict-ceiling=0",
            "-reduce-strategy=adaptive"
        ]
    },
    {
        "id": "cfg8_v2_comb_adapt",
        "name": "V2 Combined + Adaptive Reduction",
        "extra_args": [
            "-restart-strategy=adaptive-v2",
            "-v2-quality-fallback=1",
            "-v2-conflict-ceiling=1",
            "-v2-max-conflicts=2500",
            "-reduce-strategy=adaptive"
        ]
    }
]


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manifest_path: Path) -> Dict[str, Dict[str, Any]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        return {r["filename"]: r for r in rows}


def main():
    if not SOLVER_PATH.is_file():
        raise FileNotFoundError(f"Solver binary not found: {SOLVER_PATH}")
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    AUDIT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_LOGS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_map = load_manifest(MANIFEST_PATH)
    for b in DIAGNOSTIC_INSTANCES:
        if b not in manifest_map:
            raise KeyError(f"Diagnostic benchmark {b} not found in manifest!")

    solver_hash = sha256_file(SOLVER_PATH)
    benchmark_hashes = {b: sha256_file(Path(manifest_map[b]["filepath"])) for b in DIAGNOSTIC_INSTANCES}

    total_runs = len(DIAGNOSTIC_INSTANCES) * len(CONFIGURATIONS) * NUM_REPETITIONS

    # Master audit CSV
    audit_fieldnames = ["rep", "run_order", "config_id", "config_name"] + CSV_FIELDNAMES
    master_csv_path = AUDIT_RESULTS_DIR / "audit_all_runs.csv"
    master_f = open(master_csv_path, "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_f, fieldnames=audit_fieldnames)
    master_writer.writeheader()
    master_f.flush()

    metadata = {
        "timestamp_start_utc": datetime.now(timezone.utc).isoformat(),
        "solver_path": str(SOLVER_PATH),
        "solver_sha256": solver_hash,
        "timeout_seconds": TIMEOUT_S,
        "random_seed": RANDOM_SEED,
        "num_repetitions": NUM_REPETITIONS,
        "diagnostic_instances_count": len(DIAGNOSTIC_INSTANCES),
        "configurations_count": len(CONFIGURATIONS),
        "total_planned_runs": total_runs,
        "diagnostic_instances": DIAGNOSTIC_INSTANCES,
        "benchmark_hashes": benchmark_hashes,
        "configurations": CONFIGURATIONS
    }
    with open(AUDIT_RESULTS_DIR / "audit_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("=" * 85)
    print("STEP 25: TARGETED REPEATED TIMEOUT & MEMORY MEASUREMENT AUDIT")
    print(f"Solver: {SOLVER_PATH} (SHA-256: {solver_hash[:16]}...)")
    print(f"Diagnostic Instances: {len(DIAGNOSTIC_INSTANCES)} | Configurations: {len(CONFIGURATIONS)} | Reps: {NUM_REPETITIONS}")
    print(f"Total Runs: {total_runs} | Timeout: {TIMEOUT_S}s | Seed: {RANDOM_SEED}")
    print("=" * 85)

    # Deterministic schedule generation using documented seed
    rng = random.Random(RANDOM_SEED)

    run_counter = 0
    t_start_global = time.time()

    try:
        for rep in range(1, NUM_REPETITIONS + 1):
            print(f"\n>>>>>>>>>>>>>>> STARTING REPETITION {rep}/{NUM_REPETITIONS} <<<<<<<<<<<<<<<")
            rep_log_dir = AUDIT_LOGS_DIR / f"rep{rep}"
            rep_log_dir.mkdir(parents=True, exist_ok=True)

            # Permute benchmark order deterministically per repetition
            shuffled_instances = list(DIAGNOSTIC_INSTANCES)
            rng.shuffle(shuffled_instances)

            for inst_idx, bname in enumerate(shuffled_instances):
                inst_record = manifest_map[bname]
                cnf_path = Path(inst_record["filepath"])
                known_status = inst_record["known_status"]
                family = inst_record.get("family", "Unknown")

                # Cyclic rotation of configurations based on instance index and rep
                cfg_shift = (inst_idx + rep) % len(CONFIGURATIONS)
                ordered_cfgs = CONFIGURATIONS[cfg_shift:] + CONFIGURATIONS[:cfg_shift]

                print(f"\n[Rep {rep} | Inst {inst_idx + 1:2d}/{len(DIAGNOSTIC_INSTANCES):2d}] {bname} ({family}, Known: {known_status})")

                for cfg in ordered_cfgs:
                    run_counter += 1
                    cfg_id = cfg["id"]
                    cfg_name = cfg["name"]
                    cfg_log_dir = rep_log_dir / cfg_id
                    cfg_log_dir.mkdir(parents=True, exist_ok=True)

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
                    cpu_time = record["cpu_time_s"]
                    mem_mb = record["memory_mb"]
                    st = record["status"]
                    cfc = record["conflicts"]
                    gen_rst = record["genuine_restarts"]
                    red = record["reduce_db_count"]
                    v_model = record["model_verified"]

                    # Write to master CSV
                    master_row = {
                        "rep": rep,
                        "run_order": run_counter,
                        "config_id": cfg_id,
                        "config_name": cfg_name
                    }
                    master_row.update(record)
                    master_writer.writerow(master_row)
                    master_f.flush()

                    # Correctness checks
                    if st == "SAT":
                        if known_status == "UNSAT":
                            raise RuntimeError(f"CRITICAL SOUNDNESS ERROR: {bname} is UNSAT but {cfg_name} reported SAT!")
                        if v_model != "VERIFIED":
                            raise RuntimeError(f"CRITICAL MODEL VERIFICATION ERROR: {bname} model failed verification under {cfg_name}!")
                    elif st == "UNSAT":
                        if known_status == "SAT":
                            raise RuntimeError(f"CRITICAL SOUNDNESS ERROR: {bname} is SAT but {cfg_name} reported UNSAT!")

                    # Status line output
                    stat_str = f"  <Rep{rep} #{run_counter:3d}/{total_runs:3d}> {cfg_id:18s} -> {st:7s} | Wall:{wall_time:6.3f}s"
                    if cpu_time != "":
                        stat_str += f" | CPU:{float(cpu_time):6.3f}s"
                    if mem_mb != "":
                        stat_str += f" | Mem:{float(mem_mb):5.2f}MB"
                    if cfc != "":
                        stat_str += f" | Cfc:{str(cfc):>7s} | Rst:{str(gen_rst):>3s} | Red:{str(red):>2s}"
                    if st == "SAT":
                        stat_str += f" (Model:{v_model})"
                    print(stat_str)

    finally:
        master_f.close()

    total_wall = time.time() - t_start_global
    print("\n" + "=" * 85)
    print(f"Step 25 Audit Runs Completed Successfully in {total_wall:.2f}s ({total_wall/60.0:.2f} min)!")
    print(f"Results saved to: {master_csv_path}")
    print(f"Logs saved to:    {AUDIT_LOGS_DIR}")
    print("=" * 85)

    metadata["timestamp_finish_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["total_wall_time_seconds"] = total_wall
    with open(AUDIT_RESULTS_DIR / "audit_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    main()

