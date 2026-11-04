#!/usr/bin/env python3
"""
run_v2_exploration.py - Exploratory evaluation of Adaptive Restart V2 configurations
on the 36 expanded benchmarks suite (15.0s timeout).
"""

import os
import sys
import subprocess
import time

EXPANDED_DIR = "benchmarks/expanded"
RESULTS_DIR = "experiments/results/v2_exploration"
LOGS_DIR = "experiments/results/v2_exploration_logs"
TIMEOUT = 15.0
SOLVER = "src/glucose_windows/glucose-simp.exe"

V2_CONFIGS = {
    "v2_ceiling_only": [
        "-restart-strategy=adaptive-v2",
        "-v2-quality-fallback=0",
        "-v2-conflict-ceiling=1",
        "-reduce-strategy=baseline"
    ],
    "v2_quality_only": [
        "-restart-strategy=adaptive-v2",
        "-v2-quality-fallback=1",
        "-v2-conflict-ceiling=0",
        "-reduce-strategy=baseline"
    ],
    "v2_combined": [
        "-restart-strategy=adaptive-v2",
        "-v2-quality-fallback=1",
        "-v2-conflict-ceiling=1",
        "-reduce-strategy=baseline"
    ]
}

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

    print("=================================================================")
    print("Starting Adaptive Restart V2 Exploratory Evaluation (36 Instances)")
    print(f"Timeout: {TIMEOUT}s per instance")
    print("=================================================================")

    for cname, args in V2_CONFIGS.items():
        out_csv = os.path.join(RESULTS_DIR, f"expanded_{cname}.csv")
        log_dir = os.path.join(LOGS_DIR, cname)
        os.makedirs(log_dir, exist_ok=True)

        cmd = [
            sys.executable, "experiments/run_experiments.py",
            "--solver", SOLVER,
            "--benchmarks", EXPANDED_DIR,
            "--timeout", str(TIMEOUT),
            "--output-csv", out_csv,
            "--log-dir", log_dir,
            "--extra-args"
        ] + args

        print(f"\n---> Running configuration: {cname}")
        print(f"     Flags: {' '.join(args)}")
        print(f"     Output CSV: {out_csv}")
        
        t0 = time.time()
        res = subprocess.run(cmd)
        elapsed = time.time() - t0
        
        if res.returncode != 0:
            print(f"ERROR: Execution failed for {cname} (code {res.returncode})")
            sys.exit(1)
        else:
            print(f"Finished {cname} in {elapsed:.2f} seconds.")

    print("\n=================================================================")
    print("All V2 exploration configurations completed successfully!")
    print("=================================================================")

if __name__ == "__main__":
    main()

