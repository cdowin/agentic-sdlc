Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-a-consumer-can-take-the-bump a consumer can take the bump — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.8.0-a-consumer-can-take-the-bump`, off `main` at `4dae916` (the v0.7.0 merge), pushed |
| **Version** | 0.8.0, already bumped in the release commit `cd94308` (both sites and `uv.lock`) |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc`, the only checkout. No worktrees, no side branches |
| **State** | `done` through `release 0.8.0` (every check true, `make milestone` green). **PR #38 is open:** https://github.com/cdowin/agentic-sdlc/pull/38 |

## 2. Where to pick up: the four release acts that remain, all yours

```bash
gh pr checks 38                                   # `verify` (make milestone in CI) must be green
gh pr merge 38 --merge                            # a MERGE COMMIT — never squash, never rebase
git checkout main && git pull --ff-only
git tag v0.8.0 && git push origin refs/tags/v0.8.0            # the tag ref only
uvx --from git+https://github.com/cdowin/agentic-sdlc@v0.8.0 agentic-sdlc --version   # cold-cache proof
```

After the tag, delete the merged branch locally and on origin (`git branch -d …`, `git push origin
--delete …`), and open 0.9.0 (`ms-the-ledger-is-a-stamp`, which has its own handoff).

Nothing else is open in this milestone: 5 features and 9 bugs are done, and 0 issues are open on the
`0.8.0` GitHub milestone (#15 was moved off with a comment; it is tracked in the pool). Deferred work,
all filed: `bg-a-pasted-fork-answer-records-nothing`, `bg-install-skills-has-no-withdrawal-report`,
and the consumer-visible 0.9.0 work.

## 3. Traps this milestone sprang, and what now prevents each

- **The belts were starved for 1h8m** by parallel builders in one tree (the story belt's `committed`
  check). SDLC.md §2 now: two modes, one contract, and parallel ONLY through
  `tools/dev/agent-worktree.sh`, agent-owned. `check pm`'s `CLOSE` WARN names any close that is ready
  and not run.
- **The orchestrator improvised git.** A `git bisect run` of the suite in a linked worktree exported
  GIT_DIR and flipped this repo to `core.bare = true`. Fixed for the suite (6baa086: conftest scrubs
  git's env, and a session ratchet fails on a moved host). SDLC.md now binds the orchestrator to the
  builders' git rules, and 0.9.0's first feature makes that a hook. **If git ever says "must be run in
  a work tree", check `git config core.bare` FIRST.**
- **The harness's `isolation: "worktree"` bases a worktree on `main`** and rewrites `core.hooksPath`
  to an absolute path. Don't use it; `agent-worktree.sh` bases on the milestone branch. `check hooks`
  accepts the absolute path since 8571e36.
- **Briefs were hand-written ~25 times.** A dispatch brief is `agentic-sdlc dispatch --grain <id>
  --role <role>` output, verbatim, plus only what the grain file cannot know.
- **`git commit -- pm/roadmap` does not take NEW files**: `git add` what `pm new` / `pm decide` create.
- **A review disposition must match the verdict grammar:** `landed <one-hash>`, `landed in-place`,
  `rejected: <why>` or `deferred: <grain-id>`, or the feature belt refuses.
- **The pre-push gate leaves one `gate` row in `pm/roadmap/ledger.jsonl`.** That is correct
  (0.7.0/D2). It rides with the next commit.
- **zsh here:** no apostrophe inside an unquoted argument or heredoc (it ran prose as commands once).
  Write grain bodies with the Write tool.
