"""Program specs under <jurisdiction>/programs/ must be declarative and every
scope entry must resolve to a module in this repository.

Jurisdiction content and its ProgramSpecs share one direct jurisdiction root,
so the audit needs no external checkouts. Known gaps are ratcheted through
known-dangling.yaml — a
dangling entry not listed there fails, and a listed entry that starts
resolving also fails (remove it once fixed; see axiom-programs#14).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_SPEC_KEYS = {
    "acknowledged_incomplete",
    "auto_gate_outputs",
    "outputs",
    "period",
    "program",
    "rounding",
    "scope",
    "transformations",
}


def program_roots() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("uk*/programs")
        if path.is_dir() and path.parent.parent == ROOT
    )


def scope_prefix(program: str, scope_name: str) -> str:
    normalized = scope_name.strip()
    if normalized == "federal":
        return "us"
    if normalized == "state":
        return program.split("/", 1)[0]
    return normalized


def spec_paths() -> list[Path]:
    return sorted(path for root in program_roots() for path in root.rglob("*.yaml"))


def load_allowlist() -> set[tuple[str, str, str]]:
    path = ROOT / "known-dangling.yaml"
    if not path.exists():
        return set()
    payload = yaml.safe_load(path.read_text()) or {}
    return {
        (entry["spec"], entry["scope"], entry["path"])
        for entry in payload.get("entries", [])
    }


def test_program_specs_exist() -> None:
    assert spec_paths(), "<jurisdiction>/programs/ contains no specs"


def test_program_roots_contain_only_regular_exact_yaml_files() -> None:
    problems: list[str] = []
    for root in program_roots():
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(ROOT).as_posix()
            if path.is_symlink():
                problems.append(f"{relative}: aliases are not allowed")
            elif path.is_file() and path.suffix != ".yaml":
                problems.append(f"{relative}: ProgramSpecs must use exact .yaml")
            elif path.is_file() and path.name.endswith(".test.yaml"):
                problems.append(
                    f"{relative}: ProgramSpecs do not have RuleSpec companions"
                )
    assert problems == []


def test_program_specs_are_structurally_valid() -> None:
    problems: list[str] = []
    for spec_path in spec_paths():
        rel = spec_path.relative_to(ROOT).as_posix()
        raw = yaml.safe_load(spec_path.read_text()) or {}
        if not isinstance(raw, dict):
            problems.append(f"{rel}: spec root must be a mapping")
            continue
        unknown = sorted(set(raw) - PROGRAM_SPEC_KEYS)
        if unknown:
            problems.append(f"{rel}: unsupported keys: {', '.join(unknown)}")
        if not isinstance(raw.get("program"), str) or not raw.get("program"):
            problems.append(f"{rel}: missing or non-string `program`")
        else:
            program_root = next(
                root for root in program_roots() if spec_path.is_relative_to(root)
            )
            program_path = spec_path.relative_to(program_root).parent.as_posix()
            expected_program = f"{program_root.parent.name}/{program_path}"
            if raw["program"] != expected_program:
                problems.append(
                    f"{rel}: program must match canonical path {expected_program!r}"
                )
        if not isinstance(raw.get("period"), str) or not raw.get("period"):
            problems.append(f"{rel}: missing or non-string `period`")
        outputs = raw.get("outputs")
        if (
            not isinstance(outputs, list)
            or not outputs
            or not all(isinstance(item, str) for item in outputs)
        ):
            problems.append(f"{rel}: `outputs` must be a non-empty list of strings")
        scope = raw.get("scope")
        if scope is not None and not isinstance(scope, dict):
            problems.append(f"{rel}: `scope` must be a mapping")
        elif isinstance(scope, dict):
            for key, values in scope.items():
                if (
                    not isinstance(key, str)
                    or not isinstance(values, list)
                    or not all(isinstance(value, str) for value in values)
                ):
                    problems.append(
                        f"{rel}: scope entries must map strings to string lists"
                    )
        transformations = raw.get("transformations", [])
        if not isinstance(transformations, list) or not all(
            isinstance(item, dict)
            and isinstance(item.get("pattern"), str)
            and bool(item["pattern"])
            for item in transformations
        ):
            problems.append(
                f"{rel}: `transformations` must be declarative pattern mappings"
            )
    assert problems == []


def test_scope_entries_resolve_or_are_allowlisted() -> None:
    allowlist = load_allowlist()
    seen: set[tuple[str, str, str]] = set()
    problems: list[str] = []

    for spec_path in spec_paths():
        rel = spec_path.relative_to(ROOT).as_posix()
        raw = yaml.safe_load(spec_path.read_text()) or {}
        if not isinstance(raw, dict) or not isinstance(raw.get("program"), str):
            continue
        for scope_name, paths in (raw.get("scope") or {}).items():
            prefix = scope_prefix(raw["program"], scope_name)
            jurisdiction = ROOT / prefix
            if not jurisdiction.is_dir():
                problems.append(f"{rel}: no jurisdiction directory {prefix}/")
                continue
            for path in paths or []:
                key = (rel, scope_name, path)
                resolves = (jurisdiction / f"{path}.yaml").exists()
                if not resolves and key not in allowlist:
                    problems.append(
                        f"{rel}: {scope_name}: {path} does not resolve in {prefix}/"
                    )
                if resolves and key in allowlist:
                    problems.append(
                        f"{rel}: {scope_name}: {path} now resolves — remove it "
                        "from known-dangling.yaml"
                    )
                if key in allowlist:
                    seen.add(key)

    problems.extend(
        f"known-dangling.yaml entry matches no spec scope entry (stale): {stale}"
        for stale in sorted(allowlist - seen)
    )
    assert problems == []
