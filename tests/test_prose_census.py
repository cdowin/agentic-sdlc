"""Prose is the weight: comments and docstrings against code, per ROOT.

Two roots, counted the same way and graded at their own numbers: `src/` against
`PYTHON_CEILING`, `tests/` against `TESTS_CEILING`, each constant carrying the
argument for its value beside it. A root that arrives with no ceiling is
reported and NOT graded, which
`test_which_roots_are_graded_and_which_are_only_reported` fails on by name — so
the next number has to be declared instead of inherited from a root that already
had one.

Both roots' numbers land on the transcript of every run, green or red;
`_announce` carries the measurement of why that is a warning and not a `print`.
"""
from __future__ import annotations

import ast
import functools
import io
import tokenize
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import NamedTuple

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src' / 'agentic_sdlc'
TESTS = ROOT / 'tests'
INSTALLABLES = SRC / 'repo' / 'installables'
PYTHON_CEILING = 1 / 3

# --- THE `tests/` CEILING, and it is a number somebody had to ARGUE -----------
# `src/` has been graded since 0.2.0; `tests/` was measured and NOT graded until
# this line, and the gap is the whole reason this block exists. A ceiling copied
# from `src/` would have repeated 0.6.0's eight-round census fight with the
# economics reversed, so the number below is DERIVED from the suite that remains
# after the rot came out, and the derivation is written down rather than recalled.
#
# SET 2026-09-11, at st-the-tests-ceiling-is-declared-and-argued, and this is
# that argument.
#
#   THE MEASUREMENT, 2026-09-11: 11,328 prose lines against 22,186 of code over
#   63 modules — ratio 0.5106. RE-DERIVED after
#   bg-the-prose-census-subtracts-a-docstrings-blank-lines-twice: the first
#   reading of this block said 0.5267, off a census that subtracted a
#   docstring's blank lines twice and understated code on both roots. Two sibling stories were landing code in the same
#   tree that day, so the figure a run prints will differ in the third decimal;
#   it is the TRANSCRIPT that is authoritative, not this paragraph, because
#   `_announce` puts both roots on every run, green or red. The cut that preceded
#   it took 161 prose lines (1,703 words) out of 12 modules and put 68 back as
#   this argument. It came FIRST, and the number is read off what was left.
#   Nothing under `src/` paid for it.
#
#   THE DERIVATION, so anybody can re-run it: the measured ratio, rounded UP to
#   the next twentieth. 0.5106 -> 0.55. That is 7.7% of relative headroom and
#   874 prose lines of room at today's code size — more than a median module's
#   117, which is what
#   `test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling` asserts
#   for both roots and `bg-the-prose-ceiling-has-no-headroom` is the reason for.
#   `src/` carries 5.6% over its own measurement, which is the same order.
#
#   IT IS NOT `src/`'s THIRD, AND THAT IS STATED RATHER THAN SATISFIED. At 1/3
#   the suite is 53% over on the day it was declared, and the only way green is
#   deleting 3,933 lines of English nobody reviewed — a growth gate wearing a
#   quality gate's clothes, which the milestone brief forbids by name.
#   Three measurements say the two roots are not the same artefact:
#
#     * 0.6.0/D7 MOVES 223 `src/` docstring lines into `code` because `main()`
#       prints them as `--help`. Nothing under `tests/` is ever printed — pytest
#       is a test docstring's only reader — so the exclusion is legitimately
#       empty here and the like-for-like `src/` number is 0.3362, not 0.3157.
#       The argument does not transfer, and `published_docstrings` says so on
#       the `Root` rather than leaving it to be discovered.
#     * the suite is 1.49 lines of test code per line of source, and the prose
#       that documents it is per CASE — 1,595 collected against 47 source
#       modules — where `src/`'s is per function.
#     * the modules carrying the most prose are the AST-shaped guards, where the
#       comment IS the rule being enforced (`test_boundaries.py`, 717 prose
#       lines, measured and kept whole).
#
#   WHAT WAS REJECTED: a `[prose]` section in `devkit.toml`. Hard rule 5 splits
#   on it — a GATE key ships a stock default so a repo with no `devkit.toml`
#   behaves byte-identically to one declaring it, and `test_config_seed.py`
#   compares the seed key by key. This module is THIS repo's own test, not a
#   shipped gate, so the key would stand behind nothing in every consumer's
#   tree. The ceiling is a module constant for the same reason `PYTHON_CEILING`
#   is one.
#
# Re-set at a close, once, with a reason — never raised to absorb a commit.
TESTS_CEILING = 0.55

SHELL_CEILING = 0.20

# `tests/fixtures/` is INPUT, not content this repo maintains: purpose-built
# repos, hook payloads and transcripts the suite READS. It holds no `.py` today,
# so this filter removes NOTHING — which is exactly why it goes through
# `Walk.filter` rather than a comprehension. The walk records what it took out
# and the report line renders it, so the day a vendored `.py` arrives the count
# says it narrowed instead of just being smaller.
VENDORED = 'fixtures'


@dataclass(frozen=True)
class Root:
    """One census root: what it counts, what it drops, and how it is judged.

    Both roots are GRADED since st-the-tests-ceiling-is-declared-and-argued, so
    a `ceiling` of None is a root that arrived without a number — measured,
    reported, and failing `test_which_roots_are_graded_and_which_are_only_reported`
    until somebody argues one. `publishes_help` is 0.6.0/D7's exclusion, which is
    `src/`-shaped; `published_docstrings` says why it does not transfer.
    """

    name: str
    path: Path
    floor: int
    ceiling: float | None
    excluded: tuple[str, ...] = ()
    publishes_help: bool = False

    @property
    def graded(self) -> bool:
        return self.ceiling is not None


# The floors are in the spirit of `test_boundaries.MIN_SOURCES` (20, over the
# same 47 modules): well under what is really there, well over zero. Each root
# gets its OWN, because one number for two roots is a floor the smaller root can
# satisfy on the larger one's behalf.
ROOTS = (
    Root(name='src', path=SRC, floor=20, ceiling=PYTHON_CEILING,
         publishes_help=True),
    Root(name='tests', path=TESTS, floor=40, ceiling=TESTS_CEILING,
         excluded=(VENDORED,)),
)


class Modules(NamedTuple):
    """One root's census population, and the line disclosing how it narrowed."""

    paths: tuple[Path, ...]
    disclosed: str


@functools.cache
def modules(root: Root) -> Modules:
    """Every module in one root's census, enumerated through `core.walk`.

    Not `rglob`, for `test_boundaries._sources`'s reason — *a test that
    hand-rolled its own `rglob` to police `rglob` would be the joke that writes
    itself* — and a second root would have doubled the hand-roll. The walk pays
    for itself twice over here: `Walk.filter` records a narrowing under a named
    reason and `Walk.census` renders it, so `root.excluded` cannot shrink a
    count without saying so on the report line.

    The FLOOR lives here, at the one place every caller goes through, so no
    caller can be satisfied by having scanned nothing: a moved or emptied root
    otherwise reports a ratio over an empty tree and passes.
    """
    from agentic_sdlc.core import walk as walkmod
    from agentic_sdlc.core.walk import Kind, SkipReason
    found = walkmod.descendants(root.path, Kind.FILE, suffix='.py')
    found = found.filter(
        lambda path: not set(path.relative_to(root.path).parts) & set(root.excluded),
        SkipReason.EXCLUDED_PATH)
    assert len(found.kept) >= root.floor, (
        f'{len(found.kept)} module(s) under {root.path} — the `{root.name}` '
        f'census expects at least {root.floor}. A root that MOVED reports a '
        f'ratio over an empty tree, which is rule 4\'s first cardinal sin '
        f'wearing a percentage.')
    return Modules(found.kept, found.census('module(s)'))


def prose_and_code(path: Path) -> tuple[int, int]:
    """(comment + docstring lines, code lines) for one Python module.

    A PARTITION over line numbers, not three independent sums, and that is the
    whole of `bg-the-prose-census-subtracts-a-docstrings-blank-lines-twice`. The
    old form returned `prose, total - blank - prose`, and a blank line INSIDE a
    docstring is in both subtrahends — `count('\\n') + 1` spans it and
    `not line.strip()` matches it — so it came off twice and `code` was
    understated. A five-line module whose docstring holds one blank line and
    whose only statement is `x = 1` reported `code=0`; deleting 29 docstring
    lines from a real module moved its code count 339 UP to 343.

    Every ratio quoted against this was therefore overstated on both roots —
    conservatively, so the gate was stricter than it claimed and nothing shipped
    that the honest number would have caught.

    A line carrying code AND a trailing comment stays PROSE, which is what the
    old arithmetic did too: that is a judgement about which half of a mixed line
    counts, not the overlap this fixes, and moving it is a different argument.
    """
    source = path.read_text(encoding='utf-8')
    # `split('\n')`, never `splitlines()`, for `core/frontmatter._split`'s
    # reason one root over: `splitlines()` also breaks on U+2028, U+2029, form
    # feed and \x1c-\x1e, while `tokenize` and `ast` break only on a newline.
    # After the first such character every later line number SHIFTS, so the
    # partition below misattributes blanks and docstring lines for the rest of
    # the file — fail-OPEN, overstating code. Three modules here hold four of
    # them, because they are fixtures for a line-separator bug (0.7.0 review M2).
    # `read_text` has already normalised \r\n and \r, so a newline is the only
    # separator left; a trailing '' from a final newline is not a line.
    lines = source.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    prose_lines: set[int] = {
        tok.start[0]
        for tok in tokenize.generate_tokens(io.StringIO(source).readline)
        if tok.type == tokenize.COMMENT}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not ast.get_docstring(node):
            continue
        doc = node.body[0]
        prose_lines.update(range(doc.lineno, (doc.end_lineno or doc.lineno) + 1))
    blank = sum(1 for n, line in enumerate(lines, start=1)
                if not line.strip() and n not in prose_lines)
    prose = len(prose_lines)
    return prose, len(lines) - blank - prose


def published_docstrings(root: Root) -> dict[Path, int]:
    """{module: docstring lines} for every module docstring that IS `--help`.

    A docstring `main()` prints verbatim is the program's OUTPUT, not a comment
    about it — rule 6 makes an output line shape contract, and the identical
    text moved into a `USAGE` constant already counts as CODE here, because a
    string assignment is code. Two spellings of one thing, graded opposite ways
    (0.6.0/D7).

    DERIVED by running every `--help` this package prints and asking which
    docstrings came back, so a check that starts or stops publishing its own
    joins or leaves this the day it does. A roster would be the second
    scoreboard, and it would drift toward whatever made the number work.

    THE ARGUMENT DOES NOT TRANSFER TO A SECOND ROOT, and that is declared on the
    Root rather than discovered. Nothing under `tests/` is ever printed as
    `--help` — pytest is the only reader a test docstring has — so a root that
    does not publish gets an empty exclusion as the CORRECT answer, where for
    `src/` an empty one means the derivation went blind. Same value, opposite
    meaning: the two rule-4 guards below run only where it can lie.
    """
    if not root.publishes_help:
        return {}
    from test_cli_surface import help_corpus
    printed = [text for _, text in help_corpus().values()]
    published: dict[Path, int] = {}
    for path in modules(root).paths:
        doc = ast.get_docstring(
            ast.parse(path.read_text(encoding='utf-8')), clean=False)
        if doc and any(doc.strip() in text for text in printed):
            published[path] = doc.count('\n') + 1
    return published


@functools.cache
def census(root: Root) -> tuple[int, int, int]:
    """(prose, code, published) over one root, with published counted as code.

    Cached for `conftest.module_spawns`'s reason: three cases below ask for the
    same numbers, the two roots are 35k lines of `tokenize` and `ast.parse`
    between them, and a file does not change under a running session.
    """
    published = published_docstrings(root)
    prose = code = 0
    for path in modules(root).paths:
        p, c = prose_and_code(path)
        moved = published.get(path, 0)
        prose += p - moved
        code += c + moved
    return prose, code, sum(published.values())


def report(root: Root) -> str:
    """One root's census as one line: modules, code, prose, ratio, verdict."""
    prose, code, moved = census(root)
    verdict = (f'ceiling {root.ceiling:.4f}' if root.graded else
               'NO CEILING — reported, not graded, and no argument for a '
               'number: declare one beside PYTHON_CEILING')
    return (f'{root.name + "/":7} {modules(root).disclosed:32} {code:6,} code  '
            f'{prose:6,} prose  ratio {prose / code:.4f}  '
            f'{moved:,} published --help line(s) as code  {verdict}')


class CensusLine(UserWarning):
    """One root's numbers, on the transcript of a run that PASSED."""


def _announce(root: Root) -> None:
    """Put one root's census where a green run will show it.

    MEASURED on this suite's own runner rather than assumed: under `make unit`'s
    `-n auto`, a `print`, a `sys.stderr.write`, a `capsys.disabled()` block and
    the config's own terminal writer are ALL discarded from a passing test —
    xdist ships a worker's captured streams back only for a failure. The
    warnings summary is the one channel pytest renders either way, so it is the
    one that gets the number. The alternative is a number that exists only
    inside an assertion message, which fires after somebody has already lost.
    """
    warnings.warn(report(root), CensusLine, stacklevel=2)


@pytest.mark.parametrize('root', ROOTS, ids=lambda root: root.name)
def test_comments_and_docstrings_are_under_a_third_of_the_code(root: Root):
    _announce(root)
    prose, code, moved = census(root)
    assert code > 0
    if root.publishes_help:
        # Rule 4: an exclusion that derived NOTHING would have quietly become
        # the old measurement, and one that derived EVERYTHING would pass over
        # any amount of prose. Both are it failing open — and both are readable
        # only on a root that HAS a help surface. Over `tests/`, where empty is
        # the right answer, the first fails a correct census outright and the
        # second is trivially true against every line of prose in the tree,
        # which is a guard that grades nothing wearing a guard's clothes.
        assert published_docstrings(root), (
            'no module docstring reached a `--help` surface — the exclusion '
            'derived nothing, so this is measuring something else now')
        assert moved < prose, (
            f'{moved} published line(s) against {prose} of prose — the '
            f'exclusion is most of the census and has stopped being one')
    if root.graded:
        assert prose / code < root.ceiling, (
            f'{report(root)}; a docstring says what, a comment says why')


def test_which_roots_are_graded_and_which_are_only_reported():
    """Every root carries a NUMBER, and the answer is said out loud.

    The case the previous story wrote named the opposite absence — `tests/` had
    no ceiling on purpose — and its message said to delete it in the commit that
    lands one. It is AMENDED instead, because the hole the deletion would leave
    is the one rule 11 is about: with nothing asserting that every root is
    graded, a third root could arrive at `ceiling=None`, report `NO CEILING` on
    a green transcript, and pass over any amount of prose. The subject moved
    from "which root is ungraded" to "no root is", which is the same question
    with the tree's new answer.

    Still both directions, like `test_guard_corpus.UNCOVERED`: a root that loses
    its number fails here, and so does a roster that shrank to nothing to make
    the first clause true. The two ceilings must also DIFFER — `tests/` at
    `src/`'s third is the inherited number this census refused to set by
    copying, and the argument for the value it did set is beside
    `TESTS_CEILING`.
    """
    graded = {root.name for root in ROOTS if root.ceiling is not None}
    ungraded = {root.name for root in ROOTS if root.ceiling is None}
    assert len(ROOTS) >= 2, (
        'the census is down to one root, so "every root is graded" is a claim '
        'about almost nothing — a root was dropped rather than regraded')
    assert not ungraded, (
        f'{sorted(ungraded)} are measured and NOT graded. A root with no '
        f'ceiling passes over any amount of prose: declare a number beside '
        f'TESTS_CEILING with the argument for it, the way that one is')
    assert graded == {root.name for root in ROOTS}
    assert not graded & ungraded
    at = {root.name: root.ceiling for root in ROOTS}
    assert at['tests'] != at['src'], (
        f'both roots are graded at {at["src"]:.4f}, so one number was inherited '
        f'rather than argued — a test docstring and a source docstring are not '
        f'the same artefact (0.6.0/D7, and the block beside TESTS_CEILING). '
        f'Asked of the ROSTER, not of the two constants: a `Root` handed '
        f'PYTHON_CEILING is the same defect spelled the other way')
    assert {root.name for root in ROOTS if root.publishes_help} == {'src'}, (
        'the published-`--help` exclusion is 0.6.0/D7 and it is `src/`-shaped: '
        'a root whose docstrings nothing prints must not run the two rule-4 '
        'guards, because a legitimately empty exclusion trips the first')


def test_a_moved_or_empty_root_fails_instead_of_passing_over_nothing(tmp_path):
    """The floor, watched failing — `test_boundaries::TheCensusIsTheRealTree`
    one census over. Every root, because a floor only one root can reach is a
    floor the other one has not got."""
    for root in ROOTS:
        with pytest.raises(AssertionError,
                           match=f'the `{root.name}` census expects at least'):
            modules(replace(root, path=tmp_path))


def test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling():
    """`bg-the-prose-ceiling-has-no-headroom`'s own verification clause.

    > a feature that adds a well-documented module must go green without any
    > comment in any OTHER file changing.

    Measured in ABSOLUTE prose lines — the room under the ceiling at today's code
    size, against what a median module actually carries. When there is less, the
    ceiling has become a growth gate wearing a quality gate's clothes, and
    trimming somebody else's reasoning to clear it is what the milestone brief
    forbids by name.

    **The first form of this case could not fail, and 0.7.0's feature review
    proved it twice.** It added a module whose prose share was the repo's OWN
    fraction `f = p/(p+c)`, so `(p+tf)/(c+t(1-f))` reduces to exactly `p/c` —
    the main ceiling assertion, restated. Independent power: one prose line out
    of 830 on `tests/`, zero on `src/`. At a ceiling leaving 2.6 lines of room
    in the whole suite it was still green. Rule 4's first sin, inside the census
    that exists to measure it.

    BOTH ROOTS, since `tests/` gained its number: the clause generalises
    unchanged, and a ceiling with no room to write a new test module is the same
    growth gate one root over. It runs on GRADED roots because headroom is a
    fact about a ceiling, and a root that has none has all of it.
    """
    for root in (root for root in ROOTS if root.graded):
        prose, code, _ = census(root)
        per_module = sorted(prose_and_code(path)[0]
                            for path in modules(root).paths)
        typical = per_module[len(per_module) // 2]
        slack = root.ceiling * code - prose
        assert slack >= typical, (
            f'{root.name} has {slack:.0f} prose line(s) of room under its '
            f'{root.ceiling:.4f} ceiling and a median module carries {typical}. '
            f'There is no room to write a new file, so the next feature pays '
            f'for itself out of somebody else\'s comments')


def test_the_shell_installables_are_under_a_fifth_comment_lines():
    """The story's bar, measured the way it was set: comment lines over every
    line of every shipped script, in aggregate — a ten-line header on a
    thirty-line script is not the essay this guards against."""
    lines = comments = 0
    for script in sorted(INSTALLABLES.glob('*.sh')):
        body = script.read_text(encoding='utf-8').splitlines()
        lines += len(body)
        comments += sum(1 for line in body
                        if line.lstrip().startswith('#') and not line.startswith('#!'))
    assert lines
    assert comments / lines < SHELL_CEILING, (
        f'{comments} comment lines against {lines} ({comments / lines:.2f}) '
        f'across the shell installables; a why is one sentence')
