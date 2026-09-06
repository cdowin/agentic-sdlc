"""check grain-shape — grain documents stay inside the caps this kit defines.

Measures the BODY (after the closing `---`, trailing blanks trimmed) of every grain
document under `[pm] roadmap_dir`, in one read per file. A `.md` without frontmatter is
a note and is disclosed, not measured; `decisions.md` and `handoff.md` are measured
because their templates open no frontmatter. A damaged frontmatter block measures the
whole file rather than zero.

devkit.toml:

    [grain_shape]
    caps = { story = 300 }   # every kind not named keeps its shipped default

A tree over a default raises its own ceiling here, visibly. No PM tree, or a tree with
no grain yet, is a PASS that says so: `check pm` owns "is there a tree".
"""
from __future__ import annotations

from pathlib import Path

from agentic_sdlc.core import walk
from agentic_sdlc.core.config import (ConfigError, config_section, number_table,
                                      relpath)
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.core.walk import Kind, SkipReason, Walk
from agentic_sdlc.repo.pm import model

SECTION = 'grain_shape'
CAPS_KEY = 'caps'

MILESTONE = 'milestone'
FEATURE = 'feature'
STORY = 'story'
BUG = 'bug'
DECISIONS = 'decisions'
HANDOFF = 'handoff'
NOTE = 'note'

# Minted without a frontmatter block, so the grain filter would drop them.
FRONTMATTERLESS_SLOTS = (model.DECISION_FILE_NAME, model.HANDOFF_FILE_NAME)

# Body lines; `decisions` runs highest because it is append-only for a whole milestone.
DEFAULT_CAPS: dict[str, int] = {
    BUG: 150,
    DECISIONS: 500,
    FEATURE: 200,
    HANDOFF: 120,
    MILESTONE: 200,
    NOTE: 250,
    STORY: 200,
}

LABEL_WIDTH = len('UNREADABLE')


def _caps() -> dict[str, int]:
    """The ceiling per kind: defaults with `[grain_shape] caps` merged over them.

    An unknown kind, a cap below 1 and an empty table are each refused at exit 2.
    """
    sect = config_section(SECTION)
    declared = number_table(sect, SECTION, CAPS_KEY, DEFAULT_CAPS)
    if CAPS_KEY in sect and not declared:
        raise ConfigError(
            f'[{SECTION}] {CAPS_KEY} is empty — remove the key to take the '
            f'shipped caps rather than declaring nothing')
    unknown = sorted(set(declared) - set(DEFAULT_CAPS))
    if unknown:
        raise ConfigError(
            f'[{SECTION}] {CAPS_KEY} names unknown grain kind(s) '
            f'{", ".join(unknown)} — the kinds are '
            f'{" ".join(sorted(DEFAULT_CAPS))}')
    for kind, value in sorted(declared.items()):
        if value < 1:
            raise ConfigError(
                f'[{SECTION}] {CAPS_KEY}.{kind} must be at least 1, got '
                f'{value} — a cap below one line fails every document')
    # Merged, so naming one kind never un-caps the others.
    return {**DEFAULT_CAPS, **declared}


def _kind_of(rel: Path) -> str:
    """Which kind a grain document is, from `model`'s names and slots."""
    name = rel.name
    if name == model.MILESTONE_DOC:
        return MILESTONE
    if name == model.FEATURE_DOC:
        return FEATURE
    if name == model.DECISION_FILE_NAME:
        return DECISIONS
    if name == model.HANDOFF_FILE_NAME:
        return HANDOFF
    # Every component, because `bugs/<topic>/<doc>.md` is a real shape.
    parts = rel.parts[:-1]
    if model.STORIES_DIR in parts:
        return STORY
    if model.BUGS_DIR in parts:
        return BUG
    return NOTE


def _body_lines(lines: list[str]) -> int:
    """Body length in lines; a damaged frontmatter block makes the whole file the body."""
    bounds = model._fence_bounds(lines)
    body = list(lines) if bounds is None else lines[bounds[1] + 1:]
    while body and not body[-1].strip():
        body.pop()
    return len(body)


def _walk(roadmap: Path, lines_of: dict[Path, list[str] | None]) -> Walk:
    """Every grain document under the PM tree; `lines_of` is filled here so nothing is read twice."""
    def readable(path: Path) -> list[str] | None:
        if path not in lines_of:
            try:
                lines_of[path] = model._split(model.read_raw(path))
            except (OSError, UnicodeDecodeError):
                lines_of[path] = None
        return lines_of[path]

    def in_scope(path: Path) -> bool:
        # Read unconditionally: `run()` reads `lines_of` back for every kept path.
        lines = readable(path)
        if path.name in FRONTMATTERLESS_SLOTS:
            return True
        return True if lines is None else model._opens_frontmatter(lines)

    return (walk.descendants(roadmap, Kind.FILE, suffix='.md')
            .filter(lambda p: not any(part.startswith('.')
                                      for part in p.relative_to(roadmap).parts),
                    SkipReason.DOTTED_NAME)
            .filter(lambda p: model.ARCHIVE_DIR_NAME
                    not in p.relative_to(roadmap).parts,
                    SkipReason.EXCLUDED_PATH)
            .filter(in_scope, SkipReason.NO_FRONTMATTER))


def _measured_line(seen: dict[str, int], caps: dict[str, int]) -> str:
    """`bug 1/150, decisions 1/500, …`: count and cap per kind, empty kinds included."""
    return ', '.join(f'{kind} {seen.get(kind, 0)}/{caps[kind]}'
                     for kind in sorted(caps))


def run() -> int:
    caps = _caps()
    root = repo_root()
    # The same `relpath` read `repo/pm/model.load` makes, so the two readers agree.
    roadmap_dir = relpath(config_section('pm'), 'pm', 'roadmap_dir', 'pm/roadmap')
    roadmap = root / roadmap_dir

    if not roadmap.is_dir():
        print(f'[check:grain-shape] PASS — no {roadmap_dir}/ in this repo, so '
              f'there are no grain documents to measure')
        return 0

    lines_of: dict[Path, list[str] | None] = {}
    found = _walk(roadmap, lines_of)
    docs = list(found)
    census = found.census(f'PM document(s) under {roadmap_dir}/')
    if not docs:
        # A walk that kept nothing while leaving entries unexamined cannot tell
        # an empty tree from a scope that lost one.
        if found.unexamined():
            print(f'[check:grain-shape] FAIL — {census}, and this kept nothing '
                  f'while leaving {found.unexamined()} entr(ies) unexamined, so '
                  f'it cannot tell an empty tree from a scope that lost one')
            return 1
        print(f'[check:grain-shape] PASS — {census}; {roadmap_dir}/ holds no '
              f'grain document yet, so there is nothing to measure. `check pm` '
              f'is the gate with an opinion about a PM tree being there')
        return 0

    findings: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for path in docs:
        rel = path.relative_to(root)
        kind = _kind_of(path.relative_to(roadmap))
        seen[kind] = seen.get(kind, 0) + 1
        lines = lines_of[path]
        if lines is None:
            findings.append((
                'UNREADABLE',
                f'{rel} is a grain document this gate cannot open, so its '
                f'length is unknown — it is counted, never assumed to fit'))
            continue
        length = _body_lines(lines)
        if length > caps[kind]:
            findings.append((
                'OVER CAP',
                f'{rel} — {length} body line(s), {kind} cap {caps[kind]} '
                f'(raise it in [{SECTION}] {CAPS_KEY} or split the document)'))

    scope = f'{census}; measured {_measured_line(seen, caps)}'
    if findings:
        for label, said in findings:
            print(f'  {label:<{LABEL_WIDTH}} {said}')
        print(f'[check:grain-shape] FAIL — {len(findings)} finding(s) across '
              f'{scope}')
        return 1
    print(f'[check:grain-shape] PASS — {scope}')
    return 0
