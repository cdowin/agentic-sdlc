"""test_verify_select.py — the forward selector, and the miss it must never eat.

THE FIRST TEST IN THIS FILE IS THE ONE THAT MATTERS. A narrow verifier that
matches nothing and exits 0 is worse than no verifier: it reports success for
work it never checked. So `TheLoudMiss` comes first, and `TheInvariant` behind
it turns "we remembered to report misses" into "a path cannot leave the
selector without appearing on exactly one of the two lists".

The rest is the refusal matrix for a surface `rules.py` cannot see, and this is
where that grammar lives (SDLC.md §5): config validation cannot know that a
repository contains a directory called `my repo` or `$(id)`, and a capture that
BINDS one of those is a command line assembled out of tree contents.

`select.py`'s "never spawns, reads no file" claim is held structurally in
`test_verify_rules.py`, once for the three pure modules, rather than a third
time here.
"""
from __future__ import annotations

import time
import unittest

from agentic_sdlc.repo.verify import rules, select
from agentic_sdlc.repo.verify.select import Selection, SelectionError

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
                self.assertEqual(sorted(corpus),
                                 sorted(list(matched) + list(got.missed)))
        # Every path misses: the one shape where a caller most needs telling.
        empty = select.select((), ['a.py', 'b.py'])
        self.assertEqual(('a.py', 'b.py'), empty.missed)
        self.assertEqual((), empty.commands)

    def test_an_empty_changed_list_is_an_empty_selection_not_a_pass(self):
        got = select.select(ruleset(PM), [])
        self.assertEqual(Selection((), (), ()), got,
                         'nothing changed, so nothing narrow was selected — '
                         'whether that is a reason to skip verification is the '
                         "caller's question, not an empty tuple's answer")


class Dedupe(unittest.TestCase):
    """Five files under one capture are ONE command. That is the 170x."""

    def test_files_sharing_a_bound_value_collapse_to_one_command_in_order(self):
        changed = [f'systems/combat/{n}.gd' for n in 'abcde'] \
            + ['systems/ui/a.gd', 'systems/ui/b.gd']
        got = select.select(ruleset(SYS), changed)
        self.assertEqual(('make unit SYS=combat', 'make unit SYS=ui'),
                         got.commands,
                         'one command per bound value, in first-emission order')
        self.assertEqual(tuple(changed[:5]), got.matched[0].paths,
                         'a dedupe that loses the attribution is a dedupe that '
                         'cannot explain itself')
        self.assertEqual((), got.missed)

    def test_two_different_rules_substituting_to_one_command_dedupe(self):
        # Dedupe is across the whole selection, not within a single rule — and
        # the collapsed Match carries the FIRST rule's index, which is the trap
        # `main._first_claims` (finding S1) exists to work around.
        narrow = ruleset({'paths': 'a/**', 'run': 'make slice'},
                         {'paths': 'b/**', 'run': 'make slice'})
        got = select.select(narrow, ['a/x.py', 'b/y.py'])
        self.assertEqual(('make slice',), got.commands)
        self.assertEqual(('a/x.py', 'b/y.py'), got.matched[0].paths)
        self.assertEqual(1, got.matched[0].index,
                         'the first rule to emit the command owns the slot')


class FirstMatchingRuleWins(unittest.TestCase):
    """A path is not fanned out; adding a rule must not multiply the work."""

    def test_declaration_order_decides_and_reversing_it_reverses_the_answer(self):
        wide = {'paths': 'src/**', 'run': 'make first'}
        narrow = {'paths': 'src/agentic_sdlc/**', 'run': 'make second'}
        got = select.select(ruleset(wide, narrow), ['src/agentic_sdlc/cli.py'])
        self.assertEqual(('make first',), got.commands)
        self.assertEqual(1, got.matched[0].index)
        self.assertEqual(1, len(got.matched), 'claimed once, never fanned out')
        flipped = select.select(ruleset(narrow, wide),
                                ['src/agentic_sdlc/cli.py'])
        self.assertEqual(('make second',), flipped.commands)


class CapturesAreSubstitutedNotQuoted(unittest.TestCase):
    """Hostile TREE contents, which config validation cannot see."""

    def test_a_capture_binding_a_shell_character_is_refused_naming_both(self):
        # Enumerated from the constant, not from a list of spellings: a
        # character dropped from the set is the defect, and it is the only way
        # `make unit SYS=$(id)` gets assembled out of a directory name.
        self.assertEqual(set(rules.COMMAND_FORBIDDEN) | set('\'" \t'),
                         set(select.CAPTURE_FORBIDDEN),
                         'the bans are `rules.py`\'s plus whitespace and '
                         'quotes — config cannot know what a directory is '
                         'called')
        narrow = ruleset(SYS)
        earlier = set('\t\\')  # refused by the PATH check before any capture binds
        for char in sorted(select.CAPTURE_FORBIDDEN - earlier):
            path = f'systems/a{char}b/x.gd'
            with self.subTest(char=char):
                with self.assertRaises(SelectionError) as caught:
                    select.select(narrow, [path])
                message = str(caught.exception)
                self.assertIn(path, message, 'the message names the PATH')
                self.assertIn('#1', message, "and the rule's own index")
        # A TAB and a BACKSLASH are refused one guard earlier, by the PATH
        # check — two guards over one input is fine; asserting the wrong one's
        # message is not.
        for char in sorted(earlier):
            with self.subTest(char=char, guard='path'):
                with self.assertRaises(SelectionError):
                    select.select(narrow, [f'systems/a{char}b/x.gd'])

    def test_an_ordinary_value_substitutes_literally_and_is_not_over_refused(self):
        got = select.select(ruleset(SYS), ['systems/combat-2.a/x.gd'])
        self.assertEqual(('make unit SYS=combat-2.a',), got.commands)
        # `run` has no placeholder here, so a hostile filename cannot reach it:
        # a shell character in a segment nothing binds is not this module's
        # business, and refusing it would redden a legal tree.
        untouched = select.select(ruleset(PM),
                                  ['src/agentic_sdlc/repo/pm/a$b.py'])
        self.assertEqual(('python3 -m pytest tests/test_pm_rules.py',),
                         untouched.commands)


class ChangedPathRefusalMatrix(unittest.TestCase):
    """The path list is an input surface: it arrives from git or from a caller.

    Nothing else validates it — `rules.py` refuses hostile CONFIG — so the
    matrix for this grammar is enumerated here and nowhere else.
    """

    REFUSED = {
        'traversal': '../outside/x.py',
        'traversal mid-path': 'src/../../etc/passwd',
        'absolute': '/etc/passwd',
        'empty': '',
        'dot': '.',
        'dot segment': 'a/./b',
        'double slash': 'a//b',
        'trailing slash': 'a/b/',
        # `git diff -z` exists because a rename can carry a newline; a selector
        # that split on newlines would see two paths where the tree has one.
        'newline': 'a\nb.py',
        'NUL': 'a\x00b.py',
        'backslash': 'src\\pm\\a.py',
        'too long': 'a/' * 2100 + 'x.py',
    }

    def test_each_is_refused_and_the_refusal_takes_the_whole_call(self):
        narrow = ruleset(PM, SYS)
        for label, path in self.REFUSED.items():
            with self.subTest(case=label):
                with self.assertRaises(SelectionError):
                    select.select(narrow, [path])
        # Partial results are how a caller ends up verifying a subset it never
        # asked for while believing it verified the diff.
        with self.assertRaises(SelectionError):
            select.select(narrow, ['src/agentic_sdlc/repo/pm/a.py',
                                   '/etc/passwd'])


class Deterministic(unittest.TestCase):

    def test_ten_thousand_paths_against_fifty_rules_stay_a_small_command_set(self):
        # The selector is on the path a consumer runs dozens of times a day; a
        # quadratic one is a slower inner loop, which is the defect this
        # milestone exists to remove rather than a failure anything reports.
        narrow = ruleset(SYS, *[{'paths': f'other{n}/**', 'run': f'make m{n}'}
                                for n in range(49)])
        changed = [f'systems/s{n % 5}/file{n}.gd' for n in range(10_000)]
        started = time.monotonic()
        got = select.select(narrow, changed)
        elapsed = time.monotonic() - started
        self.assertEqual(5, len(got.commands))
        self.assertEqual(10_000, len(got.matched_paths))
        self.assertLess(elapsed, 10.0, 'quadratic blowup in the selector')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
