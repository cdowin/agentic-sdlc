"""declares.py — the reverse direction: a test declares what it covers.

A reverse rule (`declares` / `scan` / `run`) selects a scanned file's `run`,
with `<stem>` bound, when a changed path is under a path its header line lists
(segment-bounded prefix; a header inside a code fence does not count). `Scan`
carries two zero-censuses because they are different facts; reading is bounded
and spawns nothing; a hostile header is dropped whole (`_why_not_a_path`).
`tracked` is an argument so a scan is testable against a fixed corpus.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from agentic_sdlc.core import markdown
from agentic_sdlc.repo.verify.rules import REVERSE, Rule
from agentic_sdlc.repo.verify.select import SelectionError, substitute

# A header lives in the first screenful; a megabyte is a fixture or a blob,
# reported by size and never read.
MAX_FILE = 1_000_000
# A 100 KB header line is a payload, not a declaration.
MAX_HEADER = 4096
# Past this a declaration has become a manifest.
MAX_COVERS = 64

# Not-a-path characters plus shell fragments, since the value sits beside a
# command line.
COVER_FORBIDDEN = frozenset(';|&$`()<>#\\~:\'" ')


@dataclass(frozen=True)
class Declaration:
    """One declaring file: what it covers, and `rule.run` with `<stem>`
    bound."""

    path: str
    stem: str
    line: int
    covers: tuple[str, ...]
    command: str

    def covers_path(self, changed: str) -> bool:
        """Segment-bounded prefix: `src/a` covers `src/a/b.py`, never `src/ab`."""
        for covered in self.covers:
            if changed == covered or changed.startswith(covered + '/'):
                return True
        return False


@dataclass(frozen=True)
class Scan:
    """One reverse rule's read of the tree: both censuses, and every finding.

    `scanned == 0` is a glob matching nothing; `declaring == 0` over a non-zero
    `scanned` is a corpus that drifted. Neither reads as "nothing to run".
    """

    index: int
    glob: str
    scanned: int
    declaring: int
    declarations: tuple[Declaration, ...]
    findings: tuple[str, ...]

    @property
    def empty_scan(self) -> bool:
        """The louder zero: this rule's glob matched no tracked file at all."""
        return self.scanned == 0

    @property
    def empty_corpus(self) -> bool:
        """Files were found, and none of them declares anything."""
        return self.scanned > 0 and self.declaring == 0


def scan(rule: Rule, tracked: Iterable[str], root: Path) -> Scan:
    """One reverse rule's `scan` glob over `tracked`, sorted here so the same
    corpus always gives the same Scan."""
    if rule.kind != REVERSE:  # pragma: no cover - the verb filters by kind
        raise ValueError(f'[verify.narrow] #{rule.index} is not a reverse rule')
    matched = sorted(path for path in tracked
                     if rule.pattern.fullmatch(path))
    declarations: list[Declaration] = []
    findings: list[str] = []
    for path in matched:
        found = _one_file(rule, path, root, findings)
        if found is not None:
            declarations.append(found)
    return Scan(index=rule.index, glob=rule.glob, scanned=len(matched),
                declaring=len(declarations), declarations=tuple(declarations),
                findings=tuple(findings))


def resolve(scans: Sequence[Scan], rule: Rule, changed: str) -> str | None:
    """The command a reverse rule claims for `changed`, or None; the first
    declaring file wins, in scan order."""
    for one in scans:
        if one.index != rule.index:
            continue
        for declaration in one.declarations:
            if declaration.covers_path(changed):
                return declaration.command
    return None


def _one_file(rule: Rule, path: str, root: Path,
              findings: list[str]) -> Declaration | None:
    """One scanned file's declaration, or None, appending any finding; `stat`
    before the read keeps an oversized file to a finding."""
    where = f'[verify.narrow] #{rule.index} {path}'
    target = root / path
    try:
        size = target.stat().st_size
    except OSError as err:
        findings.append(f'{where}: cannot be read ({err.strerror or err})')
        return None
    if size > MAX_FILE:
        findings.append(
            f'{where}: is {size} bytes — a scanned file is at most {MAX_FILE}; '
            f'it was NOT read, and a declaration inside it (if any) is not in '
            f'this plan')
        return None
    try:
        text = target.read_bytes().decode('utf-8')
    except OSError as err:
        findings.append(f'{where}: cannot be read ({err.strerror or err})')
        return None
    except UnicodeDecodeError:
        findings.append(
            f'{where}: is not UTF-8 — reported rather than skipped, because a '
            f'file quietly dropped from a scan is a file nobody knows went '
            f'unread')
        return None

    lines, unterminated = markdown.non_fenced_lines(text)
    if unterminated:
        findings.append(
            f'{where}: has a code fence opened at line {unterminated} that '
            f'never closes — everything after it is read UNMASKED, so a '
            f'documentation example below it could be read as a declaration')
    hits = [(number, line) for number, line in lines
            if line.startswith(rule.declares)]
    if not hits:
        return None
    if len(hits) > 1:
        at = ', '.join(str(number) for number, _ in hits)
        findings.append(
            f'{where}: declares {rule.declares!r} on lines {at} — which one '
            f'wins is not a thing this parser may pick; leave one')
        return None

    number, line = hits[0]
    if len(line) > MAX_HEADER:
        findings.append(
            f'{where}:{number}: the header line is {len(line)} characters — at '
            f'most {MAX_HEADER}. It was not read as a value')
        return None
    covers = line[len(rule.declares):].split()
    if not covers:
        findings.append(
            f'{where}:{number}: declares {rule.declares!r} and lists nothing — '
            f'a test that declares it covers nothing has a header somebody '
            f'meant to fill, which is a finding and not an empty coverage set')
        return None
    if len(covers) > MAX_COVERS:
        findings.append(
            f'{where}:{number}: declares {len(covers)} paths — at most '
            f'{MAX_COVERS}; past that a declaration has become a manifest')
        return None
    bad = [_why_not_a_path(covered) for covered in covers]
    problems = [f'{covered!r} ({why})'
                for covered, why in zip(covers, bad) if why]
    if problems:
        findings.append(
            f'{where}:{number}: declares {", ".join(problems)} — the whole '
            f'declaration is dropped rather than half-kept: a header that is '
            f'partly unusable covers nothing knowable')
        return None

    stem = path.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    try:
        command = substitute(rule, {'stem': stem}, path)
    except SelectionError as err:
        findings.append(f'{where}:{number}: {err}')
        return None
    return Declaration(path=path, stem=stem, line=number,
                       covers=tuple(covers), command=command)


def _why_not_a_path(covered: str) -> str:
    """'' when this covered value is a usable relative path, else the reason."""
    if not covered:  # pragma: no cover - `split()` never yields one
        return 'empty'
    if covered.startswith('/'):
        return 'absolute — hard rule 8: nothing here names a path outside '\
               'the checkout'
    bad = sorted(set(covered) & COVER_FORBIDDEN)
    if bad:
        return ('contains ' + ', '.join(repr(c) for c in bad)
                + ' — a covered path is a relative path, and a covered path '
                  'that is a shell fragment is one refactor from a command line')
    control = sorted({c for c in covered if ord(c) < 0x20 or ord(c) == 0x7f})
    if control:
        return 'contains control character(s) ' \
               + ', '.join(hex(ord(c)) for c in control)
    segments = covered.split('/')
    if any(segment == '' for segment in segments):
        return 'has an empty segment — "a//b" and a trailing "/" are typos'
    if any(segment in ('.', '..') for segment in segments):
        return 'has a "." or ".." segment — traversal is refused, not resolved'
    return ''
