Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-the-last-line-tells-the-truth the last line tells the truth — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.15.0-the-last-line-tells-the-truth`, cut from `main` at `1d32b65`. `main` has one later commit, `7ee1928` (#65, a pool feature file only); the release merge carries it |
| **Version** | 0.15.0. This repo bumps at close (D8 off): `release` moves both version sites |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc`. No worktrees yet; each lane makes its own with `tools/dev/agent-worktree.sh new <slug> milestone/0.15.0-the-last-line-tells-the-truth` |

## 2. Where to pick up

Planned, not started. Every feature is `planning` and every issue has a disposition comment.
The next action is `run-the-sdlc`: six lanes in parallel, one developer per feature, briefed
from each feature's `## Decided` section. Do not re-plan.

```bash
git log --oneline main..HEAD
pm status ms-the-last-line-tells-the-truth
make sdlc ARGS='dispatch --grain <feature-id>'
```

Reading order: `ms-the-last-line-tells-the-truth-decisions.md` (D1–D11, chosen by Chris), then
the milestone file (issue → feature map), then each feature. At release, close #66–#72, #74 and
#77–#79 with a hash each; #73 is closed and #75 is transferred to cdowin/godot-devkit.

## 3. Traps this milestone has already sprung

- **#72 is not the belts.** `release`'s `tree-clean` and the story belt's `committed` already
  exclude `[pm] root` (`_uncommitted`, `repo/conveyor/steps.py`). The refusal the issue reports
  comes from `check repo-hygiene`, which is stock-off and not in this repo's roster. A probe for
  the fix needs `repo-hygiene` turned on in the scratch tree.
- **#67 cannot reproduce here by default.** Locally the gate rows live in `ledger.local.jsonl`, so
  `check budget` passes. The failure needs a tree with an empty local ledger and old FAIL gate
  rows in the tracked ledger.
- **Each guidance and agent file has ONE owning lane.** The milestone file's `## Mode` lists them.
  Brief each developer with it: an edit to a file another lane owns is a merge conflict.
- **#77 does not reproduce from a session inside the worktree.** The guard fails only when the
  session cwd is the main checkout and the command targets a worktree by `cd` or `-C`.
- **`run-the-sdlc.md` is edited only by `ft-the-loop-learns-what-the-fork-learned`**, including
  #66 and the step-10 `verify --milestone` line that lane 2's #74 needs.
- **Lanes 5 and 6 port from a consumer's fork.** The source is that consumer's `.claude/agents/`,
  `.claude/skills/` and `.claude/rules/`, read at 2026-09-27. Port the rule, never its nouns
  (rule 8). The briefs already hold the generic text; the developer does not need the fork.
