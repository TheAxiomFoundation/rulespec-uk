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

Atomic modules and their companion tests must come from the supervised encoder,
with signed `axiom-encode/applied-rulespec/v5` receipts under
`.axiom/encoding-manifests/<jurisdiction>/<atomic-root>/`, mirroring the module
path with the `.json` extension. Existing modules without receipts stay untouched
until replaced by encoder output. Signed retirement receipts may remain after
the files they cover are deleted. No workflow may accept an older schema as
current attestation.

`.axiom/workflow-toolchain.toml` pins the tools used by validation and signed
generation; `.axiom/toolchain.toml` binds the signed corpus release and validation
waiver set. UK encoding uses the supervised `targeted-signed-reencode.yml`
workflow in axiom-encode with `country=uk`.

Jurisdiction-specific materials belong in this repo. Shared federal materials belong in `rulespec-us`.
