"""`agentic-sdlc gates-extra`: `[gates] extra`, the project's own gate targets, one per line.

`Makefile.devkit`'s `check` runs them after `agentic-sdlc check all`; a verb rather than
a grep so there is one TOML reader. Each name is interpolated into a make command line,
so anything that is not a bare make goal is refused at exit 2, never dropped.
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

Exit: 0 = printed (possibly nothing) | 2 = the value is not a usable roster."""

# `fullmatch` below AND the `$`: `$` alone matches before a trailing newline.
TARGET = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*$')
MAX_LENGTH = 64


def targets() -> tuple[str, ...]:
    """`[gates] extra`, validated; duplicates collapse in declaration order."""
    roster = str_tuple(config_section(SECTION), SECTION, KEY, ())
    bad = [name for name in roster
           if not TARGET.fullmatch(name) or len(name) > MAX_LENGTH]
    if bad:
        raise ConfigError(
            f'[{SECTION}] {KEY} names {len(bad)} value(s) that are not make '
            f'targets: {", ".join(repr(name) for name in bad)} — a target is '
            f'[A-Za-z0-9][A-Za-z0-9._+-]* and at most {MAX_LENGTH} '
            f'characters, because the include interpolates it into a make '
            f'command line')
    return tuple(dict.fromkeys(roster))


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
