# Encoding gaps

## `uk-kingston-upon-thames/policies/kingston-upon-thames/council-tax-reduction.yaml`

The source-subparagraph coverage validator reports page 38(e) as uncovered. The module honestly defers the applicable-premiums amount because the source delegates its eligibility and amount to Parts 3 and 4 of the applicable-amount Schedule. The deferred-output grammar accepts only the four atomic RuleSpec roots, while coverage for this corpus row looks for a target beneath `manuals/council-tax-reduction-scheme-2026-2027/page-38/e`. A valid `policies/.../e` deferred target therefore cannot satisfy the manual-path coverage match.

This is a missing validator/source-path representation, not evidence that an encoded value is wrong. Treating the premium as zero or inventing its amount would be incorrect; the current executable rules leave it out and disclose the blocker explicitly.

## `uk/regulations/uksi/2013/376/34.yaml`

The source-scope validator rejects `other_relevant_support_amount_left_out_of_account` because it is a `Family` amount while regulation 34(3) describes claimant/member conditions for the work-transition-payment exception. Regulation 34(2), however, applies the excluded amount within the family-level relevant-childcare-charges calculation, which is where this intermediate is consumed. The pinned corpus provides the regulation as one undivided row, so there is no narrower descendant citation that separately establishes a family-scoped exception amount.

This is missing source granularity and an unresolved entity-mapping judgment, not a known wrong monetary value. Changing the rule to a person entity without an aggregation contract would alter its meaning and disconnect it from the family charge calculation, so the existing formula is retained and the validator failure is waived.

## Generated-module grounding debt (#137, waived 2026-07-13)

The hard-cut single-source grounding sweep flags generator-emitted
structural constants absent from the override source pages: 9× the weekly
annualization literal `52` (e.g. `carers_allowance_weeks_in_year`), plus
`710.00` and `1000000` scale/threshold factors (ukpga/2006/46/382,
Companies Act small-company conditions). Judgment: not wrong values —
missing groundable provenance in the govuk/compose generators. Fix belongs
upstream (emit conversions as structural constants with provenance);
tracked per-module in known-validation-gaps.yaml under #137.
