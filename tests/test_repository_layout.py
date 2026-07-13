from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
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
    assert [path.name for path in jurisdiction_dirs()] == [
        "uk",
        "uk-kingston-upon-thames",
    ]


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
    manifest_root = ROOT / ".axiom" / "encoding-manifests"
    jurisdictions = {path.name for path in jurisdiction_dirs()}
    problems: list[str] = []

    for jurisdiction in jurisdiction_dirs():
        nested = jurisdiction / ".axiom" / "encoding-manifests"
        if nested.exists() or nested.is_symlink():
            problems.append(f"co-located manifest root: {nested.relative_to(ROOT)}")

    for manifest in sorted(manifest_root.rglob("*.json")):
        relative = manifest.relative_to(manifest_root)
        if len(relative.parts) < 3 or relative.parts[0] not in jurisdictions:
            problems.append(f"noncanonical manifest path: {relative.as_posix()}")
            continue
        jurisdiction, source_root = relative.parts[:2]
        if source_root not in ATOMIC_CONTENT_DIRS:
            problems.append(f"non-atomic manifest path: {relative.as_posix()}")
        payload = json.loads(manifest.read_text())
        for applied in payload.get("applied_files", []):
            applied_path = applied.get("path") if isinstance(applied, dict) else None
            if not isinstance(applied_path, str):
                problems.append(f"invalid applied path: {relative.as_posix()}")
                continue
            parts = Path(applied_path).parts
            if (
                len(parts) < 3
                or parts[0] != jurisdiction
                or parts[1] not in ATOMIC_CONTENT_DIRS
                or Path(applied_path).suffix != ".yaml"
                or not (ROOT / applied_path).is_file()
            ):
                problems.append(
                    f"noncanonical applied path in {relative.as_posix()}: {applied_path}"
                )

    assert problems == []


def test_legacy_applied_manifests_are_not_kept_as_migration_inputs() -> None:
    manifest_root = ROOT / ".axiom" / "encoding-manifests"
    manifests = sorted(
        path.relative_to(ROOT).as_posix() for path in manifest_root.rglob("*.json")
    )

    assert manifests == [], (
        "prelaunch hard cut requires deleting every legacy applied manifest; "
        "trusted v5 manifests must be regenerated from the named release, not "
        f"carried forward as compatibility inputs: {manifests}"
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
