"""test_conveyor_deviation.py — the rows a write leaves: FORCED (D12) and
DISPOSITIONED (0.5.0/D5, folded by D6).

Story 04's proof table, criterion 3: `--force` writes and the ledger row names
the checks that were false. The BELT mints one `deviation` row with
`outcome: forced`, whose `step` lists every false check and whose `reason`
carries each one's own sentence — and nothing else of its own. Without
`--force` a false check writes NO row: a row for a refused write is rule 4's
cardinal sin with a timestamp. (`pm` mints its own rows on the same write —
the `status` flip and the arrival's `disposition` — so every case here reads
the belt's `deviation` rows by KIND through `belt_rows`, never by position.)

A `--skip <check> "<why>"` mints NO row of its own: the close is an arrival,
and the judgement is a field on that arrival's one `disposition` row
(0.5.0/D6). The 0.5.0/D5 cases live here because they share this harness
(rule 10, "prove it once") and because the two records must not bleed: a skip
counted as a false check would brand a judgement a breach, which is the
failure D5 exists to end, and a forced check swallowed into a disposition
would be the reverse.

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
from agentic_sdlc.core import frontmatter  # noqa: E402
from agentic_sdlc.repo.conveyor import driver  # noqa: E402
from agentic_sdlc.repo.pm import ledger, vocabulary  # noqa: E402

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
    """The `deviation` rows the BELT minted, in order — read by KIND, never by
    position, because `pm` writes the `status` and `disposition` rows of the
    same arrival into this file too."""
    return [r for r in rows(root) if r['kind'] == ledger.KIND_DEVIATION]


def dispositions(root: Path) -> list[dict]:
    """The arrival dispositions on this ledger. ONE shape carries the word
    (0.5.0/D6), so this is the kind and nothing else."""
    return [r for r in rows(root) if r['kind'] == ledger.KIND_DISPOSITION]


def status(root: Path) -> str:
    return frontmatter.field_of(root / MFILE, 'status')


# --- criterion 3 --------------------------------------------------------------
def test_force_writes_the_status_and_one_row_naming_the_false_checks():
    """Bites: a forced write that leaves no account of what it forced — the
    invisible deviation this row exists to end — or one that writes more
    than the two rows a run may leave."""
    with tree() as root:
        want = driver.done_state(vocabulary.load(), 'milestone')
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
        assert status(root) == driver.done_state(vocabulary.load(), 'milestone')
        assert 'WARNING' in out and 'deviation row' in out, out


# --- 0.5.0/D5: the third answer — a check the caller DISPOSITIONED -----------
def test_a_declared_skip_is_never_asked_and_rides_the_arrivals_one_row():
    """The ship criterion, end to end. Bites the four ways this can go wrong
    at once: the expensive check running anyway (the skip saved nothing), the
    close being refused over a question the caller already answered (the
    batching this feature exists to end), the judgement leaving no record (a
    skip nobody can sweep at the milestone is a skip that never happened), and
    the skip filed as a SECOND row — one event described as two, which is what
    0.5.0/D6 folded and what a per-state walk would then miscount.
    """
    ASKED.clear()
    with tree(config=SKIPPABLE) as root:
        want = driver.done_state(vocabulary.load(), 'milestone')
        code, out = run(driver.SKIP_FLAG, EXPENSIVE.name, WHY,
                        steps=(TRUE.name, EXPENSIVE.name))
        assert code == 0, out
        assert ASKED == [], f'the skipped check was asked anyway: {ASKED}'
        assert status(root) == want
        assert [r['kind'] for r in rows(root)] == [
            ledger.KIND_STATUS, ledger.KIND_DISPOSITION], rows(root)
        assert belt_rows(root) == [], 'a clean skip minted a deviation'
        row = dispositions(root)[0]
        assert row['grain'] == VERSION and row['state'] == want
        assert row['skipped'] == [{'check': EXPENSIVE.name, 'why': WHY}]
        assert set(row) <= set(ledger.DISPOSITION_KEYS), 'the row keys moved'
        # `ts`, not `at`: every reader in this package sorts on `ts`, and a
        # disposition spelled otherwise files at the beginning of time.
        assert ledger.parse_ts(row['ts']) is not None, row
    assert f'[release] skipped: {EXPENSIVE.name} — "{WHY}"' in out, out
    assert f'[release] ok — {VERSION} → {want}' in out, out


# The fork a belt's write prints on the way past. Declared here because the
# thing under test is what SURVIVES the belt, and a report with nothing in it
# survives anything.
ASK = 'who signed this off?'
ANSWERS = ('--by me', '--by agent <type>')


def test_the_belt_hands_the_arrivals_report_on_as_LINES():
    """The pressure line's ship criterion names three surfaces — every `pm`
    write, every BELT write and every `check pm` run — and this is the belt.

    The writer captures the arrival's whole report and used to join it into
    ONE 555-character sentence, so at `close` — the surface where the question
    is actually raised — the fork's two pasteable commands stopped being
    commands. Bites the re-flow, not the presence: the answers are asserted as
    whole LINES that END in the command they paste.
    """
    # From the SEED the fixture's flow is rendered from, not from this
    # repo's config: the declaration is written before the tree is entered.
    want = vocabulary.DEFAULT_FLOWS['milestone']['done'][0]
    with tree(config=(f'[pm.arrive.milestone.{want}]\nask     = "{ASK}"\n'
                      'answers = ['
                      + ', '.join(f'"{a}"' for a in ANSWERS) + ']\n')) as root:
        code, out = run(steps=(TRUE.name,))
        assert code == 0, out
        assert status(root) == want
    lines = out.splitlines()
    assert [ln for ln in lines if ln.startswith('[release] write: ')], out
    # Through the stock wiring, each answer INSIDE the one ARGS value; a
    # placeholder stays bare so the line reads as its synopsis.
    for paste in (f"make pm ARGS='milestone {want} {VERSION} --by me'",
                  f"make pm ARGS='milestone {want} {VERSION} --by agent "
                  f"<type>'"):
        assert [ln for ln in lines if ln.endswith(paste)], (paste, out)
    assert ASK in ' '.join(lines), out


def test_a_refused_close_leaves_no_skip_behind_it():
    """The ORDERING the fold bought. The belt used to mint its skip rows
    DURING the check run; a run that then refused left a judgement on the
    record for a close that never happened — rule 4's second sin with a
    timestamp. Collected and emitted once, at the arrival, there is nothing
    to leave behind."""
    ASKED.clear()
    with tree(config=SKIPPABLE) as root:
        code, out = run(driver.SKIP_FLAG, EXPENSIVE.name, WHY,
                        steps=(FALSE.name, EXPENSIVE.name))
        assert code == 1, out
        assert status(root) == 'building'
        assert rows(root) == [], 'a refused close recorded a judgement'
        assert ASKED == []
    assert f'[release] skipped: {EXPENSIVE.name} — "{WHY}"' in out, out


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


def test_a_skip_and_a_force_in_one_run_leave_two_records_that_do_not_bleed():
    """`--force` is UNCHANGED and keeps its meaning. Bites: the skipped check
    counted among the false ones — a judgement filed as a breach, which is the
    exact reading that made an operator open another grain instead of closing
    this one — or the false check absorbed into a disposition, which is that
    lie the other way round. Two ACTS, two words, and the fold did not merge
    them: a `deviation` row for the breach, a `skipped` field for the
    judgement.
    """
    ASKED.clear()
    with tree(config=SKIPPABLE) as root:
        want = driver.done_state(vocabulary.load(), 'milestone')
        code, out = run('--force', driver.SKIP_FLAG, EXPENSIVE.name, WHY,
                        steps=(TRUE.name, EXPENSIVE.name, FALSE.name))
        assert code == 0, out
        assert status(root) == want
        assert [r['kind'] for r in rows(root)] == [
            ledger.KIND_STATUS, ledger.KIND_DISPOSITION,
            ledger.KIND_DEVIATION], rows(root)
        deviation = belt_rows(root)[0]
        disposition = dispositions(root)[0]
        assert deviation['step'] == FALSE.name, 'the skip landed in the row'
        assert deviation['outcome'] == driver.FORCED
        assert EXPENSIVE.name not in deviation['reason'], deviation
        assert disposition['skipped'] == [{'check': EXPENSIVE.name,
                                           'why': WHY}]
        assert FALSE.name not in ledger.dumps(disposition), disposition
    assert f'[release] forced — {VERSION} → {want} over 1 false check(s)' \
        in out, out
    assert f'[release] skipped: {EXPENSIVE.name} — "{WHY}"' in out, out
