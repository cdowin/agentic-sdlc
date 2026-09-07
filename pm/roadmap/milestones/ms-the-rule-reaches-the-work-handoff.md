Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-the-rule-reaches-the-work the rule reaches the work — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.6.0-the-rule-reaches-the-work`, pushed. `main` is merge-commit-only at close. |
| **Version** | 0.6.0. **This project bumps at CLOSE, not at start** (D8 is off in `devkit.toml` for that reason), so both version sites still read 0.5.0 until `release` runs. |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc`. One worktree, shared: up to four dispatched agents edited it concurrently for most of this milestone. |

## 2. Where to pick up

```bash
pm ready-for milestone ms-the-rule-reaches-the-work   # what is left, by name
pm status ms-the-rule-reaches-the-work                # every grain and its state
agentic-sdlc changelog ms-the-rule-reaches-the-work   # what shipped, in `order:`
pm ledger report ms-the-rule-reaches-the-work         # spend and time per state
verify --plan                                         # the rungs, with measured cost
```

Reading order: `ms-the-rule-reaches-the-work-decisions.md` **before any feature file** — D1 (a parent
does not close over unresolved children), D2 (a retired FIELD is drift, not a config error), D3 (the
remote reader reads refs and never spawns) and D4 (rule 1 names the surface its reason protects) each
carry a rejected alternative that will otherwise be re-argued.

## 3. Traps this milestone has already sprung

**A gate on the hot path is a rule-2 violation the tests find, not the reviewer.** The remote reader
first ran `git rev-list` for a commit count. `arrive.census()` is called by every `pm` write and by
`check pm`, so that put a subprocess on the hot path of verbs whose whole contract is that they boot
nothing — and 235 cases in the `not shell` tier failed **by nodeid**, each saying *tried to spawn a
process*. Rule 2 has no fast path. The reader now reads `.git/` as text and answers *published* and
*in sync*; it does not answer HOW FAR ahead, because that needs a graph walk (D3).

**The prose census has ~17 lines of headroom and it will bite you.** `tests/test_prose_census.py`
holds `src/` comments+docstrings under 1/3 of code. It failed on nearly every feature here, and six
separate rounds of comment-trimming were spent on it — which is precisely what this milestone's own
brief says not to do. **Two placements that are not trimming**: help text belongs in a module-level
`USAGE` constant (a string assignment is CODE), and a rejected alternative belongs in `pm decide`.
Filed as `bg-the-prose-ceiling-has-no-headroom`, unbound in the pool.

**A shared worktree plus `git add -A` swept three agents' in-flight work into one commit.** Two of
them reported it. **Commit by explicit pathspec while anything else is running**; the story belt's
`committed` check says so and it is right.

**`check doc` had no test module and the reason was structural** — `REPO_ROOT` is captured at import,
so `relative_to` raises on a scratch tree and no case could build one. A `rel()` helper at the five
reporting sites fixed it. `checks/doc.py` still holds 12 other module-level `REPO_ROOT` uses;
converting the constant is the vocabulary sweep's, and it was deferred.

**Two ship criteria could not be met literally and were SCOPED, not faked.** *"No shipped file states
what a verb does in prose that the verb does not generate"* is not mechanisable in general; the sharp
slice landed and the grain says which half did not. The read-verb feature's collect-and-render
primitive did not land at all, for the reason its own text gives. Both are written into their grain
files under "What landed, and what did not" — **look there before assuming a criterion was met.**

**The tree can measure everything except its own dispatches.** `pm ledger report` shows `0 dispatch
row(s)` after six dispatched agents: every token, tool-call and duration column is `-`. Whether a
harness fires `SubagentStop` here depends on the session's project root, not on
`.claude/settings.json`, and nothing exports `GDK_LEDGER_GRAIN`. `check pm` U4 has said so correctly
for five milestones. Filed as `bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty`.
