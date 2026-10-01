"""test_adopt_hooks.py — `adopt` on a tree with `install-hooks` taken.

`unarmed:` reads `core.hooksPath` the way git resolves it: system, global,
local, worktree and include config. That is a question only git answers, so
each case builds a real repository (integration tier) and owns its global git
config. The cases without hooks are test_adopt.py, in the unit tier.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.pm import git, git_tree  # noqa: E402
from test_adopt import adopt, complete, lines_of, snapshot  # noqa: E402

from agentic_sdlc import __version__  # noqa: E402
from agentic_sdlc.repo import install  # noqa: E402
from agentic_sdlc.repo.pm import skills  # noqa: E402

HOOKS = 'tools/hooks'


@pytest.fixture(autouse=True)
def global_config(tmp_path, monkeypatch) -> Path:
    """This case's own global git config, empty, and no system config: the
    host's `core.hooksPath` must not decide a verdict here."""
    path = tmp_path / 'gitconfig'
    path.write_text('', encoding='utf-8')
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(path))
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
    return path


def executable(root: Path) -> None:
    for _name, rel in install.PLANS['install-hooks']:
        (root / rel).chmod(0o755)


def test_a_current_tree_passes_and_adopt_writes_nothing():
    """Bites: an adopt that writes, a pass over a tree it never graded, or a
    complete tree that prints an `absent:`, `unarmed:` or `not taken:` line.
    The hooks are armed as `tools/setup-hooks.sh` arms them."""
    with git_tree(config='[dispatch]\nproject = "x"\n'
                         'contracts = ["CLAUDE.md"]\n[integrate]\n'
                         'per_merge = []\nproof = ["check"]\n') as root:
        (root / 'CLAUDE.md').write_text('# x\n', encoding='utf-8')
        complete(root)
        git(root, 'config', 'core.hooksPath', HOOKS)
        executable(root)
        before = snapshot(root)
        code, out = adopt()
        assert code == 0, out
        every = (sum(len(plan) for plan in install.PLANS.values())
                 + len(skills.GUIDANCE_PLAN))
        assert f'[adopt] ok: pin-bumped — uv.lock pins {__version__}' in out
        assert (f'[adopt] ok: installables-current — {every} installed '
                f'file(s)') in out, out
        assert '[adopt] ok: config-updated' in out
        assert not lines_of(out, '[adopt] absent:'), out
        assert not lines_of(out, '[adopt] unarmed:'), out
        assert not lines_of(out, '[adopt] not taken:'), out
        assert snapshot(root) == before
        code, out = adopt('--force')
        assert code == 2 and 'nothing to force' in out, out


@pytest.mark.parametrize('value,named', [
    (None, 'git core.hooksPath is unset'),
    ('.githooks', "git core.hooksPath is '.githooks', not tools/hooks"),
    (HOOKS, 'tools/hooks/pre-push is not executable'),
])
def test_unarmed_hooks_are_named_on_one_line_with_setup_hooks(value, named):
    """Bites: hooks on disk that git never runs, and `adopt` says nothing."""
    with git_tree() as root:
        complete(root)
        if value is not None:
            git(root, 'config', 'core.hooksPath', value)
        code, out = adopt()
        assert code == 1, out
        unarmed = lines_of(out, '[adopt] unarmed:')
        assert len(unarmed) == 1, out
        assert named in unarmed[0], out
        assert unarmed[0].endswith('; run tools/setup-hooks.sh'), out


@pytest.mark.parametrize('scope', ['global', 'worktree'])
def test_hooks_path_is_read_where_git_reads_it(scope, global_config):
    """Bites rule 4: `core.hooksPath` set where git reads it — the global
    config, or `config.worktree` — and `adopt` says it is unset."""
    with git_tree() as root:
        complete(root)
        executable(root)
        if scope == 'global':
            global_config.write_text(f'[core]\n\thooksPath = {HOOKS}\n',
                                     encoding='utf-8')
        else:
            git(root, 'config', 'extensions.worktreeConfig', 'true')
            git(root, 'config', '--worktree', 'core.hooksPath', HOOKS)
        code, out = adopt()
        assert not lines_of(out, '[adopt] unarmed:'), out
        assert code == 0, out
