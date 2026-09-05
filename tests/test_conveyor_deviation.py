"""test_conveyor_deviation.py — the row a step that is not true writes.

Chris's ruling, 2026-09-04: *steps are skippable, and a skip is RECORDED.* A
protocol nobody can deviate from gets worked around, and a worked-around
protocol teaches nothing.

**D8, 2026-09-05, kept the row and removed the flag.** `--skip <step>
--reason "<why>"` existed to escape a REFUSAL, and no step refuses any more —
so it was ceremony with a grammar. The row was always the honest half, and the
driver now writes one for every step that is not true, carrying the reason the
step itself gave. Strictly more of the thing the row was minted for: a skip
reason was the operator's account of why they were stepping around the machine,
and this is the machine's account of what it found, written without anyone
having to remember to ask for it.

So what this file asserts changed shape and not subject: one row per not-true
step, written once however often the belt re-runs, `outcome` carrying the
step's own verdict rather than the constant `'skipped'`, and the whole thing
FAILING OPEN — a ledger this process cannot append to costs the run its durable
record and does not stop the release, because a belt that declined to walk over
its own bookkeeping would be the machine deciding that telemetry outranks the
operator.

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
def test_a_not_true_step_writes_exactly_one_row_carrying_its_own_reason():
    with tree() as root:
        code, out = run()
        assert code == 1, out
        assert f'[release:{FALSE.name}] JUDGEMENT NOT-TRUE' in out, out
        recorded = rows(root)
        assert len(recorded) == 1, recorded
        assert recorded[0] == {**recorded[0],
                               'kind': 'deviation', 'grain': VERSION,
                               'operation': 'release', 'step': FALSE.name,
                               'outcome': 'not-true',
                               # THE REASON IS THE STEP'S OWN `Answer.detail`.
                               # Nobody typed it, and nobody had to remember to.
                               'reason': 'no'}
        assert set(recorded[0]) == {'ts', 'kind', 'grain', 'operation', 'step',
                                    'outcome', 'reason'}


def test_a_true_step_writes_no_row():
    """The row is for what did NOT hold. A log that recorded every step would
    be a second copy of the run cache, which is gitignored precisely because
    it is reconstructible from the tree."""
    with tree() as root:
        run()
        assert [r['step'] for r in rows(root)] == [FALSE.name]


def test_re_walking_the_same_tree_writes_no_second_row():
    """Idempotence, which is what the callback's True/False is for: a durable
    log that grows on every read is a log nobody can count."""
    with tree() as root:
        assert run()[0] == 1
        first = (root / LEDGER).read_bytes()
        code, out = run()
        assert code == 1, out
        assert (root / LEDGER).read_bytes() == first


def test_an_unverifiable_step_records_its_own_outcome_word():
    """UNVERIFIABLE is not "no" — it is "this cannot be decided" — and the
    durable row keeps them apart for the same reason `Truth` is an enum."""
    unknown = driver.Step('unknowable', driver.StepKind.JUDGEMENT,
                          lambda c: driver.Answer.unverifiable('no artifact'),
                          lambda c: 'say')
    with tree() as root:
        code, out = run(registry={unknown.name: unknown},
                        steps=(unknown.name,))
        assert code == 1, out
        assert rows(root)[0]['outcome'] == 'unverifiable'
        assert rows(root)[0]['reason'] == 'no artifact'


def test_a_run_where_something_is_not_true_reports_a_scoreboard():
    with tree():
        _, out = run()
        assert f'[release] 1/2 true · 1 not true: {FALSE.name}' in out, out


# --- the refusal matrix: exit code AND a byte-identical ledger -----------------
@pytest.mark.parametrize('argv,expected', [
    # The removed flag is NAMED rather than swept into `unknown option`: a
    # consumer's script may still carry it, and "unknown option '--skip'"
    # would send them looking for a typo.
    (('--skip', FALSE.name, '--reason', 'x'), 'was removed in 0.2.0'),
    (('--skip',), 'was removed in 0.2.0'),
    (('--reason', 'x'), 'was removed in 0.2.0'),
    (('--nonsense',), 'unknown option'),
])
def test_the_flag_refusal_matrix_is_exit_2_and_writes_no_row(argv, expected):
    with tree() as root:
        before = (root / LEDGER).exists()
        code, out = run(*argv)
        assert code == 2, out
        assert expected in out, out
        assert (root / LEDGER).exists() == before, 'a refusal left a row'


def test_a_run_against_an_unresolvable_version_writes_nothing():
    with tree() as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = driver.main(['release', '0.0.0'], registry=STUB,
                               steps=ORDER)
        assert code == 1, buf.getvalue()
        assert not (root / LEDGER).exists()


def test_a_ledger_that_is_a_directory_warns_and_the_walk_still_finishes():
    """FAILING OPEN, and it is the ruling rather than an oversight. Losing the
    durable row is a telemetry problem; a belt that refused to walk over one
    would be the machine deciding its own bookkeeping outranks the operator's
    release — which is what D8 took out."""
    with tree() as root:
        (root / LEDGER).mkdir()
        code, out = run()
        assert code == 1, out
        assert 'is a directory' in out, out
        assert 'this run walks' in out, out
        # It WALKED: both steps were asked and the scoreboard is there.
        assert '1/2 true' in out, out


def test_u2028_in_a_step_detail_reads_back_as_one_row():
    """`ledger.LINE_BREAKERS` escapes it, so the row is still one line — and
    the detail now comes from a STEP rather than from an operator, so a step
    whose message carries one must not split the log."""
    odd = driver.Step('odd', driver.StepKind.GATE,
                      lambda c: driver.Answer.no('a\u2028b'))
    with tree() as root:
        code, out = run(registry={'odd': odd}, steps=('odd',))
        assert code == 1, out
        raw = (root / LEDGER).read_text(encoding='utf-8')
        assert len([line for line in raw.split('\n') if line.strip()]) == 1
        assert rows(root)[0]['reason'] == 'a\u2028b'


def test_a_step_that_answers_not_true_with_no_detail_writes_no_row():
    """`Answer`'s own docstring: a step that answers no with an empty detail
    has told the operator that something is wrong and nothing about what. The
    row minter has always refused that, and the new caller hits the same wall
    — so the run still walks and the silence is not laundered into a row."""
    mute = driver.Step('mute', driver.StepKind.GATE,
                       lambda c: driver.Answer.no(''))
    with tree() as root:
        code, out = run(registry={'mute': mute}, steps=('mute',))
        assert code == 1, out
        assert not (root / LEDGER).exists()


# --- the row minter -----------------------------------------------------------
def test_a_row_without_a_reason_cannot_be_minted_at_all():
    for bad in ('', '   ', '...', None, 3, 'x' * 2000, 'two\nlines'):
        with pytest.raises(ValueError):
            ledger.deviation_row(VERSION, 'release', 'gate', bad)


def test_an_outcome_outside_the_closed_set_cannot_be_minted_either():
    """`OUTCOMES` widened from the constant `'skipped'` to the step's own
    verdict, and a closed set is what stops it widening again by accident.
    `'skipped'` stays IN it: rows carrying it are already in every consumer's
    ledger, and a reader that stopped understanding them would be rewriting
    history — D7's reasoning, one file over."""
    for good in ledger.OUTCOMES:
        ledger.deviation_row(VERSION, 'release', 'gate', 'r', outcome=good)
    for bad in ('wombat', '', None, 'NOT-TRUE'):
        with pytest.raises(ValueError):
            ledger.deviation_row(VERSION, 'release', 'gate', 'r',
                                 outcome=bad)


def test_the_row_kind_is_distinct_from_the_kinds_already_minted():
    assert ledger.KIND_DEVIATION not in (ledger.KIND_STATUS,
                                         ledger.KIND_DECISION,
                                         ledger.KIND_GATE,
                                         ledger.KIND_DISPATCH,
                                         ledger.KIND_SESSION)


# --- --status -----------------------------------------------------------------
def test_status_prints_the_recorded_run_and_walks_nothing():
    with tree() as root:
        run()
        before = (root / LEDGER).read_bytes()
        code, out = run('--status')
        assert code == 0, out
        assert FALSE.name in out and 'NOT-TRUE' in out, out
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
        if row.get('outcome') not in ledger.OUTCOMES:
            bad.append(f'{step!r} carries outcome {row.get("outcome")!r}')
        key = (str(operation), str(step))
        if key in seen:
            bad.append(f'{step!r} carries two outcome rows')
        seen.add(key)
    return bad


def test_a_written_ledger_is_well_formed_and_round_trips():
    with tree() as root:
        run()
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
        run()
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
