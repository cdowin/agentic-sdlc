"""The pm verbs over the tree — status moves, close, retire, move, decide,
and the read/write verbs beside them (list/status/get/set/sync/vocabulary).

Split from test_pm.py by concern; the shared tree/run_cli/run_gate harness is
tests/support/pm.py. The refusal contract pinned throughout: a refused write
leaves the grain byte-identical — a half-applied cascade is worse than no
cascade.

**Selection criterion (hard rule 10, 0.2.0/the-proof-is-named-in-the-criterion):**
a `pm` verb WRITES, so what stays here is the write-side cardinal sin — a diff
that looks legitimate and is not — plus every idempotence and refusal case. A
verb's out-of-vocabulary refusal is proven once for all four grains in
`StatusVerbQuartet` rather than re-spelled per verb, and a help-text or
docstring claim is not asserted at all.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from support.pm import (
    CASE_SENSITIVE_TMP,
    STORY_REL,
    cfg_for,
    declaring,
    ledger_lines,
    loaded,
    run_cli,
    run_gate,
    tree,
    write,
    write_config,
)

from agentic_sdlc.repo.pm import model, skills

FFILE = 'pm/roadmap/0.1-demo/features/alpha/feature.md'
MFILE = 'pm/roadmap/0.1-demo/milestone.md'
SDIR = 'pm/roadmap/0.1-demo/features/alpha/stories'


class ReviewRecord(unittest.TestCase):
    """ONE question: does the pointer RESOLVE.

    There used to be a `review_min_content_bytes = 20` floor under it, and it
    refused an honest 15-byte "LGTM. Ship it.". How much a reviewer needed to
    write is not a fact about the tree; whether the file they named is there
    is, and it is the same fact V4 checks for `depends_on`.
    """

    def test_a_record_is_a_file_that_is_there_and_nothing_more(self):
        # An EMPTY file is a record: the tool has no opinion about how much is
        # enough, and the person who wrote it decided what belonged in it. A
        # missing one is not.
        with tree(with_record=True) as root:
            cfg = cfg_for(root)
            self.assertIsNotNone(model.review_record_for(cfg, '0.1/alpha'))
            (root / 'docs' / 'reviews' / 'alpha.md').write_text('', encoding='utf-8')
            self.assertIsNotNone(model.review_record_for(cfg, '0.1/alpha'))
            (root / 'docs' / 'reviews' / 'alpha.md').unlink()
            self.assertIsNone(model.review_record_for(cfg, '0.1/alpha'))


class StatusMoves(unittest.TestCase):
    """The verb writes a `status:`. It does not own a transition graph.

    The graph it replaced claimed, in this repo's own README, "transitions no
    one can hand-edit around". Proven false: a `sed` of the `status:` line
    reaches the exact state the CLI refused, and `check pm` then prints PASS,
    because nothing checks an EDGE — D3/D4/D5 check the tree's END STATE. So
    the graph taxed whoever used the sanctioned tool and stopped nobody else.

    The four shapes every status verb shares live in `StatusVerbQuartet`;
    this class keeps the round trips from a verb's write to the gate's read.
    """

    def test_a_hand_edit_reaches_what_the_cli_refused_and_the_gate_still_says_PASS(self):
        # The measurement that removed the graph, kept as the reason. A
        # `status:` line rewritten by hand lands a story at `done` under a DONE
        # feature — a state the old graph refused from `todo` — and every rule
        # that reads an END STATE is satisfied by it.
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('ready',)) as root:
            sf = root / STORY_REL
            sf.write_text(sf.read_text(encoding='utf-8')
                          .replace('status: todo', 'status: done'),
                          encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)

    def test_the_END_STATE_is_still_gated(self):
        # Report, do not refuse: a story at work under a feature that says it
        # has not started is D5's WARN whether the CLI or an editor put it
        # there — a line naming both, exit 0 (story 03).
        with tree(feature_status='planning', story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'story', 'done', '0.1/alpha/s0')[0], 0)
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('  WARN  story 0.1/alpha/s0', out)
            self.assertIn('two places in this tree disagree', out)

    def test_a_move_breadcrumbs_the_belt_that_closes_it_and_its_checks(self):
        """0.4.0/every-move-breadcrumbs-the-next-step. 0.3.0 built eleven
        features in 64 minutes and spent 93 more reviewing them, because nine
        reviews were batched to the end — and the tool said nothing at the
        moment of each move. Prose in three documents had already failed once
        to stop a builder running wide gates. What holds is what the tool SAYS
        at the moment of the act.
        """
        from agentic_sdlc.repo.conveyor import steps
        with tree(feature_status='ready', story_statuses=('ready',)) as root:
            # in_progress -> the belt that closes THIS grain
            code, out = run_cli(root, 'feature', 'building', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('close feature', out)
            for check in steps.registry_for('feature'):
                self.assertIn(check, out)
            # done -> the belt above it
            code, out = run_cli(root, 'story', 'done', '0.1/alpha/s0')
            self.assertEqual(code, 0, out)
            self.assertIn('close feature', out)
            # a milestone's `done` has no belt above it, and inventing a
            # sentence for that would be the engine having an opinion.
            code, out = run_cli(root, 'milestone', 'done', '0.1')
            self.assertEqual(code, 0, out)
            self.assertNotIn('next:', out)

    def test_every_word_of_a_breadcrumb_is_derived(self):
        """Hard rule 9 is the whole design: the tool never decides what a move
        MEANS or what should happen next, so a breadcrumb ships only if it can
        be traced to `[pm.states.<kind>]` or to `registry_for`. This asserts
        the trace rather than the sentence — a hardcoded next-step passes a
        substring check and fails here."""
        from agentic_sdlc.repo.conveyor import steps
        with tree(feature_status='ready') as root:
            _, out = run_cli(root, 'feature', 'building', '0.1/alpha')
            said = [ln for ln in out.splitlines() if 'next:' in ln][0]
            named = said.split('asks')[1]
            registry = set(steps.registry_for('feature'))
            for word in (w.strip() for w in named.split(',')):
                self.assertIn(word, registry,
                              f'{word!r} is in no belt registry — a breadcrumb '
                              f'that is not derived is an opinion')

    def test_breadcrumbs_false_turns_it_off_in_one_line(self):
        """Rule 6: a consumer parsing output strictly gets one key. Stock is
        ON, because a breadcrumb nobody sees teaches nobody."""
        with tree(feature_status='ready') as root:
            write_config(root, '[pm]\nbreadcrumbs = false\n')
            code, out = run_cli(root, 'feature', 'building', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertNotIn('next:', out)

    def test_a_feature_move_prints_what_it_wrote_and_nothing_else(self):
        """Amended from the case that asserted the advisory (`not finished:
        s0.md(...)`) on every move into `in_progress` — it could not fail once
        the advisory was deleted, so it now proves the deletion: a write
        prints the one line it wrote (story 03), and the stories left behind
        are `check pm`'s WARN, asked of the tree."""
        for to in ('reviewing', 'building'):
            with self.subTest(to=to), \
                    tree(feature_status='ready',
                         story_statuses=('ready', 'building')) as root:
                # STDOUT ONLY, and that is the claim: 0.4.0's conveyor
                # breadcrumb is on stderr precisely so this stays one line.
                code, out = run_cli(root, 'feature', to, '0.1/alpha',
                                    stdout_only=True)
                self.assertEqual(code, 0, out)
                self.assertEqual(out.strip().splitlines(),
                                 [f'[pm] feature 0.1/alpha: ready -> {to}'])
                self.assertEqual(model.field_of(root / FFILE, 'status'), to)

    def test_milestone_done_prints_what_it_wrote_and_the_gate_WARNS(self):
        # The advisory about the features left behind is gone (story 03);
        # D3 asks that question of the tree it left, as a WARN naming both.
        with tree(feature_status='building') as root:
            code, out = run_cli(root, 'milestone', 'done', '0.1')
            self.assertEqual(code, 0, out)
            self.assertEqual(out.strip().splitlines(),
                             ['[pm] milestone 0.1: building -> done'])
            self.assertEqual(model.field_of(root / MFILE, 'status'), 'done')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn("  WARN  milestone 0.1 is 'done' (done) but feature "
                          "0.1/alpha is 'building' (in_progress)", out)


class StatusVerbQuartet(unittest.TestCase):
    """The four shapes every status verb shares, once per grain KIND.

    Every vocabulary state reachable / an out-of-vocabulary target a usage
    error naming the set / the flip an idempotent no-op / an id resolving to
    nothing exit 2. One parameterized home instead of a per-grain mirror; each
    grain's UNIQUE guards stay with their grain — `StatusMoves` keeps the
    round trips to the gate, `BugStatus` the `/bugs/` cross-grain guard and
    nested-id resolution, `FeatureClose` the close protocol.

    `feature done` is deliberately exercised through the full close here (a
    move into the `done` category dispatches to the close — there is no "just
    write the field" spelling), which is why the fixture carries a review
    record and a done story.
    """

    # (kind, grain id, status-file path, initial state, unresolvable id)
    GRAINS = (
        ('story', '0.1/alpha/s0', STORY_REL, 'done', '0.1/alpha/nope'),
        ('bug', '0.1/bugs/seed-is-zero',
         'pm/roadmap/0.1-demo/bugs/seed-is-zero.md', 'open', '0.1/bugs/nope'),
        ('feature', '0.1/alpha', FFILE, 'building', '0.1/nope'),
        ('milestone', '0.1', MFILE, 'building', '9.9'),
    )

    @staticmethod
    def _states(kind: str) -> tuple[str, ...]:
        # The seed's words in their declared order — what `pm init` writes
        # and the fixture tree declares.
        return tuple(st for cat in model.CATEGORIES
                     for st in model.DEFAULT_FLOWS[kind][cat])

    @staticmethod
    @contextlib.contextmanager
    def _grain_tree(kind: str):
        with tree(story_statuses=('done',)) as root:
            if kind == 'bug':
                write(root / 'pm/roadmap/0.1-demo/bugs/seed-is-zero.md',
                      {'id': '0.1/bugs/seed-is-zero', 'milestone': '"0.1"',
                       'status': 'open'})
            yield root

    def test_any_state_in_the_vocabulary_is_reachable(self):
        """Every state a grain may HOLD is one the tool can write, with no
        exceptions left: the 0.24.0 deprecation window was the one carve-out
        (four words the tree could hold and the verbs refused) and it closed
        in 0.2.0. A word in the set the tool refuses would be a state only a
        hand edit could reach."""
        for kind, gid, rel, _, _ in self.GRAINS:
            for state in self._states(kind):
                with self.subTest(kind=kind, state=state), \
                        self._grain_tree(kind) as root:
                    code, out = run_cli(root, kind, state, gid)
                    self.assertEqual(code, 0, out)
                    self.assertEqual(
                        model.field_of(root / rel, 'status'), state)

    def test_a_state_outside_the_vocabulary_is_a_usage_error_naming_the_set(self):
        """The half that IS a fact: `banana` is not a status in any vocabulary,
        and neither is `todo` now that the window has closed — the refusal is
        `model.move_defect`'s, naming the declaration and nothing about a
        replacement. A softened close that kept the old special message would
        keep the four retired words alive in the tool's own help text for
        another release."""
        for word in ('banana', 'todo'):
            for kind, gid, rel, initial, _ in self.GRAINS:
                with self.subTest(kind=kind, word=word), \
                        self._grain_tree(kind) as root:
                    code, out = run_cli(root, kind, word, gid)
                    self.assertEqual(code, 2, out)
                    self.assertIn(f'is not a {kind} state', out)
                    self.assertIn(f'[pm.states.{kind}]', out)
                    self.assertNotIn('replaced it', out)
                    for state in self._states(kind):
                        self.assertIn(state, out)
                    self.assertEqual(model.field_of(root / rel, 'status'),
                                     initial)

    def test_idempotent_noop_succeeds(self):
        for kind, gid, _, initial, _ in self.GRAINS:
            with self.subTest(kind=kind), self._grain_tree(kind) as root:
                code, out = run_cli(root, kind, initial, gid)
                self.assertEqual(code, 0, out)
                self.assertIn('no-op', out)

    def test_unresolvable_id_is_a_usage_error(self):
        for kind, _, _, initial, bad in self.GRAINS:
            with self.subTest(kind=kind), self._grain_tree(kind) as root:
                code, _ = run_cli(root, kind, initial, bad)
                self.assertEqual(code, 2)


class FeatureClose(unittest.TestCase):
    """`pm feature <done-state>` — the close, its report, and its one refusal."""

    def test_the_blast_radius_is_the_file_the_caller_named(self):
        # A command aimed at a feature that rewrites three story files is the
        # tool acting on its own initiative. It reports what it left alone
        # instead, and names the belt that closes a story by name. The
        # `--cascade` that used to move the `reviewing` ones is gone — which
        # stories to move and to what was the engine's opinion about two
        # words — and asking for it is the unknown flag it now is.
        with tree(feature_status='reviewing',
                  story_statuses=('reviewing', 'building')) as root:
            sdir = root / SDIR
            before = {p.name: p.read_bytes() for p in sorted(sdir.iterdir())}
            code, out = run_cli(root, 'feature', 'done', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertEqual(model.field_of(root / FFILE, 'status'), 'done')
            self.assertEqual({p.name: p.read_bytes()
                              for p in sorted(sdir.iterdir())}, before)
            # ...and it does not narrate what it left alone any more (story
            # 03): the close prints the one write it made.
            self.assertNotIn('NOT touched', out)
            self.assertNotIn('s0.md', out)
            code, out = run_cli(root, 'feature', 'done', '0.1/alpha', '--cascade')
            self.assertEqual(code, 2, out)
            self.assertEqual({p.name: p.read_bytes()
                              for p in sorted(sdir.iterdir())}, before)

    def test_the_second_close_writes_nothing_and_says_so(self):
        # Rule 3: the same command twice is a no-op the second time, and it
        # says so; the story advisory it used to repeat is gone (story 03).
        with tree(feature_status='reviewing',
                  story_statuses=('reviewing', 'ready')) as root:
            fdir = root / 'pm/roadmap/0.1-demo/features/alpha'
            self.assertEqual(run_cli(root, 'feature', 'done', '0.1/alpha')[0], 0)
            settled = {p.name: p.read_bytes()
                       for p in sorted((fdir / 'stories').iterdir())}
            feature_settled = (fdir / 'feature.md').read_bytes()
            code, out = run_cli(root, 'feature', 'done', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('already done (no-op)', out)
            self.assertNotIn('s1.md', out)
            self.assertEqual({p.name: p.read_bytes()
                              for p in sorted((fdir / 'stories').iterdir())},
                             settled)
            self.assertEqual((fdir / 'feature.md').read_bytes(), feature_settled)

    def test_any_word_in_the_done_category_is_the_close(self):
        # `obe` is in the seed's `done` list, so `pm feature obe <id>` is a
        # close — it stamps the record and reports the stories — rather than
        # a plain move. The close is the CATEGORY; `done` is one word in it.
        with tree(feature_status='building',
                  story_statuses=('reviewing',)) as root:
            code, out = run_cli(root, 'feature', 'obe', '0.1/alpha',
                                '--review-record', 'docs/reviews/alpha.md')
            self.assertEqual(code, 0, out)
            self.assertEqual(model.field_of(root / FFILE, 'status'), 'obe')
            self.assertIn('reviewed -> docs/reviews/alpha.md', out)

    def test_a_record_pointer_naming_no_file_is_refused_and_writes_nothing(self):
        """The half that IS a fact, and the one D1 reports afterwards: a
        pointer that resolves to nothing. Refused WHOLE — no stale stamp, no
        story touched.

        Three routes to the same refusal, because each one was a separate
        hole: the ordinary close; the NO-OP branch, which stamped `reviewed:`
        without ever asking whether the path named a file; and a dangling
        symlink, where a pointer outlived what it pointed at and the judgement
        raised instead of refusing.
        """
        rows = (
            ('a fresh close', dict(feature_status='reviewing',
                                   story_statuses=('reviewing',)),
             'docs/reviews/never-written.md', None),
            ('the no-op branch', dict(feature_status='done',
                                      story_statuses=('done',)),
             'docs/reviews/never.md', None),
            ('a dangling symlink', dict(feature_status='reviewing',
                                        story_statuses=('reviewing',)),
             'pm/roadmap/0.1-demo/features/alpha/gone.md', 'gone.md'),
        )
        for name, kwargs, pointer, symlink in rows:
            with self.subTest(route=name), \
                    tree(with_record=False, **kwargs) as root:
                if symlink:
                    (root / 'pm/roadmap/0.1-demo/features/alpha'
                     / symlink).symlink_to('nowhere.md')
                ff, story = root / FFILE, root / STORY_REL
                before, sbefore = ff.read_text(), story.read_text()
                code, out = run_cli(root, 'feature', 'done', '0.1/alpha',
                                    '--review-record', pointer)
                self.assertEqual(code, 1, out)
                self.assertIn('names no file', out)
                self.assertEqual(ff.read_text(), before)
                self.assertEqual(story.read_text(), sbefore)

    def test_a_record_that_resolves_closes_the_feature_and_so_does_none_at_all(self):
        # "You have not written a review record yet" is an opinion about how a
        # person works. The verb says what it saw and does what it was asked.
        # And the byte floor is gone: `review_min_content_bytes = 20` refused
        # this exact fifteen-byte string, and whether a one-line close is
        # enough review was never a fact about the tree.
        with tree(feature_status='reviewing', story_statuses=('reviewing',),
                  with_record=False) as root:
            code, out = run_cli(root, 'feature', 'done', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('no review record', out)
            self.assertEqual(model.field_of(root / FFILE, 'status'), 'done')

        with tree(feature_status='reviewing', story_statuses=('reviewing',),
                  with_record=False) as root:
            record = root / 'docs' / 'reviews' / 'f.md'
            record.parent.mkdir(parents=True)
            record.write_text('LGTM. Ship it.', encoding='utf-8')
            code, out = run_cli(root, 'feature', 'done', '0.1/alpha',
                                '--review-record', 'docs/reviews/f.md')
            self.assertEqual(code, 0, out)
            self.assertEqual(model.field_of(root / FFILE, 'status'), 'done')


class ListFindsTheNail(unittest.TestCase):
    """`pm list` — a filter over facts, and nothing else.

    Measured on one consumer: `pm status` prints 165 lines, and the answer to
    "what is open right now" was 2 stories. `pm list --status building,reviewing`
    prints those 2.

    There is deliberately no `pm next`. A verb that picks THE next thing is the
    tool having an opinion about your priorities, which is what this release
    removes everywhere else.
    """

    @staticmethod
    def _rows(out: str) -> list[list[str]]:
        return [line.split('\t') for line in out.strip().split('\n')
                if '\t' in line]

    def _tree(self):
        return tree(story_statuses=('ready', 'building', 'obe', 'done'))

    def test_every_story_one_tab_separated_row_and_every_filter_narrows(self):
        with self._tree() as root:
            code, out = run_cli(root, 'list')
            self.assertEqual(code, 0, out)
            rows = self._rows(out)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0][0], '0.1/alpha/s0')
            self.assertEqual(rows[0][1], 'ready')
            self.assertEqual(rows[0][3], '0.1/alpha')

            code, out = run_cli(root, 'list', '--status', 'building,obe')
            self.assertEqual(code, 0, out)
            self.assertEqual([r[1] for r in self._rows(out)],
                             ['building', 'obe'])
            self.assertIn('2 of 4 story/ies', out)

            # `--category` asks the same question every other reader asks —
            # `obe` is finished — so the two `done`-category stories are one
            # answer, and a word the project never declared is exit 2 rather
            # than an empty match (a typo'd filter must not read as "nothing
            # is open").
            code, out = run_cli(root, 'list', '--category', 'done')
            self.assertEqual(code, 0, out)
            self.assertEqual([r[1] for r in self._rows(out)], ['obe', 'done'])
            code, out = run_cli(root, 'list', '--category', 'finished')
            self.assertEqual(code, 2, out)
            self.assertIn('todo in_progress done', out)
            code, out = run_cli(root, 'list', '--status', 'reviewing')
            self.assertEqual(code, 2, out)
            self.assertIn('[pm.states.story]', out)

            self.assertEqual(
                run_cli(root, 'set', '0.1/alpha/s1', 'owner', 'ada')[0], 0)
            code, out = run_cli(root, 'list', '--owner', 'ada')
            self.assertEqual(code, 0, out)
            self.assertEqual([r[2] for r in self._rows(out)], ['ada'])

    def test_a_tab_inside_a_name_cannot_forge_a_column(self):
        """`name` is free text a human typed, and a tab in it would shift every
        field after it — a forged column is worse than a substituted space,
        because the consumer reads a wrong value rather than a short row. The
        `--json` payload keeps the byte; only the tab-separated form
        substitutes."""
        with tree() as root:
            model.set_field(root / MFILE, 'name', 'Two\tParts')
            code, plain = run_cli(root, 'list', '--kind', 'milestone')
            self.assertEqual(code, 0, plain)
            self.assertEqual(len(self._rows(plain)[0]), 5)
            self.assertEqual(self._rows(plain)[0][4], 'Two Parts')
            code, as_json = run_cli(root, 'list', '--kind', 'milestone',
                                    '--json')
            self.assertEqual(json.loads(as_json.strip().split('\n')[0])[0]
                             ['name'], 'Two\tParts')

    def test_json_carries_exactly_the_fields_the_columns_carry(self):
        """The one thing that could diverge unseen. Columns and `--json` are
        two views of one tuple, and a payload that grew a field the columns
        lack — or lost one they have — is discovered by a consumer at the
        worst possible moment.

        Asserted as a ROUND TRIP against the tab-separated rows, both kinds,
        so it fails whichever side moves. `LIST_COLUMNS` is read rather than
        restated: a roster copied into a test goes stale exactly the way the
        thing it guards does.
        """
        from agentic_sdlc.repo.pm.cli import LIST_COLUMNS
        with tree(milestone_status='building') as root:
            model.set_field(root / MFILE, 'branch', 'milestone/0.1')
            for kind in ('story', 'milestone'):
                argv = ('list', '--kind', kind)
                code, plain = run_cli(root, *argv)
                self.assertEqual(code, 0, plain)
                code, as_json = run_cli(root, *argv, '--json')
                self.assertEqual(code, 0, as_json)
                payload = json.loads(as_json.strip().split('\n')[0])
                columns = LIST_COLUMNS[kind]
                self.assertEqual([list(row) for row in payload],
                                 [list(columns) for _ in payload],
                                 f'{kind}: --json keys are not the columns')
                self.assertTrue(payload, f'{kind}: nothing listed, so the '
                                         f'round trip proved nothing')
                self.assertEqual([[row[c] for c in columns] for row in payload],
                                 self._rows(plain),
                                 f'{kind}: --json values are not the row cells')

    def test_kind_milestone_lists_every_milestone_with_its_category_and_branch(self):
        """`--kind milestone` is what a SCRIPT asks instead of grepping
        `status: building` out of milestone.md — the worktree tool did exactly
        that and stopped matching the day a project renamed the word. FIVE
        columns always, `-` for an absent one, so a shell `read` never
        misaligns; `--category` filters on the category, whatever the word.

        The `name` column joined in 0.4.0/the-read-verbs-compose: a read verb
        that omits the field people filter on teaches them the tool cannot
        filter, and `pm list | grep '<some name>'` returned nothing."""
        with tree(milestone_status='building') as root:
            mfile = root / MFILE
            model.set_field(mfile, 'branch', 'milestone/0.1')
            write(root / 'pm/roadmap/0.2-later/milestone.md',
                  {'id': '"0.2"', 'name': 'Later', 'status': 'planning'})
            code, out = run_cli(root, 'list', '--kind', 'milestone')
            self.assertEqual(code, 0, out)
            self.assertEqual(self._rows(out), [
                ['0.1', 'building', 'in_progress', 'milestone/0.1', 'Demo'],
                ['0.2', 'planning', 'todo', '-', 'Later']])
            self.assertIn('2 of 2 milestone(s)', out)
            code, out = run_cli(root, 'list', '--kind', 'milestone',
                                '--category', 'in_progress')
            self.assertEqual(code, 0, out)
            self.assertEqual([r[0] for r in self._rows(out)], ['0.1'])
            self.assertIn('1 of 2 milestone(s)', out)
            # The story filters do not apply, and a kind this verb does not
            # list names the two it does.
            code, out = run_cli(root, 'list', '--kind', 'milestone',
                                '--owner', 'ada')
            self.assertEqual(code, 2, out)
            code, out = run_cli(root, 'list', '--kind', 'bug')
            self.assertEqual(code, 2, out)
            self.assertIn('story or milestone', out)

    def test_the_milestone_filter_selects_and_names_its_set(self):
        # `--milestone 0.2` on a tree holding only 0.1 printed `0 of 0` at exit
        # 0 — indistinguishable from a milestone whose stories are all gone,
        # and from a wrong `roadmap_dir`. Milestone ids are enumerable, so the
        # set gets named exactly the way `--status wombat` already names its
        # set.
        with self._tree() as root:
            write(root / 'pm/roadmap/0.2-later/milestone.md',
                  {'id': '"0.2"', 'name': 'Later', 'status': 'planning'})
            write(root / 'pm/roadmap/0.2-later/features/beta/feature.md',
                  {'id': '0.2/beta', 'milestone': '"0.2"', 'name': 'Beta',
                   'status': 'planning'})
            write(root / 'pm/roadmap/0.2-later/features/beta/stories/b0.md',
                  {'id': '0.2/beta/b0', 'feature': '0.2/beta',
                   'milestone': '"0.2"', 'name': 'B0', 'status': 'ready'})
            code, out = run_cli(root, 'list', '--milestone', '0.2')
            self.assertEqual(code, 0, out)
            self.assertEqual([r[0] for r in self._rows(out)], ['0.2/beta/b0'])

        with self._tree() as root:
            code, out = run_cli(root, 'list', '--milestone', '0.2')
            self.assertEqual(code, 2, out)
            self.assertIn('--milestone names', out)
            self.assertIn('0.1', out)
            code, out = run_cli(root, 'list', '--status', 'butterfly')
            self.assertEqual(code, 2, out)
            self.assertIn('is not a story state', out)

    def test_matching_nothing_and_scanning_nothing_look_different(self):
        # Rule 4, on a read verb: 0 rows out of 4 stories is an answer; 0 rows
        # out of 0 is a wrong `roadmap_dir`, and the census says which.
        with self._tree() as root:
            _, out = run_cli(root, 'list', '--owner', 'nobody')
            self.assertEqual(self._rows(out), [])
            self.assertIn('0 of 4 story/ies', out)
        with tree(story_statuses=()) as root:
            _, out = run_cli(root, 'list')
            self.assertIn('0 of 0 story/ies', out)

    def test_an_empty_tree_says_so_rather_than_naming_an_empty_set(self):
        # Rule 4: refusing against a census of ZERO milestones must not read as
        # "you typo'd" when the truth is "nothing was scanned".
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            (root / 'pm' / 'roadmap').mkdir(parents=True)
            # DECLARES ITS FLOW: `[pm.states.*]` has no runtime fallback
            # (model.py:718), so this ad-hoc tree needs it for the same
            # reason `support.pm.tree` does.
            write_config(root)
            (root / '.git').mkdir(exist_ok=True)  # a MARKER: `repo_root` walks for it
            previous = Path.cwd()
            os.chdir(root)
            try:
                code, out = run_cli(root, 'list', '--milestone', '0.1')
            finally:
                os.chdir(previous)
            self.assertEqual(code, 2, out)
            self.assertIn('no milestone at all', out)


class StatusReport(unittest.TestCase):
    def test_phases_group_numeric_then_named_then_unphased(self):
        # `seam` is a NAME the project chose, not a word the engine knows: it
        # sorts where any named phase does, after the numbered ones. The
        # engine used to spell `seam` in two places (here and the execution
        # list) and sort it specially — an opinion about a project's phase
        # vocabulary, struck by the inference census.
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'new', 'feature', '0.1', 'b', 'B')
            run_cli(root, 'new', 'feature', '0.1', 'c', 'C')
            fdir = root / 'pm/roadmap/0.1-demo/features'
            model.set_field(fdir / 'alpha' / 'feature.md', 'phase', '2')
            model.set_field(fdir / 'b' / 'feature.md', 'phase', 'seam')
            # 'c' stays unphased on purpose.
            _, out = run_cli(root, 'status')
            order = [ln for ln in out.splitlines() if ln.startswith('  --')]
            self.assertEqual(
                order, ['  -- phase 2 (0/1 done)', '  -- seam (0/1 done)',
                        '  -- unphased (0/1 done)'])


class WriteFidelity(unittest.TestCase):
    """Rule 3 — a write verb touches only what it was asked to touch."""

    def test_the_only_bytes_that_change_are_the_ones_asked_for(self):
        # CRLF is the one every editor on Windows produces. The exotic set is
        # the one `str.splitlines()` breaks on — U+2028, form feed and a lone
        # CR — where joining back on '\n' would rewrite all three. Compare
        # BYTES: `read_text()` does its own newline translation and would hide
        # exactly this defect.
        cases = (
            ('crlf', b'---\r\nid: a\r\nstatus: ready\r\n---\r\n\r\nbody\r\n'),
            ('exotic', '---\nid: a\nstatus: ready\n---\n\n'
                       'A B\npage\x0cbreak\ncr-only\rtail\n'.encode()),
        )
        for name, raw in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / 'g.md'
                p.write_bytes(raw)
                self.assertTrue(model.set_field(p, 'status', 'building'))
                self.assertEqual(p.read_bytes(),
                                 raw.replace(b'status: ready',
                                             b'status: building'))

    def test_an_unwritable_file_reports_failure_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'g.md'
            write(p, {'id': 'a', 'status': 'ready'})
            p.chmod(0o444)
            try:
                self.assertFalse(model.set_field(p, 'status', 'building'))
            finally:
                p.chmod(0o644)

class IdsAreLiterals(unittest.TestCase):
    """One case showing the refusal ARRIVES. The grammar's own matrix —
    traversal, empty and dot segments, backslashes, schemes, length — lives
    with `model.segment_is_literal`, per SDLC.md §5."""

    def test_a_glob_never_resolves_to_a_grain(self):
        with tree() as root:
            for bad in ('*', '0.1/*'):
                with self.subTest(bad=bad):
                    self.assertEqual(run_cli(root, 'milestone', 'ready', bad)[0], 2)


def _phased(root: Path, slug: str, phase: str, deps: list[str]) -> None:
    """One feature under 0.1 with a `phase:` and a `depends_on:` list."""
    write(root / f'pm/roadmap/0.1-demo/features/{slug}/feature.md',
          {'id': f'0.1/{slug}', 'milestone': '"0.1"', 'name': slug.title(),
           'status': 'planning', 'phase': phase,
           'depends_on': '[' + ', '.join(f'"{d}"' for d in deps) + ']'})


class PhaseIsABucketNotAConstraint(unittest.TestCase):
    """V5b is gone. A cycle is a fact; a bucket disagreeing with the graph is not.

    "A feature may not depend on one in a LATER phase" fired on `seam` — a
    vocabulary this tool invented, defined as neither blocking nor blocked, and
    then reported for sitting in a dependency chain. `phase:` groups the board
    for `pm status`; the dependency graph orders the work. They are allowed to
    be two different readings of the same tree. (V5a, the cycle, is proven in
    tests/test_pm_gate.py `Validate`.)
    """

    def test_a_phase_may_depend_on_a_later_or_unordered_one(self):
        for other_phase in ('5', 'seam'):
            with self.subTest(phase=other_phase), tree() as root:
                _phased(root, 'alpha', '2', ['0.1/beta'])
                _phased(root, 'beta', other_phase, [])
                code, out = run_cli(root, 'validate')
                self.assertEqual(code, 0, out)


class FieldMutation(unittest.TestCase):
    def test_set_and_get_round_trip_on_any_field_and_any_grain(self):
        # `status` is refused here — not for the "transition graph" the old
        # refusal cited (there is none) but because a status is a MOVE: the
        # status verbs ask `move_defect` and stamp a ledger row, and `set`
        # does neither, so `set … status wombat` was a write that looked
        # legitimate and was not (V2 of the feature review). The refusal
        # names the verb that does it right, and the grain is untouched.
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'new', 'bug', '0.1', 'oops')
            for gid in ('0.1', '0.1/alpha', '0.1/alpha/s0', '0.1/bugs/oops'):
                with self.subTest(gid=gid):
                    self.assertEqual(run_cli(root, 'set', gid, 'labels', '[]')[0], 0)
            self.assertEqual(
                run_cli(root, 'set', '0.1/alpha/s0', 'estimate', '3d')[0], 0)
            code, out = run_cli(root, 'get', '0.1/alpha/s0', 'estimate')
            self.assertEqual(code, 0)
            self.assertIn('3d', out)
            sf = root / STORY_REL
            before = sf.read_bytes()
            rows = ledger_lines(root)
            for gid, word, verb in (('0.1/alpha/s0', 'wombat', 'story'),
                                    ('0.1/alpha/s0', 'done', 'story'),
                                    ('0.1/alpha', 'building', 'feature'),
                                    ('0.1', 'ready', 'milestone'),
                                    ('0.1/bugs/oops', 'fixed', 'bug')):
                with self.subTest(gid=gid, word=word):
                    code, out = run_cli(root, 'set', gid, 'status', word)
                    self.assertEqual(code, 2, out)
                    self.assertIn(f'pm {verb} {word} {gid}', out)
                    self.assertIn('stamps the ledger', out)
            self.assertEqual(sf.read_bytes(), before)
            self.assertEqual(ledger_lines(root), rows)   # refused: no row

    def test_set_moves_owner_in_both_directions(self):
        # `claim`/`release` were fourteen lines calling this with the key
        # hardcoded. One verb, and `owner` is not special among fields — the
        # empty value has to CLEAR rather than be refused as missing.
        with tree(story_statuses=('ready',)) as root:
            sf = root / STORY_REL
            self.assertEqual(
                run_cli(root, 'set', '0.1/alpha/s0', 'owner', 'dev-1')[0], 0)
            self.assertEqual(model.field_of(sf, 'owner'), 'dev-1')
            self.assertEqual(
                run_cli(root, 'set', '0.1/alpha/s0', 'owner', '')[0], 0)
            self.assertEqual(model.field_of(sf, 'owner'), '')

    def test_set_replaces_or_inserts_and_changes_nothing_else(self):
        with tree() as root:
            ff = root / FFILE
            before = ff.read_bytes()
            run_cli(root, 'set', '0.1/alpha', 'name', 'Renamed')
            self.assertEqual(ff.read_bytes(),
                             before.replace(b'name: Alpha', b'name: Renamed'))
            lines = ff.read_text().splitlines()
            run_cli(root, 'set', '0.1/alpha', 'risk', 'high')
            after = ff.read_text().splitlines()
            self.assertEqual(len(after), len(lines) + 1)
            self.assertIn('risk: high', after)
            self.assertEqual([ln for ln in after if ln != 'risk: high'], lines)


class ExecutionList(unittest.TestCase):
    def _validate(self, root):
        from agentic_sdlc.repo.pm import validate
        # V6 renders the list, and a rendered row counts stories in `done` —
        # a category question, so the config has to carry the flow.
        return validate.run(cfg_for(root))

    def test_sync_writes_a_block_and_validate_then_passes(self):
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'sync')[0], 0)
            mfile = root / MFILE
            self.assertIn('pm:execution', mfile.read_text())
            self.assertEqual(self._validate(root)[0], [])

    def test_a_tree_with_no_block_is_not_stale(self):
        # The list is opt-in per file; absence is not staleness, or the gate
        # would go red on every tree that never asked for the feature.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(self._validate(root)[0], [])
            self.assertEqual(run_cli(root, 'sync', '--check')[0], 0)

    def test_v6_is_demoted_from_the_gate_but_still_answers_when_asked(self):
        # Demoted, not deleted. A generated VIEW going stale while ordinary
        # work moves the tree is not a defect in the tree, and reddening a
        # commit gate over it makes the ordinary case the exceptional one.
        with tree(story_statuses=('ready',)) as root:
            run_cli(root, 'sync')
            run_cli(root, 'new', 'feature', '0.1', 'newcomer', 'Newcomer')
            self.assertTrue(any('stale' in f for f in self._validate(root)[0]))
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('stale', out)
            # ...but `pm sync --check` answers, and naming V6 puts it back on
            # the gate.
            self.assertEqual(run_cli(root, 'sync', '--check')[0], 1)
            write_config(root, '[pm]\nchecks = ["V6"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('execution list is stale', out)
            # ...and a re-sync settles it.
            write_config(root)
            run_cli(root, 'sync')
            self.assertEqual(run_cli(root, 'sync', '--check')[0], 0)
        self.assertNotIn('V6', model.DEFAULT_CHECKS)
        self.assertIn('V6', model.KNOWN_CHECKS)

    def test_order_follows_dependencies_then_name(self):
        with tree() as root:
            for slug in ('aaa', 'zzz'):
                run_cli(root, 'new', 'feature', '0.1', slug, slug.upper())
            fdir = root / 'pm/roadmap/0.1-demo/features'
            # aaa sorts first by name but depends on zzz, so zzz must lead.
            model.set_field(fdir / 'aaa/feature.md', 'depends_on', '["0.1/zzz"]')
            run_cli(root, 'sync')
            block = (root / MFILE).read_text()
            self.assertLess(block.index('`zzz`'), block.index('`aaa`'))
            self.assertIn('after zzz', block)

    def test_sync_is_idempotent_and_preserves_the_rest_of_the_file(self):
        with tree(story_statuses=('ready',)) as root:
            mfile = root / MFILE
            mfile.write_text(mfile.read_text() + '\n## Notes\n\nkeep me\n',
                             encoding='utf-8')
            run_cli(root, 'sync')
            once = mfile.read_bytes()
            run_cli(root, 'sync')
            self.assertEqual(mfile.read_bytes(), once)
            self.assertIn('keep me', mfile.read_text())


class AStatusVerbIsTheREPAIRForWhatD4Reports(unittest.TestCase):
    """The verb validates the state it was ASKED for. Never the one it found.

    Reproduced on a hand-edited tree: `check pm` reported
    `milestone 0.1: status 'wombat' not in (planning ready building done)`,
    and `pm milestone done 0.1` answered
    `ERROR — milestone '0.1' has an unknown current status 'wombat'` and wrote
    nothing. The gate diagnosed the breakage and the verb declined to repair
    it, leaving the editor as the only way out — which is the one thing this
    tool exists to spare a person.

    The current value is read FOR THE MESSAGE. `wombat -> done`. (That the
    REQUESTED state is still closed is `StatusVerbQuartet`'s row.)
    """

    NONSENSE = {'milestone': (MFILE, '0.1', 'wombat'),
                'feature': (FFILE, '0.1/alpha', 'hedgehog'),
                'story': (STORY_REL, '0.1/alpha/s0', 'butterfly')}

    def _mangle(self, root: Path, rel: str, value: str) -> Path:
        path = root / rel
        text = path.read_text(encoding='utf-8')
        line = next(l for l in text.split('\n') if l.startswith('status:'))
        path.write_text(text.replace(line, f'status: {value}'), encoding='utf-8')
        return path

    def test_every_grain_kind_is_repairable_from_nonsense(self):
        for grain, (rel, gid, junk) in self.NONSENSE.items():
            # A milestone close still asks its features to be done (that
            # precondition is a separate question); the fixture satisfies it so
            # this case isolates the one being asked here.
            kw = ({'feature_status': 'done', 'story_statuses': ('done',)}
                  if grain == 'milestone' else {'story_statuses': ('ready',)})
            with self.subTest(grain=grain), tree(**kw) as root:
                path = self._mangle(root, rel, junk)
                # The gate reports it...
                code, out = run_gate(root)
                self.assertEqual(code, 1, out)
                self.assertIn(junk, out)
                # ...and the verb fixes it, naming what it found.
                code, out = run_cli(root, grain, 'done', gid)
                self.assertEqual(code, 0, out)
                self.assertIn(f'{junk} -> done', out)
                self.assertEqual(model.field_of(path, 'status'), 'done')

    def test_an_absent_status_key_reads_as_none_and_is_still_settable(self):
        with tree(story_statuses=('ready',)) as root:
            path = root / STORY_REL
            path.write_text(
                '\n'.join(l for l in path.read_text(encoding='utf-8').split('\n')
                          if not l.startswith('status:')), encoding='utf-8')
            code, out = run_cli(root, 'story', 'building', '0.1/alpha/s0')
            self.assertEqual(code, 0, out)
            self.assertIn('(none) -> building', out)
            self.assertEqual(model.field_of(path, 'status'), 'building')


class TheShortestPathFromNothingToAClosedMilestone(unittest.TestCase):
    """Six commands, and every one of them writes something.

    Measured on the graph this replaced: an empty repo to one closed milestone
    was 14 commands, six of them pure ceremony — `milestone ready`,
    `milestone building`, `feature ready`, `feature building`, `feature review`
    and a `story wip` nobody wanted — each existing only because an edge
    demanded it, and each reachable by `sed` anyway.
    """

    def test_it_is_six_commands_and_they_all_land(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            root.mkdir()
            (root / 'docs' / 'reviews').mkdir(parents=True)
            (root / 'docs' / 'reviews' / 'alpha.md').write_text(
                'Reviewed, and it holds up under the cases that matter.\n',
                encoding='utf-8')
            # DECLARES ITS FLOW: `[pm.states.*]` has no runtime fallback
            # (model.py:718), so this ad-hoc tree needs it for the same
            # reason `support.pm.tree` does.
            write_config(root)
            (root / '.git').mkdir(exist_ok=True)  # a MARKER: `repo_root` walks for it
            previous = Path.cwd()
            os.chdir(root)
            try:
                sequence = (
                    ('new', 'milestone', '0.1', 'Demo'),
                    ('new', 'feature', '0.1', 'alpha', 'Alpha'),
                    ('new', 'story', '0.1/alpha', 's0', 'S0'),
                    ('story', 'done', '0.1/alpha/s0'),
                    ('feature', 'done', '0.1/alpha',
                     '--review-record', 'docs/reviews/alpha.md'),
                    ('milestone', 'done', '0.1'),
                )
                for argv in sequence:
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 0, f'{argv}\n{out}')
                self.assertEqual(len(sequence), 6)
                code, out = run_gate(root)
            finally:
                os.chdir(previous)
            self.assertEqual(code, 0, out)


class Vocabulary(unittest.TestCase):
    """`pm vocabulary --json` prints the CLOSED SETS, and no longer prints edges.

    Its audience is the pin bump: this toolkit ships a shape, a project bumps
    its pin, and then has to see what changed. The set of states a grain may
    hold and the set of rule ids `[pm] checks` may name are what changed, so
    they have to be readable from the tool rather than scraped from a
    changelog — which is also why this verb keeps running when `[pm] checks`
    names an id the release retired.

    What has NOT come back is an edge table, and the step-to-state table one
    build carried is refused by name now. The flow half is proven in
    tests/test_pm_flow.py; this keeps the pin-bump surface.
    """

    def test_json_states_the_closed_sets_the_project_declared_and_no_edges(self):
        import json
        with tree() as root:
            code, out = run_cli(root, 'vocabulary', '--json')
            self.assertEqual(code, 0, out)
            data = json.loads(out)
            self.assertEqual(data['grains']['story']['states'],
                             ['planning', 'ready', 'building', 'done', 'obe'])
            self.assertEqual(data['grains']['milestone']['states'],
                             list(model.LIFECYCLE) + ['obe'])
            self.assertEqual(data['grains']['bug']['states'],
                             ['open', 'fixed', 'closed'])
            self.assertEqual(data['checks'], list(model.KNOWN_CHECKS))
            # A grain carries its closed SET and its declared FLOW, and nothing
            # else. `deprecated` may not come back: it was the 0.24.0 rename
            # map, and that window closed in 0.2.0.
            for grain in data['grains'].values():
                self.assertEqual(sorted(grain), ['flow', 'states'])
            # This tree DECLARES its flow (tests/support/pm.py `FLOW_TOML`),
            # so the payload carries it. The ABSENCE half — `flow_declared:
            # false` and a null `flow` — is proven in tests/test_pm_flow.py.
            self.assertIs(data['flow_declared'], True)
            self.assertEqual(data['grains']['milestone']['flow']['order'],
                             list(model.LIFECYCLE) + ['obe'])
            self.assertNotIn('->', out)
            self.assertNotIn('transitions', out)

            # ...and it is the PROJECT's vocabulary, never the stock one.
            write_config(root, declaring(story={
                'todo': ('todo',), 'in_progress': ('wip', 'review', 'parked'),
                'done': ('done',)}))
            code, out = run_cli(root, 'vocabulary', '--json')
            self.assertEqual(code, 0, out)
            self.assertIn('parked', json.loads(out)['grains']['story']['states'])


class StoryResolution(unittest.TestCase):
    """`story_file` and `story_files` must agree about what a story IS.

    They did not: the gate walk went recursive while the ID RESOLVER still
    globbed one directory level, so a story at `stories/parked/s2.md` was
    reported by `check pm` and then refused by `pm story building <id>` as a
    story that does not exist. Each answer is defensible alone; together they
    leave the author nothing to do.
    """

    FDIR = 'pm/roadmap/0.1-demo/features/alpha'

    def _story(self, root: Path, rel: str, sid: str) -> Path:
        p = root / self.FDIR / 'stories' / rel
        write(p, {'id': sid, 'feature': '0.1/alpha', 'milestone': '"0.1"',
                  'name': 'S', 'status': 'ready'})
        return p

    def test_a_story_the_gate_can_see_is_a_story_the_verb_can_address(self):
        with tree() as root:
            self._story(root, 'parked/s2.md', '0.1/alpha/s2')
            _, gate = run_gate(root)
            self.assertIn('2 story/ies', gate)
            self.assertIsNotNone(model.story_file(cfg_for(root), '0.1/alpha/s2'))
            code, out = run_cli(root, 'story', 'building', '0.1/alpha/s2')
            self.assertEqual(code, 0, out)
            self.assertEqual(
                model.field_of(root / self.FDIR / 'stories/parked/s2.md',
                               'status'), 'building')

    @unittest.skipUnless(CASE_SENSITIVE_TMP, 'case-insensitive filesystem')
    def test_an_uppercase_extension_resolves(self):
        with tree() as root:
            self._story(root, 'S3.MD', '0.1/alpha/S3')
            self.assertEqual(model.story_file(cfg_for(root), '0.1/alpha/S3').name,
                             'S3.MD')

    def test_the_ordinal_prefix_never_makes_a_story_ambiguous(self):
        # `story_ordinal_prefix` trees carry `07-s9.md` beside `s9.md`; an
        # exact stem wins, and a prefixed file one directory down still
        # resolves. Two files that genuinely claim ONE id refuse rather than
        # pick — a resolver that picked would write into whichever the glob
        # happened to yield first.
        with tree() as root:
            cfg = model.PmConfig(root=root, story_ordinal_prefix=True)
            self._story(root, 's9.md', '0.1/alpha/s9')
            self._story(root, '07-s9.md', '0.1/alpha/s9')
            self.assertEqual(model.story_file(cfg, '0.1/alpha/s9').name, 's9.md')
            self._story(root, 'parked/03-s4.md', '0.1/alpha/s4')
            self.assertEqual(model.story_file(cfg, '0.1/alpha/s4').name,
                             '03-s4.md')
        with tree() as root:
            self._story(root, 'dup.md', '0.1/alpha/dup')
            self._story(root, 'parked/dup.md', '0.1/alpha/dup')
            with self.assertRaises(model.AmbiguousStory):
                model.story_file(cfg_for(root), '0.1/alpha/dup')

    def test_a_note_beside_the_stories_is_not_addressable_as_one(self):
        # The same definition the walk uses: a grain IS its frontmatter, so a
        # README parked in `stories/` is not a story with an empty status.
        with tree() as root:
            (root / self.FDIR / 'stories/README.md').write_text(
                '# how stories are written here\n', encoding='utf-8')
            self.assertIsNone(model.story_file(cfg_for(root), '0.1/alpha/README'))


class OrdinalPrefix(unittest.TestCase):
    """`story_ordinal_prefix` must TEACH V2 the prefix, never switch V2 off.

    Skipping instead of stripping left every story in such a tree unchecked
    while the gate printed VALID — under the configuration the docs mandate.
    """

    def test_the_prefix_is_stripped_for_V2_and_V2_still_runs(self):
        from agentic_sdlc.repo.pm import validate

        def check(sid: str, prefix: bool):
            with tree(story_statuses=()) as root:
                write(root / 'pm/roadmap/0.1-demo/features/alpha/stories/01-boots.md',
                      {'id': sid, 'feature': '0.1/alpha', 'milestone': '"0.1"',
                       'name': 'B', 'status': 'ready'})
                return validate.run(model.PmConfig(
                    root=root, story_ordinal_prefix=prefix))[0]

        self.assertEqual(check('0.1/alpha/boots', True), [])
        # The regression: this used to pass because the whole arm was skipped.
        for sid, prefix in (('TOTAL/GARBAGE/nonsense', True),
                            ('0.1/alpha/boots', False)):
            with self.subTest(id=sid, prefix=prefix):
                findings = check(sid, prefix)
                self.assertTrue(
                    any('does not match its path' in f for f in findings),
                    findings)


class Decide(unittest.TestCase):
    """`pm decide` — one dated, ordinal-stamped heading, and nothing else.

    The two things an author writing this by hand gets wrong are the date and
    the ordinal, so the verb stamps both. It imposes no field schema: the
    four-field one this replaced produced zero conforming entries across a
    consumer's 158 decision logs.
    """

    MDIR = 'pm/roadmap/0.1-demo'

    def _scaffolded(self, root: Path) -> None:
        self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
        self.assertEqual(run_cli(root, 'new', 'feature', '0.1', 'alpha')[0], 0)

    def _log(self, root: Path, rel: str = '') -> str:
        return (root / self.MDIR / (rel or 'decisions.md')).read_text(
            encoding='utf-8')

    def test_the_log_is_minted_on_the_FIRST_decision_and_not_before(self):
        # The whole cut. `pm new` scaffolded an empty decisions.md into every
        # grain — 204 files, ~1,900 lines, a quarter of one consumer's PM tree,
        # minted by the verb that exists to stop sprawl. It appears when there
        # is something in it, stamped with today's date and the first ordinal.
        with tree() as root:
            self._scaffolded(root)
            log = root / self.MDIR / 'decisions.md'
            self.assertFalse(log.exists())
            code, out = run_cli(root, 'decide', '0.1', 'the sweep verb moves')
            self.assertEqual(code, 0, out)
            self.assertTrue(log.is_file())
            body = log.read_text(encoding='utf-8')
            # Minted from the template, header and all — a bare heading with no
            # instruction line is what D13 reports.
            self.assertTrue(body.startswith(model.SLOT_HEADER['decisions.md']))
            today = datetime.now(timezone.utc).date().isoformat()
            self.assertIn(f'## D1 — {today} — the sweep verb moves', body)

    def test_a_refused_decision_mints_nothing_and_touches_no_existing_log(self):
        # Refuses WHOLE: the mint and the append are one write, so a refusal
        # cannot leave an empty log behind — which would be the sprawl again,
        # arriving by the error path.
        with tree() as root:
            self._scaffolded(root)
            code, out = run_cli(root, 'decide', '0.1')
            self.assertEqual(code, 2, out)
            self.assertFalse((root / self.MDIR / 'decisions.md').exists())
            self.assertEqual(run_cli(root, 'decide', '0.1', 'a choice')[0], 0)
            before = self._log(root)
            code, out = run_cli(root, 'decide', '0.1')
            self.assertEqual(code, 2, out)
            self.assertEqual(self._log(root), before)

    def test_the_ordinal_advances_with_the_prefix_the_log_already_uses(self):
        # A second D1 in one log is invisible until somebody cites it, and a
        # tree numbering `M27` keeps numbering `M` — falling back to `D` would
        # put two numbering schemes in one file.
        with tree() as root:
            self._scaffolded(root)
            for n in range(3):
                self.assertEqual(
                    run_cli(root, 'decide', '0.1', f'choice {n}')[0], 0)
            body = self._log(root)
            for eid in ('## D1 ', '## D2 ', '## D3 '):
                self.assertIn(eid, body)
            log = root / self.MDIR / 'decisions.md'
            model.write_raw(log, f'{model.SLOT_HEADER["decisions.md"]}\n\n'
                                 f'## M27 — 2026-01-01 — an older choice\n')
            self.assertEqual(run_cli(root, 'decide', '0.1', 'the next one')[0], 0)
            self.assertIn('## M28 — ', self._log(root))

    def test_the_prose_under_a_heading_is_never_touched(self):
        """The log after is the log before plus ONE heading, byte for byte.

        Probed 2026-09-06 (0.2.0/the-proof-is-named-in-the-criterion): with
        this test asserting only `hand.strip() in body`, a `decide` that
        normalised CRLF to LF, or stripped trailing whitespace off every
        existing line, still passed — the prose was "in" the body, rewritten.
        That is rule 3's line-ending clause and rule 4's write-side sin, so
        the fixture now carries both hazards (CRLF endings, a line with
        trailing spaces) and the assertion is equality on the whole file.
        """
        with tree() as root:
            self._scaffolded(root)
            log = root / self.MDIR / 'decisions.md'
            hand = ('## D9 — 2026-01-01 — a hand-written entry\n'
                    'Free prose, no fields, several  \nlines of it.\n')
            before = (f'{model.SLOT_HEADER["decisions.md"]}\n\n{hand}'
                      .replace('\n', '\r\n'))
            model.write_raw(log, before)
            self.assertEqual(run_cli(root, 'decide', '0.1', 'the next one')[0], 0)
            today = datetime.now(timezone.utc).date().isoformat()
            self.assertEqual(
                log.read_bytes(),
                (before + f'\r\n## D10 — {today} — the next one\r\n').encode())

    def test_a_flag_shaped_title_is_refused_not_written(self):
        # The retired four-field interface (`--title X --chose A --over B …`)
        # once parsed here; today those words would be just words, and the one
        # caller who types a title whose FIRST word starts with `--` is a
        # caller speaking that dead interface. Writing their flag soup into a
        # durable log at exit 0 is a quiet lie — refuse, name the word, write
        # nothing.
        with tree() as root:
            code, out = run_cli(root, 'decide', '0.1/alpha', '--title',
                                'the thing', '--chose', 'A', '--over', 'B')
            self.assertEqual(code, 2, out)
            self.assertIn('--title', out)
            self.assertFalse(
                (root / 'pm/roadmap/0.1-demo/features/alpha/decisions.md')
                .exists())

    def test_a_title_left_dangling_on_a_splitter_refuses_without_writing(self):
        """The residue of an unquoted `make pm ARGS="decide <id> a; b"`: the
        consumer's shell cuts at the operator, this process gets the first half,
        and the second half runs as a command of its own. One consumer's log
        ended up carrying two half-headings that way. The refusal must not mint
        the log either."""
        with tree() as root:
            self._scaffolded(root)
            log = root / self.MDIR / 'decisions.md'
            for title in ('half a heading;', 'a thing &', '|'):
                with self.subTest(title=title):
                    code, out = run_cli(root, 'decide', '0.1', title)
                    self.assertEqual(code, 1, out)
                    self.assertIn('Quote the whole title', out)
                    self.assertFalse(log.exists(), out)

    def test_a_quoted_title_keeps_its_shell_metacharacters(self):
        # A `;` that SURVIVED the caller's shell is a word, not an operator;
        # refusing it would break the only spelling that works. And
        # `ARGS='decide 0.1 a\; b'` reaches argv as ['a;', 'b'] — joining argv
        # rebuilds the title intact, which is not a truncation.
        with tree() as root:
            self._scaffolded(root)
            for argv, expected in (
                    (('rng-streams moves to 0.90.5; the MVP base stated',),
                     'rng-streams moves to 0.90.5; the MVP base stated'),
                    (('A & B, not A | B',), 'A & B, not A | B'),
                    (('a;', 'b'), 'a; b')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, 'decide', '0.1', *argv)
                    self.assertEqual(code, 0, out)
                    self.assertIn(f'— {expected}\n', self._log(root))

    def test_only_a_milestone_or_a_feature_has_a_decision_log(self):
        with tree() as root:
            self._scaffolded(root)
            code, out = run_cli(root, 'decide', '0.1/alpha/a-story', 'nope')
            self.assertEqual(code, 1, out)
            self.assertIn('no decision log', out)
            code, out = run_cli(root, 'decide', '0.1/alpha', 'a feature choice')
            self.assertEqual(code, 0, out)
            self.assertIn('## D1 — ',
                          self._log(root, 'features/alpha/decisions.md'))


class ExeclistRefusals(unittest.TestCase):
    """A grain the renderer cannot rewrite CORRECTLY is a refusal — the file
    and the problem named, nothing written — never a traceback, and never a
    file that quietly grows by one fresh block per run."""

    def test_a_non_utf8_grain_refuses_instead_of_crashing(self):
        # The audit's \xff-grain reproduction: UnicodeDecodeError traceback
        # out of the inline read in execlist.sync, scan aborted mid-tree.
        with tree() as root:
            (root / FFILE).write_bytes(
                b'---\nid: 0.1/alpha\nstatus: building\n---\n\xff\n')
            for argv in (('sync',), ('sync', '--check')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 1, out)
                    self.assertIn('REFUSED', out)
                    self.assertIn('feature.md', out)
                    self.assertIn('not UTF-8', out)

    def test_v6_reports_a_non_utf8_grain_and_keeps_earlier_findings(self):
        from agentic_sdlc.repo.pm import validate
        with tree() as root:
            run_cli(root, 'sync')
            (root / FFILE).write_bytes(b'\xff\xfe broken')
            findings, _ = validate.run(cfg_for(root))
            self.assertTrue(any('not UTF-8' in f for f in findings), findings)
            # V1's finding about the same grain survives — the crash used to
            # abort run() and take every finding gathered before V6 with it.
            self.assertTrue(any('missing id' in f for f in findings), findings)

    def test_a_damaged_marker_pair_refuses_instead_of_growing_the_file(self):
        # The audit's growth reproduction: 25 -> 33 -> 41 lines over three
        # `pm sync` runs, each exit 0 — the append branch fired every time.
        # Half a pair is not "no block" either; it took the same branch.
        from agentic_sdlc.repo.pm import execlist
        for name, damage in (
                ('reversed markers',
                 lambda t: t.replace(execlist.OPEN, '@@TMP@@')
                            .replace(execlist.CLOSE, execlist.OPEN)
                            .replace('@@TMP@@', execlist.CLOSE)),
                ('a lone marker', lambda t: t.replace(execlist.CLOSE, ''))):
            with self.subTest(damage=name), tree() as root:
                run_cli(root, 'sync')
                mfile = root / MFILE
                mfile.write_text(damage(mfile.read_text(encoding='utf-8')),
                                 encoding='utf-8')
                before = mfile.read_bytes()
                code, out = run_cli(root, 'sync')
                self.assertEqual(code, 1, out)
                self.assertIn('milestone.md', out)
                self.assertEqual(mfile.read_bytes(), before)
                # Refusing twice is still refusing — and still not writing.
                code, _ = run_cli(root, 'sync')
                self.assertEqual(code, 1)
                self.assertEqual(mfile.read_bytes(), before)


class StatusVerbHonoursACustomVocabulary(unittest.TestCase):
    """A move into `done` dispatches to the close, but the TARGET state still
    has to be one the project declared. Pre-fix `done` and `reviewing`
    dispatched before the membership check, so with a custom vocabulary the
    sanctioned tool wrote the exact undeclared status D4 reports. The CURRENT
    state stays ungated — repair-from-wombat is pinned elsewhere and
    unchanged."""

    RENAMED = {'todo': ('todo',), 'in_progress': ('building',),
               'done': ('shipped',)}

    def test_the_target_state_must_be_in_the_projects_own_set(self):
        # (argv, the declaration the refusal must name, story statuses)
        rows = (
            (('feature', 'done', '0.1/alpha'), 'todo, building, shipped',
             ('ready',)),
            (('feature', 'reviewing', '0.1/alpha'), 'todo, building, shipped',
             ('ready',)),
        )
        for argv, named, stories in rows:
            with self.subTest(argv=argv), tree(story_statuses=stories) as root:
                write_config(root, declaring(feature=self.RENAMED))
                sfile, ffile = root / STORY_REL, root / FFILE
                s_before, f_before = sfile.read_bytes(), ffile.read_bytes()
                code, out = run_cli(root, *argv)
                self.assertEqual(code, 2, out)
                self.assertIn(named, out)
                self.assertIn('[pm.states.feature]', out)
                # Nothing was touched — neither the story nor the feature.
                self.assertEqual(sfile.read_bytes(), s_before)
                self.assertEqual(ffile.read_bytes(), f_before)

    def test_a_custom_vocabulary_closes_through_its_own_done_word(self):
        # The close is the CATEGORY: `shipped` stamps the record and reports
        # the stories exactly as `done` does in the seed.
        with tree(story_statuses=('ready',)) as root:
            write_config(root, declaring(feature=self.RENAMED))
            code, out = run_cli(root, 'feature', 'shipped', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertEqual(model.field_of(root / FFILE, 'status'), 'shipped')
            self.assertIn('review record: docs/reviews/alpha.md', out)

    def test_review_record_with_an_empty_value_refuses_in_either_spelling(self):
        # Pre-fix: `--review-record=` stored '' and silently skipped the
        # stamp at exit 0 — flag consumed, nothing done. The space spelling's
        # missing-arg case was already a Usage refusal; they now agree.
        for extra in (('--review-record=',), ('--review-record', '')):
            with self.subTest(extra=extra), tree() as root:
                ffile = root / FFILE
                before = ffile.read_bytes()
                code, out = run_cli(root, 'feature', 'done', '0.1/alpha', *extra)
                self.assertEqual(code, 2, out)
                self.assertIn('needs a path', out)
                self.assertEqual(ffile.read_bytes(), before)


class ZeroCensusIsLoud(unittest.TestCase):
    """An empty print at exit 0 over a tree that holds nothing is a scan of
    zero files, passing — rule 4's read-side sin. `pm list` got the loud arm
    first; `pm status` and `pm sync --check` mirror it."""

    def _emptied(self, root: Path) -> None:
        import shutil
        shutil.rmtree(root / 'pm/roadmap/0.1-demo')

    def test_status_over_an_empty_roadmap_refuses(self):
        with tree() as root:
            self._emptied(root)
            code, out = run_cli(root, 'status')
            self.assertEqual(code, 2, out)
            self.assertIn('no milestone at all', out)

    def test_status_names_its_set_and_still_prints_a_real_tree(self):
        with tree() as root:
            code, out = run_cli(root, 'status', '9.9')
            self.assertEqual(code, 2, out)
            self.assertIn("'9.9'", out)
            self.assertIn('0.1', out)
            code, out = run_cli(root, 'status', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('milestone 0.1', out)

    def test_sync_over_zero_grains_refuses_in_both_modes(self):
        # Pre-fix: `all 0 execution list(s) current`, exit 0 — only the write
        # mode refused.
        with tree() as root:
            self._emptied(root)
            for argv in (('sync', '--check'), ('sync',)):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 2, out)
                    self.assertIn('no grains', out)


class BugStatus(unittest.TestCase):
    """`pm bug <status> <bug-id>` — exactly `cmd_story`'s shape, for bugs.

    Before this, the vocabulary and the `/bugs/` resolver both existed
    (`_grain_file`, `checks/pm.py`'s D4) and nothing sanctioned reached them
    together — only a hand edit or the untyped `pm set` moved a bug's own
    `status:`. The shared shapes live in `StatusVerbQuartet`; kept here are
    the guards only a bug id can exercise.
    """

    @staticmethod
    def _bug(root: Path, slug: str, status: str) -> Path:
        p = root / 'pm/roadmap/0.1-demo/bugs' / f'{slug}.md'
        write(p, {'id': f'0.1/bugs/{slug}', 'milestone': '"0.1"',
                  'status': status})
        return p

    def test_a_bug_id_never_reaches_a_grain_that_is_not_a_bug(self):
        # v0.16.0 release-review blocker: `0.1/bugs/../features/alpha/feature`
        # resolved by traversal and wrote a BUG-vocabulary status into the
        # feature file — the cross-grain write the docstring above promises
        # cannot happen. The slug half holds no path segments, ever. And
        # `_grain_file` alone resolves a FEATURE id when `/bugs/` is absent, so
        # a bug verb reaching it unguarded would validate the target against
        # `bug_states` and then write it into the feature's own `status:`.
        with tree() as root:
            self._bug(root, 'crash', 'open')
            victim = root / FFILE
            for gid in ('0.1/bugs/../features/alpha/feature',
                        '0.1/bugs/sub/../../features/alpha/feature',
                        '0.1/bugs/', '0.1/alpha'):
                with self.subTest(gid=gid):
                    code, out = run_cli(root, 'bug', 'fixed', gid)
                    self.assertEqual(code, 2, (gid, out))
                    self.assertIn('no bug resolves', out)
                    self.assertEqual(model.field_of(victim, 'status'), 'building')
            # `pm set` rides the same resolver — the same id must refuse.
            code, out = run_cli(root, 'set',
                                '0.1/bugs/../features/alpha/feature',
                                'status', 'PWNED')
            self.assertEqual(code, 2, out)
            self.assertEqual(model.field_of(victim, 'status'), 'building')

    def test_a_nested_bug_id_resolves(self):
        with tree() as root:
            bug = root / 'pm/roadmap/0.1-demo/bugs/spatial/seed-is-zero.md'
            write(bug, {'id': '0.1/bugs/spatial/seed-is-zero',
                        'milestone': '"0.1"', 'status': 'open'})
            code, out = run_cli(root, 'bug', 'fixed',
                                '0.1/bugs/spatial/seed-is-zero')
            self.assertEqual(code, 0, out)
            self.assertEqual(model.field_of(bug, 'status'), 'fixed')


class Retire(unittest.TestCase):
    """`pm retire <milestone-id>` — one write that removes the directory.

    **`ROADMAP.md` retired in 0.3.0** and this verb no longer appends to it. It
    was two things wearing one name: a hand-maintained index of milestones still
    in the tree — the second scoreboard the tool forbids one grain down — and the
    only surviving record of what this verb deleted. `pm roadmap` derives the
    first; `order` plus R1's UNVERIFIABLE carries the second, with nobody
    maintaining it.

    Refuses on exactly one impossibility (an unresolvable id); everything else it
    notices about the tree — a milestone not `done`, a feature or bug still open
    — is reported below the line that says what moved, never a precondition.
    """

    def test_every_refusal_leaves_the_tree_standing(self):
        with tree() as root:
            code, out = run_cli(root, 'retire', '9.9')
            self.assertEqual(code, 2, out)
            self.assertIn('is not a milestone', out)
            self.assertIn('0.1', out)
            self.assertTrue((root / 'pm/roadmap/0.1-demo').is_dir())
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            return  # permission bits are not an obstruction as root
        # The obstruction. With ROADMAP.md gone the plan is ONE step, so the
        # half-landed state the old delete-then-append could reach — a milestone
        # removed with no row to say where — is now unreachable by construction
        # rather than by `plan.decide()` catching it. What still has to hold is
        # that a refused retire leaves the directory whole.
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            mdir = root / 'pm/roadmap/0.1-demo'
            before = sorted(p.relative_to(root) for p in mdir.rglob('*'))
            (root / 'pm/roadmap').chmod(0o555)
            try:
                code, out = run_cli(root, 'retire', '0.1')
            finally:
                (root / 'pm/roadmap').chmod(0o755)
            self.assertEqual(code, 1, out)
            self.assertIn('nothing was retired', out)
            self.assertTrue(mdir.is_dir())
            self.assertEqual(sorted(p.relative_to(root) for p in mdir.rglob('*')),
                             before)

    def test_a_non_done_milestone_is_reported_not_refused(self):
        with tree(milestone_status='building',
                  feature_status='building') as root:
            BugStatus._bug(root, 'seed-is-zero', 'open')
            code, out = run_cli(root, 'retire', '0.1', 'pulled')
            self.assertEqual(code, 0, out)
            self.assertIn('noticed: milestone 0.1 is building, not done', out)
            self.assertIn('feature(s) not done', out)
            self.assertIn('bug(s) still open', out)
            self.assertFalse((root / 'pm/roadmap/0.1-demo').exists())

    def test_the_plan_is_what_outlives_the_directory(self):
        """0.3.0: the row survives its milestone through `order`, not a file.

        A retired milestone whose version is on the plan leaves a row R1 reports
        as UNVERIFIABLE. One that was never scheduled leaves nothing, and the
        verb SAYS so rather than letting the record vanish quietly.
        """
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            model.set_field(root / 'pm/roadmap/0.1-demo/milestone.md',
                            'version', '"0.1.0"')
            run_cli(root, 'order', '--append', '0.1.0')
            code, out = run_cli(root, 'retire', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('releases.md', out)
            self.assertIn('UNVERIFIABLE', out)
            self.assertFalse((root / 'pm/roadmap/0.1-demo').exists())
            # The plan kept the version; the record is gone.
            self.assertEqual(
                model.list_field_of(root / 'pm/roadmap/releases.md', 'order'),
                ['0.1.0'])
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            code, out = run_cli(root, 'retire', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('on no plan', out)
            self.assertIn('pm order --append', out)

    def test_retire_writes_no_roadmap_file_and_needs_none(self):
        """The whole point of the retirement: a tree with no ROADMAP.md retires
        fine, and one that has the old file is not written to."""
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            stale = root / 'pm/roadmap/ROADMAP.md'
            stale.write_text('| id | name | date | ended |\n', encoding='utf-8')
            before = stale.read_bytes()
            self.assertEqual(run_cli(root, 'retire', '0.1')[0], 0)
            self.assertEqual(stale.read_bytes(), before)
            self.assertFalse((root / 'pm/roadmap/0.1-demo').exists())

    def test_dry_run_writes_nothing_byte_for_byte(self):
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            mdir = root / 'pm/roadmap/0.1-demo'
            before_files = sorted(
                (p.relative_to(root), p.read_bytes())
                for p in mdir.rglob('*') if p.is_file())
            code, out = run_cli(root, 'retire', '0.1', '--dry-run')
            self.assertEqual(code, 0, out)
            self.assertIn('[dry-run]', out)
            self.assertTrue(mdir.is_dir())
            after_files = sorted(
                (p.relative_to(root), p.read_bytes())
                for p in mdir.rglob('*') if p.is_file())
            self.assertEqual(before_files, after_files)

    def test_retire_removes_exactly_the_dir_and_nothing_beside_it(self):
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            write(root / 'pm/roadmap/0.2-two/milestone.md',
                  {'id': '"0.2"', 'name': 'Two', 'status': 'planning'})
            sibling = sorted(
                (p.relative_to(root), p.read_bytes())
                for p in (root / 'pm/roadmap/0.2-two').rglob('*') if p.is_file())
            self.assertEqual(run_cli(root, 'retire', '0.1')[0], 0)
            self.assertFalse((root / 'pm/roadmap/0.1-demo').exists())
            self.assertEqual(
                sorted((p.relative_to(root), p.read_bytes())
                       for p in (root / 'pm/roadmap/0.2-two').rglob('*')
                       if p.is_file()),
                sibling)


class Move(unittest.TestCase):
    """`pm move <story-id> <feature-id>` — re-parents a story whole, or not
    at all.

    Before this, re-parenting was a rename plus three hand-edited
    frontmatter fields, policed afterwards (if at all) by V2/V3 — one
    whole-or-nothing verb through the machinery the templates already own.
    """

    NEW_REL = 'pm/roadmap/0.2-next/features/gamma/stories/s0.md'

    @staticmethod
    def _second_feature(root: Path) -> None:
        write(root / 'pm/roadmap/0.1-demo/features/beta/feature.md',
              {'id': '0.1/beta', 'milestone': '"0.1"', 'name': 'Beta',
               'status': 'building', 'reviewed': ''})

    @staticmethod
    def _second_milestone(root: Path) -> None:
        write(root / 'pm/roadmap/0.2-next/milestone.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'building'})
        write(root / 'pm/roadmap/0.2-next/features/gamma/feature.md',
              {'id': '0.2/gamma', 'milestone': '"0.2"', 'name': 'Gamma',
               'status': 'building', 'reviewed': ''})

    def test_a_story_moves_whole_and_every_other_byte_survives(self):
        """Across milestones, so all THREE rewritten keys have to change.

        Probed 2026-09-06 (0.2.0/the-proof-is-named-in-the-criterion): this
        case used to move `0.1/alpha/s0` to `0.1/beta`, where the milestone
        key already held the right value — so a `move` that stopped
        rewriting `milestone` passed, and would have shipped stories whose
        `milestone:` named the tree they left. The target is now a feature
        under a second milestone, and the byte-exact expectation carries the
        third replacement.
        """
        with tree(story_statuses=('ready',)) as root:
            self._second_milestone(root)
            before = (root / STORY_REL).read_text(encoding='utf-8')
            code, out = run_cli(root, 'move', '0.1/alpha/s0', '0.2/gamma')
            self.assertEqual(code, 0, out)
            new = root / self.NEW_REL
            self.assertFalse((root / STORY_REL).exists())
            self.assertTrue(new.is_file())
            expected = (before.replace('feature: 0.1/alpha', 'feature: 0.2/gamma')
                              .replace('id: 0.1/alpha/s0', 'id: 0.2/gamma/s0')
                              .replace('milestone: "0.1"', 'milestone: "0.2"'))
            self.assertNotEqual(expected, before)
            self.assertEqual(expected, new.read_text(encoding='utf-8'))

    def test_an_unresolvable_end_is_a_usage_error_that_moves_nothing(self):
        for argv in (('0.1/alpha/s0', '0.1/nope'), ('0.1/alpha/nope', '0.1/beta')):
            with self.subTest(argv=argv), tree(story_statuses=('ready',)) as root:
                self._second_feature(root)
                code, out = run_cli(root, 'move', *argv)
                self.assertEqual(code, 2, out)
                self.assertTrue((root / STORY_REL).is_file())
                if argv[1] == '0.1/nope':
                    self.assertIn('no feature resolves', out)
                    self.assertIn('0.1/alpha', out)
                    self.assertIn('0.1/beta', out)

    def test_already_under_the_target_is_a_noop(self):
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'move', '0.1/alpha/s0', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('no-op', out)
            self.assertTrue((root / STORY_REL).is_file())

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0,
                     'permission bits are not the obstruction as root')
    def test_an_unwritable_target_directory_moves_nothing(self):
        with tree(story_statuses=('ready',)) as root:
            self._second_feature(root)
            target_dir = root / 'pm/roadmap/0.1-demo/features/beta'
            target_dir.chmod(0o555)
            try:
                before = (root / STORY_REL).read_bytes()
                code, out = run_cli(root, 'move', '0.1/alpha/s0', '0.1/beta')
                self.assertEqual(code, 1, out)
                self.assertIn('nothing was moved', out)
                self.assertTrue((root / STORY_REL).is_file())
                self.assertEqual((root / STORY_REL).read_bytes(), before)
                self.assertFalse((target_dir / 'stories' / 's0.md').exists())
            finally:
                target_dir.chmod(0o755)


class ThePlanIsADeclaredOrder(unittest.TestCase):
    """`order` is read as a block list, and the current release is a POSITION.

    The sin guarded here is the resolver quietly answering with the wrong entry:
    every rule downstream (R5, the ledger's home, `pm next`) grades against
    whatever this returns, so a silent off-by-one mis-grades the whole tree.
    """

    @staticmethod
    def _plan(root: Path, *versions: str) -> None:
        body = '\n'.join(f'  - "{v}"' for v in versions)
        (root / 'pm' / 'roadmap' / 'releases.md').write_text(
            f'---\norder:\n{body}\n---\n\nThe plan.\n', encoding='utf-8')

    @staticmethod
    def _milestone(root: Path, mid: str, version: str, status: str) -> None:
        front = {'id': f'"{mid}"', 'name': mid, 'status': status}
        if version:
            front['version'] = f'"{version}"'
        write(root / 'pm' / 'roadmap' / f'{mid}-m' / 'milestone.md', front)

    def test_block_list_reads_in_order_and_a_scalar_is_not_a_list(self):
        with tree() as root:
            self._plan(root, '0.1.0', '0.2.0', '0.3.0')
            cfg = cfg_for(root)
            self.assertEqual(model.declared_order(cfg),
                             ['0.1.0', '0.2.0', '0.3.0'])
            # A scalar on the key line is a DIFFERENT shape, and reading it as
            # a one-element list would make `order: 0.1.0` silently a plan.
            (root / 'pm' / 'roadmap' / 'releases.md').write_text(
                '---\norder: 0.1.0\n---\n', encoding='utf-8')
            self.assertEqual(model.declared_order(cfg), [])

    def test_no_plan_at_all_is_no_current_release(self):
        with tree() as root:
            cfg = cfg_for(root)
            self.assertEqual(model.declared_order(cfg), [])
            self.assertIsNone(model.current_release(cfg))

    def test_the_release_worked_on_and_the_release_graded_are_two_questions(self):
        """Review A1/B2/C1. `version_at` answers "what should the version FILE
        say"; it was reused for "which release am I working on", and under
        bump-at-close that made `release` re-release a shipped milestone and
        filed gate cost rows into its closed ledger.
        """
        with tree() as root:
            self._plan(root, '0.1.0', '0.2.0', '0.3.0')
            self._milestone(root, 'a', '0.1.0', 'done')
            self._milestone(root, 'b', '0.2.0', 'done')
            self._milestone(root, 'c', '0.3.0', 'building')

            # Worked on: the same answer under BOTH flows, because it is not
            # version_at's question.
            self.assertEqual(loaded(root).version_at, model.VERSION_AT_START)
            self.assertEqual(model.current_release(loaded(root)), '0.3.0')
            self.assertEqual(model.graded_release(loaded(root))[0], '0.3.0')

            write_config(root, '[pm]\nversion_at = "ship"\n')
            self.assertEqual(model.current_release(loaded(root)), '0.3.0')
            self.assertEqual(model.graded_release(loaded(root))[0], '0.2.0')

    def test_graded_release_says_why_when_there_is_nothing_to_grade(self):
        # Review B3: "every entry in `order` has shipped" was reported at exit 0
        # over a tree where NONE had.
        with tree() as root:
            self._plan(root, '0.1.0')
            self._milestone(root, 'a', '0.1.0', 'building')
            write_config(root, '[pm]\nversion_at = "ship"\n')
            version, why = model.graded_release(loaded(root))
            self.assertIsNone(version)
            self.assertIn('no entry in `order` has shipped yet', why)

    def test_an_unverifiable_entry_is_skipped_and_reported_never_guessed_at(self):
        """The ambiguity the tree cannot resolve, carried by the GATE.

        `pm retire` deletes a finished milestone's record while its row survives
        in the plan on purpose, so after a retirement an entry that shipped is
        indistinguishable from one never written. Blocking on it breaks the
        ledger and the belt for every tree that prunes; guessing it is history
        answers with a release the tree cannot support. So the resolver walks
        past it and R1 REPORTS it, every run. Decision D2 records why.
        """
        with tree() as root:
            self._plan(root, '0.1.0', '0.2.0', '0.3.0')
            self._milestone(root, 'a', '0.1.0', 'done')
            # 0.2.0 claimed by nobody; 0.3.0 claimed and building.
            self._milestone(root, 'c', '0.3.0', 'building')
            cfg = loaded(root)
            self.assertTrue(model.release_is_unverifiable(cfg_for(root), '0.2.0'))
            self.assertEqual(model.current_release(cfg), '0.3.0')
            # ...and R1 names it on the same tree, so the skip is never
            # silent. A WARN, not a finding: a dangling entry and a retired
            # milestone's surviving row are indistinguishable, and reddening on
            # a planned-but-unwritten release is what R1's own criterion 1
            # refuses to do.
            write_config(root, '[pm]\nchecks = ["R1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('UNBOUND', out)
            self.assertIn('0.2.0', out)

    def test_an_entry_no_milestone_claims_is_unverifiable_not_unshipped(self):
        """Review F1: a RETIRED milestone and an unwritten one look identical
        from here, so neither may be read as "not shipped".

        Reading them as unshipped is what made `pm retire` roll the current
        release BACKWARD, so R5 demanded a version regression — two shipped
        verbs contradicting each other.
        """
        with tree() as root:
            self._plan(root, '0.1.0', '0.2.0')
            self._milestone(root, 'a', '0.1.0', 'done')
            cfg = cfg_for(root)
            self.assertTrue(model.release_is_unverifiable(cfg, '0.2.0'))
            self.assertIsNone(model.milestone_of_version(cfg, '0.2.0'))
            # Skipped, not answered: nothing after 0.1.0 can be established.
            self.assertIsNone(model.current_release(loaded(root)))

    def test_retiring_a_shipped_milestone_never_moves_the_release_backward(self):
        # Review F1, measured end to end: the plan keeps the entry, the record
        # is gone, and the current release must not become the retired one.
        with tree() as root:
            self._plan(root, '0.1.0', '0.2.0')
            self._milestone(root, 'a', '0.1.0', 'done')
            self._milestone(root, 'b', '0.2.0', 'building')
            self.assertEqual(model.current_release(loaded(root)), '0.2.0')
            import shutil
            shutil.rmtree(root / 'pm' / 'roadmap' / 'a-m')
            self.assertEqual(model.current_release(loaded(root)), '0.2.0')

    def test_two_milestones_claiming_one_version_never_decide_by_directory_name(self):
        """Review F2: the same facts gave opposite verdicts depending on which
        directory sorted first. R3 reports the duplicate; the resolver refuses
        to guess which claimant is authoritative."""
        with tree() as root:
            self._plan(root, '0.1.0', '0.2.0')
            self._milestone(root, 'a', '0.1.0', 'done')
            self._milestone(root, 'b', '0.1.0', 'building')
            cfg = cfg_for(root)
            self.assertEqual(sorted(model.milestones_of_version(cfg, '0.1.0')),
                             ['a', 'b'])
            self.assertTrue(model.release_is_unverifiable(cfg, '0.1.0'))
            self.assertFalse(model.release_is_shipped(cfg, '0.1.0'))
            # Flipping which one is `done` must not change the answer.
            self._milestone(root, 'a', '0.1.0', 'building')
            self._milestone(root, 'b', '0.1.0', 'done')
            self.assertTrue(model.release_is_unverifiable(cfg_for(root), '0.1.0'))

    def test_version_at_refuses_a_value_it_does_not_know(self):
        with tree() as root:
            write_config(root, '[pm]\nversion_at = "whenever"\n')
            with self.assertRaises(model.ConfigError) as caught:
                loaded(root)
            self.assertIn('version_at', str(caught.exception))
            self.assertIn('whenever', str(caught.exception))


class TheListWriterKeepsEveryOtherByte(unittest.TestCase):
    """`set_list_field` — the list-aware sibling to `set_field`.

    `order` is rewritten on every ship, insertion and re-sequence, so this is
    the writer byte fidelity actually matters for: rule 3's "a write touches
    only what it was asked to touch", proven as BYTES rather than as a reparse.
    """

    PLAN = ('---\n'
            'goal: ship the thing\n'
            'order:\n'
            '  - "0.1.0"\n'
            '  - "0.2.0"\n'
            'owner: chris\n'
            '---\n'
            '\n'
            '# The plan\n'
            '\n'
            'Prose the writer must not touch.\n')

    @contextlib.contextmanager
    def _plan(self, text: str = ''):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'releases.md'
            path.write_bytes((text or self.PLAN).encode('utf-8'))
            yield path

    def test_an_append_rewrites_only_the_list(self):
        with self._plan() as path:
            self.assertTrue(model.set_list_field(
                path, 'order', ['0.1.0', '0.2.0', '0.3.0']))
            after = path.read_text(encoding='utf-8')
            self.assertEqual(model.list_field_of(path, 'order'),
                             ['0.1.0', '0.2.0', '0.3.0'])
            for kept in ('goal: ship the thing', 'owner: chris', '# The plan',
                         'Prose the writer must not touch.'):
                self.assertIn(kept, after)
            # The untouched halves are byte-identical, not merely present.
            self.assertEqual(after.split('order:')[0],
                             self.PLAN.split('order:')[0])
            self.assertEqual(after.split('---\n')[2], self.PLAN.split('---\n')[2])

    def test_insert_and_remove_move_one_entry_and_nothing_else(self):
        with self._plan() as path:
            model.set_list_field(path, 'order', ['0.1.0', '0.1.5', '0.2.0'])
            self.assertEqual(model.list_field_of(path, 'order'),
                             ['0.1.0', '0.1.5', '0.2.0'])
            model.set_list_field(path, 'order', ['0.1.0', '0.2.0'])
            self.assertEqual(path.read_text(encoding='utf-8'), self.PLAN)

    def test_the_write_is_idempotent(self):
        with self._plan() as path:
            model.set_list_field(path, 'order', ['0.1.0', '0.3.0'])
            once = path.read_bytes()
            model.set_list_field(path, 'order', ['0.1.0', '0.3.0'])
            self.assertEqual(path.read_bytes(), once)

    def test_a_crlf_plan_stays_crlf(self):
        # `pm` rewrites one line and preserves the file's convention; a plan
        # authored on Windows must not come back with mixed endings.
        crlf = self.PLAN.replace('\n', '\r\n')
        with self._plan(crlf) as path:
            model.set_list_field(path, 'order', ['0.1.0', '0.2.0', '0.3.0'])
            raw = path.read_bytes()
            self.assertNotIn(b'\r\r', raw)
            self.assertEqual(raw.count(b'\n'), raw.count(b'\r\n'))
            self.assertEqual(model.list_field_of(path, 'order'),
                             ['0.1.0', '0.2.0', '0.3.0'])

    def test_the_files_own_indent_and_quoting_survive(self):
        # A hand-edited plan is not reformatted underneath its author.
        plain = '---\norder:\n    - 0.1.0\n---\n'
        with self._plan(plain) as path:
            model.set_list_field(path, 'order', ['0.1.0', '0.2.0'])
            after = path.read_text(encoding='utf-8')
            self.assertIn('    - 0.1.0', after)
            self.assertIn('    - 0.2.0', after)
            self.assertNotIn('"', after)

    def test_the_key_is_minted_when_the_plan_has_none(self):
        with self._plan('---\ngoal: ship\n---\n\nBody\n') as path:
            self.assertTrue(model.set_list_field(path, 'order', ['9.9']))
            self.assertEqual(model.list_field_of(path, 'order'), ['9.9'])
            self.assertIn('goal: ship', path.read_text(encoding='utf-8'))
            self.assertIn('Body', path.read_text(encoding='utf-8'))

    def test_a_scalar_on_the_key_line_is_refused_and_nothing_is_written(self):
        # Rewriting it as a block would be the writer deciding the file meant
        # something else — rule 3: a verb that cannot guarantee a correct
        # result refuses and says why.
        scalar = '---\norder: 0.1.0\n---\n'
        with self._plan(scalar) as path:
            self.assertFalse(model.set_list_field(path, 'order', ['x']))
            self.assertEqual(path.read_text(encoding='utf-8'), scalar)

    def test_a_comment_or_a_blank_line_never_truncates_the_plan(self):
        """Review A2. `releases.md` is edited on every ship, so spacing and
        annotating it are the obvious things a human does — and truncating
        there dropped every entry below, silently. `--append` then wrote a
        DUPLICATE and reported a successful append.
        """
        annotated = ('---\n'
                     'order:\n'
                     '  # shipped\n'
                     '  - "0.1.0"\n'
                     '\n'
                     '  - "0.2.0"\n'
                     'owner: chris\n'
                     '---\n')
        with self._plan(annotated) as path:
            self.assertEqual(model.list_field_of(path, 'order'),
                             ['0.1.0', '0.2.0'])
            self.assertTrue(model.set_list_field(
                path, 'order', ['0.1.0', '0.2.0', '0.3.0']))
            after = path.read_text(encoding='utf-8')
            # No duplicate, the annotation kept, the neighbour untouched.
            self.assertEqual(model.list_field_of(path, 'order'),
                             ['0.1.0', '0.2.0', '0.3.0'])
            self.assertEqual(after.count('- "0.2.0"'), 1, after)
            self.assertIn('# shipped', after)
            self.assertIn('owner: chris', after)

    def test_an_inline_comment_is_not_read_into_the_value(self):
        # Review A3: it was, and the value then failed to unquote — so ONE
        # annotated entry silently changed the spelling of every version the
        # reader returned.
        with self._plan('---\norder:\n  - "0.1.0"  # the first\n'
                        '  - "0.2.0"\n---\n') as path:
            self.assertEqual(model.list_field_of(path, 'order'),
                             ['0.1.0', '0.2.0'])

    def test_no_frontmatter_is_refused(self):
        with self._plan('no fence here\n') as path:
            self.assertFalse(model.set_list_field(path, 'order', ['x']))
            self.assertEqual(path.read_text(encoding='utf-8'), 'no fence here\n')
