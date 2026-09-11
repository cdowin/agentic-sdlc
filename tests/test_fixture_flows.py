"""test_fixture_flows.py — the census: every fixture tree DECLARES its flow.

WHY THIS IS A TEST AND NOT A ONE-TIME SWEEP
`[pm.states.<kind>]` has no runtime fallback. `vocabulary.flow_of`
(src/agentic_sdlc/repo/pm/vocabulary.py) exits 2 by name when a tree declared
nothing, and the engine's questions route through `vocabulary.holds` — so a fixture
that stops declaring does NOT fail with a message about fixtures. It fails as a
`ConfigError` raised several frames below whatever verb the case was actually
about, and the reader's first guess is that the verb regressed. The one thing
that will drift here is the CENSUS: which builders declare and which do not.
So the census is the assertion.

Each row is a tree builder that some test module hands to a `pm` verb, a
`check pm` / `check grain-shape` run, a conveyor step, or `verify`. The claim
is the same for all of them and it is the strongest one available: standing in
the tree the builder made, `vocabulary.load()` yields a flow for every kind in
`vocabulary.FLOW_KINDS`, which is exactly the precondition `flow_of` checks.

DELIBERATELY NOT IN THE CENSUS, and each absence is a decision:

  * `tests/test_pm_flow.py::tree` — the module that OWNS the absence. Its cases
    are what prove a flow-less tree is refused by name, so a flow there would
    delete the feature's own tests.
  * `tests/test_ci_workflows.py::_milestone` — its `pm/roadmap` is read by the
    `ci-semver-gate.yml` compare step, a bash script that greps `milestone.md`.
    Nothing in that module loads `pm.vocabulary`, so a devkit.toml would be
    scenery.
  * `tests/test_init_verb.py` / `tests/test_fresh_project.py` — those trees are
    built BY `agentic-sdlc init`, which writes the seed section itself
    (`installables/project-devkit.toml` carries `render_seed()` verbatim, held
    there by tests/test_pm_flow.py:559). They declare by construction, and
    pinning them here would assert the installer's behaviour twice.
  * `tests/test_pm_guidance.py::Guidance::test_init_stands_up_a_usable_tree_
    from_nothing` — the OPEN one. `agentic-sdlc pm init` is a different verb
    from `agentic-sdlc init`, and it does NOT write the seed, though
    `flow_of`'s refusal names it as the command that does. That test builds a
    bare repo and runs `pm init` then `pm new`, so it is the case phase 7 has
    to make pass by teaching `pm init` to write `[pm.states.*]` — declaring for
    it here would delete the measurement.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402,F401 — puts src/ on the path

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.pm import vocabulary  # noqa: E402

# --- these tests share ONE mutable thing: this repo ----------------------------
# Every case here spawns `make` against REPO_ROOT rather than a scratch tree,
# because what it is testing IS this repo's Makefile and the gate library it
# sources. That makes them the only tests in the suite that are not fully
# encapsulated: two of them running at once write the same `.gate-reports/`
# logs and the same ledger, and the loser sees the winner's row.
#
# xdist found it the hour parallelism landed — they pass alone and fail
# together, which is the shape a suite hides until it is run in parallel.
#
# `xdist_group` is the DECLARATION that fixes it: every test carrying this name
# is dispatched to the same worker, so they serialise against each other and
# against nothing else. It costs the suite nothing — the group runs while seven
# other workers run everything else — and it says out loud what is shared,
# which a `-p no:randomly` or a `--dist loadfile` would only work around.
pytestmark = pytest.mark.xdist_group(name='the-real-repo')



@contextlib.contextmanager
def _support_pm_tree():
    from support import pm as pmfx
    with pmfx.tree() as root:
        yield root


@contextlib.contextmanager
def _conveyor_adopt_tree():
    import test_conveyor_adopt as mod
    with mod.tree() as root:
        yield root


@contextlib.contextmanager
def _conveyor_close_tree():
    import test_conveyor_close as mod
    with mod.tree() as root:
        yield root


@contextlib.contextmanager
def _conveyor_deviation_tree():
    import test_conveyor_deviation as mod
    with mod.tree() as root:
        yield root


@contextlib.contextmanager
def _conveyor_steps_tree():
    import test_conveyor_steps as mod
    with mod.tree() as root:
        yield root


@contextlib.contextmanager
def _fuzz_pm_tree():
    import test_fuzz_inputs as mod
    with mod._scratch(mod._build_pm) as (_outer, root):
        yield root


@contextlib.contextmanager
def _hooks_ledger_repo():
    if shutil.which('bash') is None:
        pytest.skip('needs bash')
    import test_hooks_payloads as mod
    with tempfile.TemporaryDirectory() as tmp:
        yield mod.ledger_repo(Path(tmp))


@contextlib.contextmanager
def _replay_migration_tree():
    import test_replay_migration as mod
    with mod._tree() as root:
        yield root


@contextlib.contextmanager
def _verify_main_repo():
    import test_verify_main as mod
    with mod.Repo(mod.LADDER + mod.STORY_RULE,
                  dict(mod.TheRatioIsMeasuredOrUnknown.TREE)) as repo:
        yield repo.root


# The census. The name is the one a failure prints, so it names the BUILDER —
# `tests/<module>::<callable>` — and not this file's wrapper.
BUILDERS = {
    'tests/support/pm.py::tree': _support_pm_tree,
    'tests/test_conveyor_adopt.py::tree': _conveyor_adopt_tree,
    'tests/test_conveyor_close.py::tree': _conveyor_close_tree,
    'tests/test_conveyor_deviation.py::tree': _conveyor_deviation_tree,
    'tests/test_conveyor_steps.py::tree': _conveyor_steps_tree,
    'tests/test_fuzz_inputs.py::_build_pm': _fuzz_pm_tree,
    'tests/test_hooks_payloads.py::ledger_repo': _hooks_ledger_repo,
    'tests/test_replay_migration.py::_tree': _replay_migration_tree,
    'tests/test_verify_main.py::Repo': _verify_main_repo,
}


@contextlib.contextmanager
def _standing_in(root: Path):
    """cwd'd into `root` with the config caches cleared, both ways.

    Several builders already chdir; entering again is a no-op for those and is
    what makes the two that do not (`_tree`, `Repo`'s root before its own
    `__enter__`) answerable. `vocabulary.load()` reads devkit.toml through
    `core.project`'s `lru_cache`d pair, so a stale entry from the previous row
    would make this whole census answer about the wrong tree.
    """
    previous = Path.cwd()
    os.chdir(root)
    repo_root.cache_clear()
    load_config.cache_clear()
    try:
        yield
    finally:
        os.chdir(previous)
        repo_root.cache_clear()
        load_config.cache_clear()


@pytest.mark.parametrize('name', sorted(BUILDERS))
def test_every_fixture_tree_declares_a_flow_for_every_grain_kind(name):
    """The precondition `flow_of` checks, asked of the builder directly.

    Not "a devkit.toml exists" and not "the file contains `[pm.states.`": both
    would pass over a declaration `load()` refuses, and a seed that cannot be
    read is worse than no seed because the failure moves.
    """
    with BUILDERS[name]() as root, _standing_in(root):
        cfg = vocabulary.load()
        assert sorted(cfg.flows) == sorted(vocabulary.FLOW_KINDS), (
            f'{name} builds a tree declaring {sorted(cfg.flows)} — every `pm` '
            f'verb and every `check pm` run over it is refused by '
            f'`vocabulary.flow_of` at exit 2, from wherever the engine asks its '
            f'first question. Build the config through '
            f'`tests/support/pm.py::with_flow`.')
        for kind in vocabulary.FLOW_KINDS:
            assert vocabulary.flow_of(cfg, kind).order, kind


def test_the_census_is_not_empty_and_names_real_builders():
    """Rule 4, applied to this file: a census of zero passes every loop above
    it in silence. The builders are resolved as attributes rather than trusted,
    so a renamed fixture fails here instead of quietly leaving the census."""
    assert len(BUILDERS) >= 9, sorted(BUILDERS)
    for name in BUILDERS:
        rel, _, attr = name.partition('::')
        source = (REPO_ROOT / rel).read_text(encoding='utf-8')
        assert f'def {attr}(' in source or f'class {attr}' in source, (
            f'{name} no longer exists — the census is naming a builder that '
            f'was renamed or deleted, which is exactly how it goes stale')


def test_the_flow_the_fixtures_declare_is_the_seed_itself():
    """One table, one source. A fixture flow that drifted from
    `render_seed()` would test a vocabulary this package never ships — the
    same second-spelling failure `installables/project-devkit.toml` is held
    against (tests/test_pm_flow.py:559)."""
    from support import pm as pmfx

    assert pmfx.FLOW_TOML == vocabulary.render_seed()
    assert pmfx.with_flow('[pm]\nchecks = ["D1"]\n').endswith(vocabulary.render_seed())
    # Idempotent: appending twice would be a TOML duplicate-table error, and a
    # fixture that already declares must come back untouched.
    once = pmfx.with_flow('')
    assert pmfx.with_flow(once) == once


def test_the_repo_this_suite_runs_in_declares_too():
    """Self-hosting, from the census's side: `subprocess`-driven cases run the
    CLI against THIS checkout, so its own devkit.toml is a fixture as much as
    any tempdir is."""
    done = subprocess.run(
        [sys.executable, '-m', 'agentic_sdlc.cli', 'pm', 'vocabulary',
         '--json'],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')})
    assert done.returncode == 0, done.stdout + done.stderr
    assert '"flow_declared": true' in done.stdout
