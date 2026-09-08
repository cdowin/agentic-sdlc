---
id: bg-the-sixth-installer-cannot-describe-itself
kind: bug
milestone: 
name: the sixth installer cannot describe itself
status: open
caused_by:
changelog:
---

# the sixth installer cannot describe itself

Filed to the pool during 0.6.0's close, by two independent agents reading the same surface for
different reasons. Not bound to a milestone: it gates nothing and is counted there.

## Symptom

Five installers share one usage block that says what each writes and where:

    $ agentic-sdlc install-gates --help
    usage: agentic-sdlc install-ci      [--force] [--diff]
           agentic-sdlc install-agents  [--force] [--diff]
           agentic-sdlc install-hooks   [--force] [--diff] [--write-settings]
           agentic-sdlc install-gates   [--force] [--diff]
           agentic-sdlc install-sdlc    [--force] [--diff]
    install-ci      three workflows under .github/workflows/: verify.yml … semver-gate.yml …
    install-agents  … AGENT DEFINITIONS under .claude/agents/ …

The sixth answers:

    $ agentic-sdlc pm install-skills --help
    [pm] ERROR — unknown flag '--help'

## Root cause

`pm install-skills` is routed through `pm`'s table, and the `pm` family answers `--help` for the
family, not per sub-verb. So the one installer that lives under `pm` is the one that cannot say what
it writes.

## Why it is a rule 11 finding rather than a nicety

**A capability nobody can find is a capability you do not have.** The measurable consequence is
already in `CLAUDE.md`: its self-hosting section carries a hand-written roster of every installer's
output, and the reason it cannot become a pointer to `install-gates --help` is precisely that the
sixth is missing from that surface. `tests/test_conveyor_adopt.py` records the same shape from the
other side — a comment there reads *"`pm install-skills` is the sixth installer (CLAUDE.md's …)"*,
which is a test knowing a doc's roster because no verb would answer.

So the doc roster is not laziness; it is the only place the sixth installer describes itself, and it
is a line a new installer forces somebody to edit. That is the second scoreboard, held in place by a
missing `--help`.

## Fix

Give `pm install-skills` its own `--help`, naming the files it writes, in the shape its five
siblings use. Then `CLAUDE.md`'s roster can become the pointer the tiering pass wanted it to be, and
the test comment can point at the verb instead of the doc.

**The cheapest layer is the flag, not the doc** (rule 11: a word, a column, a warning, a caller —
never a new capability). Nothing about what the verb DOES changes.

## Out of scope

Giving every `pm` sub-verb its own `--help`. The family surface is right for the rest of them; the
installers are the family that already answers this question, and this one is outside it.
