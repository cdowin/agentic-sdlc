"""test_pm_migrate.py — the ref sweep the nested-to-pooled migration runs.

**Selection criterion (hard rule 10):** `tests/test_pm_rename.py` covers the
SHIPPED sweeper — `pm rename`, one id at a time, which finds a ref by PARSING
the value — and its own docstring recorded the gap: `tools/dev/pm_migrate.py`
was "a script no test drives". That gap is the bug. The migration carries a
SECOND, simpler matcher sharing no code with the first, and it required a quote
character on both sides of an id: so `depends_on: ["a/b"]` was rewritten and
`consumed_by: [a/b,c/d]` — an ordinary YAML inline sequence — was not. A real
497-grain consumer tree came out of the migration with 52 refs still naming
pre-migration ids, each one counted UNVERIFIABLE while `check pm` exited 0
(bg-the-migration-rewrites-only-quoted-refs). Rule 4's first cardinal sin, on
real data.

No rename case can be amended to cover this; the two matchers are different
code. Three of the four cases below are a FUNCTION CALL on a string, which is
the cheapest tier a matcher can fail at. The fourth stands a nested tree up and
runs the whole migration, because the second half of the defect is a NUMBER the
script never printed — the ref census either side of its own write, which is
the only thing that says whether the graph survived the move.

Unit tier by construction: no case here spawns, and the migration is a library
call from this module rather than a `python3 tools/dev/pm_migrate.py`.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

from support import REPO_ROOT
from support.pm import cfg_for, tree, write

from agentic_sdlc.core import frontmatter
from agentic_sdlc.repo.pm import model

# NOT importable as a package: the script lives outside `src/` on purpose (it
# is deliberately not a verb — the CLI is a published API and this job runs
# once per tree), so the test reaches it the same way an operator does.
sys.path.insert(0, str(REPO_ROOT / 'tools' / 'dev'))
import pm_migrate  # noqa: E402

POOLS = 'pm/roadmap'
# One rename per shape the fix has to survive: a slashed id, a second one
# sharing its prefix, and a bare version — the three the consumer tree held.
RENAMES = {'0.1/alpha': 'ft-alpha', '0.1/beta': 'ft-beta', '0.90.4': 'ms-four'}


def swept(frontmatter: str) -> str:
    """`_rewritten` over a document whose frontmatter is `frontmatter`.

    The BODY carries an id too, so every case also asserts by omission that the
    sweep stays inside the fence.
    """
    return pm_migrate._rewritten(f'---\n{frontmatter}---\n\n0.1/alpha\n',
                                 RENAMES)


class TheSweepIsWholeToken(unittest.TestCase):
    """A quote is not a boundary and never was: the id grammar is."""

    def test_an_unquoted_inline_sequence_is_rewritten(self):
        """THE BUG. `consumed_by: [a/b,c/d]` is what a hand-written tree holds
        and what the quote-matching walked straight past — 52 times, silently.
        """
        text = swept('consumed_by: [0.1/alpha,0.1/beta]\n'
                     'depends_on: [0.1/alpha, 0.1/beta]\n'
                     'milestone: [0.90.4]\n'
                     'feature: 0.1/alpha\n')
        self.assertIn('consumed_by: [ft-alpha,ft-beta]', text)
        self.assertIn('depends_on: [ft-alpha, ft-beta]', text)
        self.assertIn('milestone: [ms-four]', text)
        self.assertIn('feature: ft-alpha', text)
        self.assertNotIn('0.1/alpha\n---', text)
        # The fence is the sweep's edge; the body's id is prose.
        self.assertTrue(text.endswith('---\n\n0.1/alpha\n'), text)

    def test_a_quoted_ref_is_still_rewritten(self):
        """The property the quote-matching WAS buying, kept: both quote
        characters, an inline list and a block one, in one pass."""
        text = swept('depends_on: ["0.1/alpha", \'0.1/beta\']\n'
                     'caught_in: "0.90.4"\n'
                     'order:\n'
                     '  - "0.1/alpha"\n'
                     '  - 0.1/beta\n')
        self.assertIn('depends_on: ["ft-alpha", \'ft-beta\']', text)
        self.assertIn('caught_in: "ms-four"', text)
        self.assertIn('  - "ft-alpha"', text)
        self.assertIn('  - ft-beta', text)

    def test_an_id_that_merely_starts_with_a_renamed_one_is_not_a_ref(self):
        """`0.1/alphabet` is a different grain, and a substring sweep would
        corrupt it and every path that happens to contain a renamed id.

        The `0.1/beta` on the same line is the probe: without it a matcher that
        skipped the line entirely would pass this case.
        """
        text = swept('depends_on: [0.1/alphabet, 0.1/alpha-two, 0.1/beta]\n'
                     'reviewed: docs/reviews/0.1/alpha.md\n')
        self.assertIn('depends_on: [0.1/alphabet, 0.1/alpha-two, ft-beta]',
                      text)
        self.assertIn('reviewed: docs/reviews/0.1/alpha.md', text)


def as_nested(root: Path) -> None:
    """A PRE-0.4.0 tree the migration can move, holding both ref shapes.

    `0.1/beta` depends on the feature next door through an UNQUOTED inline
    sequence — the shape the sweep missed — and on `0.99/gone`, a ref into a
    milestone that is not in the tree. That second one is legitimately
    UNVERIFIABLE on both sides of the move, so the census the migration prints
    is a real measurement rather than a pair of zeros.
    """
    pools = root / POOLS
    for path in sorted(pools.rglob('*.md')):
        path.unlink()
    mdir = pools / '0.1-demo'
    write(mdir / model.MILESTONE_DOC,
          {'id': '"0.1"', 'name': 'Demo', 'status': 'building'})
    write(mdir / 'features' / 'alpha' / model.FEATURE_DOC,
          {'id': '0.1/alpha', 'milestone': '"0.1"', 'name': 'Alpha',
           'status': 'building', 'reviewed': ''})
    write(mdir / 'features' / 'beta' / model.FEATURE_DOC,
          {'id': '0.1/beta', 'milestone': '"0.1"', 'name': 'Beta',
           'status': 'planning', 'reviewed': '',
           'depends_on': '[0.1/alpha,0.99/gone]'})
    write(mdir / 'features' / 'alpha' / 'stories' / '01-s0.md',
          {'id': '0.1/alpha/s0', 'feature': '0.1/alpha', 'milestone': '"0.1"',
           'name': 'S0', 'status': 'ready', 'depends_on': '["0.1/alpha"]'})


class TheMigrationSaysWhatHappenedToTheRefs(unittest.TestCase):
    """The second half of the defect, and the half that made it SILENT.

    An unrewritten ref names a grain that IS in the tree, under an id nothing
    answers to — so it fails no gate: it is counted UNVERIFIABLE, the bucket a
    retired milestone's refs land in. The migration reported success either
    way, because the one number that says whether the graph survived was the
    one it did not print (rule 11).
    """

    def test_the_ref_census_is_printed_either_side_of_the_move(self):
        with tree(with_record=False) as root:
            as_nested(root)
            code, lines = pm_migrate.run(cfg_for(root))
            out = '\n'.join(lines)
            self.assertEqual(code, 0, out)
            # 3 refs: beta's two and the story's one. The UNVERIFIABLE one is
            # `0.99/gone` — before AND after, because the sweep rewrote the
            # other two. Quote-matching alone leaves this at `1 -> 2`.
            self.assertIn('refs: 3 -> 3; UNVERIFIABLE: 1 -> 1', out)
            self.assertNotIn('WARNING', out)
            self.assertEqual(
                frontmatter.field_of(root / POOLS / 'features' / 'ft-beta.md',
                               'depends_on'),
                '[ft-alpha,0.99/gone]', out)

    def test_a_risen_count_is_named_rather_than_left_to_be_noticed(self):
        """A number nobody reads is the same silence one layer along, so the
        rise gets its own line and says what to run (rule 11).

        A function call on two dicts: the tree that produces a rise is the bug
        this file fixes, and staging one would prove nothing the case above
        does not already prove.
        """
        risen = pm_migrate._census_lines({'refs': 3, 'unverifiable': 1},
                                         {'refs': 3, 'unverifiable': 3})
        self.assertIn('UNVERIFIABLE: 1 -> 3', risen[0])
        self.assertIn('WARNING: 2 more ref(s)', '\n'.join(risen[1:]))
        self.assertIn('pm validate', '\n'.join(risen[1:]))
        # Unreadable on one side is UNKNOWN and says so — never a 0 that reads
        # as "no refs were harmed".
        unread = pm_migrate._census_lines({'refs': 3, 'unverifiable': 1}, None)
        self.assertIn('UNVERIFIABLE: 1 -> unknown', unread[0])
        self.assertIn('unproven', '\n'.join(unread[1:]))


if __name__ == '__main__':  # pragma: no cover - `make unit` is the runner
    unittest.main()
