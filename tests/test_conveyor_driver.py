"""test_conveyor_driver.py — the machine: every check, then at most one write.

`driver.run` is load-bearing (CLAUDE.md rule 10 names it), and everything it
decides is a function call away: scripted checks, a recording writer, a
recording deviation callback, no filesystem. What is proven here is the
D12 shape itself — every check asked and printed, the write happening exactly
when it should, UNVERIFIABLE counting as false, a `ConfigError` at a check
stopping the run before the write (D11) — plus criterion 4 of story 04's
proof table at the verb: `release` prints the caller's list and writes
nothing but the status.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import FLOW_TOML  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.core import frontmatter  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402
from agentic_sdlc.repo.pm import ledger, vocabulary  # noqa: E402

CTX = driver.Context(root=Path('.'), operation='release', version='1.0.0')


def yes(name: str) -> driver.Check:
    return driver.Check(name, lambda c: driver.Answer.yes(f'{name} holds'))


def no(name: str) -> driver.Check:
    return driver.Check(name, lambda c: driver.Answer.no(f'{name} fails'))


def cannot(name: str) -> driver.Check:
    return driver.Check(
        name, lambda c: driver.Answer.unverifiable(f'{name} unknown'))


class Writer:
    """Records every write it was asked for — and every check the caller
    ANSWERED, because the write is the arrival those answers are recorded on
    (0.5.0/D6); answers what it was told to."""

    def __init__(self, landed: bool = True):
        self.landed = landed
        self.calls: list[str] = []
        self.skipped: list[tuple[tuple[str, str], ...]] = []

    def __call__(self, ctx: driver.Context, state: str,
                 skipped: tuple[tuple[str, str], ...] = ()
                 ) -> tuple[bool, str]:
        self.calls.append(state)
        self.skipped.append(tuple(skipped))
        return self.landed, f'wrote {state}'


class Recorder:
    def __init__(self):
        self.calls: list[list[tuple[str, str]]] = []

    def __call__(self, false) -> str:
        self.calls.append(list(false))
        return ''


def run(checks, names=None, **kw) -> driver.Result:
    registry = {c.name: c for c in checks}
    return driver.run(registry, tuple(registry) if names is None else names,
                      CTX, **kw)


# --- the shape ----------------------------------------------------------------
def test_every_check_runs_and_prints_one_line_and_a_false_one_stops_the_write():
    """Bites: a run that stops at the first false check (one error per run is
    a loop of runs), or one that writes anyway."""
    writer = Writer()
    result = run([yes('a'), no('b'), cannot('c'), yes('d')], state='done',
                 write=writer)
    assert result.exit_code == 1
    assert result.false == ('b', 'c')
    assert result.written == ''
    assert writer.calls == []
    assert list(result.lines) == [
        '[release] ok: a — a holds',
        '[release] error: b: b fails',
        '[release] unverifiable: c: c unknown',
        '[release] ok: d — d holds',
        '[release] error — 2 check(s) false; no status written',
    ]


def test_all_true_calls_the_writer_exactly_once_with_the_state():
    writer = Writer()
    recorder = Recorder()
    result = run([yes('a'), yes('b')], state='shipped', write=writer,
                 record=recorder)
    assert result.exit_code == 0
    assert writer.calls == ['shipped']
    assert result.written == 'shipped'
    assert recorder.calls == [], 'a clean write minted a deviation row'
    assert result.lines[-1] == '[release] ok — 1.0.0 → shipped'


def test_force_writes_over_false_checks_and_hands_them_to_the_recorder():
    """Bites: a forced write whose row does not name what was forced."""
    writer = Writer()
    recorder = Recorder()
    result = run([no('a'), cannot('b'), yes('c')], state='done', force=True,
                 write=writer, record=recorder)
    assert result.exit_code == 0
    assert writer.calls == ['done']
    assert recorder.calls == [[('a', 'a fails'), ('b', 'b unknown')]]
    assert result.lines[-1] == ('[release] forced — 1.0.0 → done over 2 '
                                'false check(s)')


def test_a_refused_write_is_exit_1_and_no_deviation_row():
    """Bites: `pm` refusing the flip while the belt reports `forced` and
    records a deviation over nothing."""
    writer = Writer(landed=False)
    recorder = Recorder()
    result = run([no('a')], state='done', force=True, write=writer,
                 record=recorder)
    assert result.exit_code == 1
    assert result.written == ''
    assert recorder.calls == []
    assert result.lines[-1].startswith('[release] error — the write was refused')


def test_checks_only_reports_ok_with_the_census_and_writes_nothing():
    writer = Writer()
    result = run([yes('a'), yes('b')], state='', write=writer)
    assert result.exit_code == 0 and writer.calls == []
    assert result.lines[-1] == '[release] ok — 2 check(s) true; nothing to write'


def test_a_check_that_raises_is_unverifiable_and_counts_as_false():
    """Bites: a latent crash in check 3 surfacing as a traceback at exit 1
    (rule 6's code for findings) — or, worse, being skipped over."""
    def boom(ctx):
        raise ValueError('tuple.index(x): x not in tuple')

    writer = Writer()
    result = run([driver.Check('crash', boom), yes('b')], state='done',
                 write=writer)
    assert result.exit_code == 1 and writer.calls == []
    assert result.lines[0].startswith('[release] unverifiable: crash: ValueError')
    assert result.lines[1] == '[release] ok: b — b holds'


def test_a_ConfigError_at_a_check_is_exit_2_and_nothing_after_it_runs_or_writes():
    """D11. Bites: a config typo landing at exit 1 beside genuine findings,
    a check after the failed reader still running, or the write landing
    over a declaration this machine could not read."""
    asked: list[str] = []

    def unreadable(ctx):
        raise ConfigError('[release.version_files] x must be a regex string')

    def spy(ctx):
        asked.append('c')
        return driver.Answer.yes()

    writer = Writer()
    result = run([yes('a'), driver.Check('b', unreadable),
                  driver.Check('c', spy)], state='done', force=True,
                 write=writer)
    assert result.exit_code == 2
    assert result.refused.startswith("check 'b': [release.version_files]")
    assert asked == [] and writer.calls == []
    assert result.lines[0] == '[release] ok: a — a holds'
    assert result.lines[-1].endswith('no status written')


def test_an_empty_list_or_an_unknown_name_is_exit_2_not_ok():
    """Bites: `ok` over a census of zero (rule 4)."""
    assert run([yes('a')], names=()).exit_code == 2
    assert run([yes('a')], names=('a', 'zzz')).exit_code == 2
    assert 'zzz' in run([yes('a')], names=('a', 'zzz')).lines[0]


# --- the state comes from the config ------------------------------------------
@contextlib.contextmanager
def _tree(devkit: str):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        pool = root / 'pm/roadmap/milestones'
        pool.mkdir(parents=True)
        (pool / '1.0.0.md').write_text(
            '---\nid: "1.0.0"\nkind: milestone\nname: one\n'
            'status: building\nbranch: milestone/1.0.0\n---\n\n# one\n',
            encoding='utf-8')
        (root / 'devkit.toml').write_text(devkit, encoding='utf-8')
        (root / '.git').mkdir()  # a MARKER: `repo_root` walks for it
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


def test_done_state_is_the_first_of_the_done_category_as_declared():
    """Bites: `done` as a literal anywhere in the driver. The word is the
    project's, and a tree that opens its `done` category with `shipped`
    writes `shipped`."""
    head, marker, tail = FLOW_TOML.partition('[pm.states.milestone]')
    tail = re.sub(r'^(\s*done\s*=\s*\[)', r'\1"shipped", ', tail, count=1,
                  flags=re.MULTILINE)
    with _tree(head + marker + tail):
        assert driver.done_state(vocabulary.load(), 'milestone') == 'shipped'
    with _tree(FLOW_TOML):
        flow = vocabulary.flow_of(vocabulary.load(), 'milestone')
        assert driver.done_state(vocabulary.load(), 'milestone') == \
            flow.by_category[vocabulary.DONE_CATEGORY][0]


# --- criterion 4: release prints the caller's list, writes only the status ---
def test_release_prints_the_callers_list_and_writes_nothing_but_the_status():
    """Bites: any second write surviving D12 — a bump, a retitle, a push, a
    tag — and a release that closes without telling the caller what is now
    theirs. Every file is snapshotted; only the milestone's status line and
    the ledger may differ."""
    registry = {c.name: c for c in (yes('a'), yes('b'))}
    with _tree(FLOW_TOML) as root:
        before = {str(p.relative_to(root)): p.read_bytes()
                  for p in root.rglob('*') if p.is_file()}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = driver.main(['release', '1.0.0'], registry=registry,
                               steps=('a', 'b'))
        out = buf.getvalue()
        assert code == 0, out
        after = {str(p.relative_to(root)): p.read_bytes()
                 for p in root.rglob('*') if p.is_file()}
        changed = {rel for rel in before.keys() | after.keys()
                   if before.get(rel) != after.get(rel)}
        assert changed == {'pm/roadmap/milestones/1.0.0.md',
                           'pm/roadmap/ledgers/1.0.0.jsonl'}, changed
        want = driver.done_state(vocabulary.load(), 'milestone')
        assert frontmatter.field_of(root / 'pm/roadmap/milestones/1.0.0.md',
                              'status') == want
        rows = [r.data for r in
                ledger.read_rows(root / 'pm/roadmap/ledgers/1.0.0.jsonl')]
        assert rows[0]['kind'] == ledger.KIND_STATUS, rows
        # The BELT minted none of its own: no `deviation`, and no `disposition`
        # carrying a `check`. Everything else in this file is `pm`'s, written
        # by the status flip — including the ARRIVAL disposition (0.5.0/D3),
        # which shares the word and is told apart by carrying `state` where a
        # check's carries `check`.
        assert not [r for r in rows
                    if r['kind'] == ledger.KIND_DEVIATION or 'check' in r], rows
    lines = out.strip().split('\n')
    nexts = [line for line in lines if line.startswith('next: ')]
    assert len(nexts) == len(steps.AFTER['release']), out
    assert lines.index(f'[release] ok — 1.0.0 → {want}') < lines.index(nexts[0])
    joined = '\n'.join(nexts)
    assert 'v1.0.0' in joined and 'milestone/1.0.0' in joined, joined
    assert '{' not in joined, 'an after-list placeholder was left unfilled'
    # The tag is cut on the mainline's merge commit, so the LAST act is
    # bringing the local mainline up to it — fast-forward only, never a merge.
    assert nexts[-1] == ('next: sync the local mainline to the tagged merge: '
                         '`git switch main && git pull --ff-only`'), nexts[-1]
    # `retitle` was here until 0.6.0, and it is the reason this list is
    # spelled out: `CHANGELOG.md` retired, and the belt went on telling the
    # operator running that very release to retitle a section in the file it
    # had just deleted. A `next:` line is an instruction, so a retired one is
    # `bg-the-shipped-rules-name-retired-behaviour` on the surface an operator
    # is standing on at the moment of the release.
    for word in ('changelog', 'push', 'PR', 'tag', 'prove'):
        assert word in joined, word
    assert 'Unreleased' not in joined, (
        'the release belt still names a section of a file this package '
        'retired in 0.6.0')


def test_an_undeclared_done_category_is_exit_2_before_any_check_runs():
    """Bites: every check printing ok and THEN the reader failing on the
    word to write — the D8 'before the run' moment arriving late."""
    asked: list[str] = []

    def spy(ctx):
        asked.append('a')
        return driver.Answer.yes()

    with _tree('[pm]\n') as root:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code = driver.main(['release', '1.0.0'],
                               registry={'a': driver.Check('a', spy)},
                               steps=('a',))
        assert code == 2, buf.getvalue()
        assert asked == []
        assert not (root / 'pm/roadmap/ledgers/1.0.0.jsonl').exists()


# --- the subject grammar and the help ------------------------------------------
@pytest.mark.parametrize('value', [
    '', ' ', '..', '.', 'a/b', 'a b', '*', '/abs', 'x' * 129,
    'a\\b', 'https://x',
])
def test_the_version_refusal_matrix_is_exit_2(value, capsys):
    """Bites: a hostile or mistyped version joined onto the roadmap path."""
    assert driver.version_defect(value) != '', repr(value)
    assert driver.main(['release', value]) == 2
    capsys.readouterr()


def test_help_exits_zero_for_every_verb(capsys, monkeypatch):
    """Rule 11's read side: `--skip` is a capability, and a capability nobody
    can find is a capability you do not have. Bites: the flag shipped and
    named nowhere the operator stands — which is how the thirteenth grain got
    opened instead of the twelfth close.

    `adopt` names it too, as the thing it REFUSES: a flag that works one belt
    over and is silent here is the same defect wearing the other face.
    """
    for argv in (['release', '--help'], ['adopt', '-h'], ['close', 'help'],
                 ['close', 'story', '--help'], ['--help']):
        assert driver.main(argv) == 0, argv
        out = capsys.readouterr().out
        assert driver.SKIP_FLAG in out, argv
        assert 'stops' not in out, argv
    assert driver.main(['adopt', '-h']) == 0
    adopt = capsys.readouterr().out
    assert 'neither is accepted here' in adopt, adopt
    # #25: adopt's help described the WRITING belt — `<version>` as "a grain
    # id", `ok — <grain> → <state>`, `forced`, `next:` "after a write" — while
    # saying it writes nothing. Every line it names is one it can print.
    for claim in ('a grain id', 'forced', '→', 'after a write', 'skipped:'):
        assert claim not in adopt, claim
    for line in ('[adopt] ok — N check(s) true; nothing to write',
                 '[adopt] error — N check(s) false; no status written',
                 'a version — '):
        assert line in adopt, line
    # And off `WRITES`, never off the belt's name: `release` declared
    # checks-only is described as one, so the next such belt needs no case.
    assert '[release] forced — <version> → <state>' in driver.render_usage(
        'release')
    # A writing belt over a grain already there exits 0 having written nothing
    # (`pm story done`'s no-op), and its help says so.
    assert '0 written (or nothing to write)' in driver.render_usage(driver.OP_STORY)
    monkeypatch.setitem(driver.WRITES, 'release', '')
    checks_only = driver.render_usage('release')
    assert 'forced' not in checks_only and 'after a write' not in checks_only
    assert '[release] ok — N check(s) true; nothing to write' in checks_only


# --- the plan supplies the version, and refuses one out of order -------------
def _plan(root: Path, *versions: str) -> None:
    body = '\n'.join(f'  - "{v}"' for v in versions)
    (root / 'pm/roadmap/releases.md').write_text(
        f'---\norder:\n{body}\n---\n\nThe plan.\n', encoding='utf-8')


def _claim(root: Path, mid: str, version: str, status: str) -> None:
    (root / 'pm/roadmap/milestones' / f'{mid}.md').write_text(
        f'---\nid: "{mid}"\nkind: milestone\nname: {mid}\n'
        f'status: {status}\nversion: "{version}"\n---\n\n# {mid}\n',
        encoding='utf-8')


def _release(argv, root):
    """`driver.main` with scripted checks, capturing both streams."""
    registry = {c.name: c for c in (yes('a'),)}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = driver.main(argv, registry=registry, steps=('a',))
    return code, buf.getvalue()


def test_release_with_no_argument_takes_the_current_version_from_the_plan():
    """The plan already knows which version is current; making the human
    retype it is how a typo ships the wrong number."""
    with _tree(FLOW_TOML) as root:
        _plan(root, '0.9.0', '1.0.0')
        _claim(root, '0.9.0', '0.9.0', 'done')
        # The fixture's own milestone must CLAIM 1.0.0: an entry nothing claims
        # is unverifiable, and the resolver refuses to guess (review F1).
        frontmatter.set_field(root / 'pm/roadmap/milestones/1.0.0.md',
                        'version', '"1.0.0"')
        code, out = _release(['release'], root)
        assert code == 0, out
        assert '1.0.0' in out
        assert 'the plan names 1.0.0 as the current release' in out


def test_a_version_that_is_not_current_is_refused_naming_both():
    """Shipping out of order is exactly what a belt should stop."""
    with _tree(FLOW_TOML) as root:
        _plan(root, '0.9.0', '1.0.0')
        _claim(root, '0.9.0', '0.9.0', 'building')
        frontmatter.set_field(root / 'pm/roadmap/milestones/1.0.0.md',
                        'version', '"1.0.0"')
        code, out = _release(['release', '1.0.0'], root)
        assert code == 2, out
        assert "'0.9.0'" in out          # what the plan says is current
        assert '1.0.0' in out            # what was asked for
        assert 'nothing was written' in out


def test_no_plan_at_all_still_honours_an_explicit_version():
    """A tree that has not adopted the plan is not locked out of `release`."""
    with _tree(FLOW_TOML) as root:
        code, out = _release(['release', '1.0.0'], root)
        assert code == 0, out


def test_no_plan_and_no_argument_is_refused_naming_pm_order():
    with _tree(FLOW_TOML) as root:
        code, out = _release(['release'], root)
        assert code == 2, out
        # The remedy a refusal names must itself be a live verb: `pm
        # order` retired into `pm add` against the root.
        assert "`make pm ARGS='add roadmap <milestone-id>'`" in out
        assert 'pm order' not in out


def test_every_entry_shipped_and_no_argument_is_refused_rather_than_guessed():
    with _tree(FLOW_TOML) as root:
        _plan(root, '0.9.0')
        _claim(root, '0.9.0', '0.9.0', 'done')
        code, out = _release(['release'], root)
        assert code == 2, out
        # The remedy a refusal names must itself be a live verb: `pm
        # order` retired into `pm add` against the root.
        assert "`make pm ARGS='add roadmap <milestone-id>'`" in out
        assert 'pm order' not in out


# --- the middle tap: one row per check resolved (0.5.0) ----------------------
# `rung.enter` and `rung.leave` had producers; this one did not, so a consumer
# reading the stream saw a belt start and finish with nothing between. The
# claims that would cost real time if they broke: one row per check ASKED and
# none for a check nobody asked, the row saying what the LINE said, and every
# field derived from the registry or the invocation rather than written here.

class Taps:
    """A recording stand-in for `driver.Verdicts` — same one method. The real
    one is exercised over a tree below; what this proves is WHEN the belt asks
    for a row, which is a function call away (rule 10)."""

    def __init__(self):
        self.rows: list[tuple[str, driver.Answer]] = []

    def say(self, check: str, answer: driver.Answer) -> None:
        self.rows.append((check, answer))


def test_one_verdict_row_per_check_asked_and_none_for_one_the_caller_answered():
    """A skipped check is the caller's judgement recorded on the arrival's
    disposition row (D6). A verdict for it here would be this package's
    cardinal sin: a verdict nobody produced, indistinguishable afterwards from
    one a check really returned."""
    taps = Taps()
    result = run([yes('a'), no('b'), cannot('c')], state='done',
                 write=Writer(), force=True, skips={'a': 'answered already'},
                 record=Recorder(), verdicts=taps)
    assert result.skipped == ('a',)
    assert [name for name, _ in taps.rows] == ['b', 'c']
    assert [driver.VERDICT_WORDS[a.truth] for _, a in taps.rows] == [
        'error', 'unverifiable']


def test_the_row_carries_the_sentence_the_line_carried_including_the_defect():
    """A check that answers no and gives no reason has a defect, and the belt
    prints that in place of the missing reason. The ROW says the same thing:
    two carriers of one fact that disagree is the drift rule 6 is about."""
    taps = Taps()
    silent = driver.Check('b', lambda c: driver.Answer.no())
    result = run([yes('a'), silent], state='', verdicts=taps)
    assert [name for name, _ in taps.rows] == ['a', 'b']
    for name, answer in taps.rows:
        row = driver.verdict_row('release', '1.0.0', name, answer, 'ran')
        said = [ln for ln in result.lines if f'{row["verdict"]}: {name}' in ln]
        assert len(said) == 1, result.lines
        assert row['detail'] in said[0], said[0]
    assert dict(taps.rows)['b'].detail == driver.NO_REASON


def test_what_a_check_RAN_is_the_command_the_protocol_table_renders():
    """`ran` is derived, and the derivation is the one `install-sdlc` uses —
    the project's command, the shipped one, or the literal. A third answer
    here would be a document describing a run that did not happen."""
    names = steps.steps_for('feature', driver.registry_for('feature'))
    ran = driver.ran_for('feature', names, driver.registry_for('feature'))
    assert set(ran) == set(names)
    for name, said in ran.items():
        assert said == steps.SHIPPED_ACTION.get(name, steps.READS_THE_TREE)
    assert steps.READS_THE_TREE in ran.values(), (
        'no check in the feature list reads the tree — the literal half of '
        'the vocabulary is no longer exercised')


def test_a_run_given_no_tap_behaves_exactly_as_it_did():
    """The consumer that declares no sink gets today's lines and today's exit
    code: this feature adds a carrier, never replaces one."""
    checks = [yes('a'), no('b')]
    bare = run(checks, state='done', write=Writer())
    tapped = run(checks, state='done', write=Writer(), verdicts=Taps())
    assert (bare.lines, bare.exit_code) == (tapped.lines, tapped.exit_code)


# --- the three taps, on a belt, in the tree ----------------------------------
EMIT = '\n[emit]\nsink = "ledger"\n'


def _belt(argv, root, checks):
    """`driver.main` with scripted checks over `_tree`, and every row the run
    left anywhere in the roadmap, in file order."""
    registry = {c.name: c for c in checks}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = driver.main(argv, registry=registry, steps=tuple(registry))
    rows = [r.data for path in sorted((root / 'pm/roadmap').rglob('*.jsonl'))
            for r in ledger.read_rows(path)]
    return code, buf.getvalue(), rows


@pytest.mark.parametrize('operation,checks,code,leaves', [
    ('release', [yes('a'), yes('b')], 0, True),
    ('release', [yes('a'), no('b')], 1, False),
    # `adopt` is checks only (D12): it emits its verdicts and never a
    # `rung.leave`, because this tap is the BELT's and not the write's.
    ('adopt', [yes('a'), yes('b')], 0, False),
])
def test_a_belt_that_writes_nothing_emits_its_verdicts_and_no_leave_event(
        operation, checks, code, leaves):
    """The ship criterion and the decision under it in one case. THERE IS NO
    `rung.exit_failed`: a belt that writes nothing emits `check.verdict` rows
    and no `rung.leave`, and the ABSENCE is the signal — inventing a fourth
    kind to say "the thing did not happen" is the tool narrating rather than
    recording."""
    with _tree(FLOW_TOML + EMIT) as root:
        _claim(root, '1.0.0', '1.0.0', 'building')
        got, out, rows = _belt([operation, '1.0.0'], root, checks)
        assert got == code, out
        verdicts = [r for r in rows if r['kind'] == ledger.KIND_VERDICT]
        assert [r['check'] for r in verdicts] == [c.name for c in checks]
        assert [r['verdict'] for r in verdicts].count('error') == code
        assert all(r['rung'] == operation and r['grain'] == '1.0.0'
                   for r in verdicts), verdicts
        assert bool([r for r in rows
                     if r['kind'] == ledger.KIND_LEAVE]) is leaves, rows
        # And no fourth kind: every event this run emitted spells one of the
        # three taps `check pm`'s U3 counts.
        events = [r['kind'] for r in rows if '.' in r['kind']]
        assert set(events) <= set(ledger.EVENT_KEYS), events
