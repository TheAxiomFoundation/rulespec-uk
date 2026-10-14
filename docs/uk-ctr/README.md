# UK council tax reduction campaign

This directory records the campaign to encode every English billing authority's
working-age council tax reduction (CTR) scheme and how to continue it.

- Epic and decision record: [rulespec-uk#140](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140)
  (assigned to [@vahid-ahmadi](https://github.com/vahid-ahmadi); the maintainer
  took the route and the wave-11 calls on
  [10 October 2026](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-6102095622)).
- The route, decided 2026-10-11: [below](#the-route).
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

Each council has a jurisdiction root, `uk-<slug>/`. Its award surface covers
the maximum reduction, taper or band grid, capital limit and tariff income,
non-dependant deductions, minimum award and the formula connecting them. The
100 merged modules put the whole surface in one module at
`uk-<slug>/policies/<slug>/council-tax-reduction.yaml`, with a companion test.
That is the legacy layout. On the [chosen route](#the-route) the encoder writes
one module per section citation, and each council's award is assembled under
`uk-<slug>/programs/` ([design questions](#design-questions-the-route-has-to-answer)).
`tests/test_council_registry.py` recognises only the legacy path as `encoded`,
so the first council finished on the route also needs that test and the
registry's status rule updated.

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

## The route

On 2026-10-11 the open question this document used to pose (A′, B or C,
below) was settled in favour of the supervised encoder. As each closing
comment on the wave-11 PRs says (for example
[#310](https://github.com/TheAxiomFoundation/rulespec-uk/pull/310#issuecomment-6110687103)):

- Council CTR modules in this repository will come from the supervised
  encoder once rulespec-uk is on the signed encoder workflow. Agent-written
  council modules will not land.
- The 34 wave-11 encode PRs (#308 and #310–#342) were closed without merging.
- Their work is kept as annotated reference tags: an `-original` tag for each
  of the 34 PR heads, and a `-repaired` tag for the 8 that had a repair round
  with hand-derived companion cases (Arun, Bournemouth, Christchurch and Poole,
  Burnley, Charnwood, Crawley, Eastleigh, Mid Suffolk, Redditch). They are
  named `oracle/uk-ctr/wave11/<jurisdiction>/pr<N>-original` or
  `…-repaired`. The tag `oracle/uk-ctr/main-2026-10-11` marks `main` at
  `c65fd7df`, which holds the 100 merged council modules with the #447 and #449
  repairs.
- Those tags are references, not ground truth. Encoder output for a council
  is compared with them on a shared household grid, and every disagreement is
  adjudicated against the scheme text.

The encoder cannot reach a council's award surface from today's page rows
(see [the Arun pilot](#evidence-the-supervised-encoder-on-arun)). So the route
re-ingests each council scheme with section rows, encodes the award-surface
sections, and assembles them per council. That is option A′'s design. The
corpus half has been demonstrated on Arun and Crawley, though not yet signed or
released, and the known extraction defects are listed in
[`section-ingest.md`](section-ingest.md). The encoder and assembly halves are
not yet proven. [How to continue](#how-to-continue) gives the steps.

## Status on 2026-10-14

| Stage | Councils | Evidence |
|---|---:|---|
| Module on `main` | 100 | `uk-<slug>/policies/<slug>/council-tax-reduction.yaml`; no encoding receipts |
| Ingested and released, no module | 58 | 24 never encoded, plus the 34 closed wave-11 councils; all in `uk-rulespec-2026-09-07` |
| Ingested, withdrawn from releases | 1 | Shropshire: the ingested text is the 2024/25 default scheme under a 2026/27 cover |
| Not ingested | 137 | discovery, fetch or verification stage; see `notes` in [`councils.csv`](councils.csv) |
| **Total** | **296** | |

No council encode PR is open.

Corpus side:

- `rulespec-uk` binds release `uk-rulespec-2026-09-07`
  ([`.axiom/toolchain.toml`](../../.axiom/toolchain.toml)). Its 191 scopes are
  33 national `uk` scopes and 158 council scopes.
- `axiom-corpus` holds 159 council scopes. Since
  [axiom-corpus#774](https://github.com/TheAxiomFoundation/axiom-corpus/pull/774)
  (2026-09-30; tooling in #769) their bytes live outside git. Each scope is pinned by a lock
  file, `.axiom/corpus-locks/uk-<slug>/manual/<version>.json`, and fetched with
  `axiom-corpus-ingest corpus fetch`.
- 107 council scopes have their extraction manifest committed in
  `.axiom/corpus-manifests/`. The other 52 (for example Ashford, Blackpool and
  Bristol) do not. For 51 of them the signed ingest manifest records an
  extraction command that read one; Kingston's records a release promotion
  instead. Rebuild the manifest from the scope's inventory before re-versioning
  one of those.

## Continuous integration and receipts

Measured at `main` `3d0ecdc8` on 2026-10-14:

- The generated-RuleSpec guard is on
  ([#459](https://github.com/TheAxiomFoundation/rulespec-uk/pull/459),
  2026-10-12). It checks the modules a pull request changes. The 100 council
  modules on `main` carry no receipt and stay as they are until a PR changes
  one. From then on, the change has to come from the encoder, and for these
  unreceipted modules there is no supported path yet (see
  [replacing a merged module](#design-questions-the-route-has-to-answer)).
- The shared validation workflow is pinned at `b36f534`
  ([#464](https://github.com/TheAxiomFoundation/rulespec-uk/pull/464)). The
  encoder is still pinned at `c326d1ac` (0.2.1337).
  [`.axiom/workflow-toolchain.toml`](../../.axiom/workflow-toolchain.toml)
  mirrors those pins, and CI fails if it drifts
  ([#461](https://github.com/TheAxiomFoundation/rulespec-uk/pull/461)).
- There are no files under `.axiom/encoding-manifests/`.
  `test_legacy_applied_manifests_are_not_kept_as_migration_inputs` in
  `tests/test_repository_layout.py` fails if any manifest JSON exists, and
  `tests/test_encoding_manifest_prohibition.py` pins that behaviour; both change
  at the re-pin. A canonical receipt layout is staged in
  `tests/test_encoding_manifest_retirement_layout.py`.
- The migration's remaining step is an encoder re-pin whose guard verifies
  receipts, which retires the prohibition. Until it lands, no encoder output
  can be committed here.
- The same re-pin is needed before rulespec-uk can bind any newer corpus
  release. Every release cut now points at a corpus commit with lock files, and
  the shared workflow at `b36f534` then requires an encoder with `corpus-fetch`
  ([axiom-encode#1742](https://github.com/TheAxiomFoundation/axiom-encode/pull/1742),
  2026-10-10), which `c326d1ac` predates.

## Evidence: the supervised encoder on Arun

The 2026-09-13 Arun pilot explains the granularity problem. A page citation
omitted award components on other pages; adding repository context did not
supply those provisions. A whole-document citation reached more components
but failed the encoder's coverage gates. These are archival pilot records from
the campaign's working notes, not a fresh encoder run; their run artifacts are
not published, so treat the counts as reported rather than reproducible. The
retained pilot recorded:

| Input and context | Rules emitted | Recorded result |
|---|---:|---|
| Arun page 28, source only | 9 | Missing maximum, later bands and capital limit; encoder gates failed |
| Arun page 28, repository context added | 10 | Same coverage gaps; emitted YAML failed compilation |
| Arun whole document, source only | 8 | Grid, capital limit and formula present; deductions and minimum missing; coverage gates failed |
| Campaign module in #310, comparison only | 21 | Campaign gates passed; the band A source conflict remained unresolved |

The mechanism, read from `axiom-encode` (unchanged between the pinned
`c326d1ac` and later `main`): the encoder's source text for a citation is that
provision row's body. A row with no body of its own, such as a document row,
is composed from all of its descendants. Repository context is added beside
the source and never widens it.

### Options weighed before the decision

From 2026-09-13 to 2026-10-11 the campaign weighed three options:

- **A′**: re-ingest by section, encode through the supervised encoder, and
  compose per council. The chosen route takes this design.
- **B**: land the steered PRs under a written, time-limited exception to the
  encoder-only rule and backfill receipts later. Not adopted.
- **C**: stop council encoding at the 100 merged modules. Not adopted.

## Open questions and known blockers

### Arun band A: ruled 100%

Arun's adopted 2026/27 scheme prints band A twice:

| Provision | Page | Band A (£0–£219.99) |
|---|---:|---:|
| Section 23(2)–(3) | 28 | 100% |
| Schedule 3 paragraph 1 | 80 | 90% |

Bands B–E agree at 70%, 50%, 30% and 10%. Section 23(4) describes the
schedule as a summary. Schedule 3 also carries rules found nowhere else:
paragraph 7's CPI uprating of the bands and paragraph 8's band A for
applicants on specified passporting benefits.

The maintainer ruled on 10 October 2026 that band A is **100%**, following
s.23(3). An Arun encoding applies the ruling, cites both provisions, records
the ruling with the encoding, and still encodes paragraph 8 and records
paragraph 7's uprating rule. The
[playbook](../uk-council-encoding-playbook.md#contradictory-source-provisions-and-related-schemes)
records it with the Babergh ruling. A reply from the council would be recorded
under the playbook's
[publisher-confirmation rules](../uk-council-encoding-playbook.md#publisher-confirmations).

Still open for Arun: whether the grid printed "for 2026/27" in s.23 already
reflects paragraph 7's CPI uprating. The repaired reference module
(`oracle/uk-ctr/wave11/uk-arun/pr310-repaired`) encodes the printed figures and
records the uprating as an open question. Settle it before comparing encoder
output with that module.

The historical duplicate-grid sweep (an archival record; its run artifacts are
not published) covered 138 manuals, before the next 21 scopes were added. Its
Arun-only result excluded some grid layouts and DOCX blocks. Repeat the check
over all 159 council scopes before encoding.

### Design questions the route has to answer

- **Assembly.** Encoder modules are named after their citation, e.g.
  `uk-arun/policies/council-tax-reduction-scheme-2026-2027/23.yaml`. Per-council
  assembly belongs in `uk-<slug>/programs/` as an axiom-compose ProgramSpec, as
  [`uk/programs/universal-credit/fy-2026-27.yaml`](../../uk/programs/universal-credit/fy-2026-27.yaml)
  does for Universal Credit. The shared workflow's pre-check requires every
  ProgramSpec import to resolve to an existing encoded module, and allows only
  the literals 0, 1 and 12, so amounts, rates and period conversions (days per
  week, days in the year) must come from encoded modules. Arun's maximum is
  daily (A/B) while its grid and minimum award are weekly, so its assembly
  depends on those conversions. The supervised guard does not treat
  `programs/` as encoder output. Nothing exempts a hand-assembled composition
  module under `policies/`.
- **Replacing a merged module.** One UK release cannot carry two versions of
  the same document (see [`section-ingest.md`](section-ingest.md#re-versioning-a-scope-with-section-rows)).
  Re-versioning a council to section rows therefore removes the page rows its
  merged module cites. 262 files cite council page rows: the 98 module files
  and 164 vendored corpus copies under `uk-<slug>/data/corpus/` (82 councils),
  which go stale at the re-version. Leeds and Wakefield cite block rows. The
  rebind that brings a council's section rows must also replace or retire that
  council's module, and today there is no supported way to do that:
  - Under the guard, deleting or changing a module needs a changed receipt
    covering it (`guard_generated_change_issues` in `axiom-encode` at
    `c326d1ac`).
  - `axiom-encode retire` records signed deletions, but only for a module
    covered by an existing signed encode manifest (`cmd_retire`), and none of
    the 100 council modules has one.
  - On `axiom-encode` `main`, `encode --apply --replace-rulespec-path`
    regenerates a module at an existing path.

  The options, for a maintainer decision: after the encoder re-pin, replace
  each module with `--replace-rulespec-path` before the rebind removes its page
  rows; change the encoder so it can retire unreceipted modules; or take a
  reviewed guard exception (`.axiom/generated-guard-exception.md`: issue or PR
  URL on line 1, `expires: YYYY-MM-DD` on line 2) for the retirements. Settle
  this before re-versioning any encoded council.
- **Wakefield.** The 35 draft signed-backfill PRs (#269–#303) add per-block
  modules beside the merged award-surface module. Decide which layout stays.

### Source blockers

- **Hyndburn:** the scheme states two different working-age contributions.
  Obtain the adoption record and establish the operative value before ingest.
- **Shropshire:** the recorded text is a prior-year default scheme beneath a
  newer cover; obtain the actual operative scheme before releasing it again.
- **Bedford:** the retained discovery record identifies an adopted default
  scheme with local amendments (paragraphs 1.2 and 3.1), rather than a summary.
  Verify that adoption evidence, then encode the incorporated SI 2012/2886
  provisions together with Bedford's operative amendments.

### Repairs already made on main

`uk-oldham` and `uk-east-hertfordshire` applied the daily 2 6/7% coefficient
to an annual or weekly excess
([#140](https://github.com/TheAxiomFoundation/rulespec-uk/issues/140#issuecomment-5845299202)).
#447 repaired both, with period invariants and differential checks against the
national rules (`tests/test_ctr_taper_periodisation.py`). `uk-babergh` read its
"prescribed daily percentage" sentence (identical to Ipswich's) as an effective
140% weekly taper and left tariff income out of the excess; #449 applied the
10 October 2026 ruling (20% of weekly excess per week) and counts tariff
income. Both landed before the guard went on. Any further correction to a
merged module now has to come from the encoder.

## How to continue

1. **Finish the signed-workflow migration.** The encoder re-pin comes first:
   it admits verified receipts, retires the manifest prohibition, and brings
   the `corpus-fetch` support that binding any newer corpus release needs. No
   council encode can land before it.
2. **Re-version Arun with section rows.** Arun has no module on `main`, so no
   citation breaks. Use the tested extraction block, with its bare-number fix, in
   [`section-ingest.md`](section-ingest.md#arun-family-a-the-extraction-block),
   and follow the corpus procedure below.
3. **Cut, publish and bind** a release carrying the new Arun version.
4. **Encode Arun's sections** without `--apply` first, under the trusted
   signing supervisor:
   `axiom-encode encode uk-arun/manual/council-tax-reduction-scheme-2026-2027/23 --backend codex`
   (abbreviated: the encoder also requires `--corpus-path`,
   `--axiom-rules-engine-path` and `--policy-repo-path`),
   then `/19`, `/21`, `/22` and `/schedule-3`. Read the encoder's own gates.
   Then run them through the signed workflow so the modules land with
   receipts.
5. **Assemble Arun** as a ProgramSpec under `uk-arun/programs/`: the s.21
   maximum (100% of A/B less non-dependant deductions), then the s.23 band
   discount applied to that maximum, then s.21(7)'s rule that nothing is
   payable below £1 a week, with Schedule 3 paragraph 8's passported band A.
6. **Compare** its outputs with `oracle/uk-ctr/wave11/uk-arun/pr310-repaired`
   on a shared household grid. Adjudicate every disagreement against the
   scheme text, applying the band A ruling.
7. **Repeat on Crawley** (heading family B; award rules in `/1`, `/57`, `/57A`,
   `/58` and `/59`) with the label fixes in
   [`section-ingest.md`](section-ingest.md#crawley-family-b-the-template-scheme).
8. **Take the first already-encoded council** through the same cycle, once
   the module-replacement question above is settled.
9. **Scale by heading family**, A and B first, then C–H.

### Corpus procedure

Work in `axiom-corpus` on a branch pushed to the organization repository (not
a fork); it merges only with merge commits. The current references are
[`docs/corpus-storage.md`](https://github.com/TheAxiomFoundation/axiom-corpus/blob/main/docs/corpus-storage.md)
("Ingest" and "Releases") and
[`docs/named-release-publication.md`](https://github.com/TheAxiomFoundation/axiom-corpus/blob/main/docs/named-release-publication.md).
In outline:

1. Write or rebuild the council's extraction manifest in
   `.axiom/corpus-manifests/uk-<slug>-council-tax-reduction.json`.
2. Extract with `axiom-corpus-ingest extract-official-documents --base data/corpus --version <version> --manifest <manifest>`.
   Name the version `<date>-<slug>-council-tax-reduction-2026-2027` with a
   later date than the served version: activation refuses a version that sorts
   before the one it replaces.
3. Commit the extraction manifest, so the tracked tree is clean, then sign:
   `axiom-corpus-ingest sign-ingest-manifest --jurisdiction uk-<slug> --document-class manual --version <version> --command "<the exact extract command>" --lock --push`.
   This writes the scope's lock file and uploads the bytes. One commit carries
   the signed ingest manifest and the lock.
4. Fetch the locked provisions (`axiom-corpus-ingest corpus fetch --path data/corpus/provisions`),
   then run `scripts/validate_citation_paths.py`. It fails when a family of
   irregular paths (page or block rows, spaces, en dashes, uppercase, truncated
   segments) grows past its baseline, and raising a baseline is a reviewed
   change.
5. Cut a release: add one new `manifests/releases/uk-rulespec-<date>.json` that
   copies the previous selector and swaps in the new version, and merge it after
   green CI. Merging does not publish. Dispatch `publish.yml` with the selector
   name; when it succeeds, dispatch `mirror-release.yml` and
   `activate-release.yml` with that publish run's ID. Activation waits for
   approval in the protected `release-activation` environment.
6. Rebind `rulespec-uk` in one PR. Set the release name and content digest in
   `.axiom/toolchain.toml`, leaving the waiver digest alone. Set the cut's merge
   commit as `axiom_corpus_ref` in `.axiom/workflow-toolchain.toml`,
   `axiom-corpus-ref` in `.github/workflows/repository-checks.yml`, and
   `AXIOM_CORPUS_REF` in `.github/workflows/bulk-encode.yml`. The PR's validate
   job fetches the published release object and fails until the mirror has
   finished. It also needs the encoder re-pin with `corpus-fetch` (step 1).

## The registry

`councils.csv` has one row per English authority in ONS code order. Module and
PR statuses were reconciled on 2026-10-09 and again on 2026-10-14, when the 34
closed wave-11 councils returned to `ingested` with their reference tags in
`notes`. Ingestion, source URLs and
heading-family observations retain the campaign snapshot dates in the notes;
verify them before a new ingest. The repository's smaller
[`data/councils/registry.csv`](../../data/councils/registry.csv) keeps its original
identity and source fields, with only observed module/PR statuses updated.

| Column | Meaning |
|---|---|
| `ons_code`, `name` | ONS April 2025 local authority district identity |
| `jurisdiction` | `uk-<slug>` repository and corpus root |
| `status` | Pipeline stage below |
| `pr` | Open council encoding PR number, if any (none since 2026-10-11) |
| `corpus_version` | Recorded scope version; provenance dates are in `notes` |
| `heading_family` | Historical scheme-PDF family from the section survey |
| `scheme_url` | Recorded official source or best-known discovery URL |
| `other_source_urls` | Adoption records or additional sources, space-separated |
| `notes` | Evidence dates, source blockers and next steps |

| Status | Meaning |
|---|---|
| `encoded` | Council module on main; does not imply a receipt or correct award |
| `encode-pr-open` | Council module in the open PR identified in `pr` (unused since 2026-10-11) |
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
