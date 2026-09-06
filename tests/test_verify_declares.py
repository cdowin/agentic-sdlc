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

`declares.py`'s "spawns nothing, walks nothing" claim is held structurally in
`test_verify_rules.py`, once for the three pure modules of this family.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic_sdlc.repo.verify import declares, rules

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

    def test_a_changed_path_selects_the_declaring_files_run_and_nothing_else(self):
        with Corpus(self.FILES) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(2, got.scanned,
                             'the scan glob is tests/integration/**')
            self.assertEqual(1, got.declaring)
            self.assertEqual((), got.findings)
            found = got.declarations[0]
            self.assertEqual(('checkout', 'make scenario NAME=checkout'),
                             (found.stem, found.command))
            # A path the header names resolves to that file's run; one it does
            # not name resolves to None, so the caller folds it into `missed`
            # rather than a rule "handling" it.
            self.assertEqual('make scenario NAME=checkout',
                             declares.resolve([got], rule(),
                                              'src/agentic_sdlc/repo/pm/report.py'))
            self.assertIsNone(declares.resolve([got], rule(), 'README.md'))

    def test_a_declared_directory_covers_under_it_and_not_beside_it(self):
        files = {'tests/integration/s.md': declaring('src/a'),
                 'src/a/b.py': 'x\n', 'src/ab.py': 'x\n'}
        with Corpus(files) as corpus:
            found = declares.scan(rule(), corpus.tracked,
                                  corpus.root).declarations[0]
            self.assertTrue(found.covers_path('src/a/b.py'))
            self.assertTrue(found.covers_path('src/a'))
            self.assertFalse(found.covers_path('src/ab.py'),
                             'a prefix that is not segment-bounded is the '
                             'off-by-one that silently over-selects')
            self.assertFalse(found.covers_path('src/abc/d.py'))


class TheZeroCensus(unittest.TestCase):
    """Rule 4's read side. Two distinct zeros, and neither may read as a pass."""

    def test_the_two_zeros_are_reported_separately_and_stay_distinguishable(self):
        files = {f'tests/integration/f{n}.md': f'# nothing here {n}\n'
                 for n in range(4)}
        with Corpus(files) as corpus:
            # Files found, none declaring: a corpus that drifted away from the
            # rule reading it. The QUIETER of the two.
            drifted = declares.scan(rule(), corpus.tracked, corpus.root)
            # The glob matched no tracked file at all: a rule pointed at a
            # directory that was renamed away rots into a rule that quietly
            # matches nothing, forever.
            absent = declares.scan(rule(scan='tests/renamed_away/**'),
                                   corpus.tracked, corpus.root)
        self.assertEqual((4, 0), (drifted.scanned, drifted.declaring))
        self.assertEqual((False, True), (drifted.empty_scan, drifted.empty_corpus))
        self.assertEqual((0, 0), (absent.scanned, absent.declaring))
        self.assertEqual((True, False), (absent.empty_scan, absent.empty_corpus))


class TheHeaderIsLiteralAndStartsTheLine(unittest.TestCase):

    def test_a_declares_that_looks_like_a_regex_matches_only_itself(self):
        # `rules.py` stores `declares` verbatim; nothing here compiles it. A
        # compiled one claims files it was never pointed at, which is an
        # over-selection nobody would look for.
        files = {'tests/integration/a.md': '## coversXYZ: src/a.py\n',
                 'tests/integration/b.md': '## covers.*: src/b.py\n'}
        with Corpus(files) as corpus:
            got = declares.scan(rule(declares='## covers.*:'),
                                corpus.tracked, corpus.root)
        self.assertEqual((2, 1), (got.scanned, got.declaring),
                         'a literal prefix matches `## covers.*:` and NOT '
                         '`## coversXYZ:` — if it matched both, the value was '
                         'compiled as a pattern')
        self.assertEqual('b', got.declarations[0].stem)

    def test_the_prefix_must_start_the_line(self):
        files = {'tests/integration/a.md': f'   {HEADER} src/a.py\n',
                 'tests/integration/b.md': f'see {HEADER} src/b.py\n'}
        with Corpus(files) as corpus:
            self.assertEqual(0, declares.scan(rule(), corpus.tracked,
                                              corpus.root).declaring)


class AFencedExampleIsNotADeclaration(unittest.TestCase):
    """Documentation showing the syntax is not a claim about coverage."""

    def test_a_fenced_header_is_not_read_and_a_real_one_beside_it_still_is(self):
        fenced = ('# How to declare coverage\n\n```\n'
                  f'{HEADER} src/example.py\n```\n\nprose\n')
        with Corpus({'tests/integration/doc.md': fenced}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual((1, 0), (got.scanned, got.declaring))
            self.assertEqual((), got.findings)
        both = f'{HEADER} src/real.py\n\n```\n{HEADER} src/example.py\n```\n'
        with Corpus({'tests/integration/doc.md': both}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            self.assertEqual(1, got.declaring)
            self.assertEqual(('src/real.py',), got.declarations[0].covers)

    def test_an_unterminated_fence_is_reported_not_left_to_mask(self):
        with Corpus({'tests/integration/doc.md':
                     f'```\n{HEADER} src/example.py\n'}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertTrue(any('never closes' in f for f in got.findings),
                        'a checker cannot both skip a region and claim it '
                        'scanned the file')


class HeaderFindings(unittest.TestCase):
    """Each is a finding naming the file, and the declaration is dropped whole."""

    def _scan(self, body) -> declares.Scan:
        with Corpus({'tests/integration/s.md': body}) as corpus:
            return declares.scan(rule(), corpus.tracked, corpus.root)

    def test_a_header_this_parser_cannot_use_is_a_finding_never_a_declaration(self):
        cases = {
            # A header somebody meant to fill is not an empty coverage set.
            'lists nothing': (f'{HEADER}\n', 'meant to fill'),
            # Which one wins is not a thing this parser may pick.
            'declared twice': (f'{HEADER} src/a.py\nx\n{HEADER} src/b.py\n',
                               'lines 1, 3'),
            'a header line past the cap': (f'{HEADER} ' + 'a/b.py ' * 2000
                                           + '\n', 'header line is'),
            'a file past the cap': (f'{HEADER} src/a.py\n'
                                    + 'x' * (declares.MAX_FILE + 1) + '\n',
                                    'NOT read'),
            'a declaration that is a manifest': (
                f'{HEADER} ' + ' '.join(f'src/f{n}.py' for n in
                                        range(declares.MAX_COVERS + 1)) + '\n',
                'manifest'),
        }
        for label, (body, fragment) in cases.items():
            with self.subTest(case=label):
                got = self._scan(body)
                self.assertEqual(0, got.declaring)
                self.assertEqual(1, len(got.findings))
                self.assertIn('s.md', got.findings[0])
                self.assertIn(fragment, got.findings[0])

    def test_a_file_that_is_not_utf8_is_reported_by_path_never_skipped(self):
        # A file quietly dropped from a scan is a file nobody knows went unread,
        # and `scanned` would still count it.
        with Corpus({'tests/integration/s.md': b'\xff\xfe\x00bad\n'}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertEqual((1, 0), (got.scanned, got.declaring))
        self.assertTrue(any('not UTF-8' in f for f in got.findings))


class TheCoveredPathRefusalMatrix(unittest.TestCase):
    """The header is written by whoever wrote the test. It is untrusted input."""

    STRUCTURAL = ('../../etc/passwd', '/etc/passwd', '.', '..', 'a//b',
                  'a/./b', 'a/b/', '<name>')

    def test_a_covered_value_that_is_not_a_relative_path_is_a_finding(self):
        # The character bans are enumerated from the constant: a character
        # dropped from it is a covered path that is a shell fragment, one
        # refactor from a command line. The structural spellings are the ones
        # no character ban would catch.
        self.assertEqual(set(';|&$`()<>#\\~:\'" '),
                         set(declares.COVER_FORBIDDEN))
        # A SPACE is in the set but unreachable through a header: the line is
        # whitespace-separated, so `a b` arrives as two covered paths. It is in
        # the set because the set is also what a value must survive to reach a
        # command line.
        spellings = [f'a{char}b'
                     for char in sorted(declares.COVER_FORBIDDEN - {' '})]
        for covered in (*self.STRUCTURAL, *spellings):
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
        # The tree, not the config, is where a filename like this comes from,
        # and `<stem>` is substituted into a command line.
        with Corpus({'tests/integration/a b.md':
                     f'{HEADER} src/a.py\n'}) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
        self.assertEqual(0, got.declaring)
        self.assertEqual(1, len(got.findings))


class DeterministicAndFirstDeclarerWins(unittest.TestCase):

    def test_the_scan_is_sorted_and_two_files_declaring_one_path_run_once(self):
        files = {'tests/integration/c.md': declaring('src/c.py'),
                 'tests/integration/b.md': declaring('src/shared.py'),
                 'tests/integration/a.md': declaring('src/shared.py')}
        with Corpus(files) as corpus:
            got = declares.scan(rule(), corpus.tracked, corpus.root)
            reversed_input = declares.scan(rule(),
                                           list(reversed(corpus.tracked)),
                                           corpus.root)
        self.assertEqual(got, reversed_input,
                         "sorted here rather than trusted to arrive ordered — "
                         "`git ls-files`'s order is git's business")
        self.assertEqual(('a', 'b', 'c'),
                         tuple(d.stem for d in got.declarations))
        self.assertEqual('make scenario NAME=a',
                         declares.resolve([got], rule(), 'src/shared.py'),
                         'first declaring file wins — two files declaring one '
                         'path must not run twice')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
