"""test_verify_rules.py — the `[verify]` grammar, and everything it refuses.

`run` is a shell command read from config and executed later, so this file is
mostly a refusal matrix (SDLC.md §5) rather than a parse test. Three things it
is built to catch, each of which has shipped here before or is one edit away:

  * a rule quietly DROPPED from the list — the read-side cardinal sin wearing a
    new hat, because the caller then verifies less than it thinks and reports
    success. Every refusal here asserts the rule's own INDEX is in the message;
  * a BARE STRING read as a collection (`tuple(cfg.get(...))`, seven gates,
    v0.9.0). Two cases pin that shape by name;
  * exit 1 for a config typo, which CI reads as "drift found". Every refusal
    class asserts 2.

The adversarial half runs against the module's own docstring claims: it says
it never spawns and never reads a file, so `TheReaderDoesNoWork` reads its
AST and holds it to that — a claim nothing checks is a comment.
"""
from __future__ import annotations

import ast
import unittest

from support import REPO_ROOT

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.repo.verify import rules

RULES_SOURCE = REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'verify' / 'rules.py'

WIDE = 'make check test'
FORWARD = {'paths': 'src/agentic_sdlc/repo/pm/**',
           'run': 'python3 -m pytest tests/test_pm_*.py'}
CAPTURED = {'paths': 'tests/test_<name>.py',
            'run': 'python3 -m pytest tests/test_<name>.py'}
REVERSE = {'declares': '## covers:', 'scan': 'tests/integration/**',
           'run': 'make scenario NAME=<stem>'}
GOOD = {'wide': WIDE, 'narrow': [dict(FORWARD), dict(CAPTURED), dict(REVERSE)]}


def one(**rule) -> dict:
    """A section whose only interesting part is the single rule under test."""
    return {'wide': WIDE, 'narrow': [rule]}


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
    """The intended path, and the three grammar rulings it settles."""

    def test_a_mixed_rule_set_parses_in_declaration_order(self):
        parsed = rules.read(GOOD)
        self.assertEqual(WIDE, parsed.wide)
        self.assertEqual(3, len(parsed.narrow))
        self.assertEqual((1, 2, 3), tuple(r.index for r in parsed.narrow))
        self.assertEqual(('forward', 'forward', 'reverse'),
                         tuple(r.kind for r in parsed.narrow))
        self.assertEqual(0, exit_code(GOOD))

    def test_the_captures_are_already_extracted(self):
        parsed = rules.read(GOOD)
        self.assertEqual((), parsed.narrow[0].captures)
        self.assertEqual(('name',), parsed.narrow[1].captures)
        self.assertEqual(('stem',), parsed.narrow[2].captures,
                         'the reverse direction binds <stem>, derived not declared')

    def test_a_wide_only_declaration_is_legal(self):
        # Absent is not empty — `config.str_tuple`'s rule. `narrow = []` is the
        # refused one (see EmptyRuleList); leaving the key out declares a repo
        # whose close is its only command.
        parsed = rules.read({'wide': WIDE})
        self.assertEqual((), parsed.narrow)

    def test_RULING_1_a_capture_stops_at_a_path_separator(self):
        rule = rules.read(one(**CAPTURED)).narrow[0]
        matched = rule.pattern.match('tests/test_c.py')
        self.assertEqual('c', matched.group('name'))
        # Every path here reaches the capture — the literal prefix and suffix
        # both match — so what refuses them is the capture's own bound, which
        # is the whole of RULING 1. A `.`-for-`[^/]` here binds `a/b` and
        # interpolates it into a command line.
        for spanning in ('tests/test_a/b.py', 'tests/test_a/b/c.py',
                         'tests/test_/x.py'):
            with self.subTest(path=spanning):
                self.assertIsNone(rule.pattern.match(spanning))
        wide_open = rules.read(one(paths='tests/<name>.py',
                                   run='make x <name>')).narrow[0]
        self.assertIsNone(wide_open.pattern.match('tests/a/b.py'))
        self.assertEqual('c', wide_open.pattern.match('tests/c.py').group('name'))

    def test_a_double_star_does_span_separators(self):
        rule = rules.read(one(**FORWARD)).narrow[0]
        self.assertTrue(rule.pattern.match('src/agentic_sdlc/repo/pm/a/b.py'))
        self.assertIsNone(rule.pattern.match('src/agentic_sdlc/repo/checks/a.py'))

    def test_declares_is_a_literal_prefix_not_a_pattern(self):
        # `.*` is a legal declares. It is stored verbatim — nothing here
        # compiles it, so story 03 scans for the literal three characters.
        rule = rules.read(reverse(declares='.*')).narrow[0]
        self.assertEqual('.*', rule.declares)
        self.assertIsInstance(rule.declares, str)

    def test_a_run_may_carry_a_glob_and_an_assignment(self):
        # The feature's own examples: `tests/test_pm_*.py` and `NAME=<stem>`.
        self.assertEqual(0, exit_code(GOOD))


class TheBareStringTrap(Refuses):
    """v0.9.0's defect shape, pinned by name: a string is iterable."""

    def test_narrow_as_a_bare_string_is_refused_never_iterated(self):
        message = self.assertRefuses({'wide': WIDE, 'narrow': 'paths = x'},
                                     'narrow', 'paths = x')
        self.assertNotIn("'p', 'a', 't'", message,
                         'a bare string walked character by character is the '
                         'v0.9.0 defect: seven gates, empty census, PASS')

    def test_paths_as_a_list_is_refused(self):
        self.assertRefuses(forward(paths=['src/**']), '#1', 'paths')

    def test_run_as_a_list_is_refused(self):
        self.assertRefuses(forward(run=['make x']), '#1', 'run')

    def test_wide_as_a_list_is_refused(self):
        self.assertRefuses({'wide': [WIDE], 'narrow': [dict(FORWARD)]}, 'wide')

    def test_wide_as_a_number_is_refused(self):
        self.assertRefuses({'wide': 7, 'narrow': [dict(FORWARD)]}, 'wide')


class EmptyRuleList(Refuses):
    """An empty list reads as "nothing" and means the opposite downstream."""

    def test_an_empty_narrow_is_refused_and_says_to_remove_it(self):
        self.assertRefuses({'wide': WIDE, 'narrow': []}, 'narrow', 'remove')


class WideIsRequired(Refuses):
    """No wide is no close — falling back to "run nothing" is the silent pass."""

    def test_wide_absent_is_refused(self):
        self.assertRefuses({'narrow': [dict(FORWARD)]}, 'wide', 'required')

    def test_wide_empty_is_refused(self):
        self.assertRefuses({'wide': '', 'narrow': [dict(FORWARD)]}, 'wide')

    def test_wide_takes_the_same_command_grammar_as_run(self):
        for hostile in ('make a; rm -rf /', 'make a && make b', 'make `id`',
                        'make $(id)', 'a | b', 'a > f', 'make a\nmake b',
                        'make ' + 'x' * rules.MAX_RUN):
            with self.subTest(wide=hostile[:24]):
                self.assertRefuses({'wide': hostile,
                                    'narrow': [dict(FORWARD)]}, 'wide')


class RunGrammar(Refuses):
    """`run` is executed later, so it is the narrowest grammar of the three."""

    def test_an_empty_run_is_refused(self):
        self.assertRefuses(forward(run=''), '#1', 'run')
        self.assertRefuses(forward(run='   '), '#1', 'run')

    def test_chaining_and_substitution_are_refused(self):
        # A rule set is a tracked file, but a rule that CHAINS is a rule whose
        # second half nobody reviewed.
        for hostile in ('make x; rm -rf /', 'make `id`', 'make $(id)',
                        'a | b', 'a && b', 'a > f', 'a < f', 'make x & ',
                        'make $HOME', 'make (x)', 'make x # and the rest',
                        'make x \\\n make y'):
            with self.subTest(run=hostile):
                self.assertRefuses(forward(run=hostile), '#1', 'run')

    def test_an_embedded_newline_is_two_commands(self):
        self.assertRefuses(forward(run='make x\nmake y'), '#1', 'newline')

    def test_a_NUL_in_run_is_refused(self):
        self.assertRefuses(forward(run='make x\x00rm -rf /'), '#1', 'run')

    def test_a_capture_no_paths_declares_is_refused(self):
        # The single most dangerous typo here: the placeholder would otherwise
        # reach a shell literally.
        self.assertRefuses(forward(run='make x <undeclared>'),
                           '#1', 'undeclared')

    def test_RULING_3_stem_in_a_forward_run_is_refused(self):
        self.assertRefuses(forward(run='<stem> foo'), '#1', 'stem')

    def test_RULING_3_stem_may_not_be_DECLARED_by_a_forward_paths(self):
        self.assertRefuses(forward(paths='tests/<stem>.py',
                                   run='make x <stem>'), '#1', 'stem')

    def test_a_reverse_run_may_use_stem_and_nothing_else(self):
        self.assertEqual(0, exit_code(reverse()))
        self.assertRefuses(reverse(run='make scenario NAME=<other>'),
                           '#1', 'other')

    def test_a_run_longer_than_the_cap_is_refused(self):
        self.assertRefuses(forward(run='make ' + 'x' * rules.MAX_RUN),
                           '#1', str(rules.MAX_RUN))

    def test_run_absent_is_refused(self):
        self.assertRefuses(one(paths='src/**'), '#1', 'run')
        self.assertRefuses(one(declares='## covers:', scan='tests/**'),
                           '#1', 'run')


class GlobGrammar(Refuses):
    """`paths` / `scan` — matched against tracked files, so: inside the tree."""

    def _both_directions(self, value: str, *fragments: str) -> None:
        self.assertRefuses(forward(paths=value, run='make x'), *fragments)
        self.assertRefuses(reverse(scan=value), *fragments)

    def test_traversal_and_absolute_paths_are_refused(self):
        # Hard rule 8: nothing here reads outside the checkout.
        for value in ('../../etc/**', '/etc/**', 'src/../../etc/**', '..'):
            with self.subTest(paths=value):
                self._both_directions(value, '#1')

    def test_home_expansion_and_schemes_are_refused(self):
        for value in ('~/x', '~', 'file:///x', 'https://x', 'C:/x'):
            with self.subTest(paths=value):
                self._both_directions(value, '#1')

    def test_empty_and_dot_segments_are_refused(self):
        for value in ('', '.', 'a//b', 'a/./b', 'src/**/', './src/**'):
            with self.subTest(paths=value):
                self._both_directions(value, '#1')

    def test_backslash_separators_are_refused(self):
        self._both_directions('src\\pm\\**', '#1')

    def test_malformed_and_adjacent_captures_are_refused(self):
        for value in ('tests/<a><b>.py', 'tests/<>.py', 'tests/<a.py',
                      'tests/a>.py', 'tests/<a b>.py', 'tests/<1a>.py',
                      'tests/<' + 'a' * (rules.MAX_CAPTURE + 1) + '>.py'):
            with self.subTest(paths=value):
                self.assertRefuses(forward(paths=value, run='make x'), '#1')

    def test_the_whole_tree_is_refused_because_narrow_would_mean_wide(self):
        for value in ('**', '*', '**/*', '*/**'):
            with self.subTest(paths=value):
                self._both_directions(value, '#1')

    def test_a_duplicate_capture_name_is_refused(self):
        self.assertRefuses(
            forward(paths='tests/<name>/test_<name>.py',
                    run='make x <name>'), '#1', 'name')

    def test_a_glob_longer_than_the_cap_is_refused(self):
        self._both_directions('src/' + 'a' * rules.MAX_GLOB + '/**',
                              '#1', str(rules.MAX_GLOB))

    def test_a_newline_or_NUL_in_a_glob_is_refused(self):
        self._both_directions('src/**\nsrc/x', '#1')
        self._both_directions('src/\x00/**', '#1')

    def test_RULING_3_scan_may_not_declare_a_capture(self):
        self.assertRefuses(reverse(scan='tests/<kind>/**'), '#1', 'stem')


class DeclaresGrammar(Refuses):
    """The reverse direction's header, a literal line prefix."""

    def test_declares_without_scan_is_refused(self):
        self.assertRefuses(one(declares='## covers:', run='make x'),
                           '#1', 'scan')

    def test_scan_without_declares_is_refused(self):
        self.assertRefuses(one(scan='tests/**', run='make x'),
                           '#1', 'declares')

    def test_an_empty_declares_is_refused(self):
        self.assertRefuses(reverse(declares=''), '#1', 'declares')

    def test_a_declares_longer_than_the_cap_is_refused(self):
        self.assertRefuses(reverse(declares='#' * (rules.MAX_DECLARES + 1)),
                           '#1', str(rules.MAX_DECLARES))

    def test_a_newline_in_declares_is_refused(self):
        self.assertRefuses(reverse(declares='## a\n## b'), '#1', 'declares')

    def test_declares_as_a_list_is_refused(self):
        self.assertRefuses(reverse(declares=['## covers:']), '#1', 'declares')


class StructuralGrammar(Refuses):
    """Ruling 2, and the keys that decide which direction a rule is."""

    def test_RULING_2_a_rule_with_both_directions_is_refused(self):
        self.assertRefuses(
            one(paths='src/**', declares='## covers:', scan='tests/**',
                run='make x'), '#1', 'paths', 'declares')

    def test_RULING_2_a_rule_with_neither_direction_is_refused(self):
        self.assertRefuses(one(run='make x'), '#1', 'paths', 'declares')

    def test_an_unknown_key_inside_a_rule_is_named(self):
        # A typo'd `path` would otherwise make the rule match nothing forever.
        self.assertRefuses(one(path='src/**', run='make x'), '#1', 'path')

    def test_a_rule_that_is_not_a_table_is_refused(self):
        self.assertRefuses({'wide': WIDE, 'narrow': ['paths = x']}, '#1')
        self.assertRefuses({'wide': WIDE, 'narrow': [['paths', 'x']]}, '#1')

    def test_a_verify_section_that_is_not_a_table_is_refused(self):
        for value in ('wide = x', ['wide'], 7):
            with self.subTest(section=value):
                self.assertRefuses(value, 'verify')

    def test_an_unknown_key_in_the_section_is_named(self):
        self.assertRefuses({'wide': WIDE, 'wilde': WIDE,
                            'narrow': [dict(FORWARD)]}, 'wilde')


class EveryRefusalNamesItsIndex(Refuses):
    """With only the first index named, an author fixes one and re-runs blind."""

    def test_a_second_and_a_fourth_bad_rule_are_both_named(self):
        section = {'wide': WIDE, 'narrow': [
            dict(FORWARD),
            {'paths': '../../etc/**', 'run': 'make x'},
            dict(CAPTURED),
            {'paths': 'src/**', 'run': 'make x; rm -rf /'},
        ]}
        message = self.assertRefuses(section, '#2', '#4')
        self.assertNotIn('#1', message)
        self.assertNotIn('#3', message)

    def test_the_index_is_one_based_and_matches_declaration_order(self):
        section = {'wide': WIDE,
                   'narrow': [dict(FORWARD), dict(REVERSE), {'run': ''}]}
        self.assertRefuses(section, '#3')

    def test_a_bad_wide_and_a_bad_rule_are_reported_together(self):
        section = {'wide': 'make a; make b',
                   'narrow': [dict(FORWARD), {'paths': '/etc/**', 'run': 'x'}]}
        self.assertRefuses(section, 'wide', '#2')


class ExitCodeIsTwo(Refuses):
    """Rule 6 as a contract: a config problem is 2, never 1."""

    def test_every_refusal_class_exits_two(self):
        cases = {
            'bare string': {'wide': WIDE, 'narrow': 'paths = x'},
            'empty list': {'wide': WIDE, 'narrow': []},
            'wide absent': {'narrow': [dict(FORWARD)]},
            'run chaining': forward(run='a; b'),
            'glob traversal': forward(paths='../x/**'),
            'both directions': one(paths='src/**', declares='c', scan='t/**',
                                   run='make x'),
            'unknown key': one(path='src/**', run='make x'),
            'not a table': 'wide = x',
        }
        for label, section in cases.items():
            with self.subTest(case=label):
                self.assertEqual(2, exit_code(section))

    def test_the_module_names_the_contract(self):
        self.assertEqual(2, rules.EXIT_CONFIG)

    def test_a_valid_rule_set_is_zero(self):
        self.assertEqual(0, exit_code(GOOD))


class TheReaderDoesNoWork(unittest.TestCase):
    """Adversarial against the docstring: "never spawns", "reads no file".

    Both claims are structural, so they are checked structurally. A refusal
    that shelled out on its way to refusing would still be a refusal, and the
    test above would not notice.
    """

    SPAWN_OR_IO = frozenset({
        'run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen',
        'getoutput', 'getstatusoutput', 'fork', 'execv', 'execvp', 'spawnv',
        'open', 'read_text', 'read_bytes', 'write_text', 'glob', 'rglob',
        'iterdir', 'walk', 'listdir', 'load_config', 'config_section',
    })
    ALLOWED_IMPORTS = frozenset({
        're', 'dataclasses', 'agentic_sdlc.core.config'})

    def _tree(self) -> ast.Module:
        return ast.parse(RULES_SOURCE.read_text(encoding='utf-8'))

    def test_it_imports_nothing_that_could_spawn_or_read(self):
        imported = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module != '__future__':
                imported.add(node.module or '')
        self.assertEqual(set(), imported - self.ALLOWED_IMPORTS,
                         'the module claims it never spawns and reads no file; '
                         'these imports are how that stops being true')

    def test_it_calls_nothing_that_spawns_reads_or_re_reads_config(self):
        offenders = []
        for node in ast.walk(self._tree()):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else '')
            if name in self.SPAWN_OR_IO:
                offenders.append(f'rules.py:{node.lineno}: {name}()')
        self.assertEqual([], offenders,
                         'core/config.py is the ONE reader, and this module '
                         'spawns nothing:\n  ' + '\n  '.join(offenders))

    def test_the_three_rulings_are_recorded_with_their_reasons(self):
        doc = ast.get_docstring(self._tree()) or ''
        for claim in ('RULING 1', 'RULING 2', 'RULING 3',
                      'REFUSAL MATRIX', 'never spawns'):
            self.assertIn(claim, doc,
                          'the rulings live in the docstring, with the reason')

    def test_the_module_is_stdlib_only(self):
        for module in self.ALLOWED_IMPORTS:
            if module.startswith('agentic_sdlc'):
                continue
            self.assertIn(module, ('re', 'dataclasses'),
                          'hard rule 1: no runtime dependencies, ever')


if __name__ == '__main__':
    unittest.main()
