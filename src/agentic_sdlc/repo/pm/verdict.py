"""verdict.py — the machine-readable verdict block at the end of a review
record.

    verdict: SHIP-WITH-FIXES
    | id | severity | disposition |
    | W1 | WARNING | landed 3a42f19ad |
    | Q5 | QUESTION | open |

One fenced block per review pass, and `parse` returns them all. Detection
is generous (case, whitespace, CRLF); acceptance is strict — anything off
the closed sets is `MalformedVerdict` with a line number, never a partial
parse. `NoVerdict` is a fact about a record, not an error.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agentic_sdlc.core import markdown
from agentic_sdlc.repo.pm import model

# --- the closed sets ----------------------------------------------------------
# SHIP family for a feature review, RELEASE family for a milestone one; the
# same three shapes.
VERDICTS = (
    'SHIP',
    'SHIP-WITH-FIXES',
    'HOLD',
    'RELEASE-SAFE',
    'RELEASE-WITH-FIXES',
    'NOT-RELEASE-SAFE',
)

# The union of what the installed reviewer definitions grade with; the
# simplifier's DELETE/REPLACE/KEEP are kinds, not severities.
# The severities that HOLD a close. Everything below `MAJOR` is recorded and
# reported and does not block: a NIT about a regex held a feature exactly as
# hard as a shipping bug, which is how "perfect" becomes the enemy of "good" —
# and a reviewer who knows a NIT blocks stops writing NITs, which is worse,
# because the cheap observation is the one you want written down.
#
# A MINOR you actually want to stop the line is raised as MAJOR. That is a
# judgement the reviewer makes on purpose, once, instead of the belt making it
# for them on every finding.
BLOCKING_SEVERITIES = ('BLOCKER', 'CRITICAL', 'MAJOR')

SEVERITIES = (
    'BLOCKER',
    'CRITICAL',
    'MAJOR',
    'SHOULD-FIX',
    'WARNING',
    'MINOR',
    'CONSIDER',
    'SUGGESTION',
    'NIT',
    'DELTA',
    'FUTURE-LEVERAGE',
    'QUESTION',
)

LANDED = 'landed'
REJECTED = 'rejected'
DEFERRED = 'deferred'
# Raised and not yet acted on; without it a pre-landing record misfiles as
# `rejected:`.
OPEN = 'open'
DISPOSITION_KINDS = (LANDED, REJECTED, DEFERRED, OPEN)
# Reviewers fix in place and never commit, so a landed fix may honestly have no
# hash; a literal token keeps the column readable.
IN_PLACE = 'in-place'

# --- the other axis: what happened to a CHECK ---------------------------------
# The four above answer *what happened to this finding*. A belt asks a
# different question of a different thing — *what happened to this CHECK* — and
# the caller has exactly one non-`true` answer to give: SKIPPED, with a reason
# (`close feature <id> --skip <check> "<why>"`, D13). Two axes, one word, one
# file: the conveyor imports this rather than minting a second spelling of
# "disposition", which would be the second scoreboard in miniature.
#
# `false` is not on this list on purpose. It is not a disposition — it is the
# absence of one, the belt asking and nobody answering, and it writes nothing.
SKIPPED = 'skipped'
CHECK_DISPOSITIONS = (SKIPPED,)

# --- the shape ----------------------------------------------------------------
MARKER = 'verdict'
HEADER_CELLS = ('id', 'severity', 'disposition')
CELLS_PER_ROW = len(HEADER_CELLS)
CELL_SEPARATOR = '|'

# 7 to 40 hex: git's short and full hash bounds.
HASH_MIN_LEN = 7
HASH_MAX_LEN = 40
# One bounded token, so an over-long cell refuses instead of becoming a key.
MAX_ID_LEN = 32
# milestone / feature / story — the deepest grain id the tree has.
MAX_ID_SEGMENTS = 3

_MARKER_LINE = re.compile(rf'^{MARKER}\s*:\s*(.*)$', re.IGNORECASE)
_LANDED = re.compile(
    rf'^{LANDED}\s+({IN_PLACE}|[0-9a-fA-F]{{{HASH_MIN_LEN},{HASH_MAX_LEN}}})$',
    re.IGNORECASE)
_REJECTED = re.compile(rf'^{REJECTED}\s*:\s*(\S.*)$', re.IGNORECASE)
_DEFERRED = re.compile(rf'^{DEFERRED}\s*:\s*(\S+)$', re.IGNORECASE)
_OPEN = re.compile(rf'^{OPEN}(?:\s*:\s*(\S.*))?$', re.IGNORECASE)
_DISPOSITIONS = ((_LANDED, LANDED), (_REJECTED, REJECTED), (_DEFERRED, DEFERRED),
                 (_OPEN, OPEN))

# One cell of a markdown separator row, alignment colons included.
_SEPARATOR_CELL = re.compile(r'^:?-+:?$')

_VERDICT_BY_FOLD = {value.casefold(): value for value in VERDICTS}
_SEVERITY_BY_FOLD = {value.casefold(): value for value in SEVERITIES}

_DISPOSITION_FORMS = (f'`{LANDED} <commit-hash>`, `{LANDED} {IN_PLACE}`, '
                      f'`{REJECTED}: <why>`, `{DEFERRED}: <grain-id>`, '
                      f'`{OPEN}` or `{OPEN}: <note>`')

# How far below an unfenced `verdict:` the header row may sit and still be one
# block.
NEAR_MISS_LOOKAHEAD = 3


class NoVerdict(Exception):
    """This record carries no verdict block — a fact the report lists, never
    an error.
    """


class MalformedVerdict(Exception):
    """A block exists and cannot be read correctly; carries the line number
    and the line. Exit 2, nothing partial.
    """

    def __init__(self, lineno: int, line: str, why: str) -> None:
        self.lineno = lineno
        self.line = line
        self.why = why
        super().__init__(f'line {lineno}: {why}\n    {line}')


@dataclass
class Finding:
    """One row. `disposition_value` is carried raw (no inference); only the
    closed-set tokens are canonicalized.
    """

    id: str
    severity: str
    disposition_kind: str
    disposition_value: str


@dataclass
class Verdict:
    """One review pass: its verdict, and every finding it dispositioned."""

    verdict: str
    findings: list[Finding] = field(default_factory=list)


def _fenced_blocks(lines: list[str]) -> tuple[list[list[tuple[int, str]]], int]:
    """Each fenced block's body as (1-based lineno, text), plus the line of a
    fence that never closes, or 0. `core.markdown.fence_at` owns the
    CommonMark rules.
    """
    blocks: list[list[tuple[int, str]]] = []
    body: list[tuple[int, str]] = []
    fence, opened = '', 0
    for lineno, raw in enumerate(lines, 1):
        here = markdown.fence_at(raw)
        if not fence:
            if here:
                fence, opened, body = here[0], lineno, []
            continue
        # A closing fence is the same character, at least as long, no info.
        if here and here[0][0] == fence[0] \
                and len(here[0]) >= len(fence) and not here[1]:
            blocks.append(body)
            fence, body = '', []
            continue
        body.append((lineno, raw))
    return blocks, opened if fence else 0


def _content(body: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """The block's lines, stripped, with blank ones dropped."""
    return [(lineno, raw.strip()) for lineno, raw in body if raw.strip()]


def _opens_a_verdict(body: list[tuple[int, str]]) -> bool:
    rows = _content(body)
    return bool(rows) and bool(_MARKER_LINE.match(rows[0][1]))


def _is_header(line: str) -> bool:
    """True for the header row, tolerantly — this asks whether a block exists,
    so it must not refuse.
    """
    stripped = line.strip()
    if len(stripped) < 2 or not (stripped.startswith(CELL_SEPARATOR)
                                 and stripped.endswith(CELL_SEPARATOR)):
        return False
    cells = [cell.strip().casefold()
             for cell in stripped[1:-1].split(CELL_SEPARATOR)]
    return tuple(cells) == HEADER_CELLS


def _unfenced_near_miss(lines: list[str],
                        fenced: list[bool]) -> tuple[int, str] | None:
    """An unfenced `verdict:` line with the header row right under it: a
    forgotten fence is still a verdict, while a lone `verdict:` in a
    sentence stays NoVerdict.
    """
    for idx, raw in enumerate(lines):
        if fenced[idx] or not _MARKER_LINE.match(raw.strip()):
            continue
        window = lines[idx + 1:idx + 1 + NEAR_MISS_LOOKAHEAD + 1]
        if any(_is_header(later) for later in window):
            return idx + 1, raw.strip()
    return None


def _is_separator_row(line: str) -> bool:
    """Every spelling of a markdown separator row, at any width — a width test
    would send the author to fix the wrong thing.
    """
    if len(line) < 2 or not (line.startswith(CELL_SEPARATOR)
                             and line.endswith(CELL_SEPARATOR)):
        return False
    cells = [cell.strip() for cell in line[1:-1].split(CELL_SEPARATOR)]
    return all(_SEPARATOR_CELL.match(cell) for cell in cells)


def _cells(lineno: int, line: str) -> list[str]:
    """The three stripped cells of a table row, or a refusal naming which
    near-miss it was; an empty cell survives for the caller to judge.
    """
    if _is_separator_row(line):
        raise MalformedVerdict(
            lineno, line,
            'a markdown separator row is not a finding — drop it; a block is '
            'the verdict line, the header row, then one row per finding')
    if len(line) < 2 or not (line.startswith(CELL_SEPARATOR)
                             and line.endswith(CELL_SEPARATOR)):
        raise MalformedVerdict(
            lineno, line,
            f'a verdict-block row opens and closes with {CELL_SEPARATOR!r} — '
            f'a block holds the header row and one row per finding, nothing else')
    cells = [cell.strip() for cell in line[1:-1].split(CELL_SEPARATOR)]
    if len(cells) != CELLS_PER_ROW:
        why = (f'{len(cells)} cell(s); a row carries exactly {CELLS_PER_ROW} '
               f'({CELL_SEPARATOR.join(HEADER_CELLS)})')
        if len(cells) > CELLS_PER_ROW:
            # A `|` inside a reason or a fourth column: both named, neither
            # guessed.
            why += (f' — a {CELL_SEPARATOR} inside a reason splits the row, so '
                    f"write 'or'; and there is no fourth column")
        raise MalformedVerdict(lineno, line, why)
    return cells


def _is_grain_id(value: str) -> bool:
    """A milestone / feature / story id, by the resolvers' own segment
    guard.
    """
    segments = value.split('/')
    return (len(segments) <= MAX_ID_SEGMENTS
            and all(model.segment_is_literal(segment) for segment in segments))


def _finding(lineno: int, line: str) -> Finding:
    fid, severity, disposition = _cells(lineno, line)
    if not fid:
        raise MalformedVerdict(lineno, line, 'the id cell is empty')
    if len(fid) > MAX_ID_LEN:
        raise MalformedVerdict(
            lineno, line,
            f'the id is {len(fid)} characters; a finding id is a label of at '
            f'most {MAX_ID_LEN} (the report groups by it, it is not the claim)')
    if any(char.isspace() for char in fid):
        raise MalformedVerdict(
            lineno, line, f'the id {fid!r} carries whitespace — it is one token')

    canonical = _SEVERITY_BY_FOLD.get(severity.casefold())
    if canonical is None:
        raise MalformedVerdict(
            lineno, line,
            f'unknown severity {severity!r}; one of {", ".join(SEVERITIES)}')

    for pattern, kind in _DISPOSITIONS:
        match = pattern.match(disposition)
        if match:
            value = (match.group(1) or '').strip()  # `open` alone has none
            if kind == LANDED and value.casefold() == IN_PLACE:
                value = IN_PLACE  # a fixed token folds; a hash stays raw
            break
    else:
        raise MalformedVerdict(
            lineno, line,
            f'unreadable disposition {disposition!r}; one of {_DISPOSITION_FORMS}')

    if kind == DEFERRED and not _is_grain_id(value):
        raise MalformedVerdict(
            lineno, line,
            f'{DEFERRED}: {value!r} is not a grain id — a deferral names the '
            f'grain that will carry it, at most {MAX_ID_SEGMENTS} segments')
    return Finding(fid, canonical, kind, value)


def _parse_block(body: list[tuple[int, str]]) -> Verdict:
    rows = _content(body)
    lineno, line = rows[0]
    raw = _MARKER_LINE.match(line).group(1).strip()  # _opens_a_verdict matched
    canonical = _VERDICT_BY_FOLD.get(raw.casefold())
    if canonical is None:
        raise MalformedVerdict(
            lineno, line,
            f'unknown verdict {raw!r}; one of {", ".join(VERDICTS)}')

    if len(rows) < 2:
        raise MalformedVerdict(
            lineno, line,
            f'the block carries no header row — a pass that raised nothing '
            f'still writes {CELL_SEPARATOR} '
            f'{f" {CELL_SEPARATOR} ".join(HEADER_CELLS)} {CELL_SEPARATOR}')
    header_lineno, header_line = rows[1]
    header = _cells(header_lineno, header_line)
    if tuple(cell.casefold() for cell in header) != HEADER_CELLS:
        raise MalformedVerdict(
            header_lineno, header_line,
            f'the header row must read {CELL_SEPARATOR} '
            f'{f" {CELL_SEPARATOR} ".join(HEADER_CELLS)} {CELL_SEPARATOR}')

    return Verdict(canonical, [_finding(lineno, line) for lineno, line in rows[2:]])


def parse(text: str) -> list[Verdict]:
    """Every verdict block in a review record, in order — one per pass,
    nothing collapsed. Raises `NoVerdict` for none and `MalformedVerdict`
    when any block cannot be read.
    """
    lines = [line.rstrip('\r') for line in text.split('\n')]
    blocks, unterminated = _fenced_blocks(lines)

    if unterminated:
        # An unclosed fence hides the block from `blocks`, and NoVerdict there
        # would be the quiet miss; any other stray fence is `check doc`'s
        # finding.
        rest = list(enumerate(lines[unterminated:], unterminated + 1))
        if _opens_a_verdict(rest):
            raise MalformedVerdict(
                unterminated, lines[unterminated - 1],
                'the verdict block opens a code fence that is never closed')

    found = [block for block in blocks if _opens_a_verdict(block)]
    if not found:
        # Only where the answer would otherwise be NONE: a record that quotes
        # the shape in prose beside a real block must still parse.
        near_miss = _unfenced_near_miss(lines, markdown.fenced_flags(lines)[0])
        if near_miss:
            raise MalformedVerdict(
                *near_miss,
                f'the verdict block is not fenced — the report reads a FENCED '
                f'block, so wrap these lines in a code fence')
        raise NoVerdict(
            f'no verdict block: no fenced block in these {len(lines)} line(s) '
            f'opens with `{MARKER}:` ({len(blocks)} fenced block(s) read)')
    return [_parse_block(block) for block in found]
