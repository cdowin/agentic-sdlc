"""driver.py — the conveyor: a step machine that refuses to advance.

`agentic-sdlc release <version>` and `agentic-sdlc adopt <version>` are the
same machine over different step lists. An operator runs it, gets interrupted,
clears context, and runs it again from a fresh session: the second run reports
the same position as the first, skips what is already true, and stops on the
same step for the same reason. Nothing is carried in anyone's head.

## The three kinds, and why the third is not a hack

Hard rule 1 is stdlib-only forever, so `pr-open`, `ci-green` and `merge` cannot
be PERFORMED here — there is no `gh`, no HTTP client, and there never will be.
They are judgement steps whose `check()` reads an artifact or runs a command
the PROJECT configures. That is only honest if the kind is a first-class shape
rather than an escape hatch bolted onto the automatic kind:

    AUTOMATIC   check: is the postcondition already true?
                do:    performs it
    GATE        check: run a command; exit 0 is true
                do:    NONE — a gate is not made true by running it again
    JUDGEMENT   check: read the ARTIFACT of a judgement — a verdict block, a
                       merge commit, a configured command's exit code
                do:    state precisely what a human must do, and return NOT-DONE

**A `JUDGEMENT` step with no artifact and no configured command is
UNVERIFIABLE, which is a REFUSAL to advance — never a pass.** That is the whole
difference between this machine and the prose it replaces. `repo/pm/verdict.py`
already rules this way for a review record whose block does not parse; this
inherits the ruling rather than inventing a softer one.

## `do()` never decides its own outcome

A step that reports DONE without its postcondition holding is rule 4's
cardinal sin in step-machine clothing. So the driver calls `do()`, DISCARDS its
return value as advisory text — printed as a `SAID` line, attributed to the
step, never as a verdict — and asks `check()` again. `verify()` below is that
second ask, and it is the only thing that can mark a step done. A step is DONE
when `check()` says so and at no other moment.

The same rule governs the run state: it is a cache of `check()` answers, never
the authority (see `state.py`). On resume, a step the file records as done is
re-`check()`ed before the driver moves past it; a disagreement is resolved in
favour of the tree, the file is corrected, and the line says so.

## What this module does NOT own

The 21 real release steps, the step list as config, `--skip`, and the generated
SDLC document are each their own story. This is the shape they plug into:
`registry_for()` and `step_names()` are the two seams, both empty here, and
`walk()` takes a registry and a list because who supplies them is not this
module's question.

Line shapes are contract (rule 6):

    [release:tree-clean] GATE ALREADY-TRUE — no modified paths
    [release:version-sync] AUTOMATIC SAID — bumped pyproject.toml
    [release:version-sync] AUTOMATIC DONE — pyproject.toml says 0.2.0
    [release:gate] GATE STOPPED — 12 failures
    [release:ci-green] JUDGEMENT UNVERIFIABLE — no artifact, no command
    [release] CORRECTED — the run state said 'gate' was done; the tree says: …
    [release] STOPPED — 'gate' (GATE) at step 10/21; what would make it true: …
    [release] PASS — 21/21 steps

Exit codes are contract (rule 6): 0 the run completed, 1 it stopped on a step
(a finding), 2 usage or config error.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Sequence

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo.conveyor import state as run_state
from agentic_sdlc.repo.pm import ledger, model

# The operations this driver walks. `adopt` has its own step list and its own
# state file; it needs no code of its own, which is the whole argument for one
# driver over two.
OPERATIONS = ('release', 'adopt')

# A milestone id is a path segment that gets joined onto `pm/roadmap/`, and the
# pm tracker already owns that grammar (`model.segment_is_literal`). This
# reuses it rather than inventing a second one: a second grammar is a second
# answer to "is this an id", and the two will disagree.
MAX_VERSION = 128
# How much of a hostile argument is quoted back. A 4 KB version string in an
# error message is a denial of service against the reader.
QUOTE_LIMIT = 40


class Truth(Enum):
    """What `check()` answered. Three values, and the third is why this is an
    enum rather than a bool: UNVERIFIABLE is not "no", it is "this cannot be
    decided", and collapsing it into either one is how a machine comes to
    print PASS over a question nobody answered."""

    TRUE = run_state.TRUE
    FALSE = run_state.FALSE
    UNVERIFIABLE = run_state.UNVERIFIABLE


@dataclass(frozen=True)
class Answer:
    """`check()`'s return: the truth, and the sentence a human needs.

    `detail` is not decoration. It is what the stop line prints under *what
    would make it true*, and a step that answers FALSE with an empty detail has
    told the operator that something is wrong and nothing about what.
    """

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


class StepKind(Enum):
    """CLOSED — the driver dispatches off this and off nothing else. A step
    whose behaviour needs a fourth kind is a fourth kind, not an `if name ==`."""

    AUTOMATIC = 'automatic'
    GATE = 'gate'
    JUDGEMENT = 'judgement'


# Which kinds have a `do()` at all, as a table rather than a branch. A GATE is
# not made true by running it again — its `check()` IS the command — so a gate
# carrying a `do` is refused at construction rather than quietly never called.
_MAY_PERFORM = {
    StepKind.AUTOMATIC: True,
    StepKind.GATE: False,
    StepKind.JUDGEMENT: True,
}
# Which kinds MUST have one. An AUTOMATIC step with no `do` can only ever
# report what it found, which is a GATE wearing the wrong label.
_MUST_PERFORM = {
    StepKind.AUTOMATIC: True,
    StepKind.GATE: False,
    StepKind.JUDGEMENT: False,
}


@dataclass(frozen=True)
class Context:
    """What every step is handed. Deliberately small: `root` is the checkout,
    `version` the milestone id, `config` the operation's `devkit.toml` table
    (empty here — story 02 fills it). A step that needs more asks the tree,
    because a step that needs state the driver carries is a step whose answer
    depends on the run rather than on the repo."""

    root: Path
    operation: str
    version: str
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Step:
    """One step. `check` is the postcondition; `do` performs it or states what
    a human must. Neither is allowed to be the thing that decides DONE — see
    `verify`."""

    name: str
    kind: StepKind
    check: Callable[[Context], Answer]
    do: Callable[[Context], str] | None = None

    def __post_init__(self) -> None:
        if self.do is not None and not _MAY_PERFORM[self.kind]:
            raise ValueError(
                f'step {self.name!r} is a {self.kind.name} and carries a do() — '
                f'a GATE is not made true by running it again; its check() IS '
                f'the command')
        if self.do is None and _MUST_PERFORM[self.kind]:
            raise ValueError(
                f'step {self.name!r} is {self.kind.name} and carries no do() — '
                f'a step that can only report what it found is a GATE')


@dataclass(frozen=True)
class Result:
    """What one `walk` did. `lines` is the transcript in order, `done` the
    steps `check()` proved true, `stopped` the one it stopped on."""

    lines: tuple[str, ...]
    done: tuple[str, ...]
    stopped: str | None
    exit_code: int


def verify(step: Step, ctx: Context) -> Answer:
    """The postcondition, re-asked after `do()` ran.

    This function is the whole feature. `do()`'s return value never reaches it,
    so a `do()` that reports success while `check()` still answers no leaves
    the machine exactly where it was. Without this second ask the driver would
    be reporting a step's own claim about itself, which is the one source this
    package's SDLC refuses to trust.
    """
    return step.check(ctx)


# --- the registry and the list ------------------------------------------------
# Both seams, both empty. Story 03 fills the registry with the real steps;
# story 02 reads the ordered list from `[<operation>] steps` in devkit.toml.
# They are functions rather than constants so neither story has to change this
# module's shape to fill them.
REGISTRY: dict[str, Step] = {}


def registry_for(operation: str) -> dict[str, Step]:
    """The steps this package SHIPS for `operation`, by name.

    Delegates to `steps.py`, which owns the definitions. The import is LOCAL
    because `steps` imports the shapes above from here — one direction at
    module level, the other at call time, so neither file has to know which
    one a caller reached first.

    `REGISTRY` remains the injection seam it was: anything in it wins, so a
    test (or a language kit) can add a step without editing the shipped list.
    """
    from agentic_sdlc.repo.conveyor import steps as step_defs
    known = step_defs.registry_for(operation)
    known.update(REGISTRY)
    return known


def step_names(operation: str) -> tuple[str, ...]:
    """The ordered step list for `operation`, from `[<operation>] steps`.

    A project that declares nothing gets the shipped default, byte-identically
    (rule 5). A project that misspells a step name is told so and exits 2 — it
    never gets a quietly shorter release, because the step that vanishes is
    `review-landed`. An empty list is REFUSED by `walk`, never walked.
    """
    from agentic_sdlc.repo.conveyor import steps as step_defs
    known = registry_for(operation)
    names = step_defs.steps_for(operation, known)
    # Every other `[<operation>]` key is read HERE too, so a bad one is exit 2
    # before the first step rather than halfway through a release.
    step_defs.validate_config(operation, names, known)
    return names


def plan_defect(registry: Mapping[str, Step], names: Sequence[str]) -> str:
    """'' when this list can be walked whole, else why it cannot.

    Rule 4: a machine that walked nothing must say so, loudly, rather than
    print PASS over a census of zero. And a list naming a step nothing
    registers is refused BEFORE the first step runs — half a release performed
    against a plan that was never going to finish is worse than none.
    """
    if not names:
        return ('no steps to walk — the list is empty, and a run that walked '
                'nothing must not report PASS')
    missing = [n for n in names if n not in registry]
    if missing:
        return ('no step is registered for '
                + ', '.join(repr(m) for m in missing))
    return ''


def walk(registry: Mapping[str, Step], names: Sequence[str], ctx: Context,
         run: 'run_state.RunState',
         skips: Mapping[str, str] | None = None,
         record_skip: Callable[[str, str], bool] | None = None) -> Result:
    """Walk `names` in order, stopping at the first step that is not true.

    `run` is READ for what the last run answered and WRITTEN with what this one
    answers — it is never consulted to decide whether to skip a step. Every
    step is asked, every time; that is what makes a deleted state file cost
    nothing and a stale one harmless.

    `skips` maps a step name to the operator's REASON. A skipped step is not
    checked and not recorded in the run state — it has no `check()` answer to
    cache — and `record_skip` is what makes it durable: it returns True when it
    wrote a new ledger row and False when the row was already there, which is
    what makes a re-run with the same flags idempotent.
    """
    defect = plan_defect(registry, names)
    if defect:
        return Result((f'[{ctx.operation}] REFUSED — {defect}',), (), None, 2)

    skipped_reasons = dict(skips or {})
    lines = [f'[{ctx.operation}] CORRECTED — {c}' for c in run.corrections]
    done: list[str] = []
    skipped: list[str] = []
    total = len(names)
    for index, name in enumerate(names, start=1):
        step = registry[name]
        if name in skipped_reasons:
            reason = skipped_reasons[name]
            fresh = True if record_skip is None else record_skip(name, reason)
            verdict = 'SKIPPED' if fresh else 'ALREADY-SKIPPED'
            lines.append(_line(ctx, step, verdict, reason))
            skipped.append(name)
            continue
        remembered = run.answer_for(name)
        answer = step.check(ctx)
        if remembered == run_state.TRUE and not answer.is_true:
            # The tree wins. Always. The file is a cache, and a cache that
            # outranked the thing it caches would be the lie this feature ends.
            lines.append(
                f'[{ctx.operation}] CORRECTED — the run state said {name!r} '
                f'was done; the tree says: {answer.detail}')
        if answer.is_true:
            run.record(name, run_state.TRUE, answer.detail)
            lines.append(_line(ctx, step, 'ALREADY-TRUE', answer.detail))
            done.append(name)
            continue
        if step.do is not None:
            # The return value is ADVISORY TEXT and nothing else. It is printed
            # attributed to the step ("SAID"), never as a verdict, and the
            # answer below comes from `verify`, not from here.
            said = step.do(ctx)
            if said:
                lines.append(_line(ctx, step, 'SAID', str(said)))
            answer = verify(step, ctx)
        run.record(name, answer.truth.value, answer.detail)
        if answer.is_true:
            lines.append(_line(ctx, step, 'DONE', answer.detail))
            done.append(name)
            continue
        verdict = ('UNVERIFIABLE' if answer.truth is Truth.UNVERIFIABLE
                   else 'STOPPED')
        lines.append(_line(ctx, step, verdict, answer.detail))
        lines.append(
            f'[{ctx.operation}] STOPPED — {name!r} ({step.kind.name}) at step '
            f'{index}/{total}; what would make it true: {answer.detail}')
        return Result(tuple(lines), tuple(done), name, 1)
    if skipped:
        # Named, in the transcript, at the end — a run that deviated must not
        # read like one that did not.
        lines.append(f'[{ctx.operation}] DEVIATED — {len(skipped)} of {total} '
                     f'steps skipped: {", ".join(skipped)}')
    if skipped and len(skipped) == total:
        # Risk 3, arriving: a conveyor that is always skipped is worse than
        # none, because it LOOKS like control.
        lines.append(
            f'[{ctx.operation}] WARNING — every step in the list ({total}) was '
            f'skipped; a conveyor nothing walks is not control, it is a '
            f'record of a release nobody ran')
    lines.append(f'[{ctx.operation}] PASS — {len(done)}/{total} steps')
    return Result(tuple(lines), tuple(done), None, 0)


def _line(ctx: Context, step: Step, verdict: str, detail: str) -> str:
    tail = f' — {detail}' if detail else ''
    return f'[{ctx.operation}:{step.name}] {step.kind.name} {verdict}{tail}'


# --- the verb -----------------------------------------------------------------

USAGE = """\
agentic-sdlc {op} <version> [--skip <step> --reason "<why>"]...
agentic-sdlc {op} <version> --status

Walk the {op} step list for milestone <version>, stopping at the first step
whose postcondition is not true. Resumable: the position lives in
.agentic-sdlc/run/{op}.json (gitignored), and every step is re-checked against
the tree on every run, so deleting that file costs nothing.

  <version>   a milestone id, e.g. 0.2.0 — the same grammar `pm` uses
  --skip      do not walk this step. Every --skip needs its own --reason
              immediately after it, and the pair is written to the milestone's
              ledger.jsonl as a `deviation` row. Deviation stays possible;
              INVISIBLE deviation does not.
  --reason    why this step is being skipped. Not optional, not empty, not
              punctuation, one line, at most 1024 characters.
  --status    print this milestone's recorded deviations and the cached
              position, and walk nothing.

Exit codes: 0 the run completed, 1 it stopped on a step, 2 usage or config.\
"""


def parse_flags(rest: Sequence[str]) -> tuple[list[tuple[str, str]], bool,
                                              list[str], str]:
    """(skip/reason pairs, --status, positionals, '' or the usage defect).

    `--skip` and `--reason` are parsed as an ORDERED PAIR rather than as two
    independent lists, so `--reason` with no `--skip` is a defect the grammar
    catches rather than a value that silently attaches to nothing. Each value
    is taken positionally, so a reason beginning with `-` is a reason.
    """
    pairs: list[tuple[str, str]] = []
    status = False
    positional: list[str] = []
    pending: str | None = None
    index = 0
    args = list(rest)
    while index < len(args):
        arg = args[index]
        if arg == '--status':
            status = True
        elif arg == '--skip':
            if pending is not None:
                return [], False, [], (
                    f'--skip {pending!r} has no --reason — a skip without a '
                    f'reason is the silence the ledger row exists to end')
            if index + 1 >= len(args):
                return [], False, [], '--skip needs a step name'
            index += 1
            pending = args[index]
        elif arg == '--reason':
            if pending is None:
                return [], False, [], (
                    '--reason with no --skip before it is a reason for '
                    'nothing')
            if index + 1 >= len(args):
                return [], False, [], '--reason needs a value'
            index += 1
            pairs.append((pending, args[index]))
            pending = None
        elif arg.startswith('-'):
            return [], False, [], f'unknown option {arg!r}'
        else:
            positional.append(arg)
        index += 1
    if pending is not None:
        return [], False, [], (
            f'--skip {pending!r} has no --reason — a skip without a reason is '
            f'the silence the ledger row exists to end')
    if status and pairs:
        return [], False, [], (
            '--status walks nothing, so it cannot be combined with --skip')
    return pairs, status, positional, ''


def _refuse(message: str) -> int:
    print(f'agentic-sdlc: {message}', file=sys.stderr)
    return 2


def _quote(value: str) -> str:
    shown = value if len(value) <= QUOTE_LIMIT else value[:QUOTE_LIMIT] + '…'
    return repr(shown)


def version_defect(value: str) -> str:
    """'' when `value` may be joined onto the roadmap directory, else why not.

    The grammar is `model.segment_is_literal` — the pm tracker's, unchanged —
    plus the two things a path segment check has no opinion about: length, and
    whitespace. `'   '` is a literal segment by that rule and is nobody's
    milestone id.
    """
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


def _config(root: Path | None) -> 'model.PmConfig':
    """The pm config, optionally re-rooted at a scratch tree.

    One config object, so `[pm] roadmap_dir` is honoured here exactly as the
    tracker honours it — the alternative is this module hard-coding
    `pm/roadmap`, which is a second answer to where the roadmap lives.
    """
    cfg = model.load()
    return cfg if root is None else replace(cfg, root=Path(root))


def main(argv: Sequence[str], *, root: Path | None = None,
         registry: Mapping[str, Step] | None = None,
         steps: Sequence[str] | None = None) -> int:
    """`argv[0]` is the OPERATION (`release` / `adopt`); the rest is its own.

    `cli.py` routes `agentic-sdlc release 0.2.0` to
    `conveyor.main(['release', '0.2.0'])` and `agentic-sdlc adopt …` the same
    way — one entry point, because the two verbs are one machine over two step
    lists and a second `main` would be a second place for the contract to live.

    `root`, `registry` and `steps` are injection seams for tests and for the
    stories that fill the registry and the list; every one of them defaults to
    the real thing.
    """
    args = list(argv)
    if not args:
        return _refuse(
            f'an operation is required (expected: {", ".join(OPERATIONS)})')
    operation, rest = args[0], args[1:]
    if operation in ('-h', '--help', 'help'):
        print(__doc__.strip())
        return 0
    if operation not in OPERATIONS:
        return _refuse(f'unknown operation {operation!r} '
                       f'(expected: {", ".join(OPERATIONS)})')
    if any(a in ('-h', '--help', 'help') for a in rest):
        print(USAGE.format(op=operation))
        return 0

    # An argument a verb does not understand is a usage error, not a
    # suggestion — the `_run_check` precedent.
    pairs, status, positional, flag_defect = parse_flags(rest)
    if flag_defect:
        return _refuse(f'{operation}: {flag_defect}')
    if not positional:
        return _refuse(f'{operation} needs a <version> — the milestone id to '
                       f'{operation}, e.g. `agentic-sdlc {operation} 0.2.0`')
    if len(positional) > 1:
        return _refuse(f'{operation} takes exactly one <version>; got '
                       f'{len(positional)} — one operation, one milestone')
    version = positional[0]
    defect = version_defect(version)
    if defect:
        return _refuse(f'{operation}: {defect}')

    # Everything above refused without touching the filesystem. From here the
    # tree is read — and still nothing is WRITTEN until a step has run.
    cfg = _config(root)
    mdir = model.milestone_dir(cfg, version)
    if mdir is None:
        # BEFORE any ledger row: the milestone directory is where the row goes,
        # so it has to resolve first. A `--skip` against an unresolvable
        # version writes nothing at all.
        print(f'agentic-sdlc: {operation} {version}: no milestone directory '
              f'{cfg.rel(cfg.roadmap)}/{version}-* — refused, and nothing was '
              f'created', file=sys.stderr)
        return 1

    try:
        names = tuple(steps) if steps is not None else step_names(operation)
        known = (dict(registry) if registry is not None
                 else registry_for(operation))
    except ConfigError as err:
        # A typo in the step list is a CONFIG mistake, not a finding: exit 2,
        # naming the key and the offending value, with no step run.
        return _refuse(f'{operation}: {err}')
    defect = plan_defect(known, names)
    if defect:
        return _refuse(f'{operation}: {defect}')

    if status:
        return print_status(cfg, mdir, operation, version, names)

    skips, skip_defect = _skip_plan(pairs, names)
    if skip_defect:
        return _refuse(f'{operation}: {skip_defect}')
    if skips:
        blocked = _ledger_defect(mdir)
        if blocked:
            return _refuse(f'{operation}: {blocked} — nothing was skipped, '
                           f'because the RECORD is the point')

    # The state destination is decided BEFORE the first step. A run that
    # performs half a release and then cannot record where it got to has broken
    # the one promise this machine exists to keep.
    blocked = run_state.destination_defect(cfg.root, operation)
    if blocked:
        return _refuse(f'{operation}: cannot write the run state: {blocked}')
    try:
        run = run_state.load(cfg.root, operation, version, names)
    except run_state.StateDefect as err:
        return _refuse(str(err))

    # A skip cannot un-do a postcondition that already holds. Asked of the run
    # state rather than of the tree because the sentence is about THIS run.
    already = [name for name in skips
               if run.answer_for(name) == run_state.TRUE]
    if already:
        when = ', '.join(f'{n} (completed {run.records[n].at})'
                         for n in already)
        return _refuse(f'{operation}: --skip names {when}; a skip cannot '
                       f'un-do a postcondition that holds')

    ctx = Context(root=cfg.root, operation=operation, version=version)
    recorder = _skip_recorder(mdir, operation, version)
    result = walk(known, names, ctx, run, skips=skips, record_skip=recorder)
    for line in result.lines:
        print(line)
    try:
        run_state.save(cfg.root, run)
    except run_state.StateDefect as err:
        return _refuse(str(err))
    return result.exit_code


# --- the skip, and its ledger row ---------------------------------------------
def _skip_plan(pairs: Sequence[tuple[str, str]],
               names: Sequence[str]) -> tuple[dict[str, str], str]:
    """({step: reason}, '' or why the request is refused).

    Every refusal here is exit 2 and NO ROW IS WRITTEN. A `--skip` naming a
    step that is not in the configured list is the same defect class as a
    misspelled step in the list itself: the operator believes something about
    this release that is not true.
    """
    plan: dict[str, str] = {}
    for step, reason in pairs:
        if step in plan:
            return {}, (f'--skip names {step!r} twice — one decision per '
                        f'step')
        if step not in names:
            return {}, (f'--skip names {step!r}, which is not in this '
                        f'{"list" if names else "empty list"}: '
                        f'{", ".join(names)}')
        defect = ledger.reason_defect(reason)
        if defect:
            return {}, f'--reason for {step!r}: {defect}'
        plan[step] = reason
    return plan, ''


def _ledger_defect(mdir: Path) -> str:
    """'' when a deviation row can be appended here, else why not."""
    path = ledger.ledger_path(mdir)
    if path.is_dir():
        return f'{path} is a directory, not a ledger'
    probe = path if path.exists() else mdir
    if not os.access(probe, os.W_OK):
        return f'{probe} is not writable'
    return ''


def _recorded_skips(mdir: Path, operation: str,
                    version: str) -> set[str]:
    rows = ledger.read_rows(ledger.ledger_path(mdir))
    return {row.data.get('step') for row in rows
            if row.data.get('kind') == ledger.KIND_DEVIATION
            and row.data.get('operation') == operation
            and row.data.get('grain') == version
            and isinstance(row.data.get('step'), str)}


def _skip_recorder(mdir: Path, operation: str, version: str):
    """The callback `walk` uses. True when a NEW row landed, False when the
    deviation was already recorded — which is what makes a re-run with the
    same flags idempotent rather than a second row saying the same thing."""
    def record(step: str, reason: str) -> bool:
        if step in _recorded_skips(mdir, operation, version):
            return False
        ledger.append_row(mdir, ledger.deviation_row(version, operation, step,
                                                     reason))
        return True

    return record


def print_status(cfg, mdir: Path, operation: str, version: str,
                 names: Sequence[str]) -> int:
    """What the ledger and the run cache say about this milestone's run.

    So a close report QUOTES the machine rather than the operator's memory.
    The two halves are labelled apart on purpose: the ledger rows are the
    durable record, and the cached positions are a cache — a reader who
    confuses them is back to trusting a scoreboard.
    """
    try:
        rows = [row for row in ledger.read_rows(ledger.ledger_path(mdir))
                if row.data.get('kind') == ledger.KIND_DEVIATION
                and row.data.get('grain') == version]
    except ledger.LedgerError as err:
        return _refuse(f'{operation}: {err}')
    print(f'[{operation}:{version}] {len(names)} step(s) in the list')
    if rows:
        for row in rows:
            print(f'[{operation}:{row.data.get("step")}] '
                  f'{str(row.data.get("outcome", "")).upper()} — '
                  f'{row.data.get("reason", "")} ({row.data.get("ts", "")})')
    else:
        print(f'[{operation}] no deviation is recorded in '
              f'{cfg.rel(ledger.ledger_path(mdir))}')
    try:
        run = run_state.load(cfg.root, operation, version, names)
    except run_state.StateDefect as err:
        print(f'[{operation}] the run cache is unreadable: {err}')
        return 0
    if not run.records:
        print(f'[{operation}] the run cache holds no position — nothing has '
              f'been walked, or the file was deleted (which costs nothing)')
        return 0
    for name in names:
        got = run.records.get(name)
        if got is not None:
            print(f'[{operation}:{name}] cached {got.answer.upper()} '
                  f'({got.at}) — a cache, never the authority')
    return 0
