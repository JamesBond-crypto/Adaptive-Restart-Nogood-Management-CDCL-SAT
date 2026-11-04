#!/usr/bin/env python3
"""
verify_model.py - Independent DIMACS CNF Model Verifier

Verifies that a truth assignment (SAT model) reported by a SAT solver satisfies
every clause in the original DIMACS CNF benchmark file.

Features:
- Parses standard DIMACS CNF files (ignoring comments, handling multi-line clauses).
- Validates model strings or literal lists (handling 'v ...' lines and '0' terminator).
- Detects contradictions (a variable assigned both True and False).
- Detects out-of-range literals not defined in the CNF header.
- Verifies that every clause has at least one literal evaluating to True.
- Can be used both as a CLI script and imported as a Python module.
"""

import sys
import os
import argparse
from typing import Tuple, List, Set, Optional


class CNFParseError(Exception):
    """Raised when the DIMACS CNF file cannot be parsed or violates specification."""
    pass


class ModelParseError(Exception):
    """Raised when the model output is malformed or contradictory."""
    pass


def parse_dimacs_cnf(cnf_path: str) -> Tuple[int, int, List[List[int]]]:
    """
    Parses a DIMACS CNF file.

    Returns:
        (num_vars, num_clauses, clauses)
        where clauses is a list of lists of integer literals.
    """
    if not os.path.isfile(cnf_path):
        raise FileNotFoundError(f"CNF file not found: {cnf_path}")

    num_vars: Optional[int] = None
    num_clauses: Optional[int] = None
    clauses: List[List[int]] = []
    current_clause: List[int] = []

    with open(cnf_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            # Comment line
            if line.startswith('c'):
                continue

            # Problem header line: p cnf <vars> <clauses>
            if line.startswith('p'):
                tokens = line.split()
                if len(tokens) < 4 or tokens[1].lower() != 'cnf':
                    raise CNFParseError(f"Malformed problem line {line_num}: '{line}'")
                try:
                    num_vars = int(tokens[2])
                    num_clauses = int(tokens[3])
                except ValueError as e:
                    raise CNFParseError(f"Invalid integer in problem line {line_num}: {e}")
                if num_vars < 0 or num_clauses < 0:
                    raise CNFParseError(f"Negative variable or clause count on line {line_num}: '{line}'")
                continue

            # If clauses appear before the problem line
            if num_vars is None:
                raise CNFParseError(f"Clause encountered before problem line 'p cnf' on line {line_num}")

            # Clause line: read space-separated integers
            tokens = line.split()
            for token in tokens:
                try:
                    lit = int(token)
                except ValueError:
                    raise CNFParseError(f"Non-integer literal token '{token}' on line {line_num}")

                if lit == 0:
                    # End of current clause
                    clauses.append(current_clause)
                    current_clause = []
                else:
                    if abs(lit) > num_vars:
                        raise CNFParseError(
                            f"Literal {lit} on line {line_num} exceeds declared variable count {num_vars}"
                        )
                    current_clause.append(lit)

    # Check if there is an unclosed clause
    if current_clause:
        raise CNFParseError("Unexpected EOF: CNF ended with an unclosed clause (missing trailing 0)")

    if num_clauses is not None and len(clauses) != num_clauses:
        # Note: some non-standard benchmarks declare fewer/more clauses than present.
        # We issue a note/warning but allow verification to proceed against actual clauses.
        pass

    return (num_vars or 0, len(clauses), clauses)


def parse_model_string(model_input: str) -> Set[int]:
    """
    Parses a model string into a set of assigned integer literals.
    Accepts raw Glucose model lines ('v 1 -2 3 0') or raw literal strings.

    Returns:
        Set of integer literals (e.g. {1, -2, 3}).
    """
    model_literals: Set[int] = set()
    seen_vars: Set[int] = set()

    for line in model_input.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading 'v' or 'V' if present
        if line.startswith(('v ', 'v\t', 'V ', 'V\t')):
            tokens = line[1:].strip().split()
        elif line.startswith('v') and len(line) > 1 and line[1].isdigit():
            tokens = line[1:].strip().split()
        elif line.startswith(('s ', 'c ')):
            # Skip status or comment lines
            continue
        else:
            tokens = line.split()

        for token in tokens:
            try:
                lit = int(token)
            except ValueError:
                raise ModelParseError(f"Invalid non-integer literal in model: '{token}'")

            if lit == 0:
                continue

            var = abs(lit)
            # Check for contradictory assignments (e.g. both x and -x)
            if -lit in model_literals:
                raise ModelParseError(
                    f"Contradictory assignment in model: variable {var} assigned both True and False ({lit} and {-lit})"
                )

            model_literals.add(lit)
            seen_vars.add(var)

    if not model_literals:
        raise ModelParseError("Model contains no literals or could not be parsed.")

    return model_literals


def verify_model(cnf_path: str, model_data: str | List[int] | Set[int]) -> Tuple[bool, str]:
    """
    Verifies that the given model satisfies all clauses of the CNF file.

    Args:
        cnf_path: Path to the DIMACS CNF file.
        model_data: String containing solver output or collection of literal ints.

    Returns:
        (is_valid, message)
    """
    try:
        num_vars, declared_clauses, clauses = parse_dimacs_cnf(cnf_path)
    except Exception as e:
        return (False, f"CNF parsing error: {e}")

    try:
        if isinstance(model_data, str):
            model_literals = parse_model_string(model_data)
        elif isinstance(model_data, (list, set)):
            model_literals = set()
            for lit in model_data:
                lit_int = int(lit)
                if lit_int == 0:
                    continue
                if -lit_int in model_literals:
                    return (False, f"Contradictory assignment in model for variable {abs(lit_int)}")
                model_literals.add(lit_int)
        else:
            return (False, f"Unsupported model data type: {type(model_data)}")
    except Exception as e:
        return (False, f"Model parsing error: {e}")

    if not clauses:
        return (True, "Trivially satisfied: formula contains zero clauses.")

    # Check each clause
    for i, clause in enumerate(clauses, start=1):
        if not clause:
            # An empty clause is logically False and can never be satisfied
            return (False, f"Empty clause detected at index {i} (unsatisfiable clause)")

        clause_satisfied = False
        for lit in clause:
            if lit in model_literals:
                clause_satisfied = True
                break

        if not clause_satisfied:
            return (
                False,
                f"Clause {i} ({' '.join(map(str, clause))} 0) is NOT satisfied by the model."
            )

    return (True, f"SUCCESS: All {len(clauses)} clauses satisfied by the model.")


def main():
    parser = argparse.ArgumentParser(
        description="Verify that a SAT model satisfies a DIMACS CNF formula."
    )
    parser.add_argument("cnf_file", help="Path to DIMACS CNF file")
    parser.add_argument("model_file", nargs="?", help="Path to model file (or omit to read from stdin)")
    args = parser.parse_args()

    if args.model_file:
        if not os.path.isfile(args.model_file):
            print(f"Error: Model file '{args.model_file}' not found.", file=sys.stderr)
            sys.exit(2)
        with open(args.model_file, "r", encoding="utf-8", errors="replace") as f:
            model_content = f.read()
    else:
        model_content = sys.stdin.read()

    is_valid, msg = verify_model(args.cnf_file, model_content)
    print(msg)
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()

