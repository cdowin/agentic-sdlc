"""arrive.py — ARRIVAL is the one event: a grain reaches a state (0.5.0/D3).

Everything a move says and writes is a reader of that one event, and all of it
is DERIVED from what the project declared:

    1  the status is written            `pm/cli.py`, unchanged
    2  the fork is asked                `[pm.arrive.<kind>.<state>]` ask/answers
    3  the disposition is recorded      one row, `none` when nobody answered
    4  the capability is named          `[pm.arrive.…] have`, as a CENSUS
    +  the tree's open work is reported the pressure line, silent when empty

**Direction is not modelled and there is no transition table.** The unit is the
state arrived at, never the pair `(from, to)`: `building -> planning` is an
arrival at `planning`, a second pass through a state asks the same question,
and backwards was never a special case. Rule 9 says the tool has no opinion
about which state may follow which — making arrival the unit means it never
needs one.

Nothing here decides, advises or refuses a move. `next:` is the belt's binding
check list; `have:` is inventory; `open:` is a census. *"You should close
something"* is an opinion and does not ship.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentic_sdlc.repo import emit
from agentic_sdlc.repo.pm import ledger, model

# --- the row kinds this event mints -------------------------------------------
# MINTED HERE AND NOT IN `ledger.py` ONLY BECAUSE THIS LANDED FIRST: both
# builders below are `ledger.status_row`-shaped and belong beside it, keyed the
# same way and routed by the same `ledger_of_grain`. See this module's report.
KIND_DISPOSITION = 'disposition'
# `<rung>.<edge>`, the spelling `ready_for.KIND_ENTER` already uses; the last
# dotted segment is the tap `check pm` reads off `emit.TAPS`.
KIND_LEAVE = 'rung.leave'

# What a row says when nobody answered. It can never collide with a declared
# answer, because `model._arrive_node_defect` refuses an answer that does not
# open with `--`. **A bare move still writes** — refusing would make the
# conveyor something people route around — but it is never invisible.
NO_DISPOSITION = 'none'

# Which belt closes a grain of each kind, and which belt the grain ABOVE it
# needs next. Both are `steps.registry_for` keys, and that is the whole of the
# mapping this module holds: the CHECKS each belt asks are read from the
# registry at runtime and never restated here, so a check added to a belt turns
# up in the breadcrumb without anybody remembering to add it.
CLOSES = {'story': 'story', 'feature': 'feature', 'milestone': 'release'}
# A milestone's `done` names nothing above it — there is no belt over a
# milestone, and inventing a sentence for that case would be the engine having
# an opinion about what somebody does after a release.
ABOVE = {'story': 'feature', 'feature': 'release'}

# The belt whose subject is a version rather than a grain id; its own `SUBJECT`
# entry says so, and `_subject_of` asks that entry rather than this name.
RELEASE_BELT = 'release'

# The frontmatter pointer a close stamps. A grain whose document carries the
# key is one whose close wants a record; a grain whose document does not is not
# counted for want of a field it never had.
RECORD_FIELD = 'reviewed'

PREFIX = '[pm]'


def _say(line: str) -> None:
    """One line of the event's report, on STDERR.

    STDOUT is what a consumer parses and it stays the one line the write wrote
    — 0.4.0 put the breadcrumb here for exactly that reason, and every line
    this module adds joins it.
    """
    print(f'{PREFIX} {line}' if line else PREFIX, file=sys.stderr)


# --- 2: the fork --------------------------------------------------------------
@dataclass(frozen=True)
class Said:
    """What the caller answered at an arrival, or nothing.

    `answer` is the declared flag (`--by`); `value` is the rest of the line as
    it was TYPED. The tool records a claim and never verifies it: `--by agent
    developer` is a fact about what was said, which is what an append-only log
    holds (rule 9).
    """

    answer: str = NO_DISPOSITION
    value: str = ''

    def __bool__(self) -> bool:
        return self.answer != NO_DISPOSITION


NOTHING = Said()


class Incomplete(Exception):
    """A declared answer typed without the rest of itself. Exit 2, by name."""


def take(node: model.Arrival | None,
         args: list[str]) -> tuple[Said, list[str]]:
    """Split a declared answer off the tail of `args`; `(NOTHING, args)` when
    the caller typed none, and everything before the flag is handed back.

    The flags come from the node's own `answers`, so a project declaring a
    different fork gets different flags with no edit here — and a state that
    declared no fork accepts nothing, which is how an undeclared flag stays the
    usage error it already was.
    """
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
        return Said(arg, value), list(args[:index])
    return NOTHING, list(args)


def unknown_flag_hint(node: model.Arrival | None) -> str:
    """What a state DOES accept, for the refusal a flag it does not gets.

    Rule 11: absence is a finding, never silence. A caller who typed the wrong
    flag is told the answers this arrival declares rather than that the flag is
    unknown, which is true and useless.
    """
    if node is None or not node.answers:
        return ''
    return (f' — arriving at {node.kind} {node.state} accepts '
            + ', '.join(repr(a) for a in node.answers))


def fork_lines(cfg: model.PmConfig, node: model.Arrival | None, gid: str,
               said: Said = NOTHING) -> list[str]:
    """The question and both answers, each a command that can be pasted.

    The command is the ARRIVAL itself: a move is idempotent, so re-running it
    with the answer records the disposition and writes nothing else. **The
    friction was never the review; it was that answering meant deciding what
    to type while something else was already running** — so the cheap answer
    costs one paste and so does the expensive one.

    A belt with nothing skippable prints ONE option, not a fake choice — which
    falls out of the declaration rather than being decided here. A move with no
    fork prints no question, and a move that ALREADY carries its answer prints
    none either: asking somebody what they just told you is the nag this is
    not.
    """
    if node is None or not node.ask or not cfg.pressure or said:
        return []
    move = f'agentic-sdlc pm {node.kind} {node.state} {gid}'
    lines = ['', node.ask]
    for index, answer in enumerate(node.answers):
        lines.append(f'  {chr(ord("a") + index)}) {move} {answer}')
    return lines


def disposition_row(grain_id: str, state: str, said: Said,
                    ts: str = '') -> dict:
    """One arrival's disposition — the STATE arrived at and the answer given.

    No `from`: direction is not modelled (D3), and time in a state is the gap
    between two arrivals on one grain. `answer` is always present, `none`
    included, so "nobody answered" and "a row written before this shipped" are
    different facts to every reader.
    """
    row = {'ts': ts or ledger.utc_now(), 'kind': KIND_DISPOSITION,
           'grain': grain_id, 'state': state, 'answer': said.answer}
    if said.value:
        row['value'] = said.value
    return row


# --- the ONE derivation, two renderers ----------------------------------------
@dataclass(frozen=True)
class Next:
    """What the conveyor asks next, derived once and rendered twice.

    The prose renderer (`pm/cli.py`'s breadcrumb) and the row renderer
    (`rung.leave`) both read THIS — two code paths computing "what comes next"
    is the drift V2 and path-as-schema were both killed for.
    """

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

    Three runtime sources and nothing else: `[pm.states.<kind>]` for the
    category, `driver.step_names(<belt>)` for the checks that belt will ask,
    and `driver.SUBJECT` for its argument. `step_names` and not `registry_for`,
    because the registry is what SHIPS and the belt runs `[<belt>] steps`.
    """
    category = model.flow_of(cfg, kind).category(to)
    belt = (CLOSES.get(kind) if category == model.IN_PROGRESS
            else ABOVE.get(kind) if category == model.DONE_CATEGORY else None)
    if belt is None:
        return None
    from agentic_sdlc.repo.conveyor import driver
    try:
        checks = tuple(driver.step_names(belt))
    except Exception:  # noqa: BLE001
        # A breadcrumb is a courtesy on top of a write that already happened.
        # A `[<belt>] steps` the belt itself would refuse is that belt's
        # finding to report when it runs, not this line's to raise after the
        # status is on disk.
        return None
    if not checks:
        return None
    verb = belt if belt == RELEASE_BELT else f'{driver.CLOSE_VERB} {belt}'
    return Next(belt=belt, verb=verb,
                subject=driver.SUBJECT.get(belt, (0, '', ''))[2], checks=checks)


# --- 4: the capability census -------------------------------------------------
@dataclass(frozen=True)
class Capability:
    """One declared capability and whether the file is actually there."""

    path: str
    why: str
    installed: bool

    @property
    def line(self) -> str:
        """`have:` is INVENTORY. *"You should run it"* is an opinion and must
        not ship; a declared file that is absent is a NAMED line rather than
        silence, because a capability declared and missing is a contradiction
        the tree is holding (rule 11)."""
        state = ('is installed' if self.installed
                 else 'is DECLARED and not installed')
        return f'have: {self.path} {state} — {self.why}'


def capabilities(cfg: model.PmConfig,
                 node: model.Arrival | None) -> list[Capability]:
    """Which installed files this arrival's declaration binds to it.

    Two facts the tree already holds — which files exist, and which state was
    arrived at. The mapping between them is a DECLARATION, never a list in this
    package, so a project that installs different tooling names its own.
    """
    if node is None:
        return []
    return [Capability(path=path, why=why,
                       installed=(cfg.root / path).is_file())
            for path, why in node.have]


# --- the pressure line --------------------------------------------------------
def _carry(count: int) -> str:
    return 'carries' if count == 1 else 'carry'


def _ledgers(count: int) -> str:
    return f'{ledger.LEDGER_FILE_NAME}' if count == 1 else 'ledgers'


@dataclass(frozen=True)
class Census:
    """The tree's open work, every number derived and none of them a threshold.

    No colour, no exit code, no refusal: a ceiling on how long a grain may stay
    in flight is this package having an opinion about somebody's week (rule 9).
    """

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
        head = f'open: {self.open_count} in_progress'
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
    """Every ledger a status row could be in: one per milestone, plus the
    grainless one. Read once each, rather than once per grain."""
    paths = [ledger.grainless_path(cfg.roadmap)]
    for _mdir, mid in model.known_milestones(cfg):
        if mid:
            paths.append(ledger.ledger_for(cfg, mid))
    return list(dict.fromkeys(paths))


def _rows_by_grain(cfg: model.PmConfig) -> tuple[dict[str, list], int]:
    """`{grain id: its rows, oldest first}` and how many ledgers would not read.

    A damaged ledger is COUNTED and disclosed, never skipped: a census that
    quietly dropped a file would report an age it cannot support, which is rule
    4's first sin (`check pm` is where a damaged ledger becomes a finding).
    """
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

    Asked of the state and not of a date, because a grain that bounced back has
    arrived again and the question is asked again — which is the whole of D3.
    """
    for row in reversed(rows):
        if row.data.get('kind') != KIND_DISPOSITION:
            continue
        if row.data.get('state') != state:
            continue
        return row.data.get('answer') not in (NO_DISPOSITION, None)
    return False


def census(cfg: model.PmConfig, now: datetime | None = None) -> Census | None:
    """The whole tree's open work, or None when nothing is open.

    Not the grain you named — the whole tree, because back-pressure is the idea
    of a conveyor and a grain nobody moves is otherwise silent forever.
    """
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
        # document carries; a grain whose frontmatter has no such key is not
        # counted for want of a field it never had.
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
    """'' unless this write made the grain's PARENT ready, else the line saying
    so and naming the belt that closes it.

    0.3.0 recorded *"dispatch a feature's review the moment `ready-for feature`
    goes READY"* and made it prose in a document. It is derivable, on the write
    that caused it: READY stops being a question somebody must remember to ask
    and becomes an event they are told about.
    """
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
def leave_row(grain_id: str, state: str, nxt: Next | None,
              have: list[Capability], said: Said, ts: str = '') -> dict:
    """The `rung.leave` payload: the same next-step facts the printed
    breadcrumb states, from the one derivation above.

    If this row wants a fact the printed line lacks, that fact is missing from
    `derive_next` and belongs there — where both renderers get it.
    """
    row = {'ts': ts or ledger.utc_now(), 'kind': KIND_LEAVE,
           'grain': grain_id, 'state': state, 'answer': said.answer,
           'rung': nxt.belt if nxt else '',
           'next_checks': list(nxt.checks) if nxt else [],
           'next_actions': [nxt.action] if nxt else [],
           'have': [{'path': c.path, 'why': c.why, 'installed': c.installed}
                    for c in have]}
    if said.value:
        row['value'] = said.value
    return row


def emit_leave(cfg: model.PmConfig, row: dict) -> None:
    """Write the leave event, or nothing, and never change the answer.

    A tree with no `[emit]` opted out and is owed no line. Every failure is a
    finding on stderr and never the exit code: the status is already on disk,
    and a code that moved because a SINK was unwritable would make every move
    unusable from a hook.
    """
    try:
        if emit.declared():
            emit.emit(cfg, emit.TAP_LEAVE, row)
    except Exception as err:  # noqa: BLE001 — a finding, never the answer
        print(f'{emit.FINDING_PREFIX} WARNING — the {emit.TAP_LEAVE} event for '
              f'{row.get("grain")} was not recorded ({type(err).__name__}: '
              f'{err}); the write itself landed', file=sys.stderr)


# --- the whole event ----------------------------------------------------------
def report(cfg: model.PmConfig, kind: str, gid: str, to: str,
           said: Said) -> dict:
    """Say what this arrival has to say, and hand back the row it emitted.

    Order is the read order: what the belt asks, what is installed, the fork,
    then the tree. Nothing at all when there is nothing to say.
    """
    node = model.arrival_at(cfg, kind, to)
    nxt = derive_next(cfg, kind, to)
    have = capabilities(cfg, node)
    # `[pm] breadcrumbs = false` silences the PROSE only. The ROW below carries
    # the same derivation either way, because it is not on the stream a strict
    # consumer parses.
    if cfg.breadcrumbs:
        if nxt is not None:
            _say(f'next: `{nxt.action}` asks {", ".join(nxt.checks)}')
        for capability in have:
            _say(capability.line)
    for line in fork_lines(cfg, node, gid, said):
        _say(line)
    crossed = crossing(cfg, kind, gid)
    if crossed:
        _say(crossed)
    open_work = census(cfg)
    if open_work:
        _say('')
        _say(open_work.line)
    return leave_row(gid, to, nxt, have, said)
