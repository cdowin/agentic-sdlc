"""Consuming-repo resolution and the `devkit.toml` load.

The repo root is the nearest ancestor carrying `.git`, else the cwd. Nothing here
spawns except `git_lines`, because what changed is git's question and where the
checkout starts is not.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

CONFIG_NAME = 'devkit.toml'


# A directory in a clone and a file in a worktree or submodule; both count.
GIT_MARKER = '.git'


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """The top of the checkout: walk up for `.git`, or the cwd outside one.

    Cached; tests that chdir clear it.
    """
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / GIT_MARKER).exists():
            return candidate
    return Path.cwd()


@lru_cache(maxsize=1)
def load_config() -> dict:
    path = repo_root() / CONFIG_NAME
    if not path.is_file():
        return {}
    try:
        with path.open('rb') as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as err:
        # A toml typo is exit 2, never 1: CI must not read it as drift found.
        print(f'agentic-sdlc: invalid {CONFIG_NAME}: {err}', file=sys.stderr)
        raise SystemExit(2) from err


def git_lines(*args: str) -> list[str]:
    """Run git in the repo root; return non-empty stdout lines ([] on error)."""
    try:
        out = subprocess.run(
            ['git', *args], cwd=repo_root(),
            capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [ln for ln in out.stdout.splitlines() if ln.strip()]
