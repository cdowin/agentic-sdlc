"""The agent roster: which agent types exist for a tree.

The `install-agents` definitions plus the project's own `.claude/agents/*.md`,
each by `name:` else filename. A tree holding no definition declares none, and
callers stay silent (as with `[emit]`).
"""
from __future__ import annotations

from pathlib import Path

from agentic_sdlc.core import frontmatter, walk
from agentic_sdlc.repo import install

AGENTS_DIR = '.claude/agents'
AGENT_GLOB = '*.md'
NAME_FIELD = 'name'


def _name(text: str, stem: str) -> str:
    return frontmatter.parse_document(text).field(NAME_FIELD) or stem


def _own(path: Path) -> str:
    try:
        return _name(frontmatter.read_raw(path), path.stem)
    except (OSError, UnicodeDecodeError):
        return path.stem


def agent_roster(root: Path) -> tuple[str, ...]:
    """Every agent type the tree at `root` can name, sorted; () when it holds
    no definition, so nothing is declared and nothing is refused."""
    own = {_own(path) for path in
           walk.matching(root / AGENTS_DIR, AGENT_GLOB, walk.Kind.FILE)}
    if not own:
        return ()
    shipped = {_name(install.body_of(source), Path(dest).stem)
               for source, dest in install.PLANS['install-agents']}
    return tuple(sorted(own | shipped))


def agent_defect(root: Path, agent_type: str) -> str:
    """'' when `agent_type` is on the roster or there is none, else the
    refusal naming the roster."""
    names = agent_roster(root)
    if not names or agent_type in names:
        return ''
    return (f'{agent_type!r} is not an agent type — this tree has '
            f'{", ".join(names)} (install-agents plus {AGENTS_DIR}/{AGENT_GLOB})')
