"""lessons.py — a `lesson` row: recorded by hand, read back where you stand.

D1: capture with no read-back is decoration, and read-back with no capture
reads an empty file. **Never a gate**: no verdict and no exit code change, and
what would not read is a NAMED line (rule 11). **Never a nag**: the grain or
the rule named, exactly — no fuzzy match, no ranking, no scoring (rule 9), and
every match prints in recorded order.
"""
from __future__ import annotations

import sys
from typing import NamedTuple

from agentic_sdlc.repo import emit
from agentic_sdlc.repo.pm import ledger, model

# The row kind, and its fields IN ORDER — the columns a read verb names. `ts`,
# the stamp every other reader keys on: spelled `at`, a row sorts as the empty
# string and files at the beginning of time.
KIND = ledger.KIND_LESSON
FIELDS = ('grain', 'rule', 'source', 'text', 'ts')
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
    ts: str
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


def read(cfg) -> Store:
    """Every `lesson` row, oldest first. Never raises: a lesson may not decide
    a belt, so what would not read is carried and said."""
    try:
        found = ledger.ledger_paths(cfg)
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
    # Two files, one timeline: FILE order printed a later milestone's oldest
    # lesson before an earlier one's newest, and `--help` promises RECORDED
    # order. Ordering by the stamp is not ranking (D1); `show` sorts the same.
    lessons.sort(key=lambda one: one.ts)
    return Store(tuple(lessons), tuple(unreadable))


# The third surface reads grains off ANOTHER verb's sentences, so both halves of
# the coupling are trimmed rather than taken verbatim: the marker was matched
# bare while every other `BLOCKED` this repo ships is `BLOCKED:` or
# `BLOCKED (…)`, and the id was the first token exactly, so the tag rung's
# `<owner>: <defect>` yielded `0.1/alpha:` and matched nothing. Both went dark
# with no line. Four of the eleven shapes name no grain AT ALL and rightly say
# nothing; what stops that being silence is a case per shape in
# `tests/test_conveyor_lessons.py`, where a reworded sentence goes red.
TOKEN_TRIM = ',;:.!?()[]{}<>"\'`'


def _token(raw: str) -> str:
    """One printed word read as an ID, sentence punctuation off. Never re-cased
    and never re-spelled: `0.1/Alpha` is not `0.1/alpha` (rule 9)."""
    return raw.strip(TOKEN_TRIM)


def blockers_named(said: str) -> tuple[str, ...]:
    """The grains `pm ready-for` NAMED as blockers, first seen first: the first
    word of each blocked sentence that is not the verb's own vocabulary, every
    one of those words IMPORTED from the verb rather than respelled here."""
    from agentic_sdlc.repo.pm.ready_for import BLOCKED, UNVERIFIABLE

    marker = _token(BLOCKED.strip())
    prefixes = {_token(UNVERIFIABLE)}  # `UNVERIFIABLE <thing>: …`
    found: list[str] = []
    want = False
    for raw in said.split():
        token = _token(raw)
        if token == marker:
            want = True
        elif want and token not in prefixes:
            # ONE word per blocker: scanning on would collect prose into a
            # tuple the driver documents as grains.
            want = False
            if token:
                found.append(token)
    return tuple(dict.fromkeys(found))


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


# --- the verb: `agentic-sdlc lesson record|show` ------------------------------
# The WRITE half. A lesson comes from a gate verdict, a below-MAJOR review
# finding or a `--force` deviation, and the CALLER names which: nothing derives
# one, because anything inferred needs a feedback edge and a reader/writer has
# nowhere to put one (D1). `show` is the read side rule 11 requires beside it.
RECORD, SHOW = 'record', 'show'
GRAIN_FLAG, RULE_FLAG = f'--{SCOPE_GRAIN}', f'--{SCOPE_RULE}'
SOURCE_FLAG = '--source'
RECORD_FLAGS = (GRAIN_FLAG, RULE_FLAG, SOURCE_FLAG)
SHOW_FLAGS = (GRAIN_FLAG, RULE_FLAG)
DASH = '-'
HELP_WORDS = ('-h', '--help', 'help')

USAGE = f"""\
agentic-sdlc {WORD} {RECORD} {GRAIN_FLAG} <id> {RULE_FLAG} <id> \
{SOURCE_FLAG} <path> "<text>"
agentic-sdlc {WORD} {SHOW} [{GRAIN_FLAG} <id> | {RULE_FLAG} <id>]

One append-only ledger row naming the grain it came from, the rule or check it
is about, and the record it was derived from — routed to the milestone that
owns the grain, like every other row. The row POINTS at its source and never
restates it.

  {GRAIN_FLAG + ' <id>':<16}the grain the lesson came from
  {RULE_FLAG + ' <id>':<16}the rule or belt check it is about
  {SOURCE_FLAG + ' <path>':<16}the record it was derived from: a review record, a
                  gate transcript, the deviation row that prompted it — a
                  path resolving to nothing is refused, and nothing lands
  {'"<text>"':<16}the lesson itself, one line

`{SHOW}` prints one tab-separated row per lesson in the order they were
recorded; columns IN ORDER: {' '.join(COLUMNS)}
With no filter it prints them all. Nothing is ranked, scored or weighed
(rule 9) — composition is the shell's job.

The belts read these back where you stand: a lesson against the grain at the
move, one against a check's name beside that check's verdict.

Exit codes: 0 recorded or printed, 1 the source or the grain names nothing and
nothing was recorded, 2 usage or config.\
"""


def _refused(why: str, code: int) -> int:
    """One line on stderr, and the code rule 6 files it under."""
    print(f'agentic-sdlc {WORD}: {why}', file=sys.stderr)
    return code


def flags_given(rest: list[str], known: tuple[str, ...]
                ) -> tuple[dict[str, str], list[str], str]:
    """(the flags given, the words left over, '' or the defect). Both
    spellings, and a flag given twice is a defect: one lesson, one grain."""
    given: dict[str, str] = {}
    left: list[str] = []
    index = 0
    while index < len(rest):
        word = rest[index]
        name, split, value = word.partition('=')
        if name in known:
            if not split:
                if index + 1 >= len(rest):
                    return given, left, f'{name} needs a value'
                value, index = rest[index + 1], index + 1
            if name in given:
                return given, left, f'{name} was given twice'
            given[name] = value
        elif word.startswith(DASH):
            return given, left, f'unknown flag {word!r}'
        else:
            left.append(word)
        index += 1
    return given, left, ''


def record(cfg, rest: list[str]) -> int:
    """Append one row, routed by grain. Both pointers resolve BEFORE the
    append, and this ledger is committed and append-only."""
    given, words, defect = flags_given(rest, RECORD_FLAGS)
    if not defect and ([f for f in RECORD_FLAGS if not given.get(f)]
                       or len(words) != 1):
        defect = (f'{RECORD} takes {" ".join(RECORD_FLAGS)} and exactly one '
                  f'quoted text, and every one of them is required')
    if defect:
        return _refused(defect, 2)
    source = given[SOURCE_FLAG]
    # Rule 8: this ledger is committed and APPEND-ONLY, so a pointer that
    # resolves on one machine cannot be edited back out afterwards.
    if model.pointer_escapes(source):
        return _refused(f'{SOURCE_FLAG} {source!r} names a path outside this '
                        f'checkout; nothing was recorded, because a pointer '
                        f'only its author can follow points at nothing for '
                        f'every other reader of this ledger', 1)
    target = model.record_path(cfg, source)
    if not model.record_resolves(target):
        return _refused(f'{SOURCE_FLAG} {source!r} names no file '
                        f'({cfg.rel(target)}); nothing was recorded, because a '
                        f'row pointing at nothing is the paraphrase this row '
                        f'exists not to be', 1)
    where = ledger.ledger_of_grain(cfg, given[GRAIN_FLAG])
    if where is None:
        return _refused(f'no milestone owns {given[GRAIN_FLAG]!r}, so no '
                        f'{ledger.LEDGER_FILE_NAME} can hold this {WORD}; '
                        f'nothing was recorded', 1)
    try:
        row = ledger.lesson_row(given[GRAIN_FLAG], given[RULE_FLAG],
                                given[SOURCE_FLAG], words[0])
    except ValueError as err:
        return _refused(str(err), 2)
    try:
        ledger.append_to(where, row)
    except OSError as err:
        return _refused(f'{cfg.rel(where)} could not be appended to ({err}); '
                        f'nothing was recorded', 1)
    print(f'[{WORD}] recorded against {given[GRAIN_FLAG]} / '
          f'{given[RULE_FLAG]} — {cfg.rel(where)}')
    return 0


def _row_line(les: Lesson) -> str:
    """One lesson, tab-separated, `-` for an empty column: a fixed column
    count is what a shell `read` needs."""
    cells = [getattr(les, name) or DASH for name in COLUMNS]
    return '\t'.join(cell.replace('\t', ' ') for cell in cells)


def show(cfg, rest: list[str]) -> int:
    """Every lesson, or the ones naming EXACTLY one grain or one rule."""
    given, words, defect = flags_given(rest, SHOW_FLAGS)
    if not defect and words:
        defect = f'{SHOW} takes no words, got {" ".join(words)}'
    if not defect and len(given) > 1:
        defect = (f'{SHOW} filters by {GRAIN_FLAG} or by {RULE_FLAG}, never '
                  f'both — one filter, one column')
    if defect:
        return _refused(defect, 2)
    store = read(cfg)
    for why in store.unreadable:
        print(f'[{WORD}] WARNING — {why}', file=sys.stderr)
    found = store.lessons
    if GRAIN_FLAG in given:
        found = store.against_grain(given[GRAIN_FLAG])
    elif RULE_FLAG in given:
        found = store.against_rule(given[RULE_FLAG])
    for les in found:
        print(_row_line(les))
    if not found:
        # Rule 11: nothing recorded is a FACT, said in words, not a blank.
        print(f'[{WORD}] no {WORD} recorded'
              + (f' against {" ".join(given.values())}' if given else ''))
    return 0


def main(argv: list[str]) -> int:
    """`lesson record` and `lesson show`, with the config read once — and
    never before `--help` has answered."""
    args = list(argv)
    if not args or args[0] in HELP_WORDS:
        print(USAGE)
        return 0 if args else 2
    word, rest = args[0], args[1:]
    if word not in (RECORD, SHOW):
        return _refused(f'unknown {WORD} command {word!r} (expected: '
                        f'{RECORD}, {SHOW})', 2)
    try:
        cfg = model.load()
    except model.ConfigError as err:
        return _refused(str(err), 2)
    return record(cfg, rest) if word == RECORD else show(cfg, rest)
