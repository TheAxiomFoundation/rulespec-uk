#!/usr/bin/env python3
"""Print the guard-generated `--roots` for an applied module path.

`axiom-encode guard-generated --roots` wants the space-separated jurisdiction
roots that the changed files live under. A bulk job touches exactly one
jurisdiction directory plus (defensively) the national `uk` root, matching how
the org validate workflow scopes a single-jurisdiction change.

Usage:
  python bulk/roots_for.py uk/statutes/ukpga/2003/1/681B.yaml   # -> "uk"
  python bulk/roots_for.py uk-kingston-upon-thames/policies/x.yaml # -> "uk uk-kingston-upon-thames"
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath


def roots_for(module_path: str) -> str:
    parts = PurePosixPath(module_path).parts
    if not parts:
        return "uk"
    juris = parts[0]
    # Always include the national root so cross-jurisdiction imports resolve;
    # include the module's own jurisdiction when it is a sub-national directory.
    roots = ["uk"]
    if juris != "uk" and juris.startswith("uk-"):
        roots.append(juris)
    return " ".join(dict.fromkeys(roots))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: roots_for.py <module-path>", file=sys.stderr)
        raise SystemExit(2)
    print(roots_for(sys.argv[1]))
