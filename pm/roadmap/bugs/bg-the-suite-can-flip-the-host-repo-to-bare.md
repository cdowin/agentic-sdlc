---
id: bg-the-suite-can-flip-the-host-repo-to-bare
milestone: ms-the-rule-reaches-the-work
name: something in a full-suite run sets core.bare on the host repo
status: open
severity: high
kind: bug
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
