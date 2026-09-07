"""lessons.py — a recorded lesson, read back where the belt is standing.

A `lesson` row (`ft-a-lesson-is-a-row-bound-to-a-grain`) names a grain, a rule
and the `source` it came from. This module is the READ side, and D1 is why it
exists: capture with no read-back is decoration.

**Never a gate.** Nothing here blocks, refuses or changes a verdict — an
unreadable ledger and an unreachable sink are NAMED lines (rule 11), never an
exit code. **Never a nag.** Scope is exact: the grain named, or the rule named.
No fuzzy matching, no ranking, no scoring — that is the inference edge this
package does not have (rule 9), and when several match they are all printed in
recorded order, because choosing is inference and the caller has the sources.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo import emit
from agentic_sdlc.repo.pm import ledger, model

# The row kind, and its fields IN ORDER — the columns a read verb names.
KIND = 'lesson'
FIELDS = ('grain', 'rule', 'source', 'text', 'at')
COLUMNS = FIELDS

# The line this module adds BESIDE a verdict; it never reshapes one (rule 6).
WORD = 'lesson'
SCOPE_GRAIN = 'grain'
SCOPE_RULE = 'rule'
# A row that points at nothing is reported as pointing at nothing.
NO_SOURCE = '(no source recorded)'
NO_TEXT = '(no text recorded)'
# A ledger row is unbounded; a printed line is not.
TEXT_LIMIT = 400

# The emitted event's kind is `<KIND>.<tap>`, so its last segment is the tap
# `check pm` U3 counts and its first says what the row IS. It is deliberately
# not `rung.enter` / `check.verdict`: those rows are the belt's own event
# (`ft-one-event-shape-serves-three-readers`), and one kind with two payloads
# is the second scoreboard this package deletes everywhere else.
EVENT_KINDS = {emit.TAP_ENTER: f'{KIND}.{emit.TAP_ENTER}',
               emit.TAP_VERDICT: f'{KIND}.{emit.TAP_VERDICT}'}


class Lesson(NamedTuple):
    """One recorded lesson, and the row it was read from, verbatim."""

    grain: str
    rule: str
    source: str
    text: str
    at: str
    row: dict


def lesson_of(row: dict) -> Lesson | None:
    """The lesson this row IS, or None. Every field is type-checked: rows
    arrive from other branches and versions, and a field of the wrong shape
    names nothing rather than crashing a belt."""
    if row.get('kind') != KIND:
        return None
    values = [row.get(name) for name in FIELDS]
    return Lesson(*[v if isinstance(v, str) else '' for v in values],
                  dict(row))


class Store(NamedTuple):
    """Every lesson this tree has recorded, and the ledgers that could not be
    read — an unreadable file is named, never counted as silence (rule 11)."""

    lessons: tuple[Lesson, ...] = ()
    unreadable: tuple[str, ...] = ()

    def against_grain(self, gid: str) -> tuple[Lesson, ...]:
        """The lessons naming EXACTLY this grain, in recorded order."""
        if not gid:
            return ()
        return tuple(les for les in self.lessons if les.grain == gid)

    def against_rule(self, rule: str) -> tuple[Lesson, ...]:
        """The lessons naming EXACTLY this rule, in recorded order."""
        if not rule:
            return ()
        return tuple(les for les in self.lessons if les.rule == rule)


def paths(cfg) -> list[Path]:
    """Both ledger homes (0.4.0/D3): the tree's own, and one per milestone.

    THE HELPER THAT BELONGS IN `ledger.py` — `checks/pm.py` spells the same two
    lines privately, and a third reader would be a third answer to "where are
    the rows".
    """
    found = [ledger.grainless_path(cfg.roadmap)]
    found += [ledger.ledger_for(cfg, grain.gid) for grain in model.milestones(cfg)]
    return list(dict.fromkeys(found))


def read(cfg) -> Store:
    """Every `lesson` row in the tree, oldest first, ledger by ledger.

    This never raises: a lesson may not decide a belt, so what could not be
    read is carried in `unreadable` and said on the line.
    """
    try:
        found = paths(cfg)
    except Exception as err:  # noqa: BLE001 — a named non-answer, not a crash
        return Store((), (f'the ledgers could not be located '
                          f'({type(err).__name__}: {err})',))
    lessons: list[Lesson] = []
    unreadable: list[str] = []
    for path in found:
        try:
            rows = ledger.read_rows(path)
        except (ledger.LedgerError, OSError) as err:
            unreadable.append(str(err))
            continue
        lessons.extend(les for les in (lesson_of(row.data) for row in rows)
                       if les is not None)
    return Store(tuple(lessons), tuple(unreadable))


def blockers_named(said: str) -> tuple[str, ...]:
    """The grains `pm ready-for` NAMED as blockers: the token after each of its
    own `BLOCKED` markers, and nothing read out of the rest of the sentence.

    The marker is imported rather than copied — the verb owns the line shape,
    and a second spelling of it here would go stale the day the line moves.
    """
    from agentic_sdlc.repo.pm.ready_for import BLOCKED

    marker = BLOCKED.strip()
    tokens = said.split()
    return tuple(dict.fromkeys(
        tokens[i + 1] for i, token in enumerate(tokens)
        if token == marker and i + 1 < len(tokens)))


def _clip(text: str) -> str:
    """One bounded line of a recorded text — flattened, never re-worded."""
    flat = ' '.join(text.split())
    return flat if len(flat) <= TEXT_LIMIT else flat[:TEXT_LIMIT] + '…'


def line(operation: str, scope: str, name: str, les: Lesson) -> str:
    """The one line shape: what matched, the text, and always the source, so
    the reader goes to the record rather than trusting a paraphrase."""
    return (f'[{operation}] {WORD}: {scope} {name} — '
            f'{_clip(les.text) or NO_TEXT} '
            f'(source: {les.source or NO_SOURCE})')


def event(tap: str, les: Lesson, *, operation: str, grain: str, scope: str,
          name: str, check: str = '') -> dict:
    """The row emitted beside the line. The lesson travels VERBATIM under one
    key: this event says where it surfaced, never what it means."""
    row = {'ts': ledger.utc_now(), 'kind': EVENT_KINDS[tap], 'grain': grain,
           'rung': operation, 'scope': scope, 'matched': name}
    if check:
        row['check'] = check
    row['lesson'] = les.row
    return row


class Surfacer:
    """What a belt run holds: the tree's lessons, the config the emit seam
    needs, and the grain this run's events are routed by."""

    def __init__(self, store: Store, cfg, operation: str, grain: str):
        self.store = store
        self.cfg = cfg
        self.operation = operation
        self.grain = grain
        self._emit_defect = ''

    def at_entry(self) -> list[str]:
        """The move surface: this belt is about to touch `grain`."""
        lines = [f'[{self.operation}] {WORD} WARNING — {why}'
                 for why in self.store.unreadable]
        return lines + self._say(emit.TAP_ENTER, SCOPE_GRAIN, self.grain,
                                 self.store.against_grain(self.grain))

    def at_check(self, check: str, names: tuple[str, ...] = ()) -> list[str]:
        """The check surface: this check's RULE, then every blocker it named.

        Both are exact, and a lesson matching twice is printed once — under the
        rule, which is the thing that just ran.
        """
        matched = self.store.against_rule(check)
        lines = self._say(emit.TAP_VERDICT, SCOPE_RULE, check, matched, check)
        said = list(matched)
        for gid in names:
            fresh = tuple(les for les in self.store.against_grain(gid)
                          if all(les is not seen for seen in said))
            lines += self._say(emit.TAP_VERDICT, SCOPE_GRAIN, gid, fresh, check)
            said += fresh
        return lines

    def _say(self, tap: str, scope: str, name: str,
             matched: tuple[Lesson, ...], check: str = '') -> list[str]:
        """Print each match in recorded order, and emit each one."""
        lines = []
        for les in matched:
            lines.append(line(self.operation, scope, name, les))
            lines += self._emit(tap, les, scope, name, check)
        return lines

    def _emit(self, tap: str, les: Lesson, scope: str, name: str,
              check: str) -> list[str]:
        """The emit seam, and the WARNING this run owes once if it could not be
        reached. A malformed `[emit]` is exit 2 wherever the section is READ
        for its own sake; here it is a line, because a lesson that changed an
        exit code would be the gate this feature must never be.
        """
        row = event(tap, les, operation=self.operation, grain=self.grain,
                    scope=scope, name=name, check=check)
        try:
            emit.emit(self.cfg, tap, row)
        except Exception as err:  # noqa: BLE001 — never load-bearing (D1)
            if self._emit_defect:
                return []
            self._emit_defect = (
                f'[{self.operation}] {WORD} WARNING — the {WORD} above was '
                f'printed and NOT emitted ({type(err).__name__}: {err}); the '
                f'belt itself is unaffected')
            return [self._emit_defect]
        return []


def surfacer_for(cfg, operation: str, grain: str) -> Surfacer:
    """The reader one belt run uses, built once and asked per check."""
    return Surfacer(read(cfg), cfg, operation, grain)
