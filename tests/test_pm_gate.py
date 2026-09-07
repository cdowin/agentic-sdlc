"""`check pm` and `pm validate` — drift rules, flow checks, config refusals,
and the censuses that keep a zero-file scan loud.

Split from test_pm.py by concern; the shared harness is tests/support/pm.py.
The CLI and the gate share ONE definition of "reviewed" and of each drift
rule — the round trips here are what stop the two diverging.

**Selection criterion (hard rule 10, 0.2.0/the-proof-is-named-in-the-criterion):**
what remains gates one of rule 4's two cardinal sins — a gate printing PASS
over what it did not measure, or a write that looks legitimate and is not.
Families that proved one rule at three altitudes, refusal matrices spelling one
grammar twelve ways, and assertions about a docstring or a symbol's absence
were removed; the behaviour each of them stood in for is asserted once, here or
in tests/test_pm_verbs.py.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from support.pm import (
    DAMAGE_FORMS,
    STORY_REL,
    bug,
    cfg_for,
    damage,
    declaring,
    run_cli,
    run_gate,
    tree,
    write,
    write_config,
)

from agentic_sdlc.repo.checks import pm as pm_check
from agentic_sdlc.repo.pm import model


def gate_both_streams(root: Path) -> tuple[int, str]:
    """`check pm` with BOTH streams captured.

    The shared `run_gate` takes stdout only, and a config complaint goes to
    stderr — so a test built on it would assert exit 2 against an empty string
    and pass on any exit-2 whatsoever.
    """
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = pm_check.run()
    return code, buf.getvalue()


def building_milestone(root: Path, branch: str = '', version: str = '0.1'):
    """The tree D9/D10/R5 read: a `building` milestone, a `branch:` stamp and
    a `pyproject.toml` version."""
    mfile = root / 'pm/roadmap/milestones/0.1.md'
    model.set_field(mfile, 'status', 'building')
    if branch:
        model.set_field(mfile, 'branch', branch)
    if version:
        (root / 'pyproject.toml').write_text(
            f'[project]\nversion = "{version}"\n', encoding='utf-8')


class Frontmatter(unittest.TestCase):
    """`field_of` / `set_field` — the two functions every verb writes through.

    Byte fidelity is proven in tests/test_pm_verbs.py `WriteFidelity` (CRLF and
    exotic line breaks, compared as bytes), which subsumes the plain case this
    class used to carry as well.
    """

    def test_field_ignores_the_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'g.md'
            write(p, {'status': 'ready'}, body='status: done\n\nprose')
            self.assertEqual(model.field_of(p, 'status'), 'ready')

    def test_set_field_inserts_a_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'g.md'
            write(p, {'id': 'a', 'status': 'ready'})
            self.assertTrue(model.set_field(p, 'reviewed', 'docs/r.md'))
            self.assertEqual(model.field_of(p, 'reviewed'), 'docs/r.md')

    def test_set_field_refuses_a_file_with_no_frontmatter(self):
        # Nowhere to put the key: refuse rather than silently drop it.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'g.md'
            p.write_text('no fence here\n', encoding='utf-8')
            self.assertFalse(model.set_field(p, 'status', 'done'))
            self.assertEqual(p.read_text(), 'no fence here\n')


class DriftGate(unittest.TestCase):
    """The drift roster, one row per rule.

    Each row is a tree that trips exactly the rule it names, the line it must
    carry, and WHICH LINE SHAPE — `  DRIFT  ` (a finding, exit 1) or
    `  WARN  ` (a cross-level disagreement, exit 0, counted separately). A
    rule that stopped firing, started firing under a different name, or
    changed sides fails here — which is the whole read-side contract.

    Story 03 of the-code-knows-entry-and-exit moved D2, D3, D5 and D6 to
    WARN. Chris: *"a feature to-do and a story in progress, that's a warn.
    Not a fail, no action, just messaging."* D1 and D4 are facts about the
    input and stay findings.
    """

    WARNED = ('D2', 'D3', 'D5', 'D6')

    # (rule, tree kwargs, the line the finding must carry)
    #
    # D2 and D6 fire on a parent still in `todo` — `ready` here. A parent at
    # `building` over finished children is NOT drift any more: `building` is
    # `in_progress`, and which in-progress word a parent holds is the
    # project's business (the D2/D5 resolution loss the CHANGELOG names).
    # Each WARN names both grains and both categories.
    RULES = (
        ('D2', dict(feature_status='ready', story_statuses=('done',)),
         "feature 0.1/alpha: all stories done, feature still ready (todo) — "
         "all 1 stories are done"),
        ('D3', dict(milestone_status='done', feature_status='building'),
         "milestone 0.1 is 'done' (done) but feature 0.1/alpha is "
         "'building' (in_progress)"),
        # The set the tree is judged against: the FEATURE's declared order,
        # and nothing else now that the deprecation window has closed.
        ('D4', dict(feature_status='bogus'),
         'not in (planning ready building reviewing done obe)'),
        ('D5', dict(feature_status='planning', story_statuses=('done',)),
         "story 0.1/alpha/s0 is 'done' (done) but its feature 0.1/alpha is "
         "still 'planning' (todo)"),
        ('D6', dict(milestone_status='ready', feature_status='done',
                    story_statuses=('done',)),
         "milestone 0.1 is 'ready' (todo) but all 1 features are done"),
    )

    def test_a_parent_in_progress_over_finished_children_is_not_drift(self):
        # The resolution D2 and D6 GAVE UP: a `building` feature over done
        # stories, a `building` milestone over done features. Under three
        # categories both parents have started, and "which in-progress word
        # should it hold" is not a question this gate asks.
        for kwargs in (dict(feature_status='building', story_statuses=('done',)),
                       dict(milestone_status='building', feature_status='done',
                            story_statuses=('done',))):
            with self.subTest(**kwargs), tree(**kwargs) as root:
                code, out = run_gate(root)
                self.assertEqual(code, 0, out)

    def test_clean_tree_passes_and_prints_a_census(self):
        with tree(story_statuses=('ready',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 milestone(s), 1 feature(s), 1 story/ies', out)

    def test_an_empty_tree_fails_loudly_rather_than_passing(self):
        # Rule 4: a gate that scanned nothing must say so, not print PASS.
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
                code, out = run_gate(root)
            finally:
                os.chdir(previous)
            self.assertEqual(code, 1)
            self.assertIn('no milestones found', out)

    def test_each_drift_rule_fires_and_names_what_it_saw(self):
        for rule, kwargs, message in self.RULES:
            with self.subTest(rule=rule), tree(**kwargs) as root:
                code, out = run_gate(root)
                warned = rule in self.WARNED
                self.assertEqual(code, 0 if warned else 1, out)
                shape = '  WARN  ' if warned else '  DRIFT  '
                self.assertTrue(
                    any(message in ln and ln.startswith(shape)
                        for ln in out.splitlines()), (rule, out))
                if warned:
                    self.assertIn('[check:pm] PASS', out)
                    self.assertIn('warning(s)', out)
                    self.assertNotIn('DRIFT', out)
                else:
                    self.assertIn('[check:pm] FAIL', out)

    def test_d1_a_reviewed_pointer_that_resolves_to_nothing(self):
        with tree(feature_status='done', story_statuses=('done',),
                  milestone_status='done', with_record=True) as root:
            (root / 'docs' / 'reviews' / 'alpha.md').unlink()
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('resolves to nothing', out)

    def test_d1_says_nothing_about_a_feature_with_no_pointer_at_all(self):
        # The half that was an opinion. An absent review record is the absence
        # of a document — a fact about a team, not about a tree.
        with tree(feature_status='done', story_statuses=('done',),
                  milestone_status='done', with_record=False) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)

    def test_d4_reports_every_grain_against_its_own_declared_words(self):
        # The census half of D4: three grains, three findings, and each names
        # ITS OWN kind's declared order — the seed gives each kind the states
        # its belt writes, so the three lines differ. A rule that reached
        # only two of the three would still fire and still pass a
        # single-grain assertion.
        with tree(milestone_status='bogus', feature_status='bogus',
                  story_statuses=('bogus',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            for kind in ('milestone', 'feature', 'story'):
                order = ' '.join(model.DEFAULT_FLOWS[kind][cat][i]
                                 for cat in model.CATEGORIES
                                 for i in range(len(model.DEFAULT_FLOWS[kind][cat])))
                self.assertEqual(out.count(f'not in ({order})'), 1,
                                 (kind, out))

    def test_d6_goes_quiet_the_moment_the_milestone_advances(self):
        # The deadlock: the release gate could not run until the milestone was
        # flipped `done` — the decision the gate exists to inform. At
        # `reviewing` the gate runs and the decision is still open.
        for mstat in ('reviewing', 'accepted', 'packaging'):
            with self.subTest(milestone=mstat):
                with tree(milestone_status=mstat, feature_status='done',
                          story_statuses=('done',)) as root:
                    code, out = run_gate(root)
                    self.assertEqual(code, 0, out)

    def test_a_disabled_rule_does_not_fire(self):
        # `[pm] checks` is the knob. This fixture trips D2 AND D5, so turning
        # D2 off must silence D2's message specifically while D5 still fires —
        # a blanket "exit 0" would also pass if the config had disabled
        # everything, which is exactly the false green worth avoiding. Both
        # are WARN lines now, so the count on the verdict line is what moves.
        def warned(out: str) -> int:
            return int(re.search(r'; (\d+) warning\(s\)', out).group(1))

        # U1 is stock-ON and warns on any fixture tree holding one state per
        # kind, so this case pins the roster to the rules it is actually about.
        # Counting a constant would make the delta this asserts meaningless.
        with tree(feature_status='planning', story_statuses=('done',),
                  config='[pm]\nchecks = ["D1","D2","D3","D4","D5","D6",'
                         '"V1","V4","V5"]\n') as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0)
            self.assertIn('all stories done, feature still planning', out)
            before = warned(out)
            write_config(root, '[pm]\nchecks = ["D1","D3","D4","D5","D6"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0)
            self.assertNotIn('all stories done', out)
            self.assertIn('two places in this tree disagree', out)
            # Exactly D2's line left the count (the READY warnings the default
            # tree carries are not `[pm] checks`' and stay).
            self.assertEqual(warned(out), before - 1)


class ReadyIsAStampWithACheck(unittest.TestCase):
    """Story 02 of the-code-knows-entry-and-exit: `pm <kind> ready <id>` is
    the only stamp, and what `ready` MEANS is a `  WARN  ` line from
    `check pm`, never a finding and never an exit code.

    NO EXISTING CASE COULD FAIL FOR THIS. Every case in this module reads a
    grain's frontmatter; none reads a section body, and `support.pm.write`
    gives every grain the body `x` — so a gate that never opened
    `## Acceptance criteria` passed all of them. These cases write the three
    sections `pm new` scaffolds, empty (the template's HTML prompt only) and
    filled, and hold the exit code at 0 on both sides.
    """

    PROMPT = '<!-- What must be TRUE. One line each, and each one able to fail. -->'

    def _story(self, root, status, body):
        # `owner:` set, because a story in progress without one is its own
        # READY warning since 0.4.0 — and these cases are about the SECTION,
        # so a second line in the output would make them assert two things.
        write(root / STORY_REL,
              {'id': '0.1/alpha/s0', 'feature': '0.1/alpha',
               'milestone': '"0.1"', 'name': 'S0', 'status': status,
               'owner': 'ada'}, body)

    # Both feature sections the READY family reads, so a case about the
    # STORY sees only the story's line. `## Proof budget` joined in
    # 0.4.0/the-tree-names-what-it-lacks — the anti-bloat contract that
    # every template carried and nothing had ever checked was filled in.
    SHIP = ('# Alpha\n\n## Ship criterion\n\nIt ships.\n\n'
            '## Proof budget\n\n  cases: 2\n')

    def _settle(self, root):
        """The milestone and the feature with nothing left to warn about, so
        a case about the STORY sees only the story's line."""
        write(root / FFILE_REL, {'id': '0.1/alpha', 'milestone': '"0.1"',
                                 'name': 'Alpha', 'status': 'building',
                                 'reviewed': '', 'phase': '1'}, self.SHIP)
        write(root / MFILE_REL, {'id': '"0.1"', 'name': 'Demo',
                                 'status': 'building',
                                 'branch': 'milestone/0.1'}, self.SHIP)
        # An `in_progress` milestone also wants its handoff; it is never
        # auto-minted, so the fixture writes one or the milestone's own line
        # drowns the story's.
        model.shared_doc(cfg_for(root), root / MFILE_REL,
                         model.HANDOFF_FILE_NAME).write_text(
            model.SLOT_HEADER[model.HANDOFF_FILE_NAME] + '\n',
            encoding='utf-8')

    def test_a_story_in_progress_with_no_owner_warns(self):
        """A LIVE BUG, not a tidy-up. `pm-execution.md` step 1 says to set
        `owner:` in the same edit as the claim; `execlist.py` and `cli.py` both
        READ the field; nothing asked whether it was there. So a tree could run
        a whole milestone with every story unowned and the gate silent.

        Asked of the CATEGORY, never the word — a project spelling its
        in-progress state `wip` gets the same line.
        """
        for status, owner, expect in (('building', '', True),
                                      ('building', 'ada', False),
                                      ('ready', '', False),
                                      ('done', '', False)):
            with self.subTest(status=status, owner=owner), \
                    tree(feature_status='building', story_statuses=(),
                         config='[pm]\nchecks = ["D1","D2","D3","D4","D5",'
                                '"D6","V1","V4","V5"]\n') as root:
                self._settle(root)
                write(root / STORY_REL,
                      {'id': '0.1/alpha/s0', 'feature': '0.1/alpha',
                       'milestone': '"0.1"', 'name': 'S0', 'status': status,
                       'owner': owner},
                      '# S0\n\n## Acceptance criteria\n\n- it works\n')
                code, out = run_gate(root)
                # A WARN, never the exit code.
                self.assertEqual(code, 0, out)
                self.assertEqual('carries no owner:' in out, expect, out)

    def test_each_warning_fires_on_the_scaffold_and_is_silent_on_a_filled_grain(self):
        empty = f'# S0\n\n## Acceptance criteria\n\n{self.PROMPT}\n\n## Out of scope\n'
        filled = empty.replace(self.PROMPT, '- the gate says so\n')
        # A story past `todo` whose section holds only the template's prompt
        # warns; the same story with one line under the heading does not; a
        # story still in `todo` — `planning` OR `ready`, the category and not
        # the word — is not asked. Exit 0 throughout.
        for status, body, expect in (('building', empty, True),
                                     ('done', empty, True),
                                     ('building', filled, False),
                                     ('ready', empty, False),
                                     ('planning', empty, False)):
            with self.subTest(status=status, filled=body is filled), \
                    tree(feature_status='building',
                         story_statuses=('ready',),
                         config='[pm]\nchecks = ["D1","D2","D3","D4","D5",'
                                '"D6","V1","V4","V5"]\n') as root:
                self._settle(root)
                self._story(root, status, body)
                code, out = run_gate(root)
                self.assertEqual(code, 0, out)
                line = "story 0.1/alpha/s0 is %r and has an empty `## Acceptance criteria`" % status
                self.assertEqual(line in out, expect, out)
                self.assertEqual('warning(s)' in out, expect, out)
        # The feature's and the milestone's own sections, plus the
        # frontmatter fact a milestone past `todo` needs: a branch. A grain
        # with NO such heading at all says so in different words from an empty
        # one. (`phase:` retired in 0.4.0 with the grouping it fed — the
        # milestone's own `order:` sequences its features now.)
        with tree(milestone_status='building', feature_status='building',
                  story_statuses=(),
                  config='[pm]\nchecks = ["D1","D2","D3","D4","D5","D6",'
                         '"V1","V4","V5"]\n') as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            for needle in ("milestone 0.1 is 'building' with no branch:",
                           "milestone 0.1 is 'building' and has no `## Ship criterion` section",
                           "feature 0.1/alpha is 'building' with no stories",
                           "feature 0.1/alpha is 'building' and has no `## Ship criterion` section",
                           # Never auto-minted, so the ABSENCE is the signal —
                           # and the line names the verb that fills it.
                           "milestone 0.1 is 'building' with no handoff.md",
                           # The anti-bloat contract, which every feature
                           # template carried and nothing had ever checked was
                           # filled in (0.4.0/the-tree-names-what-it-lacks).
                           "feature 0.1/alpha is 'building' and has no `## Proof budget` section"):
                self.assertIn(f'  WARN  {needle}', out, out)
            self.assertIn('; 6 warning(s)', out)
            self.assertNotIn('DRIFT', out)
            # Filled: the sections written, the branch stamped, one story
            # under the feature — silent, and the verdict line is the plain
            # one.
            write(root / FFILE_REL, {'id': '0.1/alpha', 'milestone': '"0.1"',
                                     'name': 'Alpha', 'status': 'building',
                                     'reviewed': ''}, self.SHIP)
            write(root / MFILE_REL, {'id': '"0.1"', 'name': 'Demo',
                                     'status': 'building',
                                     'branch': 'milestone/0.1'}, self.SHIP)
            model.shared_doc(cfg_for(root), root / MFILE_REL,
                             model.HANDOFF_FILE_NAME).write_text(
                model.SLOT_HEADER[model.HANDOFF_FILE_NAME] + '\n',
                encoding='utf-8')
            self._story(root, 'planning', 'x')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('WARN', out)
            self.assertNotIn('warning(s)', out)

    def test_left_todo_is_the_category_not_the_order_within_it(self):
        # "Has left `todo`" is asked of the CATEGORY: under a renamed flow a
        # `doing` story is asked, neither `todo` word is, and swapping the two
        # `todo` words — no word renamed, none moved — changes no count. The
        # first cut keyed on "past the FIRST todo word", and the swap alone
        # took this repo's own tree from 7 WARN to 13 (V3 of the review).
        counts = []
        for order in (('queued', 'shaped'), ('shaped', 'queued')):
            renamed = {'todo': order, 'in_progress': ('doing',),
                       'done': ('shipped',)}
            for status, expect in (('doing', True), ('shaped', False),
                                   ('queued', False)):
                with self.subTest(order=order, status=status), \
                        tree(feature_status='building',
                             story_statuses=('ready',)) as root:
                    write_config(root, declaring(story=renamed))
                    self._settle(root)
                    self._story(root, status, 'x')
                    code, out = run_gate(root)
                    self.assertEqual(code, 0, out)
                    self.assertEqual(
                        f"story 0.1/alpha/s0 is {status!r} and has no "
                        f"`## Acceptance criteria` section" in out, expect, out)
                    counts.append((status, out.count('  WARN  ')))
                    cfg = cfg_for(root)
                    self.assertTrue(model.left_todo(cfg, 'story', 'doing'))
                    self.assertTrue(model.left_todo(cfg, 'story', 'shipped'))
                    self.assertFalse(model.left_todo(cfg, 'story', 'shaped'))
                    self.assertFalse(model.left_todo(cfg, 'story', 'queued'))
                    self.assertFalse(model.left_todo(cfg, 'story', 'wombat'))
        self.assertEqual(counts[:3], counts[3:], counts)

    def test_the_section_reader_stops_at_the_next_heading_and_sees_through_comments(self):
        text = ('---\nstatus: ready\n---\n# T\n\n## Acceptance criteria\n'
                '<!-- a\nmulti-line\nprompt -->\n\n## Out of scope\n- real\n')
        lines = model.section_lines(text, model.ACCEPTANCE_HEADING)
        self.assertEqual(lines, ['<!-- a', 'multi-line', 'prompt -->', ''])
        self.assertTrue(model.section_is_empty(lines))
        self.assertFalse(model.section_is_empty(['<!-- x --> said', '']))
        self.assertIsNone(model.section_lines(text, model.SHIP_HEADING))
        # `### Acceptance criteria` is not the scaffolded heading.
        self.assertIsNone(model.section_lines(
            text.replace('## Acceptance', '### Acceptance'),
            model.ACCEPTANCE_HEADING))


FFILE_REL = 'pm/roadmap/features/alpha.md'
MFILE_REL = 'pm/roadmap/milestones/0.1.md'


# The one ordered vocabulary the SEED writes — and that it is the seed, not a
# default the reader falls back to — is pinned once, in tests/test_pm_flow.py
# (`test_the_seed_is_the_installables_LIVE_section_and_a_tree_seeded_with_it_LOADS`).
# The `OneLifecycleAcrossGrains` golden that lived here pinned the same seven
# words as `DEFAULT_*_STATES` and the pivot/terminal names D5 and the ledger
# read BY NAME; no rule reads a name now, and those constants are gone.


class D5AStoryAheadOfItsFeature(unittest.TestCase):
    """D5 — a story at work while its feature says it has not started.

    The rule D5 USED to be ("a done story under a non-done feature") reported
    the normal path under this lifecycle: a story finishes while its feature is
    still `reviewing`, `accepted` or `packaging`, so every feature in every
    tree would have carried a finding. Asked of the two CATEGORIES — the story
    has left `todo`, the feature is still in it — it is the same question in
    every vocabulary.

    Every fixture below carries TWO stories so D2 stays quiet (it fires only
    when they are ALL done) — the exit code then belongs to D5 alone.
    """

    MSG = 'two places in this tree disagree'

    def _gate(self, feature_status, story_statuses):
        with tree(milestone_status='building', feature_status=feature_status,
                  story_statuses=story_statuses) as root:
            return run_gate(root)

    def test_the_normal_path_is_not_drift(self):
        # THE regression: a story finishing while its feature is still under
        # review (or still building) is how every feature closes. Plus the
        # other quiet shape — a PO writing stories against a feature that is
        # still being shaped. The seed's feature flow holds `building` and
        # `reviewing`; `accepted`/`packaging` are milestone acts now.
        for fstat, stories in (('reviewing', ('done', 'ready')),
                               ('building', ('done', 'ready')),
                               ('planning', ('planning', 'ready'))):
            with self.subTest(feature=fstat, stories=stories):
                code, out = self._gate(fstat, stories)
                self.assertEqual(code, 0, out)
                self.assertNotIn(self.MSG, out)

    def test_a_story_at_work_under_a_feature_still_being_shaped_IS_drift(self):
        # The direction D5 exists for, and the payoff of one vocabulary:
        # `done` is no longer the only story state the rule can see. A story
        # BUILDING under a feature that says it has not started is the same
        # disagreement, and the old equality was blind to it.
        started = [st for cat in (model.IN_PROGRESS, model.DONE_CATEGORY)
                   for st in model.DEFAULT_FLOWS['story'][cat]]
        assert started == ['building', 'done', 'obe'], started
        for fstat in ('planning', 'ready'):
            for sstat in started:
                with self.subTest(feature=fstat, story=sstat):
                    code, out = self._gate(fstat, (sstat, 'ready'))
                    # A WARN, never a finding: exit 0, counted.
                    self.assertEqual(code, 0, out)
                    self.assertIn(f'  WARN  story 0.1/alpha/s0 is {sstat!r}', out)
                    self.assertIn(self.MSG, out)
                    self.assertIn(f"is still {fstat!r} (todo)", out)
                    self.assertIn('the story is at work', out)
                    self.assertIn('warning(s)', out)

    def test_a_vocabulary_without_the_word_building_still_answers(self):
        # A project may rename the vocabulary. The 0.2.0 rule indexed each
        # list for `building` and, finding none, printed a NOTE that it was
        # reporting nothing — a category is always placeable, so there is no
        # blind vocabulary and no note. `done` under a `queued` feature is the
        # disagreement whatever the words are.
        renamed = {'todo': ('queued',), 'in_progress': ('doing',),
                   'done': ('done',)}
        with tree(feature_status='queued', story_statuses=('done', 'queued')) \
                as root:
            write_config(root, declaring('[pm]\nchecks = ["D4","D5"]\n',
                                         story=renamed, feature=renamed))
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn(self.MSG, out)
            self.assertNotIn('cannot place', out)

    # The question is asked of two CATEGORIES, so the ORDER a project lists
    # its words in within a category cannot move anything: the 0.2.0 rule was
    # an index comparison and a set authored alphabetically moved the pivot
    # for one grain and not the other, producing "the story is at work and the
    # feature says it has not started" about `planning` and `planning`. The
    # two declarations below hold the seed's words alphabetised inside each
    # category, one per grain kind, and the third is the review's repro set
    # (a `blocked` word in `in_progress`, the rest alphabetical).
    def _alphabetised(kind: str) -> dict:
        return {cat: tuple(sorted(states))
                for cat, states in model.DEFAULT_FLOWS[kind].items()}

    SORTED_STORY_SET = declaring('[pm]\nchecks = ["D4","D5"]\n',
                                 story=_alphabetised('story'))
    SORTED_FEATURE_SET = declaring('[pm]\nchecks = ["D4","D5"]\n',
                                   feature=_alphabetised('feature'))
    REVIEW_REPRO = declaring('[pm]\nchecks = ["D5"]\n', story={
        'todo': ('planning', 'ready'),
        'in_progress': ('blocked', 'building', 'reviewing'),
        'done': ('done',)})

    def _gate_with(self, config, feature_status, story_statuses):
        with tree(milestone_status='building', feature_status=feature_status,
                  story_statuses=story_statuses) as root:
            write_config(root, config)
            return run_gate(root)

    # The words BOTH kinds declare: the same word on a story and its feature
    # is only askable where both flows hold it (a story never holds
    # `accepted`; that is D4's finding, not D5's question).
    SHARED = [st for st in model.LIFECYCLE
              if all(any(st in sts for sts in model.DEFAULT_FLOWS[k].values())
                     for k in ('story', 'feature'))]

    def test_one_word_on_both_sides_is_never_a_disagreement(self):
        assert self.SHARED == ['planning', 'ready', 'building', 'done']
        for config in (self.SORTED_STORY_SET, self.SORTED_FEATURE_SET):
            for status in self.SHARED:
                with self.subTest(config=config.split('\n')[1], status=status):
                    code, out = self._gate_with(config, status,
                                                (status, status))
                    self.assertNotIn(self.MSG, out)
                    self.assertEqual(code, 0, out)
        code, out = self._gate_with(self.REVIEW_REPRO, 'planning',
                                    ('planning', 'planning'))
        self.assertNotIn(self.MSG, out)
        self.assertEqual(code, 0, out)

    def test_the_rule_still_fires_when_the_two_words_really_differ(self):
        # The other half: the guard is about the CATEGORIES, not about muting
        # D5 under a custom set. Same config, a genuine disagreement, still a
        # finding — otherwise the case above would pass over a dead rule.
        code, out = self._gate_with(self.SORTED_STORY_SET, 'planning',
                                    ('building', 'ready'))
        self.assertEqual(code, 0, out)
        self.assertIn(self.MSG, out)
        self.assertIn('  WARN  ', out)


class ConfigValidation(unittest.TestCase):
    """A malformed `[pm]` must never narrow the gate into a rubber stamp.

    A bare string iterates into characters and a table into keys, so an
    unvalidated `checks` silently disables every rule and prints PASS over real
    drift. Each spelling here is a plausible authoring mistake.
    """

    def _drifted(self, root: Path) -> None:
        write(root / 'pm/roadmap/stories/s0.md',
              {'id': '0.1/alpha/s0', 'feature': '0.1/alpha', 'milestone': '"0.1"',
               'name': 'S0', 'status': 'banana'})

    def test_a_malformed_pm_section_is_a_config_error_not_a_pass(self):
        for bad in ('checks = "D1"', 'checks = ["D99"]', 'checks = ["d1","d4"]',
                    'checks = 7', 'checks = []', 'checks = { a = 1 }',
                    'review_slug_fallback = "yes"', 'roadmap_dir = 3'):
            with self.subTest(bad=bad), tree(story_statuses=('ready',)) as root:
                self._drifted(root)
                write_config(root, f'[pm]\n{bad}\n')
                code, _ = run_gate(root)
                # 2 = config error. NEVER 0 — that is the rubber stamp.
                self.assertEqual(code, 2, f'{bad!r} must not be accepted')

    def test_a_valid_subset_still_narrows_correctly(self):
        with tree(story_statuses=('ready',)) as root:
            self._drifted(root)
            write_config(root, '[pm]\nchecks = ["D1","D2"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)   # D4 is off, so the bogus status is quiet


class AStaleRuleIdStopsTheGATE_NotTheReadVerbs(unittest.TestCase):
    """One retired id in `[pm] checks` must not take the whole CLI down.

    A version bump that retires a rule is exactly what leaves a stale id in a
    consumer's config, and one consumer names sixteen rules explicitly. Raised
    from `model.load()`, that typo killed `pm status`, `pm get`, `pm new`,
    `pm validate`, `pm vocabulary --json` and `check pm` at exit 2 together —
    so the consumer could neither read its own tree nor ask the tool what the
    new vocabulary is while deciding what to do about it.

    The strictness is right; the placement was not. The GATES refuse, because
    a narrowed roster is a lie told by a gate. Everything that only READS is
    still readable.
    """

    STALE = '[pm]\nchecks = ["D1","D2","D3","D4","D5","D6","D99"]\n'

    def test_the_verbs_still_run(self):
        with tree(story_statuses=('ready',)) as root:
            write_config(root, self.STALE)
            for argv in (('status',), ('vocabulary', '--json'),
                         ('get', '0.1/alpha', 'status'),
                         ('new', 'story', '0.1/alpha', 's9', 'S9'),
                         ('story', 'building', '0.1/alpha/s0')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 0, out)
            self.assertIn('milestone 0.1', run_cli(root, 'status')[1])

    def test_the_two_gates_refuse_loudly_and_name_the_id(self):
        with tree(story_statuses=('ready',)) as root:
            write_config(root, self.STALE)
            code, out = run_gate(root)
            self.assertEqual(code, 2, out)
            code, out = run_cli(root, 'validate')
            self.assertEqual(code, 2, out)
            self.assertIn('D99', out)


class RetiredConfigIsRefusedByName(unittest.TestCase):
    """A key the tracker stopped reading is REFUSED by name, never ignored.

    The mechanism is the `RETIRED_KEYS` / `RETIRED_SECTIONS` ledger in
    model.py — the executable tombstone that keeps a consumer arriving from an
    older pin from shipping config that silently does nothing (a config key
    that does nothing is worse than one that errors: the author believes it
    took effect). One key and one section stand in for the roster; the ledger
    itself is the enumeration, so a per-key table here would be a copy of it.
    """

    def test_a_retired_key_or_section_stops_the_gates_and_not_the_read_verbs(self):
        # `[agents]` was a whole config surface, and `config_section` cannot
        # tell an absent table from an empty one — both spellings must land.
        for body, named in (
                ('[pm]\nplace_branch_on_building = true\n',
                 'place_branch_on_building was retired'),
                ('[agents]\nscope = [".claude/agents/*.md"]\n',
                 '[agents] was retired'),
                ('[agents]\n', '[agents] was retired')):
            with self.subTest(body=body), tree(story_statuses=('ready',)) as root:
                write_config(root, body)
                code, out = gate_both_streams(root)
                self.assertEqual(code, 2, out)
                self.assertIn(named, out)
                # `pm validate` is the second gate and names it the same way.
                code, out = run_cli(root, 'validate')
                self.assertEqual(code, 2, out)
                self.assertIn(named, out)
                # Reported where a stale rule id is — on the GATES — so a
                # project can still read its own tree while deciding what to
                # do about the dead key.
                self.assertEqual(run_cli(root, 'status')[0], 0)
                self.assertEqual(run_cli(root, 'vocabulary', '--json')[0], 0)


class FlowChecks(unittest.TestCase):
    """D9/D10 — branch-per-milestone and the mainline guard. Both are OPT-IN
    (decision D3): a project running D9 alone is running a different valid
    flow, not drifting. D8 lived here and became R5, below.
    """

    def test_off_unless_named(self):
        # Every input the two rules exist to catch, on the stock roster.
        for branch, version in (('', '0.1'),        # D9: no branch stamp
                                ('main', '0.1')):   # D10: the mainline
            with self.subTest(branch=branch, version=version), \
                    tree(story_statuses=('ready',)) as root:
                building_milestone(root, branch=branch, version=version)
                code, out = run_gate(root)
                self.assertEqual(code, 0, out)

    def test_each_flow_rule_fires_when_it_is_named(self):
        # (checks, branch, version, extra config, the line the finding carries)
        rows = (
            ('["D9"]', '', '0.1', '', 'declares no branch:'),
            ('["D10"]', 'main', '0.1', '', 'the mainline itself'),
            ('["D10"]', '', '0.1', '', 'needs a branch off the mainline'),
            # `[repo_hygiene] mainline` is a git ref and keeps `origin/`; D10
            # compares against an authored `branch:` string, which never
            # carries a remote qualifier, so `origin/trunk` must read as
            # `trunk` — proved on a NON-stock value so the assertion cannot
            # pass by accident on the untouched default.
            ('["D10"]', 'trunk', '0.1',
             '[repo_hygiene]\nmainline = "origin/trunk"\n', "'trunk'"),
        )
        for checks, branch, version, extra, message in rows:
            with self.subTest(checks=checks, branch=branch), \
                    tree(story_statuses=('ready',)) as root:
                building_milestone(root, branch=branch, version=version)
                write_config(root, f'[pm]\nchecks = {checks}\n{extra}')
                code, out = run_gate(root)
                self.assertEqual(code, 1, out)
                self.assertIn(message, out)

    def test_a_correct_tree_passes_each_rule_that_names_it(self):
        # The other side of every row above, including the opt-in split: D9
        # only requires SOME stamp, so it does not refuse the mainline.
        for checks, branch in (('["D9"]', 'staging'),
                               ('["D10"]', 'milestone/0.1-demo'),
                               ('["D9"]', 'main')):
            with self.subTest(checks=checks, branch=branch), \
                    tree(story_statuses=('ready',)) as root:
                building_milestone(root, branch=branch, version='0.1')
                write_config(root, f'[pm]\nchecks = {checks}\n')
                code, out = run_gate(root)
                self.assertEqual(code, 0, out)
                self.assertNotIn('unknown rule', out)


class U2ATreeThatIsNotRecordingSaysSo(unittest.TestCase):
    """U2 — the ledger couriers are wired and the tree holds no row.

    **The rule this milestone opened on.** The hooks were installed,
    executable, self-testing and firing for the whole of the previous
    milestone; the verb they called refused every row; and a courier fails
    open by design, so the refusal went to a stderr nobody reads. Zero rows,
    zero complaints, for weeks.

    The four cases are the whole contract, and the third is the one a rule
    written from its own bug gets wrong: a tree that wires NOTHING is silent,
    because it opted out and this package does not conscript (0.4.0/D5).
    """

    SETTINGS = '.claude/settings.json'
    WIRED = ('{"hooks": {"Stop": [{"hooks": [{"type": "command", '
             '"command": "bash tools/hooks/cc-ledger-session.sh"}]}]}}')

    def _settings(self, root, text: str) -> None:
        path = root / self.SETTINGS
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def _gate(self, root):
        write_config(root, '[pm]\nchecks = ["U2"]\n')
        return run_gate(root)

    def test_wired_and_no_rows_warns_and_names_the_causes(self):
        with tree(story_statuses=('ready',)) as root:
            self._settings(root, self.WIRED)
            code, out = self._gate(root)
            # A WARN, never the exit code: recording is a posture, not a
            # requirement, and a rule that reddens a fresh consumer is undone
            # within a version.
            self.assertEqual(code, 0, out)
            self.assertIn('recording NOTHING', out)
            self.assertIn('.PHONY', out)
            self.assertIn('[pm.states.*]', out)
            self.assertIn('--self-test', out)

    def test_wired_with_a_row_anywhere_is_silent(self):
        # Either home satisfies it (0.4.0/D3): the question is whether
        # recording is happening at all, and a row in either answers it.
        for rel in ('pm/roadmap/ledger.jsonl',
                    'pm/roadmap/ledgers/0.1.jsonl'):
            with self.subTest(rel=rel), tree(story_statuses=('ready',)) as root:
                self._settings(root, self.WIRED)
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(
                    '{"ts":"2026-09-06T00:00:00Z","kind":"gate","gate":"check",'
                    '"verdict":"PASS","duration_ms":1}\n', encoding='utf-8')
                code, out = self._gate(root)
                self.assertEqual(code, 0, out)
                self.assertNotIn('recording NOTHING', out)

    def test_an_empty_ledger_file_is_not_a_row(self):
        """What a courier leaves behind when it created the file and then
        refused the row — the exact shape of the failure, so existence must
        not be mistaken for recording."""
        with tree(story_statuses=('ready',)) as root:
            self._settings(root, self.WIRED)
            (root / 'pm/roadmap/ledger.jsonl').write_text('', encoding='utf-8')
            code, out = self._gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('recording NOTHING', out)

    def test_a_tree_that_wires_nothing_is_silent(self):
        """THE OPT-OUT, and the case a rule written from its own bug gets
        wrong. No hooks wired is not a broken tree; it is a choice, and this
        package does not conscript."""
        for text in ('{}', '{"hooks": {"Stop": []}}'):
            with self.subTest(text=text), tree(story_statuses=('ready',)) as root:
                self._settings(root, text)
                code, out = self._gate(root)
                self.assertEqual(code, 0, out)
                self.assertNotIn('recording NOTHING', out)
        # And no settings file at all.
        with tree(story_statuses=('ready',)) as root:
            code, out = self._gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('U2', out)

    def test_a_settings_file_that_cannot_be_read_is_UNVERIFIABLE(self):
        """The standing convention for a pointer the gate cannot follow: said
        out loud, never counted as a pass and never a failure."""
        with tree(story_statuses=('ready',)) as root:
            path = root / self.SETTINGS
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'\xff\xfe not utf-8 \x00')
            code, out = self._gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('UNVERIFIABLE', out)

    def test_it_is_off_unless_named(self):
        with tree(story_statuses=('ready',)) as root:
            self._settings(root, self.WIRED)
            write_config(root, '[pm]\nchecks = ["D1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('recording NOTHING', out)


class R5GradesTheCurrentRelease(unittest.TestCase):
    """R5 — the version file equals the CURRENT entry in `order`.

    D8's three cases (match / mismatch / no version in the file) carry over
    unchanged in what they assert; what moved is where the expected value is
    read FROM — a position in the plan rather than the id of whichever
    milestone is in progress. The sin guarded is rule 4's first: a version file
    that disagrees with the plan while the gate prints PASS.
    """

    @staticmethod
    def _planned(root: Path, *mids: str) -> None:
        body = '\n'.join(f'  - "{m}"' for m in mids)
        (root / 'pm/roadmap/releases.md').write_text(
            f'---\nid: roadmap\nkind: roadmap\norder:\n{body}\n---\n\n'
            f'The plan.\n', encoding='utf-8')

    @staticmethod
    def _claims(root: Path, mid: str, version: str, status: str) -> None:
        write(root / f'pm/roadmap/milestones/{mid}.md',
              {'id': f'"{mid}"', 'kind': 'milestone', 'name': mid,
               'status': status, 'version': f'"{version}"'})

    def _tree(self, version: str, config: str = '[pm]\nchecks = ["R5"]\n'):
        ctx = tree(milestone_status='building', story_statuses=('ready',))
        root = ctx.__enter__()
        (root / 'pyproject.toml').write_text(
            f'[project]\nversion = "{version}"\n', encoding='utf-8')
        # The plan sequences the MILESTONES; each one's `version:` says which
        # release it is, and R5 grades the version FILE against that.
        self._planned(root, 'a', 'b')
        self._claims(root, 'a', '0.0.9', 'done')
        self._claims(root, 'b', '0.1.0', 'building')
        write_config(root, config)
        return ctx, root

    def test_off_unless_named(self):
        ctx, root = self._tree('9.9.9', config='')
        try:
            self.assertEqual(run_gate(root)[0], 0)
        finally:
            ctx.__exit__(None, None, None)

    def test_the_current_release_is_graded_and_a_mismatch_names_both(self):
        # `start`: current is 0.1.0, the first entry not yet shipped.
        for version, expected in (('0.1.0', 0), ('9.9.9', 1)):
            with self.subTest(version=version):
                ctx, root = self._tree(version)
                try:
                    code, out = run_gate(root)
                    self.assertEqual(code, expected, out)
                    if expected:
                        self.assertIn('(R5)', out)
                        self.assertIn("'9.9.9'", out)   # what the file says
                        self.assertIn("'0.1.0'", out)   # what the plan says
                        self.assertIn("'b'", out)       # the milestone claiming it
                    else:
                        self.assertNotIn('(R5)', out)
                finally:
                    ctx.__exit__(None, None, None)

    def test_version_at_ship_grades_the_last_shipped_entry_instead(self):
        # The same tree, the other flow: this package bumps at CLOSE, so the
        # version file should still read 0.0.9 while 0.1.0 is being built.
        config = '[pm]\nchecks = ["R5"]\nversion_at = "ship"\n'
        for version, expected in (('0.0.9', 0), ('0.1.0', 1)):
            with self.subTest(version=version):
                ctx, root = self._tree(version, config=config)
                try:
                    code, out = run_gate(root)
                    self.assertEqual(code, expected, out)
                finally:
                    ctx.__exit__(None, None, None)

    def test_no_version_in_the_file_is_a_finding(self):
        ctx, root = self._tree('0.1.0')
        try:
            (root / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('no version found', out)
        finally:
            ctx.__exit__(None, None, None)

    def test_a_tree_with_no_plan_warns_and_never_reddens(self):
        # Milestone risk 1: a rule that fails every fresh consumer is a rule
        # that gets switched off within a version.
        ctx, root = self._tree('0.1.0')
        try:
            (root / 'pm/roadmap/releases.md').unlink()
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('WARN', out)
            self.assertIn('pm add roadmap <milestone-id>', out)
        finally:
            ctx.__exit__(None, None, None)

    def test_d8_in_the_roster_is_named_as_retired_never_as_unknown(self):
        # A consumer whose config still lists D8 is told where the rule went.
        # Silently ungating it would be rule 4's first sin wearing a typo.
        with tree() as root:
            write_config(root, '[pm]\nchecks = ["D8"]\n')
            code, out = gate_both_streams(root)
            self.assertEqual(code, 2, out)
            self.assertIn('D8', out)
            self.assertIn('retired', out)
            self.assertIn('R5', out)
            self.assertNotIn('unknown rule', out)


class ConfigValueErrors(unittest.TestCase):
    def test_a_bad_version_at_is_exit_2_not_a_finding(self):
        # Review F8: the criterion says "at exit 2" and its first proof only
        # asserted that `load()` raises. This is the exit-code half, in the
        # exit-2 family where §6's amend-first ordering puts it.
        for bad in ('version_at = "whenever"', 'version_at = "START"',
                    'version_at = ""', 'version_at = 7'):
            with self.subTest(bad=bad), tree() as root:
                write_config(root, f'[pm]\nchecks = ["R5"]\n{bad}\n')
                self.assertEqual(gate_both_streams(root)[0], 2)

    def test_a_bad_version_pattern_is_exit_2_not_a_finding(self):
        for bad in ('version_pattern = "version = \\"(.*\\""',
                    'version_pattern = "^version = .*$"'):
            with self.subTest(bad=bad), tree() as root:
                write_config(root, f'[pm]\nchecks = ["R5"]\n{bad}\n')
                self.assertEqual(run_gate(root)[0], 2)

    def test_a_path_key_outside_the_checkout_is_refused_not_followed(self):
        """Hard rule 8, in the three `[pm]` keys that are joined onto the root.

        `check grain-shape` was the reported violation, but `roadmap_dir` has a
        second reader and the tracker had the SAME hole — measured on the
        unfixed tracker, 2026-09-05, against a milestone in a sibling tempdir:

            $ pm status                 # roadmap_dir = "<abs>"  and "../out"
            milestone 0.1.0      [done]
            EXIT=0
            $ check pm                  # both spellings
            [check:pm] scanning active PM tree (../out/, excluding zz_archive/)
            [check:pm] PASS — no PM-tree status drift; scanned 1 milestone(s)…
            EXIT=0

        What it did NOT have is the gate's traceback: `PmConfig.rel` catches the
        `ValueError` and falls back to the absolute path, so the tracker
        reported serenely about a tree outside the checkout instead of crashing
        over it. `template_dir` is the loudest of the three because
        `pm templates` WRITES there — six files installed outside the
        checkout, on the unfixed tracker, at exit 0.
        """
        # The five POOL keys go through the same `relpath`, and one case each
        # proves the REUSE — inventing a second matrix for them is the finding,
        # not the coverage (SDLC § 5).
        for key in ('roadmap_dir', 'review_dir', 'template_dir',
                    'milestone_dir', 'feature_dir', 'story_dir', 'bug_dir',
                    'ledger_dir'):
            for value in ('/tmp/elsewhere', '../outside'):
                with self.subTest(key=key, value=value), tree() as root:
                    # A Python repr is a TOML LITERAL string, so a `\` in a
                    # value reaches the guard instead of the TOML parser.
                    write_config(root, f'[pm]\n{key} = {value!r}\n')
                    code, out = gate_both_streams(root)
                    # 2, not 1: a devkit.toml mistake is not PM drift.
                    self.assertEqual(code, 2, f'{key} = {value!r}\n{out}')
                    self.assertIn(key, out)
                    self.assertIn(value, out)

    def test_a_path_key_inside_the_checkout_still_loads(self):
        """The refusal's other half — rule 5. `pm/roadmap/` with a trailing
        slash and `./pm/roadmap` both stay inside, and a guard that reddened
        them would break a consumer at upgrade rather than at a wrong value."""
        for value in ('pm/roadmap/', './pm/roadmap'):
            with self.subTest(value=value), tree() as root:
                write_config(root, f'[pm]\nroadmap_dir = {value!r}\n')
                code, out = run_gate(root)
                self.assertEqual(code, 0, f'{value!r}\n{out}')

    def test_a_declared_pool_is_read_from_where_it_says(self):
        """`[pm] milestone_dir` and friends, and the equivalence rule 5 asks
        for: a tree declaring every stock value behaves byte-identically to one
        declaring none.

        The pools are four keys rather than one `roadmap_dir` because **the
        shape of the config is the shape of the model** — reading the file
        tells you there are four kinds and that they are peers, which one root
        never could.
        """
        with tree(story_statuses=('ready',)) as root:
            silent = run_gate(root)
            write_config(root, '[pm]\n'
                               'milestone_dir = "pm/roadmap/milestones"\n'
                               'feature_dir = "pm/roadmap/features"\n'
                               'story_dir = "pm/roadmap/stories"\n'
                               'bug_dir = "pm/roadmap/bugs"\n'
                               'ledger_dir = "pm/roadmap/ledgers"\n')
            self.assertEqual(run_gate(root), silent)

        # ...and a pool declared SOMEWHERE ELSE is read from there. Moved, not
        # copied: if the reader still fell back to `<roadmap>/features`, the
        # census would count the same feature twice or not at all.
        with tree(story_statuses=('ready',)) as root:
            write_config(root, '[pm]\nfeature_dir = "planning/features"\n')
            moved = root / 'planning/features'
            moved.mkdir(parents=True)
            (root / 'pm/roadmap/features/alpha.md').rename(moved / 'alpha.md')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 feature(s)', out)

    def test_a_milestones_ledger_follows_the_configured_ledger_dir(self):
        # D3 put rows in two places — one per milestone, and the tree's own for
        # the rows naming no grain — and a key that moved only one of them
        # would split the ledger across two roots with nothing saying so.
        from agentic_sdlc.repo.pm import ledger
        with tree(story_statuses=('ready',)) as root:
            write_config(root, '[pm]\nledger_dir = "pm/logs"\n')
            cfg = cfg_for(root)
            rel = lambda p: str(p.relative_to(cfg.root))
            self.assertEqual(rel(ledger.ledgers_dir(cfg)), 'pm/logs')
            self.assertEqual(rel(ledger.ledger_for(cfg, '0.1')),
                             'pm/logs/0.1.jsonl')
            # An attributed row, through the CLI, landing under the declared
            # home rather than under the roadmap.
            self.assertEqual(run_cli(root, 'ledger', 'record', '--grain',
                                     '0.1/alpha', '--event', 'Stop')[0], 0)
            self.assertTrue((root / 'pm/logs/0.1.jsonl').is_file())

    def test_scaffold_misconfiguration_is_refused_not_ignored(self):
        for bad in ('[pm.scaffold]\nmilestone = "theme,risk"',
                    '[pm.scaffold.epic]\nx = "y"',
                    '[pm.scaffold.story]\ntags = ["a"]'):
            with self.subTest(bad=bad), tree() as root:
                write_config(root, f'[pm]\n{bad}\n')
                self.assertEqual(run_gate(root)[0], 2)


class EveryConfigSection(unittest.TestCase):
    """The gap that let a false PASS survive a refactor meant to remove it.

    Every exit-2 config assertion lived in test_pm.py, so `[defaults]` kept the
    literal `tuple(cfg.get(...))` CLAUDE.md forbids by name — and a bare-string
    exclude hid two real findings while printing PASS.

    Two malformed spellings, not four: the bare string (which ITERATES, and is
    how seven gates shipped a silent PASS in v0.9.0) and the empty list (a
    census of zero). The two type errors that merely crash the reader are the
    same rule one altitude down, in `core/config.py`'s own suite.
    """

    SECTIONS = (
        ('uid', 'exclude_prefixes'), ('tres', 'exclude_prefixes'),
        ('props', 'exclude_prefixes'), ('defaults', 'exclude_prefixes'),
        ('shell', 'roots'), ('doc', 'scope'),
        ('pm', 'checks'),
    )

    @staticmethod
    def _check(section: str, body: str, root: Path) -> tuple[int, str]:
        from agentic_sdlc.core.project import load_config, repo_root
        (root / 'devkit.toml').write_text(body, encoding='utf-8')
        repo_root.cache_clear()
        load_config.cache_clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            from agentic_sdlc import cli as top
            code = top.main(['check', section.replace('_', '-')])
        return code, buf.getvalue()

    def test_no_section_accepts_a_malformed_list(self):
        for section, key in self.SECTIONS:
            for bad in ('"a-string"', '[]'):
                with self.subTest(section=section, bad=bad), tree() as root:
                    write_config(root, f'[{section}]\n{key} = {bad}\n')
                    code, out = self._check(
                        section, (root / 'devkit.toml').read_text(), root)
                    # 2 = config error. Never 0 (a silent narrowed census) and
                    # never 1 (which CI reads as "drift found").
                    self.assertEqual(code, 2, f'[{section}] {key} = {bad}\n{out}')

    def test_a_non_table_section_is_refused(self):
        for section, _ in self.SECTIONS:
            with self.subTest(section=section), tree() as root:
                # RAW, not `write_config`: the file under test IS the malformed
                # one, and `[pm]` here is the scalar `"nope"` — appending
                # `[pm.states.*]` under it is not valid TOML at all, so the
                # refusal being proven (a non-table SECTION, refused by the
                # reader at exit 2) would be replaced by a parse error raised
                # one layer lower.
                code, out = self._check(section, f'{section} = "nope"\n', root)
                self.assertEqual(code, 2, out)


class FamilySeparation(unittest.TestCase):
    def test_core_imports_neither_family(self):
        """CLAUDE.md states this invariant; nothing else enforces it.

        It is what makes rule 2's exit clause ("if a family stops belonging, it
        leaves") a real option rather than a sentiment — exercised in 0.2.0,
        when the scene half left whole.
        """
        src = Path(__file__).resolve().parent.parent / 'src' / 'agentic_sdlc'
        offenders = []
        for path in (src / 'core').rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            if 'agentic_sdlc.godot' in text or 'agentic_sdlc.repo' in text:
                offenders.append(str(path.relative_to(src)))
        self.assertEqual(offenders, [], 'core/ must know about neither family')


class BugStatusVocabulary(unittest.TestCase):
    """D4 — a bug's status, held to the vocabulary like every other grain's,
    and the census that says how many bug files the walk opened.

    Where a bug LIVES is not this tool's business: it is filed where it was
    caught, nothing moves it, and nothing deletes it. What is a fact about the
    file is whether its status is a word the schema has — and it matters more
    for a bug than anywhere else, because every reader asking "is this still
    open" tests for a NAME, so a typo reads as closed and passes in silence.

    `bugs/` is a permitted slot D13 never descends into, so a `glob('*.md')`
    made a nested bug invisible to every rule at once — and the census printed
    the smaller number without saying it had looked less far.
    """

    @staticmethod
    def _bug(root: Path, rel: str, status: str) -> Path:
        p = root / 'pm/roadmap/bugs' / rel
        write(p, {'id': f'0.1/bugs/{Path(rel).stem}', 'milestone': '"0.1"',
                  'status': status, 'caught_in': '"0.1"'})
        return p

    def test_a_bad_status_is_a_finding_wherever_the_bug_file_sits(self):
        # On the DEFAULT roster — no devkit.toml, no opt-in.
        for rel in ('seed-is-zero.md', 'spatial/seed-is-zero.md',
                    'SEED-IS-ZERO.MD'):
            with self.subTest(rel=rel), tree(milestone_status='building') as root:
                self._bug(root, rel, 'opne')
                code, out = run_gate(root)
                self.assertEqual(code, 1, out)
                self.assertIn("bug status 'opne' is not in", out)
                self.assertIn(rel, out)
                self.assertIn('1 bug(s)', out)

    def test_the_census_counts_every_bug_file_it_opened(self):
        # Rule 4: "0 bug(s)" is a fact this scan states, never an omission, and
        # a nested or oddly-cased file is one the count must include.
        with tree(milestone_status='building') as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('0 bug(s)', out)
        with tree(milestone_status='building') as root:
            for rel, status in (('flat.md', 'open'), ('deep/nested.md', 'fixed'),
                                ('UPPER.MD', 'closed')):
                self._bug(root, rel, status)
            code, out = run_gate(root)
            # Every word the vocabulary holds passes, wherever the file sits.
            self.assertEqual(code, 0, out)
            self.assertIn('3 bug(s)', out)

    def test_an_open_bug_under_a_done_milestone_is_not_a_finding(self):
        with tree(milestone_status='done', feature_status='done',
                  story_statuses=('done',)) as root:
            self._bug(root, 'seed-is-zero.md', 'open')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)

    def test_a_non_grain_md_parked_under_bugs_is_not_a_bug(self):
        # A grain IS its frontmatter, so a README explaining how bugs are filed
        # — or a design note beside them — is not a bug with an empty status.
        # The control comes with it: narrowing the walk to grain documents must
        # not undo the recursion that made nested bugs visible at all.
        with tree(milestone_status='building') as root:
            bdir = root / 'pm/roadmap/bugs'
            (bdir / 'design').mkdir(parents=True, exist_ok=True)
            (bdir / 'README.md').write_text('# how bugs are filed here\n',
                                            encoding='utf-8')
            (bdir / 'design/sketch.md').write_text('a sketch\n',
                                                   encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('README.md', out)
            self.assertIn('0 bug(s)', out)

            self._bug(root, 'spatial/SEED.MD', 'opne')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('bugs/spatial/SEED.MD', out)
            self.assertIn('1 bug(s)', out)


class StoryWalk(unittest.TestCase):
    """The story POOL is walked whole — every depth, either case, grains only.

    The bug walk was made recursive and case-insensitive on extension and
    `stories/` never got it, so a story parked one directory down was invisible
    to every rule at once — and worse than invisible: D4 could not see its
    status, and D2 read "all stories done" off the ones it could see and filed
    a FALSE finding against a feature that had an unfinished story in it. The
    slot became a POOL in 0.4.0 and the hazard did not move: a project that
    files its stories into `stories/parked/` is filing them somewhere the walk
    has to reach, because the pool is a table and a row in it is a row.
    """

    POOL = 'pm/roadmap/stories'

    def test_a_story_the_walk_cannot_see_becomes_a_FALSE_D2_finding(self):
        # Not just an undercount: the stories it COULD see were all done, so
        # D2 told the author to close a feature with an open story in it.
        for rel in ('parked/s2.md', 'S2.MD'):
            with self.subTest(rel=rel), \
                    tree(feature_status='building',
                         story_statuses=('done',)) as root:
                write(root / self.POOL / rel,
                      {'id': '0.1/alpha/s2', 'kind': 'story',
                       'feature': '0.1/alpha',
                       'milestone': '"0.1"', 'name': 'S2', 'status': 'ready'})
                code, out = run_gate(root)
                self.assertIn('2 story/ies', out)
                self.assertNotIn('all stories done', out)

    def test_D4_can_see_a_nested_story_with_an_illegal_status(self):
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            write(root / self.POOL / 'parked/s2.md',
                  {'id': '0.1/alpha/s2', 'kind': 'story',
                   'feature': '0.1/alpha',
                   'milestone': '"0.1"', 'name': 'S2',
                   'status': 'NOT-A-REAL-STATUS'})
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn("status 'NOT-A-REAL-STATUS' not in", out)

    def test_a_non_grain_md_parked_in_the_pool_is_not_a_story(self):
        # The same rule `bugs/` gets, from the same walk: a README beside the
        # stories is not a story with an empty status.
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            (root / self.POOL / 'README.md').write_text(
                '# how stories are written here\n', encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 story/ies', out)


class StructuralIntegrity(unittest.TestCase):
    """A grain nothing claims is REPORTED, never walked past (V7).

    The nested shape of this hazard was a feature directory under a milestone
    directory with no `milestone.md` in it: the drifted feature vanished from
    the scan entirely, because the scan descended and there was nothing to
    descend from. Pools cannot lose a file that way — every document is in a
    pool and every pool is walked — but the SAME hole reopens one field over:
    the roll-ups still descend from the milestones, so a feature bound to a
    milestone that is not in the tree is counted by the census and reached by
    nothing. V7 is the walk that starts at the pools instead.
    """

    def test_a_grain_whose_binding_resolves_to_nothing_is_reported(self):
        with tree(story_statuses=('ready',)) as root:
            write(root / 'pm/roadmap/features/gizmo.md',
                  {'id': '0.2/gizmo', 'kind': 'feature', 'milestone': '"0.2"',
                   'name': 'G', 'status': 'done', 'reviewed': ''})
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn("has milestone: '0.2', which is not a grain in this "
                          'tree', out)
            # ...and it was COUNTED, so the census is not quietly short one.
            self.assertIn('2 feature(s)', out)

    def test_a_grain_with_an_empty_binding_is_COUNTED_and_never_a_finding(self):
        # The unbound/broken split, and it is the whole rule: *nothing said* is
        # a plan, *something wrong said* is drift. A tree mid-planning
        # legitimately has many unbound grains, and a gate that reddens on
        # planning is a gate people switch off.
        with tree(story_statuses=('ready',)) as root:
            model.set_field(root / 'pm/roadmap/stories/s0.md', 'feature', '')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('UNBOUND  1 story(s) name no feature:', out)
            self.assertIn('0.1/alpha/s0', out)
            # The line names the command that binds one, because a count with
            # no next step is a count somebody has to go looking behind.
            self.assertIn('pm add <feature-id> <id>', out)
            self.assertNotIn('DRIFT', out)

    def test_a_tree_that_is_ENTIRELY_unbound_still_exits_zero(self):
        # The claim people will doubt, so it is pinned rather than argued: no
        # config makes an unbound grain an error, and every edge unbound at
        # once is still exit 0.
        with tree(story_statuses=('ready',)) as root:
            for rel, field in (('features/alpha.md', 'milestone'),
                               ('stories/s0.md', 'feature')):
                model.set_field(root / 'pm/roadmap' / rel, field, '')
            bug(root, 'crash')
            model.set_field(root / 'pm/roadmap/bugs/crash.md', 'milestone', '')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            for line in ('1 feature(s) name no milestone:',
                         '1 story(s) name no feature:',
                         '1 bug(s) name no milestone:'):
                self.assertIn(line, out)

    def test_the_unbound_rows_go_quiet_when_V7_is_off(self):
        # A counted line rides with the rule that owns the edge; disabling V7
        # takes both halves, so a consumer never gets the census without the
        # finding that gives it meaning.
        with tree(story_statuses=('ready',)) as root:
            write_config(root, '[pm]\nchecks = ["D1","D4"]\n')
            model.set_field(root / 'pm/roadmap/stories/s0.md', 'feature', '')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('UNBOUND', out)

    def test_a_binding_that_names_the_wrong_KIND_is_reported(self):
        # `feature: 0.1` resolves — to a MILESTONE. A binding that lands on a
        # grain of the wrong kind is a tree that reads as valid and rolls up
        # into nothing.
        with tree(story_statuses=('ready',)) as root:
            model.set_field(root / 'pm/roadmap/stories/s0.md', 'feature', '0.1')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('which is a milestone and not a feature', out)


class Validate(unittest.TestCase):
    """Structural + referential integrity — a different question from drift.

    A tree can be perfectly undrifted and still depend on a feature that does
    not exist.
    """

    def _run(self, root: Path):
        from agentic_sdlc.repo.pm import validate
        return validate.run(model.PmConfig(root=root))

    def test_a_clean_tree_validates(self):
        with tree(story_statuses=('ready',)) as root:
            findings, census = self._run(root)
            self.assertEqual(findings, [])
            self.assertEqual(census['grains'], 3)

    def test_each_integrity_rule_fires(self):
        # (rule, grain file, field, value, the line the finding carries)
        # V2 and V3 are RETIRED — both graded a path against a field, and the
        # path is not part of the identity any more. V7 is what replaced the
        # half of V3 that was a real fact about the tree.
        rows = (
            ('V4', 'features/alpha.md', 'depends_on',
             '["0.1/no-such-feature"]', 'resolves to nothing'),
            ('V7', 'stories/s0.md', 'feature', '0.1/somewhere-else',
             'which is not a grain in this tree'),
        )
        for rule, rel, field, value, message in rows:
            with self.subTest(rule=rule), tree(story_statuses=('ready',)) as root:
                model.set_field(root / 'pm/roadmap' / rel, field, value)
                findings, _ = self._run(root)
                self.assertTrue(any(message in f for f in findings), findings)

    def test_v4_a_ref_into_a_pruned_milestone_is_unverifiable_not_a_finding(self):
        # Git history is the archive: depending on a milestone that has been
        # pruned is expected, so it is censused rather than failed.
        with tree() as root:
            ff = root / 'pm/roadmap/features/alpha.md'
            model.set_field(ff, 'depends_on', '["0.0.9/long-gone"]')
            # A HIERARCHICAL id names its milestone, and `0.0.9` is not in the
            # tree. A flat id carries no such segment and would be a finding.
            findings, census = self._run(root)
            self.assertEqual(findings, [])
            self.assertEqual(census['unverifiable'], 1)

    def test_v5_detects_a_dependency_cycle(self):
        with tree() as root:
            run_cli(root, 'new', 'feature', '0.1', 'beta', 'Beta')
            fdir = root / 'pm/roadmap/features'
            model.set_field(fdir / 'alpha.md', 'depends_on', '["0.1/beta"]')
            model.set_field(fdir / 'beta.md', 'depends_on', '["0.1/alpha"]')
            findings, _ = self._run(root)
            self.assertTrue(any('CYCLE' in f for f in findings), findings)

    def test_the_verb_refuses_an_empty_tree_instead_of_saying_VALID(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            (root / 'pm' / 'roadmap').mkdir(parents=True)
            write_config(root)
            (root / '.git').mkdir(exist_ok=True)
            previous = Path.cwd()
            os.chdir(root)
            try:
                code, _ = run_cli(root, 'validate')
            finally:
                os.chdir(previous)
            self.assertEqual(code, 2)

    def test_the_gate_runs_the_same_predicates(self):
        # One definition, two readers: a dangling ref must fail `check pm` too.
        with tree(story_statuses=('ready',)) as root:
            ff = root / 'pm/roadmap/features/alpha.md'
            model.set_field(ff, 'depends_on', '["0.1/no-such-feature"]')
            code, out = run_gate(root)
            self.assertEqual(code, 1)
            self.assertIn('resolves to nothing', out)


class CausedBy(unittest.TestCase):
    """V4 over a bug's `caused_by:` — one definition, BOTH readers.

    A ref is a ref: a `caused_by:` naming no feature reports in exactly the
    shape a dangling `depends_on` does, at exactly its exit code, counted in
    the same census, and it does so out of `pm validate` AND out of `check pm`.
    A ref that names nothing is an integrity FACT, which is the class this
    package keeps as a gate; whether a given cause counts as an escape is a
    judgement, and that belongs to the report.
    """

    def _validate(self, root: Path, **kw):
        from agentic_sdlc.repo.pm import validate
        return validate.run(model.PmConfig(root=root), **kw)

    def test_a_dangling_cause_reports_like_a_dangling_depends_on(self):
        # The SAME line, word for word, but for the key and the path — one
        # finding shape, so a consumer grepping `resolves to nothing` sees
        # both without learning a second spelling.
        with tree(story_statuses=('ready',)) as root:
            bug(root, 'seed-is-zero', caused_by='0.1/no-such-feature')
            findings, census = self._validate(root)
            self.assertEqual(findings, [
                "pm/roadmap/bugs/seed-is-zero.md: caused_by "
                "'0.1/no-such-feature' resolves to nothing "
                "(its milestone IS in the tree)"])
            self.assertEqual(census['refs'], 1)

            ff = root / 'pm/roadmap/features/alpha.md'
            model.set_field(ff, 'depends_on', '["0.1/no-such-feature"]')
            dep = [f for f in self._validate(root)[0] if 'depends_on' in f]
            self.assertEqual(len(dep), 1)
            self.assertEqual(dep[0].split(': ', 1)[1].replace('depends_on', 'X'),
                             findings[0].split(': ', 1)[1].replace('caused_by', 'X'))

    def test_what_a_cause_may_and_may_not_name(self):
        """`caused_by:` records the CHANGE that produced the bug.

        A milestone is a container of changes and a story is a slice of one, so
        neither resolves — if either passed, the escape count would attribute a
        bug to something that cannot own it. A LIST-shaped value reaches the
        resolver as a milestone id no glob matches, so the generic path would
        census it UNVERIFIABLE — a hand-written list quietly reported as "its
        milestone was pruned". An over-long segment must be a finding rather
        than a traceback: `Path.is_dir()` RAISES on a component past NAME_MAX
        up to 3.13 and answers False from 3.14 on, so the same hand-typed id
        would fail `pm validate` with a stack trace on one interpreter and a
        finding on another.
        """
        # (raw caused_by, findings expected, refs, unverifiable)
        rows = (
            ('0.1/alpha', False, 1, 0),           # the resolving case
            ('"0.1/alpha"', False, 1, 0),         # quoted is the same id
            ('', False, 0, 0),
            ('null', False, 0, 0),
            ('~', False, 0, 0),
            ('0.1', True, 1, 0),                  # a milestone owns no change
            ('0.1/alpha/s0', True, 1, 0),         # nor does a story
            # A list-shaped or comma-joined value is not a ref at all — but it
            # must be a FINDING rather than a silent UNVERIFIABLE, which is
            # how a hand-written list read as "its milestone was pruned".
            ('["0.1/alpha"]', True, 0, 0),
            ('0.1/alpha, 0.1/beta', True, 0, 0),
            ('0.1/' + 'a' * 300, True, 1, 0),     # NAME_MAX, not a traceback
            ('0.0.9/long-gone', False, 1, 1),     # pruned: unverifiable
        )
        for raw, expect_findings, refs, unverifiable in rows:
            with self.subTest(raw=raw[:40]), tree(story_statuses=('ready',)) as root:
                path = bug(root, 'seed-is-zero')
                self.assertTrue(model.set_field(path, 'caused_by', raw))
                findings, census = self._validate(root)
                self.assertEqual(bool(findings), expect_findings,
                                 f'{raw!r}: {findings}')
                self.assertEqual(census['refs'], refs, raw)
                self.assertEqual(census['unverifiable'], unverifiable, raw)
                code, out = run_cli(root, 'validate')
                self.assertNotIn('Traceback', out)
                self.assertEqual(code, 1 if expect_findings else 0, out)

    def test_a_bug_is_walked_for_its_ref_and_NOT_counted_as_a_grain(self):
        # The walk reaches a bug for `caused_by:` alone. V1/V2/V3 are still
        # stated over milestones, features and stories, and `check pm` stays
        # the one home of the bug census (`N bug(s)`).
        with tree(story_statuses=('ready',)) as root:
            self.assertIn('3 grain(s), 0 ref(s)', run_cli(root, 'validate')[1])
            for i in range(3):
                bug(root, f'b{i}', caused_by='0.1/alpha')
            _, census = self._validate(root)
            self.assertEqual(census['grains'], 3)
            self.assertEqual(census['refs'], 3)
            self.assertIn('3 grain(s), 3 ref(s)', run_cli(root, 'validate')[1])
            # The gate's census counts the same files, and stays green: a ref
            # is counted whether or not it is a finding, so `3 ref(s)` is not a
            # synonym for `3 problem(s)`.
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('3 bug(s), 3 ref(s)', out)

    def test_the_gate_reports_it_too_and_the_two_readers_agree(self):
        # One definition, two readers — the property the whole test_pm_*
        # quartet exists to hold. A dangling `depends_on` fails `check pm`, so
        # a dangling `caused_by:` fails it in the same line and at the same
        # exit code, and the ref it added is in the gate's census.
        with tree(story_statuses=('ready',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('0 bug(s), 0 ref(s)', out)

            bug(root, 'seed-is-zero', caused_by='0.1/no-such-feature')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn("  DRIFT  pm/roadmap/bugs/seed-is-zero.md: "
                          "caused_by '0.1/no-such-feature' resolves to nothing "
                          "(its milestone IS in the tree)", out)
            self.assertIn('1 bug(s), 1 ref(s)', out)
            self.assertIn('integrity violation(s)', out)
            # ...and the finding `pm validate` returns is the line the gate
            # printed, so there is no second answer to one question.
            findings, _ = self._validate(root)
            self.assertEqual(len(findings), 1)
            self.assertIn(findings[0], out)
            self.assertEqual(run_cli(root, 'validate')[0], 1)


class RefParsing(unittest.TestCase):
    """An unreadable ref list is a FINDING. Never an empty list.

    Returning [] would mean "no refs to check", so a trailing comment or a YAML
    block sequence would take every ref out of V4's reach and still read clean.
    """

    def _with(self, root: Path, raw: str):
        ff = root / 'pm/roadmap/features/alpha.md'
        self.assertTrue(model.set_field(ff, 'depends_on', raw))
        from agentic_sdlc.repo.pm import validate
        return validate.run(model.PmConfig(root=root))

    def test_unreadable_shapes_are_reported_not_silently_dropped(self):
        for raw in ('["0.1/ghost"]  # note', '0.1/ghost', '[["0.1/ghost"]]',
                    '["0.1/a, and 0.1/b"]'):
            with self.subTest(raw=raw), tree() as root:
                findings, _ = self._with(root, raw)
                self.assertTrue(findings, f'{raw!r} vanished silently')

    def test_empty_and_null_are_genuinely_empty(self):
        for raw in ('[]', 'null', '~'):
            with self.subTest(raw=raw), tree() as root:
                findings, census = self._with(root, raw)
                self.assertEqual(findings, [])
                self.assertEqual(census['refs'], 0)

    def test_the_ref_census_does_not_depend_on_which_rules_ran(self):
        with tree() as root:
            ff = root / 'pm/roadmap/features/alpha.md'
            model.set_field(ff, 'depends_on', '["0.1/alpha"]')
            from agentic_sdlc.repo.pm import validate
            cfg = model.PmConfig(root=root)
            self.assertEqual(validate.run(cfg, {'V1'})[1]['refs'],
                             validate.run(cfg, {'V4'})[1]['refs'])


class DamagedFrontmatter(unittest.TestCase):
    """A broken grain stays IN the census and is REPORTED.

    "This has no frontmatter" and "this frontmatter is broken" are different
    facts, and the grain walk answered the second with the first: scope was
    decided by the STRICT parser, so a BOM before the fence, a blank line above
    it or a missing closing fence dropped the document out of every rule at
    once — D4, D5 and V1 went blind together and the gate printed PASS. The bug
    half is the loudest: the census said there was no bug in the directory at
    all, so a damaged bug was a bug nobody could be told to fix.

    Detection is lenient, parsing is strict. That split is the whole rule, and
    the controls below are the other half of it: a genuine note must stay out.
    """

    BUG_TOML = '[pm]\nchecks = ["D4","V1"]\n'

    @staticmethod
    def _bug(root: Path, slug: str, status: str) -> Path:
        p = root / 'pm/roadmap/bugs' / f'{slug}.md'
        write(p, {'id': f'0.1/bugs/{slug}', 'milestone': '"0.1"',
                  'status': status, 'caught_in': '"0.1"'})
        return p

    def test_a_damaged_story_is_reported_not_dropped(self):
        for form in DAMAGE_FORMS:
            with self.subTest(form=form):
                with tree(feature_status='building',
                          story_statuses=('ready',)) as root:
                    damage(root / STORY_REL, form)
                    code, out = run_gate(root)
                    self.assertEqual(code, 1, out)
                    # 0.4.0: a damaged document declares no `id:`, so nothing
                    # can key on it and no walk reaches it — which is exactly
                    # the drop this case exists to forbid. It is REPORTED by
                    # name and COUNTED in the census; the words changed, the
                    # guarantee did not.
                    self.assertIn('declares no `id:`', out)
                    self.assertIn('SKIPPED by this scan', out)
                    self.assertIn('1 story/ies', out)

    def test_a_damaged_bug_is_reported_not_dropped(self):
        for form in DAMAGE_FORMS:
            with self.subTest(form=form):
                with tree(milestone_status='building') as root:
                    write_config(root, self.BUG_TOML)
                    damage(self._bug(root, 'seed-is-zero', 'open'), form)
                    code, out = run_gate(root)
                    self.assertEqual(code, 1, out)
                    self.assertIn('declares no `id:`', out)
                    self.assertIn('1 bug(s)', out)
                    self.assertNotIn('no bug files under', out)

    def test_the_resolver_names_the_damage_not_a_missing_story(self):
        # `story_file` walks the same grain walk, so it went blind with the
        # gate: `pm story building <id>` answered "no story resolves from id"
        # about a file sitting right there. Each answer is defensible alone;
        # together they leave nothing to do.
        for form in DAMAGE_FORMS:
            with self.subTest(form=form):
                with tree(feature_status='building',
                          story_statuses=('ready',)) as root:
                    damage(root / STORY_REL, form)
                    # 0.4.0: a grain is found by its `id:`, and a document
                    # whose frontmatter cannot be read declares none — so it
                    # is in no index and the resolver genuinely cannot reach
                    # it. What must NOT happen is the answer stopping there.
                    self.assertIsNone(
                        model.story_file(cfg_for(root), '0.1/alpha/s0'))
                    code, out = run_cli(root, 'story', 'building', '0.1/alpha/s0')
                    self.assertEqual(code, 2, out)
                    # The file, by path, and why it cannot be keyed on — so
                    # the fix is the next thing read rather than the next
                    # thing hunted for.
                    self.assertIn('pm/roadmap/stories/s0.md', out)
                    self.assertIn('declares no `id:`', out)

    def test_a_damaged_grain_is_never_quietly_accepted(self):
        # Lenient DETECTION must not become a lenient PARSER. A BOM'd file is a
        # grain whose frontmatter is broken, so `field_of` still reads nothing
        # out of it and `set_field` still refuses to write into it.
        for form in DAMAGE_FORMS:
            with self.subTest(form=form):
                with tree(story_statuses=('ready',)) as root:
                    sfile = root / STORY_REL
                    damage(sfile, form)
                    self.assertTrue(model._is_grain_doc(sfile))
                    self.assertEqual(model.field_of(sfile, 'status'), '')
                    before = sfile.read_bytes()
                    self.assertFalse(model.set_field(sfile, 'status', 'building'))
                    self.assertEqual(sfile.read_bytes(), before)

    # --- the controls: a genuine note stays OUT, and is DISCLOSED ---------
    def test_a_note_stays_out_of_the_census_and_the_census_says_how_many(self):
        # A census must never assert the opposite of the filesystem. "0 bug(s)"
        # is a fact about the filter, not about the directory, unless the scan
        # says how far it looked. The one thing leniency will NOT step over is
        # prose: a `---` under a paragraph is a thematic break in a note, not a
        # frontmatter fence.
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            write_config(root, self.BUG_TOML)
            sdir = root / 'pm/roadmap/stories'
            bdir = root / 'pm/roadmap/bugs'
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / 'README.md').write_text('# how bugs are filed here\n',
                                            encoding='utf-8')
            (sdir / 'README.md').write_text('# how stories are written\n',
                                            encoding='utf-8')
            (sdir / 'notes.md').write_text('Some prose\n\n---\n\nmore prose\n',
                                           encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('README.md', out)
            # Each POOL discloses its own, beside its own count: two notes in
            # `stories/` and one in `bugs/`. An aggregate would say three and
            # not say where, which is half a disclosure.
            self.assertIn('1 story/ies, 2 note(s) skipped', out)
            self.assertIn('0 bug(s), 1 note(s) skipped', out)

    def test_a_shared_doc_is_not_counted_as_somebodys_stray_note(self):
        # A grain's `decisions.md` opens no frontmatter either, so it landed in
        # the note count — honest, and about to be useless: a tree grows one
        # per grain that has ever been decided on, and at forty of them a REAL
        # stray note is invisible inside the number. Two reasons, so both keep
        # meaning something.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'decide', '0.1/alpha', 'a choice')[0], 0)
            (root / 'pm/roadmap/features/README.md').write_text(
                '# how features are written here\n', encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 shared doc(s) beside their grains', out)
            self.assertIn('1 note(s) skipped', out)

    def test_a_clean_tree_discloses_nothing_because_it_skipped_nothing(self):
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('note(s) skipped', out)
            self.assertNotIn('hidden (dot-prefixed', out)

    def test_the_census_says_how_many_documents_the_dotted_filter_hid(self):
        # The twin of the note disclosure, and the reason it matters: an open
        # bug parked under `bugs/.hold/` is out of scope for every rule, so no
        # rule can report its status. A dot prefix is a deliberate hide; an
        # UNCOUNTED one is a census asserting the opposite of the filesystem.
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            hold = root / 'pm/roadmap/bugs/.hold'
            hold.mkdir(parents=True, exist_ok=True)
            (hold / 'openbug.md').write_text(
                '---\nid: 0.1/bugs/openbug\nmilestone: "0.1"\n'
                'name: b\nstatus: open\nseverity: high\n---\n# b\n',
                encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 hidden (dot-prefixed', out)

    def test_the_grain_walk_skips_dotted_names_exactly_as_D13_does(self):
        # `structure_findings` skips a dotted entry, so a `stories/.hidden/d.md`
        # held to D4 was one walk enforcing a rule the structure gate had
        # already declared out of scope. Two walks, one tree, one answer.
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            sdir = root / 'pm/roadmap/stories'
            write(sdir / '.hidden/d.md',
                  {'id': '0.1/alpha/d', 'status': 'NOT-A-REAL-STATUS'})
            write(sdir / '.dotfile.md',
                  {'id': '0.1/alpha/dot', 'status': 'NOT-A-REAL-STATUS'})
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 story/ies', out)
            self.assertNotIn('NOT-A-REAL-STATUS', out)


class MarkdownFences(unittest.TestCase):
    """`check doc` — what a fence may and may not hide.

    A fence masks because a quoted refusal message is an ILLUSTRATION, not an
    instruction. An UNTERMINATED one illustrates nothing and hides the rest of
    the file, and a parity toggle let it do that in silence: two claims that
    FAIL normally printed PASS the moment one stray ``` was prepended above
    them. Every masking route below was reached by a different defect, and one
    of them (the balanced inline span) came out of the markdown fuzz.
    """

    DEAD = ('See [the missing spec](docs/specs/nope.md).\n'
            'Run `make no-such-target` to do it.\n')

    def _doc(self, root: Path, body: str) -> tuple[int, str]:
        import importlib
        from agentic_sdlc.repo.checks import doc
        (root / 'CLAUDE.md').write_text(body, encoding='utf-8')
        from agentic_sdlc.core.project import load_config, repo_root
        repo_root.cache_clear()
        load_config.cache_clear()
        # `doc` binds its root and scope at IMPORT, where production resolves
        # them once per process and the cwd never moves. Tests move it.
        importlib.reload(doc)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = doc.run()
        return code, buf.getvalue()

    def test_nothing_that_is_not_a_real_fence_hides_a_doc_claim(self):
        # (name, the body wrapped around DEAD)
        shapes = (
            ('no fence at all', self.DEAD),
            ('an unterminated fence', '```\n' + self.DEAD),
            # CommonMark: four spaces is INDENTED CODE, so what it holds is
            # text. A doc showing how a fence is written indents the sample,
            # and reading it as real opened a block that never closed.
            ('an indented sample', 'Opening a block:\n\n    ```gdscript\n\n'
                                   + self.DEAD),
            # A parity toggle counted any fence-looking line, so the `~~~`
            # "closed" the block and the ``` that really closed it opened a
            # new one — every line after it dropped.
            ('a tilde run inside a backtick fence', '```\n~~~\n```\n' + self.DEAD),
            # CommonMark: the info string after a BACKTICK fence may not
            # contain a backtick. Without that rule a paragraph merely
            # BEGINNING with a ```balanced``` span opened a fence, a later bare
            # ``` "closed" it, and the claims between were masked with NO
            # defect reported — the silent mask, reached by a third route.
            ('a balanced inline span leading a line',
             '```make nosuchtarget``` is the spelling.\n' + self.DEAD + '```\n'),
        )
        for name, body in shapes:
            with self.subTest(shape=name), tree() as root:
                code, out = self._doc(root, body)
                self.assertEqual(code, 1, out)
                self.assertIn('dead link target', out)
                self.assertIn('unknown make target', out)

    def test_a_real_fence_still_masks(self):
        # The fix is not "stop masking": a doc quoting a command that no longer
        # exists is illustrating it, and flagging that is how a gate gets
        # switched off. The tilde row is the over-application guard — the
        # info-string rule is BACKTICK-fence-only, and applying it to `~~~`
        # would stop a real block masking, which is the same defect pointing
        # the other way.
        for name, body, skipped in (
                ('a terminated backtick fence', '```\n' + self.DEAD + '```\n', 4),
                ('a tilde fence with backticks in its info string',
                 '~~~ a ``b`` c\n' + self.DEAD + '~~~\n', 4)):
            with self.subTest(shape=name), tree() as root:
                code, out = self._doc(root, body)
                self.assertEqual(code, 0, out)
                self.assertIn(f'{skipped} fenced line(s) skipped', out)

    def test_an_unterminated_fence_is_itself_reported_and_censused(self):
        # The verdict used to print alone. "1 malformed doc(s)" out of one doc
        # and out of two hundred are different reports, and only one of them
        # printed.
        with tree() as root:
            code, out = self._doc(root, '```\n' + self.DEAD)
            self.assertEqual(code, 1, out)
            self.assertIn('never terminated', out)
            self.assertIn('malformed doc(s)', out)
            self.assertIn('1 doc(s)', out.splitlines()[0])
            self.assertIn('fenced line(s) skipped', out.splitlines()[0])


class ARenamedVocabularyGetsTheSameAnswers(unittest.TestCase):
    """Ship criterion 5 of `every-question-is-asked-of-a-category` — the
    northstar, measured rather than asserted.

    `tests/fixtures/renamed-vocabulary/` is a PM tree in which not one state
    word is the seed's (hard rule 8: vendored here). It trips D1, D2, D3, D4,
    D5, D6, D9 and D10 and carries the clean shapes beside them. The STOCK
    twin is built from it by substitution — the same tree, the seed's words —
    and the gate's transcript over the renamed tree, with the rename undone,
    must be byte-identical to its transcript over the twin. Every rule fires
    on both (rule 4: two empty transcripts would also be equal).

    Why this and not `test_pm_flow.py`'s renamed-flow case: that one proves
    the READER maps renamed words to categories; this proves that nothing
    between the reader and the verdict line asks about a word. The gate runs
    in process on a copy — no spawn, no fixture written in place.
    """

    FIXTURE = Path(__file__).parent / 'fixtures' / 'renamed-vocabulary'
    # renamed -> seed, one entry per word the fixture declares
    RENAME = {
        'queued': 'planning', 'shaped': 'ready', 'doing': 'building',
        'checking': 'reviewing', 'blessed': 'accepted', 'boxing': 'packaging',
        'shipped': 'done', 'dropped': 'obe',
        'filed': 'open', 'patched': 'fixed', 'shut': 'closed',
    }

    def _unrename(self, text: str) -> str:
        for renamed, stock in self.RENAME.items():
            text = text.replace(renamed, stock)
        return text

    @contextlib.contextmanager
    def _copies(self):
        """(renamed copy, stock twin), each a marked tree in scratch."""
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            renamed = Path(tmp) / 'renamed'
            stock = Path(tmp) / 'stock'
            shutil.copytree(self.FIXTURE, renamed)
            shutil.copytree(self.FIXTURE, stock)
            for path in stock.rglob('*'):
                if path.is_file() and path.suffix in ('.md', '.toml'):
                    path.write_text(self._unrename(path.read_text('utf-8')),
                                    encoding='utf-8')
            for root in (renamed, stock):
                (root / '.git').mkdir()
            yield renamed, stock

    def _run(self, root: Path, verb) -> tuple[int, str]:
        previous = Path.cwd()
        os.chdir(root)
        try:
            return verb(root)
        finally:
            os.chdir(previous)

    def test_the_fixture_is_wholly_renamed_and_the_twin_is_wholly_stock(self):
        # A fixture that had drifted back toward the seed's words would make
        # the comparison below prove less than it claims.
        import tomllib
        config = tomllib.loads((self.FIXTURE / 'devkit.toml').read_text('utf-8'))
        declared = {st for kind in config['pm']['states'].values()
                    for states in kind.values() for st in states}
        self.assertEqual(declared, set(self.RENAME))
        seed = {st for kind in model.DEFAULT_FLOWS.values()
                for states in kind.values() for st in states}
        self.assertEqual(set(self.RENAME.values()), seed)
        self.assertFalse(declared & seed)

    def test_check_pm_says_the_same_thing_about_both_trees(self):
        with self._copies() as (renamed, stock):
            code_r, out_r = self._run(renamed, run_gate)
            code_s, out_s = self._run(stock, run_gate)
        self.assertEqual(code_r, 1, out_r)
        self.assertEqual(code_s, 1, out_s)
        self.assertEqual(self._unrename(out_r), out_s)
        # Every rule the fixture is built to trip, tripped — on the RENAMED
        # tree, whose output is the one that could have gone quiet.
        for needle in ('  DRIFT  feature 1.0/dangling: reviewed:',       # D1
                       '  WARN  feature 1.0/stalled: all stories done, '
                       'feature still shaped (todo)',                   # D2
                       "  WARN  milestone 0.9 is 'shipped' (done) but feature",  # D3
                       "status 'wombat' not in",                      # D4 feature
                       "status 'wobmat' not in",                      # D4 story
                       "bug status 'fidel' is not in",                # D4 bug
                       'two places in this tree disagree',            # D5
                       "  WARN  milestone 2.0 is 'queued' (todo) but all 1 "
                       "features are done",                           # D6
                       'in-progress milestone 1.1 declares no branch',  # D9/D10
                       'D10'):
            self.assertIn(needle, out_r, needle)
        # The four cross-level rules are WARN lines, the rest DRIFT — and the
        # verdict counts them apart. The renamed tree and the stock twin agree
        # on both counts (the equality above), so one is enough to state.
        self.assertRegex(out_r, r'\[check:pm\] FAIL — \d+ status-drift.*; '
                                r'\d+ warning\(s\)')
        # D5 fires per story that has started under a `todo` feature: both
        # finished stories of `stalled`, the one `doing` story of `ahead`.
        self.assertEqual(out_r.count('two places in this tree disagree'), 3)
        # ...and the normal path is silent: a `dropped` story is finished. No
        # DRIFT names it — a WARN may (its scaffold sections are empty, and
        # the READY warnings are symmetric across the two trees, which the
        # equality above already holds).
        drift = [ln for ln in out_r.splitlines() if ln.startswith('  DRIFT  ')]
        self.assertFalse([ln for ln in drift if '1.0/normal' in ln], drift)

    def test_every_read_verb_says_the_same_thing_about_both_trees(self):
        # Criterion 5 names the gate BEHAVIOUR, and `pm list`, `ready-for`
        # ×3 and `vocabulary` are as much of it as `status` is (V5 of the
        # feature review): each is byte-identical modulo the words, at the
        # same exit code. `status` is the one exception, whitespace-squeezed:
        # its status column is as wide as the longest word the project
        # declared, and `reviewing` is a character longer than `checking`.
        import re

        def squeeze(text: str) -> list[str]:
            return [' '.join(re.sub(r'\s+\]', ']', ln).split())
                    for ln in text.splitlines()]
        verbs = (('status',), ('list',), ('vocabulary',),
                 ('vocabulary', '--json'),
                 ('ready-for', 'feature', '1.0/normal'),
                 ('ready-for', 'feature', '1.0/stalled'),
                 ('ready-for', 'milestone', '1.0'),
                 ('ready-for', 'tag', '1.0'))
        for argv in verbs:
            def verb(root, argv=argv):
                return run_cli(root, *argv)
            with self.subTest(verb=' '.join(argv)), \
                    self._copies() as (renamed, stock):
                code_r, out_r = self._run(renamed, verb)
                code_s, out_s = self._run(stock, verb)
                self.assertEqual(code_r, code_s, out_r + out_s)
                self.assertTrue(out_r.strip(), argv)      # never two empties
                if argv == ('status',):
                    self.assertEqual(squeeze(self._unrename(out_r)),
                                     squeeze(out_s))
                else:
                    self.assertEqual(self._unrename(out_r), out_s)
        with self._copies() as (renamed, stock):
            code_r, out_r = self._run(renamed, lambda root: run_cli(root, 'status'))
        self.assertEqual(code_r, 0, out_r)
        self.assertIn('stories 2/2 done', out_r)          # shipped + dropped
        # D2 is the gate's WARN, so the board's marker says WARN too; a
        # dangling record stays a DRIFT marker (D1 is a finding).
        self.assertIn('<WARN: all stories done, feature still shaped>', out_r)
        self.assertIn('<DRIFT: reviewed:', out_r)


class TheUnboundFamily(unittest.TestCase):
    """R1-R4 and R6 — the plan and the tree held to each other.

    THE PLAN LISTS MILESTONE IDS (0.4.0), so the entry and the grain are the
    same name and `pm rename` sweeps both. R1 and R6 get two cases each because
    both are symmetric and only ONE direction of each is the bug that motivated
    it: an entry naming nothing is the cheap half, and a milestone that finished
    under someone else's version is the half no rule could previously see.
    """

    ALL = '[pm]\nchecks = ["R1","R2","R3","R4","R6"]\n'

    @staticmethod
    def _planned(root: Path, *mids: str) -> None:
        body = '\n'.join(f'  - "{m}"' for m in mids)
        (root / 'pm/roadmap/releases.md').write_text(
            f'---\nid: roadmap\nkind: roadmap\norder:\n{body}\n---\n\n'
            f'The plan.\n', encoding='utf-8')

    @staticmethod
    def _claims(root: Path, mid: str, version: str, status: str) -> None:
        front = {'id': f'"{mid}"', 'kind': 'milestone', 'name': mid,
                 'status': status}
        if version:
            front['version'] = f'"{version}"'
        write(root / f'pm/roadmap/milestones/{mid}.md', front)

    def test_off_unless_named(self):
        # Every input the family exists to catch, on the stock roster.
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'gone', 'a')
            self._claims(root, 'a', '0.1.0', 'done')   # R4 + R6 + R1 dangling
            self._claims(root, 'b', '9.9.9', 'done')   # unsequenced + R6
            self.assertEqual(run_gate(root)[0], 0)

    def test_r1_names_both_directions_and_only_one_of_them_reddens(self):
        """Criterion 5: an entry naming no milestone is a WARN — the row
        survives its milestone on purpose, and a retired one is
        indistinguishable from an unwritten one. A milestone on no plan is
        UNSEQUENCED, a COUNTED line and never a finding: authoring a milestone
        and scheduling it are separate acts."""
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'a', 'gone')
            self._claims(root, 'a', '0.1.0', 'building')
            self._claims(root, 'b', '9.9.9', 'planning')
            write_config(root, '[pm]\nchecks = ["R1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('UNBOUND', out)
            self.assertIn('gone', out)          # names no milestone, warned
            self.assertIn('UNSEQUENCED', out)
            self.assertIn('b', out)             # on no plan, counted
            self.assertIn('pm add roadmap <milestone-id>', out)

    def test_r2_counts_the_backlog_and_never_reddens_on_it(self):
        # A healthy tree has many, and a gate that reddens on planning is a
        # gate people switch off (milestone risk 1).
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'a')
            self._claims(root, 'a', '0.1.0', 'building')
            self._claims(root, 'someday', '', 'planning')
            self._claims(root, 'later', '', 'planning')
            write_config(root, '[pm]\nchecks = ["R2"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('BACKLOG', out)
            # The fixture's own `0.1` milestone declares no version either, and
            # counting it is right: backlog is every milestone not proposed as
            # a release, not just the ones this case wrote.
            self.assertIn('3 milestone(s)', out)
            self.assertIn('someday', out)
            self.assertIn('later', out)

    def test_r3_refuses_to_let_one_document_decide_which_release_ships(self):
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'a')
            self._claims(root, 'a', '0.1.0', 'done')
            self._claims(root, 'b', '0.1.0', 'building')
            write_config(root, '[pm]\nchecks = ["R3"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('claimed by 2 milestones', out)
            self.assertIn('read first', out)

    def test_r4_history_is_a_prefix(self):
        """The invariant that makes "next = the first unshipped entry" correct
        rather than merely usual, and what lets version_at="start" mean
        anything."""
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'a', 'b')
            self._claims(root, 'a', '0.1.0', 'building')
            self._claims(root, 'b', '0.2.0', 'done')
            write_config(root, '[pm]\nchecks = ["R4"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('history is not a prefix', out)
            self.assertIn('b has shipped and sits AFTER a', out)

    def test_r6_catches_the_first_milestone_never_closed_in_both_directions(self):
        """0.3.0/bugs/the-first-milestone-never-closed, as a rule.

        Direction one is the bug: work that went out under someone else's
        version, whose record never moved. Direction two is its mirror: a
        milestone that finished having never been scheduled at all.
        """
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'a', 'b')
            self._claims(root, 'a', '0.1.0', 'planning')   # behind a shipped one
            self._claims(root, 'b', '0.2.0', 'done')
            self._claims(root, 'c', '7.7.7', 'done')       # done, on no plan
            write_config(root, '[pm]\nchecks = ["R6"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn("its work went out under someone else's version", out)
            self.assertIn('a sits at position 1', out)
            self.assertIn('finished without ever being scheduled', out)
            self.assertIn('7.7.7', out)

    def test_a_healthy_plan_passes_every_rule_in_the_family(self):
        with tree(story_statuses=('ready',)) as root:
            self._planned(root, 'a', 'b')
            self._claims(root, 'a', '0.1.0', 'done')
            self._claims(root, 'b', '0.2.0', 'building')
            self._claims(root, 'someday', '', 'planning')
            write_config(root, self.ALL)
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('DRIFT', out)
            self.assertNotIn('unknown rule', out)


class D7ADeclaredStateNobodyUses(unittest.TestCase):
    """D4 asks "is this word declared", never "is this word used".

    The finding: a tree adopted the flow as a CONFIG FIX, watched `check pm` go
    green, and used three of its eight declared milestone states — for its whole
    life, invisibly, because nothing anywhere related the declared set to the
    set in use. A WARN, never a finding: a tree mid-adoption legitimately has
    unused states, and 0.2.0 moved four rules to warnings for the same reason.
    """

    def test_it_names_the_unused_states_with_the_count_in_use(self):
        with tree(milestone_status='building', feature_status='building',
                  story_statuses=('done',)) as root:
            write_config(root, '[pm]\nchecks = ["U1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)          # a WARN never decides the code
            self.assertIn('(U1)', out)
            self.assertIn('WARN', out)
            self.assertIn('declared state(s) are in use', out)
            # The milestone kind declares 8 and this tree holds one word.
            self.assertIn('1 of 8 declared state(s) are in use', out)
            self.assertIn('packaging', out)

    def test_a_kind_with_no_grains_at_all_is_silent_rather_than_all_unused(self):
        # "Every declared state unused" means the tree holds no grain of that
        # kind — a different fact, and reporting it as flow drift would redden
        # (well, warn at) every tree that has not filed a bug yet.
        with tree() as root:
            write_config(root, '[pm]\nchecks = ["U1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('bug:', out)

    def test_off_unless_named(self):
        with tree(milestone_status='building') as root:
            write_config(root, '[pm]\nchecks = ["D1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('(U1)', out)

    def test_an_undeclared_word_in_the_tree_is_D4s_and_not_counted_here(self):
        # The census counts DECLARED states only; a `wombat` in a file is D4's
        # finding, and letting it into this census would make the two rules
        # argue about the same byte.
        with tree(milestone_status='building') as root:
            model.set_field(root / 'pm/roadmap/milestones/0.1.md',
                            'status', 'wombat')
            write_config(root, '[pm]\nchecks = ["U1"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertNotIn('wombat', out)


class AConfigErrorIsComplete(unittest.TestCase):
    """A `devkit.toml` read reports EVERY defect, and the flow first.

    Measured on a real adoption: that tree had a retired `[pm] review_slug_fallback`
    AND no `[pm.states.*]` at all. It was told about the retired key — the
    cosmetic one — and had to fix it and re-run to learn that the flow was
    missing, which is what stops every work-moving verb in the package. Every
    config refusal in this suite was covered SINGLY; nothing asserted what a
    consumer is told when the tree is wrong in more than one way, which is the
    normal state of a real adoption.
    """

    @staticmethod
    def _bare_tree(config: str):
        import tempfile as _tf
        ctx = _tf.TemporaryDirectory()
        root = Path(ctx.name) / 'repo'
        (root / 'pm' / 'roadmap').mkdir(parents=True)
        (root / '.git').mkdir()
        (root / 'devkit.toml').write_text(config, encoding='utf-8')
        return ctx, root

    def test_two_defects_are_both_reported_and_the_flow_comes_first(self):
        ctx, root = self._bare_tree('[pm]\nreview_slug_fallback = true\n')
        try:
            previous = os.getcwd()
            os.chdir(root)
            try:
                code, out = gate_both_streams(root)
            finally:
                os.chdir(previous)
            self.assertEqual(code, 2, out)
            self.assertIn('declares no flow', out)
            self.assertIn('review_slug_fallback', out)
            # The ORDER is the feature: the flow stops every verb, the retired
            # key is cosmetic, and the tree that motivated this was told the
            # cosmetic one.
            self.assertLess(out.index('declares no flow'),
                            out.index('review_slug_fallback'), out)
        finally:
            ctx.cleanup()

    def test_it_is_exit_2_once_not_once_per_defect(self):
        ctx, root = self._bare_tree(
            '[pm]\nreview_slug_fallback = true\nalso_done = ["x"]\n')
        try:
            previous = os.getcwd()
            os.chdir(root)
            try:
                code, out = gate_both_streams(root)
            finally:
                os.chdir(previous)
            self.assertEqual(code, 2, out)
        finally:
            ctx.cleanup()

    def test_five_defects_at_once_are_all_reported_flow_first(self):
        """Review D2/D3: two defects INSIDE `load()` reported as one, and any
        `load()` defect hid the whole retired-key sweep behind it. Each reader
        is now asked separately."""
        ctx, root = self._bare_tree(
            '[pm]\nreview_slug_fallback = true\nversion_at = "whenever"\n'
            'checks = ["D8", "D99"]\n')
        try:
            previous = os.getcwd()
            os.chdir(root)
            try:
                code, out = gate_both_streams(root)
            finally:
                os.chdir(previous)
            self.assertEqual(code, 2, out)
            for needle in ('declares no flow', 'version_at', 'D8',
                           'D99', 'review_slug_fallback'):
                self.assertIn(needle, out)
            self.assertEqual(out.count('[check:pm] ERROR'), 5, out)
            self.assertLess(out.index('declares no flow'),
                            out.index('version_at'), out)
        finally:
            ctx.cleanup()

    def test_every_pm_verb_reports_the_whole_set_not_just_check_pm(self):
        """Review D1: `pm validate` on the motivating tree printed ONE line,
        the cosmetic one, and never named the flow."""
        from agentic_sdlc.repo.pm import cli as pm_cli
        from agentic_sdlc.core.project import load_config, repo_root
        ctx, root = self._bare_tree(
            '[pm]\nreview_slug_fallback = true\nversion_at = "whenever"\n')
        try:
            previous = os.getcwd()
            os.chdir(root)
            repo_root.cache_clear()
            load_config.cache_clear()
            buf = io.StringIO()
            try:
                with contextlib.redirect_stderr(buf):
                    code = pm_cli.main(['validate'])
            finally:
                os.chdir(previous)
                repo_root.cache_clear()
                load_config.cache_clear()
            out = buf.getvalue()
            self.assertEqual(code, 2, out)
            self.assertIn('declares no flow', out)
            self.assertIn('review_slug_fallback', out)
            self.assertLess(out.index('declares no flow'),
                            out.index('review_slug_fallback'), out)
        finally:
            ctx.cleanup()

    def test_a_roster_error_carries_what_the_named_gates_would_have_said(self):
        """The adoption split its roster, watched `make check` go green, and
        reported the bump complete over a PM CLI refusing every verb. The one
        message it saw was about GATE NAMES."""
        from agentic_sdlc import cli as top
        from agentic_sdlc.core.config import ConfigError
        from agentic_sdlc.core.project import load_config, repo_root
        ctx, root = self._bare_tree(
            '[checks]\nall = ["doc", "pm", "uid", "tres"]\n')
        try:
            previous = os.getcwd()
            os.chdir(root)
            repo_root.cache_clear()
            load_config.cache_clear()
            try:
                with self.assertRaises(ConfigError) as caught:
                    top.all_roster()
            finally:
                os.chdir(previous)
                repo_root.cache_clear()
                load_config.cache_clear()
            said = str(caught.exception)
            self.assertIn('unknown gate(s) uid, tres', said)
            self.assertIn('ALSO', said)
            self.assertIn('declares no flow', said)
        finally:
            ctx.cleanup()
