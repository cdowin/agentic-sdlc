"""test_conveyor_close.py — the two INNER belts under D12: checks, then one write.

Story 04's proof table, criteria 1 and 2, at the belt altitude: on a scratch
repo with a real git history, `close story` and `close feature` run every
check, print one line each, and then write EXACTLY the grain's status — to the
first state of its kind's `done` category as the tree's own devkit.toml
declares it — or write nothing at all. Every claim about what a belt DID is a
claim about bytes on disk, never about the transcript.

Every write-verb test here works on a scratch tree, never on a fixture in
place.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import with_flow  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import cli  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.core import frontmatter  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402
from agentic_sdlc.repo.pm import ledger, vocabulary  # noqa: E402

VERSION = '9.9.9'
FEATURE_ID = f'{VERSION}/alpha'
STORY_ID = f'{FEATURE_ID}/s1'
MDIR = f'pm/roadmap/{VERSION}-scratch'
FDIR = f'{MDIR}/features/alpha'
SFILE = f'{FDIR}/stories/s1.md'
FFILE = f'{FDIR}/feature.md'
LEDGER = f'{MDIR}/ledger.jsonl'
RECORD = 'docs/reviews/alpha.md'

MILESTONE = f'''---
id: "{VERSION}"
name: A scratch milestone
status: building
branch: milestone/{VERSION}
---

# A scratch milestone
'''

# `[verify]` has to be declared or `verify --story` exits 2 naming the section.
# The story rung is a make target, so the stub Makefile's `unit` IS the rung.
CONFIG = '''[verify]
story     = "make unit"
feature   = "make test"
milestone = "make milestone"
'''

MAKEFILE = 'unit:\n\t@true\n\ntest:\n\t@true\n\nmilestone:\n\t@true\n'
RED_MAKEFILE = MAKEFILE.replace('unit:\n\t@true', 'unit:\n\t@exit 1')

VERDICT_BLOCK = '''```
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| W1 | MAJOR | landed in-place |
```
'''
# MAJOR in the block above, so `open` here is a BLOCKING open finding — since
# 0.3.0 severity gates the hold, and what this fixture is for is the easiest
# false green in the belt, not the severity rule.
OPEN_BLOCK = VERDICT_BLOCK.replace('landed in-place', 'open')

# The other side: read, named, and not a blocker.
NIT_OPEN_BLOCK = OPEN_BLOCK.replace('| W1 | MAJOR |', '| W1 | NIT |')


def feature_doc(status: str = 'planning', reviewed: str = '') -> str:
    return (f'---\nid: {FEATURE_ID}\nmilestone: "{VERSION}"\n'
            f'name: Alpha\nstatus: {status}\nreviewed: {reviewed}\n'
            f'phase: 1\n---\n\n# Alpha\n')


def story_doc(status: str = 'building', evidence: str = '') -> str:
    return (f'---\nid: {FEATURE_ID}/s1\nfeature: {FEATURE_ID}\n'
            f'milestone: "{VERSION}"\nname: One\nstatus: {status}\n---\n\n'
            f'# One\n\n{evidence}')


DONE_LINE = 'done: 3a42f19ad0 — the belt walks\n'


@contextlib.contextmanager
def tree(files: dict[str, str] | None = None, *, story: str = 'building',
         evidence: str = DONE_LINE, feature: str = 'planning',
         reviewed: str = '', config: str = CONFIG):
    """A scratch repo with a milestone, a feature and one story, entered.

    `config` is this tree's devkit.toml MINUS the flow declaration, which is
    APPENDED for you (tests/support/pm.py `with_flow`). One commit: the story
    rung reads no range, so the `done:` line's hash only has to be the SHAPE
    `evidence-written` checks.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        payload = {
            f'{MDIR}/milestone.md': MILESTONE,
            FFILE: feature_doc(feature, reviewed),
            SFILE: story_doc(story, evidence),
            'devkit.toml': with_flow(config),
            'Makefile': MAKEFILE,
            'src/thing.py': 'x = 1\n',
        }
        payload.update(files or {})
        for rel, body in payload.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.email=t@example.invalid',
                        '-c', 'user.name=t', 'commit', '-qm', 'base'],
                       cwd=root, check=True)
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


def close(*args: str) -> int:
    return cli.main(['close', *args])


def status_of(root: Path, rel: str) -> str:
    return frontmatter.field_of(root / rel, 'status')


def rows(root: Path) -> list[dict]:
    path = root / LEDGER
    return [r.data for r in ledger.read_rows(path)] if path.exists() else []


def blocked_close(root: Path, grain: str, operation: str,
                  check: str) -> None:
    """A refused close preserves its failed checks as one lifecycle row."""
    events = rows(root)
    assert len(events) == 1, events
    assert events[0]['kind'] == ledger.KIND_BELT_BLOCKED
    assert events[0]['grain'] == grain
    assert events[0]['operation'] == operation
    assert events[0]['state'] == 'blocked'
    assert events[0]['checks'] == [check]


# ONE WRITE IS ONE ARRIVAL, and an arrival mints two rows: the `status` flip
# and the `disposition` that answers the state it reached (0.5.0/D3, folded by
# D6). What these cases claim is that ONE GRAIN moved — so they name the
# shape, never the length of the file.
ARRIVAL_KINDS = [ledger.KIND_STATUS, ledger.KIND_DISPOSITION]


def arrival(root: Path, grain: str, to: str) -> None:
    """Assert the ledger holds exactly one arrival, and that it is this
    grain reaching this state."""
    written = rows(root)
    assert [r['kind'] for r in written] == ARRIVAL_KINDS, written
    flip, answer = written
    assert (flip['grain'], flip['to']) == (grain, to), written
    assert (answer['grain'], answer['state']) == (grain, to), written


# The TREE's ledger — where a row naming no grain lands (0.4.0/D3) — is not a
# belt write, so it is not graded as one. A check the belt RUNS may file
# telemetry about its own run: the gate wrapper records what a target COST on
# every real gate, and `verify` records its VERDICT and the tree state it ran
# on beside it. The belt's one write is a grain's status, and the milestone
# ledger (`LEDGER`, the file a status row lands in) is graded byte for byte.
GRAINLESS_LEDGER = 'pm/roadmap/ledger.jsonl'
# 0.12.0: the same telemetry now lands in the untracked local ledger; it is
# read the same way, so only a check's own run rows are allowed there too.
LOCAL_LEDGER = 'pm/roadmap/ledger.local.jsonl'

# By KIND, not by file. A whole-file exclusion also stopped these assertions
# seeing a row naming NO grain written during a refusal, which is a real shape:
# `ledger.ledger_for` files a `deviation` grainlessly when the grain resolves
# to no milestone. These three kinds are what a check files about its own run
# and nothing else is allowed.
TELEMETRY_KINDS = frozenset({ledger.KIND_GATE, ledger.KIND_VERIFY,
                             ledger.KIND_TEST})


def _kind_of(line: str) -> str:
    try:
        row = json.loads(line)
    except ValueError:
        return ''
    return row.get('kind', '') if isinstance(row, dict) else ''


def _belt_rows(path: Path) -> tuple[str, ...]:
    """The grainless ledger's rows MINUS a check's telemetry about its own
    run; `()` when the file is not there, so a run that created it and wrote
    nothing but telemetry into it reads the same as one that never touched
    it."""
    if not path.is_file():
        return ()
    return tuple(line for line in path.read_text(encoding='utf-8').splitlines()
                 if line.strip() and _kind_of(line) not in TELEMETRY_KINDS)


def snapshot(root: Path) -> dict[str, object]:
    """Every byte the belt could have written — with the grainless ledger read
    as ROWS rather than bytes, so the telemetry a check files about itself is
    allowed and everything else in that file is still graded."""
    files: dict[str, object] = {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob('*'))
        if p.is_file() and '.git' not in p.parts
        and p not in (root / GRAINLESS_LEDGER, root / LOCAL_LEDGER)}
    for rel in (GRAINLESS_LEDGER, LOCAL_LEDGER):
        files[rel] = _belt_rows(root / rel)
    return files


def first_done(kind: str) -> str:
    """The state the belt must write, read from the tree's own declaration —
    never spelled here, so the test cannot agree with a literal."""
    return driver.done_state(vocabulary.load(), kind)


# --- the census ---------------------------------------------------------------
def test_the_driver_runs_four_operations_and_the_cli_routes_three_verbs():
    """Bites: `agentic-sdlc story` appearing beside `pm story` meaning
    something else."""
    assert driver.OPERATIONS == ('release', 'adopt', 'story', 'feature')
    assert driver.VERBS == ('release', 'adopt', 'close')
    assert cli.conveyor_verbs() == driver.VERBS
    assert steps.DEFAULT_STORY_STEPS == (
        'story-exists', 'required-lines', 'story-verified', 'committed',
        'evidence-written')
    assert steps.DEFAULT_FEATURE_STEPS == (
        'stories-done', 'feature-verified', 'review-recorded', 'findings-landed')


# --- criterion 1: one false check → error line, exit 1, byte-identical --------
def test_a_false_check_is_named_exit_1_and_nothing_is_written(capsys):
    """Bites: a belt that writes over a false check — the write-side cardinal
    sin. No `done:` line → `error: evidence-written:`; the story file and the
    ledger gains only the durable blocked-close marker."""
    with tree(evidence='') as root:
        before = snapshot(root)
        code = close('story', STORY_ID)
        out = capsys.readouterr().out
        assert code == 1, out
        after = snapshot(root)
        assert {key: value for key, value in after.items() if key != LEDGER} == {
            key: value for key, value in before.items() if key != LEDGER
        }, 'the belt changed something other than its ledger'
        events = rows(root)
        assert len(events) == 1, events
        assert events[0]['kind'] == ledger.KIND_BELT_BLOCKED
        assert events[0]['grain'] == STORY_ID
        assert events[0]['state'] == 'blocked'
        assert events[0]['checks'] == ['evidence-written']
    lines = out.strip().split('\n')
    assert '[story] error: evidence-written:' in out, out
    assert lines[-1].startswith('[story] error — '), lines[-1]
    assert 'no status written' in lines[-1]
    assert 'next:' not in out, 'the after-list printed with no status written'
    # ONE line per check, every check asked, even after the first false one.
    for name in steps.DEFAULT_STORY_STEPS:
        assert sum(1 for line in lines
                   if line.startswith(f'[story] ') and f': {name}' in line) == 1, name


def test_a_missing_story_is_ONE_LINE_and_never_a_crash(capsys):
    """Bites: an unresolvable id landing as a traceback at exit 1, which is
    rule 6's code for findings and what a consumer's hook prints.

    It is refused BEFORE the first check now, and that is the cheaper answer:
    a belt that writes needs the grain, so running `verify --story` over a
    story that does not exist spends a spawn to learn what the resolver
    already knows. What the line must do is name the STORY — saying "no
    milestone 'st-nobody-wrote-this'" sent the reader hunting for a milestone
    nobody had named.
    """
    with tree() as root:
        code = close('story', 'st-nobody-wrote-this')
        captured = capsys.readouterr()
        said = captured.out + captured.err
        assert code == 1, said
        assert 'Traceback' not in said, said
        assert "no story 'st-nobody-wrote-this'" in said, said
        assert 'nothing was written' in said, said
        assert rows(root) == []


# --- criterion 2: all true → exactly one write, the first done state ----------
def test_all_true_writes_exactly_the_first_done_state_and_nothing_else(capsys):
    """Bites: a second write (a bump, a flip of another grain, a retitle) or a
    write to a literal `done` rather than the config's word. The diff is
    compared file by file: only the story's status line and the ledger move."""
    with tree() as root:
        before = snapshot(root)
        want = first_done('story')
        assert status_of(root, SFILE) != want
        code = close('story', STORY_ID)
        out = capsys.readouterr().out
        assert code == 0, out
        after = snapshot(root)
        changed = {rel for rel in before | after.keys()
                   if before.get(rel) != after.get(rel)}
        assert changed == {SFILE, LEDGER}, changed
        assert status_of(root, SFILE) == want
        assert after[SFILE].replace(f'status: {want}\n'.encode(),
                                    b'status: building\n') == before[SFILE], (
            'the belt rewrote something other than the status line')
        arrival(root, STORY_ID, want)
    lines = out.strip().split('\n')
    assert f'[story] ok — {STORY_ID} → {want}' in lines, out
    assert any(line.startswith('next: ') for line in lines), out
    assert "[story] ok: story-verified — `make sdlc ARGS='verify --story'` exited 0" in out


def test_close_story_runs_the_story_rung_and_reports_its_exit(capsys):
    """Bites: a story closing over a red unit tier, or the belt reaching for
    a commit range or a path census the rung no longer has. `story-verified`
    is `verify --story` — the make target `[verify] story` names, run the way
    `feature-verified` runs its own rung — and a `unit` that exits 1 is one
    `error:` line and no status written. (The green half is the all-true case
    above, which asserts the same check's `ok:` line.)"""
    with tree({'Makefile': RED_MAKEFILE}) as root:
        before = snapshot(root)
        code = close('story', STORY_ID)
        out = capsys.readouterr().out
        assert code == 1, out
        assert "[story] error: story-verified: `make sdlc ARGS='verify --story'` exited 1" in out, out
        after = snapshot(root)
        assert {key: value for key, value in after.items() if key != LEDGER} == {
            key: value for key, value in before.items() if key != LEDGER
        }, 'the belt changed something other than its blocked-close ledger row'
        blocked_close(root, STORY_ID, 'story', 'story-verified')


def test_the_written_state_is_the_configs_word_not_the_literal_done(capsys):
    """Bites: `done` spelled in the driver. A tree whose `done` category
    opens with `shipped` gets `shipped`, through `pm story shipped <id>`."""
    # Rewrite the STORY block's `done` list only, by locating its header. The
    # flow is the one vocabulary `pm story <state>` validates against (the
    # `[pm] story_states` key is retired and refused), so the belt hands `pm`
    # the flow's word and `pm` accepts it because the flow declares it.
    head, marker, tail = with_flow(CONFIG).partition('[pm.states.story]')
    tail = re.sub(r'^(\s*done\s*=\s*\[)', r'\1"shipped", ', tail, count=1,
                  flags=re.MULTILINE)
    flow = head + marker + tail
    assert '"shipped", "done"' in flow, 'the seed text moved; fix the fixture'
    with tree({'devkit.toml': flow}) as root:
        assert first_done('story') == 'shipped'
        code = close('story', STORY_ID)
        out = capsys.readouterr().out
        assert code == 0, out
        assert status_of(root, SFILE) == 'shipped'
        assert f'→ shipped' in out


# --- close feature ------------------------------------------------------------
def test_close_feature_names_the_story_not_in_done_and_writes_nothing(capsys):
    """Bites: the omission this feature was written from — an orchestrator
    parking finished stories at `reviewing` and closing the feature over
    them. The blocker is NAMED (by `pm ready-for feature`, never
    re-implemented) and the feature file is byte-identical."""
    with tree(story='building', feature='building', reviewed=RECORD,
              files={RECORD: VERDICT_BLOCK}) as root:
        before = (root / FFILE).read_bytes()
        code = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert code == 1, out
        assert '[feature] error: stories-done:' in out, out
        assert 's1' in out
        assert (root / FFILE).read_bytes() == before
        blocked_close(root, FEATURE_ID, 'feature', 'stories-done')


def test_close_feature_all_true_writes_the_feature_status_once(capsys):
    """Bites: a second write — the belt moving the story too, or the feature
    written to anything but the config's first `done` state. One status row,
    the feature's, and nothing else. (Which story states count as finished is
    `pm ready-for feature`'s question, asked and never re-implemented here.)"""
    with tree(story='done', feature='building', reviewed=RECORD,
              files={RECORD: VERDICT_BLOCK}) as root:
        before = (root / SFILE).read_bytes()
        want = first_done('feature')
        code = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert code == 0, out
        assert status_of(root, FFILE) == want
        assert (root / SFILE).read_bytes() == before, 'the belt moved another grain'
        arrival(root, FEATURE_ID, want)
        assert f'[feature] ok — {FEATURE_ID} → {want}' in out


@pytest.mark.parametrize('record, code', [
    (VERDICT_BLOCK, 0), (OPEN_BLOCK, 1),
    # The shape every review here writes: the block keyed to the feature. The
    # pointer the key is checked against is the path the command was given.
    (VERDICT_BLOCK.replace('SHIP-WITH-FIXES\n',
                           f'SHIP-WITH-FIXES\nfeature: {FEATURE_ID}\n'), 0),
], ids=['landed', 'open', 'keyed'])
def test_a_landed_record_closes_in_one_command_and_a_refused_close_stamps_nothing(
        record, code, capsys):
    """`close feature <id> --review-record <path>`: the record checks read
    <path>, and the one write stamps `reviewed:` with the status. Bites: a
    stamp left behind by a close the belt refused (rule 3)."""
    with tree(story='done', feature='building', files={RECORD: record}) as root:
        before = (root / FFILE).read_bytes()
        got = close('feature', FEATURE_ID, '--review-record', RECORD)
        out = capsys.readouterr().out
        assert got == code, out
        if code:
            assert '[feature] error: findings-landed:' in out, out
            assert (root / FFILE).read_bytes() == before
            blocked_close(root, FEATURE_ID, 'feature', 'findings-landed')
        else:
            assert status_of(root, FFILE) == first_done('feature')
            assert frontmatter.field_of(root / FFILE, 'reviewed') == RECORD
            arrival(root, FEATURE_ID, first_done('feature'))


@pytest.mark.parametrize('record,expect', [
    (OPEN_BLOCK, '[feature] error: findings-landed:'),
    ('# no verdict block here\n', '[feature] unverifiable: review-recorded:'),
    # #61: a 33-character id is the reviewer's error in plain words, a false.
    (VERDICT_BLOCK.replace('| W1 |', '| WD-3-three-copies-of-the-key-rule |'),
     '[feature] error: review-recorded: refused: finding id over 32 '
     'characters (33): WD-3-three-copies-of-the-key-rule'),
])
def test_an_open_finding_is_false_and_a_record_that_does_not_parse_is_unverifiable(
        record, expect, capsys):
    """Bites: the single easiest false green in the belt — a record that
    exists but says nothing machine-readable, or one whose finding nobody
    acted on, letting a feature close. Both leave the file untouched."""
    with tree(story='done', feature='building', reviewed=RECORD,
              files={RECORD: record}) as root:
        before = (root / FFILE).read_bytes()
        code = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert code == 1, out
        assert expect in out, out
        assert (root / FFILE).read_bytes() == before


BETA_FILE = f'{MDIR}/features/beta/feature.md'
BETA_DOC = feature_doc('building', RECORD).replace(FEATURE_ID, f'{VERSION}/beta')


def keyed(key: str, word: str, *rows: str) -> str:
    """One verdict block keyed to `key` (unkeyed when it is '')."""
    head = f'verdict: {word}\n' + (f'feature: {key}\n' if key else '')
    return f'```\n{head}| id | severity | disposition |\n' + ''.join(
        f'{row}\n' for row in rows) + '```\n\n'


@pytest.mark.parametrize('record,code,expect', [
    # A bucket record: alpha's SHIP closes alpha; beta's open MAJOR stays beta's.
    (keyed(FEATURE_ID, 'SHIP') + keyed(f'{VERSION}/beta', 'HOLD',
                                       '| B1 | MAJOR | open |'),
     0, f'[feature] ok — {FEATURE_ID}'),
    (keyed(FEATURE_ID, 'HOLD', '| A1 | MAJOR | open |')
     + keyed(f'{VERSION}/beta', 'SHIP'),
     1, '[feature] error: findings-landed: 1 blocking finding(s) open'),
    # A key naming a grain that does not point here is a false, by name.
    (keyed(FEATURE_ID, 'SHIP') + keyed(f'{VERSION}/gamma', 'HOLD',
                                       '| G1 | MAJOR | open |'),
     1, f'names `feature: {VERSION}/gamma`'),
    # Keyed beside unkeyed: nobody can tell whose the unkeyed block is.
    (keyed(FEATURE_ID, 'SHIP') + keyed('', 'HOLD', '| U1 | MAJOR | open |'),
     1, 'key every block or none'),
])
def test_a_keyed_record_is_read_for_its_own_feature_only(record, code, expect,
                                                          capsys):
    """Bites #79: a record shared by a bucket of features held one feature on
    another's MAJOR — and a key the belt cannot trust must not hide one."""
    with tree(story='done', feature='building', reviewed=RECORD,
              files={RECORD: record, BETA_FILE: BETA_DOC}) as root:
        before = (root / FFILE).read_bytes()
        got = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert (got, expect in out) == (code, True), out
        if code:
            assert (root / FFILE).read_bytes() == before


# --- the refusal matrix -------------------------------------------------------
@pytest.mark.parametrize('args,why', [
    # `--skip` SHIPS since 0.5.0/D5 — bare, it is refused for want of the
    # reason, because an unexplained skip IS a deviation and `--force` is its
    # verb. What this row claims is that the refusal writes nothing.
    (['story', STORY_ID, '--skip', 'committed'], 'a check and a reason'),
    (['story', STORY_ID, '--status'], 'removed'),
    # Both closes take many ids (#95), each id once.
    (['feature', FEATURE_ID, FEATURE_ID], 'more than once'),
    (['story', STORY_ID, STORY_ID], 'more than once'),
    # NOT a segment count: an id has no shape in 0.4.0. The belt asks the
    # grain's own `kind:`, so the refusal names what it IS and which belt does
    # ask about one.
    (['story', FEATURE_ID], 'is a feature, not a story'),
    (['feature', STORY_ID], 'is a story, not a feature'),
    (['story', '../../etc'], 'not a story id'),
    (['bogus', STORY_ID], 'unknown grain'),
    ([], 'needs a grain'),
])
def test_the_refusal_matrix_exits_2_and_writes_nothing(args, why, capsys):
    """Bites: a usage error read as a finding (exit 1) or, worse, a wrong
    grain resolved to a real file and written to."""
    with tree() as root:
        before = snapshot(root)
        assert close(*args) == 2, args
        err = capsys.readouterr().err
        assert why in err, (args, err)
        assert snapshot(root) == before


# --- a green run is bought once (#95) -----------------------------------------
S2 = f'{FEATURE_ID}/s2'
S2FILE = f'{FDIR}/stories/s2.md'
REUSED = '[verify:cache] REUSED PASS'


def second_story(evidence: str = DONE_LINE) -> dict[str, str]:
    return {S2FILE: story_doc(evidence=evidence).replace(f'{FEATURE_ID}/s1', S2)}


# The escape hatch: a rung target that READS statuses keys on every byte.
OPT_OUT = CONFIG + 'reuse_ignores_status = false\n'


def test_a_second_close_on_one_commit_reuses_the_story_rung(capsys):
    """#95: each close writes a status line and ledger rows under the roadmap
    directory, and the story rung's whole-tree state took them in — so the
    second close on one commit re-bought a green it already had. The probes:
    a `changelog:` line or a body edit to a grain, or an edit under `src/`,
    between the two closes RE-RUNS the rung — only what a belt writes is left
    out — and with `reuse_ignores_status = false` the status flip alone
    re-runs it."""
    with tree(second_story()) as root:
        assert close('story', STORY_ID) == 0
        assert REUSED not in capsys.readouterr().out
        assert close('story', S2) == 0
        out = capsys.readouterr().out
        assert REUSED in out, out
        assert 'reuse_ignores_status = false' in out, out
        assert status_of(root, S2FILE) == first_done('story')
    # Uncommitted, so HEAD holds still and only these bytes move. The roadmap
    # edits leave `committed` true; the `src/` one makes it false, and the
    # rung is asked anyway.
    for rel, old, new, code, config in (
            (S2FILE, 'status: building\n',
             'status: building\nchangelog: a new line\n', 0, CONFIG),
            (S2FILE, '# One\n', '# One, edited\n', 0, CONFIG),
            ('src/thing.py', 'x = 1\n', 'x = 2\n', 1, CONFIG),
            (None, '', '', 0, OPT_OUT)):
        with tree(second_story(), config=config) as root:
            assert close('story', STORY_ID) == 0
            capsys.readouterr()
            if rel is not None:
                path = root / rel
                path.write_text(
                    path.read_text(encoding='utf-8').replace(old, new),
                    encoding='utf-8')
            assert close('story', S2) == code, (rel, new)
            out = capsys.readouterr().out
            assert '[story] ok: story-verified' in out, out
            assert REUSED not in out, (rel, new, out)


COUNTING_MAKEFILE = MAKEFILE.replace('unit:\n\t@true',
                                     'unit:\n\t@echo ran >> unit.log')


def test_close_story_many_ids_runs_the_rung_once_and_writes_each(capsys):
    """#95: `close story a b c` asks the tree-wide checks once and each story
    its own; each id is printed with its lines and written on its own verdict.
    A done id is reported and skipped; a refused id is named and exit is 1."""
    ids = [STORY_ID, S2, f'{FEATURE_ID}/s3', f'{FEATURE_ID}/s4']
    files = {'Makefile': COUNTING_MAKEFILE, '.gitignore': 'unit.log\n'}
    for sid, evidence in zip(ids[1:], (DONE_LINE, DONE_LINE, '')):
        files[f'{FDIR}/stories/{sid.rsplit("/", 1)[1]}.md'] = story_doc(
            evidence=evidence).replace(f'{FEATURE_ID}/s1', sid)
    with tree(files) as root:
        assert close('story', *ids[:3]) == 0
        out = capsys.readouterr().out
        assert (root / 'unit.log').read_text() == 'ran\n', out
        for sid in ids[:3]:
            assert f'[story] ok — {sid} → {first_done("story")}' in out, out
        assert out.count('[story] ok: story-verified') == 3, out
        assert out.count('asked once for this close') == 4, out
        assert '[story] 3 of 3 written' in out, out
        assert close('story', STORY_ID, ids[3]) == 1
        out = capsys.readouterr().out
        assert f'{STORY_ID} is already {first_done("story")}' in out, out
        assert '[story] error: evidence-written:' in out, out
        assert f'refused: {ids[3]}' in out, out
        assert status_of(root, f'{FDIR}/stories/s4.md') == 'building'
        assert (root / 'unit.log').read_text() == 'ran\n', out


# --- every rung reuses a green run: feature and release -----------------------
COUNTING_ALL = ('unit:\n\t@true\n\ntest:\n\t@echo ran >> test.log\n\n'
                'milestone:\n\t@echo ran >> milestone.log\n')
COUNTED = {'Makefile': COUNTING_ALL, '.gitignore': 'test.log\nmilestone.log\n'}


def another_feature(name: str) -> dict[str, str]:
    """A feature `name` at `building` over one `done` story, reviewed."""
    fid, fdir = f'{VERSION}/{name}', f'{MDIR}/features/{name}'
    return {f'{fdir}/feature.md': feature_doc('building', RECORD).replace(
                FEATURE_ID, fid),
            f'{fdir}/stories/s1.md': story_doc('done').replace(FEATURE_ID, fid)}


def test_feature_closes_on_one_commit_run_the_feature_rung_once(capsys):
    """Measured at 0.17.0: six `close feature` on one commit ran `make test`
    six times, because each close moved the feature rung's whole-tree state.
    One close runs it; the next reuses it; a many-id close asks
    `feature-verified` once for every id and writes each on its own verdict."""
    names = ('beta', 'gamma', 'delta')
    files = {RECORD: VERDICT_BLOCK, **COUNTED}
    for name in names:
        files.update(another_feature(name))
    with tree(files, story='done', feature='building',
              reviewed=RECORD) as root:
        assert close('feature', FEATURE_ID) == 0
        assert REUSED not in capsys.readouterr().out
        assert close('feature', f'{VERSION}/beta') == 0
        out = capsys.readouterr().out
        assert REUSED in out, out
        many = [f'{VERSION}/gamma', f'{VERSION}/delta']
        assert close('feature', *many) == 0
        out = capsys.readouterr().out
        assert out.count('[feature] ok: feature-verified') == 2, out
        assert out.count('asked once for this close') == 1, out
        assert '[feature] 2 of 2 written' in out, out
        assert (root / 'test.log').read_text() == 'ran\n', out
        for name in ('alpha', *names):
            assert status_of(root, f'{MDIR}/features/{name}/feature.md') \
                == first_done('feature'), name


# `make check` grades the milestone: green at `building`, red once `done`
# — the #87 shape, a check only a CLOSED milestone fails.
STATUS_CHECK = f"check:\n\t@grep -q '^status: building$$' {MDIR}/milestone.md\n"


@pytest.mark.parametrize('check_target, static, passes', [
    ('check:\n\t@true\n', '', True),
    (STATUS_CHECK, '', False),
    # `[verify] static` resolves: the static rung is the target it names.
    (STATUS_CHECK + 'lint:\n\t@true\n', 'static = "make lint"\n', True),
])
def test_release_reuses_a_green_milestone_run_recorded_at_building(
        check_target, static, passes, capsys):
    """0.17.0 review C2: `release` asks its gate with the milestone at `done`
    (#87), which the run recorded at `building` never saw, so it paid for
    `make milestone` again. Only the `status:` line differs, and every rung
    leaves it out: the gate reuses and runs no `make milestone`. What the
    reuse cannot say is which status that run saw, so `verify --milestone`
    asks its static rung (`[verify] static`, stock `make check`) at `done`
    first — and a check that fails a closed milestone fails the release (#87
    again, through the reuse)."""
    files = {**COUNTED, 'Makefile': COUNTING_ALL + '\n' + check_target}
    with tree(files, config=CONFIG + static) as root:
        assert cli.main(['verify', '--milestone']) == 0
        capsys.readouterr()
        answer = steps.RELEASE_STEPS['gate'].check(
            driver.Context(root=root, operation='release', version=VERSION))
        assert answer.is_true is passes, answer.detail
        assert "at 'done'" in answer.detail, answer.detail
        if passes:
            ran = 'make lint' if static else 'make check'
            assert answer.detail.endswith(
                f'; static rung re-asked: {ran} exited 0'), answer.detail
            assert '; reused — green at' in answer.detail, answer.detail
        else:
            assert 'FAILED (exit 2) — make check, the static rung' \
                in answer.detail, answer.detail
        assert (root / 'milestone.log').read_text() == 'ran\n', answer.detail
        assert status_of(root, f'{MDIR}/milestone.md') == 'building'
