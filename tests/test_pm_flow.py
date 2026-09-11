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

import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import run_cli, tree as grain_tree  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.pm import ledger, vocabulary  # noqa: E402

FULL = '\n'.join(
    f'[pm.states.{kind}]\n'
    + '\n'.join(f'{cat} = {list(states)!r}'.replace("'", '"')
                for cat, states in vocabulary.DEFAULT_FLOWS[kind].items())
    for kind in vocabulary.FLOW_KINDS)

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


def load(config: str) -> vocabulary.PmConfig:
    with tree(config):
        return vocabulary.load()


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
        `pm` call, `obe` included: the milestone's seed is today's LIFECYCLE
        plus the one word for abandoned work, whose absence is the `also_done`
        defect (a story at `obe` holding its feature open forever) shipped to
        every new consumer as a repair they have to discover — and a feature
        and a story hold the SUBSET their belts write (story 01 of
        the-code-knows-entry-and-exit: thirty stories sat at `reviewing`, a
        state no belt writes, under the all-seven seed).
    """
    body = SEED_CONFIG.read_text(encoding='utf-8')
    assert vocabulary.render_seed() in body, (
        'the installable no longer carries render_seed() verbatim — the table '
        'was hand-edited in one of its two locations')
    live = [ln for ln in body.splitlines()
            if ln.strip() and not ln.lstrip().startswith('#')]
    assert live == [ln for ln in vocabulary.render_seed().splitlines() if ln.strip()]

    cfg = load(body)
    assert sorted(cfg.flows) == sorted(vocabulary.FLOW_KINDS)
    expected = {
        'milestone': vocabulary.LIFECYCLE + ('obe',),
        'feature': ('planning', 'ready', 'building', 'reviewing', 'done',
                    'obe'),
        'story': ('planning', 'ready', 'building', 'done', 'obe'),
    }
    for kind, order in expected.items():
        flow = vocabulary.flow_of(cfg, kind)
        assert flow.order == order, kind
        assert flow.category('obe') == 'done', kind
    # A bug's vocabulary is declared exactly like the other three rather than
    # being a special case in the engine — which is the point of doing this per
    # KIND rather than once.
    bug = vocabulary.flow_of(cfg, 'bug')
    assert bug.order == ('open', 'fixed', 'closed')
    assert bug.category('closed') == 'done'


def test_this_repo_declares_its_own_flow_and_its_abandoned_word_is_done():
    """Self-hosting: the tree that ships the reader declares the section, and
    the `also_done` defect stays fixed HERE — a story at `obe` is FINISHED, and
    under a bare-word predicate it held its feature open forever."""
    cfg = vocabulary.load()
    for kind in vocabulary.FLOW_KINDS:
        assert vocabulary.flow_of(cfg, kind).order, kind
    assert vocabulary.flow_of(cfg, 'story').category('obe') == 'done'


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
        vocabulary.flow_of(cfg, 'story')
    message = str(err.value)
    assert '[pm.states.story]' in message
    assert 'there is no default' in message
    assert '`make pm ARGS=init`' in message
    assert '[pm.states.milestone]' not in message, (
        'the refusal pasted the seed instead of naming the verb that writes it')
    # The same refusal through the CLI — the path every consumer takes on the
    # day it bumps its pin, before `pm init`. `load()` parses fine (nothing to
    # parse), so `flow_of` raises MID-WALK, after dispatch: that was a Python
    # traceback at exit 1 from every reading verb, while `check pm` on the
    # identical tree exited 2 on one line. Exit 2 is the contract (rule 6).
    with grain_tree() as root:
        (root / 'devkit.toml').write_text('[pm]\n', encoding='utf-8')
        code, out = run_cli(root, 'status')
    assert code == 2, out
    assert 'Traceback' not in out, out
    assert '[pm] ERROR — ' in out and '[pm.states.' in out, out
    assert '`make pm ARGS=init`' in out, out


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
    # a leftover `[pm.transitions.<kind>]` — the step-to-state table one 0.2.0
    # build shipped and nothing read — is refused BY NAME, beside states...
    ('[pm.states.story]\ntodo = ["a"]\nin_progress = ["b"]\ndone = ["c"]\n'
     '[pm.transitions.story]\nstory-done = "c"\n',
     '[pm.transitions.story] was retired and is refused'),
    # ...and with no states at all: the key is what is refused, not its value
    ('[pm.transitions.story]\nstory-done = "done"\n',
     '[pm.transitions.story] was retired'),
    # an empty transitions table is still the key
    ('[pm.transitions]\n', '[pm.transitions] was retired'),
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
        held = vocabulary.holds(cfg, 'story', [('s1', 'done'), ('s2', 'building'),
                                          ('s3', 'planning')], 'done')
        assert not held
        assert held.names == ('s2 is building', 's3 is planning')
        assert held.counted == 3
        # An empty set is satisfied, and still says all of HOW MANY: a census
        # of zero that renders as a bare "all done" is rule 4 in a verb.
        empty = vocabulary.holds(cfg, 'story', [], 'done')
        assert empty
        assert empty.counted == 0

    def test_it_asks_the_CATEGORY_so_a_dropped_story_does_not_block(self):
        """The defect the whole design was written from. A story at `obe` is
        FINISHED and is never going to be `done`; under a bare-word predicate
        it held its feature open forever. Jira ships that exact mistake as a
        documented training problem."""
        dropped = FULL.replace('done = ["done"]', 'done = ["done", "obe"]')
        assert vocabulary.holds(load(dropped), 'story',
                           [('s1', 'done'), ('s2', 'obe')], 'done')

    def test_a_state_the_project_never_declared_BLOCKS_rather_than_passes(self):
        """Rule 4. An unrecognised word is exactly the case where a permissive
        answer would be a gate missing real drift and printing PASS — and the
        engine inventing a category for it would be it deciding what the word
        must mean (rule 9)."""
        cfg = load(FULL)
        assert cfg.flows['story'].category('wombat') is None
        held = vocabulary.holds(cfg, 'story', [('s1', 'wombat')], 'done')
        assert not held
        assert held.names == ('s1 is wombat',)

    def test_it_refuses_a_bad_category_and_a_tree_that_declared_no_flow(self):
        with pytest.raises(ConfigError):
            vocabulary.holds(load(FULL), 'story', [], 'wombat')
        with pytest.raises(ConfigError):
            vocabulary.holds(load(''), 'story', [('s1', 'done')], 'done')


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
        for state in vocabulary.flow_of(cfg, 'story').order:
            assert vocabulary.move_defect(cfg, 'story', state) == '', state
        defect = vocabulary.move_defect(cfg, 'story', 'wombat')
        assert 'not a story state' in defect
        assert 'planning, ready, building' in defect

    def test_a_renamed_vocabulary_is_moved_through_exactly_as_the_stock_one(self):
        cfg = load(with_story('[pm.states.story]\ntodo = ["icebox"]\n'
                              'in_progress = ["in-dev"]\ndone = ["shipped"]\n'))
        assert vocabulary.move_defect(cfg, 'story', 'in-dev') == ''
        assert vocabulary.move_defect(cfg, 'story', 'building') != ''


def test_a_leftover_transitions_table_names_the_fix_and_the_reader_is_gone():
    """The case this replaced asserted `transition_target` READ the table; it
    could not fail once the reader was deleted, so it proves the deletion
    instead. A tree carrying the retired table is refused before any verb
    runs, the message says what replaced it — a belt writes the FIRST state of
    its kind's `done` list — and says to remove the table rather than pasting
    a replacement."""
    assert not hasattr(vocabulary, 'transition_target')
    with pytest.raises(ConfigError) as err:
        load(FULL + '\n[pm.transitions.story]\nclaimed = "building"\n')
    message = str(err.value)
    assert '[pm.transitions.story] was retired' in message
    assert 'FIRST state' in message and 'done list' in message
    assert 'Remove the table' in message


# --- `pm vocabulary` — the pin-bump verb --------------------------------------
# It stopped being cosmetic in phase 6: it is the one place a consumer can read
# what a VERSION's declared surface is without scraping help text or a
# changelog. It echoes each kind's states with their category and NOTHING ELSE
# about flow — the `[pm.transitions.<kind>]` block and the published step names
# it printed for one build left with the table (story 01).
def vocab(*argv: str) -> tuple[int, str]:
    """`pm vocabulary` in the tree the caller is already standing in."""
    from agentic_sdlc.repo.pm import cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = cli.main(['vocabulary', *argv])
    return code, buf.getvalue()


class TestVocabulary:
    def test_a_renamed_vocabulary_is_what_gets_printed(self):
        """No engine word leaks into the flow block. If this ever prints
        `building` for a project that never wrote it, the verb is reporting the
        seed instead of the declaration — which is the one lie a discovery verb
        can tell. And nothing else about flow rides along: no transitions
        block, no published step names — those were the one build's table,
        and the table is refused now."""
        with tree(with_story('[pm.states.story]\ntodo = ["icebox"]\n'
                             'in_progress = ["in-dev"]\ndone = ["shipped"]\n')):
            code, out = vocab()
        assert code == 0, out
        flow = out.split('[pm.states.milestone]')[1].split('rules')[0]
        assert 'in-dev' in flow and 'shipped' in flow
        assert 'building' not in flow, (
            'the verb printed the seed instead of what the project declared')
        assert 'transitions' not in out and 'published steps' not in out

    def test_the_json_payload_carries_the_flow_and_the_seed_and_no_transitions(self):
        """Amended from the case that asserted a `transitions` key: with the
        table refused at load, a payload that still carried the key would be
        the verb describing a surface the reader no longer has."""
        with tree(FULL):
            code, out = vocab('--json')
        assert code == 0, out
        payload = json.loads(out)
        assert payload['categories'] == list(vocabulary.CATEGORIES)
        assert payload['flow_kinds'] == list(vocabulary.FLOW_KINDS)
        assert payload['flow_declared'] is True
        flow = payload['grains']['story']['flow']
        assert flow['categories']['in_progress'] == ['building']
        assert flow['order'] == ['planning', 'ready', 'building', 'done',
                                 'obe']
        assert sorted(flow) == ['categories', 'order']
        assert 'published_steps' not in payload
        assert 'transitions' not in payload['notes']
        assert payload['seed'] == vocabulary.render_seed()


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
        assert '`make pm ARGS=init`' in prose
        # Indented by two in the transcript, so a reader cannot mistake it for
        # the tree's own config — and byte-identical once that indent is gone.
        pasted = '\n'.join(
            ln[2:] for ln in out.splitlines()
            if ln.startswith('  [pm.states.') or ln.startswith('  todo')
            or ln.startswith('  in_progress') or ln.startswith('  done'))
        _, payload = vocab('--json')
    assert sorted(load(pasted).flows) == sorted(vocabulary.FLOW_KINDS)
    absent = json.loads(payload)
    assert absent['flow_declared'] is False
    assert absent['grains']['story']['flow'] is None
    assert absent['seed'] == vocabulary.render_seed()


# --- the inference census (ship criterion 2; decision D6) ---------------------
# `docs/design/state-categories.md` §6 counted the places the engine inferred
# from a state WORD; the feature record's table names every one. This is that
# table as a test: every symbol it said would be deleted is gone, every key it
# said would be retired is refused by name, and no state literal survives in
# the pm tracker, the gates or the verify family outside the SEED — the block
# `pm init` writes, which is the one place a word is allowed to be spelled.
#
# It fails BY NAME. A literal `'done'` added to `cli.py` next year is reported
# as `cli.py:<line>`, not as a count that went from 0 to 1.

SRC = REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo'
PKG = SRC.parent

# The words the seed spells. Any of these as a string CONSTANT in code outside
# the seed is the engine comparing against a word.
SEED_WORDS = frozenset(st for kind in vocabulary.DEFAULT_FLOWS.values()
                       for states in kind.values() for st in states)

# Deleted, per criterion 3 and the census rows that said "deleted".
DELETED = (
    ('pm.vocabulary', 'STALLED_IF_ALL_STORIES_DONE'),
    ('pm.vocabulary', 'work_started'),              # `at_or_past(BUILDING)`
    ('pm.vocabulary', 'split_blind_vocabularies'),  # `states_without_building`
    ('pm.vocabulary', 'is_terminal'),               # the `also_done` shim's reader
    ('pm.vocabulary', 'building_milestones'),       # D8/D9/D10's one line
    ('pm.vocabulary', 'DEFAULT_MILESTONE_STATES'),
    ('pm.vocabulary', 'DEFAULT_FEATURE_STATES'),
    ('pm.vocabulary', 'DEFAULT_STORY_STATES'),
    ('pm.vocabulary', 'DEFAULT_BUG_STATES'),
    ('pm.ledger', 'TERMINAL_STATE'),
    ('pm.ledger', 'terminal_state'),
    ('pm.ready_for', '_needs_state'),
    ('pm.cli', 'cmd_feature_reviewing'),       # `vocabulary.REVIEWING`'s verb
    # story 01 of the-code-knows-entry-and-exit: the step-to-state table, its
    # reader, the vocabulary section that printed it, and the ledger report's
    # `reopens` column, which counted `reviewing -> building` by name
    ('pm.vocabulary', 'transition_target'),
    ('pm.cli', 'PUBLISHED_STEPS_NOTE'),
    ('pm.cli', '_published_steps'),
    ('pm.report', 'REOPENS_COLUMN'),
    # ...and the `after_review` column beside it, the module's last seed-word
    # reader: it counted dispatches after the first move INTO `reviewing`
    ('pm.report', 'AFTER_REVIEW_COLUMN'),
    ('pm.report', 'REOPEN_TITLE'),
)

# Retired `[pm]` keys: a second declaration of the words, or an inference.
RETIRED = ('also_done', 'review_slug_fallback', 'milestone_states',
           'feature_states', 'story_states', 'bug_states')

# Where a state word MAY be spelled: the seed, the category whose name happens
# to be a word, and one HOMONYM — `verdict.OPEN` is a review FINDING's
# disposition (`pm ready-for tag` asks it), which shares its spelling with the
# bug seed's first state and has nothing to do with a grain's status.
SEED_ASSIGNMENTS = {
    'pm.vocabulary': frozenset({'LIFECYCLE', '_LIFECYCLE_CATEGORIES',
                           'DEFAULT_FLOWS', 'DONE_CATEGORY'}),
    'pm.verdict': frozenset({'OPEN'}),
    # The `rung.enter` payload's key. `ready` is a FIELD NAME there — "was the
    # entry condition met" — and shares its spelling with a state word this
    # project happens to declare. It is spelled ONCE, here: `_enter_row` zips
    # against `ENTER_KEYS` and `pm ledger show` reads `READY_FIELD`, so neither
    # keeps a second copy of the word.
    'pm.ledger': frozenset({'READY_FIELD'}),
}

# The seed's exported words (`vocabulary.LIFECYCLE` / `BUILDING` / `REVIEWING`)
# and who may still read them, by module and function. Each is a declared
# exception with its decision beside it; a reader added anywhere else fails.
SEED_WORD_READERS = {
    # the belts' step words (`CLAIMED` / `REVIEWING` / `DONE`); the R4 site
    # in the same module reads the flow instead
    ('conveyor.steps', None),
    # D7: the dispatch snapshot's frozen keys, deprecated, removal at the next
    # major — phase 8 lands the category keys beside them
    ('pm.cli', '_tree_snapshot'),
}


def _census_modules() -> list[tuple[str, Path]]:
    """Every module in the package, `(dotted, path)`, recursively.

    The first cut globbed three families one level deep and scanned 27 of 41
    modules (V4 of the feature review): a seed word added to `core/config.py`
    or `repo/init.py` would have been reported as nothing at all. `dotted` is
    the name `SEED_ASSIGNMENTS` keys on — relative to `repo/` for the modules
    that live there (`pm.vocabulary`), to the package otherwise
    (`core.config`).
    """
    out = []
    for path in sorted(PKG.rglob('*.py')):
        parts = path.relative_to(PKG).with_suffix('').parts
        if parts[0] == 'repo' and len(parts) > 1:
            parts = parts[1:]
        out.append(('.'.join(parts), path))
    return out


def _string_constants(tree: ast.AST):
    """(line, value) for every string constant that is not a docstring."""
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, 'body', [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings):
            yield node.lineno, node.value


def _enclosing_names(tree: ast.AST) -> dict[int, tuple[str | None, str | None]]:
    """line -> (top-level assignment target, enclosing function name)."""
    where: dict[int, tuple[str | None, str | None]] = {}
    for node in tree.body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        func = node.name if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None
        for line in range(node.lineno, node.end_lineno + 1):
            where[line] = (target, func)
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for line in range(sub.lineno, sub.end_lineno + 1):
                        where[line] = (None, sub.name)
    return where


def test_every_symbol_the_census_deleted_is_gone():
    import importlib
    for dotted, symbol in DELETED:
        module = importlib.import_module(f'agentic_sdlc.repo.{dotted}')
        assert not hasattr(module, symbol), f'{dotted}.{symbol} survives'
    for key in RETIRED:
        assert key in vocabulary.RETIRED_KEYS, f'[pm] {key} is not refused by name'


# --- the same census, three more vocabularies (0.6.0) --------------------------
# The state words were the FIRST vocabulary spelled as bare literals, and only
# one of four got a gate. The grain kinds, the frontmatter field names and the
# durable row's own fields are the other three, and they are ROWS on this
# harness rather than a second one: the same walk, the same
# `module -> assignment target` exception table, the same fail-by-name.
#
# `POSITION` is the one thing that differs, and it is the honest part. A second
# spelling is SILENT in a particular place — a `field_of` argument returns '',
# a row key reads `None` and sorts to the beginning of time — and the same word
# somewhere else is a git subcommand, a printed column header (rule 6) or an
# English noun. So each vocabulary declares WHERE it is graded, and what is
# outside that is stated rather than implied.

ANYWHERE = 'anywhere'          # every string constant that is not a docstring
FIELD_ARGUMENT = 'field argument'   # `field_of(path, X)` and its siblings
MAPPING_KEY = 'mapping key'    # a dict-literal key, `.get(X)`, `d[X]`

# The calls that take a FRONTMATTER field name. A wrong spelling here returns
# '' from a document that has the field, which reads as "absent".
FIELD_READERS = ('field_of', 'field_in', 'set_field', 'field')
# The calls that take a MAPPING key, beside a dict literal and a subscript.
KEY_READERS = ('get', 'setdefault', 'pop')

GRAIN_WORDS = frozenset(vocabulary.FLOW_KINDS)
FIELD_WORDS = frozenset({vocabulary.FIELD_ID, vocabulary.FIELD_KIND,
                         vocabulary.FIELD_STATUS, vocabulary.FIELD_NAME,
                         vocabulary.FIELD_OWNER})
ROW_WORDS = frozenset({ledger.TS_FIELD, ledger.KIND_FIELD, ledger.GRAIN_FIELD})


class Vocabulary(NamedTuple):
    """One closed set of words, its one home, and where it is graded."""

    words: frozenset
    home: tuple                 # (module, name) the words are spelled at
    position: str
    # module -> the top-level assignment targets that MAY spell one, each an
    # entry with a reason beside it. The `SEED_ASSIGNMENTS` shape, one vocab on.
    elsewhere: dict
    fstrings: bool = False      # grade a literal segment of an f-string too


VOCABULARIES = {
    'state': Vocabulary(SEED_WORDS, ('pm.vocabulary', 'DEFAULT_FLOWS'), ANYWHERE,
                        SEED_ASSIGNMENTS, fstrings=True),
    'grain kind': Vocabulary(
        GRAIN_WORDS, ('pm.vocabulary', 'GRAIN_<KIND>'), ANYWHERE, {
            'pm.vocabulary': frozenset({'GRAIN_MILESTONE', 'GRAIN_FEATURE',
                                   'GRAIN_STORY', 'GRAIN_BUG'}),
            # A BELT's name, not a grain kind's: a belt is named for what it
            # closes. `conveyor/driver.py` is that vocabulary's home, and
            # `pm/` may not import `conveyor/`, so `arrive` spells its own.
            'conveyor.driver': frozenset({'OP_STORY', 'OP_FEATURE'}),
            'pm.arrive': frozenset({'STORY_BELT', 'FEATURE_BELT'}),
            # A MAKE target, which is a name in the consumer's Makefile.
            'conveyor.steps': frozenset({'DEFAULT_RUNNER_TARGETS'}),
            # `verify` reads no PM tree and must not import `pm.vocabulary` to
            # spell the name of a make rung.
            'verify.rules': frozenset({'STORY', 'FEATURE', 'MILESTONE'}),
            # Printed COLUMN headers and payload keys — contract (rule 6), and
            # a different vocabulary that happens to share four words.
            'pm.cli': frozenset({'LIST_COLUMNS', 'ROADMAP_COLUMNS'}),
            'pm.report': frozenset({'MILESTONE_KEY', 'FEATURE_COLUMN',
                                    'STORY_COLUMN', 'BUG_COLUMN',
                                    'BEFORE_WRITE_TITLE'}),
        }),
    'frontmatter field': Vocabulary(
        FIELD_WORDS, ('pm.vocabulary', 'FIELD_<NAME>'), FIELD_ARGUMENT,
        {'pm.vocabulary': frozenset({'FIELD_ID', 'FIELD_KIND', 'FIELD_STATUS',
                                'FIELD_NAME', 'FIELD_OWNER'})}),
    'row field': Vocabulary(
        ROW_WORDS, ('pm.ledger', '<NAME>_FIELD'), MAPPING_KEY,
        {'pm.ledger': frozenset({'TS_FIELD', 'KIND_FIELD', 'GRAIN_FIELD'})}),
}


def _graded(tree: ast.AST, position: str, fstrings: bool):
    """(line, value) for every string constant this vocabulary is graded at."""
    docstrings, interpolated, wanted = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, 'body', [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
        if isinstance(node, ast.JoinedStr):
            interpolated |= {id(v) for v in node.values}
        if isinstance(node, ast.Call):
            func = node.func
            name = (func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else '')
            if position == FIELD_ARGUMENT and name in FIELD_READERS:
                wanted |= {id(a) for a in node.args}
            if position == MAPPING_KEY and name in KEY_READERS and node.args:
                wanted.add(id(node.args[0]))
        if position == MAPPING_KEY:
            if isinstance(node, ast.Dict):
                wanted |= {id(k) for k in node.keys if k is not None}
            elif isinstance(node, ast.Subscript):
                wanted.add(id(node.slice))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings:
            continue
        if not fstrings and id(node) in interpolated:
            continue
        if position != ANYWHERE and id(node) not in wanted:
            continue
        yield node.lineno, node.value


def _survivors(vocab: Vocabulary) -> list[str]:
    """Every place a word of this vocabulary is spelled that is not its home
    and not a named exception — `path:line 'word'`, never a count."""
    out = []
    for dotted, path in _census_modules():
        tree = ast.parse(path.read_text('utf-8'))
        where = _enclosing_names(tree)
        for line, value in _graded(tree, vocab.position, vocab.fstrings):
            if value not in vocab.words:
                continue
            target, _ = where.get(line, (None, None))
            if target in vocab.elsewhere.get(dotted, ()):
                continue
            out.append(f'{path.relative_to(REPO_ROOT)}:{line} {value!r}')
    return out


def _census_is_the_tree():
    """The census is the claim (rule 4): one module from each side of the
    `core/` / `repo/` edge must be in it, or the walk is scanning the wrong
    root and every assertion over it is over nothing."""
    names = {dotted for dotted, _ in _census_modules()}
    assert ({'pm.vocabulary', 'pm.inventory', 'core.config', 'conveyor.driver'}
            <= names), sorted(names)


def test_no_state_literal_survives_outside_the_seed():
    """The census, enumerated: every string constant equal to a seed word, in
    every census module, is in a SEED assignment — or it is named here. The
    STATE row of `VOCABULARIES`; the other three are the class below."""
    _census_is_the_tree()
    survivors = _survivors(VOCABULARIES['state'])
    assert survivors == [], '\n'.join(survivors)


# Planted modules, as (source, must the reader call it a survivor). The graded
# POSITIONS are the part that can go quietly wrong — a reader that stopped
# seeing dict keys reports an empty offender list, which is what a clean tree
# reports too.
_A_BARE_KIND = "def f(cfg):\n    return holds(cfg, 'feature', [])\n"
_A_NAMED_KIND = "def f(cfg):\n    return holds(cfg, vocabulary.GRAIN_FEATURE, [])\n"
_A_KIND_IN_A_MESSAGE = "def f():\n    return f'a {x} feature'\n"
_A_BARE_FIELD_ARGUMENT = ("def f(p):\n"
                          "    return frontmatter.field_of(p, 'status')\n")
_A_NAMED_FIELD_ARGUMENT = ("def f(p):\n"
                           "    return frontmatter.field_of("
                           "p, vocabulary.FIELD_STATUS)\n")
_A_FIELD_WORD_SOMEWHERE_ELSE = "def f():\n    return git_lines('status', '-s')\n"
_A_BARE_ROW_GET = "def f(row):\n    return row.get('ts')\n"
_A_BARE_ROW_KEY = "def f(gid):\n    return {'grain': gid}\n"
_A_BARE_ROW_SUBSCRIPT = "def f(row):\n    return row['kind']\n"
_A_NAMED_ROW_GET = "def f(row):\n    return row.get(ledger.TS_FIELD)\n"
_A_ROW_WORD_AS_A_NOUN = "def f(k):\n    return f'a {k} names its ' + 'grain'\n"


class NoVocabularyLiteralSurvivesOutsideItsHome(unittest.TestCase):
    """Grain kinds, frontmatter fields and row fields, on the state census's
    own harness.

    `lessons.FIELDS` spelled the durable stamp `at` while every reader keyed
    `ts`, so those rows sorted to the beginning of time and no test could see
    it: neither spelling is wrong to a string. A constant makes the second
    spelling a NameError at import.

    **What this does NOT grade**, stated rather than implied: a frontmatter
    field name outside a `field_of`/`field_in`/`set_field` argument, and a row
    field outside a mapping key. Both are positions where the same four words
    are a git subcommand, a printed column (rule 6) or an English noun, and a
    census that cannot tell them apart forces a module to lie about what it
    means. `tests/` is out of scope — its economics are `check budget`'s.
    """

    PROTECTS = (
        'grain kinds, frontmatter fields and row fields are spelled at their '
        'constant and nowhere else, so a second spelling is a NameError at '
        'import',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): '
        'lessons.FIELDS spelled the durable stamp `at` while every reader keyed '
        '`ts`, so those rows sorted to the beginning of time and no test could '
        'see it — neither spelling is wrong to a string',
    )

    CORPUS = (
        (_A_BARE_KIND, True),
        (_A_NAMED_KIND, False),
        # Prose in a rendered message, not the vocabulary.
        (_A_KIND_IN_A_MESSAGE, False),
        (_A_BARE_FIELD_ARGUMENT, True),
        (_A_NAMED_FIELD_ARGUMENT, False),
        # The same word as a git subcommand: outside the graded position.
        (_A_FIELD_WORD_SOMEWHERE_ELSE, False),
        # The three mapping-key shapes, each its own way for a reader to go
        # blind while still reporting a count.
        (_A_BARE_ROW_GET, True),
        (_A_BARE_ROW_KEY, True),
        (_A_BARE_ROW_SUBSCRIPT, True),
        (_A_NAMED_ROW_GET, False),
        (_A_ROW_WORD_AS_A_NOUN, False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        """Does any vocabulary but `state` report a survivor in this source?"""
        tree = ast.parse(planted)
        return any(value in vocab.words
                   for name, vocab in VOCABULARIES.items() if name != 'state'
                   for _, value in _graded(tree, vocab.position, vocab.fstrings))

    def test_every_vocabulary_is_spelled_at_its_home_and_nowhere_else(self):
        _census_is_the_tree()
        for name, vocab in VOCABULARIES.items():
            with self.subTest(vocabulary=name):
                self.assertNotEqual(frozenset(), vocab.words, name)
                survivors = _survivors(vocab)
                self.assertEqual(
                    [], survivors,
                    f'a {name} word spelled outside {vocab.home[0]}.'
                    f'{vocab.home[1]}. A second spelling is not wrong to a '
                    f'string — it is wrong at 3am, silently. Read it from its '
                    f'home, or name the assignment in VOCABULARIES with the '
                    f'reason it is a different word:\n  '
                    + '\n  '.join(survivors))


def test_the_belts_spell_no_state_word():
    """R4 was `_status_at_or_past` in `conveyor/steps.py`, a tuple index of a
    word the engine spelled; D12 deleted every automatic step and the site
    with it. What remains to hold is the whole package: a belt writes the
    first `done` state its kind's config lists, so no module under
    `conveyor/` may carry a seed word as a string constant.

    This is the NEGATIVE half of the R4 case it replaced. The positive half
    — that the site read `vocabulary.flow_of` and not `vocabulary.LIFECYCLE` /
    `BUILDING` / `REVIEWING` — is
    `test_the_seeds_exported_words_have_exactly_the_named_readers` below,
    package-wide rather than per site (V9 of the feature review)."""
    hits = []
    for path in sorted((SRC / 'conveyor').rglob('*.py')):
        tree = ast.parse(path.read_text('utf-8'))
        hits += [f'{path.name}:{v!r}' for _, v in _string_constants(tree)
                 if v in SEED_WORDS]
    assert hits == [], hits


def test_the_seeds_exported_words_have_exactly_the_named_readers():
    """`vocabulary.LIFECYCLE` / `BUILDING` / `REVIEWING` are the seed's words under
    0.2.0's names. Whoever reads them is asking about a word, and each such
    reader is a declared exception above — never a silent one."""
    readers = set()
    for family in ('pm', 'checks', 'verify', 'conveyor'):
        for path in sorted((SRC / family).glob('*.py')):
            dotted = f'{family}.{path.stem}'
            if dotted in ('pm.vocabulary', 'pm.inventory'):
                continue
            tree = ast.parse(path.read_text('utf-8'))
            where = _enclosing_names(tree)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == 'vocabulary'
                        and node.attr in ('LIFECYCLE', 'BUILDING', 'REVIEWING')):
                    _, func = where.get(node.lineno, (None, None))
                    readers.add((dotted, func))
    unexpected = {(m, f) for m, f in readers
                  if (m, f) not in SEED_WORD_READERS
                  and (m, None) not in SEED_WORD_READERS}
    assert unexpected == set(), sorted(unexpected)
    # ...and the named exceptions are real, so this list cannot go stale.
    assert ('pm.cli', '_tree_snapshot') in readers
    # The ledger report reads no seed word at all: `after_review`, its last
    # reader, left with the per-story table.
    assert not {m for m, _ in readers if m == 'pm.report'}
