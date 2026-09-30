"""The coordinated land transaction validates first and resumes after a red gate."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agentic_sdlc.repo import land


COMMIT = 'a' * 40


class LandArguments(unittest.TestCase):
    def test_parse_requires_frozen_commit_owner_and_stories(self):
        request, defect = land.parse([
            'ft-f', '--branch', 'feat/lane', '--commit', COMMIT,
            '--story', 'st-a', '--review-record', 'docs/reviews/r.md',
            '--gate-owner', 'lead', '--actor', 'lead'])
        self.assertEqual('', defect)
        self.assertEqual(('st-a',), request.stories)
        self.assertEqual('lead', request.actor)
        complete = ['ft-f', '--branch', 'feat/lane', '--commit', 'deadbeef',
                    '--story', 'st-a', '--review-record', 'r.md',
                    '--gate-owner', 'lead', '--actor', 'lead']
        for argv, expected in ((['ft-f'], 'required argument'),
                               (complete, 'full'),
                               (['ft-f', '--story', 'st-a'], 'required')):
            parsed, problem = land.parse(argv)
            self.assertIsNone(parsed)
            self.assertIn(expected, problem)

    def test_non_owner_is_refused_before_git_or_merge(self):
        cfg = SimpleNamespace(agent_branch_prefix='feat/')
        feature = SimpleNamespace(kind='feature', gid='ft-f')
        request = land.Request('ft-f', 'feat/lane', COMMIT, ('st-a',),
                               'docs/reviews/r.md', 'lead', 'builder')
        with (patch.object(land, 'repo_root', return_value=Path('.')),
              patch.object(land.vocabulary, 'load', return_value=cfg),
              patch.object(land.inventory, 'grain_index', return_value={'ft-f': feature}),
              patch.object(land, '_git') as git):
            context, defect = land._preflight(request)
        self.assertIsNone(context)
        self.assertIn('final-gate owner is', defect)
        git.assert_not_called()

    def test_completed_journal_replay_needs_no_worktree_or_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / '.git' / 'agent-land' / f'{COMMIT}.json'
            journal.parent.mkdir(parents=True)
            cfg = SimpleNamespace(agent_branch_prefix='feat/')
            feature = SimpleNamespace(kind='feature', gid='ft-f')
            story = SimpleNamespace(kind='story', gid='st-a', binding='ft-f')
            milestone = SimpleNamespace(gid='ms-1', field=lambda key: 'milestone/1')
            request = land.Request('ft-f', 'feat/lane', COMMIT, ('st-a',),
                                   'docs/reviews/removed.md', 'lead', 'lead')
            context = land.Context(root, cfg, feature, milestone, (story,), None,
                                   'lane', 'milestone/1', '', journal)
            journal.write_text(json.dumps({
                'version': 1, 'identity': land._identity(request, context),
                'phase': 'complete', 'before': 'b' * 40,
                'gate_ref': 'b' * 40,
                'gate_command': ['make', 'precommit', f'REF={"b" * 40}'],
                'gate_head': 'c' * 40}),
                encoding='utf-8')
            def git_result(_root, *args, allow_failure=False):
                if args == ('rev-parse', '--git-common-dir'):
                    return '.git'
                if args[0] == 'cat-file' or args[0] == 'merge-base':
                    return '0'
                return ''
            with (patch.object(land, 'repo_root', return_value=root),
                  patch.object(land.vocabulary, 'load', return_value=cfg),
                  patch.object(land.inventory, 'grain_index',
                               return_value={'ft-f': feature, 'st-a': story,
                                             'ms-1': milestone}),
                  patch.object(land.inventory, 'milestone_of',
                               return_value='ms-1'),
                  patch.object(land, '_git', side_effect=git_result) as git):
                resolved, defect = land._preflight(request)
            self.assertEqual('', defect)
            self.assertIsNone(resolved.worktree)
            self.assertGreater(git.call_count, 1)

    def test_completed_journal_rejects_tampered_gate_command_before_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / 'land.json'
            cfg = SimpleNamespace()
            feature = SimpleNamespace(gid='ft-f')
            milestone = SimpleNamespace(gid='ms-1')
            request = land.Request('ft-f', 'feat/lane', COMMIT, ('st-a',),
                                   'r.md', 'lead', 'lead')
            context = land.Context(root, cfg, feature, milestone, (), None,
                                   'lane', 'milestone/1', '', journal)
            body = {'version': 1, 'identity': land._identity(request, context),
                    'phase': 'complete', 'before': 'b' * 40,
                    'gate_ref': 'b' * 40,
                    'gate_command': ['make', 'precommit', 'REF=wrong'],
                    'gate_head': 'c' * 40}
            journal.write_text(json.dumps(body), encoding='utf-8')
            with patch.object(land, '_git', return_value='0'):
                self.assertIn('gate command', land._journal_defect(request, context))

    def test_completed_journal_rejects_missing_required_field(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / 'land.json'
            cfg = SimpleNamespace()
            feature = SimpleNamespace(gid='ft-f')
            milestone = SimpleNamespace(gid='ms-1')
            request = land.Request('ft-f', 'feat/lane', COMMIT, ('st-a',),
                                   'r.md', 'lead', 'lead')
            context = land.Context(root, cfg, feature, milestone, (), None,
                                   'lane', 'milestone/1', '', journal)
            journal.write_text(json.dumps({
                'version': 1, 'identity': land._identity(request, context),
                'phase': 'complete', 'before': 'b' * 40,
                'gate_ref': 'b' * 40,
                'gate_command': ['make', 'precommit', f'REF={"b" * 40}']}),
                encoding='utf-8')
            with patch.object(land, '_git', return_value='0'):
                self.assertIn('schema', land._journal_defect(request, context))

    def test_transaction_lock_is_nonblocking(self):
        with tempfile.TemporaryDirectory() as temp:
            common = Path(temp)
            with land._transaction_lock(common):
                lock_path = common / 'agent-land' / 'transaction.lock'
                self.assertTrue(lock_path.is_file())
                first_inode = lock_path.stat().st_ino
                with self.assertRaisesRegex(OSError, 'another land transaction'):
                    land._transaction_lock(common)
                self.assertEqual(first_inode, lock_path.stat().st_ino)
            unsafe_common = common / 'unsafe'
            unsafe_dir = unsafe_common / 'agent-land'
            unsafe_dir.mkdir(parents=True)
            target = common / 'target-lock'
            target.touch()
            (unsafe_dir / 'transaction.lock').symlink_to(target)
            with self.assertRaisesRegex(OSError, 'lock path is unsafe'):
                land._transaction_lock(unsafe_common)

    def test_marker_reads_immutable_base_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / '.agent-scope'
            marker.write_text('branch=feat/x\nbase=milestone/1\n'
                              f'base_sha={COMMIT}\n', encoding='utf-8')
            self.assertEqual(COMMIT, land._marker(marker)['base_sha'])

    def test_branch_marker_base_sha_must_ancestor_both_trees(self):
        root = Path('.')
        base = 'b' * 40
        with patch.object(land, '_git', side_effect=['0', '1']):
            defect = land._base_ancestry_defect(
                root, base, COMMIT, 'c' * 40, 'feat/lane', 'milestone/1')
        self.assertIn('not an ancestor of integration branch', defect)
        with patch.object(land, '_git', side_effect=['0', '0', '1']):
            defect = land._base_ancestry_defect(
                root, base, COMMIT, 'c' * 40, 'feat/lane', 'milestone/1')
        self.assertIn('does not descend from its immutable base', defect)


class LandResume(unittest.TestCase):
    def test_gate_failure_resumes_and_cleanup_runs_after_belts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lane = root / 'lane'
            lane.mkdir()
            request = land.Request('ft-f', 'feat/lane', COMMIT, ('st-a',),
                                   'docs/reviews/r.md', 'lead', 'lead')
            cfg = SimpleNamespace(roadmap_dir='pm/roadmap')
            feature = SimpleNamespace(gid='ft-f')
            milestone = SimpleNamespace(gid='ms-1')
            context = land.Context(root, cfg, feature, milestone, (), lane,
                                   'lane', 'milestone/1', 'b' * 40,
                                   root / '.git' / 'agent-land' / f'{COMMIT}.json')
            calls: list[tuple[str, ...]] = []
            gate_attempts = 0

            def fake_spawn(argv, **kwargs):
                nonlocal gate_attempts
                calls.append(tuple(argv))
                if argv[:2] == ['make', 'precommit']:
                    gate_attempts += 1
                    return SimpleNamespace(returncode=1 if gate_attempts == 1 else 0,
                                           stdout='', stderr='')
                return SimpleNamespace(returncode=0, stdout='c' * 40, stderr='')

            with patch.object(land.spawn, 'run', side_effect=fake_spawn), \
                    patch('agentic_sdlc.repo.conveyor.driver.main', return_value=0) as belt:
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                    first = land._run(request, context)
                self.assertEqual(land.EXIT_REFUSED, first)
                saved = json.loads(context.journal.read_text(encoding='utf-8'))
                self.assertEqual('merged', saved['phase'])
                self.assertEqual('b' * 40, saved['before'])
                self.assertTrue(lane.exists())

                second = land._run(request, context)
                self.assertEqual(land.EXIT_OK, second)
                self.assertEqual('complete', json.loads(
                    context.journal.read_text(encoding='utf-8'))['phase'])
                saved = json.loads(context.journal.read_text(encoding='utf-8'))
                self.assertEqual('b' * 40, saved['before'])
                self.assertEqual('b' * 40, saved['gate_ref'])
                self.assertEqual(['make', 'precommit', f'REF={"b" * 40}'],
                                 saved['gate_command'])
                self.assertEqual('c' * 40, saved['gate_head'])
                self.assertEqual(2, gate_attempts)
                self.assertEqual(2, belt.call_count)
                self.assertEqual(('bash', 'tools/dev/agent-worktree.sh', 'done', 'lane'),
                                 calls[-1])
                count = len(calls)
                self.assertEqual(land.EXIT_OK, land._run(request, context))
                self.assertEqual(count, len(calls), 'a completed retry is a no-op')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
