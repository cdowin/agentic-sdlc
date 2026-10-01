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
    base = {'ts': TS, 'kind': ledger.KIND_VERIFY, 'rung': 'spot',
            'gate': 'unit', 'verdict': 'PASS', 'exit_code': 0,
            'duration_ms': 5, 'census': 12, 'state': STATE}
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
    assert (got.ts, got.rung, got.gate, got.verdict) == (TS, 'spot', 'unit',
                                                         'PASS')
    assert (got.exit_code, got.duration_ms, got.census) == (0, 5, 12)
    assert got.state == STATE


def test_a_row_the_ledger_mints_is_a_row_the_cache_reads():
    """The two ends of one contract, held together: `verify_row` refuses to
    mint what `_verdict` refuses to read, so a row this package wrote is never
    a row this package then distrusts."""
    minted = ledger.verify_row(rung='milestone', gate='test', verdict='FAIL',
                               state=STATE, duration_ms=90170, exit_code=2,
                               census=1254)
    got = cache._verdict(json.loads(ledger.dumps(minted)))
    assert got is not None
    assert (got.verdict, got.exit_code, got.census) == ('FAIL', 2, 1254)


@pytest.mark.parametrize('field,value', [
    ('state', ''), ('state', 7), ('duration_ms', 'fast'),
    ('exit_code', True),
])
def test_the_ledger_refuses_to_mint_what_the_cache_would_refuse_to_read(field,
                                                                       value):
    whole = {'rung': 'spot', 'gate': 'unit', 'verdict': 'PASS',
             'state': STATE, 'duration_ms': 5, 'exit_code': 0}
    whole[field] = value
    with pytest.raises(ValueError):
        ledger.verify_row(**whole)


# --- what a miss SAYS ---------------------------------------------------------
def _tree(tmp_path, monkeypatch, files: dict[str, str]):
    """A scratch tree whose listing is every file in it but the ledger (which
    git ignores), read by `tree_state` with git answered in-process: the state
    is a function of the bytes, no spawn. The inputs directory is LISTED, as
    in a tree that has not taken its ignore line. Returns that directory."""
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding='utf-8')

    def git(root, *args):
        if args[0] == 'ls-files':
            return b'\0'.join(sorted(
                str(p.relative_to(root)).encode() for p in root.rglob('*')
                if p.is_file() and p.suffix != '.jsonl'))
        return b'0' * 40
    roadmap = tmp_path / 'roadmap'
    roadmap.mkdir(exist_ok=True)
    kept = ledger.local_inputs_dir(roadmap)
    monkeypatch.setattr(cache, '_git', git)
    monkeypatch.setattr(cache, 'ledger_file',
                        lambda root: ledger.local_path(roadmap))
    monkeypatch.setattr(cache, 'inputs_dir', lambda: kept)
    monkeypatch.setenv(cache.SHARED_RECEIPTS_ENV, '0')
    return kept


def _state(root):
    state, defect = cache.tree_state(root)
    assert state is not None, defect
    return state


def _pass(root, state, rung='spot'):
    assert cache.record(root, rung, 'unit', state, cache.PASS, 0, 5,
                        None) == ''


def test_a_miss_names_each_input_that_changed_was_added_or_was_removed(
        tmp_path, monkeypatch):
    """Bites: a miss that re-runs a 90 s tier and cannot say why. Record a
    PASS, edit one input, add one, remove one, look up: each is named once,
    sorted by path, and the input that did not move is not named."""
    _tree(tmp_path, monkeypatch, {'a.py': 'a', 'b.py': 'b', 'c.py': 'c'})
    before = _state(tmp_path)
    _pass(tmp_path, before)
    assert _state(tmp_path) == before, \
        'the file a PASS writes moved the state it was keyed on'
    (tmp_path / 'a.py').write_text('a2', encoding='utf-8')
    (tmp_path / 'c.py').unlink()
    (tmp_path / 'd.py').write_text('d', encoding='utf-8')
    after = _state(tmp_path)
    assert after.digest != before.digest
    assert cache.miss_lines('spot', 'unit', after) == [
        'changed: a.py', 'removed: c.py', 'added: d.py']
    assert cache.miss_lines('milestone', 'unit', after) == [], \
        'another rung\'s PASS is not this one\'s'
    # A miss whose inputs all match the last PASS: HEAD, the environment or
    # the scope moved the key, and one line says so rather than nothing.
    assert cache.miss_lines('spot', 'unit', before) == [cache.NO_INPUT_MOVED]


def test_each_pass_overwrites_its_rung_and_no_row_carries_the_digests(
        tmp_path, monkeypatch):
    """Row size: the receipt row keeps the 2.0.0 shape, and the directory
    holds one file per rung and target, overwritten — it grows with rungs,
    not with runs — of short digests, never a byte of a file. A FAIL leaves
    it alone, and one rung's PASS never rewrites another's file (the lost
    update a shared read-modify-write allowed)."""
    kept = _tree(tmp_path, monkeypatch, {'a.py': 'SECRET-CONTENT' * 50})
    first = _state(tmp_path)
    _pass(tmp_path, first)
    _pass(tmp_path, first, rung='milestone')
    (tmp_path / 'a.py').write_text('moved', encoding='utf-8')
    second = _state(tmp_path)
    _pass(tmp_path, second)
    assert cache.record(tmp_path, 'spot', 'unit', first, cache.FAIL, 1, 5,
                        None) == ''
    assert sorted(one.name for one in kept.iterdir()) == [
        'milestone@unit.json', 'spot@unit.json']
    got = {one.name: json.loads(one.read_text(encoding='utf-8'))
           for one in kept.iterdir()}
    assert got['spot@unit.json'] == dict(second.input_digests)
    assert got['milestone@unit.json'] == dict(first.input_digests)
    assert len(got['spot@unit.json']['a.py']) == cache.INPUT_SHOWN
    assert 'SECRET' not in json.dumps(got)
    rows = ledger.local_path(tmp_path / 'roadmap').read_text(encoding='utf-8')
    assert 'SECRET' not in rows
    assert all(set(json.loads(line)) <= set(row()) | {'said', 'probed'}
               for line in rows.splitlines()), 'a row left the 2.0.0 shape'


NOW_INPUTS = cache.State(digest=STATE, files=2,
                         input_digests=(('a.py', '1'), ('b.py', '2')))
NO_PRIOR = {
    'no file': None,
    'not JSON': '{"a.py": ',
    'not a mapping': '["a.py"]',
    'only another rung\'s file': ('milestone', '{"a.py": "0"}'),
    'a digest that is not a string': '{"a.py": 1}',
    'not UTF-8': b'\xff\xfe',
}


@pytest.mark.parametrize('case', sorted(NO_PRIOR))
def test_a_missing_or_malformed_inputs_file_names_nothing(case, tmp_path,
                                                          monkeypatch):
    """No prior PASS, as far as this file can say: no line, never a guess and
    never a crash."""
    monkeypatch.setattr(cache, 'inputs_dir', lambda: tmp_path)
    body = NO_PRIOR[case]
    rung = 'spot'
    if isinstance(body, tuple):
        rung, body = body
    kept = cache.inputs_file(rung, 'unit')
    if isinstance(body, str):
        kept.write_text(body, encoding='utf-8')
    elif body is not None:
        kept.write_bytes(body)
    assert cache.miss_lines('spot', 'unit', NOW_INPUTS) == [], case


def test_a_rung_miss_prints_what_moved_before_its_target_runs(
        tmp_path, monkeypatch, capsys):
    """Bites: the wiring. `_run_rung` on a miss prints each moved input, and
    prints it BEFORE the target — a line after a 90 s tier is a line nobody
    waited for. The target and the record are stubbed: no spawn."""
    from agentic_sdlc.repo.verify import main as verb
    from agentic_sdlc.repo.verify import rules
    _tree(tmp_path, monkeypatch, {'a.py': 'a', 'b.py': 'b'})
    _pass(tmp_path, _state(tmp_path))
    (tmp_path / 'a.py').write_text('a2', encoding='utf-8')
    monkeypatch.setattr(verb, 'rung_state',
                        lambda ladder, root, name: (_state(root), ''))
    monkeypatch.setattr(cache, 'recorded', lambda *args: None)
    monkeypatch.setattr(verb, '_record', lambda *args: None)
    monkeypatch.setattr(verb, '_run',
                        lambda command, root: print('TARGET RAN') or 0)
    ladder = rules.Ladder(milestone='make test', spot='make unit')
    assert verb._run_rung(ladder, tmp_path, 'spot') == verb.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert 'changed: a.py' in out, out
    assert out.index('changed: a.py') < out.index('TARGET RAN'), out
    assert 'changed: b.py' not in out, out


@pytest.mark.parametrize('how', ['listed', 'ignored'])
def test_a_static_gate_state_does_not_move_when_a_pass_keeps_its_inputs(
        how, tmp_path, monkeypatch):
    """Bites: a static gate scoped over the roadmap reads the inputs
    directory — listed where the ignore line is missing, ignored where it is
    not. If its state covered that directory, each rung PASS would move it
    and the gate would never reuse."""
    kept = _tree(tmp_path, monkeypatch, {'a.py': 'a'})
    (tmp_path / 'roadmap' / 'plan.md').write_text('x', encoding='utf-8')
    names = ['a.py', 'roadmap/plan.md']

    def state_now():
        inside = sorted(f'roadmap/{kept.name}/{one.name}'
                        for one in kept.iterdir()) if kept.is_dir() else []
        listed = names + (inside if how == 'listed' else [])
        ignored = inside if how == 'ignored' else []
        state, defect = cache.inputs_state(
            tmp_path, '\0'.join(listed).encode(), ('a.py', 'roadmap'),
            is_ledger=lambda path: False,
            ignored='\0'.join(ignored).encode())
        assert state is not None, defect
        return state

    _pass(tmp_path, _state(tmp_path))
    before = state_now()
    (tmp_path / 'a.py').write_text('a2', encoding='utf-8')
    _pass(tmp_path, _state(tmp_path))
    _pass(tmp_path, _state(tmp_path), rung='milestone')
    (tmp_path / 'a.py').write_text('a', encoding='utf-8')
    assert len(list(kept.iterdir())) == 2
    assert state_now().digest == before.digest, \
        'a rung PASS moved a static gate\'s state'


def test_a_long_miss_prints_twenty_paths_and_counts_the_rest():
    lines = cache.input_changes({}, {f'f{n:02}.py': 'x' for n in range(25)})
    assert len(lines) == cache.MISS_SHOWN + 1
    assert lines[0] == 'added: f00.py'
    assert lines[-1] == '... and 5 more'
    assert len(cache.input_changes({}, {f'{n}': 'x' for n in range(20)})) == 20


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
    state covers."""
    lines = cache.reuse_lines(_verdict_at(), 'make unit',
                              cache.State(digest=STATE, files=439), now=NOW)
    assert len(lines) == 3
    assert all(line.startswith(cache.CACHE_TAG) for line in lines)
    whole = '\n'.join(lines)
    assert 'REUSED PASS' in whole
    assert TS in whole and '2h ago' in whole
    assert 'by `verify --spot`' in whole and 'make unit' in whole
    assert 'census 12' in whole and '5 ms' in whole
    assert STATE[:cache.STATE_SHOWN] in whole and '439 files' in whole
    assert '--no-cache' in whole
    assert 'NOT re-measured' in whole


def test_a_reuse_with_no_census_says_unknown_rather_than_a_number():
    """`verify` scans no files; the census a reuse quotes is the one the GATE
    filed. A gate that filed none leaves the word, never a 0 (rule 4)."""
    whole = '\n'.join(cache.reuse_lines(
        _verdict_at(census=None), 'make test',
        cache.State(digest=STATE, files=1), now=NOW))
    assert 'census unknown' in whole


def test_an_age_is_rendered_from_the_row_and_never_guessed():
    got = _verdict_at()
    assert got.age(NOW) == '2h'
    assert got.age(NOW - timedelta(days=21)) == '0s', \
        'a row from the future ages 0, never a negative duration'


# --- the kinds, named once ------------------------------------------------------
def test_every_kind_a_run_files_about_itself_is_named_and_no_others_are():
    """A closed set, held to the ledger's own vocabulary: adding a kind here
    takes it OUT of the state, which is exactly how a change goes missing."""
    assert cache.SELF_FILED_KINDS == frozenset({
        ledger.KIND_GATE, ledger.KIND_TEST, ledger.KIND_VERIFY,
        *ledger.EVENT_KINDS.values()})
    for kind in (ledger.KIND_STATUS, ledger.KIND_DECISION,
                 ledger.KIND_DEVIATION, ledger.KIND_RETIRE):
        assert kind not in cache.SELF_FILED_KINDS, kind
    # What a BELT files about its own run, out of every rung's state unless
    # `reuse_ignores_status = false`: a closed set too, and a decision, a
    # retire or a lesson is work that stays in.
    assert cache.MOVE_KINDS == frozenset({
        ledger.KIND_STATUS, ledger.KIND_DISPOSITION, ledger.KIND_DEVIATION,
        ledger.KIND_ENTER, ledger.KIND_VERDICT, ledger.KIND_LEAVE,
        ledger.KIND_BELT_BLOCKED})
    for kind in (ledger.KIND_DECISION, ledger.KIND_RETIRE,
                 ledger.KIND_LESSON):
        assert kind not in cache.MOVE_KINDS, kind


# --- what a belt writes, and only that, is out (#95) --------------------------
GRAIN = 'roadmap/stories/s.md'


def _doc(*statuses: str) -> str:
    """A document whose frontmatter carries one `status:` line per value."""
    lines = ''.join(f'status: {status}\n' for status in statuses)
    return f'---\nid: s\n{lines}---\n\n# s\n'


def _belt_tree(tmp_path, monkeypatch, files: dict[str, str]):
    """`_tree`, with a PM config whose roadmap is `roadmap/` and whose pools
    are the derived `roadmap/<kind>s`. The root is resolved, as
    `repo_root` resolves it."""
    from agentic_sdlc.repo.pm import vocabulary
    _tree(tmp_path, monkeypatch, files)
    cfg = vocabulary.PmConfig(root=tmp_path.resolve(), roadmap_dir='roadmap')
    monkeypatch.setattr(vocabulary, 'load', lambda: cfg)


def _without_moves(root):
    state, defect = cache.tree_state(root, moves_out=True)
    assert state is not None, defect
    return state.digest


def test_only_the_first_status_line_is_out_so_a_duplicate_moves_the_state(
        tmp_path, monkeypatch):
    """Bites: rule 4's first sin. A belt rewrites the FIRST `status:` line;
    a second one is hand-written drift that `check pm` flags, and a state
    that drops it too reuses a PASS across that edit."""
    _belt_tree(tmp_path, monkeypatch, {GRAIN: _doc('building', 'building')})
    base = _without_moves(tmp_path)
    (tmp_path / GRAIN).write_text(_doc('done', 'building'), encoding='utf-8')
    assert _without_moves(tmp_path) == base, 'the belt line is out'
    (tmp_path / GRAIN).write_text(_doc('building', 'done'), encoding='utf-8')
    assert _without_moves(tmp_path) != base, 'a duplicate line is drift'
