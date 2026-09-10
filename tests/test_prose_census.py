"""Prose is the weight: comments and docstrings against code, per ROOT.

Two roots, counted the same way and judged differently. `src/` is GRADED against
`PYTHON_CEILING`; `tests/` is REPORTED and nothing else, until
`st-the-tests-ceiling-is-declared-and-argued` sets its number from the suite
left after the rot is out. A root with no ceiling PASSING is the design rather
than an oversight, and `test_which_roots_are_graded_and_which_are_only_reported`
says which is which by name — so the next ceiling has to be declared instead of
inherited from the root that already had one.

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

    `ceiling` of None is rule 11's named absence here — a root that is measured
    and reported and NOT graded. `publishes_help` is 0.6.0/D7's exclusion, which
    is `src/`-shaped; `published_docstrings` says why it does not transfer.
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
    Root(name='tests', path=TESTS, floor=40, ceiling=None,
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
    """(comment + docstring lines, code lines) for one Python module."""
    source = path.read_text(encoding='utf-8')
    lines = source.splitlines()
    comments = sum(1 for tok in tokenize.generate_tokens(io.StringIO(source).readline)
                   if tok.type == tokenize.COMMENT)
    docstrings = sum(
        ast.get_docstring(node, clean=False).count('\n') + 1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef))
        and ast.get_docstring(node))
    blank = sum(1 for line in lines if not line.strip())
    prose = comments + docstrings
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
               'NO CEILING — reported, not graded '
               '(st-the-tests-ceiling-is-declared-and-argued)')
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
    """The absence with a name on it: `tests/` has no ceiling ON PURPOSE.

    Silence would leave two readings of one green run — the root is under its
    ceiling, or nobody ever set one — and rule 11 is that the second gets said
    out loud. It fails in BOTH directions, like `test_guard_corpus.UNCOVERED`:
    a census that grades no root passes over anything, and a `tests/` that has
    quietly gained a ceiling is the number this story deliberately did not set,
    arriving without the argument story 8 owes it.
    """
    graded = {root.name for root in ROOTS if root.ceiling is not None}
    ungraded = {root.name for root in ROOTS if root.ceiling is None}
    assert graded, (
        'no root has a ceiling, so this census reports and grades nothing — '
        'it passes over any amount of prose in either tree')
    assert ungraded, (
        'every root is graded now, so the named absence this case exists for '
        'is gone: delete it in the commit that lands `tests/`\'s ceiling, with '
        'the argument for the number beside it')
    assert not graded & ungraded
    assert graded | ungraded == {root.name for root in ROOTS}
    assert 'tests' in ungraded, (
        '`tests/` has a ceiling. This story measured it and set none; '
        'st-the-tests-ceiling-is-declared-and-argued sets it from the suite '
        'after the rot is out, and not at `src/`\'s number')
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

    Measured at the repo's OWN average, so it cannot be satisfied by picking a
    flattering module: a new file the size of the median one, documented the way
    this package documents, has to fit. When it does not, the ceiling has become
    a growth gate wearing a quality gate's clothes — which is the defect, and
    trimming somebody else's reasoning to clear it is what the milestone brief
    forbids by name.

    GRADED ROOTS ONLY, which today is `src/` alone: headroom is a fact about a
    ceiling, and a root that has none has all of it.
    """
    for root in (root for root in ROOTS if root.graded):
        prose, code, _ = census(root)
        sizes = sorted(sum(prose_and_code(path)) for path in modules(root).paths)
        typical = sizes[len(sizes) // 2]
        added_prose = round(typical * (prose / (prose + code)))
        ratio = (prose + added_prose) / (code + typical - added_prose)
        assert ratio < root.ceiling, (
            f'a median {root.name} module ({typical} lines) documented at this '
            f'repo\'s own rate lands the census at {ratio:.4f}, over '
            f'{root.ceiling:.4f}. There is no room to write a new file, so the '
            f'next feature pays for itself out of somebody else\'s comments')


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
