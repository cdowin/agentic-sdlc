"""project.py — consuming-repo resolution + devkit.toml config.

Every tool operates on the repo the user invokes it FROM: the repo root is
the nearest ancestor carrying `.git`, falling back to the cwd outside a
checkout. Per-project variation lives in an optional `devkit.toml` at that
root — tools read their section with sensible defaults, so a config-less repo
gets the stock behavior for every GATE (hard rule 5; the WORKFLOW declares
its own states and is refused without them).

**Nothing here spawns.** `repo_root` used to shell out to
`git rev-parse --show-toplevel`, and since every config read comes through it,
that was one process per config read — and it forced every test fixture to be
a real `git init`/`add`/`commit` repo just to be findable. `git_lines` below
still spawns, because asking git what CHANGED is genuinely git's question;
asking where the checkout starts is not.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

CONFIG_NAME = 'devkit.toml'


# The marker that says "this is the top of a checkout". A DIRECTORY in an
# ordinary clone and a FILE in a worktree or a submodule, and both count —
# `tools/dev/agent-worktree.sh` puts every agent in a worktree, so the file
# form is the common case here rather than the exotic one.
GIT_MARKER = '.git'


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """The top of the checkout: walk up for `.git`, or the cwd outside one.

    A WALK, not `git rev-parse --show-toplevel`, and the reason is a measured
    one. Every code path that reads config comes through here, so a spawn here
    was a spawn on every config read — and because this is `lru_cache`d with no
    argument, the only way a test could point it at another tree was
    `os.chdir` + `cache_clear()`, which meant every fixture had to be a REAL
    git repo. `git init` + `git add` + `git commit` in a `tempfile`, per test,
    across a suite whose own CLAUDE.md records that ~85% of its wall clock is
    subprocess.

    The walk answers the same question for every case this package meets:
    ordinary clone, worktree, submodule, a subdirectory of any of them, and
    outside a repo entirely. It answers two cases BETTER — a checkout on a
    machine with no `git` on PATH, and a `git` that is slow because the
    repository is large — and one case differently: inside a `.git` directory
    itself, where `rev-parse` reports the toplevel and this reports the `.git`
    directory's parent, which is the same path.

    Still cached, and still cleared by the tests that chdir: the walk is cheap
    but it is not free, and the cache is what keeps a repo-root read out of
    every loop that asks for config.
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
        # Config error, not drift: exit 2 per the contract (1 is reserved for
        # findings — CI must not read a toml typo as "drift found").
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
