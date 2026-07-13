# rulespec-uk

United Kingdom RuleSpec encodings in one country monorepo. Direct jurisdiction
roots include `uk/` (national) and `uk-kingston-upon-thames/` (council).
Durable ids are `<jurisdiction>:<path>#<rule>`.

## Contents

- `<jurisdiction>/{legislation,policies,regulations,statutes}/`: atomic
  `rulespec/v1` modules and companion tests.
- `<jurisdiction>/programs/`: declarative axiom-compose ProgramSpecs. Programs
  are canonical filesystem content but are not atomic RuleSpec modules.
- `.github/workflows/`: wrapper around the shared RuleSpec validation workflow.

## Conventions

Use the exact `.yaml` extension under one of the five jurisdiction-scoped roots.
Do not add repository-root content trees, `.yml` aliases, symlinks, or Python
program implementations. ProgramSpecs are declarative composition only.

Legacy applied manifests are deleted, not retained as migration inputs. This
migration snapshot intentionally contains no applied manifests; the named-release
trusted signer must regenerate `applied-rulespec/v5` attestations before release.
No workflow may accept an older schema as current attestation.

Jurisdiction-specific materials belong in this repo. Shared federal materials belong in `rulespec-us`.
