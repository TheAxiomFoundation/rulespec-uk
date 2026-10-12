"""Receipt-only changes remain forbidden until the signed encoder is re-pinned."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import test_repository_layout as layout

try:
    from hypothesis import given, settings, strategies as st
except ImportError:
    given = None


def _write_receipt(root: Path, filename: str, payload: object) -> None:
    path = root / ".axiom" / "encoding-manifests" / "uk" / "policies" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


@pytest.mark.parametrize("tampered", [False, True], ids=["unsigned", "tampered"])
def test_receipt_only_changes_are_prohibited(tmp_path, monkeypatch, tampered):
    monkeypatch.setattr(layout, "ROOT", tmp_path)
    primary = tmp_path / "uk" / "policies" / "example.yaml"
    primary.parent.mkdir(parents=True)
    companion = primary.with_suffix(".test.yaml")
    primary.write_text("format: rulespec/v1\n")
    companion.write_text("[]\n")
    original = {path: path.read_bytes() for path in (primary, companion)}
    structure = tmp_path / ".axiom" / "repository-structure.yaml"
    structure.parent.mkdir()
    structure.write_text("allowed_root_directories: [uk]\n")
    payload = {
        "schema_version": "axiom-encode/applied-rulespec/v5",
        "applied_files": [
            {"path": "uk/policies/example.yaml"},
            {"path": "uk/policies/example.test.yaml"},
        ],
    }
    if tampered:
        payload["signature"] = {"value": "tampered"}
        payload["applied_files"][0]["sha256"] = "0" * 64
    _write_receipt(tmp_path, "example.json", payload)

    # Placement alone cannot establish signed provenance.
    layout.test_encoding_manifests_use_only_the_canonical_root_mirror()
    with pytest.raises(AssertionError, match="prelaunch hard cut"):
        layout.test_legacy_applied_manifests_are_not_kept_as_migration_inputs()
    assert {path: path.read_bytes() for path in original} == original


def _assert_every_receipt_is_prohibited(
    root: Path, filename: str, payload: object
) -> None:
    _write_receipt(root, filename, payload)
    with pytest.raises(AssertionError, match="prelaunch hard cut"):
        layout.test_legacy_applied_manifests_are_not_kept_as_migration_inputs()


if given is not None:
    @settings(max_examples=24, deadline=None, derandomize=True, database=None)
    @given(
        stem=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=32
        ),
        payload=st.one_of(
            st.none(), st.booleans(), st.integers(), st.text(),
            st.dictionaries(st.text(), st.text()),
        ),
    )
    def test_receipt_prohibition_is_independent_of_name_and_contents(
        tmp_path_factory, stem, payload
    ):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
            root = Path(directory)
            with patch.object(layout, "ROOT", root):
                _assert_every_receipt_is_prohibited(root, f"{stem}.json", payload)

else:
    @pytest.mark.parametrize("filename", ["example.json", "nested/example.json"])
    @pytest.mark.parametrize(
        "payload", [None, False, 0, "unsigned", {}, {"signature": "tampered"}]
    )
    def test_receipt_prohibition_is_independent_of_name_and_contents(
        tmp_path, monkeypatch, filename, payload
    ):
        monkeypatch.setattr(layout, "ROOT", tmp_path)
        _assert_every_receipt_is_prohibited(tmp_path, filename, payload)
