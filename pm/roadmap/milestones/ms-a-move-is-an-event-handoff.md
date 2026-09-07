Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-a-move-is-an-event a move is an event — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.5.0-a-move-is-an-event`, off `main` at `cb54d55` (v0.4.0) |
| **Version** | 0.5.0. MINOR: new verbs (`lesson`), a new config section (`[emit]`), a new `check pm` rule, new `ready-for` rungs. Bumps at CLOSE, both sites together |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc` — the primary checkout, not a worktree. `.claude/worktrees/0.4.0` still holds the finished 0.4.0 branch and can be pruned |

## 2. Where to pick up

Read `ms-a-move-is-an-event-decisions.md` first — D1 and D2 both have rejected alternatives that
will otherwise be re-argued from scratch.

`order` is the build order and it is deliberate: **five bugs before any feature.** Positions 1 and 2
are open against shipped 0.4.0 and degrading a consumer tree now.

```bash
git log --oneline cb54d55..HEAD   # the commit messages carry the arguments
pm status ms-a-move-is-an-event   # every grain, its state, its story count
pm roadmap                        # 0.5.0 and the four shipped releases
pm validate                       # refs resolve; the tree is not contradicting itself
make help                         # the authoritative target list
verify --plan                     # the rungs, with the cost each last took
```

Only `ft-a-rung-has-an-entry-edge` has a story. Every other feature is a body with a ship criterion
and a proof budget and no stories yet — that is planning done, not work started.

## 3. Traps this milestone has already sprung

**`pm new` mints an id containing the parent, and an auto-loaded rule says it does not.** Every
grain in this milestone was scaffolded with `pm new`, came back as `ms-a-move-is-an-event/<slug>`,
and was renamed by hand to `ft-`/`bg-`/`st-`. `.claude/rules/pm-execution.md` says *"pm new …
scaffolds to the schema"*, which is false and is why the defect survived a release — four bugs in
the shipped 0.4.0 tree carry compound ids. Rename after every `pm new` until
`bg-the-new-verbs-mint-a-compound-id` closes. Do NOT reach for a gate on id shape: that was
proposed, and rejected, because a version in a filename or an id is the author's business and the
tool does not get an opinion about it (rule 9). The defect is the coupling, not the style.

**The id is language; the version is `version:`; they are separate on purpose.** `ms-0.1.0` through
`ms-0.4.0` encode their version in the id, which forces a rename — and a rewrite of `order` — on any
re-version, the exact coupling 0.3.0 and 0.4.0 removed. This milestone is `ms-a-move-is-an-event`
and is the first one that demonstrates the model. Renaming the historical four would orphan their
ledger rows, since `pm rename` does not rewrite history; that trade has not been taken.

**The repo was found with `core.bare = true`** at the start of this milestone — the open 0.4.0 bug
`the-suite-can-flip-the-host-repo-to-bare` reproducing in the primary checkout. Every `git status`
and `git grep` failed with *"this operation must be run in a work tree"* until `git config core.bare
false`. If git suddenly claims there is no work tree, check that first; it is not a corrupt
checkout.

**The PyPI name `agentic-sdlc` is taken** by an active unrelated project, colliding on the
distribution name, the import package `agentic_sdlc`, AND the console script. That package is D1's
worked example of the rejected plugin path — worth reading once, before anyone re-proposes "let the
config name a command to run." Packaging is not scoped to this milestone.

**Eleven agents ran against ONE shared checkout, and that was the orchestrator's error.**
246 minutes of agent work compressed into 53 minutes wall clock (4.6x) — but the concurrency cost
real work, twice: `checks/pm.py` was overwritten mid-task by a second agent and silently lost half
its edits (restored from a scratch backup), and a hand-written grain body was reverted to its
scaffold. Three agents could not get a verdict on their own work and rebuilt isolated trees with
`git archive HEAD` first. `pm new` crashed mid-call because `cli.py` was being rewritten underneath
it. `test_prose_census` went red CUMULATIVELY — no single agent broke it and no single agent could
fix it. Use `isolation: "worktree"` per agent, or `tools/dev/agent-worktree.sh`, which ships in the
box and which nothing named at the moment it was needed (that is
`ft-a-move-names-the-capability-you-are-standing-in`, filed from this).

**The review rung was budgeted at zero and it is ~40% of a milestone.** Thirteen of eighteen grains
were BUILT and none closed, because `close feature` wants a `reviewed:` record with a parsed verdict
block and nothing had one. This is 0.3.0's lesson (dispatch a feature's review the moment
`ready-for feature` goes READY) repeated by the orchestrator that had just written it down.

**Scope grew 12 -> 18 grains while the clock ran.** Every addition was a real defect found by doing
the work. Healthy, but a target that moves is a target you miss: a finding should default to a GitHub
issue and become a grain only when it blocks.

**Statuses were flipped at the end, not when they became true.** So the ledger reports one unbroken
`in_progress` span per grain with no internal structure — which is exactly what
`ft-time-is-measured-per-state-and-rolls-up` exists to fix, demonstrated by this build failing to
follow the execution loop it ships.
