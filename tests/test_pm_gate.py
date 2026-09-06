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
    """The tree D8/D9/D10 read: a `building` milestone, a `branch:` stamp and
    a `pyproject.toml` version."""
    mfile = root / 'pm/roadmap/0.1-demo/milestone.md'
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

    Each row is a tree that trips exactly the rule it names and the line the
    finding must carry. A rule that stopped firing, or started firing under a
    different name, fails here — which is the whole read-side contract.
    """

    # (rule, tree kwargs, the line the finding must carry)
    #
    # D2 and D6 fire on a parent still in `todo` — `ready` here. A parent at
    # `building` over finished children is NOT drift any more: `building` is
    # `in_progress`, and which in-progress word a parent holds is the
    # project's business (the D2/D5 resolution loss the CHANGELOG names).
    RULES = (
        ('D2', dict(feature_status='ready', story_statuses=('done',)),
         'all stories done, feature still ready'),
        ('D3', dict(milestone_status='done', feature_status='building'),
         'is done but feature'),
        # The set the tree is judged against: the FEATURE's declared order,
        # and nothing else now that the deprecation window has closed.
        ('D4', dict(feature_status='bogus'),
         'not in (planning ready building reviewing done obe)'),
        ('D5', dict(feature_status='planning', story_statuses=('done',)),
         'two places in this tree disagree'),
        ('D6', dict(milestone_status='ready', feature_status='done',
                    story_statuses=('done',)),
         'all 1 features are done'),
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
                self.assertEqual(code, 1, out)
                self.assertIn(message, out)

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
        # everything, which is exactly the false green worth avoiding.
        with tree(feature_status='planning', story_statuses=('done',)) as root:
            code, out = run_gate(root)
            self.assertEqual(code, 1)
            self.assertIn('all stories done, feature still planning', out)
            write_config(root, '[pm]\nchecks = ["D1","D3","D4","D5","D6"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 1)
            self.assertNotIn('all stories done', out)
            self.assertIn('two places in this tree disagree', out)


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
                    self.assertEqual(code, 1, out)
                    self.assertIn(self.MSG, out)
                    self.assertIn(f"is still {fstat!r}", out)
                    self.assertIn('the story is at work', out)

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
            self.assertEqual(code, 1, out)
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
        self.assertEqual(code, 1, out)
        self.assertIn(self.MSG, out)


class ConfigValidation(unittest.TestCase):
    """A malformed `[pm]` must never narrow the gate into a rubber stamp.

    A bare string iterates into characters and a table into keys, so an
    unvalidated `checks` silently disables every rule and prints PASS over real
    drift. Each spelling here is a plausible authoring mistake.
    """

    def _drifted(self, root: Path) -> None:
        write(root / 'pm/roadmap/0.1-demo/features/alpha/stories/s0.md',
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
    """D8/D9/D10 — branch-per-milestone, bump-at-start, and the mainline
    guard. All three are OPT-IN (decision D3): a project bumping at close, or
    running D9 alone, is running a different valid flow, not drifting.
    """

    def test_off_unless_named(self):
        # Every input the three rules exist to catch, on the stock roster.
        for branch, version in (('staging', '9.9.9'),  # D8: version mismatch
                                ('', '0.1'),           # D9: no branch stamp
                                ('main', '0.1')):      # D10: the mainline
            with self.subTest(branch=branch, version=version), \
                    tree(story_statuses=('ready',)) as root:
                building_milestone(root, branch=branch, version=version)
                code, out = run_gate(root)
                self.assertEqual(code, 0, out)

    def test_each_flow_rule_fires_when_it_is_named(self):
        # (checks, branch, version, extra config, the line the finding carries)
        rows = (
            ('["D8","D9"]', 'staging', '9.9.9', '',
             'does not match the in-progress milestone'),
            ('["D8","D9"]', '', '0.1', '', 'declares no branch:'),
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
        for checks, branch in (('["D8","D9"]', 'staging'),
                               ('["D10"]', 'milestone/0.1-demo'),
                               ('["D9"]', 'main')):
            with self.subTest(checks=checks, branch=branch), \
                    tree(story_statuses=('ready',)) as root:
                building_milestone(root, branch=branch, version='0.1')
                write_config(root, f'[pm]\nchecks = {checks}\n')
                code, out = run_gate(root)
                self.assertEqual(code, 0, out)
                self.assertNotIn('unknown rule', out)

    def test_d8_reports_over_every_in_progress_milestone(self):
        # A matching sibling used to mask the exact drift D8 exists for.
        # Decision D5: the rule is asked of EVERY milestone in `in_progress`,
        # so the one the version names is clean and the other one is the
        # finding — never "two are building, close one", which was the engine
        # deciding there can only be one.
        with tree(milestone_status='building', story_statuses=('ready',)) as root:
            write(root / 'pm/roadmap/0.2-two/milestone.md',
                  {'id': '"0.2"', 'name': 'Two', 'status': 'packaging',
                   'branch': 'staging'})
            building_milestone(root, branch='staging', version='0.1')
            write_config(root, '[pm]\nchecks = ["D8"]\n')
            code, out = run_gate(root)
            self.assertEqual(code, 1)
            self.assertIn("does not match the in-progress milestone '0.2'", out)
            self.assertNotIn("milestone '0.1'", out)

    def _d8_tree_with_version(self, version: str, released: str = '0.0.9'):
        # 0.1 is building; `released` is the DONE milestone retire's lag-by-one
        # keeps in the tree — the only id a hotfix may extend.
        ctx = tree(milestone_status='building', story_statuses=('ready',))
        root = ctx.__enter__()
        building_milestone(root, branch='staging', version=version)
        write(root / f'pm/roadmap/{released}-old/milestone.md',
              {'id': f'"{released}"', 'name': 'Old', 'status': 'done'})
        write_config(root, '[pm]\nchecks = ["D8"]\n')
        return ctx, root

    def test_d8_admits_a_hotfix_of_the_released_milestone_and_nothing_else(self):
        # 0.0.9 shipped; 0.0.9.1 is a hotfix cut from the mainline that carries
        # no milestone of its own — the release branch must pass. 0.1.1 extends
        # the BUILDING id, which is not a hotfix of anything shipped, and
        # `0.0.9.01` is the same version spelled so it no longer resolves. The
        # rest of the version grammar's refusal matrix belongs to the grammar
        # (SDLC.md §5), not to this surface.
        for version, expected in (('0.0.9.1', 0), ('0.1.1', 1), ('0.0.9.01', 1)):
            with self.subTest(version=version):
                ctx, root = self._d8_tree_with_version(version)
                try:
                    code, out = run_gate(root)
                    self.assertEqual(code, expected, out)
                    if expected:
                        self.assertIn('(D8)', out)
                    else:
                        self.assertNotIn('(D8)', out)
                finally:
                    ctx.__exit__(None, None, None)


class ConfigValueErrors(unittest.TestCase):
    def test_a_bad_version_pattern_is_exit_2_not_a_finding(self):
        for bad in ('version_pattern = "version = \\"(.*\\""',
                    'version_pattern = "^version = .*$"'):
            with self.subTest(bad=bad), tree() as root:
                write_config(root, f'[pm]\nchecks = ["D8"]\n{bad}\n')
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
        for key in ('roadmap_dir', 'review_dir', 'template_dir'):
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
        p = root / 'pm/roadmap/0.1-demo/bugs' / rel
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
            bdir = root / 'pm/roadmap/0.1-demo/bugs'
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
    """`stories/` is the same never-descended slot shape `bugs/` was.

    The bug walk was made recursive and case-insensitive on extension and
    `stories/` never got it, so a story parked one directory down was invisible
    to every rule at once — and worse than invisible: D4 could not see its
    status, and D2 read "all stories done" off the ones it could see and filed
    a FALSE finding against a feature that had an unfinished story in it.
    """

    FDIR = 'pm/roadmap/0.1-demo/features/alpha'

    def test_a_story_the_walk_cannot_see_becomes_a_FALSE_D2_finding(self):
        # Not just an undercount: the stories it COULD see were all done, so
        # D2 told the author to close a feature with an open story in it.
        for rel in ('stories/parked/s2.md', 'stories/S2.MD'):
            with self.subTest(rel=rel), \
                    tree(feature_status='building',
                         story_statuses=('done',)) as root:
                write(root / self.FDIR / rel,
                      {'id': '0.1/alpha/s2', 'feature': '0.1/alpha',
                       'milestone': '"0.1"', 'name': 'S2', 'status': 'ready'})
                code, out = run_gate(root)
                self.assertIn('2 story/ies', out)
                self.assertNotIn('all stories done', out)

    def test_D4_can_see_a_nested_story_with_an_illegal_status(self):
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            write(root / self.FDIR / 'stories/parked/s2.md',
                  {'id': '0.1/alpha/s2', 'feature': '0.1/alpha',
                   'milestone': '"0.1"', 'name': 'S2',
                   'status': 'NOT-A-REAL-STATUS'})
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn("status 'NOT-A-REAL-STATUS' not in", out)

    def test_a_non_grain_md_parked_under_stories_is_not_a_story(self):
        # The same rule `bugs/` gets, from the same walk: a README beside the
        # stories is not a story with an empty status.
        with tree(feature_status='building', story_statuses=('ready',)) as root:
            (root / self.FDIR / 'stories/README.md').write_text(
                '# how stories are written here\n', encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('1 story/ies', out)


class StructuralIntegrity(unittest.TestCase):
    def test_a_dir_with_no_grain_file_is_reported_not_skipped(self):
        with tree(story_statuses=('ready',)) as root:
            ghost = root / 'pm/roadmap/0.2-beta/features/gizmo'
            write(ghost / 'feature.md',
                  {'id': '0.2/gizmo', 'milestone': '"0.2"', 'name': 'G',
                   'status': 'done', 'reviewed': ''})
            # 0.2-beta has NO milestone.md, so its drifted feature would
            # otherwise vanish from the scan entirely.
            code, out = run_gate(root)
            self.assertEqual(code, 1)
            self.assertIn('SKIPPED', out)


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
        rows = (
            ('V2', 'features/alpha/feature.md', 'id', '0.1/WRONG',
             'does not match its path'),
            ('V3', 'features/alpha/stories/s0.md', 'feature',
             '0.1/somewhere-else', 'but it lives under feature'),
            ('V4', 'features/alpha/feature.md', 'depends_on',
             '["0.1/no-such-feature"]', 'resolves to nothing'),
        )
        for rule, rel, field, value, message in rows:
            with self.subTest(rule=rule), tree(story_statuses=('ready',)) as root:
                model.set_field(root / 'pm/roadmap/0.1-demo' / rel, field, value)
                findings, _ = self._run(root)
                self.assertTrue(any(message in f for f in findings), findings)

    def test_v4_a_ref_into_a_pruned_milestone_is_unverifiable_not_a_finding(self):
        # Git history is the archive: depending on a milestone that has been
        # pruned is expected, so it is censused rather than failed.
        with tree() as root:
            ff = root / 'pm/roadmap/0.1-demo/features/alpha/feature.md'
            model.set_field(ff, 'depends_on', '["0.0.9/long-gone"]')
            findings, census = self._run(root)
            self.assertEqual(findings, [])
            self.assertEqual(census['unverifiable'], 1)

    def test_v5_detects_a_dependency_cycle(self):
        with tree() as root:
            run_cli(root, 'new', 'feature', '0.1', 'beta', 'Beta')
            fdir = root / 'pm/roadmap/0.1-demo/features'
            model.set_field(fdir / 'alpha/feature.md', 'depends_on', '["0.1/beta"]')
            model.set_field(fdir / 'beta/feature.md', 'depends_on', '["0.1/alpha"]')
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
            ff = root / 'pm/roadmap/0.1-demo/features/alpha/feature.md'
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
                "pm/roadmap/0.1-demo/bugs/seed-is-zero.md: caused_by "
                "'0.1/no-such-feature' resolves to nothing "
                "(its milestone IS in the tree)"])
            self.assertEqual(census['refs'], 1)

            ff = root / 'pm/roadmap/0.1-demo/features/alpha/feature.md'
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
            self.assertIn("  DRIFT  pm/roadmap/0.1-demo/bugs/seed-is-zero.md: "
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
        ff = root / 'pm/roadmap/0.1-demo/features/alpha/feature.md'
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
            ff = root / 'pm/roadmap/0.1-demo/features/alpha/feature.md'
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
        p = root / 'pm/roadmap/0.1-demo/bugs' / f'{slug}.md'
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
                    self.assertIn("status '' not in", out)
                    self.assertIn('missing id: or status:', out)
                    self.assertIn('1 story/ies', out)

    def test_a_damaged_bug_is_reported_not_dropped(self):
        for form in DAMAGE_FORMS:
            with self.subTest(form=form):
                with tree(milestone_status='building') as root:
                    write_config(root, self.BUG_TOML)
                    damage(self._bug(root, 'seed-is-zero', 'open'), form)
                    code, out = run_gate(root)
                    self.assertEqual(code, 1, out)
                    self.assertIn("bug status '' is not in", out)
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
                    self.assertIsNotNone(
                        model.story_file(cfg_for(root), '0.1/alpha/s0'))
                    code, out = run_cli(root, 'story', 'building', '0.1/alpha/s0')
                    self.assertEqual(code, 2, out)
                    self.assertNotIn('no story resolves', out)
                    # The one refusal a status verb keeps: the FRONTMATTER is
                    # malformed, which is a fact about the file. What the
                    # status VALUE happens to be is never a refusal.
                    self.assertIn('malformed frontmatter', out)

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
            sdir = root / 'pm/roadmap/0.1-demo/features/alpha/stories'
            bdir = root / 'pm/roadmap/0.1-demo/bugs'
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
            self.assertIn('0 bug(s)', out)
            self.assertIn('1 story/ies', out)
            self.assertIn('3 note(s) skipped', out)

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
            hold = root / 'pm/roadmap/0.1-demo/bugs/.hold'
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
            sdir = root / 'pm/roadmap/0.1-demo/features/alpha/stories'
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
        for needle in ('resolves to nothing',                         # D1
                       'all stories done, feature still shaped',      # D2
                       'milestone 0.9 is done but feature',           # D3
                       "status 'wombat' not in",                      # D4 feature
                       "status 'wobmat' not in",                      # D4 story
                       "bug status 'fidel' is not in",                # D4 bug
                       'two places in this tree disagree',            # D5
                       "milestone 2.0 is 'queued' but all 1 features are done",  # D6
                       'in-progress milestone 1.1 declares no branch',  # D9/D10
                       'D10'):
            self.assertIn(needle, out_r, needle)
        # D5 fires per story that has started under a `todo` feature: both
        # finished stories of `stalled`, the one `doing` story of `ahead`.
        self.assertEqual(out_r.count('two places in this tree disagree'), 3)
        # ...and the normal path is silent: a `dropped` story is finished.
        self.assertNotIn('normal', out_r.split('\n[check:pm]')[-1])
        self.assertNotIn('1.0/normal', out_r)

    def test_pm_status_says_the_same_thing_about_both_trees(self):
        def status(root):
            return run_cli(root, 'status')
        with self._copies() as (renamed, stock):
            code_r, out_r = self._run(renamed, status)
            code_s, out_s = self._run(stock, status)
        self.assertEqual((code_r, code_s), (0, 0), out_r + out_s)
        # Whitespace-normalised per line: the status column is padded to a
        # width, and a longer word is a longer word (rule 6 covers the gate's
        # line shapes, not this board's alignment).
        import re

        def squeeze(text: str) -> list[str]:
            return [' '.join(re.sub(r'\s+\]', ']', ln).split())
                    for ln in text.splitlines()]
        self.assertEqual(squeeze(self._unrename(out_r)), squeeze(out_s))
        self.assertIn('stories 2/2 done', out_r)          # shipped + dropped
        self.assertIn('<DRIFT: all stories done, feature still shaped>', out_r)
