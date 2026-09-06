"""Reading agent-facing markdown: a fenced block is an illustration, not a claim."""
from __future__ import annotations

import re

# CommonMark: at most three leading spaces (four is indented code, not a fence).
FENCE = re.compile(r'^[ ]{0,3}(`{3,}|~{3,})(.*)$')
CODE_SPAN = re.compile(r'`([^`]+)`')


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


def code_spans(line: str) -> list[str]:
    """The backticked spans on a line, which is where a document quotes a command."""
    return CODE_SPAN.findall(line)
