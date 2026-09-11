Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-a-consumer-can-take-the-bump a consumer can take the bump — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.8.0-a-consumer-can-take-the-bump`, off `main` at `4dae916` (the v0.7.0 merge) |
| **Version** | 0.8.0 (planned as 0.7.1; re-versioned in D1). The bump is at CLOSE, so `__version__` stays 0.7.0 until the release commit |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc`, one shared worktree. Builders run concurrently on DISJOINT file sets; reviewers use a detached worktree under the session scratchpad, removed after |

## 2. Where to pick up

```bash
git log --oneline 4dae916..HEAD
agentic-sdlc pm status ms-a-consumer-can-take-the-bump
agentic-sdlc pm ledger report ms-a-consumer-can-take-the-bump
```

Reading order: the three decisions files (milestone D1, and D1 on each of the two install and
vehicle features) before any feature, so their rejected alternatives are not re-argued.

The dispatch phases, by file set. Overlapping work is serialized:

    A  ft-install-force… (install.py)  ·  ft-the-pm-surface… (pm/cli.py, driver.py)
       ft-the-shipped-words… (guidance, briefs, README, steps.py descriptions)
       st-the-semver-gate… (ci-semver-gate.yml)
    A' the D2 narrowing of the markdown config block (install.py), the words
       follow-ups (po.md, the test tier); both after A commits
    B  three chains, in parallel with each other, serial within each:
         checks/pm.py   #19 → #30 → bg-the-gate-help…
         checks/doc.py  #26 (after the words land)
         steps.py       bg-the-release-belt… → bg-the-bump-belt…
    C  ft-every-printed-command… LAST: its sweep rewrites text the others touch,
       and it amends checks/doc.py's _STATUS_FORM after #26

Before phase B, read `docs/reviews/2026-09-11-0.8.0-spec-review.md`. Every grain it bears on has
been amended, and the amendments are marked in each grain.

Every feature acceptance closes its GH issues (SDLC.md §2): push, comment with the hash, close.

## 3. Traps this milestone has already sprung

- **The story belt's `committed` check fails whenever another builder has files in flight.** It
  reads "nothing uncommitted outside pm/roadmap/". So stories are closed after their phase's
  builders have all reported and each slice is committed by pathspec, not the moment one reports.
- **The pre-push gate leaves one `gate` row in `pm/roadmap/ledger.jsonl`.** That is correct
  (0.7.0/D2). It rides with the next commit; do not chase it.
- **U1 on this tree reports `building` as never held,** which is #30 itself. Do not "fix" the
  vocabulary because of that WARN. (#30 landed in 526cacf/2376338; U1 now reads the ledger.)
- **The belts were starved for 1h8m.** Parallel builders in the shared tree kept `committed` false.
  The flow now: concurrent builders get isolated worktrees and commit there, and each belt runs as
  the next action (SDLC.md §2). `check pm`'s CLOSE WARN names any close that is ready and not run.
- **`git bisect run` of the suite in a linked worktree flipped this repo to `core.bare = true`** and
  left stray `scratch` commits (it exports GIT_DIR). Fixed by 6baa086: conftest scrubs git's env and
  a session ratchet fails on a moved host. If git ever says "must be run in a work tree", check
  `git config core.bare` FIRST.
- **The harness creates isolated worktrees from `main`, not the milestone branch.** Every isolated
  builder is briefed to `git merge --ff-only milestone/0.8.0-…` first.
- **The Claude Code harness rewrites `core.hooksPath` to an ABSOLUTE path** when it makes an agent
  worktree, and re-arming does not stick. Since 8571e36, `check hooks` accepts a linked worktree armed
  at the main worktree's corpus and prints a `note` line; before that, every worktree was MISDIRECTED.
- **`git commit -- pm/roadmap` does not take NEW files.** `pm new` and `pm decide` create untracked
  files, so `git add` them first. Two grain files went uncommitted this way.
- **A review disposition must match the verdict grammar:** `landed <one-hash>`, `landed in-place`,
  `rejected: <why>` or `deferred: <grain-id>`. Anything else makes the record unverifiable, and the
  feature belt refuses.
- **Never put an apostrophe inside an unquoted shell argument or heredoc here** (zsh). One broke a
  `pm new bug` call and ran prose as commands. Write grain bodies with the Write tool.
