"""rules.py — `[verify]` read once, into typed rules, or refused with exit 2.

    [verify]
    feature   = "make precommit"       # optional. The range rung.
    milestone = "make milestone"       # required. The close.

    [[verify.narrow]]                  # FORWARD: a glob with a named capture
    paths = "src/agentic_sdlc/repo/pm/**"
    run   = "python3 -m pytest tests/test_pm_*.py"

    [[verify.narrow]]                  # REVERSE: the test declares its coverage
    declares = "## covers:"
    scan     = "tests/integration/**"
    run      = "make scenario NAME=<stem>"

THE LADDER HAS THREE RUNGS, and decision D3 (0.2.0) settles what each holds.
`[[verify.narrow]]` is the STORY rung — rules rather than a command, because
the story rung is a FUNCTION of the changed paths and make cannot compute one.
`feature` and `milestone` are the two fixed rungs above it, and each holds THE
NAME OF A MAKE TARGET THE PROJECT ALREADY HAS — `"make precommit"`,
`"make milestone"` — never a second command string of its own.

That is a grammar, enforced below, and it is D3's whole point: the Makefile
stays the authority on what a target RUNS, and `[verify]` is the authority on
which RUNG it is. One fact each. The rejected shape is the one this key used to
have — `wide = "make check test"`, a free command line — which reads fine until
a project's `wide` and its `make milestone` drift apart, and then two answers
exist to "did the full gate pass", with CI running one and the dispatch quoting
the other. `wide` is RENAMED to `milestone` here, not migrated: it is a config
key in a release that has not shipped.

Naming a target also makes the rung JOINABLE to the ledger: a `gate` row is
keyed by make target (`repo/pm/ledger.py`, `GATE_NAME = gates_extra.TARGET`),
so `verify --plan` can print a rung's MEASURED cost instead of a guess. A
free-form command string could not be looked up at all.

WHY THE PARSER IS THE FEATURE. `run` is a shell command read from config and
executed later, and a rule quietly DROPPED from the list is this package's
cardinal sin wearing a new hat: the caller then verifies less than it thinks
and reports success. So nothing here is lenient. Every problem is collected —
ALL of them, not the first — and every message names the rule's own 1-based
DECLARATION index, because with only the first index named an author fixes one
rule and re-runs blind.

Values arrive through `core/config.py`, the one reader: `table_array` for the
array of tables and `text` for every string. That is not ceremony — a bare
string is iterable, and `tuple(cfg.get(...))` over one is `('a','d','d',…)`,
which is how seven gates shipped a silent PASS over an empty census in v0.9.0.
The section itself is passed IN rather than fetched: this module is a pure
grammar over a dict, which keeps `core.config_section` on the CLI edge where
`tests/test_boundaries.py` allowlists it, and lets the whole matrix below be
exercised without a `devkit.toml` on disk.

Exit codes are contract (rule 6): a `[verify]` mistake is `EXIT_CONFIG` — 2 —
and never 1. CI reads 1 as "drift found", and a typo is not drift.

THREE GRAMMAR RULINGS. The feature file left these open; they are settled here
because each unsettled one has a silent-lie failure attached.

  * RULING 1 — a capture never spans a path separator. `<name>` matches one
    segment's worth of characters and stops at `/`, the way a shell glob's `*`
    does. Otherwise `tests/test_<name>.py` matched against `tests/a/b/test_c.py`
    binds `name` to `a/b/test_c`, and THAT value is interpolated into a command
    line. `**` is the only thing here that crosses `/`.
  * RULING 2 — a rule is FORWARD or REVERSE, never both and never neither.
    `paths` + `run` is forward; `declares` + `scan` + `run` is reverse. Any
    other combination is refused, naming the index. A rule carrying `paths` AND
    `declares` has two meanings, and this reader must not pick one.
  * RULING 3 — `<stem>` is the reverse direction's ONLY capture, and it is
    DERIVED (the matched file's stem), not declared. So `stem` is a reserved
    name: a forward `paths` may not declare it, a forward `run` may not
    interpolate it, and a reverse `scan` may not declare any capture at all.

`declares` is a LITERAL line prefix, not a pattern. Nothing here compiles it,
escapes it or matches with it — `declares = ".*"` is a rule looking for those
two characters at the start of a line, and the reverse scan (story 03) reads it
that way.

THE REFUSAL MATRIX. Wider grammar than `[gates] extra`'s, which is a make GOAL
and can therefore ban everything that is not `[A-Za-z0-9._+-]`. A verification
command is a real command line — flags, paths, `NAME=<stem>`, the feature's own
`tests/test_pm_*.py` — so the line is drawn at what makes ONE command into two,
or into a command the author did not write. Each refusal below is exit 2 and
names its index, and none of them does any work first: this module
never spawns a process and it reads no file — parsing is all it does.
(`tests/test_verify_rules.py` holds its AST to both claims.)

  `run` — executed later, so the narrowest of the three:
    * empty, or whitespace only    (a rule that verifies nothing)
    * chaining and substitution    `;` `|` `&` `$` backtick `(` `)` `<` `>`
                                   `#` `\\` — a rule that CHAINS is a rule whose
                                   second half nobody reviewed, and a trailing
                                   `#` comment silently verifies less
    * an embedded newline          (two commands)
    * any other control character, NUL included
    * a capture `run` uses that `paths` does not declare — the single most
      dangerous typo here, because `<undeclared>` otherwise reaches the shell
      literally
    * `<stem>` in a forward rule   (RULING 3)
    * longer than MAX_RUN          (a pasted paragraph in a command slot)
    * absent                       (every rule must say what it runs)

  `feature` / `milestone` — the two fixed rungs, and a NARROWER grammar than
  `run` because D3 says they name a target rather than spelling a command:
    * anything that is not `make <target>` — no flags, no variable
      assignments, no second goal (`make check test` is TWO goals and was the
      rejected shape), no other program
    * a target that is not a make goal by `gates_extra.TARGET`'s grammar, which
      is the same one `[gates] extra` and the ledger's `gate` rows already use
      — a second spelling of one grammar is how two halves come to disagree
      about which names exist
    * `milestone` absent           (a repo with no close; falling back to "run
                                   nothing" is the silent zero-command pass).
                                   `feature` absent is LEGAL and different: the
                                   verb names that rung as unconfigured and
                                   exits 2 when asked for it, rather than
                                   silently running the rung above.

  `paths` / `scan` — globs matched against tracked files, so: inside the tree:
    * traversal and absolute paths (hard rule 8 — nothing reads outside the
      checkout), `~` home expansion, `:` schemes and drive letters
    * empty and dot segments, a trailing `/`, backslash separators
    * malformed or adjacent captures — an unterminated `<` refuses rather than
      matching literally, and two captures with nothing between them is a
      binding this reader would have to guess at
    * a duplicate capture name in one glob (same reason)
    * a glob of nothing but `*` / `**` — it matches the entire tree, which
      makes "narrow" a synonym for "wide" and hides the fact
    * longer than MAX_GLOB

  `declares` / `scan`: one without the other, an empty `declares`, a newline or
  control character in it, longer than MAX_DECLARES.

  Structural: `[verify]` that is not a table, an unknown key in the section
  (`wide` among them — the retired name is refused BY NAME with the new one in
  the message, because a section still spelling it would otherwise read as a
  repo with no close at all) or in a rule (a typo'd `path` for `paths` would
  otherwise make the rule match nothing forever), a rule that is not a table,
  `narrow` as a bare string, and
  an empty `narrow` — refused rather than read as "nothing to do", for
  `config.str_tuple`'s reason. An ABSENT `narrow` is legal and different: it
  declares a repo whose close is its only command.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agentic_sdlc.core.config import ConfigError, table_array, text
from agentic_sdlc.repo import gates_extra

SECTION = 'verify'
NARROW = 'narrow'

# The two fixed rungs, in ladder order — narrow to wide. D3: each names a make
# target the project already has. `narrow` (the story rung) is not here because
# it is not a command; it is a function of the changed paths.
FEATURE = 'feature'
MILESTONE = 'milestone'
RUNGS = (FEATURE, MILESTONE)

# The rung whose absence is a repo with no close. `feature` may be absent; this
# one may not.
REQUIRED_RUNG = MILESTONE

# The name `milestone` replaced, kept only so a section still carrying it is
# refused BY NAME. A retired key that fell out through the generic unknown-key
# path would tell an author "unknown key 'wide'" and leave them to guess.
RETIRED = {'wide': MILESTONE}

# `make <target>`, and nothing else — the whole rung grammar. The prefix is
# fixed rather than "the first word": a rung that could name any program is a
# rung that can drift from the Makefile, which is the shape D3 rejected.
RUNG_PROGRAM = 'make'

# Rule 6: 0 pass, 1 findings, 2 usage/config error. A `[verify]` mistake is
# ALWAYS this one — named here so the verb (story 04) has nothing to invent.
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

# Checked against the value with its VALID captures removed, so `<stem>` is a
# capture and a bare `>` is a redirect. Everything here turns one command into
# two, or into a command the author did not write.
COMMAND_FORBIDDEN = ';|&$`()<>#\\'
# Globs are matched against tracked paths, never executed — the bans are about
# leaving the checkout (`~`, `:`) and about spellings that are not a path.
GLOB_FORBIDDEN = ';|&$`()<>#\\~:\'"'

_CAPTURE = re.compile(r'<([^<>]*)>')
_CAPTURE_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')


@dataclass(frozen=True)
class Rule:
    """One `[[verify.narrow]]` entry, validated, with its captures extracted.

    `index` is the 1-based declaration index — the number every refusal names,
    and the one an author can count to in their own file. `glob` is `paths` for
    a forward rule and `scan` for a reverse one; `pattern` is that glob
    compiled under RULING 1, for the matcher to use against tracked paths.
    `captures` is what the rule BINDS: the names `paths` declares, in order, or
    `('stem',)` for the reverse direction.
    """

    index: int
    kind: str
    run: str
    glob: str
    pattern: re.Pattern
    captures: tuple[str, ...]
    declares: str | None = None


@dataclass(frozen=True)
class RuleSet:
    """The ladder: the story rung's rules, and the two rungs above it.

    `milestone` is always a command — it is required, so it is never ''. In
    ladder order the three are `narrow` (the edit), `feature` (the range) and
    `milestone` (the close).

    `feature` is `None` when the project declared no middle rung, and `None` is
    the point: an empty string would be indistinguishable from a rung
    configured to run nothing, and the verb has to be able to NAME the rung as
    unconfigured rather than skip it.
    """

    milestone: str
    narrow: tuple[Rule, ...]
    feature: str | None = None

    def rung(self, name: str) -> str | None:
        """One fixed rung's command by rung name, or None when unconfigured."""
        return self.feature if name == FEATURE else self.milestone


def rung_target(command: str) -> str:
    """The make target a rung command names — `"make precommit"` -> `precommit`.

    The join to the ledger's `gate` rows, and to the Makefile `--check` reads.
    Only ever called on a value `_rung` already accepted, so it does not
    re-validate: two validators for one grammar is the drift this rename exists
    to remove.
    """
    return command.split()[1]


def read(section: dict) -> RuleSet:
    """The `[verify]` section, typed. Raises ConfigError (exit 2) on anything
    unusable, naming EVERY problem it found and the index of each.

    `section` is what `core.config.config_section('verify')` returns. Structural
    damage — a section that is not a table, a `narrow` that is not an array of
    tables — raises immediately, because there is nothing left to enumerate.
    """
    if not isinstance(section, dict):
        raise ConfigError(f'[{SECTION}] must be a table, got {section!r}')
    # Structural first: the shape has to hold before per-rule problems are
    # worth collecting, and `table_array` refuses the bare-string spelling
    # whole rather than walking it character by character.
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
    """One fixed rung. `milestone` is REQUIRED; `feature` is legally absent.

    A repo with no close has no verification at all, so `milestone` missing is
    a refusal. `feature` missing is a repo that declared two rungs instead of
    three — the verb names it when asked and never substitutes the rung above,
    which would be a story close paying for a milestone gate.
    """
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
    """`make <target>` — exactly two words, the second a make goal.

    D3, enforced. Everything a free command string could be here is refused,
    because a rung that spells its own command line is a second answer to a
    question `Makefile.devkit` already answers, and the two drift.
    """
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
    """(names in order, the value with captures replaced by their names, problems).

    The residue is what the character bans are checked against, so `<stem>` is a
    capture while a bare `>` is a redirect — and a capture keeps a segment's
    worth of text so `a/<x>/b` does not read as an empty segment.
    """
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
    """`run`: one command, and demonstrably only one.

    The rungs do NOT come through here — `_rung_grammar` is narrower still,
    because D3 gives them a target name rather than a command line.
    """
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
    """A validated glob, compiled. RULING 1 lives here.

    `<name>` and `*` are `[^/]`-bounded — they stop at a separator, the way a
    shell glob does. `**` is the only construct that crosses one: as a whole
    segment it spans zero or more of them, so `a/**` covers `a/b.py` and
    `a/b/c.py` alike.
    """
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
