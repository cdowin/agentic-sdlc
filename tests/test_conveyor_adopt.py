"""test_conveyor_adopt.py — the adopt list: checks only, and the subtraction.

The headline is `test_checks_pass_never_runs_make`: adoption runs THIS
package's `check all` and never the consumer's `make check`. A consumer's own
gates verify the consumer's code against the consumer's rules, and a version
bump here cannot change their verdict — so running them during adoption
re-verifies the game, not the adoption. Asserted with a COMMAND RECORDER and a
SENTINEL FILE, never by reading the transcript.

Under D12 `adopt` writes nothing at all: `--force` is refused, and the whole
belt leaves the tree byte-identical. Every case here works on a scratch tree.

Two of those cases are about REACH rather than verdict. The belt used to
require a milestone of its own named for the version, so a project folding the
bump into an open milestone as a feature could not run it at all; and
`installables-current` graded all 27 installed files, so a project that
deliberately owns eleven of them was stuck at 6/7 forever. `tracks=AS_FEATURE`
builds the first shape and `[adopt] ours` declares the second.

The scratch trees here are POOLED (0.4.0): a grain's kind and its binding are
frontmatter, so `milestones/<slug>.md` may carry any `id:` and the belt finds
the milestone by reading, never by walking to a path built from the version.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import FLOW_TOML, with_flow  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import __version__  # noqa: E402
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo.checks import pm as pm_check  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, steps  # noqa: E402
from agentic_sdlc.repo.pm import ledger, model  # noqa: E402

VERSION = '9.9.9'
# The milestone this project is actually building when the pin bump is folded
# into it as a feature; it does NOT carry the version being adopted.
OPEN_VERSION = '0.1.0'
# Where the scratch project records the bump: a milestone of its own, or a
# feature bound to `OPEN_VERSION` and no milestone carrying `9.9.9` anywhere.
AS_MILESTONE, AS_FEATURE = 'milestone', 'feature'
# What the belts say when no milestone carries the id — the writing belt
# refuses with it, the checks-only belt reports it and runs anyway.
NOWHERE = f'no milestone {VERSION!r} in pm/roadmap/'
# Pooled: one ledger per milestone, in a table of its own named by id.
LEDGER_REL = f'pm/roadmap/{ledger.LEDGERS_POOL}/{VERSION}.jsonl'


def milestone_doc(mid: str) -> str:
    """A pooled milestone document. `id:` and `kind:` are the identity; the
    file name below is a slug and carries none of it."""
    return f"""---
id: "{mid}"
kind: milestone
name: A scratch milestone
status: building
branch: milestone/{mid}
---

# A scratch milestone
"""


BUMP_FEATURE = f"""---
id: {OPEN_VERSION}/adopt-the-devkit-pin
kind: feature
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
    milestone grain carrying the version being adopted as its `id:`.
    `AS_FEATURE` is the consumer shape that made this belt unreachable: an OPEN
    milestone of the project's own, the bump folded into it as a feature bound
    to that milestone, and no grain anywhere carrying the adopted version.

    Both shapes sit in the POOLS, and the slugs are deliberately not the ids:
    a belt that resolved `9.9.9` by building a path would find nothing in
    either tree, which is the confusion this milestone removed.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        roadmap = root / 'pm/roadmap'
        (roadmap / 'milestones').mkdir(parents=True)
        if tracks == AS_MILESTONE:
            (roadmap / 'milestones/scratch.md').write_text(
                milestone_doc(VERSION), encoding='utf-8')
        else:
            (roadmap / 'features').mkdir(parents=True)
            (roadmap / 'milestones/open.md').write_text(
                milestone_doc(OPEN_VERSION), encoding='utf-8')
            (roadmap / 'features/adopt-the-devkit-pin.md').write_text(
                BUMP_FEATURE, encoding='utf-8')
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
CHECK_LINE = re.compile(
    r'^\[adopt\] (?:ok|error|unverifiable): ([a-z][a-z0-9-]*)', re.MULTILINE)


def asked(out: str) -> list[str]:
    """Every check the run reported on, in the order it reported them. Read
    off the belt's OWN lines, so "it ran" is what the belt said, not what the
    test hoped."""
    return CHECK_LINE.findall(out)


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.parts}


def reconfigure(root: Path, config: str) -> None:
    """A second devkit.toml over the same scratch tree, flow included, with
    the read cache cleared — one run, two declarations."""
    (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
    load_config.cache_clear()


def decoy_bytes(root: Path) -> dict[str, bytes]:
    beside = root.parent / 'next-door'
    return {str(p.relative_to(beside)): p.read_bytes()
            for p in sorted(beside.rglob('*')) if p.is_file()}


# --- the census ---------------------------------------------------------------
def test_the_adopt_registry_is_exactly_the_shipped_eight():
    """Bites: a check added to the registry and not the list, or the
    reverse — a name nothing runs."""
    assert set(steps.ADOPT_STEPS) == set(steps.DEFAULT_ADOPT_STEPS)
    assert steps.DEFAULT_ADOPT_STEPS == (
        'pin-bumped', 'installables-current', 'config-updated',
        'hooks-self-test', 'telemetry-live', 'runner-targets-resolve',
        'checks-pass', 'pm-validates')
    assert driver.WRITES['adopt'] == ''
    for name in steps.DEFAULT_ADOPT_STEPS:
        assert name in steps.STEP_DOC, f'{name} ships no sentence'


# --- where the bump lives -----------------------------------------------------
def test_adopt_runs_every_check_where_the_bump_is_tracked_as_a_feature():
    """Bites: the ENTRY condition, which made the belt unreachable rather than
    advisory. A consumer folding toolkit work into an open milestone as a
    feature has no milestone carrying `9.9.9` and will not grow one — a pin
    bump is a day of work and a milestone there is a month of game. Before the
    condition was relaxed this printed the refusal a WRITING belt still prints
    — `no milestone '9.9.9' in pm/roadmap/ — refused, and nothing was written`
    — and exited 1 with ZERO checks asked; the adopting agent then did all
    seven by hand, in an order it invented, and missed one."""
    with tree({'Makefile': PIN + 'include Makefile.devkit\n'},
              tracks=AS_FEATURE) as root:
        before = snapshot(root)
        code, out = adopt()
        # Asked of the reader the belt itself uses, so "no such milestone" is
        # a fact about the frontmatter and not about a path that happens not
        # to exist.
        assert model.milestone_file(model.load(), VERSION) is None, (
            'the fixture grew a milestone carrying the adopted version')
        assert code != 2, out
        assert asked(out) == list(steps.DEFAULT_ADOPT_STEPS), out
        assert 'refused' not in out, out
        # It says THAT it recorded: nowhere, because it writes nothing.
        assert driver.NOTHING_RECORDED in out, out
        assert driver.ANYWHERE in out, out
        assert NOWHERE in out, out
        assert snapshot(root) == before, 'adopt wrote into the tree'


def test_adopt_names_the_ledger_when_the_bump_is_tracked_as_a_milestone():
    """The other half of the same sentence: with a milestone carrying the
    version, the run says WHERE a row would land — the ledger named for that
    id, not one buried under a slug — and still that none did, because `adopt`
    writes nothing (D12)."""
    with tree({'Makefile': PIN + 'include Makefile.devkit\n'}) as root:
        code, out = adopt()
        assert code != 2, out
        assert asked(out) == list(steps.DEFAULT_ADOPT_STEPS), out
        assert driver.NOTHING_RECORDED in out, out
        assert LEDGER_REL in out, out
        assert not (root / LEDGER_REL).exists(), (
            'a belt that writes nothing minted a ledger')


def test_a_belt_that_writes_still_needs_the_milestone_grain():
    """Bites: relaxing the entry condition for ALL FOUR belts instead of the
    one that writes nothing. `close feature` sets a status in a document bound
    to the milestone, and a forced one records a row in that milestone's
    ledger; with no milestone carrying the id there is nothing to bind to and
    nowhere to record, so it is refused before the first check — which is also
    why nothing spawns here."""
    with tree(tracks=AS_FEATURE) as root:
        before = snapshot(root)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = driver.main(['close', 'feature', f'{VERSION}/nope'])
        out = buf.getvalue()
        assert code == 1, out
        # The sentence names the FEATURE it could not place, not a milestone
        # nobody typed.
        assert f"no feature '{VERSION}/nope'" in out and 'refused' in out, out
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
# The two files `install-gates` writes; the library and the include that
# sources it, so one can be claimed while the other is graded.
GATE_MK, GATE_LIB_REL = 'Makefile.devkit', 'tools/dev/gdk_gate.sh'
CLAIMED_CLAUSE = 'claimed by [adopt] ours and not graded'
UNPLANNED_CLAUSE = 'ours name no file'


def fork(root: Path, rel: str) -> None:
    """One edited byte in an installed file — the invisible fork."""
    target = root / rel
    target.write_text(target.read_text(encoding='utf-8') + '\n# fork\n',
                      encoding='utf-8')


def test_installables_current_names_a_drifted_file_and_the_verb_that_shows_it():
    """Bites: an installed file silently diverged from what the pin ships —
    the invisible fork the install verbs exist to prevent. A byte-current
    install is true; one edited byte is false, named with its verb; and the
    same edited byte under `[adopt] ours` is the project's own file, true and
    NAMED. Before `ours` the third phase could not be written at all: a
    project that deliberately owns an installed file was stuck false
    forever."""
    from agentic_sdlc.repo import install

    with tree({'Makefile': PIN + f'include {GATE_MK}\n'}) as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert install.main('install-gates', []) == 0, buf.getvalue()
        current = check('installables-current', root)
        assert current.is_true, current
        assert CLAIMED_CLAUSE not in current.detail, (
            'a repo claiming nothing must print what it always printed')
        fork(root, GATE_MK)
        drifted = check('installables-current', root)
        assert drifted.truth is driver.Truth.FALSE, drifted
        assert GATE_MK in drifted.detail
        assert 'install-gates --diff' in drifted.detail, drifted.detail
        assert GATE_LIB_REL not in drifted.detail, (
            'a current file was named as drifted')
        reconfigure(root, f'[adopt]\nours = ["{GATE_MK}"]\n')
        claimed = check('installables-current', root)
        assert claimed.is_true, claimed
        assert f'1 {CLAIMED_CLAUSE}: {GATE_MK}' in claimed.detail, (
            claimed.detail)


def test_a_claimed_file_is_named_on_every_run_and_hides_no_other_drift():
    """Bites rule 4 in the mechanism built to relieve it: a claim that
    silences the line is a hiding place, and one claimed file must not carry
    an unclaimed drifted one out with it. Both files are forked and one is
    claimed — the other is still false, still named with its `--diff` — and
    when the graded file is restored the claim is STILL on the passing line."""
    from agentic_sdlc.repo import install

    config = f'[adopt]\nours = ["{GATE_MK}"]\n'
    with tree({'Makefile': PIN + f'include {GATE_MK}\n'},
              config=config) as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert install.main('install-gates', []) == 0, buf.getvalue()
        fork(root, GATE_MK)
        fork(root, GATE_LIB_REL)
        answer = check('installables-current', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert f'{GATE_LIB_REL} (differs' in answer.detail, answer.detail
        assert 'install-gates --diff' in answer.detail, answer.detail
        assert f'{GATE_MK} (differs' not in answer.detail, (
            'a claimed file was graded anyway: ' + answer.detail)
        assert f'1 {CLAIMED_CLAUSE}: {GATE_MK}' in answer.detail, answer.detail
        with contextlib.redirect_stdout(io.StringIO()):
            assert install.main('install-gates', ['--force']) == 0
        passing = check('installables-current', root)
        assert passing.is_true, passing
        assert f'1 {CLAIMED_CLAUSE}: {GATE_MK}' in passing.detail, (
            'the claim vanished the moment nothing else was wrong — which is '
            'the run where a hiding place would pay: ' + passing.detail)


def test_a_claim_naming_no_file_this_version_installs_is_reported_not_refused():
    """Bites: a typo'd claim read as a claim (silence), or as exit 2 (a
    consumer's belt breaking because a file retired from the install plans
    between two versions). It is a fact about the tree, so it is reported —
    rule 9's line between reading and deciding."""
    from agentic_sdlc.repo import install

    stranger = 'docs/not-installed-by-this-version.md'
    with tree({'Makefile': PIN + f'include {GATE_MK}\n'},
              config=f'[adopt]\nours = ["{stranger}"]\n') as root:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert install.main('install-gates', []) == 0, buf.getvalue()
        answer = check('installables-current', root)
        assert answer.is_true, answer
        assert f'1 claim(s) in [adopt] {UNPLANNED_CLAUSE}' in answer.detail, (
            answer.detail)
        assert stranger in answer.detail, answer.detail
        assert CLAIMED_CLAUSE not in answer.detail, (
            'a claim over nothing was counted as a file the project owns')


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
CONFIG_REFUSALS = [
    ('[adopt]\nsteps = ["tag"]\n', 'no check is registered'),
    ('[adopt]\nsteps = "pin-bumped"\n', 'list of strings'),
    ('[adopt]\npin_file = 3\n', 'one path'),
    ('[adopt]\nrunner_targets = "check"\n', 'non-empty list'),
    ('[adopt.commands]\npin-bumped = "x"\n', 'reads the tree'),
    # `ours` is a list of PATHS, so it reuses `core/config.relpath_tuple` —
    # `str_tuple` plus `_escapes_checkout`. SDLC.md §5: the matrix belongs to
    # the GRAMMAR, enumerated over every leaving spelling in
    # tests/test_grain_shape.py
    # (`test_every_path_shaped_spelling_that_leaves_the_checkout_is_refused`);
    # what this surface owes is proof that it GOES THROUGH it, which is the
    # traversal row. The other two are the shapes `str_tuple` itself refuses:
    # a bare string (iterable, character by character) and an empty list
    # (declaring nothing, which downstream reads as everything).
    ('[adopt]\nours = "Makefile.devkit"\n', 'list of strings'),
    ('[adopt]\nours = []\n', 'remove the key'),
    ('[adopt]\nours = ["../next-door/Makefile"]\n', 'inside this checkout'),
]


def test_the_config_refusal_matrix_is_exit_2_and_runs_no_check():
    """Bites: a typo narrowing the adopt list in silence, a command over a
    check that reads the tree — two authorities over one fact — or a claim
    the reader cannot read taken as a claim."""
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


# --- the claim cannot become a hiding place (review O1/O2/O3) ------------------
def test_claiming_every_gradeable_file_is_refused_not_passed():
    """Milestone risk 2, arriving exactly as the record predicted it: "a project
    can silence the check by claiming every file."

    Naming the claims is what makes the list a STATEMENT. Refusing to grade
    nothing is what stops it being a hiding place — `ok — 0 installed file(s)
    are current` is rule 4's zero census wearing a pass.
    """
    from agentic_sdlc.repo import install
    from agentic_sdlc.repo.pm import skills
    every = [rel for plan in install.PLANS.values() for _, rel in plan]
    every += [rel for _, rel in skills.GUIDANCE_PLAN]
    claims = ',\n  '.join(f'"{rel}"' for rel in every)
    with tree(config=f'[adopt]\nours = [\n  {claims}\n]\n') as root:
        answer = check('installables-current', root)
        assert not answer.is_true, answer.detail
        assert 'NOTHING was graded' in answer.detail
        assert 'rule 4' in answer.detail
        # ...and it still names what was claimed, which is the other half.
        assert 'claimed by [adopt] ours' in answer.detail


def test_the_census_covers_all_six_installers_not_the_five_in_one_module():
    """Review O2: `pm install-skills` is the sixth installer (CLAUDE.md's
    self-hosting list) and its two files drifted invisibly — with no `ours` key
    in play at all, which is worse than a claim, because nothing was even
    declared."""
    from agentic_sdlc.repo.pm import skills
    guidance = [rel for _, rel in skills.GUIDANCE_PLAN]
    installed = {rel: skills.guidance_body(name)
                 for name, rel in skills.GUIDANCE_PLAN}
    # Both present and byte-current: they must be COUNTED, not skipped.
    with tree(files=installed) as root:
        answer = check('installables-current', root)
        graded = _drift_rels(root)
        for rel in guidance:
            assert rel in graded, f'{rel} is outside the census\n{answer.detail}'
    # And one of them drifting must be FOUND rather than passed over.
    installed[guidance[0]] = 'somebody edited this\n'
    with tree(files=installed) as root:
        answer = check('installables-current', root)
        assert not answer.is_true, answer.detail
        assert guidance[0] in answer.detail


def test_a_claim_that_names_no_file_is_exit_2_before_any_check_runs():
    # Review O3: `relpath_tuple` guards what LEAVES the checkout; these stay
    # inside it and still name nothing, so they would sit in the config reading
    # like a claim while matching no installed path.
    for bad in ('""', '"."', '"./"', '"   "'):
        with tree(config=f'[adopt]\nours = [{bad}]\n'):
            code, out = adopt()
            assert code == 2, f'{bad}: {out}'
            assert 'names no file' in out, f'{bad}: {out}'


def _drift_rels(root) -> set[str]:
    from agentic_sdlc.repo.conveyor import driver, steps
    ctx = driver.Context(root=root, operation='adopt', version=VERSION)
    return {rel for _verb, rel, _v in steps._installable_drift(ctx)}


# --- 0.4.0/telemetry-arrives-with-the-bump ------------------------------------
# The two halves a courier needs: make must REACH the recipe, and the recipe
# must reach a CLI with a flow to answer with. A stub is honest here — the
# check measures the vehicle, and `check hooks` measures the courier.
VEHICLE = ('.PHONY: pm\npm:\n\t@printf "milestone feature story bug\\n"\n')
# The exact shape mode 2 is: a PM tree IS a `pm/` directory, so a `pm:` target
# that is not .PHONY is already satisfied and make never runs the recipe.
NOT_PHONY = 'pm:\n\t@printf "milestone feature story bug\\n"\n'
# Reached, and inert: the recipe runs and the CLI has nothing to answer with.
INERT = '.PHONY: pm\npm:\n\t@echo "no [pm.states.*] declared" >&2; exit 2\n'

WIRED = ('{"hooks": {"Stop": [{"hooks": [{"command": "bash '
         'tools/hooks/cc-ledger-session.sh"}, {"command": "bash '
         'tools/hooks/cc-ledger-subagent.sh"}]}]}}')


def _couriers(root, *names) -> None:
    """The corpus on disk. Content is irrelevant — `hooks-self-test` grades
    the scripts; this check grades the VEHICLE."""
    for name in names or ledger_couriers():
        path = root / 'tools' / 'hooks' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')


def ledger_couriers():
    from agentic_sdlc.repo.pm import model
    return model.LEDGER_COURIERS


def _ledger_line(root, row: dict) -> None:
    """One row in the tree's OWN ledger — where a row naming no grain lands
    (0.4.0/D3), which is where a courier files when nothing exported
    `GDK_LEDGER_GRAIN`. The path comes from `ledger.grainless_path`, never
    from a second spelling of it here."""
    path = ledger.grainless_path(model.PmConfig(root=root).roadmap)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(ledger.dumps(row) + '\n')


# The hook payload's own session id, which the courier passes through
# `--session-id` and a hand-written `pm ledger record` does not carry. It is
# what separates a row a COURIER wrote from one this checkout minted itself.
SESSION = 'sess-0000'


def _hook_row(root, hours: int = 1, session_id: str = SESSION) -> None:
    """One row a COURIER wrote, `hours` back — the evidence the check reports.

    Minted through `ledger.usage_row` with `EVENT_KINDS`' own kind, so the
    fixture cannot drift from the writer's vocabulary.
    """
    when = datetime.now(timezone.utc) - timedelta(hours=hours)
    fields = {'session_id': session_id} if session_id else {}
    _ledger_line(root, ledger.usage_row(
        ledger.EVENT_KINDS['SubagentStop'],
        ts=when.strftime(ledger.TS_FORMAT), duration_s=1, **fields))


def _gate_row(root) -> None:
    """A row THIS CHECKOUT writes itself: `gdk_gate.sh` files one per gate
    run, from inside the repo, and it is not evidence a hook ever fired."""
    _ledger_line(root, ledger.gate_row('check', 'PASS', 1))


def _settings(root, text: str, rel: str = '.claude/settings.json') -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_telemetry_live_names_which_of_the_three_ways_a_bump_records_nothing():
    """A consumer bumps the pin, gets the courier scripts, and pastes the
    settings block by hand — and nothing verified the paste. The failure is
    files present, hooks unarmed, zero rows, zero complaints, which is the
    state this package's own tree was in for a whole milestone.

    **A PROBE OF THIS TREE.** It ran the courier's `--self-test`, which builds
    its own `mktemp` repo with its own stub `pm:` target and exits 0 from an
    empty directory — so it proved the courier's argv and NOTHING about the
    caller, while printing *"their self-test passes against this tree's
    vehicle"*. That is a lie inside a PASS line (rule 4). It runs `make -s pm
    ARGS=vocabulary` here instead: one call that needs make to reach the recipe
    AND the CLI to have a flow to answer with.
    """
    # No courier at all: unverifiable, never a pass and never a failure — and
    # it names the opt-out, because a consumer who does not record is not
    # broken and must not be told to install something to get past a belt.
    with tree() as root:
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert 'install-hooks' in answer.detail, answer.detail
        assert '[adopt] steps' in answer.detail, answer.detail

    # HALF the corpus is not the corpus. `install-hooks` installs two couriers
    # and prints two entries; a one-name search read half-wired as wired.
    with tree() as root:
        _couriers(root, 'cc-ledger-session.sh')
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert 'cc-ledger-subagent.sh' in answer.detail, answer.detail

    # Mode 1 — the corpus is there, the vehicle answers, nothing fires it.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert 'no ledger setup for this tree, no telemetry' in answer.detail
        # The remedy this verb GAINED, not the hand-paste it replaced: this is
        # the only surface a fresh consumer hits, because `check pm` U2 returns
        # early on a tree that wires nothing.
        assert 'install-hooks --write-settings' in answer.detail, answer.detail
        assert 'GDK_LEDGER_ROOT' in answer.detail, answer.detail
        assert 'never writes that file' not in answer.detail, answer.detail

    # Mode 1b — HALF the entries pasted. Named, so the fix is the missing one.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, '{"hooks": {"Stop": [{"hooks": [{"command": "bash '
                        'tools/hooks/cc-ledger-session.sh"}]}]}}')
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert 'cc-ledger-subagent.sh' in answer.detail, answer.detail

    # Mode 2 — the `pm` target is not .PHONY. A PM tree IS a `pm/` directory,
    # so make finds the target satisfied, exits 0, and never runs the recipe.
    # This is the case the hermetic self-test could not see at all.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(NOT_PHONY, encoding='utf-8')
        _settings(root, WIRED)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert '.PHONY' in answer.detail, answer.detail

    # Mode 3 — reached, and inert: the recipe runs and the CLI refuses.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(INERT, encoding='utf-8')
        _settings(root, WIRED)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert '[pm.states.*]' in answer.detail, answer.detail

    # Mode 4 — WIRED, the vehicle answers, and nothing has ever come through.
    # The failure this feature was filed for: whether the harness LOADS
    # `.claude/settings.json` depends on the session's project root, so a
    # session rooted above the checkout records nothing while all three checks
    # above stay green. It stays TRUE — telemetry is never mandatory
    # (0.4.0/D5) — and the LINE stops claiming an outcome it did not observe.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.TRUE, answer
        assert 'last hook-written row: never' in answer.detail, answer.detail
        assert 'telemetry is live' not in answer.detail, answer.detail

    # Wired, the vehicle answers, and a COURIER has written: the kind and the
    # age are the evidence, and only now does the line say "live".
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED)
        _hook_row(root, hours=2)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.TRUE, answer
        assert 'telemetry is live' in answer.detail, answer.detail
        assert 'last hook-written row is dispatch, 2h ago' in answer.detail, \
            answer.detail

    # A row this CHECKOUT wrote is not evidence a courier ran: the make
    # wrapper files `gate` rows from inside the tree, and reading one as
    # telemetry is the PASS-over-nothing this rule exists to end (rule 4).
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED)
        _gate_row(root)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.TRUE, answer
        assert 'last hook-written row: never' in answer.detail, answer.detail

    # Nor is a hand-minted `dispatch`: `pm ledger record SubagentStop` writes
    # exactly the courier's kinds from inside the checkout, and only the hook
    # payload's session id tells the two apart.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED)
        _hook_row(root, hours=1, session_id='')
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.TRUE, answer
        assert 'last hook-written row: never' in answer.detail, answer.detail


def test_the_ledger_outranks_the_config_and_an_unreadable_one_is_neither():
    """The two ways reading the CONFIG answered a question about the PATH.

    `install-hooks` tells a consumer the block works in whatever settings file
    their harness reads, *"including one above this repo"* — and gating the
    whole verdict on an in-checkout file returned FALSE on a tree holding an
    hour-old courier row, with the proof already in hand. The other direction
    is the third answer: `recording_phrase` has always had `UNVERIFIABLE`, and
    a belt that branches on two of its three said *"telemetry is live"* over a
    ledger it could not read, while `check pm` U4 on that same tree said *"not
    a finding, and not a pass either"*.
    """
    # Wired ABOVE the checkout: no settings file here, and a courier row.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _hook_row(root, hours=1)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.TRUE, answer
        assert 'telemetry is live' in answer.detail, answer.detail
        assert 'the settings file the harness loaded is above it' \
            in answer.detail, answer.detail

    # The per-user override Claude Code writes and a repo gitignores — where
    # an ABSOLUTE block has to live in a public checkout.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED, rel=pm_check.AGENT_SETTINGS_LOCAL)
        _hook_row(root, hours=2)
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.TRUE, answer
        assert pm_check.AGENT_SETTINGS_LOCAL in answer.detail, answer.detail

    # An allowlist mention is not wiring. `install-hooks`' own next-step text
    # tells consumers to allow the couriers' --self-test; a substring search
    # over the raw file read that as the hooks being registered.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, json.dumps({'permissions': {'allow': [
            'Bash(bash tools/hooks/cc-ledger-session.sh --self-test)',
            'Bash(bash tools/hooks/cc-ledger-subagent.sh --self-test)']}}))
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert 'cc-ledger-session.sh' in answer.detail, answer.detail

    # An unreadable ledger: not a finding, and not a pass either.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, WIRED)
        path = ledger.grainless_path(model.PmConfig(root=root).roadmap)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('not a row\n', encoding='utf-8')
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert 'telemetry is live' not in answer.detail, answer.detail
        assert pm_check.UNVERIFIABLE in answer.detail, answer.detail

    # A settings file this reader cannot parse is the same non-answer.
    with tree() as root:
        _couriers(root)
        (root / 'Makefile').write_text(VEHICLE, encoding='utf-8')
        _settings(root, '{"hooks": ')
        answer = check('telemetry-live', root)
        assert answer.truth is driver.Truth.UNVERIFIABLE, answer
        assert '.claude/settings.json' in answer.detail, answer.detail

