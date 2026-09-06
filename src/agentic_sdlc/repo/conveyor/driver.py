"""driver.py — the conveyor: a step machine that walks, reports and finishes.

`agentic-sdlc release <version>`, `agentic-sdlc adopt <version>`,
`agentic-sdlc close story <id>` and `agentic-sdlc close feature <id>` are the
same machine over four step lists. An operator runs it, gets interrupted,
clears context, and runs it again from a fresh session: the second run reports
the same position as the first, skips what is already true, and reports the
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
UNVERIFIABLE — never a pass.** `repo/pm/verdict.py` already rules this way for
a review record whose block does not parse; this inherits the ruling rather
than inventing a softer one. It no longer REFUSES to advance (D8, below); it
is counted in its own column and the run exits 1.

## Nothing halts, and that is the whole of D8

`.claude/rules/pm-execution.md` shipped before any of this:

> *"`pm feature reviewing` and `pm milestone done` REPORT, never refuse.
> Stories not at `reviewing`, features not done — the verb names them and does
> what it was asked."*

The PM CLI always worked that way and this driver was built to refuse, which
is the rule broken by the module that most needed it. Chris, 2026-09-05:

> *"I don't understand tree vs input. Everything is just a check. `release`
> should release on a red tree if I want (we mostly wouldn't but why stop
> someone?)"*

There is exactly one exit 2 and it is not a step's answer — it is this module
failing to READ its own declaration (`plan_defect`, `subject_defect`,
`validate_config`), before the walk, with nothing walked. Everything during
the walk is a check, and a check reports. The engine cannot know whether a
not-true step is wrong: descoped? a hotfix? deliberate? **The caller knows and
the engine does not**, and a machine that blocks on a question it cannot ask
is asserting an answer.

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

The 21 real release steps, the step list as config, and the generated
SDLC document are each their own story. This is the shape they plug into:
`registry_for()` and `step_names()` are the two seams, both empty here, and
`walk()` takes a registry and a list because who supplies them is not this
module's question.

## The four operations, and why the inner two changed nothing

`story` and `feature` (SDLC.md §0) are the levels that run CONSTANTLY, and
they arrived on this driver as two more rows in a table: same three kinds, same
`do()`-never-decides rule, same run-state cache, same `deviation` row.
The only thing they needed was a SUBJECT of more than one path segment
(`subject_defect`) and the ruling that a cached position belonging to a
different story is stale rather than broken (`_load_run`). A belt whose
addition had required a second machine would have been the argument against
having a machine.

Line shapes are contract (rule 6):

    [release:tree-clean] GATE ALREADY-TRUE — no modified paths
    [release:version-sync] AUTOMATIC SAID — bumped pyproject.toml
    [release:version-sync] AUTOMATIC DONE — pyproject.toml says 0.2.0
    [release:gate] GATE NOT-TRUE — 12 failures
    [release:ci-green] JUDGEMENT UNVERIFIABLE — no artifact, no command
    [release] CORRECTED — the run state said 'gate' was done; the tree says: …
    [release] step 10/21 'gate' (GATE) is not true; what would make it true: …
    [release] 19/21 true · 1 not true: gate · 1 unverifiable: ci-green
    [release] PASS — 21/21 steps

Exit codes are contract (rule 6): 0 every postcondition holds, 1 one or more
do not (a finding — the walk still finished, D8), 2 usage or config error.
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

# The operations this driver walks. Each has its own step list and its own
# state file; none needs code of its own, which is the whole argument for one
# driver over four.
#
# `story` and `feature` are the two INNER levels (SDLC.md §0). They arrived
# after `release` and `adopt` and changed nothing about the machine: same three
# kinds, same `do()`-never-decides rule, same run-state cache.
# What they changed is the SUBJECT — a milestone id is one path segment and a
# story id is three — which is why `subject_defect` exists below and
# `version_defect` is what it delegates to for the outer two.
CLOSE_VERB = 'close'
CLOSE_OPERATIONS = ('story', 'feature')
OPERATIONS = ('release', 'adopt', *CLOSE_OPERATIONS)

# The VERBS `cli.py` routes, which is not the same list. `close story` and
# `close feature` are one verb over two operations — `agentic-sdlc story` would
# be a second spelling of `pm story` and mean something else entirely, so the
# grain is a subcommand of `close` rather than a top-level verb of its own.
VERBS = ('release', 'adopt', CLOSE_VERB)

# How many `/`-separated segments each operation's subject carries, and what to
# call it in a refusal. One table rather than a branch, for the same reason
# `DEFAULT_STEPS` is one: an operation added with no row here is refused by
# name instead of silently taking the milestone grammar.
SUBJECT = {
    'release': (1, 'version', '<version>'),
    'adopt': (1, 'version', '<version>'),
    'story': (3, 'story id', '<milestone>/<feature>/<story>'),
    'feature': (2, 'feature id', '<milestone>/<feature>'),
}

# A milestone id is a path segment that gets joined onto `pm/roadmap/`, and the
# pm tracker already owns that grammar (`model.segment_is_literal`). This
# reuses it rather than inventing a second one: a second grammar is a second
# answer to "is this an id", and the two will disagree.
MAX_VERSION = 128
# The same bound, per SEGMENT, for the multi-segment ids the close operations
# take: three segments of a legal length is a legal id, and a cap on the whole
# string would refuse a perfectly ordinary story for the sum of its parts.
MAX_SUBJECT = MAX_VERSION * len(SUBJECT['story'][2].split('/'))
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
    """What one `walk` did — a SCOREBOARD, because the walk always finishes.

    D8, 2026-09-05. This used to carry `stopped: str | None`, the one step the
    walk halted on, because there was only ever one: `_walk` returned at the
    first step whose postcondition was not true. Chris: *"Everything is just a
    check. `release` should release on a red tree if I want — why stop
    someone?"* So there is no first one any more. Every step is asked, every
    answer is recorded and printed, and what comes back is what is true and
    what is not.

    `not_true` and `unverifiable` are kept APART for the reason `Truth` is an
    enum rather than a bool: UNVERIFIABLE is not "no", it is "this cannot be
    decided", and a scoreboard that added them together would be printing one
    number over two facts.
    """

    lines: tuple[str, ...]
    done: tuple[str, ...]
    not_true: tuple[str, ...]
    unverifiable: tuple[str, ...]
    exit_code: int

    @property
    def stopped(self) -> str | None:
        """The first step that is not true, or None.

        Kept as a READ-ONLY view for callers that ask "did anything go wrong"
        — it is no longer a control-flow fact, and nothing in this module
        branches on it.
        """
        return self.not_true[0] if self.not_true else None


def ask(step: Step, ctx: Context) -> Answer:
    """`step.check(ctx)`, with an unexpected exception turned into an ANSWER.

    New with D8, and it is not defensive padding — it is the consequence of no
    longer halting. While the walk stopped at the first not-true step, a step
    whose `check()` raised was usually never reached: the run had already
    returned. Now every step is asked on every run, so a latent crash in step
    19 surfaces on a tree where step 3 is red, and an uncaught exception is
    exit 1 with a traceback — which hard rule 6 gives to FINDINGS, and which a
    consumer's CI reads as drift. R4 is exactly that shape:
    `_status_at_or_past` raising `ValueError: tuple.index(x): x not in tuple`
    on a legal per-project `[pm] milestone_states`.

    UNVERIFIABLE rather than FALSE, deliberately. A step that crashed did not
    answer "no" — it failed to answer at all, and `Truth`'s three values exist
    precisely so that "this cannot be decided" is not collapsed into either
    one.

    `ConfigError` is RE-RAISED and that is the D8 line: a malformed
    declaration is the reader failing, not a check reporting, and it belongs
    to exit 2 before the walk rather than to a row on the scoreboard.
    """
    try:
        return step.check(ctx)
    except ConfigError:
        raise
    except Exception as err:  # noqa: BLE001 — an answer, not a swallow
        return Answer.unverifiable(
            f'{type(err).__name__} while checking: {err}')


def perform(step: Step, ctx: Context) -> str:
    """`step.do(ctx)`, with an unexpected exception turned into ADVISORY TEXT.

    Same reasoning as `ask`, on the other callable. A `do()` that raises is
    reported on the transcript attributed to the step and the postcondition is
    then re-asked — which answers the only question that matters, because
    `do()`'s word for itself was never trusted (see `verify`).
    """
    try:
        return str(step.do(ctx) or '') if step.do is not None else ''
    except ConfigError:
        raise
    except Exception as err:  # noqa: BLE001 — reported, then re-checked
        return f'{type(err).__name__} while performing: {err}'


def verify(step: Step, ctx: Context) -> Answer:
    """The postcondition, re-asked after `do()` ran.

    This function is the whole feature. `do()`'s return value never reaches it,
    so a `do()` that reports success while `check()` still answers no leaves
    the machine exactly where it was. Without this second ask the driver would
    be reporting a step's own claim about itself, which is the one source this
    package's SDLC refuses to trust.
    """
    return ask(step, ctx)


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
         record: Callable[[str, str, str], bool] | None = None) -> Result:
    """Walk `names` in order to the END, and return what is true and what is not.

    `run` is READ for what the last run answered and WRITTEN with what this one
    answers — it is never consulted to decide whether to ask a step. Every step
    is asked, every time; that is what makes a deleted state file cost nothing
    and a stale one harmless.

    `record` is the DURABLE half. `--skip <step> --reason "<why>"` used to be
    how a deviation reached the ledger, and D8 removed the flag: it existed to
    escape a refusal, and with nothing to escape it is ceremony. **The ledger
    row was always the honest part**, so it is now written by the machine
    rather than typed by the operator — one row per step that is not true,
    carrying the step's own `Answer.detail` as the reason. The callback returns
    True when a new row landed and False when the row was already there, which
    is what makes a re-run idempotent rather than a second row saying the same
    thing.

    That is strictly better than the flag was. A skip reason was the operator's
    account of why they were stepping around the machine; this is the machine's
    account of what it found, and nobody has to remember to type it.
    """
    defect = plan_defect(registry, names)
    if defect:
        # THE ONE EXIT 2, and it is not a step's answer — it is this module
        # failing to READ its own declaration. D8's whole distinction: before
        # the walk, a malformed plan means nothing walks; during the walk,
        # every step is a check and every check reports.
        return Result((f'[{ctx.operation}] REFUSED — {defect}',), (), (), (), 2)

    lines = [f'[{ctx.operation}] CORRECTED — {c}' for c in run.corrections]
    done: list[str] = []
    not_true: list[str] = []
    unverifiable: list[str] = []
    total = len(names)
    for index, name in enumerate(names, start=1):
        step = registry[name]
        remembered = run.answer_for(name)
        answer = ask(step, ctx)
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
            said = perform(step, ctx)
            if said:
                lines.append(_line(ctx, step, 'SAID', said))
            answer = verify(step, ctx)
        run.record(name, answer.truth.value, answer.detail)
        if answer.is_true:
            lines.append(_line(ctx, step, 'DONE', answer.detail))
            done.append(name)
            continue
        # D8: RECORD IT AND KEEP WALKING. This used to return here, which made
        # the seven steps after `findings-resolved` — `milestone-done`,
        # `push-branch`, `pr-open`, `ci-green`, `merge`, `tag`,
        # `prove-artifact` — unreachable on any resumed run, and they are
        # exactly the ones a release most needs to resume into because
        # `pr-open` -> `ci-green` -> `merge` spans a PR review and a CI wait
        # (finding R1). The engine cannot know whether a not-true step is
        # wrong. Descoped? A hotfix? Deliberate? The caller knows and the
        # engine does not, and a machine that blocks on a question it cannot
        # ask is asserting an answer.
        outcome = ('unverifiable' if answer.truth is Truth.UNVERIFIABLE
                   else 'not-true')
        if answer.truth is Truth.UNVERIFIABLE:
            lines.append(_line(ctx, step, 'UNVERIFIABLE', answer.detail))
            unverifiable.append(name)
        else:
            lines.append(_line(ctx, step, 'NOT-TRUE', answer.detail))
            not_true.append(name)
        # The durable row. The run cache is gitignored and disposable; THIS is
        # the half nobody can reconstruct from the tree afterwards, which is
        # the whole argument the `deviation` row was minted under.
        if record is not None and answer.detail:
            record(name, outcome, answer.detail)
        lines.append(
            f'[{ctx.operation}] step {index}/{total} {name!r} '
            f'({step.kind.name}) is not true; what would make it true: '
            f'{answer.detail}')
    # THE SCOREBOARD, and criterion 2 says it has to be good: a 21-step run
    # now prints 21 lines where it used to print five, so this line is what a
    # caller reads. A warning nobody reads is worse than a refusal (risk 1),
    # and the mitigation is that the counts and the NAMES are both here.
    if not not_true and not unverifiable:
        lines.append(f'[{ctx.operation}] PASS — {len(done)}/{total} steps')
        return Result(tuple(lines), tuple(done), (), (), 0)
    parts = [f'{len(done)}/{total} true']
    if not_true:
        parts.append(f'{len(not_true)} not true: {", ".join(not_true)}')
    if unverifiable:
        parts.append(
            f'{len(unverifiable)} unverifiable: {", ".join(unverifiable)}')
    lines.append(f'[{ctx.operation}] {" · ".join(parts)}')
    # Rule 6: 1 is findings. The run COMPLETED — that is what the transcript
    # says — and one or more postconditions do not hold, which is a finding
    # about the tree and not a usage error.
    return Result(tuple(lines), tuple(done), tuple(not_true),
                  tuple(unverifiable), 1)


def _line(ctx: Context, step: Step, verdict: str, detail: str) -> str:
    tail = f' — {detail}' if detail else ''
    return f'[{ctx.operation}:{step.name}] {step.kind.name} {verdict}{tail}'


# --- the verb -----------------------------------------------------------------

USAGE = """\
agentic-sdlc {op} {subject}
agentic-sdlc {op} {subject} --status

Walk the {state} step list for {subject} TO THE END. Every step is a check,
every check reports, and no step halts the walk — the ORDER is what this
machine is for, and whether a step that is not true should stop you is your
question, not its. `agentic-sdlc check <gate>` is the thing that FAILS a tree,
in CI and pre-push, with an exit-code contract for exactly that.

Resumable: the position lives in .agentic-sdlc/run/{state}.json (gitignored),
and every step is re-checked against the tree on every run, so deleting that
file costs nothing.

  {subject}
              a grain id — the same grammar `pm` uses, segment for segment
  --status    print this grain's recorded deviations and the cached position,
              and walk nothing.

Every step that is not true becomes a `deviation` row in the milestone's
ledger.jsonl, carrying the reason the step itself gave. `--skip <step>
--reason "<why>"` was how that row used to be minted, and 0.2.0 removed it:
it existed to escape a refusal, nothing refuses, and the row is now written
without anyone having to remember to ask for it.

The last line is a SCOREBOARD:

    [release] 19/21 true · 1 not true: gate · 1 unverifiable: ci-green

Exit codes: 0 every postcondition holds, 1 one or more does not, 2 the
declaration could not be read.\
"""

CLOSE_USAGE = f"""\
agentic-sdlc {CLOSE_VERB} story   <milestone>/<feature>/<story>
agentic-sdlc {CLOSE_VERB} feature <milestone>/<feature>

The two INNER belts (SDLC.md §0). `close story` is the one that runs dozens of
times a day: four of its five steps are already-computed facts, so it answers
in well under a second and there is no reason to close by hand.

  story    claimed, the narrow check green, the work committed, the evidence
           written, `done`.
  feature  every story finished (asked of `pm ready-for feature`, never
           re-implemented), reviewing, verified, a review record that PARSES,
           no finding left at `disposition: open`, `done`.

Both take the same flags as `release` and `adopt` — just `--status`.
`agentic-sdlc {CLOSE_VERB} story --help` prints it. Like every belt, they
report and finish: a story whose narrow check is red still closes, and the red
rung is named. What follows from that is yours.

The belt ABOVE these two is `agentic-sdlc release <version>`; the belt below a
story is the edit, and `agentic-sdlc verify --story` is what proves it.\
"""


def _spoken(operation: str) -> str:
    """How this operation is INVOKED, which is not always its name.

    `story` and `feature` are reached through `close`, so a refusal that told
    the operator to run `agentic-sdlc story …` would be naming a verb that does
    not exist — the exact defect `cli.py`'s docstring test exists to prevent,
    one layer down.
    """
    return (f'{CLOSE_VERB} {operation}' if operation in CLOSE_OPERATIONS
            else operation)


def _load_run(root: Path, operation: str, version: str,
              names: Sequence[str]) -> tuple['run_state.RunState', str]:
    """(the cached position, '' or what was DISCARDED to get one).

    One state file per operation (`state.py` point 4) and one `close story` run
    per STORY — so the file left by the last story is about a different grain
    every time, which `state.load` refuses as a mismatch. For the close
    operations that refusal would make the belt unusable from its second run
    onward, so a state file belonging to another grain is STALE rather than
    broken: it is thrown away, a blank position is returned, and the discard is
    PRINTED (state.py point 5 — losing it costs nothing, because every step is
    a question about the tree and is re-asked regardless).

    `release` and `adopt` keep the strict refusal. There the file describes the
    one milestone being released, a mismatch means the operator is running the
    wrong version, and starting fresh over it would hide that.
    """
    try:
        return run_state.load(root, operation, version, names), ''
    except run_state.StateDefect as err:
        if operation not in CLOSE_OPERATIONS:
            raise
        run_state.clear(root, operation)
        return (run_state.RunState(operation=operation, version=version),
                f'the run state was discarded and this run starts from the '
                f'tree: {err}')


def parse_flags(rest: Sequence[str]) -> tuple[bool, list[str], str]:
    """(--status, positionals, '' or the usage defect).

    `--skip <step> --reason "<why>"` used to be parsed here as an ordered pair.
    D8 removed both: the flag existed to escape a refusal, and no step refuses
    any more, so it was ceremony with a grammar. What it bought — the durable
    ledger row — is now written by the machine for every step that is not true
    (`walk`'s `record`), which is the same row minus the requirement that
    somebody remember to ask for it.
    """
    status = False
    positional: list[str] = []
    for arg in rest:
        if arg == '--status':
            status = True
        elif arg in ('--skip', '--reason'):
            # Named rather than swept into `unknown option`, because a
            # consumer's script may still carry it and "unknown option
            # '--skip'" would send them looking for a typo.
            return False, [], (
                f'{arg} was removed in 0.2.0: no step refuses to advance any '
                f'more, so there is nothing to skip. Every step that is not '
                f'true is already a `deviation` row in the ledger with the '
                f'reason the step itself gave — `--status` prints them')
        elif arg.startswith('-'):
            return False, [], f'unknown option {arg!r}'
        else:
            positional.append(arg)
    return status, positional, ''


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


def subject_defect(operation: str, value: str) -> str:
    """'' when `value` may be this operation's subject, else why not.

    ONE grammar, applied per segment. A story id is three segments joined by
    `/` and each of them is exactly what `version_defect` already rules on, so
    a traversal, a glob, a backslash, a scheme, an absolute path or a `..` is
    refused here for the same reason it is refused there rather than by a
    second rule that can drift away from it.

    The SEGMENT COUNT is checked and it is not a formality: `close story` given
    a feature id would resolve to a real file and get the wrong question
    answered about it, which is the quietest way this verb could lie —
    `pm ready-for`'s `_grain` learned it first.
    """
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
    """The file a close operation's subject names, or None.

    `model`'s own resolvers, never a second walk: a story this returns and a
    story `pm story done` writes to have to be the same file, and two resolvers
    are two answers on the day a tree holds `s2.md` and `07-s2.md`.
    """
    if operation == 'story':
        return model.story_file(cfg, subject)
    return model.feature_file(cfg, subject)


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
    if operation == CLOSE_VERB:
        # `close story <id>` / `close feature <id>`. The GRAIN is the operation
        # from here down — one entry point, because a second `main` for the
        # inner belts would be a second place for the contract to live.
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
    if any(a in ('-h', '--help', 'help') for a in rest):
        print(USAGE.format(op=_spoken(operation), state=operation,
                           subject=SUBJECT[operation][2]))
        return 0

    # An argument a verb does not understand is a usage error, not a
    # suggestion — the `_run_check` precedent.
    status, positional, flag_defect = parse_flags(rest)
    spoken = _spoken(operation)
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
    version = positional[0]
    defect = subject_defect(operation, version)
    if defect:
        return _refuse(f'{spoken}: {defect}')

    # Everything above refused without touching the filesystem. From here the
    # tree is read — and still nothing is WRITTEN until a step has run.
    cfg = _config(root)
    # The milestone segment, which is `version` itself for the outer two. The
    # ledger row for a deviation goes under the MILESTONE directory whatever
    # grain is being closed, so this resolves for all four.
    mid = version.split('/')[0]
    mdir = model.milestone_dir(cfg, mid)
    if mdir is None:
        # BEFORE any ledger row: the milestone directory is where the row goes,
        # so it has to resolve first. A run against an unresolvable version
        # writes nothing at all.
        print(f'agentic-sdlc: {spoken} {version}: no milestone directory '
              f'{cfg.rel(cfg.roadmap)}/{mid}-* — refused, and nothing was '
              f'created', file=sys.stderr)
        return 1
    if operation in CLOSE_OPERATIONS:
        # Same rule one grain down: the subject has to BE there before a step
        # asks a question about it. A close aimed at a story nobody wrote
        # otherwise walks a list of steps that each answer UNVERIFIABLE for the
        # same reason, which buries the one fact the operator needs.
        try:
            grain = grain_path(cfg, operation, version)
        except model.AmbiguousStory as err:
            print(f'agentic-sdlc: {spoken} {version}: {err} — refused, and '
                  f'nothing was written', file=sys.stderr)
            return 1
        if grain is None:
            print(f'agentic-sdlc: {spoken} {version}: no {noun} resolves from '
                  f'{version!r} (expected {shape}) — refused, and nothing was '
                  f'written', file=sys.stderr)
            return 1

    try:
        names = tuple(steps) if steps is not None else step_names(operation)
        known = (dict(registry) if registry is not None
                 else registry_for(operation))
    except ConfigError as err:
        # A typo in the step list is a CONFIG mistake, not a finding: exit 2,
        # naming the key and the offending value, with no step run.
        return _refuse(f'{spoken}: {err}')
    defect = plan_defect(known, names)
    if defect:
        return _refuse(f'{spoken}: {defect}')

    if status:
        return print_status(cfg, mdir, operation, version, names)

    # Reported, never refused. A ledger this process cannot append to costs
    # the run its DURABLE record of what was not true, and that is worth
    # saying out loud — but a belt that declined to walk over its own
    # bookkeeping would be the machine deciding that telemetry outranks the
    # operator's release, which is the thing D8 took out.
    blocked = _ledger_defect(mdir)
    if blocked:
        print(f'[{operation}] WARNING — {blocked}; this run walks, and the '
              f'steps that are not true will NOT be recorded')

    # The state destination is decided BEFORE the first step. A run that
    # performs half a release and then cannot record where it got to has broken
    # the one promise this machine exists to keep.
    blocked = run_state.destination_defect(cfg.root, operation)
    if blocked:
        return _refuse(f'{spoken}: cannot write the run state: {blocked}')
    try:
        run, stale = _load_run(cfg.root, operation, version, names)
    except run_state.StateDefect as err:
        return _refuse(str(err))

    # R5 goes with `--skip`. The guard here asked the disposable run-state
    # CACHE whether a skipped step's postcondition already held — a question
    # about a file the docs say costs nothing to delete. It only existed to
    # stop `--skip` un-doing a step that was already true, and there is no
    # `--skip`.
    ctx = Context(root=cfg.root, operation=operation, version=version)
    recorder = _deviation_recorder(mdir, operation, version)
    result = walk(known, names, ctx, run, record=recorder)
    if stale:
        print(f'[{operation}] CORRECTED — {stale}')
    for line in result.lines:
        print(line)
    try:
        run_state.save(cfg.root, run)
    except run_state.StateDefect as err:
        return _refuse(str(err))
    return result.exit_code


# --- the durable row for a step that is not true -------------------------------
def _ledger_defect(mdir: Path) -> str:
    """'' when a deviation row can be appended here, else why not."""
    path = ledger.ledger_path(mdir)
    if path.is_dir():
        return f'{path} is a directory, not a ledger'
    probe = path if path.exists() else mdir
    if not os.access(probe, os.W_OK):
        return f'{probe} is not writable'
    return ''


def _recorded(mdir: Path, operation: str, version: str) -> set[str]:
    rows = ledger.read_rows(ledger.ledger_path(mdir))
    return {row.data.get('step') for row in rows
            if row.data.get('kind') == ledger.KIND_DEVIATION
            and row.data.get('operation') == operation
            and row.data.get('grain') == version
            and isinstance(row.data.get('step'), str)}


def _deviation_recorder(mdir: Path, operation: str, version: str):
    """The callback `walk` uses for a step that is not true.

    True when a NEW row landed, False when this step was already recorded —
    which is what makes a re-run idempotent rather than a second row saying the
    same thing. The run cache is gitignored and disposable; the ledger is the
    durable record, and what belongs in it is what nobody can reconstruct from
    the tree afterwards.

    It FAILS OPEN, and that is deliberate: a ledger this process cannot append
    to is a telemetry problem, and a belt that refused to walk over one would
    be the machine deciding that its own bookkeeping outranks the operator's
    release. The failure is reported by `_ledger_defect` before the walk.
    """
    def record(step: str, outcome: str, reason: str) -> bool:
        try:
            if step in _recorded(mdir, operation, version):
                return False
            ledger.append_row(mdir, ledger.deviation_row(
                version, operation, step, reason, outcome=outcome))
            return True
        except (ledger.LedgerError, ValueError, OSError):
            return False

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
