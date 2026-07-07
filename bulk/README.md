# Bulk encode (UK)

A durable queue → runner → PR loop for bulk RuleSpec encoding, independent of
any local session. It encodes already-ingested UK provisions with
`axiom-encode encode <citation> --apply`, pre-checks them with the same gate
battery the PR CI runs, opens one PR per module, and lets each PR auto-merge on
green.

This is the UK port of the `rulespec-us` dispatcher. The encoder and the CI
gates own correctness. This system is **plumbing**: it never edits or invents
generated values. Its only judgement is *which* provisions to queue.

## Pieces

| File | Role |
| --- | --- |
| `bulk/worklist.yaml` | The durable queue. One entry per module. Committed. |
| `bulk/compute_matrix.py` | Turns the worklist into the CI job matrix; single source of truth for status selection. |
| `bulk/roots_for.py` | Maps an applied module path to `guard-generated --roots` (national root `uk`). |
| `.github/workflows/bulk-encode.yml` | The runner: dispatch → matrix → encode `--apply` → gate battery → PR + auto-merge. |

## Running it

Dispatch from the Actions tab (**Bulk encode → Run workflow**) or the CLI:

```bash
# Encode the first 4 pending batch-A entries (the pilot batch):
gh workflow run bulk-encode.yml -f batch=A -f limit=4 --repo TheAxiomFoundation/rulespec-uk

# Encode up to 12 pending entries regardless of batch:
gh workflow run bulk-encode.yml -f limit=12 --repo TheAxiomFoundation/rulespec-uk
```

The `schedule` trigger runs weekly and drains any remaining `pending` entries
with no human action. Parallelism is capped at 4 (`max-parallel`) to stay under
OpenAI rate limits; a top-level `concurrency` group serialises whole dispatches
so two runs never fight over the same `bulk/<slug>` branches.

### Secrets (repo Actions secrets on rulespec-uk)

| Secret | Why |
| --- | --- |
| `OPENAI_API_KEY` | Headless `--backend openai` generation. |
| `AXIOM_ENCODE_APPLY_SIGNING_KEY` | Signs the apply manifest so `guard-generated` accepts the new files. Must match the key that signs manifests elsewhere. |
| `BULK_ENCODE_TOKEN` | A `repo`+`workflow`-scoped token used to push the branch and open the PR. **Required**: PRs opened by the default `GITHUB_TOKEN` do **not** trigger the `pull_request` event, so the required `validate / validate` check would never run and auto-merge would hang forever. This token makes the PR a real event that triggers CI. |

## What each job does

1. **dispatch** — installs PyYAML, runs `compute_matrix.py --status pending`
   (optionally `--batch`, `--limit`), and emits the matrix.
2. **encode** (one leg per module, ≤4 parallel):
   - Checks out the repo into a leaf dir named exactly `rulespec-uk` (the
     `--apply` resolver requirement) using `BULK_ENCODE_TOKEN`.
   - Reads `.axiom/toolchain.toml` and checks out **the pinned** `axiom-encode`,
     `axiom-rules-engine`, and `axiom-corpus`, then builds the engine. Using the
     pinned encoder means generation and the downstream PR CI validate with the
     identical version — no version-skew surprises.
   - Runs `axiom-encode encode <citation> --apply`. `--apply` validates the main
     file, companion test, and direct dependents in a temporary overlay and
     writes nothing on failure (fail-closed), then installs the three artifacts:
     `uk/**/<sec>.yaml`, `<sec>.test.yaml`, and a signed
     `uk/.axiom/encoding-manifests/**/<sec>.json`.
   - Runs the gate battery in PR-CI order: `guard-generated` (manifest present),
     `validate --skip-reviewers`, `proof-validate`, then the companion `test`.
   - Opens `bulk/<slug>` with the manifest summary + gate output as the PR body,
     labels it `bulk-encode`, and runs `gh pr merge --auto --squash`.

The job **never** uses `--admin`, never bypasses a red check, and never merges
directly. The authoritative gate is the repository's required
`validate / validate` check on the PR.

### Difference from rulespec-us: no reverse index

`rulespec-us` maintains a committed provision → rules reverse index
(`tests/generate_reverse_index.py` → `.axiom/index/provisions_to_rules.json`)
and its bulk job regenerates + stages that artifact on every module. This repo
carries no such artifact, so there is **no index-regeneration step** here. If a
reverse index is added to rulespec-uk later, mirror the rulespec-us step (a
`git add` of the regenerated JSON alongside the module, its test, and its
manifest) so the reverse-index CI check stays green.

## Statuses

Set in `worklist.yaml`. The runner reads `pending`; humans/follow-ups own the rest.

| Status | Meaning |
| --- | --- |
| `pending` | Queued. The next dispatch may pick it up. |
| `in-progress` | A run is encoding it (transient). |
| `needs-fixtures` | Encoded + applied, but the gpt-5.5 companion fixtures hit the #1060 ceiling. The PR opens; auto-merge holds on the red required check until fixtures land. |
| `pr-open` | A PR exists and is set to auto-merge on green. |
| `merged` | The PR merged to main. Terminal success. |
| `failed` | Encode or a non-fixture gate failed. Needs human triage. Never auto-retried, never merged. |

Statuses are updated by committing to `worklist.yaml` (a reviewable diff), not by
silent CI mutation. `compute_matrix.py --set-status <citation> <status>` is a
local convenience.

## The fixture-split follow-up loop

`--apply` succeeds when the module compiles, validates, and its proof tree
checks. The **companion test fixtures** are a separate quality tier: the #1060
ceiling means gpt-5.5-authored fixtures sometimes fail. When that happens the
runner marks the module `needs-fixtures` and still opens the PR, so the encoded
module is reviewable and its auto-merge simply waits. A follow-up agent pass
then writes correct fixtures (re-derived against the engine, never back-filled),
and once they land the required check goes green and auto-merge completes.

> UK eval-date guard: the eval-date guard applies to test **suites**, not to
> encodes; any test content authored in a fixture pass must use validation
> **year 2026**.

## Failure taxonomy

| Symptom | Class | Action |
| --- | --- | --- |
| `Generated RuleSpec failed CI validation` at apply | apply-blocked | Read `*.repair.json` under the run's `encode-out`; usually a bad generated formula or unresolved import. Re-encode (a new run), do not hand-edit. |
| `points to a RuleSpec file that could not be resolved: rulespec-uk/...` | resolver/layout | The checkout leaf dir was not `rulespec-uk`, or a sibling checkout was missing. The workflow guards the leaf-dir name; check the sibling symlink step. |
| companion test red only | fixtures (#1060) | `needs-fixtures`; run the follow-up fixture pass. |
| self-import / same-section subsection import error | encode#1058 | The section is too cross-reference-heavy for a clean atomic encode. Drop it from the worklist or split the citation to the self-contained fragment. |
| `oracle coverage ... unmapped` on the PR | oracle mapping | The output needs a PolicyEngine/UKMOD oracle mapping entry. Out of scope for the encode job; handle as a mapping follow-up. |
| 429 from OpenAI | rate limit | Lower `limit`/`max-parallel` or re-dispatch later. The concurrency group prevents overlapping runs. |

## Extending the worklist

Append entries to `bulk/worklist.yaml` in the existing shape. `citation` is the
corpus citation path the encoder resolves (`uk/statute/<path>` or
`uk/regulation/<path>`). Pick self-contained rate/credit/deduction/exemption
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

Two effects serialise a full-scale drain. This section records what applies to
**this** repo and what does not.

### 1. Merge serialisation on branch-protection `strict` mode

The dominant serialiser in `rulespec-us` is the **require-branches-up-to-date**
(`strict: true`) branch-protection setting on `main`. With it on, every time one
bulk PR merges, all other open bulk PRs become "behind main", so GitHub
re-queues an auto-update on each and re-runs the required `validate / validate`
check (whose federal `us` shard is ~13 min, Supabase-throttled). N open PRs
therefore cost O(N) serial ~13-min validations, no matter how parallel the
encode legs were.

Cheap workflow-level mitigations available:

- **Turn `strict` off** for `main`. `validate / validate` still runs on every
  PR and still gates the merge; only the redundant "re-validate because an
  unrelated module merged" churn goes away. Bulk modules are independent
  (disjoint files), so a PR that was green against a slightly older `main` is
  still correct after a sibling module merges — the up-to-date requirement buys
  nothing here and costs a full re-validation per merge. This is the single
  highest-leverage change and is a one-line branch-protection edit, not a code
  change.
- **Concurrency-group the encode dispatch** (already done: `concurrency.group:
  bulk-encode`, `cancel-in-progress: false`) so two dispatches never race on the
  same `bulk/<slug>` branches. This bounds *encode* contention but does not by
  itself change *merge* serialisation, which is governed by branch protection.

When this UK dispatcher is promoted to full scale, configure `main` protection
as: required check `validate / validate`, **`strict: false`**, and enable
repo-level "Allow auto-merge". That reproduces the rulespec-us gate semantics
without importing the rulespec-us `strict`-mode merge serialisation.

### 2. Reverse-index contention — not applicable here

In `rulespec-us`, each bulk PR also regenerates the full-tree reverse index and
commits `.axiom/index/provisions_to_rules.json`. Two open PRs both touch that one
file, so after the first merges the second's committed index is stale relative
to `main`, forcing a rebase/regenerate. **This repo has no reverse index**, so
this contention does not exist here. If a reverse index is added later, prefer a
**batched** index update (regenerate once per drain in a single follow-up PR)
over per-PR regeneration, precisely to avoid reintroducing this serialiser.

### 3. Federal/national shard cost

The `validate / validate` national shard build (engine compile + full-tree
validate) is the per-PR floor. It is inherent to the gate and out of scope for
the dispatcher to change; the mitigations above reduce *how many times* it runs,
not its per-run cost.

### 4. Oracle-coverage gate on new outputs (dominant UK blocker) — out of scope

The pilot batch (`batch=A`, 4 entries) exposed the real gate for UK bulk PRs.
The org `validate / validate` required check runs a **changed-file oracle
coverage classifier** (`axiom-encode oracle-coverage --json`, then
`--fail-on-unmapped`). Every output a new module introduces must resolve to a
status other than `unmapped` — either `comparable` (a PolicyEngine oracle
exists) or `known_not_comparable` (explicitly registered as having no
comparable oracle). On the current merged UK tree, coverage is
18768 `known_not_comparable` + 1032 `comparable` + **0 `unmapped`**: every
existing output is already classified.

A freshly bulk-encoded output starts life `unmapped`, so the classifier fails
and auto-merge correctly holds on the red required check. This is **not** a
dispatcher defect and there is **no cheap workflow-level mitigation**: the
classification is a quality decision owned by `axiom-oracles` +
`axiom-encode classify`, exactly like the companion-fixture tier. The plumbing's
job ends at producing a reviewable PR with a signed manifest and armed
auto-merge; a mapping follow-up (register each new output as `comparable` with
its oracle, or `known_not_comparable`) is what turns the check green, after
which auto-merge completes on its own.

Contrast with `rulespec-us`, where many bulk targets (e.g. NY Article 22 income
tax) map to existing PolicyEngine oracles and merge green without a mapping
step. UK statute/reg outputs (UC/HICBC/HB definitions and mechanics) are largely
un-mapped today, so the mapping follow-up is the throughput-limiting step for a
UK drain — plan a mapping pass per batch alongside the fixture pass.

**Pilot result (batch A, 2026-07-07):** dispatch → matrix → pinned-toolchain
encode ran on all 4 legs. 3 legs (ITEPA s681B/s681G, WRA s7) hit the encoder's
fail-closed compile-validation gate at apply (`apply-blocked`; re-encode
territory, not plumbing). 1 leg (WRA s39) applied cleanly, and the manifest
detector correctly located and staged its signed manifest — PR #97 opened with
module + companion test + manifest and auto-merge armed, holding only on the
`unmapped` oracle-coverage check above. The dispatcher path is verified
end-to-end; the remaining blockers are the encoder (quality) and oracle mapping
(coverage), both by-design outside this plumbing.
