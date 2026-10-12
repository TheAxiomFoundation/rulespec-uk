"""Workflow pins stay authoritative while the staged TOML mirrors them."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import tomllib

import pytest
import yaml

try:
    from hypothesis import given, settings, strategies as st
except ImportError:
    given = None


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ".github/workflows/repository-checks.yml"
TOOLCHAIN_PATH = ".axiom/workflow-toolchain.toml"
DEPENDENCY_KEYS = (
    "axiom_encode_ref",
    "axiom_rules_engine_ref",
    "axiom_corpus_ref",
    "rulespec_us_ref",
)
MIRROR_KEYS = (*DEPENDENCY_KEYS, "axiom_compose_ref", "axiom_encode_version", "shared_workflow_ref")


def _reader_result(
    tmp_path, *, key=None, toml_value=None, workflow_value=None, transform_toml=None,
    quote_numeric=True,
):
    workflow = (ROOT / WORKFLOW_PATH).read_text()
    toolchain = (ROOT / TOOLCHAIN_PATH).read_text()
    original_workflow = yaml.safe_load(workflow)
    reader = original_workflow["jobs"]["workflow-toolchain"]
    script = next(step["run"] for step in reader["steps"] if step.get("id") == "pins")
    if toml_value is not None:
        toolchain, count = re.subn(
            rf'^{key} = "[^"]*"$', f'{key} = "{toml_value}"', toolchain,
            flags=re.MULTILINE,
        )
        assert count == 1
    if workflow_value is not None:
        if key == "shared_workflow_ref":
            old = original_workflow["jobs"]["validate"]["uses"]
            new = f"{old.rsplit('@', 1)[0]}@{workflow_value}"
            workflow, count = re.subn(re.escape(old), lambda _: new, workflow)
        else:
            input_name = (
                key.upper() if key in {"axiom_compose_ref", "axiom_encode_version"}
                else key.replace("_", "-")
            )
            value = (
                f'"{workflow_value}"'
                if key == "axiom_encode_version" or (quote_numeric and workflow_value.isdigit())
                else workflow_value
            )
            workflow, count = re.subn(
                rf"^      {input_name}: .*$", f"      {input_name}: {value}",
                workflow, flags=re.MULTILINE,
            )
        assert count == 1
    if transform_toml is not None:
        toolchain = transform_toml(toolchain)
    for relative, contents in ((WORKFLOW_PATH, workflow), (TOOLCHAIN_PATH, toolchain)):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    return subprocess.run(
        ["bash", "-c", script], cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(tmp_path / "github-output"),
        },
        capture_output=True, text=True,
    )


def test_matching_workflow_toolchain_passes(tmp_path):
    result = _reader_result(tmp_path)
    assert result.returncode == 0, result.stderr


def _new_value(key, sha="a" * 40):
    return "1.2.3" if key == "axiom_encode_version" else sha


@pytest.mark.parametrize("key", MIRROR_KEYS)
def test_toml_only_pin_change_fails(tmp_path, key):
    result = _reader_result(tmp_path, key=key, toml_value=_new_value(key))
    assert result.returncode != 0, "TOML-only re-pin bypassed the consistency check"
    assert f"{key} must match literal workflow value" in result.stderr


@pytest.mark.parametrize("key", MIRROR_KEYS)
def test_workflow_only_pin_change_fails(tmp_path, key):
    result = _reader_result(tmp_path, key=key, workflow_value=_new_value(key))
    assert result.returncode != 0, "workflow-only re-pin bypassed the consistency check"
    assert f"{key} must match literal workflow value" in result.stderr


@pytest.mark.parametrize("key", MIRROR_KEYS)
def test_consistent_pin_changes_pass(tmp_path, key):
    result = _reader_result(
        tmp_path, key=key, toml_value=_new_value(key), workflow_value=_new_value(key),
    )
    assert result.returncode == 0, result.stderr


def test_validation_consumes_literal_refs():
    workflow = yaml.safe_load((ROOT / WORKFLOW_PATH).read_text())
    validate = workflow["jobs"]["validate"]
    assert "workflow-toolchain" in validate["needs"]
    assert "outputs" not in workflow["jobs"]["workflow-toolchain"]
    mirror = tomllib.loads((ROOT / TOOLCHAIN_PATH).read_text())["workflow_toolchain"]
    for key in DEPENDENCY_KEYS:
        value = validate["with"][key.replace("_", "-")]
        assert re.fullmatch(r"[0-9a-f]{40}", value)
        assert value == mirror[key]


@pytest.mark.parametrize("key", MIRROR_KEYS)
def test_missing_mirror_value_fails(tmp_path, key):
    result = _reader_result(
        tmp_path, transform_toml=lambda text: re.sub(rf"^{key} = .*\n", "", text, flags=re.MULTILINE),
    )
    assert result.returncode != 0
    assert "expected exactly" in result.stderr


def test_unchecked_mirror_value_fails(tmp_path):
    result = _reader_result(tmp_path, transform_toml=lambda text: text + 'extra_ref = "' + "a" * 40 + '"\n')
    assert result.returncode != 0
    assert "expected exactly" in result.stderr


@pytest.mark.parametrize("value", ["a" * 39, "a" * 41, "A" * 40, "main", "${{ inputs.ref }}"])
def test_non_sha_refs_fail_even_when_both_files_match(tmp_path, value):
    result = _reader_result(tmp_path, key="axiom_encode_ref", toml_value=value, workflow_value=value)
    assert result.returncode != 0
    assert "axiom_encode_ref must be a literal string" in result.stderr


@pytest.mark.parametrize("quoted", (False, True))
def test_numeric_only_sha_requires_yaml_string(tmp_path, quoted):
    result = _reader_result(
        tmp_path, key="axiom_encode_ref", toml_value="0" * 40,
        workflow_value="0" * 40, quote_numeric=quoted,
    )
    assert (result.returncode == 0) == quoted, result.stderr


def _check_generated_mirror(tmp_path_factory, key, sha, change):
    value = _new_value(key, sha)
    with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
        result = _reader_result(
            Path(directory), key=key,
            toml_value=value if change in {"toml", "both"} else None,
            workflow_value=value if change in {"workflow", "both"} else None,
        )
    original = tomllib.loads((ROOT / TOOLCHAIN_PATH).read_text())["workflow_toolchain"][key]
    assert (result.returncode == 0) == (change == "both" or value == original), result.stderr


if given is not None:
    @settings(max_examples=24, deadline=None, derandomize=True, database=None)
    @given(
        key=st.sampled_from(MIRROR_KEYS),
        sha=st.text(alphabet="0123456789abcdef", min_size=40, max_size=40),
        change=st.sampled_from(("toml", "workflow", "both")),
    )
    def test_generated_mirror_consistency(tmp_path_factory, key, sha, change):
        _check_generated_mirror(tmp_path_factory, key, sha, change)
else:
    @pytest.mark.parametrize("key", MIRROR_KEYS)
    @pytest.mark.parametrize("sha", ("0" * 40, "f" * 40))
    @pytest.mark.parametrize("change", ("toml", "workflow", "both"))
    def test_generated_mirror_consistency(tmp_path_factory, key, sha, change):
        _check_generated_mirror(tmp_path_factory, key, sha, change)


def test_workflow_toolchain_has_configured_owner():
    entries = {}
    for line in (ROOT / ".github/CODEOWNERS").read_text().splitlines():
        fields = line.split()
        if fields and not fields[0].startswith("#"):
            entries[fields[0]] = fields[1:]
    assert entries.get("/.axiom/workflow-toolchain.toml")
    assert entries["/.axiom/workflow-toolchain.toml"] == entries["/.axiom/toolchain.toml"]
