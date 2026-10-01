"""test_adopt.py — `adopt <version>`: three checks, and nothing written.

`adopt` asks whether uv.lock pins the version that runs, whether every
installed file is current (a file `[adopt] ours` claims is named, never
graded), and whether this version accepts the repo's devkit.toml — naming
every key 2.0.0 retired with what replaces it. After the checks it prints
one `absent:` line per installed file that is not there and one `unarmed:`
line when the git hooks are not armed. It writes nothing, so `--force` is
refused. Every case is a scratch tree with a `.git` marker: nothing here
spawns.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import tree, write_config  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import __version__  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import belts, install  # noqa: E402
from agentic_sdlc.repo.pm import cli as pm_cli, skills  # noqa: E402

VERSION = '9.9.9'
# The pin since 1.0.0: the kit's own row in uv.lock, at the version running.
LOCK = (f'version = 1\n\n[[package]]\nname = "agentic-sdlc"\n'
        f'version = "{__version__}"\nsource = {{ registry = "x" }}\n')
GATE_MK = 'Makefile.devkit'
CI = '.github/workflows/verify.yml'


def adopt(*argv: str) -> tuple[int, str]:
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = belts.main(['adopt', VERSION, *argv])
    return code, buf.getvalue()


def installed(*verbs: str) -> None:
    repo_root.cache_clear()
    load_config.cache_clear()
    with contextlib.redirect_stdout(io.StringIO()):
        for verb in verbs:
            assert install.main(verb, []) == 0


def edit_installed(root: Path, rel: str) -> None:
    """One edited byte in an installed file — the invisible fork."""
    target = root / rel
    target.write_text(target.read_text(encoding='utf-8') + '\n# fork\n',
                      encoding='utf-8')


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*')) if p.is_file()}


def complete(root: Path, armed: bool = True) -> None:
    """Every installer run, and the hooks armed as `tools/setup-hooks.sh`
    arms them: `core.hooksPath` in the git config and each hook executable."""
    (root / 'uv.lock').write_text(LOCK, encoding='utf-8')
    installed(*install.PLANS)
    with contextlib.redirect_stdout(io.StringIO()):
        assert pm_cli.main(['install-skills']) == 0
    if armed:
        (root / '.git' / 'config').write_text(
            '[core]\n\tbare = false\n[core]\n\thooksPath = "tools/hooks"\n',
            encoding='utf-8')
        for _name, rel in install.PLANS['install-hooks']:
            (root / rel).chmod(0o755)


def lines_of(out: str, prefix: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith(prefix)]


def test_a_current_tree_passes_and_adopt_writes_nothing():
    """Bites: an adopt that writes, a pass over a tree it never graded, or a
    complete tree that prints an `absent:` or `unarmed:` line."""
    with tree(config='[dispatch]\nproject = "x"\ncontracts = ["CLAUDE.md"]\n'
                     '[integrate]\nper_merge = []\nproof = ["check"]\n') as root:
        (root / 'CLAUDE.md').write_text('# x\n', encoding='utf-8')
        complete(root)
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
        assert snapshot(root) == before
        code, out = adopt('--force')
        assert code == 2 and 'nothing to force' in out, out


def test_an_absent_installable_is_named_and_a_claimed_one_is_not():
    """Bites: an installed file deleted from the tree, and `adopt` skips it
    and passes — the installable it never grades is the one that is gone."""
    with tree() as root:
        complete(root)
        (root / CI).unlink()
        code, out = adopt()
        assert code == 1, out
        assert lines_of(out, '[adopt] absent:') == [f'[adopt] absent: {CI}']
        assert '[adopt] ok: installables-current' in out, out
        assert '[adopt] error — 1 absent or unarmed line(s)' in out, out
        write_config(root, f'[adopt]\nours = ["{CI}"]\n')
        code, out = adopt()
        assert code == 0, out
        assert not lines_of(out, '[adopt] absent:'), out


@pytest.mark.parametrize('config,named', [
    (None, 'git core.hooksPath is unset'),
    ('[core]\n\thooksPath = .githooks\n',
     "git core.hooksPath is '.githooks', not tools/hooks"),
    ('[core]\n\thooksPath = tools/hooks\n',
     'tools/hooks/pre-push is not executable'),
])
def test_unarmed_hooks_are_named_on_one_line_with_setup_hooks(config, named):
    """Bites: hooks on disk that git never runs, and `adopt` says nothing."""
    with tree() as root:
        complete(root, armed=False)
        if config is not None:
            (root / '.git' / 'config').write_text(config, encoding='utf-8')
        code, out = adopt()
        assert code == 1, out
        unarmed = lines_of(out, '[adopt] unarmed:')
        assert len(unarmed) == 1, out
        assert named in unarmed[0], out
        assert unarmed[0].endswith('; run tools/setup-hooks.sh'), out


def test_a_tree_with_no_pin_and_nothing_installed_is_false_twice():
    """Bites rule 4: `ok — 0 installed file(s) are current` over nothing."""
    with tree():
        code, out = adopt()
        assert code == 1, out
        assert '[adopt] error: pin-bumped: uv.lock names no agentic-sdlc' in out
        assert '[adopt] error: installables-current: NOTHING was graded' in out
        assert '[adopt] error — 2 check(s) false' in out


def test_drift_is_named_with_its_remedy_and_a_claim_is_named_not_graded():
    """Bites: a drifted installable hidden, or a claim that hides another."""
    with tree() as root:
        (root / 'uv.lock').write_text(LOCK, encoding='utf-8')
        installed('install-gates', 'install-ci')
        edit_installed(root, GATE_MK)
        edit_installed(root, CI)
        code, out = adopt()
        assert code == 1, out
        # `install-gates` first: every other remedy runs through its file.
        assert (f'{GATE_MK} (differs; `uv run agentic-sdlc install-gates '
                f'--force`)') in out, out
        assert f"{CI} (differs; `make sdlc ARGS='install-ci --diff'`)" in out
        assert out.index(GATE_MK) < out.index(CI)
        write_config(root, f'[adopt]\nours = ["{GATE_MK}", "docs/nothing.md"]\n')
        code, out = adopt()
        assert code == 1, out
        assert f'{GATE_MK} (differs' not in out, out
        assert f'1 claimed by [adopt] ours and not graded: {GATE_MK}' in out
        assert '1 claim(s) in [adopt] ours name no file' in out, out
        assert f'{CI} (differs' in out, 'a claim hid an unclaimed drift'


@pytest.mark.parametrize('config,named', [
    ('[story]\nsteps = ["committed"]\n', '[story] is retired'),
    ('[feature]\nsteps = ["stories-done"]\n', '[feature] is retired'),
    ('[release]\nsteps = ["gate"]\n', '[release] steps is retired'),
    ('[adopt]\nrunner_targets = ["check"]\n',
     '[adopt] runner_targets is retired'),
    ('[tests]\nbudget = { unit = 30 }\n', '[tests] budget is retired'),
    ('[tests]\ncases = { unit = 900 }\n', '[tests] cases is retired'),
    ('[tests]\nfloor = { unit = 1 }\n', '[tests] floor is retired'),
    ('[emit]\nsink = "ledger"\n', '[emit] is retired: the event sink'),
    ('[verify]\nstory = "make unit"\nmilestone = "make milestone"\n',
     'renamed: [verify] story → spot'),
    ('[verify]\nfeature = "make test"\nmilestone = "make milestone"\n',
     'retired: [verify] feature'),
    ('[dispatch]\nproject = ""\ncontracts = ["CLAUDE.md"]\n',
     '[dispatch]: [dispatch] project must be one non-empty line'),
    ('[integrate]\nper_merge = []\nproof = []\n',
     '[integrate]: [integrate] proof is empty'),
    ('[dispatch]\nproject = "x"\ncontracts = ["nothing.md"]\n',
     'resolve to nothing: nothing.md'),
    ('[dispatch]\nproject = "x"\ncontracts = ["devkit.toml"]\n',
     'names 1 path(s) outside [doc] scope: devkit.toml'),
])
def test_config_updated_names_every_retired_key_with_its_replacement(
        config, named):
    """Bites: a 2.0.0 consumer keeping a retired key that nothing reads, and
    learning so from nothing (rule 11); a malformed [dispatch] or [integrate]
    passed; a contract that is not there, or that `check doc` never reads."""
    with tree(config=config):
        code, out = adopt()
        assert code == 1, out
        assert '[adopt] error: config-updated' in out, out
        assert named in out, out


def test_a_claim_that_names_no_file_is_exit_2():
    with tree(config='[adopt]\nours = ["."]\n'):
        code, out = adopt()
        assert code == 2, out
        assert 'names no file' in out, out
