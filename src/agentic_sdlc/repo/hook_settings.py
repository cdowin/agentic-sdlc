"""The Claude Code settings files, read as text: which hook commands they register.

A `cc-*` hook is armed by a settings file, never by git. `check pm`'s courier
rules ask this one reader about what a settings file says. Nothing here starts
a process.
"""
from __future__ import annotations

import json
from pathlib import Path


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

    Absent, or a document that is not a table, is `({}, '')`.
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
    opted out (0.4.0/D5). `check pm`'s courier rules read through this.
    """
    data, why = settings_document(path)
    return tuple(_commands(data.get('hooks'))), why
