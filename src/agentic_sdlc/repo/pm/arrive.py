"""arrive.py — ARRIVAL is the one event: a grain reaches a state (0.5.0/D3).

Everything a move says and writes reads that one event, all of it DERIVED from
what the project declared:

    1  the status is written            `pm/cli.py`, unchanged
    2  the fork is asked                `[pm.arrive.<kind>.<state>]` ask/answers
    3  the disposition is recorded      one row, `none` when nobody answered
    4  the capability is named          `[pm.arrive.…] have`, as a CENSUS
    +  the tree's open work is reported the pressure line, silent when empty

Direction is not modelled and there is no transition table (0.5.0/D3); the row
grammar is in `pm/ledger.py` with every other row this package mints. Nothing
here decides, advises or refuses a move: `next:` is the belt's check list,
`have:` is inventory, `open:` is a census. *"You should close something"* is
an opinion and does not ship.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentic_sdlc.repo import emit
from agentic_sdlc.repo.pm import ledger, model

# Which belt closes a grain of each kind, and which belt the grain ABOVE it
# needs next — `steps.registry_for` keys, and the whole of the mapping: the
# CHECKS each belt asks are read from the registry at runtime.
CLOSES = {'story': 'story', 'feature': 'feature', 'milestone': 'release'}
# A milestone's `done` names nothing above it: inventing a sentence for what
# somebody does after a release would be this engine having an opinion.
ABOVE = {'story': 'feature', 'feature': 'release'}

# The belt whose subject is a version rather than a grain id; `_subject_of`
# asks its own `SUBJECT` entry rather than this name.
RELEASE_BELT = 'release'

# The frontmatter pointer a close stamps. A grain whose document does not
# carry the key is not counted for want of a field it never had.
RECORD_FIELD = 'reviewed'

PREFIX = '[pm]'


def _say(line: str) -> None:
    """One line of the event's report, on STDERR — STDOUT stays the one line
    the write wrote, which is what a consumer parses (rule 6)."""
    print(f'{PREFIX} {line}' if line else PREFIX, file=sys.stderr)


# --- 2: the fork --------------------------------------------------------------
@dataclass(frozen=True)
class Said:
    """What the caller answered at an arrival, or nothing: the declared flag
    (`--by`) and the rest of the line as it was TYPED. The tool records a
    CLAIM and never verifies it (rule 9)."""

    answer: str = ledger.NO_DISPOSITION
    value: str = ''

    def __bool__(self) -> bool:
        return self.answer != ledger.NO_DISPOSITION


NOTHING = Said()


class Incomplete(Exception):
    """A declared answer typed without the rest of itself. Exit 2, by name."""


def take(node: model.Arrival | None,
         args: list[str]) -> tuple[Said, list[str]]:
    """Split a declared answer off the tail of `args`; `(NOTHING, args)` when
    the caller typed none. The flags come from the node's own `answers`, so a
    project declaring a different fork gets its own with no edit here."""
    if node is None:
        return NOTHING, list(args)
    flags = node.flags
    for index, arg in enumerate(args):
        if arg not in flags:
            continue
        value = ' '.join(args[index + 1:]).strip()
        if not value and node.carries_value(arg):
            raise Incomplete(
                f'{arg} needs the rest of the answer — this project declares '
                f'{", ".join(repr(a) for a in node.answers)}')
        # The one free-text field on the row, held to the guard every other
        # free-text field crosses: one row is one line.
        defect = ledger.reason_defect(value) if value else ''
        if defect:
            raise Incomplete(f'{arg} cannot record that answer: {defect}')
        return Said(arg, value), list(args[:index])
    return NOTHING, list(args)


def unknown_flag_hint(node: model.Arrival | None) -> str:
    """What a state DOES accept, for the refusal a flag it does not gets —
    rule 11: naming the answers beats naming the typo."""
    if node is None or not node.answers:
        return ''
    return (f' — arriving at {node.kind} {node.state} accepts '
            + ', '.join(repr(a) for a in node.answers))


def fork_lines(cfg: model.PmConfig, node: model.Arrival | None, gid: str,
               said: Said = NOTHING) -> list[str]:
    """The question and both answers, each a command that can be pasted. The
    command is the ARRIVAL itself: a move is idempotent, so re-running it with
    the answer records the disposition and writes nothing else — the cheap
    answer costs one paste and so does the expensive one. A move that already
    carries its answer prints no question at all.
    """
    if node is None or not node.ask or not cfg.pressure or said:
        return []
    move = f'agentic-sdlc pm {node.kind} {node.state} {gid}'
    lines = ['', node.ask]
    for index, answer in enumerate(node.answers):
        lines.append(f'  {chr(ord("a") + index)}) {move} {answer}')
    return lines


def disposition_of(row: dict) -> bool:
    """Is this row an arrival's disposition? ONE shape carries the word since
    0.5.0/D6, so this is the kind and nothing else — every reader asks it here
    rather than each branching on its own idea of the shape."""
    return row.get('kind') == ledger.KIND_DISPOSITION


# --- the ONE derivation, two renderers ----------------------------------------
@dataclass(frozen=True)
class Next:
    """What the conveyor asks next, derived once and rendered twice: the prose
    breadcrumb (`pm/cli.py`) and the `rung.leave` row both read THIS."""

    belt: str
    verb: str
    subject: str
    checks: tuple[str, ...]

    @property
    def action(self) -> str:
        """The command a caller can copy, with the belt's own argument shape."""
        return f'agentic-sdlc {self.verb} {self.subject}'


def derive_next(cfg: model.PmConfig, kind: str, to: str) -> Next | None:
    """The belt this arrival hands to, and the checks it will ask — or None.
    Three runtime sources: `[pm.states.<kind>]`, `driver.step_names(<belt>)`
    (the project's list, not the shipped one) and `driver.SUBJECT`."""
    category = model.flow_of(cfg, kind).category(to)
    belt = (CLOSES.get(kind) if category == model.IN_PROGRESS
            else ABOVE.get(kind) if category == model.DONE_CATEGORY else None)
    if belt is None:
        return None
    from agentic_sdlc.repo.conveyor import driver
    try:
        checks = tuple(driver.step_names(belt))
    except Exception:  # noqa: BLE001
        # A breadcrumb is a courtesy on top of a write that already
        # happened: a `[<belt>] steps` that belt would refuse is its finding
        # to report when it runs, not this line's after the status is on disk.
        return None
    if not checks:
        return None
    verb = belt if belt == RELEASE_BELT else f'{driver.CLOSE_VERB} {belt}'
    return Next(belt=belt, verb=verb,
                subject=driver.SUBJECT.get(belt, (0, '', ''))[2], checks=checks)


# --- 4: the capability census -------------------------------------------------
@dataclass(frozen=True)
class Capability:
    """One declared capability and whether the file is there."""

    path: str
    why: str
    installed: bool

    @property
    def line(self) -> str:
        """`have:` is INVENTORY, never *"you should run it"*; a declared file
        that is absent gets a NAMED line rather than silence (rule 11)."""
        state = ('is installed' if self.installed
                 else 'is DECLARED and not installed')
        return f'have: {self.path} {state} — {self.why}'


def capabilities(cfg: model.PmConfig,
                 node: model.Arrival | None) -> list[Capability]:
    """Which installed files this arrival's declaration binds to it. The
    mapping is a DECLARATION and never a list in this package."""
    if node is None:
        return []
    return [Capability(path=path, why=why,
                       installed=(cfg.root / path).is_file())
            for path, why in node.have]


# --- the pressure line --------------------------------------------------------
def _carry(count: int) -> str:
    return 'carries' if count == 1 else 'carry'


def _ledgers(count: int) -> str:
    return 'ledger' if count == 1 else 'ledgers'


@dataclass(frozen=True)
class Census:
    """The tree's open work, every number derived and none of them a
    threshold: a ceiling on how long a grain may stay in flight would be this
    package having an opinion about somebody's week (rule 9)."""

    open_count: int
    oldest_id: str
    oldest_seconds: int | None
    unanswered: int
    no_record: int
    record_pool: int
    wip: int
    unreadable: int

    def __bool__(self) -> bool:
        return self.open_count > 0

    @property
    def line(self) -> str:
        """One line, and only when there is something to say."""
        # The CATEGORY word, not a literal: renaming a state does not rename
        # the three categories the reader asked the tree with.
        head = f'open: {self.open_count} {model.IN_PROGRESS}'
        if self.wip and self.open_count > self.wip:
            head += f', over the declared [pm] wip of {self.wip}'
        if self.oldest_id:
            head += (f', oldest {self.oldest_id} '
                     f'{ledger.human_duration(self.oldest_seconds)}')
        clauses = []
        if self.unanswered:
            clauses.append(f'{self.unanswered} of {self.open_count} '
                           f'{_carry(self.unanswered)} no disposition')
        if self.no_record:
            clauses.append(f'{self.no_record} of {self.record_pool} '
                           f'{_carry(self.no_record)} no {RECORD_FIELD} record')
        if self.unreadable:
            clauses.append(f'{self.unreadable} '
                           f'{_ledgers(self.unreadable)} could not be read, so '
                           f'the ages above are short by whatever is in them')
        return head + (' — ' + ', '.join(clauses) if clauses else '')


def _ledger_paths(cfg: model.PmConfig) -> list[Path]:
    """Every ledger a status row could be in — one per milestone plus the
    grainless one — read once each rather than once per grain."""
    paths = [ledger.grainless_path(cfg.roadmap)]
    for _mdir, mid in model.known_milestones(cfg):
        if mid:
            paths.append(ledger.ledger_for(cfg, mid))
    return list(dict.fromkeys(paths))


def _rows_by_grain(cfg: model.PmConfig) -> tuple[dict[str, list], int]:
    """`{grain id: its rows, oldest first}` and how many ledgers would not
    read. A damaged ledger is COUNTED and disclosed: an age computed over a
    file quietly dropped is rule 4's first sin."""
    out: dict[str, list] = {}
    unreadable = 0
    for path in _ledger_paths(cfg):
        try:
            rows = ledger.read_rows(path)
        except Exception:  # noqa: BLE001 — a count, never the exit code
            unreadable += 1
            continue
        for row in rows:
            gid = row.data.get('grain')
            if isinstance(gid, str) and gid:
                out.setdefault(gid, []).append(row)
    for rows in out.values():
        rows.sort(key=lambda r: str(r.data.get('ts') or ''))
    return out, unreadable


def _answered(rows: list, state: str) -> bool:
    """Did the LAST disposition row for this grain answer the state it is in?
    Asked of the STATE, because a grain that bounced back has arrived again
    and the question is asked again (D3)."""
    for row in reversed(rows):
        if not disposition_of(row.data) or row.data.get('state') != state:
            continue
        return row.data.get('answer') not in (ledger.NO_DISPOSITION, None)
    return False


def answered_at(cfg: model.PmConfig, gid: str, state: str) -> bool:
    """Did this grain's LAST disposition for `state` carry an answer? Asked
    on a NO-OP, where a fresh `none` would SHADOW the answer already given."""
    path = ledger.ledger_of_grain(cfg, gid)
    try:
        rows = ledger.read_rows(path) if path is not None else []
    except Exception:  # noqa: BLE001 — unreadable is not answered
        return False
    return _answered(sorted((r for r in rows if r.data.get('grain') == gid),
                            key=lambda r: str(r.data.get('ts') or '')), state)


def census(cfg: model.PmConfig, now: datetime | None = None) -> Census | None:
    """The whole tree's open work, or None when nothing is open — the WHOLE
    tree, because a grain nobody moves is otherwise silent forever."""
    if not cfg.pressure:
        return None
    grains = [g for g in model.grain_index(cfg).values()
              if g.kind in model.FLOW_KINDS
              and model.category_of(cfg, g.kind, g.status) == model.IN_PROGRESS]
    if not grains:
        return None
    rows, unreadable = _rows_by_grain(cfg)
    when = datetime.now(timezone.utc) if now is None else now
    oldest_id, oldest_seconds = '', None
    unanswered = no_record = record_pool = 0
    for grain in sorted(grains, key=lambda g: g.gid):
        status = [r for r in rows.get(grain.gid, ())
                  if r.data.get('kind') == ledger.KIND_STATUS]
        seconds = ledger.open_seconds(cfg, grain.kind, status, now=when)
        if seconds is not None and (oldest_seconds is None
                                    or seconds > oldest_seconds):
            oldest_id, oldest_seconds = grain.gid, seconds
        if not _answered(rows.get(grain.gid, ()), grain.status):
            unanswered += 1
        # The artifact a close requires is the pointer the grain's own
        # document carries; a grain with no such key is not counted.
        try:
            document = model.document(grain.path)
        except (OSError, UnicodeDecodeError):
            continue
        if RECORD_FIELD in document.fields:
            record_pool += 1
            if not document.field(RECORD_FIELD) or not model.record_resolves(
                    cfg.root / document.field(RECORD_FIELD)):
                no_record += 1
    return Census(open_count=len(grains), oldest_id=oldest_id,
                  oldest_seconds=oldest_seconds, unanswered=unanswered,
                  no_record=no_record, record_pool=record_pool, wip=cfg.wip,
                  unreadable=unreadable)


# --- the crossing -------------------------------------------------------------
def crossing(cfg: model.PmConfig, kind: str, gid: str) -> str:
    """'' unless this write made the grain's PARENT ready, else the line
    saying so and naming the belt that closes it. Derivable on the write that
    caused it, so READY stops being a question somebody must remember to ask
    (0.3.0 made it prose in a document instead)."""
    if not cfg.pressure:
        return ''
    grain = model.grain_index(cfg).get(gid)
    if grain is None or not grain.binding:
        return ''
    belt = ABOVE.get(kind)
    parent_kind = model.BINDS_TO.get(kind, ('', ''))[0]
    if belt is None or not parent_kind:
        return ''
    children = model.children(cfg, kind, grain.binding)
    if not children:
        return ''
    held = model.holds(cfg, kind, [(c.gid, c.status) for c in children],
                       model.DONE_CATEGORY)
    if not held:
        return ''
    from agentic_sdlc.repo.conveyor import driver
    verb = belt if belt == RELEASE_BELT else f'{driver.CLOSE_VERB} {belt}'
    subject = _subject_of(cfg, belt, grain.binding)
    return (f'ready: `agentic-sdlc {verb} {subject}` — this write made '
            f'{grain.binding} READY (every {kind} is in {model.DONE_CATEGORY}: '
            f'{held.counted} of {held.counted})')


def _subject_of(cfg: model.PmConfig, belt: str, parent_id: str) -> str:
    """The argument that belt takes for this parent — its id, or the VERSION
    the parent declares when the belt's own `SUBJECT` says it takes one."""
    from agentic_sdlc.repo.conveyor import driver
    noun = driver.SUBJECT.get(belt, (0, '', ''))
    if noun[1] != 'version':
        return parent_id
    return model.milestone_version(cfg, parent_id) or noun[2]


# --- the emitted row ----------------------------------------------------------
def emit_leave(cfg: model.PmConfig, row: dict) -> None:
    """Write the leave event, or nothing, and never change the answer. A tree
    with no `[emit]` opted out. Every failure is a finding on stderr, never
    the exit code: a code that moved because a SINK was unwritable would make
    every move unusable from a hook."""
    try:
        if emit.declared():
            emit.emit(cfg, emit.TAP_LEAVE, row)
    except Exception as err:  # noqa: BLE001 — a finding, never the answer
        print(f'{emit.FINDING_PREFIX} WARNING — the {emit.TAP_LEAVE} event for '
              f'{row.get("grain")} was not recorded ({type(err).__name__}: '
              f'{err}); the write itself landed', file=sys.stderr)


# --- the whole event ----------------------------------------------------------
def report(cfg: model.PmConfig, kind: str, gid: str, to: str,
           said: Said, answered: bool = False) -> dict:
    """Say what this arrival has to say, and hand back the row it emitted, in
    read order: what the belt asks, what is installed, the fork, then the
    tree. Nothing at all when there is nothing to say."""
    node = model.arrival_at(cfg, kind, to)
    nxt = derive_next(cfg, kind, to)
    have = capabilities(cfg, node)
    # `[pm] breadcrumbs = false` silences the PROSE only; the ROW carries the
    # same derivation either way.
    if cfg.breadcrumbs:
        if nxt is not None:
            _say(f'next: `{nxt.action}` asks {", ".join(nxt.checks)}')
        for capability in have:
            _say(capability.line)
    # Asking again for a disposition the census counts is the nag, not a fork.
    for line in ([] if answered else fork_lines(cfg, node, gid, said)):
        _say(line)
    crossed = crossing(cfg, kind, gid)
    if crossed:
        _say(crossed)
    open_work = census(cfg)
    if open_work:
        _say('')
        _say(open_work.line)
    return ledger.leave_row(gid, to, nxt, have, said)
