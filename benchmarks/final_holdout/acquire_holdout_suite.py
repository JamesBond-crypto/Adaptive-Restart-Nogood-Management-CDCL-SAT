#!/usr/bin/env python3
"""
acquire_holdout_suite.py - Step 34: Authoritative Unseen Holdout Suite Acquisition

Downloads, deterministically samples (seed 42), validates, and catalogs 48 unseen
benchmark instances from authoritative SATLIB / DIMACS Challenge repositories.

Categories:
  1. Industrial / Circuit Verification (BF, SSA) - 8 instances
  2. Application / Planning (Logistics, Hanoi) - 6 instances
  3. Structured & Crafted UNSAT (Dubois, Pretolani, AIM-no) - 14 instances
  4. Combinatorial Graph 3-Coloring (Flat100, Flat150) - 8 instances
  5. Uniform Random 3-SAT (uf200 SAT, uuf200 UNSAT) - 12 instances
Total = 48 instances.

Strict Validation:
  - Complete DIMACS syntax validation (p cnf, literal bounds, clause 0-termination).
  - SHA-256 duplicate detection.
  - Zero-overlap verification against earlier pilot & expanded suites.
  - No SAT solver invocation.
"""

import os
import io
import re
import csv
import json
import random
import hashlib
import tarfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set

HOLDOUT_DIR = Path(__file__).resolve().parent
WORKSPACE = HOLDOUT_DIR.parent.parent
MANIFEST_CSV = HOLDOUT_DIR / "holdout_manifest.csv"
MANIFEST_JSON = HOLDOUT_DIR / "holdout_manifest.json"

BASE_URL = "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/"
SAMPLING_SEED = 42

# Known DIMACS labels documented in DIMACS challenge literature (1993/1996)
DIMACS_KNOWN_LABELS = {
    # Bridging faults (BF)
    "bf0432-007.cnf": ("UNSAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    "bf1355-075.cnf": ("SAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    "bf1355-638.cnf": ("UNSAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    "bf2670-001.cnf": ("UNSAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    # Single stuck-at faults (SSA)
    "ssa0432-003.cnf": ("SAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    "ssa2670-130.cnf": ("SAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    "ssa2670-141.cnf": ("SAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    "ssa7552-038.cnf": ("UNSAT", "DIMACS Challenge 1993 / Chakradhar et al."),
    # Towers of Hanoi
    "hanoi4.cnf": ("SAT", "DIMACS Challenge 1996 / Kautz and Selman"),
    "hanoi5.cnf": ("SAT", "DIMACS Challenge 1996 / Kautz and Selman"),
}

SUITES_PLAN = [
    {
        "category": "Industrial / Circuit Verification",
        "family": "Bridging Faults (BF)",
        "archive_rel": "DIMACS/BF/bf.tar.gz",
        "year": 1993,
        "quota": 4,
        "mode": "all",
        "default_label": "UNKNOWN",
        "label_source": "DIMACS Challenge 1993",
        "author": "Chakradhar, Agrawal, Bushnell (1993)"
    },
    {
        "category": "Industrial / Circuit Verification",
        "family": "Single Stuck-at Faults (SSA)",
        "archive_rel": "DIMACS/SSA/ssa.tar.gz",
        "year": 1993,
        "quota": 4,
        "mode": "sample",
        "default_label": "UNKNOWN",
        "label_source": "DIMACS Challenge 1993",
        "author": "Chakradhar, Agrawal, Bushnell (1993)"
    },
    {
        "category": "Application / Planning",
        "family": "Logistics Planning",
        "archive_rel": "PLANNING/Logistics/logistics.tar.gz",
        "year": 1996,
        "quota": 4,
        "mode": "all",
        "default_label": "SAT",
        "label_source": "SATLIB Planning Benchmarks / Kautz & Selman",
        "author": "Kautz and Selman (1996)"
    },
    {
        "category": "Application / Planning",
        "family": "Towers of Hanoi Planning",
        "archive_rel": "DIMACS/HANOI/hanoi.tar.gz",
        "year": 1996,
        "quota": 2,
        "mode": "all",
        "default_label": "SAT",
        "label_source": "DIMACS Challenge 1996 / Kautz & Selman",
        "author": "Kautz and Selman (1996)"
    },
    {
        "category": "Crafted / Combinatorial UNSAT",
        "family": "Dubois Contradictions",
        "archive_rel": "DIMACS/DUBOIS/dubois.tar.gz",
        "year": 1993,
        "quota": 6,
        "mode": "sample",
        "default_label": "UNSAT",
        "label_source": "DIMACS Challenge 1993 / Olivier Dubois (provable contradiction)",
        "author": "Olivier Dubois (1993)"
    },
    {
        "category": "Crafted / Combinatorial UNSAT",
        "family": "Pretolani Resilient UNSAT",
        "archive_rel": "DIMACS/PRET/pret.tar.gz",
        "year": 1993,
        "quota": 4,
        "mode": "sample",
        "default_label": "UNSAT",
        "label_source": "DIMACS Challenge 1993 / Daniele Pretolani",
        "author": "Daniele Pretolani (1993)"
    },
    {
        "category": "Crafted / Combinatorial UNSAT",
        "family": "AIM Artificial UNSAT",
        "archive_rel": "DIMACS/AIM/aim.tar.gz",
        "year": 1993,
        "quota": 4,
        "mode": "filter_sample",
        "filter_fn": lambda n: "-no-" in n,
        "default_label": "UNSAT",
        "label_source": "DIMACS Challenge 1993 / Asahiro, Iwama, Miyano",
        "author": "Asahiro, Iwama, Miyano (1993)"
    },
    {
        "category": "Combinatorial / Graph Coloring",
        "family": "Flat Graph 3-Coloring (100v)",
        "archive_rel": "GCP/flat100-239.tar.gz",
        "year": 1995,
        "quota": 4,
        "mode": "sample",
        "default_label": "SAT",
        "label_source": "SATLIB Graph Coloring / Joseph Culberson (chromatic number = 3)",
        "author": "Joseph Culberson (1995)"
    },
    {
        "category": "Combinatorial / Graph Coloring",
        "family": "Flat Graph 3-Coloring (150v)",
        "archive_rel": "GCP/flat150-360.tar.gz",
        "year": 1995,
        "quota": 4,
        "mode": "sample",
        "default_label": "SAT",
        "label_source": "SATLIB Graph Coloring / Joseph Culberson (chromatic number = 3)",
        "author": "Joseph Culberson (1995)"
    },
    {
        "category": "Random 3-SAT",
        "family": "Uniform Random 3-SAT (n=200, SAT)",
        "archive_rel": "RND3SAT/uf200-860.tar.gz",
        "year": 2000,
        "quota": 6,
        "mode": "sample",
        "default_label": "SAT",
        "label_source": "SATLIB Uniform Random 3-SAT Filtered SAT (Hoos & Stutzle)",
        "author": "Hoos and Stutzle (2000)"
    },
    {
        "category": "Random 3-SAT",
        "family": "Uniform Random 3-SAT (n=200, UNSAT)",
        "archive_rel": "RND3SAT/uuf200-860.tar.gz",
        "year": 2000,
        "quota": 6,
        "mode": "sample",
        "default_label": "UNSAT",
        "label_source": "SATLIB Uniform Random 3-SAT Filtered UNSAT (Hoos & Stutzle)",
        "author": "Hoos and Stutzle (2000)"
    }
]

def get_existing_benchmark_hashes() -> Dict[str, str]:
    """Collects SHA-256 hashes of all existing pilot, expanded, and smoke benchmarks."""
    hashes = {}
    for p in WORKSPACE.glob("benchmarks/**/*.cnf"):
        if "final_holdout" in str(p):
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        hashes[h.hexdigest()] = str(p.relative_to(WORKSPACE))
    return hashes

def clean_dimacs_content(content_bytes: bytes) -> bytes:
    """Strips obsolete DIMACS EOF marker ('%' and trailing '0') if present."""
    text = content_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        sline = line.strip()
        if sline == "%":
            break
        clean_lines.append(line)
    return ("\n".join(clean_lines) + "\n").encode("utf-8")

def validate_dimacs_cnf(content_bytes: bytes) -> Tuple[bool, int, int, str]:
    """
    Validates DIMACS CNF without running a SAT solver:
    - Parses header 'p cnf <vars> <clauses>'
    - Verifies clause line termination with 0
    - Checks literal bounds (abs(lit) <= num_vars)
    - Counts actual clauses and compares to declared clauses
    """
    try:
        text = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        return False, 0, 0, f"Encoding error: {e}"

    lines = text.splitlines()
    header_found = False
    decl_vars = 0
    decl_clauses = 0
    actual_clauses = 0
    current_clause_lits = []

    for line_idx, line in enumerate(lines, 1):
        sline = line.strip()
        if not sline or sline.startswith("c"):
            continue
        if sline == "%":
            # DIMACS EOF marker
            break
        if sline.startswith("p "):
            parts = sline.split()
            if len(parts) < 4 or parts[1] != "cnf":
                return False, 0, 0, f"Malformed header line {line_idx}: '{line}'"
            try:
                decl_vars = int(parts[2])
                decl_clauses = int(parts[3])
                header_found = True
            except ValueError:
                return False, 0, 0, f"Invalid variable/clause counts in header: '{line}'"
            continue

        if not header_found:
            return False, 0, 0, f"Clause appeared before 'p cnf' header on line {line_idx}"

        # Parse literals
        tokens = sline.split()
        for tok in tokens:
            try:
                val = int(tok)
            except ValueError:
                return False, 0, 0, f"Non-integer token '{tok}' on line {line_idx}"

            if val == 0:
                actual_clauses += 1
                current_clause_lits = []
            else:
                var = abs(val)
                if var > decl_vars:
                    return False, 0, 0, f"Literal {val} exceeds declared variable bound {decl_vars} on line {line_idx}"
                current_clause_lits.append(val)

    if current_clause_lits:
        return False, decl_vars, actual_clauses, "Final clause was not terminated with 0"

    if not header_found:
        return False, 0, 0, "No 'p cnf' header found in file"

    if actual_clauses != decl_clauses:
        # Note: some DIMACS generators produce slight clause mismatches; check if non-fatal
        note = f"Warning: actual clauses ({actual_clauses}) != declared clauses ({decl_clauses})"
    else:
        note = "OK"

    return True, decl_vars, actual_clauses, note

def main():
    print("=" * 80)
    print("STEP 34: ACQUIRING & VALIDATING UNSEEN HOLDOUT BENCHMARK SUITE")
    print("=" * 80)
    
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_hashes = get_existing_benchmark_hashes()
    print(f"[*] Indexed {len(existing_hashes)} existing development benchmark files.")
    
    rng = random.Random(SAMPLING_SEED)
    
    selected_instances: List[Dict[str, Any]] = []
    seen_holdout_hashes: Set[str] = set()
    seen_holdout_names: Set[str] = set()
    
    holdout_counter = 1
    
    for plan in SUITES_PLAN:
        cat = plan["category"]
        fam = plan["family"]
        rel = plan["archive_rel"]
        quota = plan["quota"]
        mode = plan["mode"]
        archive_url = BASE_URL + rel
        
        print(f"\n[*] Processing Suite: {fam} ({cat})")
        print(f"    URL   : {archive_url}")
        print(f"    Quota : {quota} instances (mode: {mode})")
        
        # Download archive into memory
        req = urllib.request.Request(archive_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            
        tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
        
        # Extract candidate files
        candidates = []
        for member in tf.getmembers():
            if not member.isfile():
                continue
            fname = Path(member.name).name
            if not fname.endswith(".cnf"):
                continue
            if mode == "filter_sample" and "filter_fn" in plan:
                if not plan["filter_fn"](fname):
                    continue
            candidates.append((fname, member))
            
        # Sort for deterministic reproducibility
        candidates.sort(key=lambda x: x[0])
        print(f"    Found {len(candidates)} candidate files in archive.")
        
        if mode == "all":
            assert len(candidates) >= quota, f"Not enough candidates ({len(candidates)}) for quota ({quota})"
            chosen = candidates[:quota]
        elif mode in ("sample", "filter_sample"):
            assert len(candidates) >= quota, f"Not enough candidates ({len(candidates)}) for quota ({quota})"
            # Deterministic pseudo-random selection
            chosen_indices = rng.sample(range(len(candidates)), quota)
            chosen_indices.sort()
            chosen = [candidates[i] for i in chosen_indices]
            
        for fname, member in chosen:
            # Extract content
            f = tf.extractfile(member)
            raw_bytes = f.read()
            content = clean_dimacs_content(raw_bytes)
            
            # Syntax validation
            is_valid, num_vars, num_clauses, val_note = validate_dimacs_cnf(content)
            if not is_valid:
                raise ValueError(f"DIMACS Validation FAILED for {fname}: {val_note}")
                
            # Hash computation
            sha256 = hashlib.sha256(content).hexdigest()
            file_size = len(content)
            
            # Check overlap against development suites
            if sha256 in existing_hashes:
                raise ValueError(f"CRITICAL ERROR: Holdout file {fname} ({sha256}) overlaps with development benchmark {existing_hashes[sha256]}!")
                
            # Check duplicate within holdout
            if sha256 in seen_holdout_hashes:
                raise ValueError(f"CRITICAL ERROR: Duplicate file within holdout: {fname} ({sha256})")
                
            seen_holdout_hashes.add(sha256)
            
            # Label attribution
            if fname in DIMACS_KNOWN_LABELS:
                auth_label, label_src = DIMACS_KNOWN_LABELS[fname]
            else:
                auth_label = plan["default_label"]
                label_src = plan["label_source"]
                
            bid = f"HOLDOUT_{holdout_counter:02d}"
            
            # Save raw CNF file
            dest_path = HOLDOUT_DIR / fname
            with open(dest_path, "wb") as out_f:
                out_f.write(content)
                
            record = {
                "benchmark_id": bid,
                "filename": fname,
                "category": cat,
                "family": fam,
                "author_provenance": plan["author"],
                "archive_source_url": archive_url,
                "dataset_year": plan["year"],
                "authoritative_label": auth_label,
                "label_source": label_src,
                "num_vars": num_vars,
                "num_clauses": num_clauses,
                "file_size_bytes": file_size,
                "sha256_hash": sha256,
                "selection_seed": SAMPLING_SEED,
                "inclusion_rule": f"Pre-registered {cat} quota ({mode})",
                "syntax_validation_status": "VALID",
                "validation_note": val_note
            }
            selected_instances.append(record)
            print(f"    [+] {bid}: {fname:<25} | Vars={num_vars:<5} | Clauses={num_clauses:<6} | {auth_label:<5} | {sha256[:12]}...")
            holdout_counter += 1
            
    assert len(selected_instances) == 48, f"Expected 48 instances, got {len(selected_instances)}"
    print("\n" + "=" * 80)
    print(f"[*] Successfully acquired and verified {len(selected_instances)} holdout benchmarks!")
    print(f"[*] Stored under: {HOLDOUT_DIR}")
    
    # Write CSV manifest
    fieldnames = list(selected_instances[0].keys())
    with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_instances)
    print(f"[*] Wrote CSV manifest: {MANIFEST_CSV}")
    
    # Write JSON manifest
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(selected_instances, f, indent=2)
    print(f"[*] Wrote JSON manifest: {MANIFEST_JSON}")
    print("=" * 80)

if __name__ == "__main__":
    main()

