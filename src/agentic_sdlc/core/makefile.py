"""Which targets `make` knows in this tree: one reader, parsed as text, never `make -n`.

Follows `include`/`-include`/`sinclude` with `$(VAR)` resolved from plain assignments
read so far; anything richer is skipped, so this widens and never invents a target.
"""
from __future__ import annotations

import re
from pathlib import Path

MAKEFILE = 'Makefile'
# `target:` or `target: deps`, and never `target := value`, which is a variable.
TARGET = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._+-]*)\s*:(?!=)')
INCLUDE = re.compile(r'^\s*(?:-|s)?include\s+(.+?)\s*$')
# `+=` appends and is deliberately not read.
ASSIGNMENT = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(\?=|:=|=)\s*(.*?)\s*$')
VARIABLE = re.compile(r'\$[({]([A-Za-z_][A-Za-z0-9_]*)[)}]')
MAX_DEPTH = 4


def targets(root: Path, makefile: str = MAKEFILE) -> frozenset[str]:
    """Every target the root Makefile and its includes declare; no Makefile is an empty set."""
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
