"""state.py — where a conveyor run got to, on disk, as a CACHE of `check()`.

`<repo-root>/.agentic-sdlc/run/<operation>.json`, gitignored, one file per
operation. Five reasons, and the fifth is the one that makes the other four
safe:

1. **It is working state, not a record.** The RECORD is the ledger row under
   `pm/roadmap/<milestone>/ledger.jsonl` — tracked and durable. A tracked
   position file would be a second scoreboard beside the ledger, and a second
   scoreboard lies.
2. **`tree-clean` is itself a step.** A TRACKED state file would be dirtied by
   the very run that checks the tree is clean — the machine making its own
   precondition false. Gitignoring is what keeps `tree-clean` answerable.
3. **Per checkout**, so a sibling worktree gets its own and two parallel runs
   cannot overwrite one file.
4. **One file per operation**, so an `adopt` run in progress and a `release`
   run cannot clobber each other.
5. **Losing it costs nothing.** Every `check()` is a question about the TREE,
   so a deleted state file means the next run re-derives the position by
   asking. That is why it can be ignored safely, and `tests/test_conveyor_state
   .py::ADeletedStateFileCostsNothing` is the proof that points 1-4 were the
   right call.

**It is never the authority.** Nothing here decides that a step is done; it
remembers what `check()` last answered so a resumed run can PRINT the
difference. `driver.walk` re-asks every step regardless, and when the file and
the tree disagree the tree wins, the file is corrected, and the correction is
printed. A run state that could assert a step was done while the tree said
otherwise is the lie the conveyor exists to end.

**It is read from disk, so it is a payload parser and hostile by default.**
Every malformed shape below raises `StateDefect` — never a silent start from
step 0, which is the read-side cardinal sin wearing a resume button. A
`StateDefect` is a config error (exit 2), not a finding: the operator has a
broken file, not a release that is not ready.

Writing goes through `core.apply` like every other write in this package, so a
destination that cannot be written is REFUSED by path before a byte moves —
and `destination_defect` lets the driver ask that question before it runs the
first step, because a run that performs half a release and then cannot record
where it got to has broken the one promise this file exists to keep.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from agentic_sdlc.core import apply
from agentic_sdlc.repo.pm import ledger

# The on-disk vocabulary for what `check()` answered. It lives HERE rather than
# in the driver because this module is the one that serialises it: `driver.Truth`
# takes its values from these names, so the enum and the file can never drift
# into two spellings of the same answer.
TRUE = 'true'
FALSE = 'false'
UNVERIFIABLE = 'unverifiable'
ANSWERS = (TRUE, FALSE, UNVERIFIABLE)

# Bumped when the shape below changes incompatibly. A file from a LATER format
# is refused rather than read optimistically: a field this build does not know
# about is a position it cannot honour.
FORMAT = 1

STATE_DIRNAME = '.agentic-sdlc'
RUN_DIRNAME = 'run'

# An operation name reaches the filesystem as a path segment, so it is checked
# here as well as in the driver. Two callers, one grammar: a name that is not
# one of these cannot name a file.
_OPERATION_CHARS = set('abcdefghijklmnopqrstuvwxyz-')


class StateDefect(Exception):
    """The file exists and cannot be read CORRECTLY. Never a partial parse: no
    records are returned from a document with one bad row, for the same reason
    `verdict.MalformedVerdict` returns no findings from a block with one bad
    row — a position assembled from the half that parsed is a position nobody
    wrote."""


@dataclass(frozen=True)
class Record:
    """One step's last answer. `answer` is a member of `ANSWERS`."""

    step: str
    answer: str
    at: str
    reason: str = ''


@dataclass
class RunState:
    """The cache. `records` is ordered by first mention, which is the order the
    steps were walked in.

    `corrections` carries what `load` had to repair to read the file at all —
    the driver PRINTS them. A repair nobody is told about is indistinguishable
    from a file that was fine.
    """

    operation: str
    version: str
    records: dict[str, Record] = field(default_factory=dict)
    corrections: list[str] = field(default_factory=list)
    at: str = ''

    def record(self, step: str, answer: str, reason: str = '') -> None:
        if answer not in ANSWERS:
            raise ValueError(f'{answer!r} is not one of {ANSWERS}')
        self.at = ledger.utc_now()
        self.records[step] = Record(step, answer, self.at, reason)

    def answer_for(self, step: str) -> str:
        """What the file last recorded for `step`, or `''` when it holds
        nothing. Advisory ONLY — the driver re-asks `check()` either way."""
        got = self.records.get(step)
        return got.answer if got is not None else ''

    def document(self) -> dict:
        return {
            'format': FORMAT,
            'operation': self.operation,
            'version': self.version,
            'updated': self.at,
            'steps': [{'step': r.step, 'answer': r.answer, 'at': r.at,
                       'reason': r.reason} for r in self.records.values()],
        }


def path_for(root: Path, operation: str) -> Path:
    if not operation or set(operation) - _OPERATION_CHARS:
        raise StateDefect(f'{operation!r} is not an operation name')
    return Path(root) / STATE_DIRNAME / RUN_DIRNAME / f'{operation}.json'


def dumps(state: RunState) -> str:
    """The file's bytes.

    `ensure_ascii=True` is a decision, not a default: U+2028 and U+2029 are
    legal inside a JSON string and are LINE TERMINATORS to everything that
    reads by line, so a `reason` carrying one would split one record into two
    for the next reader. Escaped, the whole document is ASCII and every record
    round-trips as one. Same hazard `ledger.LINE_BREAKERS` handles a layer
    down, answered here by never emitting the character at all.
    """
    return json.dumps(state.document(), indent=2, ensure_ascii=True) + '\n'


def destination_defect(root: Path, operation: str) -> str:
    """'' when the state file can be written, else what stands in the way —
    decided WITHOUT writing a byte, through the same `core.apply` decision
    every install verb refuses by. The driver asks this BEFORE the first step.
    """
    target = path_for(root, operation)
    blocked = apply.Plan().overwrite(
        target, '', symlink=apply.Symlink.FOLLOW).decide()
    if not blocked:
        return ''
    first = blocked[0]
    return f'{first.path} {first.reason.value}'


def save(root: Path, state: RunState) -> None:
    """Write the position. All-or-nothing, like every write in this package."""
    target = path_for(root, state.operation)
    result = apply.Plan().overwrite(
        target, dumps(state), newline='\n',
        symlink=apply.Symlink.FOLLOW).apply()
    if result.blocked:
        raise StateDefect(
            f'cannot write the run state: '
            + '; '.join(b.describe() for b in result.blocked))
    if result.failed is not None:
        raise StateDefect(f'cannot write the run state {target}: {result.error}')


def clear(root: Path, operation: str) -> None:
    """Throw the position away. Costs nothing — see point 5 above."""
    result = apply.remove_file(path_for(root, operation))
    if result.failed is not None:
        raise StateDefect(f'cannot remove the run state: {result.error}')


def load(root: Path, operation: str, version: str,
         known: Sequence[str]) -> RunState:
    """The recorded position, or a blank one when there is no file.

    `known` is the CONFIGURED step list. A recorded name outside it is refused
    rather than skipped: a renamed step must not resume into a hole, and a
    driver that silently dropped the unknown row would resume from a position
    that never existed.

    Raises `StateDefect` for every unreadable shape. Nothing here writes, so
    every refusal below leaves the file exactly as it found it.
    """
    path = path_for(root, operation)
    blank = RunState(operation=operation, version=version)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        what = 'a directory' if path.is_dir() else 'not a regular file'
        raise StateDefect(f'the run state {path} is {what}')
    if not path.exists():
        return blank
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as err:
        raise StateDefect(f'cannot read the run state {path}: {err}') from None
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as err:
        raise StateDefect(
            f'the run state {path} is not JSON ({err.msg} at line {err.lineno})'
        ) from None
    if not isinstance(doc, dict):
        raise StateDefect(
            f'the run state {path} holds a {type(doc).__name__}, not an object')
    got_format = doc.get('format')
    if got_format != FORMAT:
        raise StateDefect(
            f'the run state {path} declares format {got_format!r}; '
            f'this build reads format {FORMAT}')
    if doc.get('operation') != operation:
        raise StateDefect(
            f'the run state {path} belongs to a {doc.get("operation")!r} run, '
            f'not this {operation!r} run')
    if doc.get('version') != version:
        raise StateDefect(
            f'the run state {path} belongs to version {doc.get("version")!r}, '
            f'not {version!r}')
    steps = doc.get('steps')
    if not isinstance(steps, list):
        raise StateDefect(
            f'the run state {path} has no "steps" list '
            f'(it holds a {type(steps).__name__})')
    state = RunState(operation=operation, version=version,
                     at=str(doc.get('updated', '')))
    for index, entry in enumerate(steps):
        if not isinstance(entry, dict):
            raise StateDefect(
                f'the run state {path}: "steps" entry {index} is a '
                f'{type(entry).__name__}, not an object')
        name = entry.get('step')
        answer = entry.get('answer')
        if not isinstance(name, str) or name not in known:
            raise StateDefect(
                f'the run state {path} names a step {name!r} that is not in '
                f'the configured list — a renamed step must not resume into a '
                f'hole')
        if answer not in ANSWERS:
            raise StateDefect(
                f'the run state {path}: step {name!r} carries an answer '
                f'{answer!r}, which is not one of {ANSWERS}')
        if name in state.records:
            # Not a refusal: the tree wins anyway, so the LAST answer stands
            # and the repair is carried out for the driver to print.
            state.corrections.append(
                f'the run state listed {name!r} twice; the later entry '
                f'({answer}) stands, and every step is re-checked regardless')
        state.records[name] = Record(
            name, answer, str(entry.get('at', '')),
            str(entry.get('reason', '')))
    return state
