Cold-start only. Never restate what `pm status` computes.

# 0.4.0 authoring is separate from binding — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.4.0-authoring-is-separate-from-binding`, pushed, clean |
| **Version** | `pyproject.toml` stays `0.2.0` — this tree bumps at CLOSE, in the release commit, which is why `check pm` D8 is off in `devkit.toml` |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc/.claude/worktrees/0.4.0` — a worktree NESTED inside the main tree at `.claude/worktrees/0.4.0`. No file records this; only `git worktree list` does. **Another agent is building 0.3.0 in the main tree at `/Users/cdowin/workspace/agentic-sdlc`** — stay out of it; you share only the object store. |

## 2. Where to pick up

**`one-rule-routes-a-row/01-routing-asks-the-grain-not-the-tree`.** Written, and it is what stops
telemetry rows being refused. The five telemetry features run before everything else;
`milestone.md` § Pre-work argues why.

Orient first:

```bash
git log --oneline 386f691..HEAD              # the commit messages carry the arguments
make -s pm ARGS="status 0.4.0"               # every feature, state, story count
make -s pm ARGS="ledger report"              # spend per grain; what gates have cost
make help                                    # authoritative target list
PYTHONPATH=src python3 -m agentic_sdlc.cli verify --plan   # the rungs, measured
grep -h '^depends_on' pm/roadmap/0.4.0-*/features/*/feature.md
```

Then `milestone.md` → `decisions.md` (**D1–D6, each with its rejected alternative — read them,
don't re-litigate them**) → the feature → its stories. Open `.claude/rules/pm-execution.md` with
`Read`; it auto-loads on `pm/roadmap/**` and **a Bash `cat` does not trigger it**.

Unblocks after: `recording-is-on-or-the-gate-is-red` (deps on it), then the rest of the graph.

## 3. Traps this milestone has already sprung

**Telemetry was recording nothing, silently, for the whole of 0.3.0 — and still is in the main
tree.** Looked true: hooks installed, executable, self-testing, firing. Actually true: they write
into the one `in_progress` milestone's ledger, no milestone was `in_progress`, and they fail open
to a stderr nobody reads. Surfaced by asking why `pm/roadmap/` held exactly one `ledger.jsonl`.
Flipping this milestone to `building` turned it on here. **D1 deletes the cause.**

**A `Write`/`Edit` into this worktree may be BLOCKED** if your session is rooted in another repo —
NullBound's `cc-write-confine.sh` does exactly that. Looked like a permissions glitch; actually the
guard working correctly against a misconfigured session. **Bash heredocs are not confined**, so the
failure pushes you silently onto the unguarded write path. Fix: a line in that repo's
`tools/hooks/extra-write-roots.local` naming **only this worktree** — never
`/Users/cdowin/workspace/agentic-sdlc`, so the guard keeps protecting the main tree. Already
granted on this machine.

**`git worktree add` here (git 2.50.1) set `core.bare = true` on the main repo** and made it
unusable for ~2 minutes. Check `git config core.bare` after adding one. Reads `false` now.

**This file was written three times before it was right, and the gate was correct every time.**
First draft: 194 lines restating `pm status`, the dep graph, the rung costs and the commit log.
`[grain_shape]`'s 120-line cap rejected it twice and the response was to shave prose — treating a
gate as an obstacle. What was actually true: **the package already ships this template**
(`src/agentic_sdlc/repo/pm/templates/handoff.md`), its first line already says *"Never restate what
`pm status` computes"*, and `SLOT_HEADER` calls that line *"the one channel that reaches a
dispatched subagent"*. All of it was bypassed by creating the file with `Write` instead of
`pm new milestone 0.4.0`, which is idempotent and fills empty slots. **If you need a shared doc,
scaffold it — don't author it.**

**`make check` runs ~36s cold in this worktree against a 2.2s median.** `verify --plan` shows
medians; it cannot know your cache is cold. Budget the max column, not the median.

**Omit `--tokens-in`/`--tokens-out` on hand ledger rows** unless you have real token counts. A
harness remaining-budget counter is not one, and the contract is *"a number not given is a key the
row does not carry, never a zero"*. The `Stop` hook reads real numbers off the transcript.

**Standing don'ts** not derivable from the tree: don't rewrite pushed history; don't add a filter
flag to a read verb (if you can't pipe it, the missing thing is a **column**); don't make an
optional config key required (`[pm.states.*]` earned that once and cost a consumer its PM CLI);
don't build the migration before `pm rename` exists. Lessons go in `/improvements.md` at the repo
root — outside the tree, because 0.4.0 migrates the tree.
