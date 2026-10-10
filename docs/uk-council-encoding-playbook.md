# Statutory and scheme rule encoding playbook

This playbook records the method used in the UK council-tax-reduction campaign
for encoding statutory and scheme rules. It is offered as a transferable
pattern for other jurisdiction lanes, including DK, US, and SOUTHMOD; each
lane's authority model, corpus contracts, and gate battery require separate
validation before the method is treated as established there. Replace
council-specific labels with the authority, instrument, program, and period
relevant to the lane.

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

The campaign provides current examples of this failure. Rechecked on
2026-10-09 at `1c1101c`,
[Oldham](../uk-oldham/policies/oldham/council-tax-reduction.yaml) applies
`(2 + 6/7) × 0.01` directly to an annual excess, and
[East Hertfordshire](../uk-east-hertfordshire/policies/east-hertfordshire/council-tax-reduction.yaml)
applies the same rate to a weekly excess. Both call the parameter a weekly
rate. Their companion expectations reproduce that calculation, so a passing
companion suite cannot establish period consistency. The public review on
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

Rechecked at `1c1101c` on 2026-10-09,
[Babergh](../uk-babergh/policies/babergh/council-tax-reduction.yaml) subtracts
20 percent of a weekly excess from a daily maximum, giving an effective
same-period taper of 140 percent.
[Ipswich](../uk-ipswich/policies/ipswich/council-tax-reduction.yaml) applies
20 percent to annual excess against an annual maximum. The
[maintainer's issue reply](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-5872231649)
identifies the identical scheme wording as an unresolved interpretation;
[Guildford](../uk-guildford/policies/guildford/council-tax-reduction.yaml)
also applies a 20 percent rate to annual excess and needs to be considered in
that adjudication. Formula agreement or familiar rates cannot settle the legal
reading. These observations document an open correction, not a module repair.

Arun illustrates a different conflict: s.23(3) prints band A at 100 percent,
while Schedule 3 paragraph 1 prints 90 percent for the same scheme year. Keep
both citations, establish the adopted instrument and any final amendment, and
record the controlling-source decision. The [campaign hand-off](uk-ctr/README.md)
and [section citation map](uk-ctr/section-ingest.md) preserve the unresolved
question and the evidence needed to continue.

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
