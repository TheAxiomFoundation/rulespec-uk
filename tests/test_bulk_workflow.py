"""The bulk workflow plans work without access to signing credentials."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import tomllib

import pytest
import yaml

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
except ImportError:
    given = None


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/bulk-encode.yml"
SHA_LITERAL = re.compile(r"\b[0-9a-fA-F]{40}\b")
THIRD_PARTY_USES = re.compile(
    r"\s*(?:-\s+)?uses:(?!\s*[\"']?TheAxiomFoundation/)", re.IGNORECASE
)
KINGSTON = (
    "uk-kingston-upon-thames/policies/kingston-upon-thames/council-tax-reduction.yaml"
)


def _workflow():
    # BaseLoader preserves the Actions `on` key instead of treating it as a
    # YAML 1.1 boolean. Workflow scalar values are consumed as strings here.
    return yaml.load(WORKFLOW_PATH.read_text(), Loader=yaml.BaseLoader)


def test_bulk_workflow_is_a_dispatch_only_keyless_planner():
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert set(workflow["on"]["workflow_dispatch"]["inputs"]) == {
        "batch", "limit", "verify_release",
    }
    assert set(workflow["jobs"]) == {"plan", "verify-release"}
    assert workflow["permissions"] == {"contents": "read"}
    text = WORKFLOW_PATH.read_text()
    assert "run_encode" not in text
    assert "AXIOM_ENCODE_APPLY_SIGNER_ED25519_PRIVATE_KEY" not in text
    assert re.search(r"\bsecrets\s*\.", text) is None


def _outputs(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines())


@pytest.mark.parametrize("batch, expected_count", [("fixture", 2), ("missing", 0)])
def test_plan_steps_produce_artifact_without_secrets(tmp_path, batch, expected_count):
    workflow = _workflow()
    plan_job = workflow["jobs"]["plan"]
    steps = {step["id"]: step for step in plan_job["steps"] if "id" in step}
    for relative in (
        ".axiom/toolchain.toml", ".axiom/workflow-toolchain.toml",
        "bulk/compute_matrix.py", "bulk/roots_for.py",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    worklist = {
        "defaults": {"backend": "codex", "model": "fixture-model"},
        "entries": [
            {"citation": "uk/statute/done", "batch": "fixture", "status": "done"},
            {
                "citation": "uk/regulation/uksi/2012/2885/11",
                "batch": "fixture", "status": "pending",
            },
            {"target": KINGSTON, "batch": "fixture", "status": "pending"},
            {"citation": "uk/statute/limited", "batch": "fixture", "status": "pending"},
            {"citation": "uk/statute/other", "batch": "other", "status": "pending"},
        ],
    }
    (tmp_path / "bulk/worklist.yaml").write_text(yaml.safe_dump(worklist))

    # Deliberately build an allowlisted environment; no host environment or
    # credentials are inherited by either workflow script.
    environment = {
        "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
        "GITHUB_ENV": str(tmp_path / "pins-env"),
        "GITHUB_OUTPUT": str(tmp_path / "toolchain-output"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        **workflow["env"],
    }
    result = subprocess.run(
        ["/bin/bash", "-c", steps["pins"]["run"]], cwd=tmp_path,
        env=environment, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    pins = _outputs(tmp_path / "pins-env")
    environment.update(pins)
    result = subprocess.run(
        ["/bin/bash", "-c", steps["toolchain"]["run"]], cwd=tmp_path,
        env=environment, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    toolchain = _outputs(tmp_path / "toolchain-output")
    assert toolchain == tomllib.loads(
        (tmp_path / ".axiom/toolchain.toml").read_text()
    )["toolchain"]

    expressions = {
        "${{ inputs.batch }}": batch,
        "${{ inputs.limit || '8' }}": "2",
        **{
            f"${{{{ steps.toolchain.outputs.{key} }}}}": value
            for key, value in toolchain.items()
        },
    }
    environment.update({
        key: expressions[value] for key, value in steps["plan"]["env"].items()
    })
    environment["GITHUB_OUTPUT"] = str(tmp_path / "plan-output")
    result = subprocess.run(
        ["/bin/bash", "-c", steps["plan"]["run"]], cwd=tmp_path,
        env=environment, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    outputs = _outputs(tmp_path / "plan-output")
    matrix = json.loads(outputs["matrix"])["include"]
    assert outputs["count"] == str(expected_count)
    assert len(matrix) == expected_count
    assert plan_job["outputs"] == {
        "matrix": "${{ steps.plan.outputs.matrix }}",
        "count": "${{ steps.plan.outputs.count }}",
    }

    artifact = json.loads((tmp_path / "bulk-plan.json").read_text())
    assert artifact["batch"] == batch
    assert artifact["limit"] == 2
    assert artifact["count"] == expected_count
    assert artifact["toolchain"] == toolchain
    assert artifact["pins"] == {
        "axiom_encode_ref": pins["AXIOM_ENCODE_REF"],
        "axiom_rules_engine_ref": pins["AXIOM_RULES_ENGINE_REF"],
        "axiom_corpus_ref": pins["AXIOM_CORPUS_REF"],
        "rulespec_us_ref": pins["RULESPEC_US_REF"],
        "corpus_release_base_url": workflow["env"]["CORPUS_RELEASE_BASE_URL"],
    }
    assert artifact["corpus_path"] == "_axiom/axiom-corpus"
    assert artifact["selection"] == [
        {**item, "roots": roots}
        for item, roots in zip(matrix, ("uk", "uk uk-kingston-upon-thames"))
    ]
    upload = next(
        step for step in plan_job["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["with"]["name"] == "bulk-plan"
    assert upload["with"]["path"] == "bulk-plan.json"
    assert "Bulk encode plan" in (tmp_path / "summary").read_text()

    if expected_count:
        assert [item["citation"] or item["target"] for item in matrix] == [
            "uk/regulation/uksi/2012/2885/11", KINGSTON,
        ]
        assert all(item["backend"] == "codex" for item in matrix)
        assert all(item["model"] == "fixture-model" for item in matrix)
        assert "::warning::" not in result.stderr
    else:
        assert "::warning::No pending worklist entries match" in result.stderr


REF_INPUTS = {
    "AXIOM_ENCODE_REF": ("axiom_encode_ref", "axiom-encode-ref"),
    "AXIOM_RULES_ENGINE_REF": ("axiom_rules_engine_ref", "axiom-rules-engine-ref"),
    "AXIOM_CORPUS_REF": ("axiom_corpus_ref", "axiom-corpus-ref"),
    "RULESPEC_US_REF": ("rulespec_us_ref", "rulespec-us-ref"),
}


def _toolchain_text(**values):
    table = {key: f'"{"c" * 40}"' for key, _ in REF_INPUTS.values()}
    table.update(values)
    return "[workflow_toolchain]\n" + "".join(
        f"{key} = {value}\n" for key, value in table.items() if value is not None
    )


def _run_pins_step(tmp_path, toolchain_text):
    destination = tmp_path / ".axiom/workflow-toolchain.toml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(toolchain_text)
    step = next(
        step for step in _workflow()["jobs"]["plan"]["steps"] if step.get("id") == "pins"
    )
    env_file = tmp_path / "pins-env"
    env_file.touch()
    result = subprocess.run(
        ["/bin/bash", "-c", step["run"]], cwd=tmp_path,
        env={
            "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
            "GITHUB_ENV": str(env_file),
        },
        capture_output=True, text=True, timeout=60, check=False,
    )
    return result, env_file


def test_bulk_workflow_pins_match_the_validate_job(tmp_path):
    """bulk-encode.yml resolves the refs repository-checks.yml passes to the validate job."""
    checks = yaml.load(
        (ROOT / ".github/workflows/repository-checks.yml").read_text(), Loader=yaml.BaseLoader
    )
    validate = checks["jobs"]["validate"]["with"]
    assert {k for k in validate if k.endswith("-ref")} == {
        input_key for _, input_key in REF_INPUTS.values()
    }
    result, env_file = _run_pins_step(
        tmp_path, (ROOT / ".axiom/workflow-toolchain.toml").read_text()
    )
    assert result.returncode == 0, result.stderr
    assert _outputs(env_file) == {
        env_key: validate[input_key] for env_key, (_, input_key) in REF_INPUTS.items()
    }


def _dependency_sha_literals(text):
    """Lines that hard-code a commit SHA, other than third-party actions pinned by SHA."""
    # A SHA-pinned TheAxiomFoundation action pins a dependency in this file,
    # where a three-file re-pin can't move it.
    return [
        line for line in text.splitlines()
        if SHA_LITERAL.search(line) and THIRD_PARTY_USES.match(line) is None
    ]


def test_bulk_workflow_loads_its_pins_before_any_step_uses_them():
    """A re-pin edits only the configuration files, never bulk-encode.yml."""
    workflow = _workflow()
    assert not [key for key in workflow["env"] if key.endswith("_REF")]
    assert _dependency_sha_literals(WORKFLOW_PATH.read_text()) == []
    plan_steps = workflow["jobs"]["plan"]["steps"]
    pins_step = next(step for step in plan_steps if step.get("id") == "pins")
    for steps in (plan_steps, workflow["jobs"]["verify-release"]["steps"]):
        ids = [step.get("id") for step in steps]
        assert ids.count("pins") == 1
        loaded = ids.index("pins")
        assert steps[loaded] == pins_step
        assert all("_REF" not in json.dumps(step) for step in steps[:loaded])


@pytest.mark.parametrize(
    "line, flagged",
    [
        (f"  AXIOM_CORPUS_REF: {'a' * 40}", True),
        (f"          ref: {'A' * 40}", True),
        (f"      - uses: TheAxiomFoundation/axiom-corpus/.github/actions/fetch@{'a' * 40}", True),
        (f"        uses: theaxiomfoundation/axiom-encode/.github/actions/setup@{'a' * 40}", True),
        (f"        uses: \"TheAxiomFoundation/axiom-encode/setup@{'a' * 40}\"", True),
        (f"      - uses: actions/checkout@{'a' * 40}", False),
        (f"        uses: actions/setup-python@{'a' * 40}", False),
        (f"      -   uses: 'actions/checkout@{'a' * 40}'", False),
        ("      - uses: actions/checkout@v6.0.2", False),
    ],
    ids=[
        "env", "uppercase-ref", "axiom-action", "axiom-action-lowercase",
        "axiom-action-quoted", "third-party-step", "third-party-key",
        "third-party-quoted", "tag",
    ],
)
def test_literal_check_flags_dependency_pins_but_not_third_party_actions(line, flagged):
    assert (_dependency_sha_literals(line) != []) is flagged


SAMPLE_SHA = "0123456789abcdef" * 2 + "01234567"
REF_KEYS = tuple(key for key, _ in REF_INPUTS.values())


def _corruptions(sha, at):
    """TOML values for one ref that are not a full lowercase commit SHA string."""
    digits = "".join(str(int(char, 16) % 10) for char in sha)
    return {
        "branch": '"main"',
        "uppercase": f'"{sha[:at]}{"ABCDEF"[at % 6]}{sha[at + 1:]}"',
        "non-hex": f'"{sha[:at]}{"gz-./_"[at % 6]}{sha[at + 1:]}"',
        "short": f'"{sha[:at]}"',
        "long": f'"{sha}{sha[:at + 1]}"',
        "leading-space": f'" {sha}"',
        "trailing-space": f'"{sha} "',
        "trailing-newline": f'"{sha}\\n"',
        "injected-line": f'"{sha}\\nAXIOM_CORPUS_REF={sha[::-1]}"',
        "integer": "1" + digits[1:],
        "array": f'["{sha}"]',
        "boolean": "true",
        "table": f'{{ sha = "{sha}" }}',
        "missing": None,
    }


CORRUPTIONS = tuple(_corruptions(SAMPLE_SHA, 0))


def _check_rejected(directory, toolchain_text, message):
    result, env_file = _run_pins_step(directory, toolchain_text)
    assert result.returncode != 0
    assert message in result.stderr
    assert env_file.read_text() == ""


@pytest.mark.parametrize("corruption", CORRUPTIONS)
@pytest.mark.parametrize("key", REF_KEYS)
def test_pins_step_rejects_a_ref_that_is_not_a_full_commit(tmp_path, key, corruption):
    _check_rejected(
        tmp_path,
        _toolchain_text(**{key: _corruptions(SAMPLE_SHA, 7)[corruption]}),
        f"{key} must be a full lowercase commit SHA",
    )


@pytest.mark.parametrize(
    "toolchain_text",
    [
        _toolchain_text().replace("[workflow_toolchain]", "[toolchain]"),
        _toolchain_text() + "[other]\nkey = 1\n",
        "workflow_toolchain = 1\n",
    ],
    ids=["wrong-table", "extra-table", "not-a-table"],
)
def test_pins_step_rejects_any_table_but_workflow_toolchain(tmp_path, toolchain_text):
    _check_rejected(tmp_path, toolchain_text, "expected only the workflow_toolchain table")


def _check_generated_pins(tmp_path_factory, shas):
    values = dict(zip((key for key, _ in REF_INPUTS.values()), shas))
    with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
        result, env_file = _run_pins_step(
            Path(directory),
            _toolchain_text(**{key: f'"{sha}"' for key, sha in values.items()}),
        )
        assert result.returncode == 0, result.stderr
        assert _outputs(env_file) == {
            env_key: values[key] for env_key, (key, _) in REF_INPUTS.items()
        }


if given is not None:
    @settings(max_examples=24, deadline=None, derandomize=True, database=None)
    @given(
        shas=st.lists(
            st.text(alphabet="0123456789abcdef", min_size=40, max_size=40),
            min_size=len(REF_INPUTS), max_size=len(REF_INPUTS),
        ),
    )
    def test_pins_step_sets_each_ref_under_its_own_name(tmp_path_factory, shas):
        _check_generated_pins(tmp_path_factory, shas)
else:
    @pytest.mark.parametrize(
        "shas", (("0" * 40, "1" * 40, "e" * 40, "f" * 40), ("9" * 40,) * len(REF_INPUTS)),
    )
    def test_pins_step_sets_each_ref_under_its_own_name(tmp_path_factory, shas):
        _check_generated_pins(tmp_path_factory, shas)


# Without Hypothesis, test_pins_step_rejects_a_ref_that_is_not_a_full_commit
# covers every ref and corruption at one position.
if given is not None:
    @settings(max_examples=48, deadline=None, derandomize=True, database=None)
    @given(
        key=st.sampled_from(REF_KEYS),
        sha=st.text(alphabet="0123456789abcdef", min_size=40, max_size=40),
        at=st.integers(min_value=0, max_value=39),
        corruption=st.sampled_from(CORRUPTIONS),
    )
    def test_pins_step_rejects_any_corrupted_ref(tmp_path_factory, key, sha, at, corruption):
        with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
            _check_rejected(
                Path(directory),
                _toolchain_text(**{key: _corruptions(sha, at)[corruption]}),
                f"{key} must be a full lowercase commit SHA",
            )
