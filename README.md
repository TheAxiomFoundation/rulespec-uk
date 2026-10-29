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

Legacy applied manifests are deleted, not retained as migration inputs. The
blanket encoding-manifest prohibition was retired in
[#502](https://github.com/TheAxiomFoundation/rulespec-uk/pull/502). Repository
checks admit receipts only as UTF-8 JSON objects with unique keys and finite
numbers (no `NaN` or infinite values) declaring
`axiom-encode/applied-rulespec/v5`, under
`.axiom/encoding-manifests/<jurisdiction>/<atomic-root>/`, mirroring the module
path with the `.json` extension. In the checked-out tree, every symlink on the
receipt path is refused, including one that resolves inside the repository.
These checks cover layout and schema; signature, hash and provenance
verification belongs to the pinned encoder's guard in the shared CI workflow,
including receipt-only changes.

Atomic modules and their companion tests must come from the supervised encoder
with signed receipts. Existing modules without receipts stay untouched until
replaced by encoder output. Signed retirement receipts may remain after their
files and the jurisdiction's last content root are deleted, provided the
jurisdiction remains registered.

`.axiom/workflow-toolchain.toml` mirrors the literal pins in
`.github/workflows/repository-checks.yml`, and that workflow's
`workflow-toolchain` job fails if any value differs. Since the shared workflow
pin moved to `882c5f11`
([#503](https://github.com/TheAxiomFoundation/rulespec-uk/pull/503)), the shared
workflow also reads this table from the protected commit: a pull request's base,
or, for push, scheduled and manual runs, the `main` commit under validation. It
takes each dependency pin from the table before the caller's literal input, and
fails when an effective input does not match. When a pull request changes only
this table, the caller workflow and `.axiom/toolchain.toml`, the shared workflow
validates the proposed pins. A change to a dependency ref, the staged
`axiom_compose_ref`, or the shared workflow pin (the table's
`shared_workflow_ref` or the caller's `uses:` line) selects the full
toolchain-bump validation, and such a change fails when it comes with any other
file. The shared workflow only type-checks `axiom_encode_version` as a string;
the mirror check alone compares its value. The bulk-generation workflow keeps
its own dependency refs and does not read this table. The caller passes no
`axiom-compose-ref`, so the composer never runs: the mirror check compares the
staged `axiom_compose_ref` with the caller's metadata, and a change to it counts
as a pin change, but no step checks out or builds the composer.
`.axiom/toolchain.toml` continues to bind the signed corpus release and validation
waiver set.

Jurisdiction-specific materials belong in this repo. Shared federal materials belong in `rulespec-us`.
