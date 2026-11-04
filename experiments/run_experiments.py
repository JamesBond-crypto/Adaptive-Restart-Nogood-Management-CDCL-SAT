#!/usr/bin/env python3
"""
run_experiments.py - Benchmark Execution & Telemetry Extraction Harness

Executes SAT solvers (such as Glucose 4.2.1) on sets of DIMACS CNF instances,
enforcing timeouts externally, capturing process telemetry, parsing solver metrics,
verifying SAT models, and logging reproducible results in CSV and log files.

Usage example:
    python experiments/run_experiments.py \
        --solver src/glucose_windows/glucose-simp.exe \
        --benchmarks benchmarks/smoke_test \
        --timeout 60 \
        --output-csv experiments/results/benchmark_results.csv
"""

import sys
import os
import re
import csv
import time
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import independent model verifier
from verify_model import verify_model, ModelParseError, CNFParseError


# Regex patterns for Glucose telemetry parsing
RE_SAT = re.compile(r"^s\s+SATISFIABLE", re.MULTILINE)
RE_UNSAT = re.compile(r"^s\s+UNSATISFIABLE", re.MULTILINE)
RE_INDET = re.compile(r"^s\s+INDETERMINATE", re.MULTILINE)

RE_CPU_TIME = re.compile(r"^c\s+CPU time\s*:\s*([\d\.]+)\s*s", re.MULTILINE)
RE_MEM_USED = re.compile(r"^c\s+Memory used\s*:\s*([\d\.]+)\s*MB", re.MULTILINE)
RE_CONFLICTS = re.compile(r"^c\s+conflicts\s*:\s*(\d+)", re.MULTILINE)
RE_DECISIONS = re.compile(r"^c\s+decisions\s*:\s*(\d+)", re.MULTILINE)
RE_PROPAGATIONS = re.compile(r"^c\s+propagations\s*:\s*(\d+)", re.MULTILINE)
RE_RESTARTS = re.compile(r"^c\s+restarts\s*:\s*(\d+)", re.MULTILINE)
RE_GENUINE_RESTARTS = re.compile(r"^c\s+genuine restarts\s*:\s*(\d+)", re.MULTILINE)
RE_RESTART_STRAT = re.compile(r"^c\s+restart strategy\s*:\s*([^\r\n]+)", re.MULTILINE)
RE_ADAPT_REQUESTS = re.compile(r"^c\s+adaptive restart requests\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_RESTARTS = re.compile(r"^c\s+adaptive restarts\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_SCORES = re.compile(r"^c\s+last adaptive score\s*:\s*([\d\.\-]+)\s*\(global:\s*([\d\.\-]+)\)", re.MULTILINE)
RE_BLOCKED_RESTARTS = re.compile(r"^c\s+blocked restarts\s*:\s*(\d+)", re.MULTILINE)
RE_V2_QUALITY_FALLBACK = re.compile(r"^c\s+v2 quality fallback\s*:\s*([^\r\n]+)", re.MULTILINE)
RE_V2_CONFLICT_CEILING = re.compile(r"^c\s+v2 conflict ceiling\s*:\s*([^\r\n]+)", re.MULTILINE)
RE_V2_REQ_PROGRESS = re.compile(r"^c\s+v2 req progress\s*:\s*(\d+)", re.MULTILINE)
RE_V2_REQ_QUALITY = re.compile(r"^c\s+v2 req quality\s*:\s*(\d+)", re.MULTILINE)
RE_V2_REQ_CEILING = re.compile(r"^c\s+v2 req ceiling\s*:\s*(\d+)", re.MULTILINE)
RE_V2_TOTAL_REQUESTS = re.compile(r"^c\s+v2 total requests\s*:\s*(\d+)", re.MULTILINE)
RE_V2_EXECUTED_RESTARTS = re.compile(r"^c\s+v2 executed restarts\s*:\s*(\d+)", re.MULTILINE)
RE_V2_BLOCKED_RESTARTS = re.compile(r"^c\s+v2 blocked restarts\s*:\s*(\d+)", re.MULTILINE)
RE_V2_MAX_INTERVAL = re.compile(r"^c\s+v2 max interval\s*:\s*(\d+)", re.MULTILINE)
RE_REDUCED_DB = re.compile(r"^c\s+nb ReduceDB\s*:\s*(\d+)", re.MULTILINE)
RE_REMOVED_CLAUSES = re.compile(r"^c\s+nb removed Clauses\s*:\s*(\d+)", re.MULTILINE)
RE_LEARNTS_DL2 = re.compile(r"^c\s+nb learnts DL2\s*:\s*(\d+)", re.MULTILINE)
RE_REDUCE_STRAT = re.compile(r"^c\s+reduction strategy\s*:\s*([^\r\n]+)", re.MULTILINE)
RE_ADAPT_REDUCE_CALLS = re.compile(r"^c\s+adapt reduce calls\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_CLAUSES_RANKED = re.compile(r"^c\s+adapt clauses ranked\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_CLAUSES_ELIGIBLE = re.compile(r"^c\s+adapt clauses eligible\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_CLAUSES_REMOVED = re.compile(r"^c\s+adapt clauses removed\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_SPARED_LOCKED = re.compile(r"^c\s+adapt spared locked\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_SPARED_BINARY = re.compile(r"^c\s+adapt spared binary\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_SPARED_GLUE = re.compile(r"^c\s+adapt spared glue\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_SPARED_CANBEDEL = re.compile(r"^c\s+adapt spared canbedel\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_LAST_RETAINED = re.compile(r"^c\s+adapt last retained\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_LAST_AVG_RET_LBD = re.compile(r"^c\s+adapt last avg ret LBD\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_ADAPT_LAST_AVG_DEL_LBD = re.compile(r"^c\s+adapt last avg del LBD\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_ADAPT_REDUCE_TIME = re.compile(r"^c\s+adapt reduce time\s*:\s*([\d\.\-]+)\s*s", re.MULTILINE)
RE_ADAPT_POSTPONE_EVALS = re.compile(r"^c\s+adapt postpone evals\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_POSTPONE_SAT = re.compile(r"^c\s+adapt postpone sat\s*:\s*(\d+)", re.MULTILINE)
RE_ADAPT_POSTPONE_INC_DB = re.compile(r"^c\s+adapt postpone inc db\s*:\s*(\d+)", re.MULTILINE)
RE_V3_SHADOW = re.compile(r"^c\s+v3 shadow\s*:\s*([^\r\n]+)", re.MULTILINE)
RE_V3_VALID_OBS = re.compile(r"^c\s+v3 shadow valid obs\s*:\s*(\d+)", re.MULTILINE)
RE_V3_INVALID_OBS = re.compile(r"^c\s+v3 shadow invalid obs\s*:\s*(\d+)", re.MULTILINE)
RE_V3_MEAN_RETURN = re.compile(r"^c\s+v3 shadow mean return\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_MIN_RETURN = re.compile(r"^c\s+v3 shadow min return\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_MAX_RETURN = re.compile(r"^c\s+v3 shadow max return\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_FINAL_FAST = re.compile(r"^c\s+v3 shadow final fast\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_FINAL_SLOW = re.compile(r"^c\s+v3 shadow final slow\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_MAX_DRAWDOWN = re.compile(r"^c\s+v3 shadow max drawdown\s*:\s*([\d\.\-]+)", re.MULTILINE)
RE_V3_RAW_DRAWDOWN = re.compile(r"^c\s+v3 raw cond drawdown\s*:\s*(\d+)", re.MULTILINE)
RE_V3_RAW_TREND = re.compile(r"^c\s+v3 raw cond trend\s*:\s*(\d+)", re.MULTILINE)
RE_V3_RAW_CEILING = re.compile(r"^c\s+v3 raw cond ceiling\s*:\s*(\d+)", re.MULTILINE)
RE_V3_HYP_TOTAL = re.compile(r"^c\s+v3 hyp event total\s*:\s*(\d+)", re.MULTILINE)
RE_V3_HYP_DRAWDOWN = re.compile(r"^c\s+v3 hyp event drawdown\s*:\s*(\d+)", re.MULTILINE)
RE_V3_HYP_TREND = re.compile(r"^c\s+v3 hyp event trend\s*:\s*(\d+)", re.MULTILINE)
RE_V3_HYP_CEILING = re.compile(r"^c\s+v3 hyp event ceiling\s*:\s*(\d+)", re.MULTILINE)
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
RE_FIXED_INTERVAL = re.compile(r"^c\s+fixed restart interval\s*:\s*(\d+)", re.MULTILINE)
RE_FIXED_REQUESTS = re.compile(r"^c\s+fixed restart requests\s*:\s*(\d+)", re.MULTILINE)
RE_FIXED_EXECUTED = re.compile(r"^c\s+fixed executed restarts\s*:\s*(\d+)", re.MULTILINE)
RE_FIXED_BLOCKED = re.compile(r"^c\s+fixed blocked restarts\s*:\s*(\d+)", re.MULTILINE)
RE_STRATEGY_ADAPT_RESTARTS = re.compile(r"^c\s+strategy adapt restarts\s*:\s*(\d+)", re.MULTILINE)
RE_FIXED_MAX_INTERVAL = re.compile(r"^c\s+fixed max interval\s*:\s*(\d+)", re.MULTILINE)
RE_FIXED_CFC_SINCE = re.compile(r"^c\s+fixed cfc since restart\s*:\s*(\d+)", re.MULTILINE)
RE_VARS = re.compile(r"^c\s*\|\s*Number of variables:\s*(\d+)", re.MULTILINE)
RE_CLAUSES = re.compile(r"^c\s*\|\s*Number of clauses:\s*(\d+)", re.MULTILINE)
RE_PARSE_TIME = re.compile(r"^c\s*\|\s*Parse time:\s*([\d\.]+)\s*s", re.MULTILINE)
RE_SIMP_TIME = re.compile(r"^c\s*\|\s*Simplification time:\s*([\d\.]+)\s*s", re.MULTILINE)

RE_MODEL_LINES = re.compile(r"^v\s+.*$", re.MULTILINE)


CSV_FIELDNAMES = [
    "run_id",
    "timestamp_utc",
    "solver_name",
    "solver_path",
    "benchmark_name",
    "benchmark_path",
    "status",
    "exit_code",
    "timed_out",
    "timeout_limit_s",
    "wall_time_s",
    "cpu_time_s",
    "memory_mb",
    "model_verified",
    "verification_notes",
    "conflicts",
    "decisions",
    "propagations",
    "restarts",
    "starts",
    "genuine_restarts",
    "restart_strategy",
    "adaptive_restart_requests",
    "adaptive_restarts",
    "last_adaptive_score_w",
    "last_adaptive_score_global",
    "blocked_restarts",
    "reduce_db_count",
    "removed_clauses",
    "glue_clauses_dl2",
    "reduce_strategy",
    "adapt_reduce_calls",
    "adapt_clauses_ranked",
    "adapt_clauses_eligible",
    "adapt_clauses_removed",
    "adapt_spared_locked",
    "adapt_spared_binary",
    "adapt_spared_glue",
    "adapt_spared_canbedel",
    "adapt_last_retained",
    "adapt_last_avg_ret_lbd",
    "adapt_last_avg_del_lbd",
    "adapt_reduce_time_s",
    "adapt_postpone_evals",
    "adapt_postpone_sat",
    "adapt_postpone_inc_db",
    "v2_quality_fallback",
    "v2_conflict_ceiling",
    "v2_req_progress",
    "v2_req_quality",
    "v2_req_ceiling",
    "v2_total_requests",
    "v2_executed_restarts",
    "v2_blocked_restarts",
    "v2_max_interval",
    "v3_shadow",
    "v3_valid_obs",
    "v3_invalid_obs",
    "v3_mean_return",
    "v3_min_return",
    "v3_max_return",
    "v3_final_fast",
    "v3_final_slow",
    "v3_max_drawdown",
    "v3_raw_cond_drawdown",
    "v3_raw_cond_trend",
    "v3_raw_cond_ceiling",
    "v3_hyp_events_total",
    "v3_hyp_events_drawdown",
    "v3_hyp_events_trend",
    "v3_hyp_events_ceiling",
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
    "fixed_restart_interval",
    "fixed_restart_requests",
    "fixed_executed_restarts",
    "fixed_blocked_restarts",
    "strategy_adaptation_restarts",
    "fixed_max_interval",
    "fixed_cfc_since_restart",
    "num_vars",
    "num_clauses",
    "parse_time_s",
    "simp_time_s",
    "log_file"
]


def extract_telemetry(stdout_text: str) -> Dict[str, Any]:
    """Parses standard Glucose output and returns extracted metrics dict."""
    telemetry: Dict[str, Any] = {}

    def search_pattern(pattern: re.Pattern, conv=str, default=""):
        m = pattern.search(stdout_text)
        if m:
            try:
                return conv(m.group(1))
            except (ValueError, TypeError):
                return default
        return default

    telemetry["cpu_time_s"] = search_pattern(RE_CPU_TIME, float)
    telemetry["memory_mb"] = search_pattern(RE_MEM_USED, float)
    telemetry["conflicts"] = search_pattern(RE_CONFLICTS, int)
    telemetry["decisions"] = search_pattern(RE_DECISIONS, int)
    telemetry["propagations"] = search_pattern(RE_PROPAGATIONS, int)
    
    restarts_val = search_pattern(RE_RESTARTS, int, "")
    telemetry["restarts"] = restarts_val
    telemetry["starts"] = restarts_val
    telemetry["genuine_restarts"] = search_pattern(RE_GENUINE_RESTARTS, int, "")
    
    strat_m = RE_RESTART_STRAT.search(stdout_text)
    if strat_m:
        raw_strat = strat_m.group(1).strip()
        telemetry["restart_strategy"] = "adaptive-v2" if "adaptive-v2" in raw_strat else ("adaptive" if "adaptive" in raw_strat else "baseline")
    else:
        telemetry["restart_strategy"] = ""

    telemetry["adaptive_restart_requests"] = search_pattern(RE_ADAPT_REQUESTS, int, "")
    telemetry["adaptive_restarts"] = search_pattern(RE_ADAPT_RESTARTS, int, "")

    m_score = RE_ADAPT_SCORES.search(stdout_text)
    if m_score:
        try:
            telemetry["last_adaptive_score_w"] = float(m_score.group(1))
            telemetry["last_adaptive_score_global"] = float(m_score.group(2))
        except (ValueError, TypeError):
            telemetry["last_adaptive_score_w"] = ""
            telemetry["last_adaptive_score_global"] = ""
    else:
        telemetry["last_adaptive_score_w"] = ""
        telemetry["last_adaptive_score_global"] = ""

    telemetry["blocked_restarts"] = search_pattern(RE_BLOCKED_RESTARTS, int)
    telemetry["reduce_db_count"] = search_pattern(RE_REDUCED_DB, int)
    telemetry["removed_clauses"] = search_pattern(RE_REMOVED_CLAUSES, int)
    telemetry["glue_clauses_dl2"] = search_pattern(RE_LEARNTS_DL2, int)

    red_strat_m = RE_REDUCE_STRAT.search(stdout_text)
    if red_strat_m:
        raw_red_strat = red_strat_m.group(1).strip().lower()
        if "adaptive-fixed" in raw_red_strat:
            telemetry["reduce_strategy"] = "adaptive-fixed"
        elif "adaptive" in raw_red_strat:
            telemetry["reduce_strategy"] = "adaptive"
        else:
            telemetry["reduce_strategy"] = "baseline"
    else:
        telemetry["reduce_strategy"] = ""

    telemetry["adapt_reduce_calls"] = search_pattern(RE_ADAPT_REDUCE_CALLS, int, "")
    telemetry["adapt_clauses_ranked"] = search_pattern(RE_ADAPT_CLAUSES_RANKED, int, "")
    telemetry["adapt_clauses_eligible"] = search_pattern(RE_ADAPT_CLAUSES_ELIGIBLE, int, "")
    telemetry["adapt_clauses_removed"] = search_pattern(RE_ADAPT_CLAUSES_REMOVED, int, "")
    telemetry["adapt_spared_locked"] = search_pattern(RE_ADAPT_SPARED_LOCKED, int, "")
    telemetry["adapt_spared_binary"] = search_pattern(RE_ADAPT_SPARED_BINARY, int, "")
    telemetry["adapt_spared_glue"] = search_pattern(RE_ADAPT_SPARED_GLUE, int, "")
    telemetry["adapt_spared_canbedel"] = search_pattern(RE_ADAPT_SPARED_CANBEDEL, int, "")
    telemetry["adapt_last_retained"] = search_pattern(RE_ADAPT_LAST_RETAINED, int, "")
    telemetry["adapt_last_avg_ret_lbd"] = search_pattern(RE_ADAPT_LAST_AVG_RET_LBD, float, "")
    telemetry["adapt_last_avg_del_lbd"] = search_pattern(RE_ADAPT_LAST_AVG_DEL_LBD, float, "")
    telemetry["adapt_reduce_time_s"] = search_pattern(RE_ADAPT_REDUCE_TIME, float, "")
    telemetry["adapt_postpone_evals"] = search_pattern(RE_ADAPT_POSTPONE_EVALS, int, "")
    telemetry["adapt_postpone_sat"] = search_pattern(RE_ADAPT_POSTPONE_SAT, int, "")
    telemetry["adapt_postpone_inc_db"] = search_pattern(RE_ADAPT_POSTPONE_INC_DB, int, "")

    telemetry["v2_quality_fallback"] = search_pattern(RE_V2_QUALITY_FALLBACK, str, "")
    telemetry["v2_conflict_ceiling"] = search_pattern(RE_V2_CONFLICT_CEILING, str, "")
    telemetry["v2_req_progress"] = search_pattern(RE_V2_REQ_PROGRESS, int, "")
    telemetry["v2_req_quality"] = search_pattern(RE_V2_REQ_QUALITY, int, "")
    telemetry["v2_req_ceiling"] = search_pattern(RE_V2_REQ_CEILING, int, "")
    telemetry["v2_total_requests"] = search_pattern(RE_V2_TOTAL_REQUESTS, int, "")
    telemetry["v2_executed_restarts"] = search_pattern(RE_V2_EXECUTED_RESTARTS, int, "")
    telemetry["v2_blocked_restarts"] = search_pattern(RE_V2_BLOCKED_RESTARTS, int, "")
    telemetry["v2_max_interval"] = search_pattern(RE_V2_MAX_INTERVAL, int, "")

    telemetry["v3_shadow"] = search_pattern(RE_V3_SHADOW, str, "")
    telemetry["v3_valid_obs"] = search_pattern(RE_V3_VALID_OBS, int, "")
    telemetry["v3_invalid_obs"] = search_pattern(RE_V3_INVALID_OBS, int, "")
    telemetry["v3_mean_return"] = search_pattern(RE_V3_MEAN_RETURN, float, "")
    telemetry["v3_min_return"] = search_pattern(RE_V3_MIN_RETURN, float, "")
    telemetry["v3_max_return"] = search_pattern(RE_V3_MAX_RETURN, float, "")
    telemetry["v3_final_fast"] = search_pattern(RE_V3_FINAL_FAST, float, "")
    telemetry["v3_final_slow"] = search_pattern(RE_V3_FINAL_SLOW, float, "")
    telemetry["v3_max_drawdown"] = search_pattern(RE_V3_MAX_DRAWDOWN, float, "")
    telemetry["v3_raw_cond_drawdown"] = search_pattern(RE_V3_RAW_DRAWDOWN, int, "")
    telemetry["v3_raw_cond_trend"] = search_pattern(RE_V3_RAW_TREND, int, "")
    telemetry["v3_raw_cond_ceiling"] = search_pattern(RE_V3_RAW_CEILING, int, "")
    telemetry["v3_hyp_events_total"] = search_pattern(RE_V3_HYP_TOTAL, int, "")
    telemetry["v3_hyp_events_drawdown"] = search_pattern(RE_V3_HYP_DRAWDOWN, int, "")
    telemetry["v3_hyp_events_trend"] = search_pattern(RE_V3_HYP_TREND, int, "")
    telemetry["v3_hyp_events_ceiling"] = search_pattern(RE_V3_HYP_CEILING, int, "")

    telemetry["v3_req_trend"] = search_pattern(RE_V3_REQ_TREND, int, "")
    telemetry["v3_req_drawdown"] = search_pattern(RE_V3_REQ_DRAWDOWN, int, "")
    telemetry["v3_req_ceiling"] = search_pattern(RE_V3_REQ_CEILING, int, "")
    telemetry["v3_total_requests"] = search_pattern(RE_V3_TOTAL_REQUESTS, int, "")
    telemetry["v3_executed_restarts"] = search_pattern(RE_V3_EXECUTED_RESTARTS, int, "")
    telemetry["v3_blocked_restarts"] = search_pattern(RE_V3_BLOCKED_RESTARTS, int, "")
    telemetry["v3_max_interval"] = search_pattern(RE_V3_MAX_INTERVAL, int, "")
    telemetry["v3_valid_return_obs"] = search_pattern(RE_V3_VALID_RETURN_OBS, int, "")
    telemetry["v3_active_mean_return"] = search_pattern(RE_V3_ACTIVE_MEAN_RETURN, float, "")
    telemetry["v3_active_final_fast"] = search_pattern(RE_V3_ACTIVE_FINAL_FAST, float, "")
    telemetry["v3_active_final_slow"] = search_pattern(RE_V3_ACTIVE_FINAL_SLOW, float, "")
    telemetry["v3_active_max_dd"] = search_pattern(RE_V3_ACTIVE_MAX_DD, float, "")

    telemetry["fixed_restart_interval"] = search_pattern(RE_FIXED_INTERVAL, int, "")
    telemetry["fixed_restart_requests"] = search_pattern(RE_FIXED_REQUESTS, int, "")
    telemetry["fixed_executed_restarts"] = search_pattern(RE_FIXED_EXECUTED, int, "")
    telemetry["fixed_blocked_restarts"] = search_pattern(RE_FIXED_BLOCKED, int, "")
    telemetry["strategy_adaptation_restarts"] = search_pattern(RE_STRATEGY_ADAPT_RESTARTS, int, "")
    telemetry["fixed_max_interval"] = search_pattern(RE_FIXED_MAX_INTERVAL, int, "")
    telemetry["fixed_cfc_since_restart"] = search_pattern(RE_FIXED_CFC_SINCE, int, "")

    telemetry["num_vars"] = search_pattern(RE_VARS, int)
    telemetry["num_clauses"] = search_pattern(RE_CLAUSES, int)
    telemetry["parse_time_s"] = search_pattern(RE_PARSE_TIME, float)
    telemetry["simp_time_s"] = search_pattern(RE_SIMP_TIME, float)

    return telemetry


def extract_model(stdout_text: str) -> Optional[str]:
    """Extracts all 'v ...' model lines from stdout."""
    model_lines = RE_MODEL_LINES.findall(stdout_text)
    if not model_lines:
        return None
    return "\n".join(model_lines)


def run_single_instance(
    solver_exe: str,
    cnf_file: str,
    timeout_s: float,
    log_dir: str,
    emit_model: bool = True,
    verify_models: bool = True,
    extra_solver_args: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Runs a single solver instance with external timeout enforcement."""
    solver_path = Path(solver_exe).resolve()
    cnf_path = Path(cnf_file).resolve()
    timestamp_str = datetime.now(timezone.utc).isoformat()
    benchmark_name = cnf_path.name
    solver_name = solver_path.stem

    cmd = [str(solver_path)]
    if emit_model:
        cmd.append("-model")
    if extra_solver_args:
        cmd.extend(extra_solver_args)
    cmd.append(str(cnf_path))

    timed_out = False
    exit_code: Any = ""
    stdout_text = ""
    stderr_text = ""

    start_wall = time.perf_counter()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace"
        )
        stdout_text, stderr_text = proc.communicate(timeout=timeout_s)
        exit_code = proc.returncode
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
        stderr_text += f"\nProcess execution error: {e}"

    elapsed_wall = time.perf_counter() - start_wall

    # Determine status
    if timed_out:
        status = "TIMEOUT"
    elif RE_SAT.search(stdout_text) or exit_code == 10:
        status = "SAT"
    elif RE_UNSAT.search(stdout_text) or exit_code == 20:
        status = "UNSAT"
    elif RE_INDET.search(stdout_text) or exit_code == 0:
        status = "INDETERMINATE"
    else:
        status = "ERROR"

    # Save log file
    os.makedirs(log_dir, exist_ok=True)
    clean_ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_filename = f"{benchmark_name}_{solver_name}_{clean_ts}.log"
    log_file_path = Path(log_dir) / log_filename

    with open(log_file_path, "w", encoding="utf-8") as lf:
        lf.write(f"=== BENCHMARK RUN LOG ===\n")
        lf.write(f"Timestamp UTC: {timestamp_str}\n")
        lf.write(f"Command: {' '.join(cmd)}\n")
        lf.write(f"Timeout Limit: {timeout_s}s\n")
        lf.write(f"Timed Out: {timed_out}\n")
        lf.write(f"Exit Code: {exit_code}\n")
        lf.write(f"Status: {status}\n")
        lf.write(f"Wall Time: {elapsed_wall:.6f}s\n\n")
        lf.write("--- STDOUT ---\n")
        lf.write(stdout_text or "(none)\n")
        lf.write("\n--- STDERR ---\n")
        lf.write(stderr_text or "(none)\n")

    # Parse telemetry
    metrics = extract_telemetry(stdout_text)

    # Model verification
    model_verified = "N/A"
    verification_notes = ""

    if status == "SAT":
        raw_model = extract_model(stdout_text)
        if raw_model:
            if verify_models:
                is_valid, msg = verify_model(str(cnf_path), raw_model)
                model_verified = "VERIFIED" if is_valid else "FAILED"
                verification_notes = msg
            else:
                model_verified = "NOT_CHECKED"
                verification_notes = "Verification skipped per configuration."
        else:
            model_verified = "NO_MODEL"
            verification_notes = "SAT reported but no model lines ('v ...') found in output."
    elif status == "UNSAT":
        model_verified = "N/A"
        verification_notes = "UNSAT outcome (requires proof certificate or oracle to verify)."

    record = {
        "run_id": f"{benchmark_name}_{clean_ts}",
        "timestamp_utc": timestamp_str,
        "solver_name": solver_name,
        "solver_path": str(solver_path),
        "benchmark_name": benchmark_name,
        "benchmark_path": str(cnf_path),
        "status": status,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "timeout_limit_s": timeout_s,
        "wall_time_s": round(elapsed_wall, 6),
        "cpu_time_s": metrics.get("cpu_time_s", ""),
        "memory_mb": metrics.get("memory_mb", ""),
        "model_verified": model_verified,
        "verification_notes": verification_notes,
        "conflicts": metrics.get("conflicts", ""),
        "decisions": metrics.get("decisions", ""),
        "propagations": metrics.get("propagations", ""),
        "restarts": metrics.get("restarts", ""),
        "starts": metrics.get("starts", ""),
        "genuine_restarts": metrics.get("genuine_restarts", ""),
        "restart_strategy": metrics.get("restart_strategy", ""),
        "adaptive_restart_requests": metrics.get("adaptive_restart_requests", ""),
        "adaptive_restarts": metrics.get("adaptive_restarts", ""),
        "last_adaptive_score_w": metrics.get("last_adaptive_score_w", ""),
        "last_adaptive_score_global": metrics.get("last_adaptive_score_global", ""),
        "blocked_restarts": metrics.get("blocked_restarts", ""),
        "reduce_db_count": metrics.get("reduce_db_count", ""),
        "removed_clauses": metrics.get("removed_clauses", ""),
        "glue_clauses_dl2": metrics.get("glue_clauses_dl2", ""),
        "reduce_strategy": metrics.get("reduce_strategy", ""),
        "adapt_reduce_calls": metrics.get("adapt_reduce_calls", ""),
        "adapt_clauses_ranked": metrics.get("adapt_clauses_ranked", ""),
        "adapt_clauses_eligible": metrics.get("adapt_clauses_eligible", ""),
        "adapt_clauses_removed": metrics.get("adapt_clauses_removed", ""),
        "adapt_spared_locked": metrics.get("adapt_spared_locked", ""),
        "adapt_spared_binary": metrics.get("adapt_spared_binary", ""),
        "adapt_spared_glue": metrics.get("adapt_spared_glue", ""),
        "adapt_spared_canbedel": metrics.get("adapt_spared_canbedel", ""),
        "adapt_last_retained": metrics.get("adapt_last_retained", ""),
        "adapt_last_avg_ret_lbd": metrics.get("adapt_last_avg_ret_lbd", ""),
        "adapt_last_avg_del_lbd": metrics.get("adapt_last_avg_del_lbd", ""),
        "adapt_reduce_time_s": metrics.get("adapt_reduce_time_s", ""),
        "adapt_postpone_evals": metrics.get("adapt_postpone_evals", ""),
        "adapt_postpone_sat": metrics.get("adapt_postpone_sat", ""),
        "adapt_postpone_inc_db": metrics.get("adapt_postpone_inc_db", ""),
        "v2_quality_fallback": metrics.get("v2_quality_fallback", ""),
        "v2_conflict_ceiling": metrics.get("v2_conflict_ceiling", ""),
        "v2_req_progress": metrics.get("v2_req_progress", ""),
        "v2_req_quality": metrics.get("v2_req_quality", ""),
        "v2_req_ceiling": metrics.get("v2_req_ceiling", ""),
        "v2_total_requests": metrics.get("v2_total_requests", ""),
        "v2_executed_restarts": metrics.get("v2_executed_restarts", ""),
        "v2_blocked_restarts": metrics.get("v2_blocked_restarts", ""),
        "v2_max_interval": metrics.get("v2_max_interval", ""),
        "v3_shadow": metrics.get("v3_shadow", ""),
        "v3_valid_obs": metrics.get("v3_valid_obs", ""),
        "v3_invalid_obs": metrics.get("v3_invalid_obs", ""),
        "v3_mean_return": metrics.get("v3_mean_return", ""),
        "v3_min_return": metrics.get("v3_min_return", ""),
        "v3_max_return": metrics.get("v3_max_return", ""),
        "v3_final_fast": metrics.get("v3_final_fast", ""),
        "v3_final_slow": metrics.get("v3_final_slow", ""),
        "v3_max_drawdown": metrics.get("v3_max_drawdown", ""),
        "v3_raw_cond_drawdown": metrics.get("v3_raw_cond_drawdown", ""),
        "v3_raw_cond_trend": metrics.get("v3_raw_cond_trend", ""),
        "v3_raw_cond_ceiling": metrics.get("v3_raw_cond_ceiling", ""),
        "v3_hyp_events_total": metrics.get("v3_hyp_events_total", ""),
        "v3_hyp_events_drawdown": metrics.get("v3_hyp_events_drawdown", ""),
        "v3_hyp_events_trend": metrics.get("v3_hyp_events_trend", ""),
        "v3_hyp_events_ceiling": metrics.get("v3_hyp_events_ceiling", ""),
        "v3_req_trend": metrics.get("v3_req_trend", ""),
        "v3_req_drawdown": metrics.get("v3_req_drawdown", ""),
        "v3_req_ceiling": metrics.get("v3_req_ceiling", ""),
        "v3_total_requests": metrics.get("v3_total_requests", ""),
        "v3_executed_restarts": metrics.get("v3_executed_restarts", ""),
        "v3_blocked_restarts": metrics.get("v3_blocked_restarts", ""),
        "v3_max_interval": metrics.get("v3_max_interval", ""),
        "v3_valid_return_obs": metrics.get("v3_valid_return_obs", ""),
        "v3_active_mean_return": metrics.get("v3_active_mean_return", ""),
        "v3_active_final_fast": metrics.get("v3_active_final_fast", ""),
        "v3_active_final_slow": metrics.get("v3_active_final_slow", ""),
        "v3_active_max_dd": metrics.get("v3_active_max_dd", ""),
        "fixed_restart_interval": metrics.get("fixed_restart_interval", ""),
        "fixed_restart_requests": metrics.get("fixed_restart_requests", ""),
        "fixed_executed_restarts": metrics.get("fixed_executed_restarts", ""),
        "fixed_blocked_restarts": metrics.get("fixed_blocked_restarts", ""),
        "strategy_adaptation_restarts": metrics.get("strategy_adaptation_restarts", ""),
        "fixed_max_interval": metrics.get("fixed_max_interval", ""),
        "fixed_cfc_since_restart": metrics.get("fixed_cfc_since_restart", ""),
        "num_vars": metrics.get("num_vars", ""),
        "num_clauses": metrics.get("num_clauses", ""),
        "parse_time_s": metrics.get("parse_time_s", ""),
        "simp_time_s": metrics.get("simp_time_s", ""),
        "log_file": str(log_file_path)
    }

    return record


def find_cnf_files(target_path: str) -> List[str]:
    """Locates all .cnf files in target directory or validates a single file."""
    p = Path(target_path)
    if not p.exists():
        raise FileNotFoundError(f"Benchmark path does not exist: {target_path}")

    if p.is_file():
        if p.suffix.lower() == ".cnf":
            return [str(p.resolve())]
        else:
            raise ValueError(f"Specified file is not a .cnf file: {target_path}")

    cnf_files = sorted([str(f.resolve()) for f in p.rglob("*.cnf")])
    if not cnf_files:
        raise FileNotFoundError(f"No .cnf files found in directory: {target_path}")
    return cnf_files


def run_benchmark_suite(
    solver_exe: str,
    benchmarks_path: str,
    timeout_s: float,
    output_csv: str,
    log_dir: str,
    emit_model: bool = True,
    verify_models: bool = True,
    extra_args: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Runs a suite of benchmarks and records results in a CSV file."""
    cnf_files = find_cnf_files(benchmarks_path)
    print(f"[*] Found {len(cnf_files)} CNF benchmark instance(s).")
    print(f"[*] Solver: {solver_exe}")
    print(f"[*] Timeout per instance: {timeout_s}s")
    print(f"[*] Output CSV: {output_csv}")
    print(f"[*] Raw Log Directory: {log_dir}")
    print("-" * 80)

    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    results: List[Dict[str, Any]] = []

    # Write CSV header if file doesn't exist
    file_exists = os.path.isfile(output_csv)
    csv_file = open(output_csv, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    try:
        for idx, cnf_path in enumerate(cnf_files, start=1):
            name = Path(cnf_path).name
            print(f"[{idx}/{len(cnf_files)}] Running: {name} ... ", end="", flush=True)

            record = run_single_instance(
                solver_exe=solver_exe,
                cnf_file=cnf_path,
                timeout_s=timeout_s,
                log_dir=log_dir,
                emit_model=emit_model,
                verify_models=verify_models,
                extra_solver_args=extra_args
            )

            results.append(record)
            writer.writerow(record)
            csv_file.flush()

            status = record["status"]
            wall_t = record["wall_time_s"]
            verified = record["model_verified"]
            conflicts = record["conflicts"]

            info = f"{status} in {wall_t:.3f}s"
            if status == "SAT":
                info += f" (Model: {verified})"
            if conflicts != "":
                info += f" | Conflicts: {conflicts}"

            print(info)

    finally:
        csv_file.close()

    print("-" * 80)
    print(f"[+] All runs completed. Results saved to: {output_csv}")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run automated SAT benchmark experiments and collect telemetry."
    )
    parser.add_argument(
        "--solver",
        default="src/glucose_windows/glucose-simp.exe",
        help="Path to solver executable"
    )
    parser.add_argument(
        "--benchmarks",
        default="benchmarks/smoke_test",
        help="Path to .cnf file or directory of .cnf files"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Timeout per instance in seconds (default: 300)"
    )
    parser.add_argument(
        "--output-csv",
        default="experiments/results/benchmark_results.csv",
        help="Path to output CSV file"
    )
    parser.add_argument(
        "--log-dir",
        default="experiments/results/logs",
        help="Directory to store raw solver execution logs"
    )
    parser.add_argument(
        "--no-model",
        action="store_true",
        help="Do not pass -model to solver"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable automatic SAT model verification"
    )
    parser.add_argument(
        "--extra-args",
        nargs=argparse.REMAINDER,
        help="Extra arguments passed directly to the solver"
    )

    args = parser.parse_args()

    run_benchmark_suite(
        solver_exe=args.solver,
        benchmarks_path=args.benchmarks,
        timeout_s=args.timeout,
        output_csv=args.output_csv,
        log_dir=args.log_dir,
        emit_model=not args.no_model,
        verify_models=not args.no_verify,
        extra_args=args.extra_args
    )


if __name__ == "__main__":
    main()

