"""Staged receipt layout retains retirement evidence after content disappears."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
import yaml

import test_repository_layout as layout

try:
    from hypothesis import given, settings, strategies as st
except ImportError:
    given = None


JURISDICTIONS = ("uk", "uk-adur", "uk-babergh")


def retirement_repository(
    root: Path,
    *,
    jurisdiction: str = "uk-adur",
    source_root: str = "policies",
    surviving_content_root: bool = False,
) -> None:
    """Retire a primary and companion, retaining the jurisdiction's README."""
    structure = root / ".axiom" / "repository-structure.yaml"
    structure.parent.mkdir(parents=True)
    structure.write_text(
        yaml.safe_dump({"allowed_root_directories": list(JURISDICTIONS)})
    )
    jurisdiction_dir = root / jurisdiction
    jurisdiction_dir.mkdir()
    (jurisdiction_dir / "README.md").write_text("Retained jurisdiction metadata.\n")
    content_root = jurisdiction_dir / source_root
    content_root.mkdir()
    for filename in ("award.yaml", "award.test.yaml"):
        path = content_root / filename
        path.write_text("[]\n")
        path.unlink()
    if surviving_content_root:
        (content_root / "survivor.yaml").write_text("[]\n")
        (content_root / "survivor.test.yaml").write_text("[]\n")
    else:
        # Git does not retain this empty directory after the final retirement.
        content_root.rmdir()
    receipt = (
        root / ".axiom" / "encoding-manifests" / jurisdiction / source_root
        / "award.json"
    )
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps({
            "schema_version": "axiom-encode/applied-rulespec/v5",
            "applied_files": [
                {"path": f"{jurisdiction}/{source_root}/{filename}", "deleted": True}
                for filename in ("award.yaml", "award.test.yaml")
            ],
        })
    )


def test_retirement_receipt_with_surviving_content_root(tmp_path, monkeypatch) -> None:
    retirement_repository(tmp_path, surviving_content_root=True)
    monkeypatch.setattr(layout, "ROOT", tmp_path)

    layout.test_encoding_manifests_use_only_the_canonical_root_mirror()


def test_retirement_receipt_after_last_content_root_removed(tmp_path, monkeypatch) -> None:
    retirement_repository(tmp_path)
    monkeypatch.setattr(layout, "ROOT", tmp_path)
    assert (tmp_path / "uk-adur" / "README.md").is_file()
    assert layout.jurisdiction_dirs() == []

    layout.test_encoding_manifests_use_only_the_canonical_root_mirror()


def check_retirement_layout(
    tmp_path_factory,
    jurisdiction: str,
    source_root: str,
    surviving_content_root: bool,
) -> None:
    with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
        root = Path(directory)
        retirement_repository(
            root,
            jurisdiction=jurisdiction,
            source_root=source_root,
            surviving_content_root=surviving_content_root,
        )
        with patch.object(layout, "ROOT", root):
            layout.test_encoding_manifests_use_only_the_canonical_root_mirror()


if given is not None:
    @settings(max_examples=24, deadline=None, derandomize=True, database=None)
    @given(
        jurisdiction=st.sampled_from(JURISDICTIONS),
        source_root=st.sampled_from(layout.ATOMIC_CONTENT_DIRS),
        surviving_content_root=st.booleans(),
    )
    def test_generated_retirement_layout_invariant(
        tmp_path_factory, jurisdiction, source_root, surviving_content_root
    ) -> None:
        check_retirement_layout(
            tmp_path_factory, jurisdiction, source_root, surviving_content_root
        )
else:
    @pytest.mark.parametrize("jurisdiction", JURISDICTIONS)
    @pytest.mark.parametrize("source_root", layout.ATOMIC_CONTENT_DIRS)
    @pytest.mark.parametrize("surviving_content_root", (False, True))
    def test_generated_retirement_layout_invariant(
        tmp_path_factory, jurisdiction, source_root, surviving_content_root
    ) -> None:
        check_retirement_layout(
            tmp_path_factory, jurisdiction, source_root, surviving_content_root
        )


def test_retirement_receipt_rejects_unregistered_jurisdiction(tmp_path, monkeypatch) -> None:
    retirement_repository(tmp_path, jurisdiction="uk-unregistered")
    monkeypatch.setattr(layout, "ROOT", tmp_path)

    with pytest.raises(AssertionError):
        layout.test_encoding_manifests_use_only_the_canonical_root_mirror()


def test_retired_jurisdiction_rejects_colocated_manifest_root(tmp_path, monkeypatch) -> None:
    retirement_repository(tmp_path)
    (tmp_path / ".axiom" / "encoding-manifests" / "uk-adur" / "policies" / "award.json").unlink()
    nested = tmp_path / "uk-adur" / ".axiom" / "encoding-manifests"
    nested.mkdir(parents=True)
    monkeypatch.setattr(layout, "ROOT", tmp_path)

    with pytest.raises(AssertionError):
        layout.test_encoding_manifests_use_only_the_canonical_root_mirror()
