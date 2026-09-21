Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-the-last-line-tells-the-truth the last line tells the truth — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.15.0-the-last-line-tells-the-truth`, cut from `main` at `1d32b65` |
| **Version** | 0.15.0. This repo bumps at close (D8 off): `release` moves both version sites |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc`. No worktrees yet; each lane makes its own with `tools/dev/agent-worktree.sh new <slug> milestone/0.15.0-the-last-line-tells-the-truth` |

## 2. Where to pick up

Planned, not started. Every feature is `planning` and every issue has a disposition comment.
The next action is `run-the-sdlc`: three lanes in parallel, one developer per feature, briefed
from each feature's `## Decided` section. Do not re-plan.

```bash
git log --oneline main..HEAD
pm status ms-the-last-line-tells-the-truth
make sdlc ARGS='dispatch --grain <feature-id>'
```

Reading order: `ms-the-last-line-tells-the-truth-decisions.md` (D1–D3, chosen by Chris), then
the milestone file (issue → feature map), then each feature. At release, close #66–#72 and #74
with a hash each; #73 is already closed.

## 3. Traps this milestone has already sprung

- **#72 is not the belts.** `release`'s `tree-clean` and the story belt's `committed` already
  exclude `[pm] root` (`_uncommitted`, `repo/conveyor/steps.py`). The refusal the issue reports
  comes from `check repo-hygiene`, which is stock-off and not in this repo's roster. A probe for
  the fix needs `repo-hygiene` turned on in the scratch tree.
- **#67 cannot reproduce here by default.** Locally the gate rows live in `ledger.local.jsonl`, so
  `check budget` passes. The failure needs a tree with an empty local ledger and old FAIL gate
  rows in the tracked ledger.
- **Lanes share three files**: `README.md`, the `devkit.toml` seed (lane 3's `arrival_gates`), and
  `repo/conveyor/steps.py` (lane 1 reads `_uncommitted`, lane 2 edits `check_gate`). Merge in any
  order; expect textual merges only.
- **`run-the-sdlc.md` is edited only by lane 3**, including the step-10 `verify --milestone` line
  that lane 2's #74 needs.
