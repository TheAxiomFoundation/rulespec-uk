"""Execute the retained daily-maximum/weekly-excess taper in the actual engine.

Set AXIOM_ENGINE to the CI-pinned binary to select an engine explicitly. Tests
compile temporary copies because the engine requires a real canonical
rulespec-uk directory. Test-only derived mirrors make scalar/indexed parameters
observable through the engine's derived-output execution API.

Hypothesis supplies generated cases when installed. The same assertions run
against a deterministic sweep in the repository's minimal pytest/PyYAML CI
environment; absence of Hypothesis does not suppress any invariant.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
import yaml

try:
    from hypothesis import given, settings, strategies as st
except ImportError:
    given = None


ROOT = Path(__file__).resolve().parents[1]
COUNCILS = ("oldham", "east-hertfordshire")
PERIODS = {
    "tax_year": {
        "period_kind": "tax_year", "start": "2026-04-01", "end": "2027-03-31"
    },
    "benefit_week": {
        "period_kind": "benefit_week", "start": "2026-04-06", "end": "2026-04-12"
    },
}
ORIGINAL_CASES = json.loads(
    (ROOT / "tests/fixtures/ctr_taper_original_cases.json").read_text()
)["councils"]
SOURCE_DAILY_RATE = (Fraction(2) + Fraction(6, 7)) / 100
SAME_PERIOD_RATE = 7 * SOURCE_DAILY_RATE
WEEKS_PER_YEAR = 52


def prefix(council: str) -> str:
    return council.replace("-", "_") + "_council_tax_reduction_"


def module_path(council: str) -> Path:
    return ROOT / f"uk-{council}/policies/{council}/council-tax-reduction.yaml"


@pytest.fixture(scope="session")
def engine() -> str:
    selected = os.environ.get("AXIOM_ENGINE")
    if selected:
        assert Path(selected).is_file(), f"AXIOM_ENGINE does not exist: {selected}"
        return selected
    selected = shutil.which("axiom-rules-engine")
    if not selected and shutil.which("axiom-locate"):
        located = subprocess.run(
            ["axiom-locate", "engine"], capture_output=True, text=True, check=False
        )
        candidate = located.stdout.strip()
        if located.returncode == 0 and Path(candidate).is_file():
            selected = candidate
    if not selected:
        pytest.skip("Axiom engine unavailable; set AXIOM_ENGINE to run runtime invariants")
    return selected


@dataclass
class CompiledModule:
    engine: str
    artifact: Path
    rules: dict
    inputs: list[dict]
    output_ids: dict[str, str]

    def run(self, inputs: dict, outputs: list[str], period_kind: str) -> dict:
        period = PERIODS[period_kind]
        input_reference = next(iter(self.output_ids.values())).split("#", 1)[0] + "#input."
        records = []
        for declaration in self.inputs:
            name = declaration["name"]
            value = inputs.get(name, False if declaration["dtype"] == "Boolean" else 0)
            scalar = (
                {"kind": "bool", "value": value}
                if declaration["dtype"] == "Boolean"
                else {"kind": "decimal", "value": str(value)}
            )
            records.append({
                "name": input_reference + name,
                "entity": declaration["entity"],
                "entity_id": declaration["entity"].lower(),
                "interval": {"start": period["start"], "end": period["end"]},
                "value": scalar,
            })
        by_entity: dict[str, list[str]] = {}
        for name in outputs:
            by_entity.setdefault(self.rules[name].get("entity", "Household"), []).append(name)
        request = {
            # Explain evaluates requested dependency trees. Oldham contains
            # both Household and Person outputs; eager fast mode also attempts
            # unrelated Household rules when querying its Person deduction.
            "mode": "explain",
            "dataset": {"inputs": records},
            "queries": [
                {
                    "entity_id": entity.lower(),
                    "period": period,
                    "outputs": [self.output_ids[name] for name in names],
                }
                for entity, names in by_entity.items()
            ],
        }
        completed = subprocess.run(
            [self.engine, "run-compiled", "--artifact", str(self.artifact)],
            input=json.dumps(request), capture_output=True, text=True, check=False,
        )
        assert completed.returncode == 0, completed.stderr
        response = json.loads(completed.stdout)
        ids_to_names = {value: name for name, value in self.output_ids.items()}
        result = {}
        for query in response["results"]:
            for output_id, output in query["outputs"].items():
                result[ids_to_names[output_id]] = (
                    output["outcome"] if output["kind"] == "judgment"
                    else Decimal(str(output["value"]["value"]))
                )
        assert set(result) == set(outputs)
        return result


def compile_module(engine: str, directory: Path, relative: Path, raw: dict) -> CompiledModule:
    rules = {rule["name"]: rule for rule in raw["rules"]}
    instrumented = copy.deepcopy(raw)
    mirrors = {}
    for rule in raw["rules"]:
        if rule["kind"] != "parameter":
            continue
        mirror = "ctr_test_parameter__" + rule["name"]
        formula = rule["name"]
        if rule.get("indexed_by"):
            formula += f"[{rule['indexed_by']}]"
        instrumented["rules"].append({
            "name": mirror, "kind": "derived", "entity": "Household",
            "dtype": rule["dtype"],
            **({"unit": rule["unit"]} if "unit" in rule else {}),
            "versions": [{
                "effective_from": rule["versions"][0]["effective_from"],
                "formula": formula,
            }],
        })
        mirrors[rule["name"]] = mirror
    canonical_root = directory / "rulespec-uk"
    path = canonical_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(instrumented, sort_keys=False))
    artifact = directory / "compiled.json"
    completed = subprocess.run(
        [engine, "compile", "--program", str(path), "--rulespec-root",
         str(canonical_root), "--output", str(artifact)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    compiled = json.loads(artifact.read_text())["program"]
    derived_ids = {rule["name"]: rule["id"] for rule in compiled["derived"]}
    output_ids = {
        name: derived_ids[name] if name in derived_ids else derived_ids[mirrors[name]]
        for name in rules
    }
    declarations = raw.get("inputs", [])
    if not declarations:  # The existing national module has implicit factual inputs.
        declarations = [
            {"name": name, "entity": "Household", "dtype": dtype}
            for name, dtype in (
                ("household_capital", "Money"),
                ("council_tax_liability_for_year", "Money"),
                ("non_dependant_deductions_for_year", "Money"),
                ("income_for_year", "Money"),
                ("applicable_amount_for_year", "Money"),
                ("liable_person_subject_to_immigration_control", "Boolean"),
            )
        ]
    return CompiledModule(engine, artifact, rules, declarations, output_ids)


@pytest.fixture(scope="session")
def modules(engine: str, tmp_path_factory) -> dict:
    directory = tmp_path_factory.mktemp("ctr_taper")
    result = {}
    for council in COUNCILS:
        raw = yaml.safe_load(module_path(council).read_text())
        relative = module_path(council).relative_to(ROOT)
        result[council] = compile_module(engine, directory / council, relative, raw)
        baseline = copy.deepcopy(raw)
        p = prefix(council)
        rate = next(rule for rule in baseline["rules"] if rule["name"] == p + "weekly_taper_rate")
        rate["versions"][0]["formula"] = (
            f"({p}taper_whole_percentage_points + {p}taper_fraction_numerator / "
            f"{p}days_per_week) * {p}per_cent_unit"
        )
        result[council + "-baseline"] = compile_module(
            engine, directory / (council + "-baseline"), relative, baseline
        )
    national_relative = Path("uk/policies/govuk/council-tax-reduction.yaml")
    result["national"] = compile_module(
        engine, directory / "national", national_relative,
        yaml.safe_load((ROOT / national_relative).read_text()),
    )
    return result


def clear_inputs(council: str, weekly_excess: Decimal) -> dict:
    p = prefix(council)
    if council == "oldham":
        return {
            "local_authority_is_oldham": True,
            "council_tax_reduction_household_in_england": True,
            p + "applicant_is_not_pensioner": True,
            "would_claim_council_tax_reduction": True,
            p + "assessed_capital_for_year": 0,
            p + "actual_liability_for_year": 5200,
            p + "band_a_liability_for_year": 6000,
            p + "assessed_income_for_year": (100 + weekly_excess) * WEEKS_PER_YEAR,
            p + "applicable_amount_for_year": 100 * WEEKS_PER_YEAR,
            p + "non_dependant_deductions_for_year": 0,
        }
    return {
        "local_authority_is_east_hertfordshire": True,
        p + "working_age": True,
        "would_claim_council_tax_reduction": True,
        p + "assessed_capital_for_year": 0,
        p + "weekly_liability": 100,
        p + "assessed_income_weekly": 100 + weekly_excess,
        p + "applicable_amount_weekly": 100,
        p + "non_dependant_deduction_band": 0,
    }


def check_generated_invariants(modules: dict, council: str, excess_cents: int, delta_cents: int) -> None:
    """Exact rational source arithmetic is independent of the module formula."""
    excess = Decimal(excess_cents) / 100
    delta = Decimal(delta_cents) / 100
    p = prefix(council)
    annual = council == "oldham"
    scale = WEEKS_PER_YEAR if annual else 1
    period = "tax_year" if annual else "benefit_week"
    taper_name = p + ("income_taper_deduction_for_year" if annual else "taper_deduction_weekly")
    amount_name = p + ("annual_amount" if annual else "weekly_amount")
    maximum_name = p + ("maximum_council_tax_reduction_for_year" if annual else "maximum_weekly")
    excess_name = p + ("excess_income_for_year" if annual else "excess_income_weekly")
    outputs = [
        p + "weekly_taper_rate", p + "taper_whole_percentage_points",
        p + "taper_fraction_numerator", p + "days_per_week", p + "per_cent_unit",
        taper_name, amount_name, maximum_name, excess_name, p + "award_conditions_met",
    ]
    before = modules[council].run(clear_inputs(council, excess), outputs, period)
    after = modules[council].run(clear_inputs(council, excess + delta), outputs, period)
    assert before[p + "taper_whole_percentage_points"] == 2
    assert before[p + "taper_fraction_numerator"] == 6
    assert before[p + "days_per_week"] == 7
    assert before[p + "per_cent_unit"] == Decimal("0.01")
    assert Fraction(before[p + "weekly_taper_rate"]) == SAME_PERIOD_RATE == Fraction(1, 5)
    weekly_taper = Fraction(before[taper_name]) / scale
    daily_taper = SOURCE_DAILY_RATE * Fraction(excess)
    assert weekly_taper == daily_taper * 7
    assert weekly_taper / 7 == daily_taper
    assert weekly_taper * WEEKS_PER_YEAR == daily_taper * 7 * WEEKS_PER_YEAR
    # A financial year has 365 days here. The 52-week income convention used
    # by the modules is separate: convert both operands on the same basis.
    actual_year_excess = Fraction(excess) * Fraction(365, 7)
    assert weekly_taper * Fraction(365, 7) == daily_taper * 365
    assert daily_taper * 365 == SAME_PERIOD_RATE * actual_year_excess
    assert Fraction(before[excess_name]) == Fraction(excess) * scale
    assert Fraction(after[amount_name] - before[amount_name]) == -SAME_PERIOD_RATE * Fraction(delta) * scale
    assert before[p + "award_conditions_met"] == after[p + "award_conditions_met"] == "holds"
    assert before[maximum_name] == after[maximum_name]
    assert before[amount_name] > 0 and after[amount_name] > 0

    peer_council = "east-hertfordshire" if annual else "oldham"
    peer_name = prefix(peer_council) + (
        "taper_deduction_weekly" if annual else "income_taper_deduction_for_year"
    )
    peer = modules[peer_council].run(
        clear_inputs(peer_council, excess), [peer_name],
        "benefit_week" if annual else "tax_year",
    )
    assert Fraction(peer[peer_name]) / (1 if annual else WEEKS_PER_YEAR) == weekly_taper

    # Compare only the provision retained by these two councils. Their local
    # working-age population/caps differ from the national pension-age scheme.
    # Annual income/applicable amount, zero capital/non-dependants and resulting
    # maximum are equal. Each module receives factual flags making it eligible.
    national_inputs = {
        "household_capital": 0,
        "council_tax_liability_for_year": before[maximum_name] * (1 if annual else WEEKS_PER_YEAR),
        "non_dependant_deductions_for_year": 0,
        "income_for_year": (100 + excess) * WEEKS_PER_YEAR,
        "applicable_amount_for_year": 100 * WEEKS_PER_YEAR,
        "liable_person_subject_to_immigration_control": False,
    }
    national = modules["national"].run(national_inputs, [
        "council_tax_reduction_excess_income_taper_rate",
        "council_tax_reduction_excess_income_for_year",
        "council_tax_reduction_maximum_amount_for_year",
        "council_tax_reduction_annual_amount",
        "council_tax_reduction_capital_eligible",
    ], "tax_year")
    assert national["council_tax_reduction_excess_income_taper_rate"] == Decimal("0.20")
    assert national["council_tax_reduction_capital_eligible"] == "holds"
    assert national["council_tax_reduction_excess_income_for_year"] == excess * WEEKS_PER_YEAR
    national_taper = national["council_tax_reduction_maximum_amount_for_year"] - national["council_tax_reduction_annual_amount"]
    assert Fraction(national_taper) == weekly_taper * WEEKS_PER_YEAR
    assert national["council_tax_reduction_annual_amount"] == before[amount_name] * (1 if annual else WEEKS_PER_YEAR)


if given is not None:
    @pytest.mark.parametrize("council", COUNCILS)
    @settings(max_examples=40, deadline=None, derandomize=True, database=None)
    @given(excess_cents=st.integers(1, 10000), delta_cents=st.integers(1, 2000))
    def test_generated_taper_invariants(modules, council, excess_cents, delta_cents):
        check_generated_invariants(modules, council, excess_cents, delta_cents)
else:
    @pytest.mark.parametrize("council", COUNCILS)
    @pytest.mark.parametrize("seed", range(40))
    def test_generated_taper_invariants(modules, council, seed):
        check_generated_invariants(
            modules, council, 1 + (seed * 257) % 10000, 1 + (seed * 113) % 2000
        )


def taper_dependants(rules: dict, council: str) -> set[str]:
    """Classify all versions and indexed selectors by transitive references."""
    affected = {prefix(council) + "weekly_taper_rate"}
    while True:
        expanded = affected | {
            name for name, rule in rules.items()
            if any(
                affected.intersection(re.findall(r"\b[A-Za-z_]\w*\b", version.get("formula", "")))
                for version in rule["versions"]
            ) or rule.get("indexed_by") in affected
        }
        if expanded == affected:
            return affected
        affected = expanded


@pytest.mark.parametrize("council,case", [
    (council, case)
    for council in COUNCILS
    for case in ORIGINAL_CASES[council]
], ids=[
    case["name"] for council in COUNCILS for case in ORIGINAL_CASES[council]
])
def test_non_taper_outputs_unchanged_on_original_companions(modules, council, case):
    current = modules[council]
    baseline = modules[council + "-baseline"]
    p = prefix(council)
    affected = taper_dependants(current.rules, council)
    assert affected == {
        p + "weekly_taper_rate", p + "award_conditions_met",
        p + ("income_taper_deduction_for_year" if council == "oldham" else "taper_deduction_weekly"),
        p + ("annual_amount" if council == "oldham" else "weekly_amount"),
    }
    unaffected = sorted(set(current.rules) - affected)
    for name in unaffected:
        assert current.rules[name] == baseline.rules[name]
    input_names = {
        item["name"].removeprefix(p): item["name"] for item in current.inputs
    }
    inputs = {input_names[name]: value for name, value in case["input"].items()}
    actual = current.run(inputs, unaffected, case["period_kind"])
    original = baseline.run(inputs, unaffected, case["period_kind"])
    assert actual == original
