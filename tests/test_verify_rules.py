"""test_verify_rules.py — the `[verify]` grammar, and everything it refuses.

Three rungs, each `make <target>`, read from config and executed later — so
this file is the refusal matrix for that grammar, enumerated ONCE where the
grammar lives (SDLC.md §5). Three things it is built to catch, each of which
has shipped here before or is one edit away:

  * a rung quietly DROPPED — the read-side cardinal sin wearing a new hat,
    because the caller then verifies less than it thinks and reports success.
    An optional rung that is absent is None and named by the verb; a required
    one is refused;
  * a BARE STRING or a list read where a string belongs (`tuple(cfg.get(...))`,
    seven gates, v0.9.0), and every other shape that would read as "nothing
    to do";
  * exit 1 for a config typo, which CI reads as "drift found". `assertRefuses`
    asserts 2 on every case in this file, so the contract is proven once per
    refusal rather than once more in a class of its own.
"""
from __future__ import annotations

import ast
import unittest

from support import REPO_ROOT

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo.verify import rules

VERIFY_SRC = REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'verify'

MILESTONE = 'make milestone'
GOOD = {'story': 'make unit', 'feature': 'make test', 'milestone': MILESTONE}
# The retired story rung, in the shape a consumer's devkit.toml still carries.
NARROW_TABLE = [{'paths': 'src/**', 'run': 'make story'}]


def exit_code(section: dict) -> int:
    """What a caller gets — the shape `repo/gates_extra.py:main` already uses."""
    try:
        rules.read(section)
    except ConfigError:
        return rules.EXIT_CONFIG
    return 0


class Refuses(unittest.TestCase):
    """`assertRefuses`, plus the exit code, for every case below."""

    def assertRefuses(self, section: dict, *fragments: str) -> str:
        with self.assertRaises(ConfigError) as caught:
            rules.read(section)
        message = str(caught.exception)
        for fragment in fragments:
            self.assertIn(fragment, message)
        self.assertEqual(2, exit_code(section),
                         'a [verify] mistake is exit 2 — 1 is findings, and CI '
                         'reads 1 as "drift found"')
        return message


class TheLadder(Refuses):
    """Three rungs by name; the two optional ones are None when absent, so the
    verb names the absence instead of running the rung above."""

    def test_three_rungs_parse_by_name_and_each_names_its_target(self):
        ladder = rules.read(dict(GOOD))
        self.assertEqual(rules.Ladder(story='make unit', feature='make test',
                                      milestone=MILESTONE), ladder)
        for name in rules.RUNGS:
            self.assertEqual(GOOD[name], ladder.rung(name))
            self.assertEqual(GOOD[name].split()[1],
                             rules.rung_target(ladder.rung(name)))
        self.assertEqual(('story', 'feature', 'milestone'), rules.RUNGS,
                         'narrow to wide, the order --plan prints')

    def test_an_absent_story_or_feature_is_none_never_the_milestone(self):
        ladder = rules.read({'milestone': MILESTONE})
        self.assertIsNone(ladder.story)
        self.assertIsNone(ladder.feature)
        self.assertEqual(MILESTONE, ladder.milestone)

    def test_milestone_is_required(self):
        self.assertRefuses({'story': 'make unit'}, 'milestone', 'required')
        self.assertRefuses({}, 'milestone', 'required')


class TheRungGrammar(Refuses):
    """D3: a rung NAMES a make target, and spells nothing of its own."""

    # The shape D3 rejected, by name, and the branches of `_rung_grammar`:
    # a second goal, a chained command, another program, no target at all, a
    # flag, whitespace that makes the value not `' '.join(words)`, and the cap.
    NOT_A_TARGET = ('make check test', 'make a; rm -rf /', 'python3 -m pytest',
                    'make', 'make -j4', 'make VAR=1', '  make milestone',
                    'make ' + 'x' * (rules.gates_extra.MAX_LENGTH + 1))

    def test_a_rung_that_does_not_name_a_make_target_is_refused(self):
        for hostile in self.NOT_A_TARGET:
            with self.subTest(value=hostile[:24]):
                self.assertRefuses({'milestone': hostile}, 'milestone',
                                   'make <target>')
        # `story` and `feature` REUSE the grammar rather than carrying their
        # own — one case each proving the reuse.
        for rung in ('story', 'feature'):
            with self.subTest(rung=rung):
                self.assertRefuses({**GOOD, rung: 'make check test'}, rung,
                                   'make <target>')

    def test_a_rung_that_is_not_a_string_is_refused_never_iterated(self):
        # A list where a string belongs would `' '.join` into a plausible
        # command; a number would crash one frame later. Both are named.
        self.assertRefuses({**GOOD, 'story': ['make', 'unit']}, 'story')
        self.assertRefuses({**GOOD, 'milestone': 42}, 'milestone')


class TheRetiredKeys(Refuses):
    """An author still spelling a retired key is told the new shape, not left
    to find it from "unknown key"."""

    def test_wide_is_refused_by_name(self):
        self.assertRefuses({'wide': 'make check test'}, 'wide', 'milestone',
                           'D3')

    def test_narrow_is_refused_naming_the_story_rung_as_a_target(self):
        # `[[verify.narrow]]` tables and `[verify] narrow = …` both land on
        # the key `narrow`; either is the retired path-selection engine.
        for label, value in (('the table array', NARROW_TABLE),
                             ('a bare string', 'src/**'),
                             ('an empty list', [])):
            with self.subTest(shape=label):
                self.assertRefuses({**GOOD, 'narrow': value}, 'narrow',
                                   'story = "make <target>"',
                                   '[[verify.narrow]]')


class UnknownKeysAndShapes(Refuses):

    def test_an_unknown_key_or_a_thing_that_is_not_a_table_is_named(self):
        self.assertRefuses({**GOOD, 'storey': 'make unit'}, "'storey'",
                           'story, feature, milestone')
        for bad in ('make unit', ['make unit'], None):
            with self.subTest(section=bad):
                self.assertRefuses(bad, 'must be a table')


class EveryProblemIsCollected(Refuses):

    def test_every_problem_is_named_in_one_message(self):
        # One run, five problems: two retired keys, a rung that is not a
        # string, a rung that is not `make <target>`, and the missing close.
        message = self.assertRefuses(
            {'wide': 'make x', 'narrow': NARROW_TABLE, 'story': 42,
             'feature': 'make a b'},
            'wide', 'narrow', 'story', 'feature', 'milestone')
        self.assertIn('5 problems', message)


class TheModuleReadsNoFileAndSpawnsNothing(unittest.TestCase):
    """Adversarial against the docstring: "spawns nothing, reads no file".

    `core/config.py` is the ONE config reader; `rules.read` takes its section
    as an argument so the whole grammar is exercised without a file. A spawn
    added here does not fail anything; it just makes the path `close story`
    runs dozens of times a day slower, which nothing else notices.
    """

    SPAWN = frozenset({
        'run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen',
        'getoutput', 'getstatusoutput', 'fork', 'execv', 'execvp', 'spawnv'})
    ENUMERATE = frozenset({'glob', 'rglob', 'iterdir', 'walk', 'scandir',
                           'listdir'})
    READ = frozenset({'open', 'read_text', 'read_bytes', 'write_text',
                      'load_config', 'config_section'})
    ALLOWED_IMPORTS = frozenset({'dataclasses', 'agentic_sdlc.core.config',
                                 'agentic_sdlc.repo'})

    def test_rules_imports_and_calls_nothing_that_spawns_reads_or_walks(self):
        tree = ast.parse((VERIFY_SRC / 'rules.py').read_text(encoding='utf-8'))
        imported = set()
        offenders = []
        banned = self.SPAWN | self.ENUMERATE | self.READ
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) \
                    and node.module != '__future__':
                imported.add(node.module or '')
            elif isinstance(node, ast.Call):
                func = node.func
                called = (func.attr if isinstance(func, ast.Attribute)
                          else func.id if isinstance(func, ast.Name)
                          else '')
                if called in banned:
                    offenders.append(f'rules.py:{node.lineno}: {called}()')
        self.assertEqual(set(), imported - self.ALLOWED_IMPORTS,
                         'these imports are how "spawns nothing, reads no '
                         'file" stops being true')
        self.assertEqual([], offenders, '\n  '.join(offenders))


if __name__ == '__main__':
    unittest.main()
