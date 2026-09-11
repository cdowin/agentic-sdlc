---
id: st-the-shipped-defaults-follow-the-kits-own-branch-flow
kind: story
feature: ft-every-printed-command-runs-in-a-stock-consumer
milestone: "ms-a-consumer-can-take-the-bump"
name: the shipped defaults follow the kit's own branch flow, not a staging branch
status: building
owner: agent
depends_on: []
changelog: `agent-worktree.sh`'s `FALLBACK_BASE` and `cc-stop-gate.sh`'s `DEFAULT_BASE` default to empty — the remote's HEAD — instead of `staging`; a base that does not resolve is named on stderr by the Stop gate and refused by `agent-worktree.sh new`. `install-hooks --force` keeps your header, so check both values and clear a `staging` your flow does not have.
---

# the shipped defaults follow the kit's own branch flow, not a staging branch

Issue: #37.

The kit's own flow is **main → a milestone or feature branch → a merge back to main**. The `release`
belt's `next:` lines say "push the branch — never the mainline" and "open the PR from {branch} to
{mainline}", and `ci-verify.yml` triggers on `main` only. No `staging` branch exists anywhere in it.
Two installed scripts still default to one, in their project-config headers:

    installables/agent-worktree.sh:25   FALLBACK_BASE="staging"   where an agent branches from when
                                                                  no milestone declares a branch
    installables/cc-stop-gate.sh:18     DEFAULT_BASE="staging"    the diff base when the scope
                                                                  marker records none

In a consumer following the kit's flow, each fails in its own way:

- `agent-worktree.sh new <slug>` with no milestone in progress runs
  `git worktree add -b feat/<slug> <path> staging` and dies with `git worktree add failed`;
- `cc-stop-gate.sh` fails `git rev-parse --verify staging` QUIETLY and skips slicing, so the Stop gate
  runs the whole unit tier on every agent stop and never says the base was missing. That is rule 11:
  an absence with no named line.

## Acceptance criteria

1. Neither header defaults to a branch name the kit's flow never creates. The stock default is the
   MAINLINE: the value of `[repo_hygiene] mainline` (stock `origin/main`, the one place the kit
   already declares it), or, if the script cannot read that cheaply, the remote's HEAD
   (`git symbolic-ref refs/remotes/origin/HEAD`). It is a read, never a guess (rule 9). Both headers
   say which it is.
2. **A base that does not resolve is named on stderr, never swallowed.** `cc-stop-gate.sh` prints one
   line naming the base it could not verify, saying it is running the WHOLE tier because of that, and
   then proceeds as today. `agent-worktree.sh new` refuses with
   the base it tried and where to set it, before calling `git worktree add`.
3. Because feature D1 carries a consumer's header byte-for-byte, a kept `staging` default stays until
   the consumer changes it. So criterion 2 is what makes a stale kept value VISIBLE. The story says
   this in its close, and the proposed changelog sentence tells a consumer to check both header values.
4. `installables-current` and the self-hosted copies (`tools/dev/agent-worktree.sh`,
   `tools/hooks/cc-stop-gate.sh`) are current after `install-hooks --force`. This repo has no
   `staging` either, so its own headers take the new default.
5. Each hook's `--self-test` corpus (the hooks' existing replay, `check hooks`) gains the unresolved-
   base case, and `check hooks` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | integration (the scripts ARE processes) | a scratch repo with `main` only: `new <slug>` with no milestone; the Stop gate with no marker | amend the existing agent-worktree / cc-stop-gate cases. Search first |
| 5 | per `check hooks` | the corpus rows | amend |
| 4 | unit | tests/test_install.py self-host | yes |

## Semver

Minor: a header default changes, and two new stderr lines.

## Out of scope

- `check repo-hygiene`'s stock `protected = "^(main|staging|archive/.*)$"`. #37 calls it harmless,
  and removing `staging` would silently UNprotect the staging branch of any consumer relying on the
  stock default. That is a gate getting quieter with nothing saying so, which is worse than a
  redundant alternation. It stays.
- README.md:215's `protected` example. It is illustrative config, not a default.

## Amended after the builder's premise check (2026-09-11)

- **Criterion 5 is dropped.** Neither script has a `--self-test` corpus (only the two ledger
  couriers, `prepare-commit-msg` and `gdk_gate.sh` do), and `agent-worktree.sh` lives in `tools/dev/`,
  which `check hooks` never reads (`checks/hooks.py:30`). Adding a corpus would be a new surface for a
  two-line default. The unresolved-base cases are proven in `tests/test_hooks_payloads.py`, which
  already runs both scripts in scratch repos.
- **The base is the remote's HEAD**: `git symbolic-ref --short refs/remotes/origin/HEAD`. An EMPTY
  header value means that, and the header comment names the command. Rejected: reading
  `[repo_hygiene] mainline` from bash. The system `python3` here is 3.9 with no `tomllib`, a grep/sed
  TOML reader is a hand-rolled parser, and the stock `origin/main` would need a second copy with nothing
  tying it to `repo_hygiene.py:23`. The cost, accepted: a repo made with `git init` + `git remote add`
  has no `origin/HEAD`, so it gets the named line or the refusal, which points at
  `git remote set-head origin --auto`. `new` passes `--no-track`, so `feat/<slug>` does not track
  `origin/main`.
- **Correction to the story body:** HEAD's `agent-worktree.sh new` already refuses a missing
  `staging` before `git worktree add` (exit 1, `base branch 'staging' does not exist`). What it lacks
  is where to set the base. `cc-stop-gate.sh` is silent, exactly as described.

## Close

done: 7486920 — both script headers default to the remote's HEAD; an unresolved base is named (stop gate) or refused (agent-worktree new); --no-track; 6 cases failed at HEAD.
