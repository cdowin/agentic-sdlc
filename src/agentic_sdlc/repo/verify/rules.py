"""rules.py — `[verify]` read once, into typed rules, or refused with exit 2.

The two fixed rungs (`feature`, `milestone`) name a make target the project
already has (D3); `[[verify.narrow]]` rules are the story rung, forward
(`paths` + `run`) or reverse (`declares` + `scan` + `run`), never both. Every
problem is collected and named by the rule's 1-based index. A capture never
spans `/`; `<stem>` is the reverse direction's only capture and is derived;
`declares` is a literal line prefix. Spawns nothing, reads no file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agentic_sdlc.core.config import ConfigError, table_array, text
from agentic_sdlc.repo import gates_extra

SECTION = 'verify'
NARROW = 'narrow'

# The two fixed rungs, narrow to wide; the story rung is not a command.
FEATURE = 'feature'
MILESTONE = 'milestone'
RUNGS = (FEATURE, MILESTONE)

# A repo with no `milestone` has no close; `feature` may be absent.
REQUIRED_RUNG = MILESTONE

# Refused by name, so an author is not left guessing at "unknown key".
RETIRED = {'wide': MILESTONE}

# A rung that could name any program could drift from the Makefile (D3).
RUNG_PROGRAM = 'make'

# Rule 6: a `[verify]` mistake is always 2, never 1.
EXIT_CONFIG = 2

FORWARD = 'forward'
REVERSE = 'reverse'

# The reverse direction's derived capture, and a name nothing may declare.
STEM = 'stem'

MAX_RUN = 512
MAX_GLOB = 256
MAX_DECLARES = 64
MAX_CAPTURE = 32

SECTION_KEYS = frozenset({*RUNGS, NARROW})
FORWARD_KEYS = ('paths', 'run')
REVERSE_KEYS = ('declares', 'scan', 'run')
RULE_KEYS = frozenset(FORWARD_KEYS) | frozenset(REVERSE_KEYS)

# Checked on the value with its valid captures removed, so `<stem>` is a
# capture and a bare `>` is a redirect.
COMMAND_FORBIDDEN = ';|&$`()<>#\\'
# Globs are matched, never executed; the bans are about leaving the checkout.
GLOB_FORBIDDEN = ';|&$`()<>#\\~:\'"'

_CAPTURE = re.compile(r'<([^<>]*)>')
_CAPTURE_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')


@dataclass(frozen=True)
class Rule:
    """One `[[verify.narrow]]` entry, validated. `index` is the 1-based
    declaration index every refusal names; `glob` is `paths` or `scan`;
    `captures` is what the rule binds."""

    index: int
    kind: str
    run: str
    glob: str
    pattern: re.Pattern
    captures: tuple[str, ...]
    declares: str | None = None


@dataclass(frozen=True)
class RuleSet:
    """The ladder: the story rung's rules and the two rungs above it.
    `feature` is None when unconfigured, so the verb can name that rather
    than skip it."""

    milestone: str
    narrow: tuple[Rule, ...]
    feature: str | None = None

    def rung(self, name: str) -> str | None:
        """One fixed rung's command by rung name, or None when unconfigured."""
        return self.feature if name == FEATURE else self.milestone


def rung_target(command: str) -> str:
    """The make target a rung command names — `"make precommit"` ->
    `precommit`. Not re-validated: `_rung` already accepted the value."""
    return command.split()[1]


def read(section: dict) -> RuleSet:
    """The `[verify]` section, typed; raises ConfigError (exit 2) naming
    every problem found and the index of each."""
    if not isinstance(section, dict):
        raise ConfigError(f'[{SECTION}] must be a table, got {section!r}')
    # Structural damage first: there is nothing to enumerate until the shape holds.
    entries = table_array(section, SECTION, NARROW)

    problems: list[str] = []
    for old, new in RETIRED.items():
        if old in section:
            problems.append(
                f'[{SECTION}] {old} was renamed to {new} (decision D3) — and '
                f'{new} names a make target the project already has, not a '
                f'command of its own: `{new} = "make {new}"`. Left as {old} '
                f'this section declares no close at all')
    unknown = sorted(set(section) - SECTION_KEYS - set(RETIRED))
    if unknown:
        problems.append(
            f'[{SECTION}] has unknown key(s) '
            f'{", ".join(repr(key) for key in unknown)} — the section takes '
            f'{", ".join((*RUNGS, NARROW))}; a typo here is a setting that '
            f'never applies')
    rungs = {name: _rung(section, name, problems) for name in RUNGS}

    narrow: list[Rule] = []
    for index, entry in enumerate(entries, start=1):
        rule = _rule(entry, index, problems)
        if rule is not None:
            narrow.append(rule)
    if problems:
        raise ConfigError(_message(problems))
    return RuleSet(milestone=rungs[MILESTONE] or '',
                   feature=rungs[FEATURE], narrow=tuple(narrow))


def _message(problems: list[str]) -> str:
    """One problem reads as itself; several read as a list, all of them named."""
    if len(problems) == 1:
        return problems[0]
    return (f'[{SECTION}] {len(problems)} problems:\n  - '
            + '\n  - '.join(problems))


def _rung(section: dict, key: str, problems: list[str]) -> str | None:
    """One fixed rung: `milestone` is required, `feature` legally absent."""
    where = f'[{SECTION}] {key}'
    if key not in section:
        if key != REQUIRED_RUNG:
            return None
        problems.append(
            f'{where} is required — it is the close, the rung that verifies '
            f'everything, and a rule set without it would fall back to '
            f'running nothing')
        return None
    try:
        value = text(section, SECTION, key, '')
    except ConfigError as err:
        problems.append(str(err))
        return None
    problems.extend(_rung_grammar(value, where, key))
    return value


def _rung_grammar(value: str, where: str, key: str) -> list[str]:
    """`make <target>` — exactly two words, the second a make goal (D3)."""
    words = value.split()
    if len(words) == 2 and words[0] == RUNG_PROGRAM and value == ' '.join(words) \
            and gates_extra.TARGET.fullmatch(words[1]) \
            and len(words[1]) <= gates_extra.MAX_LENGTH:
        return []
    return [
        f'{where} is {value!r} — a rung NAMES a make target the project '
        f'already has, spelled `{RUNG_PROGRAM} <target>` and nothing else '
        f'(for example `{key} = "{RUNG_PROGRAM} {key}"`). D3 rejected a rung '
        f'that carries its own command string: the Makefile stays the '
        f'authority on what a target RUNS, and two answers to "did the full '
        f'gate pass" is a second scoreboard. A target is '
        f'{gates_extra.TARGET.pattern} and at most {gates_extra.MAX_LENGTH} '
        f'characters']


def _rule(entry: dict, index: int, problems: list[str]) -> Rule | None:
    """One `[[verify.narrow]]`. Appends its problems; returns None if it had any."""
    name = f'{SECTION}.{NARROW} #{index}'
    where = f'[{name}]'
    found: list[str] = []

    unknown = sorted(set(entry) - RULE_KEYS)
    if unknown:
        found.append(
            f'{where} has unknown key(s) '
            f'{", ".join(repr(key) for key in unknown)} — a rule takes '
            f'{", ".join(sorted(RULE_KEYS))}; a typo\'d key is a rule that '
            f'matches nothing, forever, in silence')

    has_forward = 'paths' in entry
    has_reverse = 'declares' in entry or 'scan' in entry
    if has_forward and has_reverse:
        found.append(
            f'{where} carries paths AND declares/scan — a rule is FORWARD '
            f'(paths + run) or REVERSE (declares + scan + run), never both. '
            f'Two meanings, and this reader may not pick one')
    elif not has_forward and not has_reverse:
        found.append(
            f'{where} declares neither paths nor declares/scan — a rule is '
            f'FORWARD (paths + run) or REVERSE (declares + scan + run), and '
            f'this one says which files it is about in neither direction')
    if found:
        problems.extend(found)
        return None

    kind = FORWARD if has_forward else REVERSE
    glob_key = 'paths' if kind == FORWARD else 'scan'
    glob = _string(entry, name, glob_key, where, found)
    declares = _string(entry, name, 'declares', where, found) \
        if kind == REVERSE else None
    run = _string(entry, name, 'run', where, found)

    captures: tuple[str, ...] = ()
    if glob is not None:
        captures, glob_problems = _glob(glob, f'{where} {glob_key}', kind)
        found.extend(glob_problems)
    if declares is not None:
        found.extend(_declares(declares, f'{where} declares'))
    if run is not None:
        allowed = frozenset({STEM}) if kind == REVERSE else frozenset(captures)
        found.extend(_command(run, f'{where} run', allowed, kind=kind))

    if found:
        problems.extend(found)
        return None
    return Rule(index=index, kind=kind, run=run, glob=glob,
                pattern=_pattern(glob),
                captures=(STEM,) if kind == REVERSE else captures,
                declares=declares)


def _string(entry: dict, name: str, key: str, where: str,
            found: list[str]) -> str | None:
    """A required string value, through `core.config.text` and nothing else."""
    if key not in entry:
        found.append(f'{where} has no {key} — '
                     + ('every rule must say what it runs' if key == 'run'
                        else f'{key} is required in this direction'))
        return None
    try:
        return text(entry, name, key, '')
    except ConfigError as err:
        found.append(str(err))
        return None


def _captures(value: str, where: str) -> tuple[list[str], str, list[str]]:
    """(names in order, the value with captures replaced by their names,
    problems). The residue is what the character bans are checked against."""
    names: list[str] = []
    residue: list[str] = []
    problems: list[str] = []
    index = 0
    previous_end = -1
    while index < len(value):
        char = value[index]
        if char != '<':
            residue.append(char)
            index += 1
            continue
        token = _CAPTURE.match(value, index)
        if token is None:
            problems.append(
                f'{where} has an unterminated capture at offset {index} — '
                f'"<" opens a capture and must be closed by ">". An unclosed '
                f'"<" is a redirect, not a literal')
            residue.append(char)
            index += 1
            continue
        if previous_end == index:
            problems.append(
                f'{where} has two captures with nothing between them — which '
                f'characters belong to which binding is not a thing this '
                f'reader may pick')
        label = token.group(1)
        if not _CAPTURE_NAME.match(label) or len(label) > MAX_CAPTURE:
            problems.append(
                f'{where}: <{label}> is not a capture name — a name is '
                f'[A-Za-z_][A-Za-z0-9_]* and at most {MAX_CAPTURE} characters')
            residue.append('x')
        else:
            names.append(label)
            residue.append(label)
        index = token.end()
        previous_end = index
    return names, ''.join(residue), problems


def _control(value: str, where: str) -> list[str]:
    """Newlines and every other control character, NUL included."""
    problems: list[str] = []
    if '\n' in value or '\r' in value:
        problems.append(
            f'{where} contains a newline — an embedded newline is two '
            f'commands, and the second one nobody reviewed')
    other = sorted({char for char in value
                    if (ord(char) < 0x20 or ord(char) == 0x7f)
                    and char not in '\n\r'})
    if other:
        problems.append(
            f'{where} contains control character(s) '
            f'{", ".join(hex(ord(char)) for char in other)}')
    return problems


def _command(value: str, where: str, allowed: frozenset[str],
             kind: str = FORWARD) -> list[str]:
    """`run`: one command, demonstrably only one. Rungs go through the
    narrower `_rung_grammar` instead."""
    if not value.strip():
        return [f'{where} is empty — a command that verifies nothing is the '
                f'silent zero-command pass, not a rule']
    problems: list[str] = []
    if len(value) > MAX_RUN:
        problems.append(
            f'{where} is {len(value)} characters — a command is at most '
            f'{MAX_RUN}; anything longer is a pasted paragraph in a command slot')
    problems.extend(_control(value, where))
    names, residue, capture_problems = _captures(value, where)
    problems.extend(capture_problems)
    banned = sorted({char for char in residue if char in COMMAND_FORBIDDEN})
    if banned:
        problems.append(
            f'{where} contains {", ".join(repr(c) for c in banned)} — a '
            f'command that chains, redirects, substitutes or comments is a '
            f'command whose second half nobody reviewed')
    for label in names:
        if label in allowed:
            continue
        if label == STEM and kind == FORWARD:
            problems.append(
                f'{where} interpolates <{STEM}>, which is the REVERSE '
                f'direction\'s derived capture — a forward rule binds only the '
                f'names its paths declares')
        else:
            problems.append(
                f'{where} interpolates <{label}>, which this rule does not '
                f'declare — the placeholder would otherwise reach the shell '
                f'literally')
    return problems


def _glob(value: str, where: str, kind: str) -> tuple[tuple[str, ...], list[str]]:
    """`paths` / `scan`: a relative glob over tracked files, inside the checkout."""
    if not value:
        return (), [f'{where} is empty — a rule that matches nothing is a rule '
                    f'that is not there']
    problems: list[str] = []
    if len(value) > MAX_GLOB:
        problems.append(f'{where} is {len(value)} characters — a glob is at '
                        f'most {MAX_GLOB}')
    if value != value.strip():
        problems.append(f'{where} has leading or trailing whitespace')
    problems.extend(_control(value, where))
    names, residue, capture_problems = _captures(value, where)
    problems.extend(capture_problems)
    banned = sorted({char for char in residue if char in GLOB_FORBIDDEN})
    if banned:
        problems.append(
            f'{where} contains {", ".join(repr(c) for c in banned)} — a glob '
            f'is a relative path pattern: no schemes, no home expansion, no '
            f'backslash separators, no shell punctuation')
    if residue.startswith('/'):
        problems.append(
            f'{where} is absolute — hard rule 8: nothing here reads outside '
            f'the checkout')
    segments = residue.split('/')
    if any(segment == '' for segment in segments):
        problems.append(
            f'{where} has an empty segment — "a//b" and a trailing "/" are '
            f'typos, not patterns')
    dots = sorted({s for s in segments if s in ('.', '..')})
    if dots:
        problems.append(
            f'{where} has a {"/".join(dots)} segment — a rule set names paths '
            f'in the checkout, and traversal is refused rather than resolved')
    if segments and all(segment in ('*', '**') for segment in segments):
        problems.append(
            f'{where} matches the entire tree, which makes "narrow" a synonym '
            f'for "wide" and hides the fact — name the subtree it is about')
    if len(set(names)) != len(names):
        duplicated = sorted({n for n in names if names.count(n) > 1})
        problems.append(
            f'{where} declares {", ".join(f"<{n}>" for n in duplicated)} twice '
            f'— which occurrence wins is not a thing this reader may pick')
    if STEM in names:
        problems.append(
            f'{where} declares <{STEM}>, which is reserved: it is the REVERSE '
            f'direction\'s capture and it is DERIVED from the matched file, '
            f'never declared')
    elif kind == REVERSE and names:
        problems.append(
            f'{where} declares {", ".join(f"<{n}>" for n in names)} — the '
            f'reverse direction binds <{STEM}> and nothing else, derived from '
            f'the file the scan matched')
    return tuple(names), problems


def _declares(value: str, where: str) -> list[str]:
    """The reverse direction's header. A LITERAL line prefix, never a pattern."""
    if not value:
        return [f'{where} is empty — every line starts with "", so an empty '
                f'declares would claim the whole scan']
    problems: list[str] = []
    if len(value) > MAX_DECLARES:
        problems.append(f'{where} is {len(value)} characters — a line prefix is '
                        f'at most {MAX_DECLARES}')
    problems.extend(_control(value, where))
    return problems


def _pattern(glob: str) -> re.Pattern:
    """A validated glob, compiled: `<name>` and `*` stop at `/`, and `**` is
    the only construct that crosses one."""
    out: list[str] = []
    index = 0
    while index < len(glob):
        token = _CAPTURE.match(glob, index)
        if token is not None:
            out.append(f'(?P<{token.group(1)}>[^/]+)')
            index = token.end()
        elif glob.startswith('**/', index):
            out.append('(?:.*/)?')
            index += 3
        elif glob.startswith('**', index):
            out.append('.*')
            index += 2
        elif glob[index] == '*':
            out.append('[^/]*')
            index += 1
        elif glob[index] == '?':
            out.append('[^/]')
            index += 1
        else:
            out.append(re.escape(glob[index]))
            index += 1
    return re.compile(r'\A' + ''.join(out) + r'\Z')
