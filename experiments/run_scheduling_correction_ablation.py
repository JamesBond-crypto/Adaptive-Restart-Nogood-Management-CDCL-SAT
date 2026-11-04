#!/usr/bin/env python3
"""
run_scheduling_correction_ablation.py - 6-Configuration Controlled Ablation
Evaluating Reduction Scheduling Correction on 36 Expanded SAT Benchmarks.

Configurations:
  1. Base_Base:       Baseline restart + baseline reduction
  2. V1_Base:         Adaptive V1 restart + baseline reduction
  3. Base_AdaptHist:  Baseline restart + historical adaptive reduction
  4. Base_AdaptFixed: Baseline restart + adaptive-fixed reduction
  5. V1_AdaptHist:    Adaptive V1 restart + historical adaptive reduction
  6. V1_AdaptFixed:   Adaptive V1 restart + adaptive-fixed reduction

Execution:
  - Cyclic Latin-square rotation per instance
  - Timeout: 15.0 seconds per run
  - Benchmark manifest: benchmarks/expanded_manifest.csv (36 instances)
  - Results stored in: experiments/results/scheduling_correction_ablation/
  - Raw logs stored in: experiments/results/scheduling_correction_ablation_logs/
"""

import sys
import os
import csv
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure experiments dir is in sys.path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES

BASE_OUT = Path("experiments/results/scheduling_correction_ablation")
BASE_LOGS = Path("experiments/results/scheduling_correction_ablation_logs")

CONFIGURATIONS = [
    {
        "id": "cfg1_base_base",
        "name": "Base_Base",
        "desc": "Baseline Restart + Baseline Reduction",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=baseline"],
        "csv_path": BASE_OUT / "cfg1_base_base.csv",
        "log_dir": BASE_LOGS / "cfg1_base_base"
    },
    {
        "id": "cfg2_v1_base",
        "name": "V1_Base",
        "desc": "Adaptive V1 Restart + Baseline Reduction",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=baseline"],
        "csv_path": BASE_OUT / "cfg2_v1_base.csv",
        "log_dir": BASE_LOGS / "cfg2_v1_base"
    },
    {
        "id": "cfg3_base_adapt",
        "name": "Base_AdaptHist",
        "desc": "Baseline Restart + Historical Adaptive Reduction",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=adaptive"],
        "csv_path": BASE_OUT / "cfg3_base_adapt.csv",
        "log_dir": BASE_LOGS / "cfg3_base_adapt"
    },
    {
        "id": "cfg4_base_adapt_fixed",
        "name": "Base_AdaptFixed",
        "desc": "Baseline Restart + Adaptive-Fixed Reduction",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=adaptive-fixed"],
        "csv_path": BASE_OUT / "cfg4_base_adapt_fixed.csv",
        "log_dir": BASE_LOGS / "cfg4_base_adapt_fixed"
    },
    {
        "id": "cfg5_v1_adapt",
        "name": "V1_AdaptHist",
        "desc": "Adaptive V1 Restart + Historical Adaptive Reduction",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=adaptive"],
        "csv_path": BASE_OUT / "cfg5_v1_adapt.csv",
        "log_dir": BASE_LOGS / "cfg5_v1_adapt"
    },
    {
        "id": "cfg6_v1_adapt_fixed",
        "name": "V1_AdaptFixed",
        "desc": "Adaptive V1 Restart + Adaptive-Fixed Reduction",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=adaptive-fixed"],
        "csv_path": BASE_OUT / "cfg6_v1_adapt_fixed.csv",
        "log_dir": BASE_LOGS / "cfg6_v1_adapt_fixed"
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

    # Ensure output directories exist
    BASE_OUT.mkdir(parents=True, exist_ok=True)
    for cfg in CONFIGURATIONS:
        cfg["log_dir"].mkdir(parents=True, exist_ok=True)

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

    total_runs = total_instances * len(CONFIGURATIONS)
    print("=" * 80)
    print("SCHEDULING CORRECTION 6-CONFIGURATION CONTROLLED ABLATION")
    print(f"Solver: {solver_exe}")
    print(f"Timeout: {timeout_s}s per run | Total instances: {total_instances} | Total runs: {total_runs}")
    print("=" * 80)

    run_counter = 0
    t_start_global = time.time()

    try:
        for idx, inst in enumerate(manifest_records):
            cnf_path = Path(inst["filepath"])
            bname = inst["filename"]
            known_status = inst["known_status"]

            # Cyclic rotation
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

                results_by_cfg[cfg_id].append(record)
                csv_writers[cfg_id].writerow(record)
                csv_handles[cfg_id].flush()

                st = record["status"]
                wt = record["wall_time_s"]
                cfc = record["conflicts"]
                gen_rst = record["genuine_restarts"]
                red = record["reduce_db_count"]
                v_model = record["model_verified"]
                post_eval = record.get("adapt_postpone_evals", "")
                post_sat = record.get("adapt_postpone_sat", "")

                # Correctness validation
                if st == "SAT":
                    if known_status == "UNSAT":
                        raise RuntimeError(f"CRITICAL ERROR: {bname} is UNSAT but {cfg_name} reported SAT!")
                    if not v_model:
                        raise RuntimeError(f"CRITICAL ERROR: Model verification failed for {bname} under {cfg_name}!")
                elif st == "UNSAT":
                    if known_status == "SAT":
                        raise RuntimeError(f"CRITICAL ERROR: {bname} is SAT but {cfg_name} reported UNSAT!")

                info_str = f"  [{run_counter:3d}/{total_runs}] {cfg_name:16s}: {st:7s} in {wt:6.3f}s"
                if st == "SAT":
                    info_str += f" (Model: {v_model})"
                if cfc != "":
                    info_str += f" | Cfc: {str(cfc):>7s} | Rst: {str(gen_rst):>3s} | Red: {str(red):>3s}"
                if post_eval != "":
                    info_str += f" | Postpone: {str(post_sat)}/{str(post_eval)}"
                print(info_str)

    finally:
        for f in csv_handles.values():
            f.close()

    total_wall = time.time() - t_start_global
    print("\n" + "=" * 80)
    print(f"[+] All {total_runs} benchmark runs successfully completed in {total_wall:.2f}s!")
    for cfg in CONFIGURATIONS:
        print(f"  - {cfg['name']:16s}: Saved to {cfg['csv_path']}")
    print("=" * 80)


if __name__ == "__main__":
    main()

