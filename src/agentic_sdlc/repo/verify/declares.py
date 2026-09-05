"""declares.py — the REVERSE direction: a test declares what it covers.

Forward rules infer the mapping from structure, which suits unit tests. Reverse
rules read it out of the test itself, which is the only thing that works for
integration: only the scenario knows what it exercises, and no path glob could
infer it. Both ship; neither is chosen over the other.

    [[verify.narrow]]
    declares = "## covers:"
    scan     = "tests/integration/**"
    run      = "make scenario NAME=<stem>"

and in `tests/integration/checkout.md`:

    ## covers: src/agentic_sdlc/repo/pm/ledger.py src/agentic_sdlc/repo/pm

A changed path listed under that header selects that file's `run`, with
`<stem>` bound to the declaring file's stem (`checkout`) — the only capture
this direction has, and DERIVED rather than declared.

THE TWO ZERO-CENSUSES, WHICH ARE WHY THIS MODULE EXISTS. Hard rule 4: a gate
scanning nothing must say so, loudly. A reverse rule has two ways to scan
nothing and they are not the same fact, so `Scan` carries both numbers and a
caller cannot read either as "nothing to run":

  * `scanned = 0` — the `scan` glob matched no tracked file at all. The louder
    case: a rule pointed at a directory that was renamed away rots into a rule
    that quietly matches nothing, forever. `verify --check` turns this into a
    finding.
  * `scanned = N, declaring = 0` — files were found and none of them carries
    the header. A corpus that has drifted away from the rule that reads it.

THE HEADER GRAMMAR, RULED HERE:

  * `declares` is a LITERAL LINE PREFIX, never a pattern. Nothing here
    compiles it, escapes it, or matches with it — `declares = "## covers.*:"`
    looks for those exact characters at the start of a line, so a file
    containing `## coversXYZ:` does NOT match it. `rules.py` already refuses
    the metacharacters that would tempt an author; this is the other half.
  * One line. Paths are whitespace-separated.
  * A covered path matches a changed path as a PREFIX ON SEGMENT BOUNDARIES,
    so a declared directory covers the files under it and `src/a` never covers
    `src/ab`. That off-by-one is the one that silently over-selects.
  * A header INSIDE A FENCED CODE BLOCK is not a declaration. Documentation
    showing the syntax is not a claim about coverage — the same near-miss
    `repo/pm/verdict.py` already solved, and it is solved the same way here:
    through `core.markdown`, which owns the CommonMark fence rules and reports
    an unterminated fence rather than letting it mask the rest of the file.
  * A header listing NOTHING is a FINDING, not an empty coverage set. A test
    declaring it covers nothing has a header somebody meant to fill.
  * A header repeated twice in one file is a FINDING naming both line numbers.
    Which one wins is not a thing this parser may pick.

READING IS BOUNDED AND SPAWNS NOTHING. `stat` first, so a file over MAX_FILE
is REPORTED by size rather than read whole; each file is read exactly once; the
header is taken from the one matching line. Stdlib only, no `subprocess` — the
audit measured `pm-shape-scan` spending 34.8 s on four spawns per file across
683 markdown files, and that defect is why this feature exists at all.

THE REFUSAL MATRIX — the header is a PAYLOAD PARSER (SDLC.md §5). Its content
is written by whoever wrote the test, and it is a value that ends up beside a
command line. Every refusal below is a FINDING naming the declaring file, and
the whole declaration is dropped rather than half-kept: a file whose header is
partly unusable covers nothing knowable.

    ../../etc/passwd, /etc/passwd     traversal, absolute — hard rule 8
    ~/x, file:///x, https://x         home expansion, schemes
    ., .., a//b, a/./b, a trailing /  empty and dot segments
    $(id), `id`, a;b, a|b, a&b, a>b   shell fragments. They reach `run`
                                      through nothing today, and a covered
                                      path that is a shell fragment is one
                                      refactor away from being interpolated
    <name>                            captures are declared in config, never
                                      found in the tree
    a backslash                       not a separator here
    a header line over MAX_HEADER     bounded, refused, never read as a value
    a file over MAX_FILE              reported by size, not read
    not UTF-8 decodable               reported by path — never a crash, and
                                      never a silent skip

A declaring file that is a symlink is not followed: this module resolves
nothing and opens the path it was handed, which is a path git already told the
caller is tracked.

THIS MODULE DOES NOT ENUMERATE, CALL GIT, OR READ CONFIG. `tracked` is an
argument — the verb (story 04) owns git — and the parsed rules arrive from
`rules.read`. A scanner that walked the tree itself could not be tested against
a fixed corpus, and the answer would differ per machine (hard rule 8).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from agentic_sdlc.core import markdown
from agentic_sdlc.repo.verify.rules import REVERSE, Rule
from agentic_sdlc.repo.verify.select import SelectionError, substitute

# A scanned file past this is REPORTED by size, never read. A declaring header
# lives in the first screenful of a test; a megabyte is a fixture, a vendored
# blob, or a generated artefact that wandered into the scan glob.
MAX_FILE = 1_000_000
# One header LINE. A 100 KB line is a payload, and reading it into a value that
# sits beside a command line is the thing this cap exists to refuse.
MAX_HEADER = 4096
# How many paths one header may declare. A test covering more than this has
# stopped being a declaration and become a manifest.
MAX_COVERS = 64

# What a covered path may not contain. The union of "this is not a path" and
# "this would be a shell fragment if anything interpolated it".
COVER_FORBIDDEN = frozenset(';|&$`()<>#\\~:\'" ')


@dataclass(frozen=True)
class Declaration:
    """One declaring file: what it covers, and the command that runs it.

    `command` is `rule.run` with `<stem>` already bound, so a caller never
    re-derives it — one substituter (`select.substitute`) for both directions.
    """

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

    `scanned` and `declaring` are separate fields rather than a derived length
    because they are separate facts, and the caller is required to surface
    both: `scanned == 0` is a rule pointed at nothing, `declaring == 0` over a
    non-zero `scanned` is a corpus that drifted from the rule reading it.
    Neither may read as "nothing to run".
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
    """Read one REVERSE rule's `scan` glob over `tracked`, in sorted path order.

    Deterministic and idempotent: the same corpus gives the same Scan, in the
    same order, every time — `tracked` is sorted here rather than trusted to
    arrive ordered, because `git ls-files`'s order is git's business and a
    plan that changes between two identical runs cannot be reviewed.
    """
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
    """`select`'s reverse resolver: the command a reverse rule claims for a path.

    First declaring file wins, in the scan's sorted order — the same
    first-match-wins ruling `select.py` applies to rules, one level down, and
    for the same reason: two files declaring one path must not run twice.
    """
    for one in scans:
        if one.index != rule.index:
            continue
        for declaration in one.declarations:
            if declaration.covers_path(changed):
                return declaration.command
    return None


def _one_file(rule: Rule, path: str, root: Path,
              findings: list[str]) -> Declaration | None:
    """One scanned file's declaration, or None — appending anything it found.

    Bounded by `stat` BEFORE the read, so an oversized file costs a stat and
    a finding rather than a megabyte of memory.
    """
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
