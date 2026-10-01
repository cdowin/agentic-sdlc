"""required.py — the lines a project declares a grain body carries (#80, #91, #96).

`[pm.required.<kind>] lines = ["Destination:", "Scenarios:"]` names line
PREFIXES. `pm new` scaffolds each as `<prefix> <!-- required -->`; the move
into an `in_progress` state and `check pm` WARN on one missing or empty.
Nothing refuses: a close is a status write (2.0.0). The value is never read
for a meaning (rule 9): `Scenarios: none` is a value. Only presence and
non-empty are asked.

One reader for all four callers, so they cannot disagree about a line. A line
inside a code fence or an HTML comment is an example, not a line; a value that
is only an HTML comment is empty, which is how the placeholder reads as empty.
"""
from __future__ import annotations

import re

from agentic_sdlc.core import frontmatter
from agentic_sdlc.core.markdown import fenced_flags
from agentic_sdlc.repo.pm import vocabulary

PLACEHOLDER = '<!-- required -->'

PRESENT, EMPTY, MISSING = 'present', 'empty', 'missing'

# An inline comment, or one opened and not closed on this line.
_COMMENT = re.compile(r'<!--.*?(?:-->|$)')
_TITLE = re.compile(r'^# ')


def _body(text: str) -> tuple[list[str], int, list[int]]:
    """(every line, the index the body starts at, the body line indexes that
    are content — outside the frontmatter, a code fence and an HTML comment)."""
    doc = frontmatter.parse_document(text)
    lines = list(doc.lines)
    start = doc.bounds[1] + 1 if doc.bounds is not None else 0
    fenced, _ = fenced_flags(lines[start:])
    content: list[int] = []
    in_comment = False
    for offset, hidden in enumerate(fenced):
        index = start + offset
        line = lines[index].rstrip('\r')
        if hidden:
            continue
        if in_comment:
            if '-->' in line:
                in_comment = False
            continue
        content.append(index)
        tail = line[line.rfind('<!--'):] if '<!--' in line else ''
        if tail and '-->' not in tail:
            in_comment = True
    return lines, start, content


def line_state(text: str, prefix: str) -> str:
    """PRESENT when a content line opens with `prefix` and carries a value
    after it, EMPTY when every such line carries none, else MISSING."""
    lines, _, content = _body(text)
    seen = False
    for index in content:
        line = lines[index].rstrip('\r')
        if not line.startswith(prefix):
            continue
        seen = True
        if _COMMENT.sub('', line[len(prefix):]).strip():
            return PRESENT
    return EMPTY if seen else MISSING


def defects(text: str, prefixes: tuple[str, ...]) -> list[str]:
    """One clause per declared line that is missing or empty, in declared
    order: `has no `X` line` or `has an empty `X` line`."""
    out: list[str] = []
    for prefix in prefixes:
        state = line_state(text, prefix)
        if state == MISSING:
            out.append(f'has no `{prefix}` line')
        elif state == EMPTY:
            out.append(f'has an empty `{prefix}` line')
    return out


def grain_defects(cfg: vocabulary.PmConfig, kind: str, text: str) -> list[str]:
    """`defects` for the lines `kind` declares; [] when it declares none."""
    return defects(text, cfg.required_lines.get(kind, ()))


def fill(text: str, prefixes: tuple[str, ...]) -> str:
    """`text` with `<prefix> <!-- required -->` added for each prefix it has
    no line for — after the `# ` title, else after the frontmatter. A line
    that is there, written or empty, is left alone, and no other byte moves
    (rule 3). The text's own line endings are kept."""
    wanted = [p for p in prefixes if line_state(text, p) == MISSING]
    if not wanted:
        return text
    cr = '\r' if '\r\n' in text else ''
    new = [f'{prefix} {PLACEHOLDER}{cr}' for prefix in wanted]
    lines, start, content = _body(text)
    title = next((i for i in content if _TITLE.match(lines[i])), None)
    if title is not None:
        lines[title + 1:title + 1] = [cr, *new]
    elif start:
        lines[start:start] = [cr, *new]
    else:
        lines[0:0] = [*new, cr]
    return '\n'.join(lines)


def arrival_lines(cfg: vocabulary.PmConfig, kind: str, gid: str, to: str,
                  text: str) -> list[str]:
    """The move REPORTS (rule 9): one `WARN` line per missing or empty
    required line, when `to` is an `in_progress` state. The status is already
    written, and nothing refuses."""
    prefixes = cfg.required_lines.get(kind, ())
    if not prefixes or vocabulary.category_of(cfg, kind, to) != vocabulary.IN_PROGRESS:
        return []
    return [f'WARN {kind} {gid} {why} — {vocabulary.required_key(kind)} '
            f'declares it' for why in defects(text, prefixes)]
