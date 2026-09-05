"""test_conveyor_adopt.py — the adopt list, and the subtraction that is the
whole feature.

The headline is `test_checks_pass_never_runs_make`: adoption runs THIS
package's `check all` and never the consumer's `make check`. The consumer's own
gates verify the consumer's code against the consumer's rules, and a version
bump here cannot change their verdict — so running them during adoption
re-verifies the game, not the adoption. It is asserted with a COMMAND RECORDER
and a SENTINEL FILE, never by reading the transcript: a transcript that does not
mention make is not proof make did not run.

Every write-verb test here works on a scratch tree, never on a fixture in place.
"""
from __future__ import annotations

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
from agentic_sdlc import __version__  # noqa: E402
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, state as run_state, steps  # noqa: E402

VERSION = '9.9.9'
MILESTONE = f'''---
id: "{VERSION}"
name: A scratch milestone
status: building
branch: milestone/{VERSION}
---

# A scratch milestone
'''
PIN = f'DEVKIT_VERSION := v{__version__}\n'


@contextlib.contextmanager
def tree(files: dict[str, str] | None = None, config: str = '',
         sibling: bool = False):
    """A scratch consumer with a milestone directory, entered.

    `sibling` plants a DECOY repo beside it: rule 8 says `adopt` runs in a
    consumer's own tree and reads no second repo, so the tests assert the decoy
    comes back byte-identical.
    """
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
        if sibling:
            decoy = Path(tmp) / 'next-door'
            (decoy / 'tools/hooks').mkdir(parents=True)
            (decoy / 'Makefile').write_text('DEVKIT_VERSION := v0.0.1\n',
                                            encoding='utf-8')
            (decoy / 'Makefile.devkit').write_text('# not yours\n',
                                                   encoding='utf-8')
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
    return driver.Context(root=root, operation='adopt', version=VERSION)


def walk(root: Path, names=None, **kw):
    known = driver.registry_for('adopt')
    run = run_state.RunState('adopt', VERSION)
    return driver.walk(known, names or steps.DEFAULT_ADOPT_STEPS, ctx(root),
                       run, **kw)


def step(name: str):
    return steps.ADOPT_STEPS[name]


def decoy_bytes(root: Path) -> dict[str, bytes]:
    beside = root.parent / 'next-door'
    return {str(p.relative_to(beside)): p.read_bytes()
            for p in sorted(beside.rglob('*')) if p.is_file()}


# --- the census ---------------------------------------------------------------
def test_the_adopt_registry_is_exactly_the_shipped_list():
    assert set(steps.ADOPT_STEPS) == set(steps.DEFAULT_ADOPT_STEPS)
    assert steps.DEFAULT_ADOPT_STEPS == (
        'pin-bumped', 'installables-diffed', 'installable-decisions-recorded',
        'config-updated', 'hooks-self-test', 'runner-targets-resolve',
        'checks-pass', 'pm-validates')
    assert len(steps.DEFAULT_ADOPT_STEPS) == 8


def test_the_kind_census_of_the_eight():
    kinds = {n: s.kind for n, s in steps.ADOPT_STEPS.items()}
    census = {kind: sum(1 for v in kinds.values() if v is kind)
              for kind in driver.StepKind}
    assert census == {driver.StepKind.AUTOMATIC: 1,
                      driver.StepKind.GATE: 4,
                      driver.StepKind.JUDGEMENT: 3}, census
    assert [n for n, s in kinds.items()
            if s is driver.StepKind.AUTOMATIC] == ['installables-diffed']
    for name in ('hooks-self-test', 'runner-targets-resolve', 'checks-pass',
                 'pm-validates'):
        assert steps.ADOPT_STEPS[name].do is None, name


def test_every_adopt_step_carries_a_postcondition_sentence():
    for name in steps.DEFAULT_ADOPT_STEPS:
        assert steps.STEP_DOC.get(name, '').strip(), name


def test_the_two_registries_are_separate():
    """A release step named in `[adopt] steps` is a typo, not a feature."""
    assert not set(steps.ADOPT_STEPS) & set(steps.RELEASE_STEPS)


# --- THE SUBTRACTION ----------------------------------------------------------
MAKEFILE_SENTINEL = (
    'DEVKIT_VERSION := v%s\n'
    'check:\n'
    '\t@touch MAKE-CHECK-RAN\n'
    'my-gate:\n'
    '\t@touch EXTRA-GATE-RAN\n' % __version__)


def test_checks_pass_never_runs_make(monkeypatch):
    """`checks-pass` runs `agentic-sdlc check all` — never `make check`.

    ADOPT-IS-A-CONVEYOR SHIP CRITERION 2. A consumer's `make check` also runs
    its own twenty gates, they verify the consumer's code against the
    consumer's rules, and a version bump here cannot change their verdict.
    This is one line of the feature, it is easy to write correctly, and it is
    exactly the line that regresses the first time somebody makes adoption
    'more thorough'.
    """
    recorded: list[tuple[str, ...]] = []

    def recorder(context, *argv):
        recorded.append(argv)
        return 0, 'recorded', ('agentic-sdlc',) + argv

    config = ('[adopt]\nsteps = ["checks-pass"]\n\n'
              '[gates]\nextra = ["my-gate"]\n')
    with tree({'Makefile': MAKEFILE_SENTINEL}, config=config) as root:
        monkeypatch.setattr(steps, '_own_cli', recorder)
        result = walk(root, ('checks-pass',))
        assert result.exit_code == 0, result.lines
        assert recorded == [('check', 'all')], (
            f'checks-pass ran {recorded!r} — adoption verifies the ADOPTION: '
            f'`check all` in this package, never the consumer\'s make')
        for argv in recorded:
            assert not any('make' in a for a in argv), argv
            assert 'my-gate' not in argv, argv


def test_checks_pass_leaves_the_consumers_own_gates_unrun():
    """The same claim without the recorder: the real step, a real `make`
    target that leaves a file behind, and the file must not be there."""
    config = ('[adopt]\nsteps = ["checks-pass"]\n\n'
              '[gates]\nextra = ["my-gate"]\n')
    with tree({'Makefile': MAKEFILE_SENTINEL}, config=config) as root:
        result = walk(root, ('checks-pass',))
        # Not vacuous: the step really ran, and its verdict came from a
        # command. A test that passed because nothing walked would prove
        # nothing at all.
        assert result.exit_code in (0, 1), result.lines
        assert any('checks-pass] GATE' in line for line in result.lines), \
            result.lines
        assert not (root / 'MAKE-CHECK-RAN').exists(), (
            'the consumer\'s `make check` RAN during adoption')
        assert not (root / 'EXTRA-GATE-RAN').exists(), (
            'a [gates] extra target RAN during adoption')


def test_the_whole_list_leaves_the_consumers_own_gates_unrun():
    with tree({'Makefile': MAKEFILE_SENTINEL}) as root:
        walk(root)
        assert not (root / 'MAKE-CHECK-RAN').exists()
        assert not (root / 'EXTRA-GATE-RAN').exists()


def test_checks_pass_says_a_config_error_differently_from_findings(monkeypatch):
    answers = {}
    for code in (1, 2):
        monkeypatch.setattr(
            steps, '_own_cli',
            lambda c, *a, _c=code: (_c, 'said', ('agentic-sdlc',) + a))
        with tree() as root:
            answers[code] = step('checks-pass').check(ctx(root))
    assert not answers[1].is_true and not answers[2].is_true
    assert answers[1].detail != answers[2].detail
    assert 'config' in answers[2].detail.lower(), answers[2].detail


def test_checks_pass_fails_on_an_empty_roster():
    """Rule 4 at this layer: a roster that walked nothing is not a pass."""
    with tree(config='[checks]\nall = []\n') as root:
        answer = step('checks-pass').check(ctx(root))
        assert not answer.is_true, answer
        assert 'config' in answer.detail.lower(), answer.detail


# --- the two a human list keeps forgetting ------------------------------------
NEUTERED = ('#!/usr/bin/env bash\n'
            '# a guard that fails OPEN is not there\n'
            'case "$1" in --self-test) exit 0 ;; esac\n'
            'exit 0\n')


def _install_hooks(root: Path) -> None:
    from agentic_sdlc.repo import install
    install.main('install-hooks', [])
    subprocess.run(['git', 'config', 'core.hooksPath', 'tools/hooks'],
                   cwd=root, check=True)


def test_hooks_self_test_fails_on_a_guard_that_stops_nothing():
    """A hook installed, executable, and returning nothing its own corpus
    asserts. This package has already shipped exactly that."""
    with tree() as root:
        _install_hooks(root)
        target = root / 'tools/hooks/pre-push'
        target.write_text(NEUTERED, encoding='utf-8')
        target.chmod(0o755)
        answer = step('hooks-self-test').check(ctx(root))
        assert not answer.is_true, answer
        assert 'pre-push' in answer.detail or 'hooks' in answer.detail


def test_hooks_self_test_refuses_a_repo_with_no_corpus():
    with tree() as root:
        answer = step('hooks-self-test').check(ctx(root))
        assert not answer.is_true
        assert 'tools/hooks' in answer.detail, answer.detail
        assert not (root / 'tools/hooks').exists(), 'the step installed a hook'


DEVKIT_MK = (REPO_ROOT
             / 'src/agentic_sdlc/repo/installables/Makefile.devkit').read_text(
                 encoding='utf-8')
GATE_LIB = (REPO_ROOT
            / 'src/agentic_sdlc/repo/installables/gdk_gate.sh').read_text(
                encoding='utf-8')


def _framework(extra: str = '') -> dict[str, str]:
    return {'Makefile': f'DEVKIT_VERSION := v{__version__}\n{extra}'
                        'include Makefile.devkit\n',
            'Makefile.devkit': DEVKIT_MK,
            'tools/dev/gdk_gate.sh': GATE_LIB}


def test_runner_targets_resolve_fails_on_a_named_tier_file_that_is_absent():
    """`-include` of a missing file is SILENT by design, and that silence is
    what a typo'd tier file hides. It must FAIL here, naming the file."""
    with tree(_framework('GDK_PRECOMMIT_TIERS := unit\n')) as root:
        answer = step('runner-targets-resolve').check(ctx(root))
        assert not answer.is_true, answer
        assert 'Makefile.tiers' in answer.detail, answer.detail


def test_runner_targets_resolve_passes_and_says_so_on_an_empty_tier_list():
    """The other direction: no tier file and no tier list is a SUPPORTED
    shape, and the step says which of the two cases it saw."""
    with tree(_framework()) as root:
        answer = step('runner-targets-resolve').check(ctx(root))
        assert answer.is_true, answer
        assert 'TIERS' in answer.detail, answer.detail


def test_runner_targets_resolve_resolves_a_real_tier_file():
    files = _framework('GDK_PRECOMMIT_TIERS := unit\n')
    files['Makefile.tiers'] = ('.PHONY: unit\nunit:\n\t@echo unit\n')
    with tree(files) as root:
        answer = step('runner-targets-resolve').check(ctx(root))
        assert answer.is_true, answer


def test_runner_targets_resolve_refuses_a_repo_with_no_framework():
    with tree() as root:
        answer = step('runner-targets-resolve').check(ctx(root))
        assert not answer.is_true
        assert 'Makefile.devkit' in answer.detail, answer.detail
        assert not (root / 'Makefile.devkit').exists(), 'the step installed it'


# --- the steps this package cannot perform ------------------------------------
def test_pin_bumped_names_the_line_and_writes_nothing():
    with tree({'Makefile': 'DEVKIT_VERSION := v0.0.1\ninclude x\n'}) as root:
        before = (root / 'Makefile').read_bytes()
        answer = step('pin-bumped').check(ctx(root))
        assert not answer.is_true
        assert '0.0.1' in answer.detail and __version__ in answer.detail
        assert 'Makefile:1' in answer.detail, answer.detail
        said = step('pin-bumped').do(ctx(root))
        assert __version__ in said
        assert (root / 'Makefile').read_bytes() == before, (
            'pin-bumped edited the consumer\'s Makefile')


def test_pin_bumped_passes_once_the_line_names_the_running_version():
    with tree({'Makefile': PIN}) as root:
        assert step('pin-bumped').check(ctx(root)).is_true


def test_pin_bumped_refuses_a_repo_with_no_makefile():
    with tree() as root:
        answer = step('pin-bumped').check(ctx(root))
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert 'Makefile' in answer.detail
        assert not (root / 'Makefile').exists(), 'the step created a Makefile'


def test_pin_bumped_refuses_a_makefile_with_no_pin_line():
    with tree({'Makefile': 'all:\n\t@echo hi\n'}) as root:
        answer = step('pin-bumped').check(ctx(root))
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert 'DEVKIT_VERSION' in answer.detail


# --- the diff, and the decision that reads it ---------------------------------
def _installed(name: str, rel: str) -> tuple[str, str]:
    from agentic_sdlc.repo import install
    return rel, install.body_of(name)


def test_installables_diffed_writes_the_census_and_check_reads_the_tree():
    rel, body = _installed('pre-push', 'tools/hooks/pre-push')
    with tree({rel: body + '\n# a local edit\n'}) as root:
        target = step('installables-diffed')
        assert not target.check(ctx(root)).is_true
        target.do(ctx(root))
        report = root / steps.REPORT_REL
        assert report.is_file(), 'no diff report was produced'
        assert rel in report.read_text(encoding='utf-8')
        assert target.check(ctx(root)).is_true
        # The report is checked AGAINST THE TREE, never as a flag: change the
        # file and the census it recorded is stale.
        (root / rel).write_text(body + '\n# another edit\n', encoding='utf-8')
        assert not target.check(ctx(root)).is_true


def test_installables_diffed_is_idempotent():
    rel, body = _installed('pre-push', 'tools/hooks/pre-push')
    with tree({rel: body + '\n# a local edit\n'}) as root:
        target = step('installables-diffed')
        target.do(ctx(root))
        first = (root / steps.REPORT_REL).read_bytes()
        target.do(ctx(root))
        assert (root / steps.REPORT_REL).read_bytes() == first


def test_a_decision_is_the_operators_and_regeneration_preserves_it():
    rel, body = _installed('pre-push', 'tools/hooks/pre-push')
    with tree({rel: body + '\n# a local edit\n'}) as root:
        steps.ADOPT_STEPS['installables-diffed'].do(ctx(root))
        decisions = step('installable-decisions-recorded')
        answer = decisions.check(ctx(root))
        assert not answer.is_true, answer
        assert rel in answer.detail, answer.detail
        report = root / steps.REPORT_REL
        report.write_text(
            report.read_text(encoding='utf-8')
            + f'\n{rel}: hand-applied — the header is ours\n', encoding='utf-8')
        assert decisions.check(ctx(root)).is_true
        # And a regenerated census does not eat the operator's own lines.
        steps.ADOPT_STEPS['installables-diffed'].do(ctx(root))
        assert 'hand-applied' in report.read_text(encoding='utf-8')


def test_no_drift_is_no_decision_to_record():
    with tree() as root:
        steps.ADOPT_STEPS['installables-diffed'].do(ctx(root))
        assert step('installable-decisions-recorded').check(ctx(root)).is_true


def test_decisions_refuses_before_the_diff_has_been_produced():
    rel, body = _installed('pre-push', 'tools/hooks/pre-push')
    with tree({rel: body + '\n# a local edit\n'}) as root:
        answer = step('installable-decisions-recorded').check(ctx(root))
        assert not answer.is_true, answer
        assert steps.REPORT_REL in answer.detail, answer.detail


# --- config-updated -----------------------------------------------------------
def test_config_updated_names_the_key_this_version_refuses():
    with tree(config='[gates]\nextra = "my-gate"\n') as root:
        answer = step('config-updated').check(ctx(root))
        assert not answer.is_true, answer
        assert 'gates' in answer.detail, answer.detail


def test_config_updated_passes_a_stock_repo_and_reports_its_census():
    with tree() as root:
        answer = step('config-updated').check(ctx(root))
        assert answer.is_true, answer
        assert any(ch.isdigit() for ch in answer.detail), answer.detail


# --- pm-validates -------------------------------------------------------------
def test_pm_validates_refuses_a_repo_with_no_pm_tree():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            answer = step('pm-validates').check(ctx(root))
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()
    assert not answer.is_true, answer
    assert 'pm/roadmap' in answer.detail, answer.detail


def test_pm_validates_passes_a_scratch_tree():
    with tree() as root:
        assert step('pm-validates').check(ctx(root)).is_true


# --- rule 8: the tree it runs in, and no other ---------------------------------
def test_the_whole_list_touches_no_repo_but_this_one():
    with tree({'Makefile': PIN}, sibling=True) as root:
        before = decoy_bytes(root)
        walk(root)
        assert decoy_bytes(root) == before, 'a sibling repo was written to'


def test_no_adopt_step_names_a_repository():
    source = (REPO_ROOT / 'src/agentic_sdlc/repo/conveyor/steps.py').read_text(
        encoding='utf-8')
    for scheme in ('https://', 'http://', 'git@', 'github.com'):
        assert scheme not in source, scheme


# --- the run state is per operation -------------------------------------------
def test_adopt_writes_only_its_own_run_file():
    with tree({'Makefile': 'DEVKIT_VERSION := v0.0.1\n'}) as root:
        release_json = run_state.path_for(root, 'release')
        release_json.parent.mkdir(parents=True, exist_ok=True)
        release_json.write_text('{"mine": true}', encoding='utf-8')
        code = driver.main(['adopt', VERSION], root=root)
        assert code == 1, 'a stopped run is exit 1'
        assert release_json.read_text(encoding='utf-8') == '{"mine": true}'
        assert run_state.path_for(root, 'adopt').is_file()


def test_a_deleted_run_file_costs_nothing():
    with tree({'Makefile': PIN}) as root:
        first = driver.main(['adopt', VERSION], root=root)
        run_state.path_for(root, 'adopt').unlink()
        assert driver.main(['adopt', VERSION], root=root) == first


# --- the refusal matrix (SDLC.md §5) ------------------------------------------
@pytest.mark.parametrize('config,expected', [
    ('[adopt]\nsteps = "pin-bumped"\n', 'list of strings'),
    ('[adopt]\nsteps = []\n', 'remove the key'),
    ('[adopt]\nsteps = ["pin-bumpd"]\n', 'no step is registered'),
    ('[adopt]\nsteps = ["tag"]\n', 'no step is registered'),
    ('[adopt]\nsteps = ["merge"]\n', 'no step is registered'),
    ('[adopt]\nsteps = ["pin-bumped", 3]\n', 'must be a string'),
    ('[adopt]\nsteps = ["pin bumped"]\n', 'not a step name'),
    ('[adopt]\nsteps = ["checks-pass;rm -rf /"]\n', 'not a step name'),
    ('[adopt]\nsteps = ["../checks-pass"]\n', 'not a step name'),
    ('[adopt]\nsteps = ["$(checks-pass)"]\n', 'not a step name'),
    ('[adopt]\nsteps = ["' + 'g' * 4096 + '"]\n', 'the limit is'),
    ('[adopt]\ncommands = "make check"\n', 'table of step'),
    ('[adopt.commands]\nchecks-pass = 3\n', 'one command string'),
    ('[adopt.commands]\nchecks-pass = ""\n', 'is empty'),
    ('[adopt.commands]\n"installables-diffed" = "x"\n', 'AUTOMATIC'),
    ('[adopt.commands]\ntag = "x"\n', 'names no registered step'),
    ('[adopt]\nsteps = ["pin-bumped"]\n\n[adopt.commands]\n'
     'checks-pass = "x"\n', 'never runs'),
    ('[adopt]\ncommand_timeout = "soon"\n', 'positive integer'),
    ('[adopt]\npin_file = 3\n', 'pin_file'),
    ('[adopt]\nrunner_targets = "check"\n', 'runner_targets'),
    ('[adopt]\nrunner_targets = []\n', 'runner_targets'),
])
def test_the_config_refusal_matrix_is_exit_2_and_runs_no_step(config, expected):
    with tree(config=config) as root:
        with pytest.raises(ConfigError) as err:
            driver.step_names('adopt')
        assert expected in str(err.value), str(err.value)
        assert not (root / '.agentic-sdlc').exists()


def test_no_devkit_toml_and_the_stock_list_declared_are_the_same_bytes():
    """Rule 5, the equivalence test, over the adopt list."""
    declared = ('[adopt]\nsteps = [\n'
                + ''.join(f'  "{n}",\n' for n in steps.DEFAULT_ADOPT_STEPS)
                + ']\n')
    with tree():
        absent = driver.step_names('adopt')
    with tree(config=declared):
        explicit = driver.step_names('adopt')
    assert absent == explicit == steps.DEFAULT_ADOPT_STEPS


@pytest.mark.parametrize('argv,expected', [
    (['adopt'], 2),
    (['adopt', '--nope'], 2),
    (['adopt', '0.2.0', 'extra'], 2),
    (['adopt', '../etc'], 2),
    (['adopt', '9.9.9', '--skip', 'checks-pass'], 2),
])
def test_the_verb_refusal_matrix(argv, expected, capsys):
    with tree() as root:
        assert driver.main(argv, root=root) == expected
        assert not (root / '.agentic-sdlc').exists()
    capsys.readouterr()


def test_a_skip_writes_one_deviation_row_and_is_idempotent():
    with tree({'Makefile': PIN}) as root:
        argv = ['adopt', VERSION, '--skip', 'hooks-self-test', '--reason',
                'this consumer arms no hooks']
        driver.main(argv, root=root)
        ledger = root / f'pm/roadmap/{VERSION}-scratch/ledger.jsonl'
        assert ledger.is_file()
        rows = [ln for ln in ledger.read_text(encoding='utf-8').split('\n')
                if 'hooks-self-test' in ln]
        driver.main(argv, root=root)
        again = [ln for ln in ledger.read_text(encoding='utf-8').split('\n')
                 if 'hooks-self-test' in ln]
        assert len(rows) == 1 and again == rows, again
