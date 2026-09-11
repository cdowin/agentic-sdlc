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

Proven against a real build at 0.2.0: top-level `core/` and `repo/` only, no
`data/`, no `.tscn`. No entry COUNT is restated here — a number this file cannot
re-derive (there is no build in it) only ever drifts, and it drifted: 85 where
the build was 84 (E4).
"""
from __future__ import annotations

from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / 'src' / 'agentic_sdlc'

# Directories whose whole contents are payload BY DESIGN, each with the thing
# that reads them. A fourth entry here needs the same sentence.
#
# KEYED ON THE PATH, not on the directory NAME. `set(rel.parts) & {names}`
# exempted a name at ANY depth, so a blob under a `templates/` a consumer
# never asked for — `repo/checks/templates/junk.bin` — shipped green, and this
# is the guard whose whole job is to notice a blob nobody asked for (E4). Three
# paths, three readers, and a new payload directory is a new line here rather
# than a name that happens to collide.
DELIBERATE_PAYLOAD = {
    Path('repo/installables'): 'written out by the `install-*` verbs',
    Path('repo/pm/templates'): 'copied by `pm new` / `pm templates`',
    Path('repo/pm/guidance'): 'read at runtime through importlib.resources',
}

SHIPPABLE_SUFFIXES = {'.py'}


def _shipped_files() -> list[Path]:
    return [p for p in sorted(PACKAGE.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts]


def _deliberate(rel: Path) -> bool:
    """Is this file INSIDE one of the payload directories, at its real path."""
    return any(rel.is_relative_to(payload) for payload in DELIBERATE_PAYLOAD)


class TestTheWheelCarriesOnlyWhatHasAReader:

    def test_no_file_ships_without_a_reader_or_a_reason(self):
        stray = []
        for path in _shipped_files():
            rel = path.relative_to(PACKAGE)
            if path.suffix in SHIPPABLE_SUFFIXES:
                continue
            if _deliberate(rel):
                continue
            stray.append(str(rel))
        assert stray == [], (
            f'{stray} ship in the wheel and are neither code nor a member of '
            f'{sorted(DELIBERATE_PAYLOAD)}. Every consumer downloads them on a '
            f'cold resolve; add a reader, move them to tests/fixtures/, or '
            f'delete them.')

    def test_the_deliberate_payload_directories_still_exist(self):
        """A guard that names three directories is a guard that goes stale.

        If one MOVES, the exemption above stops exempting and the files inside
        it become stray — loud, and correct. If one is DELETED and the entry
        outlives it, the exemption list is documentation of something that is
        not there.

        Asked of the PATH since E4, so a directory that moved elsewhere in the
        tree can no longer answer for the one that is named.
        """
        missing = sorted(str(p) for p in DELIBERATE_PAYLOAD
                         if not (PACKAGE / p).is_dir())
        assert missing == [], (
            f'{missing} are exempted here and are not there; drop the entry, '
            f'or repoint it at where the payload moved to')

    def test_the_exemption_does_not_match_a_directory_name_at_any_depth(self):
        """E4, by construction: the bypass, planted and refused.

        The old spelling intersected `rel.parts` with the payload NAMES, so a
        blob under any directory that happened to be called `templates` was
        exempt wherever it sat — including under a package that ships no
        payload at all. This plants exactly that file rather than trusting the
        rewrite to have closed it.
        """
        planted = Path('repo/checks/templates/junk.bin')
        assert not _deliberate(planted), (
            f'{planted} is exempt, so any blob under a directory NAMED like a '
            f'payload directory ships unexamined — which is the whole census')
        for real in DELIBERATE_PAYLOAD:
            assert _deliberate(real / 'a-real-payload-file'), real

    def test_the_godot_payload_is_gone_and_named(self):
        """The specific 126 KB, named so a re-add is a deliberate act."""
        assert not (PACKAGE / 'data').exists()
        assert not list(PACKAGE.rglob('classdb.json'))
        assert not list(PACKAGE.rglob('*.tscn'))
        assert not list(PACKAGE.rglob('*.tres'))
