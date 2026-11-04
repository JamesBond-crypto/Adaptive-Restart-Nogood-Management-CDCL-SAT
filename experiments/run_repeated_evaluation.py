#!/usr/bin/env python3
"""
run_repeated_evaluation.py - 3-Repetition Four-Variant Evaluation on Expanded SAT Benchmarks

Executes 3 independent repetitions of all 36 expanded instances across all 4 configurations
(3 * 36 * 4 = 432 solver executions), strictly sequential, with documented random seeds.

Timeout: 15.0 seconds per execution.
Configurations:
  - cfg1: Baseline (-restart-strategy=baseline -reduce-strategy=baseline)
  - cfg2: Adaptive Restart Only (-restart-strategy=adaptive -reduce-strategy=baseline)
  - cfg3: Adaptive Retention Only (-restart-strategy=baseline -reduce-strategy=adaptive)
  - cfg4: Combined Adaptive (-restart-strategy=adaptive -reduce-strategy=adaptive)

Results saved to:
  - experiments/results/expanded_repeated/repeated_all_runs.csv
  - experiments/results/expanded_repeated/expanded_rep_cfg1_base_base.csv
  - experiments/results/expanded_repeated/expanded_rep_cfg2_adapt_base.csv
  - experiments/results/expanded_repeated/expanded_rep_cfg3_base_adapt.csv
  - experiments/results/expanded_repeated/expanded_rep_cfg4_adapt_adapt.csv
  - Raw logs saved to experiments/results/expanded_repeated/logs/
"""

import sys
import os
import csv
import time
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Any

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent))
from run_experiments import run_single_instance, CSV_FIELDNAMES
from verify_model import verify_model


SOLVER_EXE = Path("src/glucose_windows/glucose-simp.exe")
MANIFEST_PATH = Path("benchmarks/expanded_manifest.csv")
TIMEOUT_LIMIT = 15.0
NUM_REPETITIONS = 3
BASE_SEED = 20261030

CONFIGURATIONS = [
    {
        "id": "cfg1",
        "name": "Baseline",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=baseline"]
    },
    {
        "id": "cfg2",
        "name": "Adaptive Restart Only",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=baseline"]
    },
    {
        "id": "cfg3",
        "name": "Adaptive Retention Only",
        "extra_args": ["-restart-strategy=baseline", "-reduce-strategy=adaptive"]
    },
    {
        "id": "cfg4",
        "name": "Combined Adaptive",
        "extra_args": ["-restart-strategy=adaptive", "-reduce-strategy=adaptive"]
    }
]

REPEATED_DIR = Path("experiments/results/expanded_repeated")
LOGS_DIR = REPEATED_DIR / "logs"
MASTER_CSV_PATH = REPEATED_DIR / "repeated_all_runs.csv"

PER_CFG_CSVS = {
    "cfg1": REPEATED_DIR / "expanded_rep_cfg1_base_base.csv",
    "cfg2": REPEATED_DIR / "expanded_rep_cfg2_adapt_base.csv",
    "cfg3": REPEATED_DIR / "expanded_rep_cfg3_base_adapt.csv",
    "cfg4": REPEATED_DIR / "expanded_rep_cfg4_adapt_adapt.csv",
}

EXTENDED_FIELDNAMES = [
    "repetition",
    "global_run_seq",
    "rep_seq",
    "config_id",
    "config_name",
    "solver_sha256",
    "benchmark_family",
    "known_status"
] + CSV_FIELDNAMES


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_family(bname: str) -> str:
    if bname.startswith("rand3sat"):
        return "Random 3-SAT"
    elif bname.startswith("planted3sat"):
        return "Planted 3-SAT"
    elif bname.startswith("php"):
        return "Pigeonhole Principle"
    elif bname.startswith("gcol"):
        return "Graph Coloring"
    return "Other"


def main():
    if not SOLVER_EXE.is_file():
        raise FileNotFoundError(f"Solver executable not found: {SOLVER_EXE}")

    solver_hash = compute_sha256(SOLVER_EXE)
    print(f"[*] Solver Executable: {SOLVER_EXE}")
    print(f"[*] Solver SHA-256:    {solver_hash}")

    manifest_records = load_manifest(MANIFEST_PATH)
    total_benchmarks = len(manifest_records)
    print(f"[*] Loaded {total_benchmarks} benchmark instances from {MANIFEST_PATH}")

    # Verify benchmark hashes before beginning
    print("[*] Verifying integrity of benchmark instances...")
    for inst in manifest_records:
        p = Path(inst["filepath"])
        h = compute_sha256(p)
        if h != inst["sha256"]:
            raise ValueError(f"Hash mismatch for {inst['filename']}: expected {inst['sha256']}, got {h}")
    print("[+] All 36 benchmark SHA-256 hashes successfully verified.")

    # Create directories
    REPEATED_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    for rep in range(1, NUM_REPETITIONS + 1):
        (LOGS_DIR / f"rep{rep}").mkdir(parents=True, exist_ok=True)

    # Initialize CSV writers
    master_file = open(MASTER_CSV_PATH, "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_file, fieldnames=EXTENDED_FIELDNAMES)
    master_writer.writeheader()
    master_file.flush()

    per_cfg_files = {}
    per_cfg_writers = {}
    for cfg in CONFIGURATIONS:
        cid = cfg["id"]
        f = open(PER_CFG_CSVS[cid], "w", newline="", encoding="utf-8")
        w = csv.DictWriter(f, fieldnames=EXTENDED_FIELDNAMES)
        w.writeheader()
        f.flush()
        per_cfg_files[cid] = f
        per_cfg_writers[cid] = w

    total_runs = total_benchmarks * len(CONFIGURATIONS) * NUM_REPETITIONS
    global_seq = 0
    t_start_all = time.time()

    print("=" * 80)
    print("STARTING 3-REPETITION FOUR-VARIANT EVALUATION (432 RUNS)")
    print(f"Timeout: {TIMEOUT_LIMIT}s per run | Total planned runs: {total_runs}")
    print("=" * 80)

    try:
        for rep in range(1, NUM_REPETITIONS + 1):
            rep_seed = BASE_SEED + rep
            rng = random.Random(rep_seed)
            rep_logs_dir = LOGS_DIR / f"rep{rep}"

            # Construct balanced plan for this repetition:
            # Generate all pairs of (instance, cfg)
            # Shuffle in a randomized block order using deterministic seed
            plan = []
            for inst in manifest_records:
                cfgs_shuffled = list(CONFIGURATIONS)
                rng.shuffle(cfgs_shuffled)
                for cfg in cfgs_shuffled:
                    plan.append((inst, cfg))

            # Shuffle the order of blocks with the fixed seed
            # Group by 4 (each instance block) and shuffle block order
            blocks = [plan[i:i+4] for i in range(0, len(plan), 4)]
            rng.shuffle(blocks)
            flattened_plan = [item for blk in blocks for item in blk]

            print(f"\n>>> REPETITION {rep}/{NUM_REPETITIONS} (Seed: {rep_seed}, Planned runs: {len(flattened_plan)}) <<<")

            rep_seq = 0
            for inst, cfg in flattened_plan:
                global_seq += 1
                rep_seq += 1

                cnf_path = Path(inst["filepath"])
                bname = inst["filename"]
                fam = get_family(bname)
                known_status = inst["known_status"]
                cid = cfg["id"]
                cname = cfg["name"]

                # Run solver
                record = run_single_instance(
                    solver_exe=SOLVER_EXE,
                    cnf_file=cnf_path,
                    timeout_s=TIMEOUT_LIMIT,
                    log_dir=rep_logs_dir,
                    emit_model=True,
                    verify_models=True,
                    extra_solver_args=cfg["extra_args"]
                )

                st = record["status"]
                wt = record["wall_time_s"]
                cfc = record["conflicts"]
                gen_rst = record["genuine_restarts"]
                v_model = record["model_verified"]

                # Correctness assertions
                if st == "SAT":
                    if known_status == "UNSAT":
                        raise RuntimeError(f"CRITICAL ERROR [Rep {rep}]: {bname} is mathematically UNSAT but {cname} reported SAT!")
                    if v_model not in ("VERIFIED", "True", True):
                        raise RuntimeError(f"CRITICAL ERROR [Rep {rep}]: Model verification failed for {bname} under {cname} ({v_model})!")
                elif st == "UNSAT":
                    if known_status == "SAT":
                        raise RuntimeError(f"CRITICAL ERROR [Rep {rep}]: {bname} is known SAT but {cname} reported UNSAT!")

                # Construct full extended record
                ext_record = {
                    "repetition": f"rep{rep}",
                    "global_run_seq": global_seq,
                    "rep_seq": rep_seq,
                    "config_id": cid,
                    "config_name": cname,
                    "solver_sha256": solver_hash,
                    "benchmark_family": fam,
                    "known_status": known_status
                }
                ext_record.update(record)

                # Write to master and per-cfg CSVs
                master_writer.writerow(ext_record)
                master_file.flush()

                per_cfg_writers[cid].writerow(ext_record)
                per_cfg_files[cid].flush()

                # Print progress
                info_line = f"  [{global_seq:3d}/{total_runs}] R{rep} | {cid.upper():4s} | {bname:<32s}: {st:<7s} in {wt:6.3f}s"
                if st == "SAT":
                    info_line += f" (Model: {v_model})"
                if cfc != "":
                    info_line += f" | Cfc: {str(cfc):>7s} | Rst: {str(gen_rst):>3s}"
                print(info_line)

    finally:
        master_file.close()
        for f in per_cfg_files.values():
            f.close()

    total_wall = time.time() - t_start_all
    print("\n" + "=" * 80)
    print(f"[+] All {global_seq} runs completed successfully in {total_wall:.2f}s ({total_wall/60:.2f} min)!")
    print(f"[+] Master CSV saved: {MASTER_CSV_PATH}")
    for cid, path in PER_CFG_CSVS.items():
        print(f"  - {cid.upper()}: {path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

