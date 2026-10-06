"""Consistency checks for the English council registry.

Two files describe the 296 English billing authorities:

  * ``data/councils/registry.csv`` is the roster. The layout test reads its
    slugs as the allowlist of ``uk-<slug>`` jurisdiction namespaces.
  * ``docs/uk-ctr/councils.csv`` is the council tax reduction campaign
    registry. It adds the PR, corpus, heading-family and notes columns.

Both carry ``status`` and ``scheme_url``. These tests keep the two files in
step with each other and with the tree, so a council's status cannot drift
from what is actually encoded (rulespec-uk#347).
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data" / "councils" / "registry.csv"
CAMPAIGN = ROOT / "docs" / "uk-ctr" / "councils.csv"

ROSTER_COLUMNS = ["ons_code", "name", "slug", "scheme_url", "status"]
CAMPAIGN_COLUMNS = [
    "ons_code",
    "name",
    "jurisdiction",
    "status",
    "pr",
    "corpus_version",
    "heading_family",
    "scheme_url",
    "other_source_urls",
    "notes",
]
# Pipeline order; docs/uk-ctr/README.md defines each status.
STATUSES = (
    "encoded",
    "encode-pr-open",
    "ingested",
    "ingested-unreleased",
    "continuation-pair-ready",
    "continuation-ready",
    "continuation-needs-linkage",
    "continuation-case",
    "amendment-case-ready",
    "amendment-case",
    "amendment-needs-values",
    "rendition-case",
    "discovered-source-conflict",
    "discovered-prior-year",
    "discovered-summary-only",
    "discovered-pension-only-needs-working-age-doc",
    "discovered-html",
    "discovered-fetch-blocked",
    "browser-case",
)
# ONS local authority district codes for England, April 2025:
# unitary (E06), district (E07), metropolitan district (E08), London (E09).
ENGLISH_LAD_COUNTS = {"E06": 63, "E07": 164, "E08": 36, "E09": 33}
ONS_CODE_RE = re.compile(r"^E0[6-9]\d{6}$")


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def roster_rows() -> list[dict[str, str]]:
    columns, rows = read_rows(ROSTER)
    assert columns == ROSTER_COLUMNS
    return rows


def campaign_rows() -> list[dict[str, str]]:
    columns, rows = read_rows(CAMPAIGN)
    assert columns == CAMPAIGN_COLUMNS
    return rows


def councils_with_ctr_module() -> set[str]:
    return {
        path.parents[2].name
        for path in ROOT.glob("uk-*/policies/*/council-tax-reduction.yaml")
        if path.parent.name == path.parents[2].name.removeprefix("uk-")
    }


def test_registries_list_the_same_english_authorities_in_the_same_order() -> None:
    roster = roster_rows()
    campaign = campaign_rows()

    assert [(r["ons_code"], r["name"], f"uk-{r['slug']}") for r in roster] == [
        (r["ons_code"], r["name"], r["jurisdiction"]) for r in campaign
    ]
    codes = [r["ons_code"] for r in campaign]
    assert all(ONS_CODE_RE.match(code) for code in codes)
    assert len(set(codes)) == len(codes)
    assert codes == sorted(codes)
    assert Counter(code[:3] for code in codes) == ENGLISH_LAD_COUNTS


def test_registries_agree_on_status_and_scheme_url() -> None:
    roster = {r["ons_code"]: r for r in roster_rows()}
    mismatches = [
        (r["ons_code"], field, roster[r["ons_code"]][field], r[field])
        for r in campaign_rows()
        for field in ("status", "scheme_url")
        if roster[r["ons_code"]][field] != r[field]
    ]
    assert mismatches == []


def test_statuses_use_the_documented_vocabulary() -> None:
    unknown = sorted(
        {r["status"] for r in campaign_rows()} - set(STATUSES)
    )
    assert unknown == []


def test_encoded_status_matches_the_modules_in_the_tree() -> None:
    encoded = {r["jurisdiction"] for r in campaign_rows() if r["status"] == "encoded"}
    modules = councils_with_ctr_module()

    assert sorted(modules - encoded) == [], "module on disk but not marked encoded"
    assert sorted(encoded - modules) == [], "marked encoded but no module on disk"


def test_pr_column_is_set_exactly_for_open_encode_prs() -> None:
    problems = [
        (r["jurisdiction"], r["status"], r["pr"])
        for r in campaign_rows()
        if (r["status"] == "encode-pr-open") != bool(re.fullmatch(r"\d+", r["pr"]))
    ]
    assert problems == []
