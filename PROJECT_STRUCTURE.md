# Project Directory and File Catalog

**Project Title:** Adaptive Restart and Nogood Management for Constraint Satisfaction Solvers  
**Course:** DAC-203: Artificial Intelligence  
**Faculty Advisor:** Prof. Manoj Kumar  
**Researchers:** Manav Garg (25125026) & Kugashiya Bhavy (25125024)  

---

## Directory Overview

```text
DAC_203_Final_Submission/
│
├── README.md                                                        # Primary project introduction, findings, and guide
├── Final_Research_Report.pdf                                        # Official 48-page university research monograph
├── Final_Presentation.pptx                                          # Official 21-slide final academic presentation
├── Final_Presentation.pdf                                           # Matching vector PDF export of presentation slides (21 pages)
├── PROJECT_STRUCTURE.md                                             # This catalog document
├── RESULTS_SUMMARY.md                                               # Executive empirical performance digest
├── REPRODUCE.md                                                     # Complete reproduction instructions
├── PPT_VERIFICATION_REPORT.md                                       # Authoritative 34KB claim & formula verification report
├── .gitignore                                                       # Git exclusion rules for clean version control
│
├── docs/                                                            # Supporting academic documents & visual assets
│   ├── problem_statement/                                           # Original DAC-203 problem statement and images
│   │   └── Problem_Statement.png
│   ├── research_papers/                                             # 4 foundational academic papers studied
│   │   ├── Research_Paper_1.pdf                                     # Tolpin & Shimony (2011) - Rational Heuristics
│   │   ├── Research_Paper_2.pdf                                     # Koriche et al. (2022) - Best Heuristic ID / MAB
│   │   ├── Research_Paper_3.pdf                                     # Kurin et al. (2020) - Graph-Q-SAT / RL
│   │   └── Research_Paper_4.pdf                                     # Wallace et al. (2009) - Dynamic CSPs (IJCAI 2009)
│   ├── reports/                                                     # Detailed technical markdown logs & audits
│   │   ├── FINAL_COMPLETE_RESEARCH_REPORT_REVISED.md                # 129KB revised monograph source
│   │   ├── FINAL_REPORT_DISCREPANCY_REGISTER.md                     # Discrepancy resolution audit
│   │   ├── FINAL_HOLDOUT_EVALUATION_PROTOCOL.md                     # Pre-registered holdout evaluation protocol
│   │   ├── FINAL_HOLDOUT_STATISTICAL_ANALYSIS.md                    # Wilcoxon & bootstrap statistical tests
│   │   ├── QRE_GATED_FULL_DEVELOPMENT_EVALUATION.md                 # Full QRE gated development report
│   │   ├── PORTFOLIO_MAB_FIRST_PILOT.md                             # Multi-Armed Bandit pilot analysis
│   │   └── ... (additional technical phase logs)
│   └── figures/                                                     # 17 high-resolution empirical charts
│       ├── fig_qre_gated_par2_comparison.png                        # QRE development PAR-2 comparison
│       ├── fig_qre_gated_conflict_differences.png                   # Conflict reduction breakdown
│       ├── final_holdout/                                           # 7 holdout evaluation plots (fig01 to fig07)
│       └── presentation/                                            # 5 presentation synthesis plots (fig_pres01 to fig_pres05)
│
├── src/                                                             # C++ Solver Source Code & Build Environment
│   ├── glucose_windows/                                             # Modified Glucose 4.2.1 SAT Solver
│   │   ├── core/                                                    # Core CDCL engine (Solver.cc, Solver.h, SolverStats.h)
│   │   ├── simp/                                                    # CNF simplifier & entry point (Main.cc, SimpSolver.cc)
│   │   ├── mtl/                                                     # MiniSat template library (Vec.h, Alloc.h, Heap.h)
│   │   ├── utils/                                                   # System and option parsers (Options.cc, System.cc)
│   │   ├── parallel/                                                # Multi-threaded solver primitives
│   │   ├── build_windows.bat                                        # Standard MinGW compilation script
│   │   ├── build_qre_gated.bat                                      # Gated QRE compilation script
│   │   ├── build_portfolio_mab.bat                                  # Portfolio-MAB compilation script
│   │   ├── glucose-simp.exe                                         # Release executable (baseline, V1, V2, V3, Adaptive-Fixed)
│   │   ├── glucose-qre-gated.exe                                    # Release executable (Stagnation-Gated QRE)
│   │   ├── glucose-portfolio-mab.exe                                # Release executable (Portfolio-MAB)
│   │   ├── LICENSE                                                  # Glucose / MiniSat MIT license
│   │   └── README.md
│   └── base_solver/                                                 # Pristine reference Glucose 4.2.1 (for code diff / provenance)
│
├── benchmarks/                                                      # Evaluation benchmark suites & generation scripts
│   ├── expanded/                                                    # 36 development instances (648 factorial runs)
│   ├── final_holdout/                                               # 48 unseen holdout instances (acquired via acquire_holdout_suite.py; 1,152 runs)
│   │   ├── holdout_manifest.csv                                     # Benchmark metadata & ground-truth satisfiability
│   │   ├── acquire_holdout_suite.py                                 # Autonomous acquisition harness
│   │   └── validate_holdout_suite.py                                # DIMACS syntax and hash validator
│   ├── pilot/                                                       # 20 pilot benchmark instances
│   ├── smoke_test/                                                  # 2 unit-test CNFs (test_sat.cnf, test_unsat.cnf)
│   ├── expanded_manifest.csv                                        # Development suite manifest
│   ├── generate_expanded.py                                         # Development benchmark generator
│   └── validate_expanded.py                                         # Benchmark validator
│
├── experiments/                                                     # Execution harnesses, analysis scripts & master CSVs
│   ├── frozen_configurations.json                                   # Exact frozen hyperparameter configurations
│   ├── run_experiments.py                                           # Universal benchmark executor & telemetry parser
│   ├── run_final_holdout_evaluation.py                              # Holdout factorial evaluation runner
│   ├── run_qre_gated_full_development.py                            # QRE development runner
│   ├── run_portfolio_mab_pilot.py                                   # MAB online evaluation runner
│   ├── analyze_final_holdout_evaluation.py                          # Holdout telemetry aggregator
│   ├── analyze_qre_gated_full_development.py                        # Development telemetry aggregator
│   ├── plot_final_holdout.py                                        # Holdout chart plotting script
│   ├── plot_presentation_figures.py                                 # Presentation chart generator
│   ├── verify_model.py                                              # Independent SAT model certifier
│   ├── verify_qre_gated_invariance.py                               # Configuration invariance assertion suite
│   ├── test_framework.py                                            # End-to-end framework test harness
│   └── results/                                                     # Master experimental data
│       ├── qre_gated_full_development/master_results.csv            # Authoritative development results (648 runs)
│       ├── final_holdout/master_results.csv                         # Authoritative holdout results (1,152 runs)
│       ├── portfolio_mab_pilot/master_results.csv                   # Portfolio MAB experimental data
│       └── ... (summary CSVs across all historical phases)
│
└── presentation/                                                    # Academic presentation supporting resources
    ├── Presentation_Notes.md                                        # Slide-by-slide speaker notes, talking points & defense scripts
    └── assets/                                                      # Vector illustrations & architecture diagrams
```
