"""`pm add` / `pm remove` — one container sequences its children with `order`.

Membership is the child's field; SEQUENCE is the parent's list. One shape at
every level — root → milestones, milestone → features and bugs, feature →
stories — so the cases below are PARAMETERISED over the levels rather than
written per level, which is the claim the story makes: `add` is `set` plus a
list insert, and the level is read off the two ids.

**Selection criterion (hard rule 10):** these verbs WRITE, so what stays here
is the write-side cardinal sin — a bind or a sequence edit that looks
legitimate and is not — plus every refusal and every idempotence case. Byte
fidelity of the underlying writer is proven once in tests/test_pm_verbs.py
`TheListWriterKeepsEveryOtherByte`; the plan's own resolvers in the same file's
`ThePlanIsADeclaredOrder`.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from support.pm import (cfg_for, ledger_rows, run_cli, run_gate, tree, write,
                        write_config)

from agentic_sdlc.core import frontmatter
from agentic_sdlc.repo.pm import cli, inventory, ledger, vocabulary

PLAN_REL = 'pm/roadmap/releases.md'

# One row per LEVEL: (parent id, its document, child id, the child's document,
# the field the child names its parent with). The root's is '' — a milestone
# names no parent, so at that level `add` is the sequence half alone.
LEVELS = (
    ('roadmap', PLAN_REL, '0.1', 'pm/roadmap/milestones/0.1.md', ''),
    ('0.1', 'pm/roadmap/milestones/0.1.md',
     '0.1/alpha', 'pm/roadmap/features/alpha.md', 'milestone'),
    ('0.1/alpha', 'pm/roadmap/features/alpha.md',
     '0.1/alpha/s0', 'pm/roadmap/stories/s0.md', 'feature'),
)


def order_of(root: Path, rel: str) -> list[str]:
    return frontmatter.list_field_of(root / rel, 'order')


def unbound(root: Path) -> None:
    """The fixture's feature and story, authored and bound to nothing."""
    frontmatter.set_field(root / 'pm/roadmap/features/alpha.md', 'milestone', '')
    frontmatter.set_field(root / 'pm/roadmap/stories/s0.md', 'feature', '')


class AddBindsAndSequencesAtEveryLevel(unittest.TestCase):
    def test_one_verb_binds_and_sequences_at_each_level(self):
        for parent, prel, child, crel, field in LEVELS:
            with self.subTest(parent=parent), tree(story_statuses=('ready',)) as root:
                unbound(root)
                code, out = run_cli(root, 'add', parent, child)
                self.assertEqual(code, 0, out)
                self.assertEqual(order_of(root, prel), [child])
                if field:
                    self.assertEqual(
                        frontmatter.unquote(frontmatter.field_of(root / crel, field)),
                        parent)

    def test_the_same_add_twice_writes_nothing_the_second_time(self):
        # Hard rule 3, at every level.
        for parent, prel, child, _crel, _field in LEVELS:
            with self.subTest(parent=parent), tree(story_statuses=('ready',)) as root:
                unbound(root)
                self.assertEqual(run_cli(root, 'add', parent, child)[0], 0)
                before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                code, out = run_cli(root, 'add', parent, child)
                self.assertEqual(code, 0, out)
                self.assertIn('nothing was written', out)
                after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                self.assertEqual(before, after)

    def test_remove_unbinds_and_unsequences_together(self):
        for parent, prel, child, crel, field in LEVELS:
            with self.subTest(parent=parent), tree(story_statuses=('ready',)) as root:
                unbound(root)
                run_cli(root, 'add', parent, child)
                code, out = run_cli(root, 'remove', parent, child)
                self.assertEqual(code, 0, out)
                self.assertEqual(order_of(root, prel), [])
                if field:
                    self.assertEqual(
                        frontmatter.unquote(frontmatter.field_of(root / crel, field)), '')
                # ...and twice is a no-op that says so.
                code, out = run_cli(root, 'remove', parent, child)
                self.assertEqual(code, 0, out)
                self.assertIn('nothing was written', out)

    def test_set_still_unbinds_alone_and_leaves_the_entry_dangling(self):
        # Criterion 2: `remove` is the pair, and `pm set <id> <rel> ""` is
        # still the way to unbind WITHOUT unsequencing — which is exactly the
        # DANGLING entry the gate reports.
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'add', '0.1/alpha', '0.1/alpha/s0')
            self.assertEqual(run_cli(root, 'set', '0.1/alpha/s0',
                                     'feature', '')[0], 0)
            self.assertEqual(order_of(root, 'pm/roadmap/features/alpha.md'),
                             ['0.1/alpha/s0'])
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('DANGLING', out)
            self.assertIn('0.1/alpha/s0', out)


class TheDanglingNoticeReadsTheParentsOrder(unittest.TestCase):
    """Symptom 3 of 0.6.0/D11: the notice fired on a condition it never read.

    Rebinding a child printed `<old-parent> still lists <child> in its `order`
    — that entry is now DANGLING` off the child's PREVIOUS BINDING alone. When
    the old parent's `order:` had never held the id, the notice was false AND
    the `pm remove` it named then refused, because `remove` verifies membership
    against the binding the rebind had just changed. **The command the tool
    printed could not succeed at the moment it printed it** — a warning on a
    false condition naming an impossible fix, which is the mirror of a gate
    that cannot fail.
    """

    @staticmethod
    def _second_milestone(root: Path) -> None:
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': '"0.2"', 'kind': 'milestone', 'name': 'Two',
               'status': 'building'})

    def test_a_rebind_off_a_parent_that_never_sequenced_it_stays_silent(self):
        with tree(story_statuses=('ready',)) as root:
            self._second_milestone(root)
            # Bound to 0.1 and in NO `order:` — the normal state of a grain
            # written and never sequenced.
            write(root / 'pm/roadmap/bugs/crash.md',
                  {'id': 'bg-crash', 'kind': 'bug', 'milestone': '"0.1"',
                   'name': 'C', 'status': 'open'})
            code, out = run_cli(root, 'add', '0.2', 'bg-crash')
            self.assertEqual(code, 0, out)
            self.assertIn("milestone '0.1' -> '0.2'", out)
            self.assertNotIn('DANGLING', out)
            self.assertNotIn('noticed', out)

    def test_a_rebind_off_a_parent_that_DID_sequence_it_still_notices(self):
        """The other half — the notice is not simply deleted. Here the entry
        really is left behind, and the `pm remove` it names RUNS."""
        with tree(story_statuses=('ready',)) as root:
            self._second_milestone(root)
            write(root / 'pm/roadmap/bugs/crash.md',
                  {'id': 'bg-crash', 'kind': 'bug', 'milestone': '"0.1"',
                   'name': 'C', 'status': 'open'})
            self.assertEqual(run_cli(root, 'add', '0.1', 'bg-crash')[0], 0)
            code, out = run_cli(root, 'add', '0.2', 'bg-crash')
            self.assertEqual(code, 0, out)
            self.assertIn('DANGLING', out)
            self.assertIn('pm remove 0.1 bg-crash', out)
            # THE REMEDY RUNS. This is the assertion the bug is about: a
            # printed fix that refuses is worse than no fix printed.
            code, out = run_cli(root, 'remove', '0.1', 'bg-crash')
            self.assertEqual(code, 0, out)
            self.assertEqual(order_of(root, 'pm/roadmap/milestones/0.1.md'), [])


class ThePlaceIsTheDecisionAndNeverAGuess(unittest.TestCase):
    """Bare `add` appends; a placement flag says where, and one that cannot be
    honoured refuses rather than picking a position."""

    def _three(self, root: Path) -> None:
        for slug in ('b', 'c'):
            run_cli(root, 'new', 'feature', '0.1', slug, slug.upper())
        for fid in ('0.1/alpha', 'ft-b', 'ft-c'):
            run_cli(root, 'add', '0.1', fid)

    def test_bare_add_appends(self):
        with tree(story_statuses=('ready',)) as root:
            self._three(root)
            self.assertEqual(order_of(root, 'pm/roadmap/milestones/0.1.md'),
                             ['0.1/alpha', 'ft-b', 'ft-c'])

    def test_each_placement_flag_puts_it_where_it_says(self):
        for flag, value, expect in (
                ('--position', '1', ['ft-c', '0.1/alpha', 'ft-b']),
                ('--position', '2', ['0.1/alpha', 'ft-c', 'ft-b']),
                ('--before', 'ft-b', ['0.1/alpha', 'ft-c', 'ft-b']),
                ('--after', '0.1/alpha', ['0.1/alpha', 'ft-c', 'ft-b'])):
            with self.subTest(flag=flag, value=value), \
                    tree(story_statuses=('ready',)) as root:
                self._three(root)
                code, out = run_cli(root, 'add', '0.1', 'ft-c', flag, value)
                self.assertEqual(code, 0, out)
                self.assertEqual(order_of(root, 'pm/roadmap/milestones/0.1.md'),
                                 expect)

    def test_a_place_that_cannot_be_honoured_refuses_and_writes_nothing(self):
        for flag, value in (('--position', '9'), ('--position', '0'),
                            ('--before', '0.1/nope'), ('--after', '0.1/nope')):
            with self.subTest(flag=flag, value=value), \
                    tree(story_statuses=('ready',)) as root:
                self._three(root)
                before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                code, out = run_cli(root, 'add', '0.1', 'ft-c', flag, value)
                self.assertIn(code, (1, 2), out)
                after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                self.assertEqual(before, after)

    def test_two_places_in_one_invocation_are_usage(self):
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'add', '0.1', '0.1/alpha',
                                '--position', '1', '--before', '0.1/alpha')
            self.assertEqual(code, 2, out)
            self.assertIn('one per invocation', out)


class ContainsDecidesWhatMayHoldWhat(unittest.TestCase):
    """`[pm.contains]` — one declaration for every level, so `add` carries no
    per-level check. The pair is read off the two IDS: neither argument names a
    kind, and the refusal names BOTH."""

    OFF_MAPPING = (('0.1', '0.1/alpha/s0', 'milestone', 'story'),
                   ('0.1/alpha', '0.1', 'feature', 'milestone'),
                   ('roadmap', '0.1/alpha', 'roadmap', 'feature'),
                   ('0.1/alpha/s0', '0.1/alpha', 'story', 'feature'))

    def test_a_pair_off_the_mapping_refuses_naming_both_kinds(self):
        for parent, child, pkind, ckind in self.OFF_MAPPING:
            with self.subTest(parent=parent, child=child), \
                    tree(story_statuses=('ready',)) as root:
                run_cli(root, 'add', 'roadmap', '0.1')
                before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                code, out = run_cli(root, 'add', parent, child)
                self.assertEqual(code, 1, out)
                self.assertIn(pkind, out)
                self.assertIn(ckind, out)
                self.assertIn('[pm.contains]', out)
                after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                self.assertEqual(before, after)

    def test_a_project_that_files_no_bugs_narrows_the_mapping(self):
        # The knob's whole job: DECLARE which kinds hold which, and `add`
        # refuses off it. Nothing else in the tree changes.
        with tree(story_statuses=('ready',)) as root:
            from support.pm import bug
            bug(root, 'crash')
            self.assertEqual(run_cli(root, 'add', '0.1', '0.1/bugs/crash')[0], 0)
            write_config(root, '[pm.contains]\nmilestone = ["feature"]\n')
            code, out = run_cli(root, 'add', '0.1', '0.1/bugs/crash')
            self.assertEqual(code, 1, out)
            self.assertIn('a milestone does not hold a bug', out)

    def test_a_mapping_nothing_could_write_is_exit_2_by_name(self):
        # Hard rule 9: a malformed DECLARATION is refused at exit 2, naming
        # the field that would have to carry it. It narrows; it cannot
        # re-parent a kind.
        for toml, needle in (
                ('[pm.contains]\nmilestone = ["story"]\n', '`feature:`'),
                ('[pm.contains]\nfeature = ["milestone"]\n', 'the roadmap'),
                ('[pm.contains]\nstory = ["wombat"]\n', 'wombat'),
                ('[pm.contains]\nwombat = ["story"]\n', 'wombat')):
            with self.subTest(toml=toml), tree(story_statuses=('ready',)) as root:
                write_config(root, toml)
                code, out = run_cli(root, 'add', '0.1', '0.1/alpha')
                self.assertEqual(code, 2, out)
                self.assertIn('[pm.contains]', out)
                self.assertIn(needle, out)

    def test_a_tree_that_declares_nothing_runs_the_stock_mapping(self):
        # Hard rule 5: the byte-identical guarantee. The declared mapping and
        # no mapping at all behave the same.
        stock = ('[pm.contains]\nroadmap = ["milestone"]\n'
                 'milestone = ["feature", "bug"]\nfeature = ["story"]\n')
        outputs = []
        for config in ('', stock):
            with tree(story_statuses=('ready',)) as root:
                write_config(root, config)
                unbound(root)
                outputs.append([run_cli(root, 'add', p, c)
                                for p, _, c, _, _ in LEVELS])
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(vocabulary.DEFAULT_CONTAINS['milestone'],
                         ('feature', 'bug'))


class TheVerbRefusesOnlyFactsAboutItsInput(unittest.TestCase):
    def test_an_id_that_resolves_to_nothing_is_exit_2_naming_which_one(self):
        with tree(story_statuses=('ready',)) as root:
            for argv, role in ((('add', 'nope', '0.1/alpha'), 'parent'),
                               (('add', '0.1', 'nope'), 'child'),
                               (('remove', 'nope', '0.1/alpha'), 'parent'),
                               (('remove', '0.1', 'nope'), 'child')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 2, out)
                    self.assertIn(role, out)

    def test_remove_clears_a_dangling_entry_and_leaves_the_binding_alone(self):
        # The pair `add` names when it re-binds: the old parent still
        # sequences a child it no longer holds, and this is what clears it.
        # The binding is NOT touched — it names a parent this command was not
        # given.
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'new', 'feature', '0.1', 'b', 'B')
            run_cli(root, 'add', '0.1/alpha', '0.1/alpha/s0')
            code, out = run_cli(root, 'add', 'ft-b', '0.1/alpha/s0')
            self.assertEqual(code, 0, out)
            self.assertIn('DANGLING', out)
            self.assertEqual(order_of(root, 'pm/roadmap/features/alpha.md'),
                             ['0.1/alpha/s0'])
            code, out = run_cli(root, 'remove', '0.1/alpha', '0.1/alpha/s0')
            self.assertEqual(code, 0, out)
            self.assertEqual(order_of(root, 'pm/roadmap/features/alpha.md'), [])
            self.assertEqual(
                frontmatter.unquote(frontmatter.field_of(
                    root / 'pm/roadmap/stories/s0.md', 'feature')), 'ft-b')

    def test_removing_a_child_bound_elsewhere_refuses(self):
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'new', 'feature', '0.1', 'b', 'B')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            code, out = run_cli(root, 'remove', 'ft-b', '0.1/alpha/s0')
            self.assertEqual(code, 1, out)
            self.assertIn('nothing was written', out)
            after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_a_parent_cannot_hold_itself(self):
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'add', '0.1', '0.1')
            self.assertEqual(code, 1, out)

    def test_an_order_that_is_a_scalar_refuses_rather_than_being_rewritten(self):
        # The writer will not decide that a file meant something else.
        with tree(story_statuses=('ready',)) as root:
            path = root / 'pm/roadmap/features/alpha.md'
            path.write_text('---\nid: 0.1/alpha\nkind: feature\n'
                            'milestone: "0.1"\nstatus: building\n'
                            'order: s0\n---\n\nbody\n', encoding='utf-8')
            before = path.read_bytes()
            code, out = run_cli(root, 'add', '0.1/alpha', '0.1/alpha/s0')
            self.assertEqual(code, 1, out)
            self.assertIn('scalar', out)
            self.assertEqual(path.read_bytes(), before)


class TheRootIsAParentLikeAnyOther(unittest.TestCase):
    """Criterion 7 — `order` lists child ids at every level, INCLUDING the
    root, and `pm order` retired into this verb."""

    def test_scheduling_a_release_mints_the_plan_as_a_grain(self):
        with tree(story_statuses=('ready',)) as root:
            self.assertFalse((root / PLAN_REL).exists())
            code, out = run_cli(root, 'add', 'roadmap', '0.1')
            self.assertEqual(code, 0, out)
            text = (root / PLAN_REL).read_text(encoding='utf-8')
            self.assertTrue(text.startswith('---\n'))
            self.assertIn('# The release plan', text)
            self.assertEqual(inventory.root_id(cfg_for(root)), 'roadmap')
            self.assertEqual(order_of(root, PLAN_REL), ['0.1'])

    def test_the_plan_answers_to_the_id_it_declares(self):
        with tree(story_statuses=('ready',)) as root:
            (root / PLAN_REL).write_text(
                '---\nid: the-plan\nkind: roadmap\norder:\n---\n\nPlan.\n',
                encoding='utf-8')
            self.assertEqual(inventory.root_id(cfg_for(root)), 'the-plan')
            self.assertEqual(run_cli(root, 'add', 'the-plan', '0.1')[0], 0)
            self.assertEqual(order_of(root, PLAN_REL), ['0.1'])
            # ...and `roadmap` is then no id at all, rather than a second name
            # for the same file.
            self.assertEqual(run_cli(root, 'add', 'roadmap', '0.1')[0], 2)

    def test_the_retired_verb_names_its_replacement_at_exit_2(self):
        # A retired verb read as "unknown command" reads as a typo and sends
        # the reader hunting for a misspelling instead of for the replacement.
        with tree(story_statuses=('ready',)) as root:
            for argv, needle in ((('order', '--append', '0.1.0'), 'pm add'),
                                 (('sync',), 'order:')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 2, out)
                    self.assertIn('was retired', out)
                    self.assertIn(needle, out)
                    self.assertNotIn('unknown command', out)


class ThePlanIsRead(unittest.TestCase):
    def test_roadmap_prints_each_entry_with_its_version_and_state(self):
        with tree(story_statuses=('ready',)) as root:
            write(root / 'pm/roadmap/milestones/b.md',
                  {'id': '"b"', 'kind': 'milestone', 'name': 'B',
                   'status': 'building'})
            frontmatter.set_field(root / 'pm/roadmap/milestones/0.1.md',
                            'version', '0.1.0')
            run_cli(root, 'add', 'roadmap', '0.1')
            run_cli(root, 'add', 'roadmap', 'b')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            # COLUMNS IN ORDER, `-` for an empty cell so a shell `read` gets a
            # fixed count: version, milestone, state, name, summary.
            self.assertIn('0.1.0\t0.1\tbuilding\tDemo\t-', out)
            self.assertIn('(no version)\tb\tbuilding\tB\t-', out)
            for line in [ln for ln in out.splitlines()
                         if not ln.startswith('[pm]')]:
                self.assertEqual(len(line.split('\t')),
                                 len(cli.ROADMAP_COLUMNS), line)

    def test_roadmap_names_a_dangling_entry_rather_than_calling_it_unshipped(self):
        with tree(story_statuses=('ready',)) as root:
            (root / PLAN_REL).write_text(
                '---\nid: roadmap\norder:\n  - "gone"\n---\n\nPlan.\n',
                encoding='utf-8')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            self.assertIn('DANGLING', out)

    def test_a_retired_release_still_prints_its_version_name_and_summary(self):
        """`bg-retire-drops-the-summary-it-accepts`. A consumer deleting a
        hand-maintained ROADMAP.md loses its upcoming table to `order` — and
        its SHIPPED table to nothing at all, because a retire took the version,
        the name and the one sentence with the documents. The `retire` row is
        the tree's own copy, and this is the surface that reads it back.

        It also answers the question R1 could only call UNVERIFIABLE: a plan
        entry naming no grain is `retired` when a row says so, DANGLING when
        nothing does.
        """
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            frontmatter.set_field(root / 'pm/roadmap/milestones/0.1.md',
                            'version', '0.1.0')
            self.assertEqual(run_cli(root, 'add', 'roadmap', '0.1')[0], 0)
            self.assertEqual(
                run_cli(root, 'retire', '0.1', 'the', 'pools', 'landed')[0], 0)
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            self.assertIn('0.1.0\t0.1\tretired\tDemo\tthe pools landed', out)
            self.assertNotIn('DANGLING', out)

    def test_an_entry_no_retire_row_explains_is_DANGLING_until_one_is_backfilled(self):
        # The other half, so `retired` cannot become the answer for every
        # entry that names no grain.
        with tree(story_statuses=('ready',)) as root:
            (root / PLAN_REL).write_text(
                '---\nid: roadmap\norder:\n  - "gone"\n---\n\nPlan.\n',
                encoding='utf-8')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            self.assertIn('-\tgone\tDANGLING\t-\t-', out)
            # #31: a milestone pruned before 0.5.0 has no document to retire
            # from, so the caller supplies the two facts, and the row says it
            # was BACKFILLED rather than recorded. Twice is one row.
            backfill = ('retire', 'gone', '--version', '0.3.0', '--name',
                        'The Gone One', 'it', 'shipped')
            for _ in range(2):
                code, out = run_cli(root, *backfill)
                self.assertEqual(code, 0, out)
            self.assertIn('nothing was written (no-op)', out)
            rows = [r for r in ledger_rows(root, 'pm/roadmap/ledger.jsonl')
                    if r['kind'] == ledger.KIND_RETIRE]
            self.assertEqual(len(rows), 1, rows)
            self.assertIs(rows[0][ledger.BACKFILLED_FIELD], True)
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            self.assertIn('0.3.0\tgone\tretired\tThe Gone One\tit shipped', out)
            self.assertNotIn('DANGLING', out)
            # A CORRECTION of a backfill is a second row — `pm roadmap` reads
            # the last — and says whom it supersedes; `--dry-run` writes none.
            fix = ('retire', 'gone', '--version', '0.3.1', '--name', 'Gone')
            self.assertEqual(run_cli(root, *fix, '--dry-run')[0], 0)
            self.assertEqual(len(ledger_rows(root, 'pm/roadmap/ledger.jsonl')), 1)
            code, out = run_cli(root, *fix)
            self.assertEqual(code, 0, out)
            self.assertIn('supersedes the backfilled row', out)
            self.assertIn('0.3.1\tgone\tretired\tGone\t-',
                          run_cli(root, 'roadmap')[1])
            # Off the plan it says so — and not with `pm add`, which refuses
            # an id no grain claims.
            code, out = run_cli(root, 'retire', 'lost', '--version', '0.2.0',
                                '--name', 'Lost')
            self.assertEqual(code, 0, out)
            self.assertIn('lost is on no plan', out)
            self.assertNotIn('pm add roadmap lost', out)

    def test_next_is_the_first_unshipped_entry(self):
        with tree(story_statuses=('ready',)) as root:
            for mid, status in (('a', 'done'), ('b', 'building')):
                write(root / f'pm/roadmap/milestones/{mid}.md',
                      {'id': f'"{mid}"', 'kind': 'milestone', 'name': mid,
                       'status': status, 'version': f'"0.{mid}.0"'})
                run_cli(root, 'add', 'roadmap', mid)
            code, out = run_cli(root, 'next')
            self.assertEqual(code, 0, out)
            self.assertIn('0.b.0\tb\tbuilding', out)
            self.assertNotIn('0.a.0', out)

    def test_a_tree_with_no_plan_is_told_how_to_start_one(self):
        with tree(story_statuses=('ready',)) as root:
            for argv in (('roadmap',), ('next',)):
                code, out = run_cli(root, *argv)
                self.assertEqual(code, 0, out)
                self.assertIn('pm add roadmap <milestone-id>', out)

    def test_every_release_shipped_is_said_rather_than_guessed_at(self):
        with tree(milestone_status='done', story_statuses=('ready',)) as root:
            run_cli(root, 'add', 'roadmap', '0.1')
            code, out = run_cli(root, 'next')
            self.assertEqual(code, 0, out)
            self.assertIn('has shipped', out)
            self.assertIsNone(inventory.current_milestone(cfg_for(root)))

    def test_the_roadmap_verb_writes_nothing(self):
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'add', 'roadmap', '0.1')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(run_cli(root, 'roadmap')[0], 0)
            after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_an_unreadable_plan_is_refused_rather_than_printed_as_empty(self):
        # The same rule-4 shape R5 was fixed for: never report "no plan" over a
        # plan that is there and broken.
        with tree() as root:
            (root / PLAN_REL).write_text(
                '---\norder: 0.1\n---\n', encoding='utf-8')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 1, out)
            self.assertIn('scalar', out)


class OrderIsOptionalPerContainer(unittest.TestCase):
    """Criterion 5 — a bound child that nobody has sequenced is a CENSUS line,
    never a finding, and both numbers are printed or the census lies."""

    def test_an_unsequenced_child_is_counted_and_never_reddens(self):
        with tree(story_statuses=('ready',)) as root:
            # The fixture binds its feature and story and sequences neither.
            self.assertEqual(order_of(root, 'pm/roadmap/features/alpha.md'), [])
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('UNSEQUENCED', out)
            self.assertIn('1 story(s)', out)
            self.assertIn('1 feature(s)', out)
            self.assertNotIn('DRIFT', out)

    def test_the_census_carries_both_numbers(self):
        cases = ((False, False, 0), (True, False, 0), (False, True, 1))
        for sequence_it, dangle_it, findings in cases:
            with self.subTest(sequenced=sequence_it, dangling=dangle_it), \
                    tree(story_statuses=('ready',)) as root:
                if sequence_it:
                    run_cli(root, 'add', '0.1/alpha', '0.1/alpha/s0')
                if dangle_it:
                    run_cli(root, 'add', '0.1/alpha', '0.1/alpha/s0')
                    run_cli(root, 'set', '0.1/alpha/s0', 'feature', '')
                code, out = run_gate(root)
                self.assertEqual(code, min(findings, 1), out)
                self.assertEqual('DANGLING' in out, bool(dangle_it), out)

    def test_an_entry_naming_no_grain_at_all_is_a_warn_not_a_finding(self):
        # The retired-grain case, one level down from R1's: an entry that
        # names nothing may never be read as drift, because a grain that was
        # deleted and one never written look identical from here.
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'add', '0.1/alpha', '0.1/alpha/s0')
            (root / 'pm/roadmap/stories/s0.md').unlink()
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('UNVERIFIABLE', out)
            self.assertIn('0.1/alpha/s0', out)
