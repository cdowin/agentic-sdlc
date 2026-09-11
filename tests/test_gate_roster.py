"""The declared gate roster IS the set that dispatches.

Nothing asserted this before 0.2.0, and that is the whole reason eight phantom
gate names survived an extraction that touched every other surface in `cli.py`.
Three of them (`uid`, `tres`, `props`) sat at `True` in the default roster, so a
stock consumer — no `devkit.toml`, the path every new adopter takes — ran
`check all` and got exit 2 over a name the tool's own error message listed as
known.

Pruning the names was the small half. The census is the deliverable: without it
the next removal reproduces this exactly, and the failure is silent until
somebody outside the repo runs the default path.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from agentic_sdlc import cli
from agentic_sdlc.repo import checks as checks_pkg

REPO = Path(__file__).resolve().parents[1]

# The gate modules AS SHIPPED, asked of the installed package rather than of
# `src/` — a wheel is what a consumer runs, and a module that reaches the wheel
# and no roster is the case this census exists for.
CHECKS_DIR = Path(checks_pkg.__file__).resolve().parent


def shipped_check_modules() -> set[str]:
    """Every gate module under `repo/checks/`, spelled as a roster key.

    `_check_module` maps `x-y` -> `x_y`, so this inverts that one mapping and
    nothing else. `__init__.py` is the package, and a `_`-prefixed module is a
    shared helper by the same convention `check hooks` uses for `tools/hooks/_*`
    — neither is a gate. Anything else here IS one, whether a roster says so or
    not, which is the whole point.
    """
    return {path.stem.replace('_', '-') for path in CHECKS_DIR.glob('*.py')
            if not path.name.startswith('_')}


class TestRosterEqualsDispatchable:
    """`KNOWN_GATES` and `_check_module` answer one question. One answer."""

    def test_every_declared_gate_resolves_to_a_module(self):
        """The direction that was broken: a name in the roster with no code.

        Asked of the function rather than restated as a list — a second literal
        here would be the same defect one layer down.
        """
        unresolved = [name for name in cli.KNOWN_GATES
                      if cli._check_module(name) is None]
        assert unresolved == [], (
            f'{unresolved} are in KNOWN_GATES and dispatch nothing; '
            f'`check all` exits 2 on any repo whose roster names one')

    def test_every_resolved_module_exposes_run(self):
        """A module that imports but has no `run()` fails at dispatch, not here.

        `_dispatch_check` calls `module.run()`; a gate that resolves to a module
        without one is a roster entry that passes the census above and still
        crashes the aggregate.
        """
        for name in cli.KNOWN_GATES:
            module = cli._check_module(name)
            assert callable(getattr(module, 'run', None)), (
                f'gate {name!r} resolves to {module!r}, which has no run()')

    def test_every_shipped_check_module_is_in_the_roster(self):
        """E3 — the direction nothing asserted: a gate with no roster entry.

        The two tests above close roster -> module. This closes module ->
        roster, and it is the half CLAUDE.md's own recipe puts a gate on
        (*"New check = module in `repo/checks/` + a key in `cli.py`'s
        KNOWN_GATES"*). Miss it and a gate is authored, reviewed, shipped in the
        wheel and dispatched by nobody: `_check_module` refuses any name outside
        the roster, so an unrostered module cannot be reached even by spelling
        it on the command line. That is the same shape as the eight phantom
        names this file was written for, walked the other way — and half a
        census is what let those live for two releases.
        """
        unrostered = sorted(shipped_check_modules() - set(cli.KNOWN_GATES))
        assert unrostered == [], (
            f'{unrostered} ship under {CHECKS_DIR.name}/ and are in no '
            f'KNOWN_GATES entry, so nothing can dispatch them — add the key '
            f'(and a README row and the grain\'s `changelog:`), or `_`-prefix the '
            f'module if it is a helper rather than a gate')

    def test_the_roster_and_the_shipped_modules_are_the_same_set(self):
        """Both directions in one assertion, stated as the invariant.

        Redundant with the two halves on purpose: they fail with the diagnosis
        (which name, which way), this one fails with the sentence. A future
        edit that weakens either half still has to get past the equality.
        """
        assert shipped_check_modules() == set(cli.KNOWN_GATES)

    def test_a_name_outside_the_roster_resolves_to_nothing(self):
        """The refusal, and it is the one that keeps a derived import safe.

        `_check_module` builds a module path from `name`. That name arrives from
        argv and from `[checks] all`, so roster membership is checked FIRST and
        it is the guard, not a convenience. These are the shapes that would
        otherwise reach `import_module`.
        """
        for hostile in ('uid', 'tres', 'props', 'defaults', 'rng',
                        'tres-comment', 'unit-disk', 'test-shape',
                        'all', '', '.', '..', '../../etc/passwd',
                        'os', 'sys', 'agentic_sdlc.cli', 'doc.__init__',
                        'repo_hygiene', 'DOC', 'doc ', ' doc'):
            assert cli._check_module(hostile) is None, (
                f'{hostile!r} resolved to a module and is not in the roster')

    def test_the_unknown_check_message_names_only_what_dispatches(self, capsys):
        """The error that named its own refused gate as a known one."""
        assert cli._unknown_check('nonsense') == 2
        listed = capsys.readouterr().err
        for gone in ('uid', 'tres', 'props', 'defaults', 'rng',
                     'unit-disk', 'test-shape'):
            assert f' {gone},' not in listed and not listed.endswith(f' {gone}'), (
                f'the unknown-check message still offers {gone!r}')
        for live in cli.KNOWN_GATES:
            assert live in listed

    def test_the_default_roster_is_a_subset_of_the_declared_one(self):
        """`all_roster()`'s default is derived from the same dict it validates."""
        default = tuple(n for n, on in cli.KNOWN_GATES.items() if on)
        assert set(default) <= set(cli.KNOWN_GATES)
        assert default, 'a default roster of nothing is `check all` passing vacuously'


class TestAStockConsumer:
    """The path a new adopter takes, run end to end.

    A unit assertion over `KNOWN_GATES` would have passed at every point during
    0.1.0 if it had only checked the dict against itself. This runs the CLI in a
    repo that has no `devkit.toml`, which is the condition that made the defect
    invisible here: this repo's own config pinned a roster that dodged it.
    """

    def test_check_all_never_exits_2_on_a_repo_with_no_config(self, tmp_path):
        repo = tmp_path / 'stock'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', '.'], cwd=repo, check=True)
        (repo / 'README.md').write_text('# stock\n')
        subprocess.run(['git', 'add', '-A'], cwd=repo, check=True)
        subprocess.run(
            ['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
             'commit', '-qm', 'init'], cwd=repo, check=True)

        done = subprocess.run(
            [sys.executable, '-m', 'agentic_sdlc.cli', 'check', 'all'],
            cwd=repo, capture_output=True, text=True,
            env={'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(REPO / 'src')})

        assert done.returncode != 2, (
            'a repo with no devkit.toml gets a usage error from the DEFAULT '
            f'roster:\n{done.stdout}\n{done.stderr}')
        assert 'unknown check' not in done.stderr
