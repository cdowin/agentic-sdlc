"""`agentic-sdlc preflight` — what a session can do, said before the first dispatch.

Issue #40: a host launched every session with `SendMessage` disallowed, nobody
knew until a call failed, and every stopped builder was re-dispatched cold. The
load-bearing property is that each row is READ off the tree the session stands
in — the settings files, the hook corpus, the PM tree — and a fact that is not
readable as text says `unknown` rather than a guess (rule 4's first sin, a
report that looks like knowledge and is not).

Unit tier: every tree is built on disk and nothing is started, which is also
the verb's own contract (rule 2) — a spawn here is refused by nodeid.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from support.pm import tree

from agentic_sdlc import cli
from agentic_sdlc.core.project import load_config
from agentic_sdlc.repo import preflight
from agentic_sdlc.repo.checks import hooks

SETTINGS, LOCAL = hooks.SETTINGS_FILES


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _settings(root: Path, rel: str, **document: object) -> None:
    _write(root, rel, json.dumps(document))


def _hooked(command: str) -> dict:
    return {'SessionStart': [{'hooks': [{'type': 'command',
                                         'command': command}]}]}


class ThePreflightReadsWhatTheSessionStandsIn(unittest.TestCase):

    def test_each_capability_is_read_off_the_files_and_unread_is_unknown(self):
        """The three readers over planted trees: every value in each row's
        vocabulary, and the missing thing NAMED in the meaning (rule 11)."""
        deny = {'permissions': {'deny': ['SendMessage']}}
        allow = {'permissions': {'allow': ['SendMessage(*)', 'Bash']}}
        resume = (
            # A deny in EITHER file wins, the local override included.
            ({LOCAL: deny, SETTINGS: allow}, 'denied', LOCAL),
            ({SETTINGS: allow}, 'allowed', 'launch flag'),
            # Neither names it: a launch flag is not text, so never `allowed`.
            ({SETTINGS: {'permissions': {'allow': ['SendMessageX']}}},
             preflight.UNKNOWN, 'launch flag'),
            ({}, preflight.UNKNOWN, 'launch flag'),
        )
        for files, value, named in resume:
            with self.subTest(resume=value, files=sorted(files)), \
                    tempfile.TemporaryDirectory() as tmp:
                for rel, document in files.items():
                    _settings(Path(tmp), rel, **document)
                got, meaning = preflight.resume(Path(tmp))
                self.assertEqual((got, named in meaning), (value, True),
                                 meaning)
                if got != 'allowed':
                    self.assertIn(preflight.CHANNEL, meaning)
        with self.subTest(resume='unreadable'), \
                tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp), SETTINGS, 'not json {{{')
            got, meaning = preflight.resume(Path(tmp))
            self.assertEqual(got, preflight.UNKNOWN)
            self.assertIn(f'{SETTINGS} could not be read', meaning)

        with self.subTest(hooks='no corpus'), \
                tempfile.TemporaryDirectory() as tmp:
            got, meaning = preflight.wiring(Path(tmp))
            self.assertEqual(got, preflight.NOT_WIRED)
            self.assertIn(hooks.INSTALL_COMMAND, meaning)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('cc-a.sh', 'cc-b.sh', 'pre-push'):
                _write(root, f'{hooks.HOOKS_DIR}/{name}', '#!/bin/sh\n')
            _settings(root, SETTINGS, hooks=_hooked('bash tools/hooks/cc-a.sh'))
            with self.subTest(hooks='one of two registered'):
                got, meaning = preflight.wiring(root)
                self.assertEqual(got, preflight.NOT_WIRED)
                self.assertIn('cc-b.sh registered in no settings file',
                              meaning)
                self.assertNotIn('cc-a.sh', meaning)
            # The absolute block `install-hooks` prints lands in the local file.
            _settings(root, LOCAL,
                      hooks=_hooked(f"bash '{root}/tools/hooks/cc-b.sh'"))
            with self.subTest(hooks='both registered, across both files'):
                got, meaning = preflight.wiring(root)
                self.assertEqual(got, preflight.WIRED, meaning)
                self.assertIn('all 2', meaning)

    def test_the_verb_prints_four_rows_in_its_columns_and_counts_the_tree(self):
        """Through the router, over a real PM tree: the rows are the columns
        `--help` names, the attribution count is the couriers' fallback's own
        snapshot, and an argument is exit 2 (rule 6)."""
        said = ' '.join(preflight.USAGE.split())
        self.assertIn(f'columns IN ORDER: {" ".join(preflight.COLUMNS)}', said)
        for statuses, count, named in ((('ready',), '0', 'no story'),
                                       (('building',), '1', '0.1/alpha/s0'),
                                       (('building', 'building'), '2',
                                        'picks none')):
            with self.subTest(stories=statuses), tree(story_statuses=statuses):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), \
                        contextlib.redirect_stderr(err):
                    code = cli.main([preflight.VERB])
                self.assertEqual(code, 0, err.getvalue())
                rows = [line.split('\t') for line in
                        out.getvalue().splitlines()]
                self.assertEqual(
                    [row[0] for row in rows],
                    ['subagent-resume', 'hooks', 'attribution',
                     'subagent-channel'])
                self.assertEqual({len(row) for row in rows},
                                 {len(preflight.COLUMNS)})
                self.assertEqual(rows[2][1], count)
                self.assertIn(named, rows[2][2])
        # No flow declared: no state is in_progress, and 0 would be a lie.
        with self.subTest(stories='no [pm.states.*]'), tree() as root:
            (root / 'devkit.toml').write_text('', encoding='utf-8')
            load_config.cache_clear()
            value, meaning = preflight.attribution(
                *preflight._stories_in_progress())
            self.assertEqual(value, preflight.UNKNOWN)
            self.assertIn('[pm.states.*]', meaning)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(cli.main([preflight.VERB, '--grain']), 2)
        self.assertIn('--grain', err.getvalue())


if __name__ == '__main__':
    unittest.main()
