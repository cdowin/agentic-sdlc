"""test_conveyor_steps.py — the release registry, and the ordering that is the
whole point of it.

The headline is `test_open_finding_stops_before_gate`: on a tree whose review
has not landed, the conveyor never reaches `gate`. That is the 0.24.0 mistake —
`make milestone` run twice before a reviewer that then asked for fixes, both
runs void before the tag — made STRUCTURALLY IMPOSSIBLE rather than left as a
paragraph somebody has to remember. It is asserted with a COMMAND RECORDER (a
gate command that leaves a file on disk if it runs), never by reading the
transcript: a transcript that does not mention the gate is not proof the gate
did not run.

Every write-verb test here works on a scratch tree, never on a fixture in place.
"""
from __future__ import annotations

import ast
import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

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
    """A scratch repo with a milestone directory, entered."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / f'pm/roadmap/{VERSION}-scratch').mkdir(parents=True)
        (root / f'pm/roadmap/{VERSION}-scratch/milestone.md').write_text(
            MILESTONE, encoding='utf-8')
        if config:
            (root / 'devkit.toml').write_text(config, encoding='utf-8')
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
def test_open_finding_stops_before_gate(monkeypatch):
    """`review-landed` refuses, and the gate command is never invoked.

    Proven by a RECORDER — the configured gate command creates a file — because
    "the transcript does not mention gate" is a claim about output, and this
    has to be a claim about what ran.
    """
    monkeypatch.setattr(
        steps, 'ready_for',
        lambda c, target: driver.Answer.no('M1, M2 are at disposition: open'))
    with tree(config='[release.commands]\ngate = "touch GATE-RAN"\n') as root:
        result = walk(root, ('review-landed', 'gate'))
        assert result.stopped == 'review-landed', result.lines
        assert result.exit_code == 1
        assert not (root / 'GATE-RAN').exists(), (
            'the gate command RAN behind a review that had not landed')
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
    with an empty cell — a protocol the reader cannot follow."""
    assert set(steps.STEP_DOC) == set(steps.RELEASE_STEPS)
    assert all(v.strip() for v in steps.STEP_DOC.values())


def test_the_registry_does_not_import_verdict():
    """Two readers of "is every finding dispositioned" are two answers, and
    the second one is the permissive one on the day they disagree."""
    source = (REPO_ROOT / 'src/agentic_sdlc/repo/conveyor/steps.py').read_text(
        encoding='utf-8')
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')
            imported.update(f'{node.module}.{a.name}' for a in node.names)
    assert not any('verdict' in name for name in imported), sorted(imported)


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


def test_findings_resolved_names_the_record_that_is_still_there():
    record = f'docs/reviews/2026-01-01-{VERSION}-review.md'
    with tree({record: f'# review of {VERSION}\n'}) as root:
        answer = steps.RELEASE_STEPS['findings-resolved'].check(ctx(root))
        assert not answer.is_true
        assert record in answer.detail, answer.detail
        (root / record).unlink()
        assert steps.RELEASE_STEPS['findings-resolved'].check(ctx(root)).is_true


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


def test_a_step_whose_check_raises_stops_the_run_and_names_it():
    def explode(_c):
        raise RuntimeError('boom')

    bad = driver.Step('gate', driver.StepKind.GATE, explode)
    with tree() as root:
        from agentic_sdlc.repo.conveyor import state as run_state
        with pytest.raises(RuntimeError):
            driver.walk({'gate': bad}, ('gate',), ctx(root),
                        run_state.RunState('release', VERSION))


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
