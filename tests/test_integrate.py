"""`integrate`: a batch of lanes merged in one worktree, proved once, closed.

Integration tier: every case builds a real origin and clone and runs git.
The verb runs in-process through the router, in a clone whose milestone
branch is checked out, against lanes pushed to a bare origin.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
from pathlib import Path

import pytest

from agentic_sdlc import cli
from agentic_sdlc.core.project import load_config, repo_root
from support.pm import commit, git, with_flow, write

BASE = 'milestone/x'
MAKEFILE = 'ok:\n\t@true\nproof:\n\t@if grep -l BROKEN *.txt; then exit 1; fi\n'
INTEGRATE = '[integrate]\nper_merge = ["ok"]\nproof = ["proof"]\n'


def _status(root: Path, sid: str) -> str:
    text = (root / 'pm' / 'roadmap' / 'stories' / f'{sid}.md').read_text()
    return next(ln.split(': ', 1)[1] for ln in text.splitlines()
                if ln.startswith('status: '))


def _lane(root: Path, slug: str, files: dict[str, str]) -> None:
    """Push `feat/<slug>` holding `files`, cut from the milestone branch."""
    git(root, 'switch', '-q', '-c', f'feat/{slug}', BASE)
    for name, text in files.items():
        (root / name).write_text(text)
    commit(root, f'lane {slug}')
    git(root, 'push', '-q', 'origin', f'feat/{slug}')
    git(root, 'switch', '-q', BASE)


@contextlib.contextmanager
def _repo(config: str = INTEGRATE, stories=('a', 'b')):
    with tempfile.TemporaryDirectory() as tmp:
        origin, root = Path(tmp) / 'origin.git', Path(tmp) / 'repo'
        git(Path(tmp), 'init', '-q', '--bare', str(origin))
        git(Path(tmp), 'init', '-q', '-b', BASE, str(root))
        git(root, 'remote', 'add', 'origin', str(origin))
        (root / 'devkit.toml').write_text(with_flow(config))
        (root / 'Makefile').write_text(MAKEFILE)
        (root / '.gitignore').write_text('pm/roadmap/ledger.local.jsonl\n')
        pools = root / 'pm' / 'roadmap'
        write(pools / 'milestones' / 'ms-x.md',
              {'id': 'ms-x', 'kind': 'milestone', 'name': 'X',
               'status': 'building', 'branch': BASE})
        write(pools / 'features' / 'ft-x.md',
              {'id': 'ft-x', 'kind': 'feature', 'milestone': 'ms-x',
               'name': 'F', 'status': 'building'})
        for slug in stories:
            write(pools / 'stories' / f'st-{slug}.md',
                  {'id': f'st-{slug}', 'kind': 'story', 'feature': 'ft-x',
                   'milestone': 'ms-x', 'name': slug, 'status': 'building'})
        commit(root)
        git(root, 'push', '-q', '-u', 'origin', BASE)
        previous = Path.cwd()
        os.chdir(root)
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


@pytest.fixture(autouse=True)
def _identity(monkeypatch):
    """The verb's own merges and commit need an author; the env, not 4 spawns."""
    for role in ('AUTHOR', 'COMMITTER'):
        monkeypatch.setenv(f'GIT_{role}_NAME', 'integrate tests')
        monkeypatch.setenv(f'GIT_{role}_EMAIL', 'it@tests.invalid')


def _integrate(*argv: str) -> tuple[int, str]:
    repo_root.cache_clear()
    load_config.cache_clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(['integrate', *argv])
    return code, out.getvalue()


def _refs(root: Path, pattern: str) -> str:
    return git(root, 'for-each-ref', '--format=%(refname)', pattern)


@pytest.mark.parametrize('rerun, code_after, said_after', [
    (('a', 'b'), 0, 'nothing to integrate'),
    # A lane that never existed: no branch, no done story. Exit 0 here would
    # be a green line for nothing (rule 4).
    (('a', 'typo'), 1, 'no origin/feat/typo and st-typo is not done'),
])
def test_green_batch_merges_closes_and_removes_the_lanes_then_reruns(
        rerun, code_after, said_after):
    with _repo() as root:
        _lane(root, 'a', {'a.txt': 'a\n'})
        _lane(root, 'b', {'b.txt': 'b\n'})
        lane_a = root.parent / 'lane-a'
        git(root, 'worktree', 'add', '-q', str(lane_a), 'feat/a')

        code, out = _integrate('a', 'b')

        assert code == 0, out
        assert (root / 'a.txt').is_file() and (root / 'b.txt').is_file(), out
        assert (_status(root, 'st-a'), _status(root, 'st-b')) == ('done', 'done')
        assert git(root, 'status', '--porcelain', '--untracked-files=no') == ''
        assert _refs(root, 'refs/heads/feat/') == ''
        assert _refs(root, 'refs/heads/integrate/') == ''
        assert git(root, 'ls-remote', 'origin', 'refs/heads/feat/*') == ''
        assert not lane_a.exists()
        assert 'proof: make proof — PASS' in out
        assert out.rstrip().endswith(f'next: git push origin {BASE}')

        again, said = _integrate(*rerun)
        assert again == code_after and said_after in said, said
        assert 'a: no origin/feat/a and st-a is done — already integrated' in said


def test_conflict_stops_closes_nothing_and_a_rerun_after_the_fix_resumes():
    with _repo(stories=('a', 'c')) as root:
        _lane(root, 'a', {'a.txt': 'from a\n'})
        _lane(root, 'c', {'a.txt': 'from c\n'})
        before = git(root, 'rev-parse', BASE)

        code, out = _integrate('a', 'c', '--batch', 'one')

        assert code == 1 and 'lane c' in out, out
        assert git(root, 'rev-parse', BASE) == before
        assert _status(root, 'st-a') == 'building'
        assert 'refs/heads/integrate/one' in _refs(root, 'refs/heads/integrate/')

        git(root, 'switch', '-q', 'feat/c')
        git(root, 'rm', '-q', 'a.txt')
        (root / 'c.txt').write_text('c\n')
        commit(root, 'lane c, rebuilt')
        git(root, 'push', '-q', 'origin', 'feat/c')
        git(root, 'switch', '-q', BASE)

        code, out = _integrate('a', 'c', '--batch', 'one')

        assert code == 0, out
        assert 'a: already in the batch' in out
        assert (root / 'a.txt').read_text() == 'from a\n'
        assert (_status(root, 'st-a'), _status(root, 'st-c')) == ('done', 'done')


def test_a_merge_git_refuses_without_a_conflict_names_gits_cause(monkeypatch):
    """The 2.1.0 CI runner had no identity: git refused the merge commit, and
    the stop line called it a conflict nobody could resolve (rule 4)."""
    with _repo() as root:
        _lane(root, 'a', {'a.txt': 'a\n'})
        for role in ('AUTHOR', 'COMMITTER'):
            monkeypatch.setenv(f'GIT_{role}_NAME', '')

        code, out = _integrate('a')

        assert code == 1, out
        assert 'conflicts with the batch' not in out, out
        assert 'git merge origin/feat/a failed and nothing conflicts' in out
        assert 'empty ident name' in out, out


def test_red_proof_names_the_lane_whose_file_failed_and_closes_nothing():
    with _repo() as root:
        _lane(root, 'a', {'a.txt': 'fine\n'})
        _lane(root, 'b', {'b.txt': 'BROKEN\n'})
        before = git(root, 'rev-parse', BASE)

        code, out = _integrate('a', 'b')

        assert code == 1, out
        assert 'proof: make proof — FAIL' in out
        assert 'lanes to look at: b.' in out, out
        assert git(root, 'rev-parse', BASE) == before
        assert (_status(root, 'st-a'), _status(root, 'st-b')) == ('building', 'building')
        assert git(root, 'ls-remote', 'origin', 'refs/heads/feat/*').count('feat/') == 2


@pytest.mark.parametrize('config', ['', '[integrate]\nper_merge = []\n'])
def test_an_undeclared_integrate_section_or_key_is_exit_2_before_any_git(
        config, tmp_path, monkeypatch):
    (tmp_path / '.git').mkdir()
    (tmp_path / 'devkit.toml').write_text(with_flow(config))
    monkeypatch.chdir(tmp_path)
    code, out = _integrate('a')
    assert code == 2 and '[integrate]' in out, out
    assert sorted(p.name for p in tmp_path.iterdir()) == ['.git', 'devkit.toml']
