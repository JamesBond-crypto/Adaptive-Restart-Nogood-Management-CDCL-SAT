#!/usr/bin/env python3
"""
test_framework.py - Automated Unit & Regression Tests for Experiment Framework

Tests:
1. Valid model verification on test_sat.cnf (Expected: VALID).
2. Invalid model verification on test_sat.cnf (Expected: INVALID / REJECTED).
3. Contradictory model rejection (Expected: REJECTED).
4. Malformed CNF detection (Expected: REJECTED).
5. Controlled timeout enforcement (Expected: TIMEOUT handled cleanly).
6. End-to-end integration run on smoke-test benchmarks.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add experiments folder to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from verify_model import verify_model, parse_dimacs_cnf, parse_model_string, CNFParseError, ModelParseError
from run_experiments import run_single_instance, run_benchmark_suite


def run_tests():
    print("=" * 80)
    print("EXPERIMENT INFRASTRUCTURE UNIT TESTS")
    print("=" * 80)

    sat_cnf = "benchmarks/smoke_test/test_sat.cnf"
    unsat_cnf = "benchmarks/smoke_test/test_unsat.cnf"

    # Test 1: Valid model
    print("[TEST 1] Verifying known satisfying model for test_sat.cnf ... ", end="")
    is_valid, msg = verify_model(sat_cnf, "v -1 2 0")
    assert is_valid is True, f"Failed: {msg}"
    print(f"PASSED ({msg})")

    # Test 2: Invalid (falsifying) model
    print("[TEST 2] Verifying invalid/falsifying model for test_sat.cnf ... ", end="")
    is_valid, msg = verify_model(sat_cnf, "v 1 -2 0")
    assert is_valid is False, "Should have rejected falsifying model!"
    print(f"PASSED (Correctly rejected: {msg})")

    # Test 3: Contradictory model (variable assigned both True and False)
    print("[TEST 3] Testing contradictory model rejection ... ", end="")
    is_valid, msg = verify_model(sat_cnf, "v 1 -1 2 0")
    assert is_valid is False, "Should have rejected contradictory model!"
    assert "Contradictory assignment" in msg
    print(f"PASSED (Correctly rejected: {msg})")

    # Test 4: Malformed CNF detection
    print("[TEST 4] Testing malformed CNF detection ... ", end="")
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as tf:
        tf.write("p cnf 2 2\n1 99 0\n")  # Literal 99 exceeds 2 variables
        temp_cnf = tf.name

    try:
        is_valid, msg = verify_model(temp_cnf, "v 1 2 0")
        assert is_valid is False, "Should have caught out-of-range literal!"
        assert "exceeds declared variable count" in msg
        print(f"PASSED (Correctly caught: {msg})")
    finally:
        if os.path.exists(temp_cnf):
            os.remove(temp_cnf)

    # Test 5: Controlled timeout handling
    print("[TEST 5] Testing controlled external timeout handling ... ", end="")
    # Use python executable running a 5-second sleep, with timeout set to 0.5s
    timeout_test_py = sys.executable
    timeout_extra_args = ["-c", "import time; time.sleep(5)"]

    temp_log_dir = tempfile.mkdtemp(prefix="exp_test_logs_")
    try:
        record = run_single_instance(
            solver_exe=timeout_test_py,
            cnf_file=sat_cnf,
            timeout_s=0.5,
            log_dir=temp_log_dir,
            emit_model=False,
            verify_models=False,
            extra_solver_args=timeout_extra_args
        )
        assert record["timed_out"] is True, "Process should have been flagged as timed out!"
        assert record["status"] == "TIMEOUT", f"Expected status TIMEOUT, got {record['status']}"
        assert record["exit_code"] == "TIMEOUT", f"Expected exit code TIMEOUT, got {record['exit_code']}"
        assert record["wall_time_s"] >= 0.45, "Elapsed wall time should reflect timeout duration!"
        print(f"PASSED (Timed out after {record['wall_time_s']:.3f}s as expected)")
    finally:
        # Cleanup temp log files
        for f in Path(temp_log_dir).glob("*"):
            try:
                os.remove(f)
            except Exception:
                pass
        try:
            os.rmdir(temp_log_dir)
        except Exception:
            pass

    # Test 6: Glucose integration test on smoke benchmarks
    print("[TEST 6] Testing solver integration on smoke test instances ...")
    solver_exe = "src/glucose_windows/glucose-simp.exe"
    csv_out = "experiments/results/test_verification_results.csv"
    log_dir = "experiments/results/test_verification_logs"

    results = run_benchmark_suite(
        solver_exe=solver_exe,
        benchmarks_path="benchmarks/smoke_test",
        timeout_s=10.0,
        output_csv=csv_out,
        log_dir=log_dir,
        emit_model=True,
        verify_models=True
    )

    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    sat_res = next(r for r in results if r["benchmark_name"] == "test_sat.cnf")
    unsat_res = next(r for r in results if r["benchmark_name"] == "test_unsat.cnf")

    assert sat_res["status"] == "SAT", f"Expected SAT, got {sat_res['status']}"
    assert sat_res["exit_code"] == 10, f"Expected 10, got {sat_res['exit_code']}"
    assert sat_res["model_verified"] == "VERIFIED", f"Expected VERIFIED, got {sat_res['model_verified']}"
    assert sat_res["restart_strategy"] == "baseline", f"Expected baseline, got {sat_res['restart_strategy']}"
    assert sat_res["starts"] == 1, f"Expected 1 start, got {sat_res['starts']}"
    assert sat_res["genuine_restarts"] == 0, f"Expected 0 genuine restarts, got {sat_res['genuine_restarts']}"

    assert unsat_res["status"] == "UNSAT", f"Expected UNSAT, got {unsat_res['status']}"
    assert unsat_res["exit_code"] == 20, f"Expected 20, got {unsat_res['exit_code']}"
    assert unsat_res["model_verified"] == "N/A", f"Expected N/A, got {unsat_res['model_verified']}"
    assert unsat_res["reduce_strategy"] == "baseline", f"Expected baseline, got {unsat_res['reduce_strategy']}"
    print("PASSED")

    # Test 7: Telemetry extraction for adaptive reduction
    print("[TEST 7] Verifying parsing of adaptive reduction telemetry ... ", end="")
    from run_experiments import extract_telemetry
    sample_adaptive_stdout = """
c restarts              : 5 (100 conflicts in avg)
c genuine restarts      : 4
c restart strategy      : adaptive (theta=0.60, min_interval=50, warmup=100)
c adaptive restart requests: 12
c adaptive restarts     : 4
c last adaptive score   : 0.7241 (global: 0.6512)
c reduction strategy    : adaptive
c adapt reduce calls    : 3
c adapt clauses ranked  : 15200
c adapt clauses eligible: 7600
c adapt clauses removed : 5400
c adapt spared locked   : 350
c adapt spared binary   : 200
c adapt spared glue     : 1100
c adapt spared canbedel : 550
c adapt last retained   : 9800
c adapt last avg ret LBD: 4.82
c adapt last avg del LBD: 6.15
c adapt reduce time     : 0.0125 s
c nb ReduceDB           : 3
c nb removed Clauses    : 5400
c conflicts             : 4500
c decisions             : 6200
c propagations          : 85000
c Memory used           : 15.50 MB
c CPU time              : 0.45 s
"""
    telem = extract_telemetry(sample_adaptive_stdout)
    assert telem["reduce_strategy"] == "adaptive", f"Expected adaptive, got {telem['reduce_strategy']}"
    assert telem["adapt_reduce_calls"] == 3, f"Expected 3, got {telem['adapt_reduce_calls']}"
    assert telem["adapt_clauses_ranked"] == 15200, f"Expected 15200, got {telem['adapt_clauses_ranked']}"
    assert telem["adapt_clauses_eligible"] == 7600, f"Expected 7600, got {telem['adapt_clauses_eligible']}"
    assert telem["adapt_clauses_removed"] == 5400, f"Expected 5400, got {telem['adapt_clauses_removed']}"
    assert telem["adapt_spared_locked"] == 350, f"Expected 350, got {telem['adapt_spared_locked']}"
    assert telem["adapt_spared_binary"] == 200, f"Expected 200, got {telem['adapt_spared_binary']}"
    assert telem["adapt_spared_glue"] == 1100, f"Expected 1100, got {telem['adapt_spared_glue']}"
    assert telem["adapt_spared_canbedel"] == 550, f"Expected 550, got {telem['adapt_spared_canbedel']}"
    assert telem["adapt_last_retained"] == 9800, f"Expected 9800, got {telem['adapt_last_retained']}"
    assert abs(telem["adapt_last_avg_ret_lbd"] - 4.82) < 1e-4, f"Mismatch ret LBD: {telem['adapt_last_avg_ret_lbd']}"
    assert abs(telem["adapt_last_avg_del_lbd"] - 6.15) < 1e-4, f"Mismatch del LBD: {telem['adapt_last_avg_del_lbd']}"
    assert abs(telem["adapt_reduce_time_s"] - 0.0125) < 1e-4, f"Mismatch reduce time: {telem['adapt_reduce_time_s']}"
    print("PASSED")

    # Test 8: Missing telemetry field handling (e.g. baseline output)
    print("[TEST 8] Verifying graceful handling of missing telemetry fields ... ", end="")
    sample_baseline_stdout = """
c restarts              : 1 (0 conflicts in avg)
c restart strategy      : baseline
c reduction strategy    : baseline
c nb ReduceDB           : 0
c nb removed Clauses    : 0
c conflicts             : 0
c decisions             : 1
c propagations          : 1
c CPU time              : 0 s
"""
    telem_base = extract_telemetry(sample_baseline_stdout)
    assert telem_base["reduce_strategy"] == "baseline"
    assert telem_base["adapt_reduce_calls"] == ""
    assert telem_base["adapt_clauses_ranked"] == ""
    assert telem_base["adapt_clauses_eligible"] == ""
    assert telem_base["adapt_clauses_removed"] == ""
    assert telem_base["adapt_spared_locked"] == ""
    assert telem_base["adapt_spared_binary"] == ""
    assert telem_base["adapt_spared_glue"] == ""
    assert telem_base["adapt_spared_canbedel"] == ""
    assert telem_base["adapt_last_retained"] == ""
    assert telem_base["adapt_last_avg_ret_lbd"] == ""
    assert telem_base["adapt_last_avg_del_lbd"] == ""
    assert telem_base["adapt_reduce_time_s"] == ""
    assert telem_base["v3_shadow"] == ""
    assert telem_base["v3_valid_obs"] == ""
    print("PASSED")

    # Test 9: Solver-error handling on invalid CLI options
    print("[TEST 9] Verifying solver-error handling on invalid CLI arguments ... ", end="")
    rec_err = run_single_instance(
        solver_exe=solver_exe,
        cnf_file=sat_cnf,
        timeout_s=5.0,
        log_dir=log_dir,
        extra_solver_args=["-reduce-strategy=invalid_strat_xyz"]
    )
    assert rec_err["exit_code"] == 1, f"Expected exit code 1, got {rec_err['exit_code']}"
    assert rec_err["status"] in ("ERROR", "CRASH_OR_ERROR"), f"Expected ERROR or CRASH_OR_ERROR, got {rec_err['status']}"
    print(f"PASSED (Correctly flagged status={rec_err['status']}, exit_code={rec_err['exit_code']})")

    # Test 10: V3 shadow telemetry extraction
    print("[TEST 10] Verifying parsing of V3 shadow telemetry ... ", end="")
    sample_v3_stdout = """
c restarts              : 2 (150 conflicts in avg)
c genuine restarts      : 1
c restart strategy      : baseline
c v3 shadow             : enabled
c v3 shadow valid obs   : 300
c v3 shadow invalid obs : 0
c v3 shadow mean return : 0.5421
c v3 shadow min return  : 0.0350
c v3 shadow max return  : 3.1250
c v3 shadow final fast  : 0.4850
c v3 shadow final slow  : 0.5210
c v3 shadow max drawdown: 0.7850
c v3 raw cond drawdown  : 15
c v3 raw cond trend     : 42
c v3 raw cond ceiling   : 0
c v3 hyp event total    : 2
c v3 hyp event drawdown : 1
c v3 hyp event trend    : 2
c v3 hyp event ceiling  : 0
c conflicts             : 300
c decisions             : 500
c propagations          : 6000
"""
    telem_v3 = extract_telemetry(sample_v3_stdout)
    assert telem_v3["v3_shadow"] == "enabled", f"Expected enabled, got {telem_v3['v3_shadow']}"
    assert telem_v3["v3_valid_obs"] == 300, f"Expected 300, got {telem_v3['v3_valid_obs']}"
    assert telem_v3["v3_invalid_obs"] == 0, f"Expected 0, got {telem_v3['v3_invalid_obs']}"
    assert abs(telem_v3["v3_mean_return"] - 0.5421) < 1e-4
    assert abs(telem_v3["v3_min_return"] - 0.0350) < 1e-4
    assert abs(telem_v3["v3_max_return"] - 3.1250) < 1e-4
    assert abs(telem_v3["v3_final_fast"] - 0.4850) < 1e-4
    assert abs(telem_v3["v3_final_slow"] - 0.5210) < 1e-4
    assert abs(telem_v3["v3_max_drawdown"] - 0.7850) < 1e-4
    assert telem_v3["v3_raw_cond_drawdown"] == 15
    assert telem_v3["v3_raw_cond_trend"] == 42
    assert telem_v3["v3_raw_cond_ceiling"] == 0
    assert telem_v3["v3_hyp_events_total"] == 2
    assert telem_v3["v3_hyp_events_drawdown"] == 1
    assert telem_v3["v3_hyp_events_trend"] == 2
    assert telem_v3["v3_hyp_events_ceiling"] == 0
    print("PASSED")

    # Test 11: Active V3 telemetry extraction
    print("[TEST 11] Verifying parsing of Active V3 telemetry ... ", end="")
    sample_v3_active_stdout = """
c restarts              : 12 (120 conflicts in avg)
c genuine restarts      : 11
c restart strategy      : adaptive-v3 (trend=enabled, drawdown=enabled, ceiling=enabled)
c v3 req trend          : 8
c v3 req drawdown       : 3
c v3 req ceiling        : 1
c v3 total requests     : 11
c v3 executed restarts  : 11
c v3 blocked restarts   : 2
c v3 max interval       : 2500
c v3 valid return obs   : 1400
c v3 mean return        : 0.4523
c v3 final fast ewma    : 0.3812
c v3 final slow ewma    : 0.4910
c v3 max observed dd    : 0.8120
c conflicts             : 1400
c decisions             : 2100
c propagations          : 25000
"""
    telem_v3_active = extract_telemetry(sample_v3_active_stdout)
    assert telem_v3_active["v3_req_trend"] == 8
    assert telem_v3_active["v3_req_drawdown"] == 3
    assert telem_v3_active["v3_req_ceiling"] == 1
    assert telem_v3_active["v3_total_requests"] == 11
    assert telem_v3_active["v3_executed_restarts"] == 11
    assert telem_v3_active["v3_blocked_restarts"] == 2
    assert telem_v3_active["v3_max_interval"] == 2500
    assert telem_v3_active["v3_valid_return_obs"] == 1400
    assert abs(telem_v3_active["v3_active_mean_return"] - 0.4523) < 1e-4
    assert abs(telem_v3_active["v3_active_final_fast"] - 0.3812) < 1e-4
    assert abs(telem_v3_active["v3_active_final_slow"] - 0.4910) < 1e-4
    assert abs(telem_v3_active["v3_active_max_dd"] - 0.8120) < 1e-4
    print("PASSED")

    # Test 12: Fixed-Interval & No-Heuristic-Restart telemetry extraction (Step 32)
    print("[TEST 12] Verifying parsing of Fixed-Interval & No-Heuristic telemetry ... ", end="")
    sample_fixed_stdout = """
c restarts              : 4 (10000 conflicts in avg)
c genuine restarts      : 3
c restart strategy      : fixed-interval (interval=10000)
c fixed restart interval: 10000
c fixed restart requests: 3
c fixed executed restarts: 3
c fixed blocked restarts : 0
c strategy adapt restarts: 0
c fixed max interval     : 10050
c fixed cfc since restart: 250
c conflicts             : 30250
c decisions             : 45000
c propagations          : 450000
"""
    telem_fixed = extract_telemetry(sample_fixed_stdout)
    assert telem_fixed["fixed_restart_interval"] == 10000
    assert telem_fixed["fixed_restart_requests"] == 3
    assert telem_fixed["fixed_executed_restarts"] == 3
    assert telem_fixed["fixed_blocked_restarts"] == 0
    assert telem_fixed["strategy_adaptation_restarts"] == 0
    assert telem_fixed["fixed_max_interval"] == 10050
    assert telem_fixed["fixed_cfc_since_restart"] == 250

    sample_no_heur_stdout = """
c restarts              : 1 (100000 conflicts in avg)
c genuine restarts      : 0
c restart strategy      : no-heuristic-restart
c fixed restart interval: 0
c fixed restart requests: 0
c fixed executed restarts: 0
c fixed blocked restarts : 0
c strategy adapt restarts: 0
c fixed max interval     : 54321
c fixed cfc since restart: 54321
c conflicts             : 54321
"""
    telem_no_heur = extract_telemetry(sample_no_heur_stdout)
    assert telem_no_heur["fixed_restart_interval"] == 0
    assert telem_no_heur["fixed_restart_requests"] == 0
    assert telem_no_heur["fixed_executed_restarts"] == 0
    assert telem_no_heur["fixed_max_interval"] == 54321
    assert telem_no_heur["fixed_cfc_since_restart"] == 54321
    print("PASSED")

    print("[+] ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()

