"""check shell — `shellcheck -x` over every tracked `*.sh` (and shell-shebang file) under the roots.

Soft-skips at exit 0 when shellcheck is not installed and nothing pins it. A
zero census FAILS. Every verdict line names the shellcheck version it ran.

`shellcheck_version` pins the one shellcheck this gate may run, so a local pass
means a CI pass: set, another version FAILS naming both, and a missing
shellcheck FAILS rather than skips. `""` (stock) takes any version. A pin
with a leading `v` is refused at exit 2: shellcheck reports `0.11.0`, never
`v0.11.0`, and the release URL adds its own `v`.
`check shell --pin` prints the pin, or an empty line, and runs nothing; the
stock verify.yml reads it to install that release before the gate.

devkit.toml: [shell] roots = ["tools"]
             [shell] shellcheck_version = ""
"""
from __future__ import annotations

import os
import shutil

from agentic_sdlc.core import spawn, walk
from agentic_sdlc.core.walk import Kind
from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      relpath_tuple, text)

# How many names a finding lists before it says how many more there are.
SHOWN_MAX = 5

DEFAULT_ROOTS = ('tools',)
# Any version: the gate as it ran before the key existed.
DEFAULT_VERSION = ''
SHEBANGS = ('#!/usr/bin/env bash', '#!/bin/bash', '#!/usr/bin/env sh', '#!/bin/sh')
# `shellcheck --version` prints `version: 0.11.0` on its own line.
VERSION_PREFIX = 'version:'
UNKNOWN = 'unknown'


def pinned() -> str:
    """`[shell] shellcheck_version`; empty means any version. A leading `v`
    is refused, never stripped: the tool does not guess what a pin means."""
    pin = text(config_section('shell'), 'shell', 'shellcheck_version',
               DEFAULT_VERSION).strip()
    if pin[:1] in ('v', 'V'):
        raise ConfigError(
            f'[shell] shellcheck_version must be a bare version like '
            f'{pin[1:]!r}, got {pin!r}: shellcheck reports no leading v')
    return pin


def print_pin() -> int:
    """`check shell --pin`: the pinned version, or an empty line. Runs nothing."""
    print(pinned())
    return 0


# What shellcheck reads beside the scripts: the rc file it looks for in each
# script's directory and every one above it, and the options in its env.
RC_FILE = '.shellcheckrc'
OPTS_ENV = 'SHELLCHECK_OPTS'


def inputs():
    """What this gate reads, for `check all`'s reuse (#98): the scripts under
    its roots, devkit.toml, which shellcheck is on PATH at which version, the
    `.shellcheckrc` in each directory from the tree's root down to a root —
    one below a root is under the scope — and `SHELLCHECK_OPTS`."""
    from agentic_sdlc.core.project import CONFIG_NAME
    from agentic_sdlc.repo.verify.gates import Inputs
    roots = relpath_tuple(config_section('shell'), 'shell', 'roots',
                          DEFAULT_ROOTS)
    rcs = {'/'.join((*parts[:depth], RC_FILE))
           for parts in (root.strip('/').split('/') for root in roots)
           for depth in range(len(parts))}
    found = shutil.which('shellcheck') or ''
    return Inputs(scope=(*roots, CONFIG_NAME), also=tuple(sorted(rcs)),
                  facts=(found, _installed_version() if found else '',
                         f'{OPTS_ENV}={os.environ.get(OPTS_ENV, "")}'))


def _installed_version() -> str:
    """The version `shellcheck --version` reports, or `unknown`."""
    try:
        done = spawn.run(['shellcheck', '--version'],
                         capture_output=True, text=True)
    except OSError:
        return UNKNOWN
    for line in (done.stdout or '').splitlines():
        if line.startswith(VERSION_PREFIX):
            return line[len(VERSION_PREFIX):].strip() or UNKNOWN
    return UNKNOWN


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
    pin = pinned()
    if shutil.which('shellcheck') is None:
        if pin:
            # A pinned gate that skips is a PASS that never looked.
            print(f'[check:shell] FAIL — shellcheck not on PATH and [shell] '
                  f'shellcheck_version pins {pin}; install shellcheck {pin}')
            return 1
        print('[check:shell] SKIP — shellcheck not on PATH (install it to enable this gate)')
        return 0
    # Every config value is read before a process starts: a typo is exit 2, never a spawn.
    roots = relpath_tuple(config_section('shell'), 'shell', 'roots',
                          DEFAULT_ROOTS)
    version = _installed_version()
    if pin and version != pin:
        print(f'[check:shell] FAIL — shellcheck {version} on PATH, [shell] '
              f'shellcheck_version pins {pin}; install shellcheck {pin} or '
              f'change the pin')
        return 1
    ran = f' (shellcheck {version})'
    root = repo_root()
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
            shown = ', '.join(on_disk[:SHOWN_MAX])
            more = (f' (+{len(on_disk) - SHOWN_MAX} more)'
                    if len(on_disk) > SHOWN_MAX else '')
            print(f'[check:shell] FAIL — {len(on_disk)} shell script(s) under '
                  f'{", ".join(roots)}/ and none TRACKED, so this scanned '
                  f'nothing: {shown}{more}. `git add` them — this gate reads '
                  f'`git ls-files`, and an untracked script is one nothing '
                  f'else will read either{ran}')
            return 1
        print(f'[check:shell] FAIL — no shell scripts found under '
              f'{", ".join(roots)}/; check [shell] roots{ran}')
        return 1
    result = spawn.run(['shellcheck', '-x', *targets], cwd=root)
    if result.returncode != 0:
        print(f'[check:shell] FAIL — findings across {len(targets)} script(s){ran}')
        return 1
    print(f'[check:shell] PASS — {len(targets)} script(s) clean{ran}')
    return 0
