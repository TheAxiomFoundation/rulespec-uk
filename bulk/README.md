# Bulk encode (UK)

A durable queue → **planner** for bulk RuleSpec encoding. `bulk/worklist.yaml`
is the committed queue of already-ingested UK provisions to encode;
`.github/workflows/bulk-encode.yml` turns a dispatch into a *plan* — the batch
selection plus the exact pinned toolchain a signed-apply encode leg consumes —
and verifies the pinned signed corpus release resolves. The encoder and the CI
gates own correctness. This system is **plumbing**: it never edits or invents
generated values. Its only judgement is *which* provisions to queue.

## Why this is a planner, not an autonomous encoder

Before the canonical-provenance hard cut (axiom-encode#1108) this workflow ran
an autonomous `encode --apply` leg in CI, signing the apply manifest from the
`AXIOM_ENCODE_APPLY_SIGNING_KEY` secret. That path is gone. Under the pinned
encoder (≥ 0.2.1215):

- `AXIOM_ENCODE_APPLY_SIGNING_KEY` in the environment is **fatal at startup**; and
- `encode --apply` signs a `v5`/Ed25519 apply manifest through an **externally
  attached** trusted broker — an external Ed25519 signer connected on
  `--apply-signer-fd`, with no unsigned path.

A CI runner cannot self-provision that signer without reintroducing a raw
private key into the runner, which is exactly what the hard cut removes.
axiom-encode's own bulk lane was cut to routing-only for the same reason. So the
migration split the old workflow in two:

- **This workflow's `plan` / `verify-release` jobs (the planner)** — select the
  batch and resolve the pinned toolchain / signed corpus release. No secrets.
- **The signed encode leg (Path B), the `encode` job** — a signer-attached job
  that provisions the trusted signing supervisor with a **production external
  apply signer** (`cmd/axiom-encode-apply-signer` in axiom-encode) and runs
  `encode --apply` under it, producing a `v5`/Ed25519 module + manifest and
  opening one PR per module. Fans out over the `plan` job's matrix seam. Gated:
  it runs on `schedule`, or on `workflow_dispatch` with `-f run_encode=true`.

The `encode` job is the only part that uses the apply signing secret; a plain
plan dispatch (`run_encode` unset) never touches it.

## Pieces

| File | Role |
| --- | --- |
| `bulk/worklist.yaml` | The durable queue. One entry per module (`citation` or `target`). Committed. |
| `bulk/compute_matrix.py` | Turns the worklist into the selection JSON; single source of truth for status/target selection. |
| `bulk/roots_for.py` | Maps a module/target path to `guard-generated --roots` (national `uk`, plus a sub-national root like `uk-kingston-upon-thames`). |
| `.github/workflows/bulk-encode.yml` | The planner: dispatch → selection + pinned toolchain → `bulk-plan.json` + `verify-release`. |

## Running it

Dispatch from the Actions tab (**Bulk encode plan → Run workflow**) or the CLI:

```bash
# Plan the England-pensioner CTR batch (24 entries):
gh workflow run bulk-encode.yml -f batch=CTR-ENP -f limit=24 --repo TheAxiomFoundation/rulespec-uk

# Plan up to 12 pending entries regardless of batch:
gh workflow run bulk-encode.yml -f limit=12 --repo TheAxiomFoundation/rulespec-uk
```

The run produces the `bulk-plan` artifact (`bulk-plan.json`) and exposes the
selection as job outputs (below). The `verify-release` job fetches and verifies
the pinned signed corpus release object from R2; it **fails closed** until the
release is published (set `-f verify_release=false` to skip it while a release
rebind is pending). A `concurrency` group serialises whole dispatches.

The `plan` and `verify-release` jobs use **no** repository secrets. The `encode`
job uses three: `OPENAI_API_KEY` (generation), `BULK_ENCODE_TOKEN` (PR creation),
and `AXIOM_ENCODE_APPLY_SIGNER_ED25519_PRIVATE_KEY` — the raw 32-byte Ed25519
apply seed (base64), delivered only to the one signing step's `env:`. The
launcher reads it, clears it from the environment, and streams it to the signer
over a pipe, so the supervised encoder never sees it. Because this workflow
triggers only on `workflow_dispatch`/`schedule` (never `pull_request`), a fork or
PR-modified workflow can never see the secret.

`AXIOM_ENCODE_APPLY_SIGNING_KEY` (the pre-#1108 HMAC env-var key) is **obsolete**:
it is fatal at encoder startup and no job references it. Delete it from the repo.

### Running the signed encode leg

```bash
# Plan + sign + open PRs for the England-pensioner CTR batch:
gh workflow run bulk-encode.yml -f batch=CTR-ENP -f limit=8 -f run_encode=true \
  --repo TheAxiomFoundation/rulespec-uk
```

Prerequisites (one-time, operator):
- `AXIOM_ENCODE_APPLY_SIGNER_ED25519_PRIVATE_KEY` set as a repository (or org)
  Actions secret to the base64 raw-32 Ed25519 apply seed whose public half is the
  `AXIOM_ENCODE_APPLY_SIGNING_PUBLIC_KEY` Actions variable.
- `AXIOM_ENCODE_REF` (here and in `repository-checks.yml`, in lockstep) pinned to
  an axiom-encode commit that contains `cmd/axiom-encode-apply-signer`.

## What each job does

1. **plan** — reads the strict 3-key `.axiom/toolchain.toml` (rejecting the
   removed pre-#133 keys — the #144 defect), runs `compute_matrix.py
   --status pending` (optionally `--batch`, `--limit`), and emits the plan. No
   network, no supervisor, no signing.
2. **verify-release** — checks out the pinned `axiom-corpus`, fetches the pinned
   signed corpus release object from R2, verifies its name + content sha256, and
   authenticates its provenance commit against the corpus default branch and the
   pinned checkout — mirroring the shared `validate-rulespec` resolution. The
   Ed25519 signature and full grounding are verified downstream by the supervised
   PR CI and the signed encode leg.

The workflow **never** signs, **never** runs `encode --apply`, and **never**
opens PRs. The authoritative gate remains the required `validate / validate`
check (`repository-checks.yml` → the shared, supervised `validate-rulespec`
workflow).

## Handoff to the signed encode leg (the seam)

The signed encode leg (Path B, lane O) attaches to this planner without
reworking selection or resolution. The plan is emitted two ways:

- **Job outputs** `plan.outputs.matrix` and `plan.outputs.count`. `matrix` is
  the `compute_matrix.py --format matrix` result — `{"include": [ … ]}` — so a
  downstream job in this workflow can fan out with:

  ```yaml
  encode:
    needs: plan
    if: ${{ needs.plan.outputs.count != '0' }}
    strategy:
      matrix:
        item: ${{ fromJSON(needs.plan.outputs.matrix).include }}
    # … checkout pinned deps, provision supervisor + attach the external apply
    # signer (--apply-signer-fd), encode --apply --corpus-path _axiom/axiom-corpus,
    # open one PR per module …
  ```

- **`bulk-plan.json`** (the `bulk-plan` artifact) — the same selection enriched
  with the resolved toolchain, dependency pins, corpus release, `corpus_path`,
  and per-entry guard `roots`, for out-of-workflow consumers.

Each selection item is:

```json
{ "citation": "uk/regulation/uksi/2012/2885/11", "target": null,
  "repo": "rulespec-uk", "backend": "openai", "model": "gpt-5.5",
  "slug": "uk-regulation-uksi-2012-2885-11" }
```

`citation` XOR `target` is set (see the worklist schema below); `roots` is added
in `bulk-plan.json`. The signed leg reads `citation` (a corpus path the encoder
resolves) or `target` (a module path / council scope it re-emits), uses the
`pins` to check out the identical toolchain, and runs under the supervisor with
`--corpus-path` = the plan's `corpus_path`.

## Worklist schema

Each entry sets **exactly one** encode target:

- `citation` — a corpus citation path (`uk/statute/<path>` or
  `uk/regulation/<path>`) the encoder resolves against the corpus. The standard
  bulk case.
- `target` — a repo module path or council scope, for council / re-emission
  entries grounded on an ingested manual rather than a corpus citation. For
  example, the Kingston CTR closeout (rulespec-uk#46, #140) would queue:

  ```yaml
  - target: uk-kingston-upon-thames/policies/kingston-upon-thames/council-tax-reduction.yaml
    batch: D
    status: pending
  ```

  The planner selects, slugs, and hands off such an entry; the signed encode leg
  owns how it is encoded. (This is schema support only — no Kingston entry is
  queued here.)

Common fields: `batch` (label), `status` (below), optional `backend`/`model`
(default `openai`/`gpt-5.5`), `repo` (default `rulespec-uk`).

## Statuses

Set in `worklist.yaml`. The planner selects `pending`; humans/follow-ups own the rest.

| Status | Meaning |
| --- | --- |
| `pending` | Queued. The next plan may select it. |
| `in-progress` | The signed leg is encoding it (transient). |
| `needs-fixtures` | Encoded + applied, but the gpt-5.5 companion fixtures hit the #1060 ceiling. The PR opens; auto-merge holds on the red required check until fixtures land. |
| `pr-open` | A PR exists and is set to auto-merge on green. |
| `merged` | The PR merged to main. Terminal success. |
| `failed` | Encode or a non-fixture gate failed. Needs human triage. Never auto-retried, never merged. |

Statuses are updated by committing to `worklist.yaml` (a reviewable diff), not by
silent CI mutation. `compute_matrix.py --set-status <ref> <status>` (where `ref`
is the entry's citation or target) is a local convenience.

## The fixture-split follow-up loop (signed leg)

`--apply` succeeds when the module compiles, validates, and its proof tree
checks. The **companion test fixtures** are a separate quality tier: the #1060
ceiling means gpt-5.5-authored fixtures sometimes fail. When that happens the
signed leg marks the module `needs-fixtures` and still opens the PR, so the
encoded module is reviewable and its auto-merge simply waits. A follow-up pass
then writes correct fixtures (re-derived against the engine, never back-filled),
and once they land the required check goes green and auto-merge completes.

> UK eval-date guard: the eval-date guard applies to test **suites**, not to
> encodes; any test content authored in a fixture pass must use validation
> **year 2026**.

## Failure taxonomy (signed leg)

| Symptom | Class | Action |
| --- | --- | --- |
| `Generated RuleSpec failed CI validation` at apply | apply-blocked | Read `*.repair.json` under the run's `encode-out`; usually a bad generated formula or unresolved import. Re-encode (a new run), do not hand-edit. |
| `points to a RuleSpec file that could not be resolved: rulespec-uk/...` | resolver/layout | The checkout was not the exact canonical `rulespec-uk` country checkout or the module was not under a direct UK jurisdiction's atomic root. The signed leg passes dependency checkouts explicitly; no sibling or symlink fallback is supported. |
| companion test red only | fixtures (#1060) | `needs-fixtures`; run the follow-up fixture pass. |
| self-import / same-section subsection import error | encode#1058 | The section is too cross-reference-heavy for a clean atomic encode. Drop it from the worklist or split the citation to the self-contained fragment. |
| `oracle coverage ... unmapped` on the PR | oracle mapping | The output needs a PolicyEngine/UKMOD oracle mapping entry. Out of scope for the encode leg; handle as a mapping follow-up. |
| 429 from OpenAI | rate limit | Lower `limit`/`max-parallel` or re-dispatch later. The concurrency group prevents overlapping runs. |

## Extending the worklist

Append entries to `bulk/worklist.yaml` in the schema above. For corpus entries,
`citation` is the corpus citation path the encoder resolves (`uk/statute/<path>`
or `uk/regulation/<path>`). Pick self-contained rate/credit/deduction/exemption
sections; **skip** cross-reference-heavy ones (encode#1058) and any known
gate-held sections.

To find candidates mechanically, enumerate un-encoded provisions from the public
corpus view and cross-reference the encoded YAML on main:

```bash
python - <<'PY'
import urllib.request, urllib.parse, json
BASE="https://swocpijqqahhuwtuahwc.supabase.co"
from axiom_encode.harness import validator_pipeline as v
KEY=v.DEFAULT_AXIOM_SUPABASE_ANON_KEY
def q(and_filter):
    params={"select":"citation_path,level,heading,body,has_rulespec",
            "and":and_filter,"order":"citation_path","limit":"1000"}
    p="&".join(f"{k}={urllib.parse.quote(str(x), safe='.*/()-,')}" for k,x in params.items())
    r=urllib.request.Request(f"{BASE}/rest/v1/current_provisions?{p}",
        headers={"apikey":KEY,"Authorization":f"Bearer {KEY}","Accept-Profile":"corpus"})
    with urllib.request.urlopen(r,timeout=90) as resp: return json.loads(resp.read())
# Everything ingested under uk/, then diff against the uk/statutes + uk/regulations tree.
rows=q("(citation_path.gte.uk/,citation_path.lt.ul/)")
print(len(rows), "uk provisions")
PY
```

Then vet each candidate's body: low external cross-reference count (sections,
regulations, schedules), a concrete rate/credit/deduction/definition, non-empty
substantive text. `has_rulespec` in the view can be stale post-merge, so the
authoritative "already encoded" check is the YAML tree on `main`.

## Full-scale bottlenecks (from the pilot report) and mitigations

These serialise a full-scale drain by the signed encode leg. Recorded here so
that leg inherits the analysis.

### 1. Merge serialisation on branch-protection `strict` mode

The dominant serialiser in `rulespec-us` is the **require-branches-up-to-date**
(`strict: true`) branch-protection setting on `main`. With it on, every time one
bulk PR merges, all other open bulk PRs become "behind main", so GitHub
re-queues an auto-update on each and re-runs the required `validate / validate`
check. N open PRs therefore cost O(N) serial validations, no matter how parallel
the encode legs were.

- **Turn `strict` off** for `main`. `validate / validate` still runs on every PR
  and still gates the merge; only the redundant "re-validate because an
  unrelated module merged" churn goes away. Bulk modules are independent
  (disjoint files), so a PR that was green against a slightly older `main` is
  still correct after a sibling module merges. Single highest-leverage change; a
  one-line branch-protection edit.
- **Concurrency-group the dispatch** (already done: `concurrency.group:
  bulk-encode-plan`) so two dispatches never race.

When the signed leg is promoted to full scale, configure `main` protection as:
required check `validate / validate`, **`strict: false`**, and enable repo-level
"Allow auto-merge".

### 2. Reverse-index contention — not applicable here

`rulespec-us` regenerates a full-tree reverse index per bulk PR and commits
`.axiom/index/provisions_to_rules.json`, which two open PRs contend on. **This
repo has no reverse index**, so this contention does not exist. If one is added
later, prefer a **batched** index update (once per drain, in a single follow-up
PR) over per-PR regeneration.

### 3. National shard cost

The `validate / validate` national shard build (engine compile + full-tree
validate) is the per-PR floor. It is inherent to the gate; the mitigations above
reduce *how many times* it runs, not its per-run cost.

### 4. Oracle-coverage gate on new outputs (dominant UK blocker)

The org `validate / validate` required check runs a **changed-file oracle
coverage classifier** (`axiom-encode oracle-coverage --json`, then
`--fail-on-unmapped`). Every output a new module introduces must resolve to a
status other than `unmapped` — either `comparable` (a PolicyEngine oracle
exists) or `known_not_comparable` (explicitly registered as having no comparable
oracle). UK statute/reg outputs (UC/HICBC/HB definitions and mechanics) are
largely un-mapped today, so a freshly encoded output starts life `unmapped`.

The pending ledger records the backlog without turning blocking debt green:

* **Declared debt.** New outputs are declared in the repo-root
  [`oracle-coverage-pending.yaml`](../oracle-coverage-pending.yaml). The gate
  (`axiom-encode` ≥ 0.2.1185) reclassifies a declared `unmapped` output to
  `pending_classification` — visible, counted, and still blocking under
  `--fail-on-pending`. An output declared in neither the mappings nor the
  pending file remains `unmapped` and also blocks.
* **No self-declaration.** The signed encode leg never writes or stages pending
  debt. It runs oracle coverage with `--fail-on-unmapped`, `--fail-on-pending`,
  and `--fail-on-stale-pending`; a new output must be classified before a PR
  opens. (encode#1113: the shared workflow's changed-file gate can ignore
  `oracle-coverage-pending.yaml` on hosted runners when it is rooted one level
  above the checkout; the signed leg roots oracle-coverage at the checkout
  itself, avoiding that collision.)
* **Ratchet down.** `tests/test_oracle_coverage_pending.py` runs
  `oracle-coverage-pending check` both ways: an undeclared unmapped output
  fails, and a declaration whose output is now classified upstream is **stale**
  and must be removed.
* **Sweep drains it.** A periodic classification sweep maps declared outputs in
  one batch `axiom-oracles` change and bumps the pin once — not per PR. Track the
  drain in issue #101. The CTR outputs mitigate via real mappings
  (axiom-oracles#278, merged).

The UK queue remains intentionally paused while live pending classifications
exist. Drain them through reviewed oracle mappings or explicit
`known_not_comparable` decisions before resuming bulk encoding.
