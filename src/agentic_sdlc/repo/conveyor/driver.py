"""driver.py — the conveyor: every check, then at most one write.

`agentic-sdlc close story <id>`, `agentic-sdlc close feature <id>`,
`agentic-sdlc release <version>` and `agentic-sdlc adopt <version>` are one
machine over four check lists. D12 (`decisions.md`), Chris, 2026-09-05:

> *"You say `close feature` and it goes `error: story xyz not closed`. It
> doesn't do anything, no feature closed, just a clean error. It wants all
> stories under it to be in any matching done state. But it doesn't do
> anything else. That's up to the caller. The actions ARE the checks. And a
> `--force` flag does the action anyway."*

So a belt is: every check in its list runs and prints one line — `ok` or
`error: <check>: <what is false>` — and then AT MOST ONE write, the status of
the grain the belt was asked about, set to the FIRST state of its kind's `done`
category (`[pm.states.<kind>] done`, read through `model.flow_of`, never a
literal). All true → the write, exit 0. Any false → no write, exit 1.
`--force` → the write anyway, and the ledger's `deviation` row names the checks
that were false. `adopt` has no grain to write; it is checks only. Nothing else
is written, moved, bumped, retitled, pushed or tagged: what the caller does
next is printed as words (`steps.AFTER`).

## What a check may answer

`Answer` carries three truths and the third is why it is not a bool:
UNVERIFIABLE is not "no", it is "this cannot be decided" — a callee's exit 2
(D11), a crash inside a check, a record that does not parse. For the write it
counts as false, because a write over a question nobody answered is rule 4's
cardinal sin; on the line it is named apart, because the fix is different.

## Exit codes (rule 6) and the two exit 2s

`0` every check true (or `--force`) and the write landed; `1` a check is false
and nothing was written, or the write itself was refused; `2` this machine
could not READ its own declaration — a malformed subject, an unknown check
name in `[<operation>] steps`, a bad config value, an undeclared `done`
category — before the first check, or at the check whose reader met it
(D11: the lines already printed stay, one line names the check, nothing after
it runs, and nothing is written).

Line shapes are contract (rule 6):

    [story] ok: committed — no modified path outside pm/roadmap/
    [story] error: evidence-written: …/s1.md carries no `done:` line — …
    [story] unverifiable: narrow-verified: `agentic-sdlc verify --story` exited 2 — …
    [story] error — 1 check(s) false; nothing written
    [story] ok — 0.2.0/f/s1 → done
    [story] forced — 0.2.0/f/s1 → done over 1 false check(s)
    next: commit the roadmap directory — …
    [adopt] ok — 7 check(s) true; nothing to write
"""
from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Sequence

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo.pm import ledger, model

# The operations this driver runs. `story` and `feature` are the two INNER
# levels (SDLC.md §0), reached through `close`; `release` and `adopt` are
# verbs of their own. `agentic-sdlc story` would be a second spelling of
# `pm story` and mean something else, so the grain is a subcommand of `close`.
CLOSE_VERB = 'close'
CLOSE_OPERATIONS = ('story', 'feature')
OPERATIONS = ('release', 'adopt', *CLOSE_OPERATIONS)
VERBS = ('release', 'adopt', CLOSE_VERB)

# Which grain KIND each operation writes — the key of `[pm.states.<kind>]` —
# and '' for the one that writes nothing.
WRITES = {'release': 'milestone', 'story': 'story', 'feature': 'feature',
          'adopt': ''}

# How many `/`-separated segments each operation's subject carries, and what
# to call it in a refusal. One table rather than a branch.
SUBJECT = {
    'release': (1, 'version', '<version>'),
    'adopt': (1, 'version', '<version>'),
    'story': (3, 'story id', '<milestone>/<feature>/<story>'),
    'feature': (2, 'feature id', '<milestone>/<feature>'),
}

# A milestone id is a path segment joined onto `pm/roadmap/`, and the pm
# tracker owns that grammar (`model.segment_is_literal`).
MAX_VERSION = 128
MAX_SUBJECT = MAX_VERSION * len(SUBJECT['story'][2].split('/'))
# How much of a hostile argument is quoted back.
QUOTE_LIMIT = 40

# The `outcome` a forced run's deviation row carries. `ledger.OUTCOMES` does
# not list it yet (that table is `pm`'s), so the row is minted here with the
# same keys `ledger.deviation_row` writes and the same reason bound.
FORCED = 'forced'
# The `outcome` word an UNVERIFIABLE answer is named by on the line.
UNVERIFIABLE_WORD = 'unverifiable'


class Truth(Enum):
    """What a check answered. Three values: UNVERIFIABLE is not "no", it is
    "this cannot be decided", and collapsing it into either one is how a
    machine comes to write over a question nobody answered."""

    TRUE = 'true'
    FALSE = 'false'
    UNVERIFIABLE = 'unverifiable'


@dataclass(frozen=True)
class Answer:
    """A check's return: the truth, and the sentence a human needs. `detail`
    is what the `error:` line prints after the check's name — a check that
    answers FALSE with an empty detail has said something is wrong and
    nothing about what."""

    truth: Truth
    detail: str = ''

    @property
    def is_true(self) -> bool:
        return self.truth is Truth.TRUE

    @classmethod
    def yes(cls, detail: str = '') -> 'Answer':
        return cls(Truth.TRUE, detail)

    @classmethod
    def no(cls, detail: str = '') -> 'Answer':
        return cls(Truth.FALSE, detail)

    @classmethod
    def unverifiable(cls, detail: str = '') -> 'Answer':
        return cls(Truth.UNVERIFIABLE, detail)


@dataclass(frozen=True)
class Context:
    """What every check is handed: the checkout, the operation, the subject.
    A check that needs more asks the tree."""

    root: Path
    operation: str
    version: str


@dataclass(frozen=True)
class Check:
    """One check: a name and a question about the tree. There is no second
    callable — a check is not made true by this machine (D12)."""

    name: str
    check: Callable[[Context], Answer]


@dataclass(frozen=True)
class Result:
    """What one run did. `false` names every check that was not true (an
    UNVERIFIABLE answer is among them); `written` is the state the one write
    set, or '' when nothing was written; `refused` is the one sentence a
    `ConfigError` met DURING the run left behind (exit 2, D11)."""

    lines: tuple[str, ...]
    false: tuple[str, ...]
    written: str
    exit_code: int
    refused: str = ''


def ask(check: Check, ctx: Context) -> Answer:
    """`check.check(ctx)`, with an unexpected exception turned into an ANSWER.

    Every check is asked on every run, so a latent crash in check 6 surfaces
    on a tree where check 3 is false — and an uncaught exception is exit 1
    with a traceback, which rule 6 gives to FINDINGS. UNVERIFIABLE rather than
    FALSE: a check that crashed did not answer "no", it failed to answer.
    `ConfigError` is RE-RAISED: a malformed declaration is the reader
    failing, and it belongs to exit 2 (`run` catches it at the check).
    """
    try:
        return check.check(ctx)
    except ConfigError:
        raise
    except Exception as err:  # noqa: BLE001 — an answer, not a swallow
        return Answer.unverifiable(
            f'{type(err).__name__} while checking: {err}')


# --- the registry and the list ------------------------------------------------
# `REGISTRY` is an injection seam: anything in it wins, so a test (or a
# language kit) can add a check without editing the shipped list.
REGISTRY: dict[str, Check] = {}


def registry_for(operation: str) -> dict[str, Check]:
    """The checks this package SHIPS for `operation`, by name. The import is
    LOCAL because `steps` imports the shapes above from here."""
    from agentic_sdlc.repo.conveyor import steps as step_defs
    known = step_defs.registry_for(operation)
    known.update(REGISTRY)
    return known


def step_names(operation: str) -> tuple[str, ...]:
    """The ordered check list for `operation`, from `[<operation>] steps`. A
    project that declares nothing gets the shipped default byte-identically
    (rule 5); a misspelled name is exit 2, never a quietly shorter belt."""
    from agentic_sdlc.repo.conveyor import steps as step_defs
    known = registry_for(operation)
    names = step_defs.steps_for(operation, known)
    step_defs.validate_config(operation, names, known)
    return names


def plan_defect(registry: Mapping[str, Check], names: Sequence[str]) -> str:
    """'' when this list can be run whole, else why it cannot. A run that
    asked nothing must not report ok over a census of zero."""
    if not names:
        return ('no checks to run — the list is empty, and a run that asked '
                'nothing must not report ok')
    missing = [n for n in names if n not in registry]
    if missing:
        return ('no check is registered for '
                + ', '.join(repr(m) for m in missing))
    return ''


def done_state(cfg: 'model.PmConfig', kind: str) -> str:
    """The FIRST state of `[pm.states.<kind>] done` — what a belt writes.

    Through `model.flow_of`, which refuses an undeclared flow at exit 2 by
    name; `_flow_defect` already guarantees every category holds at least one
    state, so `[0]` cannot miss. Never a literal: the word is the project's.
    """
    return model.flow_of(cfg, kind).by_category[model.DONE_CATEGORY][0]


# --- the run ------------------------------------------------------------------
Writer = Callable[[Context, str], tuple[bool, str]]
Recorder = Callable[[Sequence[tuple[str, str]]], str]


def run(registry: Mapping[str, Check], names: Sequence[str], ctx: Context,
        *, force: bool = False, state: str = '',
        write: Writer | None = None,
        record: Recorder | None = None) -> Result:
    """Ask every check, print each, then write once or not at all.

    `state` is the done state the write sets and `write` performs it — both
    are handed in so that the decision (here) and the mechanism (`main`'s
    `_writer`, which is `pm <kind> <state> <id>`) are two functions with one
    seam between them, and a test can stub either. `record` mints the
    `deviation` row a forced write leaves; it returns '' or why the row could
    not be written. With `state == ''` the operation writes nothing (adopt).
    """
    op = ctx.operation
    defect = plan_defect(registry, names)
    if defect:
        return Result((f'[{op}] error — {defect}',), (), '', 2, defect)
    lines: list[str] = []
    false: list[tuple[str, str]] = []
    for name in names:
        try:
            answer = ask(registry[name], ctx)
        except ConfigError as err:
            # D11: the reader failed AT this check. Everything already asked
            # stays on the transcript; nothing after it runs; nothing is
            # written.
            refused = f'check {name!r}: {err}'
            lines.append(f'[{op}] error — {refused}; nothing written')
            return Result(tuple(lines), tuple(n for n, _ in false), '', 2,
                          refused)
        if answer.is_true:
            lines.append(f'[{op}] ok: {name}'
                         + (f' — {answer.detail}' if answer.detail else ''))
            continue
        # A check that is not true and gave no reason has a DEFECT, and the
        # defect is what gets reported rather than laundered into silence.
        reason = answer.detail or (
            'the check answered no and gave no reason — a defect in the '
            'check, not a fact about the tree')
        word = (UNVERIFIABLE_WORD if answer.truth is Truth.UNVERIFIABLE
                else 'error')
        lines.append(f'[{op}] {word}: {name}: {reason}')
        false.append((name, reason))
    names_false = tuple(n for n, _ in false)
    if false and not force:
        lines.append(f'[{op}] error — {len(false)} check(s) false; nothing '
                     f'written')
        return Result(tuple(lines), names_false, '', 1)
    if not state:
        # adopt: checks only. `--force` was refused before this point.
        lines.append(f'[{op}] ok — {len(names)} check(s) true; nothing to '
                     f'write')
        return Result(tuple(lines), names_false, '', 0)
    if write is None:
        raise ValueError(f'{op} writes {state!r} and no writer was given')
    landed, said = write(ctx, state)
    if said:
        lines.append(f'[{op}] write: {said}')
    if not landed:
        lines.append(f'[{op}] error — the write was refused; nothing written')
        return Result(tuple(lines), names_false, '', 1)
    if false:
        lines.append(f'[{op}] forced — {ctx.version} → {state} over '
                     f'{len(false)} false check(s)')
        blocked = record(false) if record is not None else ''
        if blocked:
            lines.append(f'[{op}] WARNING — the deviation row naming the '
                         f'forced checks was not written: {blocked}')
    else:
        lines.append(f'[{op}] ok — {ctx.version} → {state}')
    return Result(tuple(lines), names_false, state, 0)


# --- the verb -----------------------------------------------------------------

USAGE = """\
agentic-sdlc {op} {subject}
agentic-sdlc {op} {subject} --force

Run every check in the {state} list, print each one, then write ONCE or not
at all: {writes}

  {subject}
              a grain id — the same grammar `pm` uses, segment for segment
  --force     write anyway; the milestone's ledger.jsonl gets one `deviation`
              row naming the checks that were false

One line per check — `ok: <check> — <detail>`, `error: <check>: <what is
false>`, or `unverifiable: <check>: <why>` (counts as false) — then one of:

    [{state}] ok — <grain> → <state>
    [{state}] error — N check(s) false; nothing written
    [{state}] forced — <grain> → <state> over N false check(s)

and, after a write, `next:` lines saying what is yours to do. Nothing else
is written, moved, bumped, retitled, pushed or tagged.

Exit codes: 0 written (or nothing to write), 1 a check is false and nothing
was written, 2 the declaration could not be read.\
"""

CLOSE_USAGE = f"""\
agentic-sdlc {CLOSE_VERB} story   <milestone>/<feature>/<story>   [--force]
agentic-sdlc {CLOSE_VERB} feature <milestone>/<feature>           [--force]

The two INNER belts (SDLC.md §0). Each runs its checks, prints one line per
check, and then writes exactly one thing or nothing: the grain's status, set
to the first state of its kind's `done` category (`[pm.states.<kind>] done`).

  story    the story exists; `verify --story` over its commit range is green;
           nothing outside the roadmap directory is uncommitted; the story
           carries a `done:` line.
  feature  every story is in the `done` category (each one that is not is
           named, by `pm ready-for feature`); `reviewed:` points at a record
           that parses; no finding in it is `open`.

Any check false → `error:` lines, exit 1, nothing written. `--force` writes
anyway and the ledger row names the false checks. `agentic-sdlc {CLOSE_VERB}
story --help` prints the full line shapes. The belt above these two is
`agentic-sdlc release <version>`.\
"""


def _spoken(operation: str) -> str:
    """How this operation is INVOKED, which is not always its name."""
    return (f'{CLOSE_VERB} {operation}' if operation in CLOSE_OPERATIONS
            else operation)


def _writes(operation: str) -> str:
    kind = WRITES[operation]
    if not kind:
        return 'this one writes nothing — it is checks only.'
    return (f'the {kind}\'s status, set to the first state of '
            f'[pm.states.{kind}] done. Any check false → exit 1 and no write.')


def parse_flags(rest: Sequence[str]) -> tuple[bool, list[str], str]:
    """(--force, positionals, '' or the usage defect).

    `--skip`, `--reason` and `--status` are named rather than swept into
    `unknown option`, because a consumer's script may still carry them.
    """
    force = False
    positional: list[str] = []
    for arg in rest:
        if arg == '--force':
            force = True
        elif arg in ('--skip', '--reason', '--status'):
            return False, [], (
                f'{arg} was removed in 0.2.0: a belt is its checks and then '
                f'one write. `--force` writes over false checks and the '
                f'ledger row names them; `pm ledger report` reads those rows')
        elif arg.startswith('-'):
            return False, [], f'unknown option {arg!r}'
        else:
            positional.append(arg)
    return force, positional, ''


def _refuse(message: str) -> int:
    print(f'agentic-sdlc: {message}', file=sys.stderr)
    return 2


def _quote(value: str) -> str:
    shown = value if len(value) <= QUOTE_LIMIT else value[:QUOTE_LIMIT] + '…'
    return repr(shown)


def version_defect(value: str) -> str:
    """'' when `value` may be joined onto the roadmap directory, else why not.
    The grammar is `model.segment_is_literal` plus length and whitespace."""
    if not value:
        return 'the version is empty'
    if len(value) > MAX_VERSION:
        return (f'the version is too long ({len(value)} characters; the limit '
                f'is {MAX_VERSION})')
    if any(ch.isspace() for ch in value):
        return f'{_quote(value)} carries whitespace, which no milestone id has'
    if not model.segment_is_literal(value):
        return (f'{_quote(value)} is not a milestone id — globs, path '
                f'separators, schemes, absolute paths and the "." / ".." '
                f'segments are all refused')
    return ''


def subject_defect(operation: str, value: str) -> str:
    """'' when `value` may be this operation's subject, else why not. ONE
    grammar, applied per segment; the segment COUNT is checked because
    `close story` given a feature id would resolve to a real file and get the
    wrong question answered about it."""
    segments, noun, shape = SUBJECT.get(operation, SUBJECT['release'])
    if segments == 1:
        return version_defect(value)
    if not value:
        return f'the {noun} is empty'
    if len(value) > MAX_SUBJECT:
        return (f'the {noun} is too long ({len(value)} characters; the limit '
                f'is {MAX_SUBJECT})')
    if any(ch.isspace() for ch in value):
        return f'{_quote(value)} carries whitespace, which no {noun} has'
    parts = value.split('/')
    if len(parts) != segments:
        return (f'{_quote(value)} is not a {noun} — a {operation} id is '
                f'{segments} segments, {shape}; this one has {len(parts)}')
    for part in parts:
        if len(part) > MAX_VERSION:
            return (f'{_quote(value)}: one segment is {len(part)} characters; '
                    f'the limit is {MAX_VERSION}')
        if not model.segment_is_literal(part):
            return (f'{_quote(value)} is not a {noun} — globs, path '
                    f'separators, schemes, absolute paths and the "." / ".." '
                    f'segments are all refused')
    return ''


def grain_path(cfg, operation: str, subject: str) -> Path | None:
    """The file a close operation's subject names, or None — `model`'s own
    resolvers, never a second walk."""
    if operation == 'story':
        return model.story_file(cfg, subject)
    return model.feature_file(cfg, subject)


def _config(root: Path | None) -> 'model.PmConfig':
    """The pm config, optionally re-rooted at a scratch tree."""
    cfg = model.load()
    return cfg if root is None else replace(cfg, root=Path(root))


def _writer(cfg: 'model.PmConfig', kind: str) -> Writer:
    """THE ONE WRITE: `pm <kind> <state> <id>`, in process.

    Through the pm CLI and never a regex over frontmatter — `check pm` is the
    drift gate and it reads what the CLI writes, and the CLI is what mints
    the `status` ledger row. Exit 0 is landed; anything else is refused with
    the CLI's own words.
    """
    from agentic_sdlc.repo.pm import cli as pm_cli

    def write(ctx: Context, state: str) -> tuple[bool, str]:
        argv = [kind, state, ctx.version]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(buffer):
            code = pm_cli.main(argv)
        said = ' '.join(buffer.getvalue().split())
        return code == 0, f'`pm {" ".join(argv)}` exited {code}: {said}'

    return write


def _recorder(mdir: Path, operation: str, subject: str) -> Recorder:
    """The `deviation` row a forced write leaves: one row, `step` naming every
    false check, `reason` carrying each one's own sentence, `outcome`
    `forced`. The row's keys are `ledger.deviation_row`'s."""
    def record(false: Sequence[tuple[str, str]]) -> str:
        reason = '; '.join(f'{name}: {why}' for name, why in false)
        # One row is one line: the three characters `reason_defect` refuses
        # become spaces. U+2028/9 are left alone — `ledger.dumps` escapes them.
        for char in ('\n', '\r', '\x00'):
            reason = reason.replace(char, ' ')
        if len(reason) > ledger.REASON_MAX:
            reason = reason[:ledger.REASON_MAX - 1] + '…'
        defect = ledger.reason_defect(reason)
        if defect:
            return defect
        row = {'ts': ledger.utc_now(), 'kind': ledger.KIND_DEVIATION,
               'grain': subject, 'operation': operation,
               'step': ', '.join(name for name, _ in false),
               'outcome': FORCED, 'reason': reason}
        try:
            ledger.append_row(mdir, row)
        except (ledger.LedgerError, OSError) as err:
            return str(err)
        return ''

    return record


def _after(cfg: 'model.PmConfig', operation: str, subject: str) -> list[str]:
    """The `next:` lines, from `steps.AFTER`, with the tree's own words filled
    in. Read-only: a missing `branch:` renders as the placeholder."""
    from agentic_sdlc.repo.conveyor import steps as step_defs

    mid = subject.split('/')[0]
    path = model.milestone_file(cfg, mid)
    branch = (model.field_of(path, 'branch') if path is not None else '') \
        or '<branch>'
    try:
        mainline = model.mainline_branch()
        commands = step_defs.commands_for(operation)
    except ConfigError:
        mainline, commands = '<mainline>', {}
    return [f'next: {line}' for line in step_defs.after_lines(
        operation, commands, version=subject, branch=branch,
        mainline=mainline)]


def main(argv: Sequence[str], *, root: Path | None = None,
         registry: Mapping[str, Check] | None = None,
         steps: Sequence[str] | None = None,
         write: Writer | None = None) -> int:
    """`argv[0]` is the VERB (`release` / `adopt` / `close`); the rest is its
    own. `root`, `registry`, `steps` and `write` are injection seams for
    tests; every one of them defaults to the real thing."""
    args = list(argv)
    if not args:
        return _refuse(
            f'an operation is required (expected: {", ".join(OPERATIONS)})')
    operation, rest = args[0], args[1:]
    if operation in ('-h', '--help', 'help'):
        print(__doc__.strip())
        return 0
    if operation == CLOSE_VERB:
        if rest and rest[0] in ('-h', '--help', 'help'):
            print(CLOSE_USAGE)
            return 0
        if not rest:
            return _refuse(
                f'{CLOSE_VERB} needs a grain '
                f'(expected: {", ".join(CLOSE_OPERATIONS)})')
        if rest[0] not in CLOSE_OPERATIONS:
            return _refuse(
                f'unknown grain {rest[0]!r} — `{CLOSE_VERB}` closes one of '
                f'{", ".join(CLOSE_OPERATIONS)}. A milestone closes through '
                f'`agentic-sdlc release <version>`, which is the belt above '
                f'these two')
        operation, rest = rest[0], rest[1:]
    if operation not in OPERATIONS:
        return _refuse(f'unknown operation {operation!r} '
                       f'(expected: {", ".join(OPERATIONS)})')
    spoken = _spoken(operation)
    if any(a in ('-h', '--help', 'help') for a in rest):
        print(USAGE.format(op=spoken, state=operation,
                           subject=SUBJECT[operation][2],
                           writes=_writes(operation)))
        return 0

    force, positional, flag_defect = parse_flags(rest)
    segments, noun, shape = SUBJECT[operation]
    if flag_defect:
        return _refuse(f'{spoken}: {flag_defect}')
    if not positional:
        return _refuse(f'{spoken} needs a {shape} — the {noun} to close, e.g. '
                       f'`agentic-sdlc {spoken} '
                       f'{"0.2.0" if segments == 1 else shape}`')
    if len(positional) > 1:
        return _refuse(f'{spoken} takes exactly one {shape}; got '
                       f'{len(positional)} — one operation, one grain')
    subject = positional[0]
    defect = subject_defect(operation, subject)
    if defect:
        return _refuse(f'{spoken}: {defect}')
    kind = WRITES[operation]
    if force and not kind:
        return _refuse(f'{spoken} writes nothing, so there is nothing to '
                       f'force — it is checks only')

    # Everything above refused without touching the filesystem. From here the
    # tree is READ, and nothing is written until every check has answered.
    try:
        cfg = _config(root)
        names = tuple(steps) if steps is not None else step_names(operation)
        known = (dict(registry) if registry is not None
                 else registry_for(operation))
        # The state the write sets is read BEFORE the first check: an
        # undeclared `done` category is the reader failing, and it fails
        # before anything runs rather than after every check printed ok.
        state = done_state(cfg, kind) if kind else ''
    except ConfigError as err:
        return _refuse(f'{spoken}: {err}')
    defect = plan_defect(known, names)
    if defect:
        return _refuse(f'{spoken}: {defect}')
    mid = subject.split('/')[0]
    mdir = model.milestone_dir(cfg, mid)
    if mdir is None:
        # The milestone directory is where the ledger row goes and where the
        # grain lives; a subject naming none has nothing to check.
        print(f'agentic-sdlc: {spoken} {subject}: no milestone directory '
              f'{cfg.rel(cfg.roadmap)}/{mid}-* — refused, and nothing was '
              f'written', file=sys.stderr)
        return 1

    ctx = Context(root=cfg.root, operation=operation, version=subject)
    result = run(known, names, ctx, force=force, state=state,
                 write=write if write is not None else _writer(cfg, kind),
                 record=_recorder(mdir, operation, subject))
    for line in result.lines:
        print(line)
    if result.refused:
        # D11: one line on stderr, the transcript already on stdout, exit 2.
        return _refuse(f'{spoken}: {result.refused}')
    if result.exit_code == 0:
        for line in _after(cfg, operation, subject):
            print(line)
    return result.exit_code
