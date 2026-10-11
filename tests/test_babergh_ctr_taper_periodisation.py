"""Execute Babergh's adjudicated weekly taper and tariff in the pinned engine.

The 2026-10-10 ruling reads the printed 20 percent as the weekly excess-income
taper. These tests use exact rational arithmetic independently of the module,
convert Babergh's actual-day annualisation before comparison with Ipswich's
52-week convention, and retain every unrelated output on the original cases.
Set AXIOM_ENGINE to run with an explicitly selected engine. Temporary modules
use the real canonical rulespec-uk directory required by the engine.
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


def _load_fixture_data():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "babergh_ctr_original_cases_fixture",
        ROOT / "tests/babergh_ctr_original_cases_fixture.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DATA


SNAPSHOT = _load_fixture_data()
# JSON object keys are strings; RuleSpec indexed-table keys are integers.
for original_rule in SNAPSHOT["original_rules"].values():
    for version in original_rule["versions"]:
        if "values" in version:
            version["values"] = {int(key): value for key, value in version["values"].items()}
SEMANTIC_FIELDS = ("kind", "entity", "dtype", "period", "unit", "indexed_by", "versions")
B = "babergh_council_tax_reduction_"
I = "ipswich_council_tax_reduction_"
SAME_PERIOD_RATE = Fraction(20, 100)
DAYS_PER_WEEK = 7
IPSWICH_WEEKS_PER_YEAR = 52
# The engine uses finite decimal arithmetic, up to 28 fractional digits. An
# annual result may multiply rounding by 366; this bound is below a penny.
ROUNDING_TOLERANCE = Fraction(1, 10**22)


def assert_rational_close(actual, expected) -> None:
    actual, expected = Fraction(actual), Fraction(expected)
    assert abs(actual - expected) <= ROUNDING_TOLERANCE, (actual, expected)


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
        if located.returncode == 0 and Path(located.stdout.strip()).is_file():
            selected = located.stdout.strip()
    if not selected:
        pytest.skip("Axiom engine unavailable; set AXIOM_ENGINE to run runtime invariants")
    return selected


def expression_inputs(node: dict, boolean: bool = False) -> list[tuple[str, bool]]:
    """Recover implicit input slots and their boolean contexts from compiled AST."""
    if node.get("kind") == "input":
        return [(node["name"], boolean)]
    boolean_comparison = node.get("kind") == "comparison" and any(
        isinstance(value, dict) and value.get("kind") == "literal"
        and value.get("value", {}).get("kind") == "bool"
        for value in node.values()
    )
    result = []
    for key, value in node.items():
        child_boolean = (
            key == "condition" or node.get("kind") in {"and", "or", "not"}
            or boolean_comparison
        )
        if isinstance(value, dict):
            result.extend(expression_inputs(value, child_boolean))
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict):
                    result.extend(expression_inputs(child, child_boolean))
    return result


@dataclass
class CompiledModule:
    engine: str
    artifact: Path
    rules: dict
    inputs: list[dict]
    output_ids: dict[str, str]

    def run(self, inputs: dict, outputs: list[str], days: int = 365) -> dict:
        period = {
            "period_kind": "tax_year", "start": "2026-04-01",
            "end": "2027-03-31" if days == 365 else "2028-03-31",
        }
        if days == 366:
            period["start"] = "2027-04-01"
        records = []
        for declaration in self.inputs:
            name = declaration["name"]
            # The printed-parameter case supplies no facts. Give its unrelated
            # daily maximum a valid divisor while retaining zero/false defaults.
            default = days if name == B + "number_of_days_in_financial_year" else (
                False if declaration["boolean"] else 0
            )
            value = inputs.get(name, default)
            scalar = (
                {"kind": "bool", "value": bool(value)}
                if declaration["boolean"] else {"kind": "decimal", "value": str(value)}
            )
            records.append({
                "name": declaration["canonical_name"],
                "entity": declaration["entity"],
                "entity_id": declaration["entity"].lower(),
                "interval": {"start": period["start"], "end": period["end"]},
                "value": scalar,
            })
        by_entity: dict[str, list[str]] = {}
        for name in outputs:
            by_entity.setdefault(self.rules[name].get("entity", "Household"), []).append(name)
        request = {
            "mode": "explain", "dataset": {"inputs": records},
            "queries": [
                {
                    "entity_id": entity.lower(), "period": period,
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


def compile_module(engine: str, directory: Path, council: str, raw: dict) -> CompiledModule:
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
    path = canonical_root / module_path(council).relative_to(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(instrumented, sort_keys=False))
    artifact = directory / "compiled.json"
    completed = subprocess.run(
        [engine, "compile", "--program", str(path), "--rulespec-root",
         str(canonical_root), "--output", str(artifact)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    compiled = json.loads(artifact.read_text())
    derived_ids = {rule["name"]: rule["id"] for rule in compiled["program"]["derived"]}
    output_ids = {
        name: derived_ids[mirrors.get(name, name)] for name in rules
    }
    # These schemes use implicit inputs. The compiler's catalog is authoritative
    # for names; the compiled expressions establish entity and boolean contexts.
    catalog = {
        item["slot"]: item["canonical_request_name"]
        for item in compiled["metadata"]["input_catalog"]
    }
    declarations = {}
    for rule in compiled["program"]["derived"]:
        for name, boolean in expression_inputs(rule["expr"]):
            entity = "Household" if rule["entity"] == "Scalar" else rule["entity"]
            key = (name, entity)
            declaration = declarations.setdefault(key, {
                "name": name, "entity": entity,
                "boolean": False, "canonical_name": catalog[name],
            })
            declaration["boolean"] |= boolean
    assert set(catalog) == {item["name"] for item in declarations.values()}
    return CompiledModule(engine, artifact, rules, list(declarations.values()), output_ids)


@pytest.fixture(scope="session")
def modules(engine: str, tmp_path_factory) -> dict:
    directory = tmp_path_factory.mktemp("babergh_ctr")
    raw = yaml.safe_load(module_path("babergh").read_text())
    baseline = copy.deepcopy(raw)
    assert {rule["name"] for rule in baseline["rules"]} == set(SNAPSHOT["original_rules"])
    for rule in baseline["rules"]:
        for key in SEMANTIC_FIELDS:
            rule.pop(key, None)
        rule.update(copy.deepcopy(SNAPSHOT["original_rules"][rule["name"]]))
    return {
        "babergh": compile_module(engine, directory / "babergh", "babergh", raw),
        "original": compile_module(engine, directory / "original", "babergh", baseline),
        "ipswich": compile_module(
            engine, directory / "ipswich", "ipswich",
            yaml.safe_load(module_path("ipswich").read_text()),
        ),
    }


def clear_inputs(weekly_excess, days: int = 365, capital=0, non_dependant_daily=0) -> dict:
    return {
        B + "working_age_scheme_applies": True,
        "would_claim_council_tax_reduction": True,
        B + "assessed_capital_for_year": capital,
        B + "eligible_liability_for_year": 20 * days,
        B + "non_dependant_deductions_for_day": non_dependant_daily,
        B + "assessed_income_weekly": Decimal(100) + Decimal(weekly_excess),
        B + "applicable_amount_weekly": 100,
        B + "class_f_applies": False,
        B + "class_f_no_entitlement": False,
        B + "class_f_income_band": 0,
        B + "number_of_days_in_financial_year": days,
    }


def check_generated_invariants(modules, excess_cents: int, delta_cents: int, days: int) -> None:
    excess = Decimal(excess_cents) / 100
    delta = Decimal(delta_cents) / 100
    outputs = [
        B + "daily_taper_rate", B + "weekly_taper_rate", B + "days_per_week",
        B + "capital_eligible", B + "tariff_income_weekly", B + "excess_income_weekly",
        B + "maximum_amount_for_day", B + "class_e_taper_deduction_daily",
        B + "class_e_amount_before_floor_for_day", B + "annual_amount",
    ]
    before = modules["babergh"].run(clear_inputs(excess, days), outputs, days)
    after = modules["babergh"].run(clear_inputs(excess + delta, days), outputs, days)
    assert Fraction(before[B + "daily_taper_rate"]) == SAME_PERIOD_RATE
    assert Fraction(before[B + "weekly_taper_rate"]) == SAME_PERIOD_RATE
    assert before[B + "days_per_week"] == DAYS_PER_WEEK
    assert before[B + "capital_eligible"] == after[B + "capital_eligible"] == "holds"
    assert before[B + "tariff_income_weekly"] == after[B + "tariff_income_weekly"] == 0
    assert before[B + "excess_income_weekly"] == excess
    assert after[B + "excess_income_weekly"] == excess + delta
    assert before[B + "maximum_amount_for_day"] == after[B + "maximum_amount_for_day"] == 20
    source_weekly_deduction = SAME_PERIOD_RATE * Fraction(excess)
    daily_deduction = Fraction(before[B + "class_e_taper_deduction_daily"])
    daily_support = Fraction(before[B + "class_e_amount_before_floor_for_day"])
    annual_support = Fraction(before[B + "annual_amount"])
    assert_rational_close(daily_deduction, source_weekly_deduction / DAYS_PER_WEEK)
    assert_rational_close(daily_deduction * DAYS_PER_WEEK, source_weekly_deduction)
    assert_rational_close(daily_deduction * days, source_weekly_deduction * Fraction(days, 7))
    actual_year_excess = Fraction(excess) * Fraction(days, 7)
    assert_rational_close(20 * days - annual_support, SAME_PERIOD_RATE * actual_year_excess)
    assert_rational_close(daily_support, 20 - source_weekly_deduction / 7)
    assert_rational_close(annual_support, daily_support * days)
    assert_rational_close(
        Fraction(before[B + "annual_amount"]) - Fraction(after[B + "annual_amount"]),
        SAME_PERIOD_RATE * Fraction(delta) * Fraction(days, 7),
    )
    assert_rational_close(
        (Fraction(before[B + "class_e_amount_before_floor_for_day"])
         - Fraction(after[B + "class_e_amount_before_floor_for_day"])) * 7,
        SAME_PERIOD_RATE * Fraction(delta),
    )
    # £140 weekly maximum and at most £24 taper leaves both awards far above
    # the £1 minimum and zero floor; capital is below the tariff threshold.
    assert before[B + "annual_amount"] > 0 and after[B + "annual_amount"] > 0
    assert after[B + "class_e_amount_before_floor_for_day"] * 7 > 100


if given is not None:
    @settings(max_examples=40, deadline=None, derandomize=True, database=None)
    @given(
        excess_cents=st.integers(1, 10000), delta_cents=st.integers(1, 2000),
        days=st.sampled_from([365, 366]),
    )
    def test_generated_taper_period_consistency(modules, excess_cents, delta_cents, days):
        check_generated_invariants(modules, excess_cents, delta_cents, days)
else:
    @pytest.mark.parametrize("seed", range(40))
    def test_generated_taper_period_consistency(modules, seed):
        check_generated_invariants(
            modules, 1 + (seed * 257) % 10000, 1 + (seed * 113) % 2000,
            365 + seed % 2,
        )


@pytest.mark.parametrize("weekly_excess,capital,non_dependant_daily", [
    (0, 0, 0), (10, 6000, 0), (10, Decimal("6000.01"), 0),
    (10, 6250, 1), (10, Decimal("6250.01"), 1), (60, 10000, 0),
    (100, 16000, 1),
])
@pytest.mark.parametrize("days", [365, 366])
def test_same_text_matches_ipswich_after_period_conversion(
    modules, weekly_excess, capital, non_dependant_daily, days,
):
    babergh = modules["babergh"].run(
        clear_inputs(weekly_excess, days, capital, non_dependant_daily),
        [B + "weekly_taper_rate", B + "tariff_income_weekly", B + "annual_amount"], days,
    )
    ipswich_inputs = {
        I + "assessed_capital_for_year": capital,
        I + "maximum_eligible_liability_for_year": 20 * 7 * IPSWICH_WEEKS_PER_YEAR,
        I + "assessed_income_for_year": (100 + weekly_excess) * IPSWICH_WEEKS_PER_YEAR,
        I + "applicable_amount_for_year": 100 * IPSWICH_WEEKS_PER_YEAR,
        I + "non_dependant_deductions_for_year": non_dependant_daily * 7 * IPSWICH_WEEKS_PER_YEAR,
        I + "has_universal_credit_award": False,
    }
    ipswich = modules["ipswich"].run(ipswich_inputs, [
        I + "taper_rate", I + "tariff_income_for_year", I + "working_age_annual_amount",
    ], days)
    assert Fraction(ipswich[I + "taper_rate"]) == SAME_PERIOD_RATE
    assert babergh[B + "weekly_taper_rate"] == ipswich[I + "taper_rate"]
    assert_rational_close(
        Fraction(ipswich[I + "tariff_income_for_year"]) / IPSWICH_WEEKS_PER_YEAR,
        babergh[B + "tariff_income_weekly"],
    )
    expected_weekly = (20 - non_dependant_daily) * 7 - SAME_PERIOD_RATE * (
        weekly_excess + Fraction(babergh[B + "tariff_income_weekly"])
    )
    assert_rational_close(Fraction(babergh[B + "annual_amount"]) * Fraction(7, days), expected_weekly)
    assert_rational_close(Fraction(ipswich[I + "working_age_annual_amount"]) / 52, expected_weekly)


@pytest.mark.parametrize("capital,tariff", [
    (Decimal("6000.01"), 1), (6250, 1), (Decimal("6250.01"), 2),
    (6500, 2), (10000, 16), (16000, 40),
])
def test_tariff_income_raises_excess_and_reduces_support(modules, capital, tariff):
    outputs = [
        B + "capital_eligible", B + "tariff_income_weekly", B + "excess_income_weekly",
        B + "maximum_amount_for_day", B + "class_e_taper_deduction_daily", B + "annual_amount",
    ]
    before = modules["babergh"].run(clear_inputs(10), outputs)
    after = modules["babergh"].run(clear_inputs(10, capital=capital), outputs)
    assert before[B + "capital_eligible"] == after[B + "capital_eligible"] == "holds"
    assert before[B + "tariff_income_weekly"] == 0
    assert after[B + "tariff_income_weekly"] == tariff
    assert before[B + "excess_income_weekly"] == 10
    assert after[B + "excess_income_weekly"] == 10 + tariff
    assert before[B + "maximum_amount_for_day"] == after[B + "maximum_amount_for_day"] == 20
    assert_rational_close(after[B + "class_e_taper_deduction_daily"], Fraction(10 + tariff, 35))
    assert_rational_close(
        Fraction(before[B + "annual_amount"]) - Fraction(after[B + "annual_amount"]),
        Fraction(tariff, 5) * Fraction(365, 7),
    )


@pytest.mark.parametrize("defect", ["taper", "tariff"])
def test_original_defects_fail_independent_source_oracles(modules, defect):
    """Each source oracle rejects its historical defect without the other one."""
    outputs = [B + "annual_amount", B + "excess_income_weekly"]
    changes = {}
    for label in ("babergh", "original"):
        before = modules[label].run(
            clear_inputs(10, capital=6000 if defect == "tariff" else 0), outputs,
        )
        if defect == "taper":
            # No tariff on either side: £10 more weekly excess costs £2 weekly.
            after = modules[label].run(clear_inputs(20), outputs)
            changes[label] = (
                Fraction(before[B + "annual_amount"])
                - Fraction(after[B + "annual_amount"])
            ) * Fraction(7, 365)
            expected = Fraction(2)
        else:
            # Query excess itself: this oracle does not depend on taper rates.
            after = modules[label].run(clear_inputs(10, capital=6250), outputs)
            changes[label] = (
                Fraction(after[B + "excess_income_weekly"])
                - Fraction(before[B + "excess_income_weekly"])
            )
            expected = Fraction(1)
    assert_rational_close(changes["babergh"], expected)
    with pytest.raises(AssertionError):
        assert_rational_close(changes["original"], expected)


def repair_dependants(rules: dict) -> set[str]:
    """Classify every version and indexed selector by transitive dependencies."""
    affected = {
        B + "weekly_taper_rate", B + "excess_income_weekly",
        B + "class_e_taper_deduction_daily",
    }
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


@pytest.mark.parametrize("case", SNAPSHOT["cases"], ids=lambda case: case["name"])
def test_unrelated_outputs_unchanged_on_all_original_cases(modules, case):
    current, original = modules["babergh"], modules["original"]
    affected = repair_dependants(current.rules)
    assert affected == {
        B + "weekly_taper_rate", B + "excess_income_weekly",
        B + "class_e_taper_deduction_daily", B + "class_e_amount_before_floor_for_day",
        B + "annual_amount",
    }
    unaffected = sorted(set(current.rules) - affected)
    assert B + "tariff_income_weekly" in unaffected
    assert B + "class_f_amount_before_floor_for_day" in unaffected
    for name in unaffected:
        assert {
            key: current.rules[name][key] for key in SEMANTIC_FIELDS if key in current.rules[name]
        } == SNAPSHOT["original_rules"][name]
    actual = current.run(case["input"], unaffected)
    baseline = original.run(case["input"], unaffected)
    assert actual == baseline
    # Original printed expectations are another independent retained check.
    for name in set(case["output"]) & set(unaffected):
        expected = case["output"][name]
        assert actual[name] == (expected if isinstance(expected, str) else Decimal(str(expected)))
