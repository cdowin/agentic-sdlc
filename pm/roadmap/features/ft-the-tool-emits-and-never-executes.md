---
id: ft-the-tool-emits-and-never-executes
kind: feature
milestone: "ms-a-move-is-an-event"
name: the tool emits and never executes
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# the tool emits and never executes

D1 is the argument; this is the boundary it draws, built. **A hook is an event this package writes.
It is never a command this package runs.**

Hard rule 2 — *"pure text, boots nothing; safe anywhere, any time, in parallel"* — is what makes
every gate here runnable from a git hook and from CI without a sandbox. A verb that spawns a
consumer-named command ends that for every verb, because a caller cannot tell which ones are safe
any more.

## The sink is a declaration

    [emit]
    sink = "ledger" | "<path>" | "-"        # the ledger, a file, or stdout. Default: ledger
    kinds = ["enter", "verdict", "leave"]   # which taps. Default: all three

A path is opened, appended to, closed. `-` writes JSON lines to stdout, separate from the human prose
on the same stream — a consumer parsing prose today keeps parsing prose (rule 6). Nothing is
executed, imported, resolved to a callable, or looked up in an entry-point group.

**A sink this package cannot write to is a finding, never a crash and never a silent skip** — the
verb does its work, exits on its own merits, and names the sink it could not reach. Emission is never
load-bearing for a belt's verdict.

## What carries it onward

A courier the consumer arms, exactly as `cc-ledger-session.sh` and `cc-ledger-subagent.sh` already
carry transcripts. The courier is where a harness's own callback shape is known — rule 8 says this
package knows nothing about its consumers, so no shipped file names a harness event, and the adapter
lives in the hook corpus where a consumer can read and edit it.

## Ship criterion

`[emit]` is read, its sink written on every tap, and no code path in the package spawns a process,
imports a module named in config, or resolves a config string to a callable. A test asserts it: the
emit path is held to the same no-subprocess boundary `tests/conftest.py` already derives the `shell`
mark from, so adding a spawn fails collection rather than review.

A tree declaring no `[emit]` behaves exactly as 0.4.0 does, including exit codes.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_emit.py`, new — the sink is a new surface with no existing harness
  what already covers this: nothing; the no-spawn assertion amends `tests/test_boundaries.py`
    rather than starting a second source-shaped family.

## Out of scope

The payload — `ft-one-event-shape-serves-three-readers` says what a row is. This says where it goes,
and what the package refuses to do to get it there.
