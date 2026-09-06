"""test_conveyor_adopt.py — the adopt list: checks only, and the subtraction.

The headline is `test_checks_pass_never_runs_make`: adoption runs THIS
package's `check all` and never the consumer's `make check`. A consumer's own
gates verify the consumer's code against the consumer's rules, and a version
bump here cannot change their verdict — so running them during adoption
re-verifies the game, not the adoption. Asserted with a COMMAND RECORDER and a
SENTINEL FILE, never by reading the transcript.

Under D12 `adopt` writes nothing at all: `--force` is refused, and the whole
belt leaves the tree byte-identical. Every case here works on a scratch tree.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import FLOW_TOML, with_flow  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import __version__  # noqa: E402
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402
from agentic_sdlc.repo.pm import ledger  # noqa: E402

VERSION = '9.9.9'
# The milestone this project is actually building when the pin bump is folded
# into it as a feature; it is NOT named for the version being adopted.
OPEN_VERSION = '0.1.0'
# Where the scratch project records the bump: a milestone of its own, or a
# feature under `OPEN_VERSION` and no `9.9.9-*` directory anywhere.
AS_MILESTONE, AS_FEATURE = 'milestone', 'feature'


def milestone_doc(mid: str) -> str:
    return f"""---
id: "{mid}"
name: A scratch milestone
status: building
branch: milestone/{mid}
---

# A scratch milestone
"""


BUMP_FEATURE = f"""---
id: {OPEN_VERSION}/adopt-the-devkit-pin
milestone: "{OPEN_VERSION}"
name: adopt the v{VERSION} pin
status: building
---

# adopt the v{VERSION} pin

A day of work inside a milestone that is a month of game.
"""
PIN = f'DEVKIT_VERSION := v{__version__}\n'


@contextlib.contextmanager
def tree(files: dict[str, str] | None = None, config: str = '',
         sibling: bool = False, tracks: str = AS_MILESTONE):
    """A scratch consumer, entered. `sibling` plants a DECOY repo beside it
    (rule 8: `adopt` reads no second repo). `config` is the devkit.toml MINUS
    the flow declaration, which `with_flow` appends.

    `tracks` is WHERE the project records the bump. `AS_MILESTONE` is a
    `9.9.9-*` directory named for the version being adopted. `AS_FEATURE` is
    the consumer shape that made this belt unreachable: an OPEN milestone of
    the project's own, the bump folded into it as a feature, and no directory
    named for the version anywhere in the tree.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        roadmap = root / 'pm/roadmap'
        if tracks == AS_MILESTONE:
            (roadmap / f'{VERSION}-scratch').mkdir(parents=True)
            (roadmap / f'{VERSION}-scratch/milestone.md').write_text(
                milestone_doc(VERSION), encoding='utf-8')
        else:
            fdir = roadmap / f'{OPEN_VERSION}-open/features/adopt-the-devkit-pin'
            fdir.mkdir(parents=True)
            (roadmap / f'{OPEN_VERSION}-open/milestone.md').write_text(
                milestone_doc(OPEN_VERSION), encoding='utf-8')
            (fdir / 'feature.md').write_text(BUMP_FEATURE, encoding='utf-8')
        (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
        for rel, body in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        if sibling:
            decoy = Path(tmp) / 'next-door'
            (decoy / 'tools/hooks').mkdir(parents=True)
            (decoy / 'Makefile').write_text('DEVKIT_VERSION := v0.0.1\n',
                                            encoding='utf-8')
            (decoy / 'Makefile.devkit').write_text('# not yours\n',
                                                   encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.email=t@example.invalid',
                        '-c', 'user.name=t', 'commit', '-qm', 'scratch'],
                       cwd=root, check=True)
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def ctx(root: Path) -> driver.Context:
    return driver.Context(root=root, operation='adopt', version=VERSION)


def check(name: str, root: Path) -> driver.Answer:
    return steps.ADOPT_STEPS[name].check(ctx(root))


def adopt(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = driver.main(['adopt', VERSION, *argv])
    return code, buf.getvalue()


# `[adopt] ok: <name> — …`, `[adopt] error: <name>: …`, `[adopt]
# unverifiable: <name>: …` — the three line shapes `driver.run` prints.
CHECK_LINE = re.compile(r'^\[adopt\] (?:ok|error|unverifiable): ([a-z][a-z0-9-]*)',
                        re.MULTILINE)


def asked(out: str) -> list[str]:
    """Every check the run reported on, in the order it reported them. Read
    off the belt's OWN lines, so "it ran" is what the belt said, not what the
    test hoped."""
    return CHECK_LINE.findall(out)


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.parts}


def decoy_bytes(root: Path) -> dict[str, bytes]:
    beside = root.parent / 'next-door'
    return {str(p.relative_to(beside)): p.read_bytes()
            for p in sorted(beside.rglob('*')) if p.is_file()}


# --- the census ---------------------------------------------------------------
def test_the_adopt_registry_is_exactly_the_shipped_seven():
    """Bites: a check added to the registry and not the list, or the
    reverse — a name nothing runs."""
    assert set(steps.ADOPT_STEPS) == set(steps.DEFAULT_ADOPT_STEPS)
    assert steps.DEFAULT_ADOPT_STEPS == (
        'pin-bumped', 'installables-current', 'config-updated',
        'hooks-self-test', 'runner-targets-resolve', 'checks-pass',
        'pm-validates')
    assert driver.WRITES['adopt'] == ''
    for name in steps.DEFAULT_ADOPT_STEPS:
        assert name in steps.STEP_DOC, f'{name} ships no sentence'


# --- where the bump lives -----------------------------------------------------
def test_adopt_runs_every_check_where_the_bump_is_tracked_as_a_feature():
    """Bites: the ENTRY condition, which made the belt unreachable rather than
    advisory. A consumer folding toolkit work into an open milestone as a
    feature has no `9.9.9-*` directory and will not grow one — a pin bump is a
    day of work and a milestone there is a month of game. At HEAD this printed
    `no milestone directory pm/roadmap/9.9.9-* — refused, and nothing was
    written` and exited 1 with ZERO checks asked; the adopting agent then did
    all seven by hand, in an order it invented, and missed one."""
    with tree({'Makefile': PIN + 'include Makefile.devkit\n'},
              tracks=AS_FEATURE) as root:
        before = snapshot(root)
        code, out = adopt()
        assert not list(root.glob(f'pm/roadmap/{VERSION}-*')), (
            'the fixture grew a milestone named for the version')
        assert code != 2, out
        assert asked(out) == list(steps.DEFAULT_ADOPT_STEPS), out
        assert 'refused' not in out, out
        # It says THAT it recorded: nowhere, because it writes nothing.
        assert driver.NOTHING_RECORDED in out, out
        assert driver.ANYWHERE in out, out
        assert f'pm/roadmap/{VERSION}-*' in out, out
        assert snapshot(root) == before, 'adopt wrote into the tree'


def test_adopt_names_the_ledger_when_the_bump_is_tracked_as_a_milestone():
    """The other half of the same sentence: with a directory named for the
    version, the run says WHERE a row would land — and still that none did,
    because `adopt` writes nothing (D12)."""
    with tree({'Makefile': PIN + 'include Makefile.devkit\n'}) as root:
        code, out = adopt()
        assert code != 2, out
        assert asked(out) == list(steps.DEFAULT_ADOPT_STEPS), out
        assert driver.NOTHING_RECORDED in out, out
        assert f'{VERSION}-scratch/{ledger.LEDGER_FILE_NAME}' in out, out
        assert not (root / f'pm/roadmap/{VERSION}-scratch'
                    / ledger.LEDGER_FILE_NAME).exists(), (
            'a belt that writes nothing minted a ledger')


def test_a_belt_that_writes_still_needs_the_milestone_directory():
    """Bites: relaxing the entry condition for ALL FOUR belts instead of the
    one that writes nothing. `close feature` sets a status that lives in the
    milestone directory, and a forced one records there too; without the
    directory there is nowhere to write and nowhere to record, so it is
    refused before the first check — which is also why no check spawns here."""
    with tree(tracks=AS_FEATURE) as root:
        before = snapshot(root)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = driver.main(['close', 'feature', f'{VERSION}/nope'])
        out = buf.getvalue()
        assert code == 1, out
        assert 'no milestone directory' in out and 'refused' in out, out
        assert 'nothing was written' in out, out
        assert asked(out) == [], out
        assert snapshot(root) == before


def test_the_help_line_says_adopt_takes_a_pin_not_a_grain():
    """Bites: the second, cheaper miss. Beside `release <version>` and `close
    story|feature <id>` — all grain operations — a bare `adopt <version>`
    reads as one, and the adopting agent read past it twice. The meaning has
    to be ON the line, not only in `[adopt] pin_file`."""
    from agentic_sdlc import cli

    lines = [ln for ln in cli.__doc__.split('\n') if 'adopt <version>' in ln]
    assert len(lines) == 1, cli.__doc__
    line = lines[0]
    assert 'pin' in line.lower(), line
    assert 'grain' in line.lower(), line
    assert line.split('#')[-1].strip(), (
        'the line carries no description at all')


# --- the subtraction ----------------------------------------------------------
MAKEFILE_SENTINEL = (
    'DEVKIT_VERSION := v%s\n'
    'check:\n'
    '\t@touch MAKE-CHECK-RAN\n'
    'my-gate:\n'
    '\t@touch EXTRA-GATE-RAN\n' % __version__)


def test_checks_pass_never_runs_make(monkeypatch):
    """Bites: the one line that regresses the first time somebody makes
    adoption 'more thorough' — `checks-pass` reaching for the consumer's
    `make check`. The recorder sees what RAN; the sentinel proves the
    consumer's targets did not."""
    recorded: list[tuple[str, ...]] = []

    def recorder(context, *argv):
        recorded.append(argv)
        return 0, 'recorded', ('agentic-sdlc',) + argv

    config = ('[adopt]\nsteps = ["checks-pass"]\n\n'
              '[gates]\nextra = ["my-gate"]\n')
    with tree({'Makefile': MAKEFILE_SENTINEL}, config=config) as root:
        monkeypatch.setattr(steps, '_own_cli', recorder)
        answer = check('checks-pass', root)
        assert answer.is_true, answer
        assert recorded == [('check', 'all')], (
            f'checks-pass ran {recorded!r} — adoption verifies the ADOPTION')
        assert not (root / 'MAKE-CHECK-RAN').exists()
        assert not (root / 'EXTRA-GATE-RAN').exists()


def test_the_whole_belt_writes_nothing_and_touches_no_repo_but_this_one():
    """Bites: any write surviving in `adopt` (D12: checks only), and rule 8 —
    a check reading or writing the repo next door. Byte-identical before and
    after, both trees, whatever the checks answered."""
    with tree({'Makefile': MAKEFILE_SENTINEL}, sibling=True) as root:
        before, decoy = snapshot(root), decoy_bytes(root)
        code, out = adopt()
        assert code in (0, 1), out
        assert snapshot(root) == before, 'adopt wrote into the tree'
        assert decoy_bytes(root) == decoy, 'adopt touched the repo next door'
        assert not (root / 'MAKE-CHECK-RAN').exists()
        assert not (root / '.agentic-sdlc').exists()
    assert out.strip().split('\n')[-1].startswith('[adopt] '), out


def test_checks_pass_says_a_config_error_differently_from_findings(monkeypatch):
    """D11. Bites: a callee's exit 2 folded into a plain no."""
    answers = {}
    for code in (1, 2):
        monkeypatch.setattr(
            steps, '_own_cli',
            lambda c, *a, _c=code: (_c, 'said', ('agentic-sdlc',) + a))
        with tree() as root:
            answers[code] = check('checks-pass', root)
    assert answers[1].truth is driver.Truth.FALSE
    assert answers[2].truth is driver.Truth.UNVERIFIABLE
    assert 'config' in answers[2].detail.lower(), answers[2].detail


# --- pin-bumped ---------------------------------------------------------------
@pytest.mark.parametrize('makefile,truth,names', [
    ('DEVKIT_VERSION := v0.0.1\ninclude x\n', driver.Truth.FALSE,
     ('0.0.1', __version__)),
    (PIN + 'include x\n', driver.Truth.TRUE, (__version__,)),
    ('include x\n', driver.Truth.UNVERIFIABLE, ('DEVKIT_VERSION',)),
    (None, driver.Truth.UNVERIFIABLE, ('Makefile',)),
])
def test_pin_bumped_reads_the_line_names_it_and_writes_nothing(
        makefile, truth, names):
    """Bites: the pin edited by a machine in a file this package does not
    own, or a missing line read as a pass."""
    files = {'Makefile': makefile} if makefile is not None else {}
    with tree(files) as root:
        before = snapshot(root)
        answer = check('pin-bumped', root)
        assert answer.truth is truth, answer
        for name in names:
            assert name in answer.detail, answer.detail
        assert snapshot(root) == before


# --- installables-current -----------------------------------------------------
def test_installables_current_names_a_drifted_file_and_the_verb_that_shows_it():
    """Bites: an installed file silently diverged from what the pin ships —
    the invisible fork the install verbs exist to prevent. A byte-current
    install is true; one edited byte is false, named with its verb."""
    from agentic_sdlc.repo import install

    with tree({'Makefile': PIN + 'include Makefile.devkit\n'}) as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert install.main('install-gates', []) == 0, buf.getvalue()
        current = check('installables-current', root)
        assert current.is_true, current
        target = root / 'Makefile.devkit'
        target.write_text(target.read_text(encoding='utf-8') + '\nfork:\n',
                          encoding='utf-8')
        drifted = check('installables-current', root)
        assert drifted.truth is driver.Truth.FALSE, drifted
        assert 'Makefile.devkit' in drifted.detail
        assert 'install-gates --diff' in drifted.detail, drifted.detail
        assert 'tools/dev/gdk_gate.sh' not in drifted.detail, (
            'a current file was named as drifted')


# --- config-updated -----------------------------------------------------------
def test_config_updated_names_the_key_this_version_refuses_and_passes_stock():
    """Bites: `config-updated` printing accept over a section it never asked
    (A1) — the count in the pass line is the count that was asked."""
    with tree(config='[gates]\nextra = "my-gate"\n') as root:
        answer = check('config-updated', root)
        assert not answer.is_true, answer
        assert 'gates' in answer.detail, answer.detail
    with tree() as root:
        answer = check('config-updated', root)
        assert answer.is_true, answer
        assert str(len(steps._config_readers())) in answer.detail, answer.detail


# --- the three that ask make, the hooks, and pm --------------------------------
DEVKIT_MK = (REPO_ROOT
             / 'src/agentic_sdlc/repo/installables/Makefile.devkit').read_text(
                 encoding='utf-8')
GATE_LIB = (REPO_ROOT
            / 'src/agentic_sdlc/repo/installables/gdk_gate.sh').read_text(
                encoding='utf-8')


def _framework(extra: str = '') -> dict[str, str]:
    return {'Makefile': f'{PIN}{extra}include Makefile.devkit\n',
            'Makefile.devkit': DEVKIT_MK,
            'tools/dev/gdk_gate.sh': GATE_LIB}


def test_runner_targets_resolve_fails_on_a_named_tier_file_and_passes_an_empty_list():
    """Bites: `-include`'s silence read as a pass — a typo'd tier file turning
    a five-gate `precommit` into a one-gate one that exits 0."""
    with tree(_framework('GDK_PRECOMMIT_TIERS := unit\n')) as root:
        answer = check('runner-targets-resolve', root)
        assert not answer.is_true, answer
        assert 'Makefile.tiers' in answer.detail, answer.detail
    with tree(_framework()) as root:
        answer = check('runner-targets-resolve', root)
        assert answer.is_true, answer
        assert 'TIERS' in answer.detail, answer.detail


def test_hooks_self_test_and_runner_targets_refuse_a_repo_missing_the_file():
    """Bites: a check that installs what it was meant to read."""
    with tree() as root:
        hooks = check('hooks-self-test', root)
        assert not hooks.is_true and 'tools/hooks' in hooks.detail
        assert not (root / 'tools/hooks').exists(), 'the check installed a hook'
        runner = check('runner-targets-resolve', root)
        assert not runner.is_true and 'Makefile.devkit' in runner.detail
        assert not (root / 'Makefile.devkit').exists(), 'the check installed it'


def test_pm_validates_refuses_a_repo_with_no_pm_tree_and_passes_a_scratch_one():
    """Bites: a repo with no PM tree read as vacuously fine."""
    with tree() as root:
        assert check('pm-validates', root).is_true
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        (root / 'devkit.toml').write_text(FLOW_TOML, encoding='utf-8')
        (root / '.git').mkdir()
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            answer = check('pm-validates', root)
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()
    assert not answer.is_true, answer
    assert 'pm/roadmap' in answer.detail, answer.detail


# --- config and the verb ------------------------------------------------------
def reconfigure(root: Path, config: str) -> None:
    (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
    load_config.cache_clear()


CONFIG_REFUSALS = [
    ('[adopt]\nsteps = ["tag"]\n', 'no check is registered'),
    ('[adopt]\nsteps = "pin-bumped"\n', 'list of strings'),
    ('[adopt]\npin_file = 3\n', 'one path'),
    ('[adopt]\nrunner_targets = "check"\n', 'non-empty list'),
    ('[adopt.commands]\npin-bumped = "x"\n', 'reads the tree'),
]


def test_the_config_refusal_matrix_is_exit_2_and_runs_no_check():
    """Bites: a typo narrowing the adopt list in silence, or a command over
    a check that reads the tree — two authorities over one fact."""
    with tree() as root:
        for config, expected in CONFIG_REFUSALS:
            reconfigure(root, config)
            with pytest.raises(ConfigError) as err:
                driver.step_names('adopt')
            assert expected in str(err.value), (config, str(err.value))


def test_no_devkit_toml_and_the_stock_list_declared_are_the_same_bytes():
    """Rule 5, the equivalence test, over the adopt list."""
    declared = ('[adopt]\nsteps = [\n'
                + ''.join(f'  "{n}",\n' for n in steps.DEFAULT_ADOPT_STEPS)
                + ']\n')
    with tree():
        absent = driver.step_names('adopt')
    with tree(config=declared):
        explicit = driver.step_names('adopt')
    assert absent == explicit == steps.DEFAULT_ADOPT_STEPS


def test_the_verb_refusal_matrix_writes_nothing():
    """Bites: `--force` on a belt with nothing to force exiting 0."""
    with tree() as root:
        before = snapshot(root)
        for argv in (['adopt'], ['adopt', '--nope'], ['adopt', '0.2.0', 'x'],
                     ['adopt', '../etc'], ['adopt', VERSION, '--skip', 'x'],
                     ['adopt', VERSION, '--force']):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                assert driver.main(argv) == 2, argv
        assert snapshot(root) == before
