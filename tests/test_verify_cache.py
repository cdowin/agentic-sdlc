"""test_verify_cache.py — the trust boundary, as function calls.

`verify/cache.py` is the one module in this package that can commit hard rule
4's first cardinal sin: report PASS for a target it did not run. Three of its
pieces decide that, and all three are PURE — a row is read or refused, a
ledger's rows are in the state or out of it, and a reuse says so or does not.
So they are proven here, in the tier `make unit` runs, rather than by eight
scratch repos and eight `make` spawns: rule 10's "a function call before a temp
tree, a temp tree before a process".

The WIRING — a row in a real ledger becoming a real reuse — stays end to end in
`tests/test_verify_main.py`, where the sentinel files prove what ran.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from agentic_sdlc.repo.pm import ledger
from agentic_sdlc.repo.verify import cache

STATE = 'a' * 64
TS = '2026-09-05T10:00:00Z'
NOW = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)


def row(**over) -> dict:
    """A whole `verify` row; `over` is the one field a case is about."""
    base = {'ts': TS, 'kind': ledger.KIND_VERIFY, 'rung': 'story',
            'gate': 'unit', 'verdict': 'PASS', 'exit_code': 0,
            'duration_ms': 5, 'census': 12, 'graded': 3, 'state': STATE}
    base.update(over)
    return base


# --- `_verdict`: never the record over the tree --------------------------------
REFUSED = {
    'no verdict': row(verdict=None),
    'a verdict this does not know': row(verdict='HANG', exit_code=1),
    'PASS with a failing exit code': row(exit_code=3),
    'FAIL with exit 0': row(verdict='FAIL'),
    'a duration that is not a number': row(duration_ms='fast'),
    'a duration that is a bool': row(duration_ms=True),
    'a negative exit code': row(exit_code=-1),
    'a timestamp nothing can age': row(ts='yesterday'),
    'no timestamp at all': row(ts=None),
    'an empty state': row(state='   '),
    'a state of the wrong type': row(state=7),
    'no rung': row(rung=''),
    'a census that is not a number': row(census='lots'),
    # The count `check budget`'s rows are guarded by: a row from a spelling
    # that never counted them cannot say whether it may still be reused, and
    # defaulting it to 0 would reuse every one of them exactly once too often.
    'no graded count': {k: v for k, v in row().items() if k != 'graded'},
    'a graded count that is not a number': row(graded='some'),
    'a negative graded count': row(graded=-1),
}


@pytest.mark.parametrize('case', sorted(REFUSED))
def test_a_row_this_cannot_read_whole_is_refused(case):
    """Bites: rule 4's first sin with a record behind it. Rows arrive from
    other branches, versions and hands; a half-read row that became a PASS is
    a gate reporting a verdict nobody measured."""
    assert cache._verdict(REFUSED[case]) is None, case


def test_the_whole_row_is_read_and_every_field_survives():
    """The control the refusals stand on: each case above is refused for the
    field it names, not because nothing is ever read."""
    got = cache._verdict(row())
    assert got is not None
    assert (got.ts, got.rung, got.gate, got.verdict) == (TS, 'story', 'unit',
                                                         'PASS')
    assert (got.exit_code, got.duration_ms, got.census, got.graded) == (0, 5,
                                                                       12, 3)
    assert got.state == STATE


def test_a_row_the_ledger_mints_is_a_row_the_cache_reads():
    """The two ends of one contract, held together: `verify_row` refuses to
    mint what `_verdict` refuses to read, so a row this package wrote is never
    a row this package then distrusts."""
    minted = ledger.verify_row(rung='feature', gate='test', verdict='FAIL',
                               state=STATE, duration_ms=90170, exit_code=2,
                               graded=41, census=1254)
    got = cache._verdict(json.loads(ledger.dumps(minted)))
    assert got is not None
    assert (got.verdict, got.exit_code, got.graded) == ('FAIL', 2, 41)


@pytest.mark.parametrize('field,value', [
    ('graded', -1), ('duration_ms', 'fast'), ('exit_code', True),
])
def test_the_ledger_refuses_to_mint_what_the_cache_would_refuse_to_read(field,
                                                                       value):
    whole = {'rung': 'story', 'gate': 'unit', 'verdict': 'PASS',
             'state': STATE, 'duration_ms': 5, 'exit_code': 0, 'graded': 0}
    whole[field] = value
    with pytest.raises(ValueError):
        ledger.verify_row(**whole)


# --- `ledger_digest`: which rows are a fact about the tree --------------------
def _lines(*rows) -> str:
    return ''.join(ledger.dumps(r) + '\n' for r in rows)


GATE = {'ts': TS, 'kind': ledger.KIND_GATE, 'gate': 'unit', 'verdict': 'PASS',
        'duration_ms': 10000}
STATUS = {'ts': TS, 'kind': ledger.KIND_STATUS, 'grain': 'st-x',
          'from': 'building', 'to': 'done'}


def test_a_ledger_of_nothing_but_a_runs_own_leavings_contributes_nothing():
    """Every gate writes a cost row and every rung writes a verdict row, so a
    state that hashed them could never repeat and the feature would be dead.
    None, not an empty digest: the FIRST run creates the file, and a state that
    moved for that could never match the row that run just wrote."""
    telemetry = _lines(GATE, row(), {'ts': TS, 'kind': ledger.KIND_TEST,
                                     'tier': 'unit', 'nodeid': 'x',
                                     'duration_ms': 1, 'rank': 1})
    assert cache.ledger_digest('') is None
    assert cache.ledger_digest('\n  \n') is None
    assert cache.ledger_digest(telemetry) is None


def test_the_rows_a_check_grades_are_in_the_state_row_by_row():
    """Bites the finding this replaced: excluding the ledger FILE took every
    status flip, decision and deviation with it, and `check pm` grades those
    inside the same `make milestone` the milestone rung runs."""
    base = cache.ledger_digest(_lines(GATE, STATUS))
    assert base is not None
    assert base == cache.ledger_digest(_lines(GATE, STATUS, row())), \
        'appending a run\'s own verdict row must leave the state alone'
    assert base == cache.ledger_digest(_lines(STATUS)), \
        'a gate row is dropped whatever it sits beside'
    moved = cache.ledger_digest(_lines(GATE, STATUS, dict(STATUS, to='obe')))
    assert moved != base, 'a second status flip is drift'


def test_a_line_this_version_cannot_parse_is_KEPT():
    """Only a row provably filed by a run may be dropped. A line that will not
    parse, or one naming a kind from a version this does not know, is a fact
    about the tree until proven otherwise — the wrong answer here is the one
    that hides a change."""
    kept = cache.ledger_digest(_lines(GATE) + '{"kind": "verify"\n')
    assert kept is not None
    assert kept != cache.ledger_digest(_lines(GATE) + '{"kind": "verify"}\n')
    future = cache.ledger_digest(_lines(GATE, {'ts': TS, 'kind': 'arrival'}))
    assert future is not None


# --- what a reuse SAYS ---------------------------------------------------------
def _verdict_at(**over):
    got = cache._verdict(row(**over))
    assert got is not None
    return got


def test_a_reuse_names_the_run_the_state_and_what_it_did_not_re_measure():
    """A reused green that reads like a fresh green is the cardinal sin, so
    loudness is the fix and it is never conditional: the run it came from, its
    age, its cost, the state, the flag that refuses it — and the inputs no
    state covers, which is where an operator standing on a stale answer finds
    out that `check budget` reads rows this could not carry."""
    lines = cache.reuse_lines(_verdict_at(), 'make unit',
                              cache.State(digest=STATE, files=439), now=NOW)
    assert len(lines) == 3
    assert all(line.startswith(cache.CACHE_TAG) for line in lines)
    whole = '\n'.join(lines)
    assert 'REUSED PASS' in whole
    assert TS in whole and '2h ago' in whole
    assert 'by `verify --story`' in whole and 'make unit' in whole
    assert 'census 12' in whole and '5 ms' in whole
    assert STATE[:cache.STATE_SHOWN] in whole and '439 files' in whole
    assert '--no-cache' in whole
    assert 'NOT re-measured' in whole
    assert '`check budget`' in whole and '3 ledger row(s)' in whole


def test_a_reuse_with_no_census_says_unknown_rather_than_a_number():
    """`verify` scans no files; the census a reuse quotes is the one the GATE
    filed. A gate that filed none leaves the word, never a 0 (rule 4)."""
    whole = '\n'.join(cache.reuse_lines(
        _verdict_at(census=None), 'make test',
        cache.State(digest=STATE, files=1), now=NOW))
    assert 'census unknown' in whole


def test_a_refused_reuse_names_the_count_that_moved_and_the_check_that_grades_it():
    """Rule 11: the state matched and the answer was still bought. An operator
    who is not told why reads this as a cache that does not work."""
    line = cache.stale_line(_verdict_at(), 5, 'make milestone', now=NOW)
    assert line.startswith(cache.CACHE_TAG)
    assert '`check budget`' in line
    assert 'left 3' in line and '5 row(s)' in line
    assert 'make milestone' in line


def test_an_age_is_rendered_from_the_row_and_never_guessed():
    got = _verdict_at()
    assert got.age(NOW) == '2h'
    assert got.age(NOW - timedelta(days=21)) == '0s', \
        'a row from the future ages 0, never a negative duration'


# --- the kinds, named once ------------------------------------------------------
def test_every_kind_a_run_files_about_itself_is_named_and_no_others_are():
    """A closed set, held to the ledger's own vocabulary: adding a kind here
    takes it OUT of the state, which is exactly how a change goes missing."""
    assert cache.GRADED_KINDS == (ledger.KIND_GATE, ledger.KIND_TEST)
    assert cache.SELF_FILED_KINDS == frozenset({
        ledger.KIND_GATE, ledger.KIND_TEST, ledger.KIND_VERIFY,
        *ledger.EVENT_KINDS.values()})
    for kind in (ledger.KIND_STATUS, ledger.KIND_DECISION,
                 ledger.KIND_DEVIATION, ledger.KIND_RETIRE):
        assert kind not in cache.SELF_FILED_KINDS, kind
