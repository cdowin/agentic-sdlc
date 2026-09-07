"""driver.py — the conveyor: every check, then at most one write (D12).

`close story <id>`, `close feature <id>`, `release <version>` and
`adopt <version>` are one machine over four check lists. Every check prints
one line — `ok: <check> — <detail>`, `error: <check>: <what is false>` or
`unverifiable: <check>: <why>` (counts as false) — then: all true → the
grain's status is set to the first state of `[pm.states.<kind>] done`, exit 0;
any false → no status written, exit 1; `--force` → the write anyway and a
ledger `deviation` row naming the false checks. `adopt` is checks only. Exit 2
is a declaration this machine could not read (D11). What the caller does next
is printed as `next:` lines; nothing else is written, moved, pushed or tagged.
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

# `story` and `feature` are subcommands of `close`, since `agentic-sdlc story`
# would be a second spelling of `pm story`.
CLOSE_VERB = 'close'
CLOSE_OPERATIONS = ('story', 'feature')
OPERATIONS = ('release', 'adopt', *CLOSE_OPERATIONS)
VERBS = ('release', 'adopt', CLOSE_VERB)

# The grain kind each operation writes; '' for the one that writes nothing.
WRITES = {'release': 'milestone', 'story': 'story', 'feature': 'feature',
          'adopt': ''}

# Segment count, noun and shape of each operation's subject.
SUBJECT = {
    'release': (1, 'version', '<version>'),
    'adopt': (1, 'version', '<version>'),
    # The count only separates a version subject from a grain one.
    'story': (2, 'story id', '<story-id>'),
    'feature': (2, 'feature id', '<feature-id>'),
}

# A milestone id is one path segment; `model.segment_is_literal` owns the
# grammar.
MAX_VERSION = 128
MAX_SUBJECT = MAX_VERSION * len(SUBJECT['story'][2].split('/'))
# How much of a hostile argument is quoted back.
QUOTE_LIMIT = 40

# `ledger.OUTCOMES` does not list it, so the row is minted here with
# `ledger.deviation_row`'s keys.
FORCED = 'forced'
# The word an UNVERIFIABLE answer is named by on the line.
UNVERIFIABLE_WORD = 'unverifiable'
# What a checks-only belt says about the record, before its first check: it
# writes nothing (D12), so the milestone directory is where a row WOULD land
# and never a condition for running.
NOTHING_RECORDED = 'nothing recorded, because this belt writes nothing'
ANYWHERE = 'the bump may be tracked as a feature, as a story, or nowhere'


class Truth(Enum):
    """What a check answered; UNVERIFIABLE is "this cannot be decided", not
    "no"."""

    TRUE = 'true'
    FALSE = 'false'
    UNVERIFIABLE = 'unverifiable'


@dataclass(frozen=True)
class Answer:
    """A check's return: the truth, and the sentence the line prints after
    the check's name."""

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
    """What every check is handed: the checkout, the operation, the subject."""

    root: Path
    operation: str
    version: str


@dataclass(frozen=True)
class Check:
    """One check: a name and a question about the tree; nothing performs
    anything (D12)."""

    name: str
    check: Callable[[Context], Answer]


@dataclass(frozen=True)
class Result:
    """What one run did: `false` names every check not true, `written` is
    the state set or '', `refused` is a mid-run `ConfigError`'s sentence
    (exit 2, D11)."""

    lines: tuple[str, ...]
    false: tuple[str, ...]
    written: str
    exit_code: int
    refused: str = ''


def ask(check: Check, ctx: Context) -> Answer:
    """`check.check(ctx)`, with an unexpected exception turned into an
    UNVERIFIABLE answer; `ConfigError` is re-raised because a malformed
    declaration is the reader failing (exit 2)."""
    try:
        return check.check(ctx)
    except ConfigError:
        raise
    except Exception as err:  # noqa: BLE001 — an answer, not a swallow
        return Answer.unverifiable(
            f'{type(err).__name__} while checking: {err}')


# --- the registry and the list ------------------------------------------------
# An injection seam: anything here wins, so a test can add a check without
# editing the shipped list.
REGISTRY: dict[str, Check] = {}


def registry_for(operation: str) -> dict[str, Check]:
    """The checks shipped for `operation`, by name; the import is local
    because `steps` imports from here."""
    from agentic_sdlc.repo.conveyor import steps as step_defs
    known = step_defs.registry_for(operation)
    known.update(REGISTRY)
    return known


def step_names(operation: str) -> tuple[str, ...]:
    """The ordered check list from `[<operation>] steps`; a misspelled name
    is exit 2, never a quietly shorter belt."""
    from agentic_sdlc.repo.conveyor import steps as step_defs
    known = registry_for(operation)
    names = step_defs.steps_for(operation, known)
    step_defs.validate_config(operation, names, known)
    return names


def plan_defect(registry: Mapping[str, Check], names: Sequence[str]) -> str:
    """'' when this list can be run whole, else why it cannot."""
    if not names:
        return ('no checks to run — the list is empty, and a run that asked '
                'nothing must not report ok')
    missing = [n for n in names if n not in registry]
    if missing:
        return ('no check is registered for '
                + ', '.join(repr(m) for m in missing))
    return ''


def done_state(cfg: 'model.PmConfig', kind: str) -> str:
    """The first state of `[pm.states.<kind>] done` — what a belt writes,
    never a literal; `model.flow_of` refuses an undeclared flow at exit 2."""
    return model.flow_of(cfg, kind).by_category[model.DONE_CATEGORY][0]


# --- the run ------------------------------------------------------------------
Writer = Callable[[Context, str], tuple[bool, str]]
Recorder = Callable[[Sequence[tuple[str, str]]], str]


def run(registry: Mapping[str, Check], names: Sequence[str], ctx: Context,
        *, force: bool = False, state: str = '',
        write: Writer | None = None,
        record: Recorder | None = None) -> Result:
    """Ask every check, print each, then write once or not at all.

    `state` and `write` are handed in so decision and mechanism are two
    functions with one seam; `record` mints a forced write's `deviation` row
    and returns '' or why it could not; `state == ''` writes nothing.
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
            # D11: the reader failed at this check; nothing after it runs.
            refused = f'check {name!r}: {err}'
            lines.append(f'[{op}] error — {refused}; no status written')
            return Result(tuple(lines), tuple(n for n, _ in false), '', 2,
                          refused)
        if answer.is_true:
            lines.append(f'[{op}] ok: {name}'
                         + (f' — {answer.detail}' if answer.detail else ''))
            continue
        # A check that is not true and gave no reason has a defect, and the
        # defect is what gets reported.
        reason = answer.detail or (
            'the check answered no and gave no reason — a defect in the '
            'check, not a fact about the tree')
        word = (UNVERIFIABLE_WORD if answer.truth is Truth.UNVERIFIABLE
                else 'error')
        lines.append(f'[{op}] {word}: {name}: {reason}')
        false.append((name, reason))
    names_false = tuple(n for n, _ in false)
    if false and not force:
        lines.append(f'[{op}] error — {len(false)} check(s) false; '
                     f'no status written')
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
        lines.append(f'[{op}] error — the write was refused; no status written')
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
    [{state}] error — N check(s) false; no status written
    [{state}] forced — <grain> → <state> over N false check(s)

and, after a write, `next:` lines saying what is yours to do. Nothing else
is written, moved, bumped, retitled, pushed or tagged.

Exit codes: 0 written (or nothing to write), 1 a check is false and nothing
was written, 2 the declaration could not be read.\
"""

CLOSE_USAGE = f"""\
agentic-sdlc {CLOSE_VERB} story   <story-id>     [--force]
agentic-sdlc {CLOSE_VERB} feature <feature-id>   [--force]

The two INNER belts (SDLC.md §0). Each runs its checks, prints one line per
check, and then writes exactly one thing or nothing: the grain's status, set
to the first state of its kind's `done` category (`[pm.states.<kind>] done`).

  story    the story exists; `verify --story` (the `[verify] story` make
           target) is green; nothing outside the roadmap directory is
           uncommitted; the story carries a `done:` line.
  feature  every story is in the `done` category (each one that is not is
           named, by `pm ready-for feature`); `reviewed:` points at a record
           that parses; no finding in it is `open`.

Any check false → `error:` lines, exit 1, no status written. `--force` writes
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
    """(--force, positionals, '' or the usage defect). `--skip`, `--reason`
    and `--status` are named because a consumer's script may still carry
    them."""
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
    """'' when `value` may be joined onto the roadmap directory, else why
    not."""
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
    """'' when `value` COULD be this operation's subject, else why not — a fact
    about the INPUT and nothing more. It counted segments (the nested id shape,
    the path spelled as an id) and so refused every id a migrated tree holds;
    story-or-feature is a question about the GRAIN, which `_wrong_kind` asks."""
    segments, noun, _shape = SUBJECT.get(operation, SUBJECT['release'])
    if segments == 1:
        return version_defect(value)
    if any(ch.isspace() for ch in value):
        return f'{_quote(value)} carries whitespace, which no {noun} has'
    if len(value) > MAX_SUBJECT:
        return (f'the {noun} is too long ({len(value)} characters; the limit '
                f'is {MAX_SUBJECT})')
    defect = model.id_defect(value)
    return f'{_quote(value)} is not a {noun}: {defect}' if defect else ''


def _wrong_kind(cfg, operation: str, subject: str) -> str:
    """'' when the tree's grain for `subject` is this belt's kind, else why not.
    The half of the old segment count that was real — `close story` given a
    FEATURE id answers the wrong question about a real file — asked off
    `kind:`, so it holds for any id shape."""
    want = {'story': 'story', 'feature': 'feature'}.get(operation)
    if want is None:
        return ''
    found = model.kind_of(cfg, subject)
    if not found or found == want:
        return ''
    return (f'{_quote(subject)} is a {found}, not a {want} — '
            f'`close {found} {subject}` is the belt that asks about one')


def grain_path(cfg, operation: str, subject: str) -> Path | None:
    """The file a close operation's subject names, or None, through `model`'s
    own resolvers."""
    if operation == 'story':
        return model.story_file(cfg, subject)
    return model.feature_file(cfg, subject)


def _config(root: Path | None) -> 'model.PmConfig':
    """The pm config, optionally re-rooted at a scratch tree."""
    cfg = model.load()
    return cfg if root is None else replace(cfg, root=Path(root))


def _writer(cfg: 'model.PmConfig', kind: str) -> Writer:
    """The one write, `pm <kind> <state> <id>` in process, so the CLI mints
    the `status` row and `check pm` reads what it wrote."""
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


def _recorder(mledger: Path, operation: str, subject: str) -> Recorder:
    """The `deviation` row a forced write leaves, with `ledger.deviation_row`'s
    keys: `step` names every false check, `reason` carries each sentence."""
    def record(false: Sequence[tuple[str, str]]) -> str:
        reason = '; '.join(f'{name}: {why}' for name, why in false)
        # One row is one line; U+2028/9 are left to `ledger.dumps`.
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
            ledger.append_to(mledger, row)
        except (ledger.LedgerError, OSError) as err:
            return str(err)
        return ''

    return record


def _no_ledger(nowhere: str) -> Recorder:
    """The recorder for a run whose milestone is not in the tree: it records
    nothing and says why, so a forced write can never print as though a row
    landed.

    Only a checks-only belt gets here — a belt that writes is still refused
    without the grain — but `run` may not assume that, and a silent recorder is
    rule 4's second sin in miniature.
    """
    def record(false: Sequence[tuple[str, str]]) -> str:
        return f'{nowhere} to hold a ledger row'

    return record


def _milestone_id(cfg, operation: str, subject: str) -> str:
    """The milestone this operation's subject belongs to — followed through the
    grain's BINDINGS for a close, and the subject itself for release/adopt.
    Splitting the id on `/` read the nested shape."""
    if operation in ('release', 'adopt'):
        return subject
    return model.milestone_of(cfg, subject) or subject


def _after(cfg: 'model.PmConfig', operation: str, subject: str) -> list[str]:
    """The `next:` lines from `steps.AFTER` with the tree's words filled in;
    a missing `branch:` renders as the placeholder."""
    from agentic_sdlc.repo.conveyor import steps as step_defs

    mid = _milestone_id(cfg, operation, subject)
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
    """`argv[0]` is the verb (`release` / `adopt` / `close`); the keyword
    arguments are injection seams for tests."""
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
    if not positional and operation != 'release':
        return _refuse(f'{spoken} needs a {shape} — the {noun} to close, e.g. '
                       f'`agentic-sdlc {spoken} '
                       f'{"0.2.0" if segments == 1 else shape}`')
    if len(positional) > 1:
        return _refuse(f'{spoken} takes exactly one {shape}; got '
                       f'{len(positional)} — one operation, one grain')
    # `release` alone resolves its subject from the plan, below, once the
    # config is loaded; every other operation is named on the command line.
    subject = positional[0] if positional else ''
    # A value that WAS given is graded, empty or not. Reading `release ''` as
    # "no argument" would resolve it from the plan and run the belt over a
    # version nobody named — the refusal matrix exists to stop exactly that.
    if positional:
        defect = subject_defect(operation, subject)
        if defect:
            return _refuse(f'{spoken}: {defect}')
    kind = WRITES[operation]
    if force and not kind:
        return _refuse(f'{spoken} writes nothing, so there is nothing to '
                       f'force — it is checks only')

    # Everything above refused without touching the filesystem.
    try:
        cfg = _config(root)
        names = tuple(steps) if steps is not None else step_names(operation)
        known = (dict(registry) if registry is not None
                 else registry_for(operation))
        # Read before the first check, so an undeclared `done` category fails
        # before anything runs.
        state = done_state(cfg, kind) if kind else ''
    except ConfigError as err:
        return _refuse(f'{spoken}: {err}')
    defect = plan_defect(known, names)
    if defect:
        return _refuse(f'{spoken}: {defect}')
    # The KIND needs the TREE, so it sits below the config load; the guard
    # above it stays a fact about the input.
    wrong = _wrong_kind(cfg, operation, subject) if subject else ''
    if wrong:
        return _refuse(f'{spoken}: {wrong}')

    if operation == 'release':
        # The plan already knows which version is current, so the human does
        # not retype it — and shipping OUT of order is what a belt should stop.
        current = model.current_release(cfg)
        if not subject:
            if current is None:
                return _refuse(
                    f'{spoken} needs a version, and the plan cannot supply one: '
                    f'{cfg.rel(model.releases_file(cfg))} declares no `order` '
                    f'(or every entry in it has shipped). Name the version, or '
                    f'schedule the milestone that carries it: `agentic-sdlc pm '
                    f'add {model.ROOT_ID} <milestone-id>`')
            subject = current
            defect = subject_defect(operation, subject)
            if defect:
                return _refuse(
                    f'{spoken}: the plan names {subject!r} as the current '
                    f'release, and {defect}')
            print(f'[{operation}] the plan names {subject} as the current '
                  f'release — '
                  f'{cfg.rel(model.releases_file(cfg))}, [pm] version_at = '
                  f'{cfg.version_at!r}')
        elif current is not None and subject != current:
            return _refuse(
                f'{spoken} {subject}: the current release is {current!r} — '
                f'shipping out of the order declared in '
                f'{cfg.rel(model.releases_file(cfg))} is refused, and nothing '
                f'was written. Re-sequence the plan with `agentic-sdlc pm add '
                f'{model.ROOT_ID} <milestone-id> --before <id>` if {subject} '
                f'really goes first')

    mid = _milestone_id(cfg, operation, subject)
    # The GRAIN, not a directory: what a belt needs is the milestone's document
    # (whose status it writes) and the ledger its rows land in, and both are
    # addressed by id now.
    mfile = model.milestone_file(cfg, mid)
    mledger = ledger.ledger_for(cfg, mid) if mfile is not None else None
    nowhere = f'no milestone {mid!r} in {cfg.rel(cfg.roadmap)}/'
    # A belt that WRITES needs the grain, and is refused BEFORE the first
    # check — which is also why nothing spawns here. The sentence names what
    # was looked for: "no milestone 'st-nobody-wrote-this'" about a STORY id
    # sent the reader hunting for a milestone nobody had named.
    if mfile is None and kind:
        missing = (nowhere if operation in ('release', 'adopt')
                   else f'no {operation} {subject!r} in '
                        f'{cfg.rel(cfg.roadmap)}/, or it is bound to no '
                        f'milestone')
        print(f'agentic-sdlc: {spoken} {subject}: {missing} — refused, and '
              f'nothing was written', file=sys.stderr)
        return 1
    if not kind:
        # Checks only (D12): the milestone is the LEDGER's home and nothing
        # else, so its absence is not an entry condition. WHERE the project
        # tracks the bump — a milestone, a feature, a story, nowhere at all —
        # is the project's business, the same way `[pm.states.*]` is. Every
        # check runs either way, and the run says which it found.
        print(f'[{operation}] {NOTHING_RECORDED} — '
              + (f'a row would land in {cfg.rel(mledger)}'
                 if mledger is not None
                 else f'there is {nowhere} to land one in; {ANYWHERE}'))

    ctx = Context(root=cfg.root, operation=operation, version=subject)
    result = run(known, names, ctx, force=force, state=state,
                 write=write if write is not None else _writer(cfg, kind),
                 record=(_recorder(mledger, operation, subject)
                         if mledger is not None else _no_ledger(nowhere)))
    for line in result.lines:
        print(line)
    if result.refused:
        # D11: one line on stderr, exit 2.
        return _refuse(f'{spoken}: {result.refused}')
    if result.exit_code == 0:
        for line in _after(cfg, operation, subject):
            print(line)
    return result.exit_code
