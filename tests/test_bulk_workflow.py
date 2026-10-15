"""The bulk workflow plans work without access to signing credentials."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/bulk-encode.yml"
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
        ".axiom/toolchain.toml", "bulk/compute_matrix.py", "bulk/roots_for.py",
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
        "GITHUB_OUTPUT": str(tmp_path / "toolchain-output"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        **workflow["env"],
    }
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
        "axiom_encode_ref": workflow["env"]["AXIOM_ENCODE_REF"],
        "axiom_rules_engine_ref": workflow["env"]["AXIOM_RULES_ENGINE_REF"],
        "axiom_corpus_ref": workflow["env"]["AXIOM_CORPUS_REF"],
        "rulespec_us_ref": workflow["env"]["RULESPEC_US_REF"],
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
