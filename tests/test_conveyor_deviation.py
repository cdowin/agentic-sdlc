"""test_conveyor_deviation.py — the row a FORCED write leaves (D12).

Story 04's proof table, criterion 3: `--force` writes and the ledger row names
the checks that were false. Two rows at most per run — the `status` row the
write makes (minted by `pm`, not here) and one `deviation` row with
`outcome: forced` whose `step` lists every false check and whose `reason`
carries each one's own sentence. Without `--force` a false check writes NO
row: a row for a refused write is rule 4's cardinal sin with a timestamp.

A stub registry keeps the checks scripted; the WRITE is the real one, through
`pm milestone <state> <id>`, on a scratch tree that declares its flow.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import FLOW_TOML  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver  # noqa: E402
from agentic_sdlc.repo.pm import ledger, model  # noqa: E402

VERSION = '9.9.9'
MDIR = f'pm/roadmap/{VERSION}-scratch'
LEDGER = f'{MDIR}/ledger.jsonl'
MFILE = f'{MDIR}/milestone.md'
MILESTONE = f'---\nid: "{VERSION}"\nname: s\nstatus: building\n---\n\n# s\n'

TRUE = driver.Check('always-true', lambda c: driver.Answer.yes('yes'))
FALSE = driver.Check('always-false', lambda c: driver.Answer.no('no'))
CANNOT = driver.Check('cannot-say',
                      lambda c: driver.Answer.unverifiable('nobody looked'))
STUB = {c.name: c for c in (TRUE, FALSE, CANNOT)}


@contextlib.contextmanager
def tree():
    """A one-milestone scratch repo, entered, DECLARING its flow — `[pm.states.*]`
    has no runtime fallback (tests/support/pm.py `FLOW_TOML`)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / MDIR).mkdir(parents=True)
        (root / MFILE).write_text(MILESTONE, encoding='utf-8')
        (root / 'devkit.toml').write_text(FLOW_TOML, encoding='utf-8')
        (root / '.git').mkdir(exist_ok=True)  # a MARKER: `repo_root` walks for it
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


def run(*argv, steps=(TRUE.name, FALSE.name)):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = driver.main(['release', VERSION, *argv], registry=STUB,
                           steps=steps)
    return code, buf.getvalue()


def rows(root: Path) -> list[dict]:
    path = root / LEDGER
    return [r.data for r in ledger.read_rows(path)] if path.exists() else []


def status(root: Path) -> str:
    return model.field_of(root / MFILE, 'status')


# --- criterion 3 --------------------------------------------------------------
def test_force_writes_the_status_and_one_row_naming_the_false_checks():
    """Bites: a forced write that leaves no account of what it forced — the
    invisible deviation this row exists to end — or one that writes more
    than the two rows a run may leave."""
    with tree() as root:
        want = driver.done_state(model.load(), 'milestone')
        code, out = run('--force', steps=(TRUE.name, FALSE.name, CANNOT.name))
        assert code == 0, out
        assert status(root) == want
        written = rows(root)
        assert [r['kind'] for r in written] == [ledger.KIND_STATUS,
                                                ledger.KIND_DEVIATION], written
        forced = written[1]
        assert forced['outcome'] == driver.FORCED
        assert forced['step'] == f'{FALSE.name}, {CANNOT.name}'
        assert f'{FALSE.name}: no' in forced['reason']
        assert f'{CANNOT.name}: nobody looked' in forced['reason']
        assert forced['grain'] == VERSION and forced['operation'] == 'release'
        assert set(forced) == {'ts', 'kind', 'grain', 'operation', 'step',
                               'outcome', 'reason'}, 'the row keys moved'
    assert (f'[release] forced — {VERSION} → {want} over 2 false check(s)'
            in out), out


def test_without_force_a_false_check_writes_no_row_and_no_status():
    """Bites: a row minted for a write that did not happen."""
    with tree() as root:
        code, out = run()
        assert code == 1, out
        assert status(root) == 'building'
        assert rows(root) == []
        assert not (root / LEDGER).exists()


def test_all_true_writes_the_status_row_and_no_deviation_row():
    with tree() as root:
        code, out = run(steps=(TRUE.name,))
        assert code == 0, out
        written = rows(root)
        assert [r['kind'] for r in written] == [ledger.KIND_STATUS], written
        assert f'[release] ok — {VERSION} → ' in out


def test_a_u2028_in_a_reason_reads_back_as_one_row():
    """Bites: a check's sentence carrying a JSON-legal line terminator that
    splits one row into two for every line-oriented reader."""
    split = driver.Check('split', lambda c: driver.Answer.no('a b'))
    STUB[split.name] = split
    try:
        with tree() as root:
            code, _ = run('--force', steps=(split.name,))
            assert code == 0
            written = rows(root)
            assert len(written) == 2
            assert written[1]['reason'] == f'{split.name}: a b'
    finally:
        del STUB[split.name]


def test_force_is_refused_for_adopt_and_writes_nothing():
    """Bites: `adopt --force` — there is no grain to write, so a flag that
    exits 0 there would be a promise with nothing behind it."""
    with tree() as root:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code = driver.main(['adopt', VERSION, '--force'], registry=STUB,
                               steps=(FALSE.name,))
        assert code == 2, buf.getvalue()
        assert 'nothing to force' in buf.getvalue()
        assert rows(root) == []


def test_a_run_against_an_unresolvable_version_writes_nothing():
    with tree() as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = driver.main(['release', '8.8.8', '--force'], registry=STUB,
                               steps=(TRUE.name,))
        assert code == 1, buf.getvalue()
        assert 'nothing was written' in buf.getvalue()
        assert not (root / 'pm/roadmap/8.8.8-scratch').exists()
        assert rows(root) == []


def test_a_ledger_that_is_a_directory_warns_and_the_forced_write_still_lands():
    """Bites: a belt that declined to write over its own bookkeeping — the
    machine deciding telemetry outranks the operator. The status lands, the
    missing row is said out loud."""
    with tree() as root:
        (root / LEDGER).mkdir()
        code, out = run('--force')
        assert code == 0, out
        assert status(root) == driver.done_state(model.load(), 'milestone')
        assert 'WARNING' in out and 'deviation row' in out, out
