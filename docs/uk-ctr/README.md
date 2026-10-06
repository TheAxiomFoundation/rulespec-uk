# UK council tax reduction campaign

This directory is the durable record of the campaign to encode every English
billing authority's working-age council tax reduction (CTR) scheme. It is
enough to continue the campaign without any other material.

- Epic: [rulespec-uk#140](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140)
- Owner (from 2026-09-25): [@vahid-ahmadi](https://github.com/vahid-ahmadi)
- Registry of all 296 councils with statuses: [`councils.csv`](councils.csv)
- Section-level ingest findings (option A′): [`section-ingest.md`](section-ingest.md)
- Encoding method and error classes: [`../uk-council-encoding-playbook.md`](../uk-council-encoding-playbook.md)

Nothing runs automatically for this campaign. Every step below is started by
the owner.

## What the campaign is

Local Government Finance Act 1992 s.13A(2) requires each billing authority in
England to make a council tax reduction scheme, and Schedule 1A sets how it is
made and revised. Pension-age classes are prescribed nationally
(SI 2012/2885, encoded under `uk/`); the working-age scheme is designed by each
council. So there is no single working-age rule: each council's adopted scheme
document is the operative law for its area, and each one is a separate
encoding.

The target population is the 296 English billing authorities in the ONS local
authority district list of April 2025: 63 unitary authorities (E06), 164
districts (E07), 36 metropolitan districts (E08) and 33 London boroughs
including the City of London (E09). Each council gets its own jurisdiction
root, `uk-<slug>/`, and one working-age award-surface module at
`uk-<slug>/policies/<slug>/council-tax-reduction.yaml` with a companion test.
The award surface is the maximum reduction, the income taper or banded
discount grid, the capital limit and tariff income, non-dependant deductions,
minimum-award floors, and the formula that composes them.

## Status on 2026-09-25

| Stage | Councils | Where |
|---|---:|---|
| Encoded and merged | 100 | `uk-<slug>/policies/<slug>/council-tax-reduction.yaml` on `main` |
| Encode PR open | 34 | #308 and #310–#342; all conflict with `main` |
| Ingested and released, not encoded | 24 | corpus release `uk-rulespec-2026-09-07` |
| Ingested, withdrawn from releases | 1 | Shropshire (wrong-year text) |
| Not yet ingested | 137 | discovery, fetch or verification stage |
| **Total** | **296** | |

Corpus side:

- `rulespec-uk` binds corpus release `uk-rulespec-2026-09-07`
  (`.axiom/toolchain.toml`). That release has 191 scopes: 33 national `uk`
  scopes and 158 council scopes, one `manual` scope per council.
- The corpus holds 159 council scopes. The extra one, `uk-shropshire`
  (ingested 2026-07-25), was in release `uk-rulespec-2026-07-26` only. It was
  withdrawn by omission from `uk-rulespec-2026-08-02` onward because its
  operative text turned out to be the 2024/25 default scheme under a 2026/27
  cover (discussed in [axiom-corpus#534](https://github.com/TheAxiomFoundation/axiom-corpus/pull/534)).
  It needs the real 2026/27 text before it goes back into a release.
- The 159 scopes hold 174 source documents: 169 PDF, 3 DOCX (Barking and
  Dagenham, Nottingham, Wakefield) and 2 HTML (Leeds; Broxtowe's adoption
  minutes). Ten scopes hold more than one document: a scheme text plus the Full
  Council adoption record, and sometimes a report used as corroboration.

Registry columns and the status vocabulary are described under
[The registry](#the-registry).

## The encoder-regime issue

The Axiom encoding regime requires every RuleSpec module to come from the
supervised encoder, `axiom-encode encode <corpus citation> --backend codex
--apply`, and to carry the encoder's signed receipt under
`.axiom/encoding-manifests/`. The shared validation workflow states the rule
in its own error text: RuleSpec content must come from `axiom-encode encode
--apply`, and hand-authored modules are rejected.

The campaign did not use that path. Its modules were generated per council
from a scheme-specific brief (verified findings, target, hard rules; see the
playbook's "Steer anatomy") and admitted by the campaign's own gate battery and
cross-family review. As a result:

- `rulespec-uk` has **no** files under `.axiom/encoding-manifests/`. All 100
  merged council modules are unreceipted.
- The 34 open encode PRs are the same class.
- `rulespec-uk` CI does not enforce the regime today. Its
  `repository-checks.yml` sets `run-generated-guard: false` and pins the shared
  workflow `TheAxiomFoundation/.github` at `842c69d` (2026-07-22). The gate that
  rejects unreceipted modules, and that requires a time-boxed
  `.axiom/generated-guard-exception.md` whenever the guard is off, landed in the
  shared workflow on 2026-09-06 (`6c2d9eb`). Bumping the pin past that commit
  forces the decision below: either an exception file, or the guard on.

The corpus side (discovery, fetch, ingest, release cuts, rebinds) is not
RuleSpec content and is unaffected under every option.

## Evidence: the supervised encoder on Arun

On 2026-09-13 the supervised encoder was run three times on Arun without
`--apply`, against release `uk-rulespec-2026-09-06`, and compared with the
campaign's module for Arun (PR #310).

| Run | Citation | Rules | Award surface | Encoder gate |
|---|---|---:|---|---|
| Cold | `.../page-28` | 9 | maximum, bands B–E and capital limit absent | CI fail |
| Repo-augmented, campaign brief as context | `.../page-28` | 10 | same; emitted YAML does not parse | compile fail |
| Cold | whole document | 8 | grid, capital limit and formula present; non-dependant deductions and £1 floor absent | CI fail (sub-paragraph coverage, deferred outputs) |
| Campaign module (#310) | n/a | 21 | complete; atoms on pages 27, 28 and 29 | campaign gates pass |

Why: the encoder hands the model exactly the cited provision row. Council
scopes are ingested as one document row plus one row per page (Arun: 1 + 111),
with no section rows. Arun's award surface spans pages 27–29 (s.19 capital,
s.21 maximum, s.22 non-dependant deductions, s.23 grid) plus Schedule 3 on
page 80, so a page citation starves the model. A document citation reaches
everything but the module is then held to sub-paragraph coverage of all 111
pages. Adding the campaign brief as context did not widen the source; it made
the result worse.

So re-encoding the campaign's councils at page citations cannot reproduce
award-surface modules. That is corpus granularity, not model or prompt quality.
Section-level rows fix the granularity; see [`section-ingest.md`](section-ingest.md).

The document-level run also exposed a real conflict in Arun's scheme, below.

## Options

### A′: section-level ingest, supervised encoder, per-council composition

1. Corpus: re-version each council scope with section rows
   (`extraction.segmentation: labeled_sections` in its corpus manifest), so
   each award-surface component is one citation, e.g. Arun `/19`, `/21`, `/22`,
   `/23`, `/schedule-3`.
2. Encoder: `axiom-encode encode <section citation> --backend codex --apply`
   per component, under the trusted signing supervisor, producing receipted
   modules.
3. Per council, assemble the components into one award surface with a
   composition module (maximum → grid or taper → deductions → award).
4. Use the 134 steered modules (100 merged, 34 open) only as verification
   evidence: expected values and cross-page findings for companion tests. They
   never become content.

Evidence for: the corpus half works with manifest configuration only, proven
on Arun and on Crawley (the two largest heading families, about 90 of the 155
long PDFs). Evidence against: the encoder half is untested; it needs one
section-row version in a signed release before anyone can run
`encode` on `/23`. It is also the largest amount of work: 159 re-versions and
an encode per component.

It is the only option that ends with every module receipted.

### B: documented exception and receipt backfill

Keep the 100 merged modules and merge the 34 open PRs under a written
`.axiom/generated-guard-exception.md` that names them as steered, non-encoder
modules (line 1: the authorizing issue or PR URL; line 2:
`expires: YYYY-MM-DD`). Then backfill receipts through the encoder's signed
re-encode path.

Evidence for: fastest route to 134 of 296. Evidence against: the modules stay
unreceipted until backfilled, and the backfill path emits per-block modules,
not award surfaces. The open draft PRs #269–#303 show that shape for
Wakefield: `uk-wakefield/policies/council-tax-support-scheme-working-age/block-N.yaml`,
beside the existing `uk-wakefield/policies/wakefield/council-tax-reduction.yaml`.
The two layouts would have to be reconciled.

### C: stop at 100

Close the 34 PRs, keep the corpus (159 council scopes) as the asset, and
resume council encoding when A′ tooling exists. Nothing already merged
changes.

## Open questions (owner: @vahid-ahmadi)

### 1. A′, B or C

The campaign's recommendation was A′, with the corpus side continuing under
any option, and no open encode PR merged until this is decided. The first
concrete A′ step is one full cycle on Arun: re-version `uk-arun` with section
rows, cut and publish a release, rebind, then run `axiom-encode encode` on
`uk-arun/manual/council-tax-reduction-scheme-2026-2027/23` without `--apply`.

### 2. Arun band A: 100% or 90%

Arun's adopted 2026/27 scheme prints its discount grid twice with a different
top band. Bands B–E (70/50/30/10%) agree.

| Where | Page | Wording | Band A (£0–£219.99) |
|---|---:|---|---:|
| s.23(2)–(3) | 28 | "The authority has determined that for 2026/27 a discount shall be applied to the maximum council tax reduction determined in section 21 of this scheme in accordance with the following table" | 100% |
| Schedule 3 ¶1 | 80 | "The authority's Council Tax Reduction scheme from 2026/27 shall be calculated on the basis of the following Banded Discount Scheme" | 90% |

Points on each side:

- s.23(4) says "A summary of the entitlement is shown within Schedule 3 of this
  scheme", which reads the schedule as a summary of s.23.
- Schedule 3's own wording is operative ("shall be calculated on the basis
  of"), and the schedule carries rules found nowhere else: ¶7 uprates the
  income bands each year by CPI at 1 October, and ¶8 puts applicants on Income
  Support, income-related ESA or income-based JSA in band A regardless of
  income.

The open PR #310 encodes 100% from page 28, never cites page 80, and encodes
neither ¶7 nor ¶8. The supervised encoder's document-level run took 90%.
Neither flagged the conflict. Options: rule that the operative section
prevails and record the ruling with the encoding, or ask Arun District Council
which figure it applies.

A sweep for the same class (a first band restated on another page with a
different rate) over the 138 council manuals then in the rig found Arun only;
the Harrow hit was a false positive (six per-category grids). It did not cover
the 21 scopes added in `uk-rulespec-2026-09-07`, grids printed as
"N% £0–£X", or DOCX block paths. Rerun it over all 159 scopes before any encode
of those councils.

### 3. Smaller calls

- **Hyndburn** (not ingested): the scheme PDF says 30% working-age
  contribution on page 9 and 20% in §59A.1. The 13 November 2025 Council minutes
  may settle it but are not retrievable without a browser. Ingest only with the
  operative figure established, adding the adoption record as a second
  document.
- **Shropshire**: withdrawn from releases because the ingested text is the
  2024/25 default scheme under a 2026/27 cover. Find the adopted 2026/27 scheme
  or amendment with its values, ingest it as a new version, then include it in
  a cut.
- **Bedford**: the ingested document yielded 16 provisions against 65–254 for
  full schemes. Confirm it is the full scheme and not a summary before
  encoding.
- **Wakefield**: the draft signed-backfill PRs #269–#303 add per-block modules
  that overlap the merged `uk-wakefield` module. Decide which layout stays.

## How to continue

### Under every option: the corpus pipeline

CORPUS-RECIPE-PLACEHOLDER

### Under A′

Prove the whole chain on one council before scaling.

1. **Arun, corpus.** Add the tested `extraction` block
   ([`section-ingest.md`](section-ingest.md#arun-family-a-the-extraction-block))
   to Arun's corpus manifest, re-extract under a new version from the retained
   PDF, and land it through the corpus pipeline above: signed ingest manifest,
   citation-path ratchet, retired page identities recorded as `split` mapping
   events, review, merge.
2. **Arun, release.** Cut, publish, mirror and activate a release containing
   the section-row version, then rebind `rulespec-uk`.
3. **Arun, encoder.** Under the trusted signing supervisor, run
   `axiom-encode encode uk-arun/manual/council-tax-reduction-scheme-2026-2027/23 --backend codex`
   without `--apply`, and read the encoder's own gates. Then `/21`, `/19`,
   `/22` and `/schedule-3`. The steered module in #310 is the reference for
   expected values and companion cases, not content.
4. **Arun, composition.** Design the per-council composition that wires the
   component modules into one award (maximum → grid → deductions → floor).
   No `rulespec-*` repository has a composition module yet, and whether the
   generated-content guard accepts one is not yet tested; resolve both on
   Arun. Settle open question 2 first.
5. **Crawley.** Repeat for the family-B template (`/1`, `/58`), with the
   pattern fixes in [`section-ingest.md`](section-ingest.md#crawley-family-b-the-template-scheme).
6. **Scale by heading family**, A and B first (about 90 PDFs), then C–H. Each
   council: pick the family, set `start_page` and the running-header drop,
   extract, check labels against the contents page, re-version.
7. **Retire the steered modules** as each council's receipted composition
   lands, and close the corresponding open PR.

### Under B

1. Open an issue that authorizes the exception and lists the steered modules
   (the 100 on `main` and the 34 in PRs).
2. Add `.axiom/generated-guard-exception.md`: line 1 the issue URL, line 2
   `expires: YYYY-MM-DD`, then the list or a pointer to it. With the current
   shared-workflow pin CI does not read this file; it becomes mandatory the
   moment the pin moves past `6c2d9eb`, so add it before bumping.
3. Bring each of #308 and #310–#342 up to date one at a time, because every
   merge changes the shared ledger:
   - merge `origin/main` into the branch (do not rebase);
   - resolve `oracle-coverage-pending.yaml` as `main`'s ledger plus this
     council's own declarations (playbook, "Shared-ledger reconciliation");
   - rerun the gate battery; the PRs were generated against release
     `uk-rulespec-2026-09-06`, and every council scope in it is unchanged in
     `uk-rulespec-2026-09-07`, so citations still resolve;
   - get an independent semantic review; the last recorded review state of
     each PR is in [`open-prs.md`](open-prs.md);
   - merge with a merge commit once `validate / validate` is green.
4. Settle Arun (open question 2) before #310 merges.
5. Backfill receipts through the encoder's signed re-encode path, and decide
   how its per-block modules relate to the award-surface modules.

### Under C

1. Close #308 and #310–#342 with a comment linking this README.
2. Keep corpus work optional: new scopes remain useful for A′ later.
3. Update [`councils.csv`](councils.csv) statuses (`encode-pr-open` →
   `ingested`).

## The registry

[`councils.csv`](councils.csv) has one row per English billing authority (296),
in ONS code order. Stage statuses (`encoded` to `ingested-unreleased`) were
reconciled on 2026-09-25 against `main`, the open PRs, and the corpus; the
pre-ingest statuses are the campaign's last recorded discovery results.

| Column | Meaning |
|---|---|
| `ons_code`, `name` | ONS local authority district code and name (April 2025) |
| `jurisdiction` | the `rulespec-uk` and corpus root, `uk-<slug>` |
| `status` | see below |
| `pr` | open encode PR number, if any |
| `corpus_version` | the scope version in `uk-rulespec-2026-09-07` (or the latest ingested version) |
| `heading_family` | heading family of the scope's scheme PDF, for section ingest ([`section-ingest.md`](section-ingest.md)) |
| `scheme_url` | the ingested scheme text's source URL; before ingest, the best-known URL |
| `other_source_urls` | adoption records and other documents in the scope, or other useful URLs before ingest (space-separated) |
| `notes` | caveats, blockers and the next step |

Statuses, in pipeline order:

| Status | Meaning |
|---|---|
| `encoded` | module merged on `main` |
| `encode-pr-open` | module in an open PR (`pr`) |
| `ingested` | scope in the bound corpus release; no module yet |
| `ingested-unreleased` | scope in the corpus but in no current release |
| `continuation-pair-ready` | a Full Council resolution continues an earlier scheme; both documents in hand, not yet ingested |
| `continuation-ready` | continuation established; documents to assemble |
| `continuation-needs-linkage` | the chain from the resolution to the exact scheme text is not yet established |
| `continuation-case` | continuation suspected; resolution not yet found |
| `amendment-case-ready` | an amending resolution plus base scheme in hand |
| `amendment-case` | amendment suspected; documents not yet found |
| `amendment-needs-values` | amendment found but the amended values are not in any document yet in hand |
| `rendition-case` | the PDF's text layer is unusable (for example image-only pages) |
| `discovered-source-conflict` | the scheme text contradicts itself on an award value |
| `discovered-prior-year` | only a pre-2026/27 text found |
| `discovered-summary-only` | only a summary or leaflet found |
| `discovered-pension-only-needs-working-age-doc` | only pension-age material found |
| `discovered-html` | scheme published as HTML pages |
| `discovered-fetch-blocked` | the document URL is known but refuses automated download |
| `browser-case` | the document must be located or downloaded in a real browser |
