"""Ratchet check for the oracle-coverage pending lane.

``oracle-coverage-pending.yaml`` records executable outputs awaiting oracle
classification. It is an accountable worklist, not a merge bypass. These tests
enforce both the ledger ratchet and the production fail-on-pending gate:

  * every unmapped output in this repo is declared (nothing silent), and
  * every declaration is still unmapped — an output classified upstream in
    axiom-oracles must be removed here, so the debt only ratchets down.

They delegate to the toolchain-pinned ``axiom-encode`` against this exact
canonical country checkout. No workspace, sibling, or repository-name fallback
is supported.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_oracle_coverage_pending_ratchet() -> None:
    axiom_encode = shutil.which("axiom-encode")
    if axiom_encode is None:
        pytest.skip("axiom-encode is not installed; ratchet runs in the validate job")

    result = subprocess.run(
        [
            axiom_encode,
            "oracle-coverage-pending",
            "check",
            "--root",
            str(REPO_ROOT),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    problems = payload.get("problems") or [result.stderr.strip() or "<no output>"]

    assert result.returncode == 0, (
        "oracle-coverage-pending ratchet failed. Declare new unmapped outputs in "
        "oracle-coverage-pending.yaml, and remove declarations whose output is "
        "now classified upstream:\n- " + "\n- ".join(problems)
    )


def test_oracle_coverage_has_no_pending_or_unmapped_outputs() -> None:
    axiom_encode = shutil.which("axiom-encode")
    if axiom_encode is None:
        pytest.skip("axiom-encode is not installed; release gate runs in CI")

    # Always-run CI enforces the RATCHET: unmapped and stale-pending outputs
    # fail; debt declared in oracle-coverage-pending.yaml (the visible
    # remediation worklist, issue #101) is tolerated. The strict release
    # gate additionally fails on declared pending — run it by setting
    # AXIOM_RELEASE_GATE=1. This matches the shared validate workflow's own
    # oracle-coverage enforcement (--fail-on-unmapped, not
    # --fail-on-pending); the old pinned CI never executed this test at all
    # (no axiom-encode on PATH), so the strict mode had never actually
    # gated merges.
    flags = ["--fail-on-unmapped", "--fail-on-stale-pending"]
    if os.environ.get("AXIOM_RELEASE_GATE"):
        flags.append("--fail-on-pending")

    result = subprocess.run(
        [
            axiom_encode,
            "oracle-coverage",
            "--root",
            str(REPO_ROOT),
            *flags,
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    pending = (payload.get("pending") or {}).get("applied") or []
    status_counts = payload.get("status_counts") or {}
    detail = [
        f"status counts: {status_counts}",
        *(str(item) for item in pending[:20]),
    ]
    if len(pending) > 20:
        detail.append(f"... {len(pending) - 20} more pending outputs")
    if not pending and result.stderr.strip():
        detail.append(result.stderr.strip())

    assert result.returncode == 0, (
        "oracle coverage gate failed; unmapped or stale-pending outputs are "
        "blocking debt (declared pending blocks only under "
        "AXIOM_RELEASE_GATE=1):\n- " + "\n- ".join(detail)
    )
