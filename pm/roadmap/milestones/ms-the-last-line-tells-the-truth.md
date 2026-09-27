---
id: "ms-the-last-line-tells-the-truth"
kind: milestone
name: the last line tells the truth
status: planning
depends_on: []
branch: milestone/0.15.0-the-last-line-tells-the-truth
mode: parallel
version: 0.15.0
changelog:
order:
  - "ft-a-verdict-is-the-last-line"
  - "ft-a-gate-reads-what-this-run-did"
  - "ft-an-arrival-names-what-it-starts"
  - "ft-a-template-grows-without-a-fork"
---

# 0.15.0 — the last line tells the truth

**A small fix release from the issues open on 2026-09-21, plus four filed by 2026-09-27**, all
from one consumer's 0.91–0.93 milestones. The common thread: the line an operator reads — a
verdict, a footer, a gate row, an arrival — says less than, or other than, what the run did.

    #70 #71 #72      → ft-a-verdict-is-the-last-line
    #67 #74 #77      → ft-a-gate-reads-what-this-run-did
    #68 #69 #66 #79  → ft-an-arrival-names-what-it-starts
    #78              → ft-a-template-grows-without-a-fork
    #73              → not this package: deriving suites from changed files is inference (rule 9)
                       over a consumer's own refs index (rule 8); `[verify] story` is the consumer's
                       declared target, and that target can derive its suite set
    #75              → not this package (rule 8): the pre-commit `loc` hook and `make loc` are the
                       consumer's; transferred to cdowin/godot-devkit

Part of three issues is declined on purpose, and each issue's close says which part:
#68 names the edit and does not stamp the file (rule 3); #72 moves roadmap dirt to a WARN and
does not commit (rules 3, 9); #69 warns and does not refuse (rule 9).

## Mode

PARALLEL, four lanes in `tools/dev/agent-worktree.sh` worktrees. Lane files are disjoint except
`README.md`, `devkit.toml`'s seed (lane 3's `arrival_gates`, lane 4's `extra_sections`),
`core/config.py` (the same two keys) and `repo/conveyor/steps.py` (lane 1 reads `_uncommitted`,
lane 2 edits `check_gate`, lane 3 edits `_passes`); these merge textually.

## Ship criterion

Every feature's criterion holds, `make milestone` is green, and each issue above is closed citing
a hash or, for #73 and #75, the rule.

## Risks

- #70 changes the `check` recipe every consumer runs through `install-gates`. Its test must run
  the real recipe once.
- #69 adds a spawn to `pm`. It runs only when a project declares `arrival_gates`; stock stays
  pure text (rule 2).
- #79 filters the blocks a close reads. A filter that drops a block it should keep is a close
  that passes on an open MAJOR (rule 4). The test keys one block to a wrong id and proves refusal.
- #74 reuse must never serve a green verdict for a tree it did not grade (rule 4). The test edits
  one tracked file and proves the gate runs again.
