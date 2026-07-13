# rulespec-uk Agent Notes

This repo stores UK RuleSpec source registry materials and related policy metadata.

## Do

- Keep jurisdiction-administered source slices under `sources/` when source slices are present.
- Add or update sidecar `.meta.yaml` files with source provenance, relations, and jurisdiction metadata.
- Add atomic RuleSpec under a direct jurisdiction's `legislation/`, `policies/`,
  `regulations/`, or `statutes/` root.
- Add only declarative YAML ProgramSpecs under `<jurisdiction>/programs/`.
- Keep parameter tables as structured YAML when they are useful reference data.
- Keep large source payloads outside Git and point to them through metadata or manifests.

## Do Not

- Add repository-root content trees, `.yml` aliases, symlinks, Python program
  implementations, singular rule roots, or generated formula artifacts.
- Put unrelated jurisdiction materials here.
- Add generated source payloads to Git.
