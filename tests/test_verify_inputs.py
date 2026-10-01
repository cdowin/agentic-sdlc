"""test_verify_inputs.py — `[verify.inputs]`, the pure half.

The measured defect (a consumer, 2026-09-16): 140 of 141 unit-tier runs in two
days were "new" tree states, because every `pm` status flip moved the whole-tree
digest, so the story rung re-bought a 44 s tier nine times over one unchanged
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
    ladder = rules.read({'milestone': 'make milestone', 'spot': 'make unit',
                         'inputs': {'spot': ['src/', './tests']}})
    assert ladder.scope('spot') == ('src', 'tests')
    assert ladder.scope('milestone') == ()


def test_no_inputs_table_scopes_nothing():
    assert rules.read({'milestone': 'make milestone'}).inputs == {}


def test_history_independent_is_explicit_per_rung_and_false_by_default():
    default = rules.read({'milestone': 'make milestone'})
    enabled = rules.read({
        'milestone': 'make milestone',
        'history_independent': {'spot': True, 'milestone': False},
    })
    assert not default.omits_history('spot')
    assert enabled.omits_history('spot')
    assert not enabled.omits_history('milestone')


def test_environment_names_are_a_global_explicit_list():
    assert rules.read({'milestone': 'make milestone',
                       'environment': ['CI', 'FEATURE_SWITCH']}).environment \
        == ('CI', 'FEATURE_SWITCH')
    with pytest.raises(ConfigError, match='invalid environment name'):
        rules.read({'milestone': 'make milestone', 'environment': ['BAD=1']})


@pytest.mark.parametrize('value, fragment', [
    ('spot', 'must be a table'),
    ({'wombat': True}, "'wombat'"),
    ({'spot': 'true'}, 'spot must be true/false'),
])
def test_malformed_history_independent_table_is_refused(value, fragment):
    with pytest.raises(ConfigError) as err:
        rules.read({'milestone': 'make milestone',
                    'history_independent': value})
    assert fragment in str(err.value)


@pytest.mark.parametrize('key, stock, override, bad, refusal', [
    # The escape hatch for a rung target that READS statuses: stock `true`
    # (every rung leaves out what a belt writes), `false` keys on every byte,
    # and a value that is not a bool is refused by name, never read as truthy.
    ('reuse_ignores_status', True, False, 'false',
     'reuse_ignores_status must be true/false'),
    # What a milestone reuse under that exclusion asks first (0.18.0 review
    # F1/F2): stock `make check`, an override resolves, and a command that is
    # not `make <target>` is refused by name, never run through a shell.
    ('static', 'make check', 'make lint', 'echo ok; exit 3',
     '[verify] static is'),
])
def test_the_gate_keys_have_a_stock_value_an_override_and_a_refusal(
        key, stock, override, bad, refusal):
    assert getattr(rules.read({'milestone': 'make milestone'}), key) == stock
    assert getattr(rules.read({'milestone': 'make milestone', key: override}),
                   key) == override
    with pytest.raises(ConfigError) as err:
        rules.read({'milestone': 'make milestone', key: bad})
    assert refusal in str(err.value)


@pytest.mark.parametrize('inputs, names', [
    ({'wombat': ['src']}, 'wombat'),
    ('src', 'must be a table'),
    ({'spot': 'src'}, 'must be a list'),
    ({'spot': []}, 'is empty'),
    ({'spot': ['']}, 'at least one path'),
    ({'spot': ['../up']}, 'climbs out'),
    ({'spot': ['/abs']}, 'is absolute'),
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
    assert cache.State('a' * 64, 3, (), True).where() == (
        f'the whole tree except {cache.MOVES_OUT}')
    assert '`status:` lines' in cache.MOVES_OUT
    # Rule 11: the operator whose rung reads statuses finds the key here.
    assert '[verify] reuse_ignores_status = false' in cache.MOVES_OUT
