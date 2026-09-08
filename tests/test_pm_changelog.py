"""`changelog:` on the grain, and the two gates that read it.

`CHANGELOG.md` went the way of `ROADMAP.md`: 469 lines by ~12 authors with no
binding between an entry and the work it described. The field is the record and
`agentic-sdlc changelog` is the view.

Both gates get a DELIBERATELY-BROKEN PROBE, because both replaced a check that
graded almost nothing — bullets in a file — and a replacement that cannot fail
would be the same defect wearing a better sentence.
"""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from support.pm import loaded, run_gate, tree, write

from agentic_sdlc.repo.pm import changelog, model

MILESTONE = '0.1'
FEATURE = '0.1/alpha'
STORY = '0.1/alpha/s0'


def render(root, *args) -> tuple[int, str, str]:
    """The verb through its own `main`, both streams captured separately —
    the rows are stdout and the census is stderr, and a consumer piping the
    first must never receive the second."""
    out, err = io.StringIO(), io.StringIO()
    import os
    previous = os.getcwd()
    os.chdir(root)
    try:
        from agentic_sdlc.core.project import load_config, repo_root
        repo_root.cache_clear()
        load_config.cache_clear()
        with redirect_stdout(out), redirect_stderr(err):
            code = changelog.main(list(args))
    finally:
        os.chdir(previous)
        from agentic_sdlc.core.project import load_config, repo_root
        repo_root.cache_clear()
        load_config.cache_clear()
    return code, out.getvalue(), err.getvalue()


def stamp(root, gid: str, text: str) -> None:
    grain = model.grain_index(loaded(root))[gid]
    assert model.set_field(grain.path, changelog.FIELD, text), gid


class TheFieldIsTheRecord(unittest.TestCase):

    def test_the_walk_is_the_parents_declared_order_across_kinds(self):
        """A milestone's `order:` interleaves bugs and features, and walking
        kind-by-kind would reorder the release note away from the sequence the
        work shipped in. Parent before child, depth first."""
        with tree(story_statuses=('done',)) as root:
            write(root / 'pm/roadmap/bugs/crash.md',
                  {'id': 'bg-crash', 'kind': 'bug', 'milestone': '"0.1"',
                   'name': 'C', 'status': 'closed'})
            mfile = root / 'pm/roadmap/milestones/0.1.md'
            model.set_list_field(mfile, model.ORDER_KEY,
                                 ['bg-crash', FEATURE])
            walked = [e.gid for e in changelog.collect(loaded(root), MILESTONE)]
            self.assertEqual(walked, [MILESTONE, 'bg-crash', FEATURE, STORY])
            # And the declared order is honoured, not the kind or the id.
            model.set_list_field(mfile, model.ORDER_KEY,
                                 [FEATURE, 'bg-crash'])
            walked = [e.gid for e in changelog.collect(loaded(root), MILESTONE)]
            self.assertEqual(walked, [MILESTONE, FEATURE, STORY, 'bg-crash'])

    def test_none_is_an_ANSWER_and_an_empty_field_is_not(self):
        """The whole point of the word. `none` says this grain earned no
        consumer-visible line; empty says nobody has decided."""
        with tree(story_statuses=('done',)) as root:
            stamp(root, FEATURE, 'The feature shipped a thing.')
            stamp(root, STORY, 'none')
            entries = {e.gid: e for e in changelog.collect(loaded(root), MILESTONE)}
            self.assertTrue(entries[FEATURE].said_something)
            self.assertFalse(entries[FEATURE].declined)
            self.assertTrue(entries[STORY].declined)
            self.assertFalse(entries[STORY].said_something)
            self.assertFalse(entries[MILESTONE].declined)
            self.assertFalse(entries[MILESTONE].said_something)
            # NONE renders nothing; it is a decision the tree keeps, not a line.
            rows = changelog.rows(list(entries.values()))
            self.assertEqual([r[0] for r in rows], [FEATURE])

    def test_the_verb_renders_rows_on_stdout_and_its_census_on_stderr(self):
        with tree(feature_status='done', story_statuses=('done',)) as root:
            stamp(root, FEATURE, 'A sentence.')
            stamp(root, STORY, 'none')
            code, out, err = render(root, MILESTONE)
            self.assertEqual(code, 0, err)
            self.assertEqual(out.strip().split('\t'),
                             [FEATURE, 'feature', 'done', 'A sentence.'])
            self.assertNotIn('[changelog]', out)
            # Rule 4: the census says what it walked, and `declined` is what a
            # grain SAID rather than the arithmetic remainder.
            self.assertIn('1 entry/ies of 3 grain(s)', err)
            self.assertIn('1 declined', err)
            self.assertIn('1 unanswered', err)

    def test_json_carries_the_same_rows_under_the_declared_columns(self):
        with tree(story_statuses=('done',)) as root:
            stamp(root, FEATURE, 'A sentence.')
            code, out, _ = render(root, MILESTONE, '--json')
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(len(payload), 1)
            self.assertEqual(tuple(payload[0]), changelog.COLUMNS)
            self.assertEqual(payload[0]['changelog'], 'A sentence.')

    def test_an_id_that_resolves_to_nothing_is_exit_2(self):
        with tree() as root:
            code, out, err = render(root, 'ms-nope')
            self.assertEqual(code, 2)
            self.assertIn('no grain resolves', err)
            self.assertEqual(out, '')


class TheGatesReadIt(unittest.TestCase):
    """D12 and the release step, each with the probe that proves it can fail."""

    def test_D12_names_a_closed_grain_that_answered_neither_way(self):
        with tree(milestone_status='building', feature_status='done',
                  story_statuses=('done',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)   # a WARN, never the exit code
            self.assertIn(f'feature {FEATURE}', out)
            self.assertIn(f'carries no `{changelog.FIELD}:`', out)
            self.assertIn('(D12)', out)
            self.assertIn('CHANGELOG  0 of 2 closed grain(s) answered', out)

    def test_D12_goes_quiet_on_a_sentence_AND_on_none(self):
        """The probe for the rule's own vacuity: it must go quiet for the right
        reason, so both answers are exercised and the census is asserted."""
        with tree(milestone_status='building', feature_status='done',
                  story_statuses=('done',)) as root:
            stamp(root, FEATURE, 'A sentence.')
            stamp(root, STORY, 'none')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn(f'carries no `{changelog.FIELD}:`', out)
            self.assertIn('CHANGELOG  2 of 2 closed grain(s) answered', out)

    def test_D12_is_silent_over_a_SHIPPED_milestone(self):
        """Not history rewriting. The field arrived at 0.6.0 and 168 grains
        closed before it existed; asking them all for a sentence nobody will
        write is the unactionable-warning defect this milestone is fixing."""
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn(f'carries no `{changelog.FIELD}:`', out)
            self.assertIn('CHANGELOG  0 of 0 closed grain(s) answered', out)


if __name__ == '__main__':
    unittest.main()
