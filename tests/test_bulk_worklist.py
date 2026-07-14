"""Tests for the bulk encode planner (bulk/compute_matrix.py + bulk/roots_for.py).

These cover the post-#133 planner contract: corpus `citation` entries and
council/module `target` entries are both selectable and slug cleanly, and the
real committed worklist is well-formed (every entry sets exactly one target).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BULK = REPO_ROOT / "bulk"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(f"bulk_{name}", BULK / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


compute_matrix = _load_module("compute_matrix")
roots_for = _load_module("roots_for")

KINGSTON = (
    "uk-kingston-upon-thames/policies/kingston-upon-thames/council-tax-reduction.yaml"
)


def test_citation_slug_corpus_paths():
    assert (
        compute_matrix.citation_slug("uk/statute/ukpga/2003/1/681B")
        == "uk-statute-ukpga-2003-1-681b"
    )
    assert (
        compute_matrix.citation_slug(
            "uk/regulation/uksi/2012/2885/schedule/1/paragraph/2"
        )
        == "uk-regulation-uksi-2012-2885-schedule-1-paragraph-2"
    )


def test_citation_slug_module_target_strips_extension():
    assert (
        compute_matrix.citation_slug(KINGSTON)
        == "uk-kingston-upon-thames-policies-kingston-upon-thames-council-tax-reduction"
    )
    assert compute_matrix.citation_slug(
        "uk-kingston-upon-thames/policies/x/council-tax-reduction.test.yaml"
    ) == "uk-kingston-upon-thames-policies-x-council-tax-reduction"


def test_entry_ref_requires_exactly_one():
    assert compute_matrix.entry_ref({"citation": "uk/statute/x"}) == "uk/statute/x"
    assert compute_matrix.entry_ref({"target": KINGSTON}) == KINGSTON
    with pytest.raises(SystemExit):
        compute_matrix.entry_ref({"citation": "a", "target": "b"})
    with pytest.raises(SystemExit):
        compute_matrix.entry_ref({})


def test_select_includes_citation_and_target_entries():
    data = {
        "defaults": {"backend": "openai", "model": "gpt-5.5"},
        "entries": [
            {
                "citation": "uk/regulation/uksi/2012/2885/11",
                "batch": "CTR-ENP",
                "status": "pending",
            },
            {"target": KINGSTON, "batch": "D", "status": "pending"},
            {"citation": "uk/statute/x", "batch": "A", "status": "done"},
        ],
    }
    selected = compute_matrix.select(data, "pending", None, None)
    assert len(selected) == 2
    corpus = next(item for item in selected if item["citation"])
    council = next(item for item in selected if item["target"])
    assert corpus["target"] is None
    assert corpus["slug"] == "uk-regulation-uksi-2012-2885-11"
    assert council["citation"] is None
    assert (
        council["slug"]
        == "uk-kingston-upon-thames-policies-kingston-upon-thames-council-tax-reduction"
    )


def test_batch_and_limit_filters():
    data = {
        "entries": [
            {"citation": "a", "batch": "CTR-ENP", "status": "pending"},
            {"citation": "b", "batch": "CTR-ENP", "status": "pending"},
            {"citation": "c", "batch": "CTR-SC", "status": "pending"},
        ]
    }
    assert len(compute_matrix.select(data, "pending", "CTR-ENP", None)) == 2
    assert len(compute_matrix.select(data, "pending", "CTR-ENP", 1)) == 1
    assert len(compute_matrix.select(data, "pending", "ctr-sc", None)) == 1


def test_roots_for_council_and_corpus():
    assert roots_for.roots_for(KINGSTON) == "uk uk-kingston-upon-thames"
    assert roots_for.roots_for("uk/statutes/ukpga/2003/1/681B.yaml") == "uk"


def test_committed_worklist_is_well_formed():
    data = compute_matrix.load()
    assert data.get("entries"), "worklist has no entries"
    seen_slugs: dict[str, str] = {}
    for entry in data["entries"]:
        ref = compute_matrix.entry_ref(entry)  # raises if not exactly one target
        slug = compute_matrix.citation_slug(ref)
        assert slug, f"empty slug for {ref}"
        assert slug not in seen_slugs, f"duplicate slug {slug}: {ref} vs {seen_slugs[slug]}"
        seen_slugs[slug] = ref
