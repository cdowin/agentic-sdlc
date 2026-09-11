"""Reading agent-facing markdown: a fenced block is an illustration, not a claim."""
from __future__ import annotations

import bisect
import re

# CommonMark: at most three leading spaces (four is indented code, not a fence).
FENCE = re.compile(r'^[ ]{0,3}(`{3,}|~{3,})(.*)$')


def fence_at(raw: str) -> tuple[str, str] | None:
    """(marker run, info string) when this line is a fence line, else None.

    A backtick fence's info string may not contain a backtick (CommonMark), or a
    paragraph opening with an inline span would mask everything to the next bare fence.
    """
    match = FENCE.match(raw)
    if not match:
        return None
    marker, info = match.group(1), match.group(2).strip()
    if marker[0] == '`' and '`' in info:
        return None
    return marker, info


def fenced_flags(lines: list[str]) -> tuple[list[bool], int]:
    """(per line: inside a fenced block?, 1-based line of an unterminated fence, or 0).

    An unterminated fence masks nothing: it is reported instead of eating the file.
    """
    fenced = [False] * len(lines)
    fence, opened = '', 0
    for idx, raw in enumerate(lines):
        here = fence_at(raw.rstrip('\r'))
        if fence:
            fenced[idx] = True
            # Same character, at least as long, no info string.
            if here and here[0][0] == fence[0] \
                    and len(here[0]) >= len(fence) and not here[1]:
                fence = ''
            continue
        if here:
            fence, opened = here[0], idx
            fenced[idx] = True
    if fence:
        for k in range(opened, len(lines)):  # never terminated: it masked nothing
            fenced[k] = False
        return fenced, opened + 1
    return fenced, 0


def non_fenced_lines(text: str) -> tuple[list[tuple[int, str]], int]:
    """((1-indexed lineno, line) pairs outside fenced blocks, the unterminated-fence
    line or 0); the caller must report the second half."""
    lines = text.split('\n')
    fenced, unterminated = fenced_flags(lines)
    kept = [(n, line)
            for n, (line, hidden) in enumerate(zip(lines, fenced), 1)
            if not hidden]
    return kept, unterminated


# What ends a paragraph without a blank line. A heading is one line; a table row
# is one line; a list item STARTS one, and its continuation lines belong to it.
_HEADING = re.compile(r'^[ ]{0,3}#{1,6}(?:[ \t]|$)')
_LIST_ITEM = re.compile(r'^[ \t]*(?:[-*+]|[0-9]{1,9}[.)])(?:[ \t]|$)')
_TABLE_ROW = re.compile(r'^[ \t]*\|')
_QUOTE_MARKER = re.compile(r'^ {0,3}> ?')  # one blockquote level


def _unquote(line: str) -> tuple[int, str]:
    """(quote depth, the line inside its `>` markers), which are not text."""
    depth = 0
    while match := _QUOTE_MARKER.match(line):
        line = line[match.end():]
        depth += 1
    return depth, line


class Paragraph:
    """A run of CONSECUTIVE non-fenced lines, read as one text.

    A code span may cross a line break inside one and never crosses the break
    between two, because CommonMark pairs backticks within a paragraph: a line
    at a time, a span wrapped across a line never forms, and every backtick
    after it on the next line pairs with the wrong partner. `text` is read
    inside the quote markers; `lines` and `at` keep the line as written.
    """

    def __init__(self, lines: list[tuple[int, str]]):
        self.lines = tuple(lines)
        contents = [_unquote(line)[1] for _, line in self.lines]
        self.text = '\n'.join(contents)
        self._starts: list[int] = []
        offset = 0
        for content in contents:
            self._starts.append(offset)
            offset += len(content) + 1

    def at(self, offset: int) -> tuple[int, str]:
        """(1-indexed lineno, line) of the line holding `offset` in `text`."""
        return self.lines[bisect.bisect_right(self._starts, offset) - 1]


def _breaks_after(raw: str) -> bool:
    return bool(_HEADING.match(raw) or _TABLE_ROW.match(raw)
                or fence_at(raw))


def _breaks_before(raw: str) -> bool:
    return bool(_HEADING.match(raw) or _TABLE_ROW.match(raw)
                or _LIST_ITEM.match(raw) or fence_at(raw))


def paragraphs(lines: list[tuple[int, str]]) -> list[Paragraph]:
    """`non_fenced_lines`' pairs, grouped: broken at a blank line, a gap in line
    numbers (which is where a fence was dropped, so a join never crosses one),
    a fence line still present (an UNTERMINATED one, which masks nothing), a
    heading, a list-item start, a table row and a change of quote depth (a
    lazy continuation too), each read inside the quote: `>` alone is blank."""
    runs: list[list[tuple[int, str]]] = []
    run: list[tuple[int, str]] = []
    previous, depth_before, content_before = None, 0, ''
    for lineno, line in lines:
        depth, content = _unquote(line.rstrip('\r'))
        if not content.strip():
            run, previous = [], None
            continue
        if (not run or lineno != previous + 1 or depth != depth_before
                or _breaks_after(content_before)
                or _breaks_before(content)):
            run = []
            runs.append(run)
        run.append((lineno, line))
        previous, depth_before, content_before = lineno, depth, content
    return [Paragraph(run) for run in runs]


_BACKTICK_RUN = re.compile(r'`+')


def code_span_matches(text: str) -> list[tuple[int, int, str]]:
    """(start, end, raw content) of every code span in `text`, paired the way
    CommonMark pairs them: a run of N backticks opens a span that only a run of
    exactly N closes, and a run nothing closes is literal text.

    Pairing single backticks one by one was harmless on one line; across a
    paragraph, one ``double`` span or a stray ``` would shift every pairing to
    the paragraph's end and hide the claims after it. Backslash escapes are
    not read, as the line-at-a-time reader never read them either.
    """
    runs = list(_BACKTICK_RUN.finditer(text))
    spans: list[tuple[int, int, str]] = []
    i = 0
    while i < len(runs):
        opener = runs[i]
        width = len(opener.group())
        close = next((k for k in range(i + 1, len(runs))
                      if len(runs[k].group()) == width), None)
        if close is None:
            i += 1
            continue
        closer = runs[close]
        spans.append((opener.start(), closer.end(),
                      text[opener.end():closer.start()]))
        i = close + 1
    return spans


def span_text(raw: str) -> str:
    """A code span's content as a reader sees it: a line break, with the
    indentation around it, is one space (CommonMark), and a break at either
    edge — a backtick ending a line — is the wrap, not content. A span on one
    line is returned unchanged."""
    if '\n' not in raw:
        return raw
    parts = raw.split('\n')
    parts = ([parts[0].rstrip()] + [p.strip() for p in parts[1:-1]]
             + [parts[-1].lstrip()])
    while parts and not parts[0]:
        parts.pop(0)
    while parts and not parts[-1]:
        parts.pop()
    return ' '.join(p for p in parts if p)
