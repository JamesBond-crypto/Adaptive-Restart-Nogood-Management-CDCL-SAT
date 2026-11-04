#!/usr/bin/env python3
"""
run_final_holdout_evaluation.py - Step 36 Final Frozen Holdout Evaluation Runner

Executes the pre-registered 4x2 factorial evaluation campaign on the 48-instance
unseen holdout benchmark suite under strict quarantine protocol:
  - 8 configurations (frozen_configurations.json)
  - 48 holdout benchmarks (benchmarks/final_holdout/)
  - 3 repetitions
  - 1,152 planned sequential executions
  - 30.0s external wall-clock timeout
  - Independent model verification for every SAT result
  - Authoritative label cross-checking for every UNSAT result
  - Comprehensive telemetry extraction and atomic checkpointing
"""

import sys
import os
import re
import csv
import time
import json
import hashlib
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

# Ensure experiments dir is in Python path for verify_model
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "experiments"))

from verify_model import verify_model, ModelParseError, CNFParseError

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


# Telemetry Regex Patterns for Glucose 4.2.1
RE_SAT = re.compile(r"^s\s+SATISFIABLE", re.MULTILINE)
RE_UNSAT = re.compile(r"^s\s+UNSATISFIABLE", re.MULTILINE)
RE_INDET = re.compile(r"^s\s+INDETERMINATE", re.MULTILINE)
RE_MODEL_LINES = re.compile(r"^v\s+(.*)$", re.MULTILINE)

RE_CPU_TIME = re.compile(r"^c\s+CPU time\s*:\s*([\d\.]+)\s*s", re.MULTILINE)
RE_MEM_USED = re.compile(r"^c\s+Memory used\s*:\s*([\d\.]+)\s*MB", re.MULTILINE)
RE_CONFLICTS = re.compile(r"^c\s+conflicts\s*:\s*(\d+)", re.MULTILINE)
RE_DECISIONS = re.compile(r"^c\s+decisions\s*:\s*(\d+)", re.MULTILINE)
RE_PROPAGATIONS = re.compile(r"^c\s+propagations\s*:\s*(\d+)", re.MULTILINE)
RE_RESTARTS = re.compile(r"^c\s+restarts\s*:\s*(\d+)", re.MULTILINE)
RE_GENUINE_RESTARTS = re.compile(r"^c\s+genuine restarts\s*:\s*(\d+)", re.MULTILINE)
RE_BLOCKED_RESTARTS = re.compile(r"^c\s+blocked restarts\s*:\s*(\d+)", re.MULTILINE)
RE_RESTART_STRAT = re.compile(r"^c\s+restart strategy\s*:\s*([^\r\n]+)", re.MULTILINE)
RE_REDUCE_STRAT = re.compile(r"^c\s+reduction strategy\s*:\s*([^\r\n]+)", re.MULTILINE)

# Adaptive Restart V1 Telemetry
RE_ADAPT_REQUESTS = re.compile(r"^c\s+adaptive restart requests\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_RESTARTS = re.compile(r"^c\s+adaptive restarts\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_SCORES = re.compile(r"^c\s+last adaptive score\s*:\s*([\d\.\-]+)\s*\(global:\s*([\d\.\-]+)\)", re.MULTILINE)

# Adaptive Restart V3 Active Telemetry
RE_V3_REQ_TREND = re.compile(r"^c\s+v3 req trend\s*:\s*(\d+)", re.MULTILINE)
RE_V3_REQ_DRAWDOWN = re.compile(r"^c\s+v3 req drawdown\s*:\s*(\d+)", re.MULTILINE)
RE_V3_REQ_CEILING = re.compile(r"^c\s+v3 req ceiling\s*:\s*(\d+)", re.MULTILINE)
RE_V3_TOTAL_REQUESTS = re.compile(r"^c\s+v3 total requests\s*:\s*(\d+)", re.MULTILINE)
RE_V3_EXECUTED_RESTARTS = re.compile(r"^c\s+v3 executed restarts\s*:\s*(\d+)", re.MULTILINE)
RE_V3_BLOCKED_RESTARTS = re.compile(r"^c\s+v3 blocked restarts\s*:\s*(\d+)", re.MULTILINE)
RE_V3_MAX_INTERVAL = re.compile(r"^c\s+v3 max interval\s*:\s*(\d+)", re.MULTILINE)
RE_V3_VALID_RETURN_OBS = re.compile(r"^c\s+v3 valid return obs\s*:\s*(\d+)", re.MULTILINE)
RE_V3_ACTIVE_MEAN_RETURN = re.compile(r"^c\s+v3 mean return\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_ACTIVE_FINAL_FAST = re.compile(r"^c\s+v3 final fast ewma\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_ACTIVE_FINAL_SLOW = re.compile(r"^c\s+v3 final slow ewma\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_ACTIVE_MAX_DD = re.compile(r"^c\s+v3 max observed dd\s*:\s*([\d\.\-]+)", re.MULTILINE)

# Reduction / Nogood Telemetry
RE_REDUCED_DB = re.compile(r"^c\s+nb ReduceDB\s*:\s*(\d+)", re.MULTILINE)
RE_REMOVED_CLAUSES = re.compile(r"^c\s+nb removed Clauses\s*:\s*(\d+)", re.MULTILINE)
RE_LEARNTS_DL2 = re.compile(r"^c\s+nb learnts DL2\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_REDUCE_CALLS = re.compile(r"^c\s+adaptive reduceDB calls\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_CLAUSES_RANKED = re.compile(r"^c\s+adaptive clauses ranked\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_CLAUSES_ELIG = re.compile(r"^c\s+adaptive clauses eligible\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_CLAUSES_REM = re.compile(r"^c\s+adaptive clauses removed\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_POSTPONE_EVALS = re.compile(r"^c\s+adaptive postpone evals\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_POSTPONE_SAT = re.compile(r"^c\s+adaptive postpone satisfied\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_POSTPONE_INC = re.compile(r"^c\s+adaptive postpone inc db\s*:\s*(\d+)", re.MULTILINE)


CSV_FIELDNAMES = [
    "run_id",
    "execution_order",
    "repetition",
    "config_id",
    "config_name",
    "restart_strategy",
    "reduce_strategy",
    "command_flags",
    "benchmark_id",
    "benchmark_name",
    "category",
    "family",
    "authoritative_label",
    "cnf_sha256",
    "solver_sha256",
    "solver_commit",
    "status",
    "verification_status",
    "exit_code",
    "wall_time_s",
    "process_cpu_time_s",
    "process_peak_rss_mb",
    "solver_cpu_time_s",
    "solver_memory_mb",
    "conflicts",
    "decisions",
    "propagations",
    "restarts",
    "genuine_restarts",
    "blocked_restarts",
    "v1_adaptive_requests",
    "v1_adaptive_restarts",
    "v1_last_score_w",
    "v1_last_score_global",
    "v3_req_trend",
    "v3_req_drawdown",
    "v3_req_ceiling",
    "v3_total_requests",
    "v3_executed_restarts",
    "v3_blocked_restarts",
    "v3_max_interval",
    "v3_valid_return_obs",
    "v3_active_mean_return",
    "v3_active_final_fast",
    "v3_active_final_slow",
    "v3_active_max_dd",
    "reduce_db_count",
    "removed_clauses",
    "glue_clauses_dl2",
    "adapt_reduce_calls",
    "adapt_clauses_ranked",
    "adapt_clauses_eligible",
    "adapt_clauses_removed",
    "adapt_postpone_evals",
    "adapt_postpone_sat",
    "adapt_postpone_inc_db",
    "log_file",
    "timestamp_utc"
]


def sha256_file(path: Path) -> str:
    """Computes SHA-256 of file in 64KB blocks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def extract_telemetry(stdout_text: str) -> Dict[str, Any]:
    """Parses standard Glucose output and returns extracted metrics dict."""
    telemetry: Dict[str, Any] = {}

    def search_pat(pattern: re.Pattern, conv=str, default=""):
        m = pattern.search(stdout_text)
        if m:
            try:
                return conv(m.group(1))
            except (ValueError, TypeError):
                return default
        return default

    telemetry["solver_cpu_time_s"] = search_pat(RE_CPU_TIME, float)
    telemetry["solver_memory_mb"] = search_pat(RE_MEM_USED, float)
    telemetry["conflicts"] = search_pat(RE_CONFLICTS, int)
    telemetry["decisions"] = search_pat(RE_DECISIONS, int)
    telemetry["propagations"] = search_pat(RE_PROPAGATIONS, int)
    telemetry["restarts"] = search_pat(RE_RESTARTS, int)
    telemetry["genuine_restarts"] = search_pat(RE_GENUINE_RESTARTS, int)
    telemetry["blocked_restarts"] = search_pat(RE_BLOCKED_RESTARTS, int)

    # V1 Telemetry
    telemetry["v1_adaptive_requests"] = search_pat(RE_ADAPT_REQUESTS, int)
    telemetry["v1_adaptive_restarts"] = search_pat(RE_ADAPT_RESTARTS, int)
    m_scores = RE_ADAPT_SCORES.search(stdout_text)
    if m_scores:
        try:
            telemetry["v1_last_score_w"] = float(m_scores.group(1))
            telemetry["v1_last_score_global"] = float(m_scores.group(2))
        except (ValueError, TypeError):
            telemetry["v1_last_score_w"] = ""
            telemetry["v1_last_score_global"] = ""
    else:
        telemetry["v1_last_score_w"] = ""
        telemetry["v1_last_score_global"] = ""

    # V3 Active Telemetry
    telemetry["v3_req_trend"] = search_pat(RE_V3_REQ_TREND, int)
    telemetry["v3_req_drawdown"] = search_pat(RE_V3_REQ_DRAWDOWN, int)
    telemetry["v3_req_ceiling"] = search_pat(RE_V3_REQ_CEILING, int)
    telemetry["v3_total_requests"] = search_pat(RE_V3_TOTAL_REQUESTS, int)
    telemetry["v3_executed_restarts"] = search_pat(RE_V3_EXECUTED_RESTARTS, int)
    telemetry["v3_blocked_restarts"] = search_pat(RE_V3_BLOCKED_RESTARTS, int)
    telemetry["v3_max_interval"] = search_pat(RE_V3_MAX_INTERVAL, int)
    telemetry["v3_valid_return_obs"] = search_pat(RE_V3_VALID_RETURN_OBS, int)
    telemetry["v3_active_mean_return"] = search_pat(RE_V3_ACTIVE_MEAN_RETURN, float)
    telemetry["v3_active_final_fast"] = search_pat(RE_V3_ACTIVE_FINAL_FAST, float)
    telemetry["v3_active_final_slow"] = search_pat(RE_V3_ACTIVE_FINAL_SLOW, float)
    telemetry["v3_active_max_dd"] = search_pat(RE_V3_ACTIVE_MAX_DD, float)

    # Reduction Telemetry
    telemetry["reduce_db_count"] = search_pat(RE_REDUCED_DB, int)
    telemetry["removed_clauses"] = search_pat(RE_REMOVED_CLAUSES, int)
    telemetry["glue_clauses_dl2"] = search_pat(RE_LEARNTS_DL2, int)
    telemetry["adapt_reduce_calls"] = search_pat(RE_ADAPT_REDUCE_CALLS, int)
    telemetry["adapt_clauses_ranked"] = search_pat(RE_ADAPT_CLAUSES_RANKED, int)
    telemetry["adapt_clauses_eligible"] = search_pat(RE_ADAPT_CLAUSES_ELIG, int)
    telemetry["adapt_clauses_removed"] = search_pat(RE_ADAPT_CLAUSES_REM, int)
    telemetry["adapt_postpone_evals"] = search_pat(RE_ADAPT_POSTPONE_EVALS, int)
    telemetry["adapt_postpone_sat"] = search_pat(RE_ADAPT_POSTPONE_SAT, int)
    telemetry["adapt_postpone_inc_db"] = search_pat(RE_ADAPT_POSTPONE_INC, int)

    return telemetry


def extract_model_lines(stdout_text: str) -> Optional[str]:
    """Extracts all 'v ...' model lines from stdout."""
    model_lines = RE_MODEL_LINES.findall(stdout_text)
    if not model_lines:
        return None
    return "\n".join(model_lines)


class FatalCorrectnessError(Exception):
    """Raised when an invalid model or label contradiction is detected."""
    pass


def main():
    parser = argparse.ArgumentParser(description="Step 36 Final Frozen Holdout Evaluation Runner")
    parser.add_argument("--solver", default="src/glucose_windows/glucose-simp.exe", help="Path to release solver executable")
    parser.add_argument("--manifest", default="benchmarks/final_holdout/holdout_manifest.json", help="Path to holdout benchmark manifest")
    parser.add_argument("--configs", default="experiments/frozen_configurations.json", help="Path to frozen configurations JSON")
    parser.add_argument("--output-dir", default="experiments/results/final_holdout", help="Output directory for results and logs")
    parser.add_argument("--timeout", type=float, default=30.0, help="Wall-clock timeout in seconds (default 30.0)")
    parser.add_argument("--repetitions", type=int, default=3, help="Number of repetitions (default 3)")
    parser.add_argument("--max-runs", type=int, default=None, help="Optional max runs limit for testing")
    args = parser.parse_args()

    solver_path = (WORKSPACE / args.solver).resolve()
    manifest_path = (WORKSPACE / args.manifest).resolve()
    configs_path = (WORKSPACE / args.configs).resolve()
    output_dir = (WORKSPACE / args.output_dir).resolve()
    logs_dir = output_dir / "logs"
    master_csv = output_dir / "master_results.csv"
    checkpoint_file = output_dir / "checkpoint.json"
    summary_file = output_dir / "completion_summary.json"

    logs_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("STEP 36: FINAL FROZEN HOLDOUT EVALUATION CAMPAIGN")
    print("=" * 80)
    print(f"[*] Solver Binary   : {solver_path}")
    print(f"[*] Manifest Path   : {manifest_path}")
    print(f"[*] Configs Path    : {configs_path}")
    print(f"[*] Output Dir      : {output_dir}")
    print(f"[*] Timeout Budget  : {args.timeout}s (PAR-2 penalty = {args.timeout * 2}s)")
    print(f"[*] Repetitions     : {args.repetitions}")

    # 1. Re-verify solver binary SHA-256
    expected_bin_hash = "e811005ab18256aa70efba2945ad5a578f5a38abec7e5c563d0989fd69e06b66"
    actual_bin_hash = sha256_file(solver_path)
    if actual_bin_hash != expected_bin_hash:
        print(f"[FATAL ERROR] Solver binary hash mismatch!\nExpected: {expected_bin_hash}\nActual:   {actual_bin_hash}")
        sys.exit(1)
    print(f"[+] Verified Solver Binary SHA-256: {actual_bin_hash}")

    # 2. Load manifest and verify all 48 CNF hashes
    with open(manifest_path, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)
    print(f"[+] Loaded {len(benchmarks)} holdout benchmark instances from manifest.")

    benchmarks_by_id = {b["benchmark_id"]: b for b in benchmarks}
    sorted_benchmarks = sorted(benchmarks, key=lambda b: b["benchmark_id"])

    for b in sorted_benchmarks:
        cnf_file = WORKSPACE / "benchmarks" / "final_holdout" / b["filename"]
        if not cnf_file.exists():
            print(f"[FATAL ERROR] Holdout CNF file missing: {cnf_file}")
            sys.exit(1)
        actual_cnf_hash = sha256_file(cnf_file)
        if actual_cnf_hash != b["sha256_hash"]:
            print(f"[FATAL ERROR] Holdout CNF hash mismatch for {b['filename']}!\nExpected: {b['sha256_hash']}\nActual:   {actual_cnf_hash}")
            sys.exit(1)
    print("[+] Verified all 48 Holdout Benchmark CNF SHA-256 hashes.")

    # 3. Load configurations
    with open(configs_path, "r", encoding="utf-8") as f:
        cfg_data = json.load(f)
    configurations = cfg_data["configurations"]
    print(f"[+] Loaded {len(configurations)} frozen configurations.")
    if len(configurations) != 8:
        print(f"[FATAL ERROR] Expected exactly 8 configurations, got {len(configurations)}")
        sys.exit(1)

    # 4. Generate Pre-Registered Balanced Cyclic Execution Schedule
    # Order: For repetition r in 1..3:
    #          For b_idx, b in enumerate(sorted_benchmarks):
    #            For offset in 0..7:
    #              c_idx = (offset + b_idx + (r - 1)) % 8
    planned_runs = []
    run_counter = 1

    for rep in range(1, args.repetitions + 1):
        for b_idx, b in enumerate(sorted_benchmarks):
            for offset in range(8):
                c_idx = (offset + b_idx + (rep - 1)) % 8
                cfg = configurations[c_idx]
                run_id = f"run_{run_counter:04d}_{cfg['id']}_{b['benchmark_id']}_rep{rep}"
                planned_runs.append({
                    "run_id": run_id,
                    "execution_order": run_counter,
                    "repetition": rep,
                    "config": cfg,
                    "benchmark": b
                })
                run_counter += 1

    total_planned = len(planned_runs)
    print(f"[+] Pre-registered Execution Plan: {total_planned} planned sequential runs.")
    if total_planned != 1152:
        print(f"[WARNING] Planned total runs ({total_planned}) != 1152 standard budget.")

    # 5. Check Existing Results for Safe Resumption
    completed_runs: Dict[str, Dict[str, Any]] = {}
    csv_exists = master_csv.exists()

    if csv_exists:
        try:
            with open(master_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = row.get("run_id")
                    if rid and row.get("status") in ["SAT", "UNSAT", "TIMEOUT", "ERROR"]:
                        completed_runs[rid] = row
            print(f"[*] Resuming campaign: Found {len(completed_runs)} already completed runs in {master_csv.name}")
        except Exception as e:
            print(f"[WARNING] Could not parse existing CSV: {e}")

    # Open CSV in append mode if exists, else write with header
    csv_file = open(master_csv, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
    if not csv_exists or master_csv.stat().st_size == 0:
        writer.writeheader()
        csv_file.flush()
        os.fsync(csv_file.fileno())

    # Limit runs if max-runs specified
    if args.max_runs is not None:
        planned_runs = planned_runs[:args.max_runs]
        print(f"[*] Running restricted test suite of {len(planned_runs)} runs.")

    # 6. Execute Experiment Loop
    start_campaign_time = time.time()
    runs_executed_in_session = 0
    runs_skipped_in_session = 0

    print("=" * 80)
    print("BEGINNING EXECUTION CAMPAIGN")
    print("=" * 80)

    try:
        for plan in planned_runs:
            rid = plan["run_id"]
            order = plan["execution_order"]
            rep = plan["repetition"]
            cfg = plan["config"]
            bmk = plan["benchmark"]

            if rid in completed_runs:
                runs_skipped_in_session += 1
                continue

            cnf_path = WORKSPACE / "benchmarks" / "final_holdout" / bmk["filename"]
            log_path = logs_dir / f"{rid}.log"

            # Construct execution command:
            # glucose-simp.exe -model <config_flags> <cnf_path>
            cmd = [str(solver_path), "-model"] + cfg["command_flags"] + [str(cnf_path)]

            print(f"[{order:04d}/{total_planned}] {cfg['id']} on {bmk['filename']} (Rep {rep})... ", end="", flush=True)

            timed_out = False
            proc_cpu_time = 0.0
            proc_peak_rss = 0.0
            start_wall = time.perf_counter()

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace"
                )

                ps_proc = None
                if PSUTIL_AVAILABLE:
                    try:
                        ps_proc = psutil.Process(proc.pid)
                    except Exception:
                        pass

                stdout_text, stderr_text = proc.communicate(timeout=args.timeout)
                exit_code = proc.returncode

                if ps_proc:
                    try:
                        ct = ps_proc.cpu_times()
                        proc_cpu_time = ct.user + ct.system
                        proc_peak_rss = ps_proc.memory_info().rss / (1024 * 1024)
                    except Exception:
                        pass

            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    proc.kill()
                except Exception:
                    pass
                stdout_text, stderr_text = proc.communicate()
                exit_code = "TIMEOUT"

            except Exception as e:
                exit_code = "ERROR"
                stdout_text = ""
                stderr_text = f"Process launch error: {e}"

            elapsed_wall = time.perf_counter() - start_wall

            # Determine solver outcome status
            if timed_out or exit_code == "TIMEOUT":
                status = "TIMEOUT"
            elif RE_SAT.search(stdout_text) or exit_code == 10:
                status = "SAT"
            elif RE_UNSAT.search(stdout_text) or exit_code == 20:
                status = "UNSAT"
            else:
                status = "ERROR"

            # Telemetry extraction
            telemetry = extract_telemetry(stdout_text)
            if not proc_cpu_time and telemetry.get("solver_cpu_time_s"):
                proc_cpu_time = telemetry["solver_cpu_time_s"]
            if not proc_peak_rss and telemetry.get("solver_memory_mb"):
                proc_peak_rss = telemetry["solver_memory_mb"]

            # 7. Independent Model & Correctness Verification
            verification_status = "UNKNOWN"
            authoritative_label = bmk["authoritative_label"]

            if status == "SAT":
                raw_model = extract_model_lines(stdout_text)
                if not raw_model:
                    verification_status = "MISSING_MODEL"
                    print("ERROR: SAT claimed but no model lines found!")
                    raise FatalCorrectnessError(f"Benchmark {bmk['filename']} claimed SAT by {cfg['id']} but emitted no model.")
                else:
                    is_valid, msg = verify_model(str(cnf_path), raw_model)
                    if is_valid:
                        verification_status = "VERIFIED_SAT"
                        # Also check against known label if authoritative label is UNSAT
                        if authoritative_label == "UNSAT":
                            print(f"\n[FATAL ERROR] Label contradiction: {bmk['filename']} is known UNSAT, but model verified true!")
                            raise FatalCorrectnessError(f"Contradiction: {bmk['filename']} has authoritative label UNSAT but model verified SAT.")
                    else:
                        verification_status = "INVALID_MODEL"
                        print(f"\n[FATAL ERROR] Invalid SAT model: {msg}")
                        raise FatalCorrectnessError(f"Invalid model on {bmk['filename']} ({cfg['id']}): {msg}")

            elif status == "UNSAT":
                if authoritative_label == "SAT":
                    print(f"\n[FATAL ERROR] Label contradiction: {bmk['filename']} is known SAT, but solver reported UNSAT!")
                    raise FatalCorrectnessError(f"Contradiction: {bmk['filename']} has authoritative label SAT but solver reported UNSAT.")
                elif authoritative_label == "UNSAT":
                    verification_status = "VERIFIED_UNSAT"
                else:
                    verification_status = "CONSISTENT_UNKNOWN"

            elif status == "TIMEOUT":
                verification_status = "TIMEOUT"
            else:
                verification_status = "ERROR"

            # Save full log file
            with open(log_path, "w", encoding="utf-8") as f_log:
                f_log.write(f"c --- EXECUTION RUN METADATA ---\n")
                f_log.write(f"c Run ID: {rid}\n")
                f_log.write(f"c Execution Order: {order}\n")
                f_log.write(f"c Repetition: {rep}\n")
                f_log.write(f"c Configuration ID: {cfg['id']}\n")
                f_log.write(f"c Benchmark ID: {bmk['benchmark_id']} ({bmk['filename']})\n")
                f_log.write(f"c Authoritative Label: {authoritative_label}\n")
                f_log.write(f"c Status: {status} ({verification_status})\n")
                f_log.write(f"c Exit Code: {exit_code}\n")
                f_log.write(f"c Wall Time (s): {elapsed_wall:.4f}\n")
                f_log.write(f"c Command: {' '.join(cmd)}\n")
                f_log.write(f"c --- SOLVER STDOUT ---\n")
                f_log.write(stdout_text)
                if stderr_text:
                    f_log.write(f"\nc --- SOLVER STDERR ---\n")
                    f_log.write(stderr_text)

            # Build master CSV row
            row = {
                "run_id": rid,
                "execution_order": order,
                "repetition": rep,
                "config_id": cfg["id"],
                "config_name": cfg["name"],
                "restart_strategy": cfg["restart_strategy"],
                "reduce_strategy": cfg["reduce_strategy"],
                "command_flags": " ".join(cfg["command_flags"]),
                "benchmark_id": bmk["benchmark_id"],
                "benchmark_name": bmk["filename"],
                "category": bmk["category"],
                "family": bmk["family"],
                "authoritative_label": authoritative_label,
                "cnf_sha256": bmk["sha256_hash"],
                "solver_sha256": actual_bin_hash,
                "solver_commit": "16ad544bd3d20d88a054aea3b962784e380ae9be",
                "status": status,
                "verification_status": verification_status,
                "exit_code": exit_code,
                "wall_time_s": round(elapsed_wall, 4),
                "process_cpu_time_s": round(proc_cpu_time, 4),
                "process_peak_rss_mb": round(proc_peak_rss, 2),
                "solver_cpu_time_s": telemetry.get("solver_cpu_time_s", ""),
                "solver_memory_mb": telemetry.get("solver_memory_mb", ""),
                "conflicts": telemetry.get("conflicts", ""),
                "decisions": telemetry.get("decisions", ""),
                "propagations": telemetry.get("propagations", ""),
                "restarts": telemetry.get("restarts", ""),
                "genuine_restarts": telemetry.get("genuine_restarts", ""),
                "blocked_restarts": telemetry.get("blocked_restarts", ""),
                "v1_adaptive_requests": telemetry.get("v1_adaptive_requests", ""),
                "v1_adaptive_restarts": telemetry.get("v1_adaptive_restarts", ""),
                "v1_last_score_w": telemetry.get("v1_last_score_w", ""),
                "v1_last_score_global": telemetry.get("v1_last_score_global", ""),
                "v3_req_trend": telemetry.get("v3_req_trend", ""),
                "v3_req_drawdown": telemetry.get("v3_req_drawdown", ""),
                "v3_req_ceiling": telemetry.get("v3_req_ceiling", ""),
                "v3_total_requests": telemetry.get("v3_total_requests", ""),
                "v3_executed_restarts": telemetry.get("v3_executed_restarts", ""),
                "v3_blocked_restarts": telemetry.get("v3_blocked_restarts", ""),
                "v3_max_interval": telemetry.get("v3_max_interval", ""),
                "v3_valid_return_obs": telemetry.get("v3_valid_return_obs", ""),
                "v3_active_mean_return": telemetry.get("v3_active_mean_return", ""),
                "v3_active_final_fast": telemetry.get("v3_active_final_fast", ""),
                "v3_active_final_slow": telemetry.get("v3_active_final_slow", ""),
                "v3_active_max_dd": telemetry.get("v3_active_max_dd", ""),
                "reduce_db_count": telemetry.get("reduce_db_count", ""),
                "removed_clauses": telemetry.get("removed_clauses", ""),
                "glue_clauses_dl2": telemetry.get("glue_clauses_dl2", ""),
                "adapt_reduce_calls": telemetry.get("adapt_reduce_calls", ""),
                "adapt_clauses_ranked": telemetry.get("adapt_clauses_ranked", ""),
                "adapt_clauses_eligible": telemetry.get("adapt_clauses_eligible", ""),
                "adapt_clauses_removed": telemetry.get("adapt_clauses_removed", ""),
                "adapt_postpone_evals": telemetry.get("adapt_postpone_evals", ""),
                "adapt_postpone_sat": telemetry.get("adapt_postpone_sat", ""),
                "adapt_postpone_inc_db": telemetry.get("adapt_postpone_inc_db", ""),
                "log_file": str(log_path.relative_to(WORKSPACE)),
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }

            # Atomic write and sync to CSV
            writer.writerow(row)
            csv_file.flush()
            os.fsync(csv_file.fileno())

            completed_runs[rid] = row
            runs_executed_in_session += 1

            # Print brief status
            cfc_str = f"cfc={telemetry.get('conflicts', 0)}" if status != "TIMEOUT" else "TIMEOUT"
            print(f"{status} ({verification_status}) in {elapsed_wall:.2f}s [{cfc_str}]")

            # Periodic checkpoint update (every 10 runs or at end)
            if runs_executed_in_session % 10 == 0:
                with open(checkpoint_file, "w", encoding="utf-8") as f_chk:
                    json.dump({
                        "total_planned": total_planned,
                        "completed_count": len(completed_runs),
                        "last_order": order,
                        "last_run_id": rid,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat()
                    }, f_chk, indent=2)

    except KeyboardInterrupt:
        print("\n[WARNING] Execution campaign interrupted by user! Progress safely checkpointed.")
    finally:
        csv_file.close()

    total_completed = len(completed_runs)
    total_duration = time.time() - start_campaign_time

    # 8. Produce Final Completion Summary
    sat_count = sum(1 for r in completed_runs.values() if r["status"] == "SAT")
    unsat_count = sum(1 for r in completed_runs.values() if r["status"] == "UNSAT")
    timeout_count = sum(1 for r in completed_runs.values() if r["status"] == "TIMEOUT")
    error_count = sum(1 for r in completed_runs.values() if r["status"] == "ERROR")
    verified_sat_count = sum(1 for r in completed_runs.values() if r["verification_status"] == "VERIFIED_SAT")
    verified_unsat_count = sum(1 for r in completed_runs.values() if r["verification_status"] == "VERIFIED_UNSAT")

    cfg_counts = {}
    for r in completed_runs.values():
        cid = r["config_id"]
        cfg_counts[cid] = cfg_counts.get(cid, 0) + 1

    bmk_counts = {}
    for r in completed_runs.values():
        bid = r["benchmark_id"]
        bmk_counts[bid] = bmk_counts.get(bid, 0) + 1

    summary = {
        "campaign_name": "Final Frozen Holdout Evaluation (Step 36)",
        "timestamp_finished": datetime.now(timezone.utc).isoformat(),
        "total_planned": total_planned,
        "total_completed": total_completed,
        "session_executed": runs_executed_in_session,
        "session_skipped": runs_skipped_in_session,
        "total_duration_s": round(total_duration, 2),
        "status_counts": {
            "SAT": sat_count,
            "UNSAT": unsat_count,
            "TIMEOUT": timeout_count,
            "ERROR": error_count
        },
        "verification_counts": {
            "VERIFIED_SAT": verified_sat_count,
            "VERIFIED_UNSAT": verified_unsat_count
        },
        "config_run_counts": cfg_counts,
        "benchmark_run_counts": bmk_counts,
        "is_complete": (total_completed == total_planned)
    }

    with open(summary_file, "w", encoding="utf-8") as f_sum:
        json.dump(summary, f_sum, indent=2)

    with open(checkpoint_file, "w", encoding="utf-8") as f_chk:
        json.dump({
            "total_planned": total_planned,
            "completed_count": total_completed,
            "is_complete": (total_completed == total_planned),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }, f_chk, indent=2)

    print("=" * 80)
    print("CAMPAIGN COMPLETION SUMMARY")
    print("=" * 80)
    print(f"[*] Total Planned      : {total_planned}")
    print(f"[*] Total Completed    : {total_completed} / {total_planned}")
    print(f"[*] Session Runs       : {runs_executed_in_session} (Skipped: {runs_skipped_in_session})")
    print(f"[*] Wall Duration      : {total_duration / 60.0:.2f} minutes")
    print(f"[*] Outcomes           : SAT={sat_count}, UNSAT={unsat_count}, TIMEOUT={timeout_count}, ERROR={error_count}")
    print(f"[*] Verifications      : VERIFIED_SAT={verified_sat_count}, VERIFIED_UNSAT={verified_unsat_count}")
    print(f"[*] Master Results CSV : {master_csv}")
    print(f"[*] Summary JSON       : {summary_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()

