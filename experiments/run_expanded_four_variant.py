#!/usr/bin/env python3
"""
run_expanded_four_variant.py - Four-Variant Evaluation on Expanded SAT Benchmarks

Executes all four solver configurations on the 36 expanded benchmark instances
using a balanced, cyclic execution order (Latin-square rotation) to eliminate
systematic timing and caching biases:

  Cfg 1: Baseline Restart + Baseline Reduction (-restart-strategy=baseline -reduce-strategy=baseline)
  Cfg 2: Adaptive Restart + Baseline Reduction (-restart-strategy=adaptive -reduce-strategy=baseline)
  Cfg 3: Baseline Restart + Adaptive Reduction (-restart-strategy=baseline -reduce-strategy=adaptive)
  Cfg 4: Combined Adaptive                     (-restart-strategy=adaptive -reduce-strategy=adaptive)

Timeout: 15.0 seconds per run.
Outputs:
  - experiments/results/expanded_cfg1_base_base.csv
  - experiments/results/expanded_cfg2_adapt_base.csv
  - experiments/results/expanded_cfg3_base_adapt.csv
  - experiments/results/expanded_cfg4_adapt_adapt.csv
  - Raw logs stored in separate directories per configuration.
"""

import sys
import os
import csv
import time
from pathlib import Path
from typing import Dict, List, Any

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES


CONFIGURATIONS = [
    {
        "id": "cfg1",
        "name": "Baseline",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=baseline"],
        "csv_path": Path("experiments/results/expanded_cfg1_base_base.csv"),
        "log_dir": Path("experiments/results/expanded_cfg1_base_base_logs")
    },
    {
        "id": "cfg2",
        "name": "Adaptive Restart Only",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=baseline"],
        "csv_path": Path("experiments/results/expanded_cfg2_adapt_base.csv"),
        "log_dir": Path("experiments/results/expanded_cfg2_adapt_base_logs")
    },
    {
        "id": "cfg3",
        "name": "Adaptive Retention Only",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=adaptive"],
        "csv_path": Path("experiments/results/expanded_cfg3_base_adapt.csv"),
        "log_dir": Path("experiments/results/expanded_cfg3_base_adapt_logs")
    },
    {
        "id": "cfg4",
        "name": "Combined Adaptive",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=adaptive"],
        "csv_path": Path("experiments/results/expanded_cfg4_adapt_adapt.csv"),
        "log_dir": Path("experiments/results/expanded_cfg4_adapt_adapt_logs")
    }
]


def load_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    solver_exe = Path("src/glucose_windows/glucose-simp.exe")
    manifest_path = Path("benchmarks/expanded_manifest.csv")
    timeout_s = 15.0

    if not solver_exe.is_file():
        raise FileNotFoundError(f"Solver executable not found: {solver_exe}")

    manifest_records = load_manifest(manifest_path)
    total_instances = len(manifest_records)
    print(f"[*] Loaded {total_instances} benchmark instances from {manifest_path}")

    # Ensure log and result directories exist
    for cfg in CONFIGURATIONS:
        cfg["csv_path"].parent.mkdir(parents=True, exist_ok=True)
        cfg["log_dir"].mkdir(parents=True, exist_ok=True)

    # Initialize CSV writers
    csv_handles = {}
    csv_writers = {}
    results_by_cfg = {cfg["id"]: [] for cfg in CONFIGURATIONS}

    for cfg in CONFIGURATIONS:
        f = open(cfg["csv_path"], "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        f.flush()
        csv_handles[cfg["id"]] = f
        csv_writers[cfg["id"]] = w

    print("=" * 80)
    print("FOUR-VARIANT EXPANDED BENCHMARK EVALUATION (CYCLIC ROTATION ORDER)")
    print(f"Solver: {solver_exe}")
    print(f"Timeout: {timeout_s}s per run | Total runs: {total_instances * 4}")
    print("=" * 80)

    total_runs = total_instances * len(CONFIGURATIONS)
    run_counter = 0
    t_start_global = time.time()

    try:
        for idx, inst in enumerate(manifest_records):
            cnf_path = Path(inst["filepath"])
            bname = inst["filename"]
            known_status = inst["known_status"]

            # Cyclic permutation to balance execution order:
            # idx=0 -> [cfg1, cfg2, cfg3, cfg4]
            # idx=1 -> [cfg2, cfg3, cfg4, cfg1]
            # idx=2 -> [cfg3, cfg4, cfg1, cfg2]
            # idx=3 -> [cfg4, cfg1, cfg2, cfg3]
            shift = idx % len(CONFIGURATIONS)
            ordered_cfgs = CONFIGURATIONS[shift:] + CONFIGURATIONS[:shift]

            print(f"\n--- Instance [{idx + 1}/{total_instances}]: {bname} (Known: {known_status}) ---")

            for cfg in ordered_cfgs:
                run_counter += 1
                cfg_id = cfg["id"]
                cfg_name = cfg["name"]

                record = run_single_instance(
                    solver_exe=solver_exe,
                    cnf_file=cnf_path,
                    timeout_s=timeout_s,
                    log_dir=cfg["log_dir"],
                    emit_model=True,
                    verify_models=True,
                    extra_solver_args=cfg["extra_args"]
                )

                # Append and flush
                results_by_cfg[cfg_id].append(record)
                csv_writers[cfg_id].writerow(record)
                csv_handles[cfg_id].flush()

                st = record["status"]
                wt = record["wall_time_s"]
                cfc = record["conflicts"]
                gen_rst = record["genuine_restarts"]
                red = record["reduce_db_count"]
                v_model = record["model_verified"]

                # Quick correctness validation check
                if st == "SAT":
                    if known_status == "UNSAT":
                        raise RuntimeError(f"CRITICAL ERROR: Instance {bname} is mathematically UNSAT but {cfg_name} reported SAT!")
                    if not v_model:
                        raise RuntimeError(f"CRITICAL ERROR: SAT model verification failed for {bname} under {cfg_name}!")
                elif st == "UNSAT":
                    if known_status == "SAT":
                        raise RuntimeError(f"CRITICAL ERROR: Instance {bname} is known SAT but {cfg_name} reported UNSAT!")

                info_str = f"  [{run_counter:3d}/{total_runs}] {cfg_id.upper()} ({cfg_name:24s}): {st:7s} in {wt:6.3f}s"
                if st == "SAT":
                    info_str += f" (Model: {v_model})"
                if cfc != "":
                    info_str += f" | Cfc: {str(cfc):>7s} | Rst: {str(gen_rst):>3s} | Red: {str(red):>3s}"
                print(info_str)

    finally:
        for f in csv_handles.values():
            f.close()

    total_wall = time.time() - t_start_global
    print("\n" + "=" * 80)
    print(f"[+] All {total_runs} benchmark runs successfully completed in {total_wall:.2f}s!")
    for cfg in CONFIGURATIONS:
        print(f"  - {cfg['id'].upper()} ({cfg['name']}): Saved to {cfg['csv_path']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
