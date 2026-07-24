# Derby City Council jurisdiction notes

This direct jurisdiction root belongs to the `rulespec-uk` country monorepo; it
is not a standalone repository or toolchain boundary.

## Do

- Add atomic RuleSpec under `legislation/`, `policies/`, `regulations/`, or
  `statutes/`, and declarative ProgramSpecs only under `programs/`.
- Keep local Council Tax Reduction source material ingestion-led, with signed corpus ingest manifests for generated corpus artifacts.
- Use source verification against the official Derby City Council scheme PDF or other primary council sources.

## Do Not

- Add unrelated UK-wide or other local-authority materials here.
- Hand-write corpus provision rows to satisfy validation.
- Put unrelated source payloads or generated formula artifacts in Git.
