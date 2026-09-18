"""test_ship.py — a release with no milestone to close, in one verb.

The measured defect (2026-09-16): `release` over two merged PRs cost seven
minutes of invented grains, records and verdict words for one minute of work.
`ship` is that minute. The refusal matrix is proven first — every wrong input
writes nothing — and the happy path in a real git tree, because a branch, a
clean tree and a bump are questions only git and the filesystem answer.
"""
from __future__ import annotations

import contextlib
import io
import subprocess
import unittest
from pathlib import Path

from support.pm import git_tree

from agentic_sdlc import cli

MAKEFILE = 'check:\n\t@touch check.ran\n'
CONFIG = ('[verify]\nfeature = "make check"\nmilestone = "make check"\n'
          '[pm]\nversion_file = "VERSION"\nversion_pattern = \'^v=(.*)$\'\n')


def run_cli(root: Path, *argv: str) -> tuple[int, str]:
    """The ROOT router, both streams merged: `ship` is not a `pm` subcommand."""
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(argv))
    return code, out.getvalue()


def _git(root: Path, *args: str) -> None:
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@e', *args],
                   cwd=root, check=True, capture_output=True)


def _ready(root: Path) -> None:
    (root / 'Makefile').write_text(MAKEFILE, encoding='utf-8')
    (root / 'VERSION').write_text('v=0.1.0\n', encoding='utf-8')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'seed')
    _git(root, 'checkout', '-q', '-b', 'release/ship')


class TheRefusalMatrix(unittest.TestCase):
    def test_usage_faults_are_exit_2_and_write_nothing(self):
        with git_tree(config=CONFIG) as root:
            _ready(root)
            for argv, needle in (
                ((), 'both required'),
                (('0.2.0',), 'both required'),
                (('0.2.0', '--force', 'x'), 'no flags'),
                (('not a version', 'x'), 'not a version'),
                (('0.2.0', '   '), 'changelog line is empty'),
            ):
                code, out = run_cli(root, 'ship', *argv)
                self.assertEqual(2, code, (argv, out))
                self.assertIn(needle, out, (argv, out))
            self.assertEqual('v=0.1.0\n', (root / 'VERSION').read_text())
            self.assertFalse(list((root / 'pm/roadmap/milestones').glob('ms-release-*')))

    def test_a_mainline_a_dirty_tree_and_a_minted_grain_are_refused(self):
        with git_tree(config=CONFIG) as root:
            _ready(root)
            _git(root, 'checkout', '-q', 'main') if _has_branch(root, 'main') \
                else _git(root, 'branch', '-m', 'main')
            code, out = run_cli(root, 'ship', '0.2.0', 'x')
            self.assertEqual(1, code, out)
            self.assertIn('mainline', out)
            # #52: an agent-worktree branch, refused before the grain exists.
            _git(root, 'checkout', '-q', '-b', 'feat/ship2')
            code, out = run_cli(root, 'ship', '0.2.0', 'x')
            self.assertEqual(1, code, out)
            self.assertIn('agent-worktree prefix', out)
            self.assertIn('milestone/0.2.0-release', out)
            self.assertFalse(list((root / 'pm/roadmap/milestones').glob('ms-release-*')))
            _git(root, 'checkout', '-q', '-b', 'release/ship2')
            (root / 'src.txt').write_text('dirty\n', encoding='utf-8')
            code, out = run_cli(root, 'ship', '0.2.0', 'x')
            self.assertEqual(1, code, out)
            self.assertIn('modified path(s) outside', out)
            (root / 'src.txt').unlink()
            (root / 'pm/roadmap/milestones/ms-release-0-2-0.md').write_text(
                '---\nid: "ms-release-0-2-0"\nkind: milestone\nname: x\n'
                'status: done\n---\n', encoding='utf-8')
            code, out = run_cli(root, 'ship', '0.2.0', 'x')
            self.assertEqual(1, code, out)
            self.assertIn('already exists', out)
            self.assertEqual('v=0.1.0\n', (root / 'VERSION').read_text())


def _has_branch(root: Path, name: str) -> bool:
    done = subprocess.run(['git', 'branch', '--list', name], cwd=root,
                          capture_output=True, text=True)
    return name in done.stdout


class TheHappyPath(unittest.TestCase):
    def test_ship_mints_bumps_runs_the_rung_and_writes_done(self):
        with git_tree(config=CONFIG) as root:
            _ready(root)
            code, out = run_cli(root, 'ship', '0.2.0', '**Faster.** One verb.')
            self.assertEqual(0, code, out)
            self.assertIn('VERSION: 0.1.0 -> 0.2.0', out)
            self.assertEqual('v=0.2.0\n', (root / 'VERSION').read_text())
            self.assertTrue((root / 'check.ran').exists(), 'the feature rung ran')
            grain = (root / 'pm/roadmap/milestones/ms-release-0-2-0.md').read_text()
            self.assertIn('version: 0.2.0', grain)
            self.assertIn('status: done', grain)
            self.assertIn('changelog: **Faster.** One verb.', grain)
            self.assertIn('branch: release/ship', grain)
            plan = (root / 'pm/roadmap/releases.md').read_text()
            self.assertIn('ms-release-0-2-0', plan)
            self.assertIn('[ship] ok — 0.2.0 → done', out)
            self.assertIn('next: git push -u origin release/ship', out)
            # R5 reads the release the way it reads every other: the version
            # file equals the current entry in the plan.
            code, out = run_cli(root, 'check', 'pm')
            self.assertNotIn('(R5)', out, out)

    def test_a_red_rung_leaves_the_bump_and_says_what_remains(self):
        with git_tree(config=CONFIG) as root:
            _ready(root)
            (root / 'Makefile').write_text('check:\n\t@exit 3\n', encoding='utf-8')
            _git(root, 'commit', '-q', '-am', 'red')
            code, out = run_cli(root, 'ship', '0.2.0', 'x')
            self.assertEqual(1, code, out)
            self.assertIn('feature rung is red', out)
            self.assertEqual('v=0.2.0\n', (root / 'VERSION').read_text())
            grain = (root / 'pm/roadmap/milestones/ms-release-0-2-0.md').read_text()
            self.assertNotIn('status: done', grain)
            self.assertIn('milestone done ms-release-0-2-0', out)
