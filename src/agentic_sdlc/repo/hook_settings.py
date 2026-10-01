"""The Claude Code settings files, read as text: which hook commands they register.

A `cc-*` hook is armed by a settings file, never by git. `check pm`'s courier
rules and `preflight` both ask this one reader, so the two cannot disagree
about what a settings file says. Nothing here starts a process.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentic_sdlc.core import walk
from agentic_sdlc.core.walk import Kind, SkipReason, Walk
from agentic_sdlc.repo import vehicle

HOOKS_DIR = 'tools/hooks'
CC_PREFIX = 'cc-'
INSTALL_COMMAND = vehicle.command('install-hooks')
SETTINGS_FILES = ('.claude/settings.json', '.claude/settings.local.json')


def _commands(node: object) -> list[str]:
    """Every `command` string under a settings file's `hooks` key — never the
    document's text, where an allowlist entry reads as a registration."""
    found: list[str] = []
    if isinstance(node, dict):
        command = node.get('command')
        if isinstance(command, str):
            found.append(command)
        for key, value in node.items():
            if key != 'command':
                found.extend(_commands(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_commands(item))
    return found


def settings_document(path: Path) -> tuple[dict, str]:
    """(one settings file's top-level table, why it was unread).

    Absent, or a document that is not a table, is `({}, '')`. `preflight`
    reads `permissions` through this, so both readers fail the same way.
    """
    if not path.is_file():
        return {}, ''
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError) as err:
        return {}, err.__class__.__name__
    except ValueError as err:
        return {}, f'it is not JSON: {err}'
    return (data if isinstance(data, dict) else {}), ''


def settings_commands(path: Path) -> tuple[tuple[str, ...], str]:
    """(the hook commands this one settings file registers, why it was unread).

    Absent is `((), '')` and never a defect: a tree that registers nothing has
    opted out (0.4.0/D5). `check pm`'s courier rules read through this too.
    """
    data, why = settings_document(path)
    return tuple(_commands(data.get('hooks'))), why


def _registered(root: Path, names: list[str]) -> tuple[set[str], str, str]:
    """(which of `names` a settings file registers, where, why unread)."""
    found: set[str] = set()
    where: list[str] = []
    unread: list[str] = []
    for rel in SETTINGS_FILES:
        commands, why = settings_commands(root / rel)
        if why:
            unread.append(f'{rel} could not be read ({why})')
            continue
        here = {name for name in names
                if any(name in command for command in commands)}
        if here:
            found |= here
            where.append(rel)
    return found, ' and '.join(where), '; '.join(unread)


def _entries(directory: Path) -> Walk:
    """The hook entry points; `_*` libraries and `*.local` files are excluded."""
    return walk.children(directory, Kind.ANY).filter(
        lambda path: not path.name.startswith('_')
        and not path.name.endswith('.local'),
        SkipReason.EXCLUDED_PATH)


def cc_registration(root: Path) -> tuple[list[str], set[str], str, str]:
    """(the `cc-*` hook files on disk, which of them a settings file
    registers, where, why unread) — read as text, nothing started."""
    names = [path.name for path in _entries(root / HOOKS_DIR)
             if path.is_file() and path.name.startswith(CC_PREFIX)]
    return (names, *_registered(root, names))
