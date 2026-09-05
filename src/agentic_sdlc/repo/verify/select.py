"""select.py — changed paths in, ONE command per slice out, and the misses named.

Given a parsed rule set (`rules.read`) and a list of changed paths, this answers
what proves that diff:

    Selection(commands=('python3 -m pytest tests/test_pm_x.py',),
              matched=(Match(command=…, index=1, paths=('src/…/a.py', …)),),
              missed=('README.md',))

THE MISS LIST IS THE STORY. A narrow verifier that matches nothing and exits 0
is worse than no verifier: it reports success for work it never checked, which
is hard rule 4's read-side cardinal sin wearing a new hat. So `missed` is a
first-class field of the return value, not a log line a caller may forget to
print — and the invariant below makes an empty-on-both-counts Selection
unreachable rather than merely unlikely:

    len(every path in matched) + len(missed) == len(changed_paths)

with the two sets DISJOINT. Every path lands in exactly one of them. A caller
that ignores `missed` still cannot get a zero-command pass out of a non-empty
diff without the number of missed paths saying so.

A non-empty `missed` is NOT an error here. It is a fact the caller acts on —
the verb (`main.py`) names each path and falls back to the widest rung.

DEDUPE, WHICH IS WHAT "NARROW" ACTUALLY MEANS. Five files under
`systems/combat/` bind `sys=combat` five times and produce ONE
`make unit SYS=combat`. Dedupe happens AFTER substitution, so two DIFFERENT
rules that substitute to the identical command string also collapse, and it
preserves FIRST-EMISSION order, so a rule set's declaration order is the run
order and two runs of one input give byte-identical output. Without this the
narrow path re-runs the same slice per file and stops being narrow — which is
the entire measured 170x this feature exists to collect.

FIRST MATCHING RULE WINS, PER PATH. A path is not fanned out across every rule
that could claim it; that would make ADDING a rule silently multiply the work,
and the run time of a rule set would depend on how many ways it can spell the
same intent. Declaration order is the tie-break, and it is the author's.

TWO CLAIMS THIS MODULE MAKES, BOTH GENERATED AGAINST IN ITS TESTS:

  * it never spawns a process — it does not import `subprocess`, it runs
    nothing, and it does not so much as stat a path. It is a pure function of
    (rules, paths).
  * it never reads the filesystem. `changed_paths` is an ARGUMENT: a selector
    that read the working tree could not be tested against a fixed input, and
    the git call belongs to the verb (story 04).

WHAT IT REFUSES, AND WHY IT IS A DIFFERENT SURFACE FROM `rules.py`'s. `rules.py`
refuses hostile CONFIG. This refuses hostile TREE CONTENTS, which config
validation cannot see — a repository is allowed to contain a file called
`a b.py` or `$(id).py`, and a capture that BINDS one of those names would
otherwise interpolate it into a command line. Both classes raise
`SelectionError` and are exit 2 at the verb: no plan could be produced, which
is a config-or-input problem and never a finding about the code.

  changed path — arrives from `git diff --name-only -z` or from a caller:
    * absolute, or containing a `..` / `.` / empty segment — hard rule 8: a
      `..` that MATCHED would run a command about a file this repo does not own
    * empty, `.`, `..`
    * a newline or any control character — `git diff -z` exists precisely
      because a rename can carry one, and a selector that split on newlines
      would see two paths where the tree has one
    * a backslash — never a directory separator here, so a Windows-shaped path
      is refused rather than silently matching nothing
    * longer than MAX_PATH

  a capture's BOUND VALUE — it is substituted into `run`:
    * whitespace, quotes, and every character `rules.py` bans in a command
      (`;` `|` `&` `$` backtick `(` `)` `<` `>` `#` `\\`), naming BOTH the path
      that bound it and the rule's own 1-based index

A symlink is matched as a PATH and nothing here follows or reads it, which
falls out of never touching the filesystem at all.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from agentic_sdlc.repo.verify.rules import COMMAND_FORBIDDEN, FORWARD, Rule

# A changed path longer than this is not a path a tree produced. PATH_MAX is
# 4096 on Linux and the value a `git diff` line can plausibly carry; anything
# past it is a payload wearing a path's shape.
MAX_PATH = 4096

# The characters a BOUND CAPTURE may not contain. `rules.py`'s command bans,
# plus whitespace and quotes: config cannot know what a directory is called, so
# this is the only place `systems/my combat/` can be caught before
# `make unit SYS=my combat` becomes two words on a command line.
CAPTURE_FORBIDDEN = frozenset(COMMAND_FORBIDDEN) | frozenset('\'" \t')

# The capture spelling, matched against a run string `rules.py` has ALREADY
# validated — every name here is one that rule's `paths` declares. Respelled
# rather than imported from `rules.py` because that module's copy is a
# PARSER's, tolerant of the malformed spellings it exists to refuse; this one
# is a substituter's and matches only what survived.
CAPTURE = re.compile(r'<([A-Za-z_][A-Za-z0-9_]*)>')

# What a reverse resolver is: (rule, path) -> the substituted command, or None
# when that rule's declarations do not cover the path. `declares.py` supplies
# one; None here means reverse rules match nothing, which is the honest
# behaviour for a caller that has not scanned.
ReverseResolver = Callable[[Rule, str], 'str | None']


class SelectionError(Exception):
    """A path or a bound capture this selector will not turn into a command.

    Exit 2 at the verb, never 1. It is not a finding about the code under
    verification — it is "no plan could be produced from this input", which is
    the same class of answer as a malformed `[verify]` section.
    """


@dataclass(frozen=True)
class Match:
    """One command, the rule that produced it, and every path that chose it.

    `paths` is why dedupe can explain itself: five files collapsing to one
    command is only trustworthy if the five are still nameable afterwards.
    Order is input order, and a path appears in exactly one Match.
    """

    command: str
    index: int
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Selection:
    """The plan for one diff: what to run, why, and what nothing covered.

    `commands` is `tuple(m.command for m in matched)` — kept as its own field
    because it is what a caller runs, and deriving it at every call site is how
    two orders of the same list come to exist.
    """

    commands: tuple[str, ...]
    matched: tuple[Match, ...]
    missed: tuple[str, ...]

    @property
    def matched_paths(self) -> tuple[str, ...]:
        """Every path that produced a command, in first-emission order."""
        return tuple(path for match in self.matched for path in match.paths)


def select(rules: Sequence[Rule], changed_paths: Iterable[str],
           reverse: ReverseResolver | None = None) -> Selection:
    """The narrow plan for `changed_paths`. Raises SelectionError on bad input.

    An EMPTY `changed_paths` returns an empty Selection with an empty `missed`,
    and that means exactly one thing: nothing changed, so nothing narrow was
    selected. It is NOT a pass — whether "no diff" is a reason to skip
    verification is the caller's question, and the verb answers it out loud
    rather than letting an empty tuple stand in for a verdict.

    `reverse` resolves REVERSE rules (`declares`/`scan`), which this module
    does not read files for. Without it, reverse rules are passed through
    untouched: they match nothing, and their paths fall to `missed` like any
    other unclaimed path — visible, never silently absorbed.
    """
    paths = list(changed_paths)
    for path in paths:
        _check_path(path)

    # command -> its position in `order`, so dedupe is O(1) per path and the
    # first emission fixes the order for good.
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

    Literal and positional: nothing is quoted, escaped or reordered, because a
    value that would NEED quoting is refused instead. Quoting it would hide the
    fact that a repository contains a filename nobody can put in a command line,
    and hiding it is how the value reaches a shell one refactor later.
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
    """One changed path, or SelectionError. Nothing is normalised into legality.

    `a//b` and `a/./b` are REFUSED rather than cleaned up: they are two
    spellings of one path, and a selector that quietly canonicalises them can
    match the same file twice under two names — which is the dedupe promise
    failing in the one case nobody would look at.
    """
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
