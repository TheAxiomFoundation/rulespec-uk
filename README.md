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

Repository checks continue to prohibit every encoding manifest. The canonical
receipt-layout test is an additional staged check for a later encoder re-pin.
The prohibition is lifted only once the pinned encoder's guard verifies every
added or modified receipt, including receipt-only changes, with trusted
signature, hash, and provenance verification.

That later migration requires atomic modules and their companion tests to come
from the supervised encoder, with signed `axiom-encode/applied-rulespec/v5`
receipts under `.axiom/encoding-manifests/<jurisdiction>/<atomic-root>/`,
mirroring the module path with the `.json` extension. Existing modules without
receipts stay untouched until replaced by encoder output. Signed retirement
receipts may then remain after their files and the jurisdiction's last content
root are deleted, provided the jurisdiction remains registered.

The staged `.axiom/workflow-toolchain.toml` is a checked mirror of the literal,
authoritative pins in `.github/workflows/repository-checks.yml`. The reader fails
validation if any value differs. The TOML becomes authoritative only in a later
re-pin that adopts a shared workflow which classifies changes to this TOML as a
full toolchain change. The bulk-generation workflow retains its separate
dependency refs; compose does not consume the new file yet.
`.axiom/toolchain.toml` continues to bind the signed corpus release and validation
waiver set.

Jurisdiction-specific materials belong in this repo. Shared federal materials belong in `rulespec-us`.
