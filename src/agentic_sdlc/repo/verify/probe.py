"""probe.py — the paths a static gate asks the filesystem about, as it ran.

Recorded while `check all` runs the gate (#98, review F1).

A gate's declared inputs are what git lists under its scope. A gate that asks
`exists()` of a path git does not list — a gitignored file, a path outside the
tree, a tracked file deleted from the working tree — read something no key
held, and a reuse over it was rule 4's first sin: a PASS reprinted over a claim
that now FAILs. So a gate asks through here: `exists`, `is_file`, `is_dir`
and `read_text` answer as `pathlib` does, and inside `recording()` each one
notes the path and what it saw — its kind for an existence probe, the digest
of its bytes for a read. `gates.Session` files that set with the PASS, and a
reuse needs every probe to see the same thing again (`holds`).

Outside `recording()` these are `pathlib`, and note nothing.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import stat
from pathlib import Path
from typing import Iterator

# What a probe asked: the path's kind, or its bytes.
EXISTS, READ = 'exists', 'read'
MODES = (EXISTS, READ)

# A path's kind, as an existence probe sees it: `pathlib` follows a link.
ABSENT, FILE, DIR, OTHER = 'absent', 'file', 'dir', 'other'

DIGEST_ALGO = 'sha256'

# The open recordings, innermost last: a probe notes into every one of them.
_OPEN: list[dict[tuple[str, str], str]] = []


@contextlib.contextmanager
def recording() -> Iterator[dict[tuple[str, str], str]]:
    """{(mode, path): what the probe saw} for every probe made inside."""
    seen: dict[tuple[str, str], str] = {}
    _OPEN.append(seen)
    try:
        yield seen
    finally:
        _OPEN.remove(seen)


def _note(mode: str, path: Path, saw: str) -> None:
    key = (mode, os.fsdecode(path))
    for seen in _OPEN:
        # The FIRST answer is what the gate acted on.
        seen.setdefault(key, saw)


def kind(path: Path) -> str:
    """ABSENT, FILE, DIR or OTHER, following a link as `Path.exists` does."""
    try:
        mode = os.stat(path).st_mode
    except (OSError, ValueError):
        return ABSENT
    if stat.S_ISREG(mode):
        return FILE
    return DIR if stat.S_ISDIR(mode) else OTHER


def exists(path: Path) -> bool:
    saw = kind(path)
    _note(EXISTS, path, saw)
    return saw != ABSENT


def is_file(path: Path) -> bool:
    saw = kind(path)
    _note(EXISTS, path, saw)
    return saw == FILE


def is_dir(path: Path) -> bool:
    saw = kind(path)
    _note(EXISTS, path, saw)
    return saw == DIR


def read_text(path: Path, encoding: str = 'utf-8',
              errors: str | None = None) -> str:
    """`Path.read_text`, newline translation included; an unreadable path
    raises as it would there, and is noted ABSENT."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        _note(READ, path, ABSENT)
        raise
    _note(READ, path, _digest(data))
    with io.TextIOWrapper(io.BytesIO(data), encoding=encoding,
                          errors=errors) as text:
        return text.read()


def _digest(data: bytes) -> str:
    return hashlib.new(DIGEST_ALGO, data).hexdigest()


def seen_now(mode: str, path: Path) -> str:
    """What the probe `mode` would see at `path` now."""
    if mode == EXISTS:
        return kind(path)
    try:
        return _digest(Path(path).read_bytes())
    except OSError:
        return ABSENT


def filed(root: Path, seen: dict[tuple[str, str], str]) -> list[list[str]]:
    """The probes as a ledger row carries them: [mode, path, saw], sorted, a
    path under `root` written relative to it — textually, so `a/../b` stays
    the path the gate asked — and any other path as it was asked."""
    base = os.fsdecode(root).rstrip(os.sep) + os.sep
    rows = []
    for (mode, raw), saw in seen.items():
        rel = raw[len(base):] if raw.startswith(base) else raw
        rows.append([mode, rel, saw])
    return sorted(rows)


def holds(root: Path, probed: tuple[tuple[str, str, str], ...]) -> str:
    """'' when every filed probe sees what it saw; else the first path that
    moved, for the line that says why the gate runs."""
    for mode, rel, saw in probed:
        if seen_now(mode, root / rel) != saw:
            return rel
    return ''
