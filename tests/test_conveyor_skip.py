"""test_conveyor_skip.py — `--skip <step> --reason "…"`, and the row it writes.

Chris's ruling, 2026-09-04: *steps are skippable, and a skip is RECORDED.* A
protocol nobody can deviate from gets worked around, and a worked-around
protocol teaches nothing. So the flag exists — and every refusal below asserts
the ledger is BYTE-IDENTICAL afterwards, because a rejected skip that left a
row behind would be a record of a decision nobody made.

**What is deliberately NOT here** (story 04's own trap): a test asserting this
repo's 0.2.0 ledger holds a completed release run. It would be red for the
entire milestone and green only after the tag, so `make milestone` — which runs
BEFORE the tag, as a step of the list — could never pass. A gate that cannot be
green at the moment it must run is a gate that gets deleted. What ships instead
is a WELL-FORMEDNESS test over any ledger, and a live-tree assertion that checks
SHAPE and is inert before the run starts.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver  # noqa: E402
from agentic_sdlc.repo.pm import ledger, model  # noqa: E402

VERSION = '9.9.9'
MDIR = f'pm/roadmap/{VERSION}-scratch'
LEDGER = f'{MDIR}/ledger.jsonl'
MILESTONE = f'---\nid: "{VERSION}"\nname: s\nstatus: building\n---\n\n# s\n'

TRUE = driver.Step('always-true', driver.StepKind.JUDGEMENT,
                   lambda c: driver.Answer.yes('yes'), lambda c: 'say')
FALSE = driver.Step('always-false', driver.StepKind.JUDGEMENT,
                    lambda c: driver.Answer.no('no'), lambda c: 'say')
STUB = {TRUE.name: TRUE, FALSE.name: FALSE}
ORDER = (TRUE.name, FALSE.name)


@contextlib.contextmanager
def tree():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / MDIR).mkdir(parents=True)
        (root / MDIR / 'milestone.md').write_text(MILESTONE, encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
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


def run(*argv, registry=STUB, steps=ORDER):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = driver.main(['release', VERSION, *argv], registry=registry,
                           steps=steps)
    return code, buf.getvalue()


def rows(root: Path) -> list[dict]:
    return [r.data for r in ledger.read_rows(root / LEDGER)]


# --- the row, and its idempotence ---------------------------------------------
def test_a_skip_writes_exactly_one_row_and_advances_past_the_step():
    with tree() as root:
        code, out = run('--skip', FALSE.name, '--reason', 'deferred to 9.9.10')
        assert code == 0, out
        assert f'[release:{FALSE.name}] JUDGEMENT SKIPPED' in out, out
        assert 'DEVIATED — 1 of 2' in out, out
        recorded = rows(root)
        assert len(recorded) == 1, recorded
        assert recorded[0] == {**recorded[0],
                               'kind': 'deviation', 'grain': VERSION,
                               'operation': 'release', 'step': FALSE.name,
                               'outcome': 'skipped',
                               'reason': 'deferred to 9.9.10'}
        assert set(recorded[0]) == {'ts', 'kind', 'grain', 'operation', 'step',
                                    'outcome', 'reason'}


def test_re_running_the_same_skip_writes_no_second_row():
    with tree() as root:
        assert run('--skip', FALSE.name, '--reason', 'deferred')[0] == 0
        first = (root / LEDGER).read_bytes()
        code, out = run('--skip', FALSE.name, '--reason', 'deferred')
        assert code == 0, out
        assert 'ALREADY-SKIPPED' in out, out
        assert (root / LEDGER).read_bytes() == first


def test_skipping_every_step_warns_by_count():
    """Risk 3 arriving: a conveyor nothing walks looks like control."""
    with tree():
        code, out = run('--skip', TRUE.name, '--reason', 'a',
                        '--skip', FALSE.name, '--reason', 'b')
        assert code == 0, out
        assert 'WARNING — every step in the list (2) was skipped' in out, out


def test_a_run_that_skipped_reports_fewer_than_total_steps():
    with tree():
        _, out = run('--skip', FALSE.name, '--reason', 'deferred')
        assert '[release] PASS — 1/2 steps' in out, out


# --- the refusal matrix: exit code AND a byte-identical ledger -----------------
@pytest.mark.parametrize('argv,expected', [
    (('--skip', 'no-such-step', '--reason', 'x'), 'not in this'),
    (('--skip', FALSE.name), 'has no --reason'),
    (('--skip',), 'needs a step name'),
    (('--reason', 'x'), 'reason for nothing'),
    (('--skip', FALSE.name, '--reason', ''), 'empty or whitespace'),
    (('--skip', FALSE.name, '--reason', '   '), 'empty or whitespace'),
    (('--skip', FALSE.name, '--reason', '!!! ...'), 'punctuation'),
    (('--skip', FALSE.name, '--reason', 'x' * 1025), 'the limit is 1024'),
    (('--skip', FALSE.name, '--reason', 'two\nlines'), r'\n'),
    (('--skip', FALSE.name, '--reason', 'nul\x00here'), r'\x00'),
    (('--skip', FALSE.name, '--reason', 'a',
      '--skip', FALSE.name, '--reason', 'b'), 'twice'),
    (('--skip', FALSE.name, '--reason', 'a', '--status'), 'cannot be combined'),
    (('--skip', FALSE.name, '--reason'), 'needs a value'),
    (('--nonsense',), 'unknown option'),
])
def test_the_skip_refusal_matrix_is_exit_2_and_writes_no_row(argv, expected):
    with tree() as root:
        before = (root / LEDGER).exists()
        code, out = run(*argv)
        assert code == 2, out
        assert expected in out, out
        assert (root / LEDGER).exists() == before, 'a refusal left a row'


def test_a_skip_against_an_unresolvable_version_writes_nothing():
    with tree() as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = driver.main(['release', '0.0.0', '--skip', FALSE.name,
                                '--reason', 'x'], registry=STUB, steps=ORDER)
        assert code == 1, buf.getvalue()
        assert not (root / LEDGER).exists()


def test_a_skip_cannot_un_do_a_postcondition_that_already_holds():
    with tree() as root:
        assert run()[0] == 1        # walks; always-true is recorded TRUE
        code, out = run('--skip', TRUE.name, '--reason', 'changed my mind')
        assert code == 2, out
        assert 'cannot un-do a postcondition that holds' in out, out
        assert not (root / LEDGER).exists()


def test_a_ledger_that_is_a_directory_refuses_and_skips_nothing():
    with tree() as root:
        (root / LEDGER).mkdir()
        code, out = run('--skip', FALSE.name, '--reason', 'x')
        assert code == 2, out
        assert 'is a directory' in out and 'RECORD is the point' in out, out


def test_u2028_is_accepted_and_reads_back_as_one_row():
    """`ledger.LINE_BREAKERS` escapes it, so the row is still one line."""
    with tree() as root:
        code, out = run('--skip', FALSE.name, '--reason', 'a b')
        assert code == 0, out
        raw = (root / LEDGER).read_text(encoding='utf-8')
        assert len([line for line in raw.split('\n') if line.strip()]) == 1
        assert rows(root)[0]['reason'] == 'a b'


# --- the row minter -----------------------------------------------------------
def test_a_skipped_row_without_a_reason_cannot_be_minted_at_all():
    for bad in ('', '   ', '...', None, 3, 'x' * 2000, 'two\nlines'):
        with pytest.raises(ValueError):
            ledger.deviation_row(VERSION, 'release', 'gate', bad)


def test_the_row_kind_is_distinct_from_the_kinds_already_minted():
    assert ledger.KIND_DEVIATION not in (ledger.KIND_STATUS,
                                         ledger.KIND_DECISION,
                                         ledger.KIND_GATE,
                                         ledger.KIND_DISPATCH,
                                         ledger.KIND_SESSION)


# --- --status -----------------------------------------------------------------
def test_status_prints_the_recorded_run_and_walks_nothing():
    with tree() as root:
        run('--skip', FALSE.name, '--reason', 'deferred to 9.9.10')
        before = (root / LEDGER).read_bytes()
        code, out = run('--status')
        assert code == 0, out
        assert 'deferred to 9.9.10' in out and 'SKIPPED' in out, out
        assert (root / LEDGER).read_bytes() == before


def test_status_on_a_milestone_with_no_deviation_says_so():
    with tree():
        code, out = run('--status')
        assert code == 0, out
        assert 'no deviation is recorded' in out, out


# --- well-formedness, over any ledger -----------------------------------------
def well_formed(data: list[dict], names) -> list[str]:
    """Every complaint about the `deviation` rows in one ledger."""
    bad: list[str] = []
    seen: set[tuple[str, str]] = set()
    for row in data:
        if row.get('kind') != ledger.KIND_DEVIATION:
            continue
        step, operation = row.get('step'), row.get('operation')
        if names is not None and step not in names:
            bad.append(f'{step!r} is not a step of {operation!r}')
        if ledger.reason_defect(row.get('reason', '')):
            bad.append(f'{step!r}: {ledger.reason_defect(row.get("reason"))}')
        if row.get('outcome') != 'skipped':
            bad.append(f'{step!r} carries outcome {row.get("outcome")!r}')
        key = (str(operation), str(step))
        if key in seen:
            bad.append(f'{step!r} carries two outcome rows')
        seen.add(key)
    return bad


def test_a_written_ledger_is_well_formed_and_round_trips():
    with tree() as root:
        run('--skip', FALSE.name, '--reason', 'deferred')
        data = rows(root)
        assert well_formed(data, ORDER) == []
        raw = (root / LEDGER).read_text(encoding='utf-8').strip().split('\n')
        assert [json.loads(line) for line in raw] == data


def test_a_second_row_for_one_step_is_caught_by_the_well_formedness_rule():
    """The rule has teeth: a hand-forged double row FAILS it."""
    forged = [ledger.deviation_row(VERSION, 'release', FALSE.name, 'a'),
              ledger.deviation_row(VERSION, 'release', FALSE.name, 'b')]
    assert well_formed(forged, ORDER) != []


def test_the_report_does_not_redden_on_the_new_kind():
    """Forward compatibility: a row kind the report does not know is ignored,
    never a parse error."""
    from agentic_sdlc.repo.pm import cli as pm_cli
    with tree() as root:
        run('--skip', FALSE.name, '--reason', 'deferred')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = pm_cli.main(['ledger', 'report', VERSION])
        assert code == 0, buf.getvalue()


# --- the live tree: SHAPE, never existence ------------------------------------
def test_every_deviation_row_in_this_repos_own_tree_is_well_formed():
    """Inert before a conveyor run has deviated, and a real assertion the
    moment one has. It proves the SHAPE and never the EXISTENCE — the existence
    half is the close protocol's job, not a test's, because a test asserting it
    would be red for the whole milestone."""
    cfg = model.load()
    checked = 0
    for mdir in model.milestone_dirs(cfg):
        path = ledger.ledger_path(mdir)
        if not path.is_file():
            continue
        data = [r.data for r in ledger.read_rows(path)]
        deviations = [r for r in data
                      if r.get('kind') == ledger.KIND_DEVIATION]
        if not deviations:
            continue
        checked += len(deviations)
        assert well_formed(data, None) == [], cfg.rel(path)
    assert checked >= 0
