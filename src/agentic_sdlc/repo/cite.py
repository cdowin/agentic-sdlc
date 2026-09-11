"""The rule-citation census: how many times each numbered rule is cited in this tree, and where.

The number a brief quotes, as a command's output. `ms-the-rule-reaches-the-work`
asserted *"roughly 600 citations, rule 4 alone 194"*; the tree said 1,107, then
1,151 four commits later, then 1,240 — and nobody could ask, so the wrong number
was quoted forward through three milestones
(`bg-the-brief-undercounts-the-coupling-it-argues-from`).

GENERAL OVER THE TREE THE CALLER STANDS IN, which is hard rule 8 and not an
accident of implementation: nothing here names a repo, a rule set or a file.
The universe is `git ls-files` from `repo_root()` — the same tree every gate in
this package reads — and the grammar is `rule <n>`, so a project whose rules are
numbered gets its own census and a project whose rules are not gets a census of
zero that SAYS so rather than a quiet PASS (rule 4).

It reports; it never grades. A rising citation count is what a rule being USED
looks like, so there is no ceiling here and no verdict word — only the count,
the sites, and what was scanned. Reads text, runs nothing, writes nothing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, Mapping, NamedTuple

from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.repo import vehicle

VERB = 'cite'
PREFIX = f'[{VERB}]'
HELP_WORDS = ('-h', '--help', 'help')
SITES_FLAG = '--sites'

# `\s+` rather than a literal space, because a citation WRAPS: six of this
# tree's own — `hard rule\n4` — are invisible to a line-based grep, which is
# one more reason the answer is a reader and not a one-liner in a brief.
CITATION = re.compile(r'(?i)\brule\s+([0-9]+)\b')

# The two row shapes, declared once and named in USAGE below in this order.
ROSTER_COLUMNS = ('rule', 'citations', 'files')
SITE_COLUMNS = ('rule', 'path', 'line', 'text')

# Why a tracked path was not read. A narrowing is never silent (rule 11): each
# one renders on the census line with its count, in this order.
UNREADABLE = 'not readable as text (binary, or gone from the worktree)'
SYMLINKED = 'symlink(s) NOT followed (a symlink may leave the checkout)'

USAGE = f"""usage: agentic-sdlc {VERB} [{SITES_FLAG}]

Counts every `rule <n>` in the tracked text of the tree you are standing in —
the census a brief quotes, so the number is read rather than remembered.

  (no flag)   one tab-separated row per RULE CITED, ascending by rule,
              columns IN ORDER:
                {'  '.join(ROSTER_COLUMNS)}
  {SITES_FLAG}     one tab-separated row per CITATION, in path order,
              columns IN ORDER:
                {'  '.join(SITE_COLUMNS)}
              `text` is the line the citation sits on, whitespace squeezed.

THE ROWS GO TO STDOUT and the census line to STDERR, so a pipe carries rows
only. There is no `--rule` flag and there will not be one: the rule is the
first COLUMN of both shapes, so one rule is a grep and a total is an awk
(rule 11 — composition is the shell's job).

THE GRAMMAR is `rule <n>`, case-insensitive, and the whitespace may be a line
break, so a wrapped `hard rule\\n4` counts where a line-based grep loses it.
It reports what matched and judges nothing: a citation of a rule your project
does not have is a row, not a finding (rule 9).

Exit codes: 0 the census read at least one file; 1 it read none, which is a
census of zero and never a pass; 2 usage."""


class Site(NamedTuple):
    """One citation, where it is, and the line it sits on."""
    rule: int
    path: str
    line: int
    text: str


def sites(sources: Mapping[str, str]) -> tuple[Site, ...]:
    """Every citation in `{path: text}`, in path order then position order."""
    found: list[Site] = []
    for path in sorted(sources):
        text = sources[path]
        lines = text.splitlines()
        for match in CITATION.finditer(text):
            at = text.count('\n', 0, match.start()) + 1
            row = lines[at - 1] if at <= len(lines) else ''
            found.append(Site(int(match.group(1)), path, at,
                              ' '.join(row.split())))
    return tuple(found)


def roster(found: Iterable[Site]) -> tuple[tuple[int, int, int], ...]:
    """`(rule, citations, files)` per rule cited, ascending by rule."""
    counts: dict[int, int] = {}
    files: dict[int, set[str]] = {}
    for site in found:
        counts[site.rule] = counts.get(site.rule, 0) + 1
        files.setdefault(site.rule, set()).add(site.path)
    return tuple((rule, counts[rule], len(files[rule]))
                 for rule in sorted(counts))


def read_texts(root: Path, rels: Iterable[str]) -> tuple[dict[str, str],
                                                         dict[str, int]]:
    """`({path: text}, {why it was skipped: how many})` for the paths named.

    A symlink is refused rather than followed: a tracked symlink may point
    outside the checkout, which hard rule 8 forbids this package from reading,
    and `walk.py` skips a symlinked directory for the same reason.
    """
    texts: dict[str, str] = {}
    skipped: dict[str, int] = {}
    for rel in rels:
        path = root / rel
        if path.is_symlink():
            skipped[SYMLINKED] = skipped.get(SYMLINKED, 0) + 1
            continue
        try:
            texts[rel] = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError, ValueError):
            skipped[UNREADABLE] = skipped.get(UNREADABLE, 0) + 1
    return texts, skipped


def tracked_texts(root: Path) -> tuple[dict[str, str], dict[str, int]]:
    """The tree's tracked text, read off `git ls-files` — never a directory walk.

    Tracked is the right universe and the only one that is cheap to be right
    about: it excludes a venv, a cache and a nested worktree without a roster
    of names to keep current.
    """
    return read_texts(root, git_lines('ls-files'))


def report(sources: Mapping[str, str], where: object, *,
           show_sites: bool = False,
           skipped: Mapping[str, int] | None = None) -> int:
    """Print the census and return its exit code; writes no file.

    A census of zero files is exit 1 and says what it looked at — rule 4's
    first sin is a gate that scanned nothing and printed a verdict.
    """
    narrowed = ''.join(f'; {count} {why}'
                       for why, count in sorted((skipped or {}).items()))
    if not sources:
        print(f'{PREFIX} FAIL — 0 tracked text file(s) read under {where}, so '
              f'this census scanned nothing{narrowed}. `git ls-files` lists '
              f'none there; a census of zero is never a pass', file=sys.stderr)
        return 1
    found = sites(sources)
    rows = (found if show_sites else roster(found))
    for row in rows:
        print('\t'.join(str(cell) for cell in row))
    print(f'{PREFIX} {len(found)} citation(s) of `rule <n>` across '
          f'{len(sources)} tracked text file(s) under {where}; '
          f'{len(roster(found))} rule(s) cited{narrowed}', file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    show_sites = False
    for arg in argv:
        if arg in HELP_WORDS:
            print(USAGE)
            return 0
        if arg == SITES_FLAG:
            show_sites = True
            continue
        print(f'agentic-sdlc {VERB}: unexpected argument {arg!r} — this verb '
              f'takes {SITES_FLAG} and nothing else. One rule is a grep on the '
              f'first column, not a flag: '
              f'`{vehicle.command(VERB, SITES_FLAG)} | grep -P "^4\\t"`',
              file=sys.stderr)
        return 2
    root = repo_root()
    texts, skipped = tracked_texts(root)
    return report(texts, root, show_sites=show_sites, skipped=skipped)
