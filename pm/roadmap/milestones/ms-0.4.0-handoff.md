Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-0.4.0 authoring is separate from binding — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.4.0-authoring-is-separate-from-binding` |
| **Version** | 0.4.0, bumped at CLOSE (`[pm] version_at = "ship"`), so `pyproject.toml` correctly still reads 0.3.0 while this builds |
| **Tree** | `~/workspace/agentic-sdlc/.claude/worktrees/0.4.0` — a WORKTREE. **0.3.0 is building in the main checkout at the same time**; 0.4.0 has merged it twice already and must merge it again before close. Never edit the main tree from here. |

## 2. Where to pick up

**The tree is MIGRATED and the code is done; what is left is closing it out.** Read
`ms-0.4.0-decisions.md` first — eight decisions, several of which overrule a story's own
acceptance criteria and say why.

Open, in order:

1. **The READY warnings only reach BOUND grains.** `_drift_walk` in `checks/pm.py`
   enumerates by binding, so an authored-but-unbound grain — which 0.4.0 made the normal
   authoring state — gets none of them. Found by the `the-tree-names-what-it-lacks`
   review (M1); the fix is at the loop, not at each WARN.
2. The stories whose code has landed are still `planning`/`building`; the features
   above them cannot close until they do.
3. Four features have no review record yet.

```bash
git log --oneline <base>..HEAD    # the commit messages carry the arguments
pm status <id>                    # every grain, its state, its story count
pm ledger report                  # spend per grain, and what the gates cost
pm validate                       # refs resolve; the tree is not contradicting itself
make help                         # the authoritative target list
verify --plan                     # the rungs, with the cost each last took
```

Reading order: `ms-0.4.0-decisions.md`, then `improvements.md`'s last three lessons
(they are about THIS milestone), then any feature's own `-decisions.md`.

## 3. Traps this milestone has already sprung

**The migration deletes what it does not know to move.** `pm_migrate.py`'s `REF_FIELDS`
missed `caught_in:` and `fix_milestone:`, so all eleven bugs kept pre-migration milestone
ids and `ready-for milestone ms-0.2.0` counted *0 bugs* of the six naming it — a read that
looked right. Separately it DELETED six `decisions.md` files rather than moving them,
including this milestone's own eight decisions; they were restored from
`git show 4d9fb0c~1:`. **If you migrate another tree: diff the file list before and after,
and grep the new tree for every id the old one used.**

**A green suite says nothing about whether a gate is looking at the right thing.** Four
separate checks passed their own tests while reporting PASS over trees they could not see:
a telemetry probe that ran in its own `mktemp` repo, a shape gate that decided a
document's kind from its filename, an in-flight distribution that discarded every row it
was meant to count, and a roster join that suppressed itself whenever nothing was
measured. All four were found by REVIEWERS running the gate against this repo's real tree
and asking *is this number true*. The fixture cannot ask that; it is built to make the
answer yes.

**Following a gate's own repair instruction destroyed the document.** `check grain-shape`
told the author of a story slugged `…-decisions` to prepend a decisions header. Doing so
pushes `---` off line 1, the story stops opening frontmatter, and `check pm` then reports
`0 story/ies`. **A finding that names a repair is a claim — run the repair and check it.**

**The surfaces are not in the census.** Every Python reader of the old layout was found by
the tests. Five more — `.gitattributes`, the CI semver gate, the `pm-operations` skill, the
handoff guidance and three shipped agent contracts — were found only by grepping outside
`src/`, and two of them were live bugs. A layout change needs one deliberate sweep of
everything that is not code.

**A test that pins a generated string must pin what the string MEANS.** The
`merge=union` case asserted the pattern the tool produces, so it stayed green when the
pattern stopped matching any milestone ledger. It asks `git check-attr` now, over a real
repo, naming a path that must match and one that must not.
