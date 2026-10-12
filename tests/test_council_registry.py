"""Keep the English council roster and CTR campaign registry consistent.

The roster supplies the jurisdiction allowlist. The campaign registry adds
source discovery and ingestion evidence, which can predate the current tree.
Only module and open-PR statuses are synchronized with the roster; these tests
check module presence locally without relying on live GitHub or corpus access.
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
STATUSES = {
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
}
# The campaign uses the ONS English local authority district roster, April 2025.
ENGLISH_LAD_COUNTS = {"E06": 63, "E07": 164, "E08": 36, "E09": 33}


def read_rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == columns
        rows = list(reader)
    assert all(None not in row and None not in row.values() for row in rows)
    return rows


def roster_rows() -> list[dict[str, str]]:
    return read_rows(ROSTER, ROSTER_COLUMNS)


def campaign_rows() -> list[dict[str, str]]:
    return read_rows(CAMPAIGN, CAMPAIGN_COLUMNS)


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
    assert all(re.fullmatch(r"E0[6-9]\d{6}", code) for code in codes)
    assert len(set(codes)) == len(codes)
    assert codes == sorted(codes)
    assert Counter(code[:3] for code in codes) == ENGLISH_LAD_COUNTS
    jurisdictions = [r["jurisdiction"] for r in campaign]
    assert len(set(jurisdictions)) == len(jurisdictions)


def test_current_module_and_pr_statuses_agree_between_registries() -> None:
    roster = {r["ons_code"]: r for r in roster_rows()}
    current_statuses = {"encoded", "encode-pr-open"}
    mismatches = [
        (r["ons_code"], roster[r["ons_code"]]["status"], r["status"])
        for r in campaign_rows()
        if (
            r["status"] in current_statuses
            or roster[r["ons_code"]]["status"] in current_statuses
        )
        and roster[r["ons_code"]]["status"] != r["status"]
    ]
    assert mismatches == []


def test_campaign_statuses_use_the_documented_vocabulary() -> None:
    assert {r["status"] for r in campaign_rows()} <= STATUSES


def test_encoded_status_matches_the_modules_in_the_tree() -> None:
    encoded = {r["jurisdiction"] for r in campaign_rows() if r["status"] == "encoded"}
    modules = councils_with_ctr_module()
    assert modules - encoded == set(), "module on disk but not marked encoded"
    assert encoded - modules == set(), "marked encoded but no module on disk"


def test_pr_column_is_set_exactly_for_open_encode_pr_status() -> None:
    rows = campaign_rows()
    for row in rows:
        if row["status"] == "encode-pr-open":
            assert re.fullmatch(r"[1-9]\d*", row["pr"]), row["jurisdiction"]
        else:
            assert row["pr"] == "", row["jurisdiction"]
    prs = [row["pr"] for row in rows if row["pr"]]
    assert len(set(prs)) == len(prs)


def test_ingested_and_encoded_rows_identify_the_corpus_version() -> None:
    for row in campaign_rows():
        if row["status"] in {
            "encoded", "encode-pr-open", "ingested", "ingested-unreleased"
        }:
            assert re.fullmatch(
                r"\d{4}-\d{2}-\d{2}-.+-council-tax-reduction-2026-2027",
                row["corpus_version"],
            ), row["jurisdiction"]
