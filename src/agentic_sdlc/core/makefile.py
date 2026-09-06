"""Which targets does `make` know in this tree — ONE reader, asked by every verb.

`check doc` holds a doc's `make <target>` claims to it; `verify --check` holds
a rung's `make <target>` to it. Two readers gave two answers (each followed
`include Makefile.devkit` and neither followed the tier seam inside it), so
there is one now, here, where nothing family-specific can reach it.

TEXT, parsed — never `make -n` (hard rule 2: nothing here boots anything, and
asking make whether a name exists lets make decide to build something first).

What is followed: `include`, `-include` and `sinclude`, depth-first as make
does, bounded and cycle-safe. A `$(VAR)` or `${VAR}` in an include path is
resolved from the plainest assignments read SO FAR (`VAR ?= x`, `VAR := x`,
`VAR = x`) — which is exactly the shipped seam, `-include $(GDK_TIERS_MK)`
under `GDK_TIERS_MK ?= Makefile.tiers`. Anything richer — a nested variable,
a function call, a value set on the command line — is skipped rather than
guessed at: the finding it would cause is a false one, and the target it
would miss is one name. Widening only; this can never invent a target no file
defines.
"""
from __future__ import annotations

import re
from pathlib import Path

MAKEFILE = 'Makefile'
# `target:` or `target: deps`, and never `target := value`, which is a variable.
TARGET = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._+-]*)\s*:(?!=)')
INCLUDE = re.compile(r'^\s*(?:-|s)?include\s+(.+?)\s*$')
# `VAR ?= x`, `VAR := x`, `VAR = x`. `+=` appends and is deliberately not read.
ASSIGNMENT = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(\?=|:=|=)\s*(.*?)\s*$')
VARIABLE = re.compile(r'\$[({]([A-Za-z_][A-Za-z0-9_]*)[)}]')
MAX_DEPTH = 4


def targets(root: Path, makefile: str = MAKEFILE) -> frozenset[str]:
    """Every target the root Makefile and everything it includes declare.

    A tree with no Makefile has no targets — an empty set, not a crash.
    """
    names: set[str] = set()
    variables: dict[str, str] = {}
    seen: set[Path] = set()

    def read(path: Path, depth: int) -> None:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            return
        seen.add(resolved)
        for line in path.read_text(encoding='utf-8',
                                   errors='replace').splitlines():
            hit = TARGET.match(line)
            if hit:
                names.add(hit.group(1))
                continue
            assigned = ASSIGNMENT.match(line)
            if assigned:
                name, op, value = assigned.groups()
                if op != '?=' or name not in variables:
                    variables[name] = value
                continue
            included = INCLUDE.match(line)
            if included and depth < MAX_DEPTH:
                for token in included.group(1).split():
                    expanded = _expand(token, variables)
                    if expanded is not None:
                        read(root / expanded, depth + 1)

    read(root / makefile, 0)
    return frozenset(names)


def _expand(token: str, variables: dict[str, str]) -> str | None:
    """`token` with every `$(VAR)` substituted, or None when one is unknown."""
    def substitute(match: re.Match[str]) -> str:
        value = variables.get(match.group(1))
        if value is None or '$' in value:
            raise LookupError(match.group(1))
        return value
    try:
        return VARIABLE.sub(substitute, token)
    except LookupError:
        return None
