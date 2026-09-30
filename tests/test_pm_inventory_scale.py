"""The tree is walked once per verb, at 2,000 grains (#100).

`pm validate` looked each id up OUTSIDE a read scope, so every lookup rebuilt
the grain index: four pool walks and a sort per lookup, and the verb was
quadratic in the tree. A consumer's 840-grain tree took 61 s. The fix is one
`inventory.reading_tree()` per verb at the entry points; this holds it.

A PROCESS per verb, because the claim is *one walk per pool per process* and a
consumer pays the interpreter start too. That is also what puts the case in the
integration tier: at 2,000 grains it is past the unit tier's 2 s.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

from support.pm import tree, write

from agentic_sdlc.repo.pm import inventory

SRC = Path(__file__).resolve().parent.parent / 'src'
WALKS = 'WALKS '
# The real router, in a child, with `core.walk`'s count as the last line of
# stderr — the count is from the same process as the wall time.
CHILD = (
    'import json, sys\n'
    'from agentic_sdlc import cli\n'
    'from agentic_sdlc.core import walk\n'
    'code = cli.main(sys.argv[1:])\n'
    f'print({WALKS!r} + json.dumps(walk.walks()), file=sys.stderr)\n'
    'sys.exit(code)\n')


def synthetic_tree(pools: Path) -> int:
    """50 milestones with a decisions doc each, 450 features chained by
    `depends_on`, 1,200 stories and 300 bugs, every one sequenced in its
    parent's `order:` — 2,000 grains, pooled. Replaces `tree()`'s own three.
    The count it wrote."""
    for stale in ('milestones/0.1.md', 'features/alpha.md', 'stories/s0.md'):
        (pools / stale).unlink()

    def order(ids: list[str]) -> str:
        return ''.join(f'\n  - "{i}"' for i in ids)

    n = 0
    for m in range(50):
        mid = f'ms-m{m}'
        fids = [f'ft-m{m}-f{f}' for f in range(9)]
        bids = [f'bg-m{m}-b{b}' for b in range(6)]
        write(pools / 'milestones' / f'{mid}.md',
              {'id': f'"{mid}"', 'kind': 'milestone', 'name': f'M{m}',
               'status': 'done', 'depends_on': '[]', 'branch': '',
               'version': f'0.{m}.0', 'order': order(fids + bids)},
              f'# M{m}\n\n## Goal\n\nx')
        (pools / 'milestones' / f'{mid}-decisions.md').write_text(
            f'# {mid} decisions\n\n## D1 x\n\ny\n', encoding='utf-8')
        n += 1
        for f, fid in enumerate(fids):
            sids = [f'st-m{m}-f{f}-s{s}'
                    for s in range(2 if (m * 9 + f) % 3 == 0 else 3)]
            write(pools / 'features' / f'{fid}.md',
                  {'id': fid, 'kind': 'feature', 'milestone': f'"{mid}"',
                   'name': fid, 'status': 'done', 'reviewed': '',
                   'depends_on': f'["{fids[f - 1]}"]' if f else '[]',
                   'consumed_by': '[]', 'changelog': 'none',
                   'order': order(sids)})
            n += 1
            for sid in sids:
                write(pools / 'stories' / f'{sid}.md',
                      {'id': sid, 'kind': 'story', 'feature': fid,
                       'milestone': f'"{mid}"', 'name': sid, 'status': 'done',
                       'owner': '', 'depends_on': '[]'},
                      f'# {sid}\n\n## Acceptance criteria\n\n- x')
                n += 1
        for bid in bids:
            write(pools / 'bugs' / f'{bid}.md',
                  {'id': bid, 'kind': 'bug', 'milestone': f'"{mid}"',
                   'name': bid, 'status': 'closed', 'caused_by': '',
                   'changelog': 'none'})
            n += 1
    return n


def run(root: Path, *argv: str) -> tuple[int, str, dict[str, int], float]:
    """(exit, output, {root: walks}, wall seconds) for one verb in a child."""
    started = time.perf_counter()
    done = subprocess.run([sys.executable, '-c', CHILD, *argv], cwd=root,
                          capture_output=True, text=True,
                          env={**os.environ, 'PYTHONPATH': str(SRC)})
    took = time.perf_counter() - started
    lines = done.stderr.splitlines()
    walked = (json.loads(lines[-1][len(WALKS):])
              if lines and lines[-1].startswith(WALKS) else {})
    return done.returncode, done.stdout + done.stderr, walked, took


class TheTreeIsWalkedOnce(unittest.TestCase):

    def test_a_2000_grain_tree_is_walked_once_per_pool_per_verb(self):
        """Before, on this tree: `pm validate` walked 4,024 times, made 466M
        calls and took 80 s. After, each verb in its own process on an Apple
        laptop at load 34 (an idle one was not available), interpreter start
        included, best of 3: `pm validate` 0.4 s, `check pm` 1.1 s. The budgets
        are about 5x. The walk COUNT is the guard, since wall time is noisy;
        the budget catches a regression the count misses."""
        with tree() as root:
            self.assertEqual(synthetic_tree(root / 'pm' / 'roadmap'), 2000)
            for argv, budget in ((('pm', 'validate'), 2.0),
                                 (('check', 'pm'), 5.5)):
                code, out, walked, took = run(root, *argv)
                said = f'{" ".join(argv)}: {walked}\n{out[-800:]}'
                self.assertEqual(code, 0, said)
                # A zero count passes vacuously (rule 4): every pool was
                # walked, and nothing was walked twice.
                for pool in inventory.POOL_NAME.values():
                    self.assertEqual([n for key, n in walked.items()
                                      if Path(key).name == pool], [1], said)
                self.assertEqual({n for n in walked.values()}, {1}, said)
                self.assertLess(took, budget, said)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
