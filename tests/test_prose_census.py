"""Prose is the weight: comments and docstrings against code, with a ceiling.

No existing case covers this because nothing measured prose before; the nearest
census, test_shell_mark.py, counts spawns. The Python list is the modules this
story trimmed; the orchestrator widens it to all of `src/` once every prose
branch has merged.
"""
from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src' / 'agentic_sdlc'
INSTALLABLES = SRC / 'repo' / 'installables'
PYTHON = sorted(SRC.rglob('*.py'))
PYTHON_CEILING = 1 / 3
SHELL_CEILING = 0.20


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


def published_docstrings() -> dict[Path, int]:
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
    """
    from test_cli_surface import help_corpus
    printed = [text for _, text in help_corpus().values()]
    published: dict[Path, int] = {}
    for path in PYTHON:
        doc = ast.get_docstring(
            ast.parse(path.read_text(encoding='utf-8')), clean=False)
        if doc and any(doc.strip() in text for text in printed):
            published[path] = doc.count('\n') + 1
    return published


def census() -> tuple[int, int, int]:
    """(prose, code, published) over `src/`, with published counted as code."""
    published = published_docstrings()
    prose = code = 0
    for path in PYTHON:
        p, c = prose_and_code(path)
        moved = published.get(path, 0)
        prose += p - moved
        code += c + moved
    return prose, code, sum(published.values())


def test_comments_and_docstrings_are_under_a_third_of_the_code():
    assert len(PYTHON) > 10, 'the census lost its modules'
    published = published_docstrings()
    # Rule 4: a census that excluded NOTHING would have quietly become the old
    # measurement, and a census that excluded EVERYTHING would pass over any
    # amount of prose. Both are the exclusion failing open.
    assert published, (
        'no module docstring reached a `--help` surface — the exclusion '
        'derived nothing, so this is measuring something else now')
    prose, code, moved = census()
    assert code > 0
    assert moved < prose, (
        f'{moved} published line(s) against {prose} of prose — the exclusion '
        f'is most of the census and has stopped being an exclusion')
    assert prose / code < PYTHON_CEILING, (
        f'{prose} prose lines against {code} code lines ({prose / code:.2f}) '
        f'across {len(PYTHON)} modules, {moved} line(s) of published `--help` '
        f'counted as the output they are; a docstring says what, a comment '
        f'says why')


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
    """
    prose, code, _ = census()
    sizes = sorted(sum(prose_and_code(path)) for path in PYTHON)
    typical = sizes[len(sizes) // 2]
    added_prose = round(typical * (prose / (prose + code)))
    ratio = (prose + added_prose) / (code + typical - added_prose)
    assert ratio < PYTHON_CEILING, (
        f'a median module ({typical} lines) documented at this repo\'s own '
        f'rate lands the census at {ratio:.4f}, over {PYTHON_CEILING:.4f}. '
        f'There is no room to write a new file, so the next feature pays for '
        f'itself out of somebody else\'s comments')


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
