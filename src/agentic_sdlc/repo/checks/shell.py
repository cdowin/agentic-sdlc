"""check shell — `shellcheck -x` over every tracked `*.sh` (and shell-shebang file) under the roots.

Soft-skips at exit 0 when shellcheck is not installed. A zero census FAILS.

devkit.toml: [shell] roots = ["tools"]
"""
from __future__ import annotations

import shutil
import subprocess

from agentic_sdlc.core import walk
from agentic_sdlc.core.walk import Kind
from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.core.config import config_section, relpath_tuple

DEFAULT_ROOTS = ('tools',)
SHEBANGS = ('#!/usr/bin/env bash', '#!/bin/bash', '#!/usr/bin/env sh', '#!/bin/sh')


def _untracked_scripts(root, roots) -> list[str]:
    """`*.sh` present under the roots and absent from the index; asked only on a zero census."""
    found = []
    for rel in roots:
        base = root / rel
        if not base.is_dir():
            continue
        found.extend(str(p.relative_to(root))
                     for p in walk.descendants(base, Kind.FILE, suffix='.sh'))
    return found


def run() -> int:
    if shutil.which('shellcheck') is None:
        print('[check:shell] SKIP — shellcheck not on PATH (install it to enable this gate)')
        return 0
    root = repo_root()
    roots = relpath_tuple(config_section('shell'), 'shell', 'roots',
                          DEFAULT_ROOTS)
    targets = []
    for rel in git_lines('ls-files', *roots):
        path = root / rel
        if rel.endswith('.sh'):
            targets.append(rel)
            continue
        if '.' not in path.name:
            try:
                first = path.open(encoding='utf-8', errors='replace').readline().strip()
            except OSError:
                continue
            if first in SHEBANGS:
                targets.append(rel)
    if not targets:
        # The commonest zero is a fresh `init` that never `git add`ed, not a wrong root.
        on_disk = sorted(
            rel for rel in _untracked_scripts(root, roots))
        if on_disk:
            shown = ', '.join(on_disk[:5])
            more = f' (+{len(on_disk) - 5} more)' if len(on_disk) > 5 else ''
            print(f'[check:shell] FAIL — {len(on_disk)} shell script(s) under '
                  f'{", ".join(roots)}/ and none TRACKED, so this scanned '
                  f'nothing: {shown}{more}. `git add` them — this gate reads '
                  f'`git ls-files`, and an untracked script is one nothing '
                  f'else will read either')
            return 1
        print(f'[check:shell] FAIL — no shell scripts found under '
              f'{", ".join(roots)}/; check [shell] roots')
        return 1
    result = subprocess.run(['shellcheck', '-x', *targets], cwd=root)
    if result.returncode != 0:
        print(f'[check:shell] FAIL — findings across {len(targets)} script(s)')
        return 1
    print(f'[check:shell] PASS — {len(targets)} script(s) clean')
    return 0
