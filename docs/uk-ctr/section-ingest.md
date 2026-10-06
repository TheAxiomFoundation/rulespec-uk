# Section-level ingest for council schemes (option A′)

Findings from the 2026-09-13 spike and survey that test whether council CTR
schemes can be ingested with one corpus row per scheme section, so that each
award-surface component is one citation the supervised encoder can take. The
spike ran locally against `axiom-corpus` at `440162d0` (the cut of
`uk-rulespec-2026-09-07`); nothing was committed.

**Result:** the corpus half of A′ needs manifest configuration only, no code.
It is proven on Arun (heading family A) and Crawley (family B), which together
cover about 90 of the 155 long council PDFs. The encoder half is untested.

## Why sections

Council scopes are ingested today with one `document` row and one `page-N` row
per PDF page (`block-N` for DOCX). The supervised encoder gives the model
exactly the cited row, and an award surface spans several pages. For Arun:

| Citation | Source text given to the model | Maximum (s.21) | £6,000 capital (s.19) | Band B | Band E |
|---|---:|:-:|:-:|:-:|:-:|
| `.../page-28` | 3,115 bytes, 0 component rows | no | no | no | no |
| `.../council-tax-reduction-scheme-2026-2027` (document) | 343,163 bytes, 111 component rows | yes | yes | yes | yes |

A page citation starves the model; a document citation over-scopes it (the
module must then cover every sub-paragraph of 111 pages). The corpus has no
page-range citation, and anchors cannot span pages. Section rows are the only
way to make one citation carry one award-surface component.

## How the corpus makes section rows

Checked against `axiom-corpus` `main` at `3858e928` (2026-09-25):

- Granularity is set per document by `extraction.segmentation` in the corpus
  manifest, not by file format. `_extract_pdf_blocks` in
  `src/axiom_corpus/corpus/documents.py` sends `labeled_sections` to
  `_extract_labeled_pdf_section_blocks`, which emits `kind="section"` rows with
  `page_start` and `page_end` in their metadata. Paths are flat,
  `<document>/<label>`, with the document as parent.
- With no `segmentation`, PDFs fall through to one row per page (`page-N`), and
  DOCX and HTML to one row per block (`block-N`). None of the 107 council
  corpus manifests committed to `axiom-corpus` has an `extraction` key, which is
  why every council scope has page or block rows.
- `labeled_sections` is established: 262 manifests use it, covering 136
  `manual` documents among others (for example
  `manifests/us-vt-medicaid-eligibility-manual.yaml`).
- The other section mode, `numbered_sections`, only recognizes three-digit
  labels such as `035.` (Idaho rules) and takes no pattern, so it cannot serve
  council `19.` headings.
- No page-range or multi-page citation exists, and anchors resolve only within
  one parent row, so nothing else lets one citation span pages 27–29.

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
- `section_heading_requires_bold` keeps cross-references ("see section 21")
  and contents lines from matching.
- `section_heading_pattern` matches bold `NN.0 Heading` lines; the empty
  `sched` group keeps both patterns' groups aligned for the template.
- `section_label_pattern` with `label_only_heading_pattern` handles a label on
  its own line with the heading on the next line, and `Schedule N` labels.
- `section_label_replacements` turns `Schedule 3` into `schedule-3`, so no path
  segment contains a space (which would count against the corpus's
  space-segment ratchet).
- `drop_line_patterns` removes the running header, the header with a page
  number, and bare page numbers.

Output: 96 rows, 1 document and 95 sections: sections 1–88 with no gaps or
duplicates, then `schedule-1` to `schedule-7`. The citation-path validator
reported 0 irregular paths and no ratchet regression. No running header or
footer text remained in any section body.

### Arun's award surface as citations

All under `uk-arun/manual/council-tax-reduction-scheme-2026-2027/`.

| Citation | Heading | Pages | Carries |
|---|---|---|---|
| `/19` | Class of person excluded from this scheme: capital limit | 27 | capital limit £6,000 |
| `/21` | Maximum and minimum council tax reduction amount | 27–28 | maximum = 100 per cent of A/B less non-dependant deductions; no award below £1 a week |
| `/22` | Non-dependant deductions | 28 | £5.00 × 1/7 for each non-dependant aged 18 or over who is in remunerative work or has no income; none where the non-dependant receives Universal Credit, income-related ESA, income-based JSA, Pension Credit guarantee credit or Income Support, or is a student |
| `/23` | Amount of reduction under this scheme: Class D | 28–29 | banded discount on the s.21 maximum: A 100%, B 70%, C 50%, D 30%, E 10% |
| `/schedule-3` | Calculation of the amount of Council Tax Reduction | 80 | the same grid with band A at **90%**; the linkage sentence (discount based on the scheme's maximum, income and capital); CPI uprating of the bands (¶7); band A for Income Support, income-related ESA and income-based JSA (¶8) |

`/23` and `/schedule-3` disagree on band A. That is open question 2 in the
[README](README.md#2-arun-band-a-100-or-90).

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

Output: 113 rows, 1 document and 112 sections: labels 1–107 with lettered
inserts (`7A`, `15A`, `51A`, `60A`, `60B`, `60D`, `61A`–`61D`, `69A`, `106A`),
then `schedule-1` to `schedule-5`. Most absent numbers are printed as "Not
Used" in the scheme itself (`62.0- 63.0 Not Used`, `65.0 - 66.0 Not Used`,
`82.0 – 90.0 Not used`). Two are real misses caused by the scheme's own
typography, not by the ranges:

- `60C Extended reductions – movers` is printed without `.0`, so it is merged
  into `60B`;
- `71. 0 Use of telephone provided evidence` has a space inside the label, so
  it is merged into `70`.

Neither is on the award surface, but both break section coverage. Make the
patterns tolerant (for example `(?P<label>\\d{1,3}[A-Z]?)(?:\\.\\s?0)?` with the
bold gate still on) and re-run the gap check. The lesson for every council: read
the extractor's label list against the scheme's contents page; "the gaps are
Not Used ranges" has to be checked, not assumed.

### Crawley's award surface as citations

In family B, the council's local working-age rules are not spread across
numbered calculation sections as in Arun. They sit in:

| Citation | Heading | Pages | Carries |
|---|---|---|---|
| `/1` | Introduction to the Council Tax Reduction Scheme | 5–11 | the local classes, maximum, capital limit and percentage award (about 15,700 characters; it also describes the pension-age classes) |
| `/58` | Non-dependant deductions | 66–68 | non-dependant deductions |

The rest of the document (sections 2–107) is the template's default-scheme
text. Crawley has no income-band grid. If the encoder over-scopes on `/1`, a
second-level split of that section is possible with `page_windows` and a
narrower heading pattern; that is untested.

## Heading-family survey

Every council PDF in the corpus (169 PDFs in the 155 PDF-sourced council
scopes; the other 4 scopes are DOCX or HTML) was classified by counting
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

Only A and B have been run. The C–H variants are proposals.

Some entries are not scheme texts. Adoption records and reports that sit beside
a scheme in the same scope (Amber Valley, Cambridge, Chelmsford, East
Hertfordshire, Herefordshire, Middlesbrough, Oldham, Tameside, West Lindsey)
are mostly `short-doc`, but the Cambridge minutes (43 pages) and Oldham minutes
(19 pages) classify as G and a 7-page Middlesbrough report as H. Keep all of
those at page level: they are corroboration, never value sources.

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

So the configuration work is: A and B, about 90 PDFs, with the tested blocks;
C–F, 48 PDFs, one regex variant per family; G–H, 8 PDFs, non-bold variants;
none, 9 PDFs, bespoke or page rows; short-doc, 14, page rows. Per council:
choose the family, set `start_page`, add the council's running-header drop,
extract, and check the label list against the contents page.

## Re-versioning a scope with section rows

RE-VERSION-PLACEHOLDER

## What is not yet known

- Whether `axiom-encode encode` on a section citation (Arun `/23`, Crawley
  `/1`) under the signing supervisor yields a module that passes the encoder's
  own gates. This is the first thing to test under A′, and it needs a
  section-row version in a signed, bound release.
- The encoder names a module after its citation (for example
  `policies/<document>/23.yaml`), not `policies/<council>/council-tax-reduction`.
  How the per-council composition module references the component modules
  still has to be designed.
- Schedule paragraphs as their own rows (`schedule-3/2`): today a schedule is
  one row, which is enough for the award surface. Paragraph rows need a small
  extractor change to carry the schedule prefix onto paragraph labels.
