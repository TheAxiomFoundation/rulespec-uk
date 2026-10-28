"""Receipts are admitted as trusted v5 JSON in canonical layout, never via a symlink.

These tests drive the two repository checks that replaced the blanket
encoding-manifest prohibition: the canonical root-mirror layout check and the
trusted v5 schema check. Both check layout and schema only; authenticating a
receipt is the pinned encoder's job in CI.
"""

from __future__ import annotations

import json
import os
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
V5 = layout.TRUSTED_APPLIED_MANIFEST_SCHEMA
NAME_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_-"


def receipt_bytes(kind: str, applied_files: list[dict]) -> bytes:
    """Serialise one receipt variant. Only `v5` declares the trusted schema."""
    receipt = {"schema_version": V5, "applied_files": applied_files}
    if kind == "v5":
        return json.dumps(receipt).encode()
    if kind == "missing-schema":
        return json.dumps({"applied_files": applied_files}).encode()
    if kind.startswith("schema="):
        return json.dumps(
            {**receipt, "schema_version": json.loads(kind.removeprefix("schema="))}
        ).encode()
    non_json = {
        "non-json-yaml": f"schema_version: {V5}\n".encode(),
        "non-json-empty": b"",
        "non-json-truncated": json.dumps(receipt).encode()[:-1],
        "non-json-invalid-utf8": b'{"schema_version": "\xff"}',
    }
    if kind in non_json:
        return non_json[kind]
    non_object = {
        "non-object-list": [receipt],
        "non-object-string": V5,
        "non-object-null": None,
        "non-object-number": 5,
        "non-object-true": True,
    }
    return json.dumps(non_object[kind]).encode()


UNTRUSTED_SCHEMA_KINDS = (
    "schema=" + json.dumps("axiom-encode/applied-rulespec/v4"),
    "schema=" + json.dumps("axiom-encode/applied-rulespec/v6"),
    "schema=" + json.dumps(V5 + " "),
    "schema=" + json.dumps(V5.upper()),
    "schema=" + json.dumps([V5]),
    "schema=null",
)
NON_JSON_KINDS = (
    "non-json-yaml",
    "non-json-empty",
    "non-json-truncated",
    "non-json-invalid-utf8",
)
NON_OBJECT_KINDS = (
    "non-object-list",
    "non-object-string",
    "non-object-null",
    "non-object-number",
    "non-object-true",
)
# The schema check's message for each family of refused payloads.
REFUSALS = (
    *((kind, "untrusted schema") for kind in UNTRUSTED_SCHEMA_KINDS),
    ("missing-schema", "untrusted schema None"),
    *((kind, "not JSON") for kind in NON_JSON_KINDS),
    *((kind, "not a JSON object") for kind in NON_OBJECT_KINDS),
)


def admission_repository(
    root: Path,
    *,
    jurisdiction: str = "uk",
    source_root: str = "policies",
    nesting: tuple[str, ...] = (),
    stem: str = "example",
    kind: str = "v5",
) -> Path:
    """Write one module, its companion and their receipt; return the receipt."""
    structure = root / ".axiom" / "repository-structure.yaml"
    structure.parent.mkdir(parents=True, exist_ok=True)
    structure.write_text(
        yaml.safe_dump({"allowed_root_directories": list(JURISDICTIONS)})
    )
    module_parts = (jurisdiction, source_root, *nesting)
    module_dir = root.joinpath(*module_parts)
    module_dir.mkdir(parents=True, exist_ok=True)
    applied_files = []
    for suffix in (".yaml", ".test.yaml"):
        (module_dir / f"{stem}{suffix}").write_text("[]\n")
        applied_files.append({"path": "/".join((*module_parts, f"{stem}{suffix}"))})
    receipt = root.joinpath(".axiom", "encoding-manifests", *module_parts, f"{stem}.json")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(receipt_bytes(kind, applied_files))
    return receipt


def passes(check) -> bool:
    """Run a repository check; only an AssertionError counts as a refusal."""
    try:
        check()
    except AssertionError:
        return False
    return True


def outcomes(root: Path) -> tuple[bool, bool]:
    """(layout check passes, schema check passes) for the repository at root."""
    with patch.object(layout, "ROOT", root):
        return (
            passes(layout.test_encoding_manifests_use_only_the_canonical_root_mirror),
            passes(layout.test_applied_manifests_use_trusted_v5_schema),
        )


def manifest_tree(root: Path) -> tuple[list[Path], list[str]]:
    with patch.object(layout, "ROOT", root):
        return layout.encoding_manifest_tree()


ALIAS_KINDS = ("metadata-root", "manifest-root", "intermediate", "receipt")


def alias_component(
    root: Path, outside: Path, receipt: Path, kind: str, *, inside: bool, level: int = 0
) -> tuple[Path, str]:
    """Move one component of the receipt's path away and symlink it back.

    The moved copy is intact, so the symlink is the only defect. Returns the
    symlink and the walk problem it must raise. `level` picks which directory
    between the manifest root and the receipt is aliased, counting from the
    jurisdiction directory.
    """
    manifest_root = root / ".axiom" / "encoding-manifests"
    if kind == "metadata-root":
        component, problem = root / ".axiom", "aliased manifest ancestor: .axiom"
    elif kind == "manifest-root":
        component = manifest_root
        problem = "aliased manifest root: .axiom/encoding-manifests"
    elif kind == "intermediate":
        between = receipt.relative_to(manifest_root).parts[:-1]
        component = manifest_root.joinpath(*between[: level % len(between) + 1])
        problem = f"aliased manifest path: {component.relative_to(manifest_root).as_posix()}"
    elif kind == "receipt":
        component = receipt
        problem = f"aliased manifest path: {receipt.relative_to(manifest_root).as_posix()}"
    else:
        raise ValueError(kind)
    base = root / "aliased-targets" if inside else outside
    target = base / component.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    component.rename(target)
    link = os.path.relpath(target, component.parent) if inside else target
    component.symlink_to(link, target_is_directory=target.is_dir())
    assert component.resolve().is_relative_to(root.resolve()) is inside
    return component, problem


def test_absent_manifest_root_admits_the_repository(tmp_path) -> None:
    (tmp_path / ".axiom").mkdir()
    (tmp_path / ".axiom" / "repository-structure.yaml").write_text(
        yaml.safe_dump({"allowed_root_directories": list(JURISDICTIONS)})
    )

    assert manifest_tree(tmp_path) == ([], [])
    assert outcomes(tmp_path) == (True, True)


def test_v5_receipt_in_canonical_layout_is_admitted(tmp_path) -> None:
    receipt = admission_repository(tmp_path, nesting=("council", "scheme"))

    assert manifest_tree(tmp_path) == ([receipt], [])
    assert outcomes(tmp_path) == (True, True)


@pytest.mark.parametrize(("kind", "message"), REFUSALS, ids=[kind for kind, _ in REFUSALS])
def test_schema_check_refuses_untrusted_payloads(tmp_path, monkeypatch, kind, message) -> None:
    admission_repository(tmp_path, kind=kind)
    monkeypatch.setattr(layout, "ROOT", tmp_path)

    with pytest.raises(AssertionError) as refusal:
        layout.test_applied_manifests_use_trusted_v5_schema()
    assert message in str(refusal.value)
    # The layout check also refuses rather than crashing on the payload.
    assert outcomes(tmp_path) == (False, False)


def test_schema_check_does_not_judge_layout(tmp_path) -> None:
    receipt = admission_repository(tmp_path)
    stray = tmp_path / ".axiom" / "encoding-manifests" / "uk" / "example.json"
    receipt.rename(stray)

    assert outcomes(tmp_path) == (False, True)


ALIAS_CASES = (
    ("metadata-root", 0),
    ("manifest-root", 0),
    ("intermediate", 0),  # .axiom/encoding-manifests/uk
    ("intermediate", 1),  # .axiom/encoding-manifests/uk/policies
    ("intermediate", 3),  # .axiom/encoding-manifests/uk/policies/council/scheme
    ("receipt", 0),
)


@pytest.mark.parametrize("inside", (True, False), ids=("inside-repo", "outside-repo"))
@pytest.mark.parametrize(
    ("kind", "level"), ALIAS_CASES, ids=[f"{kind}-{level}" for kind, level in ALIAS_CASES]
)
def test_symlink_on_the_receipt_path_is_refused(tmp_path, kind, level, inside) -> None:
    root, outside = tmp_path / "repo", tmp_path / "outside"
    receipt = admission_repository(root, nesting=("council", "scheme"))
    assert outcomes(root) == (True, True)

    _, problem = alias_component(root, outside, receipt, kind, inside=inside, level=level)

    files, problems = manifest_tree(root)
    assert problems == [problem]
    # The walk never enters an aliased directory, so it sees no receipt there.
    assert files == []
    assert outcomes(root) == (False, False)


def test_walk_never_enters_a_symlinked_directory(tmp_path) -> None:
    root, outside = tmp_path / "repo", tmp_path / "outside"
    receipt = admission_repository(root)
    elsewhere = admission_repository(outside, stem="elsewhere")
    link = root / ".axiom" / "encoding-manifests" / "uk" / "policies" / "linked"
    link.symlink_to(elsewhere.parent, target_is_directory=True)
    read: list[Path] = []
    load = layout.load_encoding_manifest

    def recording_load(path: Path):
        read.append(path)
        return load(path)

    with patch.object(layout, "load_encoding_manifest", recording_load):
        assert outcomes(root) == (False, False)
    assert manifest_tree(root) == ([receipt], ["aliased manifest path: uk/policies/linked"])
    assert set(read) == {receipt}


@pytest.mark.parametrize("inside", (True, False), ids=("inside-repo", "outside-repo"))
def test_metadata_symlink_is_refused_before_reading_structure(tmp_path, inside) -> None:
    root, outside = tmp_path / "repo", tmp_path / "outside"
    receipt = admission_repository(root)
    alias_component(root, outside, receipt, "metadata-root", inside=inside)

    with patch.object(layout, "ROOT", root), patch.object(
        Path, "read_text", side_effect=RuntimeError("read through symlinked .axiom")
    ) as read:
        with pytest.raises(AssertionError, match="aliased manifest ancestor: .axiom"):
            layout.test_encoding_manifests_use_only_the_canonical_root_mirror()
    read.assert_not_called()


def test_symlink_loop_is_refused_without_recursing(tmp_path) -> None:
    admission_repository(tmp_path)
    loop = tmp_path / ".axiom" / "encoding-manifests" / "uk" / "loop"
    loop.symlink_to("..", target_is_directory=True)

    _, problems = manifest_tree(tmp_path)
    assert problems == ["aliased manifest path: uk/loop"]
    assert outcomes(tmp_path) == (False, False)


def test_dangling_receipt_symlink_is_refused(tmp_path) -> None:
    receipt = admission_repository(tmp_path)
    receipt.unlink()
    receipt.symlink_to(tmp_path / "missing.json")

    assert manifest_tree(tmp_path) == ([], ["aliased manifest path: uk/policies/example.json"])
    assert outcomes(tmp_path) == (False, False)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs named pipes")
def test_special_file_receipt_is_refused(tmp_path) -> None:
    receipt = admission_repository(tmp_path)
    receipt.unlink()
    os.mkfifo(receipt)

    assert manifest_tree(tmp_path) == ([], ["not a regular file: uk/policies/example.json"])
    assert outcomes(tmp_path) == (False, False)


def test_manifest_root_that_is_a_file_is_refused(tmp_path) -> None:
    (tmp_path / ".axiom").mkdir()
    (tmp_path / ".axiom" / "repository-structure.yaml").write_text(
        yaml.safe_dump({"allowed_root_directories": list(JURISDICTIONS)})
    )
    (tmp_path / ".axiom" / "encoding-manifests").write_text("{}\n")

    assert manifest_tree(tmp_path) == (
        [], ["manifest root is not a directory: .axiom/encoding-manifests"]
    )
    assert outcomes(tmp_path) == (False, False)


# Property: in canonical layout, admission depends only on the payload's
# schema and on whether a symlink sits on the receipt's path, never on the
# receipt's name, nesting depth, jurisdiction or atomic root. Each generated
# placement is checked against every schema kind and every symlink status, and
# against a fixed reference placement with the same kind and status.
PROPERTY_SCHEMA_KINDS = (
    "v5", UNTRUSTED_SCHEMA_KINDS[0], "missing-schema", NON_JSON_KINDS[0], NON_OBJECT_KINDS[0],
)
PROPERTY_ALIASES = (None, *ALIAS_KINDS)
# The reference placement's outcome per status, computed once per run.
REFERENCE_OUTCOMES: dict[tuple, tuple[bool, bool]] = {}


def admission_outcome(
    container: Path,
    *,
    stem: str,
    nesting: tuple[str, ...],
    jurisdiction: str,
    source_root: str,
    kind: str,
    alias: str | None,
    inside: bool,
    level: int,
) -> tuple[bool, bool]:
    root, outside = container / "repo", container / "outside"
    receipt = admission_repository(
        root,
        jurisdiction=jurisdiction,
        source_root=source_root,
        nesting=nesting,
        stem=stem,
        kind=kind,
    )
    if alias is not None:
        alias_component(root, outside, receipt, alias, inside=inside, level=level)
    return outcomes(root)


def check_admission_property(
    tmp_path_factory,
    *,
    stem: str,
    nesting: tuple[str, ...],
    jurisdiction: str,
    source_root: str,
    inside: bool,
    level: int,
) -> None:
    placements = {
        "generated": {
            "stem": stem,
            "nesting": nesting,
            "jurisdiction": jurisdiction,
            "source_root": source_root,
        },
        "reference": {
            "stem": "example",
            "nesting": (),
            "jurisdiction": "uk",
            "source_root": "policies",
        },
    }
    for kind in PROPERTY_SCHEMA_KINDS:
        for alias in PROPERTY_ALIASES:
            status = {"kind": kind, "alias": alias, "inside": inside, "level": level}
            observed = {}
            for label, placement in placements.items():
                key = tuple(status.values())
                if label == "reference" and key in REFERENCE_OUTCOMES:
                    observed[label] = REFERENCE_OUTCOMES[key]
                    continue
                with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as container:
                    observed[label] = admission_outcome(
                        Path(container), **placement, **status
                    )
                if label == "reference":
                    REFERENCE_OUTCOMES[key] = observed[label]
            admitted = kind == "v5" and alias is None
            assert observed == {
                "generated": (admitted, admitted),
                "reference": (admitted, admitted),
            }, (kind, alias)


if given is not None:
    names = st.text(alphabet=NAME_ALPHABET, min_size=1, max_size=24)

    @settings(max_examples=16, deadline=None, derandomize=True, database=None)
    @given(
        stem=names,
        nesting=st.lists(names, max_size=3).map(tuple),
        jurisdiction=st.sampled_from(JURISDICTIONS),
        source_root=st.sampled_from(layout.ATOMIC_CONTENT_DIRS),
        inside=st.booleans(),
        level=st.integers(min_value=0, max_value=4),
    )
    def test_admission_depends_only_on_schema_and_symlinks(
        tmp_path_factory, stem, nesting, jurisdiction, source_root, inside, level
    ) -> None:
        check_admission_property(
            tmp_path_factory,
            stem=stem,
            nesting=nesting,
            jurisdiction=jurisdiction,
            source_root=source_root,
            inside=inside,
            level=level,
        )

else:
    PLACEMENTS = (
        ("x-1_y", ("a",), "uk-adur", "regulations", 2),
        ("0", ("deep", "er", "est"), "uk-babergh", "statutes", 4),
        ("council-tax-reduction", (), "uk", "legislation", 1),
    )

    @pytest.mark.parametrize("inside", (True, False), ids=("inside-repo", "outside-repo"))
    @pytest.mark.parametrize("placement", PLACEMENTS, ids=[p[0] for p in PLACEMENTS])
    def test_admission_depends_only_on_schema_and_symlinks(
        tmp_path_factory, placement, inside
    ) -> None:
        stem, nesting, jurisdiction, source_root, level = placement
        check_admission_property(
            tmp_path_factory,
            stem=stem,
            nesting=nesting,
            jurisdiction=jurisdiction,
            source_root=source_root,
            inside=inside,
            level=level,
        )
