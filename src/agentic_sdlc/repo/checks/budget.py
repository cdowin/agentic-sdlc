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

It follows that this gate is **honest about not knowing**. A tier with no row
in the ledger has not been run since the ledger was last rotated, and that is
reported as `unmeasured` — never as zero, never as a pass. Hard rule 4's zero
census, applied to a column of numbers instead of a column of files.

## Why it ships OFF a ceiling

Hard rule 5: a GATE ships stock defaults, and a repo with no `devkit.toml` runs
every gate byte-identically to one declaring them. A stock ceiling cannot exist
here — "ten seconds" is a claim about a machine, and this package knows nothing
about its consumers (rule 8). A shipped number would redden every tree whose CI
runner is slower than the laptop it was picked on, which is milestone risk 2:
*a gate landing in the default roster reds every consumer at once.*

So with no `[tests] budget` declared it REPORTS the measured costs and exits 0.
It becomes a gate the moment a project names its own ceilings, which is the
`[gates] extra` posture one layer in: the mechanism is ours, the number is
theirs.

## Config

    [tests]
    budget = { unit = 15, integration = 120 }   # seconds, per tier

The numbers come from the `gate` rows `make unit` / `make integration` /
`make test` already file in the building milestone's `ledger.jsonl` — this gate
runs nothing and measures nothing itself.

A tier with no ceiling is REPORTED and never failed. A tier with no ROW is
reported as unmeasured, which is not a pass: a gate that has not run has not
told you anything.

Exit codes: 0 nothing over its ceiling, 1 a tier is over, 2 usage or config.
"""
from __future__ import annotations

from datetime import datetime, timezone


from agentic_sdlc.core.config import ConfigError, config_section, number_table
from agentic_sdlc.repo.pm import ledger, model

NAME = 'budget'



def _budgets() -> dict[str, int]:
    """`[tests] budget`, in whole seconds, or {}.

    Seconds rather than the row's own milliseconds, because a human types a
    ceiling and nobody types 15000. The comparison converts once, here, so the
    unit a project writes and the unit the ledger holds meet in one place.
    """
    section = config_section('tests')
    raw = number_table(section, 'tests', 'budget', {})
    for tier, ceiling in raw.items():
        if ceiling <= 0:
            raise ConfigError(
                f'[tests] budget.{tier} is {ceiling} — a ceiling of zero or '
                f'less is not a budget, it is a tier that may never run. '
                f'Remove the entry to stop measuring it.')
    return raw


def _last_costs() -> tuple[dict[str, tuple[int, str, str]], str]:
    """{target: (duration_ms, verdict, ts)} from the newest `gate` row for each.

    Newest WINS rather than an average, and the reason is what this gate is
    for: an average hides the run that got slower behind the ten that did not,
    and the question here is "what does it cost now".
    """
    cfg = model.load()
    out: dict[str, tuple[int, str, str]] = {}
    # `building_milestones` yields (id, branch, milestone.md) — the DIRECTORY
    # is the file's parent, and the ledger sits beside it. Asked of the model
    # rather than joined by hand: `ledger_path` is the one place that name is
    # built, and a second spelling here would be a second answer to where a
    # ledger lives.
    for _mid, _branch, mfile in model.building_milestones(cfg):
        path = ledger.ledger_path(mfile.parent)
        if not path.is_file():
            continue
        try:
            rows = ledger.read_rows(path)
        except ledger.LedgerError as err:
            return {}, f'{cfg.rel(path)} could not be read: {err}'
        for row in rows:
            data = row.data
            if data.get('kind') != ledger.KIND_GATE:
                continue
            name, ms = data.get('gate'), data.get('duration_ms')
            if isinstance(name, str) and isinstance(ms, int):
                out[name] = (ms, str(data.get('verdict', '')),
                             str(data.get('ts', '')))
    return out, ''


def _age(stamp: str) -> str:
    """How long ago that row was filed, in words, or '' when it cannot say.

    **The staleness is the honest half of this gate.** It grades a MEASUREMENT
    rather than taking one, so a tier's number is only as current as the last
    time somebody ran that tier — and a ceiling reported against a row from
    last week is a ceiling reported against last week's code. Saying the age
    out loud is what stops "ok, 7.2s of 20s" reading as a fact about the tree
    in front of you.
    """
    if not stamp:
        return ''
    try:
        when = datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=timezone.utc)
    except ValueError:
        return ''
    seconds = (datetime.now(timezone.utc) - when).total_seconds()
    if seconds < 0:
        return 'timestamped in the future'
    for size, unit in ((86400, 'd'), (3600, 'h'), (60, 'm')):
        if seconds >= size:
            return f'{int(seconds // size)}{unit} ago'
    return 'just now'


def _slowest() -> dict[str, tuple[str, int]]:
    """{tier: (nodeid, duration_ms)} — the rank-1 `test` row of the last run.

    The `gate` row says a tier got slower; this says WHICH CASE, which is the
    half you can act on. `tests/conftest.py` files the slowest few of every
    gated run, and rank 1 is the one worth printing beside a ceiling.
    """
    cfg = model.load()
    out: dict[str, tuple[str, int]] = {}
    for _mid, _branch, mfile in model.building_milestones(cfg):
        path = ledger.ledger_path(mfile.parent)
        if not path.is_file():
            continue
        try:
            rows = ledger.read_rows(path)
        except ledger.LedgerError:
            return {}
        for row in rows:
            data = row.data
            if data.get('kind') != ledger.KIND_TEST or data.get('rank') != 1:
                continue
            tier, node = data.get('tier'), data.get('nodeid')
            ms = data.get('duration_ms')
            if isinstance(tier, str) and isinstance(node, str) \
                    and isinstance(ms, int):
                out[tier] = (node, ms)
    return out


def run() -> int:
    # No argv: `cli._run_check_inner` serves `--help` from this module's
    # docstring and refuses an unknown flag before dispatch, so every gate here
    # takes nothing. `USAGE` above is the config contract in prose; the
    # docstring is what `check budget --help` prints.
    budgets = _budgets()
    costs, defect = _last_costs()
    if defect:
        print(f'[check:{NAME}] FAIL — {defect}')
        return 1

    if not budgets:
        # Rule 5, and rule 4's census in the same line: no ceiling is declared,
        # so nothing can fail — but what WAS measured is printed, because a
        # gate that passes in silence has told a reader nothing about the tree.
        measured = ', '.join(
            f'{n} {v[0] / 1000:.1f}s{f" ({_age(v[2])})" if _age(v[2]) else ""}'
            for n, v in sorted(costs.items()))
        print(f'[check:{NAME}] PASS — no [tests] budget is declared, so no '
              f'tier has a ceiling; last measured: {measured or "nothing yet"}')
        return 0

    slowest = _slowest()
    over: list[str] = []
    lines: list[str] = []
    for tier in sorted(budgets):
        ceiling = budgets[tier]
        if tier not in costs:
            # NOT a pass. A tier nobody ran is a tier nobody measured, and
            # reporting it as under budget is the zero census in a stopwatch.
            lines.append(f'  UNMEASURED  {tier} — ceiling {ceiling}s, and no '
                         f'`gate` row for it in this milestone\'s ledger; run '
                         f'`make {tier}`')
            continue
        ms, verdict, stamp = costs[tier]
        seconds = ms / 1000
        age = _age(stamp)
        when = f', measured {age}' if age else ''
        if seconds > ceiling:
            over.append(tier)
            lines.append(f'  OVER BUDGET {tier} — {seconds:.1f}s against a '
                         f'{ceiling}s ceiling ({seconds - ceiling:+.1f}s), '
                         f'verdict {verdict or "unknown"}{when}')
        else:
            lines.append(
                f'  ok          {tier} — {seconds:.1f}s of {ceiling}s{when}')
    for line in lines:
        print(line)
    for tier in sorted(budgets):
        worst = slowest.get(tier)
        if worst:
            nodeid, ms = worst
            print(f'  slowest    {tier} — {ms / 1000:.1f}s  {nodeid}')
    if over:
        print(f'[check:{NAME}] FAIL — {len(over)} tier(s) over budget: '
              f'{", ".join(over)}. A tier that got slower is a finding: it '
              f'degrades a human\'s patience instead of a boolean, so nothing '
              f'else in this gate set will ever notice.')
        return 1
    print(f'[check:{NAME}] PASS — {len(budgets)} tier(s) within budget')
    return 0
