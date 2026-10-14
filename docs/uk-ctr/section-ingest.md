# Section-level ingest for council schemes (option A′)

Findings from the 2026-09-13 spike and survey that test whether council CTR
schemes can be ingested with one corpus row per scheme section, so that each
award-surface component is one citation the supervised encoder can take. The
spike used the source corpus at [`440162d0`](https://github.com/TheAxiomFoundation/axiom-corpus/tree/440162d04375a5071f2ac02de94f85def3e74053),
the commit bound by `uk-rulespec-2026-09-07`. The section outputs described
below are historical extraction results, not a published section-row release.

**Result:** the corpus half of A′, the route chosen on 2026-10-11 (see the
[README](README.md#the-route)), needs manifest configuration only, no code.
It was demonstrated on Arun (heading family A) and Crawley (family B).
The archived survey below contains 169 PDFs across 155 PDF-sourced council
scopes; 90 PDFs fall in families A/B, with documents of different lengths. The encoder half
was untested in that spike, and these extraction results do not establish that
a supervised encode can pass its gates.

## Why sections

The campaign scopes in the September corpus were ingested with one
`document` row and one `page-N` row
per PDF page (`block-N` for DOCX). The supervised encoder gives the model
exactly the cited row, and an award surface spans several pages. For Arun:

| Citation scope | Bound source rows | Maximum (s.21) | £6,000 capital (s.19) | Band B | Band E |
|---|---:|:-:|:-:|:-:|:-:|
| `.../page-28` | one page row | no | no | no | no |
| `.../council-tax-reduction-scheme-2026-2027` (document) | all 111 page rows | yes | yes | yes | yes |

The bound rows were rechecked on 2026-10-09. The page citation lacks several
required award provisions; the document citation includes the whole scheme.
A model asked to cover its cited document would therefore face all 111 pages.
In the tested corpus extractor, page rows cannot carry a multi-page section.
Section rows give one citation the complete text of a component that crosses
a page boundary.

## How the corpus makes section rows

The historical spike used the corpus's existing `labeled_sections` mode.
The [PDF extraction implementation](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/src/axiom_corpus/corpus/documents.py)
is pinned here to the campaign's bound release commit, rather than to moving
`main`:

- Set `extraction.segmentation` on the document in its corpus manifest.
  `labeled_sections` emits section rows with `page_start` and `page_end`
  metadata. Their paths are `<document>/<label>`, with the document as parent.
- The [Arun manifest](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/.axiom/corpus-manifests/uk-arun-council-tax-reduction.json)
  and [Crawley manifest](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/.axiom/corpus-manifests/uk-crawley-council-tax-reduction.json)
  do not set segmentation: their published rows remain page rows.
- The alternative `numbered_sections` mode recognizes three-digit labels
  such as `035.`. Its default shape does not fit council `19.` headings.
- A section configuration must be checked against the actual source bytes:
  contents entries, cross-references, running headers and page numbers can all
  create false boundaries or contaminate section bodies.

## Arun (family A): the extraction block

Add this `extraction` key to the Arun document entry in
`.axiom/corpus-manifests/uk-arun-council-tax-reduction.json`:

```json
"extraction": {
  "segmentation": "labeled_sections",
  "start_page": 4,
  "section_heading_requires_bold": true,
  "section_heading_pattern": "^\\s*(?P<label>\\d{1,3})\\.0(?P<sched>)\\s+(?P<heading>\\S.*?)\\s*$",
  "section_label_pattern": "^\\s*(?:(?P<label>\\d{1,3})\\.0|(?P<sched>Schedule\\s+\\d+))\\s*$",
  "section_label_template": "{label}{sched}",
  "section_label_replacements": {
    "Schedule 1": "schedule-1",
    "Schedule 2": "schedule-2",
    "Schedule 3": "schedule-3",
    "Schedule 4": "schedule-4",
    "Schedule 5": "schedule-5",
    "Schedule 6": "schedule-6",
    "Schedule 7": "schedule-7",
    "Schedule 8": "schedule-8",
    "Schedule 9": "schedule-9"
  },
  "label_only_heading_pattern": "^[A-Z].*$",
  "drop_line_patterns": [
    "^\\s*Council Tax Reduction Scheme 2026/27\\s*$",
    "^\\s*Council Tax Reduction Scheme 2026/27\\s+\\d{1,3}\\s*$",
    "^\\s*\\d{1,3}\\s*$"
  ]
}
```

What each part does:

- `start_page: 4` skips the contents pages, whose entries would otherwise
  become false sections.
- `section_heading_requires_bold` rejects non-bold cross-references. The
  separate `start_page` setting excludes contents entries; bold alone cannot
  distinguish a bold contents entry from an operative heading.
- `section_heading_pattern` matches bold `NN.0 Heading` lines; the empty
  `sched` group keeps both patterns' groups aligned for the template.
- `section_label_pattern` with `label_only_heading_pattern` handles a label on
  its own line with the heading on the next line, and `Schedule N` labels.
- `section_label_replacements` turns `Schedule 3` into `schedule-3`. A literal
  `Schedule 3` segment would count against two of the corpus's citation-path
  ratchets: space segments and uppercase segments.
- `drop_line_patterns` removes the running header, the header with a page
  number, and bare page numbers.

Fix one defect before reusing this block: the bare-number pattern
`^\\s*\\d{1,3}\\s*$` also deletes paragraph numbers that a scheme prints on
their own line. Arun's page 80 prints Schedule 3's paragraphs as `1`, `2`, `4`,
`5` and `6` (the scheme has no paragraph 3) and then `7.` and `8.`. The
extracted `schedule-3` body keeps the text of every paragraph and the `7.` and
`8.` markers, but loses the other five numbers. Narrow the pattern, for example
to page numbers in the footer position, before any citation or review relies on
Schedule 3 paragraph numbers.

The 2026-09-13 spike recorded 96 rows, 1 document and 95 sections; the
95-section extraction was reproduced against the bound PDF and pinned extractor
on 2026-10-09: sections 1–88 with no gaps or duplicates, then `schedule-1`
to `schedule-7`. The historical citation-path validation reported no irregular
paths or
ratchet regression. The reproduction checked that the section labels are
unique and that the configured running header is removed. Full corpus path
validation must be rerun when publishing the new scope version.

### Arun's award surface as citations

These are proposed section citations under
`uk-arun/manual/council-tax-reduction-scheme-2026-2027/`, not citations in the
currently bound page-row release. Source text can be inspected in the
[September Arun rows](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/data/corpus/provisions/uk-arun/manual/2026-09-05-arun-council-tax-reduction-2026-2027.jsonl).

| Citation | Heading | Pages | Carries |
|---|---|---|---|
| `/19` | Class of person excluded from this scheme: capital limit | 27 | capital limit £6,000 |
| `/21` | Maximum and minimum council tax reduction amount | 27–28 | maximum = 100 per cent of A/B less non-dependant deductions; no award below £1 a week |
| `/22` | Non-dependant deductions | 28 | £5.00 × 1/7 for each non-dependant aged 18 or over who is in remunerative work or has no income; none where the non-dependant receives Universal Credit, income-related ESA, income-based JSA, Pension Credit guarantee credit or Income Support, or is a student |
| `/23` | Amount of reduction under this scheme: Class D | 28–29 | banded discount on the s.21 maximum: A 100%, B 70%, C 50%, D 30%, E 10% |
| `/schedule-3` | Calculation of the amount of Council Tax Reduction | 80 | the same grid with band A at **90%**; the linkage sentence (discount based on the scheme's maximum, income and capital); CPI uprating of the bands (¶7); band A for Income Support, income-related ESA and income-based JSA (¶8) |

`/23` and `/schedule-3` disagree on band A. The maintainer ruled on
10 October 2026 that band A is 100%, following s.23(3); see the
[README](README.md#arun-band-a-ruled-100).

Cosmetic quirks, not blocking: each section's `heading` starts with its label
(`"19 Class of person…"`), as in production `labeled_sections` output; the
`citation_label` of schedule rows is ordinal-based while the `citation_path` is
correct (`schedule-3`).

## Crawley (family B): the template scheme

Crawley's 132-page scheme uses the most common council template: a bold
`N.0` label on its own line, the heading on the next line, and lettered
inserts such as `7A.0`. The Arun block transfers with two changes:

- allow a letter after the number in both patterns:
  `(?P<label>\\d{1,3}[A-Z]?)\\.0`;
- add the council's own running header to `drop_line_patterns`, here
  `^\\s*Crawley Council Tax Reduction Scheme 2026/27\\s*$`. Without it, 56
  section bodies kept the header.

Lettered labels need one more decision before publication. A label such as
`7A` becomes an uppercase path segment (`…/7A`), and the corpus's
`scripts/validate_citation_paths.py` counts every path containing an uppercase
character in its `uppercase_segments` family. The script fails when a family's
live count exceeds its baseline in `schema/citation-path.v1.json`, and raising
a baseline is a reviewed change. Either map each lettered label to lower case
with `section_label_replacements` (`"7A": "7a"`), or carry a reviewed baseline
raise in the same corpus PR. Crawley has 12 such labels in the strict
extraction (14 once `57A` and `60C` are repaired), and family B covers 73 PDFs.

The 2026-09-13 spike recorded 113 rows, 1 document and 112 sections; the
112-section extraction was reproduced against the bound PDF and pinned extractor
on 2026-10-09: labels from 1–107 with lettered inserts (`7A`, `15A`, `51A`, `60A`, `60B`, `60D`, `61A`–`61D`, `69A`, `106A`),
then `schedule-1` to `schedule-5`. Most absent numbers are printed as "Not
Used" in the scheme itself (`62.0- 63.0 Not Used`, `65.0 - 66.0 Not Used`,
`82.0 – 90.0 Not used`). The source pages also show headings outside the
strict `.0` pattern:

- `57A Minimum Council Tax Support` is printed without `.0`, so the strict
  pattern leaves the minimum-award rule inside `/57` rather than giving it a
  separate `/57A` row;
- `60C Extended reductions – movers` is printed without `.0`, so it is merged
  into `60B`;
- `71. 0 Use of telephone provided evidence` has a space inside the label, so
  it is merged into `70`.

These headings were rechecked in the bound source on 2026-10-09.
The minimum-award provision is part of the award surface. The other two
headings also need to be accounted for before claiming section coverage. Make the
patterns tolerant (for example `(?P<label>\\d{1,3}[A-Z]?)(?:\\.\\s?0)?` with the
bold gate still on) and re-run the gap check. Applying that change to both
patterns on 2026-10-09 produced 115 unique sections, including separate `57A`,
`60C` and `71` rows. With the council-specific drop pattern, no section body
retained the running header; omitting it reproduced the 56 contaminated bodies.
This is extraction validation, not a published scope or a supervised encode.
The lesson for every council: read
the extractor's label list against the scheme's contents page; "the gaps are
Not Used ranges" has to be checked, not assumed.

### Crawley's award surface as citations

Crawley's introduction establishes the local classes and points to later
calculation provisions. It is not a complete standalone award citation. These
proposed citations are under
`uk-crawley/manual/council-tax-reduction-scheme-2026-2027/`; their source pages
were rechecked on 2026-10-09 in the [September Crawley rows](https://github.com/TheAxiomFoundation/axiom-corpus/blob/440162d04375a5071f2ac02de94f85def3e74053/data/corpus/provisions/uk-crawley/manual/2026-09-05-crawley-council-tax-reduction-2026-2027.jsonl):

| Citation | Heading | Pages | Carries |
|---|---|---|---|
| `/1` | Introduction to the Council Tax Reduction Scheme | 5–11 | local working-age classes, £9,000 capital condition and daily-versus-weekly taper wording; refers to s.57 for the maximum and also describes pension-age classes |
| `/57` | Maximum council tax support | 66 | daily maximum at 100% of A/B, subject to non-dependant deductions and joint-liability rules |
| `/57A` (after pattern repair) | Minimum Council Tax Support | 66 | no support where the daily amount is below £5.00 × 1/7; in the strict spike extraction this text remains in `/57` |
| `/58` | Non-dependant deductions | 66–68 | non-dependant deductions |
| `/59` | Council tax support taper | 68 | the printed 2 6/7% taper and linkage to the s.57 maximum; read with the day/week wording in `/1` |

The remaining numbered sections contain the template scheme text, including
the non-dependant deduction provision cited above. Crawley has no income-band
grid. If the encoder over-scopes on `/1`, a
second-level split of that section is possible with `page_windows` and a
narrower heading pattern; that is untested.

## Heading-family survey

This preserves the **2026-09-13 heading survey**, not today's ingest inventory.
The survey's classification run is an archival record whose artifacts are not
published; the council lists and totals below were rechecked, the classifier was not.
Counts were rechecked on 2026-10-09 by counting the PDF entries in the council
lists below: 169 PDFs across 155 unique PDF-sourced council scopes, plus the
4 DOCX/HTML scopes listed separately. A scope can include a scheme and adoption
records, so a PDF count is not a council count. The historical survey classified
the PDF texts by counting
heading-like lines with the corpus's own PDF line filter. A bold family with at
least 15 matching lines wins; otherwise a non-bold family; otherwise the PDF is
`short-doc` (20 pages or fewer) or `none`.

| Family | Pattern (line start) | PDFs | Config |
|---|---|---:|---|
| A | bold `NN.0 Heading` on one line | 17 | Arun block as is |
| B | bold `N.0` label alone, heading on the next line | 73 | Arun block with lettered labels and the council's header drop |
| C | bold `NN. Heading` | 28 | one regex variant |
| D | bold `Section NN` / `Part NN` / `Paragraph NN` / `Chapter NN` | 13 | one regex variant |
| E | bold `N.N Heading` | 2 | one regex variant |
| F | bold `NN Heading` | 5 | one regex variant |
| G | non-bold `NN. Heading` | 6 | the C pattern without the bold gate, plus cross-reference drops |
| H | non-bold `N.N Heading` | 2 | the E pattern without the bold gate, plus cross-reference drops |
| none | long document, no numbering family | 9 | bespoke configuration, or keep page rows |
| short-doc | 20 pages or fewer, no family | 14 | keep page rows |
| **Total** | | **169** | |

Only A and B have been run. The C–H variants are proposals, and the B pattern still needs the typography
repairs described above.

Some entries are not scheme texts. Adoption records and reports that sit beside
a scheme in the same scope (Amber Valley, Cambridge, Chelmsford, East
Hertfordshire, Herefordshire, Middlesbrough, Oldham, Tameside, West Lindsey)
are mostly `short-doc`, but the Cambridge minutes (43 pages) and Oldham minutes
(19 pages) classify as G and a 7-page Middlesbrough report as H. Keep all of
those at page level for the operative-year and adoption checks. They do not
replace the scheme provisions that define the award. If an adopted resolution
contains a binding amendment or uprating, preserve and apply that overlay under
the playbook's incorporation gate.

PDFs by family (scope and page count):

- **A (17):** uk-adur (151), uk-arun (111), uk-cumberland (144), uk-east-hampshire (185), uk-east-suffolk (195), uk-fareham (87), uk-fenland (194), uk-havant (187), uk-hertsmere (149), uk-isles-of-scilly (143), uk-newcastle-upon-tyne (171), uk-northumberland (85), uk-salford (181), uk-sefton (195), uk-slough (118), uk-wigan (211), uk-worthing (150)
- **B (73):** uk-ashford (126), uk-blackpool (137), uk-bournemouth-christchurch-and-poole (186), uk-braintree (85), uk-brentwood (77), uk-bromsgrove (86), uk-broxbourne (137), uk-burnley (151), uk-cannock-chase (123), uk-canterbury (97), uk-castle-point (73), uk-chelmsford (133), uk-cheshire-east (127), uk-chorley (145), uk-cotswold (166), uk-coventry (141), uk-crawley (132), uk-dartford (88), uk-dover (97), uk-east-hertfordshire (142), uk-east-riding-of-yorkshire (76), uk-eastleigh (143), uk-folkestone-and-hythe (67), uk-forest-of-dean (142), uk-fylde (139), uk-gravesham (89), uk-harlow (146), uk-hartlepool (90), uk-hastings (133), uk-herefordshire (137), uk-isle-of-wight (106), uk-lancaster (141), uk-lichfield (82), uk-maldon (148), uk-malvern-hills (135), uk-mansfield (146), uk-medway (87), uk-middlesbrough (89), uk-north-east-lincolnshire (84), uk-north-hertfordshire (82), uk-north-lincolnshire (84), uk-north-norfolk (142), uk-north-warwickshire (137), uk-north-yorkshire (81), uk-nuneaton-and-bedworth (135), uk-plymouth (130), uk-portsmouth (87), uk-redditch (86), uk-ribble-valley (145), uk-rochford (82), uk-rossendale (146), uk-rother (74), uk-rugby (84), uk-rushmoor (146), uk-sandwell (132), uk-solihull (84), uk-southend-on-sea (85), uk-stafford (123), uk-stevenage (141), uk-stratford-on-avon (146), uk-tameside (83), uk-tamworth (89), uk-telford-and-wrekin (121), uk-thanet (97), uk-torbay (90), uk-warrington (139), uk-wealden (77), uk-west-oxfordshire (96), uk-winchester (83), uk-wirral (87), uk-wolverhampton (141), uk-worcester (134), uk-wyre (143)
- **C (28):** uk-amber-valley (168), uk-bath-and-north-east-somerset (181), uk-bedford (15), uk-bracknell-forest (114), uk-breckland (210), uk-cambridge (173), uk-charnwood (209), uk-cherwell (149), uk-dudley (150), uk-east-cambridgeshire (210), uk-epsom-and-ewell (106), uk-gloucester (176), uk-harrow (196), uk-hart (148), uk-hillingdon (134), uk-merton (255), uk-milton-keynes (322), uk-newham (340), uk-oldham (160), uk-peterborough (155), uk-reading (151), uk-rotherham (156), uk-rushcliffe (266), uk-southampton (183), uk-spelthorne (145), uk-warwick (155), uk-west-northamptonshire (157), uk-west-suffolk (210)
- **D (13):** uk-broxtowe (250), uk-elmbridge (296), uk-guildford (140), uk-haringey (221), uk-kensington-and-chelsea (220), uk-kingston-upon-thames (162), uk-newark-and-sherwood (248), uk-north-kesteven (193), uk-north-west-leicestershire (220), uk-redbridge (158), uk-south-oxfordshire (156), uk-vale-of-white-horse (157), uk-westmorland-and-furness (144)
- **E (2):** uk-cheshire-west-and-chester (298), uk-redcar-and-cleveland (22)
- **F (5):** uk-babergh (152), uk-ipswich (152), uk-mid-suffolk (152), uk-south-kesteven (298), uk-west-lindsey (229)
- **G (6):** uk-bassetlaw (92), uk-cambridge (43, adoption minutes), uk-darlington (49), uk-oldham (19, adoption minutes), uk-runnymede (37), uk-shropshire (220)
- **H (2):** uk-county-durham (40), uk-middlesbrough (7, adoption report)
- **none (9):** uk-barnsley (64), uk-bristol-city-of (54), uk-broadland (58), uk-bury (59), uk-knowsley (62), uk-north-somerset (60), uk-south-derbyshire (55), uk-south-norfolk (58), uk-st-helens (58)
- **short-doc (14):** uk-amber-valley (10), uk-cambridge (3), uk-chelmsford (9), uk-derby (10), uk-ealing (17), uk-east-hertfordshire (7), uk-east-hertfordshire (9), uk-herefordshire (14), uk-herefordshire (2), uk-middlesbrough (8), uk-oldham (8), uk-tameside (10), uk-west-lindsey (14), uk-westminster (7)

Not surveyed (DOCX or HTML sources): uk-barking-and-dagenham, uk-leeds,
uk-nottingham, uk-wakefield. DOCX scopes can use the DOCX extractor's
`labeled_sections` or `styled_labeled_sections` modes.

So the configuration work is: A and B, 90 PDFs, with configurations piloted
on Arun and Crawley;
C–F, 48 PDFs, one regex variant per family; G–H, 8 PDFs, non-bold variants;
none, 9 PDFs, bespoke or page rows; short-doc, 14, page rows. Per council:
choose the family, set `start_page`, add the council's running-header drop,
extract, and check the label list against the contents page.

## Re-versioning a scope with section rows

Changing segmentation changes citation identities. Carry out this work in
`axiom-corpus`, then bind the resulting signed release in `rulespec-uk`; adding
an extraction block here cannot change the externally bound corpus. The
constraints below were checked against `axiom-corpus` `main` at `dc82e4c4` and
`axiom-encode` at `c326d1ac` (rulespec-uk's encoder pin) on 2026-10-14.

- **One version of a document per release.** UK releases use the
  `complete-expression-dates-v1` quality profile. Under it,
  `_check_release_citation_uniqueness` in
  `src/axiom_corpus/corpus/release_quality.py` rejects a release in which any
  citation path appears in two scopes. A page-row version and a section-row
  version of the same council document share the document's own path, so a
  release carries one or the other. Binding the section-row version therefore
  removes the page rows from the served corpus. 262 files across 98 councils in
  `rulespec-uk` cite council page rows, and Leeds and Wakefield cite block rows.
  Re-version a council with a merged module only in a change that also replaces
  or retires that module; under the generated-RuleSpec guard, deleting a module
  needs a changed receipt that marks it deleted, which `axiom-encode retire`
  records. Councils with no module, such as Arun, carry no such cost.
- **Path-mapping events do not exist yet.** `schema/citation-path.v1.md` §6
  specifies `split`, `merge` and `retire` events and is headed "spec only — no
  implementation here"; no event stream is produced. A page-to-section change
  is many-to-many: a section spans pages and a page holds several sections.
  Until the stream exists, put the page-to-section correspondence (from each
  section's `page_start` and `page_end`) in the corpus PR description.
- **The new version must sort after the served one.** Activation's
  monotonicity check (`scripts/check_release_gate.py`) refuses a release whose
  version for a scope sorts before the active one unless regression is
  explicitly allowed. Keep the `<date>-<slug>-council-tax-reduction-2026-2027`
  form with a later date.
- **Source bytes live outside git.** Since
  [axiom-corpus#769](https://github.com/TheAxiomFoundation/axiom-corpus/pull/769)
  (2026-09-29), each scope's sources, inventory, provisions and coverage are
  pinned by `.axiom/corpus-locks/<jurisdiction>/<document_class>/<version>.json`
  and fetched with `axiom-corpus-ingest corpus fetch`. Extracting from a fetched
  copy through a document's `local_path` works, but `_download_document` then
  records the absolute `file://` path as every row's `download_url`, with no
  content type. Prefer downloading again from the official URL and checking the
  sha256 against the locked source; otherwise correct the recorded URL before
  signing.
- **52 council scopes have no committed extraction manifest.** 107 council
  manifests are in `.axiom/corpus-manifests/`; the other 52 scopes' signed
  ingest manifests record an extraction command that read a manifest which was
  never committed. Rebuild it from the scope's inventory before adding an
  `extraction` block.

Procedure:

1. Start from the council's verified source manifest and preserve its source
   identity, operative-period evidence and source-byte hash. Add the extraction
   configuration to that document.
2. Extract a new scope version. Compare the complete label list with the
   printed contents and operative headings; account for every missing,
   duplicated or unexpected label. Inspect page spans and the full bodies of
   award provisions and schedules, including boundaries adjoining a page break.
   Run `scripts/validate_citation_paths.py` and confirm running headers and
   footers are gone.
3. Sign from a clean tracked tree with
   `axiom-corpus-ingest sign-ingest-manifest --lock --push`, which writes the
   scope's lock and uploads its bytes; commit the signed ingest manifest and the
   lock together. The current references are
   [`docs/corpus-storage.md`](https://github.com/TheAxiomFoundation/axiom-corpus/blob/main/docs/corpus-storage.md)
   and [`docs/named-release-publication.md`](https://github.com/TheAxiomFoundation/axiom-corpus/blob/main/docs/named-release-publication.md).
   Extraction success alone does not publish or bind anything.
4. Cut and publish a release that swaps the scope's version, then bind it in
   `rulespec-uk` (`.axiom/toolchain.toml`, `.axiom/workflow-toolchain.toml` and
   both workflow corpus refs; see the [README](README.md#corpus-procedure)).
   Verify that the chosen section citation resolves in that release before
   asking the supervised encoder to use it.
5. Pilot one Arun and one Crawley component through the supervised encoder.
   Inspect emitted evidence and receipts, run the full gate battery, and review
   the legal formula against the complete section and related provisions. Only
   then decide how to migrate the existing modules and compose components.

Pin the corpus and encoder versions in the pilot report. Do not describe old
modules as supervised encodes merely because their proof citations have been
changed to section rows.

## What is not yet known

- Whether `axiom-encode encode` on a section citation (Arun `/23`, Crawley
  `/1`) under the signing supervisor yields a module that passes the encoder's
  own gates. This is the first thing to test on the chosen route, and it needs
  a section-row version in a signed, bound release.
- The encoder names a module after its citation (for example
  `uk-arun/policies/council-tax-reduction-scheme-2026-2027/23.yaml`), not
  `policies/<council>/council-tax-reduction`. The per-council assembly is
  expected to be an axiom-compose ProgramSpec under `uk-<slug>/programs/`, like
  `uk/programs/universal-credit/fy-2026-27.yaml`: the shared workflow requires
  each ProgramSpec import to resolve to an existing encoded module and allows
  only the literals 0, 1 and 12. Whether one ProgramSpec can wire a council's
  section modules into its award is untested.
- Schedule paragraphs as their own rows (`schedule-3/2`): in the spike a schedule was
  one row, which is enough for the award surface. Paragraph rows need a small
  extractor change to carry the schedule prefix onto paragraph labels.
