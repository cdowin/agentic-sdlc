"""test_conveyor_deviation.py — the rows a write leaves: FORCED (D12) and
DISPOSITIONED (0.5.0/D5).

Story 04's proof table, criterion 3: `--force` writes and the ledger row names
the checks that were false. The BELT mints one `deviation` row with
`outcome: forced`, whose `step` lists every false check and whose `reason`
carries each one's own sentence — and nothing else of its own. Without
`--force` a false check writes NO row: a row for a refused write is rule 4's
cardinal sin with a timestamp. (`pm` mints its own rows on the same write —
the `status` flip and, since 0.5.0/D3, an arrival `disposition` — so every
case here reads the belt's rows by SHAPE through `belt_rows`, never by
position.)

The `disposition` row a `--skip <check> "<why>"` mints is a SIBLING of that
row kind and lands on the same harness, which is why the 0.5.0/D5 cases are
here rather than in a family of their own (rule 10, "prove it once"). The two
must not bleed: a skip counted as a false check would brand a judgement a
breach, which is the failure 0.5.0/D5 exists to end, and a forced check
swallowed into a disposition would be the reverse.

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
from support.pm import with_flow  # noqa: E402

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

# The check a skip is FOR: an expensive question, recorded as ASKED whenever it
# runs. A skip that still ran it would be a `skipped:` line over a review that
# happened anyway — the flag's whole economy is that the question goes unasked.
ASKED: list[str] = []


def _spy(name: str) -> driver.Check:
    def check(ctx):
        ASKED.append(name)
        return driver.Answer.yes('asked')

    return driver.Check(name, check)


EXPENSIVE = _spy('review-recorded')
STUB = {c.name: c for c in (TRUE, FALSE, CANNOT, EXPENSIVE)}

# The DECLARATION, which is the whole of what makes a check skippable. Stock
# carries no such key, so a tree built with `tree()` alone is today's belt.
SKIPPABLE = f'[release]\nskippable = ["{EXPENSIVE.name}"]\n'
WHY = 'one-line fix, read inline'


@contextlib.contextmanager
def tree(config: str = ''):
    """A one-milestone scratch repo, entered, DECLARING its flow — `[pm.states.*]`
    has no runtime fallback (tests/support/pm.py `with_flow`)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / MDIR).mkdir(parents=True)
        (root / MFILE).write_text(MILESTONE, encoding='utf-8')
        (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
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


def belt_rows(root: Path) -> list[dict]:
    """The rows the BELT minted, in order — its `deviation` and its check
    `disposition`s, and nothing `pm` wrote on the same write.

    `pm` mints the `status` row and, since 0.5.0/D3, an ARRIVAL disposition
    beside it. That row and this belt's share one `kind` and have disjoint
    keys: an arrival's always carries `state`, a check's always carries
    `check`. Reading by SHAPE rather than by position says which collision
    this module is living with, and survives whichever way it is settled.
    """
    return [r for r in rows(root)
            if r['kind'] == ledger.KIND_DEVIATION
            or (r['kind'] == driver.KIND_DISPOSITION and 'check' in r)]


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
        assert rows(root)[0]['kind'] == ledger.KIND_STATUS, rows(root)
        written = belt_rows(root)
        assert [r['kind'] for r in written] == [ledger.KIND_DEVIATION], written
        forced = written[0]
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
        assert rows(root)[0]['kind'] == ledger.KIND_STATUS, rows(root)
        assert belt_rows(root) == [], 'a clean run minted a row of its own'
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
            written = belt_rows(root)
            assert len(written) == 1, written
            assert written[0]['reason'] == f'{split.name}: a b'
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


# --- 0.5.0/D5: the third answer — a check the caller DISPOSITIONED -----------
def test_a_declared_skip_is_never_asked_writes_the_status_and_mints_one_row():
    """The ship criterion, end to end. Bites the three ways this can go wrong
    at once: the expensive check running anyway (the skip saved nothing), the
    close being refused over a question the caller already answered (the
    batching this feature exists to end), and the judgement leaving no record
    (a skip nobody can sweep at the milestone is a skip that never happened).
    """
    ASKED.clear()
    with tree(config=SKIPPABLE) as root:
        want = driver.done_state(model.load(), 'milestone')
        code, out = run(driver.SKIP_FLAG, EXPENSIVE.name, WHY,
                        steps=(TRUE.name, EXPENSIVE.name))
        assert code == 0, out
        assert ASKED == [], f'the skipped check was asked anyway: {ASKED}'
        assert status(root) == want
        assert rows(root)[0]['kind'] == ledger.KIND_STATUS, rows(root)
        written = belt_rows(root)
        assert [r['kind'] for r in written] == [driver.KIND_DISPOSITION], \
            written
        row = written[0]
        assert row['check'] == EXPENSIVE.name and row['why'] == WHY
        assert row['grain'] == VERSION and row['operation'] == 'release'
        assert set(row) == set(driver.DISPOSITION_KEYS), 'the row keys moved'
        # `ts`, not `at`: every reader in this package sorts on `ts`, and a
        # disposition spelled otherwise files at the beginning of time.
        assert ledger.parse_ts(row['ts']) is not None, row
    assert f'[release] skipped: {EXPENSIVE.name} — "{WHY}"' in out, out
    assert f'[release] ok — {VERSION} → {want}' in out, out


def test_a_skip_with_no_reason_or_no_reason_in_it_is_refused_and_writes_nothing():
    """**An unexplained skip IS a deviation, and `--force` is already its
    verb.** Bites: `--skip review-recorded` accepted bare, which would make the
    flag a second `--force` that leaves a friendlier-looking row — the tool
    lying about what happened, in the one field the record exists for.
    """
    for argv, expected in (
            ((driver.SKIP_FLAG, EXPENSIVE.name), 'a check and a reason'),
            ((driver.SKIP_FLAG, EXPENSIVE.name, '   '), 'is not a reason'),
            ((driver.SKIP_FLAG, EXPENSIVE.name, '...'), 'no letter or digit'),
    ):
        ASKED.clear()
        with tree(config=SKIPPABLE) as root:
            code, out = run(*argv, steps=(TRUE.name, EXPENSIVE.name))
            assert code == 2, (argv, out)
            assert expected in out, (argv, out)
            assert status(root) == 'building', argv
            assert rows(root) == [], argv
            assert ASKED == [], argv


def test_a_skip_the_project_did_not_declare_is_refused_by_name():
    """Rule 9, both halves. Stock declares NOTHING skippable, so stock
    behaviour is unchanged — that is what keeps this feature inside the rule.
    Bites: the tool deciding for itself that a review is the skippable one.
    """
    ASKED.clear()
    with tree() as root:  # no `[release] skippable` at all — the stock tree
        code, out = run(driver.SKIP_FLAG, EXPENSIVE.name, WHY,
                        steps=(TRUE.name, EXPENSIVE.name))
        assert code == 2, out
        assert repr(EXPENSIVE.name) in out, out
        assert 'declared no check skippable' in out, out
        assert ASKED == [] and rows(root) == [] and status(root) == 'building'
    with tree(config=SKIPPABLE) as root:  # declared — for a DIFFERENT check
        code, out = run(driver.SKIP_FLAG, TRUE.name, WHY,
                        steps=(TRUE.name, EXPENSIVE.name))
        assert code == 2, out
        assert repr(TRUE.name) in out and repr(EXPENSIVE.name) in out, out
        assert rows(root) == [] and status(root) == 'building'


def test_a_skip_and_a_force_in_one_run_leave_two_rows_that_do_not_bleed():
    """`--force` is UNCHANGED and keeps its meaning. Bites: the skipped check
    counted among the false ones — a judgement filed as a breach, which is the
    exact reading that made an operator open another grain instead of closing
    this one — or the false check absorbed into a disposition, which is that
    lie the other way round.
    """
    ASKED.clear()
    with tree(config=SKIPPABLE) as root:
        want = driver.done_state(model.load(), 'milestone')
        code, out = run('--force', driver.SKIP_FLAG, EXPENSIVE.name, WHY,
                        steps=(TRUE.name, EXPENSIVE.name, FALSE.name))
        assert code == 0, out
        assert status(root) == want
        assert rows(root)[0]['kind'] == ledger.KIND_STATUS, rows(root)
        written = belt_rows(root)
        assert [r['kind'] for r in written] == [
            ledger.KIND_DEVIATION, driver.KIND_DISPOSITION], written
        deviation, disposition = written
        assert deviation['step'] == FALSE.name, 'the skip landed in the row'
        assert deviation['outcome'] == driver.FORCED
        assert EXPENSIVE.name not in deviation['reason'], deviation
        assert disposition['check'] == EXPENSIVE.name
    assert f'[release] forced — {VERSION} → {want} over 1 false check(s)' \
        in out, out
    assert f'[release] skipped: {EXPENSIVE.name} — "{WHY}"' in out, out
