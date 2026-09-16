"""test_verify_inputs.py — `[verify.inputs]`, the pure half.

The measured defect (a consumer, 2026-09-16): 140 of 141 unit-tier runs in two
days were "new" tree states, because every `pm` status flip moved the whole-tree
digest, so `close story` re-bought a 44 s tier nine times over one unchanged
code tree. `[verify.inputs]` names the paths a rung's state covers. Parsing
and the prefix match are function calls and live here; the wiring — a state
over a real git listing, an out-of-scope edit reusing, an in-scope edit
re-running — spawns git and make, and lives in `tests/test_verify_spawns.py`
under `AScopedRungReadsOnlyWhatItsTargetReads`.
"""
from __future__ import annotations

import pytest

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo.verify import cache, rules


def test_inputs_are_read_per_rung_and_an_absent_rung_is_the_whole_tree():
    ladder = rules.read({'milestone': 'make milestone', 'story': 'make story',
                         'inputs': {'story': ['src/', './tests']}})
    assert ladder.scope('story') == ('src', 'tests')
    assert ladder.scope('milestone') == ()
    assert ladder.scope('feature') == ()


def test_no_inputs_table_scopes_nothing():
    assert rules.read({'milestone': 'make milestone'}).inputs == {}


@pytest.mark.parametrize('inputs, names', [
    ({'wombat': ['src']}, 'wombat'),
    ('src', 'must be a table'),
    ({'story': 'src'}, 'must be a list'),
    ({'story': []}, 'is empty'),
    ({'story': ['']}, 'at least one path'),
    ({'story': ['../up']}, 'climbs out'),
    ({'story': ['/abs']}, 'is absolute'),
])
def test_a_malformed_inputs_table_is_refused_by_name(inputs, names):
    with pytest.raises(ConfigError) as err:
        rules.read({'milestone': 'make milestone', 'inputs': inputs})
    assert names in str(err.value)


@pytest.mark.parametrize('rel, scope, hit', [
    ('src/a.py', ('src',), True),
    ('src', ('src',), True),
    ('srcs/a.py', ('src',), False),
    ('pm/roadmap/x.md', ('src', 'tests'), False),
    ('tests/unit/t.py', ('src', 'tests'), True),
])
def test_a_prefix_matches_by_segment_and_never_by_spelling(rel, scope, hit):
    assert cache.in_scope(rel, scope) is hit


def test_a_state_says_what_it_covers():
    assert cache.State('a' * 64, 3).where() == 'the whole tree'
    assert cache.State('a' * 64, 3, ('src', 'tests')).where() == 'src tests'
