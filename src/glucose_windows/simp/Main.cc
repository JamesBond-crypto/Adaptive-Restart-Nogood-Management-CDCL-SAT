/***************************************************************************************[Main.cc]
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

#include <errno.h>

#include <signal.h>
#include <zlib.h>
#ifndef _WIN32
#include <sys/resource.h>
#endif

#include "utils/System.h"
#include "utils/ParseUtils.h"
#include "utils/Options.h"
#include "core/Dimacs.h"
#include "simp/SimpSolver.h"

using namespace Glucose;

//=================================================================================================

static const char* _certified = "CORE -- CERTIFIED UNSAT";

void printStats(Solver& solver)
{
    double cpu_time = cpuTime();
    double mem_used = memUsedPeak();
    printf("c restarts              : %" PRIu64" (%" PRIu64" conflicts in avg)\n", solver.starts,(solver.starts>0 ?solver.conflicts/solver.starts : 0));
    printf("c genuine restarts      : %" PRIu64"\n", solver.starts > 0 ? solver.starts - 1 : 0);
    printf("c blocked restarts      : %" PRIu64" (multiple: %" PRIu64") \n", solver.stats[nbstopsrestarts],solver.stats[nbstopsrestartssame]);
    printf("c last block at restart : %" PRIu64"\n",solver.stats[lastblockatrestart]);
    if (solver.restart_strategy == Solver::RESTART_ADAPTIVE_V2) {
        solver.updateV2MaxInterval();
    }
    if (solver.restart_strategy == Solver::RESTART_ADAPTIVE_V3) {
        solver.updateV3MaxInterval();
    }
    if (solver.restart_strategy == Solver::RESTART_FIXED_INTERVAL || solver.restart_strategy == Solver::RESTART_NO_HEURISTIC) {
        solver.updateFixedMaxInterval();
    }
    if (solver.restart_strategy == Solver::RESTART_ADAPTIVE_V1) {
        printf("c restart strategy      : adaptive (theta=%.2f, min_interval=%d, warmup=%d)\n",
               solver.adapt_theta, solver.adapt_min_interval, solver.adapt_warmup);
        printf("c adaptive restart requests: %" PRIu64"\n", solver.adaptive_restart_requests);
        printf("c adaptive restarts     : %" PRIu64"\n", solver.adaptive_restarts);
        printf("c last adaptive score   : %.4f (global: %.4f)\n", solver.last_adapt_score_w, solver.last_adapt_score_global);
    } else if (solver.restart_strategy == Solver::RESTART_ADAPTIVE_V2) {
        printf("c restart strategy      : adaptive-v2 (theta=%.2f, min_interval=%d, warmup=%d)\n",
               solver.adapt_theta, solver.adapt_min_interval, solver.adapt_warmup);
        printf("c v2 quality fallback   : %s (k=%.2f)\n", solver.v2_quality_fallback ? "enabled" : "disabled", solver.v2_fallback_lbd_k);
        printf("c v2 conflict ceiling   : %s (max_conflicts=%d)\n", solver.v2_conflict_ceiling ? "enabled" : "disabled", solver.v2_max_conflicts);
        printf("c v2 req progress       : %" PRIu64"\n", solver.v2_req_progress);
        printf("c v2 req quality        : %" PRIu64"\n", solver.v2_req_quality);
        printf("c v2 req ceiling        : %" PRIu64"\n", solver.v2_req_ceiling);
        printf("c v2 total requests     : %" PRIu64"\n", solver.v2_total_requests);
        printf("c v2 executed restarts  : %" PRIu64"\n", solver.v2_executed_restarts);
        printf("c v2 blocked restarts   : %" PRIu64"\n", solver.v2_blocked_restarts);
        printf("c v2 max interval       : %" PRIu64"\n", solver.v2_max_observed_interval);
        printf("c last adaptive score   : %.4f (global: %.4f)\n", solver.last_adapt_score_w, solver.last_adapt_score_global);
    } else if (solver.restart_strategy == Solver::RESTART_ADAPTIVE_V3) {
        printf("c restart strategy      : adaptive-v3 (trend=%s, drawdown=%s, ceiling=%s)\n",
               solver.v3_opt_trend ? "enabled" : "disabled",
               solver.v3_opt_drawdown ? "enabled" : "disabled",
               solver.v3_opt_ceiling ? "enabled" : "disabled");
        printf("c v3 req trend          : %" PRIu64"\n", solver.v3_req_trend);
        printf("c v3 req drawdown       : %" PRIu64"\n", solver.v3_req_drawdown);
        printf("c v3 req ceiling        : %" PRIu64"\n", solver.v3_req_ceiling);
        printf("c v3 total requests     : %" PRIu64"\n", solver.v3_total_requests);
        printf("c v3 executed restarts  : %" PRIu64"\n", solver.v3_executed_restarts);
        printf("c v3 blocked restarts   : %" PRIu64"\n", solver.v3_blocked_restarts);
        printf("c v3 max interval       : %" PRIu64"\n", solver.v3_max_observed_interval);
        printf("c v3 valid return obs   : %" PRIu64"\n", solver.v3_valid_obs);
        double mean_r = (solver.v3_valid_obs > 0) ? (solver.v3_sum_return / (double)solver.v3_valid_obs) : 0.0;
        printf("c v3 mean return        : %.4f\n", mean_r);
        printf("c v3 final fast ewma    : %.4f\n", solver.v3_ewma_fast);
        printf("c v3 final slow ewma    : %.4f\n", solver.v3_ewma_slow);
        printf("c v3 max observed dd    : %.4f\n", solver.v3_max_drawdown);
    } else if (solver.restart_strategy == Solver::RESTART_FIXED_INTERVAL) {
        printf("c restart strategy      : fixed-interval (interval=%d)\n", solver.fixed_restart_interval);
        printf("c fixed restart interval: %d\n", solver.fixed_restart_interval);
        printf("c fixed restart requests: %" PRIu64"\n", solver.fixed_restart_requests);
        printf("c fixed executed restarts: %" PRIu64"\n", solver.fixed_executed_restarts);
        printf("c fixed blocked restarts : %" PRIu64"\n", solver.fixed_blocked_restarts);
        printf("c strategy adapt restarts: %" PRIu64"\n", solver.strategy_adaptation_restarts);
        printf("c fixed max interval     : %" PRIu64"\n", solver.fixed_max_observed_interval);
        printf("c fixed cfc since restart: %" PRIu64"\n", solver.fixed_conflicts_since_restart);
    } else if (solver.restart_strategy == Solver::RESTART_NO_HEURISTIC) {
        printf("c restart strategy      : no-heuristic-restart\n");
        printf("c fixed restart interval: 0\n");
        printf("c fixed restart requests: 0\n");
        printf("c fixed executed restarts: 0\n");
        printf("c fixed blocked restarts : 0\n");
        printf("c strategy adapt restarts: %" PRIu64"\n", solver.strategy_adaptation_restarts);
        printf("c fixed max interval     : %" PRIu64"\n", solver.fixed_max_observed_interval);
        printf("c fixed cfc since restart: %" PRIu64"\n", solver.fixed_conflicts_since_restart);
    } else if (solver.isAdaptiveQRE() || solver.isAdaptiveQREGated()) {
        printf("c restart strategy      : %s\n", solver.isAdaptiveQREGated() ? "adaptive-qre-gated" : "adaptive-qre");
        printf("c qre native requests   : %" PRIu64"\n", solver.qre_native_restart_requests);
        printf("c qre raw sharpe events : %" PRIu64"\n", solver.qre_sharpe_raw_triggers);
        printf("c qre raw var events    : %" PRIu64"\n", solver.qre_var_raw_triggers);
        printf("c qre raw both events   : %" PRIu64"\n", solver.qre_both_raw_triggers);
        printf("c qre sustained events  : %" PRIu64"\n", solver.qre_sustained_events);
        printf("c qre eligible requests : %" PRIu64"\n", solver.qre_eligible_requests);
        printf("c qre executed restarts : %" PRIu64"\n", solver.qre_executed_restarts);
        printf("c qre cooldown supp     : %" PRIu64"\n", solver.qre_cooldown_suppressions);
        printf("c qre freq cap supp     : %" PRIu64"\n", solver.qre_cap_suppressions);
        printf("c qre strategy adapt rst: %" PRIu64"\n", solver.strategy_adaptation_restarts);
    } else if (solver.isPortfolioMAB()) {
        printf("c restart strategy      : portfolio-mab\n");
        printf("c mab arm 0 selections  : %" PRIu64"\n", solver.mab_arm_selections[0]);
        printf("c mab arm 1 selections  : %" PRIu64"\n", solver.mab_arm_selections[1]);
        printf("c mab total intervals   : %" PRIu64"\n", solver.mab_total_intervals);
        printf("c mab postponed requests: %" PRIu64"\n", solver.mab_postponed_requests);
        printf("c mab executed postp rst: %" PRIu64"\n", solver.mab_executed_postponed_restarts);
        printf("c mab canceled postp rst: %" PRIu64"\n", solver.mab_canceled_postponements);
        printf("c mab arm 0 mean reward : %.6f\n", solver.mab_last_mean_reward[0]);
        printf("c mab arm 1 mean reward : %.6f\n", solver.mab_last_mean_reward[1]);
        printf("c mab arm 0 final ucb   : %.6f\n", solver.mab_last_ucb[0]);
        printf("c mab arm 1 final ucb   : %.6f\n", solver.mab_last_ucb[1]);
        printf("c mab next arm          : %d\n", solver.mab_next_arm);
    } else {
        printf("c restart strategy      : baseline\n");
    }
    if (solver.v3_shadow_mode) {
        printf("c v3 shadow             : enabled\n");
        printf("c v3 shadow valid obs   : %" PRIu64"\n", solver.v3_valid_obs);
        printf("c v3 shadow invalid obs : %" PRIu64"\n", solver.v3_invalid_obs);
        double mean_r = (solver.v3_valid_obs > 0) ? (solver.v3_sum_return / (double)solver.v3_valid_obs) : 0.0;
        printf("c v3 shadow mean return : %.4f\n", mean_r);
        printf("c v3 shadow min return  : %.4f\n", solver.v3_min_return);
        printf("c v3 shadow max return  : %.4f\n", solver.v3_max_return);
        printf("c v3 shadow final fast  : %.4f\n", solver.v3_ewma_fast);
        printf("c v3 shadow final slow  : %.4f\n", solver.v3_ewma_slow);
        printf("c v3 shadow max drawdown: %.4f\n", solver.v3_max_drawdown);
        printf("c v3 raw cond drawdown  : %" PRIu64"\n", solver.v3_raw_cond_drawdown);
        printf("c v3 raw cond trend     : %" PRIu64"\n", solver.v3_raw_cond_trend);
        printf("c v3 raw cond ceiling   : %" PRIu64"\n", solver.v3_raw_cond_ceiling);
        printf("c v3 hyp event total    : %" PRIu64"\n", solver.v3_hyp_events_total);
        printf("c v3 hyp event drawdown : %" PRIu64"\n", solver.v3_hyp_events_drawdown);
        printf("c v3 hyp event trend    : %" PRIu64"\n", solver.v3_hyp_events_trend);
        printf("c v3 hyp event ceiling  : %" PRIu64"\n", solver.v3_hyp_events_ceiling);
    } else {
        printf("c v3 shadow             : disabled\n");
    }
    if (solver.qre_shadow_mode) {
        printf("c qre shadow            : enabled\n");
        printf("c qre decisions obs     : %" PRIu64"\n", solver.qre_decisions_observed);
        printf("c qre conflicts obs     : %" PRIu64"\n", solver.qre_conflicts_observed);
        printf("c qre total shocks      : %" PRIu64"\n", solver.qre_total_shocks);
        printf("c qre raw sharpe trig   : %" PRIu64"\n", solver.qre_sharpe_raw_triggers);
        printf("c qre raw var trig      : %" PRIu64"\n", solver.qre_var_raw_triggers);
        printf("c qre raw both trig     : %" PRIu64"\n", solver.qre_both_raw_triggers);
        printf("c qre supp sharpe start : %" PRIu64"\n", solver.qre_sharpe_suppressed_startup);
        printf("c qre supp var start    : %" PRIu64"\n", solver.qre_var_suppressed_startup);
        printf("c qre supp sharpe cd    : %" PRIu64"\n", solver.qre_sharpe_suppressed_cooldown);
        printf("c qre supp var cd       : %" PRIu64"\n", solver.qre_var_suppressed_cooldown);
        printf("c qre elig sharpe req   : %" PRIu64"\n", solver.qre_eligible_sharpe_requests);
        printf("c qre elig var req      : %" PRIu64"\n", solver.qre_eligible_var_requests);
        printf("c qre elig either req   : %" PRIu64"\n", solver.qre_eligible_either_requests);
        printf("c qre elig both req     : %" PRIu64"\n", solver.qre_eligible_both_requests);
        printf("c qre min sharpe obs    : %.4f\n", (solver.qre_min_sharpe_observed > 1e8) ? 0.0 : solver.qre_min_sharpe_observed);
        printf("c qre max var95 obs     : %.4f\n", (solver.qre_max_var95_observed < -1e8) ? 0.0 : solver.qre_max_var95_observed);
        printf("c qre final sharpe      : %.4f\n", solver.qre_last_sharpe);
        printf("c qre final var95       : %.4f\n", solver.qre_last_var95);
        printf("c qre final median shock: %.4f\n", solver.qre_last_median_shock);
        printf("c qre final cmin        : %u\n", solver.qre_last_cmin);
    } else {
        printf("c qre shadow            : disabled\n");
    }
    if (solver.portfolio_shadow_mode) {
        printf("c portfolio shadow      : enabled\n");
        printf("c mab shadow intervals  : %" PRIu64"\n", solver.mab_total_intervals);
        printf("c mab shadow arm0 pulls : %.2f\n", solver.mab_discounted_pulls[0]);
        printf("c mab shadow arm1 pulls : %.2f\n", solver.mab_discounted_pulls[1]);
        printf("c mab shadow arm0 reward: %.6f\n", solver.mab_last_mean_reward[0]);
        printf("c mab shadow arm1 reward: %.6f\n", solver.mab_last_mean_reward[1]);
        printf("c mab shadow arm0 ucb   : %.6f\n", solver.mab_last_ucb[0]);
        printf("c mab shadow arm1 ucb   : %.6f\n", solver.mab_last_ucb[1]);
    } else {
        printf("c portfolio shadow      : disabled\n");
    }
    if (solver.adaptive_reduce_mode) {
        if (solver.reduce_strategy_mode == Solver::REDUCE_ADAPTIVE_FIXED) {
            printf("c reduction strategy    : adaptive-fixed\n");
        } else {
            printf("c reduction strategy    : adaptive\n");
        }
        printf("c adapt reduce calls    : %" PRIu64"\n", solver.adapt_reduce_calls);
        printf("c adapt clauses ranked  : %" PRIu64"\n", solver.adapt_clauses_considered);
        printf("c adapt clauses eligible: %" PRIu64"\n", solver.adapt_clauses_eligible);
        printf("c adapt clauses removed : %" PRIu64"\n", solver.adapt_clauses_removed);
        printf("c adapt spared locked   : %" PRIu64"\n", solver.adapt_spared_locked);
        printf("c adapt spared binary   : %" PRIu64"\n", solver.adapt_spared_binary);
        printf("c adapt spared glue     : %" PRIu64"\n", solver.adapt_spared_glue);
        printf("c adapt spared canbedel : %" PRIu64"\n", solver.adapt_spared_canbedel);
        printf("c adapt last retained   : %" PRIu64"\n", solver.adapt_last_retained);
        printf("c adapt last avg ret LBD: %.2f\n", solver.adapt_last_avg_retained_lbd);
        printf("c adapt last avg del LBD: %.2f\n", solver.adapt_last_avg_deleted_lbd);
        printf("c adapt reduce time     : %.4f s\n", solver.adapt_reduce_time);
        printf("c adapt postpone evals  : %" PRIu64"\n", solver.adapt_postpone_evals);
        printf("c adapt postpone sat    : %" PRIu64"\n", solver.adapt_postpone_satisfied);
        printf("c adapt postpone inc db : %" PRIu64"\n", solver.adapt_postpone_inc_db);
    } else {
        printf("c reduction strategy    : baseline\n");
    }
    printf("c nb ReduceDB           : %" PRIu64"\n", solver.stats[nbReduceDB]);
    printf("c nb removed Clauses    : %" PRIu64"\n",solver.stats[nbRemovedClauses]);
    printf("c average learnt size   : %" PRIu64"\n", solver.conflicts == 0 ? 0 : solver.stats[sumSizes]/solver.conflicts);
    printf("c nb learnts DL2        : %" PRIu64"\n", solver.stats[nbDL2]);
    printf("c nb learnts size 2     : %" PRIu64"\n", solver.stats[nbBin]);
    printf("c nb learnts size 1     : %" PRIu64"\n", solver.stats[nbUn]);
    if(solver.chanseokStrategy)
        printf("c nb permanent learnts  : %" PRIu64"\n", solver.stats[nbPermanentLearnts]);

    printf("c conflicts             : %-12" PRIu64"   (%.0f /sec)\n", solver.conflicts   , solver.conflicts   /cpu_time);
    printf("c decisions             : %-12" PRIu64"   (%4.2f %% random) (%.0f /sec)\n", solver.decisions, (float)solver.stats[rnd_decisions]*100 / (float)solver.decisions, solver.decisions   /cpu_time);
    printf("c propagations          : %-12" PRIu64"   (%.0f /sec)\n", solver.propagations, solver.propagations/cpu_time);
    //    printf("c conflict literals     : %-12" PRIu64"   (%4.2f %% deleted)\n", solver.stats[tot_literals], (solver.stats[max_literals] - solver.stats[tot_literals])*100 / (double)solver.stats[max_literals]);
    //    printf("c Average resolutions   : %-12" PRIu64"   (%.0f seen ones)\n",solver.stats[sumRes]/solver.conflicts,((double)solver.stats[sumResSeen])/solver.conflicts);
    printf("c nb reduced Clauses    : %" PRIu64"\n",solver.stats[nbReducedClauses]);
    printf("c LCM                   : %" PRIu64" / %" PRIu64" \n", solver.stats[lcmreduced],solver.stats[lcmtested]);
    if (mem_used != 0) printf("c Memory used           : %.2f MB\n", mem_used);
    printf("c CPU time              : %g s\n", cpu_time);
}



static Solver* solver;
// Terminate by notifying the solver and back out gracefully. This is mainly to have a test-case
// for this feature of the Solver as it may take longer than an immediate call to '_exit()'.
static void SIGINT_interrupt(int signum) { solver->interrupt(); }

// Note that '_exit()' rather than 'exit()' has to be used. The reason is that 'exit()' calls
// destructors and may cause deadlocks if a malloc/free function happens to be running (these
// functions are guarded by locks for multithreaded use).
static void SIGINT_exit(int signum) {
    printf("\n"); printf("*** INTERRUPTED ***\n");
    if (solver->verbosity > 0){
        printStats(*solver);
        printf("\n"); printf("*** INTERRUPTED ***\n"); }
    _exit(1); }


//=================================================================================================
// Main:

int main(int argc, char** argv)
{
    try {
      printf("c\nc This is glucose 4.2.1 --  based on MiniSAT (Many thanks to MiniSAT team)\nc\n");


      setUsageHelp("c USAGE: %s [options] <input-file> <result-output-file>\n\n  where input may be either in plain or gzipped DIMACS.\n");


#if defined(__linux__)
        fpu_control_t oldcw, newcw;
        _FPU_GETCW(oldcw); newcw = (oldcw & ~_FPU_EXTENDED) | _FPU_DOUBLE; _FPU_SETCW(newcw);
        //printf("c WARNING: for repeatability, setting FPU to use double precision\n");
#endif
        // Extra options:
        //
        IntOption    verb   ("MAIN", "verb",   "Verbosity level (0=silent, 1=some, 2=more).", 1, IntRange(0, 2));
        BoolOption   mod   ("MAIN", "model",   "show model.", false);
        IntOption    vv  ("MAIN", "vv",   "Verbosity every vv conflicts", 10000, IntRange(1,INT32_MAX));
        BoolOption   pre    ("MAIN", "pre",    "Completely turn on/off any preprocessing.", true);
        StringOption dimacs ("MAIN", "dimacs", "If given, stop after preprocessing and write the result to this file.");
        IntOption    cpu_lim("MAIN", "cpu-lim","Limit on CPU time allowed in seconds.\n", INT32_MAX, IntRange(0, INT32_MAX));
        IntOption    mem_lim("MAIN", "mem-lim","Limit on memory usage in megabytes.\n", INT32_MAX, IntRange(0, INT32_MAX));
 //       BoolOption opt_incremental ("MAIN","incremental", "Use incremental SAT solving",false);

         BoolOption    opt_certified      (_certified, "certified",    "Certified UNSAT using DRUP format", false);
         StringOption  opt_certified_file      (_certified, "certified-output",    "Certified UNSAT output file", "NULL");
         BoolOption    opt_vbyte             (_certified, "vbyte",    "Emit proof in variable-byte encoding", false);

        parseOptions(argc, argv, true);

        SimpSolver  S;
        double      initial_time = cpuTime();

        S.parsing = 1;
        S.use_simplification = pre;

        //if (!pre) S.eliminate(true);

        S.verbosity = verb;
        S.verbEveryConflicts = vv;
	    S.showModel = mod;

        S.certifiedUNSAT = opt_certified;
        S.vbyte = opt_vbyte;
        if(S.certifiedUNSAT) {
            if(!strcmp(opt_certified_file,"NULL")) {
                S.vbyte =  false;  // Cannot write binary to stdout
                S.certifiedOutput =  fopen("/dev/stdout", "wb");
                if(S.verbosity >= 1)
                    printf("c\nc Write unsat proof on stdout using text format\nc\n");
            } else
                S.certifiedOutput =  fopen(opt_certified_file, "wb");
                const char *name = opt_certified_file;
                if(S.verbosity >= 1)
                    printf("c\nc Write unsat proof on %s using %s format\nc\n",name,S.vbyte ? "binary" : "text");
        }

        solver = &S;
        // Use signal handlers that forcibly quit until the solver will be able to respond to
        // interrupts:
        signal(SIGINT, SIGINT_exit);
#ifndef _WIN32
        signal(SIGXCPU,SIGINT_exit);
#endif


#ifndef _WIN32
        // Set limit on CPU-time:
        if (cpu_lim != INT32_MAX){
            rlimit rl;
            getrlimit(RLIMIT_CPU, &rl);
            if (rl.rlim_max == RLIM_INFINITY || (rlim_t)cpu_lim < rl.rlim_max){
                rl.rlim_cur = cpu_lim;
                if (setrlimit(RLIMIT_CPU, &rl) == -1)
                    printf("c WARNING! Could not set resource limit: CPU-time.\n");
            } }

        // Set limit on virtual memory:
        if (mem_lim != INT32_MAX){
            rlimit rl;
            getrlimit(RLIMIT_AS, &rl);
            if (rl.rlim_max == RLIM_INFINITY || new_mem_lim < rl.rlim_max){
                rl.rlim_cur = new_mem_lim;
                if (setrlimit(RLIMIT_AS, &rl) == -1)
                    printf("c WARNING! Could not set resource limit: Virtual memory.\n");
            } }
#else
        if (cpu_lim != INT32_MAX || mem_lim != INT32_MAX) {
            printf("c WARNING! In-process CPU/memory limits are not supported on Windows. Use external timeout wrappers.\n");
        }
#endif

        if (argc == 1)
            printf("c Reading from standard input... Use '--help' for help.\n");

        gzFile in = (argc == 1) ? gzdopen(0, "rb") : gzopen(argv[1], "rb");
        if (in == NULL)
            printf("ERROR! Could not open file: %s\n", argc == 1 ? "<stdin>" : argv[1]), exit(1);

      if (S.verbosity > 0){
            printf("c ========================================[ Problem Statistics ]===========================================\n");
            printf("c |                                                                                                       |\n"); }

        FILE* res = (argc >= 3) ? fopen(argv[argc-1], "wb") : NULL;
        parse_DIMACS(in, S);
        gzclose(in);

       if (S.verbosity > 0){
            printf("c |  Number of variables:  %12d                                                                   |\n", S.nVars());
            printf("c |  Number of clauses:    %12d                                                                   |\n", S.nClauses()); }

        double parsed_time = cpuTime();
        if (S.verbosity > 0){
            printf("c |  Parse time:           %12.2f s                                                                 |\n", parsed_time - initial_time);
            printf("c |                                                                                                       |\n"); }

        // Change to signal-handlers that will only notify the solver and allow it to terminate
        // voluntarily:
        signal(SIGINT, SIGINT_interrupt);
#ifndef _WIN32
        signal(SIGXCPU,SIGINT_interrupt);
#endif

        S.parsing = 0;
        if(pre/* && !S.isIncremental()*/) {
	  printf("c | Preprocesing is fully done\n");
	  S.eliminate(true);
        double simplified_time = cpuTime();
        if (S.verbosity > 0){
            printf("c |  Simplification time:  %12.2f s                                                                 |\n", simplified_time - parsed_time);
 }
	}
	printf("c |                                                                                                       |\n");
        if (!S.okay()){
            if (S.certifiedUNSAT) fprintf(S.certifiedOutput, "0\n"), fclose(S.certifiedOutput);
            if (res != NULL) fprintf(res, "UNSAT\n"), fclose(res);
            if (S.verbosity > 0){
 	        printf("c =========================================================================================================\n");
               printf("Solved by simplification\n");
                printStats(S);
                printf("\n"); }
            printf("s UNSATISFIABLE\n");
            exit(20);
        }

        if (dimacs){
            if (S.verbosity > 0)
                printf("c =======================================[ Writing DIMACS ]===============================================\n");
            S.toDimacs((const char*)dimacs);
            if (S.verbosity > 0)
                printStats(S);
            exit(0);
        }

        vec<Lit> dummy;
        lbool ret = S.solveLimited(dummy);

        if (S.verbosity > 0){
            printStats(S);
            printf("\n"); }
        printf(ret == l_True ? "s SATISFIABLE\n" : ret == l_False ? "s UNSATISFIABLE\n" : "s INDETERMINATE\n");

        if (res != NULL){
            if (ret == l_True){
                printf("SAT\n");
                for (int i = 0; i < S.nVars(); i++)
                    if (S.model[i] != l_Undef)
                        fprintf(res, "%s%s%d", (i==0)?"":" ", (S.model[i]==l_True)?"":"-", i+1);
                fprintf(res, " 0\n");
            } else {
	      if (ret == l_False){
		fprintf(res, "UNSAT\n");
	      }
	    }
            fclose(res);
        } else {
	  if(S.showModel && ret==l_True) {
	    printf("v ");
	    for (int i = 0; i < S.nVars(); i++)
                if (S.model[i] != l_Undef)
		printf("%s%s%d", (i==0)?"":" ", (S.model[i]==l_True)?"":"-", i+1);
              printf(" 0\n");
	  }


        }


#ifdef NDEBUG
        exit(ret == l_True ? 10 : ret == l_False ? 20 : 0);     // (faster than "return", which will invoke the destructor for 'Solver')
#else
        return (ret == l_True ? 10 : ret == l_False ? 20 : 0);
#endif
    } catch (OutOfMemoryException&){
	        printf("c =========================================================================================================\n");
        printf("INDETERMINATE\n");
        exit(0);
    }
}
