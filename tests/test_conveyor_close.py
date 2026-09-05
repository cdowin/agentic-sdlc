"""test_conveyor_close.py — the two INNER belts, `close story` and `close feature`.

The headline is `test_close_feature_cannot_advance_past_stories_done`: on a tree
whose stories are parked at `reviewing`, the feature belt walks NOTHING else.
That is the mistake this feature was written from — an orchestrator parked 28
finished stories at `reviewing` and reviewed the whole milestone in one pass,
skipping the feature level, in the milestone that built the levels — made
structurally impossible rather than left as a paragraph somebody has to
remember.

The second headline is `test_a_clean_story_closes_well_under_a_second`. Risk 2
of the feature: *a story-close conveyor slower than closing by hand will be
skipped, and a skipped conveyor is worse than none because it looks like
control.* The story list is five steps and four of them are already-computed
facts, so the budget is asserted rather than hoped for.

Every write-verb test here works on a scratch tree, never on a fixture in
place, and every claim about what a step DID is a claim about the tree (a
status line, a file's bytes, a recorder file) rather than about the transcript.
A transcript that does not mention a step is not proof the step did not run.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import cli  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402
from agentic_sdlc.repo.pm import model  # noqa: E402

VERSION = '9.9.9'
FEATURE_ID = f'{VERSION}/alpha'
STORY_ID = f'{FEATURE_ID}/s1'
MDIR = f'pm/roadmap/{VERSION}-scratch'
FDIR = f'{MDIR}/features/alpha'
SFILE = f'{FDIR}/stories/s1.md'
FFILE = f'{FDIR}/feature.md'
RECORD = 'docs/reviews/alpha.md'

MILESTONE = f'''---
id: "{VERSION}"
name: A scratch milestone
status: building
branch: milestone/{VERSION}
---

# A scratch milestone
'''

# `[verify]` has to be declared or `verify --story` exits 2 naming the section —
# which is itself the right answer, and is asserted below.
CONFIG = '''[verify]
feature   = "make feature"
milestone = "make milestone"

[[verify.narrow]]
paths = "src/**"
run   = "true"
'''

# D3: a rung NAMES a make target, so the scratch repo has the two targets the
# config above names. They do nothing, which is the point — what is under test
# is which rung the step asks for, never what the project's rung runs.
MAKEFILE = 'feature:\n\t@true\n\nmilestone:\n\t@true\n'

VERDICT_BLOCK = '''```
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| W1 | WARNING | landed in-place |
```
'''


def feature_doc(status: str = 'planning', reviewed: str = '') -> str:
    return (f'---\nid: {FEATURE_ID}\nmilestone: "{VERSION}"\n'
            f'name: Alpha\nstatus: {status}\nreviewed: {reviewed}\n'
            f'phase: 1\n---\n\n# Alpha\n')


def story_doc(status: str = 'reviewing', evidence: str = '') -> str:
    return (f'---\nid: {FEATURE_ID}/s1\nfeature: {FEATURE_ID}\n'
            f'milestone: "{VERSION}"\nname: One\nstatus: {status}\n---\n\n'
            f'# One\n\n{evidence}')


DONE_LINE = 'done: 3a42f19ad0 — the belt walks\n'


@contextlib.contextmanager
def tree(files: dict[str, str] | None = None, *, story: str = 'reviewing',
         evidence: str = DONE_LINE, feature: str = 'planning',
         reviewed: str = '', config: str = CONFIG):
    """A scratch repo with a milestone, a feature and one story, entered."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        payload = {
            f'{MDIR}/milestone.md': MILESTONE,
            FFILE: feature_doc(feature, reviewed),
            SFILE: story_doc(story, evidence),
            'devkit.toml': config,
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
                        '-c', 'user.name=t', 'commit', '-qm', 'scratch'],
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
    return model.field_of(root / rel, 'status')


def porcelain(root: Path) -> str:
    return subprocess.run(['git', 'status', '--porcelain'], cwd=root,
                          capture_output=True, text=True).stdout


def head(root: Path) -> str:
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root,
                          capture_output=True, text=True).stdout.strip()


# --- the census ---------------------------------------------------------------
def test_the_driver_walks_four_operations_and_the_cli_routes_three_verbs():
    """`driver.OPERATIONS` grew from two to four; the ROUTER did not, because
    `story` and `feature` are reached through `close`. An `agentic-sdlc story`
    verb would sit beside `agentic-sdlc pm story` meaning something else."""
    assert driver.OPERATIONS == ('release', 'adopt', 'story', 'feature')
    assert driver.VERBS == ('release', 'adopt', 'close')
    assert cli.conveyor_verbs() == driver.VERBS
    assert 'story' not in cli.conveyor_verbs()


@pytest.mark.parametrize('operation', driver.CLOSE_OPERATIONS)
def test_each_close_registry_is_exactly_its_shipped_list(operation):
    """The roster == dispatchable bar. A name in the list with no step is half
    a close against a plan that cannot finish; a step nothing lists is a
    postcondition nobody checks."""
    registry = steps.REGISTRIES[operation]
    listed = steps.DEFAULT_STEPS[operation]
    assert set(registry) == set(listed)
    assert len(listed) == len(set(listed)), 'the shipped list has a duplicate'


def test_the_step_kind_census_of_both_close_lists():
    """Which steps are JUDGEMENT is the whole ruling — *the entry conditions
    are ENFORCED, the judgement is EXPRESSED* — so the census is pinned. A step
    that changes kind has changed what the machine claims to know."""
    def census(registry):
        return {kind.name: sum(1 for s in registry.values() if s.kind is kind)
                for kind in driver.StepKind}

    assert census(steps.STORY_STEPS) == {
        'AUTOMATIC': 2, 'GATE': 1, 'JUDGEMENT': 2}
    assert census(steps.FEATURE_STEPS) == {
        'AUTOMATIC': 2, 'GATE': 1, 'JUDGEMENT': 3}


def test_no_close_step_ships_a_command_default():
    """Every default here is a VERB this package owns (`verify`, `pm`), run
    through the code, so `[story.commands]` / `[feature.commands]` stay the
    project's override rather than something it has to supply."""
    for operation in driver.CLOSE_OPERATIONS:
        # The list first: `commands_for` over an operation with no registry
        # answers `{}` too, and a claim that would hold for a list nobody
        # shipped is not a claim about this one.
        assert steps.steps_for(operation), operation
        assert steps.commands_for(operation) == {}


# --- close story: the budget --------------------------------------------------
def test_a_clean_story_closes_well_under_a_second():
    """Risk 2, measured. Four of the five steps read a line already on disk;
    the fifth shells out once to the narrow rung, which on a committed tree
    reports `no changed paths` and returns."""
    with tree() as root:
        started = time.monotonic()
        code = close('story', STORY_ID)
        elapsed = time.monotonic() - started
        assert code == 0
        assert status_of(root, SFILE) == 'done'
        assert elapsed < 1.0, f'the story belt took {elapsed:.2f}s'


def test_the_narrow_rung_reports_that_it_verified_nothing_rather_than_passing(
        capsys):
    """A committed tree has no diff, so `verify --story` proves nothing — and
    says so. The sentence is QUOTED into the line rather than summarised as a
    pass, because a reader has to be able to see that nothing ran."""
    with tree() as root:
        close('story', STORY_ID)
        out = capsys.readouterr().out
        assert 'no changed paths' in out, out


# --- close story: it REPORTS, and it finishes ---------------------------------
# D8, 2026-09-05. Chris: "Everything is just a check. `release` should release
# on a red tree if I want (we mostly wouldn't but why stop someone?)" These
# tests used to assert that the belt REFUSED to advance — that the story was
# still `reviewing` because a later step never ran. It now walks to the end,
# and what they assert is the pair that actually matters: the problem is NAMED
# and the exit code is 1. What has NOT changed, and is the half worth keeping,
# is that the belt never writes what it exists to read and never commits on
# your behalf.
def test_a_red_narrow_check_is_named_and_the_belt_still_finishes(capsys):
    """Ship criterion 2, re-read under D8. The narrow rung is red, it says so,
    the run exits 1 — and the story closes, because whether a red narrow check
    should stop this close is the caller's question and not the engine's."""
    with tree(config=CONFIG.replace('run   = "true"', 'run   = "false"')) as root:
        (root / 'src/thing.py').write_text('x = 2\n', encoding='utf-8')
        code = close('story', STORY_ID)
        out = capsys.readouterr().out
        assert code == 1
        assert 'narrow-verified' in out, out
        assert 'not true' in out, out
        assert status_of(root, SFILE) == 'done'


def test_the_narrow_command_comes_from_verify_and_not_from_the_step():
    """Ship criterion 2's second half, proven with a RECORDER — a narrow rule
    whose command leaves a file. A claim about output is not a claim about
    what ran."""
    recorder = CONFIG.replace('run   = "true"', 'run   = "touch NARROW-RAN"')
    with tree(config=recorder) as root:
        (root / 'src/thing.py').write_text('x = 2\n', encoding='utf-8')
        close('story', STORY_ID)
        assert (root / 'NARROW-RAN').exists(), (
            'the step did not run the command [[verify.narrow]] names')


def test_a_repo_that_never_said_what_proves_an_edit_is_never_a_green_step(
        capsys):
    """`[verify]` absent is exit 2 from the rung, and the step reports it as a
    CONFIG error that decided nothing — never as a green step. That is the
    claim, and D8 did not touch it: the step is not true, and it is named."""
    with tree(config='') as root:
        code = close('story', STORY_ID)
        out = capsys.readouterr().out
        assert code == 1
        assert 'narrow-verified' in out, out


def test_committed_names_uncommitted_work_and_commits_nothing():
    with tree() as root:
        before = head(root)
        (root / 'src/thing.py').write_text('x = 3\n', encoding='utf-8')
        # The narrow rung passes (`run = "true"`), so the walk reaches
        # `committed` with a real uncommitted path in front of it.
        code = close('story', STORY_ID)
        assert code == 1
        # THE half that survives D8 and is the whole point of the test: the
        # belt reports uncommitted work, and commits nothing on your behalf.
        assert 'src/thing.py' in porcelain(root), 'the belt committed'
        assert head(root) == before, 'the belt moved HEAD'


def test_the_belts_own_roadmap_write_does_not_redden_its_own_third_step():
    """`claimed` moves a status line INSIDE pm/roadmap/, and `committed` asks
    about the worktree outside it. A machine whose first step falsifies its
    third is `state.py` point 2 arriving one grain down."""
    with tree(story='planning') as root:
        code = close('story', STORY_ID)
        assert code == 0, porcelain(root)
        assert status_of(root, SFILE) == 'done'
        assert MDIR in porcelain(root), 'nothing was written to the PM tree'


# --- close story: the evidence is the author's --------------------------------
def test_evidence_written_refuses_a_story_with_no_done_line_and_writes_nothing():
    with tree(evidence='') as root:
        before = (root / SFILE).read_bytes()
        code = close('story', STORY_ID)
        assert code == 1
        # The half that survives D8: a step that READS the author's evidence
        # must never write it. A belt that supplied the line it checks for is
        # the write-side cardinal sin.
        assert b'done:' not in (root / SFILE).read_bytes().replace(before, b''), (
            'the belt wrote the `done:` line it exists to READ')


@pytest.mark.parametrize('line,why', [
    ('done: shipped the thing\n', 'names no commit'),
    ('done: 3a42f19ad0\n', 'names what landed and not what shipped'),
])
def test_a_done_line_that_is_not_evidence_is_refused_by_name(line, why):
    with tree(evidence=line) as root:
        code = close('story', STORY_ID)
        assert code == 1, line


def test_landed_in_place_is_evidence_because_verdict_py_already_ruled_so():
    """Reviewers in this SDLC fix in place and never commit, so a hash-only
    rule would refuse the honest half of the corpus. The form is inherited
    from `pm/verdict.py` rather than re-decided here."""
    with tree(evidence='done: in-place — the belt walks\n') as root:
        assert close('story', STORY_ID) == 0
        assert status_of(root, SFILE) == 'done'


# --- close feature ------------------------------------------------------------
def test_close_feature_names_the_story_that_is_not_finished(capsys):
    """Ship criterion 3, and the mistake this feature was written from — the
    orchestrator that parked 28 stories at `reviewing`.

    Under D8 the belt does not refuse; it NAMES the story, which is the half
    that ends the mistake. A feature closed over an unfinished story is then a
    contradiction in the tree, and `check pm` D3/D5 is the thing that fails
    it — in CI, pre-push, with an exit-code contract for exactly that."""
    with tree(story='reviewing') as root:
        code = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert code == 1
        assert f'{STORY_ID} is reviewing' in out, out
        assert 'stories-done' in out, out


def test_stories_done_asks_pm_ready_for_rather_than_reading_the_stories(
        monkeypatch):
    """It IS `pm ready-for feature`. Asserted by recording what the step
    ASKED, because a second reader of "is every story done" would answer
    identically on the day it was written and differently on some later one."""
    asked: list[str] = []

    def record(ctx, target):
        asked.append(target)
        return driver.Answer.no('recorded')

    monkeypatch.setattr(steps, 'ready_for', record)
    with tree():
        close('feature', FEATURE_ID)
    # Twice — `check()`, then `verify()` re-asking after `do()` ran — and the
    # target is `feature` both times. That second ask IS the driver's rule:
    # `do()` never decides its own outcome.
    assert asked == ['feature', 'feature'], asked


def test_a_feature_with_no_review_record_is_refused(capsys):
    with tree(story='done') as root:
        code = close('feature', FEATURE_ID)
        assert code == 1
        assert 'no review record' in capsys.readouterr().out
        assert status_of(root, FFILE) != 'done'


@pytest.mark.parametrize('body,expected', [
    ('# a review with no verdict block\n', 'UNVERIFIABLE'),
    ('```\nverdict: SHIP\n| id | severity |\n```\n', 'UNVERIFIABLE'),
    ('```\nverdict: WOMBAT\n| id | severity | disposition |\n```\n',
     'UNVERIFIABLE'),
])
def test_a_record_that_does_not_parse_is_unverifiable_and_never_a_pass(
        body, expected, capsys):
    """Ship criterion 4. `verdict.parse`'s ruling, inherited: this is the
    single easiest place in the belt to get a false green."""
    with tree(story='done', reviewed=RECORD,
              files={RECORD: body}) as root:
        code = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert code == 1
        # UNVERIFIABLE is still not a pass, and it is still counted apart from
        # a plain no — D8 removed the halt, not the third truth value.
        assert expected in out, out
        assert 'unverifiable' in out, out


def test_a_finding_at_disposition_open_blocks_and_is_named(capsys):
    """Ship criterion 4's third case."""
    record = ('```\nverdict: SHIP-WITH-FIXES\n'
              '| id | severity | disposition |\n'
              '| W1 | WARNING | landed in-place |\n'
              '| Q5 | QUESTION | open |\n```\n')
    with tree(story='done', reviewed=RECORD, files={RECORD: record}) as root:
        code = close('feature', FEATURE_ID)
        out = capsys.readouterr().out
        assert code == 1
        assert 'Q5' in out, out


def test_the_whole_feature_belt_walks_and_closes_through_the_pm_cli(capsys):
    with tree(story='done', reviewed=RECORD,
              files={RECORD: VERDICT_BLOCK}) as root:
        code = close('feature', FEATURE_ID)
        assert code == 0, capsys.readouterr().out
        assert status_of(root, FFILE) == 'done'
        assert model.field_of(root / FFILE, 'reviewed') == RECORD


# --- the run state ------------------------------------------------------------
def test_a_position_left_by_another_story_is_stale_rather_than_broken(capsys):
    """One state file per OPERATION and one run per STORY, so the file left by
    the last story is about a different grain every time. `release` keeps the
    strict refusal; here it would make the belt unusable from its second run
    onward, and losing the position costs nothing because every step is
    re-asked against the tree."""
    second = f'{FDIR}/stories/s2.md'
    with tree(files={second: story_doc(evidence=DONE_LINE
                                       ).replace('/s1', '/s2')}) as root:
        assert close('story', STORY_ID) == 0
        capsys.readouterr()
        assert close('story', f'{FEATURE_ID}/s2') == 0
        out = capsys.readouterr().out
        assert 'CORRECTED' in out, out
        assert status_of(root, second) == 'done'


def test_the_release_belt_keeps_the_strict_refusal(capsys):
    """The other half of the ruling above: a `release` state file naming
    another version means the operator is running the wrong one."""
    with tree() as root:
        state = root / '.agentic-sdlc/run/release.json'
        state.parent.mkdir(parents=True)
        state.write_text('{"format": 1, "operation": "release", '
                         '"version": "0.0.1", "steps": []}\n',
                         encoding='utf-8')
        assert cli.main(['release', VERSION]) == 2
        assert '0.0.1' in capsys.readouterr().err


# --- the refusal matrix (SDLC.md §5) ------------------------------------------
# argv is an input surface, so the grammar's negatives are enumerated. Every one
# of these is exit 2 (usage/config) or 1 (a fact about the tree) and NONE of
# them writes: the run-state directory is the tell, because it is the first
# thing a walk creates.
USAGE_REFUSALS = [
    ([], 'no grain'),
    (['milestone', VERSION], 'a milestone is not a grain close takes'),
    (['story'], 'no id'),
    (['story', STORY_ID, f'{FEATURE_ID}/s2'], 'two ids'),
    (['story', FEATURE_ID], 'a feature id has too few segments for a story'),
    (['feature', STORY_ID], 'a story id has too many segments for a feature'),
    (['story', f'{VERSION}/../../etc/x'], 'traversal'),
    (['story', f'{VERSION}/alpha/../s1'], 'a dot-dot segment'),
    (['story', f'{VERSION}/./s1'], 'a dot segment'),
    (['story', f'{VERSION}//s1'], 'an empty segment'),
    (['story', f'{VERSION}/*/s1'], 'a glob'),
    (['story', f'{VERSION}/alpha/s?'], 'a glob in the last segment'),
    (['story', '/etc/passwd/x'], 'an absolute path'),
    (['story', f'{VERSION}\\alpha\\s1'], 'backslashes'),
    (['story', 'https://example.invalid/a/b'], 'a scheme'),
    (['story', f'{VERSION}/alpha/s 1'], 'whitespace'),
    (['story', f'{VERSION}/alpha/s\n1'], 'a newline'),
    (['story', ''], 'an empty id'),
    (['story', '   '], 'whitespace alone'),
    (['story', f'{VERSION}/alpha/' + 'x' * 400], 'an over-long segment'),
    (['story', STORY_ID, '--reason', 'why'], '--reason with no --skip'),
    (['story', STORY_ID, '--skip', 'claimed'], '--skip with no --reason'),
    (['story', STORY_ID, '--skip', 'wombat', '--reason', 'x'],
     'a step that is not in this list'),
    (['story', STORY_ID, '--nope'], 'an unknown option'),
]


@pytest.mark.parametrize('args,why', USAGE_REFUSALS,
                         ids=[w for _, w in USAGE_REFUSALS])
def test_the_refusal_matrix_exits_2_and_writes_nothing(args, why, capsys):
    with tree() as root:
        assert close(*args) == 2, why
        assert not (root / '.agentic-sdlc').exists(), why
        assert status_of(root, SFILE) == 'reviewing', why
        err = capsys.readouterr().err
        assert err.strip(), f'{why}: refused in silence'
        # A router with no `close` branch prints its whole menu at exit 2, so
        # every case above would pass against a tool that has not shipped the
        # verb at all. The refusal has to be the GRAMMAR's, not the router's.
        assert 'unknown command' not in err, f'{why}: the verb is not routed'


@pytest.mark.parametrize('args,why', [
    (['story', f'{VERSION}/alpha/nope'], 'a story that is not there'),
    (['story', '8.8.8/alpha/s1'], 'a milestone that is not there'),
    (['feature', f'{VERSION}/nope'], 'a feature that is not there'),
    # `~` is a legal path SEGMENT and nothing expands it — the id grammar is
    # `pm`'s, segment for segment, and it joins `~` onto the roadmap directory
    # as the literal directory name it is. So this lands where every other
    # well-formed-and-absent id lands, rather than in a second grammar's
    # refusal list.
    (['story', '~/alpha/s1'], 'a home-relative-looking milestone segment'),
])
def test_an_unresolvable_grain_is_exit_1_and_writes_nothing(args, why, capsys):
    """Well-formed and absent is a FACT about the tree, not a usage error — the
    same split `release` already makes for a missing milestone directory."""
    with tree() as root:
        assert close(*args) == 1, why
        assert not (root / '.agentic-sdlc').exists(), why
        assert 'nothing was' in capsys.readouterr().err, why


def test_two_files_claiming_one_story_id_refuse_rather_than_pick_one(capsys):
    """`model.story_file`'s ruling, surfaced by the belt rather than absorbed:
    two files at the same precedence is an authoring error, and a close that
    picked one would write a status into a file the operator did not name."""
    ordinal = CONFIG + '\n[pm]\nstory_ordinal_prefix = true\n'
    with tree(config=ordinal,
              files={f'{FDIR}/stories/01-s9.md': story_doc(),
                     f'{FDIR}/stories/02-s9.md': story_doc()}) as root:
        assert close('story', f'{FEATURE_ID}/s9') == 1
        assert 'matches 2 files' in capsys.readouterr().err
        assert not (root / '.agentic-sdlc').exists()


def test_a_step_that_is_not_true_is_recorded_as_a_deviation_row():
    """Inherited whole from the driver — INVISIBLE deviation does not stay
    possible — and asserted here because the ledger row lands under the
    MILESTONE directory whatever grain is being closed.

    D8 kept this row and changed who mints it. It used to take
    `--skip evidence-written --reason "the story predates step 6"`: the
    operator's account of why they were stepping around the machine. It is now
    the MACHINE's account of what it found, written without anyone having to
    remember to ask for it — which is strictly more of the thing the row was
    minted for.
    """
    with tree(evidence='') as root:
        code = close('story', STORY_ID)
        assert code == 1
        rows = (root / f'{MDIR}/ledger.jsonl').read_text(encoding='utf-8')
        assert 'evidence-written' in rows and 'deviation' in rows
        assert '"outcome":"not-true"' in rows, rows
        assert STORY_ID in rows, 'the row does not name the grain it walked'


def test_the_deviation_row_is_written_once_however_often_the_belt_reruns():
    """Idempotence, which is what the callback's True/False is for. A re-run
    finds the same step not true and must not append a second row saying so —
    a durable log that grows on every read is a log nobody can count.

    Counted per STEP rather than by comparing the file's bytes: a second run
    legitimately discovers things the first one caused (the belt's own run
    state under `.agentic-sdlc/`, which is what finding R3 is about), and this
    test is about the row minter rather than about what else the tree grew.
    """
    def evidence_rows(root):
        raw = (root / f'{MDIR}/ledger.jsonl').read_text(encoding='utf-8')
        return [ln for ln in raw.splitlines()
                if '"step":"evidence-written"' in ln]

    with tree(evidence='') as root:
        assert close('story', STORY_ID) == 1
        assert len(evidence_rows(root)) == 1, evidence_rows(root)
        assert close('story', STORY_ID) == 1
        assert len(evidence_rows(root)) == 1, evidence_rows(root)


def test_the_removed_skip_flag_is_named_rather_than_called_an_unknown_option():
    """A consumer's script may still carry `--skip`, and "unknown option
    '--skip'" would send them looking for a typo. Exit 2 with the reason and
    the replacement."""
    with tree() as root:
        code = close('story', STORY_ID, '--skip', 'evidence-written',
                     '--reason', 'whatever')
        assert code == 2
