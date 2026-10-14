# Statutory and scheme rule encoding playbook

This playbook records the method used in the UK council-tax-reduction campaign
for encoding statutory and scheme rules. It is offered as a transferable
pattern for other jurisdiction lanes, including DK, US, and SOUTHMOD; each
lane's authority model, corpus contracts, and gate battery require separate
validation before the method is treated as established there. Replace
council-specific labels with the authority, instrument, program, and period
relevant to the lane.

Since 2026-10-11, council modules in this repository come only from the
supervised encoder ([campaign route](uk-ctr/README.md#the-route)). The
generator described here, a model working from a scheme-specific steer, is
retired. The error classes, checks, gate battery and review protocol are how
encoder output is reviewed.

## The two-layer harness

The harness has two layers.

The first layer generates a grounded module and runs deterministic gates. The
generator receives a narrow target, the operative authority, verified findings,
known failure classes, the required output shape, and the exact run context. It
emits parameter rules, derived rules, proof atoms, companion tests, and scoped
deferrals. Deterministic checks then reject schema errors, invalid expressions,
non-verbatim or insufficient proof, missing companion declarations, role
mismatches, ledger drift, and repository regressions.

The second layer is cross-family semantic review. A reviewer compares several
modules that implement related schemes and adjudicates the differences against
each scheme's own text. This catches errors that can be internally consistent
and green: the wrong maximum-rate source, the wrong legal population, an
incorrect band-linkage model, a reversed boundary, a collapsed family table, or
a test expectation copied from the implementation rather than the printed
scheme.

Review is the quality floor. In this campaign, every generated module required
at least one substantive correction. Passing deterministic gates establishes
mechanical admissibility; it does not establish formula fidelity.

The working loop is:

1. Discover and verify the operative source.
2. Fetch and preserve the source bytes.
3. Ingest the verified source into the lane's corpus tree.
4. Generate from a scheme-specific steer.
5. Run deterministic gates with no waivers.
6. Obtain a cross-family semantic verdict.
7. Correct every finding, rerun the gates, and request a re-verdict.
8. Merge only on `SHIP` and green checks.

## The error-class catalog

Each error class below pairs an anonymized campaign example with the check that
caught it. Treat the examples as patterns, not exceptions tied to one lane.

### Maximum-rate caps

The maximum rate belongs inside the maximum-award calculation, before a band or
taper is applied. Do not assume 100 percent and do not infer a cap from a table's
top row.

Real example: one module used a maximum rate from a pension-age document, and
another generation had cross-authority steer contamination. The resulting
formulas were plausible but sourced to the wrong scheme. Other reviewed schemes
printed caps such as 91.5, 85, and 78 percent, showing why a default is unsafe.

Check: require a value-bearing, verbatim atom from the authority's own operative
provision for the encoded population. Review the formula order as
`eligible liability × maximum rate`, followed by the printed band, deduction,
taper, floor, or minimum-award operations.

### Banded-versus-taper linkage adjudication

Band tables do not say by themselves whether a rate composes with a defined
maximum or directly determines an award ceiling. Quote the deciding sentence.

Real example: two modules had to be rewritten from a ceiling interpretation to
`maximum × band rate`, followed by the non-dependant deduction and a zero floor.
Across the campaign, this adjudication caught at least five formula errors.

Check: if the deciding sentence says the discount is based on the scheme's
defined maximum, compose the band rate onto that maximum. Use a ceiling or
`min` form only when the text prints affirmative operative wording for direct
award. Numerical coincidence, such as the top band equalling the cap, may
corroborate a reading but never decides it: tables alone are insufficient, and
equality without operative wording is still a table. For a taper, implement the
printed structure, such as maximum less excess income multiplied by the taper.
If no linkage sentence exists, encode the printed award basis and record the
verified absence; do not guess.

### Daily, weekly and annual taper consistency

Read the period of the maximum, the income excess and the deduction together.
A rate's name or `period:` declaration does not convert its operands. Where a
scheme deducts 2 6/7 percent of a **weekly** excess from a **daily** maximum,
the equivalent weekly deduction is 20 percent of that excess: multiply the
daily deduction by seven, or use the derived same-period rate after converting
the calculation consistently.

The campaign provides examples of this failure. Until #447,
[Oldham](../uk-oldham/policies/oldham/council-tax-reduction.yaml) applied
`(2 + 6/7) × 0.01` directly to an annual excess, and
[East Hertfordshire](../uk-east-hertfordshire/policies/east-hertfordshire/council-tax-reduction.yaml)
applied the same rate to a weekly excess, while both called the parameter a
weekly rate. Their companion expectations reproduced that calculation, so a
passing companion suite could not establish period consistency. #447 repaired
both and added the period-consistency tests in
`tests/test_ctr_taper_periodisation.py`. The public review on
[#140](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-5845299202)
records the source context and the broader failure class.

Check: derive the expected same-period rate from the operative provision,
using grounded conversion parameters. In cases clear of capital cliffs, band
edges, minimum awards and the zero floor, increase weekly excess by a known
amount and assert the change in weekly support. Verify that daily, weekly and
annual formulations agree after conversion. Compare with a national module
only where the council retains that provision, including its local overrides;
a global requirement that every council taper be 20 percent would be wrong.
Re-derive companion expectations from the text before testing the repair.

### Contradictory source provisions and related schemes

A verbatim excerpt can still omit the sentence that changes its meaning. When
source provisions disagree, record both provisions and the unresolved decision
instead of silently selecting a value or copying a neighbouring council.

[Babergh](../uk-babergh/policies/babergh/council-tax-reduction.yaml) and
[Ipswich](../uk-ipswich/policies/ipswich/council-tax-reduction.yaml) print the
same sentence: a "prescribed daily percentage" of 20 per cent, deducted from a
maximum that the scheme states per day. Read literally, that withdraws 140
percent of a week's excess income per week. Until October 2026 the two modules
disagreed: Babergh subtracted 20 percent of a weekly excess from a daily
maximum, and Ipswich applied 20 percent to annual excess against an annual
maximum. The
[maintainer's issue reply](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-5872231649)
identified the wording as an unresolved interpretation.

The maintainer ruled on 10 October 2026 that the sentence means 20 percent of
weekly excess per week, for every scheme with this wording. The prescribed and
default schemes deduct 2 6/7 percent a day from a daily maximum, which is 20
percent a week, and these schemes printed "20 per cent" without dividing by
seven. Babergh now applies that reading and quotes the literal sentence and the
ruling in its module summary. Ipswich and
[Guildford](../uk-guildford/policies/guildford/council-tax-reduction.yaml)
already apply 20 percent to same-period excess. The ruling also names Mid
Suffolk, which is not in this repository yet.

The ruling settles this wording only. Formula agreement and familiar rates did
not settle it, and will not settle the next conflict: record both provisions
and ask.

Arun illustrates a different conflict: s.23(3) prints band A at 100 percent,
while Schedule 3 paragraph 1 prints 90 percent for the same scheme year, and
s.23(4) calls the schedule a summary. The maintainer ruled on 10 October 2026
that band A is 100 percent, following s.23(3). An Arun encoding keeps both
citations, records the ruling, and still encodes Schedule 3's passported
band A rule. The [campaign hand-off](uk-ctr/README.md#arun-band-a-ruled-100)
and [section citation map](uk-ctr/section-ingest.md) hold the evidence.

### Publisher confirmations

When a council answers a question about its own scheme, the answer can confirm
or contradict the reading an encoding adopted. Record it with the rules below.
The RuleSpec `interpretations` metadata being added in
[axiom-rules-engine#247](https://github.com/TheAxiomFoundation/axiom-rules-engine/pull/247)
proposes a `confirmation` record that holds the organisation, date, quoted
sentence and public URL as `by`, `date`, `excerpt` and `record`; the private
original and its hash stay outside it.

- Cite the organisation and the date of its reply. Never cite an officer's
  name, email address, or mailbox or message identifier.
- Quote only the factual sentence that answers the question. When the email
  carries a protective marking or a non-disclosure footer, quote it only after
  the council gives permission. Until then the reading stays recorded as a
  ruling or an open question, not as a confirmation.
- Keep the original message privately, outside the repository, with its hash.
- Auto-replies and acknowledgements never count as confirmations.
- Ask new clarification questions as Freedom of Information requests through
  WhatDoTheyKnow, so each answer has a permanent public URL that the record
  can cite.

### Operative-year traps

A current cover or filename does not make prior-year substantive text operative.
The period and the incorporated instrument must be established by official
operative material.

Real example: a prior scheme instrument remained the substantive text while a
later Full Council resolution continued it. A simple old-PDF-plus-Cabinet pair
failed because Cabinet had only recommended adoption and the later decision also
uprated values. In a separate year-silent appendix pattern, the operative-year
anchor had to come from the page-1 identification text rather than the appendix
body.

Check: apply the closed-corpus incorporation gate. Require a timely, final Full
Council decision with adopted status, a target period covering the encode, and
an unbroken identification chain to the exact scheme text. Classify the chain as
`ACCEPT`, `ACCEPT-DERIVED`, or `REJECT`. Tripwire amendment language such as
“uprate”, “as amended”, or “new income bands”; include every determinate overlay
or reject the corpus. Cite the commencement or scheme-year clause, or the page-1
identification atom for a year-silent appendix.

LGFA 1992 Schedule 1A paragraph 5 requires a revision or replacement scheme to
be made no later than 11 March in the financial year before it takes effect.
A decision dated after that deadline does not meet the requirement, so treat
the operative year as not established and record the question rather than
encoding it.

Adoption records play two roles. Where minutes, reports or decision records
only identify the year and the instrument, they are corroboration: value atoms
cite the scheme-text page that prints the value. Where an adopted resolution
itself sets a binding amendment or uprating, that resolution is operative text
under the incorporation gate above, and the atom for that value cites the
resolution. Example: one merged module takes its maximum-award starting point
from the Full Council minutes that continued the scheme.

### Provision-role anchoring

A printed numeral is not sufficient when its surrounding provision serves a
different legal population or function.

Real example: a working-age non-dependant deduction cited a page whose context
was pensioners. The value-bearing proof check passed because the numeral was
present, but the rule inherited the wrong provision role. The same class had
previously turned a pensioner capital value into a working-age value.

Check: run a role audit over rule names, cited pages, and surrounding provision
headings. In composite instruments, map working-age, pension-age, UC, non-UC,
discretionary, and other scheme limbs separately. Semantic review must read the
context around every locally controlled value.

### Controlling-source and authority attestation

Grounding every value verbatim does not establish that the module as a whole
attests the right controlling source. A module can pass every atom-level and
money-value check while its source-verification contract names the wrong
instrument, page, or authority for the calculation it implements.

Real example: a module's atoms and money checks all passed while validation
correctly failed the module-level source-authority contract, which required
repair independently of any individual excerpt.

Check: validate the module-level source-verification contract as its own gate,
distinct from atom grounding: the cited instrument is the operative authority
for the encoded calculation, and the citation path points at the provision
that carries it.

### Band-edge over and at-least semantics

Translate boundary words literally. “Over X” selects the next band only above
X; “at least X” includes X. Likewise, “not exceeding X” includes X.

Real example: a capital rule said “not exceeding £16,000”. Exactly £16,000 was
eligible even though a conventional capital-cliff implementation rejected it.
Another family-grid repair required each non-terminal upper bound to select the
current band at the bound and the next band at £0.01 above it.

Check: write boundary pairs before trusting the selector: below/at/above as the
wording requires. Inspect comparison operators in the derived rule and assert
the selected band as well as the final award.

### Strict class boundaries and the equality gap

Many schemes define one class by income "less than" the applicable amount and
another by income "greater than" it. Income exactly equal to the applicable
amount is then in neither class. Encode the classes as printed. A taper written
as the maximum less a rate times `max(0, income − applicable amount)` awards
the full maximum at equality, whatever the classes say.

Real example: several wave-11 modules computed the award from that `max(0, …)`
form with no class predicate, so a household whose income equalled its
applicable amount received full support that no printed class granted. Another
tested the boundary with whole-pound incomes on either side of the equality
point instead of the penny neighbours.

Check: read the operative class conditions, not class headings or summaries;
a heading can say "less than" while the operative condition says "does not
exceed". Assert the class predicates themselves. Add cases at income equal to
the applicable amount and one penny either side. Where the operative conditions
leave equality uncovered, do not extend a class to close the gap on your own
reading: record both readings and get a ruling, as for contradictory
provisions, then assert the ruled outcome in a companion case.

### Award entitlement conditions

The award rule carries every printed entitlement condition, not only the
capital limit: the working-age population (not a pensioner), membership of an
award class, a made application where the scheme requires one, and any
passported route that sets the award regardless of income.

Real example: several wave-11 modules gated the award on capital alone, so a
pensioner, a non-applicant or a household in no class still received the
working-age award. Another omitted a printed passported branch for applicants
on Income Support, income-based Jobseeker's Allowance or income-related
Employment and Support Allowance.

Check: for each printed condition, add a case in which only that condition
fails and the award is zero. For each passported route, add a case whose income
alone would give a lower award.

### Per-household parameter collapse

Do not replace a family- or household-indexed table with one scalar ceiling,
even when nearby rows share amounts.

Real example: a protected-group grid printed upper limits of £180, £250, £330,
and £500 for different household categories. The module ended its selector with
an unconditional top band and omitted the household-specific upper-limit
parameters, so income above a category's ceiling still received an award.

Check: represent the printed grid as an indexed parameter table, cover every
family column, and test the terminal edge independently for each category. Table
proof must span all claimed cells; a same-amount row still needs the atom for the
claimed row.

### Liability ceilings

Where the maximum is computed on the lower of the actual liability and the
charge for a stated band (a Band B, C or D cap), the module computes that
minimum itself. Taking an already-capped liability as an input moves the
scheme's rule outside the module.

Real example: two wave-11 modules accepted a pre-capped liability input for a
printed Band D ceiling, so neither module ever applied the cap.

Check: encode `min(actual liability, band charge)` with the band charge as a
grounded parameter or a declared input. Add one case where the actual liability
is strictly below the ceiling and one where the ceiling binds; a case at
equality demonstrates neither branch.

### Companion coverage

Companions are an independent executable transcription of the printed scheme,
not examples selected to make the implementation pass.

Real example: one reviewed module covered a terminal edge but omitted both-side
cases for every non-terminal edge. Another omitted four household ceilings,
internal band pairs, a just-below-minimum-award case, and assertions for several
parameter identifiers.

Check: exercise both sides of every edge in every family column, both sides of
each cliff, the zero branch, each parameter, and every derived rule. Use one
derived-output entity per case. Hand-derive expected values from the printed
grid. Quote the engine's exact decimal string when division repeats; do not use
a float-truncated expectation.

Case mechanics the campaign's gates enforced or its reviews kept finding:
every case assigns every factual input that the outputs under test depend on,
including inputs that are false (a parameter-only case may have none);
companions use no YAML merge anchors; parameter tables are not
keyed by booleans, so branch with conditions over grounded parameters instead.
For tariff income, test the threshold and the first step on both sides,
following the scheme's "or part thereof" wording.

Indexed-table assertion boundary (adjudicated wave 8): direct per-index
assertions are required where the index is a factual input slot; where the
index is derived, complete spanning coverage through cases that derive and
assert the resulting legal outcomes is sufficient. The pinned validator makes
the direct form impossible for derived indices (it requires the `indexed_by`
selector in case input and rejects computed outputs as inputs), and replacing a
derived index with an input slot bypasses legally meaningful classification
logic — do not restructure modules to force direct assertions.

### Embedded scalars versus parameter rules

Every legally meaningful constant is a named, grounded parameter rule. Derived
rules refer to parameters rather than embedding numeric literals.

Real example: generated band selectors embedded category keys such as 0 through
6 directly in nested conditions. Other modules embedded non-dependant band
numbers. The expressions worked, but the constants had no independently
reviewable proof or parameter companions.

Check: the validator's embedded-scalar check must be clean. Extract selector
keys, thresholds, rates, floors, and amounts into named numeric concepts or
indexed tables, give each its own atom, and assert each parameter in companions.

### Derived constants from printed values

Derived constants must remain visibly derived from grounded printed values.
Do not type the arithmetic result as a new literal.

Real example: a mixed taper-and-band module contained an ungrounded `5.2`
literal. The value was repaired by expressing it from the values the scheme
actually printed rather than treating the result as an independent fact.

Check: proof validation should find printed forms in the atoms for source
parameters; formula review should trace every derived number to those parameters.
For weekly/daily conversions and similar arithmetic, encode the formula and let
the engine calculate the result.

For percentages, most merged council modules ground the printed percentage
directly as a decimal `Rate` (for example 0.2 for "20 per cent"). Seven of the
100 instead use a `Rate` unit of 0.01 grounded on the scheme's own "per cent"
wording (for example "100 per cent of the amount A/B") and multiply by it,
which keeps a mixed number such as 2 6/7 visible as its printed whole number,
numerator and denominator. During the campaign a `/100` divisor repeatedly
failed the numeric-grounding check ("Ungrounded generated numeric literal"),
and no merged module divides by 100.

### Test suppression and mislabeling

A regression test must state and assert the intended legal behavior. Renaming a
test, weakening it, or asserting the current bug is not a repair.

Real example: a test named as an above-ceiling zero-award regression supplied
£180.01 but asserted the top band and a £6 award. The selector still used an
unconditional top-band fallback, so the test preserved the defect while its
name claimed the opposite.

Check: on every re-review, compare the test name, fixture, intermediate
selectors, and final expected award with the printed row. Confirm that the prior
finding changed production behavior. A re-verdict cites the reviewer's own
earlier finding and shows how the new diff resolves it.

## Steer anatomy

A steer is a compact, scheme-specific contract. Keep these sections in this
order.

### Hard rules

List the campaign's mechanical invariants: contiguous verbatim proof atoms,
value-bearing sufficiency, parameterized constants, expression typing, total
band maps including zero, exact repeating decimals, source-verification shape,
self-scoped deferrals, and companion obligations. This prevents known failure
classes from being rediscovered during generation.

### Target and authority

Name the module path, population, award surface, operative source, primary
citation page, and legal delegation or hierarchy. State what must be encoded and
what is out of scope. This keeps the generator from deferring a locally operative
scheme in search of a nonexistent higher-authority value.

### Verified findings

Record findings already checked against corpus bodies: operative year, document
identity, population, maximum rate, structure, and key quotations. Include page
and provision references. These are inputs to generation, not a substitute for
rule-level proof atoms.

### Linkage rule

State the document-specific decision on taper, composed band rate, or
ceiling/`min` form, and quote the sentence that decides it. If the corpus is
silent, record the verified absence and constrain the encode to the printed
award basis.

### Run context

Pin the corpus release and hash, toolchain location, module and companion paths,
gate commands, ledger date, and expected diff scope. Recheck pins immediately
before compiling because campaign releases can move between steer creation and
execution.

## The gate battery

Run the battery after the module is written and again after every semantic fix.

1. `validate`: check schema, expression types, active output shape, scalar
   extraction, source-verification contract, and module compilation.
2. `proof-validate`: check that excerpts are verbatim, contiguous, and sufficient
   for the values and table cells claimed.
3. `companions`: execute parameter, edge, cliff, taper or band, floor, and zero
   cases against the engine.
4. `role-audit`: require zero unresolved flags for proof anchored in the wrong
   population or provision context. Inspect false-positive candidates rather
   than gaming rule names or weakening evidence.
5. `ledger-ratchet`: run after the module exists, add declarations verbatim for
   actual outputs, and require entry count to equal the ceiling.
6. `suite`: run the repository test suite to catch shared-contract regressions.

Verify before ingest. Discovery must resolve an official source, the relevant
program, and the target period before fetching and ingesting. For continuation
schemes, preserve the resolution, incorporated report, base instrument, hashes,
and retrieval timestamps as one closed corpus. Only Full Council adoption passes
the operative-year gate unless another lawful route is affirmatively established.

Keep scope mechanical. A per-authority branch changes its own jurisdiction tree
and the shared pending ledger only. Before review and before landing, compare the
branch with its base and scrub stray files. The ledger declarations must equal
the module outputs and the ceiling arithmetic must be exact.

## Review protocol

Review related scheme families in batches so the reviewer can compare maximum
rates, linkage language, boundary conventions, grids, and operative-year forms.
Return one numbered, evidence-cited verdict block per PR.

Verdicts remain per-PR. One authority's sound encode does not validate another,
and each PR must be independently mergeable. When live checks are unavailable,
mark CI unverified rather than borrowing another PR's state.

For a re-review, cite the reviewer's own prior findings. Inspect the production
rule and the regression test, not only the repair summary. State whether each
finding is resolved, still present, renamed, or suppressed.

Review the full bound source, including neighbouring provisions. Embedded
proof excerpts are a useful index, but cannot reveal a population heading or
qualification omitted from the excerpt. Resolve the release in
`.axiom/toolchain.toml`, then locate its council version in `axiom-corpus` under
`data/corpus/provisions/uk-<council>/manual/<version>.jsonl`. Read the relevant
page rows and their context, and inspect the original official document when a
table or typography affects interpretation. For example, the
[Arun release rows](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/data/corpus/provisions/uk-arun/manual/2026-09-05-arun-council-tax-reduction-2026-2027.jsonl)
show both sides of the band A conflict. Pin the release commit in the review's
source links so a later ingest does not change the evidence being reviewed.

Source and companion gates also do not establish how a module was generated.
Inspect the encoder's required receipts separately. A historical module without
those receipts does not acquire them by passing today's validation or by
changing its citation granularity. Use the documented campaign decision before
representing such a module as compliant with the supervised encoder regime.

The merge gate is `SHIP` plus green CI on the reviewed head. A static `SHIP` with
CI marked unverified is not the merge condition. Any semantic edit after a
verdict requires gates and a new verdict.

## Scaling patterns

### Shared-ledger reconciliation

Every parallel authority branch edits the same pending ledger. On rebase, rebuild
the ledger as the current base entries plus that branch's own declarations. Set
the ceiling to the resulting entry count, check that declarations match the
module outputs, then rerun the ratchet and suite. Do not resolve conflicts by
retaining another branch's stale snapshot.

### Omnibus merge for CI-matrix growth

Adding one root per authority expands the validation matrix. When many
individually reviewed branches would create repeated matrix churn, assemble an
omnibus branch from their reviewed heads. Verify each authority tree is byte-for-
byte equivalent to its reviewed branch, reconcile the ledger once, and require
the omnibus diff to contain only those trees and the ledger. Review the omnibus
for equivalence and scope; do not use it to introduce semantic changes.

### Reland cascade

After an omnibus or another ledger-heavy PR lands, remaining branches are based
on an older ledger and matrix. Rebase each branch onto the new base, reconcile
only its own declarations, rerun the gate battery, and obtain a re-verdict if
the rebase changes semantic content. Process the queue from the new base forward;
each landing becomes the base for the next branch. Stop the cascade on any gate
failure rather than propagating a bad ledger or stale generated artifact.
