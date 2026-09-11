"""check budget — a tier that got slower, grew, or shrank is a finding.

Reads the `gate` rows `make unit` / `make integration` / `make test` file in the
current release's ledger; runs nothing. The newest row by timestamp is graded.

The two ways of not knowing are NOT the same finding. A tier whose newest run
did not end PASS is NOT GRADED and that IS a finding — a run that stopped is
cheaper and smaller than one that finished, so its numbers measure the stop. A
tier with no row is UNMEASURED: named, never counted as within its ceiling, and
NOT a finding, because a tier nobody ran has not got slower. Ships no ceiling (a
number is the project's), so with nothing declared it reports and exits 0.

**That reason is about the CLOCK and does not carry to the COUNT.** A case count
is a fact about the source, so a tier nobody ran can still have grown past its
`[tests] cases` entry — which is how this repo's own integration tier sat two
over its ceiling across a release with the gate green. A declared case limit
with no count is therefore UNCOUNTED and a FINDING, while a declared time budget
with no run stays merely unmeasured. Whatever grades a case limit must also
MEASURE it: a milestone gate that runs `matrix` files a `matrix` row and no
per-tier census, so the tiers it grades belong in its own tier list.

    [tests]
    budget = { unit = 15, integration = 120 }   # seconds, per tier
    cases  = { unit = 1250, integration = 800 } # case-count ceiling, per tier
    floor  = { unit = 1000, integration = 600 } # case-count floor, per tier

Exit codes: 0 nothing is over its ceiling or under its floor, and a declared time
budget with no row is reported as unmeasured; 1 a tier is over, under its floor,
not graded, or carries a declared case limit with no count; 2 usage or config.
"""
from __future__ import annotations

from datetime import datetime, timezone


from agentic_sdlc.core.config import ConfigError, config_section, number_table
from agentic_sdlc.repo.pm import ledger, vocabulary

NAME = 'budget'

# Every duration this gate is handed is milliseconds; every one it PRINTS is
# seconds, because that is the unit the ladder's costs are talked about in.
MS_PER_SECOND = 1000

# Only a finished run measures its tier; `ledger.GATE_VERDICTS` closes the vocabulary.
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
    """`[tests] cases`, per tier, or {}; a tier can hold its wall clock while doubling in size."""
    return _positive_table(
        'cases', 'a tier allowed zero cases is a tier that proves nothing.')


def _census_floors(ceilings: dict[str, int]) -> dict[str, int]:
    """`[tests] floor`, per tier, or {}; a floor above its ceiling is refused."""
    floors = _positive_table(
        'floor', 'a floor of zero or less holds nothing.')
    for tier, floor in floors.items():
        if tier in ceilings and floor > ceilings[tier]:
            raise ConfigError(
                f'[tests] floor.{tier} is {floor}, above cases.{tier} '
                f'({ceilings[tier]}) — no census can satisfy both.')
    return floors


def _budgets() -> dict[str, int]:
    """`[tests] budget`, in whole seconds (nobody types 15000), or {}."""
    return _positive_table(
        'budget', 'a ceiling of zero or less is not a budget, it is a tier '
        'that may never run.')


def _rows() -> tuple[list[tuple[str, ledger.Row]], str]:
    """Every row of the current release's ledger, or the defect that stopped the read."""
    cfg = vocabulary.load()
    path = ledger.grainless_path(cfg.roadmap)
    if not path.is_file():
        return [], ''
    try:
        rows = ledger.read_rows(path)
    except ledger.LedgerError as err:
        return [], f'{cfg.rel(path)} could not be read: {err}'
    return [(cfg.rel(path), row) for row in rows], ''


def _by_name(rows: list[tuple[str, ledger.Row]], kind: str,
             key: str) -> tuple[dict[str, list[dict]], str]:
    """{name: rows of `kind` carrying it under `key`}, oldest first by timestamp.

    File order is not age (concurrent appends, merged files); an unparseable `ts` is a defect.
    """
    found: dict[str, list[tuple[datetime, dict]]] = {}
    for where, row in rows:
        data = row.data
        if data.get(ledger.KIND_FIELD) != kind:
            continue
        name = data.get(key)
        if not isinstance(name, str):
            continue
        when = ledger.parse_ts(data.get(ledger.TS_FIELD))
        if when is None:
            return {}, (f'{where} line {row.lineno} is a `{kind}` row for '
                        f'`{name}` whose ts {data.get(ledger.TS_FIELD)!r} is not a '
                        f'timestamp, so its newest row cannot be chosen')
        found.setdefault(name, []).append((when, data))
    return {name: [data for _when, data in sorted(pairs, key=lambda p: p[0])]
            for name, pairs in found.items()}, ''


def _age(stamp: object) -> str:
    """How long ago that row was filed, in words, or '' when it cannot say."""
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
    """{tier: (nodeid, duration_ms)}: the rank-1 `test` row of the newest run."""
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


def _delta(newest: dict, ordered: list[dict]) -> str:
    """', N fewer than the run before (M)', or '' when there is no graded run before."""
    census = newest.get('census')
    for data in reversed(ordered):
        if data is newest or data.get('verdict') != GRADED_VERDICT:
            continue
        before = data.get('census')
        if isinstance(before, int) and isinstance(census, int):
            if census == before:
                return ''
            word = 'fewer' if census < before else 'more'
            return f', {abs(census - before)} {word} than the run before ({before})'
        return ''
    return ''


def run() -> int:
    budgets = _budgets()
    ceilings = _census_ceilings()
    floors = _census_floors(ceilings)
    rows, defect = _rows()
    gates, defect = _by_name(rows, ledger.KIND_GATE, 'gate') \
        if not defect else ({}, defect)
    if defect:
        print(f'[check:{NAME}] FAIL — {defect}')
        return 1
    newest = {name: ordered[-1] for name, ordered in gates.items()}

    if not budgets and not ceilings and not floors:
        # Nothing can fail, but what was measured is still printed.
        measured = []
        for name, data in sorted(newest.items()):
            ms = data.get('duration_ms')
            if not isinstance(ms, int):
                continue
            notes = [n for n in (
                '' if data.get('verdict') == GRADED_VERDICT
                else str(data.get('verdict') or 'no verdict'),
                _age(data.get(ledger.TS_FIELD))) if n]
            note = f' ({", ".join(notes)})' if notes else ''
            measured.append(f'{name} {ms / MS_PER_SECOND:.1f}s{note}')
        print(f'[check:{NAME}] PASS — no [tests] budget is declared, so no '
              f'tier has a ceiling; last measured: '
              f'{", ".join(measured) or "nothing yet"}')
        return 0

    slowest, defect = _slowest(rows)
    if defect:
        print(f'[check:{NAME}] FAIL — {defect}')
        return 1
    # Rule 4's zero census, and the one case that is NOT the per-tier
    # UNMEASURED above: ceilings are declared and there is not a single `gate`
    # row to grade any of them against. The gate would print PASS having
    # measured nothing at all, which is the sin the rule names. A tier that has
    # not run yet is a fact; a gate with NOTHING to read is a gate that cannot
    # answer, and it says so.
    if not gates:
        print(f'[check:{NAME}] FAIL — [tests] budget declares '
              f'{len(set(ceilings) | set(floors) | set(budgets))} '
              f'ceiling(s)/floor(s)/budget(s) and the '
              f'current release\'s ledger holds no `gate` row at all, so '
              f'nothing was graded. A verdict over an empty census is the one '
              f'this package refuses to print (CLAUDE.md rule 4). Run a gated '
              f'tier, or remove [tests] budget if this project does not grade '
              f'its own cost')
        return 1
    counted_tiers = sorted(set(ceilings) | set(floors))
    over: list[str] = []
    ungraded: list[str] = []
    unmeasured: list[str] = []
    uncounted: list[str] = []
    ok_time: list[str] = []
    ok_count: list[str] = []
    lines: list[str] = []

    # An ungraded tier is said once, before either column, and neither grades it.
    for tier in sorted(set(budgets) | set(counted_tiers)):
        data = newest.get(tier)
        if data is None or data.get('verdict') == GRADED_VERDICT:
            continue
        verdict = str(data.get('verdict') or 'no verdict')
        ms = data.get('duration_ms')
        cost = f' at {ms / MS_PER_SECOND:.1f}s' if isinstance(ms, int) else ''
        age = _age(data.get(ledger.TS_FIELD))
        when = f', measured {age}' if age else ''
        ungraded.append(f'{tier} ({verdict})')
        lines.append(f'  NOT GRADED  {tier} — newest run ended {verdict}'
                     f'{cost}{when}; a run that did not finish is not a '
                     f'measurement of the tier; run `make {tier}`')

    for tier in sorted(budgets):
        ceiling = budgets[tier]
        data = newest.get(tier)
        if data is None:
            unmeasured.append(tier)
            lines.append(f'  UNMEASURED  {tier} — ceiling {ceiling}s, and no '
                         f'`gate` row for it in this tree\'s ledger; run '
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
        seconds = ms / MS_PER_SECOND
        age = _age(data.get(ledger.TS_FIELD))
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
        ceiling, floor = ceilings.get(tier), floors.get(tier)
        limit = (f'ceiling {ceiling} case(s)' if ceiling is not None
                 else f'floor {floor} case(s)')
        data = newest.get(tier)
        count = data.get('census') if data is not None else None
        if data is None or (data.get('verdict') == GRADED_VERDICT
                            and not isinstance(count, int)):
            uncounted.append(tier)
            lines.append(
                f'  UNCOUNTED   {tier} — {limit}, and '
                + ('no `gate` row for it in this tree\'s ledger'
                   if data is None else
                   'its newest `gate` row carries no census')
                + '. A case COUNT is a fact about the source, not about a '
                  'run, so a tier nobody ran can still have grown past this '
                  'number — run the tier, or drop its `[tests] cases` entry')
            continue
        if data.get('verdict') != GRADED_VERDICT:
            continue
        delta = _delta(data, gates[tier])
        if ceiling is not None and count > ceiling:
            over.append(f'{tier} (cases)')
            lines.append(f'  OVER COUNT  {tier} — {count} case(s) against a '
                         f'{ceiling} ceiling ({count - ceiling:+d}){delta}. A '
                         f'tier can hold its wall clock while doubling in size.')
        elif floor is not None and count < floor:
            over.append(f'{tier} (cases)')
            lines.append(f'  UNDER FLOOR {tier} — {count} case(s) against a '
                         f'{floor} floor ({count - floor:+d}){delta}. A test '
                         f'deleted because it was slow is the sin this gate '
                         f'exists to prevent.')
        else:
            ok_count.append(tier)
            band = (f'{count} of {ceiling} case(s)' if ceiling is not None
                    else f'{count} case(s)')
            if floor is not None:
                band += f', floor {floor}'
            lines.append(f'  ok          {tier} — {band}{delta}')

    for line in lines:
        print(line)
    for tier in sorted(budgets):
        worst = slowest.get(tier)
        if worst:
            nodeid, ms = worst
            print(f'  slowest    {tier} — {ms / MS_PER_SECOND:.1f}s  {nodeid}')

    if over or ungraded or uncounted:
        parts = []
        if over:
            parts.append(f'{len(over)} tier(s) over budget: {", ".join(over)}')
        if ungraded:
            parts.append(f'{len(ungraded)} tier(s) not graded: '
                         f'{", ".join(ungraded)}')
        if uncounted:
            parts.append(f'{len(uncounted)} tier(s) with a declared case '
                         f'limit and no count: {", ".join(uncounted)}')
        why = ('A tier that got slower is a finding: it degrades a human\'s '
               'patience instead of a boolean, so nothing else in this gate '
               'set will ever notice.' if over else
               'A declared case limit nobody measured is the census failing '
               'open: the count moves when the SOURCE moves, so silence here '
               'is a PASS over a number that was never read (rule 4).'
               if uncounted and not ungraded else
               'A run that did not finish is not a measurement, and grading '
               'it would be printing PASS over what was not measured.')
        print(f'[check:{NAME}] FAIL — {"; ".join(parts)}. {why}')
        return 1

    # The summary names only what was measured; it is the line a CI tail keeps.
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
