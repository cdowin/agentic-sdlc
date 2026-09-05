"""support — shared test scaffolding.

The checks resolve their scope through `git ls-files` from the git toplevel of
the cwd, so exercising one means standing up a throwaway git repo. `tree` does
exactly that, and `run_check` runs a gate inside it with the module-level caches
cleared (they are `lru_cache`d on purpose in production, where the cwd never
moves mid-run).
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# This file is tests/support/__init__.py, so tests/ is two levels up.
TESTS = Path(__file__).resolve().parent.parent
FIXTURES = TESTS / 'fixtures'
REPO_ROOT = TESTS.parent

sys.path.insert(0, str(REPO_ROOT / 'src'))


def run_check(module, **kwargs) -> tuple[int, str]:
    """Run a check's `run()` in the current repo; returns (exit code, stdout).

    `kwargs` reach the gate — `run_check(uid, fix=True)` exercises the repair
    path through the same cache-clearing scaffolding as the read-only one.
    """
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = module.run(**kwargs)
    repo_root.cache_clear()
    load_config.cache_clear()
    return code, buffer.getvalue()
