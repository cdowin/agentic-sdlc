"""How every command this package prints for a person to run is spelled: through the stock wiring's make targets.

The stock wiring never puts `agentic-sdlc` on PATH, so a printed bare command
is `command not found` in every consumer wired as the README says. The spelling
is `make pm|sdlc ARGS=…` (feature D1), fixed here and never detected (rule 9).
Two shells parse it — the operator's, then the recipe's, since `$(value ARGS)`
hands the text over unexpanded — so each argument is quoted for the second and
the whole value for the first (D2). A command that WRITES `Makefile.devkit`
cannot use a target that file may not have yet: `pinned` spells it in uvx form.
"""
from __future__ import annotations

import shlex

from agentic_sdlc import __version__

MAKE = 'make'
VAR = 'ARGS'
# The two passthroughs `Makefile.devkit` defines over `$(DEVKIT)`.
PM_TARGET = 'pm'
SDLC_TARGET = 'sdlc'
TARGETS = (PM_TARGET, SDLC_TARGET)
PROGRAM = 'agentic-sdlc'
# Where `Makefile.devkit`'s own `DEVKIT` resolves the pin from.
SOURCE = 'git+https://github.com/cdowin/agentic-sdlc'


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
    """The uvx form at this tool's own version, for the bootstrap."""
    return (f'uvx --from "{SOURCE}@v{__version__}" {PROGRAM} '
            f'{_joined(argv)}')


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
