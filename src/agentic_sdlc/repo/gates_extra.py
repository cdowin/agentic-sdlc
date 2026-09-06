"""`agentic-sdlc gates-extra`: `[gates] extra`, the project's own gate targets, one per line.

`Makefile.devkit`'s `check` runs them after `agentic-sdlc check all`; a verb rather than
a grep so there is one TOML reader. Each name is interpolated into a make command line,
so anything that is not a bare make goal is refused at exit 2, never dropped.

Two namespaces sit next to each other in devkit.toml and neither key says
which it is: this one takes MAKE TARGETS, `[checks] all` takes GATE NAMES. A
gate name is a perfectly legal make goal, so the grammar below cannot see it,
and what an adopting agent got for `extra = ["budget"]` was `make[1]: *** No
rule to make target 'budget'. Stop.` — GNU make, three layers under the config
that caused it. `_refuse_gate_names` is that report, moved to the key's own
reader.
"""
from __future__ import annotations

import re
import sys

from agentic_sdlc.core.config import ConfigError, config_section, str_tuple

SECTION = 'gates'
KEY = 'extra'

USAGE = """usage: agentic-sdlc gates-extra

Prints `[gates] extra` from devkit.toml, one make target per line — the
project's own gate targets, which Makefile.devkit's `check` runs after the
devkit ones. No section, or no key: prints nothing, exits 0.

This key is a MAKE TARGET namespace; `[checks] all` next door is the GATE
name one. A devkit gate name here is refused and told which key runs it.

Exit: 0 = printed (possibly nothing) | 2 = the value is not a usable roster."""

# `fullmatch` below AND the `$`: `$` alone matches before a trailing newline.
TARGET = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*$')
MAX_LENGTH = 64

# The other namespace, for the message that has to name it: `[checks] all` is
# the gate roster, and `make check` is the target Makefile.devkit gives it.
GATE_TARGET = 'check'
ROSTER_SECTION = 'checks'
ROSTER_KEY = 'all'


def targets() -> tuple[str, ...]:
    """`[gates] extra`, validated; duplicates collapse in declaration order."""
    roster = str_tuple(config_section(SECTION), SECTION, KEY, ())
    # Shape first, namespace second: a value make cannot parse is the more
    # fundamental defect and its repair is a different one, so a roster holding
    # both reports the shape refusal rather than being told about a namespace
    # it never reached.
    _refuse_non_targets(roster)
    _refuse_gate_names(roster)
    return tuple(dict.fromkeys(roster))


def _refuse_non_targets(roster: tuple[str, ...]) -> None:
    """Every value the include could not interpolate as one make goal."""
    bad = [name for name in roster
           if not TARGET.fullmatch(name) or len(name) > MAX_LENGTH]
    if bad:
        raise ConfigError(
            f'[{SECTION}] {KEY} names {len(bad)} value(s) that are not make '
            f'targets: {", ".join(repr(name) for name in bad)} — a target is '
            f'[A-Za-z0-9][A-Za-z0-9._+-]* and at most {MAX_LENGTH} '
            f'characters, because the include interpolates it into a make '
            f'command line')


def _refuse_gate_names(roster: tuple[str, ...]) -> None:
    """A well-formed target name that is a GATE name is the wrong namespace.

    The universe is `gate_universe()`, derived from `repo/checks/`, so a gate
    added later is named here the day it ships and there is no second roster
    to fall out of date. Imported inside the call because `conveyor.steps`
    reads this module's `targets` — a module-level import either way is a
    cycle — and because a repo declaring no `[gates] extra` should not pay for
    the import to be told nothing (rule 5: stock runs byte-identically).

    Exact membership, never a substring: `budget-check` is an ordinary name
    for a project target that WRAPS a devkit gate, and refusing it would be
    this key's own version of the cardinal sin.
    """
    if not roster:
        return
    from agentic_sdlc.repo.conveyor.steps import gate_universe

    universe = gate_universe()
    named = [name for name in dict.fromkeys(roster) if name in universe]
    if not named:
        return
    entries = ", ".join(repr(name) for name in named)
    is_are = 'is a gate' if len(named) == 1 else 'are gates'
    them = 'it' if len(named) == 1 else 'them'
    raise ConfigError(
        f'[{SECTION}] {KEY} names make targets, not gate names: {entries} '
        f'{is_are} this package ships, and `make {GATE_TARGET}` is the target '
        f'that runs {them} — declare {them} in [{ROSTER_SECTION}] '
        f'{ROSTER_KEY} instead. [{SECTION}] {KEY} is for targets your OWN '
        f'makefile defines, which `make {GATE_TARGET}` runs after the devkit '
        f'gates')


def main(argv: list[str]) -> int:
    for arg in argv:
        if arg in ('-h', '--help', 'help'):
            print(USAGE)
            return 0
        print(f'agentic-sdlc gates-extra: unexpected argument {arg!r}',
              file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    try:
        roster = targets()
    except ConfigError as err:
        print(f'agentic-sdlc: {err}', file=sys.stderr)
        return 2
    for name in roster:
        print(name)
    return 0
