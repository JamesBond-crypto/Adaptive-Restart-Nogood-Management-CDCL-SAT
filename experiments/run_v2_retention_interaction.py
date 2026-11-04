#!/usr/bin/env python3
"""
run_v2_retention_interaction.py - Adaptive Restart V2 x Adaptive Learned-Clause Retention Interaction Evaluation

Executes 8 solver configurations across all 36 expanded benchmark instances
(288 runs total) with 15.0s external timeout under a balanced cyclic rotation order:

  1. cfg1_base_base:     Baseline Restart + Baseline Reduction
  2. cfg2_v1_base:       Adaptive V1 Restart + Baseline Reduction
  3. cfg3_v1_adapt:      Adaptive V1 Restart + Adaptive Reduction
  4. cfg4_v2_ceil_base:  V2 Ceiling-Only + Baseline Reduction
  5. cfg5_v2_ceil_adapt: V2 Ceiling-Only + Adaptive Reduction
  6. cfg6_v2_qual_base:  V2 Quality-Only + Baseline Reduction
  7. cfg7_v2_qual_adapt: V2 Quality-Only + Adaptive Reduction
  8. cfg8_v2_comb_adapt: V2 Combined Safeguards + Adaptive Reduction

All raw logs and outputs are saved to experiments/results/v2_retention_interaction/
and experiments/results/v2_retention_interaction_logs/.
"""

import sys
import os
import csv
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES

RESULTS_DIR = Path("experiments/results/v2_retention_interaction")
LOGS_DIR = Path("experiments/results/v2_retention_interaction_logs")
MANIFEST_PATH = Path("benchmarks/expanded_manifest.csv")
SOLVER_PATH = Path("src/glucose_windows/glucose-simp.exe")
TIMEOUT_S = 15.0

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
        "id": "cfg3_v1_adapt",
        "name": "Adaptive V1 Restart + Adaptive Reduction",
        "restart_strategy": "adaptive",
        "reduce_strategy": "adaptive",
        "extra_args": [
            "-restart-strategy=adaptive",
            "-reduce-strategy=adaptive"
        ]
    },
    {
        "id": "cfg4_v2_ceil_base",
        "name": "V2 Ceiling Only + Baseline Reduction",
        "restart_strategy": "adaptive-v2",
        "reduce_strategy": "baseline",
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
        "restart_strategy": "adaptive-v2",
        "reduce_strategy": "adaptive",
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
        "restart_strategy": "adaptive-v2",
        "reduce_strategy": "baseline",
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
        "restart_strategy": "adaptive-v2",
        "reduce_strategy": "adaptive",
        "extra_args": [
            "-restart-strategy=adaptive-v2",
            "-v2-quality-fallback=1",
            "-v2-conflict-ceiling=0",
            "-reduce-strategy=adaptive"
        ]
    },
    {
        "id": "cfg8_v2_comb_adapt",
        "name": "V2 Combined Safeguards + Adaptive Reduction",
        "restart_strategy": "adaptive-v2",
        "reduce_strategy": "adaptive",
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


def load_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    if not SOLVER_PATH.is_file():
        raise FileNotFoundError(f"Solver binary not found: {SOLVER_PATH}")
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_records = load_manifest(MANIFEST_PATH)
    total_instances = len(manifest_records)
    total_configs = len(CONFIGURATIONS)
    total_runs = total_instances * total_configs

    # Record hashes
    solver_hash = sha256_file(SOLVER_PATH)
    benchmark_hashes = {}
    for inst in manifest_records:
        cnf_p = Path(inst["filepath"])
        benchmark_hashes[inst["filename"]] = sha256_file(cnf_p)

    metadata = {
        "timestamp_start_utc": datetime.now(timezone.utc).isoformat(),
        "solver_path": str(SOLVER_PATH),
        "solver_sha256": solver_hash,
        "timeout_seconds": TIMEOUT_S,
        "benchmark_count": total_instances,
        "configurations_count": total_configs,
        "total_planned_runs": total_runs,
        "benchmark_hashes": benchmark_hashes,
        "configurations": CONFIGURATIONS
    }

    with open(RESULTS_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Initialize individual CSV writers
    individual_handles = {}
    individual_writers = {}
    for cfg in CONFIGURATIONS:
        c_id = cfg["id"]
        csv_p = RESULTS_DIR / f"{c_id}.csv"
        cfg_log_dir = LOGS_DIR / c_id
        cfg_log_dir.mkdir(parents=True, exist_ok=True)
        f = open(csv_p, "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        f.flush()
        individual_handles[c_id] = f
        individual_writers[c_id] = w

    # Master CSV writer
    master_fieldnames = ["run_order", "config_id", "config_name"] + CSV_FIELDNAMES
    master_f = open(RESULTS_DIR / "master_interaction_results.csv", "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_f, fieldnames=master_fieldnames)
    master_writer.writeheader()
    master_f.flush()

    print("=" * 85)
    print("ADAPTIVE RESTART V2 x ADAPTIVE NOGOOD RETENTION: CONTROLLED INTERACTION EVALUATION")
    print(f"Solver: {SOLVER_PATH} (SHA-256: {solver_hash[:16]}...)")
    print(f"Benchmarks: {total_instances} expanded instances | Timeout: {TIMEOUT_S}s")
    print(f"Configurations: {total_configs} | Total runs: {total_runs}")
    print(f"Execution Order: Balanced Cyclic Permutation across configurations")
    print("=" * 85)

    run_counter = 0
    t_start_global = time.time()

    try:
        for idx, inst in enumerate(manifest_records):
            cnf_path = Path(inst["filepath"])
            bname = inst["filename"]
            known_status = inst["known_status"]
            family = inst.get("family", "Unknown")

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
                master_row = {"run_order": run_counter, "config_id": cfg_id, "config_name": cfg_name}
                master_row.update(record)
                master_writer.writerow(master_row)
                master_f.flush()

                # Strict correctness verification
                if st == "SAT":
                    if known_status == "UNSAT":
                        raise RuntimeError(f"CRITICAL SOUNDNESS ERROR: {bname} is mathematically UNSAT but {cfg_name} reported SAT!")
                    if v_model != "VERIFIED":
                        raise RuntimeError(f"CRITICAL MODEL VERIFICATION ERROR: {bname} model could not be verified under {cfg_name}! Status: {v_model}, Notes: {record.get('verification_notes')}")
                elif st == "UNSAT":
                    if known_status == "SAT":
                        raise RuntimeError(f"CRITICAL SOUNDNESS ERROR: {bname} is known SAT but {cfg_name} reported UNSAT!")

                # Status line printout
                stat_str = f"  <{run_counter:3d}/{total_runs:3d}> {cfg_id:18s} -> {st:7s} in {wall_time:6.3f}s"
                if cfc != "":
                    stat_str += f" | Cfc: {str(cfc):>7s} | Rst: {str(gen_rst):>3s} | Red: {str(red):>3s}"
                if st == "SAT":
                    stat_str += f" (Model: {v_model})"
                print(stat_str)

    finally:
        for f in individual_handles.values():
            f.close()
        master_f.close()

    total_wall = time.time() - t_start_global
    print("\n" + "=" * 85)
    print(f"Interaction experiment completed successfully in {total_wall:.2f}s ({total_wall/60.0:.2f} min)!")
    print(f"Results saved to: {RESULTS_DIR}")
    print(f"Logs saved to:    {LOGS_DIR}")
    print("=" * 85)

    metadata["timestamp_finish_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["total_wall_time_seconds"] = total_wall
    with open(RESULTS_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    main()

