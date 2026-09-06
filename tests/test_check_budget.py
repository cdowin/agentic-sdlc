"""test_check_budget.py — a tier that got slower is a finding, and this proves it fails.

The gate exists because a suite is a gate whose cost can double while every
other gate stays green: the drift degrades a human's patience instead of a
boolean, so nothing notices. Which means this module's job is the FAILING
direction. A budget gate that only ever passed would be the thing it was built
to catch.

Cheap by construction (hard rule 10): every case writes a `ledger.jsonl` and a
`devkit.toml` into a `tmp_path` and calls `run()`. No repo, no `make`, no
subprocess — the gate reads rows and compares numbers, so proving it needs rows
and numbers.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

import pytest

from support.pm import with_flow

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo.checks import budget

MILESTONE = '---\nid: "1.0"\nname: M\nstatus: building\n---\n\n# M\n'


@contextlib.contextmanager
def tree(tmp_path: Path, rows: list[dict], config: str = ''):
    """A marked tree with a milestone, a ledger and a config. Never a repo.

    The config DECLARES ITS FLOW (`with_flow`): the gate finds the ledger by
    asking which milestone is in `in_progress`, and a tree that declared no
    categories is refused by name before any row is read.
    """
    root = tmp_path / 'repo'
    mdir = root / 'pm' / 'roadmap' / '1.0-m'
    mdir.mkdir(parents=True)
    (root / '.git').mkdir()
    (mdir / 'milestone.md').write_text(MILESTONE, encoding='utf-8')
    (mdir / 'ledger.jsonl').write_text(
        ''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
    previous = Path.cwd()
    os.chdir(root)
    repo_root.cache_clear()
    load_config.cache_clear()
    try:
        yield root
    finally:
        os.chdir(previous)
        repo_root.cache_clear()
        load_config.cache_clear()


def gate_row(name: str, ms: int, ts: str = '2026-09-05T12:00:00Z',
             verdict: str = 'PASS', census: int | None = None) -> dict:
    row = {'ts': ts, 'kind': 'gate', 'gate': name, 'verdict': verdict,
           'duration_ms': ms}
    if census is not None:
        row['census'] = census
    return row


def check() -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = budget.run()
    return code, buf.getvalue()


BUDGET = '[tests]\nbudget = { unit = 10, integration = 60 }\n'


# --- the failing direction, which is the whole point --------------------------
def test_a_tier_over_its_ceiling_FAILS_and_names_the_overage(tmp_path):
    rows = [gate_row('unit', 25_000), gate_row('integration', 30_000)]
    with tree(tmp_path, rows, BUDGET):
        code, out = check()
    assert code == 1, out
    assert 'OVER BUDGET unit' in out, out
    assert '25.0s against a 10s ceiling' in out, out
    assert '+15.0s' in out, out
    # …and the tier that is fine is still reported, so a reader sees the shape
    # of the whole thing rather than only what broke.
    assert 'ok          integration' in out, out


def test_the_newest_row_wins_so_an_average_cannot_hide_a_regression(tmp_path):
    """An average hides the run that got slower behind the ten that did not,
    and the question this gate answers is "what does it cost NOW".

    NEWEST BY TIMESTAMP, not last in the file. This case once wrote its rows
    oldest-first, so a gate grading the last line passed it while grading the
    wrong row on any ledger with concurrent writers or a merge in it — on this
    repo's own ledger, a 62.6s row from eight minutes before a 13.2s one. The
    40s row now sits FIRST in the file behind two newer-looking stale ones,
    and the age printed beside it must be that row's own, because an age
    computed from the row it did not pick certifies the stale number."""
    rows = [gate_row('unit', 40_000, '2026-09-05T12:00:00Z'),
            gate_row('unit', 1_000, '2026-09-05T10:00:00Z'),
            gate_row('unit', 1_000, '2020-01-01T00:00:00Z')]
    with tree(tmp_path, rows, BUDGET):
        code, out = check()
    assert code == 1, out
    line = next(l for l in out.splitlines() if 'OVER BUDGET unit' in l)
    assert '40.0s' in line, out
    assert budget._age('2026-09-05T12:00:00Z') in line, out
    assert budget._age('2020-01-01T00:00:00Z') not in out, out


def test_a_run_that_did_not_end_PASS_is_NOT_GRADED_and_a_finding(tmp_path):
    """Every row this module wrote before said PASS, so nothing here could tell
    whether the gate READ the verdict — and it did not, on the passing path:
    a `unit` row ending FAIL at 9.3s of 20s printed `ok` and PASS. A run that
    stopped is cheaper and smaller than one that finished, so a failed run is
    the one most likely to sit under both ceilings; its duration and census
    are the cost of a run that stopped, not measurements of the tier."""
    rows = [gate_row('unit', 9_300, verdict='FAIL', census=734),
            gate_row('integration', 30_000, census=673)]
    with tree(tmp_path, rows, BUDGET + 'cases = { unit = 1250 }\n'):
        code, out = check()
    assert code == 1, out
    assert 'NOT GRADED  unit — newest run ended FAIL at 9.3s' in out, out
    assert 'run `make unit`' in out, out
    # Neither column grades it: no `ok unit` for time, none for cases.
    assert 'ok          unit' not in out, out
    assert '734' not in out, out
    assert 'not graded: unit (FAIL)' in out, out
    # The tier that did finish is still graded beside it.
    assert 'ok          integration — 30.0s of 60s' in out, out


# --- the honest-about-not-knowing direction -----------------------------------
def test_a_tier_with_no_row_is_UNMEASURED_and_never_a_pass(tmp_path):
    """Rule 4's zero census, in a column of numbers. A tier nobody ran is a
    tier nobody measured, and reporting it as under budget would be the gate
    printing PASS over something it did not look at."""
    with tree(tmp_path, [gate_row('unit', 1_000)], BUDGET):
        code, out = check()
    assert 'UNMEASURED  integration' in out, out
    assert 'run `make integration`' in out, out
    # It does not FAIL on it — a tier that has never run is not a regression —
    # but it is said out loud rather than counted as fine.
    assert code == 0, out
    # …in the SUMMARY too. This case once stopped at the detail line, and the
    # summary beneath it read `2 tier(s) within their time budget` over one
    # measured tier — the one line a CI tail keeps, and it was false.
    summary = out.splitlines()[-1]
    assert summary.startswith('[check:budget] PASS — '), out
    assert 'within their time budget: unit;' in summary, out
    assert 'unmeasured: integration' in summary, out
    assert '2 tier' not in summary, out


def test_every_graded_row_carries_its_AGE(tmp_path):
    """A ceiling reported against last week's row is a ceiling reported against
    last week's code. A number without its age reads as a fact about the tree
    in front of you."""
    rows = [gate_row('unit', 1_000, '2020-01-01T00:00:00Z'),
            gate_row('integration', 1_000, '2020-01-01T00:00:00Z')]
    with tree(tmp_path, rows, BUDGET):
        _code, out = check()
    assert 'measured' in out and 'ago' in out, out


# --- the census, both directions ---------------------------------------------
CASES = ('[tests]\nbudget = { unit = 10 }\n'
         'cases = { unit = 1250 }\nfloor = { unit = 1000 }\n')


def test_a_census_under_its_floor_FAILS_and_every_count_carries_its_delta(
        tmp_path):
    """No case in this module ever wrote a `census` on a row, so neither
    direction of the case count was proven — and the ceiling only looked up:
    a tier that had shrunk 35% under its declared baseline read `ok`. A
    census that shrinks cannot trip a ceiling, and deleting a test because it
    is slow is the sin this gate exists to prevent. The floor is a finding
    the same way the ceiling is; the delta against the run before is printed
    either way, so a drop is visible with no second number to maintain."""
    rows = [gate_row('unit', 1_000, '2026-09-05T10:00:00Z', census=1123),
            gate_row('unit', 1_000, '2026-09-05T12:00:00Z', census=734)]
    with tree(tmp_path / 'floor', rows, CASES):
        code, out = check()
    assert code == 1, out
    assert 'UNDER FLOOR unit — 734 case(s) against a 1000 floor (-266)' in out
    assert '389 fewer than the run before (1123)' in out, out
    assert 'unit (cases)' in out.splitlines()[-1], out
    # The same two rows, over a ceiling instead: growth reads the same way.
    rows[-1]['census'] = 1300
    with tree(tmp_path / 'ceiling', rows, CASES):
        code, out = check()
    assert code == 1, out
    assert 'OVER COUNT  unit — 1300 case(s) against a 1250 ceiling (+50)' in out
    assert '177 more than the run before (1123)' in out, out
    # Inside the band, the delta still rides on the `ok` line.
    rows[-1]['census'] = 1100
    with tree(tmp_path / 'band', rows, CASES):
        code, out = check()
    assert code == 0, out
    assert 'ok          unit — 1100 of 1250 case(s), floor 1000, ' \
           '23 fewer than the run before (1123)' in out, out
    assert 'within their case limits: unit' in out.splitlines()[-1], out


# --- rule 5: a gate ships stock defaults, and a ceiling cannot be one ---------
def test_no_ceiling_of_either_kind_REPORTS_and_passes(tmp_path):
    """"Twenty seconds" is a claim about a machine, and rule 8 says this
    package knows nothing about its consumers'. A stock ceiling would redden
    every tree whose runner is slower than the laptop it was picked on."""
    rows = [gate_row('unit', 999_000),
            gate_row('integration', 5_000, verdict='FAIL')]
    with tree(tmp_path, rows):
        code, out = check()
    assert code == 0, out
    assert 'no [tests] budget is declared' in out, out
    # Reported, not silent: a gate that passes saying nothing has told a reader
    # nothing about the tree — and a run that did not end PASS says so.
    assert 'unit 999.0s' in out, out
    assert 'integration 5.0s (FAIL' in out, out


def test_an_empty_tree_says_nothing_yet_rather_than_zero(tmp_path):
    with tree(tmp_path, []):
        code, out = check()
    assert code == 0, out
    assert 'nothing yet' in out, out


# --- the config is refused, not interpreted -----------------------------------
@pytest.mark.parametrize('bad,needle', [
    ('[tests]\nbudget = { unit = 0 }\n', 'not a budget'),
    ('[tests]\nbudget = { unit = -5 }\n', 'not a budget'),
    ('[tests]\nbudget = "fast"\n', 'must be a table'),
    ('[tests]\nbudget = { unit = "ten" }\n', 'unit'),
    ('[tests]\ncases = { unit = 0 }\n', 'proves nothing'),
    ('[tests]\nfloor = { unit = 0 }\n', 'holds nothing'),
    ('[tests]\ncases = { unit = 100 }\nfloor = { unit = 101 }\n',
     'no census can satisfy both'),
])
def test_a_malformed_ceiling_is_a_config_error(tmp_path, bad, needle):
    with tree(tmp_path, [], bad):
        with pytest.raises(ConfigError) as err:
            budget.run()
    assert needle in str(err.value), str(err.value)


@pytest.mark.parametrize('line,needle', [
    ('{not json\n', 'could not be read'),
    # A gate row this gate cannot place in time is a row it cannot call newest
    # or oldest; ordering it silently would be guessing which run is current.
    (json.dumps({'ts': 'yesterday', 'kind': 'gate', 'gate': 'unit',
                 'verdict': 'PASS', 'duration_ms': 1}) + '\n',
     "ts 'yesterday' is not a timestamp"),
])
def test_an_unreadable_ledger_FAILS_rather_than_reporting_no_costs(
        tmp_path, line, needle):
    """The census again: a ledger this gate cannot parse is not a tree with no
    gate rows in it."""
    with tree(tmp_path, [gate_row('unit', 1_000)], BUDGET) as root:
        ledger = root / 'pm/roadmap/1.0-m/ledger.jsonl'
        ledger.write_text(line, encoding='utf-8')
        code, out = check()
    assert code == 1, out
    assert needle in out, out
