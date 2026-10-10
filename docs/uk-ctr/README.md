# UK council tax reduction campaign

This directory records the campaign to encode every English billing authority's
working-age council tax reduction (CTR) scheme and how to continue it.

- Epic and decision record: [rulespec-uk#140](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140).
- Campaign owner: [@vahid-ahmadi](https://github.com/vahid-ahmadi), as recorded in
  [the 2026-09-28 hand-off](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-5872231649).
- Council registry: [`councils.csv`](councils.csv).
- Section-level ingest evidence: [`section-ingest.md`](section-ingest.md).
- Encoding and review method: [`../uk-council-encoding-playbook.md`](../uk-council-encoding-playbook.md).

## Scope

England's working-age CTR schemes are adopted by individual billing authorities
under [LGFA 1992 s.13A](https://www.legislation.gov.uk/ukpga/1992/14/section/13A)
and [Schedule 1A](https://www.legislation.gov.uk/ukpga/1992/14/schedule/1A).
Pension-age requirements are prescribed nationally by SI 2012/2885.
The campaign registry contains 296 English authorities from the ONS April 2025
local authority district list: 63 E06, 164 E07, 36 E08 and 33 E09 codes
(recounted from the registry on 2026-10-09).

The target layout for each council is a jurisdiction root, `uk-<slug>/`, and a
working-age module at
`uk-<slug>/policies/<slug>/council-tax-reduction.yaml`, with a companion test.
Its award surface covers the maximum reduction, taper or band grid, capital
limit and tariff income, non-dependant deductions, minimum award and the
formula connecting them.

**Scotland needs no per-council modules.** It has one national CTR scheme,
with working-age rules in SSI 2021/249 and pension-age rules in SSI 2012/319.
[Issue #442](https://github.com/TheAxiomFoundation/rulespec-uk/issues/442), read
on 2026-10-09, tracks the Scottish composite gap: wire regulations 13–14 to
regulation 79's daily maximum, recover the omitted regulation 79(2) band E–H
formula in the corpus, correct the period label on regulation 13's taper
amount, and resolve pension-age deferrals. Scotland's taper value is distinct
from the English periodisation errors below: it correctly applies the daily
percentage to weekly excess against a daily maximum; its period label needs
correction. Scottish composition belongs to #442, outside this council registry.

## Status measured on 2026-10-09

The local `HEAD`, `origin/main` and GitHub's `main` all resolve to `1c1101c`.
Tracked module paths were counted with `git ls-files`; open council PRs were
queried read-only with:

```bash
gh pr list -R TheAxiomFoundation/rulespec-uk --state open --search CTR \
  --limit 1000 --json number,title,files,mergeable,statusCheckRollup
```

Only PRs adding a council's `council-tax-reduction.yaml` count as council
encoding PRs; the worklist PR returned by the search does not.

| Stage | Councils | Evidence and measurement date |
|---|---:|---|
| Module on main | 100 | Tracked module paths at `1c1101c`, 2026-10-09 |
| Open wave-11 encoding PR | 34 | GitHub query, 2026-10-09: #308 and #310–#342 |
| Ingested, no module or open encoding PR | 25 | Bound selector rechecked 2026-10-09: 24 scopes; historical 2026-09-28 record: Shropshire outside the release |
| Not ingested in the campaign snapshot | 137 | 2026-10-09 set difference against the bound selector and historical Shropshire record |
| **Total** | **296** | Registry identities, recounted 2026-10-09 |

The main-module and open-PR counts are unchanged from the 2026-09-28 report.
The [bound selector](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/manifests/releases/uk-rulespec-2026-09-07.json)
was reread on 2026-10-09: its 191 scopes comprise 33 national scopes and 158
council scopes, including every merged and open-PR council. All recorded
released versions in `councils.csv` match it. The bound release remains
`uk-rulespec-2026-09-07` in [the toolchain pin](../../.axiom/toolchain.toml).
Adding the historically ingested Shropshire scope gives the retained
159-council snapshot. These figures remain unchanged from 2026-09-28. The
137 figure describes councils outside this snapshot, rather than a fresh query
of live corpus ingestion. Discovery findings and Shropshire’s status retain
their 2026-09-28 date; verify them before new work. The historical section
survey and document counts are in [`section-ingest.md`](section-ingest.md).

All 34 council PRs report `CONFLICTING` on 2026-10-09. The same query shows
22 with no attached check results and 12 with attached results; this does not
establish that a PR never ran CI or that its current head passes. Reconcile the
shared `oracle-coverage-pending.yaml` ledger, update the corpus pin and require
fresh checks on each reviewed head before landing.

## The encoder-regime decision

Measured on 2026-10-09, `git ls-files '.axiom/encoding-manifests/**'` returns
**zero encoding receipts**. The 100 merged council modules therefore have no
tracked receipts. The hand-off on #140 identifies these and the open wave as
campaign encodes produced outside the supervised encoder path.

The [current workflow](../../.github/workflows/repository-checks.yml) pins the
shared validation workflow at `842c69d` and sets `run-generated-guard: false`.
The [shared workflow at `6c2d9eb`](https://github.com/TheAxiomFoundation/.github/blob/6c2d9eb/.github/workflows/validate-rulespec.yml),
read on 2026-10-09, requires supervised `axiom-encode encode --apply` content
when the guard is enabled, or a reviewed, dated exception when it is disabled.
The existing [migration test](../../tests/test_repository_layout.py)
also asserts that the encoding-manifest directory contains no JSON files.
A route that introduces newly supervised receipts must reconcile this empty-
directory assertion with the new receipt contract in a separate reviewed
change; generating receipts alone will not pass the current suite.

That later guard contract requires an authorizing issue or PR URL on line 1
of `.axiom/generated-guard-exception.md` and `expires: YYYY-MM-DD` on line 2,
with a date that has not expired in UTC. A workflow upgrade needs a decision
about the existing unreceipted content.

The 2026-09-13 Arun pilot explains the granularity problem. A page citation
omitted award components on other pages; adding repository context did not
supply those provisions. A whole-document citation reached more components
but failed the encoder's coverage gates. These are retained pilot findings,
not a fresh encoder run. The retained pilot recorded:

| Input and context | Rules emitted | Recorded result |
|---|---:|---|
| Arun page 28, source only | 9 | Missing maximum, later bands and capital limit; encoder gates failed |
| Arun page 28, repository context added | 10 | Same coverage gaps; emitted YAML failed compilation |
| Arun whole document, source only | 8 | Grid, capital limit and formula present; deductions and minimum missing; coverage gates failed |
| Campaign module in #310, comparison only | 21 | Campaign gates passed; the band A source conflict remained unresolved |

Section ingest was demonstrated on Arun and Crawley; section-citation encoding
and composition still need a full pilot.

### A′: section ingest and supervised re-encoding

Re-version council corpus scopes with `extraction.segmentation: labeled_sections`,
encode each award component through the supervised encoder, and compose the
resulting modules into a council award. Use earlier modules as comparison
material after correcting known errors; independently derive expected awards
from the source rather than copying their tests.

The corpus spike succeeded with manifest configuration on Arun and Crawley.
Their heading families A and B contain 90 of the historical survey's 169 PDFs,
across 155 PDF-sourced council scopes. Other families need configuration and
coverage checks. The encoder and composition steps remain unproven for this
campaign; prove them before scaling. See [`section-ingest.md`](section-ingest.md).

### B: reviewed exception and supervised backfill

Retain existing modules and consider landing corrected open PRs under an
explicit, time-limited exception. Record the covered modules, authority and
expiry, then backfill through supervised re-encoding. Do not equate an exception
with an encoding receipt, or promise receipts can be attached to unchanged
campaign output.

The draft Wakefield PRs #269–#303 remain open on 2026-10-09 (read-only
`gh pr list --state open --search Wakefield`). Their per-block modules overlap
the existing award-surface module, illustrating the layout and composition
question that backfill must resolve. This route retains useful work sooner,
but still needs source review, defect repairs and a demonstrated backfill path.

### C: pause further council encoding

Keep the 100 modules already on main, close or defer the 34 open encoding PRs,
and retain the corpus and findings for later section-level work. Continue to
repair known defects in merged modules. This option does not resolve the
receipt gap; reconsider it before adopting the later generated-content guard.

## Open questions

### 1. A′, B or C

@vahid-ahmadi owns this decision under the public hand-off on #140. Record the
chosen route and the disposition of existing modules and open PRs there.
The retained campaign recommendation is to pilot A′ before scaling; that is
an evidence-based proposal, not a decision already made by the new owner.

### 2. Arun band A: 100% or 90%

The retained source review found a conflict in the adopted 2026/27 scheme:

| Provision | Page | Band A (£0–£219.99) |
|---|---:|---:|
| Section 23(2)–(3) | 28 | 100% |
| Schedule 3 paragraph 1 | 80 | 90% |

Bands B–E agree at 70%, 50%, 30% and 10%. Section 23(4) describes the schedule
as a summary, but Schedule 3 also contains operative rules: paragraph 7's CPI
uprating and paragraph 8's treatment of specified passporting benefits.
The source pointers and proposed section citations are in
[`section-ingest.md`](section-ingest.md#aruns-award-surface-as-citations).
The [public review of #310](https://github.com/TheAxiomFoundation/rulespec-uk/pull/310)
raises the unresolved adoption evidence. Resolve the operative band A with the
Full Council adoption record or council clarification, and record the ruling
with the encoding. Neither the pilot's 90% result nor the PR's 100% result
settles the conflict.

The historical duplicate-grid sweep covered 138 manuals, before the next
21 scopes were added. Its Arun-only result excluded some grid layouts and
DOCX blocks. Repeat the check over the full bound inventory before encoding.

### 3. Known correctness and source blockers

The tracked modules at `1c1101c` still contain the periodisation errors reported
on [#140](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-5845299202):
`uk-oldham` applies the daily 2 6/7% coefficient to annual excess, and
`uk-east-hertfordshire` applies it to weekly excess before scaling the award.
Both withdraw support at one-seventh of the intended same-period 20% rate.
Their companion expectations reproduce the error. Repair with independently
derived period invariants and differential checks against the national rules.

`uk-babergh` scales a daily 20% coefficient into an effective 140% weekly
taper; `uk-ipswich` uses 20% on same-period excess despite the same quoted
scheme wording. Establish the operative period interpretation before changing
either, and apply the ruling consistently to `uk-guildford`. The
[playbook](../uk-council-encoding-playbook.md) describes the review checks.
These findings were rechecked in the tracked formulas on 2026-10-09.

Other retained discovery blockers require renewed source verification:

- **Hyndburn:** conflicting working-age contributions in the scheme; obtain the
  adoption record and establish the operative value before ingest.
- **Shropshire:** the recorded text is a prior-year default scheme beneath a
  newer cover; obtain the actual operative scheme before releasing it again.
- **Bedford:** the retained discovery record identifies an adopted default
  scheme with local amendments (paragraphs 1.2 and 3.1), rather than a summary.
  Verify that adoption evidence, then encode the incorporated SI 2012/2886
  provisions together with Bedford’s operative amendments.
- **Wakefield:** settle how supervised per-block modules compose into or replace
  the existing award-surface module.

## How to continue

### Under every option: source and corpus work

1. Select a council from `councils.csv`. Verify the official working-age scheme,
   target year and lawful adoption; retain the exact incorporated scheme,
   resolution and amendments, source URLs, hashes and retrieval dates. A draft,
   summary, cover year or pension-only instrument is insufficient.
2. In `axiom-corpus`, create or update a document manifest and extract into a new
   immutable scope version. For continuation schemes, preserve the adoption
   record and base instrument together. Check source references, coverage and
   citation identities; section re-versioning also needs explicit mappings
   from retired page identities.
3. Review the corpus change and pass its checks. Cut a new named selector with
   exact scopes, preflight it, publish and verify the signed release, and
   preview its scope effects before activation through the protected workflow.
   Merging corpus files alone does not publish a release.
4. Rebind `rulespec-uk` to that release's name and signed content digest in
   `.axiom/toolchain.toml`, then verify all referenced citations and run checks.
   Update registry statuses only when their evidence changes.

Use the corpus [ingestion runbook](https://github.com/TheAxiomFoundation/axiom-corpus/blob/3858e928/docs/agent-ingestion-runbook.md)
and [named-release contract](https://github.com/TheAxiomFoundation/axiom-corpus/blob/3858e928/docs/named-release-publication.md)
(read on 2026-10-09) for the concrete commands and publication boundary.

### Under A′

1. Settle Arun's source conflict. Re-version its scope with the tested
   [extraction block](section-ingest.md#arun-family-a-the-extraction-block),
   verify every label, and put it in a signed release bound by this repository.
2. Pilot without applying output:
   `axiom-encode encode uk-arun/manual/council-tax-reduction-scheme-2026-2027/23 --backend codex`.
   Inspect its gates, then repeat for `/19`, `/21`, `/22` and `/schedule-3`.
3. Demonstrate supervised application with receipts and a composition that
   connects maximum, grid, deductions and floor. Test against independently
   derived awards and the resolved adoption evidence.
4. Repeat on Crawley after repairing the section-label misses described in the
   spike, including minimum-award section 57A; encode the maximum, minimum,
   deductions and taper as well as the introduction. Scale by heading family only after both complete cycles pass.
5. Replace the superseded council module as the receipted composition lands;
   close or update the corresponding open PR and registry entry.

### Under B

1. Obtain the reviewed exception and record its scope and expiry before moving
   to a workflow that requires it.
2. Update each council PR onto current main according to the hand-off on #140;
   reconcile the ledger as current main plus only that council's declarations,
   with the ceiling equal to the resulting entry count.
3. Check citations against the bound release, repair semantic findings, and
   require fresh gates and independent source review on the proposed head.
   Land sequentially because each merge changes the shared ledger.
4. Pilot supervised receipt backfill and composition on one council, resolve
   layout overlap, then expand before the exception expires.

### Under C

Record the pause and PR dispositions on #140. If a PR closes without merging,
return its council to the appropriate ingested status. Keep the corpus evidence
and discovery blockers, repair merged defects, and define the evidence needed
to resume.

## The registry

`councils.csv` has one row per English authority in ONS code order. Module and
open-PR statuses were reconciled on 2026-10-09. Ingestion, source URLs and
heading-family observations retain the campaign snapshot dates in the notes;
verify them before a new ingest. The repository's smaller
[`data/councils/registry.csv`](../../data/councils/registry.csv) keeps its original
identity and source fields, with only observed module/PR statuses updated.

| Column | Meaning |
|---|---|
| `ons_code`, `name` | ONS April 2025 local authority district identity |
| `jurisdiction` | `uk-<slug>` repository and corpus root |
| `status` | Pipeline stage below |
| `pr` | Current open council encoding PR number, if any |
| `corpus_version` | Recorded scope version; provenance dates are in `notes` |
| `heading_family` | Historical scheme-PDF family from the section survey |
| `scheme_url` | Recorded official source or best-known discovery URL |
| `other_source_urls` | Adoption records or additional sources, space-separated |
| `notes` | Evidence dates, source blockers and next steps |

| Status | Meaning |
|---|---|
| `encoded` | Council module on main; does not imply a receipt or correct award |
| `encode-pr-open` | Council module in the open PR identified in `pr` |
| `ingested` | Recorded in the bound release, without a module or open encode PR |
| `ingested-unreleased` | Recorded corpus scope outside the bound release |
| `continuation-pair-ready` | Continuation resolution and base scheme located |
| `continuation-ready` | Continuation established; documents still to assemble |
| `continuation-needs-linkage` | Resolution not yet linked to the exact scheme |
| `continuation-case` | Continuation suspected; resolution still to find |
| `amendment-case-ready` | Amending resolution and base scheme located |
| `amendment-case` | Amendment suspected; documents still to find |
| `amendment-needs-values` | Amendment found; operative amended values missing |
| `rendition-case` | Source text layer unusable |
| `discovered-source-conflict` | Source contradicts itself on an award value |
| `discovered-prior-year` | Only an earlier-year source located |
| `discovered-summary-only` | Only a summary or leaflet located |
| `discovered-pension-only-needs-working-age-doc` | Working-age source missing |
| `discovered-html` | Source published as HTML |
| `discovered-fetch-blocked` | Known official URL refuses download |
| `browser-case` | Source needs browser discovery or retrieval |
