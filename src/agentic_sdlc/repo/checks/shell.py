"""check shell — shellcheck over the repo's tooling shell scripts.

Lints every tracked *.sh under the configured roots, plus tracked
extension-less files there whose shebang is a shell, with `shellcheck -x`.
Soft-skips (exit 0, loud note) when shellcheck isn't installed — it's a
SHOULD-have dev dependency, not a hard one.

devkit.toml: [shell] roots = ["tools"]
"""
from __future__ import annotations

import shutil
import subprocess

from agentic_sdlc.core import walk
from agentic_sdlc.core.walk import Kind
from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.core.config import config_section, str_tuple

DEFAULT_ROOTS = ('tools',)
SHEBANGS = ('#!/usr/bin/env bash', '#!/bin/bash', '#!/usr/bin/env sh', '#!/bin/sh')


def _untracked_scripts(root, roots) -> list[str]:
    """`*.sh` present under the roots and absent from the index.

    The one question that tells a WRONG ROOT from an UNCOMMITTED tree, and it is
    asked only when the census is already zero — so a green run never pays for
    it.
    """
    found = []
    for rel in roots:
        base = root / rel
        if not base.is_dir():
            continue
        # `core.walk`, not `rglob` — boundaries primitive 4. A walk that
        # returns one list has nowhere to put what it dropped, and this
        # question is asked precisely when a census already came back empty,
        # which is the worst moment to lose a second one silently.
        found.extend(str(p.relative_to(root))
                     for p in walk.descendants(base, Kind.FILE, suffix='.sh'))
    return found


def run() -> int:
    if shutil.which('shellcheck') is None:
        print('[check:shell] SKIP — shellcheck not on PATH (install it to enable this gate)')
        return 0
    root = repo_root()
    roots = str_tuple(config_section('shell'), 'shell', 'roots', DEFAULT_ROOTS)
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
        # Rule 4 — a gate that scanned nothing must say so. A misconfigured
        # exclude or a wrong root is indistinguishable from a clean tree, and
        # that PASS is the most dangerous output this package emits.
        #
        # But it MUST name the right cause. This gate scans TRACKED files, and
        # the commonest way to reach zero is not a wrong root: it is a fresh
        # `agentic-sdlc init`, which writes eight scripts under `tools/` and
        # does not `git add` them. Measured 2026-09-05 on a stock init — the
        # gate failed, correctly, and sent the operator to `[shell] roots`,
        # which was right all along. A verdict that names the wrong cause costs
        # more than one that names none.
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
