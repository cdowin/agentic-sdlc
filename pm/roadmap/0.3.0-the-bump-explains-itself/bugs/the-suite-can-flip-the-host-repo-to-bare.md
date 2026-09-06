---
id: 0.3.0/bugs/the-suite-can-flip-the-host-repo-to-bare
milestone: "0.3.0"
name: something in a full-suite run sets core.bare on the host repo
status: open
severity: high
caught_in: "0.3.0"
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

## Next step for whoever picks this up

Run `make test` (both tiers) with a `.git/config` watcher — `fswatch .git/config` or a
loop hashing it — and capture the process tree at the moment it changes. The
integration tier is the place to look; `test_fresh_project.py`, `test_check_hooks.py`
and `test_hooks_payloads.py` are the modules that spawn `git` against a real repo.

## Verified when

A full `make test` run, repeated, leaves `.git/config` byte-identical — asserted by a
case, not by a person looking.
