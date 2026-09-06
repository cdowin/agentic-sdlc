"""test_conveyor_steps.py — the release checks, each a read of a real tree.

Every check here is a question about a scratch git repo, and every answer is
asserted against the bytes the check left behind (none) as much as against
the sentence it returned. Under D12 no check writes: `version-sync` READS the
version sites and names the release commit as the caller's, the changelog is
read and never retitled, and the gate is a configured command whose exit code
is the whole answer.
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
from support.pm import with_flow  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402

VERSION = '9.9.9'
MDIR = f'pm/roadmap/{VERSION}-scratch'
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
    """A scratch repo with a milestone directory, committed, entered.
    `config` is the devkit.toml MINUS the flow declaration (`with_flow`)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / MDIR).mkdir(parents=True)
        (root / MDIR / 'milestone.md').write_text(MILESTONE, encoding='utf-8')
        (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
        for rel, body in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        subprocess.run(['git', 'init', '-q', '-b', f'milestone/{VERSION}'],
                       cwd=root, check=True)
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


def check(name: str, root: Path) -> driver.Answer:
    return steps.RELEASE_STEPS[name].check(ctx(root))


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.parts}


# --- the census ---------------------------------------------------------------
def test_the_release_registry_is_exactly_the_shipped_list_and_every_check_has_a_sentence():
    """Bites: a name in the list nothing runs, a check nothing lists, or a
    check the rendered protocol cannot describe."""
    assert set(steps.RELEASE_STEPS) == set(steps.DEFAULT_RELEASE_STEPS)
    assert steps.DEFAULT_RELEASE_STEPS == (
        'tree-clean', 'on-milestone-branch', 'changelog-unreleased-nonempty',
        'features-done', 'findings-resolved', 'version-sync', 'gate')
    for operation, names in steps.DEFAULT_STEPS.items():
        for name in names:
            assert name in steps.STEP_DOC, (operation, name)
    for name in ('milestone-done', 'changelog-retitle', 'push-branch', 'tag',
                 'readme-pins', 'pr-open', 'ci-green', 'prove-artifact'):
        assert name not in steps.RELEASE_STEPS, f'{name} survived D12'


# --- tree-clean ---------------------------------------------------------------
def test_tree_clean_names_every_modified_path_and_the_first_is_not_short_by_one():
    """Bites: `git status --porcelain` is COLUMNAR and a blanket strip ate
    column 0 of the first line — `SDLC.md` reported as `DLC.md`. Two files,
    compared exactly, because `'DLC.md' in 'SDLC.md'`."""
    with tree({'SDLC.md': 'one\n', 'zzz.md': 'one\n'}) as root:
        assert check('tree-clean', root).is_true
        for name in ('SDLC.md', 'zzz.md'):
            (root / name).write_text('two\n', encoding='utf-8')
        answer = check('tree-clean', root)
        assert not answer.is_true
        listed = answer.detail.split(': ', 1)[1].split(', ')
        assert listed == ['SDLC.md', 'zzz.md'], listed


# --- on-milestone-branch ------------------------------------------------------
def test_on_milestone_branch_reads_the_stamp_and_will_not_assume_without_one():
    """Bites: a release cut from whatever branch was checked out, or a
    missing `branch:` stamp read as 'the current one must be right'."""
    with tree() as root:
        assert check('on-milestone-branch', root).is_true
        subprocess.run(['git', 'switch', '-q', '-c', 'elsewhere'], cwd=root,
                       check=True)
        wrong = check('on-milestone-branch', root)
        assert wrong.truth is driver.Truth.FALSE
        assert 'elsewhere' in wrong.detail and f'milestone/{VERSION}' in wrong.detail
        stamped = root / MDIR / 'milestone.md'
        stamped.write_text(MILESTONE.replace(f'branch: milestone/{VERSION}\n', ''),
                           encoding='utf-8')
        assert check('on-milestone-branch', root).truth is \
            driver.Truth.UNVERIFIABLE


# --- the changelog ------------------------------------------------------------
@pytest.mark.parametrize('body,truth,why', [
    (None, driver.Truth.UNVERIFIABLE, 'is not at'),
    ('# Changelog\n\n## v0.1.0 — 2026-01-01\n\n- old\n', driver.Truth.FALSE,
     'no `## Unreleased`'),
    ('# Changelog\n\n## Unreleased\n\n## v0.1.0 — 2026-01-01\n\n- old\n',
     driver.Truth.FALSE, 'no bullet'),
    ('# Changelog\n\n## Unreleased\n\n- a\n\n## Unreleased\n\n- b\n',
     driver.Truth.FALSE, '2 `## Unreleased`'),
    ('# Changelog\n\n## Unreleased\n\n- a change\n', driver.Truth.TRUE,
     '1 bullet'),
])
def test_the_changelog_is_read_and_never_created_or_retitled(body, truth, why):
    """Bites: a tag over empty notes, an ambiguous pair of headings picked
    from, or a changelog the check created or rewrote."""
    files = {'CHANGELOG.md': body} if body is not None else {}
    with tree(files) as root:
        before = snapshot(root)
        answer = check('changelog-unreleased-nonempty', root)
        assert answer.truth is truth, answer
        assert why in answer.detail, answer.detail
        assert snapshot(root) == before


# --- version-sync -------------------------------------------------------------
PYPROJECT = '[project]\nname = "x"\nversion = "0.0.1"\n'


def test_version_sync_names_every_site_and_bumps_nothing():
    """Bites: the bump this check used to PERFORM. It reads both sites, names
    the one that is wrong with the value it holds, and leaves both bytes
    alone; with every site right it is true."""
    config = ('[release.version_files]\n'
              '"pyproject.toml" = \'^version = "(.*)"$\'\n'
              '"pkg/__init__.py" = "^__version__ = \'(.*)\'$"\n')
    files = {'pyproject.toml': PYPROJECT,
             'pkg/__init__.py': f"__version__ = '{VERSION}'\n"}
    with tree(files, config=config) as root:
        before = snapshot(root)
        answer = check('version-sync', root)
        assert answer.truth is driver.Truth.FALSE
        assert 'pyproject.toml says 0.0.1' in answer.detail, answer.detail
        assert snapshot(root) == before, 'version-sync wrote a version site'
        (root / 'pyproject.toml').write_text(
            PYPROJECT.replace('0.0.1', VERSION), encoding='utf-8')
        assert check('version-sync', root).is_true
    with tree(config=config) as root:
        assert check('version-sync', root).truth is driver.Truth.UNVERIFIABLE


# --- the pm predicates, asked of the verb --------------------------------------
def test_findings_resolved_and_features_done_ask_pm_ready_for():
    """Bites: a second reader of 'is every finding dispositioned'. The
    milestone has one feature pointing at a record with an open finding:
    `ready-for tag` says so by name; with no feature at all `ready-for
    milestone` reports the empty census rather than passing."""
    record = ('```\nverdict: SHIP-WITH-FIXES\n'
              '| id | severity | disposition |\n| W1 | MAJOR | open |\n```\n')
    feature = (f'---\nid: {VERSION}/alpha\nmilestone: "{VERSION}"\n'
               f'name: Alpha\nstatus: done\nreviewed: docs/reviews/alpha.md\n'
               f'phase: 1\n---\n\n# Alpha\n')
    with tree({f'{MDIR}/features/alpha/feature.md': feature,
               'docs/reviews/alpha.md': record}) as root:
        answer = check('findings-resolved', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert 'W1' in answer.detail or 'open' in answer.detail, answer.detail
    with tree() as root:
        answer = check('features-done', root)
        assert not answer.is_true, answer


# --- the gate: a configured command -------------------------------------------
def test_the_gate_fills_version_passes_the_shells_braces_through_and_names_the_code():
    """Bites: `{version}` handed to the shell unfilled (M4 — this repo's own
    command carried it for a milestone), the shell's own braces mangled, or
    a failing gate whose exit code is not on the line."""
    filled = '[release.commands]\ngate = "test {version} = 9.9.9 && echo v{version}"\n'
    with tree(config=filled) as root:
        answer = check('gate', root)
        assert answer.is_true, answer.detail
        assert '{version}' not in answer.detail and 'v9.9.9' in answer.detail
    theirs = ('[release.commands]\n'
              "gate = \"echo ${HOME} {} | awk '{print $1}' >/dev/null\"\n")
    with tree(config=theirs) as root:
        answer = check('gate', root)
        assert answer.is_true, answer.detail
        assert "{print $1}" in answer.detail and '${HOME}' in answer.detail
    with tree(config='[release.commands]\ngate = "exit 3"\n') as root:
        answer = check('gate', root)
        assert answer.truth is driver.Truth.FALSE
        assert 'exited 3' in answer.detail, answer.detail


def test_a_gates_output_is_bounded_and_a_timeout_is_false_not_a_hang():
    noisy = "awk 'BEGIN{for(i=0;i<200000;i++)printf \"x\"}'\nexit 1\n"
    with tree({'noisy.sh': noisy},
              config='[release.commands]\ngate = "sh noisy.sh"\n') as root:
        answer = check('gate', root)
        assert answer.truth is driver.Truth.FALSE
        assert len(answer.detail) < 1000, len(answer.detail)
    config = ('[release]\ncommand_timeout = 1\n\n'
              '[release.commands]\ngate = "sleep 30"\n')
    with tree(config=config) as root:
        answer = check('gate', root)
        assert answer.truth is driver.Truth.FALSE
        assert 'did not finish' in answer.detail, answer.detail


def test_a_callee_that_exits_2_is_UNVERIFIABLE_and_never_a_finding(monkeypatch):
    """D11. Bites: a callee's config error read as a plain no, and the belt
    then deciding over a question that was never asked."""
    monkeypatch.setattr(
        steps, '_own_cli',
        lambda c, *argv: (2, '[verify] feature must be a string, got 42',
                          argv))
    context = driver.Context(root=Path('.'), operation='story', version='x')
    answer = steps._own_verdict(context, 'verify', '--story', 'x')
    assert answer.truth is driver.Truth.UNVERIFIABLE, answer
    assert 'nothing was decided' in answer.detail and 'got 42' in answer.detail


# --- config -------------------------------------------------------------------
def test_no_devkit_toml_and_the_stock_list_declared_are_the_same_bytes():
    """Rule 5, the equivalence test."""
    declared = ('[release]\nsteps = [\n'
                + ''.join(f'  "{n}",\n' for n in steps.DEFAULT_RELEASE_STEPS)
                + ']\n')
    with tree():
        absent = driver.step_names('release')
    with tree(config=declared):
        explicit = driver.step_names('release')
    assert absent == explicit == steps.DEFAULT_RELEASE_STEPS


@pytest.mark.parametrize('config,expected', [
    ('[release]\nsteps = "tree-clean"\n', 'list of strings'),
    ('[release]\nsteps = []\n', 'remove the key'),
    ('[release]\nsteps = ["tree-clan"]\n', 'no check is registered'),
    ('[release]\nsteps = ["tree-clean", 3]\n', 'must be a string'),
    ('[release]\nsteps = ["gate;rm -rf /"]\n', 'not a step name'),
    ('[release]\nsteps = ["' + 'g' * 4096 + '"]\n', 'the limit is'),
    ('[release]\ncommands = "make x"\n', 'table of step'),
    ('[release.commands]\ngate = 3\n', 'one command string'),
    ('[release.commands]\ngate = "   "\n', 'is empty'),
    ('[release.commands]\ngate = "echo {verison}"\n', 'placeholder'),
    ('[release.commands]\n"version-sync" = "x"\n', 'reads the tree'),
    ('[release]\nsteps = ["tree-clean"]\n\n[release.commands]\ngate = "x"\n',
     'never runs'),
    ('[release.commands]\nnot-a-step = "x"\n', 'names no registered check'),
    ('[release]\ncommand_timeout = "soon"\n', 'positive integer'),
    ('release = "x"\n', ''),
])
def test_the_config_refusal_matrix_is_exit_2_and_runs_no_check(config, expected):
    """Bites: a typo narrowing the release list in silence — the check that
    vanishes is the one that mattered."""
    with tree(config=config):
        with pytest.raises(ConfigError) as err:
            driver.step_names('release')
        assert expected in str(err.value), str(err.value)


def test_duplicates_collapse_in_declaration_order_and_are_reported(capsys):
    config = '[release]\nsteps = ["gate", "tree-clean", "gate"]\n'
    with tree(config=config):
        assert driver.step_names('release') == ('gate', 'tree-clean')
    assert 'more than once' in capsys.readouterr().out


def test_an_after_belt_command_is_accepted_and_lands_on_the_next_line():
    """Bites: this repo's own `[release.commands] prove-artifact` — a key that
    names no check since D12 — refused at exit 2, or accepted and lost. It is
    the caller's command, and the after-list carries it filled in."""
    config = ('[release.commands]\n'
              'prove-artifact = "uvx --from x@v{version} x --version"\n')
    with tree(config=config):
        names = driver.step_names('release')
        commands = steps.commands_for('release', names)
        assert 'prove-artifact' in commands
        lines = steps.after_lines('release', commands, version=VERSION,
                                  branch='b', mainline='m')
        assert any(f'x@v{VERSION} x --version' in line for line in lines), lines
        assert not any('{' in line for line in lines), lines
