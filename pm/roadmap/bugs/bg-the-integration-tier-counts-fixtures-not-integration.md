---
id: bg-the-integration-tier-counts-fixtures-not-integration
kind: bug
milestone: ms-nothing-is-hand-rolled
name: 125 of 436 integration cases spawn nothing or only a fixture git
status: open
caused_by:
changelog: none
---

# the integration tier counts fixtures, not integration

Audited 2026-09-10 by instrumenting `subprocess.Popen` and running the whole
`shell` tier single-process, counting real spawns per nodeid. Every number
below is that run, not a reading of the source.

## The measurement

    436 nodeids, 359 distinct functions (parametrize accounts for +77)
    19 modules, 30.5s on 8 workers against a 130s budget, 1,910 spawns

    spawns per case      0   78 cases      what gets spawned
                         1  114                git   1,294
                       2-4   97                bash    432
                      5-19  138                make     87 (+18 `make story`)
                       20+    9                python3  68

**78 cases in the tier spawn NOTHING.** 26 of them are `test_ci_workflows.py`,
which parses YAML. 7 are `test_gate_roster.py`, 7 `test_makefile_include.py`,
7 `test_shell_mark.py`.

**47 more spawn exactly one `git`, and it is fixture setup** — 35 of them in
`test_pm_scaffold.py`, 11 in `test_verify_main.py`.

**So 125 of 436 cases (29%) are in the integration tier without integrating
anything.**

## Root cause, and it is not carelessness

`tests/conftest.py:180` derives the mark per MODULE — `if module_spawns(item.path)`
— and applies it to every case in that module. The derivation is deliberate and
its reason is sound: a static reader cannot see a spawn reached indirectly, and
0.3.0 has the scar where a unit test ran the full gate. Coarse-in, plus a
runtime guard, beats a per-case guess.

What the coarseness then meets is a per-module FIXTURE CHOICE.
`tests/support/pm.py` ships exactly the right pair — `tree()` builds a repo with
no git, `git_tree()` builds a real one, and `git_tree`'s own docstring argues
the point: *"The declaration is the point. The default is cheap and the
exception is visible, so a module that quietly grows a git dependency changes
tier in the census rather than in somebody's wall clock."*

**`test_pm_scaffold.py:24` reads `from support.pm import git_tree as tree`.**
One import alias puts 38 cases in the integration tier; the module references
git three times. `test_pm_ledger_report_git.py` aliases it too and earns it —
12 cases, 46 git references, 248 spawns.

So the pattern is present, correct and argued. It is applied at the wrong
granularity, and an alias hides which one is in use at the call site.

## The shape this leaves

The tier is **broad and shallow, not deep**. 138 cases sit at 5-19 spawns and
only **9 exceed 20**. `make story` — the composition that exercises the most
system per case — appears **18 times in the whole tier**. The heaviest cases
are the honest ones:

    41 spawns  test_pm_ledger_report_git::test_the_verb_writes_nothing_and_checks_nothing_out
    38 spawns  test_conveyor_adopt::test_telemetry_live_names_which_of_the_three_ways_a_bump_runs
    34 spawns  test_verify_main::VerifyRemembersItsLastGreen::test_one_byte_anywhere_else_moves

## What is irreducible

~198 cases exercise artifacts that are not Python — bash hooks fired at real
PreToolUse payloads (63), the Makefile framework (35+23), CI workflow scripts
(32), the shell gate library (17), hook arming (28). **A bash hook cannot be
unit-tested.** Any target for this tier that ignores this is a target that gets
met by deleting coverage of the shipped shell.

## Fix

  * **Per-case fixture choice, not a per-module alias.** A case that asks git a
    question reaches for `git_tree`; one that does not uses `tree`. Import both
    under their own names so the call site says which. Floor of 125 cases
    demoted, taking the tier to ~310 and the unit tier up by the same.
  * **`test_ci_workflows.py` spawns nothing at all in 26 of 32 cases** and is in
    the tier because the module reaches `bash` somewhere. Split the parsing
    cases from the executing ones and the whole module stops being integration.

Neither changes what is asserted. Both are moves.

## Taken into 0.7.0

Bound to `ms-nothing-is-hand-rolled` on 2026-09-10, to land before dev
complete. It belongs to this milestone rather than a later one for the reason
the milestone's own northstar gives: a module whose fixture choice is hidden
behind an import alias does not say what it does, and the tier census is a
number this milestone argues from.

## Out of scope

The per-module derivation in `conftest.py`. It is coarse on purpose, the reason
is written down, and the runtime guard behind it is what makes the coarseness
safe. Making it per-case would delete the property 0.3.0 paid for.

Lowering the count by deleting cases. The suite is 1.47:1 against source for a
tool whose cardinal sins are a lying gate and a corrupting write.
