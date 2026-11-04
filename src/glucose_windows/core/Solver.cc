/***************************************************************************************[Solver.cc]
 Glucose -- Copyright (c) 2009-2014, Gilles Audemard, Laurent Simon
                                CRIL - Univ. Artois, France
                                LRI  - Univ. Paris Sud, France (2009-2013)
                                Labri - Univ. Bordeaux, France

 Syrup (Glucose Parallel) -- Copyright (c) 2013-2014, Gilles Audemard, Laurent Simon
                                CRIL - Univ. Artois, France
                                Labri - Univ. Bordeaux, France

Glucose sources are based on MiniSat (see below MiniSat copyrights). Permissions and copyrights of
Glucose (sources until 2013, Glucose 3.0, single core) are exactly the same as Minisat on which it
is based on. (see below).

Glucose-Syrup sources are based on another copyright. Permissions and copyrights for the parallel
version of Glucose-Syrup (the "Software") are granted, free of charge, to deal with the Software
without restriction, including the rights to use, copy, modify, merge, publish, distribute,
sublicence, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

- The above and below copyrights notices and this permission notice shall be included in all
copies or substantial portions of the Software;
- The parallel version of Glucose (all files modified since Glucose 3.0 releases, 2013) cannot
be used in any competitive event (sat competitions/evaluations) without the express permission of
the authors (Gilles Audemard / Laurent Simon). This is also the case for any competitive event
using Glucose Parallel as an embedded SAT engine (single core or not).


--------------- Original Minisat Copyrights

Copyright (c) 2003-2006, Niklas Een, Niklas Sorensson
Copyright (c) 2007-2010, Niklas Sorensson

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 **************************************************************************************************/

#include <math.h>
#include <string.h>

#include "utils/System.h"
#include "mtl/Sort.h"
#include "core/Solver.h"
#include "core/Constants.h"
#include"simp/SimpSolver.h"

using namespace Glucose;


//=================================================================================================
// Statistics
//=================================================================================================



//=================================================================================================
// Options:

static const char *_cat = "CORE";
static const char *_cr = "CORE -- RESTART";
static const char *_cred = "CORE -- REDUCE";
static const char *_cm = "CORE -- MINIMIZE";


static DoubleOption opt_K(_cr, "K", "The constant used to force restart", 0.8, DoubleRange(0, false, 1, false));
static DoubleOption opt_R(_cr, "R", "The constant used to block restart", 1.4, DoubleRange(1, false, 5, false));
static IntOption opt_size_lbd_queue(_cr, "szLBDQueue", "The size of moving average for LBD (restarts)", 50, IntRange(10, INT32_MAX));
static IntOption opt_size_trail_queue(_cr, "szTrailQueue", "The size of moving average for trail (block restarts)", 5000, IntRange(10, INT32_MAX));
static StringOption opt_restart_strategy(_cr, "restart-strategy", "Restart strategy: baseline, adaptive, adaptive-v2, adaptive-v3, fixed-interval, no-heuristic-restart, adaptive-qre, adaptive-qre-gated, or portfolio-mab", "baseline");
static IntOption    opt_fixed_restart_interval(_cr, "fixed-restart-interval", "Conflict interval for fixed-interval restart comparator", 10000, IntRange(1, INT32_MAX));
static DoubleOption opt_adapt_theta(_cr, "adapt-theta", "Degradation threshold for adaptive restart", 0.60, DoubleRange(0.01, false, 1.0, false));
static IntOption opt_adapt_min_interval(_cr, "adapt-min-interval", "Minimum conflicts between adaptive restarts", 50, IntRange(1, INT32_MAX));
static IntOption opt_adapt_warmup(_cr, "adapt-warmup", "Warmup conflicts before adaptive restarts can fire", 100, IntRange(1, INT32_MAX));

// Adaptive Restart V2 Options
static BoolOption   opt_v2_quality_fallback(_cr, "v2-quality-fallback", "Enable LBD-quality distress fallback for adaptive-v2 restart", true);
static BoolOption   opt_v2_conflict_ceiling(_cr, "v2-conflict-ceiling", "Enable maximum conflict interval ceiling for adaptive-v2 restart", true);
static IntOption    opt_v2_max_conflicts(_cr, "v2-max-conflicts", "Maximum conflicts allowed without a restart in adaptive-v2", 2500, IntRange(100, INT32_MAX));
static DoubleOption opt_v2_fallback_lbd_k(_cr, "v2-fallback-lbd-k", "LBD moving average multiplier for quality fallback in adaptive-v2", 0.80, DoubleRange(0.01, false, 5.0, false));

// Finance-Inspired Adaptive Restart V3 Options
static BoolOption   opt_v3_trend(_cr, "v3-trend", "Enable trend deterioration trigger in adaptive-v3 restart", true);
static BoolOption   opt_v3_drawdown(_cr, "v3-drawdown", "Enable sustained drawdown trigger in adaptive-v3 restart", true);
static BoolOption   opt_v3_ceiling(_cr, "v3-ceiling", "Enable anti-starvation conflict ceiling trigger in adaptive-v3 restart", true);
static BoolOption   opt_v3_shadow(_cr, "v3-shadow", "Enable shadow-mode instrumentation for Finance-Inspired Restart V3 (diagnostic only, does not execute restarts)", false);
static BoolOption   opt_restart_trace(_cr, "restart-trace", "Enable opt-in diagnostic event trace for actual restarts", false);

// Quantitative Risk Engine (QRE) Shadow-Mode Options (Step 38)
static BoolOption   opt_qre_shadow(_cr, "qre-shadow", "Enable Quantitative Risk Engine shadow-mode telemetry (diagnostic only, does not execute restarts)", false);

// Portfolio-MAB Options (Step 44)
static BoolOption   opt_portfolio_shadow(_cr, "portfolio-shadow", "Enable Portfolio-MAB shadow-mode telemetry (diagnostic only, does not execute restarts)", false);
static DoubleOption opt_mab_gamma(_cr, "mab-gamma", "Discount factor for Portfolio-MAB rewards", 0.95, DoubleRange(0.01, false, 0.999, false));
static DoubleOption opt_mab_c_explore(_cr, "mab-c-explore", "Exploration coefficient for Portfolio-MAB", 0.40, DoubleRange(0.0, true, 10.0, true));
static IntOption    opt_mab_max_postpone(_cr, "mab-max-postpone", "Maximum conflicts to postpone restart in Arm 1", 500, IntRange(10, INT32_MAX));

static IntOption opt_first_reduce_db(_cred, "firstReduceDB", "The number of conflicts before the first reduce DB (or the size of leernts if chanseok is used)",
                                     2000, IntRange(0, INT32_MAX));
static IntOption opt_inc_reduce_db(_cred, "incReduceDB", "Increment for reduce DB", 300, IntRange(0, INT32_MAX));
static IntOption opt_spec_inc_reduce_db(_cred, "specialIncReduceDB", "Special increment for reduce DB", 1000, IntRange(0, INT32_MAX));
static IntOption opt_lb_lbd_frozen_clause(_cred, "minLBDFrozenClause", "Protect clauses if their LBD decrease and is lower than (for one turn)", 30,
                                          IntRange(0, INT32_MAX));
static BoolOption opt_chanseok_hack(_cred, "chanseok",
                                    "Use Chanseok Oh strategy for LBD (keep all LBD<=co and remove half of firstreduceDB other learnt clauses", false);
static IntOption opt_chanseok_limit(_cred, "co", "Chanseok Oh: all learnt clauses with LBD<=co are permanent", 5, IntRange(2, INT32_MAX));
static StringOption opt_reduce_strategy(_cred, "reduce-strategy", "Clause reduction strategy: baseline, adaptive, or adaptive-fixed", "baseline");


static IntOption opt_lb_size_minimzing_clause(_cm, "minSizeMinimizingClause", "The min size required to minimize clause", 30, IntRange(3, INT32_MAX));
static IntOption opt_lb_lbd_minimzing_clause(_cm, "minLBDMinimizingClause", "The min LBD required to minimize clause", 6, IntRange(3, INT32_MAX));
static BoolOption opt_lcm(_cm, "lcm", "Use inprocessing vivif (ijcai17 paper)", true);
static BoolOption opt_lcm_update_lbd(_cm, "lcm-update", "Updates LBD when doing LCM", false);

static DoubleOption opt_var_decay(_cat, "var-decay", "The variable activity decay factor (starting point)", 0.8, DoubleRange(0, false, 1, false));
static DoubleOption opt_max_var_decay(_cat, "max-var-decay", "The variable activity decay factor", 0.95, DoubleRange(0, false, 1, false));
static DoubleOption opt_clause_decay(_cat, "cla-decay", "The clause activity decay factor", 0.999, DoubleRange(0, false, 1, false));
static DoubleOption opt_random_var_freq(_cat, "rnd-freq", "The frequency with which the decision heuristic tries to choose a random variable", 0,
                                        DoubleRange(0, true, 1, true));
static DoubleOption opt_random_seed(_cat, "rnd-seed", "Used by the random variable selection", 91648253, DoubleRange(0, false, HUGE_VAL, false));
static IntOption opt_ccmin_mode(_cat, "ccmin-mode", "Controls conflict clause minimization (0=none, 1=basic, 2=deep)", 2, IntRange(0, 2));
static IntOption opt_phase_saving(_cat, "phase-saving", "Controls the level of phase saving (0=none, 1=limited, 2=full)", 2, IntRange(0, 2));
static BoolOption opt_rnd_init_act(_cat, "rnd-init", "Randomize the initial activity", false);
static DoubleOption opt_garbage_frac(_cat, "gc-frac", "The fraction of wasted memory allowed before a garbage collection is triggered", 0.20,
                                     DoubleRange(0, false, HUGE_VAL, false));
static BoolOption opt_glu_reduction(_cat, "gr", "glucose strategy to fire clause database reduction (must be false to fire Chanseok strategy)", true);
static BoolOption opt_luby_restart(_cat, "luby", "Use the Luby restart sequence", false);
static DoubleOption opt_restart_inc(_cat, "rinc", "Restart interval increase factor", 2, DoubleRange(1, false, HUGE_VAL, false));
static IntOption opt_luby_restart_factor(_cred, "luby-factor", "Luby restart factor", 100, IntRange(1, INT32_MAX));

static IntOption opt_randomize_phase_on_restarts(_cat, "phase-restart",
                                                 "The amount of randomization for the phase at each restart (0=none, 1=first branch, 2=first branch (no bad clauses), 3=first branch (only initial clauses)",
                                                 0, IntRange(0, 3));
static BoolOption opt_fixed_randomize_phase_on_restarts(_cat, "fix-phas-rest", "Fixes the first 7 levels at random phase", false);

static BoolOption opt_adapt(_cat, "adapt", "Adapt dynamically stategies after 100000 conflicts", true);

static BoolOption opt_forceunsat(_cat,"forceunsat","Force the phase for UNSAT",true);
//=================================================================================================
// Constructor/Destructor:

Solver::Solver() :

// Parameters (user settable):
//
verbosity(0)
, showModel(0)
, K(opt_K)
, R(opt_R)
, sizeLBDQueue(opt_size_lbd_queue)
, sizeTrailQueue(opt_size_trail_queue)
, firstReduceDB(opt_first_reduce_db)
, incReduceDB(opt_chanseok_hack ? 0 : opt_inc_reduce_db)
, specialIncReduceDB(opt_chanseok_hack ? 0 : opt_spec_inc_reduce_db)
, lbLBDFrozenClause(opt_lb_lbd_frozen_clause)
, chanseokStrategy(opt_chanseok_hack)
, coLBDBound (opt_chanseok_limit)
, lbSizeMinimizingClause(opt_lb_size_minimzing_clause)
, lbLBDMinimizingClause(opt_lb_lbd_minimzing_clause)
, useLCM(opt_lcm)
, LCMUpdateLBD (opt_lcm_update_lbd)
, var_decay(opt_var_decay)
, max_var_decay(opt_max_var_decay)
, clause_decay(opt_clause_decay)
, random_var_freq(opt_random_var_freq)
, random_seed(opt_random_seed)
, ccmin_mode(opt_ccmin_mode)
, phase_saving(opt_phase_saving)
, rnd_pol(false)
, rnd_init_act(opt_rnd_init_act)
, randomizeFirstDescent(false)
, garbage_frac(opt_garbage_frac)
, certifiedOutput(NULL)
, certifiedUNSAT(false) // Not in the first parallel version
, vbyte(false)
, panicModeLastRemoved(0), panicModeLastRemovedShared(0)
, useUnaryWatched(false)
, promoteOneWatchedClause(true)
,solves(0),starts(0),decisions(0),propagations(0),conflicts(0),conflictsRestarts(0)
, curRestart(1)
, glureduce(opt_glu_reduction)
, restart_inc(opt_restart_inc)
, luby_restart(opt_luby_restart)
, adaptStrategies(opt_adapt)
, luby_restart_factor(opt_luby_restart_factor)
, randomize_on_restarts(opt_randomize_phase_on_restarts)
, fixed_randomize_on_restarts(opt_fixed_randomize_phase_on_restarts)
, newDescent(0)
, randomDescentAssignments(0)
, forceUnsatOnNewDescent(opt_forceunsat)

, ok(true)
, cla_inc(1)
, var_inc(1)
, watches(WatcherDeleted(ca))
, watchesBin(WatcherDeleted(ca))
, unaryWatches(WatcherDeleted(ca))
, qhead(0)
, simpDB_assigns(-1)
, simpDB_props(0)
, order_heap(VarOrderLt(activity))
, progress_estimate(0)
, remove_satisfied(true)
,lastLearntClause(CRef_Undef)
// Resource constraints:
//
, conflict_budget(-1)
, propagation_budget(-1)
, asynch_interrupt(false)
, incremental(false)
, nbVarsInitialFormula(INT32_MAX)
, totalTime4Sat(0.)
, totalTime4Unsat(0.)
, nbSatCalls(0)
, nbUnsatCalls(0)
        // simplify
, performLCM(1)
{
    MYFLAG = 0;
    // Initialize only first time. Useful for incremental solving (not in // version), useless otherwise
    // Kept here for simplicity
    lbdQueue.initSize(sizeLBDQueue);
    trailQueue.initSize(sizeTrailQueue);
    sumLBD = 0;
    nbclausesbeforereduce = firstReduceDB;
    stats.growTo(coreStatsSize, 0);

    initAdaptiveRestartController();
    initAdaptiveRestartV2();
    initAdaptiveRestartV3();
    initFixedRestartController();
    const char* strat = (const char*)opt_restart_strategy;
    if(strat == NULL || strcmp(strat, "baseline") == 0) {
        restart_strategy = RESTART_BASELINE;
        adaptive_restart_mode = false;
    } else if(strcmp(strat, "adaptive") == 0) {
        restart_strategy = RESTART_ADAPTIVE_V1;
        adaptive_restart_mode = true;
    } else if(strcmp(strat, "adaptive-v2") == 0) {
        restart_strategy = RESTART_ADAPTIVE_V2;
        adaptive_restart_mode = true;
    } else if(strcmp(strat, "adaptive-v3") == 0) {
        restart_strategy = RESTART_ADAPTIVE_V3;
        adaptive_restart_mode = true;
    } else if(strcmp(strat, "fixed-interval") == 0) {
        restart_strategy = RESTART_FIXED_INTERVAL;
        adaptive_restart_mode = false;
    } else if(strcmp(strat, "no-heuristic-restart") == 0) {
        restart_strategy = RESTART_NO_HEURISTIC;
        adaptive_restart_mode = false;
    } else if(strcmp(strat, "adaptive-qre") == 0) {
        restart_strategy = RESTART_ADAPTIVE_QRE;
        adaptive_restart_mode = false;
    } else if(strcmp(strat, "adaptive-qre-gated") == 0) {
        restart_strategy = RESTART_ADAPTIVE_QRE_GATED;
        adaptive_restart_mode = false;
    } else if(strcmp(strat, "portfolio-mab") == 0) {
        restart_strategy = RESTART_PORTFOLIO_MAB;
        adaptive_restart_mode = false;
    } else {
        fprintf(stderr, "ERROR! Invalid restart strategy \"%s\". Valid options are: 'baseline', 'adaptive', 'adaptive-v2', 'adaptive-v3', 'fixed-interval', 'no-heuristic-restart', 'adaptive-qre', 'adaptive-qre-gated', 'portfolio-mab'.\n", strat);
        exit(1);
    }
    fixed_restart_interval = opt_fixed_restart_interval;
    restart_trace = opt_restart_trace;
    if(fixed_restart_interval < 1) {
        fprintf(stderr, "ERROR! Invalid value for -fixed-restart-interval: must be >= 1.\n");
        exit(1);
    }
    adapt_theta = opt_adapt_theta;
    if(!isfinite(adapt_theta) || adapt_theta <= 0.0 || adapt_theta > 1.0) {
        fprintf(stderr, "ERROR! Invalid value for -adapt-theta: must be a finite number in (0, 1].\n");
        exit(1);
    }
    adapt_min_interval = opt_adapt_min_interval;
    if(adapt_min_interval < 1) {
        fprintf(stderr, "ERROR! Invalid value for -adapt-min-interval: must be >= 1.\n");
        exit(1);
    }
    adapt_warmup = opt_adapt_warmup;
    if(adapt_warmup < 1) {
        fprintf(stderr, "ERROR! Invalid value for -adapt-warmup: must be >= 1.\n");
        exit(1);
    }

    v2_quality_fallback = opt_v2_quality_fallback;
    v2_conflict_ceiling = opt_v2_conflict_ceiling;
    v2_max_conflicts = opt_v2_max_conflicts;
    if(v2_max_conflicts < 100) {
        fprintf(stderr, "ERROR! Invalid value for -v2-max-conflicts: must be >= 100.\n");
        exit(1);
    }
    v2_fallback_lbd_k = opt_v2_fallback_lbd_k;
    if(!isfinite(v2_fallback_lbd_k) || v2_fallback_lbd_k <= 0.0) {
        fprintf(stderr, "ERROR! Invalid value for -v2-fallback-lbd-k: must be a positive finite number.\n");
        exit(1);
    }

    v3_opt_trend = opt_v3_trend;
    v3_opt_drawdown = opt_v3_drawdown;
    v3_opt_ceiling = opt_v3_ceiling;
    v3_shadow_mode = opt_v3_shadow;
    initV3Shadow();

    qre_shadow_mode = opt_qre_shadow;
    initQREShadow();
    initQREActive();

    portfolio_shadow_mode = opt_portfolio_shadow;
    initPortfolioMAB();
    mab_gamma = opt_mab_gamma;
    mab_c_explore = opt_mab_c_explore;
    mab_max_postpone_conflicts = (uint64_t)opt_mab_max_postpone;

    initAdaptiveReduceController();
    const char* red_strat = (const char*)opt_reduce_strategy;
    if(red_strat == NULL || strcmp(red_strat, "baseline") == 0) {
        adaptive_reduce_mode = false;
        reduce_strategy_mode = REDUCE_BASELINE;
    } else if(strcmp(red_strat, "adaptive") == 0) {
        adaptive_reduce_mode = true;
        reduce_strategy_mode = REDUCE_ADAPTIVE;
    } else if(strcmp(red_strat, "adaptive-fixed") == 0) {
        adaptive_reduce_mode = true;
        reduce_strategy_mode = REDUCE_ADAPTIVE_FIXED;
    } else {
        fprintf(stderr, "ERROR! Invalid reduce strategy \"%s\". Valid options are: 'baseline', 'adaptive', 'adaptive-fixed'.\n", red_strat);
        exit(1);
    }
}

//-------------------------------------------------------
// Special constructor used for cloning solvers
//-------------------------------------------------------

Solver::Solver(const Solver &s) :
  verbosity(s.verbosity)
, showModel(s.showModel)
, K(s.K)
, R(s.R)
, sizeLBDQueue(s.sizeLBDQueue)
, sizeTrailQueue(s.sizeTrailQueue)
, firstReduceDB(s.firstReduceDB)
, incReduceDB(s.incReduceDB)
, specialIncReduceDB(s.specialIncReduceDB)
, lbLBDFrozenClause(s.lbLBDFrozenClause)
, chanseokStrategy(opt_chanseok_hack)
, coLBDBound (opt_chanseok_limit)
, lbSizeMinimizingClause(s.lbSizeMinimizingClause)
, lbLBDMinimizingClause(s.lbLBDMinimizingClause)
, useLCM(s.useLCM)
, LCMUpdateLBD (s.LCMUpdateLBD)
, var_decay(s.var_decay)
, max_var_decay(s.max_var_decay)
, clause_decay(s.clause_decay)
, random_var_freq(s.random_var_freq)
, random_seed(s.random_seed)
, ccmin_mode(s.ccmin_mode)
, phase_saving(s.phase_saving)
, rnd_pol(s.rnd_pol)
, rnd_init_act(s.rnd_init_act)
, randomizeFirstDescent(s.randomizeFirstDescent)
, garbage_frac(s.garbage_frac)
, certifiedOutput(NULL)
, certifiedUNSAT(false) // Not in the first parallel version
, panicModeLastRemoved(s.panicModeLastRemoved), panicModeLastRemovedShared(s.panicModeLastRemovedShared)
, useUnaryWatched(s.useUnaryWatched)
, promoteOneWatchedClause(s.promoteOneWatchedClause)
// Statistics: (formerly in 'SolverStats')
//
,solves(0),starts(0),decisions(0),propagations(0),conflicts(0),conflictsRestarts(0)

, curRestart(s.curRestart)
, glureduce(s.glureduce)
, restart_inc(s.restart_inc)
, luby_restart(s.luby_restart)
, adaptStrategies(s.adaptStrategies)
, luby_restart_factor(s.luby_restart_factor)
, randomize_on_restarts(s.randomize_on_restarts)
, fixed_randomize_on_restarts(s.fixed_randomize_on_restarts)
, newDescent(s.newDescent)
, randomDescentAssignments(s.randomDescentAssignments)
, forceUnsatOnNewDescent(s.forceUnsatOnNewDescent)
, ok(true)
, cla_inc(s.cla_inc)
, var_inc(s.var_inc)
, watches(WatcherDeleted(ca))
, watchesBin(WatcherDeleted(ca))
, unaryWatches(WatcherDeleted(ca))
, qhead(s.qhead)
, simpDB_assigns(s.simpDB_assigns)
, simpDB_props(s.simpDB_props)
, order_heap(VarOrderLt(activity))
, progress_estimate(s.progress_estimate)
, remove_satisfied(s.remove_satisfied)
,lastLearntClause(CRef_Undef)
// Resource constraints:
//
, conflict_budget(s.conflict_budget)
, propagation_budget(s.propagation_budget)
, asynch_interrupt(s.asynch_interrupt)
, incremental(s.incremental)
, nbVarsInitialFormula(s.nbVarsInitialFormula)
, totalTime4Sat(s.totalTime4Sat)
, totalTime4Unsat(s.totalTime4Unsat)
, nbSatCalls(s.nbSatCalls)
, nbUnsatCalls(s.nbUnsatCalls)
, performLCM(s.performLCM)
{
    // Copy clauses.
    s.ca.copyTo(ca);
    ca.extra_clause_field = s.ca.extra_clause_field;

    // Initialize  other variables
    MYFLAG = 0;
    // Initialize only first time. Useful for incremental solving (not in // version), useless otherwise
    // Kept here for simplicity
    sumLBD = s.sumLBD;
    nbclausesbeforereduce = s.nbclausesbeforereduce;

    // Copy all search vectors
    s.watches.copyTo(watches);
    s.watchesBin.copyTo(watchesBin);
    s.unaryWatches.copyTo(unaryWatches);
    s.assigns.memCopyTo(assigns);
    s.vardata.memCopyTo(vardata);
    s.activity.memCopyTo(activity);
    s.seen.memCopyTo(seen);
    s.permDiff.memCopyTo(permDiff);
    s.polarity.memCopyTo(polarity);
    s.decision.memCopyTo(decision);
    s.trail.memCopyTo(trail);
    s.order_heap.copyTo(order_heap);
    s.clauses.memCopyTo(clauses);
    s.learnts.memCopyTo(learnts);
    s.permanentLearnts.memCopyTo(permanentLearnts);
    s.permanentLearntsReduced.memCopyTo(permanentLearntsReduced);

    s.lbdQueue.copyTo(lbdQueue);
    s.trailQueue.copyTo(trailQueue);
    s.forceUNSAT.copyTo(forceUNSAT);
    s.stats.copyTo(stats);

    restart_strategy = s.restart_strategy;
    adaptive_restart_mode = s.adaptive_restart_mode;
    reduce_strategy_mode = s.reduce_strategy_mode;
    adaptive_reduce_mode = s.adaptive_reduce_mode;
    adapt_reduce_calls = s.adapt_reduce_calls;
    adapt_clauses_considered = s.adapt_clauses_considered;
    adapt_clauses_eligible = s.adapt_clauses_eligible;
    adapt_clauses_removed = s.adapt_clauses_removed;
    adapt_spared_locked = s.adapt_spared_locked;
    adapt_spared_binary = s.adapt_spared_binary;
    adapt_spared_glue = s.adapt_spared_glue;
    adapt_spared_canbedel = s.adapt_spared_canbedel;
    adapt_last_retained = s.adapt_last_retained;
    adapt_last_avg_retained_lbd = s.adapt_last_avg_retained_lbd;
    adapt_last_avg_deleted_lbd = s.adapt_last_avg_deleted_lbd;
    adapt_reduce_time = s.adapt_reduce_time;
    adapt_postpone_evals = s.adapt_postpone_evals;
    adapt_postpone_satisfied = s.adapt_postpone_satisfied;
    adapt_postpone_inc_db = s.adapt_postpone_inc_db;
    adapt_theta = s.adapt_theta;
    adapt_min_interval = s.adapt_min_interval;
    adapt_warmup = s.adapt_warmup;
    adaptive_restarts = s.adaptive_restarts;
    adaptive_restart_requests = s.adaptive_restart_requests;
    last_adapt_score_w = s.last_adapt_score_w;
    last_adapt_score_global = s.last_adapt_score_global;
    adapt_last_props = s.adapt_last_props;
    adapt_win_head = s.adapt_win_head;
    adapt_win_size = s.adapt_win_size;
    for(int i = 0; i < ADAPT_WIN_CAPACITY; i++) {
        adapt_win_props[i] = s.adapt_win_props[i];
        adapt_win_levels[i] = s.adapt_win_levels[i];
    }
    adapt_conflicts_since_restart = s.adapt_conflicts_since_restart;
    adapt_global_sum_props = s.adapt_global_sum_props;
    adapt_global_mean_level = s.adapt_global_mean_level;
    adapt_global_m2_level = s.adapt_global_m2_level;

    v2_quality_fallback = s.v2_quality_fallback;
    v2_conflict_ceiling = s.v2_conflict_ceiling;
    v2_max_conflicts = s.v2_max_conflicts;
    v2_fallback_lbd_k = s.v2_fallback_lbd_k;
    v2_req_progress = s.v2_req_progress;
    v2_req_quality = s.v2_req_quality;
    v2_req_ceiling = s.v2_req_ceiling;
    v2_total_requests = s.v2_total_requests;
    v2_executed_restarts = s.v2_executed_restarts;
    v2_blocked_restarts = s.v2_blocked_restarts;
    v2_max_observed_interval = s.v2_max_observed_interval;

    v3_opt_trend = s.v3_opt_trend;
    v3_opt_drawdown = s.v3_opt_drawdown;
    v3_opt_ceiling = s.v3_opt_ceiling;
    v3_req_trend = s.v3_req_trend;
    v3_req_drawdown = s.v3_req_drawdown;
    v3_req_ceiling = s.v3_req_ceiling;
    v3_total_requests = s.v3_total_requests;
    v3_executed_restarts = s.v3_executed_restarts;
    v3_blocked_restarts = s.v3_blocked_restarts;
    v3_max_observed_interval = s.v3_max_observed_interval;
    v3_conflicts_since_restart = s.v3_conflicts_since_restart;

    v3_shadow_mode = s.v3_shadow_mode;
    v3_valid_obs = s.v3_valid_obs;
    v3_invalid_obs = s.v3_invalid_obs;
    v3_sum_return = s.v3_sum_return;
    v3_min_return = s.v3_min_return;
    v3_max_return = s.v3_max_return;
    v3_ewma_fast = s.v3_ewma_fast;
    v3_ewma_slow = s.v3_ewma_slow;
    v3_hwm = s.v3_hwm;
    v3_max_drawdown = s.v3_max_drawdown;
    v3_consec_drawdown = s.v3_consec_drawdown;
    v3_conflicts_since_actual_restart = s.v3_conflicts_since_actual_restart;
    v3_conflicts_since_hyp_event = s.v3_conflicts_since_hyp_event;
    v3_raw_cond_drawdown = s.v3_raw_cond_drawdown;
    v3_raw_cond_trend = s.v3_raw_cond_trend;
    v3_raw_cond_ceiling = s.v3_raw_cond_ceiling;
    v3_hyp_events_total = s.v3_hyp_events_total;
    v3_hyp_events_drawdown = s.v3_hyp_events_drawdown;
    v3_hyp_events_trend = s.v3_hyp_events_trend;
    v3_hyp_events_ceiling = s.v3_hyp_events_ceiling;
    v3_last_props = s.v3_last_props;


}


Solver::~Solver() {
}


/****************************************************************
 Certified UNSAT proof in binary format
****************************************************************/


void Solver::write_char(unsigned char ch) {
    if(putc((int) ch, certifiedOutput) == EOF)
        exit(1);
}


void Solver::write_lit(int n) {
    for(; n > 127; n >>= 7)
        write_char(128 | (n & 127));
    write_char(n);
}

/****************************************************************
 Set the incremental mode
****************************************************************/

// This function set the incremental mode to true.
// You can add special code for this mode here.

void Solver::setIncrementalMode() {
#ifdef INCREMENTAL
    incremental = true;
#else
    fprintf(stderr, "c Trying to set incremental mode, but not compiled properly for this.\n");
    exit(1);
#endif
}


// Number of variables without selectors
void Solver::initNbInitialVars(int nb) {
    nbVarsInitialFormula = nb;
}


bool Solver::isIncremental() {
    return incremental;
}


//=================================================================================================
// Minor methods:


// Creates a new SAT variable in the solver. If 'decision' is cleared, variable will not be
// used as a decision variable (NOTE! This has effects on the meaning of a SATISFIABLE result).
//

Var Solver::newVar(bool sign, bool dvar) {
    int v = nVars();
    watches.init(mkLit(v, false));
    watches.init(mkLit(v, true));
    watchesBin.init(mkLit(v, false));
    watchesBin.init(mkLit(v, true));
    unaryWatches.init(mkLit(v, false));
    unaryWatches.init(mkLit(v, true));
    assigns.push(l_Undef);
    vardata.push(mkVarData(CRef_Undef, 0));
    activity.push(rnd_init_act ? drand(random_seed) * 0.00001 : 0);
    seen.push(0);
    permDiff.push(0);
    polarity.push(sign);
    forceUNSAT.push(0);
    decision.push();
    trail.capacity(v + 1);
    setDecisionVar(v, dvar);


    return v;
}


bool Solver::addClause_(vec <Lit> &ps) {

    assert(decisionLevel() == 0);
    if(!ok) return false;

    // Check if clause is satisfied and remove false/duplicate literals:
    sort(ps);

    vec <Lit> oc;
    oc.clear();

    Lit p;
    int i, j, flag = 0;
    if(certifiedUNSAT) {
        for(i = j = 0, p = lit_Undef; i < ps.size(); i++) {
            oc.push(ps[i]);
            if(value(ps[i]) == l_True || ps[i] == ~p || value(ps[i]) == l_False)
                flag = 1;
        }
    }

    for(i = j = 0, p = lit_Undef; i < ps.size(); i++)
        if(value(ps[i]) == l_True || ps[i] == ~p)
            return true;
        else if(value(ps[i]) != l_False && ps[i] != p)
            ps[j++] = p = ps[i];
    ps.shrink(i - j);

    if(flag && (certifiedUNSAT)) {
        addToDrat(ps,true);
        addToDrat(oc, false);
    }


    if(ps.size() == 0)
        return ok = false;
    else if(ps.size() == 1) {
        uncheckedEnqueue(ps[0]);
        return ok = (propagate() == CRef_Undef);
    } else {
        CRef cr = ca.alloc(ps, false);
        clauses.push(cr);
        attachClause(cr);

    }

    return true;
}


void Solver::attachClause(CRef cr) {
    const Clause &c = ca[cr];

    assert(c.size() > 1);
    if(c.size() == 2) {
        watchesBin[~c[0]].push(Watcher(cr, c[1]));
        watchesBin[~c[1]].push(Watcher(cr, c[0]));
    } else {
        watches[~c[0]].push(Watcher(cr, c[1]));
        watches[~c[1]].push(Watcher(cr, c[0]));
    }
    if(c.learnt()) stats[learnts_literals] += c.size();
    else stats[clauses_literals] += c.size();
}


void Solver::attachClausePurgatory(CRef cr) {
    const Clause &c = ca[cr];

    assert(c.size() > 1);
    unaryWatches[~c[0]].push(Watcher(cr, c[1]));

}


void Solver::detachClause(CRef cr, bool strict) {
    const Clause &c = ca[cr];

    assert(c.size() > 1);
    if(c.size() == 2) {
        if(strict) {
            remove(watchesBin[~c[0]], Watcher(cr, c[1]));
            remove(watchesBin[~c[1]], Watcher(cr, c[0]));
        } else {
            // Lazy detaching: (NOTE! Must clean all watcher lists before garbage collecting this clause)
            watchesBin.smudge(~c[0]);
            watchesBin.smudge(~c[1]);
        }
    } else {
        if(strict) {
            remove(watches[~c[0]], Watcher(cr, c[1]));
            remove(watches[~c[1]], Watcher(cr, c[0]));
        } else {
            // Lazy detaching: (NOTE! Must clean all watcher lists before garbage collecting this clause)
            watches.smudge(~c[0]);
            watches.smudge(~c[1]);
        }
    }
    if(c.learnt()) stats[learnts_literals] -= c.size();
    else stats[clauses_literals] -= c.size();
}


// The purgatory is the 1-Watched scheme for imported clauses

void Solver::detachClausePurgatory(CRef cr, bool strict) {
    const Clause &c = ca[cr];

    assert(c.size() > 1);
    if(strict)
        remove(unaryWatches[~c[0]], Watcher(cr, c[1]));
    else
        unaryWatches.smudge(~c[0]);
}


void Solver::removeClause(CRef cr, bool inPurgatory) {

    Clause &c = ca[cr];

    if(certifiedUNSAT) {
        addToDrat(c, false);
    }

    if(inPurgatory)
        detachClausePurgatory(cr);
    else
        detachClause(cr);
    // Don't leave pointers to free'd memory!
    if(locked(c)) vardata[var(c[0])].reason = CRef_Undef;
    c.mark(1);
    ca.free(cr);
}


bool Solver::satisfied(const Clause &c) const {
#ifdef INCREMENTAL
    if(incremental)
        return (value(c[0]) == l_True) || (value(c[1]) == l_True);
#endif

    // Default mode
    for(int i = 0; i < c.size(); i++)
        if(value(c[i]) == l_True)
            return true;
    return false;
}



/******************************************************************
 * Minimisation with binary reolution
 ******************************************************************/
void Solver::minimisationWithBinaryResolution(vec <Lit> &out_learnt) {

    // Find the LBD measure
    unsigned int lbd = computeLBD(out_learnt);
    Lit p = ~out_learnt[0];

    if(lbd <= lbLBDMinimizingClause) {
        MYFLAG++;

        for(int i = 1; i < out_learnt.size(); i++) {
            permDiff[var(out_learnt[i])] = MYFLAG;
        }

        vec <Watcher> &wbin = watchesBin[p];
        int nb = 0;
        for(int k = 0; k < wbin.size(); k++) {
            Lit imp = wbin[k].blocker;
            if(permDiff[var(imp)] == MYFLAG && value(imp) == l_True) {
                nb++;
                permDiff[var(imp)] = MYFLAG - 1;
            }
        }
        int l = out_learnt.size() - 1;
        if(nb > 0) {
            stats[nbReducedClauses]++;
            for(int i = 1; i < out_learnt.size() - nb; i++) {
                if(permDiff[var(out_learnt[i])] != MYFLAG) {
                    Lit p = out_learnt[l];
                    out_learnt[l] = out_learnt[i];
                    out_learnt[i] = p;
                    l--;
                    i--;
                }
            }

            out_learnt.shrink(nb);

        }
    }
}

// Revert to the state at given level (keeping all assignment at 'level' but not beyond).
//

void Solver::cancelUntil(int level) {
    if(decisionLevel() > level) {
        for(int c = trail.size() - 1; c >= trail_lim[level]; c--) {
            Var x = var(trail[c]);
            assigns[x] = l_Undef;
            if(phase_saving > 1 || ((phase_saving == 1) && c > trail_lim.last())) {
                polarity[x] = sign(trail[c]);
            }
            insertVarOrder(x);
        }
        qhead = trail_lim[level];
        trail.shrink(trail.size() - trail_lim[level]);
        trail_lim.shrink(trail_lim.size() - level);
    }
}


//=================================================================================================
// Major methods:

Lit Solver::pickBranchLit() {
    Var next = var_Undef;

    // Random decision:
    if(((randomizeFirstDescent && conflicts == 0) || drand(random_seed) < random_var_freq) && !order_heap.empty()) {
        next = order_heap[irand(random_seed, order_heap.size())];
        if(value(next) == l_Undef && decision[next])
            stats[rnd_decisions]++;
    }

    // Activity based decision:
    while(next == var_Undef || value(next) != l_Undef || !decision[next])
        if(order_heap.empty()) {
            next = var_Undef;
            break;
        } else {
            next = order_heap.removeMin();
        }

    if(randomize_on_restarts && !fixed_randomize_on_restarts && newDescent && (decisionLevel() % 2 == 0)) {
        return mkLit(next, (randomDescentAssignments >> (decisionLevel() % 32)) & 1);
    }

    if(fixed_randomize_on_restarts && decisionLevel() < 7) {
        return mkLit(next, (randomDescentAssignments >> (decisionLevel() % 32)) & 1);
    }

    if(next == var_Undef) return lit_Undef;

    if(forceUnsatOnNewDescent && newDescent) {
        if(forceUNSAT[next] != 0)
            return mkLit(next, forceUNSAT[next] < 0);
        return mkLit(next, polarity[next]);

    }

    return next == var_Undef ? lit_Undef : mkLit(next, rnd_pol ? drand(random_seed) < 0.5 : polarity[next]);
}


/*_________________________________________________________________________________________________
|
|  analyze : (confl : Clause*) (out_learnt : vec<Lit>&) (out_btlevel : int&)  ->  [void]
|
|  Description:
|    Analyze conflict and produce a reason clause.
|
|    Pre-conditions:
|      * 'out_learnt' is assumed to be cleared.
|      * Current decision level must be greater than root level.
|
|    Post-conditions:
|      * 'out_learnt[0]' is the asserting literal at level 'out_btlevel'.
|      * If out_learnt.size() > 1 then 'out_learnt[1]' has the greatest decision level of the
|        rest of literals. There may be others from the same level though.
|
|________________________________________________________________________________________________@*/
void Solver::analyze(CRef confl, vec <Lit> &out_learnt, vec <Lit> &selectors, int &out_btlevel, unsigned int &lbd, unsigned int &szWithoutSelectors) {
    int pathC = 0;
    Lit p = lit_Undef;


    // Generate conflict clause:
    //
    out_learnt.push(); // (leave room for the asserting literal)
    int index = trail.size() - 1;
    do {
        assert(confl != CRef_Undef); // (otherwise should be UIP)
        Clause &c = ca[confl];
        // Special case for binary clauses
        // The first one has to be SAT
        if(p != lit_Undef && c.size() == 2 && value(c[0]) == l_False) {

            assert(value(c[1]) == l_True);
            Lit tmp = c[0];
            c[0] = c[1], c[1] = tmp;
        }

        if(c.learnt()) {
            parallelImportClauseDuringConflictAnalysis(c, confl);
            claBumpActivity(c);
        } else { // original clause
            if(!c.getSeen()) {
                stats[originalClausesSeen]++;
                c.setSeen(true);
            }
        }

        // DYNAMIC NBLEVEL trick (see competition'09 companion paper)
        if(c.learnt() && c.lbd() > 2) {
            unsigned int nblevels = computeLBD(c);
            if(nblevels + 1 < c.lbd()) { // improve the LBD
                if(c.lbd() <= lbLBDFrozenClause) {
                    // seems to be interesting : keep it for the next round
                    c.setCanBeDel(false);
                }
                if(chanseokStrategy && nblevels <= coLBDBound) {
                    c.nolearnt();
                    learnts.remove(confl);
                    permanentLearnts.push(confl);
                    stats[nbPermanentLearnts]++;

                } else {
                    c.setLBD(nblevels); // Update it
                }
            }
        }


        for(int j = (p == lit_Undef) ? 0 : 1; j < c.size(); j++) {
            Lit q = c[j];

            if(!seen[var(q)]) {
                if(level(var(q)) == 0) {
                } else { // Here, the old case
                    if(!isSelector(var(q)))
                        varBumpActivity(var(q));

                    // This variable was responsible for a conflict,
                    // consider it as a UNSAT assignation for this literal
                    bumpForceUNSAT(~q); // Negation because q is false here

                    seen[var(q)] = 1;
                    if(level(var(q)) >= decisionLevel()) {
                        pathC++;
                        // UPDATEVARACTIVITY trick (see competition'09 companion paper)
                        if(!isSelector(var(q)) && (reason(var(q)) != CRef_Undef) && ca[reason(var(q))].learnt())
                            lastDecisionLevel.push(q);
                    } else {
                        if(isSelector(var(q))) {
                            assert(value(q) == l_False);
                            selectors.push(q);
                        } else
                            out_learnt.push(q);
                    }
                }
            } //else stats[sumResSeen]++;
        }

        // Select next clause to look at:
        while (!seen[var(trail[index--])]);
        p = trail[index + 1];
        //stats[sumRes]++;
        confl = reason(var(p));
        seen[var(p)] = 0;
        pathC--;

    } while(pathC > 0);
    out_learnt[0] = ~p;

    // Simplify conflict clause:
    //
    int i, j;

    for(int i = 0; i < selectors.size(); i++)
        out_learnt.push(selectors[i]);

    out_learnt.copyTo(analyze_toclear);
    if(ccmin_mode == 2) {
        uint32_t abstract_level = 0;
        for(i = 1; i < out_learnt.size(); i++)
            abstract_level |= abstractLevel(var(out_learnt[i])); // (maintain an abstraction of levels involved in conflict)

        for(i = j = 1; i < out_learnt.size(); i++)
            if(reason(var(out_learnt[i])) == CRef_Undef || !litRedundant(out_learnt[i], abstract_level))
                out_learnt[j++] = out_learnt[i];

    } else if(ccmin_mode == 1) {
        for(i = j = 1; i < out_learnt.size(); i++) {
            Var x = var(out_learnt[i]);

            if(reason(x) == CRef_Undef)
                out_learnt[j++] = out_learnt[i];
            else {
                Clause &c = ca[reason(var(out_learnt[i]))];
                // Thanks to Siert Wieringa for this bug fix!
                for(int k = ((c.size() == 2) ? 0 : 1); k < c.size(); k++)
                    if(!seen[var(c[k])] && level(var(c[k])) > 0) {
                        out_learnt[j++] = out_learnt[i];
                        break;
                    }
            }
        }
    } else
        i = j = out_learnt.size();

    //    stats[max_literals]+=out_learnt.size();
    out_learnt.shrink(i - j);
    //    stats[tot_literals]+=out_learnt.size();


    /* ***************************************
      Minimisation with binary clauses of the asserting clause
      First of all : we look for small clauses
      Then, we reduce clauses with small LBD.
      Otherwise, this can be useless
     */
    if(!incremental && out_learnt.size() <= lbSizeMinimizingClause) {
        minimisationWithBinaryResolution(out_learnt);
    }
    // Find correct backtrack level:
    //
    if(out_learnt.size() == 1)
        out_btlevel = 0;
    else {
        int max_i = 1;
        // Find the first literal assigned at the next-highest level:
        for(int i = 2; i < out_learnt.size(); i++)
            if(level(var(out_learnt[i])) > level(var(out_learnt[max_i])))
                max_i = i;
        // Swap-in this literal at index 1:
        Lit p = out_learnt[max_i];
        out_learnt[max_i] = out_learnt[1];
        out_learnt[1] = p;
        out_btlevel = level(var(p));
    }
#ifdef INCREMENTAL
    if(incremental) {
       szWithoutSelectors = 0;
       for(int i=0;i<out_learnt.size();i++) {
     if(!isSelector(var((out_learnt[i])))) szWithoutSelectors++;
     else if(i>0) break;
       }
     } else
#endif
    szWithoutSelectors = out_learnt.size();

    // Compute LBD
    lbd = computeLBD(out_learnt, out_learnt.size() - selectors.size());

    // UPDATEVARACTIVITY trick (see competition'09 companion paper)
    if(lastDecisionLevel.size() > 0) {
        for(int i = 0; i < lastDecisionLevel.size(); i++) {
            if(ca[reason(var(lastDecisionLevel[i]))].lbd() < lbd)
                varBumpActivity(var(lastDecisionLevel[i]));
        }
        lastDecisionLevel.clear();
    }


    for(int j = 0; j < analyze_toclear.size(); j++) seen[var(analyze_toclear[j])] = 0; // ('seen[]' is now cleared)
    for(int j = 0; j < selectors.size(); j++) seen[var(selectors[j])] = 0;
}


// Check if 'p' can be removed. 'abstract_levels' is used to abort early if the algorithm is
// visiting literals at levels that cannot be removed later.

bool Solver::litRedundant(Lit p, uint32_t abstract_levels) {
    analyze_stack.clear();
    analyze_stack.push(p);
    int top = analyze_toclear.size();
    while(analyze_stack.size() > 0) {
        assert(reason(var(analyze_stack.last())) != CRef_Undef);
        Clause &c = ca[reason(var(analyze_stack.last()))];
        analyze_stack.pop(); //
        if(c.size() == 2 && value(c[0]) == l_False) {
            assert(value(c[1]) == l_True);
            Lit tmp = c[0];
            c[0] = c[1], c[1] = tmp;
        }

        for(int i = 1; i < c.size(); i++) {
            Lit p = c[i];
            if(!seen[var(p)]) {
                if(level(var(p)) > 0) {
                    if(reason(var(p)) != CRef_Undef && (abstractLevel(var(p)) & abstract_levels) != 0) {
                        seen[var(p)] = 1;
                        analyze_stack.push(p);
                        analyze_toclear.push(p);
                    } else {
                        for(int j = top; j < analyze_toclear.size(); j++)
                            seen[var(analyze_toclear[j])] = 0;
                        analyze_toclear.shrink(analyze_toclear.size() - top);
                        return false;
                    }
                }
            }
        }
    }

    return true;
}


/*_________________________________________________________________________________________________
|
|  analyzeFinal : (p : Lit)  ->  [void]
|
|  Description:
|    Specialized analysis procedure to express the final conflict in terms of assumptions.
|    Calculates the (possibly empty) set of assumptions that led to the assignment of 'p', and
|    stores the result in 'out_conflict'.
|________________________________________________________________________________________________@*/
void Solver::analyzeFinal(Lit p, vec <Lit> &out_conflict) {
    out_conflict.clear();
    out_conflict.push(p);

    if(decisionLevel() == 0)
        return;

    seen[var(p)] = 1;

    for(int i = trail.size() - 1; i >= trail_lim[0]; i--) {
        Var x = var(trail[i]);
        if(seen[x]) {
            if(reason(x) == CRef_Undef) {
                assert(level(x) > 0);
                out_conflict.push(~trail[i]);
            } else {
                Clause &c = ca[reason(x)];
                //                for (int j = 1; j < c.size(); j++) Minisat (glucose 2.0) loop
                // Bug in case of assumptions due to special data structures for Binary.
                // Many thanks to Sam Bayless (sbayless@cs.ubc.ca) for discover this bug.
                for(int j = ((c.size() == 2) ? 0 : 1); j < c.size(); j++)
                    if(level(var(c[j])) > 0)
                        seen[var(c[j])] = 1;
            }

            seen[x] = 0;
        }
    }

    seen[var(p)] = 0;
}


void Solver::uncheckedEnqueue(Lit p, CRef from) {
    assert(value(p) == l_Undef);
    assigns[var(p)] = lbool(!sign(p));
    vardata[var(p)] = mkVarData(from, decisionLevel());
    trail.push_(p);
}


void Solver::bumpForceUNSAT(Lit q) {
    forceUNSAT[var(q)] = sign(q) ? -1 : +1;
    return;
}


/*_________________________________________________________________________________________________
|
|  propagate : [void]  ->  [Clause*]
|
|  Description:
|    Propagates all enqueued facts. If a conflict arises, the conflicting clause is returned,
|    otherwise CRef_Undef.
|
|    Post-conditions:
|      * the propagation queue is empty, even if there was a conflict.
|________________________________________________________________________________________________@*/
CRef Solver::propagate() {
    CRef confl = CRef_Undef;
    int num_props = 0;
    watches.cleanAll();
    watchesBin.cleanAll();
    unaryWatches.cleanAll();
    while(qhead < trail.size()) {
        Lit p = trail[qhead++]; // 'p' is enqueued fact to propagate.
        vec <Watcher> &ws = watches[p];
        Watcher *i, *j, *end;
        num_props++;


        // First, Propagate binary clauses
        vec <Watcher> &wbin = watchesBin[p];
        for(int k = 0; k < wbin.size(); k++) {

            Lit imp = wbin[k].blocker;

            if(value(imp) == l_False) {
                return wbin[k].cref;
            }

            if(value(imp) == l_Undef) {
                uncheckedEnqueue(imp, wbin[k].cref);
            }
        }

        // Now propagate other 2-watched clauses
        for(i = j = (Watcher *) ws, end = i + ws.size(); i != end;) {
            // Try to avoid inspecting the clause:
            Lit blocker = i->blocker;
            if(value(blocker) == l_True) {
                *j++ = *i++;
                continue;
            }

            // Make sure the false literal is data[1]:
            CRef cr = i->cref;
            Clause &c = ca[cr];
            assert(!c.getOneWatched());
            Lit false_lit = ~p;
            if(c[0] == false_lit)
                c[0] = c[1], c[1] = false_lit;
            assert(c[1] == false_lit);
            i++;

            // If 0th watch is true, then clause is already satisfied.
            Lit first = c[0];
            Watcher w = Watcher(cr, first);
            if(first != blocker && value(first) == l_True) {

                *j++ = w;
                continue;
            }
#ifdef INCREMENTAL
            if(incremental) { // ----------------- INCREMENTAL MODE
              int choosenPos = -1;
              for (int k = 2; k < c.size(); k++) {

            if (value(c[k]) != l_False){
              if(decisionLevel()>assumptions.size()) {
                choosenPos = k;
                break;
              } else {
                choosenPos = k;

                if(value(c[k])==l_True || !isSelector(var(c[k]))) {
                  break;
                }
              }

            }
              }
              if(choosenPos!=-1) {
            c[1] = c[choosenPos]; c[choosenPos] = false_lit;
            watches[~c[1]].push(w);
            goto NextClause; }
            } else {  // ----------------- DEFAULT  MODE (NOT INCREMENTAL)
#endif
            for(int k = 2; k < c.size(); k++) {

                if(value(c[k]) != l_False) {
                    c[1] = c[k];
                    c[k] = false_lit;
                    watches[~c[1]].push(w);
                    goto NextClause;
                }
            }
#ifdef INCREMENTAL
            }
#endif
            // Did not find watch -- clause is unit under assignment:
            *j++ = w;
            if(value(first) == l_False) {
                confl = cr;
                qhead = trail.size();
                // Copy the remaining watches:
                while(i < end)
                    *j++ = *i++;
            } else {
                uncheckedEnqueue(first, cr);


            }
            NextClause:;
        }
        ws.shrink(i - j);

        // unaryWatches "propagation"
        if(useUnaryWatched && confl == CRef_Undef) {
            confl = propagateUnaryWatches(p);

        }

    }


    propagations += num_props;
    simpDB_props -= num_props;

    return confl;
}


/*_________________________________________________________________________________________________
|
|  propagateUnaryWatches : [Lit]  ->  [Clause*]
|
|  Description:
|    Propagates unary watches of Lit p, return a conflict
|    otherwise CRef_Undef
|
|________________________________________________________________________________________________@*/

CRef Solver::propagateUnaryWatches(Lit p) {
    CRef confl = CRef_Undef;
    Watcher *i, *j, *end;
    vec <Watcher> &ws = unaryWatches[p];
    for(i = j = (Watcher *) ws, end = i + ws.size(); i != end;) {
        // Try to avoid inspecting the clause:
        Lit blocker = i->blocker;
        if(value(blocker) == l_True) {
            *j++ = *i++;
            continue;
        }

        // Make sure the false literal is data[1]:
        CRef cr = i->cref;
        Clause &c = ca[cr];
        assert(c.getOneWatched());
        Lit false_lit = ~p;
        assert(c[0] == false_lit); // this is unary watch... No other choice if "propagated"
        //if (c[0] == false_lit)
        //c[0] = c[1], c[1] = false_lit;
        //assert(c[1] == false_lit);
        i++;
        Watcher w = Watcher(cr, c[0]);
        for(int k = 1; k < c.size(); k++) {
            if(value(c[k]) != l_False) {
                c[0] = c[k];
                c[k] = false_lit;
                unaryWatches[~c[0]].push(w);
                goto NextClauseUnary;
            }
        }

        // Did not find watch -- clause is empty under assignment:
        *j++ = w;

        confl = cr;
        qhead = trail.size();
        // Copy the remaining watches:
        while(i < end)
            *j++ = *i++;

        // We can add it now to the set of clauses when backtracking
        //printf("*");
        if(promoteOneWatchedClause) {
            stats[nbPromoted]++;
            // Let's find the two biggest decision levels in the clause s.t. it will correctly be propagated when we'll backtrack
            int maxlevel = -1;
            int index = -1;
            for(int k = 1; k < c.size(); k++) {
                assert(value(c[k]) == l_False);
                assert(level(var(c[k])) <= level(var(c[0])));
                if(level(var(c[k])) > maxlevel) {
                    index = k;
                    maxlevel = level(var(c[k]));
                }
            }
            detachClausePurgatory(cr, true); // TODO: check that the cleanAll is ok (use ",true" otherwise)
            assert(index != -1);
            Lit tmp = c[1];
            c[1] = c[index], c[index] = tmp;
            attachClause(cr);
            // TODO used in function ParallelSolver::reportProgressArrayImports
            //Override :-(
            //goodImportsFromThreads[ca[cr].importedFrom()]++;
            ca[cr].setOneWatched(false);
            ca[cr].setExported(2);
        }
        NextClauseUnary:;
    }
    ws.shrink(i - j);

    return confl;
}


/*_________________________________________________________________________________________________
|
|  reduceDB : ()  ->  [void]
|
|  Description:
|    Remove half of the learnt clauses, minus the clauses locked by the current assignment. Locked
|    clauses are clauses that are reason to some assignment. Binary clauses are never removed.
|________________________________________________________________________________________________@*/


void Solver::reduceDB() {
    if(reduce_strategy_mode == REDUCE_ADAPTIVE_FIXED) {
        reduceDBAdaptiveFixed();
    } else if(reduce_strategy_mode == REDUCE_ADAPTIVE) {
        reduceDBAdaptive();
    } else {
        reduceDBBaseline();
    }
}


void Solver::reduceDBBaseline() {

    int i, j;
    stats[nbReduceDB]++;

    if (!chanseokStrategy) { // We will use the LBD, but keep 10% of the best active clauses
      sort(learnts, reduceDBAct_lt(ca));
      for(int i=learnts.size()*90/100;i<learnts.size();i++) {
        Clause &c = ca[learnts[i]];
        c.setCanBeDel(false);
      }
    }

    if(chanseokStrategy)
        sort(learnts, reduceDBAct_lt(ca));
    else {
        sort(learnts, reduceDB_lt(ca));

        // We have a lot of "good" clauses, it is difficult to compare them. Keep more !
        if(ca[learnts[learnts.size() / RATIOREMOVECLAUSES]].lbd() <= 3) nbclausesbeforereduce += specialIncReduceDB;
        // Useless :-)
        if(ca[learnts.last()].lbd() <= 5) nbclausesbeforereduce += specialIncReduceDB;

    }
    // Don't delete binary or locked clauses. From the rest, delete clauses from the first half
    // Keep clauses which seem to be usefull (their lbd was reduce during this sequence)

    int limit = (learnts.size() / 2); // 

    for(i = j = 0; i < learnts.size(); i++) {
        Clause &c = ca[learnts[i]];
        if(c.lbd() > 2 && c.size() > 2 && c.canBeDel() && !locked(c) && (i < limit)) {
            //mostActiveClauses.push(learnts[i]);
            removeClause(learnts[i]);
            stats[nbRemovedClauses]++;
        }
        else {
            if(!c.canBeDel()) limit++; //we keep c, so we can delete an other clause
            c.setCanBeDel(true);       // At the next step, c can be delete
            learnts[j++] = learnts[i];
        }
    }
    learnts.shrink(i - j);


    checkGarbage();
}


struct ScoredClause {
    CRef  cr;
    float score;
};

struct ScoredClause_lt {
    bool operator()(const ScoredClause& a, const ScoredClause& b) const {
        assert(!isnan(a.score) && !isnan(b.score));
        assert(a.cr != CRef_Undef && b.cr != CRef_Undef);
        if(a.score != b.score)
            return a.score < b.score; // Lower score = lower utility = purged first
        return a.cr < b.cr;           // Deterministic tie-breaker
    }
};

void Solver::reduceDBAdaptive() {
    int i, j;
    stats[nbReduceDB]++;

    if(learnts.size() == 0) return;

    double start_time = cpuTime();
    adapt_reduce_calls++;
    adapt_clauses_considered += learnts.size();

    // Step 1: Scan population to compute max_activity and LBD statistics
    float max_activity = 0.0f;
    int good_lbd_count = 0;
    unsigned int min_lbd = ca[learnts[0]].lbd();

    for(i = 0; i < learnts.size(); i++) {
        assert(learnts[i] != CRef_Undef);
        Clause &c = ca[learnts[i]];
        assert(!c.mark());
        float act = c.activity();
        if(isfinite(act) && act > max_activity) {
            max_activity = act;
        }
        if(c.lbd() <= 3) {
            good_lbd_count++;
        }
        if(c.lbd() < min_lbd) {
            min_lbd = c.lbd();
        }
    }

    // Step 2: Postponement check preserving Glucose's reduction interval heuristic (Historical Mode)
    adapt_postpone_evals++;
    if(good_lbd_count >= learnts.size() / RATIOREMOVECLAUSES) {
        adapt_postpone_satisfied++;
        adapt_postpone_inc_db += specialIncReduceDB;
        nbclausesbeforereduce += specialIncReduceDB;
    }
    if(min_lbd <= 5) {
        adapt_postpone_satisfied++;
        adapt_postpone_inc_db += specialIncReduceDB;
        nbclausesbeforereduce += specialIncReduceDB;
    }

    // Step 3: Compute continuous multi-attribute retention score R(c) for all candidates
    vec<ScoredClause> scored;
    scored.growTo(learnts.size());

    for(i = 0; i < learnts.size(); i++) {
        CRef cr = learnts[i];
        Clause &c = ca[cr];

        // S_LBD: 1 / (1 + 0.50 * max(0, LBD - 2))
        int lbd_delta = (int)c.lbd() - 2;
        if(lbd_delta < 0) lbd_delta = 0;
        float s_lbd = 1.0f / (1.0f + 0.50f * (float)lbd_delta);
        assert(s_lbd > 0.0f && s_lbd <= 1.0f);

        // S_act: sqrt(clamp(activity / max_activity, 0, 1)) when max_activity > 0, else 0
        float s_act = 0.0f;
        if(max_activity > 0.0f) {
            float act = c.activity();
            if(isfinite(act) && act > 0.0f) {
                float ratio = act / max_activity;
                if(!isfinite(ratio) || ratio < 0.0f) ratio = 0.0f;
                else if(ratio > 1.0f) ratio = 1.0f;
                s_act = sqrtf(ratio);
            }
        }
        assert(s_act >= 0.0f && s_act <= 1.0f);

        // S_size: 1 / (1 + 0.05 * max(0, size - 2))
        int size_delta = c.size() - 2;
        if(size_delta < 0) size_delta = 0;
        float s_size = 1.0f / (1.0f + 0.05f * (float)size_delta);
        assert(s_size > 0.0f && s_size <= 1.0f);

        // R(c) = 0.50 * S_LBD + 0.40 * S_act + 0.10 * S_size
        float score = 0.50f * s_lbd + 0.40f * s_act + 0.10f * s_size;
        if(!isfinite(score) || score < 0.0f) score = 0.0f;
        else if(score > 1.0f) score = 1.0f;
        assert(score >= 0.0f && score <= 1.0f);

        scored[i].cr = cr;
        scored[i].score = score;
    }

    assert(scored.size() == learnts.size());

    // Step 4: Deterministic sort in ascending order of score (worst candidates at front)
    sort(scored, ScoredClause_lt());

    // Step 5: Safe deletion loop preserving all mandatory protections
    int limit = (learnts.size() / 2);
    uint64_t current_reduce_del_count = 0;
    uint64_t current_reduce_sum_del_lbd = 0;

    for(i = j = 0; i < scored.size(); i++) {
        CRef cr = scored[i].cr;
        Clause &c = ca[cr];
        if(i < limit) {
            adapt_clauses_eligible++;
            if(c.lbd() > 2 && c.size() > 2 && c.canBeDel() && !locked(c)) {
                // Safety Invariants:
                assert(cr != CRef_Undef);
                assert(!c.mark());
                assert(c.learnt());
                assert(!locked(c));
                assert(c.size() > 2);
                assert(c.lbd() > 2);
                assert(c.canBeDel());

                current_reduce_del_count++;
                current_reduce_sum_del_lbd += c.lbd();
                adapt_clauses_removed++;
                removeClause(cr);
                stats[nbRemovedClauses]++;
            } else {
                // Precedence classification for spared clauses within deletion quota:
                if(c.size() <= 2) {
                    adapt_spared_binary++;
                } else if(c.lbd() <= 2) {
                    adapt_spared_glue++;
                } else if(!c.canBeDel()) {
                    adapt_spared_canbedel++;
                } else if(locked(c)) {
                    adapt_spared_locked++;
                }

                if(!c.canBeDel()) limit++; // Quota compensation: keep c, purge another clause
                c.setCanBeDel(true);        // Reset single-round immunity for next reduction
                assert(!c.mark());
                learnts[j++] = cr;
            }
        } else {
            // Outside deletion quota: retained by limit
            if(!c.canBeDel()) limit++; // Quota compensation: keep c, purge another clause
            c.setCanBeDel(true);        // Reset single-round immunity for next reduction
            assert(!c.mark());
            learnts[j++] = cr;
        }
    }

    // Conservation assertion:
    assert(j + current_reduce_del_count == (uint64_t)scored.size());

    learnts.shrink(i - j);
    assert(learnts.size() == j);

    adapt_last_retained = j;

    uint64_t sum_retained_lbd = 0;
    for(int k = 0; k < j; k++) {
        Clause &c_ret = ca[learnts[k]];
        assert(!c_ret.mark());
        assert(c_ret.canBeDel());
        sum_retained_lbd += c_ret.lbd();
    }
    adapt_last_avg_retained_lbd = (j > 0) ? (double)sum_retained_lbd / j : 0.0;
    adapt_last_avg_deleted_lbd = (current_reduce_del_count > 0) ? (double)current_reduce_sum_del_lbd / current_reduce_del_count : 0.0;

    // Step 6: Memory compaction if needed
    checkGarbage();

    for(int k = 0; k < learnts.size(); k++) {
        assert(learnts[k] != CRef_Undef);
        assert(!ca[learnts[k]].mark());
    }

    adapt_reduce_time += (cpuTime() - start_time);
}


void Solver::reduceDBAdaptiveFixed() {
    int i, j;
    stats[nbReduceDB]++;

    if(learnts.size() == 0) return;

    double start_time = cpuTime();
    adapt_reduce_calls++;
    adapt_clauses_considered += learnts.size();

    // Step 1: Scan population to compute max_activity and LBD statistics
    float max_activity = 0.0f;
    int good_lbd_count = 0;
    unsigned int min_lbd = ca[learnts[0]].lbd();

    for(i = 0; i < learnts.size(); i++) {
        assert(learnts[i] != CRef_Undef);
        Clause &c = ca[learnts[i]];
        assert(!c.mark());
        float act = c.activity();
        if(isfinite(act) && act > max_activity) {
            max_activity = act;
        }
        if(c.lbd() <= 3) {
            good_lbd_count++;
        }
        if(c.lbd() < min_lbd) {
            min_lbd = c.lbd();
        }
    }

    // Step 2: Postponement check with corrected Glucose reduction interval heuristic
    adapt_postpone_evals++;
    if(!chanseokStrategy) {
        // Condition 1: Median LBD <= 3 on descending LBD-sorted array.
        // In baseline, ca[learnts[N/2]].lbd() <= 3 requires at least N - (N/2) = (N + 1)/2 clauses with LBD <= 3.
        if(good_lbd_count >= (learnts.size() + 1) / 2) {
            adapt_postpone_satisfied++;
            adapt_postpone_inc_db += specialIncReduceDB;
            nbclausesbeforereduce += specialIncReduceDB;
        }
        // Condition 2: Min LBD <= 5 (matching baseline's ca[learnts.last()].lbd() <= 5)
        if(min_lbd <= 5) {
            adapt_postpone_satisfied++;
            adapt_postpone_inc_db += specialIncReduceDB;
            nbclausesbeforereduce += specialIncReduceDB;
        }
    }

    // Step 3: Compute continuous multi-attribute retention score R(c) for all candidates
    vec<ScoredClause> scored;
    scored.growTo(learnts.size());

    for(i = 0; i < learnts.size(); i++) {
        CRef cr = learnts[i];
        Clause &c = ca[cr];

        // S_LBD: 1 / (1 + 0.50 * max(0, LBD - 2))
        int lbd_delta = (int)c.lbd() - 2;
        if(lbd_delta < 0) lbd_delta = 0;
        float s_lbd = 1.0f / (1.0f + 0.50f * (float)lbd_delta);
        assert(s_lbd > 0.0f && s_lbd <= 1.0f);

        // S_act: sqrt(clamp(activity / max_activity, 0, 1)) when max_activity > 0, else 0
        float s_act = 0.0f;
        if(max_activity > 0.0f) {
            float act = c.activity();
            if(isfinite(act) && act > 0.0f) {
                float ratio = act / max_activity;
                if(!isfinite(ratio) || ratio < 0.0f) ratio = 0.0f;
                else if(ratio > 1.0f) ratio = 1.0f;
                s_act = sqrtf(ratio);
            }
        }
        assert(s_act >= 0.0f && s_act <= 1.0f);

        // S_size: 1 / (1 + 0.05 * max(0, size - 2))
        int size_delta = c.size() - 2;
        if(size_delta < 0) size_delta = 0;
        float s_size = 1.0f / (1.0f + 0.05f * (float)size_delta);
        assert(s_size > 0.0f && s_size <= 1.0f);

        // R(c) = 0.50 * S_LBD + 0.40 * S_act + 0.10 * S_size
        float score = 0.50f * s_lbd + 0.40f * s_act + 0.10f * s_size;
        if(!isfinite(score) || score < 0.0f) score = 0.0f;
        else if(score > 1.0f) score = 1.0f;
        assert(score >= 0.0f && score <= 1.0f);

        scored[i].cr = cr;
        scored[i].score = score;
    }

    assert(scored.size() == learnts.size());

    // Step 4: Deterministic sort in ascending order of score (worst candidates at front)
    sort(scored, ScoredClause_lt());

    // Step 5: Safe deletion loop preserving all mandatory protections
    int limit = (learnts.size() / 2);
    uint64_t current_reduce_del_count = 0;
    uint64_t current_reduce_sum_del_lbd = 0;

    for(i = j = 0; i < scored.size(); i++) {
        CRef cr = scored[i].cr;
        Clause &c = ca[cr];
        if(i < limit) {
            adapt_clauses_eligible++;
            if(c.lbd() > 2 && c.size() > 2 && c.canBeDel() && !locked(c)) {
                // Safety Invariants:
                assert(cr != CRef_Undef);
                assert(!c.mark());
                assert(c.learnt());
                assert(!locked(c));
                assert(c.size() > 2);
                assert(c.lbd() > 2);
                assert(c.canBeDel());

                current_reduce_del_count++;
                current_reduce_sum_del_lbd += c.lbd();
                adapt_clauses_removed++;
                removeClause(cr);
                stats[nbRemovedClauses]++;
            } else {
                // Precedence classification for spared clauses within deletion quota:
                if(c.size() <= 2) {
                    adapt_spared_binary++;
                } else if(c.lbd() <= 2) {
                    adapt_spared_glue++;
                } else if(!c.canBeDel()) {
                    adapt_spared_canbedel++;
                } else if(locked(c)) {
                    adapt_spared_locked++;
                }

                if(!c.canBeDel()) limit++; // Quota compensation: keep c, purge another clause
                c.setCanBeDel(true);        // Reset single-round immunity for next reduction
                assert(!c.mark());
                learnts[j++] = cr;
            }
        } else {
            // Outside deletion quota: retained by limit
            if(!c.canBeDel()) limit++; // Quota compensation: keep c, purge another clause
            c.setCanBeDel(true);        // Reset single-round immunity for next reduction
            assert(!c.mark());
            learnts[j++] = cr;
        }
    }

    // Conservation assertion:
    assert(j + current_reduce_del_count == (uint64_t)scored.size());

    learnts.shrink(i - j);
    assert(learnts.size() == j);

    adapt_last_retained = j;

    uint64_t sum_retained_lbd = 0;
    for(int k = 0; k < j; k++) {
        Clause &c_ret = ca[learnts[k]];
        assert(!c_ret.mark());
        assert(c_ret.canBeDel());
        sum_retained_lbd += c_ret.lbd();
    }
    adapt_last_avg_retained_lbd = (j > 0) ? (double)sum_retained_lbd / j : 0.0;
    adapt_last_avg_deleted_lbd = (current_reduce_del_count > 0) ? (double)current_reduce_sum_del_lbd / current_reduce_del_count : 0.0;

    // Step 6: Memory compaction if needed
    checkGarbage();

    for(int k = 0; k < learnts.size(); k++) {
        assert(learnts[k] != CRef_Undef);
        assert(!ca[learnts[k]].mark());
    }

    adapt_reduce_time += (cpuTime() - start_time);
}


void Solver::removeSatisfied(vec <CRef> &cs) {

    int i, j;
    for(i = j = 0; i < cs.size(); i++) {
        Clause &c = ca[cs[i]];


        if(satisfied(c))
            if(c.getOneWatched())
            removeClause(cs[i], true);
        else {
                //// simplify
                removeClause(cs[i]);
            }
        else
            cs[j++] = cs[i];
    }
    cs.shrink(i - j);
}


void Solver::rebuildOrderHeap() {
    vec <Var> vs;
    for(Var v = 0; v < nVars(); v++)
        if(decision[v] && value(v) == l_Undef)
            vs.push(v);
    order_heap.build(vs);

}


/*_________________________________________________________________________________________________
|
|  simplify : [void]  ->  [bool]
|
|  Description:
|    Simplify the clause database according to the current top-level assigment. Currently, the only
|    thing done here is the removal of satisfied clauses, but more things can be put here.
|________________________________________________________________________________________________@*/
bool Solver::simplify() {
    assert(decisionLevel() == 0);

    if(!ok) return ok = false;
    else {
        CRef cr = propagate();
        if(cr != CRef_Undef) {
            return ok = false;
        }
    }


    if(nAssigns() == simpDB_assigns || (simpDB_props > 0))
        return true;

    // Remove satisfied clauses:
    removeSatisfied(learnts);
    removeSatisfied(permanentLearnts);
    removeSatisfied(permanentLearntsReduced);
    removeSatisfied(unaryWatchedClauses);
    if(remove_satisfied) // Can be turned off.
        removeSatisfied(clauses);
    checkGarbage();
    rebuildOrderHeap();

    simpDB_assigns = nAssigns();
    simpDB_props = stats[clauses_literals] + stats[learnts_literals]; // (shouldn't depend on stats really, but it will do for now)

    return true;
}


void Solver::adaptSolver() {
    bool adjusted = false;
    bool reinit = false;
    printf("c\nc Try to adapt solver strategies\nc \n");
      printf("c Adjusting solver for the SAT Race 2015 (alpha feature)\n");
    /*printf("c key successive Conflicts       : %" PRIu64"\n",stats[noDecisionConflict]);
    printf("c nb unary clauses learnt        : %" PRIu64"\n",stats[nbUn]);
    printf("c key avg dec per conflicts      : %.2f\n", (float)decisions / (float)conflicts);
    printf("c avg learnt clauses :  %" PRIu64"\n", stats[sumSizes]/conflicts);
    */float decpc = (float) decisions / (float) conflicts;
    if(decpc <= 1.2) {
        chanseokStrategy = true;
        coLBDBound = 4;
        glureduce = true;
        adjusted = true;
        printf("c Adjusting for low decision levels.\n");
        reinit = true;
        firstReduceDB = 2000;
        nbclausesbeforereduce = firstReduceDB;
        curRestart = (conflicts / nbclausesbeforereduce) + 1;
        incReduceDB = 0;
    }
    if(stats[noDecisionConflict] < 30000) {
        luby_restart = true;
        luby_restart_factor = 100;

        var_decay = 0.999;
        max_var_decay = 0.999;
        adjusted = true;
        printf("c Adjusting for low successive conflicts.\n");
    }
    if(stats[noDecisionConflict] > 54400) {
        printf("c Adjusting for high successive conflicts.\n");
        chanseokStrategy = true;
        glureduce = true;
        coLBDBound = 3;
        firstReduceDB = 30000;
        var_decay = 0.99;
        max_var_decay = 0.99;
        randomize_on_restarts = 1;
        adjusted = true;
    }
    if(stats[nbDL2] - stats[nbBin] > 20000) {
        var_decay = 0.91;
        max_var_decay = 0.91;
        adjusted = true;
        printf("c Adjusting for a very large number of true glue clauses found.\n");
    }
    if(!adjusted) {
        printf("c Nothing extreme in this problem, continue with glucose default strategies.\n");
    }
    printf("c\n");
    if(adjusted) { // Let's reinitialize the glucose restart strategy counters
        lbdQueue.fastclear();
        sumLBD = 0;
        conflictsRestarts = 0;
    }

    if(chanseokStrategy && adjusted) {
        int moved = 0;
        int i, j;
        for(i = j = 0; i < learnts.size(); i++) {
            Clause &c = ca[learnts[i]];
            if(c.lbd() <= coLBDBound) {
                permanentLearnts.push(learnts[i]);
                moved++;
            }
            else {
                learnts[j++] = learnts[i];
            }
        }
        learnts.shrink(i - j);
        printf("c Activating Chanseok Strategy: moved %d clauses to the permanent set.\n", moved);
    }

    if(reinit) {
        assert(decisionLevel() == 0);
        for(int i = 0; i < learnts.size(); i++) {
            removeClause(learnts[i]);
        }
        learnts.shrink(learnts.size());
        checkGarbage();
/*
order_heap.clear();
for(int i=0;i<nVars();i++) {
    polarity[i] = true;
    activity[i] = 0.0;
    if (decision[i]) order_heap.insert(i);
}
printf("c reinitialization of all variables activity/phase/learnt clauses.\n");
*/
        printf("c Removing of non permanent clauses.\n");
    }

}


/*_________________________________________________________________________________________________
|
|  search : (nof_conflicts : int) (params : const SearchParams&)  ->  [lbool]
|
|  Description:
|    Search for a model the specified number of conflicts.
|    NOTE! Use negative value for 'nof_conflicts' indicate infinity.
|
|  Output:
|    'l_True' if a partial assigment that is consistent with respect to the clauseset is found. If
|    all variables are decision variables, this means that the clause set is satisfiable. 'l_False'
|    if the clause set is unsatisfiable. 'l_Undef' if the bound on number of conflicts is reached.
|________________________________________________________________________________________________@*/
lbool Solver::search(int nof_conflicts) {
    assert(ok);
    int backtrack_level;
    int conflictC = 0;
    vec <Lit> learnt_clause, selectors;
    unsigned int nblevels, szWithoutSelectors = 0;
    bool blocked = false;
    bool aDecisionWasMade = false;

    starts++;

    // simplify
    if (useLCM && performLCM){
        //printf("###simplifyAll: %lld\n", conflicts);
        sort(learnts, reduceDB_lt(ca));
        //printf("nbClauses : %d, nbLearnts : %d\n", clauses.size(), learnts.size());
        if (!simplifyAll())
        {
            return l_False;
        }
        performLCM = 0;
    }


    for(; ;) {
        if(decisionLevel() == 0) { // We import clauses FIXME: ensure that we will import clauses enventually (restart after some point)
            parallelImportUnaryClauses();

            if(parallelImportClauses())
                return l_False;

        }
        CRef confl = propagate();

        if((qre_shadow_mode || isAnyAdaptiveQRE()) && qre_pending_decision) {
            uint64_t cur_props = propagations;
            uint64_t delta_p = (cur_props >= qre_last_decision_props) ? (cur_props - qre_last_decision_props) : 0;
            qre_last_decision_props = cur_props;
            onDecisionQRE((double)delta_p, decisionLevel());
            qre_pending_decision = false;
        }

        if(confl != CRef_Undef) {
            newDescent = false;
            if(parallelJobIsFinished())
                return l_Undef;

            if(!aDecisionWasMade)
                stats[noDecisionConflict]++;
            aDecisionWasMade = false;

            stats[sumDecisionLevels] += decisionLevel();
            stats[sumTrail] += trail.size();
            // CONFLICT
            int pre_confl_level = decisionLevel();
            conflicts++;
            conflictC++;
            conflictsRestarts++;
            if(restart_strategy == RESTART_FIXED_INTERVAL || restart_strategy == RESTART_NO_HEURISTIC) {
                fixed_conflicts_since_restart++;
            }
            if(isAdaptiveRestart()) {
                updateAdaptiveRestartController(decisionLevel());
            }
            if(conflicts % 5000 == 0 && var_decay < max_var_decay)
                var_decay += 0.01;

            if(verbosity >= 1 && starts>0 && conflicts % verbEveryConflicts == 0) {
                printf("c | %8d   %7d    %5d | %7d %8d %8d | %5d %8d   %6d %8d | %6.3f %% |\n",
                       (int) starts, (int) stats[nbstopsrestarts], (int) (conflicts / starts),
                       (int) stats[dec_vars] - (trail_lim.size() == 0 ? trail.size() : trail_lim[0]), nClauses(), (int) stats[clauses_literals],
                       (int) stats[nbReduceDB], nLearnts(), (int) stats[nbDL2], (int) stats[nbRemovedClauses], progressEstimate() * 100);
            }
            if(decisionLevel() == 0) {
                return l_False;

            }
            if(adaptStrategies && conflicts == 100000) {
                cancelUntil(0);
                adaptSolver();
                adaptStrategies = false;
                strategy_adaptation_restarts++;
                if(restart_trace) {
                    printf("c [RESTART_TRACE] conflict=%llu reason=STRATEGY_ADAPTATION starts=%llu\n",
                           (unsigned long long)conflicts, (unsigned long long)starts);
                }
                if(restart_strategy == RESTART_ADAPTIVE_V3) {
                    resetAdaptiveRestartDescentV3();
                } else if(restart_strategy == RESTART_FIXED_INTERVAL) {
                    resetFixedRestartDescent();
                } else if(restart_strategy == RESTART_NO_HEURISTIC) {
                    if(fixed_conflicts_since_restart > fixed_max_observed_interval) {
                        fixed_max_observed_interval = fixed_conflicts_since_restart;
                    }
                    fixed_conflicts_since_restart = 0;
                } else if(isPortfolioMAB() || portfolio_shadow_mode) {
                    if(mab_postponement_active) {
                        mab_canceled_postponements++;
                        mab_postponement_active = false;
                    }
                    endMABInterval(false);
                    startMABInterval(mab_next_arm);
                } else if(v3_shadow_mode) {
                    onActualRestartV3Shadow();
                }
                if(qre_shadow_mode || isAnyAdaptiveQRE()) {
                    onRestartQRE();
                }
                if(isAnyAdaptiveQRE()) {
                    onGenuineRestartQRE();
                }
                return l_Undef;
            }

            trailQueue.push(trail.size());
            // BLOCK RESTART (CP 2012 paper)
            bool is_valid = isAdaptiveV3() ? (v3_valid_obs >= 50) : (isAdaptiveRestart() ? isAdaptiveWindowValid() : lbdQueue.isvalid());
            if(conflictsRestarts > LOWER_BOUND_FOR_BLOCKING_RESTART && is_valid && trail.size() > R * trailQueue.getavg()) {
                lbdQueue.fastclear();
                if(isAdaptiveRestart()) {
                    clearAdaptiveWindow();
                }
                if(isAdaptiveV2()) {
                    v2_blocked_restarts++;
                }
                if(isAdaptiveV3()) {
                    v3_blocked_restarts++;
                }
                stats[nbstopsrestarts]++;
                if(!blocked) {
                    stats[lastblockatrestart] = starts;
                    stats[nbstopsrestartssame]++;
                    blocked = true;
                }
            }

            learnt_clause.clear();
            selectors.clear();

            analyze(confl, learnt_clause, selectors, backtrack_level, nblevels, szWithoutSelectors);

            stats[sumSizes]+= learnt_clause.size();
            lbdQueue.push(nblevels);
            sumLBD += nblevels;
            mab_total_learned_clauses++;
            if(nblevels <= 2) mab_total_glue_clauses++;

            cancelUntil(backtrack_level);
            if(isAdaptiveV3() || v3_shadow_mode) {
                updateV3Indicators(nblevels, pre_confl_level, backtrack_level);
            }
            if(qre_shadow_mode || isAnyAdaptiveQRE()) {
                onConflictQRE(nblevels);
            }

            if(certifiedUNSAT)
                addToDrat(learnt_clause, true);



            if(learnt_clause.size() == 1) {
                uncheckedEnqueue(learnt_clause[0]);
                stats[nbUn]++;
                parallelExportUnaryClause(learnt_clause[0]);
            } else {
                CRef cr;
                if(chanseokStrategy && nblevels <= coLBDBound) {
                    cr = ca.alloc(learnt_clause, false);
                    permanentLearnts.push(cr);
                    stats[nbPermanentLearnts]++;
                } else {
                    cr = ca.alloc(learnt_clause, true);
                    ca[cr].setLBD(nblevels);
                    ca[cr].setOneWatched(false);
                    learnts.push(cr);
                    claBumpActivity(ca[cr]);
                }
#ifdef INCREMENTAL
                ca[cr].setSizeWithoutSelectors(szWithoutSelectors);
#endif
                if(nblevels <= 2) { stats[nbDL2]++; } // stats
                if(ca[cr].size() == 2) stats[nbBin]++; // stats
                attachClause(cr);
                lastLearntClause = cr; // Use in multithread (to hard to put inside ParallelSolver)


                parallelExportClauseDuringSearch(ca[cr]);
                uncheckedEnqueue(learnt_clause[0], cr);

            }
            varDecayActivity();
            claDecayActivity();


        } else {
            // Restart decision: baseline, adaptive (V1), adaptive-v2, adaptive-v3, fixed-interval, no-heuristic, or adaptive-qre
            bool do_restart = false;
            bool qre_restart = false;
            if(restart_strategy == RESTART_BASELINE) {
                do_restart = (luby_restart && nof_conflicts <= conflictC) ||
                             (!luby_restart && (lbdQueue.isvalid() && ((lbdQueue.getavg() * K) > (sumLBD / conflictsRestarts))));
            } else if(restart_strategy == RESTART_ADAPTIVE_V1) {
                do_restart = checkAdaptiveRestartTrigger();
            } else if(restart_strategy == RESTART_ADAPTIVE_V2) {
                do_restart = checkAdaptiveRestartTriggerV2();
            } else if(restart_strategy == RESTART_ADAPTIVE_V3) {
                do_restart = checkAdaptiveRestartTriggerV3();
            } else if(restart_strategy == RESTART_FIXED_INTERVAL) {
                if(fixed_conflicts_since_restart >= (uint64_t)fixed_restart_interval) {
                    fixed_restart_requests++;
                    do_restart = true;
                }
            } else if(restart_strategy == RESTART_NO_HEURISTIC) {
                do_restart = false;
            } else if(restart_strategy == RESTART_ADAPTIVE_QRE || restart_strategy == RESTART_ADAPTIVE_QRE_GATED) {
                // 1. Native Glucose baseline restart condition is strictly preserved
                bool native_restart = (luby_restart && nof_conflicts <= conflictC) ||
                                      (!luby_restart && (lbdQueue.isvalid() && ((lbdQueue.getavg() * K) > (sumLBD / conflictsRestarts))));
                if(native_restart) {
                    qre_native_restart_requests++;
                    do_restart = true;
                    qre_restart = false;
                } else if(restart_strategy == RESTART_ADAPTIVE_QRE_GATED ? checkAdaptiveRestartTriggerQREGated() : checkAdaptiveRestartTriggerQRE()) {
                    do_restart = true;
                    qre_restart = true;
                }
            } else if(restart_strategy == RESTART_PORTFOLIO_MAB || portfolio_shadow_mode) {
                bool native_restart = (luby_restart && nof_conflicts <= conflictC) ||
                                      (!luby_restart && (lbdQueue.isvalid() && ((lbdQueue.getavg() * K) > (sumLBD / conflictsRestarts))));
                do_restart = checkRestartPortfolioMAB(native_restart);
            }

            if(do_restart) {
                if(restart_trace) {
                    if(restart_strategy == RESTART_PORTFOLIO_MAB) {
                        printf("c [RESTART_TRACE] conflict=%llu reason=PORTFOLIO_MAB arm=%d starts=%llu\n",
                               (unsigned long long)conflicts, mab_current_arm, (unsigned long long)starts);
                    } else if(restart_strategy == RESTART_ADAPTIVE_QRE || restart_strategy == RESTART_ADAPTIVE_QRE_GATED) {
                        const char* strat_name = (restart_strategy == RESTART_ADAPTIVE_QRE_GATED) ? "ADAPTIVE_QRE_GATED" : "ADAPTIVE_QRE";
                        if(qre_restart) {
                            printf("c [RESTART_TRACE] conflict=%llu reason=%s starts=%llu consec=%u cfc_since_rst=%llu\n",
                                   (unsigned long long)conflicts, strat_name, (unsigned long long)starts, (unsigned int)qre_consecutive_both, (unsigned long long)qre_conflicts_since_genuine_restart);
                        } else {
                            printf("c [RESTART_TRACE] conflict=%llu reason=%s_NATIVE starts=%llu\n",
                                   (unsigned long long)conflicts, strat_name, (unsigned long long)starts);
                        }
                    } else if(restart_strategy == RESTART_ADAPTIVE_V3) {
                        printf("c [RESTART_TRACE] conflict=%llu reason=ADAPTIVE_V3_%s starts=%llu dd=%.4f fast=%.4f slow=%.4f consec=%u\n",
                               (unsigned long long)conflicts, v3_last_trigger_reason, (unsigned long long)starts, v3_drawdown, v3_ewma_fast, v3_ewma_slow, (unsigned int)v3_consec_drawdown);
                    } else if(restart_strategy == RESTART_FIXED_INTERVAL) {
                        printf("c [RESTART_TRACE] conflict=%llu reason=FIXED_INTERVAL starts=%llu\n",
                               (unsigned long long)conflicts, (unsigned long long)starts);
                    } else if(restart_strategy == RESTART_ADAPTIVE_V2) {
                        printf("c [RESTART_TRACE] conflict=%llu reason=ADAPTIVE_V2 starts=%llu\n",
                               (unsigned long long)conflicts, (unsigned long long)starts);
                    } else if(restart_strategy == RESTART_ADAPTIVE_V1) {
                        printf("c [RESTART_TRACE] conflict=%llu reason=ADAPTIVE_V1 starts=%llu\n",
                               (unsigned long long)conflicts, (unsigned long long)starts);
                    } else {
                        printf("c [RESTART_TRACE] conflict=%llu reason=BASELINE starts=%llu\n",
                               (unsigned long long)conflicts, (unsigned long long)starts);
                    }
                }
                if(restart_strategy == RESTART_ADAPTIVE_QRE || restart_strategy == RESTART_ADAPTIVE_QRE_GATED) {
                    if(qre_restart) {
                        qre_executed_restarts++;
                    }
                    onGenuineRestartQRE();
                    lbdQueue.fastclear();
                } else if(restart_strategy == RESTART_ADAPTIVE_V3) {
                    resetAdaptiveRestartDescentV3();
                } else if(restart_strategy == RESTART_ADAPTIVE_V2) {
                    resetAdaptiveRestartDescentV2();
                } else if(restart_strategy == RESTART_ADAPTIVE_V1) {
                    resetAdaptiveRestartDescent();
                } else if(restart_strategy == RESTART_FIXED_INTERVAL) {
                    resetFixedRestartDescent();
                    fixed_executed_restarts++;
                } else {
                    lbdQueue.fastclear();
                }
                if(v3_shadow_mode && restart_strategy != RESTART_ADAPTIVE_V3) {
                    onActualRestartV3Shadow();
                }
                if(qre_shadow_mode || isAnyAdaptiveQRE()) {
                    onRestartQRE();
                }
                if(isAnyAdaptiveQRE()) {
                    onGenuineRestartQRE();
                }
                progress_estimate = progressEstimate();
                int bt = 0;
#ifdef INCREMENTAL
                if(incremental) // DO NOT BACKTRACK UNTIL 0.. USELESS
                    bt = (decisionLevel()<assumptions.size()) ? decisionLevel() : assumptions.size();
#endif
                newDescent = true;

                if(randomize_on_restarts || fixed_randomize_on_restarts) {
                    randomDescentAssignments = (uint32_t) drand(random_seed);
                }

                cancelUntil(bt);
                return l_Undef;
            }


            // Simplify the set of problem clauses:
            if(decisionLevel() == 0 && !simplify()) {
                return l_False;
            }
            // Perform clause database reduction !
            if((chanseokStrategy && !glureduce && learnts.size() > firstReduceDB) ||
               (glureduce && conflicts >= ((unsigned int) curRestart * nbclausesbeforereduce))) {

                if(learnts.size() > 0) {
                    curRestart = (conflicts / nbclausesbeforereduce) + 1;
                    reduceDB();
                    performLCM = 1;
                    if(!panicModeIsEnabled())
                        nbclausesbeforereduce += incReduceDB;
                }
            }

            lastLearntClause = CRef_Undef;
            Lit next = lit_Undef;
            while(decisionLevel() < assumptions.size()) {
                // Perform user provided assumption:
                Lit p = assumptions[decisionLevel()];
                if(value(p) == l_True) {
                    // Dummy decision level:
                    newDecisionLevel();
                } else if(value(p) == l_False) {
                    analyzeFinal(~p, conflict);
                    return l_False;
                } else {
                    next = p;
                    break;
                }
            }

            if(next == lit_Undef) {
                // New variable decision:
                decisions++;
                next = pickBranchLit();
                if(next == lit_Undef) {
                    printf("c last restart ## conflicts  :  %d %d \n", conflictC, decisionLevel());
                    // Model found:
                    return l_True;
                }
            }

            // Increase decision level and enqueue 'next'
            aDecisionWasMade = true;
            newDecisionLevel();
            uncheckedEnqueue(next);
            if(qre_shadow_mode || isAnyAdaptiveQRE()) {
                qre_pending_decision = true;
                qre_last_decision_props = propagations;
            }
        }
    }
}


double Solver::progressEstimate() const {
    double progress = 0;
    double F = 1.0 / nVars();

    for(int i = 0; i <= decisionLevel(); i++) {
        int beg = i == 0 ? 0 : trail_lim[i - 1];
        int end = i == decisionLevel() ? trail.size() : trail_lim[i];
        progress += pow(F, i) * (end - beg);
    }

    return progress / nVars();
}


void Solver::printIncrementalStats() {

    printf("c---------- Glucose Stats -------------------------\n");
    printf("c restarts              : %"
    PRIu64
    "\n", starts);
    printf("c nb ReduceDB           : %"
    PRIu64
    "\n", stats[nbReduceDB]);
    printf("c nb removed Clauses    : %"
    PRIu64
    "\n", stats[nbRemovedClauses]);
    printf("c nb learnts DL2        : %"
    PRIu64
    "\n", stats[nbDL2]);
    printf("c nb learnts size 2     : %"
    PRIu64
    "\n", stats[nbBin]);
    printf("c nb learnts size 1     : %"
    PRIu64
    "\n", stats[nbUn]);

    printf("c conflicts             : %"
    PRIu64
    "\n", conflicts);
    printf("c decisions             : %"
    PRIu64
    "\n", decisions);
    printf("c propagations          : %"
    PRIu64
    "\n", propagations);

    printf("\nc SAT Calls             : %d in %g seconds\n", nbSatCalls, totalTime4Sat);
    printf("c UNSAT Calls           : %d in %g seconds\n", nbUnsatCalls, totalTime4Unsat);

    printf("c--------------------------------------------------\n");
}


double Solver::luby(double y, int x) {

    // Find the finite subsequence that contains index 'x', and the
    // size of that subsequence:
    int size, seq;
    for(size = 1, seq = 0; size < x + 1; seq++, size = 2 * size + 1);

    while(size - 1 != x) {
        size = (size - 1) >> 1;
        seq--;
        x = x % size;
    }

    return pow(y, seq);
}


// NOTE: assumptions passed in member-variable 'assumptions'.

lbool Solver::solve_(bool do_simp, bool turn_off_simp) // Parameters are useless in core but useful for SimpSolver....
{

    if(incremental && certifiedUNSAT) {
        printf("Can not use incremental and certified unsat in the same time\n");
        exit(-1);
    }

    model.clear();
    conflict.clear();
    if(!ok) return l_False;
    double curTime = cpuTime();

    solves++;

    if(isAdaptiveRestart()) {
        adapt_last_props = propagations;
        adapt_conflicts_since_restart = 0;
        clearAdaptiveWindow();
        adapt_global_sum_props = 0;
        adapt_global_mean_level = 0.0;
        adapt_global_m2_level = 0.0;
    }

    if(isAdaptiveV2()) {
        v2_req_progress = 0;
        v2_req_quality = 0;
        v2_req_ceiling = 0;
        v2_total_requests = 0;
        v2_executed_restarts = 0;
        v2_blocked_restarts = 0;
        v2_max_observed_interval = 0;
    }

    if(adaptive_reduce_mode) {
        adapt_reduce_calls = 0;
        adapt_clauses_considered = 0;
        adapt_clauses_eligible = 0;
        adapt_clauses_removed = 0;
        adapt_spared_locked = 0;
        adapt_spared_binary = 0;
        adapt_spared_glue = 0;
        adapt_spared_canbedel = 0;
        adapt_last_retained = 0;
        adapt_last_avg_retained_lbd = 0.0;
        adapt_last_avg_deleted_lbd = 0.0;
        adapt_reduce_time = 0.0;
        adapt_postpone_evals = 0;
        adapt_postpone_satisfied = 0;
        adapt_postpone_inc_db = 0;
    }

    if(isAdaptiveV3()) {
        initAdaptiveRestartV3();
        v3_last_props = propagations;
    } else if(v3_shadow_mode) {
        initV3Shadow();
        v3_last_props = propagations;
    }
    if(qre_shadow_mode || isAnyAdaptiveQRE()) {
        initQREShadow();
        initQREActive();
    }


    lbool status = l_Undef;
    if(!incremental && verbosity >= 1) {
        printf("c ========================================[ MAGIC CONSTANTS ]==============================================\n");
        printf("c | Constants are supposed to work well together :-)                                                      |\n");
        printf("c | however, if you find better choices, please let us known...                                           |\n");
        printf("c |-------------------------------------------------------------------------------------------------------|\n");
        if(adaptStrategies) {
            printf("c | Adapt dynamically the solver after 100000 conflicts (restarts, reduction strategies...)               |\n");
            printf("c |-------------------------------------------------------------------------------------------------------|\n");
        }
        printf("c |                                |                                |                                     |\n");
        printf("c | - Restarts:                    | - Reduce Clause DB:            | - Minimize Asserting:               |\n");
        if(chanseokStrategy) {
            printf("c |   * LBD Queue    : %6d      |     chanseok Strategy          |    * size < %3d                     |\n", lbdQueue.maxSize(),
                   lbSizeMinimizingClause);
            printf("c |   * Trail  Queue : %6d      |   * learnts size     : %6d  |    * lbd  < %3d                     |\n", trailQueue.maxSize(),
                   firstReduceDB, lbLBDMinimizingClause);
            printf("c |   * K            : %6.2f      |   * Bound LBD   : %6d       |                                     |\n", K, coLBDBound);
            printf("c |   * R            : %6.2f      |   * Protected :  (lbd)< %2d     |                                     |\n", R, lbLBDFrozenClause);
        } else if(restart_strategy == RESTART_ADAPTIVE_V1) {
            printf("c |   * Strategy     :   adaptive   |   * First     : %6d         |    * size < %3d                     |\n",
                   nbclausesbeforereduce, lbSizeMinimizingClause);
            printf("c |   * Theta        : %6.2f      |   * Inc       : %6d         |    * lbd  < %3d                     |\n", adapt_theta, incReduceDB,
                   lbLBDMinimizingClause);
            printf("c |   * Min Interval : %6d      |   * Special   : %6d         |                                     |\n", adapt_min_interval, specialIncReduceDB);
            printf("c |   * Warmup       : %6d      |   * Protected :  (lbd)< %2d     |                                     |\n", adapt_warmup, lbLBDFrozenClause);
        } else if(restart_strategy == RESTART_ADAPTIVE_V2) {
            printf("c |   * Strategy     : adaptive-v2  |   * First     : %6d         |    * size < %3d                     |\n",
                   nbclausesbeforereduce, lbSizeMinimizingClause);
            printf("c |   * Fallback LBD : %6s      |   * Inc       : %6d         |    * lbd  < %3d                     |\n",
                   v2_quality_fallback ? "on" : "off", incReduceDB, lbLBDMinimizingClause);
            printf("c |   * Ceiling      : %6s      |   * Special   : %6d         |                                     |\n",
                   v2_conflict_ceiling ? "on" : "off", specialIncReduceDB);
            printf("c |   * Max Conflicts: %6d      |   * Protected :  (lbd)< %2d     |                                     |\n",
                   v2_max_conflicts, lbLBDFrozenClause);
        } else {
            printf("c |   * LBD Queue    : %6d      |   * First     : %6d         |    * size < %3d                     |\n", lbdQueue.maxSize(),
                   nbclausesbeforereduce, lbSizeMinimizingClause);
            printf("c |   * Trail  Queue : %6d      |   * Inc       : %6d         |    * lbd  < %3d                     |\n", trailQueue.maxSize(), incReduceDB,
                   lbLBDMinimizingClause);
            printf("c |   * K            : %6.2f      |   * Special   : %6d         |                                     |\n", K, specialIncReduceDB);
            printf("c |   * R            : %6.2f      |   * Protected :  (lbd)< %2d     |                                     |\n", R, lbLBDFrozenClause);
        }
        printf("c |                                |                                |                                     |\n");
        printf("c ==================================[ Search Statistics (every %6d conflicts) ]=========================\n", verbEveryConflicts);
        printf("c |                                                                                                       |\n");

        printf("c |          RESTARTS           |          ORIGINAL         |              LEARNT              | Progress |\n");
        printf("c |       NB   Blocked  Avg Cfc |    Vars  Clauses Literals |   Red   Learnts    LBD2  Removed |          |\n");
        printf("c =========================================================================================================\n");
    }

    // Search:
    int curr_restarts = 0;
    while(status == l_Undef) {
        status = search(
                luby_restart ? luby(restart_inc, curr_restarts) * luby_restart_factor : 0); // the parameter is useless in glucose, kept to allow modifications

        if(!withinBudget()) break;
        curr_restarts++;
    }

    if (isPortfolioMAB() || portfolio_shadow_mode) {
        endMABInterval(true);
    }

    if(!incremental && verbosity >= 1)
        printf("c =========================================================================================================\n");

    if(certifiedUNSAT) { // Want certified output
        if(status == l_False) {
            if(vbyte) {
                write_char('a');
                write_lit(0);
            }
            else {
                fprintf(certifiedOutput, "0\n");
            }
        }
        fclose(certifiedOutput);
    }


    if(status == l_True) {
        // Extend & copy model:
        model.growTo(nVars());
        for(int i = 0; i < nVars(); i++) model[i] = value(i);
    } else if(status == l_False && conflict.size() == 0)
        ok = false;


    cancelUntil(0);


    double finalTime = cpuTime();
    if(status == l_True) {
        nbSatCalls++;
        totalTime4Sat += (finalTime - curTime);
    }
    if(status == l_False) {
        nbUnsatCalls++;
        totalTime4Unsat += (finalTime - curTime);
    }

    if(isAdaptiveV2()) {
        if(adapt_conflicts_since_restart > v2_max_observed_interval) {
            v2_max_observed_interval = adapt_conflicts_since_restart;
        }
    }

    return status;

}





//=================================================================================================
// Writing CNF to DIMACS:
//
// FIXME: this needs to be rewritten completely.

static Var mapVar(Var x, vec <Var> &map, Var &max) {
    if(map.size() <= x || map[x] == -1) {
        map.growTo(x + 1, -1);
        map[x] = max++;
    }
    return map[x];
}


void Solver::toDimacs(FILE *f, Clause &c, vec <Var> &map, Var &max) {
    if(satisfied(c)) return;

    for(int i = 0; i < c.size(); i++)
        if(value(c[i]) != l_False)
            fprintf(f, "%s%d ", sign(c[i]) ? "-" : "", mapVar(var(c[i]), map, max) + 1);
    fprintf(f, "0\n");
}


void Solver::toDimacs(const char *file, const vec <Lit> &assumps) {
    FILE *f = fopen(file, "wr");
    if(f == NULL)
        fprintf(stderr, "could not open file %s\n", file), exit(1);
    toDimacs(f, assumps);
    fclose(f);
}


void Solver::toDimacs(FILE *f, const vec <Lit> &assumps) {
    // Handle case when solver is in contradictory state:
    if(!ok) {
        fprintf(f, "p cnf 1 2\n1 0\n-1 0\n");
        return;
    }

    vec <Var> map;
    Var max = 0;

    // Cannot use removeClauses here because it is not safe
    // to deallocate them at this point. Could be improved.
    int cnt = 0;
    for(int i = 0; i < clauses.size(); i++)
        if(!satisfied(ca[clauses[i]]))
            cnt++;

    for(int i = 0; i < clauses.size(); i++)
        if(!satisfied(ca[clauses[i]])) {
            Clause &c = ca[clauses[i]];
            for(int j = 0; j < c.size(); j++)
                if(value(c[j]) != l_False)
                    mapVar(var(c[j]), map, max);
        }

    // Assumptions are added as unit clauses:
    cnt += assumptions.size();

    fprintf(f, "p cnf %d %d\n", max, cnt);

    for(int i = 0; i < assumptions.size(); i++) {
        assert(value(assumptions[i]) != l_False);
        fprintf(f, "%s%d 0\n", sign(assumptions[i]) ? "-" : "", mapVar(var(assumptions[i]), map, max) + 1);
    }

    for(int i = 0; i < clauses.size(); i++)
        toDimacs(f, ca[clauses[i]], map, max);

    if(verbosity > 0)
        printf("Wrote %d clauses with %d variables.\n", cnt, max);
}


//=================================================================================================
// Garbage Collection methods:

void Solver::relocAll(ClauseAllocator &to) {
    // All watchers:
    // for (int i = 0; i < watches.size(); i++)
    watches.cleanAll();
    watchesBin.cleanAll();
    unaryWatches.cleanAll();
    for(int v = 0; v < nVars(); v++)
        for(int s = 0; s < 2; s++) {
            Lit p = mkLit(v, s);
            // printf(" >>> RELOCING: %s%d\n", sign(p)?"-":"", var(p)+1);
            vec <Watcher> &ws = watches[p];
            for(int j = 0; j < ws.size(); j++)
                ca.reloc(ws[j].cref, to);
            vec <Watcher> &ws2 = watchesBin[p];
            for(int j = 0; j < ws2.size(); j++)
                ca.reloc(ws2[j].cref, to);
            vec <Watcher> &ws3 = unaryWatches[p];
            for(int j = 0; j < ws3.size(); j++)
                ca.reloc(ws3[j].cref, to);
        }

    // All reasons:
    //
    for(int i = 0; i < trail.size(); i++) {
        Var v = var(trail[i]);

        if(reason(v) != CRef_Undef && (ca[reason(v)].reloced() || locked(ca[reason(v)])))
            ca.reloc(vardata[v].reason, to);
    }

    // All learnt:
    //
    for(int i = 0; i < learnts.size(); i++)
        ca.reloc(learnts[i], to);

    for(int i = 0; i < permanentLearnts.size(); i++)
        ca.reloc(permanentLearnts[i], to);

    for(int i = 0; i < permanentLearntsReduced.size(); i++)
        ca.reloc(permanentLearntsReduced[i], to);

    // All original:
    //
    for(int i = 0; i < clauses.size(); i++)
        ca.reloc(clauses[i], to);

    for(int i = 0; i < unaryWatchedClauses.size(); i++)
        ca.reloc(unaryWatchedClauses[i], to);
}


void Solver::garbageCollect() {
    // Initialize the next region to a size corresponding to the estimated utilization degree. This
    // is not precise but should avoid some unnecessary reallocations for the new region:
    ClauseAllocator to(ca.size() - ca.wasted());
    relocAll(to);
    if(verbosity >= 2)
        printf("|  Garbage collection:   %12d bytes => %12d bytes             |\n",
               ca.size() * ClauseAllocator::Unit_Size, to.size() * ClauseAllocator::Unit_Size);
    to.moveTo(ca);
}

//--------------------------------------------------------------
// Functions related to MultiThread.
// Useless in case of single core solver (aka original glucose)
// Keep them empty if you just use core solver
//--------------------------------------------------------------

bool Solver::panicModeIsEnabled() {
    return false;
}


void Solver::parallelImportUnaryClauses() {
}


bool Solver::parallelImportClauses() {
    return false;
}


void Solver::parallelExportUnaryClause(Lit) {
}


void Solver::parallelExportClauseDuringSearch(Clause &) {
}


bool Solver::parallelJobIsFinished() {
    // Parallel: another job has finished let's quit
    return false;
}


void Solver::parallelImportClauseDuringConflictAnalysis(Clause &, CRef ) {
}

//=================================================================================================
// Adaptive Nogood (Clause Reduction) Controller:

void Solver::initAdaptiveReduceController() {
    adaptive_reduce_mode = false;
    adapt_reduce_calls = 0;
    adapt_clauses_considered = 0;
    adapt_clauses_eligible = 0;
    adapt_clauses_removed = 0;
    adapt_spared_locked = 0;
    adapt_spared_binary = 0;
    adapt_spared_glue = 0;
    adapt_spared_canbedel = 0;
    adapt_last_retained = 0;
    adapt_last_avg_retained_lbd = 0.0;
    adapt_last_avg_deleted_lbd = 0.0;
    adapt_reduce_time = 0.0;
    adapt_postpone_evals = 0;
    adapt_postpone_satisfied = 0;
    adapt_postpone_inc_db = 0;
}

//=================================================================================================
// Adaptive Restart Controller:

void Solver::initAdaptiveRestartController() {
    adaptive_restart_mode = false;
    adapt_theta = 0.60;
    adapt_min_interval = 50;
    adapt_warmup = 100;
    adaptive_restarts = 0;
    adaptive_restart_requests = 0;
    last_adapt_score_w = 0.0;
    last_adapt_score_global = 0.0;
    adapt_last_props = 0;
    adapt_win_head = 0;
    adapt_win_size = 0;
    for(int i = 0; i < ADAPT_WIN_CAPACITY; i++) {
        adapt_win_props[i] = 0;
        adapt_win_levels[i] = 0;
    }
    adapt_conflicts_since_restart = 0;
    adapt_global_sum_props = 0;
    adapt_global_mean_level = 0.0;
    adapt_global_m2_level = 0.0;
}

void Solver::clearAdaptiveWindow() {
    adapt_win_head = 0;
    adapt_win_size = 0;
}

void Solver::updateAdaptiveRestartController(int conflict_level) {
    if(!adaptive_restart_mode) return;

    uint64_t delta_p = 0;
    if(propagations >= adapt_last_props) {
        delta_p = propagations - adapt_last_props;
    }
    adapt_last_props = propagations;

    adapt_win_props[adapt_win_head] = delta_p;
    adapt_win_levels[adapt_win_head] = conflict_level;
    adapt_win_head = (adapt_win_head + 1) % ADAPT_WIN_CAPACITY;
    if(adapt_win_size < ADAPT_WIN_CAPACITY) {
        adapt_win_size++;
    }

    adapt_conflicts_since_restart++;
    adapt_global_sum_props += delta_p;

    // Welford's online algorithm for running mean and sum of squared differences (population variance)
    double x = (double)conflict_level;
    double delta1 = x - adapt_global_mean_level;
    adapt_global_mean_level += delta1 / (double)conflicts;
    double delta2 = x - adapt_global_mean_level;
    adapt_global_m2_level += delta1 * delta2;
}

bool Solver::checkAdaptiveRestartTrigger() {
    if(!adaptive_restart_mode) return false;

    // Guard 1: Minimum warmup period
    if(conflicts < (uint64_t)adapt_warmup)
        return false;

    // Guard 2: Full sliding window
    if(adapt_win_size < ADAPT_WIN_CAPACITY)
        return false;

    // Guard 3: Anti-thrashing minimum interval between restarts
    if(adapt_conflicts_since_restart < (uint64_t)adapt_min_interval)
        return false;

    // Calculate window statistics (Search Progress E_W and Instability sigma_W)
    double sum_p = 0.0;
    double sum_l = 0.0;
    double sum_l_sq = 0.0;
    for(int i = 0; i < ADAPT_WIN_CAPACITY; i++) {
        sum_p += (double)adapt_win_props[i];
        double lvl = (double)adapt_win_levels[i];
        sum_l += lvl;
        sum_l_sq += lvl * lvl;
    }

    double mean_p = sum_p / (double)ADAPT_WIN_CAPACITY;
    double mean_l = sum_l / (double)ADAPT_WIN_CAPACITY;
    double var_l = (sum_l_sq / (double)ADAPT_WIN_CAPACITY) - (mean_l * mean_l);
    if(var_l < 0.0) var_l = 0.0;
    double std_l = sqrt(var_l);

    // Risk-adjusted efficiency score over window (epsilon = 1.0 prevents division by zero)
    double s_w = mean_p / (std_l + 1.0);

    // Calculate global cumulative baseline statistics (search propagations and Welford variance)
    double total_c = (double)conflicts; // guaranteed >= adapt_warmup >= 100 > 0
    double global_mean_p = (double)adapt_global_sum_props / total_c;
    double global_var_l = adapt_global_m2_level / total_c;
    if(global_var_l < 0.0) global_var_l = 0.0;
    double global_std_l = sqrt(global_var_l);

    // Global risk-adjusted efficiency score
    double s_global = global_mean_p / (global_std_l + 1.0);

    last_adapt_score_w = s_w;
    last_adapt_score_global = s_global;

    // Trigger restart if recent efficiency drops below theta * global baseline
    if(s_w < adapt_theta * s_global) {
        adaptive_restart_requests++;
        return true;
    }
    return false;
}

void Solver::resetAdaptiveRestartDescent() {
    adaptive_restarts++;
    adapt_conflicts_since_restart = 0;
    clearAdaptiveWindow();
    lbdQueue.fastclear();
}

void Solver::initAdaptiveRestartV2() {
    v2_quality_fallback = true;
    v2_conflict_ceiling = true;
    v2_max_conflicts = 2500;
    v2_fallback_lbd_k = 0.80;
    v2_req_progress = 0;
    v2_req_quality = 0;
    v2_req_ceiling = 0;
    v2_total_requests = 0;
    v2_executed_restarts = 0;
    v2_blocked_restarts = 0;
    v2_max_observed_interval = 0;
}

bool Solver::checkAdaptiveRestartTriggerV2() {
    if(restart_strategy != RESTART_ADAPTIVE_V2) return false;

    bool trig_ceiling = false;
    bool trig_quality = false;
    bool trig_progress = false;

    // Trigger 1: Anti-Starvation Conflict Ceiling
    // Operates independently of rolling window validity to cure sterile subtree traps.
    if(v2_conflict_ceiling && adapt_conflicts_since_restart >= (uint64_t)v2_max_conflicts) {
        trig_ceiling = true;
    }

    // Trigger 2: Learned-Clause Quality Fallback
    // Restores Glucose LBD quality sensitivity when trapped in unproductive resolution.
    if(v2_quality_fallback &&
       conflicts >= (uint64_t)adapt_warmup &&
       adapt_conflicts_since_restart >= (uint64_t)adapt_min_interval &&
       lbdQueue.isvalid()) {
        if((lbdQueue.getavg() * v2_fallback_lbd_k) > (sumLBD / conflictsRestarts)) {
            trig_quality = true;
        }
    }

    // Trigger 3: V1 Progress Degradation Trigger
    // Maintains Sharpe-ratio efficiency controller for structured formulas.
    if(conflicts >= (uint64_t)adapt_warmup &&
       adapt_win_size >= ADAPT_WIN_CAPACITY &&
       adapt_conflicts_since_restart >= (uint64_t)adapt_min_interval) {

        double sum_p = 0.0;
        double sum_l = 0.0;
        double sum_l_sq = 0.0;
        for(int i = 0; i < ADAPT_WIN_CAPACITY; i++) {
            sum_p += (double)adapt_win_props[i];
            double lvl = (double)adapt_win_levels[i];
            sum_l += lvl;
            sum_l_sq += lvl * lvl;
        }

        double mean_p = sum_p / (double)ADAPT_WIN_CAPACITY;
        double mean_l = sum_l / (double)ADAPT_WIN_CAPACITY;
        double var_l = (sum_l_sq / (double)ADAPT_WIN_CAPACITY) - (mean_l * mean_l);
        if(var_l < 0.0) var_l = 0.0;
        double std_l = sqrt(var_l);

        double s_w = mean_p / (std_l + 1.0);

        double total_c = (double)conflicts;
        double global_mean_p = (double)adapt_global_sum_props / total_c;
        double global_var_l = adapt_global_m2_level / total_c;
        if(global_var_l < 0.0) global_var_l = 0.0;
        double global_std_l = sqrt(global_var_l);

        double s_global = global_mean_p / (global_std_l + 1.0);

        last_adapt_score_w = s_w;
        last_adapt_score_global = s_global;

        if(s_w < adapt_theta * s_global) {
            trig_progress = true;
        }
    }

    if(trig_ceiling || trig_quality || trig_progress) {
        if(trig_ceiling)  v2_req_ceiling++;
        if(trig_quality)  v2_req_quality++;
        if(trig_progress) v2_req_progress++;
        v2_total_requests++;
        return true;
    }

    return false;
}

void Solver::resetAdaptiveRestartDescentV2() {
    v2_executed_restarts++;
    if(adapt_conflicts_since_restart > v2_max_observed_interval) {
        v2_max_observed_interval = adapt_conflicts_since_restart;
    }
    adapt_conflicts_since_restart = 0;
    clearAdaptiveWindow();
    lbdQueue.fastclear();
}

//=================================================================================================
// Finance-Inspired Adaptive Restart V3 (Shadow-Mode Diagnostics)

void Solver::initV3Shadow() {
    v3_valid_obs = 0;
    v3_invalid_obs = 0;
    v3_sum_return = 0.0;
    v3_min_return = 0.0;
    v3_max_return = 0.0;
    v3_ewma_fast = 0.0;
    v3_ewma_slow = 0.0;
    v3_hwm = 0.0;
    v3_drawdown = 0.0;
    v3_max_drawdown = 0.0;
    v3_consec_drawdown = 0;
    v3_conflicts_since_actual_restart = 0;
    v3_conflicts_since_hyp_event = 0;
    v3_raw_cond_drawdown = 0;
    v3_raw_cond_trend = 0;
    v3_raw_cond_ceiling = 0;
    v3_hyp_events_total = 0;
    v3_hyp_events_drawdown = 0;
    v3_hyp_events_trend = 0;
    v3_hyp_events_ceiling = 0;
    v3_last_props = propagations;
}

void Solver::initAdaptiveRestartV3() {
    v3_req_trend = 0;
    v3_req_drawdown = 0;
    v3_req_ceiling = 0;
    v3_total_requests = 0;
    v3_executed_restarts = 0;
    v3_blocked_restarts = 0;
    v3_max_observed_interval = 0;
    v3_conflicts_since_restart = 0;
    v3_last_trigger_reason = "NONE";
    initV3Shadow();
}

bool Solver::checkAdaptiveRestartTriggerV3() {
    if(restart_strategy != RESTART_ADAPTIVE_V3) return false;

    bool trig_ceiling = false;
    bool trig_drawdown = false;
    bool trig_trend = false;

    // Trigger 1: Anti-Starvation Conflict Ceiling
    // Operates independently of EWMA validity, warmup, or cooldown.
    if(v3_opt_ceiling && v3_conflicts_since_restart >= 2500) {
        trig_ceiling = true;
    }

    // Statistical Triggers: Require warmup (conflicts >= 100), minimum cooldown (v3_conflicts_since_restart >= 50),
    // and sufficient valid observations (v3_valid_obs >= 50).
    if(conflicts >= 100 && v3_conflicts_since_restart >= 50 && v3_valid_obs >= 50) {
        // Trigger 2: Sustained Drawdown Collapse (30 consecutive eligible observations >= 0.75)
        if(v3_opt_drawdown && v3_consec_drawdown >= 30) {
            trig_drawdown = true;
        }

        // Trigger 3: Dual-Horizon Trend Deterioration (fast < 0.60 * slow)
        if(v3_opt_trend && (v3_ewma_fast < 0.60 * v3_ewma_slow)) {
            trig_trend = true;
        }
    }

    if(trig_ceiling || trig_drawdown || trig_trend) {
        if(trig_drawdown && trig_trend && trig_ceiling) v3_last_trigger_reason = "DRAWDOWN+TREND+CEILING";
        else if(trig_drawdown && trig_trend)            v3_last_trigger_reason = "DRAWDOWN+TREND";
        else if(trig_drawdown && trig_ceiling)          v3_last_trigger_reason = "DRAWDOWN+CEILING";
        else if(trig_trend && trig_ceiling)             v3_last_trigger_reason = "TREND+CEILING";
        else if(trig_drawdown)                          v3_last_trigger_reason = "DRAWDOWN";
        else if(trig_trend)                             v3_last_trigger_reason = "TREND";
        else if(trig_ceiling)                           v3_last_trigger_reason = "CEILING";
        else                                            v3_last_trigger_reason = "UNKNOWN";

        if(trig_ceiling)  v3_req_ceiling++;
        if(trig_drawdown) v3_req_drawdown++;
        if(trig_trend)    v3_req_trend++;
        v3_total_requests++;
        return true;
    }

    return false;
}

void Solver::resetAdaptiveRestartDescentV3() {
    v3_executed_restarts++;
    if(v3_conflicts_since_restart > v3_max_observed_interval) {
        v3_max_observed_interval = v3_conflicts_since_restart;
    }
    v3_conflicts_since_restart = 0;
    v3_consec_drawdown = 0;
    // Reset HWM to current fast EWMA to maintain descent-local peak (EWMAs persist globally)
    v3_hwm = v3_ewma_fast;
    lbdQueue.fastclear();
}

void Solver::updateV3Indicators(int lbd, int pre_level, int backtrack_level) {
    if(!isAdaptiveV3() && !v3_shadow_mode) return;

    if(isAdaptiveV3()) {
        v3_conflicts_since_restart++;
    }

    // 1. Delta propagations strictly since last conflict
    uint64_t cur_props = propagations;
    uint64_t delta_p = (cur_props >= v3_last_props) ? (cur_props - v3_last_props) : 0;
    v3_last_props = cur_props;

    // 2. Backjump distance
    int raw_delta_d = pre_level - backtrack_level;
    double delta_d = (raw_delta_d > 0) ? (double)raw_delta_d : 0.0;

    // 3. LBD Quality factor
    double eff_lbd = (lbd < 1) ? 1.0 : (double)lbd;
    double q_lbd = 2.0 / eff_lbd;

    // 4. Return computation
    double boost = 1.0 + log(1.0 + delta_d);
    double work = 1.0 + ((double)delta_p / 25.0);
    double r_t = (q_lbd * boost) / work;

    // 5. Numerical validation
    if(!isfinite(r_t) || r_t < 0.0) {
        v3_invalid_obs++;
        return;
    }

    if(v3_valid_obs == 0) {
        v3_min_return = r_t;
        v3_max_return = r_t;
    } else {
        if(r_t < v3_min_return) v3_min_return = r_t;
        if(r_t > v3_max_return) v3_max_return = r_t;
    }
    v3_sum_return += r_t;
    v3_valid_obs++;
    if(v3_shadow_mode) {
        v3_conflicts_since_actual_restart++;
        v3_conflicts_since_hyp_event++;
    }

    // 6. EWMA and High-Water Mark updates
    if(v3_valid_obs == 1) {
        v3_ewma_fast = r_t;
        v3_ewma_slow = r_t;
        v3_hwm = r_t;
    } else {
        v3_ewma_fast = 0.92 * v3_ewma_fast + 0.08 * r_t;
        v3_ewma_slow = 0.99 * v3_ewma_slow + 0.01 * r_t;
        double decayed_hwm = 0.999 * v3_hwm;
        v3_hwm = (v3_ewma_fast > decayed_hwm) ? v3_ewma_fast : decayed_hwm;
    }

    // 7. Relative Drawdown computation
    double cur_dd = 0.0;
    if(v3_hwm > v3_ewma_fast) {
        cur_dd = (v3_hwm - v3_ewma_fast) / (v3_hwm + 0.05);
    }
    v3_drawdown = cur_dd;
    if(cur_dd > v3_max_drawdown) {
        v3_max_drawdown = cur_dd;
    }
    if(cur_dd >= 0.75) {
        v3_consec_drawdown++;
    } else {
        v3_consec_drawdown = 0;
    }

    // 8. Raw hypothetical conditions (for shadow mode)
    if(v3_shadow_mode) {
        bool cond_drawdown = (v3_consec_drawdown >= 30);
        bool cond_trend = (v3_ewma_fast < 0.60 * v3_ewma_slow);
        bool cond_ceiling = (v3_conflicts_since_actual_restart >= 2500);

        if(cond_drawdown) v3_raw_cond_drawdown++;
        if(cond_trend)    v3_raw_cond_trend++;
        if(cond_ceiling)  v3_raw_cond_ceiling++;

        // 9. Virtual trigger event policy (cooldown = 50 conflicts, warmup = 100 conflicts)
        if(conflicts >= 100 && v3_conflicts_since_hyp_event >= 50) {
            if(cond_drawdown || cond_trend || cond_ceiling) {
                v3_hyp_events_total++;
                if(cond_drawdown) v3_hyp_events_drawdown++;
                if(cond_trend)    v3_hyp_events_trend++;
                if(cond_ceiling)  v3_hyp_events_ceiling++;
                v3_conflicts_since_hyp_event = 0;
            }
        }
    }
}

void Solver::onActualRestartV3Shadow() {
    v3_conflicts_since_actual_restart = 0;
    v3_consec_drawdown = 0;
    // Reset HWM to current fast EWMA to maintain descent-local peak
    v3_hwm = v3_ewma_fast;
}

// Frequency-Controlled Restart Baselines & Telemetry (Step 32)
void Solver::initFixedRestartController() {
    fixed_restart_interval = 10000;
    fixed_conflicts_since_restart = 0;
    fixed_restart_requests = 0;
    fixed_executed_restarts = 0;
    fixed_blocked_restarts = 0;
    fixed_max_observed_interval = 0;
    strategy_adaptation_restarts = 0;
}

void Solver::resetFixedRestartDescent() {
    if(fixed_conflicts_since_restart > fixed_max_observed_interval) {
        fixed_max_observed_interval = fixed_conflicts_since_restart;
    }
    fixed_conflicts_since_restart = 0;
}

//=================================================================================================
// Quantitative Risk Engine (QRE) Shadow-Mode Instrumentation (Step 38)
// Mathematical Architecture from Technical Report:
// 1. Sharpe Signal: S_branch = (SMA_10(R) - SMA_50(R)) / max(0.75, stddev_10(decision_depth))
// 2. Conflict Shock: Shock_t = LBD_t / max(1, decisions_since_previous_conflict)
// 3. Predictive VaR_95: VaR_95 >= 3.2 AND VaR_95 >= 1.6 * median(shocks) (12-conflict rolling window)
// 4. Dynamic Cooldown: C_min = 14 + floor(2 * log2(1 + restart_count))
//=================================================================================================

void Solver::initQREShadow() {
    qre_pending_decision = false;
    qre_decisions_observed = 0;
    qre_last_decision_props = propagations;
    qre_r_idx_50 = 0;
    qre_sum_r_50 = 0.0;
    for (int i = 0; i < 50; i++) qre_r_hist_50[i] = 0.0;
    qre_r_idx_10 = 0;
    qre_sum_r_10 = 0.0;
    for (int i = 0; i < 10; i++) qre_r_hist_10[i] = 0.0;

    qre_depth_idx_10 = 0;
    qre_sum_depth_10 = 0.0;
    qre_sum_sq_depth_10 = 0.0;
    for (int i = 0; i < 10; i++) qre_depth_hist_10[i] = 0.0;

    qre_conflicts_observed = 0;
    qre_last_conflict_decisions = decisions;
    qre_shock_idx_12 = 0;
    qre_total_shocks = 0;
    for (int i = 0; i < 12; i++) qre_shock_hist_12[i] = 0.0;

    qre_conflicts_since_restart = 0;

    qre_sharpe_raw_triggers = 0;
    qre_var_raw_triggers = 0;
    qre_both_raw_triggers = 0;

    qre_sharpe_suppressed_startup = 0;
    qre_var_suppressed_startup = 0;
    qre_sharpe_suppressed_cooldown = 0;
    qre_var_suppressed_cooldown = 0;

    qre_eligible_sharpe_requests = 0;
    qre_eligible_var_requests = 0;
    qre_eligible_either_requests = 0;
    qre_eligible_both_requests = 0;

    qre_min_sharpe_observed = 1e9;
    qre_max_var95_observed = -1e9;
    qre_last_sharpe = 0.0;
    qre_last_var95 = 0.0;
    qre_last_median_shock = 0.0;
    qre_cmin = 14;
    qre_last_cmin = 14;
}

void Solver::initQREActive() {
    qre_conflicts_since_genuine_restart = 0;
    qre_consecutive_both = 0;
    qre_budget_block = 0;
    qre_restarts_in_block = 0;
    qre_native_restart_requests = 0;
    qre_sustained_events = 0;
    qre_eligible_requests = 0;
    qre_executed_restarts = 0;
    qre_cooldown_suppressions = 0;
    qre_cap_suppressions = 0;
    qre_last_trigger_reason = "NONE";
}

void Solver::onGenuineRestartQRE() {
    qre_conflicts_since_genuine_restart = 0;
    qre_consecutive_both = 0;
    qre_conflicts_since_restart = 0;
}

bool Solver::checkAdaptiveRestartTriggerQRE() {
    if (restart_strategy != RESTART_ADAPTIVE_QRE) return false;

    // Signal 1 & 2: Both Sharpe and VaR conditions must be active simultaneously
    bool sharpe_active = (qre_decisions_observed >= 50 && qre_last_sharpe < -0.35);
    bool var_active = false;
    if (qre_total_shocks >= 12) {
        if (qre_last_var95 >= 3.2 && qre_last_var95 >= 1.6 * qre_last_median_shock) {
            var_active = true;
        }
    }

    if (!sharpe_active || !var_active) {
        return false;
    }

    // Safeguard 1: Require 8 consecutive eligible conflict observations
    if (qre_consecutive_both < 8) {
        return false;
    }
    qre_sustained_events++;

    // Safeguard 2: Require at least 500 conflicts since the last genuine restart
    if (qre_conflicts_since_genuine_restart < 500) {
        qre_cooldown_suppressions++;
        return false;
    }
    qre_eligible_requests++;

    // Safeguard 3: Permit at most 5 additional QRE-triggered restarts per 10,000 total conflicts
    uint64_t current_block = conflicts / 10000;
    if (current_block != qre_budget_block) {
        qre_budget_block = current_block;
        qre_restarts_in_block = 0;
    }

    if (qre_restarts_in_block >= 5) {
        qre_cap_suppressions++;
        return false;
    }

    qre_restarts_in_block++;
    qre_last_trigger_reason = "QRE_SHARPE_VAR_SUSTAINED_8";
    return true;
}

bool Solver::checkAdaptiveRestartTriggerQREGated() {
    if (restart_strategy != RESTART_ADAPTIVE_QRE_GATED) return false;

    // Signal 1 & 2: Both Sharpe and VaR conditions must be active simultaneously
    bool sharpe_active = (qre_decisions_observed >= 50 && qre_last_sharpe < -0.35);
    bool var_active = false;
    if (qre_total_shocks >= 12) {
        if (qre_last_var95 >= 3.2 && qre_last_var95 >= 1.6 * qre_last_median_shock) {
            var_active = true;
        }
    }

    if (!sharpe_active || !var_active) {
        return false;
    }

    // Safeguard 1: Require 8 consecutive eligible conflict observations
    if (qre_consecutive_both < 8) {
        return false;
    }
    qre_sustained_events++;

    // Safeguard 2 (Stagnation Gate): Require at least 1,500 conflicts since the last genuine restart
    if (qre_conflicts_since_genuine_restart < 1500) {
        qre_cooldown_suppressions++;
        return false;
    }
    qre_eligible_requests++;

    // Safeguard 3 (Frequency Budget): Permit at most 2 additional QRE-triggered restarts per 10,000 total conflicts
    uint64_t current_block = conflicts / 10000;
    if (current_block != qre_budget_block) {
        qre_budget_block = current_block;
        qre_restarts_in_block = 0;
    }

    if (qre_restarts_in_block >= 2) {
        qre_cap_suppressions++;
        return false;
    }

    qre_restarts_in_block++;
    qre_last_trigger_reason = "QRE_GATED_SHARPE_VAR_SUSTAINED_8";
    return true;
}

void Solver::onDecisionQRE(double delta_p, int depth) {
    if (!qre_shadow_mode && !isAnyAdaptiveQRE()) return;

    qre_decisions_observed++;

    // 1. Update 50-step SMA for R (unit propagations per decision)
    if (qre_decisions_observed > 50) {
        qre_sum_r_50 -= qre_r_hist_50[qre_r_idx_50];
    }
    qre_r_hist_50[qre_r_idx_50] = delta_p;
    qre_sum_r_50 += delta_p;
    qre_r_idx_50 = (qre_r_idx_50 + 1) % 50;

    // 2. Update 10-step SMA for R
    if (qre_decisions_observed > 10) {
        qre_sum_r_10 -= qre_r_hist_10[qre_r_idx_10];
    }
    qre_r_hist_10[qre_r_idx_10] = delta_p;
    qre_sum_r_10 += delta_p;
    qre_r_idx_10 = (qre_r_idx_10 + 1) % 10;

    // 3. Update 10-step depth volatility
    double d = (double)depth;
    if (qre_decisions_observed > 10) {
        qre_sum_depth_10 -= qre_depth_hist_10[qre_depth_idx_10];
        qre_sum_sq_depth_10 -= (qre_depth_hist_10[qre_depth_idx_10] * qre_depth_hist_10[qre_depth_idx_10]);
    }
    qre_depth_hist_10[qre_depth_idx_10] = d;
    qre_sum_depth_10 += d;
    qre_sum_sq_depth_10 += (d * d);
    qre_depth_idx_10 = (qre_depth_idx_10 + 1) % 10;

    // 4. Compute Sharpe ratio if window is populated (>= 10 steps, fully populated at 50)
    if (qre_decisions_observed >= 10) {
        double var_d = (qre_sum_sq_depth_10 - (qre_sum_depth_10 * qre_sum_depth_10) * 0.1) * (1.0 / 9.0);
        double denom = 0.75;
        if (var_d > 0.5625) { // 0.75^2 = 0.5625; avoids sqrt when variance is below floor
            denom = sqrt(var_d);
        }

        double sma_10 = qre_sum_r_10 * 0.1;
        double sma_50 = (qre_decisions_observed >= 50) ? (qre_sum_r_50 * 0.02) : (qre_sum_r_50 / (double)qre_decisions_observed);
        double s_branch = (sma_10 - sma_50) / denom;

        qre_last_sharpe = s_branch;
        if (s_branch < qre_min_sharpe_observed) {
            qre_min_sharpe_observed = s_branch;
        }
    }
}

void Solver::onConflictQRE(int lbd) {
    if (!qre_shadow_mode && !isAnyAdaptiveQRE()) return;

    qre_conflicts_observed++;
    qre_conflicts_since_restart++;
    qre_conflicts_since_genuine_restart++;

    // 1. Conflict shock calculation:
    // Shock_t = LBD_t / max(1, decisions_since_previous_conflict)
    uint64_t cur_dec = decisions;
    uint64_t delta_dec = (cur_dec >= qre_last_conflict_decisions) ? (cur_dec - qre_last_conflict_decisions) : 0;
    qre_last_conflict_decisions = cur_dec;

    double eff_delta_dec = (delta_dec < 1) ? 1.0 : (double)delta_dec;
    double eff_lbd = (lbd < 1) ? 1.0 : (double)lbd;
    double shock_t = eff_lbd / eff_delta_dec;

    // 2. Rolling window of 12 conflicts
    qre_shock_hist_12[qre_shock_idx_12] = shock_t;
    qre_shock_idx_12 = (qre_shock_idx_12 + 1) % 12;
    qre_total_shocks++;

    // 3. Evaluate VaR_95 if window is full (12 shocks)
    bool var_cond = false;
    double var95 = 0.0;
    double median_shock = 0.0;

    if (qre_total_shocks >= 12) {
        // Fast pre-filter: find max_shock across 12 elements (nearest-rank 95th percentile is max)
        double max_shock = qre_shock_hist_12[0];
        for (int i = 1; i < 12; i++) {
            if (qre_shock_hist_12[i] > max_shock) max_shock = qre_shock_hist_12[i];
        }
        var95 = max_shock;
        qre_last_var95 = var95;
        if (var95 > qre_max_var95_observed) {
            qre_max_var95_observed = var95;
        }

        // Only sort when max_shock >= 3.2 to compute exact median; otherwise var_cond is false
        if (max_shock >= 3.2) {
            double s[12];
            for (int i = 0; i < 12; i++) s[i] = qre_shock_hist_12[i];
            for (int i = 1; i < 12; i++) {
                double key = s[i];
                int j = i - 1;
                while (j >= 0 && s[j] > key) {
                    s[j + 1] = s[j];
                    j--;
                }
                s[j + 1] = key;
            }
            median_shock = (s[5] + s[6]) * 0.5;
            qre_last_median_shock = median_shock;

            if (var95 >= 3.2 && var95 >= 1.6 * median_shock) {
                var_cond = true;
            }
        }
    }

    // 4. Evaluate Sharpe condition
    bool sharpe_cond = false;
    bool sharpe_startup = (qre_decisions_observed < 50);
    if (!sharpe_startup && qre_last_sharpe < -0.35) {
        sharpe_cond = true;
    }

    // 5. Update consecutive both persistence counter
    if (sharpe_cond && var_cond) {
        qre_consecutive_both++;
    } else {
        qre_consecutive_both = 0;
    }

    // 6. Dynamic Logarithmic Cooldown C_min for shadow-mode reporting
    bool cooldown_ok = (qre_conflicts_since_restart >= qre_cmin);

    // 7. Update Raw trigger counters
    if (sharpe_cond) qre_sharpe_raw_triggers++;
    if (var_cond)    qre_var_raw_triggers++;
    if (sharpe_cond && var_cond) qre_both_raw_triggers++;

    // 8. Update Startup suppression counters
    if (qre_last_sharpe < -0.35 && sharpe_startup) {
        qre_sharpe_suppressed_startup++;
    }
    if (qre_total_shocks < 12 && shock_t >= 3.2) {
        qre_var_suppressed_startup++;
    }

    // 9. Update Cooldown suppression counters
    if (sharpe_cond && !sharpe_startup && !cooldown_ok) {
        qre_sharpe_suppressed_cooldown++;
    }
    if (var_cond && !cooldown_ok) {
        qre_var_suppressed_cooldown++;
    }

    // 10. Eligible hypothetical requests
    bool sharpe_eligible = (sharpe_cond && !sharpe_startup && cooldown_ok);
    bool var_eligible = (var_cond && cooldown_ok);

    if (sharpe_eligible) qre_eligible_sharpe_requests++;
    if (var_eligible)    qre_eligible_var_requests++;
    if (sharpe_eligible || var_eligible) qre_eligible_either_requests++;
    if (sharpe_eligible && var_eligible) qre_eligible_both_requests++;
}

void Solver::onRestartQRE() {
    if (!qre_shadow_mode && !isAnyAdaptiveQRE()) return;
    qre_conflicts_since_restart = 0;
    qre_conflicts_since_genuine_restart = 0;
    qre_consecutive_both = 0;

    // Pre-calculate c_min once per restart to avoid calling log2() on every conflict
    uint64_t r_count = (starts > 0) ? (starts - 1) : 0;
    qre_cmin = (uint32_t)(14.0 + floor(2.0 * log2(1.0 + (double)r_count)));
    qre_last_cmin = qre_cmin;
}

// =========================================================================
// Portfolio-MAB: Duration-Aware Two-Armed Bandit Restart Controller (Step 44)
// =========================================================================

void Solver::initPortfolioMAB() {
    portfolio_mab_mode = (restart_strategy == RESTART_PORTFOLIO_MAB);
    mab_current_arm = MAB_ARM_NATIVE;
    mab_next_arm = MAB_ARM_NATIVE;
    mab_total_intervals = 0;
    mab_arm_selections[0] = 0;
    mab_arm_selections[1] = 0;
    mab_discounted_pulls[0] = 0.0;
    mab_discounted_pulls[1] = 0.0;
    mab_discounted_rewards[0] = 0.0;
    mab_discounted_rewards[1] = 0.0;
    mab_last_ucb[0] = 0.0;
    mab_last_ucb[1] = 0.0;
    mab_last_mean_reward[0] = 0.0;
    mab_last_mean_reward[1] = 0.0;
    mab_gamma = 0.95;
    mab_c_explore = 0.40;
    mab_max_postpone_conflicts = 500;

    mab_total_learned_clauses = 0;
    mab_total_glue_clauses = 0;
    mab_interval_start_conflict = 0;
    mab_interval_start_clauses = 0;
    mab_interval_start_glue = 0;
    mab_interval_start_propagations = 0;
    mab_interval_in_progress = false;

    mab_postponement_active = false;
    mab_postponed_at_conflict = 0;
    mab_postponed_requests = 0;
    mab_executed_postponed_restarts = 0;
    mab_canceled_postponements = 0;
}

void Solver::startMABInterval(int arm) {
    mab_current_arm = arm;
    mab_interval_start_conflict = conflicts;
    mab_interval_start_clauses = mab_total_learned_clauses;
    mab_interval_start_glue = mab_total_glue_clauses;
    mab_interval_start_propagations = propagations;
    mab_interval_in_progress = true;
    mab_arm_selections[arm]++;
    mab_postponement_active = false;
    mab_postponed_at_conflict = 0;
}

void Solver::endMABInterval(bool solver_terminating) {
    if (!mab_interval_in_progress) return;

    uint64_t delta_c = (conflicts >= mab_interval_start_conflict) ? (conflicts - mab_interval_start_conflict) : 0;
    uint64_t delta_clauses = (mab_total_learned_clauses >= mab_interval_start_clauses) ? (mab_total_learned_clauses - mab_interval_start_clauses) : 0;
    uint64_t delta_glue = (mab_total_glue_clauses >= mab_interval_start_glue) ? (mab_total_glue_clauses - mab_interval_start_glue) : 0;

    // Bounded duration-normalized reward
    double raw_reward = 0.0;
    if (delta_c > 0) {
        uint64_t non_glue = (delta_clauses >= delta_glue) ? (delta_clauses - delta_glue) : 0;
        raw_reward = ((double)delta_glue + 0.20 * (double)non_glue) / (double)delta_c;
    }
    double reward = raw_reward;
    if (reward < 0.0) reward = 0.0;
    if (reward > 1.0) reward = 1.0;

    int a = mab_current_arm;

    // Discount accumulated statistics for both arms
    mab_discounted_pulls[0] *= mab_gamma;
    mab_discounted_pulls[1] *= mab_gamma;
    mab_discounted_rewards[0] *= mab_gamma;
    mab_discounted_rewards[1] *= mab_gamma;

    // Add observation to the pulled arm
    mab_discounted_pulls[a] += 1.0;
    mab_discounted_rewards[a] += reward;

    mab_last_mean_reward[0] = (mab_discounted_pulls[0] > 1e-6) ? (mab_discounted_rewards[0] / mab_discounted_pulls[0]) : 0.0;
    mab_last_mean_reward[1] = (mab_discounted_pulls[1] > 1e-6) ? (mab_discounted_rewards[1] / mab_discounted_pulls[1]) : 0.0;

    double n_total = mab_discounted_pulls[0] + mab_discounted_pulls[1];
    double ln_n = (n_total > 0.0) ? log(1.0 + n_total) : 0.0;

    mab_last_ucb[0] = mab_last_mean_reward[0] + mab_c_explore * sqrt(ln_n / ((mab_discounted_pulls[0] > 1e-6) ? mab_discounted_pulls[0] : 1e-6));
    mab_last_ucb[1] = mab_last_mean_reward[1] + mab_c_explore * sqrt(ln_n / ((mab_discounted_pulls[1] > 1e-6) ? mab_discounted_pulls[1] : 1e-6));

    mab_total_intervals++;
    mab_interval_in_progress = false;

    if (mab_postponement_active) {
        if (solver_terminating) {
            mab_canceled_postponements++;
        }
        mab_postponement_active = false;
    }

    // Select next arm
    if (mab_total_intervals == 1) {
        // Initial deterministic exploration: Interval 0 was Arm 0, Interval 1 must be Arm 1
        mab_next_arm = MAB_ARM_BOUNDED_DESCENT;
    } else {
        // Discounted UCB selection (tie-breaker defaults to Arm 0)
        mab_next_arm = (mab_last_ucb[1] > mab_last_ucb[0]) ? MAB_ARM_BOUNDED_DESCENT : MAB_ARM_NATIVE;
    }
}

bool Solver::checkRestartPortfolioMAB(bool native_restart) {
    if (!mab_interval_in_progress) {
        startMABInterval(mab_next_arm);
    }

    if (portfolio_shadow_mode) {
        // Shadow mode: Never alters restart decision!
        // Always honors native_restart immediately.
        if (native_restart) {
            endMABInterval(false);
            startMABInterval(mab_next_arm);
            return true;
        }
        return false;
    }

    // Active Portfolio-MAB mode
    if (mab_current_arm == MAB_ARM_NATIVE) {
        if (native_restart) {
            endMABInterval(false);
            startMABInterval(mab_next_arm);
            return true;
        }
        return false;
    }

    // Arm 1: MAB_ARM_BOUNDED_DESCENT
    if (mab_postponement_active) {
        // Postponement is active: check 500-conflict budget
        if (conflicts - mab_postponed_at_conflict >= mab_max_postpone_conflicts) {
            // Budget exhausted: MUST execute postponed restart now
            mab_executed_postponed_restarts++;
            endMABInterval(false);
            startMABInterval(mab_next_arm);
            return true;
        }
        if (native_restart) {
            // Already postponed once; do not postpone a second time in a row
            mab_executed_postponed_restarts++;
            endMABInterval(false);
            startMABInterval(mab_next_arm);
            return true;
        }
        // Still within budget and no forced trigger
        return false;
    } else {
        // No postponement active yet
        if (native_restart) {
            // Check safety guards before postponing
            // Must have valid LBD stats, decisionLevel > 0, and not strategy adaptation
            if (lbdQueue.isvalid() && decisionLevel() > 0 && conflicts != 100000) {
                // Postpone restart! Extend descent!
                mab_postponement_active = true;
                mab_postponed_at_conflict = conflicts;
                mab_postponed_requests++;
                if (restart_trace) {
                    printf("c [RESTART_TRACE] conflict=%llu reason=MAB_POSTPONE arm=1\n", (unsigned long long)conflicts);
                }
                return false;
            } else {
                // Unsafe to postpone: execute restart immediately
                endMABInterval(false);
                startMABInterval(mab_next_arm);
                return true;
            }
        }
        return false;
    }
}
