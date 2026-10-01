"""test_fresh_project.py — the milestone's ship criterion, as a gate.

THE FRESH PROJECT: an empty repo, `agentic-sdlc init`, and then the standard
targets work with zero hand edits. This file is that sentence made runnable —
one fixture project and every claim below asked of it rather than of a
hand-written stand-in.

WHAT THE SHIP CRITERION IS. `Makefile.devkit` keeps `help`, `pm`, `check`,
`precommit` and `milestone`; a LANGUAGE KIT contributes its tiers through
`-include $(GDK_TIERS_MK)` and two variables (0.2.0/D1). This package ships no
tier file, so the fresh project this builds is the TIERLESS shape — a supported
case rather than a degraded one, and it gets its own test: `precommit` there is
`check` alone, and it SAYS so.

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
appears, and the stock locked `DEVKIT` is never resolved (a `uv sync` would
reach the network from a target that promised to run nothing).

**Selection criterion (hard rule 10, 0.2.0/the-proof-is-named-in-the-criterion):**
every case here costs an `init` and a real `make`, so a claim the include
already proves against a scratch Makefile (test_makefile_include.py: `help`
lists the set, `[gates] extra` joins `check`) is not proven a second time
on an init'd tree. What stays is what only the init'd tree can answer: the
standard set as INSTALLED, and the gates run over what `init` wrote — ONE
real `make check`, every other case standing `check all` in or asking one
gate. The hook census against the install roster is
`test_check_hooks.py`'s shipped-corpus case, and `init` arming the corpus is
`test_init_verb.py::test_the_hooks_are_armed_not_merely_installed`.
"""
from __future__ import annotations

import contextlib
import json
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
from agentic_sdlc.core import frontmatter, project  # noqa: E402
from agentic_sdlc.repo import install  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which('make') is None
                                or shutil.which('bash') is None
                                or shutil.which('git') is None,
                                reason='needs make, bash and git')

PROJECT_GODOT = ('config_version=5\n\n[application]\n\n'
                 'config/name="Fresh"\nconfig/version="0.1.0"\n'
                 'config/features=PackedStringArray("4.6")\n')
ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>\n'

# THE STANDARD SET, spelled out: what `install-gates` writes is these six and
# two internal announce targets, everything a language kit contributes arriving
# behind the `-include $(GDK_TIERS_MK)` seam (0.2.0/D1). The set is asserted as
# an EQUALITY, which is stronger than a count: a target quietly dropped from the
# include would shrink the sweep and still pass a count somebody remembered to
# lower, and a target ADDED without a line here fails too.
STANDARD = ('help', 'pm', 'sdlc', 'check', 'precommit', 'milestone')
DOCUMENTED = re.compile(r'^([a-z][a-z0-9-]*):.*?## ', re.MULTILINE)


@contextlib.contextmanager
def initialized_project(parent: Path | None = None):
    """An empty Godot 4 project with `agentic-sdlc init` run in it, once —
    under `parent` when one is given, else under a temp dir of its own."""
    with (contextlib.nullcontext(str(parent)) if parent
          else tempfile.TemporaryDirectory()) as tmp:
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


def synced(root: Path) -> None:
    """Next step 1, `uv sync`, without the network: a uv.lock naming the kit
    and the entry point it installs, stood in, so the STOCK `DEVKIT` resolves
    and nothing reaches uv."""
    (root / 'uv.lock').write_text(
        'version = 1\n\n[[package]]\nname = "agentic-sdlc"\n'
        'version = "0.0.0"\n', encoding='utf-8')
    kit = root / '.venv/bin/agentic-sdlc'
    kit.parent.mkdir(parents=True)
    kit.write_text('#!/bin/sh\n', encoding='utf-8')
    kit.chmod(0o755)


def make(root: Path, *args: str) -> subprocess.CompletedProcess:
    """`make` in the fresh project. The recorder is the STOCK one, `$(DEVKIT)`:
    under `make test` this package's own `GDK_LEDGER_CMD` (`uv run`) is
    exported into the suite, and in a tree `init` seeded with a pyproject.toml
    it tries to lock that tree against the index on every slot."""
    env = dict(os.environ)
    env.pop('GDK_LEDGER_CMD', None)
    return subprocess.run(['make', *args], cwd=root, text=True,
                          capture_output=True, env=env, timeout=120)


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
        synced(root)
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
# IT IS EMPTY, and that is the assertion rather than an oversight: every gate
# on the stock roster reads markdown, shell or git, which a blank repo has, so
# nothing is excused from `test_the_gates_that_do_apply_to_a_blank_project_pass`
# and that case covers the whole roster. An entry added here has to carry the
# sentence saying which file kind a fresh repo genuinely does not have.
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
    """`make check` resolves `DEVKIT` to `.venv/bin/agentic-sdlc`, synced from
    uv.lock — the RELEASED wheel, over the network. Overriding it on the command line is how
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
    every applicable gate has to be green on it.

    And the run leaves the tree it gated CLEAN: `check all` records a PASS it
    can reuse and the gate library files a cost row, and both must land in
    what `init` gitignored. This is the one real `check all` on an `init`'d
    tree, so `test_init_verb`'s commit-through-a-hook case stands it in."""
    with initialized_project() as root:
        verdicts = check_verdicts(root)
        status = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=all'],
            cwd=root, capture_output=True, text=True, check=True).stdout
    assert status == '', f'`make check` left its own tree dirty:\n{status}'
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
        # `repo_root` is lru_cached and its docstring says a test that chdirs
        # clears it. This one did not: it passed only while nothing earlier in
        # the run had populated the cache, so adding a test module elsewhere
        # silently redirected the install to the CACHED root and left this
        # temp tree empty — `check doc` then scanned 0 docs and failed.
        project.repo_root.cache_clear()
        project.load_config.cache_clear()
        try:
            assert install.main('install-agents', []) == 0
            # Since 0.8.0 every command a definition cites is a target of
            # the stock wiring (`make sdlc`/`make pm`, feature D1), so the
            # consumer is the README's: the include, and what it includes.
            # Without it `check doc` is RIGHT to call `make sdlc` unknown.
            assert install.main('install-gates', []) == 0
            (root / 'Makefile').write_text(
                'include Makefile.devkit\n',
                encoding='utf-8')
        finally:
            os.chdir(previous)
            project.repo_root.cache_clear()
            project.load_config.cache_clear()
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


# A stand-in DEVKIT: `check all` prints one gate, `gates-extra` names none, and
# as the stock recorder it files nothing.
STUB_DEVKIT = """#!/usr/bin/env bash
[ "$1 $2" = "check all" ] || exit 0
echo "[check:doc] PASS"
"""


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
        # `check all` stood in: what is asked here is the COMPOSITION, and the
        # one real `check all` on this tree is the case above.
        stub = root.parent / 'devkit.sh'
        stub.write_text(STUB_DEVKIT, encoding='utf-8')
        done = make(root, 'precommit', f'DEVKIT=bash {stub}')
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


# --- `check shell` before the first commit ------------------------------------
def devkit_cli(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, '-m', 'agentic_sdlc.cli', *argv], cwd=root,
        capture_output=True, text=True,
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')})


def test_check_shell_names_the_UNTRACKED_case_not_the_roots_key():
    """A fresh `init` writes eight scripts and tracks none of them.

    The gate reads `git ls-files`, so its census is legitimately zero and it is
    right to FAIL — but until 0.2.0 it said `check [shell] roots`, which was
    correct all along. Measured on a stock init: the operator is sent to
    inspect a config key that is not the problem, on the very first run of the
    tool. A verdict that names the wrong cause costs more than one that names
    none.

    The committed half — the same scripts, tracked, are clean — is
    `test_nothing_the_install_wrote_is_a_check_finding_and_the_gates_pass`,
    whose one `make check` runs `shell` over them.
    """
    with initialized_project() as root:
        before = devkit_cli(root, 'check', 'shell')

    out = before.stdout + before.stderr
    assert before.returncode == 1, out
    assert 'none TRACKED' in out, out
    assert 'git add' in out, out
    assert 'check [shell] roots' not in out, out


# --- the loop, end to end -----------------------------------------------------
# The workflow keys a stock `init` leaves undeclared (rule 5: no default), each
# pointed at one trivial target, so the case proves the LOOP and no toolchain.
LOOP_TARGET = 'loop-ok'
LOOP_CONFIG = f"""
[verify]
spot      = "make {LOOP_TARGET}"
milestone = "make {LOOP_TARGET}"

[integrate]
per_merge = []
proof     = ["{LOOP_TARGET}"]

[dispatch]
project   = "the loop, end to end"
contracts = ["CLAUDE.md"]

[release.version_files]
"VERSION" = "^(.*)$"
"""
LOOP_VERSION = '0.2.0'
LOOP_BRANCH = f'milestone/{LOOP_VERSION}-loop'
WORKTREE_NEW = re.compile(r'agent-worktree\.sh new (\S+) (\S+)')


def loop_env() -> dict[str, str]:
    """The stock recorder, the working-tree kit as `DEVKIT` for every `make`
    a verb spawns, and no `GIT_*` from a hook that runs this suite."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith('GIT_') and k != 'GDK_LEDGER_CMD'}
    env['PYTHONPATH'] = str(REPO_ROOT / 'src')
    env['DEVKIT'] = working_tree_devkit().partition('=')[2]
    return env


def kit(cwd: Path, *argv: str) -> str:
    done = subprocess.run([sys.executable, '-m', 'agentic_sdlc.cli', *argv],
                          cwd=cwd, capture_output=True, text=True,
                          env=loop_env(), timeout=120)
    assert done.returncode == 0, f'`{" ".join(argv)}`:\n{done.stdout}{done.stderr}'
    return done.stdout


def git(cwd: Path, *argv: str) -> str:
    done = subprocess.run(['git', '-c', 'user.email=t@example.com',
                           '-c', 'user.name=t', *argv], cwd=cwd,
                          capture_output=True, text=True, env=loop_env(),
                          timeout=120)
    assert done.returncode == 0, f'`git {" ".join(argv)}`:\n{done.stderr}'
    return done.stdout


def status(root: Path, grain: str) -> str:
    return frontmatter.field_of(root / 'pm/roadmap' / grain, 'status')


def test_the_loop_runs_end_to_end_in_one_fresh_project(tmp_path):
    """init, `pm new` x3, dispatch, a lane that passes spot, integrate,
    release — in one tree with a bare origin. Each step asserts the one status
    or file it writes; what joins two steps (a state move, a commit) is the
    operator's hand, done here without assertion."""
    origin = tmp_path / 'origin.git'
    subprocess.run(['git', 'init', '-q', '--bare', str(origin)],
                   cwd=tmp_path, check=True)
    with initialized_project(tmp_path) as root:
        # init writes the config and the include.
        assert (root / 'devkit.toml').is_file()
        assert (root / 'Makefile.devkit').is_file()
        with (root / 'devkit.toml').open('a', encoding='utf-8') as fh:
            fh.write(LOOP_CONFIG)
        with (root / 'Makefile').open('a', encoding='utf-8') as fh:
            fh.write(f'\n{LOOP_TARGET}: ## the loop case stand-in\n\t@true\n')
        git(root, 'remote', 'add', 'origin', str(origin))

        # pm new writes one grain file each, in its first state.
        kit(root, 'pm', 'new', 'milestone', 'loop', 'The loop',
            '--version', LOOP_VERSION)
        kit(root, 'pm', 'new', 'feature', 'ms-loop', 'loopf', 'Loop feature')
        kit(root, 'pm', 'new', 'story', 'ft-loopf', 'lane', 'The lane')
        for grain in ('milestones/ms-loop.md', 'features/ft-loopf.md',
                      'stories/st-lane.md'):
            assert status(root, grain) == 'planning', grain

        kit(root, 'pm', 'set', 'ms-loop', 'branch', LOOP_BRANCH)
        for kind, gid in (('milestone', 'ms-loop'), ('feature', 'ft-loopf'),
                          ('story', 'st-lane')):
            kit(root, 'pm', kind, 'building', gid)
        git(root, 'checkout', '-q', '-b', LOOP_BRANCH)
        git(root, 'add', '-A')
        git(root, 'commit', '-qm', 'plan the loop')
        git(root, 'push', '-q', '-u', 'origin', LOOP_BRANCH)

        # dispatch writes nothing; the case reads the brief and follows it.
        brief = kit(root, 'dispatch', '--grain', 'st-lane')
        assert git(root, 'status', '--porcelain') == ''
        new = WORKTREE_NEW.search(brief)
        assert new, f'the brief names no worktree command:\n{brief}'
        made = subprocess.run(['bash', 'tools/dev/agent-worktree.sh', 'new',
                               *new.groups()], cwd=root, capture_output=True,
                              text=True, env=loop_env(), timeout=120)
        assert made.returncode == 0, made.stdout + made.stderr
        lane = Path(made.stdout.strip().splitlines()[-1])

        # The lane: one commit, then spot writes a PASS row to its ledger.
        (lane / 'feature.txt').write_text('the lane\n', encoding='utf-8')
        git(lane, 'add', 'feature.txt')
        git(lane, 'commit', '-qm', 'the lane', '--', 'feature.txt')
        kit(lane, 'verify', '--spot')
        rows = (lane / 'pm/roadmap/ledger.local.jsonl').read_text(
            encoding='utf-8').splitlines()
        row = json.loads(rows[-1])
        assert (row['kind'], row['rung'], row['verdict']) == (
            'verify', 'spot', 'PASS'), row
        git(lane, 'push', '-q', '-u', 'origin',
            git(lane, 'branch', '--show-current').strip())

        # integrate writes the story's done state, on the milestone branch.
        kit(root, 'integrate', new.group(1))
        assert status(root, 'stories/st-lane.md') == 'done'

        kit(root, 'pm', 'feature', 'done', 'ft-loopf')
        (root / 'VERSION').write_text(f'{LOOP_VERSION}\n', encoding='utf-8')
        git(root, 'add', 'VERSION', 'pm')
        git(root, 'commit', '-qm', 'close the feature')

        # release writes the milestone's done state.
        kit(root, 'release', LOOP_VERSION)
        assert status(root, 'milestones/ms-loop.md') == 'done'
