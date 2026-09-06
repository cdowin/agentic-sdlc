"""budget.py — a tier that got slower is a finding, not a mood.

**Why this gate exists, in one measurement.** This package spent a milestone
building a conveyor to end a 170x — a wide gate run in an inner loop — and its
own suite was the same defect one layer down: 1842 tests, 240 s of wall clock,
150 s of CPU inside it, and `make precommit` running every one of them after
every edit. The number had been MEASURED and written into CLAUDE.md
(*"~85% of this suite's wall clock is subprocess"*), and it was used to justify
skipping interpreters rather than to fix the spawns. Nobody was wrong; nothing
watched.

So this is rule 4 pointed at cost. A gate that misses real drift and prints
PASS is the read-side cardinal sin, and a test tier that doubles in wall clock
while every gate stays green is exactly that drift — it just degrades a human's
patience instead of a boolean, so it never trips anything.

## What it reads, and why it does not run anything

The ledger. Every `make` gate in this package's target set routes through
`gdk_gate_capture` / `gdk_gate_verdict`, which file a `gate` row carrying the
target's name, its verdict and its `duration_ms`. That is the measurement this
gate reports on — so it costs milliseconds, runs no suite, and cannot itself
become the thing it is warning about. A budget gate that ran the suite to time
the suite would be a fine joke and a bad gate.

It follows that this gate is **honest about not knowing**, three ways:

- A tier with no row in the ledger has not been run since the ledger was last
  rotated, and that is reported as `UNMEASURED` — never as zero, never as a
  pass. Hard rule 4's zero census, applied to a column of numbers instead of a
  column of files.
- A tier whose newest row did not end `PASS` is reported as `NOT GRADED`, and
  that IS a finding. A run that stopped is cheaper and smaller than a run that
  finished, so a failed run is the one most likely to sit comfortably under
  both ceilings — the gate would be at its most confident exactly where its
  input is least trustworthy. Its duration and census are the cost of a run
  that stopped, not measurements of the tier.
- The row it grades is the NEWEST BY TIMESTAMP, not the last in the file. The
  ledger is append-only from concurrent writers and is a committed file that
  gets merged, so file order is not age; a gate that graded the last line
  would report a number an arbitrary number of runs behind, chosen by file
  layout, with a confident `measured 10m ago` computed from the wrong row. A
  row whose `ts` will not parse is reported as a defect rather than ordered
  silently.

And the summary line names only what was measured. `PASS — 3 tier(s) within
their time budget` over one measured tier and two unmeasured ones is the line
a CI tail keeps, and it would be false.

## Why it ships OFF a ceiling

Hard rule 5: a GATE ships stock defaults, and a repo with no `devkit.toml` runs
every gate byte-identically to one declaring them. A stock ceiling cannot exist
here — "ten seconds" is a claim about a machine, and this package knows nothing
about its consumers (rule 8). A shipped number would redden every tree whose CI
runner is slower than the laptop it was picked on, which is milestone risk 2:
*a gate landing in the default roster reds every consumer at once.*

So with no `[tests]` ceiling declared it REPORTS the measured costs and exits 0.
It becomes a gate the moment a project names its own ceilings, which is the
`[gates] extra` posture one layer in: the mechanism is ours, the number is
theirs.

## Config

    [tests]
    budget = { unit = 15, integration = 120 }   # seconds, per tier
    cases  = { unit = 1250, integration = 800 } # case-count ceiling, per tier

`budget` holds a tier's wall clock. `cases` holds its SIZE — a tier can hold
its wall clock while doubling in case count, because parallelism and a faster
machine both absorb it.

The numbers come from the `gate` rows `make unit` / `make integration` /
`make test` already file in the building milestone's `ledger.jsonl` — this gate
runs nothing and measures nothing itself. A tier with no ceiling of any kind is
REPORTED and never failed.

Exit codes: 0 nothing over its ceiling and every declared tier's newest run
ended PASS, 1 a tier is over or not graded, 2 usage or config.
"""
from __future__ import annotations

from datetime import datetime, timezone


from agentic_sdlc.core.config import ConfigError, config_section, number_table
from agentic_sdlc.repo.pm import ledger, model

NAME = 'budget'

# The verdict a row must carry to be a measurement of its tier. `HANG`, `SKIP`
# and `FAIL` are all runs that did not finish the work the tier exists to do,
# and `ledger.GATE_VERDICTS` says why the vocabulary is closed.
GRADED_VERDICT = 'PASS'


def _positive_table(key: str, why: str) -> dict[str, int]:
    """`[tests] <key>`, in whole units per tier, or {} — refusing zero or less."""
    section = config_section('tests')
    raw = number_table(section, 'tests', key, {})
    for tier, value in raw.items():
        if value <= 0:
            raise ConfigError(f'[tests] {key}.{tier} is {value} — {why} '
                              f'Remove the entry to stop holding it.')
    return raw


def _census_ceilings() -> dict[str, int]:
    """`[tests] cases`, in whole test cases per tier, or {}.

    THE SECOND CEILING, and it measures the thing a duration cannot. A tier can
    hold its wall clock while doubling in size — parallelism and faster
    machines both hide growth — and the number that then goes wrong is not the
    gate's, it is the reader's: 1,478 test functions over 7,241 statements of
    source, one per 4.9, arrived at without any single addition being
    unreasonable.

    Rule 4's census, pointed at the suite's own size. Same posture as the
    duration ceiling: no stock value, because how many cases a project needs is
    the project's business, and a shipped number would be this package having
    an opinion about somebody else's tree (rule 8).
    """
    return _positive_table(
        'cases', 'a tier allowed zero cases is a tier that proves nothing.')


def _budgets() -> dict[str, int]:
    """`[tests] budget`, in whole seconds, or {}.

    Seconds rather than the row's own milliseconds, because a human types a
    ceiling and nobody types 15000. The comparison converts once, here, so the
    unit a project writes and the unit the ledger holds meet in one place.
    """
    return _positive_table(
        'budget', 'a ceiling of zero or less is not a budget, it is a tier '
        'that may never run.')


def _rows() -> tuple[list[tuple[str, ledger.Row]], str]:
    """Every row of every building milestone's ledger, or the defect that stopped
    the read — one walk, so the three readers below cannot disagree.

    `building_milestones` yields (id, branch, milestone.md) — the DIRECTORY is
    the file's parent, and the ledger sits beside it. Asked of the model rather
    than joined by hand: `ledger_path` is the one place that name is built, and
    a second spelling here would be a second answer to where a ledger lives.
    """
    cfg = model.load()
    out: list[tuple[str, ledger.Row]] = []
    for _mid, _branch, mfile in model.building_milestones(cfg):
        path = ledger.ledger_path(mfile.parent)
        if not path.is_file():
            continue
        try:
            rows = ledger.read_rows(path)
        except ledger.LedgerError as err:
            return [], f'{cfg.rel(path)} could not be read: {err}'
        out.extend((cfg.rel(path), row) for row in rows)
    return out, ''


def _by_name(rows: list[tuple[str, ledger.Row]], kind: str,
             key: str) -> tuple[dict[str, list[dict]], str]:
    """{name: rows of `kind` carrying it under `key`}, OLDEST FIRST BY TIMESTAMP.

    File order is not age. The ledger is append-only from concurrent writers
    and is a committed file that gets merged, so the last line for a tier can
    be a run from eight minutes before the newest one — and the age this gate
    prints is computed from the row it picks, so a gate that graded the last
    line would certify the stale number instead of catching it. The sort is
    stable, so rows with one timestamp keep their file order.

    A row of this kind whose `ts` will not parse is a DEFECT, returned rather
    than ordered silently: a row this gate cannot place in time is a row it
    cannot call newest or oldest, and guessing is the read-side sin.
    """
    found: dict[str, list[tuple[datetime, dict]]] = {}
    for where, row in rows:
        data = row.data
        if data.get('kind') != kind:
            continue
        name = data.get(key)
        if not isinstance(name, str):
            continue
        when = ledger.parse_ts(data.get('ts'))
        if when is None:
            return {}, (f'{where} line {row.lineno} is a `{kind}` row for '
                        f'`{name}` whose ts {data.get("ts")!r} is not a '
                        f'timestamp, so its newest row cannot be chosen')
        found.setdefault(name, []).append((when, data))
    return {name: [data for _when, data in sorted(pairs, key=lambda p: p[0])]
            for name, pairs in found.items()}, ''


def _age(stamp: object) -> str:
    """How long ago that row was filed, in words, or '' when it cannot say.

    **The staleness is the honest half of this gate.** It grades a MEASUREMENT
    rather than taking one, so a tier's number is only as current as the last
    time somebody ran that tier — and a ceiling reported against a row from
    last week is a ceiling reported against last week's code. Saying the age
    out loud is what stops "ok, 7.2s of 20s" reading as a fact about the tree
    in front of you.
    """
    when = ledger.parse_ts(stamp)
    if when is None:
        return ''
    seconds = (datetime.now(timezone.utc) - when).total_seconds()
    if seconds < 0:
        return 'timestamped in the future'
    for size, unit in ((86400, 'd'), (3600, 'h'), (60, 'm')):
        if seconds >= size:
            return f'{int(seconds // size)}{unit} ago'
    return 'just now'


def _slowest(rows: list[tuple[str, ledger.Row]]
             ) -> tuple[dict[str, tuple[str, int]], str]:
    """{tier: (nodeid, duration_ms)} — the rank-1 `test` row of the newest run.

    The `gate` row says a tier got slower; this says WHICH CASE, which is the
    half you can act on. `tests/conftest.py` files the slowest few of every
    gated run, and rank 1 is the one worth printing beside a ceiling.
    """
    tests, defect = _by_name(rows, ledger.KIND_TEST, 'tier')
    if defect:
        return {}, defect
    out: dict[str, tuple[str, int]] = {}
    for tier, ordered in tests.items():
        for data in reversed(ordered):
            node, ms = data.get('nodeid'), data.get('duration_ms')
            if data.get('rank') == 1 and isinstance(node, str) \
                    and isinstance(ms, int):
                out[tier] = (node, ms)
                break
    return out, ''


def run() -> int:
    # No argv: `cli._run_check_inner` serves `--help` from this module's
    # docstring and refuses an unknown flag before dispatch, so every gate here
    # takes nothing. The docstring is what `check budget --help` prints.
    budgets = _budgets()
    ceilings = _census_ceilings()
    rows, defect = _rows()
    gates, defect = _by_name(rows, ledger.KIND_GATE, 'gate') \
        if not defect else ({}, defect)
    if defect:
        print(f'[check:{NAME}] FAIL — {defect}')
        return 1
    newest = {name: ordered[-1] for name, ordered in gates.items()}

    if not budgets and not ceilings:
        # Rule 5, and rule 4's census in the same line: no ceiling is declared,
        # so nothing can fail — but what WAS measured is printed, because a
        # gate that passes in silence has told a reader nothing about the tree.
        # A run that did not end PASS says so beside its number.
        measured = []
        for name, data in sorted(newest.items()):
            ms = data.get('duration_ms')
            if not isinstance(ms, int):
                continue
            notes = [n for n in (
                '' if data.get('verdict') == GRADED_VERDICT
                else str(data.get('verdict') or 'no verdict'),
                _age(data.get('ts'))) if n]
            note = f' ({", ".join(notes)})' if notes else ''
            measured.append(f'{name} {ms / 1000:.1f}s{note}')
        print(f'[check:{NAME}] PASS — no [tests] budget is declared, so no '
              f'tier has a ceiling; last measured: '
              f'{", ".join(measured) or "nothing yet"}')
        return 0

    slowest, defect = _slowest(rows)
    if defect:
        print(f'[check:{NAME}] FAIL — {defect}')
        return 1
    counted_tiers = sorted(ceilings)
    over: list[str] = []
    ungraded: list[str] = []
    unmeasured: list[str] = []
    uncounted: list[str] = []
    ok_time: list[str] = []
    ok_count: list[str] = []
    lines: list[str] = []

    # A tier whose newest run did not end PASS is said ONCE, before either
    # column, and neither column grades it: its duration is the cost of a run
    # that stopped, and its census is the part of the tier that ran.
    for tier in sorted(set(budgets) | set(counted_tiers)):
        data = newest.get(tier)
        if data is None or data.get('verdict') == GRADED_VERDICT:
            continue
        verdict = str(data.get('verdict') or 'no verdict')
        ms = data.get('duration_ms')
        cost = f' at {ms / 1000:.1f}s' if isinstance(ms, int) else ''
        age = _age(data.get('ts'))
        when = f', measured {age}' if age else ''
        ungraded.append(f'{tier} ({verdict})')
        lines.append(f'  NOT GRADED  {tier} — newest run ended {verdict}'
                     f'{cost}{when}; a run that did not finish is not a '
                     f'measurement of the tier; run `make {tier}`')

    for tier in sorted(budgets):
        ceiling = budgets[tier]
        data = newest.get(tier)
        if data is None:
            # NOT a pass. A tier nobody ran is a tier nobody measured, and
            # reporting it as under budget is the zero census in a stopwatch.
            unmeasured.append(tier)
            lines.append(f'  UNMEASURED  {tier} — ceiling {ceiling}s, and no '
                         f'`gate` row for it in this milestone\'s ledger; run '
                         f'`make {tier}`')
            continue
        if data.get('verdict') != GRADED_VERDICT:
            continue
        ms = data.get('duration_ms')
        if not isinstance(ms, int):
            unmeasured.append(tier)
            lines.append(f'  UNMEASURED  {tier} — ceiling {ceiling}s, and its '
                         f'newest `gate` row carries duration_ms {ms!r}, '
                         f'which is not a number of milliseconds')
            continue
        seconds = ms / 1000
        age = _age(data.get('ts'))
        when = f', measured {age}' if age else ''
        if seconds > ceiling:
            over.append(tier)
            lines.append(f'  OVER BUDGET {tier} — {seconds:.1f}s against a '
                         f'{ceiling}s ceiling ({seconds - ceiling:+.1f}s), '
                         f'verdict {GRADED_VERDICT}{when}')
        else:
            ok_time.append(tier)
            lines.append(
                f'  ok          {tier} — {seconds:.1f}s of {ceiling}s{when}')

    for tier in counted_tiers:
        ceiling = ceilings[tier]
        limit = f'ceiling {ceiling} case(s)'
        data = newest.get(tier)
        count = data.get('census') if data is not None else None
        if data is None or (data.get('verdict') == GRADED_VERDICT
                            and not isinstance(count, int)):
            uncounted.append(tier)
            lines.append(f'  UNCOUNTED   {tier} — {limit}, and '
                         + ('no `gate` row for it in this milestone\'s ledger'
                            if data is None else
                            'its newest `gate` row carries no census'))
            continue
        if data.get('verdict') != GRADED_VERDICT:
            continue
        if count > ceiling:
            over.append(f'{tier} (cases)')
            lines.append(f'  OVER COUNT  {tier} — {count} case(s) against a '
                         f'{ceiling} ceiling ({count - ceiling:+d}). A tier '
                         f'can hold its wall clock while doubling in size.')
        else:
            ok_count.append(tier)
            lines.append(f'  ok          {tier} — {count} of {ceiling} case(s)')

    for line in lines:
        print(line)
    for tier in sorted(budgets):
        worst = slowest.get(tier)
        if worst:
            nodeid, ms = worst
            print(f'  slowest    {tier} — {ms / 1000:.1f}s  {nodeid}')

    if over or ungraded:
        parts = []
        if over:
            parts.append(f'{len(over)} tier(s) over budget: {", ".join(over)}')
        if ungraded:
            parts.append(f'{len(ungraded)} tier(s) not graded: '
                         f'{", ".join(ungraded)}')
        why = ('A tier that got slower is a finding: it degrades a human\'s '
               'patience instead of a boolean, so nothing else in this gate '
               'set will ever notice.' if over else
               'A run that did not finish is not a measurement, and grading '
               'it would be printing PASS over what was not measured.')
        print(f'[check:{NAME}] FAIL — {"; ".join(parts)}. {why}')
        return 1

    # The summary names what was MEASURED and says what was not, because this
    # is the line a CI tail keeps, and "3 tier(s) within their time budget"
    # over one measured tier is the read-side sin in the one line that
    # survives summarising.
    parts = []
    if budgets:
        parts.append('within their time budget: '
                     + (', '.join(ok_time) or 'none measured'))
    if counted_tiers:
        parts.append('within their case limits: '
                     + (', '.join(ok_count) or 'none counted'))
    if unmeasured:
        parts.append(f'unmeasured: {", ".join(unmeasured)}')
    if uncounted:
        parts.append(f'uncounted: {", ".join(uncounted)}')
    print(f'[check:{NAME}] PASS — {"; ".join(parts)}')
    return 0
