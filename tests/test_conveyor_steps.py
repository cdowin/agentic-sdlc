"""test_conveyor_steps.py — the release registry, and the ordering that is the
whole point of it.

The headline USED to be `test_open_finding_stops_before_gate`: on a tree whose
review had not landed, the conveyor never reached `gate` — the 0.24.0 mistake
(`make milestone` run twice before a reviewer that then asked for fixes, both
runs void before the tag) made structurally impossible rather than left as a
paragraph somebody has to remember. **D8 removed the halt**
(`pm/roadmap/0.2.0-the-conveyor/decisions.md`): everything is just a check, no
step blocks any later step, and a red gate reports red and the walk goes on.

So the headline is now what SURVIVED that: every step is asked, every answer is
reported by name, and the scoreboard is the deliverable. The gate case is still
asserted with a COMMAND RECORDER (a gate command that leaves a file on disk if
it runs), never by reading the transcript — in both directions, because a
transcript is not proof of what ran.

Every write-verb test here works on a scratch tree, never on a fixture in place.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import with_flow  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402

VERSION = '9.9.9'
MILESTONE = f'''---
id: "{VERSION}"
name: A scratch milestone
status: building
branch: milestone/{VERSION}
---

# A scratch milestone
'''


@contextlib.contextmanager
def tree(files: dict[str, str] | None = None, config: str = ''):
    """A scratch repo with a milestone directory, entered.

    `config` is this tree's devkit.toml MINUS the flow declaration, which is
    APPENDED for you — `[pm.states.*]` has no runtime fallback, so a case that
    supplied its own `[release]` block and thereby dropped the flow would build
    a tree `model.flow_of` refuses for a reason unrelated to what it asserts.
    See tests/support/pm.py `with_flow`.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / f'pm/roadmap/{VERSION}-scratch').mkdir(parents=True)
        (root / f'pm/roadmap/{VERSION}-scratch/milestone.md').write_text(
            MILESTONE, encoding='utf-8')
        (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
        for rel, body in (files or {}).items():
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


def ctx(root: Path) -> driver.Context:
    return driver.Context(root=root, operation='release', version=VERSION)


def walk(root: Path, names, **kw):
    known = driver.registry_for('release')
    from agentic_sdlc.repo.conveyor import state as run_state
    run = run_state.RunState('release', VERSION)
    return driver.walk(known, names, ctx(root), run, **kw)


# --- the ordering, which is the feature ---------------------------------------
def test_an_open_finding_is_reported_and_the_walk_carries_on_to_the_gate(
        monkeypatch):
    """`review-landed` reports NOT-TRUE and the gate still runs — D8.

    THIS TEST USED TO ASSERT THE OPPOSITE, and the inversion is the decision,
    not a regression: it was `test_open_finding_stops_before_gate`, and it held
    while `_walk` returned at the first step whose postcondition was not true.
    D8 (`pm/roadmap/0.2.0-the-conveyor/decisions.md`) removed that halt whole —
    *"Everything is just a check. `release` should release on a red tree if I
    want"* — so no step guards any later step, and a gate running behind an
    open finding is the operator's call with the finding printed above it.

    What survives unchanged is the part that is still a claim about the tree:
    the finding is REPORTED, by name, and the run exits 1. Still proven by a
    RECORDER — the configured gate command creates a file — because "the
    transcript mentions gate" is a claim about output, and this has to be a
    claim about what ran.
    """
    monkeypatch.setattr(
        steps, 'ready_for',
        lambda c, target: driver.Answer.no('M1, M2 are at disposition: open'))
    with tree(config='[release.commands]\ngate = "touch GATE-RAN"\n') as root:
        result = walk(root, ('review-landed', 'gate'))
        assert result.not_true[0] == 'review-landed', result.lines
        assert result.exit_code == 1
        assert (root / 'GATE-RAN').exists(), (
            'D8: no step halts the walk, so the gate command runs and reports')
        assert 'M1, M2' in '\n'.join(result.lines), result.lines


def test_the_gate_does_run_once_the_review_has_landed(monkeypatch):
    """The other direction, so the test above is not passing vacuously."""
    monkeypatch.setattr(steps, 'ready_for',
                        lambda c, target: driver.Answer.yes('0 open findings'))
    with tree(config='[release.commands]\ngate = "touch GATE-RAN"\n') as root:
        result = walk(root, ('review-landed', 'gate'))
        assert result.exit_code == 0, result.lines
        assert (root / 'GATE-RAN').exists(), result.lines


def test_review_landed_sits_above_gate_in_the_shipped_list():
    order = steps.DEFAULT_RELEASE_STEPS
    assert order.index('review-landed') < order.index('gate')
    assert order.index('features-done') < order.index('gate')


# --- the census ---------------------------------------------------------------
def test_the_registry_is_exactly_the_shipped_default_list():
    """The roster == dispatchable bar, applied to steps. A name in the list
    with no step is half a release against a plan that cannot finish; a step
    nothing lists is a postcondition nobody checks."""
    assert set(steps.RELEASE_STEPS) == set(steps.DEFAULT_RELEASE_STEPS)
    assert len(steps.DEFAULT_RELEASE_STEPS) == len(
        set(steps.DEFAULT_RELEASE_STEPS)), 'the shipped list has a duplicate'
    assert len(steps.DEFAULT_RELEASE_STEPS) == 21


def test_every_step_declares_a_kind_from_the_closed_set():
    kinds = {name: step.kind for name, step in steps.RELEASE_STEPS.items()}
    assert all(k in driver.StepKind for k in kinds.values())
    census = {kind: sum(1 for v in kinds.values() if v is kind)
              for kind in driver.StepKind}
    assert census == {driver.StepKind.AUTOMATIC: 9,
                      driver.StepKind.GATE: 1,
                      driver.StepKind.JUDGEMENT: 11}, census


def test_every_step_carries_a_postcondition_sentence_for_the_document():
    """Story 05 renders from here. A step with no sentence would render a row
    with an empty cell — a protocol the reader cannot follow. Both registries:
    a second operation whose steps render blank cells is the same defect."""
    every = set().union(*(set(r) for r in steps.REGISTRIES.values()))
    assert set(steps.STEP_DOC) == every
    assert all(v.strip() for v in steps.STEP_DOC.values())


def test_the_registry_holds_no_second_reader_of_a_verdict_block():
    """`pm/verdict.py` is the ONE parser, and this module reaches for it rather
    than growing a cheaper copy.

    The rule used to be "does not import verdict at all", which was right while
    every finding question had a `pm ready-for` verb to ask. The feature belt
    has none — `ready-for tag` asks about a whole milestone — so
    `review-recorded` and `findings-landed` read the record here. What must
    never appear is a SECOND reader: a regex over `| id | severity |
    disposition |`, a `casefold() == 'open'` beside `verdict.OPEN`, a
    hand-rolled fence walk. The second reader is the permissive one on the day
    they disagree.
    """
    source = (REPO_ROOT / 'src/agentic_sdlc/repo/conveyor/steps.py').read_text(
        encoding='utf-8')
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')
            imported.update(f'{node.module}.{a.name}' for a in node.names)
    assert any('verdict' in name for name in imported), sorted(imported)
    # The disposition token and the block's columns are named in ONE place.
    # Read off the code, not the comments: a paragraph explaining the rule is
    # not a violation of it.
    code = '\n'.join(line for line in source.split('\n')
                     if not line.lstrip().startswith('#'))
    for spelling in ("'open'", '"open"', 'severity', 'disposition |'):
        assert spelling not in code, (
            f'{spelling!r} is spelled in steps.py — the verdict vocabulary is '
            f'verdict.py\'s, and a copy here is the second answer')


def test_no_url_and_no_default_command_for_the_three_that_cannot_be_python():
    """Rule 8: a shipped default naming a repository would put a consumer's
    provenance in this package's code."""
    for name in steps.NO_DEFAULT_COMMAND:
        assert name in steps.RELEASE_STEPS
        assert name not in steps.DEFAULT_COMMANDS, name
        assert steps.RELEASE_STEPS[name].kind is driver.StepKind.JUDGEMENT
    source = (REPO_ROOT / 'src/agentic_sdlc/repo/conveyor/steps.py').read_text(
        encoding='utf-8')
    for scheme in ('https://', 'http://', 'git@', 'github.com'):
        assert scheme not in source, f'{scheme} appears in the step registry'


# --- the three kinds behave as the driver's construction rules demand ---------
def test_the_gate_step_carries_no_do():
    assert steps.RELEASE_STEPS['gate'].do is None


def test_an_unconfigured_judgement_is_unverifiable_and_not_a_pass():
    with tree() as root:
        for name in steps.NO_DEFAULT_COMMAND:
            answer = steps.RELEASE_STEPS[name].check(ctx(root))
            assert answer.truth is driver.Truth.UNVERIFIABLE, (name, answer)
            assert not answer.is_true, name
            assert name in answer.detail, answer.detail


def test_a_configured_command_that_fails_is_not_done_and_names_the_code():
    with tree(config='[release.commands]\nci-green = "exit 3"\n') as root:
        answer = steps.RELEASE_STEPS['ci-green'].check(ctx(root))
        assert answer.truth is driver.Truth.FALSE
        assert 'exited 3' in answer.detail, answer.detail


def test_a_commands_output_is_bounded_into_the_line():
    noisy = "awk 'BEGIN{for(i=0;i<200000;i++)printf \"x\"}'\nexit 1\n"
    with tree({'noisy.sh': noisy},
              config='[release.commands]\nci-green = "sh noisy.sh"\n') as root:
        answer = steps.RELEASE_STEPS['ci-green'].check(ctx(root))
        assert answer.truth is driver.Truth.FALSE
        assert len(answer.detail) < 1000, len(answer.detail)


def test_a_command_that_outruns_the_timeout_stops_the_run():
    config = ('[release]\ncommand_timeout = 1\n\n'
              '[release.commands]\nci-green = "sleep 30"\n')
    with tree(config=config) as root:
        answer = steps.RELEASE_STEPS['ci-green'].check(ctx(root))
        assert answer.truth is driver.Truth.FALSE
        assert 'did not finish' in answer.detail, answer.detail


# --- the automatic steps ------------------------------------------------------
PYPROJECT = '[project]\nname = "x"\nversion = "0.0.1"\n'


def test_version_sync_names_both_current_values_before_writing():
    with tree({'pyproject.toml': PYPROJECT}) as root:
        answer = steps.RELEASE_STEPS['version-sync'].check(ctx(root))
        assert not answer.is_true
        assert '0.0.1' in answer.detail and VERSION in answer.detail


def test_version_sync_is_idempotent_and_writes_nothing_the_second_time():
    with tree({'pyproject.toml': PYPROJECT}) as root:
        step = steps.RELEASE_STEPS['version-sync']
        step.do(ctx(root))
        after = (root / 'pyproject.toml').read_bytes()
        assert step.check(ctx(root)).is_true
        said = step.do(ctx(root))
        assert (root / 'pyproject.toml').read_bytes() == after
        assert 'no version site needed rewriting' in said


def test_version_sync_preserves_crlf():
    with tree({'pyproject.toml': PYPROJECT.replace('\n', '\r\n')}) as root:
        steps.RELEASE_STEPS['version-sync'].do(ctx(root))
        want = PYPROJECT.replace('0.0.1', VERSION).replace('\n', '\r\n')
        assert (root / 'pyproject.toml').read_bytes() == want.encode()


def test_a_do_that_did_not_take_leaves_the_step_not_done(monkeypatch):
    """`verify` is the second ask, and it is the only DONE-maker."""
    with tree({'pyproject.toml': PYPROJECT}) as root:
        step = steps.RELEASE_STEPS['version-sync']
        lying = driver.Step(step.name, step.kind, step.check,
                            lambda c: 'bumped everything, honest')
        known = {lying.name: lying}
        from agentic_sdlc.repo.conveyor import state as run_state
        result = driver.walk(known, (lying.name,), ctx(root),
                             run_state.RunState('release', VERSION))
        assert result.stopped == 'version-sync', result.lines
        assert any('SAID' in line for line in result.lines)
        assert not any('DONE' in line for line in result.lines), result.lines


README = ('# x\n\nsee v0.0.1 in the prose, which is HISTORY\n\n'
          '```\nuvx --from "git+ssh://x@v0.0.1" thing\n```\n')


def test_readme_pins_rewrites_only_inside_fenced_blocks():
    with tree({'README.md': README}) as root:
        step = steps.RELEASE_STEPS['readme-pins']
        assert not step.check(ctx(root)).is_true
        step.do(ctx(root))
        text = (root / 'README.md').read_text(encoding='utf-8')
        assert 'see v0.0.1 in the prose' in text, (
            'a prose mention of an older tag was rewritten — that makes the '
            'document say something false')
        assert f'@v{VERSION}' in text
        assert step.check(ctx(root)).is_true


def test_readme_pins_refuses_a_census_of_zero():
    """Rule 4: a scan that walked nothing must say so, loudly."""
    with tree({'README.md': '# x\n\nno pins here at all\n'}) as root:
        answer = steps.RELEASE_STEPS['readme-pins'].check(ctx(root))
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert 'zero' in answer.detail


# --- the refusal matrix over a hostile tree -----------------------------------
def test_a_milestone_with_no_branch_stamp_refuses_rather_than_assuming():
    with tree() as root:
        path = root / f'pm/roadmap/{VERSION}-scratch/milestone.md'
        path.write_text(MILESTONE.replace(f'branch: milestone/{VERSION}',
                                          'branch:'), encoding='utf-8')
        answer = steps.RELEASE_STEPS['on-milestone-branch'].check(ctx(root))
        assert answer.truth is driver.Truth.UNVERIFIABLE
        assert 'D9' in answer.detail


def test_an_absent_changelog_is_named_and_never_created():
    with tree() as root:
        answer = steps.RELEASE_STEPS[
            'changelog-unreleased-nonempty'].check(ctx(root))
        assert answer.truth is driver.Truth.UNVERIFIABLE
        assert not (root / 'CHANGELOG.md').exists()


@pytest.mark.parametrize('body,why', [
    ('# c\n\n## Unreleased\n\n## v0.0.1 — 2020-01-01\n', 'no bullet'),
    ('# c\n\n## Unreleased\n\n<!-- nothing -->\n', 'a comment is not a bullet'),
    ('# c\n\n## Unreleased\n   \n', 'whitespace is not a bullet'),
])
def test_an_empty_unreleased_section_is_the_case_not_the_headings_absence(
        body, why):
    with tree({'CHANGELOG.md': body}) as root:
        answer = steps.RELEASE_STEPS[
            'changelog-unreleased-nonempty'].check(ctx(root))
        assert not answer.is_true, why


def test_two_unreleased_headings_are_ambiguous_and_never_retitled():
    body = '# c\n\n## Unreleased\n\n- a\n\n## Unreleased\n\n- b\n'
    with tree({'CHANGELOG.md': body}) as root:
        answer = steps.RELEASE_STEPS[
            'changelog-unreleased-nonempty'].check(ctx(root))
        assert not answer.is_true
        assert 'ambiguous' in answer.detail
        said = steps.RELEASE_STEPS['changelog-retitle'].do(ctx(root))
        assert 'refusing to retitle' in said
        assert (root / 'CHANGELOG.md').read_text(encoding='utf-8') == body


def test_changelog_retitle_opens_a_fresh_empty_unreleased_above():
    body = '# c\n\n## Unreleased\n\n- a change\n'
    with tree({'CHANGELOG.md': body}) as root:
        step = steps.RELEASE_STEPS['changelog-retitle']
        assert not step.check(ctx(root)).is_true
        step.do(ctx(root))
        text = (root / 'CHANGELOG.md').read_text(encoding='utf-8')
        assert text.index('## Unreleased') < text.index(f'## v{VERSION}')
        assert step.check(ctx(root)).is_true


RESOLVED_BLOCK = ('```\nverdict: SHIP\n| id | severity | disposition |\n'
                  '| M1 | BLOCKER | landed abc1234 |\n```\n')
OPEN_BLOCK = ('```\nverdict: SHIP-WITH-FIXES\n| id | severity | disposition |\n'
              '| M1 | BLOCKER | open: not done |\n```\n')


def _reviewed_feature(record: str) -> dict[str, str]:
    """One `done` feature whose `reviewed:` points at `record`."""
    return {f'pm/roadmap/{VERSION}-scratch/features/f1/feature.md':
            f'---\nid: {VERSION}/f1\nmilestone: "{VERSION}"\nname: F\n'
            f'status: done\nreviewed: {record}\n---\n\n# F\n'}


def test_findings_resolved_names_a_finding_still_at_open():
    """R1 + R2, and they are one finding read from two ends.

    This step used to require the record to be DELETED, decided by matching the
    version as a SUBSTRING of a filename or a body. Two things wrong with that,
    and the second outlived the first:

    * `review-landed` and `features-done` need the `reviewed:` pointer to
      resolve, so the two could not both hold and a release could not resume
      past this step (R1). D8 removed the halt.
    * **Performing it left `check pm` permanently RED on D1**, because the
      pointers then resolve to nothing — and `check pm` is in `[checks] all`.
      A halt was never the whole defect: removing it changes what a false
      postcondition costs, not whether it is false.
    """
    record = f'docs/reviews/2026-01-01-{VERSION}-review.md'
    files = {record: OPEN_BLOCK, **_reviewed_feature(record)}
    with tree(files) as root:
        answer = steps.RELEASE_STEPS['findings-resolved'].check(ctx(root))
        assert not answer.is_true
        assert 'M1' in answer.detail, answer.detail
        # Dispositioned IN PLACE — the record stays.
        (root / record).write_text(RESOLVED_BLOCK, encoding='utf-8')
        assert steps.RELEASE_STEPS['findings-resolved'].check(ctx(root)).is_true


def test_a_performed_findings_resolved_leaves_check_pm_green():
    """The postcondition that was wrong, asserted directly. Satisfying this
    step must not redden a gate in the stock roster."""
    from agentic_sdlc.repo.checks import pm as check_pm

    record = f'docs/reviews/2026-01-01-{VERSION}-review.md'
    files = {record: RESOLVED_BLOCK, **_reviewed_feature(record),
             # `packaging`, which is where a release actually is by step 14 —
             # `milestone-done` is step 15. At `building` with every feature
             # done, D6 fires about the MILESTONE's own status, which is a
             # true finding about this fixture and not the one under test.
             f'pm/roadmap/{VERSION}-scratch/milestone.md':
                 MILESTONE.replace('status: building', 'status: packaging')}
    with tree(files) as root:
        assert steps.RELEASE_STEPS['findings-resolved'].check(ctx(root)).is_true
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = check_pm.run()
        assert code == 0, buffer.getvalue()


def test_findings_resolved_does_not_ask_the_operator_to_delete_the_record():
    """The `do()` used to say "create → resolve → delete". The record is the
    durable evidence that the review happened and is what `reviewed:` points
    at; a release that destroyed it would be deleting the artifact it exists
    to prove."""
    record = f'docs/reviews/2026-01-01-{VERSION}-review.md'
    with tree({record: OPEN_BLOCK, **_reviewed_feature(record)}) as root:
        said = steps.RELEASE_STEPS['findings-resolved'].do(ctx(root))
    assert 'delete it' not in said.lower(), said
    assert 'resolve and delete' not in said.lower(), said
    assert 'The RECORD stays' in said, said
    assert 'disposition' in said, said


def test_push_branch_refuses_on_the_mainline_and_pushes_nothing():
    with tree() as root:
        subprocess.run(['git', 'checkout', '-q', '-B', 'main'], cwd=root,
                       check=True)
        answer = steps.RELEASE_STEPS['push-branch'].check(ctx(root))
        assert answer.truth is driver.Truth.UNVERIFIABLE
        assert 'pre-push' in answer.detail
        said = steps.RELEASE_STEPS['push-branch'].do(ctx(root))
        assert 'refusing to push' in said and 'nothing was pushed' in said


def test_tag_will_not_guess_the_remote_from_the_local_ref():
    with tree() as root:
        answer = steps.RELEASE_STEPS['tag'].check(ctx(root))
        # No remote at all: unverifiable, never "already true".
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert not answer.is_true


# --- main-merged reads a REFRESHED ref (R7) -----------------------------------
def _clone_with_a_moved_mainline(tmp_path: Path) -> Path:
    """A clone whose `origin/main` is behind the remote's `main`.

    The ordinary shape of a milestone branch that has been open for a day, and
    the one this step used to answer TRUE over.
    """
    def git(cwd, *args):
        subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                        *args], cwd=cwd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    bare, source = tmp_path / 'remote.git', tmp_path / 'source'
    bare.mkdir()
    source.mkdir()
    git(bare, 'init', '-q', '--bare', '-b', 'main', '.')
    git(source, 'init', '-q', '-b', 'main', '.')
    (source / 'f.txt').write_text('one\n', encoding='utf-8')
    git(source, 'add', '-A')
    git(source, 'commit', '-qm', 'one')
    git(source, 'remote', 'add', 'origin', str(bare))
    git(source, 'push', '-q', 'origin', 'main')

    clone = tmp_path / 'clone'
    git(tmp_path, 'clone', '-q', str(bare), str(clone))
    git(clone, 'switch', '-q', '-c', 'milestone/9.9.9')
    (clone / 'w.txt').write_text('work\n', encoding='utf-8')
    git(clone, 'add', '-A')
    git(clone, 'commit', '-qm', 'work')

    # The mainline moves AFTER the clone, and nothing in the clone is told.
    (source / 'f.txt').write_text('one\ntwo\n', encoding='utf-8')
    git(source, 'commit', '-qam', 'two')
    git(source, 'push', '-q', 'origin', 'main')
    return clone


def test_main_merged_refreshes_the_ref_before_it_answers(tmp_path):
    """R7 — it read `origin/<mainline>` and never fetched.

    Measured before the fix, on exactly this fixture:

        local origin/main: 6c12867…   remote main: 041fc6e…
        -> Answer(TRUE, 'origin/main is an ancestor of HEAD')

    TRUE for "the mainline is in this tree" about a mainline that had moved on:
    a gate that missed real drift and printed PASS, off a ref nothing updated.
    Asserted on the ANSWER and on the REF, because "it called fetch" is a claim
    about the transcript and this has to be a claim about what was read.
    """
    clone = _clone_with_a_moved_mainline(tmp_path)
    before = subprocess.run(['git', 'rev-parse', 'origin/main'], cwd=clone,
                            capture_output=True, text=True).stdout.strip()

    answer = steps.check_main_merged(
        driver.Context(root=clone, operation='release', version=VERSION))

    after = subprocess.run(['git', 'rev-parse', 'origin/main'], cwd=clone,
                           capture_output=True, text=True).stdout.strip()
    assert before != after, 'origin/main was never refreshed'
    assert not answer.is_true, answer
    assert 'not an ancestor' in answer.detail, answer.detail


def test_main_merged_will_not_answer_from_a_ref_it_could_not_refresh(tmp_path):
    """An unreachable remote is UNVERIFIABLE, never a pass off the stale ref.

    `check_tag` already rules this shape: what the remote holds is a fact about
    the remote, and this will not guess it from the local copy. Without the
    refusal the fetch would be decorative — a failed fetch would leave the old
    read intact and R7 would reproduce on every offline run.
    """
    clone = _clone_with_a_moved_mainline(tmp_path)
    subprocess.run(['git', 'remote', 'set-url', 'origin', str(tmp_path / 'no')],
                   cwd=clone, check=True)

    answer = steps.check_main_merged(
        driver.Context(root=clone, operation='release', version=VERSION))

    assert answer.truth is driver.Truth.UNVERIFIABLE, answer
    assert 'could not be refreshed' in answer.detail, answer.detail


def test_a_repo_with_no_remote_still_answers_from_its_local_mainline():
    """The fetch is not allowed to redden a repo that simply has no origin.

    Rule 5's shape: a local-only checkout is a legitimate consumer, and a
    refusal there would be the refresh deciding something it was not asked.
    """
    with tree() as root:
        subprocess.run(['git', 'checkout', '-q', '-B', 'main'], cwd=root,
                       check=True)
        subprocess.run(['git', 'checkout', '-q', '-b', f'milestone/{VERSION}'],
                       cwd=root, check=True)
        answer = steps.check_main_merged(ctx(root))
    assert answer.is_true, answer
    assert answer.detail == 'main is an ancestor of HEAD', answer.detail


def test_a_step_whose_check_raises_answers_unverifiable_and_names_the_crash():
    """A crash is an ANSWER now, not an escape — D8, via `driver.ask`.

    It used to propagate, and that was survivable only while the walk halted:
    a latent crash in step 19 was usually never reached because the run had
    already returned. With every step asked on every run it would surface as an
    uncaught traceback and exit 1 — the code hard rule 6 gives to FINDINGS, and
    the one a consumer's CI reads as drift. So it is UNVERIFIABLE (it did not
    answer "no"; it failed to answer) and the exception type is in the line.
    """
    def explode(_c):
        raise RuntimeError('boom')

    bad = driver.Step('gate', driver.StepKind.GATE, explode)
    with tree() as root:
        from agentic_sdlc.repo.conveyor import state as run_state
        result = driver.walk({'gate': bad}, ('gate',), ctx(root),
                             run_state.RunState('release', VERSION))
    assert result.unverifiable == ('gate',), result.lines
    assert result.not_true == (), result.lines
    assert result.exit_code == 1
    said = '\n'.join(result.lines)
    assert 'RuntimeError' in said and 'boom' in said, said


# --- the list as config -------------------------------------------------------
def test_no_devkit_toml_and_the_stock_list_declared_are_the_same_bytes():
    """Rule 5, the equivalence test."""
    declared = ('[release]\nsteps = [\n'
                + ''.join(f'  "{n}",\n' for n in steps.DEFAULT_RELEASE_STEPS)
                + ']\n')
    with tree() as root:
        absent = driver.step_names('release')
    with tree(config=declared) as root:
        explicit = driver.step_names('release')
    assert absent == explicit == steps.DEFAULT_RELEASE_STEPS


@pytest.mark.parametrize('config,expected', [
    ('[release]\nsteps = "tree-clean"\n', 'list of strings'),
    ('[release]\nsteps = []\n', 'remove the key'),
    ('[release]\nsteps = ["tree-clan"]\n', 'no step is registered'),
    ('[release]\nsteps = ["tree-clean", 3]\n', 'must be a string'),
    ('[release]\nsteps = [["tree-clean"]]\n', 'must be a string'),
    ('[release]\nsteps = ["tree clean"]\n', 'not a step name'),
    ('[release]\nsteps = ["gate;rm -rf /"]\n', 'not a step name'),
    ('[release]\nsteps = ["../gate"]\n', 'not a step name'),
    ('[release]\nsteps = ["$(gate)"]\n', 'not a step name'),
    ('[release]\nsteps = ["gate/x"]\n', 'not a step name'),
    ('[release]\nsteps = ["' + 'g' * 4096 + '"]\n', 'the limit is'),
    ('[release]\ncommands = "gh pr checks"\n', 'table of step'),
    ('[release.commands]\nci-green = 3\n', 'one command string'),
    ('[release.commands]\nci-green = []\n', 'one command string'),
    ('[release.commands]\nci-green = ""\n', 'is empty'),
    ('[release.commands]\nci-green = "   "\n', 'is empty'),
    ('[release.commands]\n"version-sync" = "x"\n', 'AUTOMATIC'),
    ('[release]\nsteps = ["gate"]\n\n[release.commands]\nci-green = "x"\n',
     'never runs'),
    ('[release.commands]\nnot-a-step = "x"\n', 'names no registered step'),
    ('[release]\ncommand_timeout = "soon"\n', 'positive integer'),
    ('[release]\npin_files = "README.md"\n', 'non-empty list'),
])
def test_the_config_refusal_matrix_is_exit_2_and_runs_no_step(config, expected,
                                                              capsys):
    with tree(config=config) as root:
        with pytest.raises(ConfigError) as err:
            driver.step_names('release')
        assert expected in str(err.value), str(err.value)
    assert not (root / '.agentic-sdlc').exists()


def test_a_non_table_release_section_is_refused():
    with tree(config='release = "x"\n'):
        with pytest.raises(ConfigError):
            driver.step_names('release')


def test_duplicates_collapse_in_declaration_order_and_are_reported(capsys):
    config = '[release]\nsteps = ["gate", "tree-clean", "gate"]\n'
    with tree(config=config):
        assert driver.step_names('release') == ('gate', 'tree-clean')
    assert 'more than once' in capsys.readouterr().out


def test_tree_clean_is_the_defect_the_step_reports_not_a_crash():
    with tree() as root:
        (root / 'dirty.txt').write_text('x', encoding='utf-8')
        answer = steps.RELEASE_STEPS['tree-clean'].check(ctx(root))
        assert not answer.is_true
        assert 'dirty.txt' in answer.detail


# --- tree-clean says whose path is whose (R6) ---------------------------------
LEDGER_REL = f'pm/roadmap/{VERSION}-scratch/ledger.jsonl'


def test_tree_clean_names_the_ledger_the_gate_step_dirtied_as_the_belts_own():
    """R6 — `gate` dirties the TRACKED ledger, and the census blamed the operator.

    Story 04's stated reason for writing only deviations is that *"the ledger
    is tracked, so a row per completed step would dirty the tree and falsify
    `tree-clean`"*. The driver honours it; step 10 does not — `gate` runs the
    project's gate command and the shipped `gdk_gate.sh` files a cost row per
    gate through `GDK_LEDGER_CMD` into that same tracked file. Measured on a
    stock consumer with the milestone `building` and the ledger committed
    clean:

        $ make check
        $ git status --porcelain
         M pm/roadmap/1.0.0-m/ledger.jsonl

    The write is not the finding — those rows are the record `pm ledger report`
    is built on. The finding is the SENTENCE: the path was counted with the
    operator's own and `do()` told them to "commit or stash your own paths"
    about a file the belt wrote. So it is still counted (rule 4 — nothing is
    excluded from the census) and it is now attributed.
    """
    with tree({LEDGER_REL: '{"kind":"status"}\n'}) as root:
        (root / LEDGER_REL).write_text(
            '{"kind":"status"}\n{"kind":"gate","gate":"check"}\n',
            encoding='utf-8')
        (root / 'mine.txt').write_text('x', encoding='utf-8')
        answer = steps.RELEASE_STEPS['tree-clean'].check(ctx(root))
        said = steps.RELEASE_STEPS['tree-clean'].do(ctx(root))
    assert not answer.is_true, answer
    # BOTH paths in the census — the attribution never subtracts one.
    assert '2 modified path(s)' in answer.detail, answer.detail
    assert 'mine.txt' in answer.detail and LEDGER_REL in answer.detail
    assert "belt's OWN" in answer.detail, answer.detail
    assert 'not one of yours' in said and LEDGER_REL in said, said


def test_tree_clean_says_nothing_about_the_ledger_when_the_belt_did_not_write_it():
    """The other direction, so the attribution above is not printed blind.

    An attribution that appears whether or not the path is dirty is a sentence
    the reader learns to ignore, and this step's whole subject is which paths
    are whose.
    """
    with tree({LEDGER_REL: '{"kind":"status"}\n'}) as root:
        (root / 'mine.txt').write_text('x', encoding='utf-8')
        answer = steps.RELEASE_STEPS['tree-clean'].check(ctx(root))
    assert not answer.is_true, answer
    assert '1 modified path(s)' in answer.detail, answer.detail
    assert "belt's OWN" not in answer.detail, answer.detail


def test_the_first_modified_path_is_not_short_by_one_character(tmp_path):
    """`git status --porcelain` is COLUMNAR, and a blanket strip ate column 0.

    The format is `XY<space>PATH`, and X is a space for a worktree-only change.
    `_git` stripped the whole output, so the first line arrived as `M SDLC.md`
    instead of ` M SDLC.md` and `line[3:]` returned `DLC.md` — right for every
    path below it, wrong for the first, and wrong in the direction that looks
    like a real filename. Found by running the conveyor on this repo.

    The fixture uses two files on purpose: one alone would pass against a parse
    that is wrong only about the first line.
    """
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', '.'], cwd=root, check=True)
    for name in ('SDLC.md', 'zzz.md'):
        (root / name).write_text('one\n', encoding='utf-8')
    subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
    subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                    'commit', '-qm', 'init'], cwd=root, check=True)
    for name in ('SDLC.md', 'zzz.md'):
        (root / name).write_text('two\n', encoding='utf-8')

    answer = steps.check_tree_clean(
        driver.Context(root=root, operation='release', version='0.2.0'))

    assert not answer.is_true
    # The whole list, compared exactly. A substring check cannot see this
    # defect: `'DLC.md'` is IN `'SDLC.md'`, so the obvious assertion passes on
    # the broken parse — which is a small demonstration of why the bug survived
    # in the first place.
    listed = answer.detail.split(': ', 1)[1].split(', ')
    assert listed == ['SDLC.md', 'zzz.md'], listed
