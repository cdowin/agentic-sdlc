"""The one place this package enumerates a filesystem.

A `Walk` returns both halves of an enumeration: `kept`, and `skipped` with a reason from
the closed `SkipReason` enum, so a narrowing cannot be silent. `census()` is the only way
to a count. `tests/test_boundaries.py` forbids `glob`/`rglob`/`iterdir`/`os.walk` elsewhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator


class SkipReason(Enum):
    """Every reason an entry may leave a walk; the value is the census template, or None
    for a universe reason (never a candidate). Declaration order is render order."""

    # --- universe: never a candidate ------------------------------------------
    NOT_A_FILE = None
    NOT_A_DIRECTORY = None
    SUFFIX_MISMATCH = None

    # --- narrowing: was a candidate, a filter removed it ----------------------
    NO_FRONTMATTER = '{n} note(s) skipped (no frontmatter — not a grain)'
    DOTTED_NAME = '{n} hidden (dot-prefixed — skipped, as D13 skips them)'
    NO_GRAIN_FILE = '{n} dir(s) with no grain file'
    EXCLUDED_PATH = '{n} path(s) excluded from scope'
    # Not descended, because a symlink may point outside the checkout (hard rule 8).
    SYMLINKED_DIR = '{n} symlinked dir(s) NOT descended (a symlink may leave the checkout)'
    # `rglob` swallows the OSError, so an unreadable subtree would otherwise vanish.
    UNREADABLE_DIR = '{n} dir(s) NOT READABLE by this process and so not descended'

    @property
    def census(self) -> str | None:
        return self.value

    @property
    def is_narrowing(self) -> bool:
        return self.value is not None

    @property
    def is_unexamined(self) -> bool:
        """Was this entry not looked inside at all; a zero census with one of these is loud."""
        return self in (SkipReason.EXCLUDED_PATH, SkipReason.SYMLINKED_DIR,
                        SkipReason.UNREADABLE_DIR)


class Kind(Enum):
    """What an enumerator is asked for: the universe declaration."""

    FILE = 'file'
    DIR = 'dir'
    ANY = 'any'


@dataclass(frozen=True)
class Skip:
    path: Path
    reason: SkipReason


@dataclass(frozen=True)
class Walk:
    """Both halves of one enumeration; has no length, so a count carries its narrowings."""

    kept: tuple[Path, ...]
    skipped: tuple[Skip, ...] = ()

    def __len__(self) -> int:  # pragma: no cover - the message IS the API
        raise TypeError(
            'a Walk has no length: call .census(label) so the count and the '
            'entries the walk skipped render together, or iterate .kept when '
            'you want the paths rather than a number')

    def __iter__(self) -> Iterator[Path]:
        return iter(self.kept)

    def filter(self, keep: Callable[[Path], bool], reason: SkipReason) -> 'Walk':
        """A narrower walk with the removals recorded under `reason`; refuses a universe reason."""
        if not reason.is_narrowing:
            raise ValueError(
                f'{reason.name} is a universe reason — it may only be produced '
                f'by an enumerator argument. A filter must name a narrowing '
                f'reason, because a narrowing is what the census discloses.')
        kept: list[Path] = []
        skipped = list(self.skipped)
        for path in self.kept:
            (kept.append(path) if keep(path) else skipped.append(Skip(path, reason)))
        return Walk(tuple(kept), tuple(skipped))

    def partition(self, keep: Callable[[Path], bool], reason: SkipReason) -> tuple['Walk', tuple[Path, ...]]:
        """`(the narrower walk, the paths it removed)`, for a caller reporting the removals."""
        removed = tuple(p for p in self.kept if not keep(p))
        return self.filter(keep, reason), removed

    def merge(self, other: 'Walk') -> 'Walk':
        return Walk(self.kept + other.kept, self.skipped + other.skipped)

    def unexamined(self) -> int:
        """How many entries this walk never looked inside. See `is_unexamined`."""
        return sum(1 for skip in self.skipped if skip.reason.is_unexamined)

    def counts(self) -> dict[SkipReason, int]:
        """How many entries each narrowing reason removed; universe reasons are absent."""
        out: dict[SkipReason, int] = {}
        for skip in self.skipped:
            if skip.reason.is_narrowing:
                out[skip.reason] = out.get(skip.reason, 0) + 1
        return out

    def disclosures(self) -> str:
        """`', 2 note(s) skipped (…)'` per narrowing that removed something, else ''."""
        counts = self.counts()
        return ''.join(f', {reason.census.format(n=counts[reason])}'
                       for reason in SkipReason if reason in counts)

    def census(self, label: str) -> str:
        """`'3 bug(s), 1 note(s) skipped (…)'`: the count and its disclosures, one string."""
        return f'{len(self.kept)} {label}{self.disclosures()}'


# --- the enumerators ----------------------------------------------------------

def _classify(paths: list[Path], kind: Kind) -> Walk:
    """Split a raw listing against the universe `kind` declares."""
    if kind is Kind.ANY:
        return Walk(tuple(paths))
    want_dir = kind is Kind.DIR
    # `is_dir()`/`is_file()`, never a negation: a broken symlink is neither.
    reason = SkipReason.NOT_A_DIRECTORY if want_dir else SkipReason.NOT_A_FILE
    kept: list[Path] = []
    skipped: list[Skip] = []
    for path in paths:
        if path.is_dir() if want_dir else path.is_file():
            kept.append(path)
        else:
            skipped.append(Skip(path, reason))
    return Walk(tuple(kept), tuple(skipped))


def entries(path: Path) -> dict[str, str]:
    """{exact name: 'file'|'dir'} for one directory; a listing, because macOS
    resolves `decisions.md` to an existing `DECISIONS.md` and Linux does not."""
    try:
        return {p.name: ('dir' if p.is_dir() else 'file') for p in path.iterdir()}
    except OSError:
        return {}


def children(path: Path, kind: Kind = Kind.ANY) -> Walk:
    """One directory's immediate entries, sorted; a missing directory is an empty walk."""
    try:
        raw = sorted(path.iterdir())
    except OSError:
        return Walk(())
    return _classify(raw, kind)


def matching(path: Path, pattern: str, kind: Kind = Kind.ANY) -> Walk:
    """One directory's entries matching a glob pattern, sorted."""
    try:
        raw = sorted(path.glob(pattern))
    except OSError:
        return Walk(())
    return _classify(raw, kind)


def descendants(path: Path, kind: Kind = Kind.ANY, suffix: str | None = None,
                pattern: str = '*') -> Walk:
    """Everything under a tree, recursively, sorted; `suffix` is case-insensitive."""
    try:
        raw = sorted(path.rglob(pattern))
    except OSError:
        return Walk(())
    # A separate pass over every directory: `rglob(pattern)` yields neither a
    # symlinked nor an unreadable directory, so `raw` cannot disclose them.
    links: list[Skip] = []
    try:
        for entry in sorted(path.rglob('*')):
            if not entry.is_dir():
                continue
            if entry.is_symlink():
                links.append(Skip(entry, SkipReason.SYMLINKED_DIR))
            elif not os.access(entry, os.R_OK | os.X_OK):
                links.append(Skip(entry, SkipReason.UNREADABLE_DIR))
    except OSError:
        links = []
    walk = _classify(raw, kind)
    walk = Walk(walk.kept, walk.skipped + tuple(links))
    if suffix is None:
        return walk
    want = suffix.lower()
    kept: list[Path] = []
    skipped = list(walk.skipped)
    for candidate in walk.kept:
        (kept.append(candidate) if candidate.suffix.lower() == want
         else skipped.append(Skip(candidate, SkipReason.SUFFIX_MISMATCH)))
    return Walk(tuple(kept), tuple(skipped))


def named(root: Path, name: str, prune: tuple[str, ...] = ()) -> tuple[list[Path], list[Path]]:
    """`(files named exactly `name`, files whose lowercased name matches)`, from a
    listing rather than `rglob(name)`, which resolves case-insensitively on macOS."""
    exact: list[Path] = []
    variants: list[Path] = []
    low = name.lower()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in prune]
        for entry in filenames:
            if entry == name:
                exact.append(Path(dirpath) / entry)
            elif entry.lower() == low:
                variants.append(Path(dirpath) / entry)
    return sorted(exact), sorted(variants)
