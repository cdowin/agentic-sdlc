"""lessons.py — a recorded `lesson` row, read back where the belt is standing.

D1: capture with no read-back is decoration. **Never a gate**: no verdict and
no exit code change, and what would not read is a NAMED line (rule 11).
**Never a nag**: the grain or the rule named, exactly — no fuzzy match, no
ranking, no scoring (rule 9), and every match prints in recorded order.
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
# A row pointing at nothing says so, and a row is unbounded where a line is not.
WORD = 'lesson'
SCOPE_GRAIN = 'grain'
SCOPE_RULE = 'rule'
NO_SOURCE = '(no source recorded)'
NO_TEXT = '(no text recorded)'
TEXT_LIMIT = 400

# `<KIND>.<tap>`: the last segment is the tap `check pm` U3 counts, and it is
# not `rung.enter`/`check.verdict` — that is the belt's own event's kind.
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
    """The lesson this row IS, or None; typed, since a row from another version
    with a bad field must name nothing."""
    if row.get('kind') != KIND:
        return None
    values = [row.get(name) for name in FIELDS]
    return Lesson(*[v if isinstance(v, str) else '' for v in values],
                  dict(row))


class Store(NamedTuple):
    """Every lesson recorded, and the ledgers that would not read — named,
    never counted as silence (rule 11)."""

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
    """Both ledger homes (0.4.0/D3), and THE HELPER THAT BELONGS IN `ledger.py`:
    `checks/pm.py` spells it privately, and a third is a third answer."""
    found = [ledger.grainless_path(cfg.roadmap)]
    found += [ledger.ledger_for(cfg, g.gid) for g in model.milestones(cfg)]
    return list(dict.fromkeys(found))


def read(cfg) -> Store:
    """Every `lesson` row, oldest first. Never raises: a lesson may not decide
    a belt, so what would not read is carried and said."""
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
    """The grains `pm ready-for` NAMED as blockers: the token after each of
    its own `BLOCKED` marker, imported and never copied — the verb owns it."""
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
    """What matched, the text, and ALWAYS the source: the reader goes to the
    record rather than trusting a paraphrase."""
    return (f'[{operation}] {WORD}: {scope} {name} — '
            f'{_clip(les.text) or NO_TEXT} '
            f'(source: {les.source or NO_SOURCE})')


def event(tap: str, les: Lesson, *, operation: str, grain: str, scope: str,
          name: str, check: str = '') -> dict:
    """The row emitted beside the line; the lesson rides VERBATIM under one key,
    because this event says where it surfaced, never what it means."""
    row = {'ts': ledger.utc_now(), 'kind': EVENT_KINDS[tap], 'grain': grain,
           'rung': operation, 'scope': scope, 'matched': name}
    if check:
        row['check'] = check
    row['lesson'] = les.row
    return row


class Surfacer:
    """One run's read-back: the lessons, the config the emit seam needs, and
    the grain its events are routed by."""

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
        """The check surface: this check's RULE, then every blocker it named —
        both exact, and a lesson matching twice prints once, under the rule."""
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
        """The emit seam, and the one WARNING a run owes if it could not be
        reached — even a malformed `[emit]`, which decides nothing here."""
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
