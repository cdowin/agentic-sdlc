---
id: st-force-leaves-a-claimed-file-alone-and-takes-one-by-path
kind: story
feature: ft-install-force-keeps-what-the-project-owns
milestone: "ms-a-consumer-can-take-the-bump"
name: --force leaves an adopt-ours claim alone, and one installable can be taken by path
status: building
owner: agent
depends_on: []
changelog:
---

# --force leaves an adopt-ours claim alone, and one installable can be taken by path

Issues: #20 (items 1 and 3), #29.

`[adopt] ours` tells the adopt belt which installed files the project has rewritten. `install.py`
never reads it (the only reader is `conveyor/steps.py:574` `_ours_of`), so `--force` rewrites every
file in the plan, claimed or not. There is also no way to take ONE installable. The argv loop
(`install.py:767-782`) accepts `--force`, `--diff`, the settings flag and help, and nothing else. The
workaround people used was `git show v0.7.0:src/…/pm-operator.md > .claude/agents/pm-operator.md`.

This applies to every installer: `install-agents` (9–11 claimed briefs per consumer), `install-ci`
(a claimed `verify.yml` next to the kit-owned `semver-gate.yml`) and `install-hooks` (`prepare-commit-msg`).

## Acceptance criteria

1. `install-* --force` does not write any path named in `[adopt] ours`. It prints one line per skip
   naming the path and the claim, and the census line counts the skips.
2. Naming a path explicitly takes that installable, whether or not it is claimed:
   `install-* --force <path>` or `--only <path>`, whichever spelling the router's conventions favour.
   A path that is not in the verb's plan is refused at exit 2 by name.
3. `--diff` still shows a claimed file's diff (a claim is not a blindfold) and marks it claimed.
4. The claim list is read through one function that `install.py` and `conveyor/steps.py` share, so
   the belt and the installer cannot disagree about what a claim is.
5. Idempotent: a second `--force` over the result writes nothing.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 5 | unit | temp tree with one claimed and one drifted unclaimed agent | new, in tests/test_install.py |
| 2 | unit | the same tree, the claimed path named; an unknown path exits 2 | amend the above |
| 3 | unit | the existing `--diff` case, with a claim added | amend |

## Semver

Minor: a new flag or argument, and a new report disposition line (rule 6's CLOSED set of dispositions).

## Out of scope

The config header, which is `st-the-project-config-header-survives-force`.
