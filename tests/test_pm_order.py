"""`pm order` and `pm next` — the release plan as a declared sequence.

Order is a DECISION, not a sort: nothing here compares two version strings, and
the cases below are what hold that line. `--append` deliberately does not
interrogate the tree — a version is a fact about the INPUT, valid whether or not
a milestone claims it yet — so what this module proves is the split the package
states: a VERB refuses facts about its input, and the R rules in `check pm`
report the contradiction between the plan and the tree.

**Selection criterion (hard rule 10):** `pm order` WRITES, so what stays here is
the write-side cardinal sin — a plan edit that looks legitimate and is not —
plus every refusal and idempotence case. Byte fidelity of the underlying writer
is proven once in tests/test_pm_verbs.py `TheListWriterKeepsEveryOtherByte`.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from support.pm import cfg_for, run_cli, tree, write

from agentic_sdlc.repo.pm import model

PLAN_REL = 'pm/roadmap/releases.md'


def plan_of(root: Path) -> list[str]:
    return model.list_field_of(root / PLAN_REL, 'order')


def claims(root: Path, mid: str, version: str, status: str) -> None:
    write(root / f'pm/roadmap/{mid}-m/milestone.md',
          {'id': f'"{mid}"', 'name': mid, 'status': status,
           'version': f'"{version}"'})


class TheVerbWritesThePlan(unittest.TestCase):
    def test_append_mints_the_plan_then_extends_it_in_order(self):
        with tree() as root:
            self.assertFalse((root / PLAN_REL).exists())
            for version in ('0.1.0', '0.2.0', '0.3.0'):
                code, out = run_cli(root, 'order', '--append', version)
                self.assertEqual(code, 0, out)
            self.assertEqual(plan_of(root), ['0.1.0', '0.2.0', '0.3.0'])
            # The minted file is a GRAIN: frontmatter plus a body a human owns.
            text = (root / PLAN_REL).read_text(encoding='utf-8')
            self.assertTrue(text.startswith('---\n'))
            self.assertIn('# The release plan', text)

    def test_a_duplicate_append_is_a_no_op_that_says_so(self):
        # Rule 3: the same command twice is a no-op the second time.
        with tree() as root:
            run_cli(root, 'order', '--append', '0.1.0')
            before = (root / PLAN_REL).read_bytes()
            code, out = run_cli(root, 'order', '--append', '0.1.0')
            self.assertEqual(code, 0, out)
            self.assertIn('already in', out)
            self.assertIn('nothing was written', out)
            self.assertEqual((root / PLAN_REL).read_bytes(), before)

    def test_insert_places_one_entry_and_remove_takes_it_back_out(self):
        with tree() as root:
            for version in ('0.1.0', '0.3.0'):
                run_cli(root, 'order', '--append', version)
            code, out = run_cli(root, 'order', '--insert', '0.2.0',
                                '--before', '0.3.0')
            self.assertEqual(code, 0, out)
            self.assertEqual(plan_of(root), ['0.1.0', '0.2.0', '0.3.0'])
            code, out = run_cli(root, 'order', '--remove', '0.2.0')
            self.assertEqual(code, 0, out)
            self.assertEqual(plan_of(root), ['0.1.0', '0.3.0'])

    def test_removing_what_is_not_there_writes_nothing(self):
        with tree() as root:
            run_cli(root, 'order', '--append', '0.1.0')
            before = (root / PLAN_REL).read_bytes()
            code, out = run_cli(root, 'order', '--remove', '9.9.9')
            self.assertEqual(code, 0, out)
            self.assertIn('nothing was written', out)
            self.assertEqual((root / PLAN_REL).read_bytes(), before)


class TheVerbRefusesOnlyFactsAboutItsInput(unittest.TestCase):
    """The package's own split: a verb refuses its INPUT and reports nothing
    about the tree. `--append 9.9.9` on a tree where no milestone claims it is
    VALID — that contradiction is R1's to report, not this verb's to prevent.
    """

    def test_append_does_not_interrogate_the_tree(self):
        with tree() as root:
            code, out = run_cli(root, 'order', '--append', '9.9.9')
            self.assertEqual(code, 0, out)
            self.assertEqual(plan_of(root), ['9.9.9'])

    def test_an_empty_or_non_literal_version_is_exit_2(self):
        # Reuse of `model.segment_is_literal` (SDLC §5 — the matrix belongs to
        # the grammar). One case per class proves the REUSE; the grammar's own
        # 	matrix is not re-spelled here.
        for bad in ('', '   ', '../etc', 'a/b', '0.*', '.', '..'):
            with self.subTest(bad=bad), tree() as root:
                code, out = run_cli(root, 'order', '--append', bad)
                self.assertEqual(code, 2, out)
                self.assertFalse((root / PLAN_REL).exists())

    def test_insert_before_an_entry_that_is_not_there_is_refused(self):
        with tree() as root:
            run_cli(root, 'order', '--append', '0.1.0')
            before = (root / PLAN_REL).read_bytes()
            code, out = run_cli(root, 'order', '--insert', '0.2.0',
                                '--before', '9.9.9')
            self.assertEqual(code, 1, out)
            self.assertIn('nothing was written', out)
            self.assertEqual((root / PLAN_REL).read_bytes(), before)

    def test_insert_without_before_is_usage_because_where_is_the_decision(self):
        with tree() as root:
            code, out = run_cli(root, 'order', '--insert', '0.2.0')
            self.assertEqual(code, 2, out)
            self.assertIn('--before', out)

    def test_two_edits_in_one_invocation_are_refused(self):
        with tree() as root:
            code, out = run_cli(root, 'order', '--append', '0.1.0',
                                '--remove', '0.2.0')
            self.assertEqual(code, 2, out)
            self.assertFalse((root / PLAN_REL).exists())


class ThePlanIsRead(unittest.TestCase):
    def test_bare_order_prints_each_entry_with_its_milestone_and_state(self):
        with tree() as root:
            for version in ('0.1.0', '0.2.0'):
                run_cli(root, 'order', '--append', version)
            claims(root, 'a', '0.1.0', 'done')
            code, out = run_cli(root, 'order')
            self.assertEqual(code, 0, out)
            self.assertIn('0.1.0\ta\tshipped', out)
            self.assertIn('0.2.0\t(unclaimed)\t-', out)

    def test_next_is_the_first_unshipped_entry_and_who_claims_it(self):
        with tree() as root:
            for version in ('0.1.0', '0.2.0'):
                run_cli(root, 'order', '--append', version)
            claims(root, 'a', '0.1.0', 'done')
            claims(root, 'b', '0.2.0', 'building')
            code, out = run_cli(root, 'next')
            self.assertEqual(code, 0, out)
            self.assertIn('0.2.0\tb\tbuilding', out)
            self.assertNotIn('0.1.0', out)

    def test_a_tree_with_no_plan_is_told_how_to_start_one(self):
        with tree() as root:
            for argv in (('order',), ('next',)):
                code, out = run_cli(root, *argv)
                self.assertEqual(code, 0, out)
                self.assertIn('pm order --append', out)

    def test_every_release_shipped_is_said_rather_than_guessed_at(self):
        with tree() as root:
            run_cli(root, 'order', '--append', '0.1.0')
            claims(root, 'a', '0.1.0', 'done')
            code, out = run_cli(root, 'next')
            self.assertEqual(code, 0, out)
            self.assertIn('has shipped', out)
            self.assertIsNone(model.current_release(cfg_for(root)))


class TheRoadmapVerbReplacesTheFile(unittest.TestCase):
    """`pm roadmap` — the plan, derived. It is what `ROADMAP.md` was pretending
    to be: a live index of milestones, which a hand-maintained table cannot stay.
    """

    def test_it_prints_every_scheduled_release_then_the_backlog(self):
        with tree() as root:
            for version in ('0.1.0', '0.2.0'):
                run_cli(root, 'order', '--append', version)
            claims(root, 'a', '0.1.0', 'done')
            claims(root, 'b', '0.2.0', 'building')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            self.assertIn('2 scheduled release(s)', out)
            self.assertIn('0.1.0\ta\tshipped', out)
            self.assertIn('0.2.0\tb\tbuilding', out)
            # The fixture's own milestone declares no version — backlog.
            self.assertIn('backlog', out)
            self.assertIn('0.1', out)

    def test_it_writes_nothing(self):
        with tree() as root:
            run_cli(root, 'order', '--append', '0.1.0')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(run_cli(root, 'roadmap')[0], 0)
            after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_a_version_two_milestones_claim_is_named_rather_than_picked(self):
        with tree() as root:
            run_cli(root, 'order', '--append', '0.1.0')
            claims(root, 'a', '0.1.0', 'done')
            claims(root, 'b', '0.1.0', 'building')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 0, out)
            self.assertIn('CLAIMED TWICE', out)

    def test_an_unreadable_plan_is_refused_rather_than_printed_as_empty(self):
        # The same rule-4 shape R5 was fixed for: never report "no plan" over a
        # plan that is there and broken.
        with tree() as root:
            (root / 'pm/roadmap/releases.md').write_text(
                '---\norder: 0.1.0\n---\n', encoding='utf-8')
            code, out = run_cli(root, 'roadmap')
            self.assertEqual(code, 1, out)
            self.assertIn('scalar', out)
