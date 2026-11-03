from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
# The only schema an encoding receipt may declare. It is the encoder's
# APPLIED_ENCODING_MANIFEST_SCHEMA at the pinned axiom-encode.
TRUSTED_APPLIED_MANIFEST_SCHEMA = "axiom-encode/applied-rulespec/v5"
# Country-monorepo layout: every RuleSpec filesystem root lives beneath one
# direct UK jurisdiction directory. Only the four atomic roots are indexed as
# rulespec/v1 modules; programs/ contains declarative composition specs.
COUNTRY = "uk"
JURISDICTION_DIR_RE = re.compile(r"^uk(?:-[a-z0-9]+)*$")
ATOMIC_CONTENT_DIRS = ("legislation", "policies", "regulations", "statutes")
PROGRAM_CONTENT_DIR = "programs"
FILESYSTEM_CONTENT_DIRS = (*ATOMIC_CONTENT_DIRS, PROGRAM_CONTENT_DIR)
IGNORED_DIRS = {".git", ".pytest_cache", ".venv", "__pycache__", "_axiom"}
DISALLOWED_GENERIC_RULE_NAMES = {
    "amount",
    "base",
    "excess",
    "excess_wages",
    "rate",
    "threshold",
    "value",
}


def jurisdiction_dirs() -> list[Path]:
    return sorted(
        child
        for child in ROOT.iterdir()
        if child.is_dir()
        and not child.is_symlink()
        and JURISDICTION_DIR_RE.match(child.name)
        and any((child / marker).is_dir() for marker in FILESYSTEM_CONTENT_DIRS)
    )


def rulespec_content_roots() -> list[Path]:
    return [
        jurisdiction / marker
        for jurisdiction in jurisdiction_dirs()
        for marker in ATOMIC_CONTENT_DIRS
        if (jurisdiction / marker).is_dir()
    ]


def allowed_yaml_roots() -> set[str]:
    return {
        ".axiom",
        ".github",
        "bulk",
        "known-dangling.yaml",
        "known-validation-gaps.yaml",
        "oracle-coverage-pending.yaml",
        "data",
        "validation_baselines",
        *(d.name for d in jurisdiction_dirs()),
    }


def _validation_gaps(section: str) -> set[str]:
    path = ROOT / "known-validation-gaps.yaml"
    if not path.exists():
        return set()
    payload = yaml.safe_load(path.read_text()) or {}
    return set(payload.get(section) or [])


def apply_gap_ratchet(section: str, found: list[str]) -> list[str]:
    """Filter `found` through the gap allowlist, failing both ways.

    Returns problems: gaps not allowlisted, plus allowlisted entries that
    no longer reproduce (remove them from known-validation-gaps.yaml).
    """
    allowlisted = _validation_gaps(section)
    found_set = set(found)
    problems = [item for item in found if item not in allowlisted]
    problems.extend(
        f"known-validation-gaps.yaml {section} entry is fixed — remove it: {stale}"
        for stale in sorted(allowlisted - found_set)
    )
    return problems


def iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def encoding_manifest_tree() -> tuple[list[Path], list[str]]:
    """Walk `.axiom/encoding-manifests/` without following any symlink.

    Returns the regular files beneath the manifest root, and one problem for
    each entry that is not a real directory or regular file: a symlinked
    `.axiom`, a symlinked manifest root, a symlinked directory at any depth
    beneath it, a symlinked receipt, or a special file. Every symlink is
    refused, including one that resolves inside the repository: this is a
    stricter rule than containment, and it is intended. A symlinked directory
    is reported and never entered, so the walk reads nothing outside the real
    tree. (`Path.rglob` would start from the target of a symlinked `.axiom` or
    manifest root, so this walk does not use it.)

    These guarantees hold for a stable tree. The walk reopens entries by name,
    so it does not defend against a concurrent writer that swaps an entry for
    a symlink while the walk runs.
    """
    metadata_root = ROOT / ".axiom"
    manifest_root = metadata_root / "encoding-manifests"
    if metadata_root.is_symlink():
        return [], ["aliased manifest ancestor: .axiom"]
    if manifest_root.is_symlink():
        return [], ["aliased manifest root: .axiom/encoding-manifests"]
    if not manifest_root.exists():
        return [], []
    if not manifest_root.is_dir():
        return [], ["manifest root is not a directory: .axiom/encoding-manifests"]

    files: list[Path] = []
    problems: list[str] = []
    pending = [manifest_root]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(manifest_root).as_posix()
                if entry.is_symlink():
                    problems.append(f"aliased manifest path: {relative}")
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    problems.append(f"not a regular file: {relative}")
    return sorted(files), sorted(problems)


def _refuse_json_constant(name: str) -> object:
    raise ValueError(f"non-standard JSON constant {name}")


def _finite_json_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"JSON number out of range: {text}")
    return value


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload = dict(pairs)
    if len(payload) != len(pairs):
        raise ValueError("duplicate JSON object key")
    return payload


def load_encoding_manifest(path: Path) -> tuple[object, str | None]:
    """Parse a receipt as UTF-8 JSON; return (payload, None) or (None, why).

    Beyond Python's decoder, every object must have unique keys (otherwise the
    last `schema_version` would silently win) and every number must be finite:
    the NaN, Infinity and -Infinity literals are refused, and so is a number
    such as 1e999 that overflows to infinity.
    """
    try:
        return (
            json.loads(
                path.read_bytes().decode("utf-8"),
                parse_constant=_refuse_json_constant,
                parse_float=_finite_json_float,
                object_pairs_hook=_unique_json_object,
            ),
            None,
        )
    except (ValueError, RecursionError) as exc:
        # UnicodeDecodeError and json.JSONDecodeError are both ValueErrors.
        return None, type(exc).__name__


def iter_rulespec_files() -> list[Path]:
    files: list[Path] = []
    for root in rulespec_content_roots():
        files.extend(
            path
            for path in root.rglob("*.yaml")
            if not path.name.endswith(".test.yaml")
        )
    return sorted(files)


def canonical_rule_id(path: Path, rule_name: str) -> str:
    relative = path.relative_to(ROOT)
    prefix = relative.parts[0]
    target = Path(*relative.parts[1:]).with_suffix("").as_posix()
    return f"{prefix}:{target}#{rule_name}"


def test_has_only_canonical_uk_jurisdiction_namespaces() -> None:
    """Every jurisdiction namespace is `uk` or a registered English billing
    authority (`uk-<slug>` per data/councils/registry.csv), and every
    registered namespace is admitted by .axiom/repository-structure.yaml —
    so a stray or typo'd directory still fails, but registered councils land
    without editing this test."""
    import csv

    with open(ROOT / "data" / "councils" / "registry.csv") as fh:
        registered = {f"uk-{row['slug']}" for row in csv.DictReader(fh)}
    assert registered, "council registry must not be empty"

    detected = [path.name for path in jurisdiction_dirs()]
    allowed = {"uk"} | registered
    strays = [name for name in detected if name not in allowed]
    assert strays == [], f"unregistered jurisdiction namespaces: {strays}"

    structure = (ROOT / ".axiom" / "repository-structure.yaml").read_text()
    admitted_dirs = {
        line.strip().removeprefix("- ")
        for line in structure.splitlines()
        if line.strip().startswith("- ")
    }
    unadmitted = sorted(registered - admitted_dirs)
    assert unadmitted == [], (
        "registered councils missing from repository-structure.yaml: "
        f"{unadmitted[:5]}{'…' if len(unadmitted) > 5 else ''}"
    )


def test_five_filesystem_roots_and_four_atomic_roots_are_distinct() -> None:
    assert set(ATOMIC_CONTENT_DIRS) == {
        "legislation",
        "policies",
        "regulations",
        "statutes",
    }
    assert set(FILESYSTEM_CONTENT_DIRS) == {
        *ATOMIC_CONTENT_DIRS,
        "programs",
    }
    assert all(
        path.relative_to(ROOT).parts[1] != PROGRAM_CONTENT_DIR
        for path in iter_rulespec_files()
    )


def test_no_obsolete_formula_artifacts() -> None:
    obsolete_ext = ".rac"
    obsolete = [
        path.relative_to(ROOT).as_posix()
        for path in iter_repo_files()
        if path.name.endswith(obsolete_ext)
        or path.name.endswith(f"{obsolete_ext}.test")
        or path.name in {"parameters.yaml", "tests.yaml"}
    ]

    assert obsolete == []


def test_no_disallowed_roots_or_yaml_fixtures() -> None:
    jurisdiction_roots = jurisdiction_dirs()
    disallowed_roots = [
        name
        for name in FILESYSTEM_CONTENT_DIRS
        if (ROOT / name).exists() or (ROOT / name).is_symlink()
    ]
    disallowed_roots.extend(
        (base / name).relative_to(ROOT).as_posix()
        for base in jurisdiction_roots
        for name in ("statute", "regulation", "policy", "program")
        if (base / name).exists() or (base / name).is_symlink()
    )
    disallowed_roots.extend(
        child.relative_to(ROOT).as_posix()
        for child in ROOT.iterdir()
        if child.is_dir()
        and (child.is_symlink() or not JURISDICTION_DIR_RE.fullmatch(child.name))
        and any(
            (child / marker).exists() or (child / marker).is_symlink()
            for marker in FILESYSTEM_CONTENT_DIRS
        )
    )
    yaml_fixtures = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests").rglob("*.yaml")
        if (ROOT / "tests").exists()
    ]
    allowed = allowed_yaml_roots()
    stray_yaml = [
        path.relative_to(ROOT).as_posix()
        for path in iter_repo_files()
        if path.suffix in {".yaml", ".yml"}
        and path.relative_to(ROOT).parts[0] not in allowed
    ]

    assert disallowed_roots == []
    assert yaml_fixtures == []
    assert stray_yaml == []


def test_canonical_content_uses_regular_exact_yaml_files_without_aliases() -> None:
    problems: list[str] = []
    for jurisdiction in jurisdiction_dirs():
        for marker in FILESYSTEM_CONTENT_DIRS:
            content_root = jurisdiction / marker
            if not content_root.exists() and not content_root.is_symlink():
                continue
            if content_root.is_symlink() or not content_root.is_dir():
                problems.append(
                    f"not a regular directory: {content_root.relative_to(ROOT)}"
                )
                continue
            for path in sorted(content_root.rglob("*")):
                relative = path.relative_to(ROOT).as_posix()
                if path.is_symlink():
                    problems.append(f"alias: {relative}")
                elif path.is_file() and path.suffix != ".yaml":
                    problems.append(f"not exact .yaml: {relative}")

    assert problems == []


def test_encoding_manifests_use_only_the_canonical_root_mirror() -> None:
    """Receipts sit only at the canonical mirror of the module they cover.

    A receipt is `.axiom/encoding-manifests/<jurisdiction>/<atomic-root>/...json`
    for a registered jurisdiction, mirrors the primary module it applies, and
    lists only applied files that exist as regular files or are recorded as
    deleted. No symlink may sit on the way to a receipt: `.axiom`,
    `.axiom/encoding-manifests`, every directory beneath it and the receipt
    file itself must be real, whatever the symlink resolves to (see
    `encoding_manifest_tree`).

    These repository tests check layout and schema only. Cryptographic
    verification is the encoder's job in CI through the shared validation
    workflow at the pinned encoder.
    """
    manifest_root = ROOT / ".axiom" / "encoding-manifests"
    manifests, problems = encoding_manifest_tree()
    # Reject aliases before even reading metadata through a symlinked .axiom.
    assert problems == [], problems
    structure = yaml.safe_load((ROOT / ".axiom" / "repository-structure.yaml").read_text())
    # Retirement can remove a jurisdiction's final content root. Its receipt
    # namespace remains canonical because the jurisdiction is still admitted.
    jurisdictions = {
        name for name in structure["allowed_root_directories"]
        if JURISDICTION_DIR_RE.fullmatch(name)
    }
    for jurisdiction in sorted(jurisdictions):
        nested = ROOT / jurisdiction / ".axiom" / "encoding-manifests"
        if nested.exists() or nested.is_symlink():
            problems.append(f"co-located manifest root: {nested.relative_to(ROOT)}")

    for manifest in manifests:
        relative = manifest.relative_to(manifest_root)
        if manifest.suffix != ".json":
            problems.append(f"not exact .json: {relative.as_posix()}")
            continue
        if len(relative.parts) < 3 or relative.parts[0] not in jurisdictions:
            problems.append(f"noncanonical manifest path: {relative.as_posix()}")
            continue
        jurisdiction, source_root = relative.parts[:2]
        if source_root not in ATOMIC_CONTENT_DIRS:
            problems.append(f"non-atomic manifest path: {relative.as_posix()}")
            continue
        payload, parse_error = load_encoding_manifest(manifest)
        if parse_error is not None:
            problems.append(f"manifest is not JSON: {relative.as_posix()}")
            continue
        if not isinstance(payload, dict):
            problems.append(f"manifest is not an object: {relative.as_posix()}")
            continue
        if payload.get("schema_version") != TRUSTED_APPLIED_MANIFEST_SCHEMA:
            problems.append(f"not a current v5 receipt: {relative.as_posix()}")
        applied_files = payload.get("applied_files")
        if not isinstance(applied_files, list) or not applied_files:
            problems.append(f"missing applied files: {relative.as_posix()}")
            continue
        mirrored_module = relative.with_suffix(".yaml").as_posix()
        applied_paths: set[str] = set()
        for applied in applied_files:
            applied_path = applied.get("path") if isinstance(applied, dict) else None
            if not isinstance(applied_path, str):
                problems.append(f"invalid applied path: {relative.as_posix()}")
                continue
            parts = Path(applied_path).parts
            if (
                Path(applied_path).is_absolute()
                or ".." in parts
                or not parts
            ):
                problems.append(
                    f"noncanonical applied path in {relative.as_posix()}: {applied_path}"
                )
                continue
            # Signed replacement receipts can also cover reconciled metadata.
            # The encoder guard verifies which metadata rewrites are permitted.
            if len(parts) >= 2 and parts[1] in ATOMIC_CONTENT_DIRS:
                if (
                    len(parts) < 3
                    or parts[0] not in jurisdictions
                    or Path(applied_path).suffix != ".yaml"
                ):
                    problems.append(f"noncanonical atomic applied path: {applied_path}")
                    continue
            applied_paths.add(applied_path)
            target = ROOT / applied_path
            if applied.get("deleted") is True:
                if target.exists() or target.is_symlink():
                    problems.append(f"retired file still exists: {applied_path}")
            elif not target.is_file() or target.is_symlink():
                problems.append(f"missing regular applied file: {applied_path}")
        if mirrored_module.endswith(".test.yaml") or mirrored_module not in applied_paths:
            problems.append(f"missing mirrored primary module: {relative.as_posix()}")

    assert problems == []


def test_applied_manifests_use_trusted_v5_schema() -> None:
    """Every receipt is a UTF-8 JSON object declaring the trusted v5 schema.

    Every file under `.axiom/encoding-manifests/` must parse as JSON, be an
    object, and set `schema_version` to `TRUSTED_APPLIED_MANIFEST_SCHEMA`.
    An entry this check cannot read as a regular file without following a
    symlink is refused too, so it fails closed.

    These repository tests check layout and schema only. Cryptographic
    verification is the encoder's job in CI through the shared validation
    workflow at the pinned encoder.
    """
    manifest_root = ROOT / ".axiom" / "encoding-manifests"
    manifests, problems = encoding_manifest_tree()
    for manifest in manifests:
        relative = manifest.relative_to(manifest_root).as_posix()
        payload, parse_error = load_encoding_manifest(manifest)
        if parse_error is not None:
            problems.append(f"not JSON ({parse_error}): {relative}")
        elif not isinstance(payload, dict):
            problems.append(f"not a JSON object: {relative}")
        elif payload.get("schema_version") != TRUSTED_APPLIED_MANIFEST_SCHEMA:
            problems.append(
                f"untrusted schema {payload.get('schema_version')!r}: {relative}"
            )

    assert problems == [], (
        f"encoding receipts must declare {TRUSTED_APPLIED_MANIFEST_SCHEMA}: {problems}"
    )


def test_rulespec_files_have_companion_tests() -> None:
    missing = [
        path.relative_to(ROOT).as_posix()
        for path in iter_rulespec_files()
        if not path.with_name(f"{path.stem}.test.yaml").exists()
    ]

    assert apply_gap_ratchet("missing_companion_tests", missing) == []


def test_companion_tests_have_rulespec_files() -> None:
    orphaned = []
    for root in rulespec_content_roots():
        orphaned.extend(
            path.relative_to(ROOT).as_posix()
            for path in sorted(root.rglob("*.test.yaml"))
            if not path.with_name(f"{path.stem.removesuffix('.test')}.yaml").exists()
        )

    assert orphaned == []


def test_rulespec_files_use_rulespec_v1_shape() -> None:
    invalid: list[str] = []

    for path in iter_rulespec_files():
        payload = yaml.safe_load(path.read_text()) or {}
        if not isinstance(payload, dict):
            invalid.append(f"{path.relative_to(ROOT)}: top-level YAML is not a mapping")
            continue
        if payload.get("format") != "rulespec/v1":
            invalid.append(f"{path.relative_to(ROOT)}: missing format: rulespec/v1")
        rules = payload.get("rules")
        if not isinstance(rules, list) or not rules:
            module = payload.get("module")
            status = module.get("status") if isinstance(module, dict) else None
            if rules == [] and status in {"deferred", "entity_not_supported"}:
                continue
            invalid.append(f"{path.relative_to(ROOT)}: missing non-empty rules list")
            continue
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                invalid.append(
                    f"{path.relative_to(ROOT)}: rules[{index}] is not a mapping"
                )
                continue
            for key in ("name", "kind"):
                if key not in rule:
                    invalid.append(
                        f"{path.relative_to(ROOT)}: rules[{index}] missing {key}"
                    )
            if rule.get("kind") in {"parameter", "derived"} and "versions" not in rule:
                invalid.append(
                    f"{path.relative_to(ROOT)}: rules[{index}] missing versions"
                )

    invalid_paths = sorted({item.split(":", 1)[0] for item in invalid})
    assert apply_gap_ratchet("shape_issues", invalid_paths) == []


def test_rulespec_rules_have_source_metadata() -> None:
    missing: list[str] = []

    for path in iter_rulespec_files():
        payload = yaml.safe_load(path.read_text()) or {}
        rules = payload.get("rules")
        if not isinstance(rules, list):
            continue
        module_source_locator = module_has_source_locator(payload)
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            name = rule.get("name", f"rules[{index}]")
            if rule.get("kind") in {"data_relation", "source_relation"}:
                continue
            if not rule.get("source"):
                missing.append(f"{path.relative_to(ROOT)}: {name} missing source")
            if not module_source_locator:
                missing.append(
                    f"{path.relative_to(ROOT)}: {name} missing source locator"
                )

    assert missing == []


def test_rulespec_files_use_corpus_source_locators() -> None:
    legacy: list[str] = []

    for path in iter_rulespec_files():
        payload = yaml.safe_load(path.read_text()) or {}
        if isinstance(payload, dict):
            module = payload.get("module")
            if isinstance(module, dict):
                if module.get("source_url"):
                    legacy.append(f"{path.relative_to(ROOT)}: module.source_url")
                source_verification = module.get("source_verification")
                if isinstance(source_verification, dict) and source_verification.get(
                    "source_url"
                ):
                    legacy.append(
                        f"{path.relative_to(ROOT)}: "
                        "module.source_verification.source_url"
                    )
            rules = payload.get("rules")
            if isinstance(rules, list):
                for index, rule in enumerate(rules):
                    if not isinstance(rule, dict) or not rule.get("source_url"):
                        continue
                    name = rule.get("name", f"rules[{index}]")
                    legacy.append(f"{path.relative_to(ROOT)}: {name}.source_url")

    assert legacy == []


def test_source_verification_uses_the_exact_singular_contract() -> None:
    problems: list[str] = []
    allowed_keys = {"corpus_citation_path", "source_sha256"}

    for path in iter_rulespec_files():
        payload = yaml.safe_load(path.read_text()) or {}
        module = payload.get("module") if isinstance(payload, dict) else None
        source_verification = (
            module.get("source_verification") if isinstance(module, dict) else None
        )
        relative = path.relative_to(ROOT).as_posix()
        if not isinstance(source_verification, dict):
            problems.append(f"{relative}: source_verification must be a mapping")
            continue
        unknown = sorted(set(source_verification) - allowed_keys)
        if unknown:
            problems.append(
                f"{relative}: retired or unknown source_verification keys: "
                + ", ".join(unknown)
            )
        citation = source_verification.get("corpus_citation_path")
        if not isinstance(citation, str) or not citation.strip():
            problems.append(
                f"{relative}: corpus_citation_path must be one non-empty string"
            )
        source_sha256 = source_verification.get("source_sha256")
        if source_sha256 is not None and (
            not isinstance(source_sha256, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", source_sha256) is None
        ):
            problems.append(f"{relative}: source_sha256 must be 64 hex characters")

    assert problems == []


def module_has_source_locator(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    module = payload.get("module")
    if not isinstance(module, dict):
        return False
    source_verification = module.get("source_verification")
    if not isinstance(source_verification, dict):
        return False
    citation_path = source_verification.get("corpus_citation_path")
    return isinstance(citation_path, str) and bool(citation_path.strip())


def test_rulespec_rule_names_are_specific() -> None:
    vague: list[str] = []

    for path in iter_rulespec_files():
        payload = yaml.safe_load(path.read_text()) or {}
        rules = payload.get("rules")
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            name = rule.get("name")
            if name in DISALLOWED_GENERIC_RULE_NAMES:
                vague.append(f"{path.relative_to(ROOT)}: {name}")

    assert vague == []


def test_derived_rules_are_exercised_by_companion_tests() -> None:
    missing: list[str] = []

    for path in iter_rulespec_files():
        payload = yaml.safe_load(path.read_text()) or {}
        rules = payload.get("rules")
        if not isinstance(rules, list):
            continue
        derived_rule_names = [
            str(rule["name"])
            for rule in rules
            if isinstance(rule, dict)
            and rule.get("kind") == "derived"
            and isinstance(rule.get("name"), str)
        ]

        test_path = path.with_name(f"{path.stem}.test.yaml")
        if not test_path.exists():
            continue
        cases = yaml.safe_load(test_path.read_text()) or []
        covered_outputs: set[str] = set()
        if isinstance(cases, list):
            for case in cases:
                if not isinstance(case, dict):
                    continue
                outputs = case.get("output")
                if isinstance(outputs, dict):
                    covered_outputs.update(str(name) for name in outputs)

        missing.extend(
            f"{path.relative_to(ROOT).as_posix()}#{rule_name}"
            for rule_name in derived_rule_names
            if canonical_rule_id(path, rule_name) not in covered_outputs
        )

    assert apply_gap_ratchet("uncovered_derived_rules", missing) == []
