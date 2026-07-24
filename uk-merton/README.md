# London Borough of Merton jurisdiction

London Borough of Merton RuleSpec encodings inside the `rulespec-uk` country
monorepo. This directory is a jurisdiction content root, not a standalone
repository or toolchain boundary.

## Contents

- `policies/`: local atomic RuleSpec YAML.
- `programs/`: declarative axiom-compose ProgramSpecs when needed.
- `data/corpus/`: scoped generated corpus artifacts when needed for source verification.
- `.axiom/corpus-manifests/`: source manifests used by the corpus ingester.
- `.axiom/ingest-manifests/`: signed manifests for generated corpus artifacts.

## Conventions

Jurisdiction-specific materials belong here. Shared UK materials belong under
the sibling `uk/` jurisdiction root. Toolchain configuration and encoding
manifests live only at the country-checkout root.

Local Council Tax Reduction source rows should be produced by the corpus ingester from official council sources. Do not edit corpus JSONL rows by hand.
