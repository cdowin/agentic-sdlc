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
import io
import json
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
        (root / '.git').mkdir(exist_ok=True)  # a MARKER, not a repo: `repo_root` walks for it
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
    assert model.flow_of(cfg, 'story').order == model.LIFECYCLE + ('obe',)


def test_the_seed_is_todays_lifecycle_plus_a_word_for_abandoned_work():
    """`obe` is the ONE place the seed is not literally `LIFECYCLE`, and it is
    deliberate.

    Found by asking why a freshly-initialised tree had no word for abandoned
    work while this repo's own devkit.toml had one: `also_done`'s live defect —
    a story at `obe` holding its feature open forever — would have come
    straight back for every new consumer. Shipping the fix as a repair a
    project has to discover is shipping the bug.

    It costs a tree that never types `obe` nothing, which is what makes it safe
    to seed rather than a behaviour change: an unused state is an unused state.
    """
    for kind in ('milestone', 'feature', 'story'):
        flow = model.Flow(kind, model.DEFAULT_FLOWS[kind],
                          {st: cat
                           for cat, sts in model.DEFAULT_FLOWS[kind].items()
                           for st in sts}, {})
        assert flow.order == model.LIFECYCLE + ('obe',), kind
        assert flow.category('obe') == 'done', kind
        # Every word LIFECYCLE has, in its order, is still here and still in
        # the category it was in — that is the "no behaviour change" half.
        assert flow.order[:len(model.LIFECYCLE)] == model.LIFECYCLE, kind


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


# --- `pm vocabulary` — the pin-bump verb --------------------------------------
# It stopped being cosmetic in phase 6. Its docstring used to say "there are no
# TRANSITIONS to print", which `[pm.transitions.<kind>]` falsifies, and it is
# the one place a consumer can read what a VERSION's declared surface is
# without scraping help text or a changelog (plan review finding P6).
def vocab(*argv: str) -> tuple[int, str]:
    """`pm vocabulary` in the tree the caller is already standing in."""
    from agentic_sdlc.repo.pm import cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = cli.main(['vocabulary', *argv])
    return code, buf.getvalue()


# `FULL` ends on a value line with no trailing newline, so the join is
# EXPLICIT: `FULL + TRANSITIONS` glued a `]` to a `[` and every case using it
# failed as a TOML parse error rather than as the thing it was asserting.
WITH_TRANSITIONS = FULL + ('\n[pm.transitions.story]\nclaimed = "building"\n'
                           'story-done = "done"\n')


class TestVocabulary:
    def test_it_prints_the_categories_and_the_states_in_each(self):
        with tree(FULL):
            code, out = vocab()
        assert code == 0
        assert '[pm.states.story]' in out
        for category in model.CATEGORIES:
            assert category in out
        # The states arrive UNDER their category, not as one flat list: the
        # mapping is the whole thing phase 6 made declarable.
        block = out.split('[pm.states.bug]')[1]
        assert 'todo         open' in block
        assert 'in_progress  fixed' in block
        assert 'done         closed' in block

    def test_it_prints_the_transitions_the_project_declared(self):
        with tree(WITH_TRANSITIONS):
            code, out = vocab()
        assert code == 0
        assert 'claimed -> building' in out
        assert 'story-done -> done' in out
        # And says so rather than printing a blank where a table would be.
        assert '(this project declares none)' in out

    def test_a_renamed_vocabulary_is_what_gets_printed(self):
        """No engine word leaks into the flow block. If this ever prints
        `building` for a project that never wrote it, the verb is reporting the
        seed instead of the declaration."""
        renamed = ('[pm.states.story]\ntodo = ["icebox"]\n'
                   'in_progress = ["in-dev"]\ndone = ["shipped"]\n'
                   + '\n'.join(
                       f'[pm.states.{k}]\ntodo = ["a"]\nin_progress = ["b"]\n'
                       f'done = ["c"]\n'
                       for k in ('milestone', 'feature', 'bug')))
        with tree(renamed):
            _, out = vocab()
        flow = out.split('[pm.states.milestone]')[1].split('published steps')[0]
        assert 'in-dev' in flow and 'shipped' in flow
        assert 'building' not in flow, (
            'the verb printed the seed instead of what the project declared')

    def test_the_published_step_names_come_from_the_conveyor_REGISTRY(self):
        """Asserted against the registry itself, never a literal list here.

        A literal would be a third spelling of `conveyor/steps.py` — the one
        in the CLI, the one in this test, and the real one — and the first
        release that adds a step would leave two of the three wrong while this
        passed. So the census is derived, and the FLOOR is that it is not
        empty: an emptied registry would satisfy a subset assertion in silence
        (hard rule 4).
        """
        from agentic_sdlc.repo.conveyor import steps
        with tree(FULL):
            _, out = vocab()
        published = {name for operation in steps.REGISTRIES
                     for name in steps.registry_for(operation)}
        assert published, 'the step registry is empty — nothing was censused'
        # `textwrap` wraps the lists, so the whitespace is normalised before
        # the membership question is asked; the names themselves are never
        # broken (`break_on_hyphens=False`).
        printed = set(out.split())
        assert published <= printed, sorted(published - printed)
        for operation in steps.REGISTRIES:
            assert operation in out, operation

    def test_it_says_whose_the_step_key_set_IS(self):
        """P6's ruling, and it has to be VISIBLE in the output: the keys are
        the engine's published vocabulary a project selects from. Presented as
        pure project declaration, the table would be the engine's opinion with
        a config file in front of it."""
        with tree(FULL):
            _, out = vocab()
        assert 'ENGINE' in out
        assert 'cannot invent one' in out

    def test_it_prints_the_rule_ids_it_always_did(self):
        with tree(FULL):
            _, out = vocab()
        assert f'rules  {" ".join(model.KNOWN_CHECKS)}' in out

    def test_it_no_longer_claims_there_are_no_transitions(self):
        """The sentence phase 6 falsified. It is asserted as an ABSENCE
        because that is the defect: output that contradicts the config schema
        the same release shipped."""
        with tree(WITH_TRANSITIONS):
            _, out = vocab()
        assert 'there is no transition graph' not in out
        assert 'no EDGE graph' in out, (
            'the narrower true statement went with the false one')

    def test_an_unknown_flag_is_still_a_usage_error(self):
        with tree(FULL):
            code, _ = vocab('--wombat')
        assert code == 2


class TestVocabularyWithNoFlow:
    """The tree `flow_of` refuses is the tree this verb has to ANSWER.

    `vocabulary` is what you run to find out what to declare; a discovery verb
    that refuses until you have already discovered the answer is a closed loop.
    Every other flow-reading verb refuses here, and that is correct — they
    create, move or locate work over states the project never chose.
    """

    def test_it_does_not_crash(self):
        with tree(''):
            code, out = vocab()
        assert code == 0, out

    def test_it_reports_the_absence_by_name(self):
        with tree(''):
            _, out = vocab()
        # WHITESPACE-NORMALISED: the paragraph is prose and its line breaks
        # are not contract, unlike the `  DRIFT  ` / `[check:x] PASS` shapes
        # consumers grep (hard rule 6). Asserting against the wrap made a
        # re-flow of one sentence look like the absence going unreported.
        prose = ' '.join(out.split())
        assert '[pm.states.*] is not in devkit.toml' in prose
        assert 'no default' in prose
        assert 'agentic-sdlc pm init' in prose

    def test_it_prints_what_init_would_write_and_it_is_the_SEED(self):
        with tree(''):
            _, out = vocab()
        # Indented by two in the transcript, so a reader cannot mistake it for
        # the tree's own config. Byte-identical once that indent is removed.
        for line in model.render_seed().splitlines():
            if line:
                assert f'  {line}' in out, line

    def test_what_it_prints_is_a_declaration_that_LOADS(self):
        """The seed it hands a reader has to survive the reader it is pasted
        into — otherwise the verb's whole answer is a config error."""
        with tree(''):
            _, out = vocab()
        pasted = '\n'.join(
            ln[2:] for ln in out.splitlines()
            if ln.startswith('  [pm.states.') or ln.startswith('  todo')
            or ln.startswith('  in_progress') or ln.startswith('  done'))
        assert sorted(load(pasted).flows) == sorted(model.FLOW_KINDS)

    def test_the_flat_sets_the_gate_still_measures_are_printed_anyway(self):
        """Phase 6 changed no question the engine asks: `check pm` D4 still
        measures a status against `[pm] <kind>_states`. Dropping those lines
        would hide the set the gate actually runs on."""
        with tree(''):
            _, out = vocab()
        assert 'bug        open fixed closed' in out

    def test_the_json_payload_says_the_flow_is_absent_rather_than_omitting_it(
            self):
        """A consumer diffing two pins has to tell "this tree declares
        nothing" from "this release dropped the field"."""
        with tree(''):
            _, out = vocab('--json')
        payload = json.loads(out)
        assert payload['flow_declared'] is False
        assert payload['grains']['story']['flow'] is None
        assert payload['seed'] == model.render_seed()


class TestVocabularyJson:
    def payload(self, config: str = WITH_TRANSITIONS) -> dict:
        with tree(config):
            code, out = vocab('--json')
        assert code == 0, out
        return json.loads(out)

    def test_it_carries_the_categories_and_the_kinds(self):
        payload = self.payload()
        assert payload['categories'] == list(model.CATEGORIES)
        assert payload['flow_kinds'] == list(model.FLOW_KINDS)
        assert payload['flow_declared'] is True

    def test_it_carries_the_flow_per_kind(self):
        flow = self.payload()['grains']['story']['flow']
        assert flow['categories']['in_progress'] == [
            'building', 'reviewing', 'accepted', 'packaging']
        # The seed's `done` carries `obe` beside `done`, so the order is
        # LIFECYCLE plus the one word for abandoned work.
        assert flow['order'] == list(model.LIFECYCLE) + ['obe']
        assert flow['transitions'] == {'claimed': 'building',
                                       'story-done': 'done'}

    def test_it_carries_the_published_steps_from_the_registry(self):
        from agentic_sdlc.repo.conveyor import steps
        published = self.payload()['published_steps']
        assert set(published) == set(steps.REGISTRIES)
        for operation, names in published.items():
            assert names == list(steps.registry_for(operation)), operation

    def test_it_carries_the_rule_ids_and_the_flat_sets_it_always_did(self):
        payload = self.payload()
        assert payload['checks'] == list(model.KNOWN_CHECKS)
        assert payload['grains']['bug']['states'] == list(
            model.DEFAULT_BUG_STATES)

    def test_it_carries_the_seed_in_every_payload(self):
        """Declared, it is what a pin bump diffs a declaration against;
        undeclared, it is what `init` would write. One key, both readings."""
        assert self.payload()['seed'] == model.render_seed()

    def test_the_note_that_says_whose_the_key_set_is_travels_in_json_too(self):
        """A reader who only ever sees `--json` must still see P6's ruling."""
        note = self.payload()['notes']['published_steps']
        assert 'ENGINE' in note and 'cannot invent one' in note


# --- the installable's LIVE section -------------------------------------------
def test_the_seed_config_carries_render_seed_VERBATIM():
    """P1: `installables/project-devkit.toml` had ZERO uncommented lines, and
    every section it seeds is inert on arrival because a gate ships stock
    defaults and a commented default IS the default. `[pm.states.*]` cannot be
    — there is no runtime fallback behind it, so a commented one leaves a
    freshly-initialised tree refused on its first `pm` call.

    BYTE-IDENTICAL, not merely equivalent. A hand-copied table is a second
    spelling of `DEFAULT_FLOWS`, and the copy nobody runs is the one that goes
    stale; this test is what makes the file's live section and `render_seed()`
    one table with two locations rather than two tables.
    """
    body = (REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'installables'
            / 'project-devkit.toml').read_text(encoding='utf-8')
    assert model.render_seed() in body, (
        'the installable no longer carries render_seed() verbatim — the table '
        'was hand-edited in one of its two locations')


def test_the_seed_config_declares_the_flow_LIVE_and_nothing_else():
    """The live lines are the flow's and no other section's. A default that
    stops being commented is a gate acquiring an opinion the project cannot
    see it did not choose (hard rule 5)."""
    body = (REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'installables'
            / 'project-devkit.toml').read_text(encoding='utf-8')
    live = [ln for ln in body.splitlines()
            if ln.strip() and not ln.lstrip().startswith('#')]
    assert live == [ln for ln in model.render_seed().splitlines() if ln.strip()]


def test_a_tree_seeded_with_the_installable_can_be_read_by_the_reader():
    """The whole point of P1, end to end: the config `init` writes has to
    satisfy `flow_of` on the tree's FIRST `pm` call. A commented section parses
    and then refuses, which is the failure this proves is gone."""
    body = (REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'installables'
            / 'project-devkit.toml').read_text(encoding='utf-8')
    cfg = load(body)
    for kind in model.FLOW_KINDS:
        assert model.flow_of(cfg, kind).order, kind
