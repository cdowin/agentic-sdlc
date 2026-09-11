"""The suite cannot move the repository it gates — and says so if it does.

bg-the-suite-run-in-a-worktree-mutates-the-host-repo: `git bisect run`, in a
linked worktree, exports `GIT_DIR=.git/worktrees/<name>`, and under it every
`git init -q <tmp>` in this suite flipped the COMMON config to `bare = true`
and every scratch commit landed on the worktree's HEAD. The guard and the
ratchet live in `tests/conftest.py`; these cases run a COPY of it over a
scratch suite that sits inside a throwaway repo, so the host a failure moves is
the throwaway, never this checkout.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import conftest

TESTS = Path(__file__).resolve().parent
IDENTITY = ('-c', 'user.email=t@example.invalid', '-c', 'user.name=t')
BRANCH = 'host-branch'
INI = '[pytest]\nmarkers =\n    shell: derived by conftest.py\n'

# The exact shape of the stray commit `2dc6514 scratch`, and a temp tree that
# never ran `git init` asking where its repository is.
UNDER_AN_INHERITED_GIT_DIR = '''\
import subprocess
import tempfile
from pathlib import Path


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)


def test_a_scratch_repo_is_its_own():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'f').write_text('x', encoding='utf-8')
        git(tmp, 'init', '-q')
        git(tmp, 'add', '-A')
        git(tmp, '-c', 'user.email=t@example.invalid', '-c', 'user.name=t',
            'commit', '-qm', 'scratch')
        assert (Path(tmp) / '.git').is_dir(), 'git init went somewhere else'


def test_a_tree_that_is_not_a_repo_finds_none_above_it():
    with tempfile.TemporaryDirectory() as tmp:
        done = git(tmp, 'rev-parse', '--show-toplevel')
        assert done.returncode != 0, f'walked up into {done.stdout.strip()}'
'''

# A test that moves every field the ratchet holds, and PASSES doing it.
MOVES_ITS_HOST = '''\
import subprocess
from pathlib import Path

HOST = Path(__file__).resolve().parent.parent


def test_moves_the_host():
    for argv in (['git', '-c', 'user.email=t@example.invalid', '-c',
                  'user.name=t', 'commit', '-q', '--allow-empty', '-m', 'planted'],
                 ['git', 'checkout', '-q', '--detach'],
                 ['git', 'config', 'core.bare', 'true']):
        subprocess.run(argv, cwd=HOST, check=True, capture_output=True)
'''


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


def _throwaway(tmp: Path) -> tuple[Path, Path]:
    """(main checkout, a linked worktree on `BRANCH`) — the host under test."""
    main = tmp / 'main'
    main.mkdir()
    _git(main, 'init', '-q', '-b', 'trunk')
    (main / 'seed').write_text('x', encoding='utf-8')
    _git(main, 'add', '-A')
    _git(main, *IDENTITY, 'commit', '-qm', 'seed')
    linked = tmp / 'linked'
    _git(main, 'worktree', 'add', '-q', '-b', BRANCH, str(linked))
    return main, linked


def _suite(host: Path, module: str) -> Path:
    """A scratch suite at `<host>/tests`, under a copy of the real conftest."""
    suite = host / 'tests'
    (suite / 'support').mkdir(parents=True)
    (suite / 'support' / '__init__.py').write_text('', encoding='utf-8')
    shutil.copy2(TESTS / 'conftest.py', suite / 'conftest.py')
    (suite / 'pytest.ini').write_text(INI, encoding='utf-8')
    (suite / 'test_scratch.py').write_text(module, encoding='utf-8')
    return suite


def _run(suite: Path, **env: str) -> tuple[int, str]:
    """Under xdist, as `make test` runs: the scrub must reach the workers, and
    the ratchet must hold on the controller after they are done."""
    child = {k: v for k, v in os.environ.items() if k != conftest.TIER_ENV}
    child.update(env)
    done = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--no-header',
                           '-p', 'no:cacheprovider', '-n', '2', str(suite)],
                          cwd=suite.parent, env=child,
                          capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


class TheHostIsOutOfReach(unittest.TestCase):

    def test_an_inherited_git_dir_reaches_nothing(self):
        """What `git bisect run` hands its child, and a TMPDIR inside the host
        so a missing `git init` has a repository above it to find."""
        with tempfile.TemporaryDirectory() as tmp:
            main, linked = _throwaway(Path(tmp).resolve())
            suite = _suite(linked, UNDER_AN_INHERITED_GIT_DIR)
            (linked / 'tmp').mkdir()
            before = conftest.host_state(linked)
            code, out = _run(suite, GIT_DIR=str(main / '.git/worktrees/linked'),
                             GIT_PREFIX='', TMPDIR=str(linked / 'tmp'))
            self.assertEqual(conftest.host_moved(before, conftest.host_state(linked)),
                             [], out)
            self.assertEqual(code, 0, out)
            self.assertIn('2 passed', out)

    def test_a_session_that_moves_its_host_fails_naming_each_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, linked = _throwaway(Path(tmp).resolve())
            code, out = _run(_suite(linked, MOVES_ITS_HOST))
            self.assertIn('1 passed', out)
            self.assertEqual(code, 1, f'a passing session that moved its host exited {code}\n{out}')
            for field in ('THE SUITE MOVED ITS HOST REPOSITORY', 'core.bare: ',
                          'HEAD: ref: refs/heads/host-branch -> ',
                          f'refs/heads/{BRANCH}: '):
                self.assertIn(field, out)

    def test_the_scrub_clears_every_variable_git_calls_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run(['git', 'rev-parse', '--local-env-vars'], cwd=tmp,
                                  check=True, capture_output=True, text=True)
        named = done.stdout.split()
        self.assertGreater(len(named), 5, done.stdout)
        self.assertEqual(sorted(set(named) - set(conftest.GIT_LOCAL_ENV)), [],
                         'git names these repository-local; the session inherits them')
