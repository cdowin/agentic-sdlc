"""How every command this package prints for a person to run is spelled: through the stock wiring's make targets.

The stock wiring never puts `agentic-sdlc` on PATH, so a printed bare command
is `command not found` in every consumer wired as the README says. The spelling
is `make pm|sdlc ARGS=…` (feature D1), fixed here and never detected (rule 9).
It is parsed twice — by the operator's shell, then by the CLI's `shlex`, since
the recipe hands `$(value ARGS)` over unexpanded through the environment (#60) —
so each argument is quoted for the second and the whole value for the first (D2). A command that WRITES `Makefile.devkit`
cannot use a target that file may not have yet: `pinned` spells it through
`uv run`, which runs the version `uv.lock` pins.

Since 1.0.0 the lock is the ONLY way the kit is installed: a consumer declares
`agentic-sdlc==X.Y.Z` in a dependency group, resolved from this project's own
index, and `Makefile.devkit` runs `.venv/bin/agentic-sdlc`. The index, the
`uv add` line that declares it and the reader of the locked version live here,
so every surface that names the install spells it one way.
"""
from __future__ import annotations

import shlex
import tomllib
from pathlib import Path

from agentic_sdlc import __version__

MAKE = 'make'
VAR = 'ARGS'
# The two passthroughs `Makefile.devkit` defines over `$(DEVKIT)`.
PM_TARGET = 'pm'
SDLC_TARGET = 'sdlc'
TARGETS = (PM_TARGET, SDLC_TARGET)
PROGRAM = 'agentic-sdlc'
# Where the kit is published: a static PEP 503 index, one wheel and one sdist
# per tag. `Makefile.devkit` spells the same URL in its refusal.
INDEX_NAME = PROGRAM
INDEX_URL = 'https://cdowin.github.io/agentic-sdlc/simple/'
# What `uv sync` reads, and the only version marker a consumer carries.
LOCK_FILE = 'uv.lock'
PYPROJECT = 'pyproject.toml'
# `uv add --index` writes the source pin and not this: without it the index is
# searched for EVERY package, ahead of PyPI (measured, uv 0.11). A later
# `uv add` keeps it.
EXPLICIT = 'explicit = true'


class Slot(str):
    """A placeholder like `<id>`, rendered bare. Never a value, and never free
    text: a placeholder for a sentence is a plain string, and is quoted."""


# A `'` typed in a free-text slot is reopened for the recipe's shell, then each
# of THOSE quotes again for the operator's (review M5).
_REOPENED = "'\"'\"'"
APOSTROPHE = _REOPENED.replace("'", _REOPENED)
FREE_TEXT_NOTE = f"each `'` in the sentence is typed `{APOSTROPHE}`"


def _joined(argv: tuple[str, ...]) -> str:
    return ' '.join(arg if isinstance(arg, Slot) else shlex.quote(arg)
                    for arg in argv)


def command(*argv: str) -> str:
    """`make pm ARGS=…` for a `pm` verb, `make sdlc ARGS=…` for every other."""
    if not argv:
        raise ValueError('a vehicle line needs a verb')
    if any('\n' in arg for arg in argv):
        raise ValueError(f'a vehicle line cannot carry a newline, which make '
                         f'splits the recipe at: {argv!r}')
    target, rest = ((PM_TARGET, argv[1:]) if argv[0] == PM_TARGET
                    else (SDLC_TARGET, argv))
    if not rest:
        return f'{MAKE} {target}'
    return f'{MAKE} {target} {VAR}={shlex.quote(_joined(rest))}'


def pinned(*argv: str) -> str:
    """The `uv run` form, for the bootstrap: it runs the version `uv.lock`
    pins, and needs no `Makefile.devkit` target to exist yet."""
    return f'uv run {PROGRAM} {_joined(argv)}'


def add_line(version: str = __version__) -> str:
    """The one command that declares the kit at `version` and locks it."""
    return (f'uv add --dev {PROGRAM}=={version} '
            f'--index {INDEX_NAME}={INDEX_URL}')


def locked_version(root: Path) -> str | None:
    """The version of this kit `root`'s `uv.lock` pins, or None when the lock
    is absent, unreadable, or names no package called this program."""
    try:
        lock = tomllib.loads((root / LOCK_FILE).read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    packages = lock.get('package', [])
    if not isinstance(packages, list):
        return None
    for package in packages:
        if isinstance(package, dict) and package.get('name') == PROGRAM:
            version = package.get('version')
            return version if isinstance(version, str) else None
    return None


def argv_of(line: str) -> list[str]:
    """The argv a vehicle line hands the verb, both parses undone, or ValueError."""
    words = shlex.split(line)
    if len(words) < 2 or words[0] != MAKE or words[1] not in TARGETS:
        raise ValueError(f'not a vehicle line: {line!r}')
    rest: list[str] = []
    if len(words) > 2:
        if len(words) != 3 or not words[2].startswith(f'{VAR}='):
            raise ValueError(f'a vehicle line takes one {VAR}=: {line!r}')
        rest = shlex.split(words[2][len(VAR) + 1:])
    return ([PM_TARGET] if words[1] == PM_TARGET else []) + rest
