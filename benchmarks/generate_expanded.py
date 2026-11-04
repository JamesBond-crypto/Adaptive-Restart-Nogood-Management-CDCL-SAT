#!/usr/bin/env python3
"""
generate_expanded.py - Expanded SAT Benchmark Generator & Manifest Builder

Generates an expanded collection of 36 nontrivial DIMACS CNF benchmarks across
four structural families to evaluate CDCL solver search behavior:
1. Larger Uniform Random 3-SAT (150-250 vars) near the phase transition ratio (~4.20-4.30).
2. Larger Planted Satisfiable 3-SAT (160-260 vars) with certified planted models.
3. Expanded Pigeonhole Principle (PHP) formulas with guaranteed UNSAT status.
4. Graph Coloring (K-Coloring) formulas with certified SAT cases and mathematically
   justified UNSAT cases (complete graphs K_{k+1}, Grötzsch graph, embedded cliques).

Outputs:
- CNF files saved in: benchmarks/expanded/
- CSV manifest saved in: benchmarks/expanded_manifest.csv
"""

import os
import sys
import csv
import random
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

# Add experiments directory to path for independent model verification
sys.path.insert(0, str(Path(__file__).parent.parent / "experiments"))
from verify_model import verify_model


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def write_cnf_file(path: Path, num_vars: int, clauses: List[List[int]], header_comment: str):
    """Writes clauses to a DIMACS CNF file format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"c {header_comment}\n")
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for clause in clauses:
            f.write(f"{' '.join(map(str, clause))} 0\n")


# =====================================================================
# Family A: Uniform Random 3-SAT
# =====================================================================

def generate_random_3sat(num_vars: int, num_clauses: int, seed: int) -> List[List[int]]:
    """
    Generates a uniform random 3-SAT formula with fixed seed.
    Each clause contains 3 distinct variables with random polarities.
    """
    rng = random.Random(seed)
    clauses: List[List[int]] = []
    clause_set = set()

    attempts = 0
    max_attempts = num_clauses * 100

    while len(clauses) < num_clauses and attempts < max_attempts:
        attempts += 1
        vars_chosen = rng.sample(range(1, num_vars + 1), 3)
        lits = tuple(sorted([v if rng.choice([True, False]) else -v for v in vars_chosen], key=abs))
        if lits not in clause_set:
            clause_set.add(lits)
            clauses.append(list(lits))

    if len(clauses) < num_clauses:
        raise RuntimeError(f"Could not generate {num_clauses} distinct random clauses without duplicates.")

    return clauses


# =====================================================================
# Family B: Planted Satisfiable 3-SAT
# =====================================================================

def generate_planted_3sat(num_vars: int, num_clauses: int, seed: int) -> Tuple[List[List[int]], Dict[int, bool]]:
    """
    Generates a planted satisfiable 3-SAT formula.
    First chooses a satisfying assignment sigma.
    Ensures that every generated clause has at least one literal satisfied by sigma.
    """
    rng = random.Random(seed)
    planted_model = {v: rng.choice([True, False]) for v in range(1, num_vars + 1)}

    clauses: List[List[int]] = []
    clause_set = set()

    attempts = 0
    max_attempts = num_clauses * 100

    while len(clauses) < num_clauses and attempts < max_attempts:
        attempts += 1
        vars_chosen = rng.sample(range(1, num_vars + 1), 3)

        while True:
            polarities = [rng.choice([True, False]) for _ in range(3)]
            lits = [vars_chosen[i] if polarities[i] else -vars_chosen[i] for i in range(3)]
            is_sat = any(
                (lit > 0 and planted_model[abs(lit)]) or (lit < 0 and not planted_model[abs(lit)])
                for lit in lits
            )
            if is_sat:
                break

        canonical = tuple(sorted(lits, key=abs))
        if canonical not in clause_set:
            clause_set.add(canonical)
            clauses.append(list(canonical))

    if len(clauses) < num_clauses:
        raise RuntimeError(f"Could not generate {num_clauses} planted clauses without duplicates.")

    return clauses, planted_model


# =====================================================================
# Family C: Pigeonhole Principle (PHP)
# =====================================================================

def generate_php(num_pigeons: int, num_holes: int) -> List[List[int]]:
    """
    Encodes PHP(num_pigeons, num_holes).
    Variables: x_{i,j} = pigeon i is in hole j.
    Mapping: var(i, j) = (i - 1) * num_holes + j.
    """
    def var_idx(pigeon: int, hole: int) -> int:
        return (pigeon - 1) * num_holes + hole

    clauses: List[List[int]] = []

    # 1. Each pigeon must be in at least one hole:
    for i in range(1, num_pigeons + 1):
        clause = [var_idx(i, j) for j in range(1, num_holes + 1)]
        clauses.append(clause)

    # 2. No hole can hold two pigeons:
    for j in range(1, num_holes + 1):
        for i1 in range(1, num_pigeons + 1):
            for i2 in range(i1 + 1, num_pigeons + 1):
                clauses.append([-var_idx(i1, j), -var_idx(i2, j)])

    return clauses


# =====================================================================
# Family D: Graph Coloring
# =====================================================================

def encode_graph_coloring(num_vertices: int, num_colors: int, edges: List[Tuple[int, int]]) -> List[List[int]]:
    """
    Encodes K-coloring of an undirected graph G = (V, E) into CNF.
    Variables: x_{v, c} = vertex v is colored with color c.
    Mapping: var(v, c) = (v - 1) * num_colors + c.
    """
    def var_idx(v: int, c: int) -> int:
        return (v - 1) * num_colors + c

    clauses: List[List[int]] = []

    # 1. At-least-one color per vertex (ALO)
    for v in range(1, num_vertices + 1):
        clauses.append([var_idx(v, c) for c in range(1, num_colors + 1)])

    # 2. At-most-one color per vertex (AMO)
    for v in range(1, num_vertices + 1):
        for c1 in range(1, num_colors + 1):
            for c2 in range(c1 + 1, num_colors + 1):
                clauses.append([-var_idx(v, c1), -var_idx(v, c2)])

    # 3. Adjacent vertices cannot share the same color (conflict clauses)
    for u, v in edges:
        for c in range(1, num_colors + 1):
            clauses.append([-var_idx(u, c), -var_idx(v, c)])

    return clauses


def generate_planted_k_colorable_graph(
    num_vertices: int, num_colors: int, num_edges: int, seed: int
) -> Tuple[List[Tuple[int, int]], Dict[int, int]]:
    """
    Generates a random K-colorable graph with planted partition.
    Returns list of edges (u, v) with u < v, and the planted vertex color map {v: c}.
    """
    rng = random.Random(seed)
    # Balanced partition assignment
    color_assign = {v: (v % num_colors) + 1 for v in range(1, num_vertices + 1)}

    # Candidate edges strictly between different color classes
    possible_edges = [
        (u, v)
        for u in range(1, num_vertices + 1)
        for v in range(u + 1, num_vertices + 1)
        if color_assign[u] != color_assign[v]
    ]

    if num_edges > len(possible_edges):
        raise ValueError(f"Requested {num_edges} edges, but maximum bipartition edges is {len(possible_edges)}")

    chosen_edges = sorted(rng.sample(possible_edges, num_edges))
    return chosen_edges, color_assign


# =====================================================================
# Main Suite Construction & Manifest Generation
# =====================================================================

def build_expanded_suite() -> List[Dict[str, Any]]:
    output_dir = Path("benchmarks/expanded")
    manifest_path = Path("benchmarks/expanded_manifest.csv")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_records: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # Family A: Larger Random 3-SAT (150-250 vars, ratio ~4.20-4.30)
    # -------------------------------------------------------------
    random_configs = [
        (150, 639, 1001),  # ratio 4.26
        (150, 645, 1002),  # ratio 4.30
        (175, 735, 1003),  # ratio 4.20
        (175, 745, 1004),  # ratio 4.26
        (200, 840, 1005),  # ratio 4.20
        (200, 852, 1006),  # ratio 4.26
        (215, 915, 1007),  # ratio 4.26
        (225, 958, 1008),  # ratio 4.26
        (235, 999, 1009),  # ratio 4.25
        (250, 1065, 1010), # ratio 4.26
    ]

    for n_vars, n_clauses, seed in random_configs:
        fname = f"rand3sat_n{n_vars}_c{n_clauses}_s{seed}.cnf"
        fpath = output_dir / fname
        clauses = generate_random_3sat(n_vars, n_clauses, seed)
        write_cnf_file(
            fpath,
            n_vars,
            clauses,
            f"Expanded Random 3-SAT: n={n_vars}, m={n_clauses}, seed={seed}, ratio={n_clauses/n_vars:.2f}"
        )
        h = compute_sha256(fpath)
        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath).replace("\\", "/"),
            "family": "Random 3-SAT",
            "parameters": f"n={n_vars}, m={n_clauses}",
            "random_seed": str(seed),
            "num_vars": n_vars,
            "num_clauses": len(clauses),
            "known_status": "UNKNOWN",
            "status_reason": f"Uniform random sampling near phase transition ratio (m/n = {n_clauses/n_vars:.2f}); no ground-truth oracle applied.",
            "sha256": h
        })

    # -------------------------------------------------------------
    # Family B: Planted Satisfiable 3-SAT (160-260 vars)
    # -------------------------------------------------------------
    planted_configs = [
        (160, 682, 2001),  # ratio 4.26
        (160, 688, 2002),  # ratio 4.30
        (180, 756, 2003),  # ratio 4.20
        (180, 767, 2004),  # ratio 4.26
        (200, 852, 2005),  # ratio 4.26
        (200, 860, 2006),  # ratio 4.30
        (220, 937, 2007),  # ratio 4.26
        (220, 946, 2008),  # ratio 4.30
        (240, 1022, 2009), # ratio 4.26
        (260, 1108, 2010), # ratio 4.26
    ]

    for n_vars, n_clauses, seed in planted_configs:
        fname = f"planted3sat_n{n_vars}_c{n_clauses}_s{seed}.cnf"
        fpath = output_dir / fname
        clauses, model = generate_planted_3sat(n_vars, n_clauses, seed)
        model_str = " ".join(f"{v if model[v] else -v}" for v in sorted(model.keys()))
        write_cnf_file(
            fpath,
            n_vars,
            clauses,
            f"Expanded Planted Satisfiable 3-SAT: n={n_vars}, m={n_clauses}, seed={seed}. Planted model: {model_str}"
        )
        h = compute_sha256(fpath)

        # Independent verification check of the planted model
        v_model_str = f"v {model_str} 0"
        ok, msg = verify_model(str(fpath), v_model_str)
        if not ok:
            raise RuntimeError(f"Planted model verification failed for {fname}: {msg}")

        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath).replace("\\", "/"),
            "family": "Planted Satisfiable 3-SAT",
            "parameters": f"n={n_vars}, m={n_clauses}",
            "random_seed": str(seed),
            "num_vars": n_vars,
            "num_clauses": len(clauses),
            "known_status": "SAT",
            "status_reason": "Mathematically guaranteed satisfiable by construction with certified planted assignment.",
            "sha256": h
        })

    # -------------------------------------------------------------
    # Family C: Pigeonhole Principle (PHP)
    # -------------------------------------------------------------
    php_configs = [
        (9, 7),   # 9 pigeons, 7 holes -> 63 vars, 261 clauses
        (10, 8),  # 10 pigeons, 8 holes -> 80 vars, 370 clauses
        (10, 9),  # 10 pigeons, 9 holes -> 90 vars, 415 clauses
        (11, 10), # 11 pigeons, 10 holes -> 110 vars, 561 clauses
    ]

    for pigeons, holes in php_configs:
        fname = f"php_{pigeons}p_{holes}h.cnf"
        fpath = output_dir / fname
        clauses = generate_php(pigeons, holes)
        n_vars = pigeons * holes
        write_cnf_file(
            fpath,
            n_vars,
            clauses,
            f"Expanded Pigeonhole Principle PHP({pigeons},{holes}): {pigeons} pigeons into {holes} holes."
        )
        h = compute_sha256(fpath)
        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath).replace("\\", "/"),
            "family": "Pigeonhole Principle (PHP)",
            "parameters": f"pigeons={pigeons}, holes={holes}",
            "random_seed": "N/A (deterministic)",
            "num_vars": n_vars,
            "num_clauses": len(clauses),
            "known_status": "UNSAT",
            "status_reason": f"Mathematically unsatisfiable by Dirichlet's box principle ({pigeons} pigeons cannot occupy {holes} distinct holes without collision).",
            "sha256": h
        })

    # -------------------------------------------------------------
    # Family D: Graph Coloring (6 SAT, 6 UNSAT)
    # -------------------------------------------------------------
    # D1: Satisfiable Graph Coloring Instances
    gcol_sat_configs = [
        (30, 3, 90, 3001),   # 30 vertices, 3 colors, 90 edges
        (35, 3, 115, 3002),  # 35 vertices, 3 colors, 115 edges
        (40, 3, 140, 3003),  # 40 vertices, 3 colors, 140 edges
        (45, 3, 165, 3004),  # 45 vertices, 3 colors, 165 edges
        (50, 3, 190, 3005),  # 50 vertices, 3 colors, 190 edges
        (40, 4, 180, 3006),  # 40 vertices, 4 colors, 180 edges
    ]

    for n_verts, n_colors, n_edges, seed in gcol_sat_configs:
        fname = f"gcol_sat_n{n_verts}_k{n_colors}_m{n_edges}_s{seed}.cnf"
        fpath = output_dir / fname
        edges, color_map = generate_planted_k_colorable_graph(n_verts, n_colors, n_edges, seed)
        clauses = encode_graph_coloring(n_verts, n_colors, edges)
        total_vars = n_verts * n_colors
        write_cnf_file(
            fpath,
            total_vars,
            clauses,
            f"Expanded Graph Coloring SAT: n_verts={n_verts}, k_colors={n_colors}, edges={n_edges}, seed={seed}"
        )
        h = compute_sha256(fpath)

        # Build planted model string and verify
        model_lits = []
        for v in range(1, n_verts + 1):
            for c in range(1, n_colors + 1):
                var_num = (v - 1) * n_colors + c
                if c == color_map[v]:
                    model_lits.append(str(var_num))
                else:
                    model_lits.append(str(-var_num))
        v_model_str = f"v {' '.join(model_lits)} 0"
        ok, msg = verify_model(str(fpath), v_model_str)
        if not ok:
            raise RuntimeError(f"Planted model verification failed for {fname}: {msg}")

        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath).replace("\\", "/"),
            "family": "Graph Coloring",
            "parameters": f"n_verts={n_verts}, k_colors={n_colors}, edges={n_edges}",
            "random_seed": str(seed),
            "num_vars": total_vars,
            "num_clauses": len(clauses),
            "known_status": "SAT",
            "status_reason": f"Mathematically guaranteed satisfiable by construction with planted {n_colors}-coloring partition.",
            "sha256": h
        })

    # D2: Unsatisfiable Graph Coloring Instances
    # 1. Complete graphs Kn with K=n-1 colors
    for n in [8, 9, 10, 11]:
        k = n - 1
        fname = f"gcol_unsat_k{n}_c{k}.cnf"
        fpath = output_dir / fname
        edges = [(u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1)]
        clauses = encode_graph_coloring(n, k, edges)
        total_vars = n * k
        write_cnf_file(
            fpath,
            total_vars,
            clauses,
            f"Expanded Graph Coloring UNSAT: Complete graph K_{n} with {k} colors."
        )
        h = compute_sha256(fpath)
        manifest_records.append({
            "filename": fname,
            "filepath": str(fpath).replace("\\", "/"),
            "family": "Graph Coloring",
            "parameters": f"n_verts={n}, k_colors={k}, complete_clique=K_{n}",
            "random_seed": "N/A (deterministic)",
            "num_vars": total_vars,
            "num_clauses": len(clauses),
            "known_status": "UNSAT",
            "status_reason": f"Mathematically unsatisfiable: complete graph K_{n} has chromatic number χ(K_{n})={n}, requiring at least {n} colors.",
            "sha256": h
        })

    # 2. Grötzsch graph (triangle-free, chromatic number 4) with 3 colors
    grotzsch_edges = [
        (1, 2), (2, 3), (3, 4), (4, 5), (5, 1), # C5 cycle
        (6, 2), (6, 5), # shadow of 1
        (7, 1), (7, 3), # shadow of 2
        (8, 2), (8, 4), # shadow of 3
        (9, 3), (9, 5), # shadow of 4
        (10, 4), (10, 1), # shadow of 5
        (11, 6), (11, 7), (11, 8), (11, 9), (11, 10) # apex vertex 11 to shadows
    ]
    fname = "gcol_unsat_grotzsch_k3.cnf"
    fpath = output_dir / fname
    clauses = encode_graph_coloring(11, 3, grotzsch_edges)
    total_vars = 11 * 3
    write_cnf_file(
        fpath,
        total_vars,
        clauses,
        "Expanded Graph Coloring UNSAT: Grötzsch graph (Mycielskian of C5, χ=4) with 3 colors."
    )
    h = compute_sha256(fpath)
    manifest_records.append({
        "filename": fname,
        "filepath": str(fpath).replace("\\", "/"),
        "family": "Graph Coloring",
        "parameters": "n_verts=11, k_colors=3, graph=Grotzsch",
        "random_seed": "N/A (deterministic)",
        "num_vars": total_vars,
        "num_clauses": len(clauses),
        "known_status": "UNSAT",
        "status_reason": "Mathematically unsatisfiable: Grötzsch graph has chromatic number χ=4 by Mycielski's theorem, impossible to color with 3 colors.",
        "sha256": h
    })

    # 3. Clique K_6 embedded in 30-vertex graph with 120 total edges, 5 colors
    embed_seed = 3101
    rng = random.Random(embed_seed)
    clique_verts = list(range(1, 7)) # K_6
    edges_set = set((u, v) for u in clique_verts for v in range(u + 1, 7)) # 15 clique edges
    other_possible = [
        (u, v) for u in range(1, 31) for v in range(u + 1, 31)
        if (u, v) not in edges_set
    ]
    additional_edges = rng.sample(other_possible, 120 - len(edges_set))
    edges_set.update(additional_edges)
    all_edges = sorted(list(edges_set))
    fname = "gcol_unsat_clique_embed_n30_k5_s3101.cnf"
    fpath = output_dir / fname
    clauses = encode_graph_coloring(30, 5, all_edges)
    total_vars = 30 * 5
    write_cnf_file(
        fpath,
        total_vars,
        clauses,
        f"Expanded Graph Coloring UNSAT: K_6 clique embedded in 30-vertex graph (total edges 120, seed {embed_seed}) with 5 colors."
    )
    h = compute_sha256(fpath)
    manifest_records.append({
        "filename": fname,
        "filepath": str(fpath).replace("\\", "/"),
        "family": "Graph Coloring",
        "parameters": f"n_verts=30, k_colors=5, edges=120, embedded_clique=K_6",
        "random_seed": str(embed_seed),
        "num_vars": total_vars,
        "num_clauses": len(clauses),
        "known_status": "UNSAT",
        "status_reason": "Mathematically unsatisfiable: graph contains embedded K_6 subgraph, giving χ(G) >= χ(K_6) = 6 > 5 colors.",
        "sha256": h
    })

    # -------------------------------------------------------------
    # Write Manifest CSV
    # -------------------------------------------------------------
    fieldnames = [
        "filename",
        "filepath",
        "family",
        "parameters",
        "random_seed",
        "num_vars",
        "num_clauses",
        "known_status",
        "status_reason",
        "sha256"
    ]

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_records)

    print(f"[+] Successfully generated {len(manifest_records)} expanded instances.")
    print(f"[+] Files stored in: {output_dir}")
    print(f"[+] Manifest created at: {manifest_path}")

    return manifest_records


if __name__ == "__main__":
    build_expanded_suite()

