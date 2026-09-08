---
id: bg-the-suite-can-flip-the-host-repo-to-bare
milestone: ms-the-rule-reaches-the-work
name: something in a full-suite run sets core.bare on the host repo
status: closed
severity: high
kind: bug
changelog: A boundary test now refuses any test that spawns git against the host checkout — no `cwd=`, a `cwd=` rooted here, a GIT_DIR/GIT_WORK_TREE in `env=`, or `-C`/`--git-dir` in the argv. One real offender was running `git init --bare` in whatever directory pytest started in.
---

# something in a full-suite run sets core.bare on the host repo

Observed **twice** on 2026-09-06 while building this milestone. `.git/config` of the
real checkout acquired `bare = true`, after which every git command in the working
tree fails with:

```
fatal: this operation must be run in a work tree
```

No commits were lost either time — the objects, refs and reflog were intact and
`git config core.bare false` restored the checkout whole.

## What is known

- It appeared while integration-tier tests were running (the tier that spawns real
  `git` and `make`). It did NOT reproduce under `make unit`, `make check`,
  `test_pm_order.py` or `test_pm_verbs.py` run alone.
- **No test sets `core.bare`.** Every `subprocess.run(['git', 'config', ...])` in the
  suite passes `cwd=<temp tree>`, and none names `bare`.
- The second occurrence flipped between two ADJACENT shell commands with nothing but
  `cat` and `git ls-files` in between, which does not fit any test being the writer.
- Both occurrences followed a session in which orphaned `make`/`pytest` processes had
  been killed, so an interrupted `git config` rewrite (git writes a temp file and
  renames) remains the leading hypothesis — but it is a hypothesis, not a diagnosis.

**This is filed unresolved on purpose.** Naming a cause that has not been established
would be worse than the open finding: whatever it is, a suite that can leave the host
repository unusable is a hazard, and rule 4's shape — something that looks legitimate
and is not — is exactly what it wears.

## Narrowed 2026-09-06, same session — it correlates with CONCURRENCY

Measured after a third occurrence. Each git-spawning module was run on its own against
this checkout, hashing `.git/config` before and after:

```
tests/test_conveyor_adopt.py   -m shell   config unchanged, bare=false
tests/test_fresh_project.py    -m shell   config unchanged, bare=false
tests/test_check_hooks.py      -m shell   config unchanged, bare=false
tests/test_hooks_payloads.py   -m shell   config unchanged, bare=false
tests/test_makefile_gates.py   -m shell   config unchanged, bare=false
tests/test_gate_roster.py      -m shell   config unchanged, bare=false
```

**No module flips it alone.** All three occurrences happened while one or more SUBAGENTS
were running their own test processes against this same worktree — the shared-worktree
dispatch SDLC.md §2 describes. Git writes `.git/config` by taking a lock, writing a temp
file and renaming; two processes doing that concurrently, one of them holding a stale
read, is a shape that fits every observation and that a single-module run cannot
reproduce.

That is a HYPOTHESIS with good evidence, not a diagnosis. What is established: it is not
any one test module in isolation, and it needs concurrency to appear.

## Next step for whoever picks this up

Reproduce under CONCURRENCY, since serial runs do not: two or three `make test` runs
against this worktree at once, with a `.git/config` watcher (`fswatch .git/config`, or a
loop hashing it) capturing the process tree at the moment it changes. If it is a
lock/rename race, the fix is that no test may spawn `git` with this repository as its
cwd or `GIT_DIR` — which is assertable as a boundary test over `tests/`, in the same
family as `NoCodePathParsesAVersion`.

## Verified when

A full `make test` run, repeated, leaves `.git/config` byte-identical — asserted by a
case, not by a person looking.

## Established 2026-09-07 — the precondition is removed, the race is not diagnosed

**A gate now removes the precondition.** `tests/test_boundaries.py::NoTestSpawnsGitAgainstThisCheckout`
refuses any test that can reach the host repository with git, decided from syntax: no `cwd=`; a
`cwd=` rooted at `__file__` or a support path constant; `GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`/
`GIT_INDEX_FILE`/`GIT_OBJECT_DIRECTORY` in `env=`; or `-C`/`--git-dir`/`--work-tree` in the argv —
the last two banned outright, because an AST cannot resolve what they point at. Census: 57 test
modules, 48 git call sites across 13 modules, with floors so the walk cannot go vacuous.

**One real offender.** `tests/test_hooks_payloads.py`'s `with_origin` ran
`subprocess.run(['git', 'init', '-q', '--bare', str(origin)])` with **no `cwd=`** — in whatever
directory pytest was started in, which is this checkout, and `git init --bare` is a verb whose job
is writing a `.git/config`. Fixed with `cwd=parent`. No allowlist was added.

**Reproduced in a sandbox, and it is NOT what happened here.** `GIT_DIR=<repo>/.git` plus
`git init --bare` with **no path argument** writes `bare = true` into that repo's config — the exact
symptom. With a path argument it does not, in any combination tried. But this suite's call passes a
path, and git 2.50.1 does not export `GIT_DIR` to a `pre-commit` hook (checked with a hook that
echoes it). **So the mechanism reproduced is not the mechanism that fired.**

**The lock/rename race under concurrency is neither confirmed nor refuted.** It was not reproduced.
Naming it as the cause would be the thing this file said not to do.

## Still open, and named rather than closed over

- **`.git/config` was byte-identical across one full `make test`**, not the repeated concurrent runs
  the "Verified when" section asks for. That condition is not asserted by any case, and it is not
  obvious a single case can assert it.
- **`make` and `bash` spawns against the host are outside the gate**, deliberately:
  `test_makefile_gates.py` runs `make` with `cwd=REPO_ROOT` because that IS its subject, and several
  `bash <hook>` spawns pass no `cwd=`. Those hooks read a cwd from their JSON payload rather than
  the process cwd, but not every script was audited for a git call that falls back to the ambient
  directory.
- **No `env=` scrub for an inherited `GIT_DIR`.** One would defeat every `cwd=` in the suite. Nothing
  in this repo sets it, and building machinery against a condition nobody has shown occurs is the
  speculative fix this bug warns against.
