"""test_adopt.py — `adopt <version>`: three checks, and nothing written.

`adopt` asks whether uv.lock pins the version that runs, whether every
installed file is current (a file `[adopt] ours` claims is named, never
graded), and whether this version accepts the repo's devkit.toml — naming
every key 2.0.0 retired with what replaces it. It writes nothing, so
`--force` is refused. Every case is a scratch tree with a `.git` marker:
nothing here spawns.
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


def fork(root: Path, rel: str) -> None:
    """One edited byte in an installed file — the invisible fork."""
    target = root / rel
    target.write_text(target.read_text(encoding='utf-8') + '\n# fork\n',
                      encoding='utf-8')


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*')) if p.is_file()}


def test_a_current_tree_passes_and_adopt_writes_nothing():
    """Bites: an adopt that writes, or a pass over a tree it never graded."""
    with tree() as root:
        (root / 'uv.lock').write_text(LOCK, encoding='utf-8')
        installed('install-gates', 'install-ci')
        before = snapshot(root)
        code, out = adopt()
        assert code == 0, out
        assert f'[adopt] ok: pin-bumped — uv.lock pins {__version__}' in out
        assert '[adopt] ok: installables-current — 5 installed file(s)' in out
        assert '[adopt] ok: config-updated' in out
        assert snapshot(root) == before
        code, out = adopt('--force')
        assert code == 2 and 'nothing to force' in out, out


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
        fork(root, GATE_MK)
        fork(root, CI)
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
    ('[verify]\nstory = "make unit"\nmilestone = "make milestone"\n',
     'renamed: [verify] story → spot'),
    ('[verify]\nfeature = "make test"\nmilestone = "make milestone"\n',
     'retired: [verify] feature'),
])
def test_config_updated_names_every_retired_key_with_its_replacement(
        config, named):
    """Bites: a 2.0.0 consumer keeping a retired key that nothing reads, and
    learning so from nothing (rule 11)."""
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
