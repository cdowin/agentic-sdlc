---
id: bg-a-unit-test-can-spawn-the-full-gate
milestone: ms-0.3.0
name: a unit-tier test can spawn the full gate, and nothing says why
status: closed
severity: high
kind: bug
---

# a unit-tier test can spawn the full gate, and nothing says why

Measured here on 2026-09-06, mid-milestone. `make unit` went from **7 s to 153 s**
and reported nothing but slowness.

The cause: `release ''` stopped being refused (an empty positional was read as
"no argument given"), so it resolved a version from the plan and ran the belt
with its REAL registry — whose `gate` check is `make milestone`. The existing
`test_the_version_refusal_matrix_is_exit_2` case, a unit test, was running the
full matrix gate. Against this repo. Once per parametrised value.

**This is the 170x the milestone's parent northstar exists to end, reached from
inside the package's own suite.**

## Why no gate caught it

`tests/conftest.py` derives the `shell` mark from a module's SOURCE — it imports
`subprocess`, or binds a `tests/support` helper that spawns. That is static, and
this spawn was **indirect**: four frames down, through a library function, into a
registry the test never named. Source cannot see it.

Three separate prose rules said "never the full gate" — SDLC §4, CLAUDE.md's
ladder, and the dispatch brief of every builder. In the same session a builder
ran wide gates anyway, and the orchestrator ran a bare `pytest tests/<module>.py`,
which collects the spawning tier. **Prose held none of the three.**

## Fix

1. **A runtime guard behind the static mark** (`tests/conftest.py`): outside the
   `shell` tier, `subprocess.Popen` raises immediately, naming the nodeid, the
   command, and how to make the reach visible to the derivation. A 153-second
   silent slowdown becomes an instant, named failure.
2. **The empty positional is graded**, never read as absent (`conveyor/driver.py`).
3. **The rung's literal command shape is written where it is read**: CLAUDE.md's
   ladder and SDLC §2/§4 now say never `pytest tests/<module>.py`, and the SHIPPED
   `developer.md` roster file says it too — a brief is per-dispatch and forgettable,
   an installed contract is not.

## Verified when

A unit-tier test that spawns fails by nodeid rather than running, and `make unit`
is back to ~7 s. The guard is proven by `TheGuardBehindTheDerivation` in
tests/test_shell_mark.py, which builds a scratch suite under a copy of the real
conftest and runs a REAL pytest against it — one case reaching a spawn
indirectly (and failing by nodeid), one spawning openly from a marked module
(and passing, because the guard enforces the TIER, not a ban).

The first attempt put that proof in `tests/test_boundaries.py` and reached
`subprocess` through `importlib` so the derivation could not mark the module.
`NoUnreadSpawnSpelling` failed it — correctly: a spawn spelling the derivation
cannot read, inside an unmarked module, is the exact hole that gate exists to
close, and writing one to test another gate is not a special case. Proving what
a real pytest does with the real conftest is an integration concern, so it moved
to the tier that already spawns.

done: in-place — the guard, the driver fix, and the rung shape in three surfaces.
