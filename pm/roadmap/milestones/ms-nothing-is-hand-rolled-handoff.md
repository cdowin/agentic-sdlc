Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-nothing-is-hand-rolled nothing is hand-rolled — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.7.0-nothing-is-hand-rolled`, tracking the same name on `origin`. Merges to `main` as a merge commit at the close (`SDLC.md`). |
| **Version** | 0.7.0. Bumped at CLOSE, not at start — this tree turns D8 off deliberately, and `agentic-sdlc release 0.7.0` moves both version sites (rule 7). |
| **Tree** | `/home/user/agentic-sdlc`, one checkout, no worktrees live. A review pass ran in a detached worktree at `5f42df6` because the live tree was mid-surgery; that worktree is gone. |

## 2. Where to pick up

```bash
pm status ms-nothing-is-hand-rolled   # 2 features, their story counts
pm list --status planning,ready,building
pm list --kind bug --milestone ms-nothing-is-hand-rolled
pm ledger report                      # spend per grain, and what the gates cost
verify --plan                         # the rungs, with the cost each last took
```

Reading order: this milestone's `decisions.md`, then the feature brief, then the story. The
milestone doc's "The measurement" numbers are a 2026-09-10 reading and several are now stale by
design — the stories that corrected them say so in their closes.

## 3. Traps this milestone has already sprung

**A pathspec commit does not scope to a story.** `f7a8114` captured a concurrent agent's
`test_pm_gate.py` amendment because both stories touched that one file; the other story's −8 prose
cut was silently lost and only the feature review found it. Name files, and check `git status`
belongs to you before `git add`.

**`close story` refuses while any peer agent holds uncommitted work.** Its `committed` check cannot
scope to one story, and `--force` on that is a lie on the record. Wait for a quiet tree; do not
batch concurrent dispatches that write.

**The pre-push hook gates the WORKING TREE, not the commit.** A push mid-refactor fails on another
agent's half-finished edits. `--no-verify` is not the answer; a quiet tree is.

**Never hand-roll a census this tree can answer.** The `src/` prose ratio reads 0.3426 from a naive
loop and 0.3221 from the real one, because 224 published `--help` lines count as code (0.6.0/D7).
`agentic-sdlc cite` and the census cases print the real numbers. Two milestones running, two briefs
quoting hand-rolled numbers that were wrong — that is what this milestone is named against.

**A story body at exactly 200 lines has no room for its own `done:` line.** The cap counts the whole
file. Write the close to 195.

**`GDK_LEDGER_GRAIN` cannot be exported by an orchestrator whose shell state does not persist
between tool calls.** Use `pm ledger record --grain <id> --tokens-total N --tool-calls N
--duration-s N` off the numbers the dispatch reports back, after each agent returns.

**A brief that names one offender has usually found one of several.** Every gate written this
milestone that was asked to fail at HEAD failed with MORE offenders than the grain named —
`NoNameIsBoundTwice` found three where the bug said one, two of them in a different file. Run the
gate before believing the census.
