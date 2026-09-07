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

A check has THREE answers, not two (0.5.0/D5). `--skip <check> "<why>"` is the
third: the caller ANSWERED the question, so the check is not asked, the line
reads `skipped: <check> — "<why>"`, the close is a clean one, and a
`disposition` row records the judgement against the grain forever. Only a
check named in `[<op>] skippable` may be skipped, a skip with no reason is
refused — an unexplained skip is a deviation and `--force` is already its
verb — and stock declares nothing skippable, so stock behaviour is unchanged.
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
from agentic_sdlc.repo.conveyor import lessons
from agentic_sdlc.repo.pm import ledger, model, verdict

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

# --- the disposition a caller gives a check (0.5.0/D5) ------------------------
# The flag and how many words it takes: the CHECK and the WHY, in that order,
# positionally, so a reason opening with a dash is still a reason.
SKIP_FLAG = '--skip'
SKIP_ARITY = 2

# The row a skip mints. `pm/ledger.py` owns every other row grammar and these
# two belong beside `KIND_DEVIATION`; they are minted here because that module
# is another grain's to edit, and a row is read by its `kind`, so the move
# changes no byte on disk. `ts`, not the grain's `at`: every reader in this
# package — `ledger.read_rows`, `parse_ts`, `pm ledger show`'s sort — keys the
# stamp as `ts`, and a second spelling of the timestamp would file every
# disposition at the beginning of time.
#
# TWO ROW SHAPES CARRY THIS WORD, and a reader must branch. An ARRIVAL's
# disposition (0.5.0/D3) answers "what happened AT this state" and always
# carries `state`; a CHECK's disposition answers "what happened to this
# question" and always carries `check`. `check` is the discriminator, and
# whether the two should be one row is the milestone's to settle — not
# something either half may decide alone.
KIND_DISPOSITION = 'disposition'
DISPOSITION_KEYS = ('ts', 'kind', 'grain', 'operation', 'check', 'why')
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
    names: tuple[str, ...] = ()
    """The grains this answer NAMED, for the checks that name any — the
    blockers `pm ready-for` printed. A lesson recorded against one surfaces
    beside the check that named it, and every other check names none. Read off
    another verb's sentences (`lessons.blockers_named`), a few of which lead
    with a record path or a finding id instead; filtering those would mean
    deciding what an id LOOKS like, and matching is `==` at the reader, so one
    naming no lesson surfaces nothing."""

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
    """What one run did: `false` names every check not true, `skipped` every
    check the caller answered instead, `written` is the state set or '',
    `refused` is a mid-run `ConfigError`'s sentence (exit 2, D11)."""

    lines: tuple[str, ...]
    false: tuple[str, ...]
    written: str
    exit_code: int
    refused: str = ''
    skipped: tuple[str, ...] = ()


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


def _skippable(operation: str, names: Sequence[str],
               registry: Mapping[str, Check]) -> tuple[str, ...]:
    """The checks `[<operation>] skippable` declares; the import is local
    because `steps` imports from here."""
    from agentic_sdlc.repo.conveyor import steps as step_defs
    return step_defs.skippable_for(operation, tuple(names), dict(registry))


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
        *, force: bool = False, skips: Mapping[str, str] | None = None,
        state: str = '', write: Writer | None = None,
        record: Recorder | None = None,
        dispose: Recorder | None = None,
        surfacer: 'lessons.Surfacer | None' = None) -> Result:
    """Ask every check the caller did not answer, print each, then write once
    or not at all.

    `state` and `write` are handed in so decision and mechanism are two
    functions with one seam; `record` mints a forced write's `deviation` row
    and returns '' or why it could not; `dispose` mints one `disposition` row
    per skipped check the same way; `state == ''` writes nothing. `surfacer`
    reads recorded lessons back beside the verdicts and CANNOT change one — it
    contributes lines and nothing else.

    `skips` is check -> why, already graded against `[<op>] skippable` by the
    caller: a check in it is NOT asked, because the whole point is that the
    expensive question goes unasked once someone has answered it.
    """
    op = ctx.operation
    defect = plan_defect(registry, names)
    if defect:
        return Result((f'[{op}] error — {defect}',), (), '', 2, defect)
    answered = dict(skips or {})
    lines: list[str] = []
    false: list[tuple[str, str]] = []
    dispositioned: list[tuple[str, str]] = []
    if surfacer is not None:
        # The MOVE surface: this run is about to touch its subject grain.
        lines += surfacer.at_entry()
    for name in names:
        if name in answered:
            # A FIRST-CLASS answer, not a hole in the list: the check is named
            # on its own line with the judgement that stood in for it.
            why = answered[name]
            lines.append(f'[{op}] {verdict.SKIPPED}: {name} — "{why}"')
            dispositioned.append((name, why))
            if surfacer is not None:
                lines += surfacer.at_check(name)
            continue
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
        else:
            # A check that is not true and gave no reason has a defect, and the
            # defect is what gets reported.
            reason = answer.detail or (
                'the check answered no and gave no reason — a defect in the '
                'check, not a fact about the tree')
            word = (UNVERIFIABLE_WORD if answer.truth is Truth.UNVERIFIABLE
                    else 'error')
            lines.append(f'[{op}] {word}: {name}: {reason}')
            false.append((name, reason))
        if surfacer is not None:
            # The RULE surface, and the blockers this check named — after the
            # verdict line, because the verdict is the check's own business.
            lines += surfacer.at_check(name, answer.names)
    names_false = tuple(n for n, _ in false)
    names_skipped = tuple(n for n, _ in dispositioned)
    if false and not force:
        lines.append(f'[{op}] error — {len(false)} check(s) false; '
                     f'no status written')
        return Result(tuple(lines), names_false, '', 1,
                      skipped=names_skipped)
    if not state:
        # adopt: checks only. `--force` was refused before this point.
        # The census is what was ASKED and came out true; a skipped check
        # counted as true here would be rule 4's first sin with a number on it.
        census = f'{len(names) - len(dispositioned)} check(s) true'
        if dispositioned:
            census += f', {len(dispositioned)} skipped'
        lines.append(f'[{op}] ok — {census}; nothing to write')
        return Result(tuple(lines), names_false, '', 0,
                      skipped=names_skipped)
    if write is None:
        raise ValueError(f'{op} writes {state!r} and no writer was given')
    landed, said = write(ctx, state)
    if said:
        lines.append(f'[{op}] write: {said}')
    if not landed:
        lines.append(f'[{op}] error — the write was refused; no status written')
        return Result(tuple(lines), names_false, '', 1,
                      skipped=names_skipped)
    if false:
        lines.append(f'[{op}] forced — {ctx.version} → {state} over '
                     f'{len(false)} false check(s)')
        blocked = record(false) if record is not None else ''
        if blocked:
            lines.append(f'[{op}] WARNING — the deviation row naming the '
                         f'forced checks was not written: {blocked}')
    else:
        lines.append(f'[{op}] ok — {ctx.version} → {state}')
    if dispositioned:
        # After the write, for the same reason the deviation row is: a row for
        # a close that did not happen is rule 4's second sin with a timestamp.
        blocked = dispose(dispositioned) if dispose is not None else ''
        if blocked:
            lines.append(f'[{op}] WARNING — the disposition row(s) naming the '
                         f'skipped check(s) were not written: {blocked}')
    return Result(tuple(lines), names_false, state, 0, skipped=names_skipped)


# --- the verb -----------------------------------------------------------------

USAGE = """\
{synopsis}

Run every check in the {state} list, print each one, then write ONCE or not
at all: {writes}

  {subject}
              a grain id — the same grammar `pm` uses, segment for segment
{flags}
One line per check — `ok: <check> — <detail>`, `error: <check>: <what is
false>`, `unverifiable: <check>: <why>` (counts as false), or `skipped:
<check> — "<why>"` (you answered it) — then one of:

    [{state}] ok — <grain> → <state>
    [{state}] error — N check(s) false; no status written
    [{state}] forced — <grain> → <state> over N false check(s)

and, after a write, `next:` lines saying what is yours to do. Nothing else
is written, moved, bumped, retitled, pushed or tagged.

A `lesson` row recorded against this grain, or against a check's name, is
printed beside that verdict with its `source` path and emitted on the
`[emit]` sink. It is a record, never a gate: it changes no verdict and no
exit code.

Exit codes: 0 written (or nothing to write), 1 a check is false and nothing
was written, 2 the declaration could not be read.\
"""

CLOSE_USAGE = f"""\
agentic-sdlc {CLOSE_VERB} story   <story-id>     [{SKIP_FLAG} <check> "<why>"] [--force]
agentic-sdlc {CLOSE_VERB} feature <feature-id>   [{SKIP_FLAG} <check> "<why>"] [--force]

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
anyway and the ledger row names the false checks. `{SKIP_FLAG} <check> "<why>"`
is the other answer: the caller answered that check, so it is not asked, the
close is clean, and a `disposition` row carries the reason — for any check the
project named in `[story] skippable` / `[feature] skippable`, which stock
leaves empty. `agentic-sdlc {CLOSE_VERB} story --help` prints the full line
shapes. The belt above these two is `agentic-sdlc release <version>`.\
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


# The two flags a belt that WRITES takes, and what a checks-only belt says
# about them instead. Both are named either way, because a flag that is
# refused here and works one belt over is exactly the thing rule 11 says must
# not be left to be discovered by trying it.
WRITE_FLAGS = f"""\
  {SKIP_FLAG} <check> "<why>"
              you ANSWERED that check: it is not asked, the close is a clean
              one, and a `disposition` row keeps the reason against the grain.
              Only a check named in `[{{state}}] skippable` may be skipped
              (stock declares none), and a skip with no reason is refused —
              an unexplained skip is a deviation, and `--force` is its verb.
              Repeatable, once per check
  --force     write anyway; the milestone's ledger.jsonl gets one `deviation`
              row naming the checks that were false
"""

CHECKS_ONLY_FLAGS = f"""\
  {SKIP_FLAG} / --force
              neither is accepted here, and both are exit 2: this belt writes
              nothing, so there is no status to force and a skip would be a
              judgement with nowhere to be recorded. They are the close belts'
              flags — `close story`, `close feature`, `release`
"""


def _flags(operation: str) -> str:
    return WRITE_FLAGS if WRITES[operation] else CHECKS_ONLY_FLAGS


def _synopsis(operation: str) -> str:
    """The invocation lines: a belt that writes carries its two flags, and one
    that writes nothing is one line, because it takes neither."""
    spoken, subject = _spoken(operation), SUBJECT[operation][2]
    head = f'agentic-sdlc {spoken} {subject}'
    if not WRITES[operation]:
        return head
    return '\n'.join((head, f'{head} {SKIP_FLAG} <check> "<why>"',
                      f'{head} --force'))


def parse_flags(rest: Sequence[str]
                ) -> tuple[bool, dict[str, str], list[str], str]:
    """(--force, the checks `--skip` answered and why, positionals, '' or the
    usage defect).

    `--skip <check> "<why>"` takes its two words POSITIONALLY, so a reason
    opening with a dash is a reason and not a mistyped flag. WHICH checks may
    be skipped is not a question about argv — it is `[<op>] skippable`, graded
    by `skip_defect` once the config is loaded. `--reason` and `--status` are
    named because a consumer's script may still carry them.
    """
    force = False
    skips: dict[str, str] = {}
    positional: list[str] = []
    args = list(rest)
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == '--force':
            force = True
        elif arg == SKIP_FLAG:
            values = args[index:index + SKIP_ARITY]
            index += len(values)
            if len(values) < SKIP_ARITY:
                return False, {}, [], (
                    f'{SKIP_FLAG} takes a check and a reason — '
                    f'`{SKIP_FLAG} <check> "<why>"`. A skip with no reason is '
                    f'refused, because an unexplained skip IS a deviation and '
                    f'`--force` is already the verb for one')
            name, why = values
            defect = ledger.reason_defect(why)
            if defect:
                return False, {}, [], (
                    f'{SKIP_FLAG} {name}: {defect}. The reason is the whole '
                    f'difference between a judgement and a deviation, and the '
                    f'tree keeps it against the grain forever')
            if name in skips:
                return False, {}, [], (
                    f'{SKIP_FLAG} names {name!r} twice, with two reasons — '
                    f'one check, one answer')
            skips[name] = why
        elif arg in ('--reason', '--status'):
            return False, {}, [], (
                f'{arg} was removed in 0.2.0: a belt is its checks and then '
                f'one write. `--force` writes over false checks and the '
                f'ledger row names them; `pm ledger report` reads those rows')
        elif arg.startswith('-'):
            return False, {}, [], f'unknown option {arg!r}'
        else:
            positional.append(arg)
    return force, skips, positional, ''


def skip_defect(operation: str, asked: Mapping[str, str],
                declared: Sequence[str]) -> str:
    """'' when every `--skip` names a check this project DECLARED skippable,
    else why not — by name, which is the ship criterion.

    The tool has no opinion about which check is a judgement (rule 9); it has
    an opinion about whether the project said anything, and says so.
    """
    unknown = [name for name in asked if name not in declared]
    if not unknown:
        return ''
    listed = ', '.join(repr(name) for name in unknown)
    if declared:
        return (f'{listed} is not skippable — [{operation}] skippable declares '
                f'{", ".join(repr(name) for name in declared)}')
    return (f'{listed} is not skippable: this project declared no check '
            f'skippable, so nothing may be. Which checks are dispositionable '
            f'is yours to declare — `skippable = [{listed}]` under '
            f'[{operation}] in devkit.toml — or write anyway with --force, '
            f'which records a deviation naming every false check')


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
    from agentic_sdlc.repo.conveyor import steps as step_defs
    from agentic_sdlc.repo.pm import cli as pm_cli

    def write(ctx: Context, state: str) -> tuple[bool, str]:
        argv = [kind, state, step_defs.subject_grain(ctx)]
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


def _disposer(mledger: Path, operation: str, subject: str) -> Recorder:
    """The `disposition` rows a skipped check leaves — ONE PER CHECK, so
    "which closes skipped a review, and why" is a question the tree answers a
    row at a time and a milestone review can sweep. The deviation row lists
    every false check in one row because a forced write is one act; a
    disposition is one judgement about one question.
    """
    def dispose(skipped: Sequence[tuple[str, str]]) -> str:
        rows = []
        for check, why in skipped:
            # Graded at the flag too; a row minted by any other caller must
            # not be able to carry a reason that is not one.
            defect = ledger.reason_defect(why)
            if defect:
                return f'{check}: {defect}'
            rows.append({'ts': ledger.utc_now(), 'kind': KIND_DISPOSITION,
                         'grain': subject, 'operation': operation,
                         'check': check, 'why': why})
        for row in rows:
            try:
                ledger.append_to(mledger, row)
            except (ledger.LedgerError, OSError) as err:
                return str(err)
        return ''

    return dispose


def _no_ledger(nowhere: str) -> Recorder:
    """The recorder for a run whose milestone is not in the tree: it records
    nothing and says why, so neither a forced write nor a skipped check can
    ever print as though a row landed.

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
        # A VERSION; the milestone is whichever one CLAIMS it. `release` takes
        # the version a human says out loud, and the plan lists ids.
        return model.milestone_of_version(cfg, subject) or subject
    return model.milestone_of(cfg, subject) or subject


def _subject_grain(ctx: Context) -> str:
    """The grain this run is ABOUT, asked of the check lists so the lesson
    surface and the write cannot disagree about what is being touched."""
    from agentic_sdlc.repo.conveyor import steps as step_defs
    try:
        return step_defs.subject_grain(ctx)
    except Exception:  # noqa: BLE001 — a grain nobody could name is no grain
        return ctx.version


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
                           writes=_writes(operation),
                           synopsis=_synopsis(operation),
                           flags=_flags(operation).format(state=operation)))
        return 0

    force, skips, positional, flag_defect = parse_flags(rest)
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
    if skips and not kind:
        # A skip is a judgement the tree KEEPS, and this belt writes nothing —
        # not a status and not a row; it says so before its first check. A
        # `skipped:` line with no `disposition` behind it would be the record
        # this flag exists to make, missing.
        return _refuse(f'{spoken} writes nothing — not a status and not a row '
                       f'— so a skip has nowhere to be recorded; it is checks '
                       f'only. `{SKIP_FLAG}` is a close belt\'s flag: '
                       f'{CLOSE_VERB} story, {CLOSE_VERB} feature, release')

    # Everything above refused without touching the filesystem.
    try:
        cfg = _config(root)
        names = tuple(steps) if steps is not None else step_names(operation)
        known = (dict(registry) if registry is not None
                 else registry_for(operation))
        # Read before the first check, so an undeclared `done` category fails
        # before anything runs.
        state = done_state(cfg, kind) if kind else ''
        # The DECLARATION `--skip` is graded against; a malformed one is exit 2
        # here rather than a skip refused for a reason nobody can see.
        declared = _skippable(operation, names, known) if skips else ()
    except ConfigError as err:
        return _refuse(f'{spoken}: {err}')
    defect = plan_defect(known, names)
    if defect:
        return _refuse(f'{spoken}: {defect}')
    defect = skip_defect(operation, skips, declared)
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
    result = run(known, names, ctx, force=force, skips=skips, state=state,
                 write=write if write is not None else _writer(cfg, kind),
                 record=(_recorder(mledger, operation, subject)
                         if mledger is not None else _no_ledger(nowhere)),
                 dispose=(_disposer(mledger, operation, subject)
                          if mledger is not None else _no_ledger(nowhere)),
                 surfacer=lessons.surfacer_for(cfg, operation,
                                               _subject_grain(ctx)))
    for line in result.lines:
        print(line)
    if result.refused:
        # D11: one line on stderr, exit 2.
        return _refuse(f'{spoken}: {result.refused}')
    if result.exit_code == 0:
        for line in _after(cfg, operation, subject):
            print(line)
    return result.exit_code
