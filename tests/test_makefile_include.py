"""test_makefile_include.py — Makefile.devkit: the gate FRAMEWORK.

A consumer's Makefile is two lines plus its own targets; everything else is
this installable. Since 0.2.0 the installable is the framework ONLY — the
language-specific tiers arrive through `-include $(GDK_TIERS_MK)` and two
variables a kit sets. So the contract under test is:

  * the framework's target set is EXACTLY the declared one, it names no
    language kit's target, and every target parses and dry-runs on a fixture
    project that holds nothing but the include and its library;
  * `help` lists the framework set AND the project's own, from one grep;
  * `check` is the devkit gates followed by `[gates] extra` — read once,
    through the CLI, and a bad value STOPS the gate rather than narrowing it;
  * `precommit` / `milestone` compose from `GDK_PRECOMMIT_TIERS` /
    `GDK_MILESTONE_TIERS`, an EMPTY list announces itself, and a NAMED tier
    that resolves to no target is a parse-time failure naming the variable.
    Those two cases are held apart on exactly one condition, and a check that
    fires on both is as wrong as one that fires on neither;
  * each composition OPENS A SLOT of its own name around one sub-make of its
    members, so the ledger carries a `precommit` / `milestone` row beside the
    members' rows — and the console still carries only the members' lines.

`make -n` is the whole engine story here: nothing in this file builds anything,
and the dry runs are asserted to stay dry — which is why neither sub-make, the
one in `check` nor the one in each composition, is spelled `$(MAKE)`.
"""
from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support import consumers

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.repo import install  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which('make') is None
                                or shutil.which('bash') is None,
                                reason='needs make and bash')

INCLUDE = REPO_ROOT / 'src/agentic_sdlc/repo/installables/Makefile.devkit'
INSTALLABLES = INCLUDE.parent

# The framework set, spelled out so this file READS as the contract. It is
# cross-checked against the include below, so it cannot become a second roster
# that quietly disagrees.
STANDARD = ('help', 'pm', 'sdlc', 'check', 'precommit', 'milestone')

# Framework targets with no `## ` line: they exist to be depended ON, never to
# be typed, so `help` must not list them — but `.PHONY` must.
INTERNAL = ('gdk-tiers-none-precommit', 'gdk-tiers-none-milestone',
            'gdk-tiers-skipped-milestone')

# Target names that were the Godot roster this file carried through 0.1.0.
# None of them may come back: the framework composes from tiers now, and a
# language name in here is what blocked the split of this package in two.
LANGUAGE_KIT_TARGETS = (
    'parse', 'lint', 'warnings', 'unit', 'integration', 'integration-all',
    'integration-diff', 'integration-list', 'scenario', 'smoke', 'capture',
    'import-cache', 'scene', 'scene-diff', 'refs', 'orphans', 'autoloads',
    'uid-scan', 'hermetic-scan', 'hooks-self-test', 'runners-self-test',
    'doctor', 'pm-scan',
)

# Which targets wrap their tool here, because the tool has no verdict of its
# own. `check` is the only gate the framework itself runs; a tier target's
# verdict is the tier file's problem, and the `gdk_gate` define is what it
# reaches for.
WRAPPED = ('check',)

PROJECT_MAKEFILE = (
    'include Makefile.devkit\n'
    '\n'
    'my-scan: ## a gate this project owns\n'
    '\t@echo "[my-scan] PASS" && touch .my-scan-ran\n'
)

# A language kit's contribution: it DEFINES its targets, DECLARES which
# compositions they join, and carries its OWN `.PHONY` — the framework's
# cannot name what the framework has never heard of.
TIERS_MK = (
    'GDK_PRECOMMIT_TIERS := kit-parse kit-unit\n'
    'GDK_MILESTONE_TIERS := kit-parse kit-lint kit-unit\n'
    '\n'
    '.PHONY: kit-parse kit-lint kit-unit\n'
    'kit-parse: ## the kit\'s compile gate\n'
    '\t@echo "[KIT-PARSE] PASS"\n'
    'kit-lint: ## the kit\'s lint gate\n'
    '\t@echo "[KIT-LINT] PASS"\n'
    'kit-unit: ## the kit\'s unit gate\n'
    '\t@echo "[KIT-UNIT] PASS"\n'
)

# `check all` is stubbed (its roster is not this file's subject and every real
# gate would report a 0-file census on a fixture); `gates-extra` is the REAL
# verb, reading the fixture's own devkit.toml.
DEVKIT_STUB = """#!/usr/bin/env bash
case "$1" in
  check)       echo "[check:stub] PASS — stubbed for the fixture" ;;
  gates-extra) shift; exec env PYTHONPATH="{src}" python3 -m agentic_sdlc.cli \\
                    gates-extra "$@" ;;
  *)           echo "stub: unexpected $*" >&2; exit 2 ;;
esac
"""


# The pin since 1.0.0 (#101): the kit's row in uv.lock, and the entry point
# `uv sync` installs, stood in for so no case reaches uv or the network.
LOCK = ('version = 1\n\n[[package]]\nname = "agentic-sdlc"\n'
        'version = "0.0.0"\nsource = { registry = "x" }\n')
VENV_KIT = '.venv/bin/agentic-sdlc'
VENV_STUB = '#!/bin/sh\necho "venv-kit $*"\n'


@contextlib.contextmanager
def project(config: str = '', makefile: str = PROJECT_MAKEFILE,
            tiers: str | None = None, locked: bool = True):
    """A fixture project carrying the include and nothing else — and, unless
    `locked` is False, a uv.lock naming the kit and its synced entry point."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'app'
        root.mkdir()
        (root / 'pyproject.toml').write_text('[project]\nname = "fixture"\n',
                                             encoding='utf-8')
        # The whole install-gates payload, at its stock layout: the include
        # SOURCES the library, so a fixture carrying only the Makefile would
        # prove the targets parse and nothing about whether they run.
        for name, rel in install.PLANS['install-gates']:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(install.body_of(name), encoding='utf-8')
        (root / 'Makefile').write_text(makefile, encoding='utf-8')
        if locked:
            (root / 'uv.lock').write_text(LOCK, encoding='utf-8')
            stub = root / VENV_KIT
            stub.parent.mkdir(parents=True)
            stub.write_text(VENV_STUB, encoding='utf-8')
            stub.chmod(0o755)
        if config:
            (root / 'devkit.toml').write_text(config, encoding='utf-8')
        if tiers is not None:
            (root / 'Makefile.tiers').write_text(tiers, encoding='utf-8')
        (root / 'devkit-stub').write_text(
            DEVKIT_STUB.format(src=REPO_ROOT / 'src'), encoding='utf-8')
        (root / '.git').mkdir(exist_ok=True)  # a MARKER, not a repo: `repo_root` walks for it
        yield root


def make(root: Path, *args: str, **env_extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Under `make test` the recipe's shell carries MAKELEVEL/MAKEFLAGS, and a
    # sub-make that inherits them announces 'Entering directory' ahead of the
    # one verdict line these tests read. The make under test is a top-level one.
    # VERBOSE is the same shape one layer up: the installed CI exports it for
    # the whole `make milestone` step, so under it every "quiet by default"
    # run below streamed — green under bare pytest, red where CI runs it. The
    # default these tests speak of is VERBOSE UNSET; a case that wants the
    # stream passes VERBOSE='1' explicitly.
    for leaked in ('MAKELEVEL', 'MAKEFLAGS', 'MFLAGS', 'VERBOSE'):
        env.pop(leaked, None)
    # The cost recorder is OFF unless a case asks for it. `make check` files
    # a real `kind: gate` row through `GDK_LEDGER_CMD`, and a suite that
    # left it on would append one to this repo's own milestone ledger on
    # every run — a test writing into the tree it grades. ASSIGNED, not
    # `setdefault`: the include EXPORTS it, so under `make test` the
    # environment already carries the real recorder, and every fixture gate
    # here was spawning `uv run` against a fixture with no PM tree and
    # printing a "recorder exited 2" note — on stderr, where nothing read it,
    # until the compositions started carrying a member's stderr on stdout.
    # An EMPTY value is still a defined make variable, so the `?=` keeps it.
    env['GDK_LEDGER_CMD'] = ''
    env.update(env_extra)
    return subprocess.run(['make', *args], cwd=root, text=True,
                          capture_output=True, env=env, timeout=120)


def stubbed(root: Path) -> str:
    return f'DEVKIT=bash {root}/devkit-stub'


# A stand-in ledger recorder: appends the argv it was handed, one call per
# line. What the composition cases read is WHICH gate names got a row and how
# many times — never this repo's own ledger.
RECORDER = """#!/usr/bin/env bash
{ printf 'CALL'; for a in "$@"; do printf ' ARG[%s]' "$a"; done; printf '\\n'
} >> "$GDK_TEST_ROWS"
"""


def recording(root: Path) -> dict[str, str]:
    """Env that wires the stand-in recorder into a fixture run."""
    (root / 'recorder.sh').write_text(RECORDER, encoding='utf-8')
    (root / 'rows.txt').write_text('', encoding='utf-8')
    return {'GDK_LEDGER_CMD': f'bash {root}/recorder.sh',
            'GDK_TEST_ROWS': str(root / 'rows.txt')}


def rows_filed(root: Path) -> list[tuple[str, str]]:
    """(gate, verdict) per recorder call, in filing order."""
    found = []
    for line in (root / 'rows.txt').read_text(encoding='utf-8').splitlines():
        gate = re.search(r'ARG\[--gate\] ARG\[([^\]]+)\]', line)
        verdict = re.search(r'ARG\[--verdict\] ARG\[([^\]]+)\]', line)
        found.append((gate.group(1) if gate else '?',
                      verdict.group(1) if verdict else '?'))
    return found


def declared_targets() -> list[str]:
    """Every documented target in the include, asked of the file."""
    pattern = re.compile(r'^([a-z][a-z0-9-]*):.*?## ')
    return [m.group(1) for m in
            (pattern.match(line) for line
             in INCLUDE.read_text(encoding='utf-8').splitlines()) if m]


def recipes() -> dict[str, str]:
    found: dict[str, list[str]] = {}
    current = None
    for line in INCLUDE.read_text(encoding='utf-8').splitlines():
        if line.startswith('\t'):
            if current is not None:
                found[current].append(line)
            continue
        match = re.match(r'^([a-z][a-z0-9-]*):(?!=)', line)
        current = match.group(1) if match else None
        if current is not None:
            found.setdefault(current, [])
    return {name: '\n'.join(body) for name, body in found.items()}


# --- the set ------------------------------------------------------------------
def test_the_include_declares_exactly_the_standard_set():
    """A target added to the include and not to STANDARD would never be dry-run
    below; one removed would leave the parametrization asking for a target that
    no longer exists. The roster is asked of the FILE."""
    declared = declared_targets()
    assert len(declared) == len(set(declared)), f'declared twice: {declared}'
    assert sorted(declared) == sorted(STANDARD)


def test_the_framework_names_no_language_kits_target():
    """The whole point of the split: `Makefile.devkit` composes, it does not
    enumerate. A roster name back in here is the coupling that blocked
    godot-devkit 0.25.0 coming back with it."""
    defined = set(recipes()) | set(declared_targets())
    leaked = sorted(defined & set(LANGUAGE_KIT_TARGETS))
    assert not leaked, (
        f'{leaked} are a language kit\'s targets — they belong in the file '
        f'GDK_TIERS_MK names, not in the framework')


def test_make_n_succeeds_for_every_standard_target():
    """Parse the whole Makefile, resolve the target, expand its recipe — with
    the STOCK `DEVKIT` (the locked entry point), because a dry run that reached the network would
    be a dry run in name only. One project, every target: standing one up
    per target proved the same thing five times."""
    with project() as root:
        failed = {}
        for target in STANDARD:
            done = make(root, '-n', target)
            if done.returncode != 0:
                failed[target] = done.stdout + done.stderr
    assert not failed, failed


def test_a_dry_run_of_check_runs_nothing_at_all():
    """`make -n` executes any recipe line holding the literal `$(MAKE)`. The
    sub-make that runs `[gates] extra` is therefore spelled `$${MAKE:-make}`,
    and this is the assertion that keeps it that way: the project gate must not
    fire, and neither must the stub."""
    with project('[gates]\nextra = ["my-scan"]\n') as root:
        done = make(root, '-n', 'check', stubbed(root))
        assert done.returncode == 0, done.stdout + done.stderr
        assert not (root / '.my-scan-ran').exists(), done.stdout


def test_help_lists_the_standard_set_and_the_projects_own():
    with project() as root:
        done = make(root, 'help')
    assert done.returncode == 0, done.stdout + done.stderr
    # The roster is colourized; the names live between the escapes.
    plain = re.sub(r'\x1b\[[0-9;]*m', '', done.stdout)
    listed = {m.group(1) for m in
              re.finditer(r'^  ([a-z][a-z0-9-]*) +\S', plain, re.M)}
    assert set(STANDARD) <= listed, (
        f'missing from `make help`: {sorted(set(STANDARD) - listed)}')
    assert not (set(INTERNAL) & listed), (
        'an internal announce target is being offered as something to type')
    assert 'my-scan' in listed, "the project's own target is not listed"
    assert 'a gate this project owns' in plain


def test_help_lists_the_kits_tiers_and_names_the_composition():
    """One grep over MAKEFILE_LIST, so the tier file's own `## ` lines are in
    the same roster — and the footer says which tiers each composition holds,
    because that is the number an operator has no other way to see."""
    with project(tiers=TIERS_MK) as root:
        done = make(root, 'help')
    assert done.returncode == 0, done.stdout + done.stderr
    plain = re.sub(r'\x1b\[[0-9;]*m', '', done.stdout)
    for tier in ('kit-parse', 'kit-lint', 'kit-unit'):
        assert re.search(rf'^  {tier} +\S', plain, re.M), (
            f'{tier} is not in `make help`:\n{plain}')
    assert 'precommit=[kit-parse kit-unit]' in plain, plain
    assert 'milestone=[kit-parse kit-lint kit-unit]' in plain, plain


# --- check: the devkit gates, then the project's own --------------------------
# `check pm`'s verdict clause while a close ready to run stands open.
CLOSES = "; 1 close(s) ready to run — make pm ARGS='feature done ft-a'"
PM_READY = f'echo "[check:pm] PASS — clean{CLOSES}"; '


def test_check_runs_the_devkit_gates_and_then_the_projects_own():
    """And a ready close ends the verdict over all of them, the one line an
    operator reads (`ft-a-ready-close-is-not-left-standing`)."""
    stub = DEVKIT_STUB.replace('check)       echo', f'check)       {PM_READY}echo')
    with project('[gates]\nextra = ["my-scan"]\n') as root:
        (root / 'devkit-stub').write_text(stub.format(src=REPO_ROOT / 'src'),
                                          encoding='utf-8')
        done = make(root, 'check', stubbed(root))
        assert done.returncode == 0, done.stdout + done.stderr
        assert (root / '.my-scan-ran').exists(), (
            f'[gates] extra never ran:\n{done.stdout}{done.stderr}')
        assert (root / '.gate-reports' / 'check.log').is_file()
    verdicts = [ln for ln in done.stdout.splitlines() if ln.startswith('[CHECK]')]
    assert len(verdicts) == 2, done.stdout
    assert 'full log: .gate-reports/check.log' in verdicts[0]
    assert '[my-scan] PASS' in done.stdout
    assert verdicts[0].startswith(f'[CHECK] 2 check(s) PASS{CLOSES} — '), \
        verdicts[0]
    # #70: with extras declared, the verdict over ALL of them is the last line.
    assert done.stdout.splitlines()[-1] == f'[CHECK] PASS — 2 gate(s){CLOSES}', \
        done.stdout


def test_check_with_no_extras_is_just_the_devkit_gates():
    with project() as root:
        done = make(root, 'check', stubbed(root))
        assert done.returncode == 0, done.stdout + done.stderr
        assert not (root / '.my-scan-ran').exists()
    assert done.stdout.startswith('[CHECK]'), done.stdout


def test_an_ambient_verbose_does_not_turn_the_quiet_run_loud(monkeypatch):
    """The installed CI exports VERBOSE=1 for the whole `make milestone` step,
    and this suite runs inside it: every quiet-by-default case in this file
    streamed there and read as loud. The default is VERBOSE UNSET, whatever
    the environment the suite was started from says."""
    monkeypatch.setenv('VERBOSE', '1')
    test_check_with_no_extras_is_just_the_devkit_gates()


def test_verbose_streams_the_transcript_and_still_ends_with_the_verdict():
    with project() as root:
        done = make(root, 'check', stubbed(root), VERBOSE='1')
    assert done.returncode == 0, done.stdout + done.stderr
    assert '[check:stub] PASS' in done.stdout
    assert done.stdout.strip().splitlines()[-1].startswith('[CHECK]')


# Three project gates; `scan-b` is red when asked to be. Each leaves a marker.
THREE_SCANS = PROJECT_MAKEFILE + ''.join(
    f'scan-{x}:\n\t@touch .scan-{x}-ran; echo "[scan-{x}] ran"'
    + ('; [ -z "$$FAIL_B" ] || exit 3' if x == 'b' else '') + '\n'
    for x in 'abc')


@pytest.mark.parametrize('red, failed, code', [
    # A red extra does not stop the next one; its sub-make exits 2.
    ('FAIL_B', 'scan-b', 2),
    # A red roster does not stop the extras; the recipe exits the verb's 1.
    ('RED_ROSTER', 'check all', 1),
])
def test_every_gate_runs_and_the_last_line_is_the_verdict_over_all(
        red, failed, code):
    """#70: the last line was whichever extra ran last, and the exit came from
    an earlier gate. Every gate runs; the last line counts them all."""
    stub = DEVKIT_STUB.replace(
        'echo "[check:stub] PASS — stubbed for the fixture" ;;',
        'if [ -n "$RED_ROSTER" ]; then echo "[check:stub] FAIL"; exit 1; '
        'else echo "[check:stub] PASS"; fi ;;')
    with project('[gates]\nextra = ["scan-a", "scan-b", "scan-c"]\n',
                 makefile=THREE_SCANS) as root:
        (root / 'devkit-stub').write_text(stub.format(src=REPO_ROOT / 'src'),
                                          encoding='utf-8')
        done = make(root, 'check', stubbed(root), **{red: '1'})
        ran = [x for x in 'abc' if (root / f'.scan-{x}-ran').exists()]
    assert ran == ['a', 'b', 'c'], done.stdout + done.stderr
    # make exits 2 on any red recipe; the recipe's own code is make's "Error N".
    assert done.returncode == 2, done.stdout + done.stderr
    assert f'Error {code}' in done.stderr, done.stderr
    assert done.stdout.splitlines()[-1] == (
        f'[CHECK] FAIL — 1 of 4 gate(s) failed: {failed}'), done.stdout


def test_a_bad_gates_extra_stops_check_instead_of_narrowing_it():
    """The cardinal sin, with a config file in front of it: a value make cannot
    use must never read as "no extra gates"."""
    with project('[gates]\nextra = ["my scan"]\n') as root:
        done = make(root, 'check', stubbed(root))
        assert done.returncode == 2, done.stdout + done.stderr
        assert not (root / '.my-scan-ran').exists()
    assert 'not make targets' in done.stderr, done.stderr


def test_extra_naming_check_itself_is_refused_rather_than_recursing():
    """`extra = ["check"]` is a value the grammar CANNOT reject — it is a
    perfectly well-formed target name. The include catches it on re-entry, and
    so it also catches a project gate that runs `make check` two levels down."""
    with project('[gates]\nextra = ["check"]\n') as root:
        done = make(root, 'check', stubbed(root))
    assert done.returncode != 0
    assert 're-entered through [gates] extra' in done.stderr, done.stderr


def test_a_check_all_that_reused_files_no_cost_row_and_leaves_no_mark():
    """#98: a reused gate did no work, and a `check` row for it would move
    the digest `verify --milestone` grades. `check all` says so by creating
    the file GDK_GATE_UNMEASURED names; a run that creates nothing still files
    its row (`test_tiers_actually_run_in_the_composition_…` holds that)."""
    stub = DEVKIT_STUB.replace(
        'echo "[check:stub] PASS — stubbed for the fixture" ;;',
        ': > "$GDK_GATE_UNMEASURED"; '
        f'echo "[check:pm] PASS — clean{CLOSES}; reused — green at T on inputs X"; '
        'echo "[check:stub] PASS; reused — green at T on inputs X" ;;')
    with project() as root:
        (root / 'devkit-stub').write_text(stub.format(src=REPO_ROOT / 'src'),
                                          encoding='utf-8')
        done = make(root, 'check', stubbed(root), **recording(root))
        filed = rows_filed(root)
        left = sorted(p.name for p in (root / '.gate-reports').iterdir())
    assert done.returncode == 0, done.stdout + done.stderr
    assert filed == [], filed
    assert left == ['check.log'], left
    # A reused `check pm` keeps its close clause, and the reuse clause is not it.
    assert done.stdout.startswith(
        f'[CHECK] 2 check(s) PASS, 2 reused{CLOSES} — full log: '), done.stdout


def test_a_declared_extra_target_is_reused_until_one_of_its_inputs_moves():
    """#98: `[gates.inputs]` keys a `[gates] extra` target on the paths it
    names; unchanged, `make check` prints its PASS line and does not run it."""
    from support.pm import with_flow
    config = with_flow('[gates]\nextra = ["my-scan"]\n'
                       '[gates.inputs]\nmy-scan = ["scan.sh"]\n')
    with project(config) as root:
        (root / '.git').rmdir()
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        (root / 'scan.sh').write_text('echo scan\n', encoding='utf-8')
        (root / 'pm/roadmap').mkdir(parents=True)
        runs = []
        for edit in (None, None, 'echo scan two\n'):
            if edit:
                (root / 'scan.sh').write_text(edit, encoding='utf-8')
            (root / '.my-scan-ran').unlink(missing_ok=True)
            done = make(root, 'check', stubbed(root))
            assert done.returncode == 0, done.stdout + done.stderr
            runs.append(((root / '.my-scan-ran').exists(), done.stdout))
    assert [ran for ran, _ in runs] == [True, False, True], runs
    assert '[my-scan] PASS; reused — green at ' in runs[1][1], runs[1][1]
    assert runs[1][1].splitlines()[-1] == '[CHECK] PASS — 2 gate(s)', runs[1][1]


# --- the tier seam: what the compositions are made of -------------------------
def test_precommit_with_no_tiers_runs_check_alone_and_says_the_list_is_empty():
    """A project with no language kit is a SUPPORTED shape, not a degraded one
    — and a one-gate run that reads like a five-gate run is the cardinal sin
    with a Makefile in front of it. It passes, and it announces itself."""
    with project() as root:
        done = make(root, 'precommit', stubbed(root))
    assert done.returncode == 0, done.stdout + done.stderr
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    assert lines[0].startswith('[TIERS] GDK_PRECOMMIT_TIERS is empty'), done.stdout
    assert 'Makefile.tiers is not present' in lines[0], done.stdout
    # The announcement comes BEFORE the gate it is describing, and `check` is
    # the only thing that ran.
    assert [ln for ln in lines if ln.startswith('[CHECK]')], done.stdout
    assert len(lines) == 2, done.stdout


def test_milestone_with_no_tiers_names_its_own_variable():
    """Two compositions, two variables. An announcement that named the wrong
    one would send an operator to edit a list that was never consulted."""
    with project() as root:
        done = make(root, 'milestone', stubbed(root))
    assert done.returncode == 0, done.stdout + done.stderr
    first = done.stdout.splitlines()[0]
    assert first.startswith('[TIERS] GDK_MILESTONE_TIERS is empty'), done.stdout
    assert 'GDK_PRECOMMIT_TIERS' not in done.stdout, done.stdout


def test_tiers_compose_into_both_gates_in_declaration_order():
    """`-include` resolves at parse time, so the dry run names the whole
    composition — `check`, then the tiers in the order the kit declared —
    without running any of it.

    Why the old case did not catch the slot bug: it asserted that `make -n`
    printed each MEMBER's recipe, which is what a prerequisite-only target
    expands to — and a prerequisite-only target is the one shape that can
    never open a slot. The members are now the goals of the composition's
    sub-make, so the dry run prints ONE recipe naming them, and the members'
    own recipes are `make -n check` / `make -n kit-parse`'s to print."""
    with project(tiers=TIERS_MK) as root:
        pre = make(root, '-n', 'precommit', stubbed(root))
        mil = make(root, '-n', 'milestone', stubbed(root))
    assert pre.returncode == 0, pre.stdout + pre.stderr
    assert mil.returncode == 0, mil.stdout + mil.stderr

    def goals(out: str) -> list[str]:
        found = re.findall(r'\$\{MAKE:-make\} ([a-z -]+?);', out)
        assert len(found) == 1, out
        return found[0].split()
    assert goals(pre.stdout) == ['check', 'kit-parse', 'kit-unit'], pre.stdout
    assert goals(mil.stdout) == ['check', 'kit-parse', 'kit-lint', 'kit-unit'], mil.stdout
    # Dry means dry: the sub-make must not be one `-n` would execute, and no
    # member's recipe ran or was printed as if it had.
    assert '$(MAKE)' not in pre.stdout + mil.stdout
    assert 'echo "[KIT-' not in pre.stdout + mil.stdout, pre.stdout + mil.stdout
    assert 'gdk_gate_log precommit' in pre.stdout, pre.stdout
    assert 'gdk_gate_log milestone' in mil.stdout, mil.stdout
    # A declared list is not an empty one: no announcement in either.
    assert '[TIERS]' not in pre.stdout + mil.stdout, pre.stdout + mil.stdout


def test_tiers_actually_run_in_the_composition_and_the_composition_files_a_row():
    """The members run, in order, and their lines are the WHOLE console; the
    ledger gets one row per slot that opened, and the composition's own row
    — named `precommit`, verdict PASS, filed once — is among them.

    Why the old case did not catch the slot bug: it ran the recorder OFF, so
    it proved the members ran and never asked what got filed — and the
    answer was "every member and never the composition", which is why
    `verify --plan` said `unknown` for the wide rungs on every project
    (0.2.0/bugs/a-composition-has-no-slot). The kit tiers here are plain
    echos that open no slot, so they file nothing; the one-per-member count
    against tiers that do open slots is test_makefile_gates.py's, on this
    repo's real `unit` tier."""
    with project(tiers=TIERS_MK) as root:
        done = make(root, 'precommit', stubbed(root), **recording(root))
        assert done.returncode == 0, done.stdout + done.stderr
        filed = rows_filed(root)
        assert (root / '.gate-reports' / 'precommit.log').is_file()
        transcript = (root / '.gate-reports' / 'precommit.log').read_text(encoding='utf-8')
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    assert lines[0].startswith('[CHECK]'), done.stdout
    assert lines[1:] == ['[KIT-PARSE] PASS', '[KIT-UNIT] PASS'], done.stdout
    assert filed == [('check', 'PASS'), ('precommit', 'PASS')], filed
    # The composition's verdict line is in its transcript, not on the console.
    assert '[PRECOMMIT] PASS (check kit-parse kit-unit)' in transcript, transcript
    assert '[PRECOMMIT]' not in done.stdout, done.stdout


def test_a_failing_member_fails_the_composition_and_its_row_says_so():
    """The row that matters most is the one for a run that FAILED: a
    composition row reading PASS above a member that did not is a durable
    record contradicting the console, hard rule 4's read-side sin. The
    composition exits non-zero, adds nothing to the console beyond what the
    member printed, and files exactly one row, verdict FAIL."""
    failing = (TIERS_MK.replace('@echo "[KIT-UNIT] PASS"',
                                '@echo "[KIT-UNIT] FAIL"; exit 3'))
    with project(tiers=failing) as root:
        done = make(root, 'precommit', stubbed(root), **recording(root))
        filed = rows_filed(root)
    assert done.returncode != 0, done.stdout + done.stderr
    assert filed == [('check', 'PASS'), ('precommit', 'FAIL')], filed
    assert '[KIT-UNIT] FAIL' in done.stdout, done.stdout
    assert '[PRECOMMIT]' not in done.stdout, done.stdout


def test_neither_tier_path_warns_about_an_undefined_variable():
    """`--warn-undefined-variables` is on. Both tier variables are defined
    before use in the include-ABSENT path too, which is the path a project
    with no language kit takes on every single run. Two projects, four goals
    each — not eight projects."""
    for tiers in (None, TIERS_MK):
        with project(tiers=tiers) as root:
            for goal in ('help', 'check', 'precommit', 'milestone'):
                done = make(root, '-n', goal, stubbed(root))
                assert done.returncode == 0, (goal, done.stdout + done.stderr)
                warnings = [ln for ln in done.stderr.splitlines()
                            if 'undefined variable' in ln]
                assert not warnings, (
                    f'{goal}, tiers={"set" if tiers else "absent"}: {warnings}')


# --- story 02: a named tier that resolves to nothing is loud -------------------
# The distinguishing condition is whether a tier LIST is empty, and nothing
# else. Both of the next two have no Makefile.tiers on disk.
def test_a_missing_tier_file_with_empty_lists_is_the_supported_shape():
    """`-include` of a missing file is silent BY DESIGN — that silence is what
    makes a project with no tiers work at all. It must not be turned into an
    error, or the pure-framework consumer stops existing."""
    with project() as root:
        done = make(root, 'precommit', stubbed(root))
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'Makefile.tiers' not in done.stderr, done.stderr
    assert 'No rule to make target' not in done.stderr, done.stderr


def test_a_missing_tier_file_with_a_named_tier_is_the_typo_and_fails():
    """Same missing file, one condition different: a tier list names something.
    That is a typo'd GDK_TIERS_MK, and the silence that serves the case above
    is exactly what would hide it."""
    with project() as root:
        done = make(root, 'precommit', stubbed(root),
                    'GDK_PRECOMMIT_TIERS=kit-parse')
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'GDK_PRECOMMIT_TIERS' in done.stderr, done.stderr
    assert 'GDK_TIERS_MK=Makefile.tiers does not exist' in done.stderr, done.stderr


def test_a_named_tier_with_no_target_fails_naming_the_tier_and_the_variable():
    """The tier file is present and one name in it resolves to nothing. Make's
    own "No rule to make target" would name the tier and NOT the variable that
    named it, which is the half an operator actually has to edit."""
    broken = ('GDK_PRECOMMIT_TIERS := kit-parse nonexistent-tier\n'
              '\n.PHONY: kit-parse\nkit-parse:\n\t@echo "[KIT-PARSE] PASS"\n')
    with project(tiers=broken) as root:
        done = make(root, 'precommit', stubbed(root))
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'nonexistent-tier' in done.stderr, done.stderr
    assert 'GDK_PRECOMMIT_TIERS' in done.stderr, done.stderr


def test_the_milestone_list_is_named_when_it_is_the_one_at_fault():
    broken = ('GDK_MILESTONE_TIERS := kit-parse nonexistent-tier\n'
              '\n.PHONY: kit-parse\nkit-parse:\n\t@echo "[KIT-PARSE] PASS"\n')
    with project(tiers=broken) as root:
        done = make(root, 'milestone', stubbed(root))
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'GDK_MILESTONE_TIERS names a tier no makefile defines' in done.stderr
    assert 'GDK_PRECOMMIT_TIERS names' not in done.stderr, done.stderr


def test_a_bad_tier_list_fails_before_the_gates_run():
    """An operator should not pay for `check` to be told the list was wrong.
    The guard is parse-time, so nothing has run when it fires — proven by the
    transcript directory the first gate would have created."""
    broken = ('GDK_PRECOMMIT_TIERS := nonexistent-tier\n'
              '\n.PHONY: kit-parse\nkit-parse:\n\t@echo "[KIT-PARSE] PASS"\n')
    with project('[gates]\nextra = ["my-scan"]\n', tiers=broken) as root:
        done = make(root, 'precommit', stubbed(root))
        assert done.returncode == 2, done.stdout + done.stderr
        assert not (root / '.gate-reports').exists(), (
            'check ran before the tier list was refused')
        assert not (root / '.my-scan-ran').exists()
    assert '[CHECK]' not in done.stdout, done.stdout


def test_a_bad_tier_list_is_refused_under_n_too():
    """A dry run that printed a plan holding a target that does not exist would
    be a plan nobody can execute."""
    broken = ('GDK_PRECOMMIT_TIERS := nonexistent-tier\n'
              '\n.PHONY: kit-parse\nkit-parse:\n\t@echo ok\n')
    with project(tiers=broken) as root:
        done = make(root, '-n', 'precommit', stubbed(root))
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'nonexistent-tier' in done.stderr, done.stderr


def test_an_unrelated_goal_is_not_held_hostage_by_a_tier_typo():
    """The guard is about the compositions, but it is parse-time, so it fires
    on every goal. That is deliberate and this records it: a tree whose tier
    list is wrong is wrong before you pick a target, and `help` saying so is
    better than `help` working and `precommit` quietly shrinking."""
    broken = ('GDK_PRECOMMIT_TIERS := nonexistent-tier\n'
              '\n.PHONY: kit-parse\nkit-parse:\n\t@echo ok\n')
    with project(tiers=broken) as root:
        done = make(root, 'help')
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'nonexistent-tier' in done.stderr, done.stderr


# --- the shape of the file ----------------------------------------------------
def test_a_tool_with_no_verdict_of_its_own_gets_one_here():
    bodies = recipes()
    bare = [target for target in WRAPPED
            if '$(call gdk_gate,' not in bodies[target]
            and '$(call gdk_gate_sh,' not in bodies[target]
            and 'gdk_gate_verdict' not in bodies[target]]
    assert not bare, (
        f'{bare} print whatever their tool prints instead of one verdict line')


def test_the_compositions_open_a_slot_of_their_own_name():
    """Why the old case did not catch the slot bug: it asserted the
    compositions had NO recipe at all, as the guarantee that they printed
    nothing of their own — and a target with no recipe is precisely one that
    can never open a slot, so the assertion pinned the bug in place. The
    shape now: each composition's recipe is `gdk_composition`, which opens a
    slot under the composition's name, runs the members through one sub-make
    inside the capture, and sends its own verdict to its transcript rather
    than the console. "Nothing of their own on the console" is proven by
    the run cases above, on output, where it belongs; the empty-tier
    announcement stays a PREREQUISITE, ahead of the slot."""
    bodies = recipes()
    for name in ('precommit', 'milestone'):
        assert f'$(call gdk_composition,{name},' in bodies[name], bodies[name]
    text = INCLUDE.read_text(encoding='utf-8')
    define = text.split('define gdk_composition\n', 1)[1].split('\nendef', 1)[0]
    for helper in ('gdk_gate_log $(1)', 'gdk_gate_capture', 'gdk_gate_verdict $(2)'):
        assert helper in define, define
    assert 'env $(if $(value 4),$(4) )VERBOSE=' in define, define
    assert '$(MAKE)' not in define, 'a literal $(MAKE) runs the members under -n'
    assert re.search(r'gdk_gate_verdict [^\n]* >> "\$\$log"', define), (
        'the composition verdict goes to its transcript, not the console')


def test_phony_lists_this_files_targets_AND_the_declared_tiers():
    """None of these produce a file of their own name.

    Two groups, and the second one is a bug fix. The framework's own targets
    are named literally. The declared TIERS are `.PHONY` through the two
    variables — `$(GDK_PRECOMMIT_TIERS)` and `$(GDK_MILESTONE_TIERS)` — which
    expand to whatever the tier file declared.

    That second line was added 2026-09-05 after a feature review built the case:
    `GDK_PRECOMMIT_TIERS := parse test` in a tree that also has a `test/`
    DIRECTORY ran `check` and `parse`, **skipped `test`**, exited 0, and printed
    nothing about it. A target with no prerequisites is up-to-date when a file
    of that name exists, and the orphan guard above cannot see it: `test` IS a
    defined target, so it is not an orphan — it is a defined target make decided
    it did not need to build.

    A kit's tier file should declare its own `.PHONY` too. This is the braces:
    one line, against a gate that reports success without running.
    """
    text = INCLUDE.read_text(encoding='utf-8')
    phony: set[str] = set()
    for match in re.finditer(r'^\.PHONY:((?:.*\\\n)*.*)$', text, re.M):
        phony |= set(match.group(1).split()) - {'\\'}

    tier_vars = {'$(GDK_PRECOMMIT_TIERS)', '$(GDK_MILESTONE_TIERS)'}
    assert tier_vars <= phony, (
        'a declared tier shadowed by a same-named file is skipped in SILENCE — '
        f'.PHONY must carry {sorted(tier_vars - phony)}')

    literal = phony - tier_vars
    assert literal == set(STANDARD) | set(INTERNAL)
    assert literal == set(recipes()), (
        f'.PHONY and the file disagree: '
        f'{sorted(literal ^ set(recipes()))}')



def test_the_header_documents_the_tier_file_shape():
    """The tier file is written by a kit author reading this header and nothing
    else — the seam, the two variables, and the fact that the tier file carries
    its own `.PHONY`."""
    header = INCLUDE.read_text(encoding='utf-8').split('\nSHELL :=')[0]
    for token in ('GDK_TIERS_MK', 'GDK_PRECOMMIT_TIERS', 'GDK_MILESTONE_TIERS',
                  '.PHONY'):
        assert token in header, f'the header never mentions {token}'


# --- the file is generic ------------------------------------------------------
def test_the_include_names_no_consumer_project():
    text = INCLUDE.read_text(encoding='utf-8').lower()
    for name in consumers.require():
        assert name not in text, f'the include names {name}'


def test_a_tree_whose_lock_names_no_kit_is_a_parse_error_naming_the_fix():
    """#101: the lock is the only way the kit is installed. With no lock, or
    one that does not name the kit, every target stops at exit 2 BY NAME,
    printing the one `uv add` line — the same line the CLI prints
    (`vehicle.add_line`), so the two spellings of the index cannot drift."""
    from agentic_sdlc.repo import vehicle

    expected = vehicle.add_line('<X.Y.Z>')
    for lock in (None, LOCK.replace('agentic-sdlc', 'other-kit')):
        with project(makefile='include Makefile.devkit\n',
                     locked=False) as root:
            if lock is not None:
                (root / 'uv.lock').write_text(lock, encoding='utf-8')
            done = make(root, 'help')
        assert done.returncode == 2, done.stdout + done.stderr
        assert 'uv.lock does not name agentic-sdlc' in done.stderr, done.stderr
        assert expected in done.stderr, done.stderr
        assert vehicle.EXPLICIT in done.stderr, done.stderr
    # Unless the project supplies the command itself — then there is nothing
    # for a lock to resolve. This is how the package that ships the include
    # consumes it: its own tree, installed on itself.
    with project(makefile='DEVKIT := echo devkit\ninclude Makefile.devkit\n',
                 locked=False) as root:
        done = make(root, '-n', 'pm')
    assert done.returncode == 0, done.stderr
    assert 'echo devkit pm' in done.stdout, done.stdout


# A stand-in `uv`: records its argv, and installs the entry point unless told
# to fail — `uv sync` without the network.
FAKE_UV = """#!/bin/sh
echo "$*" >> uv-calls
[ -n "$FAKE_UV_FAIL" ] && exit 1
mkdir -p .venv/bin && printf '#!/bin/sh\\necho "venv-kit $*"\\n' > .venv/bin/agentic-sdlc
chmod +x .venv/bin/agentic-sdlc
"""


def test_the_locked_kit_runs_from_the_venv_and_is_synced_when_missing():
    """The stock `DEVKIT` is `.venv/bin/agentic-sdlc`: present and newer than
    the lock, nothing is synced; missing, `uv sync --frozen` runs once at
    parse time and the target proceeds; a sync that installs nothing is
    exit 2 naming it, never a recipe running a command that is not there."""
    with project() as root:
        (root / 'uv').write_text(FAKE_UV, encoding='utf-8')
        done = make(root, 'pm', f'UV=sh {root}/uv')
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'venv-kit pm --help' in done.stdout, done.stdout
        assert not (root / 'uv-calls').exists(), 'a fresh kit was re-synced'
        (root / VENV_KIT).unlink()
        done = make(root, 'pm', f'UV=sh {root}/uv')
        assert done.returncode == 0, done.stdout + done.stderr
        assert (root / 'uv-calls').read_text() == 'sync --frozen\n'
        assert 'venv-kit pm --help' in done.stdout, done.stdout
        assert 'Makefile.devkit:' not in done.stdout, (
            'the sync notice is on stdout, where a piped read verb reads')
        (root / VENV_KIT).unlink()
        done = make(root, 'pm', f'UV=sh {root}/uv', FAKE_UV_FAIL='1')
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'did not install .venv/bin/agentic-sdlc' in done.stderr, done.stderr


UVX_SHIM = '#!/bin/sh\necho "uvx $*" >> "$(dirname "$0")/uvx-calls"\nexit 1\n'


# What uv prints when `uv build` cannot reach an index for its build backend:
# `--offline` (or UV_OFFLINE) with a cold cache, and an index it cannot
# connect to. Matched on uv's own words, so no other failure skips.
UV_NO_INDEX = ('the network was disabled', 'Failed to fetch: `')


@pytest.mark.skipif(shutil.which('uv') is None, reason='needs uv')
def test_a_consumer_locked_from_a_built_index_runs_the_venv_kit_and_no_uvx(
        tmp_path):
    """#101's ship criterion, end to end on a scratch consumer: `uv build`
    this tree, publish it with `tools/publish_index.py` to a `file://` index,
    lock the pyproject `init` seeds against it, and `make` syncs the kit and
    runs `.venv/bin/agentic-sdlc` — with a `uvx` on PATH that fails the run
    if anything reaches for it."""
    import importlib.util

    from agentic_sdlc import __version__
    from agentic_sdlc.repo import init, vehicle

    spec = importlib.util.spec_from_file_location(
        'publish_index', REPO_ROOT / 'tools' / 'publish_index.py')
    publish_index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publish_index)
    env = {k: v for k, v in os.environ.items()
           if k not in ('VIRTUAL_ENV', 'UV_PROJECT_ENVIRONMENT', 'MAKELEVEL',
                        'MAKEFLAGS', 'MFLAGS', 'VERBOSE')}
    shims = tmp_path / 'shims'
    shims.mkdir()
    (shims / 'uvx').write_text(UVX_SHIM, encoding='utf-8')
    (shims / 'uvx').chmod(0o755)
    env['PATH'] = f'{shims}{os.pathsep}{env["PATH"]}'
    env['GDK_LEDGER_CMD'] = ''
    dist = tmp_path / 'dist'
    built = subprocess.run(['uv', 'build', '-q', '--out-dir', str(dist)],
                           cwd=REPO_ROOT, env=env, text=True,
                           capture_output=True, timeout=300)
    if built.returncode != 0:
        said = built.stdout + built.stderr
        # Only a build that cannot reach an index for hatchling skips; any
        # other build error is this tree's, and fails.
        offline = [m for m in UV_NO_INDEX if m in said]
        if offline:
            pytest.skip(f'uv build cannot reach an index: {offline[0]!r}')
        pytest.fail(f'uv build failed (exit {built.returncode}):\n{said}')
    site = tmp_path / 'site'
    publish_index.publish(dist, site)
    with project(locked=False) as root:
        (root / 'pyproject.toml').write_text(
            init.seed_body(init.SEED_PYPROJECT[0], root).replace(
                vehicle.INDEX_URL, f'{site.as_uri()}/simple/'),
            encoding='utf-8')
        subprocess.run(['uv', 'lock', '-q'], cwd=root, env=env, check=True,
                       timeout=300)
        assert vehicle.locked_version(root) == __version__
        ran = subprocess.run(['make', 'sdlc', 'ARGS=--version'], cwd=root,
                             env=env, text=True, capture_output=True,
                             timeout=300)
        dry = subprocess.run(['make', '-n', 'check'], cwd=root, env=env,
                             text=True, capture_output=True, timeout=120)
        synced = (root / VENV_KIT).is_file()
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert f'agentic-sdlc {__version__}' in ran.stdout, ran.stdout
    assert synced, 'make did not sync the kit into .venv'
    assert f'{VENV_KIT} check all' in dry.stdout, dry.stdout + dry.stderr
    assert not (shims / 'uvx-calls').exists(), (
        shims / 'uvx-calls').read_text(encoding='utf-8')


# --- the vehicle: a printed command runs in a stock consumer (#22, #36) -------
# The tools a pasted line needs, and nothing else: a PATH holding the builder's
# own `agentic-sdlc` would pass this file for a reason no consumer has.
VEHICLE_TOOLS = ('make', 'bash', 'sh', 'env', 'git')
VEHICLE_STORY = '0.1/alpha/s0'


def test_a_rendered_line_pasted_verbatim_runs_with_nothing_on_path(tmp_path):
    """Criteria 3, 5, 7 and 10 of the vehicle story, on the README's wiring.

    `DEVKIT` is this checkout (M8: the pin is not tagged, and the lock would
    run a released wheel), reached through the ENVIRONMENT so the Makefile
    stays the one line the README prints. The RECORDING line is lifted out of a preamble rendered
    through the vehicle itself and pasted into bash as printed; a sentence
    carrying `$5` is written through it and read back byte-exact (M2); and the
    sub-make a verb spawns sees no `ARGS`, by environment or by MAKEFLAGS.
    """
    from support.pm import ledger_rows, tree as pm_tree

    from agentic_sdlc.core import frontmatter
    from agentic_sdlc.repo import vehicle

    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for tool in VEHICLE_TOOLS:
        found = shutil.which(tool)
        assert found, f'{tool} is not on this machine'
        (bin_dir / tool).symlink_to(found)
    env = {'PATH': str(bin_dir), 'HOME': str(tmp_path), 'LC_ALL': 'C',
           'DEVKIT': f'env PYTHONPATH={REPO_ROOT / "src"} {sys.executable} '
                     f'-m agentic_sdlc.cli'}
    config = ('[dispatch]\nproject = "A worked example."\n'
              'contracts = ["RULES.md"]\n'
              '[verify]\nspot = "make leak"\nmilestone = "make leak"\n')
    with pm_tree(config=config, story_statuses=('building',)) as root:
        (root / 'RULES.md').write_text('# rules\n', encoding='utf-8')
        for name, rel in install.PLANS['install-gates']:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(install.body_of(name), encoding='utf-8')
        (root / 'Makefile').write_text(
            'include Makefile.devkit\n\n'
            'leak:\n\t@echo "nested ARGS=[$(ARGS)] env=[$${ARGS-unset}]"\n',
            encoding='utf-8')

        def paste(line: str) -> subprocess.CompletedProcess:
            return subprocess.run(['bash', '-c', line], cwd=root, env=env,
                                  text=True, capture_output=True, timeout=120)

        # Criterion 5: the proof cannot pass on the builder's PATH.
        assert paste('command -v agentic-sdlc').stdout == ''

        rendered = paste(vehicle.command('dispatch', '--grain', VEHICLE_STORY,
                                         '--role', 'developer'))
        assert rendered.returncode == 0, rendered.stdout + rendered.stderr
        lines = [ln.strip() for ln in rendered.stdout.splitlines()]
        # 0.11.0: a rendered stamp line attributes the dispatch; no export.
        assert not [ln for ln in lines if ln.startswith('export ')], lines
        record = next(ln for ln in lines
                      if 'ledger record' in ln and not ln.startswith('#'))
        assert record.startswith('make pm '), record
        done = paste(record)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'ledger dispatch row appended' in done.stdout + done.stderr
        rows = [r for r in ledger_rows(root) if r.get('kind') == 'dispatch']
        assert [r.get('grain') for r in rows] == [VEHICLE_STORY], rows

        story = root / 'pm/roadmap/stories/s0.md'
        done = paste("make sdlc ARGS='pm set " + VEHICLE_STORY
                     + " changelog '\"'\"'costs $5'\"'\"''")
        assert done.returncode == 0, done.stdout + done.stderr
        assert frontmatter.field_of(story, 'changelog') == 'costs $5'
        # The spelling the CLI renders, for the other target and quote kind.
        sentence = '`pm list` gains "a" column'
        done = paste(vehicle.command('pm', 'set', VEHICLE_STORY, 'changelog',
                                     sentence))
        assert done.returncode == 0, done.stdout + done.stderr
        assert frontmatter.field_of(story, 'changelog') == sentence

        # #60: ARGS reaches the verb by environment, never a shell, so a name
        # carrying `(`, `,` and `\'` is created as typed; a stray quote is 2.
        done = paste('make pm ARGS="new story 0.1/alpha s1 The HUD reads '
                     'f(host), then g\\\'s"')
        assert done.returncode == 0, done.stdout + done.stderr
        made = next((root / 'pm/roadmap/stories').glob('*s1*.md'))
        assert (frontmatter.field_of(made, 'name')
                == "The HUD reads f(host), then g's"), made.read_text()
        done = paste('make pm ARGS="new story 0.1/alpha s2 The HUD\'s"')
        assert 'Error 2' in done.stderr, done.stdout + done.stderr
        assert "as \\'" in done.stderr and 'syntax error' not in done.stderr

        done = paste("make sdlc ARGS='verify --spot --no-cache'")
        assert 'nested ARGS=[] env=[unset]' in done.stdout, (
            done.stdout + done.stderr)
        # Only the verb's recipes drop it (review M4): a consumer's own target,
        # and a script it calls, still read `$ARGS` as make always exported it.
        done = paste('make leak ARGS=hello')
        assert 'nested ARGS=[hello] env=[hello]' in done.stdout, (
            done.stdout + done.stderr)


# --- T1: a tier shadowed by a file or directory of the same name --------------
# The BEHAVIOURAL half, and it is the one that was missing. `Makefile.devkit`
# carries `.PHONY: $(GDK_PRECOMMIT_TIERS) $(GDK_MILESTONE_TIERS)`, and
# `test_phony_lists_this_files_targets_AND_the_declared_tiers` asserts that
# LINE is there — a text assertion, which stays green if make's behaviour and
# the line ever part company.
#
# The defect it guards is not exotic. Make asks "is this prerequisite out of
# date?", the orphan guard asks "is this name defined as a target?", and those
# are different questions: a defined target whose name matches an existing file
# or directory, with no `.PHONY`, is UP TO DATE — so make runs its recipe not
# at all and says nothing. `test`, `docs`, `bin`, `lint`, `build` and `tools`
# are all plausible tier names and all plausible directory names, and a
# language kit writes the tier file FOR the consumer, so the consumer never
# sees the `.PHONY` line it depends on.
#
# Exit 0, a shorter gate, and no line anywhere saying a gate was skipped. That
# is rule 4 wearing a Makefile, and it is D1's accepted cost arriving exactly
# as D1 said it would.
#
# EVERY OTHER TIER FIXTURE IN THIS FILE DECLARES ITS OWN `.PHONY`, which is
# precisely the condition that made T1 invisible to the suite. These two do not.
SHADOWABLE_TIERS = (
    'GDK_PRECOMMIT_TIERS := kit-parse test\n'
    'GDK_MILESTONE_TIERS := kit-parse test\n'
    '\n'
    'kit-parse: ## the kit\'s compile gate\n'
    '\t@echo "[KIT-PARSE] PASS"\n'
    'test: ## a tier whose name is also an ordinary directory name\n'
    '\t@echo "[KIT-TEST] PASS"\n'
)


def test_a_tier_shadowed_by_a_same_named_path_still_runs():
    """The framework's `.PHONY` covers the tiers the kit declared, so a
    `test/` directory beside a `test` tier cannot silently shorten the gate.
    Both shadow shapes, both compositions, two projects."""
    for shadow in ('dir', 'file'):
        with project(tiers=SHADOWABLE_TIERS) as root:
            if shadow == 'dir':
                (root / 'test').mkdir()
            else:
                (root / 'test').write_text('not a target\n', encoding='utf-8')
            for composition in ('precommit', 'milestone'):
                done = make(root, composition, stubbed(root))
                output = done.stdout + done.stderr
                assert done.returncode == 0, (shadow, composition, output)
                assert '[KIT-PARSE] PASS' in output, (shadow, composition, output)
                assert '[KIT-TEST] PASS' in output, (
                    f'{composition}: the `test` tier was shadowed by a {shadow} '
                    f'of the same name and did not run — a gate list that quietly '
                    f'gets shorter is the one failure a gate must never have (T1)')


def test_the_shadow_fixture_would_catch_a_missing_phony():
    """The probe, so the test above cannot pass vacuously.

    Same tier file, same shadowing directory, but the framework's `.PHONY` line
    is REMOVED from the installed `Makefile.devkit` — which is the tree T1 was
    measured on. If this does not go quiet, the test above is proving nothing.
    """
    with project(tiers=SHADOWABLE_TIERS) as root:
        (root / 'test').mkdir()
        devkit = root / 'Makefile.devkit'
        text = devkit.read_text(encoding='utf-8')
        stripped = text.replace(
            '.PHONY: $(GDK_PRECOMMIT_TIERS) $(GDK_MILESTONE_TIERS)\n', '')
        assert stripped != text, (
            'the .PHONY-over-tiers line is gone from Makefile.devkit; this '
            'probe and the test above are both about that line')
        devkit.write_text(stripped, encoding='utf-8')
        done = make(root, 'precommit', stubbed(root))
    output = done.stdout + done.stderr
    # THE DEFECT, reproduced: exit 0, a shorter gate, nothing said.
    assert done.returncode == 0, output
    assert '[KIT-PARSE] PASS' in output, output
    assert '[KIT-TEST] PASS' not in output, (
        'the shadowed tier ran without the .PHONY line, so this fixture does '
        'not reproduce T1 and the test above proves nothing')
