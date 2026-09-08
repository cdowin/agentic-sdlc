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
carry a rejected alternative that will otherwise be re-argued. D5-D8 were taken at the CLOSE and
each is a rule NARROWED or a measurement ruled on: a warning fires only where an answer exists;
registration is counted, never asserted; a printed docstring is output; and the path-triggered tier
reaches less than the always-loaded one.

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
Filed as `bg-the-prose-ceiling-has-no-headroom` — **bound and CLOSED at this milestone's own
close (D7)**, after two more placement moves and nine lines still over. A printed `--help`
docstring now counts as the output it is. 276 lines of headroom; the ceiling is still 1/3.

**A shared worktree plus `git add -A` swept three agents' in-flight work into one commit.** Two of
them reported it. **Commit by explicit pathspec while anything else is running**; the story belt's
`committed` check says so and it is right. **The hook that enforces this was not running** and
`check hooks` said `PASS — armed` over it for five milestones — `core.hooksPath` arms git's two
hooks and nothing arms the five `cc-*` ones (D6). It is still not running here: a session rooted
above the checkout loads no `.claude/settings.json`. Two agents also planted probes in `src/` during
one review pass, each briefly visible to the other (0.6.0 review S9), so a reviewer asked to plant
anything in this tree should expect company.

**`check doc` had no test module and the reason was structural** — `REPO_ROOT` is captured at import,
so `relative_to` raises on a scratch tree and no case could build one. A `rel()` helper at the five
reporting sites fixed it. `checks/doc.py` still holds 12 other module-level `REPO_ROOT` uses;
converting the constant is the vocabulary sweep's, and it was deferred.

**Two ship criteria could not be met literally and were SCOPED, not faked.** *"No shipped file states
what a verb does in prose that the verb does not generate"* is not mechanisable in general; the sharp
slice landed and the grain says which half did not. The read-verb feature's collect-and-render
primitive did not land at all, for the reason its own text gives. Both are written into their grain
files under "What landed, and what did not" — **look there before assuming a criterion was met.**

**The tree can measure everything except its own dispatches — the REACH half is fixed, the harness
half is not.** `pm ledger report` showed `0 dispatch row(s)` after six dispatched agents. The
arrival now names the courier and the env var on its `have:` line, `dispatch --grain` renders the
export and a pasteable `pm ledger record`, and U4 says how long "never" has been true
(`bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty`, closed). **The close's own four
dispatches were recorded by hand off those lines — the first spend rows this tree has ever held.**
No hook wrote any of them: whether a harness fires `SubagentStop` still depends on the session's
project root, `GDK_LEDGER_ROOT` is what points a session rooted elsewhere at this tree, and nothing
in a checkout can set it. Expect `0 dispatch row(s)` again unless somebody exports it.
