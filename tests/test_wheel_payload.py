"""Everything under `src/agentic_sdlc/` ships, so everything there needs a reader.

`pyproject.toml` packages the whole of `src/agentic_sdlc`, which makes that tree
the wheel's manifest whether anyone maintains it as one or not. Through 0.1.0 it
carried `data/classdb.json` — 129,490 bytes of Godot ClassDB with zero readers,
inside the wheel root, downloaded by every consumer on every cold `uvx` resolve.

A build-and-unzip assertion would be the direct proof and it needs a build
backend and a network resolve to run. This is the same invariant read off the
source tree instead: a file that ships is a `.py`, or it belongs to one of the
three directories whose contents are *deliberately* payload — the installables,
the PM templates, and the guidance markdown read back through
`importlib.resources`. Anything else is a blob nobody asked for.

Proven against a real build once, at 0.2.0: 85 entries, top-level `core/` and
`repo/` only, no `data/`, no `.tscn`.
"""
from __future__ import annotations

from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / 'src' / 'agentic_sdlc'

# Directories whose whole contents are payload BY DESIGN, each with the thing
# that reads them. A fourth entry here needs the same sentence.
DELIBERATE_PAYLOAD = {
    'installables': 'written out by the `install-*` verbs',
    'templates': 'copied by `pm new` / `pm templates`',
    'guidance': 'read at runtime through importlib.resources',
}

SHIPPABLE_SUFFIXES = {'.py'}


def _shipped_files() -> list[Path]:
    return [p for p in sorted(PACKAGE.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts]


class TestTheWheelCarriesOnlyWhatHasAReader:

    def test_no_file_ships_without_a_reader_or_a_reason(self):
        stray = []
        for path in _shipped_files():
            rel = path.relative_to(PACKAGE)
            if path.suffix in SHIPPABLE_SUFFIXES:
                continue
            if set(rel.parts) & set(DELIBERATE_PAYLOAD):
                continue
            stray.append(str(rel))
        assert stray == [], (
            f'{stray} ship in the wheel and are neither code nor a member of '
            f'{sorted(DELIBERATE_PAYLOAD)}. Every consumer downloads them on a '
            f'cold resolve; add a reader, move them to tests/fixtures/, or '
            f'delete them.')

    def test_the_deliberate_payload_directories_still_exist(self):
        """A guard that names three directories is a guard that goes stale.

        If one is renamed, the exemption above silently stops exempting — which
        is fine — but if one is DELETED and the entry outlives it, the exemption
        list is documentation of something that is not there. Same discipline as
        the MIGRATION_DOC entry in test_consumer_independence.py.
        """
        present = {p.name for p in PACKAGE.rglob('*') if p.is_dir()}
        missing = sorted(set(DELIBERATE_PAYLOAD) - present)
        assert missing == [], (
            f'{missing} are exempted here and no longer exist; drop the entry')

    def test_the_godot_payload_is_gone_and_named(self):
        """The specific 126 KB, named so a re-add is a deliberate act."""
        assert not (PACKAGE / 'data').exists()
        assert not list(PACKAGE.rglob('classdb.json'))
        assert not list(PACKAGE.rglob('*.tscn'))
        assert not list(PACKAGE.rglob('*.tres'))
