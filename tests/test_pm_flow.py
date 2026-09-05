"""test_pm_flow.py — the flow a PROJECT declares, and what the engine refuses.

`docs/design/state-categories.md`. The engine keeps three opinions and no more:
the category set is `todo` / `in_progress` / `done`, they are ordered that way,
and every declared state maps to exactly one. Everything else — how many
states, what they are called, which category each sits in, what order they
appear in within it — is the project's.

**The point of the seam this file guards** is that `[pm.states.*]` is a
DECLARATION with no runtime fallback behind it. `DEFAULT_FLOWS` is what `init`
WRITES; a reader that fell back to it would make the shipped words persist
forever inside a default argument, invisible to the project whose flow they
claim to be. Hard rule 5, as it now reads: a GATE ships stock defaults, a
WORKFLOW does not.

Every refusal below is exit 2 and a fact about the INPUT, which rule 9 names as
the one thing this package is always allowed to refuse.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.pm import model  # noqa: E402

FULL = '\n'.join(
    f'[pm.states.{kind}]\n'
    + '\n'.join(f'{cat} = {list(states)!r}'.replace("'", '"')
                for cat, states in model.DEFAULT_FLOWS[kind].items())
    for kind in model.FLOW_KINDS)


@contextlib.contextmanager
def tree(config: str = ''):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        if config:
            (root / 'devkit.toml').write_text(config, encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def load(config: str) -> model.PmConfig:
    with tree(config):
        return model.load()


# --- the closed set -----------------------------------------------------------
def test_the_category_set_is_three_and_ordered():
    assert model.CATEGORIES == ('todo', 'in_progress', 'done')


def test_the_seed_is_valid_under_the_rules_it_will_be_read_by():
    """The one test that would have caught a seed nobody can load: `init`
    writes `render_seed()`, so it has to survive `load()`."""
    cfg = load(model.render_seed())
    assert sorted(cfg.flows) == sorted(model.FLOW_KINDS)
    assert model.flow_of(cfg, 'story').order == model.LIFECYCLE


def test_the_seed_reproduces_todays_lifecycle_for_the_three_that_share_it():
    for kind in ('milestone', 'feature', 'story'):
        flow = model.Flow(kind, model.DEFAULT_FLOWS[kind],
                          {st: cat
                           for cat, sts in model.DEFAULT_FLOWS[kind].items()
                           for st in sts}, {})
        assert flow.order == model.LIFECYCLE, kind


def test_a_bugs_vocabulary_stops_being_a_special_case():
    """It is declared exactly like the other three, which is the point of doing
    this per KIND rather than once."""
    flow = load(FULL).flows['bug']
    assert flow.order == ('open', 'fixed', 'closed')
    assert flow.category('closed') == 'done'


# --- absent is ABSENT, never the seed -----------------------------------------
def test_a_tree_declaring_nothing_gets_no_flow_rather_than_the_default():
    assert load('').flows == {}


def test_asking_for_a_flow_that_was_never_declared_is_refused_by_name():
    cfg = load('')
    with pytest.raises(ConfigError) as err:
        model.flow_of(cfg, 'story')
    assert '[pm.states.story]' in str(err.value)
    assert 'there is no default' in str(err.value)


def test_the_refusal_names_the_command_rather_than_the_seed_to_paste():
    """A refusal that hands a reader forty lines of TOML to copy is a refusal
    that gets copied wrong."""
    with pytest.raises(ConfigError) as err:
        model.flow_of(load(''), 'story')
    message = str(err.value)
    assert 'agentic-sdlc pm init' in message
    assert '[pm.states.milestone]' not in message, (
        'the refusal pasted the seed instead of naming the verb that writes it')


# --- the three opinions, each refused at exit 2 -------------------------------
@pytest.mark.parametrize('config,expected', [
    # a category outside the closed set
    ('[pm.states.story]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
     'wombat = ["d"]\n', 'the set is closed'),
    # a state in two categories
    ('[pm.states.story]\ntodo = ["a"]\nin_progress = ["a"]\ndone = ["c"]\n',
     'maps to exactly one category'),
    # a category with nothing in it
    ('[pm.states.story]\ntodo = ["a"]\nin_progress = ["b"]\n',
     'declares no state in done'),
    # a transition to a state nobody declared
    ('[pm.states.story]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
     '[pm.transitions.story]\nstory-done = "shipped"\n',
     'does not declare'),
    # transitions with no states at all
    ('[pm.transitions.story]\nstory-done = "done"\n',
     'the states have to exist first'),
    # a grain kind this package never walks
    ('[pm.states.wombat]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n',
     'names grain kind(s) wombat'),
    # a value of the wrong shape
    ('[pm.states.story]\ntodo = 3\nin_progress = ["b"]\ndone = ["c"]\n',
     'must be a string or a non-empty list'),
])
def test_a_malformed_declaration_is_a_config_error(config, expected):
    with pytest.raises(ConfigError) as err:
        load(config)
    assert expected in str(err.value), str(err.value)


def test_a_partial_declaration_is_refused_rather_than_half_honoured():
    """Three kinds declared and one absent is the worst of both: the omitted
    kind falls back to words the project never chose, silently."""
    partial = '\n'.join(
        f'[pm.states.{k}]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
        for k in ('milestone', 'feature', 'story'))
    with pytest.raises(ConfigError) as err:
        load(partial)
    assert 'and not bug' in str(err.value), str(err.value)
    assert 'a partial flow is worse than none' in str(err.value)


# --- what a project may do, and the engine may not have an opinion about ------
def test_a_project_may_rename_every_word_and_the_categories_still_answer():
    """The northstar, as a test. Not one of these words is in `LIFECYCLE`."""
    renamed = ('[pm.states.story]\n'
               'todo = ["icebox", "groomed"]\n'
               'in_progress = ["in-dev", "in-review", "staged"]\n'
               'done = ["shipped", "abandoned"]\n')
    flow = load(renamed + '\n'.join(
        f'[pm.states.{k}]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
        for k in ('milestone', 'feature', 'bug'))).flows['story']
    assert flow.category('in-dev') == 'in_progress'
    assert flow.category('abandoned') == 'done'
    assert flow.order == ('icebox', 'groomed', 'in-dev', 'in-review',
                          'staged', 'shipped', 'abandoned')


def test_a_state_the_project_never_declared_has_no_category_rather_than_a_guess():
    """The D4 drift `check pm` reports. Inventing a category for a word the
    engine has never seen would be it deciding what that word must mean."""
    assert load(FULL).flows['story'].category('wombat') is None


def test_order_within_a_category_is_the_projects_and_is_preserved():
    odd = ('[pm.states.story]\ntodo = ["a"]\n'
           'in_progress = ["z-last", "a-first"]\ndone = ["c"]\n')
    flow = load(odd + '\n'.join(
        f'[pm.states.{k}]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
        for k in ('milestone', 'feature', 'bug'))).flows['story']
    assert flow.order == ('a', 'z-last', 'a-first', 'c')


# --- this repo's own declaration ----------------------------------------------
def test_this_repo_declares_its_own_flow_and_it_loads():
    """Self-hosting: the tree that ships the reader declares the section."""
    cfg = model.load()
    for kind in model.FLOW_KINDS:
        assert model.flow_of(cfg, kind).order, kind


def test_this_repos_declaration_carries_obe_in_done():
    """The defect `also_done` was minted for, now expressed rather than
    enumerated: a story that was abandoned is FINISHED, and under a bare-word
    predicate it held its feature open forever."""
    assert model.flow_of(model.load(), 'story').category('obe') == 'done'


def test_the_seed_parses_as_toml_at_all():
    """`render_seed` builds text that `init` writes into a config file. A seed
    that is not valid TOML would leave a tree unloadable by every verb."""
    assert set(tomllib.loads(model.render_seed())['pm']['states']) == set(
        model.FLOW_KINDS)


# --- the two verbs ------------------------------------------------------------
class TestHolds:
    """`holds(grains, category)` — are they all there, and who is not."""

    def test_it_answers_and_names_who_is_not_there(self):
        cfg = load(FULL)
        held = model.holds(cfg, 'story', [('s1', 'done'), ('s2', 'building'),
                                          ('s3', 'planning')], 'done')
        assert not held
        assert held.names == ('s2 is building', 's3 is planning')
        assert held.counted == 3

    def test_an_empty_set_is_satisfied_and_says_all_of_how_many(self):
        held = model.holds(load(FULL), 'story', [], 'done')
        assert held
        assert held.counted == 0

    def test_it_asks_the_CATEGORY_so_a_dropped_story_does_not_block(self):
        """The defect the whole design was written from. A story at `obe` is
        FINISHED and is never going to be `done`; under a bare-word predicate
        it held its feature open forever. Jira ships that exact mistake as a
        documented training problem."""
        dropped = FULL.replace('done = ["done"]', 'done = ["done", "obe"]')
        assert model.holds(load(dropped), 'story',
                           [('s1', 'done'), ('s2', 'obe')], 'done')

    def test_a_state_the_project_never_declared_BLOCKS_rather_than_passes(self):
        """Rule 4. An unrecognised word is exactly the case where a permissive
        answer would be a gate missing real drift and printing PASS."""
        held = model.holds(load(FULL), 'story', [('s1', 'wombat')], 'done')
        assert not held
        assert held.names == ('s1 is wombat',)

    def test_a_category_outside_the_closed_set_is_a_config_error(self):
        with pytest.raises(ConfigError):
            model.holds(load(FULL), 'story', [], 'wombat')

    def test_it_refuses_a_tree_that_declared_no_flow(self):
        with pytest.raises(ConfigError):
            model.holds(load(''), 'story', [('s1', 'done')], 'done')


class TestMove:
    """`move(grain, to_state)` — is this transition declared?"""

    def test_a_declared_state_is_permitted(self):
        assert model.move_defect(load(FULL), 'story', 'reviewing') == ''

    def test_an_undeclared_state_is_refused_and_names_what_this_project_has(
            self):
        defect = model.move_defect(load(FULL), 'story', 'wombat')
        assert 'not a story state' in defect
        assert 'planning, ready, building' in defect

    def test_the_engine_has_no_opinion_about_which_state_may_FOLLOW_which(self):
        """There is still no edge graph, and the reason has not changed: a
        `sed` of the `status:` line reaches any state the CLI would have
        refused, so a graph taxes whoever uses the sanctioned tool and stops
        nobody else. END STATE is what D3/D4/D5 check."""
        cfg = load(FULL)
        for state in model.flow_of(cfg, 'story').order:
            assert model.move_defect(cfg, 'story', state) == '', state

    def test_a_renamed_vocabulary_is_moved_through_exactly_as_the_stock_one(
            self):
        renamed = ('[pm.states.story]\ntodo = ["icebox"]\n'
                   'in_progress = ["in-dev"]\ndone = ["shipped"]\n'
                   + '\n'.join(
                       f'[pm.states.{k}]\ntodo = ["a"]\nin_progress = ["b"]\n'
                       f'done = ["c"]\n'
                       for k in ('milestone', 'feature', 'bug')))
        cfg = load(renamed)
        assert model.move_defect(cfg, 'story', 'in-dev') == ''
        assert model.move_defect(cfg, 'story', 'building') != ''


class TestTransitionTarget:
    """ASK BY CATEGORY, WRITE BY NAME — a category holds several states, so a
    step that wrote "the done category" would make the engine guess a member."""

    def test_a_declared_step_names_its_exact_state(self):
        cfg = load(FULL + '\n[pm.transitions.story]\nstory-done = "done"\n')
        assert model.transition_target(cfg, 'story', 'story-done') == 'done'

    def test_an_undeclared_step_is_None_rather_than_a_guess(self):
        cfg = load(FULL)
        assert model.transition_target(cfg, 'story', 'story-done') is None
