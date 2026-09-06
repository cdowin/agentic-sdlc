"""test_fresh_project.py — the milestone's ship criterion, as a gate.

THE FRESH PROJECT: an empty repo, `agentic-sdlc init`, and then the standard
targets work with zero hand edits. This file is that sentence made runnable —
one fixture project and every claim below asked of it rather than of a
hand-written stand-in.

WHAT THE SHIP CRITERION IS NOW. Through 0.1.0 the installed include carried a
language's whole target roster, so most of this file was `make -n` over
targets that would boot an engine nothing here has. Decision D1 split that out:
`Makefile.devkit` keeps `help`, `pm`, `check`, `precommit` and `milestone`, and
a LANGUAGE KIT contributes its tiers through `-include $(GDK_TIERS_MK)` and two
variables. This package ships no tier file, so the fresh project this builds is
the TIERLESS shape — which is not a degraded case but a supported one, and it
gets its own test: `precommit` there is `check` alone, and it SAYS so.

`make check` IS run for real here, and that is not a hedge — the gate roster is
pure parse and boots nothing, so a dry run of it was never the best this file
could do. Dry-running it is what shipped an installed file with a live gate
finding on every freshly-`init`'d project: `make -n precommit` expands recipes
and reaches no verdict, while the gate had something to say about a real file
the install wrote. What the run asserts is the honest half of the ship
criterion — that nothing the INSTALL wrote is a finding, and, in the other
direction, that the gates which DO apply are green rather than merely quiet.

WHAT IT STILL CANNOT PROVE. A tier target's contact with a real toolchain. No
tier file ships here, so nothing in this repo can run one; that last mile is
proven where the toolchain exists, which is a consuming project's own gate, in
its own repo. Stated rather than implied.

A DRY RUN THAT EXECUTES IS NOT A DRY RUN. `make -n` runs any recipe line
holding the literal `$(MAKE)`, so `check`'s sub-make is spelled `$${MAKE:-make}`
— and the census below proves it: nothing is written, no report directory
appears, and the stock uvx `DEVKIT` is never resolved (which would reach the
network from a target that promised to run nothing).

**Selection criterion (hard rule 10, 0.2.0/the-proof-is-named-in-the-criterion):**
every case here costs an `init` and a real `make`, so a claim the include
already proves against a scratch Makefile (test_makefile_include.py: `help`
lists the set, `[gates] extra` joins `check`) is not proven a second time
on an init'd tree. What stays is what only the init'd tree can answer: the
standard set as INSTALLED, the gates run over what `init` wrote, and the
hook corpus armed.
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

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.repo import install  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which('make') is None
                                or shutil.which('bash') is None
                                or shutil.which('git') is None,
                                reason='needs make, bash and git')

PROJECT_GODOT = ('config_version=5\n\n[application]\n\n'
                 'config/name="Fresh"\nconfig/version="0.1.0"\n'
                 'config/features=PackedStringArray("4.6")\n')
ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>\n'

# THE STANDARD SET, spelled out. It was 28 targets through 0.1.0, when the
# include carried a language kit's whole roster; decision D1 moved every one of
# those behind the `-include $(GDK_TIERS_MK)` seam, and what `install-gates`
# writes is these five and two internal announce targets. The set is asserted
# as an EQUALITY, which is stronger than the count-plus-four-names it replaces:
# a target quietly dropped from the include would shrink the sweep and still
# pass a count that somebody remembered to lower, and a target ADDED without a
# line here now fails too.
#
# 22 of the 23 that left are a language kit's; the twenty-third, `doctor`, has
# no replacement in the include at all — the question it answered ("is this
# checkout's hook corpus armed?") is `agentic-sdlc check hooks` now, and the
# case at the bottom of this file is where that coupling is held.
STANDARD = ('help', 'pm', 'check', 'precommit', 'milestone')
DOCUMENTED = re.compile(r'^([a-z][a-z0-9-]*):.*?## ', re.MULTILINE)


@contextlib.contextmanager
def initialized_project():
    """An empty Godot 4 project with `agentic-sdlc init` run in it, once."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'game'
        root.mkdir()
        (root / 'project.godot').write_text(PROJECT_GODOT, encoding='utf-8')
        (root / 'icon.svg').write_text(ICON, encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        done = subprocess.run(
            [sys.executable, '-m', 'agentic_sdlc.cli', 'init'],
            cwd=root, capture_output=True, text=True,
            env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')})
        assert done.returncode == 0, done.stdout + done.stderr
        yield root


def make(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['make', *args], cwd=root, text=True,
                          capture_output=True, env=dict(os.environ),
                          timeout=120)


def standard_targets(root: Path) -> list[str]:
    """The documented target set, asked of the INSTALLED include."""
    body = (root / 'Makefile.devkit').read_text(encoding='utf-8')
    return DOCUMENTED.findall(body)


def files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob('*')
            if p.is_file() and not p.relative_to(root).as_posix().startswith('.git/')}


# --- the ship criterion -------------------------------------------------------
def test_the_installed_include_carries_the_whole_standard_set():
    with initialized_project() as root:
        targets = standard_targets(root)
    assert len(targets) == len(set(targets)), f'a target is documented twice: {targets}'
    assert sorted(targets) == sorted(STANDARD), (
        f'the installed include is not the standard set: '
        f'{sorted(set(targets) ^ set(STANDARD))}')


def test_make_n_succeeds_for_every_standard_target_with_zero_hand_edits():
    """One project, every target, in one fixture: standing each of them up
    separately would cost one init apiece and prove the same thing five
    times."""
    with initialized_project() as root:
        before = files(root)
        failures = []
        for target in standard_targets(root):
            done = make(root, '-n', target)
            if done.returncode != 0:
                failures.append(f'--- make -n {target}\n{done.stdout}{done.stderr}')
        default = make(root, '-n')
        after = files(root)
    assert not failures, '\n'.join(failures)
    assert default.returncode == 0, default.stdout + default.stderr
    assert after == before, f'a dry run WROTE: {sorted(after ^ before)}'
    assert not (root / '.gate-reports').exists()


# --- `make check`, RUN --------------------------------------------------------
# A verdict line reads `[check:<gate>] FAIL — …`, and on a blank project there
# are exactly two kinds: a finding about a file the INSTALL wrote (this
# package's problem, and the class that shipped a sidecar-less
# compile_sweep.gd), and a 0-file census over a file kind a project with no
# scene in it does not have (the stock roster being wrong for a blank repo —
# the seed devkit.toml says so in those words and narrows it in one line).
VERDICT_RE = re.compile(r'^\[check:([a-z-]+)\] (PASS|FAIL) — (.*)$', re.MULTILINE)
EMPTY_CENSUS = 'scanned 0 of 0 tracked'
# What a blank project holds nothing of. Spelled out, so a gate JOINING this
# set is a decision somebody makes here rather than a silent widening.
#
# IT IS EMPTY NOW, and that is the assertion rather than an oversight. It held
# `uid`, `tres` and `props` — the three gates that read engine files — and all
# three left this package in 0.2.0. Every gate on the stock roster today reads
# markdown, shell or git, which a blank repo has, so nothing is excused from
# `test_the_gates_that_do_apply_to_a_blank_project_pass` and that case now
# covers the whole roster. An entry added back here has to carry the sentence
# saying which file kind a fresh repo genuinely does not have.
GATES_WITH_NOTHING_TO_SCAN: set[str] = set()


def committed(root: Path) -> None:
    """Every gate resolves its scope through `git ls-files`, so an uncommitted
    tree is a 0-file census for ALL of them and the run would prove nothing."""
    subprocess.run(['git', 'add', '-A'], cwd=root, check=True,
                   capture_output=True)
    subprocess.run(['git', '-c', 'user.email=t@example.com',
                    '-c', 'user.name=t', 'commit', '-qm', 'init', '--', '.'],
                   cwd=root, check=True, capture_output=True)


def working_tree_devkit() -> str:
    """`make check` resolves `DEVKIT` to `uvx --from git+…@<pin>` — the
    RELEASED tag, over the network. Overriding it on the command line is how
    this package verifies itself against source (CLAUDE.md: never a cached
    wheel), and it is not a hand edit to the project."""
    return (f'DEVKIT=env PYTHONPATH={REPO_ROOT / "src"} '
            f'{sys.executable} -m agentic_sdlc.cli')


def check_verdicts(root: Path) -> list[tuple[str, str, str]]:
    """(gate, PASS|FAIL, detail) for every gate `make check` actually ran."""
    committed(root)
    make(root, 'check', working_tree_devkit())
    transcript = (root / '.gate-reports' / 'check.log').read_text(
        encoding='utf-8')
    verdicts = VERDICT_RE.findall(transcript)
    assert verdicts, f'no gate verdict in the transcript:\n{transcript}'
    return verdicts


def test_nothing_the_install_wrote_is_a_check_finding_and_the_gates_pass():
    """The ship criterion's real half, run rather than dry-run — both
    directions asked of ONE `make check`, because they were two inits and two
    runs proving one verdict list. Nothing `init` wrote is a finding; and the
    assertion must not be satisfiable by a roster on which everything reports
    an empty census — `doc` and `shell` read what `init` actually wrote, and
    every applicable gate has to be green on it."""
    with initialized_project() as root:
        verdicts = check_verdicts(root)
    ours = [(gate, detail) for gate, outcome, detail in verdicts
            if outcome == 'FAIL' and EMPTY_CENSUS not in detail]
    assert not ours, (
        'a gate reported a finding about a file `init` wrote:\n'
        + '\n'.join(f'  [check:{g}] {d}' for g, d in ours))
    applicable = {gate: outcome for gate, outcome, _ in verdicts
                  if gate not in GATES_WITH_NOTHING_TO_SCAN}
    assert applicable, f'every gate on the roster scanned nothing: {verdicts}'
    assert set(applicable.values()) == {'PASS'}, applicable


def test_the_installed_contracts_do_not_redden_a_consumers_gates():
    """Install day must be green for `install-agents` under a `[doc]` scope
    that covers it. A contract that fails the gates it arrives beside gets
    deleted by the first person who runs them. (From test_install.py, which
    spawns nothing now; `init`'s stock scope above does not cover
    `.claude/agents/`, so this is not the same run.)"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        (root / 'devkit.toml').write_text(
            '[doc]\nscope = [".claude/agents/*.md"]\n', encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        previous = Path.cwd()
        os.chdir(root)
        try:
            assert install.main('install-agents', []) == 0
        finally:
            os.chdir(previous)
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        # A SUBPROCESS on purpose. `check doc` binds its scope and its repo
        # root at import time, so reloading it in-process to see a temp repo
        # leaves the module pointing at a directory that no longer exists —
        # and the next test to import it inherits that.
        proc = subprocess.run(
            [sys.executable, '-m', 'agentic_sdlc.cli', 'check', 'doc'],
            cwd=root, capture_output=True, text=True,
            env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')})
    assert proc.returncode == 0, (
        'the installed contract fails `check doc` on install day:\n'
        f'{proc.stdout}{proc.stderr}')


def test_precommit_on_a_tierless_project_is_check_alone_and_says_the_list_is_empty():
    """The shape decision D1 created, RUN on a real `init`'d tree.

    This package installs no `Makefile.tiers`, so a fresh project's
    `GDK_PRECOMMIT_TIERS` is empty and `-include` of the missing file is
    silent — deliberately, because a project with no language kit is a
    supported shape rather than a degraded one. That same silence is how a
    typo'd `GDK_TIERS_MK` would turn a five-gate `precommit` into a one-gate
    `precommit` that exits 0, which is this package's cardinal sin in a
    Makefile. The two are held apart by the empty case ANNOUNCING itself, and
    an announcement asserted only against the include's source is an
    announcement nobody has watched arrive: this asks the tree `init` built.
    """
    with initialized_project() as root:
        assert not (root / 'Makefile.tiers').exists(), (
            'this package ships a tier file now — the tierless shape below is '
            'no longer what a fresh project gets')
        committed(root)
        done = make(root, 'precommit', working_tree_devkit())
        gate_logs = sorted(p.name for p in (root / '.gate-reports').iterdir()
                           if p.suffix == '.log')
        composition = (root / '.gate-reports' / 'precommit.log').read_text(
            encoding='utf-8')
    assert done.returncode == 0, done.stdout + done.stderr
    assert '[TIERS] GDK_PRECOMMIT_TIERS is empty' in done.stdout, done.stdout
    assert 'Makefile.tiers is not present' in done.stdout, done.stdout
    # `check` ALONE, proven by what ran rather than by what was printed. Two
    # transcripts on disk: check's, and the composition's OWN — `precommit`
    # opens a slot of its own name around its members since
    # 0.2.0/bugs/a-composition-has-no-slot, and that slot is not a gate that
    # ran but the bracket around the ones that did. Its closing line names
    # the goals it was handed, and that list is `check`, nothing after it.
    assert gate_logs == ['check.log', 'precommit.log'], gate_logs
    assert '[PRECOMMIT] PASS (check) — full log:' in composition, composition


# --- the hook census: the gate's count vs the install roster -------------------
# The number of hooks the ARMING gate reports must equal the number
# `install-hooks` ships. A gate once carried that number as a hand-written
# literal, and the two 0.22.0 ledger couriers turned it into `8 tracked hook(s)
# armed, 6 installed` on the day they landed — red about a roster, not about
# behaviour. The gate itself was never wrong: it counts what is IN tools/hooks/
# precisely so a hook added after it was written is still covered. The literal
# was the only roster in the loop, so the census is asked of the install PLAN
# here, in the suite, where a new hook cannot be discovered by a gate first.
#
# THE SURFACE MOVED, THE COUPLING DID NOT. This was `tools/dev/checks/doctor.sh`
# until 0.2.0, when doctor left with the language kit (decision D2).
# `agentic-sdlc check hooks` is what reports an unarmed or dead corpus now — it
# asks the DIRECTORY the same way, excludes the same two shapes (`_*` sourced
# libraries, `*.local` drop-ins), and prints the same repair — so the case is
# re-pointed rather than dropped. A coupling that stops being asserted because
# the thing asserting it moved is a coupling that breaks on the next hook.
HOOKS_DIR = 'tools/hooks'
CC_PREFIX = 'cc-'
# `<n> hook(s) under tools/hooks/; <n> fail open on a payload they cannot read,
# <n> parse` — the gate's own scope line, which is where its census lives.
HOOK_CENSUS = re.compile(
    r'(\d+) hook\(s\) under tools/hooks/; '
    r'(\d+) fail open on a payload they cannot read, (\d+) parse')


def installed_hook_roster() -> list[str]:
    """What `install-hooks` puts under tools/hooks/, minus the gate's own
    exclusions (`_*` sourced libraries, `*.local` config drop-ins)."""
    return [rel for _, rel in install.PLANS['install-hooks']
            if rel.startswith(f'{HOOKS_DIR}/')
            and not Path(rel).name.startswith('_')
            and not rel.endswith('.local')]


def devkit_cli(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, '-m', 'agentic_sdlc.cli', *argv], cwd=root,
        capture_output=True, text=True,
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')})


def test_check_hooks_arms_and_reports_every_hook_the_install_verb_ships():
    """The coupling itself, on a real `init`'d tree: the gate's census is asked
    of the DIRECTORY, so it must come back equal to the roster that filled it,
    split the way the roster splits. Asked of a tree this file builds, so it
    holds on CI and on any machine."""
    roster = installed_hook_roster()
    assert roster, 'install-hooks ships no hook — this census covers nothing'
    claude_hooks = [rel for rel in roster
                    if Path(rel).name.startswith(CC_PREFIX)]
    with initialized_project() as root:
        for rel in roster:
            assert (root / rel).is_file(), f'{rel} was not installed'
        done = devkit_cli(root, 'check', 'hooks')
    assert done.returncode == 0, (
        f'a freshly-`init`\'d tree is not reported armed:\n'
        f'{done.stdout}{done.stderr}')
    counted = HOOK_CENSUS.search(done.stdout)
    assert counted, f'the gate published no census:\n{done.stdout}'
    total, ran, parsed = (int(n) for n in counted.groups())
    assert total == len(roster), (
        f'the gate reports {total} hook(s), install-hooks ships '
        f'{len(roster)}: {roster}\n{done.stdout}')
    # Not just the total: the gate proves a `cc-*` hook by RUNNING it and a git
    # hook by parsing it, and a roster that shifted between the two shapes
    # would keep the total while changing what was actually asked.
    assert (ran, parsed) == (len(claude_hooks), len(roster) - len(claude_hooks)), (
        f'the gate ran {ran} and parsed {parsed}; the roster is '
        f'{len(claude_hooks)} Claude Code hook(s) and '
        f'{len(roster) - len(claude_hooks)} git hook(s)\n{done.stdout}')


def test_check_hooks_says_so_when_the_corpus_is_installed_but_unarmed():
    """The other direction, and the reason `init` runs `setup-hooks.sh` at all:
    installing a hook is not arming it, and git skips an unarmed corpus in
    silence. Without this, the case above is satisfiable by a gate that only
    ever counts files."""
    with initialized_project() as root:
        subprocess.run(['git', 'config', '--unset', 'core.hooksPath'],
                       cwd=root, check=True, capture_output=True)
        done = devkit_cli(root, 'check', 'hooks')
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'UNARMED' in done.stdout, done.stdout
    assert 'bash tools/setup-hooks.sh' in done.stdout, done.stdout


def test_check_shell_names_the_UNTRACKED_case_not_the_roots_key():
    """A fresh `init` writes eight scripts and tracks none of them.

    The gate reads `git ls-files`, so its census is legitimately zero and it is
    right to FAIL — but until 0.2.0 it said `check [shell] roots`, which was
    correct all along. Measured on a stock init: the operator is sent to
    inspect a config key that is not the problem, on the very first run of the
    tool. A verdict that names the wrong cause costs more than one that names
    none.
    """
    with initialized_project() as root:
        before = devkit_cli(root, 'check', 'shell')
        committed(root)
        after = devkit_cli(root, 'check', 'shell')

    out = before.stdout + before.stderr
    assert before.returncode == 1, out
    assert 'none TRACKED' in out, out
    assert 'git add' in out, out
    assert 'check [shell] roots' not in out, out

    out = after.stdout + after.stderr
    assert after.returncode == 0, out
    assert 'script(s) clean' in out, out
