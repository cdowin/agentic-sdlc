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
PYTHON = ([SRC / 'cli.py']
          + sorted((SRC / 'core').glob('*.py'))
          + sorted((SRC / 'repo' / 'checks').glob('*.py'))
          + [SRC / 'repo' / 'install.py', SRC / 'repo' / 'init.py',
             SRC / 'repo' / 'gates_extra.py'])
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


def test_comments_and_docstrings_are_under_a_third_of_the_code():
    assert len(PYTHON) > 10, 'the census lost its modules'
    prose = code = 0
    for path in PYTHON:
        p, c = prose_and_code(path)
        prose += p
        code += c
    assert code > 0
    assert prose / code < PYTHON_CEILING, (
        f'{prose} prose lines against {code} code lines ({prose / code:.2f}) '
        f'across {len(PYTHON)} modules; a docstring says what, a comment says why')


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
