"""test_emit.py — where an event goes, and what this package refuses to do to
get it there.

`repo/emit.py` is 0.5.0/D1 built: **a hook is an event this package WRITES; it
is never a command this package RUNS.** A sink is opened, appended to, closed.
The four claims that would cost real time if they broke, and nothing else:

  1. declaring the section is what opts a tree IN — no `[emit]` at all writes
     nothing anywhere, a bare one is the ledger and all three taps, and a value
     of the wrong shape is exit 2 rather than a gate quietly emitting nothing;
  2. the ledger sink routes by the GRAIN the row names and by nothing else —
     the same rule every other row is filed under (0.4.0/D1);
  3. a path sink is APPENDED to, and `-` is one JSON line on stdout beside the
     prose rather than inside it;
  4. a sink this package cannot reach is a FINDING — never a crash, never a
     changed exit code, and never silence.

The NO-SPAWN half of the same feature is source-shaped and lives in
`tests/test_boundaries.py` (`TheToolEmitsAndNeverExecutes`), where the import
allowlist and the shell derivation already are. What a row IS belongs to
`ft-one-event-shape-serves-three-readers`; every row below is the smallest
thing with a `kind` and a `grain`, because this module asserts routing.
"""
from __future__ import annotations

import contextlib
import json

import pytest
from support.pm import cfg_for, ledger_rows, tree, write_config

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo import emit

STORY = '0.1/alpha/s0'
MILESTONE_LEDGER = 'pm/roadmap/ledgers/0.1.jsonl'
# 0.4.0/D3: a row naming no grain lands in the TREE's own ledger, beside the
# gate rows, rather than in a milestone somebody had to pick.
GRAINLESS_LEDGER = 'pm/roadmap/ledger.jsonl'
TS = '2026-09-07T00:00:00Z'


def row(kind: str, grain: str = '', **fields: object) -> dict:
    """One event row, minimally. The SHAPE is another feature's; what this
    module reads off a row is the grain it names."""
    out: dict = {'ts': TS, 'kind': kind}
    if grain:
        out['grain'] = grain
    out.update(fields)
    return out


@contextlib.contextmanager
def emitting(config: str = '', **kwargs):
    """A `support.pm` tree whose devkit.toml carries `config`, plus its loaded
    `PmConfig` — `cfg_for` is what clears the config caches, so every case
    reads the toml it just wrote rather than the previous case's."""
    with tree(**kwargs) as root:
        write_config(root, config)
        yield root, cfg_for(root)


def lines_of(root, rel: str) -> list[str]:
    """The raw lines of a sink file, or [] when nothing was written there."""
    path = root / rel
    return (path.read_text(encoding='utf-8').splitlines()
            if path.is_file() else [])


# --- 1: the declaration -------------------------------------------------------

def test_no_emit_section_writes_nothing_and_a_bare_one_takes_every_default(
        capsys):
    """Hard rule 5's gate half, and the guarantee under it: both KEYS have a
    stock default behind them, so a bare `[emit]` behaves exactly like one that
    spelled them out — while the SECTION is what opts a tree in, so a tree with
    none is byte-identical to 0.4.0. That second half is asserted through
    `emit()` itself, because a guarantee held at the call sites is one the next
    tap forgets. A malformed value is exit 2 — a sink quietly emitting nothing
    is the read-side cardinal sin with a config file in front of it.
    """
    # The two spellings of the tap set. `TAPS` is literal because the seed
    # census folds it; these constants are what a caller names.
    assert emit.TAPS == (emit.TAP_ENTER, emit.TAP_VERDICT, emit.TAP_LEAVE)

    with emitting() as (root, cfg):
        assert not emit.declared(), 'a tree with no [emit] declared one'
        assert emit.settings() == emit.Settings(emit.SINK_LEDGER, emit.TAPS)
        for tap in emit.TAPS:
            assert emit.emit(cfg, tap, row(f'rung.{tap}', STORY)) == ''
        assert lines_of(root, MILESTONE_LEDGER) == [], (
            'a tree that declared no [emit] was emitted for anyway — the '
            'stock-defaulted KEYS are not a stock-defaulted section, and this '
            'tree is meant to be byte-identical to 0.4.0')
        assert lines_of(root, GRAINLESS_LEDGER) == []
        assert capsys.readouterr() == ('', '')

    with emitting('[emit]\nsink = "-"\nkinds = ["leave"]\n') as (_root, _cfg):
        assert emit.declared()
        assert emit.settings() == emit.Settings(emit.SINK_STDOUT, ('leave',))

    refusals = {
        # a bare string is iterable, and `("l","e","a","v","e")` is five taps
        'kinds = "leave"': 'kinds',
        'kinds = []': 'kinds',
        'kinds = ["leave", "landed"]': 'landed',
        'sink = 3': 'sink',
        # rule 8: nothing here reads a path outside the checkout
        'sink = "/var/log/events.jsonl"': 'sink',
    }
    for declaration, named in refusals.items():
        with emitting(f'[emit]\n{declaration}\n') as (_root, _cfg):
            with pytest.raises(ConfigError) as raised:
                emit.settings()
            assert named in str(raised.value), (
                f'{declaration!r} was refused without naming {named!r}: '
                f'{raised.value}')


# --- 2: the ledger sink -------------------------------------------------------

def test_the_ledger_sink_files_an_event_by_the_grain_it_names(capsys):
    """The default sink, and the routing every other row already uses: the
    milestone that owns the row's GRAIN, followed through its bindings, with no
    status read on the write path (0.4.0/D1)."""
    # A bare section: the opt-in, at every default the keys hold.
    with emitting('[emit]\n') as (root, cfg):
        assert emit.emit(cfg, emit.TAP_LEAVE, row('rung.leave', STORY)) == ''
        assert emit.emit(cfg, emit.TAP_ENTER, row('rung.enter', STORY)) == ''
        filed = ledger_rows(root, MILESTONE_LEDGER)
        assert [r['kind'] for r in filed] == ['rung.leave', 'rung.enter'], (
            'the story\'s events did not land in its milestone\'s ledger, '
            'oldest first')
        assert lines_of(root, GRAINLESS_LEDGER) == []

        # A row naming no grain has no milestone to pick, so it lands beside
        # the gate rows in the tree's own ledger (D3).
        assert emit.emit(cfg, emit.TAP_VERDICT, row('check.verdict')) == ''
        assert [r['kind'] for r in ledger_rows(root, GRAINLESS_LEDGER)] == [
            'check.verdict']

        # A grain no milestone owns is a sink with nowhere to file: named,
        # never dropped in silence, and nothing is written.
        before = lines_of(root, MILESTONE_LEDGER)
        finding = emit.emit(cfg, emit.TAP_LEAVE, row('rung.leave', 'ft-ghost'))
        assert 'ft-ghost' in finding, finding
        assert finding in capsys.readouterr().err
        assert lines_of(root, MILESTONE_LEDGER) == before


# --- 3: a path, and a stream --------------------------------------------------

def test_a_path_sink_is_appended_to_and_dash_is_one_json_line_on_stdout(capsys):
    """A path is opened, appended to and closed — never rewritten, because two
    appenders and a read-modify-write lose rows. `-` puts the same bytes on
    stdout, one whole JSON object per line: prose this package prints never
    opens with `{`, so a consumer parsing prose keeps parsing prose (rule 6).
    """
    sink = 'logs/events.jsonl'
    with emitting(f'[emit]\nsink = "{sink}"\n') as (root, cfg):
        (root / 'logs').mkdir()
        (root / sink).write_text('{"kind":"already here"}\n', encoding='utf-8')
        assert emit.emit(cfg, emit.TAP_ENTER, row('rung.enter', STORY)) == ''
        assert emit.emit(cfg, emit.TAP_LEAVE, row('rung.leave', STORY)) == ''
        written = [json.loads(line) for line in lines_of(root, sink)]
        assert [r['kind'] for r in written] == [
            'already here', 'rung.enter', 'rung.leave'], (
            'a path sink must APPEND: the bytes already there stay, and each '
            'event is one more line')
        assert lines_of(root, MILESTONE_LEDGER) == [], (
            'a declared path sink also wrote the ledger — one sink, not two')
        assert capsys.readouterr().out == ''

    with emitting('[emit]\nsink = "-"\n') as (root, cfg):
        assert emit.emit(cfg, emit.TAP_LEAVE, row('rung.leave', STORY)) == ''
        streamed = capsys.readouterr()
        assert streamed.err == ''
        assert streamed.out.splitlines() == [
            '{"ts":"' + TS + '","kind":"rung.leave","grain":"' + STORY + '"}'], (
            'the stdout sink is ONE compact JSON object on ONE line — the same '
            'serialisation the ledger file gets')
        assert json.loads(streamed.out)['grain'] == STORY
        assert lines_of(root, MILESTONE_LEDGER) == []


# --- 4: the sink that cannot be reached ---------------------------------------

def test_a_sink_that_cannot_be_written_is_a_finding_and_never_a_crash(capsys):
    """The whole posture of this feature in one case. Emission is never
    load-bearing for a belt's verdict: the caller's work has landed, the
    exception does not escape, and the sink it could not reach is NAMED — the
    fail-open courier with no fail-loud counterpart is what recorded nothing
    for the whole of 0.3.0 and nobody could tell.
    """
    sink = 'events.jsonl'
    with emitting(f'[emit]\nsink = "{sink}"\n') as (root, cfg):
        # A directory where the file goes: an `open('a')` that raises, without
        # asking a test to make a filesystem read-only.
        (root / sink).mkdir()
        finding = emit.emit(cfg, emit.TAP_LEAVE, row('rung.leave', STORY))
        assert finding.startswith('[emit] WARNING'), finding
        assert sink in finding, 'the finding does not name the sink'
        assert finding in capsys.readouterr().err, (
            'the finding was returned and never said — a caller that ignores '
            'the return value would have swallowed it')

    # A tap the tree did not declare is SILENT, and that silence is what the
    # project asked for: nothing written, nothing reported.
    with emitting(f'[emit]\nsink = "{sink}"\nkinds = ["leave"]\n') as (root, cfg):
        assert emit.emit(cfg, emit.TAP_ENTER, row('rung.enter', STORY)) == ''
        assert not (root / sink).exists()
        assert capsys.readouterr() == ('', '')
        assert emit.emit(cfg, emit.TAP_LEAVE, row('rung.leave', STORY)) == ''
        assert len(lines_of(root, sink)) == 1

        # A tap this version does not have is a CALLER defect, not a sink
        # condition, and it refuses rather than emitting into the dark.
        with pytest.raises(ValueError):
            emit.emit(cfg, 'landed', row('rung.landed', STORY))

    # A row `ledger.dumps` cannot serialise fails in the same posture as a sink
    # that cannot be opened: named on stderr, never raised into the belt that
    # called it. Both sinks, because a file and a stream fail in different
    # places and only one of them was ever guarded.
    unserialisable = row('rung.leave', STORY, blockers={'a set'})
    for declaration in (f'sink = "{sink}"', f'sink = "{emit.SINK_STDOUT}"'):
        with emitting(f'[emit]\n{declaration}\n') as (root, cfg):
            finding = emit.emit(cfg, emit.TAP_LEAVE, unserialisable)
            assert finding.startswith('[emit] WARNING'), (
                f'{declaration} raised or swallowed a row it could not '
                f'serialise instead of naming it: {finding!r}')
            assert 'TypeError' in finding, finding
            assert finding in capsys.readouterr().err
            assert lines_of(root, sink) == []
