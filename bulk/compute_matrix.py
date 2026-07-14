#!/usr/bin/env python3
"""Compute the bulk-encode job matrix from bulk/worklist.yaml.

The worklist is the durable queue. This script is the single source of truth
for turning it into a GitHub Actions matrix and for reading/writing entry
status, so CI and local operators behave identically.

Each entry targets exactly one of:
  * `citation` -- a corpus citation path (uk/statute/..., uk/regulation/...),
    the standard bulk case; the encoder resolves the provision from the corpus.
  * `target` -- a repo module path or council scope
    (e.g. uk-kingston-upon-thames/policies/kingston-upon-thames/council-tax-reduction.yaml),
    for council / re-emission entries whose encoder invocation targets a module
    rather than a corpus citation. This field only lets the planner *express and
    select* such an entry; the operator's signed-apply session owns how it is
    encoded.

Usage:
  # Emit a GitHub Actions matrix of pending entries (optionally capped/filtered):
  python bulk/compute_matrix.py --status pending [--batch A] [--limit 8]

  # Human-readable listing:
  python bulk/compute_matrix.py --status pending --format table

  # Read one field (used to look up backend/model per entry, by citation OR target):
  python bulk/compute_matrix.py --get uk/statute/ukpga/2003/1/681B --field model

The matrix shape is {"include": [{"citation", "target", "repo", "backend",
"model", "slug"}, ...]} (exactly one of `citation`/`target` is set per item).
`slug` is the branch-safe slug used for `bulk/<slug>` branches and the PR title.

Status writes are intentionally NOT done here: the workflow updates statuses by
committing to the worklist through a dedicated follow-up (so status changes are
reviewable diffs, never silent CI mutations). `--set-status` exists only for
local operator use and edits the file in place.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

WORKLIST = Path(__file__).resolve().parent / "worklist.yaml"

SELECTABLE_STATUSES = {"pending"}


def citation_slug(ref: str) -> str:
    """Branch-safe slug for a corpus citation path or a module/target path.

    uk/statute/ukpga/2003/1/681B -> uk-statute-ukpga-2003-1-681b
    uk/regulation/uksi/2006/213/70 -> uk-regulation-uksi-2006-213-70
    uk-kingston-upon-thames/policies/kingston-upon-thames/council-tax-reduction.yaml
      -> uk-kingston-upon-thames-policies-kingston-upon-thames-council-tax-reduction
    """
    slug = ref.strip().lower()
    # Module/target paths may carry a RuleSpec extension; drop it for a clean slug.
    for suffix in (".test.yaml", ".test.yml", ".yaml", ".yml"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def entry_ref(entry: dict) -> str:
    """The encode target for one worklist entry.

    Exactly one of `citation` (a corpus citation path) or `target` (a module
    path / council scope) must be set. Raises otherwise so a malformed queue
    fails closed rather than silently selecting nothing.
    """
    citation = entry.get("citation")
    target = entry.get("target")
    if bool(citation) == bool(target):
        raise SystemExit(
            "worklist entry must set exactly one of 'citation' or 'target': "
            f"{entry!r}"
        )
    return citation or target


def load() -> dict:
    data = yaml.safe_load(WORKLIST.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or "entries" not in data:
        raise SystemExit(f"{WORKLIST} is missing an 'entries' list")
    return data


def entry_backend(data: dict, entry: dict) -> str:
    return entry.get("backend") or data.get("defaults", {}).get("backend", "openai")


def entry_model(data: dict, entry: dict) -> str:
    return entry.get("model") or data.get("defaults", {}).get("model", "gpt-5.5")


def select(data: dict, status: str, batch: str | None, limit: int | None) -> list[dict]:
    out: list[dict] = []
    for entry in data["entries"]:
        if status != "any" and entry.get("status") != status:
            continue
        if batch and str(entry.get("batch", "")).upper() != batch.upper():
            continue
        ref = entry_ref(entry)
        out.append(
            {
                "citation": entry.get("citation"),
                "target": entry.get("target"),
                "repo": entry.get("repo", "rulespec-uk"),
                "backend": entry_backend(data, entry),
                "model": entry_model(data, entry),
                "slug": citation_slug(ref),
            }
        )
    if limit is not None:
        out = out[:limit]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", default="pending", help="Entry status to select (or 'any').")
    ap.add_argument("--batch", default=None, help="Restrict to a batch label (A, B, ...).")
    ap.add_argument("--limit", type=int, default=None, help="Cap the number of entries.")
    ap.add_argument(
        "--format",
        choices=["matrix", "table", "count"],
        default="matrix",
        help="matrix = GitHub Actions include JSON; table = human listing.",
    )
    ap.add_argument("--get", default=None, help="Look up a single entry by its citation OR target.")
    ap.add_argument("--field", default=None, help="With --get, print one field (model/backend/status/slug).")
    ap.add_argument(
        "--set-status",
        nargs=2,
        metavar=("REF", "STATUS"),
        default=None,
        help="LOCAL ONLY: set an entry's status in place (REF = its citation or target).",
    )
    args = ap.parse_args()

    data = load()

    if args.set_status:
        ref, new_status = args.set_status
        found = False
        for entry in data["entries"]:
            if entry_ref(entry) == ref:
                entry["status"] = new_status
                found = True
                break
        if not found:
            raise SystemExit(f"entry not found: {ref}")
        WORKLIST.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        print(f"set {ref} -> {new_status}")
        return 0

    if args.get:
        for entry in data["entries"]:
            if entry_ref(entry) == args.get:
                if args.field == "slug":
                    print(citation_slug(entry_ref(entry)))
                elif args.field == "model":
                    print(entry_model(data, entry))
                elif args.field == "backend":
                    print(entry_backend(data, entry))
                elif args.field:
                    print(entry.get(args.field, ""))
                else:
                    print(json.dumps(entry))
                return 0
        raise SystemExit(f"entry not found: {args.get}")

    selected = select(data, args.status, args.batch, args.limit)

    if args.format == "count":
        print(len(selected))
    elif args.format == "table":
        for item in selected:
            ref = item.get("citation") or item.get("target") or ""
            print(f"{item['slug']:34s} {item['backend']}:{item['model']:10s} {ref}")
        print(f"\n{len(selected)} entr{'y' if len(selected) == 1 else 'ies'} selected (status={args.status}).")
    else:
        print(json.dumps({"include": selected}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
