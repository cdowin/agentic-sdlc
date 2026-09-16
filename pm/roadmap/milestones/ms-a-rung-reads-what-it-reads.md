---
id: "ms-a-rung-reads-what-it-reads"
kind: milestone
name: a rung reads what it reads
status: building
depends_on: []
branch: feat/release-0-13-0
mode:
version: 0.13.0
changelog: **A rung reuses its last green.** `[verify.inputs]` keys a rung on the paths its target reads, so a status flip or a doc edit no longer re-runs a tier; four agents install instead of twelve; tree writes ride code commits; a quiet agent stop runs no unit tier.
---

# ms-a-rung-reads-what-it-reads — a rung reads what it reads

<!-- Theme: one paragraph. What can a user DO or SEE when this ships? -->

## Ship criterion

<!-- What "done" means, in observable terms. -->

## Risks

Two merged PRs, cut as a release so consumers can pin them: #54 (`[verify.inputs]`, the story and
feature rungs reuse on tree state) and #55 (four installed agents, tree writes ride code commits,
no unit tier on a quiet stop, no hand-written ledger record). Measured on a consumer on
2026-09-16: 140 of 141 unit runs were new whole-tree states, review time beat build time on every
feature, and 47% of commits touched only the PM tree.
