"""test_verify_rules.py — the `[verify]` grammar, and everything it refuses.

`run` is a shell command read from config and executed later, so this file is
the refusal matrix for that grammar — enumerated ONCE, here, where the grammar
lives (SDLC.md §5, amended 2026-09-05). Three things it is built to catch, each
of which has shipped here before or is one edit away:

  * a rule quietly DROPPED from the list — the read-side cardinal sin wearing a
    new hat, because the caller then verifies less than it thinks and reports
    success. Every refusal here asserts the rule's own INDEX is in the message;
  * a BARE STRING read as a collection (`tuple(cfg.get(...))`, seven gates,
    v0.9.0), and every other shape that would read as "nothing to do";
  * exit 1 for a config typo, which CI reads as "drift found". `assertRefuses`
    asserts 2 on every case in this file, so the contract is proven once per
    refusal rather than once more in a class of its own.

Where a ban is a CONSTANT — `COMMAND_FORBIDDEN`, `GLOB_FORBIDDEN` — the test
enumerates the constant rather than a hand-written list of spellings. A
character silently dropped from the set is the defect (it reaches a shell); a
twelfth spelling of a character already in it is not.
"""
from __future__ import annotations

import ast
import unittest

from support import REPO_ROOT

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo.verify import rules

VERIFY_SRC = REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'verify'

MILESTONE = 'make milestone'
FORWARD = {'paths': 'src/agentic_sdlc/repo/pm/**',
           'run': 'python3 -m pytest tests/test_pm_*.py'}
CAPTURED = {'paths': 'tests/test_<name>.py',
            'run': 'python3 -m pytest tests/test_<name>.py'}
REVERSE = {'declares': '## covers:', 'scan': 'tests/integration/**',
           'run': 'make scenario NAME=<stem>'}
GOOD = {'milestone': MILESTONE, 'feature': 'make precommit',
        'narrow': [dict(FORWARD), dict(CAPTURED), dict(REVERSE)]}


def one(**rule) -> dict:
    """A section whose only interesting part is the single rule under test."""
    return {'milestone': MILESTONE, 'narrow': [rule]}


def forward(**overrides) -> dict:
    return one(**{**FORWARD, **overrides})


def reverse(**overrides) -> dict:
    return one(**{**REVERSE, **overrides})


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


class ValidRuleSet(Refuses):
    """The intended path, and the two rulings the compiled pattern carries."""

    def test_a_mixed_rule_set_parses_in_order_with_its_captures_and_rungs(self):
        parsed = rules.read(GOOD)
        self.assertEqual(0, exit_code(GOOD))
        self.assertEqual((1, 2, 3), tuple(r.index for r in parsed.narrow))
        self.assertEqual(('forward', 'forward', 'reverse'),
                         tuple(r.kind for r in parsed.narrow))
        self.assertEqual(((), ('name',), ('stem',)),
                         tuple(r.captures for r in parsed.narrow),
                         'the reverse direction binds <stem>, derived not '
                         'declared')
        self.assertEqual('.*', rules.read(reverse(declares='.*')).narrow[0]
                         .declares,
                         'declares is stored verbatim — nothing compiles it')
        # Both rungs, and the make target each names: the join to the ledger's
        # `gate` rows and the name `--check` holds against the Makefile.
        self.assertEqual(('make precommit', MILESTONE),
                         (parsed.feature, parsed.milestone))
        self.assertEqual(('precommit', 'milestone'),
                         (rules.rung_target(parsed.feature),
                          rules.rung_target(parsed.milestone)))
        # `feature` ABSENT is legal and is not the same as configured-to-run-
        # nothing: the verb has to be able to NAME the rung as unconfigured
        # rather than skip it, and '' could not be told apart from a rung that
        # runs nothing. An absent `narrow` is legal too — see
        # test_the_shapes_that_would_read_as_nothing_to_do for `narrow = []`.
        two_rungs = rules.read({'milestone': MILESTONE})
        self.assertEqual((), two_rungs.narrow)
        self.assertIsNone(two_rungs.rung(rules.FEATURE))
        self.assertEqual(MILESTONE, two_rungs.rung(rules.MILESTONE))

    def test_RULING_1_a_capture_stops_at_a_separator_and_only_star_star_spans(self):
        rule = rules.read(one(**CAPTURED)).narrow[0]
        self.assertEqual('c', rule.pattern.match('tests/test_c.py').group('name'))
        # Every path here reaches the capture — the literal prefix and suffix
        # both match — so what refuses them is the capture's own bound, which
        # is the whole of RULING 1. A `.`-for-`[^/]` here binds `a/b` and
        # interpolates it into a command line.
        for spanning in ('tests/test_a/b.py', 'tests/test_a/b/c.py',
                         'tests/test_/x.py'):
            with self.subTest(path=spanning):
                self.assertIsNone(rule.pattern.match(spanning))
        wide = rules.read(one(**FORWARD)).narrow[0]
        self.assertTrue(wide.pattern.match('src/agentic_sdlc/repo/pm/a/b.py'),
                        '** is the one construct that crosses a separator')
        self.assertIsNone(wide.pattern.match('src/agentic_sdlc/repo/checks/a.py'))


class TheSilentEmptyCensus(Refuses):
    """v0.9.0's defect shape, and every other spelling of "nothing to do"."""

    def test_narrow_as_a_bare_string_is_refused_never_iterated(self):
        message = self.assertRefuses({'milestone': MILESTONE, 'narrow': 'paths = x'},
                                     'narrow', 'paths = x')
        self.assertNotIn("'p', 'a', 't'", message,
                         'a bare string walked character by character is the '
                         'v0.9.0 defect: seven gates, empty census, PASS')

    def test_the_shapes_that_would_read_as_nothing_to_do_are_refused(self):
        cases = {
            # `narrow = []` is refused where an ABSENT `narrow` is legal —
            # `config.str_tuple`'s rule.
            'an empty rule list': ({'milestone': MILESTONE, 'narrow': []},
                                   ('narrow', 'remove')),
            # No close is no verification, and falling back to "run nothing" is
            # the silent zero-command pass this whole feature exists to prevent.
            'no milestone rung': ({'narrow': [dict(FORWARD)]},
                                  ('milestone', 'required')),
            'an empty milestone rung': ({'milestone': '',
                                         'narrow': [dict(FORWARD)]},
                                        ('milestone',)),
            # A value of the wrong TYPE goes through `core/config.py`, which is
            # where that grammar lives; these two prove this reader routes both
            # a rule's values and a rung's through it rather than coercing.
            'a rule value that is a list': (forward(paths=['src/**']),
                                            ('#1', 'paths')),
            'a rung value that is a number': ({'milestone': 7,
                                               'narrow': [dict(FORWARD)]},
                                              ('milestone',)),
        }
        for label, (section, fragments) in cases.items():
            with self.subTest(case=label):
                self.assertRefuses(section, *fragments)


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
                self.assertRefuses({'milestone': hostile,
                                    'narrow': [dict(FORWARD)]},
                                   'milestone', 'make <target>')
        # `feature` REUSES the grammar rather than carrying its own — one case
        # proving the reuse, per SDLC.md §5's amendment.
        self.assertRefuses({'milestone': MILESTONE, 'feature': 'make check test',
                            'narrow': [dict(FORWARD)]},
                           'feature', 'make <target>')

    def test_the_retired_wide_key_is_refused_by_name(self):
        # An author still spelling `wide` has declared no close at all. Falling
        # through the generic unknown-key path would say "unknown key 'wide'"
        # and leave them to find the new name themselves.
        self.assertRefuses({'wide': 'make check test',
                            'narrow': [dict(FORWARD)]},
                           'wide', 'milestone', 'D3')


class RunGrammar(Refuses):
    """`run` reaches a shell, so it is the narrowest grammar of the three."""

    def test_every_character_that_makes_one_command_two_is_refused(self):
        self.assertEqual(set(';|&$`()<>#\\'), set(rules.COMMAND_FORBIDDEN),
                         'this set is what stands between a `run` and a second '
                         'command nobody reviewed — a character dropped from '
                         'it reaches the shell, and no other case here would '
                         'notice')
        for char in sorted(rules.COMMAND_FORBIDDEN):
            with self.subTest(char=char):
                self.assertRefuses(forward(run=f'make x{char}y'), '#1', 'run')
        for label, value in (('newline', 'make x\nmake y'),
                             ('NUL', 'make x\x00rm -rf /')):
            with self.subTest(char=label):
                self.assertRefuses(forward(run=value), '#1', 'run')

    def test_a_capture_the_rule_does_not_declare_never_reaches_the_shell(self):
        # The single most dangerous typo here: `<undeclared>` would otherwise
        # arrive at a shell literally.
        self.assertRefuses(forward(run='make x <undeclared>'), '#1', 'undeclared')
        # RULING 3: <stem> is the reverse direction's DERIVED capture, so a
        # forward rule may neither interpolate nor declare it.
        self.assertRefuses(forward(run='<stem> foo'), '#1', 'stem')
        self.assertRefuses(forward(paths='tests/<stem>.py', run='make x <stem>'),
                           '#1', 'stem')
        self.assertRefuses(reverse(run='make scenario NAME=<other>'),
                           '#1', 'other')
        self.assertEqual(0, exit_code(reverse()),
                         '<stem> is legal in the direction that derives it')


class ValueBounds(Refuses):
    """Empty, absent and over-long, for all three value kinds at once."""

    def test_a_value_that_is_empty_absent_or_past_its_cap_is_refused(self):
        cases = {
            'run empty': (forward(run=''), ('#1', 'run')),
            'run whitespace only': (forward(run='   '), ('#1', 'run')),
            'run absent (forward)': (one(paths='src/**'), ('#1', 'run')),
            'run absent (reverse)': (one(declares='## covers:',
                                         scan='tests/**'), ('#1', 'run')),
            'run over the cap': (forward(run='make ' + 'x' * rules.MAX_RUN),
                                 ('#1', str(rules.MAX_RUN))),
            'glob empty': (forward(paths='', run='make x'), ('#1',)),
            'glob over the cap': (
                forward(paths='src/' + 'a' * rules.MAX_GLOB + '/**',
                        run='make x'), ('#1', str(rules.MAX_GLOB))),
            # An empty `declares` would claim the whole scan: every line starts
            # with "". That is a silent over-selection, not an empty set.
            'declares empty': (reverse(declares=''), ('#1', 'declares')),
            'declares over the cap': (
                reverse(declares='#' * (rules.MAX_DECLARES + 1)),
                ('#1', str(rules.MAX_DECLARES))),
        }
        for label, (section, fragments) in cases.items():
            with self.subTest(case=label):
                self.assertRefuses(section, *fragments)


class GlobGrammar(Refuses):
    """`paths` / `scan` — matched against tracked files, so: inside the tree."""

    def test_a_glob_that_leaves_the_checkout_or_means_the_whole_tree(self):
        cases = {
            # Hard rule 8: nothing here reads outside the checkout.
            'traversal': '../../etc/**',
            'traversal mid-path': 'src/../../etc/**',
            'absolute': '/etc/**',
            'empty segment': 'a//b',
            'dot segment': 'a/./b',
            'trailing slash': 'src/**/',
            # "narrow" that matches everything is "wide" with the fact hidden.
            'the whole tree': '**',
            'the whole tree, spelled long': '*/**',
            'a newline': 'src/**\nsrc/x',
            'a NUL': 'src/\x00/**',
        }
        for label, value in cases.items():
            with self.subTest(case=label):
                self.assertRefuses(forward(paths=value, run='make x'), '#1')
        self.assertEqual(set(';|&$`()<>#\\~:\'"'), set(rules.GLOB_FORBIDDEN),
                         'the ban list is the census: `~` and `:` are what keep '
                         'a glob from naming a home directory or a scheme, and '
                         '`\\` is what keeps a Windows-shaped path from '
                         'silently matching nothing')
        for char in sorted(rules.GLOB_FORBIDDEN):
            with self.subTest(char=char):
                self.assertRefuses(forward(paths=f'src/a{char}b/**',
                                           run='make x'), '#1')
        # `scan` REUSES the glob grammar — one case proving the reuse.
        self.assertRefuses(reverse(scan='../../etc/**'), '#1')

    def test_a_capture_that_is_malformed_duplicated_or_reserved_is_refused(self):
        cases = {
            # An unterminated `<` is a redirect, not a literal.
            'unterminated': 'tests/<a.py',
            'adjacent': 'tests/<a><b>.py',
            'not a name': 'tests/<1a>.py',
            # Which occurrence wins is not a thing this reader may pick.
            'duplicated': 'tests/<name>/test_<name>.py',
        }
        for label, value in cases.items():
            with self.subTest(case=label):
                self.assertRefuses(forward(paths=value, run='make x <name>'),
                                   '#1')
        # RULING 3: the reverse direction binds <stem> and nothing else.
        self.assertRefuses(reverse(scan='tests/<kind>/**'), '#1', 'stem')


class TheDirectionRulings(Refuses):
    """RULING 2, and the keys that decide which direction a rule is."""

    def test_a_rule_is_forward_or_reverse_and_carries_that_direction_whole(self):
        cases = {
            'both directions': (one(paths='src/**', declares='## covers:',
                                    scan='tests/**', run='make x'),
                                ('#1', 'paths', 'declares')),
            'neither direction': (one(run='make x'),
                                  ('#1', 'paths', 'declares')),
            'declares without scan': (one(declares='## covers:', run='make x'),
                                      ('#1', 'scan')),
            'scan without declares': (one(scan='tests/**', run='make x'),
                                      ('#1', 'declares')),
        }
        for label, (section, fragments) in cases.items():
            with self.subTest(case=label):
                self.assertRefuses(section, *fragments)

    def test_an_unknown_key_or_a_thing_that_is_not_a_table_is_named(self):
        cases = {
            # A typo'd `path` would otherwise make the rule match nothing,
            # forever, in silence.
            'unknown key in a rule': (one(path='src/**', run='make x'),
                                      ('#1', 'path')),
            'unknown key in the section': ({'milestone': MILESTONE,
                                            'mileston': MILESTONE,
                                            'narrow': [dict(FORWARD)]},
                                           ('mileston',)),
            'a rule that is a string': ({'milestone': MILESTONE,
                                         'narrow': ['paths = x']}, ('#1',)),
            'a rule that is a list': ({'milestone': MILESTONE,
                                      'narrow': [['paths', 'x']]}, ('#1',)),
            'a section that is a string': ('milestone = x', ('verify',)),
            'a section that is a number': (7, ('verify',)),
        }
        for label, (section, fragments) in cases.items():
            with self.subTest(case=label):
                self.assertRefuses(section, *fragments)


class EveryProblemIsCollectedWithItsIndex(Refuses):
    """With only the first problem named, an author fixes one and re-runs blind."""

    def test_a_bad_rung_and_the_second_and_fourth_rules_are_all_named(self):
        section = {'milestone': 'make a; make b', 'narrow': [
            dict(FORWARD),
            {'paths': '../../etc/**', 'run': 'make x'},
            dict(CAPTURED),
            {'paths': 'src/**', 'run': 'make x; rm -rf /'},
        ]}
        message = self.assertRefuses(section, 'milestone', '#2', '#4')
        self.assertNotIn('#1', message, 'and the good rules are not named')
        self.assertNotIn('#3', message)


class TheFamilyReadsNoFileAndSpawnsNothing(unittest.TestCase):
    """Adversarial against three docstrings: "never spawns", "reads no file".

    One check for the three pure modules rather than one per file: the claim is
    the same claim, and the defect it guards is the one this milestone measured
    — `pm-shape-scan` spending 34.8 s on four spawns per file across 683 files.
    A spawn added here does not fail anything; it just makes the path a
    consumer runs dozens of times a day slower, which nothing else notices.
    """

    SPAWN = frozenset({
        'run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen',
        'getoutput', 'getstatusoutput', 'fork', 'execv', 'execvp', 'spawnv'})
    ENUMERATE = frozenset({'glob', 'rglob', 'iterdir', 'walk', 'scandir',
                           'listdir'})
    # `core/config.py` is the ONE config reader; these three take their section
    # as an argument so the whole grammar can be exercised without a file.
    READ = frozenset({'open', 'read_text', 'read_bytes', 'write_text',
                      'load_config', 'config_section'})

    # module -> (imports it may have, call names it may not make). `declares.py`
    # is the one that legitimately reads a file — it stats and reads each
    # scanned file exactly once — so only spawning and ENUMERATING are banned
    # there; the enumeration ban is what keeps `tracked` an argument (rule 8).
    MODULES = {
        'rules.py': (frozenset({'re', 'dataclasses', 'agentic_sdlc.core.config',
                                'agentic_sdlc.repo'}),
                     SPAWN | ENUMERATE | READ),
        'select.py': (frozenset({'re', 'dataclasses', 'typing',
                                 'agentic_sdlc.repo.verify.rules'}),
                      SPAWN | ENUMERATE | READ | frozenset({'exists', 'stat',
                                                            'resolve'})),
        'declares.py': (frozenset({'dataclasses', 'pathlib', 'typing',
                                   'agentic_sdlc.core',
                                   'agentic_sdlc.repo.verify.rules',
                                   'agentic_sdlc.repo.verify.select'}),
                        SPAWN | ENUMERATE),
    }

    def test_none_of_the_pure_modules_imports_or_calls_a_spawn_or_a_walk(self):
        for name, (allowed, banned) in self.MODULES.items():
            with self.subTest(module=name):
                tree = ast.parse((VERIFY_SRC / name).read_text(encoding='utf-8'))
                imported = set()
                offenders = []
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
                            offenders.append(f'{name}:{node.lineno}: {called}()')
                self.assertEqual(set(), imported - allowed,
                                 'these imports are how "never spawns, reads '
                                 'no file" stops being true')
                self.assertEqual([], offenders, '\n  '.join(offenders))


if __name__ == '__main__':
    unittest.main()
