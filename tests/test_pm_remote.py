"""`remote.read` and the two surfaces that carry it — is the work anywhere else?

0.5.0 ran five hours and thirty-four commits with nothing pushed and no surface
looked. Every case here builds a REAL git tree with a real remote, because the
defect is a fact about REFS — including the packed ones — and a fixture that
stubs the layout would prove only that the stub agrees with itself.

The reader spawns nothing (hard rule 2); these cases spawn git to BUILD the
tree, which is why the module sits in the `shell` tier while the code under it
is safe to call from `census` on every write.

The three the proof budget named: the arrival line, the pressure clause, and
the belt's report. `has_a_remote` gets a fourth because *quiet, not broken* is
the half a consumer without a remote actually runs.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from support.pm import tree, write_config

from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo.pm import arrive, model, remote

AUTHOR = ('-c', 'user.email=t@example.invalid', '-c', 'user.name=t')
BRANCH = 'milestone/0.1-probe'


def _git(root: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=root, check=True,
                   capture_output=True)


def _commit(root: Path, message: str) -> None:
    _git(root, 'add', '-A')
    _git(root, *AUTHOR, 'commit', '-q', '--allow-empty', '-m', message)


@contextmanager
def git_tree(with_remote: bool = True, pushed: bool = False):
    """A checkout on `BRANCH`, cwd'd into, with a real bare remote.

    The remote is a local bare repo rather than a stub: `--not --remotes` reads
    remote-TRACKING refs, and only a real push creates one.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'work'
        root.mkdir()
        _git(root, 'init', '-q', '-b', BRANCH)
        (root / 'seed.txt').write_text('x', encoding='utf-8')
        _commit(root, 'first')
        if with_remote:
            bare = Path(tmp) / 'origin.git'
            _git(root, 'init', '-q', '--bare', str(bare))
            _git(root, 'remote', 'add', 'origin', str(bare))
            if pushed:
                _git(root, 'push', '-q', '-u', 'origin', BRANCH)
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


class ReadingTheRefs(unittest.TestCase):
    """What `read` answers, at each of the three states a branch can be in."""

    def test_an_unpushed_branch_is_neither_published_nor_in_sync(self):
        with git_tree(pushed=False) as root:
            state = remote.read(root)
            self.assertIsNotNone(state)
            self.assertEqual(state.branch, BRANCH)
            self.assertFalse(state.published)
            self.assertFalse(state.in_sync)
            self.assertTrue(state, 'work only on this disk must be truthy')

    def test_a_pushed_branch_is_published_and_in_sync(self):
        with git_tree(pushed=True) as root:
            state = remote.read(root)
            self.assertTrue(state.published)
            self.assertTrue(state.in_sync)
            self.assertFalse(state, 'in sync must be falsey — every surface '
                                    'below is silent on it')

    def test_a_pushed_branch_that_advanced_is_published_AND_not_in_sync(self):
        """The two facts are separate. A branch pushed once and since advanced
        is not 'on no remote', and saying so would teach an operator to ignore
        the line on the day it matters."""
        with git_tree(pushed=True) as root:
            _commit(root, 'second')
            state = remote.read(root)
            self.assertTrue(state.published)
            self.assertFalse(state.in_sync)

    def test_a_PACKED_remote_ref_still_counts_as_published(self):
        """THE BROKEN PROBE for the reader's one real trap. `git gc` moves a
        ref that has not moved out of `refs/` and into `packed-refs`, so a
        reader of the directory alone reports a pushed branch as unpushed —
        and the operator is told to push work that is already safe."""
        with git_tree(pushed=True) as root:
            _git(root, 'pack-refs', '--all')
            self.assertFalse((root / '.git/refs/remotes/origin' / BRANCH
                              ).is_file(), 'pack-refs did not pack the ref, '
                                           'so this case proves nothing')
            state = remote.read(root)
            self.assertTrue(state.published)
            self.assertTrue(state.in_sync)

    def test_a_tree_with_no_remote_is_quiet_not_broken(self):
        with git_tree(with_remote=False) as root:
            self.assertFalse(remote.has_a_remote(root))
            self.assertIsNone(remote.read(root))

    def test_a_detached_head_has_no_branch_to_be_behind(self):
        with git_tree(pushed=False) as root:
            _git(root, 'checkout', '-q', '--detach')
            self.assertIsNone(remote.read(root))

    def test_the_reader_SPAWNS_NOTHING(self):
        """Hard rule 2, and the reason this module was rewritten. The first
        draft shelled out for a commit count; `census` calls this on every `pm`
        write, and the suite's tier guard failed 235 cases in the `not shell`
        tier by nodeid. A grep is the cheapest thing that can fail here."""
        source = Path(remote.__file__).read_text(encoding='utf-8')
        for forbidden in ('subprocess', 'os.system', 'git_lines', 'popen'):
            self.assertNotIn(forbidden, source, forbidden)
        self.assertIn('git push -u origin', remote.push_command('b'))


class TheSurfacesCarryIt(unittest.TestCase):
    """The two derived lines, each silent at zero (rule 11)."""

    def _cfg(self, root: Path):
        write_config(root, '')
        (root / 'pm' / 'roadmap').mkdir(parents=True, exist_ok=True)
        return model.load()

    def test_the_census_clause_appears_only_when_something_is_unpushed(self):
        base = dict(open_count=1, oldest_id='x', oldest_seconds=5,
                    unanswered=0, no_record=0, record_pool=0, wip=0,
                    unreadable=0)
        silent = arrive.Census(**base)
        self.assertNotIn('disk', silent.line)
        loud = arrive.Census(**base, unpushed_branch=BRANCH)
        self.assertIn(f'{BRANCH} is on this disk only', loud.line)

    def test_the_arrival_line_fires_on_in_progress_and_names_the_command(self):
        with git_tree(pushed=False) as root:
            cfg = self._cfg(root)
            lines = arrive.remote_lines(cfg, 'milestone', 'building')
            self.assertEqual(len(lines), 2, lines)
            self.assertIn('is on no remote', lines[0])
            self.assertIn('the work is on this disk only', lines[0])
            self.assertIn(f'git push -u origin {BRANCH}', lines[1])

    def test_it_is_silent_at_todo_at_done_and_for_other_kinds(self):
        """The arrival that matters is into `in_progress`: that is when the
        work starts being worth something. Every other edge stays quiet."""
        with git_tree(pushed=False) as root:
            cfg = self._cfg(root)
            for kind, to in (('milestone', 'planning'), ('milestone', 'done'),
                             ('feature', 'building'), ('story', 'building')):
                with self.subTest(kind=kind, to=to):
                    self.assertEqual(arrive.remote_lines(cfg, kind, to), [])

    def test_a_published_branch_says_nothing_at_all(self):
        with git_tree(pushed=True) as root:
            cfg = self._cfg(root)
            self.assertEqual(
                arrive.remote_lines(cfg, 'milestone', 'building'), [])


if __name__ == '__main__':
    unittest.main()
