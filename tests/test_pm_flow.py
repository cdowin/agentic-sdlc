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

**Cut in 0.2.0 (feature `the-proof-is-named-in-the-criterion`, phase B):** the
cases that proved `tomllib` parses TOML or that a tuple constant has the values
it is written with, and the seed round-trip asserted from five directions —
`render_seed()` is proven where it BITES, in the installable a fresh consumer
is handed, loaded by the reader that will read it. What is left is the three
engine opinions refusing at exit 2, the absence of a fallback, and the renamed
vocabulary, which is the northstar expressed as a test.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
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

SEED_CONFIG = (REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'installables'
               / 'project-devkit.toml')


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


def with_story(story_block: str) -> str:
    """One kind declared by the caller; the other three declared minimally.

    A partial declaration is refused (see below), so a case about `story` still
    has to say something about the rest — and saying it in one place keeps the
    subject of each test the only interesting text in it.
    """
    return story_block + '\n'.join(
        f'[pm.states.{k}]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
        for k in ('milestone', 'feature', 'bug'))


# --- the seed: one table, and the file a fresh consumer is handed -------------
def test_the_seed_is_the_installables_LIVE_section_and_a_tree_seeded_with_it_LOADS():
    """P1, end to end, and the only place `render_seed()` needs proving.

    `installables/project-devkit.toml` had ZERO uncommented lines, and every
    section it seeds is inert on arrival because a gate ships stock defaults and
    a commented default IS the default. `[pm.states.*]` cannot be — there is no
    runtime fallback behind it, so a commented one leaves a freshly-initialised
    tree refused on its first `pm` call.

    Three claims, one fixture, because they are one fact:

      * BYTE-IDENTICAL, not merely equivalent. A hand-copied table is a second
        spelling of `DEFAULT_FLOWS`, and the copy nobody runs goes stale;
      * the LIVE lines are the flow's and no other section's — a default that
        stops being commented is a gate acquiring an opinion the project cannot
        see it did not choose (hard rule 5);
      * and the config `init` writes satisfies `flow_of` on the tree's FIRST
        `pm` call, `obe` included: the seed is today's LIFECYCLE plus the one
        word for abandoned work, whose absence is the `also_done` defect (a
        story at `obe` holding its feature open forever) shipped to every new
        consumer as a repair they have to discover.
    """
    body = SEED_CONFIG.read_text(encoding='utf-8')
    assert model.render_seed() in body, (
        'the installable no longer carries render_seed() verbatim — the table '
        'was hand-edited in one of its two locations')
    live = [ln for ln in body.splitlines()
            if ln.strip() and not ln.lstrip().startswith('#')]
    assert live == [ln for ln in model.render_seed().splitlines() if ln.strip()]

    cfg = load(body)
    assert sorted(cfg.flows) == sorted(model.FLOW_KINDS)
    for kind in ('milestone', 'feature', 'story'):
        flow = model.flow_of(cfg, kind)
        assert flow.order == model.LIFECYCLE + ('obe',), kind
        assert flow.category('obe') == 'done', kind
    # A bug's vocabulary is declared exactly like the other three rather than
    # being a special case in the engine — which is the point of doing this per
    # KIND rather than once.
    bug = model.flow_of(cfg, 'bug')
    assert bug.order == ('open', 'fixed', 'closed')
    assert bug.category('closed') == 'done'


def test_this_repo_declares_its_own_flow_and_its_abandoned_word_is_done():
    """Self-hosting: the tree that ships the reader declares the section, and
    the `also_done` defect stays fixed HERE — a story at `obe` is FINISHED, and
    under a bare-word predicate it held its feature open forever."""
    cfg = model.load()
    for kind in model.FLOW_KINDS:
        assert model.flow_of(cfg, kind).order, kind
    assert model.flow_of(cfg, 'story').category('obe') == 'done'


# --- absent is ABSENT, never the seed -----------------------------------------
def test_a_tree_declaring_nothing_gets_no_flow_and_is_refused_by_name():
    """The no-fallback seam itself. A reader that fell back to `DEFAULT_FLOWS`
    would make the shipped words the project's flow without the project ever
    choosing them — and the refusal names the VERB that writes the declaration
    rather than handing a reader forty lines of TOML to copy, because a refusal
    that gets copied is a refusal that gets copied wrong."""
    cfg = load('')
    assert cfg.flows == {}
    with pytest.raises(ConfigError) as err:
        model.flow_of(cfg, 'story')
    message = str(err.value)
    assert '[pm.states.story]' in message
    assert 'there is no default' in message
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
    """The northstar, as a test. Not one of these words is in `LIFECYCLE`.

    The order inside a category is the project's too and is preserved exactly —
    `z-last` before `a-first` — because sorting it would be the engine deciding
    a sequence the project wrote down.
    """
    flow = load(with_story(
        '[pm.states.story]\n'
        'todo = ["icebox", "groomed"]\n'
        'in_progress = ["z-last", "a-first", "staged"]\n'
        'done = ["shipped", "abandoned"]\n')).flows['story']
    assert flow.category('z-last') == 'in_progress'
    assert flow.category('abandoned') == 'done'
    assert flow.order == ('icebox', 'groomed', 'z-last', 'a-first',
                          'staged', 'shipped', 'abandoned')


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
        # An empty set is satisfied, and still says all of HOW MANY: a census
        # of zero that renders as a bare "all done" is rule 4 in a verb.
        empty = model.holds(cfg, 'story', [], 'done')
        assert empty
        assert empty.counted == 0

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
        answer would be a gate missing real drift and printing PASS — and the
        engine inventing a category for it would be it deciding what the word
        must mean (rule 9)."""
        cfg = load(FULL)
        assert cfg.flows['story'].category('wombat') is None
        held = model.holds(cfg, 'story', [('s1', 'wombat')], 'done')
        assert not held
        assert held.names == ('s1 is wombat',)

    def test_it_refuses_a_bad_category_and_a_tree_that_declared_no_flow(self):
        with pytest.raises(ConfigError):
            model.holds(load(FULL), 'story', [], 'wombat')
        with pytest.raises(ConfigError):
            model.holds(load(''), 'story', [('s1', 'done')], 'done')


class TestMove:
    """`move(grain, to_state)` — is this transition declared?"""

    def test_every_declared_state_is_permitted_and_nothing_else_is(self):
        """There is still no edge graph, and the reason has not changed: a
        `sed` of the `status:` line reaches any state the CLI would have
        refused, so a graph taxes whoever uses the sanctioned tool and stops
        nobody else. END STATE is what D3/D4/D5 check — so every declared state
        is permitted, and a word the project never declared is refused naming
        what it DOES have."""
        cfg = load(FULL)
        for state in model.flow_of(cfg, 'story').order:
            assert model.move_defect(cfg, 'story', state) == '', state
        defect = model.move_defect(cfg, 'story', 'wombat')
        assert 'not a story state' in defect
        assert 'planning, ready, building' in defect

    def test_a_renamed_vocabulary_is_moved_through_exactly_as_the_stock_one(self):
        cfg = load(with_story('[pm.states.story]\ntodo = ["icebox"]\n'
                              'in_progress = ["in-dev"]\ndone = ["shipped"]\n'))
        assert model.move_defect(cfg, 'story', 'in-dev') == ''
        assert model.move_defect(cfg, 'story', 'building') != ''


def test_a_declared_step_names_its_state_and_an_undeclared_one_is_None():
    """ASK BY CATEGORY, WRITE BY NAME — a category holds several states, so a
    step that wrote "the done category" would make the engine guess a member,
    and a step the project never declared is None rather than a guess."""
    declared = load(FULL + '\n[pm.transitions.story]\nstory-done = "done"\n')
    assert model.transition_target(declared, 'story', 'story-done') == 'done'
    assert model.transition_target(load(FULL), 'story', 'story-done') is None


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
    def test_a_renamed_vocabulary_is_what_gets_printed(self):
        """No engine word leaks into the flow block. If this ever prints
        `building` for a project that never wrote it, the verb is reporting the
        seed instead of the declaration — which is the one lie a discovery verb
        can tell. P6's ruling rides along in the same output: the step keys are
        the ENGINE's published vocabulary a project selects from, and saying so
        is what keeps the table from being the engine's opinion wearing the
        project's clothes."""
        with tree(with_story('[pm.states.story]\ntodo = ["icebox"]\n'
                             'in_progress = ["in-dev"]\ndone = ["shipped"]\n')):
            code, out = vocab()
        assert code == 0, out
        flow = out.split('[pm.states.milestone]')[1].split('published steps')[0]
        assert 'in-dev' in flow and 'shipped' in flow
        assert 'building' not in flow, (
            'the verb printed the seed instead of what the project declared')
        assert 'ENGINE' in out and 'cannot invent one' in out

    def test_the_json_payload_carries_the_flow_the_transitions_and_the_seed(self):
        with tree(WITH_TRANSITIONS):
            code, out = vocab('--json')
        assert code == 0, out
        payload = json.loads(out)
        assert payload['categories'] == list(model.CATEGORIES)
        assert payload['flow_kinds'] == list(model.FLOW_KINDS)
        assert payload['flow_declared'] is True
        flow = payload['grains']['story']['flow']
        assert flow['categories']['in_progress'] == [
            'building', 'reviewing', 'accepted', 'packaging']
        assert flow['order'] == list(model.LIFECYCLE) + ['obe']
        assert flow['transitions'] == {'claimed': 'building',
                                       'story-done': 'done'}
        assert payload['seed'] == model.render_seed()

    def test_the_published_steps_come_from_the_conveyor_REGISTRY(self):
        """Read off the registry itself, never a literal list here.

        A literal would be a third spelling of `conveyor/steps.py` — the one in
        the CLI, the one in this test, and the real one — and the first release
        that adds a step would leave two of the three wrong while this passed.
        So the census is derived, and the FLOOR is that it is not empty: an
        emptied registry would satisfy a subset assertion in silence (rule 4).
        """
        from agentic_sdlc.repo.conveyor import steps
        with tree(FULL):
            code, out = vocab('--json')
        assert code == 0, out
        published = json.loads(out)['published_steps']
        assert published, 'the step registry is empty — nothing was censused'
        assert set(published) == set(steps.REGISTRIES)
        for operation, names in published.items():
            assert names == list(steps.registry_for(operation)), operation


def test_vocabulary_ANSWERS_the_tree_that_every_other_verb_refuses():
    """The tree `flow_of` refuses is the tree this verb has to answer.

    `vocabulary` is what you run to find out what to declare; a discovery verb
    that refuses until you have already discovered the answer is a closed loop.
    So: exit 0, the absence named, and the seed it prints has to survive the
    reader it will be pasted into — otherwise the verb's whole answer is a
    config error. The JSON half says the flow is ABSENT rather than omitting
    the key, because a consumer diffing two pins has to tell "this tree
    declares nothing" from "this release dropped the field".
    """
    with tree(''):
        code, out = vocab()
        assert code == 0, out
        # WHITESPACE-NORMALISED: the paragraph is prose and its line breaks are
        # not contract, unlike the `  DRIFT  ` / `[check:x] PASS` shapes
        # consumers grep (hard rule 6).
        prose = ' '.join(out.split())
        assert '[pm.states.*] is not in devkit.toml' in prose
        assert 'no default' in prose
        assert 'agentic-sdlc pm init' in prose
        # Indented by two in the transcript, so a reader cannot mistake it for
        # the tree's own config — and byte-identical once that indent is gone.
        pasted = '\n'.join(
            ln[2:] for ln in out.splitlines()
            if ln.startswith('  [pm.states.') or ln.startswith('  todo')
            or ln.startswith('  in_progress') or ln.startswith('  done'))
        _, payload = vocab('--json')
    assert sorted(load(pasted).flows) == sorted(model.FLOW_KINDS)
    absent = json.loads(payload)
    assert absent['flow_declared'] is False
    assert absent['grains']['story']['flow'] is None
    assert absent['seed'] == model.render_seed()
