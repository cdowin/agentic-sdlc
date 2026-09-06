"""select.py — changed paths in, one deduplicated command per slice out.

Every changed path lands in exactly one of `matched` or `missed`; the first
matching rule wins per path, and commands dedupe after substitution in
first-emission order. Pure: no filesystem, no subprocess. Hostile tree contents
(paths and bound captures) raise `SelectionError`, exit 2 at the verb.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from agentic_sdlc.repo.verify.rules import COMMAND_FORBIDDEN, FORWARD, Rule

# Past PATH_MAX (4096 on Linux) a value is a payload wearing a path's shape.
MAX_PATH = 4096

# Config cannot know what a directory is called, so a bound value is checked
# here before it becomes two words on a command line.
CAPTURE_FORBIDDEN = frozenset(COMMAND_FORBIDDEN) | frozenset('\'" \t')

# A substituter's spelling: it matches only what `rules.py` already accepted.
CAPTURE = re.compile(r'<([A-Za-z_][A-Za-z0-9_]*)>')

# (rule, path) -> the substituted command, or None when the rule's declarations
# do not cover the path; None for the whole resolver means reverse rules match
# nothing, which is honest for a caller that has not scanned.
ReverseResolver = Callable[[Rule, str], 'str | None']


class SelectionError(Exception):
    """No plan could be produced from this input — exit 2 at the verb,
    never 1."""


@dataclass(frozen=True)
class Match:
    """One command, the rule that produced it, and every path that chose it."""

    command: str
    index: int
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Selection:
    """The plan for one diff: what to run, why, and what nothing covered."""

    commands: tuple[str, ...]
    matched: tuple[Match, ...]
    missed: tuple[str, ...]

    @property
    def matched_paths(self) -> tuple[str, ...]:
        """Every path that produced a command, in first-emission order."""
        return tuple(path for match in self.matched for path in match.paths)


def select(rules: Sequence[Rule], changed_paths: Iterable[str],
           reverse: ReverseResolver | None = None) -> Selection:
    """The narrow plan for `changed_paths`; raises SelectionError on bad input.

    An empty input is an empty Selection, not a pass — the verb says so out
    loud. Without `reverse`, reverse rules match nothing and fall to `missed`.
    """
    paths = list(changed_paths)
    for path in paths:
        _check_path(path)

    # The first emission fixes a command's position for good.
    seen: dict[str, int] = {}
    order: list[tuple[str, int, list[str]]] = []
    missed: list[str] = []

    for path in paths:
        found = _first_match(rules, path, reverse)
        if found is None:
            missed.append(path)
            continue
        command, index = found
        at = seen.get(command)
        if at is None:
            seen[command] = len(order)
            order.append((command, index, [path]))
        else:
            order[at][2].append(path)

    matched = tuple(Match(command=command, index=index, paths=tuple(bound))
                    for command, index, bound in order)
    return Selection(commands=tuple(m.command for m in matched),
                     matched=matched, missed=tuple(missed))


def _first_match(rules: Sequence[Rule], path: str,
                 reverse: ReverseResolver | None) -> tuple[str, int] | None:
    """(command, rule index) from the FIRST rule that claims `path`, or None."""
    for rule in rules:
        if rule.kind == FORWARD:
            hit = rule.pattern.fullmatch(path)
            if hit is None:
                continue
            return substitute(rule, hit.groupdict(), path), rule.index
        if reverse is None:
            continue
        command = reverse(rule, path)
        if command is not None:
            return command, rule.index
    return None


def substitute(rule: Rule, bindings: dict[str, str], path: str) -> str:
    """`rule.run` with every `<name>` replaced by what `path` bound to it.

    A value that would need quoting is refused rather than quoted, so it can
    never reach a shell one refactor later.
    """
    for name, value in sorted(bindings.items()):
        if value is None:  # pragma: no cover - every capture is `[^/]+`
            continue
        bad = sorted(set(value) & CAPTURE_FORBIDDEN)
        control = sorted({c for c in value if ord(c) < 0x20 or ord(c) == 0x7f})
        if bad or control:
            spelled = ', '.join(repr(c) for c in bad + control)
            raise SelectionError(
                f'[verify.narrow] #{rule.index}: {path!r} binds <{name}> to '
                f'{value!r}, which contains {spelled} — that value is '
                f'substituted into a command line, so it is refused here '
                f'rather than quoted: a name that needs quoting is a name the '
                f'rule set cannot verify, and saying so is the only honest '
                f'answer')
    return CAPTURE.sub(lambda m: bindings.get(m.group(1), m.group(0)), rule.run)


def _check_path(path: str) -> None:
    """One changed path, or SelectionError. `a//b` is refused rather than
    canonicalised, so one file cannot match twice under two names."""
    if not isinstance(path, str):
        raise SelectionError(f'changed path {path!r} is not a string')
    if not path:
        raise SelectionError(
            'a changed path is empty — an empty pathspec is the WHOLE tree to '
            'git, which is the opposite of what it looks like')
    if len(path) > MAX_PATH:
        raise SelectionError(
            f'changed path is {len(path)} characters — at most {MAX_PATH}; '
            f'anything longer is a payload wearing a path\'s shape')
    control = sorted({c for c in path if ord(c) < 0x20 or ord(c) == 0x7f})
    if control:
        raise SelectionError(
            f'changed path {path!r} contains control character(s) '
            f'{", ".join(hex(ord(c)) for c in control)} — a rename can carry a '
            f'newline, which is why the diff is read NUL-separated; a path '
            f'that holds one is refused rather than read as two')
    if '\\' in path:
        raise SelectionError(
            f'changed path {path!r} contains a backslash — the separator here '
            f'is "/" only, and a backslash-separated path would match no rule '
            f'while looking like it should')
    if path.startswith('/'):
        raise SelectionError(
            f'changed path {path!r} is absolute — hard rule 8: nothing here '
            f'names a path outside the checkout')
    segments = path.split('/')
    if any(segment == '' for segment in segments):
        raise SelectionError(
            f'changed path {path!r} has an empty segment — "a//b" and a '
            f'trailing "/" are two spellings of one path, and a selector that '
            f'canonicalised them could match one file twice')
    if any(segment in ('.', '..') for segment in segments):
        raise SelectionError(
            f'changed path {path!r} has a "." or ".." segment — traversal is '
            f'refused rather than resolved, because a ".." that MATCHED would '
            f'run a command about a file this repo does not own')
