"""Pinned original cases for the regression tests (moved from tests/fixtures/ctr_taper_original_cases.json:
the repository allows only Python files under tests/)."""

import json

DATA = json.loads(
    r'''{
 "baseline_commit": "1bdb98374",
 "note": "Original 13 Oldham and 34 East Hertfordshire companion cases from main. Council prefixes are omitted. False and zero inputs are omitted and supplied as neutral defaults; every original nonzero/true input is preserved. Missing original inputs receive the same defaults in both runs.",
 "councils": {
  "oldham": [
   {
    "name": "oldham_ctr_printed_parameters",
    "period_kind": "tax_year",
    "input": {}
   },
   {
    "name": "oldham_ctr_positive_taper_band_a_binding",
    "period_kind": "tax_year",
    "input": {
     "local_authority_is_oldham": true,
     "council_tax_reduction_household_in_england": true,
     "applicant_is_not_pensioner": true,
     "would_claim_council_tax_reduction": true,
     "actual_liability_for_year": 1200,
     "band_a_liability_for_year": 1000,
     "assessed_income_for_year": 520
    }
   },
   {
    "name": "oldham_ctr_positive_taper_band_a_non_binding",
    "period_kind": "tax_year",
    "input": {
     "local_authority_is_oldham": true,
     "council_tax_reduction_household_in_england": true,
     "applicant_is_not_pensioner": true,
     "would_claim_council_tax_reduction": true,
     "band_a_liability_for_year": 1000,
     "assessed_income_for_year": 520,
     "actual_liability_for_year": 800
    }
   },
   {
    "name": "oldham_ctr_taper_equality_zero_award",
    "period_kind": "tax_year",
    "input": {
     "local_authority_is_oldham": true,
     "council_tax_reduction_household_in_england": true,
     "applicant_is_not_pensioner": true,
     "would_claim_council_tax_reduction": true,
     "actual_liability_for_year": 1200,
     "band_a_liability_for_year": 1000,
     "assessed_income_for_year": 29750
    }
   },
   {
    "name": "oldham_ctr_taper_exhaustion_zero_award",
    "period_kind": "tax_year",
    "input": {
     "local_authority_is_oldham": true,
     "council_tax_reduction_household_in_england": true,
     "applicant_is_not_pensioner": true,
     "would_claim_council_tax_reduction": true,
     "actual_liability_for_year": 1200,
     "band_a_liability_for_year": 1000,
     "assessed_income_for_year": 30000
    }
   },
   {
    "name": "oldham_ctr_capital_limit_eligible",
    "period_kind": "tax_year",
    "input": {
     "local_authority_is_oldham": true,
     "council_tax_reduction_household_in_england": true,
     "applicant_is_not_pensioner": true,
     "would_claim_council_tax_reduction": true,
     "actual_liability_for_year": 1200,
     "band_a_liability_for_year": 1000,
     "assessed_capital_for_year": 16000,
     "applicable_amount_for_year": 2080
    }
   },
   {
    "name": "oldham_ctr_capital_cliff_ineligible",
    "period_kind": "tax_year",
    "input": {
     "local_authority_is_oldham": true,
     "council_tax_reduction_household_in_england": true,
     "applicant_is_not_pensioner": true,
     "would_claim_council_tax_reduction": true,
     "actual_liability_for_year": 1200,
     "band_a_liability_for_year": 1000,
     "assessed_income_for_year": 520,
     "assessed_capital_for_year": 16000.01
    }
   },
   {
    "name": "oldham_ctr_non_dependant_exemption_no_deduction",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "oldham_ctr_non_remunerative_other_case",
    "period_kind": "benefit_week",
    "input": {
     "non_dependant_deduction_applies": true
    }
   },
   {
    "name": "oldham_ctr_remunerative_below_266",
    "period_kind": "benefit_week",
    "input": {
     "non_dependant_deduction_applies": true,
     "non_dependant_in_remunerative_work": true,
     "non_dependant_normal_gross_weekly_income": 265.99
    }
   },
   {
    "name": "oldham_ctr_remunerative_266_to_below_463",
    "period_kind": "benefit_week",
    "input": {
     "non_dependant_deduction_applies": true,
     "non_dependant_in_remunerative_work": true,
     "non_dependant_normal_gross_weekly_income": 266.0
    }
   },
   {
    "name": "oldham_ctr_remunerative_463_to_below_577",
    "period_kind": "benefit_week",
    "input": {
     "non_dependant_deduction_applies": true,
     "non_dependant_in_remunerative_work": true,
     "non_dependant_normal_gross_weekly_income": 463.0
    }
   },
   {
    "name": "oldham_ctr_remunerative_at_least_577",
    "period_kind": "benefit_week",
    "input": {
     "non_dependant_deduction_applies": true,
     "non_dependant_in_remunerative_work": true,
     "non_dependant_normal_gross_weekly_income": 577.0
    }
   }
  ],
  "east-hertfordshire": [
   {
    "name": "east_hertfordshire_ctr_parameters",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_taper_whole_points_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_fraction_numerator_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_days_per_week_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_per_cent_unit_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_weekly_taper_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_capital_limit_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_tariff_threshold_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_tariff_step_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_tariff_amount_parameter",
    "period_kind": "benefit_week",
    "input": {}
   },
   {
    "name": "east_hertfordshire_ctr_non_dependant_no_deduction",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_non_dependant_520",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100,
     "non_dependant_deduction_band": 1
    }
   },
   {
    "name": "east_hertfordshire_ctr_non_dependant_1060",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100,
     "non_dependant_deduction_band": 2
    }
   },
   {
    "name": "east_hertfordshire_ctr_non_dependant_1330",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100,
     "non_dependant_deduction_band": 3
    }
   },
   {
    "name": "east_hertfordshire_ctr_non_dependant_1595",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100,
     "non_dependant_deduction_band": 4
    }
   },
   {
    "name": "east_hertfordshire_ctr_tariff_at_6000",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "assessed_capital_for_year": 6000,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_tariff_at_600001",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "assessed_capital_for_year": 6000.01,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_tariff_at_6250",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "assessed_capital_for_year": 6250,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_tariff_at_625001",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "assessed_capital_for_year": 6250.01,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_capital_at_limit",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "assessed_capital_for_year": 16000,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_capital_above_limit",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "assessed_capital_for_year": 16000.01,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_maximum_after_selected_deduction",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100,
     "non_dependant_deduction_band": 4
    }
   },
   {
    "name": "east_hertfordshire_ctr_income_below_applicable",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 99,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_income_equal_applicable",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_income_above_applicable",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 150,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_taper_deduction",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 150,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_excess_income",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 150,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_taper_just_below_exhaustion",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 3302.49,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_taper_at_exhaustion",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 3302.5,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_taper_above_exhaustion",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 3302.51,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_wrong_authority",
    "period_kind": "benefit_week",
    "input": {
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_award_conditions_hold",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "assessed_income_weekly": 150,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_non_working_age",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "would_claim_council_tax_reduction": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   },
   {
    "name": "east_hertfordshire_ctr_no_claim",
    "period_kind": "benefit_week",
    "input": {
     "local_authority_is_east_hertfordshire": true,
     "working_age": true,
     "weekly_liability": 100,
     "applicable_amount_weekly": 100
    }
   }
  ]
 }
}'''
)
