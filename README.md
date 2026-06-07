# rulespec-uk-kingston-upon-thames

Kingston upon Thames RuleSpec encodings.

## Contents

- `policies/`: local policy RuleSpec YAML.
- `data/corpus/`: scoped generated corpus artifacts when needed for source verification.
- `.axiom/ingest-manifests/`: signed manifests for generated corpus artifacts.
- `.github/workflows/`: wrapper around the shared RuleSpec validation workflow.

## Conventions

Jurisdiction-specific materials belong in this repo. Shared UK materials belong in `rulespec-uk`.

Local Council Tax Reduction source rows should be produced by the corpus ingester from official council sources. Do not edit corpus JSONL rows by hand.
