"""test_verify_declares.py — the reverse scan, its two zero-censuses, and the
payload refusals its header grammar is.

The corpus is BUILT HERE, as literal strings, into a `tempfile` tree. That is
rule 8 satisfied the cheapest way: the fixture is committed with the code that
reads it and versioned with it, and no case reaches for a tree outside this
checkout — which would answer differently on every machine. Nothing here writes
into `tests/fixtures/`, so two builders in one worktree cannot collide.

`TheZeroCensus` is the reason the story exists: a `scan` that finds no
declaring file must return something a caller cannot mistake for "nothing to
run", and a `scan` that matches no file AT ALL is the louder of the two.
"""
from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

from agentic_sdlc.repo.verify import declares, rules

DECLARES_SOURCE = (REPO_ROOT / 'src' / 'agentic_sdlc' / 'repo' / 'verify'
                   / 'declares.py')

MILESTONE = 'make milestone'
HEADER = '## covers:'
RULE = {'declares': HEADER, 'scan': 'tests/integration/**',
        'run': 'make scenario NAME=<stem>'}


def rule(**overrides):
    """The single reverse rule under test, through the shipped reader."""
    entry = {**RULE, **overrides}
    return rules.read({'milestone': MILESTONE, 'narrow': [entry]}).narrow[0]


class Corpus:
    """A scratch tree of declaring and non-declaring files, and its tracked list."""

    def __init__(self, files: dict[str, str]):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, body in files.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(body, bytes):
                target.write_bytes(body)
            else:
                target.write_text(body, encoding='utf-8')
        self.tracked = sorted(files)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()
        return False


def declaring(*covered: str, extra: str = '') -> str:
    return f'# A scenario\n\n{HEADER} {" ".join(covered)}\n\n{extra}body\n'


class TheHappyPath(unittest.TestCase):

    FILES = {
        'tests/integration/checkout.md': declaring(
            'src/agentic_sdlc/repo/pm/ledger.py', 'src/agentic_sdlc/repo/pm'),
        'tests/integration/plain.md': '# no header at all\n',
        'tests/other/ignored.md': declaring('src/anything.py'),
    }

    def test_a_changed_path_selects_the_declaring_files_run(self):
        with Corpus(self.FILES) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(2, got.scanned, 'the scan glob is tests/integration/**')
            self.assertEqual(1, got.declaring)
            self.assertEqual((), got.findings)
            found = got.declarations[0]
            self.assertEqual('checkout', found.stem)
            self.assertEqual('make scenario NAME=checkout', found.command)
            self.assertTrue(found.covers_path('src/agentic_sdlc/repo/pm/ledger.py'))

    def test_a_changed_path_listed_nowhere_selects_nothing(self):
        with Corpus(self.FILES) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertIsNone(declares.resolve([got], rule(), 'README.md'),
                              'unmatched here means the caller folds it into '
                              '`missed` — never absorbed by a rule that '
                              '"handled" it')

    def test_resolve_returns_the_command_for_a_covered_path(self):
        with Corpus(self.FILES) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(
                'make scenario NAME=checkout',
                declares.resolve([got], rule(),
                                 'src/agentic_sdlc/repo/pm/report.py'))


class SegmentBoundedPrefix(unittest.TestCase):
    """`src/a` covers `src/a/b.py` and never `src/ab.py`. The over-selection."""

    def test_a_declared_directory_covers_under_it_and_not_beside_it(self):
        files = {'tests/integration/s.md': declaring('src/a'),
                 'src/a/b.py': 'x\n', 'src/ab.py': 'x\n'}
        with Corpus(files) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            found = got.declarations[0]
            self.assertTrue(found.covers_path('src/a/b.py'))
            self.assertTrue(found.covers_path('src/a'))
            self.assertFalse(found.covers_path('src/ab.py'),
                             'a prefix that is not segment-bounded is the '
                             'off-by-one that silently over-selects')
            self.assertFalse(found.covers_path('src/abc/d.py'))


class TheZeroCensus(unittest.TestCase):
    """Rule 4's read side. Two distinct zeros, and neither may read as a pass."""

    def test_files_found_and_none_declaring_is_scanned_N_declaring_0(self):
        files = {f'tests/integration/f{n}.md': f'# nothing here {n}\n'
                 for n in range(4)}
        with Corpus(files) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(4, got.scanned)
            self.assertEqual(0, got.declaring)
            self.assertTrue(got.empty_corpus)
            self.assertFalse(got.empty_scan,
                             'this is the QUIETER of the two zeros and must '
                             'stay distinguishable from a glob that matched '
                             'no file at all')

    def test_a_glob_matching_zero_files_is_the_louder_scanned_0(self):
        with Corpus({'src/a.py': 'x\n'}) as corpus:
            got = declares.scan(rule(scan='tests/renamed_away/**'),
                                corpus.tracked, corpus.root)
            self.assertEqual(0, got.scanned)
            self.assertEqual(0, got.declaring)
            self.assertTrue(got.empty_scan)
            self.assertFalse(got.empty_corpus)

    def test_the_two_zeros_are_distinguishable_from_each_other(self):
        with Corpus({'tests/integration/f.md': '# none\n'}) as corpus:
            drifted = declares.scan(rule(), corpus.tracked, corpus.root)
            absent = declares.scan(rule(scan='tests/gone/**'),
                                   corpus.tracked, corpus.root)
        self.assertNotEqual((drifted.empty_scan, drifted.empty_corpus),
                            (absent.empty_scan, absent.empty_corpus))


class TheHeaderIsLiteralNotAPattern(unittest.TestCase):

    def test_a_declares_that_looks_like_a_regex_matches_only_itself(self):
        # `rules.py` stores `declares` verbatim; nothing here compiles it.
        files = {'tests/integration/a.md': '## coversXYZ: src/a.py\n',
                 'tests/integration/b.md': '## covers.*: src/b.py\n'}
        with Corpus(files) as corpus:
            got = declares.scan(rule(declares='## covers.*:'),
                                corpus.tracked, corpus.root)
            self.assertEqual(2, got.scanned)
            self.assertEqual(1, got.declaring,
                             'a literal prefix matches `## covers.*:` and NOT '
                             '`## coversXYZ:` — if it matched both, the value '
                             'was compiled as a pattern')
            self.assertEqual('b', got.declarations[0].stem)

    def test_the_prefix_must_start_the_line(self):
        files = {'tests/integration/a.md': f'   {HEADER} src/a.py\n',
                 'tests/integration/b.md': f'see {HEADER} src/b.py\n'}
        with Corpus(files) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(0, got.declaring)


class AFencedExampleIsNotADeclaration(unittest.TestCase):
    """Documentation showing the syntax is not a claim about coverage."""

    def test_a_header_inside_a_fence_is_not_read(self):
        body = ('# How to declare coverage\n\n```\n'
                f'{HEADER} src/example.py\n```\n\nprose\n')
        with Corpus({'tests/integration/doc.md': body}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(1, got.scanned)
            self.assertEqual(0, got.declaring)
            self.assertEqual((), got.findings)

    def test_a_real_header_beside_a_fenced_example_still_declares(self):
        body = (f'{HEADER} src/real.py\n\n```\n{HEADER} src/example.py\n```\n')
        with Corpus({'tests/integration/doc.md': body}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(1, got.declaring)
            self.assertEqual(('src/real.py',), got.declarations[0].covers)

    def test_an_unterminated_fence_is_reported_not_left_to_mask(self):
        body = f'```\n{HEADER} src/example.py\n'
        with Corpus({'tests/integration/doc.md': body}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertTrue(any('never closes' in f for f in got.findings),
                            'a checker cannot both skip a region and claim it '
                            'scanned the file')


class HeaderFindings(unittest.TestCase):
    """Each is a finding naming the file, and the declaration is dropped whole."""

    def _findings(self, body) -> declares.Scan:
        with Corpus({'tests/integration/s.md': body}) as corpus:
            return declares.scan(rule(), corpus.tracked, corpus.root)

    def test_an_empty_header_list_is_a_finding_not_an_empty_coverage_set(self):
        got = self._findings(f'{HEADER}\n')
        self.assertEqual(0, got.declaring)
        self.assertEqual(1, len(got.findings))
        self.assertIn('s.md', got.findings[0])
        self.assertIn('meant to fill', got.findings[0])

    def test_two_headers_in_one_file_name_both_line_numbers(self):
        got = self._findings(f'{HEADER} src/a.py\nx\n{HEADER} src/b.py\n')
        self.assertEqual(0, got.declaring)
        self.assertIn('lines 1, 3', got.findings[0])

    def test_a_header_line_over_the_cap_is_bounded_and_refused(self):
        got = self._findings(f'{HEADER} ' + 'a/b.py ' * 2000 + '\n')
        self.assertEqual(0, got.declaring)
        self.assertTrue(any('header line is' in f for f in got.findings))

    def test_a_file_over_the_cap_is_reported_by_size_and_not_read(self):
        got = self._findings(f'{HEADER} src/a.py\n'
                             + 'x' * (declares.MAX_FILE + 1) + '\n')
        self.assertEqual(0, got.declaring)
        self.assertTrue(any('bytes' in f and 'NOT read' in f
                            for f in got.findings))

    def test_a_file_that_is_not_utf8_is_reported_by_path_never_skipped(self):
        with Corpus({'tests/integration/s.md': b'\xff\xfe\x00bad\n'}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertEqual(1, got.scanned)
        self.assertEqual(0, got.declaring)
        self.assertTrue(any('not UTF-8' in f for f in got.findings))

    def test_too_many_covered_paths_is_a_finding(self):
        got = self._findings(f'{HEADER} '
                             + ' '.join(f'src/f{n}.py'
                                        for n in range(declares.MAX_COVERS + 1))
                             + '\n')
        self.assertEqual(0, got.declaring)
        self.assertTrue(any('manifest' in f for f in got.findings))


class TheCoveredPathRefusalMatrix(unittest.TestCase):
    """The header is written by whoever wrote the test. It is untrusted input."""

    REFUSED = ('../../etc/passwd', '/etc/passwd', '~/x', 'file:///x',
               'https://x', '.', '..', 'a//b', 'a/./b', 'a/b/',
               '$(id)', '`id`', 'a;b', 'a|b', 'a&b', 'a>b', 'a#b',
               'src\\pm\\a.py', '<name>', 'a"b', "a'b")

    def test_each_is_a_finding_naming_the_declaring_file(self):
        for covered in self.REFUSED:
            with self.subTest(covered=covered):
                with Corpus({'tests/integration/s.md':
                             f'{HEADER} {covered}\n'}) as corpus:
                    got = declares.scan(rule(), corpus.tracked, corpus.root)
                self.assertEqual(0, got.declaring)
                self.assertEqual(1, len(got.findings))
                self.assertIn('s.md', got.findings[0])

    def test_one_bad_path_drops_the_whole_declaration(self):
        with Corpus({'tests/integration/s.md':
                     f'{HEADER} src/good.py /etc/passwd\n'}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertEqual(0, got.declaring,
                         'a header that is partly unusable covers nothing '
                         'knowable — half-keeping it is the silent narrowing')

    def test_a_stem_that_would_need_quoting_is_a_finding_not_a_command(self):
        # The tree, not the config, is where a filename like this comes from.
        with Corpus({'tests/integration/a b.md':
                     f'{HEADER} src/a.py\n'}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertEqual(0, got.declaring)
        self.assertEqual(1, len(got.findings))


class DeterministicAndBounded(unittest.TestCase):

    FILES = {
        'tests/integration/b.md': declaring('src/b.py'),
        'tests/integration/a.md': declaring('src/a.py'),
        'tests/integration/c.md': declaring('src/c.py'),
    }

    def test_the_same_corpus_gives_the_same_scan_twice_in_the_same_order(self):
        with Corpus(self.FILES) as corpus:
            first = declares.scan(rule(), corpus.tracked, corpus.root)
            second = declares.scan(rule(), list(reversed(corpus.tracked)),
                                   corpus.root)
        self.assertEqual(first, second)
        self.assertEqual(('a', 'b', 'c'),
                         tuple(d.stem for d in first.declarations),
                         'sorted here rather than trusted to arrive ordered — '
                         "`git ls-files`'s order is git's business")

    def test_two_files_declaring_one_path_resolve_to_the_first(self):
        files = {'tests/integration/b.md': declaring('src/shared.py'),
                 'tests/integration/a.md': declaring('src/shared.py')}
        with Corpus(files) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertEqual('make scenario NAME=a',
                         declares.resolve([got], rule(), 'src/shared.py'))


class TheScannerDoesNotSpawn(unittest.TestCase):
    """Adversarial against the docstring: no subprocess, and it does not walk."""

    SPAWN = frozenset({
        'run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen',
        'getoutput', 'getstatusoutput', 'fork', 'execv', 'execvp', 'spawnv',
    })
    ENUMERATE = frozenset({'glob', 'rglob', 'iterdir', 'walk', 'scandir',
                           'listdir'})
    ALLOWED_IMPORTS = frozenset({
        'dataclasses', 'pathlib', 'typing', 'agentic_sdlc.core',
        'agentic_sdlc.repo.verify.rules', 'agentic_sdlc.repo.verify.select'})

    def _tree(self) -> ast.Module:
        return ast.parse(DECLARES_SOURCE.read_text(encoding='utf-8'))

    def test_it_imports_nothing_that_could_spawn(self):
        imported = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module != '__future__':
                imported.add(node.module or '')
        self.assertEqual(set(), imported - self.ALLOWED_IMPORTS)

    def test_it_calls_nothing_that_spawns_or_enumerates(self):
        offenders = []
        for node in ast.walk(self._tree()):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else '')
            if name in self.SPAWN | self.ENUMERATE:
                offenders.append(f'{name} at line {node.lineno}')
        self.assertEqual([], offenders,
                         'the audit measured pm-shape-scan spending 34.8 s on '
                         'four spawns per file across 683 files; that defect '
                         'is why this feature exists')

    def test_a_scanned_file_is_read_once(self):
        # `stat` bounds it and one `read_bytes` follows. Counted from the AST
        # rather than by patching, because a second read added later would be a
        # second read whatever a mock said about this corpus.
        source = DECLARES_SOURCE.read_text(encoding='utf-8')
        self.assertEqual(1, source.count('.read_bytes()'))
        self.assertEqual(0, source.count('.read_text('))


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
