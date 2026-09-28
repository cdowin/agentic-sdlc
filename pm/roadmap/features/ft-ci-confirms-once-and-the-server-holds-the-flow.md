---
id: ft-ci-confirms-once-and-the-server-holds-the-flow
kind: feature
milestone: "ms-the-rules-hold-everywhere"
name: CI confirms once and the server holds the flow
status: done
reviewed: docs/reviews/2026-09-28-0.16.0-ci-confirms-once.md
depends_on: []
consumed_by: []
changelog: install-ci writes a verify workflow that runs once per PR, cancels a stale run and times out, and `install-ci --ruleset branch|tag` prints one GitHub ruleset as bare JSON, holding merge-commit-only main or immutable v* tags.
---

# CI confirms once and the server holds the flow

Issues: #82 #83.

CI is the one confirmation at merge: the hooks and belts already run the gates on
every commit. And the flow's server-side rules ship as a payload, because a first-hand ruleset had
two mistakes the flow forbids (`required_linear_history`, `rebase` as a merge method).

## Decided (do not re-plan)

- **#82 — `src/agentic_sdlc/repo/installables/ci-verify.yml`.** `on:` becomes `pull_request:
  branches: ["main"]` + `workflow_dispatch`; drop `push`. Add top-level `concurrency: { group:
  verify-${{ github.ref }}, cancel-in-progress: true }`. Add `timeout-minutes: 30` on the job and
  `retention-days: 3` on the red-run upload. Literal values in the template, not config keys: the
  header already says the file is the consumer's after install. The header gains two sentences:
  CI is the confirmation at merge, and no `paths-ignore` because a skipped REQUIRED check blocks
  the merge. Re-install this repo's `.github/workflows/verify.yml` with `install-ci --force`.
- **#83 — `install-ci --ruleset`.** A new flag on the existing verb (minor). It PRINTS, writes
  nothing, exits 0: two JSON documents, each preceded by the `gh api -X POST
  repos/<owner>/<repo>/rulesets --input -` line that applies it (`<owner>/<repo>` literal
  placeholders; the tool reads no remote, rule 2). Branch payload: name `protected-main`, target
  `~DEFAULT_BRANCH`, rules `deletion`, `non_fast_forward`, `pull_request` (0 approvals,
  `allowed_merge_methods: ["merge"]`, every other param false/empty), `required_status_checks`
  (context = the job id in ci-verify.yml, read from the template, never a second literal;
  `integration_id` 15368, strict false); bypass: RepositoryRole 5 (admin), mode `pull_request`.
  NO `required_linear_history`. Tag payload: `release-tags-immutable`, `refs/tags/v*`, rules
  `deletion` + `update`, no bypass. One comment line above each payload says why (approvals 0: a
  solo maintainer cannot approve their own PR, and a bypass skips the required check too).
- **Surfaces (rule 11):** `install-ci --help` names `--ruleset`; README install row; SDLC.md
  section 1 bullet "`main` is merge-commit-only" gains "held on the server by `install-ci
  --ruleset`".

## Ship criterion

- `install-ci` into a scratch repo writes a verify.yml with no `push:` trigger, a `concurrency`
  block and `timeout-minutes`.
- `install-ci --ruleset` stdout parses as two JSON payloads; the branch one has no
  `required_linear_history`, allows only `merge`, and requires the template's job id; the tag one
  has `deletion` and `update` and no bypass. Nothing written.

## Proof budget

<!-- Roughly how many test cases this feature should cost, written before it is
     built and compared after. Name the tier and the existing module they land
     in; say what the suite already checks and why that is not enough. -->

  cases: 2 (amend the install-ci case for the triggers; one new case for --ruleset)
  tier: unit (a function call, no process)
  lands in: tests/test_install.py
  what already covers this: install-ci's write and --force cases; nothing reads the triggers.
