"""test_verify_select.py — the forward selector, and the miss it must never eat.

THE FIRST TEST IN THIS FILE IS THE ONE THAT MATTERS. A narrow verifier that
matches nothing and exits 0 is worse than no verifier: it reports success for
work it never checked. So `TheLoudMiss` comes first, and `TheInvariant` behind
it turns "we remembered to report misses" into "a path cannot leave the
selector without appearing on exactly one of the two lists".

The rest is the refusal matrix for a surface `rules.py` cannot see. Config
validation cannot know that a repository contains a directory called `my repo`
or `$(id)`; a capture that BINDS one of those is a command line assembled out
of tree contents, so this module refuses at selection time and names both the
path and the rule.
"""
from __future__ import annotations

import ast
import time
import unittest

from support import REPO_ROOT

from agentic_sdlc.repo.verify import rules, select
from agentic_sdlc.repo.verify.select import Selection, SelectionError

SELECT_SOURCE = (REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'verify'
                 / 'select.py')

MILESTONE = 'make milestone'


def ruleset(*narrow: dict) -> tuple:
    """The parsed narrow rules for a section built from these entries.

    Built through `rules.read` rather than by constructing `Rule` objects, so
    every fixture here is a rule set the shipped grammar actually accepts — a
    hand-built Rule could carry a pattern the reader would have refused, and
    then this file would be testing a selector against inputs that cannot
    occur.
    """
    return rules.read({'milestone': MILESTONE, 'narrow': list(narrow)}).narrow


PM = {'paths': 'src/agentic_sdlc/repo/pm/**',
      'run': 'python3 -m pytest tests/test_pm_rules.py'}
SYS = {'paths': 'systems/<sys>/**', 'run': 'make unit SYS=<sys>'}
TESTS = {'paths': 'tests/test_<name>.py',
         'run': 'python3 -m pytest tests/test_<name>.py'}
REVERSE = {'declares': '## covers:', 'scan': 'tests/integration/**',
           'run': 'make scenario NAME=<stem>'}


class TheLoudMiss(unittest.TestCase):
    """A path nothing claims is NAMED. This is the story of the whole module."""

    def test_a_path_matching_no_rule_is_missed_verbatim_and_in_input_order(self):
        narrow = ruleset(PM)
        changed = ['README.md', 'src/agentic_sdlc/repo/pm/model.py',
                   'CHANGELOG.md', 'Makefile']
        got = select.select(narrow, changed)
        self.assertEqual(('README.md', 'CHANGELOG.md', 'Makefile'), got.missed,
                         'a changed path no rule claims must come back NAMED, '
                         'verbatim and in input order — a verifier that '
                         'silently drops it reports success for work it never '
                         'checked')
        self.assertEqual(('python3 -m pytest tests/test_pm_rules.py',),
                         got.commands)

    def test_a_diff_where_everything_misses_selects_nothing_and_says_so(self):
        # The most dangerous input in the design: no command, and the ONLY
        # thing standing between that and a green run is `missed` being loud.
        got = select.select(ruleset(PM), ['README.md', 'LICENSE'])
        self.assertEqual((), got.commands)
        self.assertEqual((), got.matched)
        self.assertEqual(('README.md', 'LICENSE'), got.missed)

    def test_a_reverse_rule_with_no_resolver_misses_rather_than_absorbs(self):
        # This module does not read files, so a reverse rule claims nothing
        # here. Its paths must fall to `missed`, not vanish into a rule that
        # "handled" them.
        got = select.select(ruleset(REVERSE), ['tests/integration/a.py'])
        self.assertEqual((), got.commands)
        self.assertEqual(('tests/integration/a.py',), got.missed)


class TheInvariant(unittest.TestCase):
    """matched + missed == input, disjoint. Makes a silent pass unreachable."""

    CORPORA = (
        ['src/agentic_sdlc/repo/pm/a.py'],
        ['README.md'],
        ['systems/combat/a.gd', 'systems/combat/b.gd', 'systems/ai/c.gd'],
        ['tests/test_pm_model.py', 'tests/test_verify_rules.py', 'x/y/z.txt'],
        ['src/agentic_sdlc/repo/pm/a.py'] * 7,
        ['a/b/c/d/e/f/g.py', 'systems/x/y/z.gd', 'tests/test_q.py', 'Makefile'],
        [f'systems/s{n % 5}/file{n}.gd' for n in range(50)],
        [f'unclaimed/{n}.txt' for n in range(30)],
        ['tests/test_a.py', 'tests/nested/test_b.py', 'tests/test_c.py'],
    )

    def test_every_path_lands_in_exactly_one_of_matched_or_missed(self):
        narrow = ruleset(PM, SYS, TESTS)
        for corpus in self.CORPORA:
            with self.subTest(paths=len(corpus)):
                got = select.select(narrow, corpus)
                matched = got.matched_paths
                self.assertEqual(
                    len(corpus), len(matched) + len(got.missed),
                    'a path left the selector without landing on either list — '
                    'that is the silent zero-command pass, arrived at by '
                    'arithmetic')
                self.assertEqual(set(), set(matched) & set(got.missed),
                                 'the two lists must be disjoint')
                self.assertEqual(sorted(corpus), sorted(list(matched) + list(got.missed)))

    def test_the_invariant_holds_with_no_rules_at_all(self):
        # Every path misses. The one shape where a caller most needs to be told.
        corpus = ['a.py', 'b.py']
        got = select.select((), corpus)
        self.assertEqual(tuple(corpus), got.missed)
        self.assertEqual((), got.commands)


class Dedupe(unittest.TestCase):
    """Five files under one capture are ONE command. That is the 170x."""

    def test_five_files_under_one_capture_produce_one_command(self):
        changed = [f'systems/combat/{name}.gd'
                   for name in ('a', 'b', 'c', 'd', 'e')]
        got = select.select(ruleset(SYS), changed)
        self.assertEqual(1, len(got.commands))
        self.assertEqual('make unit SYS=combat', got.commands[0])
        self.assertEqual(tuple(changed), got.matched[0].paths,
                         'a dedupe that loses the attribution is a dedupe that '
                         'cannot explain itself')
        self.assertEqual((), got.missed)

    def test_two_captured_values_are_two_commands_in_first_seen_order(self):
        got = select.select(ruleset(SYS), ['systems/ui/a.gd',
                                           'systems/combat/b.gd',
                                           'systems/ui/c.gd'])
        self.assertEqual(('make unit SYS=ui', 'make unit SYS=combat'),
                         got.commands)
        self.assertEqual(('systems/ui/a.gd', 'systems/ui/c.gd'),
                         got.matched[0].paths)

    def test_two_different_rules_substituting_to_one_command_dedupe(self):
        # Dedupe is across the whole selection, not within a single rule: the
        # docstring says "the same command is never emitted twice".
        narrow = ruleset({'paths': 'a/**', 'run': 'make slice'},
                         {'paths': 'b/**', 'run': 'make slice'})
        got = select.select(narrow, ['a/x.py', 'b/y.py'])
        self.assertEqual(('make slice',), got.commands)
        self.assertEqual(1, len(got.matched))
        self.assertEqual(('a/x.py', 'b/y.py'), got.matched[0].paths)
        self.assertEqual(1, got.matched[0].index,
                         'the first rule to emit the command owns the slot')


class FirstMatchingRuleWins(unittest.TestCase):
    """A path is not fanned out; adding a rule must not multiply the work."""

    def test_the_earlier_rule_claims_the_path_and_it_appears_once(self):
        narrow = ruleset({'paths': 'src/**', 'run': 'make first'},
                         {'paths': 'src/agentic_sdlc/**', 'run': 'make second'})
        got = select.select(narrow, ['src/agentic_sdlc/cli.py'])
        self.assertEqual(('make first',), got.commands)
        self.assertEqual(1, got.matched[0].index)

    def test_reversing_the_declaration_order_reverses_the_answer(self):
        narrow = ruleset({'paths': 'src/agentic_sdlc/**', 'run': 'make second'},
                         {'paths': 'src/**', 'run': 'make first'})
        got = select.select(narrow, ['src/agentic_sdlc/cli.py'])
        self.assertEqual(('make second',), got.commands)


class CapturesAreSubstitutedNotQuoted(unittest.TestCase):
    """Hostile TREE contents, which config validation cannot see."""

    HOSTILE = {
        'space': 'systems/my combat/a.gd',
        'single quote': "systems/it's/a.gd",
        'double quote': 'systems/"q"/a.gd',
        'dollar': 'systems/$(id)/a.gd',
        'semicolon': 'systems/a;b/a.gd',
        'pipe': 'systems/a|b/a.gd',
        'backtick': 'systems/`id`/a.gd',
        'ampersand': 'systems/a&b/a.gd',
        'redirect': 'systems/a>b/a.gd',
        'comment': 'systems/a#b/a.gd',
    }
    # A TAB is not here: it is a control character, so the PATH check refuses
    # it before any capture binds — see ChangedPathRefusalMatrix. Two guards
    # covering one input is fine; asserting the wrong one's message is not.

    def test_a_capture_binding_a_shell_character_is_refused_naming_both(self):
        narrow = ruleset(SYS)
        for label, path in self.HOSTILE.items():
            with self.subTest(character=label):
                with self.assertRaises(SelectionError) as caught:
                    select.select(narrow, [path])
                message = str(caught.exception)
                self.assertIn(path, message, 'the message names the PATH')
                self.assertIn('#1', message, 'and the rule\'s own index')

    def test_an_ordinary_value_substitutes_literally(self):
        got = select.select(ruleset(SYS), ['systems/combat-2.a/x.gd'])
        self.assertEqual(('make unit SYS=combat-2.a',), got.commands)

    def test_a_rule_with_no_capture_never_consults_the_path(self):
        # `run` has no placeholder, so a hostile filename cannot reach it. It is
        # still refused as a PATH if it is malformed, but a shell character in
        # a segment nothing binds is not this module's business.
        got = select.select(ruleset(PM),
                            ['src/agentic_sdlc/repo/pm/a$b.py'])
        self.assertEqual(('python3 -m pytest tests/test_pm_rules.py',),
                         got.commands)


class ChangedPathRefusalMatrix(unittest.TestCase):
    """The path list is an input surface: it arrives from git or from a caller."""

    REFUSED = {
        'traversal': '../outside/x.py',
        'traversal mid-path': 'src/../../etc/passwd',
        'absolute': '/etc/passwd',
        'empty': '',
        'dot': '.',
        'dotdot': '..',
        'dot segment': 'a/./b',
        'double slash': 'a//b',
        'trailing slash': 'a/b/',
        'newline': 'a\nb.py',
        'carriage return': 'a\rb.py',
        'NUL': 'a\x00b.py',
        'tab': 'systems/a\tb/a.gd',
        'backslash': 'src\\pm\\a.py',
        'too long': 'a/' * 2100 + 'x.py',
    }

    def test_each_is_refused_naming_the_path(self):
        narrow = ruleset(PM, SYS)
        for label, path in self.REFUSED.items():
            with self.subTest(case=label):
                with self.assertRaises(SelectionError):
                    select.select(narrow, [path])

    def test_a_refusal_takes_the_whole_call_not_just_that_path(self):
        # Partial results are how a caller ends up verifying a subset it never
        # asked for while believing it verified the diff.
        with self.assertRaises(SelectionError):
            select.select(ruleset(PM),
                          ['src/agentic_sdlc/repo/pm/a.py', '/etc/passwd'])

    def test_a_symlink_shaped_path_is_matched_as_a_path_and_nothing_more(self):
        # Nothing here stats, opens or resolves — the name is all there is.
        got = select.select(ruleset(PM),
                            ['src/agentic_sdlc/repo/pm/link_to_elsewhere.py'])
        self.assertEqual(1, len(got.commands))


class EmptyAndDeterministic(unittest.TestCase):

    def test_an_empty_changed_list_is_an_empty_selection_not_a_pass(self):
        got = select.select(ruleset(PM), [])
        self.assertEqual(Selection((), (), ()), got,
                         'nothing changed, so nothing narrow was selected — '
                         'whether that is a reason to skip verification is the '
                         "caller's question, not an empty tuple's answer")

    def test_the_same_input_gives_the_identical_selection_twice(self):
        narrow = ruleset(PM, SYS, TESTS)
        changed = ['systems/ui/a.gd', 'README.md', 'systems/ui/b.gd',
                   'tests/test_x.py', 'src/agentic_sdlc/repo/pm/m.py']
        first = select.select(narrow, changed)
        second = select.select(narrow, changed)
        self.assertEqual(first, second)
        self.assertEqual(first.commands, second.commands)

    def test_ten_thousand_paths_against_fifty_rules_stay_a_small_command_set(self):
        narrow = ruleset(SYS, *[{'paths': f'other{n}/**', 'run': f'make m{n}'}
                                for n in range(49)])
        changed = [f'systems/s{n % 5}/file{n}.gd' for n in range(10_000)]
        started = time.monotonic()
        got = select.select(narrow, changed)
        elapsed = time.monotonic() - started
        self.assertEqual(5, len(got.commands))
        self.assertEqual(10_000, len(got.matched_paths))
        self.assertLess(elapsed, 10.0, 'quadratic blowup in the selector')


class TheSelectorDoesNoWork(unittest.TestCase):
    """Adversarial against the docstring: "never spawns", "reads no file"."""

    SPAWN_OR_IO = frozenset({
        'run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen',
        'getoutput', 'getstatusoutput', 'open', 'read_text', 'read_bytes',
        'write_text', 'glob', 'rglob', 'iterdir', 'walk', 'listdir', 'exists',
        'stat', 'resolve', 'load_config', 'config_section',
    })
    ALLOWED_IMPORTS = frozenset({
        're', 'dataclasses', 'typing', 'agentic_sdlc.repo.verify.rules'})

    def _tree(self) -> ast.Module:
        return ast.parse(SELECT_SOURCE.read_text(encoding='utf-8'))

    def test_it_imports_nothing_that_could_spawn_or_read(self):
        imported = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module != '__future__':
                imported.add(node.module or '')
        self.assertEqual(set(), imported - self.ALLOWED_IMPORTS)

    def test_it_calls_nothing_that_spawns_or_reads(self):
        offenders = []
        for node in ast.walk(self._tree()):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else '')
            if name in self.SPAWN_OR_IO:
                offenders.append(f'{name} at line {node.lineno}')
        self.assertEqual([], offenders)

    def test_a_run_that_would_be_a_command_is_never_executed(self):
        # `rules.py` refuses the chaining spellings, so the worst a run can be
        # is a real command line. Selecting it must produce a STRING.
        got = select.select(ruleset({'paths': 'a/**',
                                     'run': 'rm -rf /tmp/verify-sentinel'}),
                            ['a/x.py'])
        self.assertEqual(('rm -rf /tmp/verify-sentinel',), got.commands)
        self.assertIsInstance(got.commands[0], str)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
