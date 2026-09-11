"""test_check_hooks.py — the gate that says whether THIS checkout is guarded.

`install-hooks` writes the corpus and `core.hooksPath` is what makes git run
it. Between those two facts sits the state this gate exists for: a tree whose
guards are on disk, tracked, executable and reviewed, and which git never
consults. This package sat in it for two releases while telling its consumers
the corpus was self-hosted here
(0.24.0/bugs/self-hosting-has-no-arm-or-verify-target).

Every case below builds a REAL repo, installs the REAL corpus into it and runs
the gate against it. Nothing disarms the checkout the suite is running in —
that would be a test that breaks the tree it is proving.

A hook can also be dead before the exec bit is ever asked about. Git's hook
universe is every ENTRY in the directory, so a broken symlink or a directory
holding a hook's name is a name git tries and cannot start — and enumerating
only regular files does not miss it, it SUBTRACTS it: the census reads smaller
than the directory and no line says why. `NOT A FILE` is that case.

The sharp case is `test_a_hook_that_starts_and_dies_...`: armed, executable,
byte-present, and dead. It is the shape the installer measured on this
package's own history — a 0.16.0 project-config header under a current body
drops keys the body reads under `set -u`, so the hook exits 1 before deciding
anything where only 2 is a BLOCK. A gate that asks where a path points calls
that tree armed, which is why this one starts every hook.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT, run_check                        # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root    # noqa: E402
from agentic_sdlc.repo import install                           # noqa: E402
from agentic_sdlc.repo.checks import hooks                      # noqa: E402

HOOKS_DIR = hooks.HOOKS_DIR
A_CC_HOOK = 'cc-commit-pathspec.sh'
A_GIT_HOOK = 'pre-push'
# Six `cc-*.sh` and two git hooks — asked of the plan, never restated, so the
# next hook to ship does not need this file edited.
SHIPPED = [rel for _, rel in install.PLANS['install-hooks']
           if rel.startswith(f'{HOOKS_DIR}/')]
CC_COUNT = sum(1 for rel in SHIPPED
               if Path(rel).name.startswith(hooks.CC_PREFIX))
GIT_COUNT = len(SHIPPED) - CC_COUNT


@contextlib.contextmanager
def hooked_repo(arm: bool = True):
    """A git repo with the corpus installed, armed or not, cwd'd into."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=root, check=True)
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            assert install.main('install-hooks', []) == 0
            if arm:
                armed = subprocess.run(['bash', 'tools/setup-hooks.sh'],
                                       cwd=root, capture_output=True, text=True)
                assert armed.returncode == 0, armed.stderr
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def gate() -> tuple[int, str]:
    return run_check(hooks)


def disarm_exec_bit(path: Path) -> None:
    path.chmod(path.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


# --- the three states -------------------------------------------------------
def test_an_unarmed_checkout_is_a_red_line_naming_the_repair():
    """The bug itself. The corpus is installed and every exec bit is on; git
    has simply never been told, so not one guard runs."""
    with hooked_repo(arm=False):
        code, out = gate()
    assert code == 1, out
    assert 'UNARMED' in out, out
    assert 'core.hooksPath is unset' in out, out
    assert hooks.ARM_COMMAND in out, out


def test_arming_the_same_tree_turns_it_green():
    """The other half: the gate must be satisfiable by the repair it names,
    or it is a red line nobody can clear."""
    with hooked_repo(arm=True):
        code, out = gate()
    assert code == 0, out
    assert '[check:hooks] PASS' in out, out
    assert f'armed at {HOOKS_DIR}' in out, out


def test_a_hooks_path_pointing_somewhere_else_names_both_paths():
    """Set, and set wrong, is not armed — and the operator needs to see the
    value that is there, not only the one that should be."""
    with hooked_repo(arm=True) as root:
        subprocess.run(['git', 'config', 'core.hooksPath', '.githooks'],
                       cwd=root, check=True)
        code, out = gate()
    assert code == 1, out
    assert 'MISDIRECTED' in out, out
    assert '.githooks' in out and HOOKS_DIR in out, out


def test_a_linked_worktree_armed_at_the_main_worktrees_corpus_is_not_misdirected():
    """What a harness that makes agent worktrees does (Claude Code, measured
    2026-09-11): it writes an ABSOLUTE core.hooksPath naming the main
    worktree's tools/hooks into the SHARED config. From a linked worktree that
    is armed, and MISDIRECTED was a red line no repair could clear. It is a
    named note instead, because git runs the MAIN corpus there."""
    with hooked_repo(arm=True) as root:
        subprocess.run(['git', 'config', 'core.hooksPath',
                        str(root / HOOKS_DIR)], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t',
                        'commit', '-q', '--allow-empty', '-m', 'base'],
                       cwd=root, check=True)
        linked = root.parent / 'linked'
        subprocess.run(['git', 'worktree', 'add', '-q', '--detach',
                        str(linked)], cwd=root, check=True)
        shutil.copytree(root / HOOKS_DIR, linked / HOOKS_DIR)
        os.chdir(linked)
        repo_root.cache_clear()
        code, out = gate()
        os.chdir(root)
        repo_root.cache_clear()
    assert 'MISDIRECTED' not in out, out
    assert 'a linked worktree' in out, out
    assert code == 0, out


# --- armed is not the same as working ----------------------------------------
def test_a_hook_without_its_exec_bit_is_named():
    """core.hooksPath skips a non-executable hook in SILENCE — a checkout onto
    a filesystem that drops the bit disarms one guard and nothing else moves."""
    with hooked_repo(arm=True) as root:
        disarm_exec_bit(root / HOOKS_DIR / A_GIT_HOOK)
        code, out = gate()
    assert code == 1, out
    assert 'NOT EXECUTABLE' in out and A_GIT_HOOK in out, out
    assert hooks.ARM_COMMAND in out, out


def test_a_hook_that_starts_and_dies_is_a_finding_though_it_looks_installed():
    """THE case a path check cannot make. The hook is present, tracked, armed
    and executable; its project-config header reads a variable the body never
    sets, so under `set -u` it dies before deciding anything and exits 1 —
    where only 2 is a BLOCK. Every raw boot walks straight through a guard
    that looks installed."""
    with hooked_repo(arm=True) as root:
        hook = root / HOOKS_DIR / A_CC_HOOK
        body = hook.read_text(encoding='utf-8')
        hook.write_text(body.replace('set -eu\n',
                                     'set -eu\necho "$NEVER_SET_BY_THIS_BODY"\n',
                                     1), encoding='utf-8')
        # It is still armed and still executable: the two things a path check
        # asks. Proven here so the case cannot pass for the other reason.
        assert os.access(hook, os.X_OK)
        code, out = gate()
    assert code == 1, out
    assert 'DEAD' in out and A_CC_HOOK in out, out
    assert 'fails OPEN' in out, out


def test_a_git_hook_that_does_not_parse_is_a_finding():
    """A git hook's argv contract is git's, so the gate asks the one question
    it can ask honestly of any of them: does the file still parse."""
    with hooked_repo(arm=True) as root:
        hook = root / HOOKS_DIR / A_GIT_HOOK
        hook.write_text(hook.read_text(encoding='utf-8') + '\nif then fi\n',
                        encoding='utf-8')
        code, out = gate()
    assert code == 1, out
    assert 'DEAD' in out and A_GIT_HOOK in out, out
    assert 'does not parse' in out, out


# --- what it counts, and what it refuses to count -----------------------------
def test_the_verdict_says_which_shape_proved_what():
    """`bash -n` is not the fail-open probe, and the line must not let one read
    as the other — a reader has to be able to tell what was actually asked."""
    with hooked_repo(arm=True):
        code, out = gate()
    assert code == 0, out
    assert f'{len(SHIPPED)} hook(s)' in out, out
    assert f'{CC_COUNT} fail open' in out, out
    assert f'{GIT_COUNT} parse' in out, out


def test_a_corpus_of_nothing_is_a_FAIL_not_a_PASS_over_nothing():
    """Rule 4. An empty directory and a guarded tree must never print the same
    word — that PASS is the most dangerous output this gate could emit."""
    with hooked_repo(arm=True) as root:
        for entry in (root / HOOKS_DIR).iterdir():
            entry.unlink()
        code, out = gate()
    assert code == 1, out
    assert '0 hook(s)' in out, out


# --- the census is the DIRECTORY --------------------------------------------
# `Kind.FILE` is a universe declaration and a universe reason never renders, so
# a non-regular entry left the walk with nothing saying so. Every case here
# counts the directory with a raw listing, so a test can never inherit the
# enumeration defect it exists to catch.
CENSUS = re.compile(r'(\d+) hook\(s\) under ')


def census_of(out: str) -> int:
    match = CENSUS.search(out)
    assert match, out
    return int(match.group(1))


def entries_on_disk(root: Path) -> list[str]:
    """Every name git would try, minus the two shapes the gate declares it
    excludes."""
    return sorted(p.name for p in (root / HOOKS_DIR).iterdir()
                  if not p.name.startswith('_')
                  and not p.name.endswith('.local'))


def test_a_directory_that_took_a_hooks_name_is_a_finding_not_a_subtraction():
    """It is on disk, it is tracked, it looks installed, and git cannot exec
    it. The old walk answered by making it disappear from the count."""
    with hooked_repo(arm=True) as root:
        (root / HOOKS_DIR / A_GIT_HOOK).unlink()
        (root / HOOKS_DIR / A_GIT_HOOK).mkdir()
        (root / HOOKS_DIR / A_GIT_HOOK / 'hook.sh').write_text('true\n',
                                                               encoding='utf-8')
        code, out = gate()
        on_disk = entries_on_disk(root)
    assert code == 1, out
    assert 'NOT A FILE' in out, out
    assert f'{A_GIT_HOOK} is a directory' in out, out
    assert census_of(out) == len(on_disk), (census_of(out), on_disk)


def test_a_broken_symlink_where_a_hook_was_is_a_finding_not_a_subtraction():
    """A checkout whose symlink target went away. git skips it in silence,
    which is a disarmed guard — and the walk skipped it in silence too, which
    is the same failure one layer up."""
    with hooked_repo(arm=True) as root:
        (root / HOOKS_DIR / A_CC_HOOK).unlink()
        (root / HOOKS_DIR / A_CC_HOOK).symlink_to('../../gone/somewhere.sh')
        code, out = gate()
        on_disk = entries_on_disk(root)
    assert code == 1, out
    assert 'NOT A FILE' in out, out
    assert f'{A_CC_HOOK} is a symlink to ../../gone/somewhere.sh' in out, out
    assert 'does not resolve' in out, out
    assert census_of(out) == len(on_disk), (census_of(out), on_disk)


def test_the_census_never_reads_smaller_than_the_directory():
    """The universal the two cases above are instances of. Whatever is under
    the corpus, the number in the verdict is the number of entries git would
    try — the disclosed `_*`/`*.local` exclusions being the only subtraction,
    and they are disclosed IN the same string."""
    with hooked_repo(arm=True) as root:
        (root / HOOKS_DIR / 'a-directory').mkdir()
        (root / HOOKS_DIR / 'a-dangling-link').symlink_to('nowhere')
        (root / HOOKS_DIR / '_lib.sh').write_text('true\n', encoding='utf-8')
        (root / HOOKS_DIR / 'pre-push.local').write_text('X=1\n', encoding='utf-8')
        code, out = gate()
        on_disk = entries_on_disk(root)
    assert code == 1, out
    assert census_of(out) == len(on_disk) == len(SHIPPED) + 2, (out, on_disk)
    assert '2 path(s) excluded from scope' in out, out
    assert out.count('NOT A FILE') == 2, out


def test_an_underscore_prefix_is_how_a_non_hook_lives_there_legitimately():
    """The finding names `_`-prefixing as the way out, so it has to BE one: a
    directory of fixtures under a corpus is a real thing to want, and the
    escape hatch has to leave the tree green and the subtraction disclosed."""
    with hooked_repo(arm=True) as root:
        (root / HOOKS_DIR / '_fixtures').mkdir()
        code, out = gate()
    assert code == 0, out
    assert f'{len(SHIPPED)} hook(s)' in out, out
    assert '1 path(s) excluded from scope' in out, out


def test_sourced_libraries_and_local_dropins_are_not_hooks():
    """`_*` is sourced by a hook and `*.local` is config — git runs neither, so
    neither needs an exec bit and neither may redden the gate."""
    with hooked_repo(arm=True) as root:
        (root / HOOKS_DIR / '_lib.sh').write_text('true\n', encoding='utf-8')
        (root / HOOKS_DIR / 'pre-push.local').write_text('X=1\n', encoding='utf-8')
        code, out = gate()
    assert code == 0, out
    assert f'{len(SHIPPED)} hook(s)' in out, out
    # DISCLOSED, not subtracted: the two are named in the count they left.
    assert '2 path(s) excluded from scope' in out, out


# --- the corpus each hook ships, replayed ------------------------------------
# The move story 02 is about: this kit installs the corpus, so this kit owns the
# gate over it — instead of twenty per-consumer make targets each repo has to
# remember to wire. A guard nobody wired is a guard that is not there.
#
# WHICH hooks carry one is DERIVED here as it is in the gate, from the installed
# files, because a literal list in a test is the same defect the gate refuses:
# `HOOKS_WITH_CORPUS` in one Makefile emptied out to nothing and kept passing.
def corpus_hooks(root: Path) -> list[Path]:
    return sorted(p for p in (root / HOOKS_DIR).iterdir()
                  if p.is_file() and hooks.SELF_TEST_DECL.search(
                      p.read_text(encoding='utf-8', errors='replace')))


def edit_hook(path: Path, old: str, new: str) -> None:
    body = path.read_text(encoding='utf-8')
    assert old in body, f'{path.name} no longer contains {old!r}'
    path.write_text(body.replace(old, new), encoding='utf-8')


def test_the_verdict_counts_the_hooks_that_replayed_their_own_corpus():
    """A census of what was actually asked. `bash -n` proves a file parses and
    a fail-open payload proves it starts; neither replays a single case of the
    block/allow corpus the hook ships, and the line must not let one read as
    another."""
    with hooked_repo(arm=True) as root:
        carriers = corpus_hooks(root)
        code, out = gate()
    assert code == 0, out
    assert carriers, 'the installed corpus ships no --self-test at all'
    assert f'{len(carriers)} replay their own --self-test corpus' in out, out


def test_a_corpus_in_which_NOTHING_replays_is_a_FAIL_not_a_PASS():
    """The defect this package's own `make hooks-self-test` carried until
    0.2.0: the list emptied out, `for h in <nothing>` ran zero corpora, exited
    0, and the summary reported `0 hook(s) SELF-TEST OK` as a pass. From here
    an uninstalled corpus and a passing one are the same picture."""
    with hooked_repo(arm=True) as root:
        for path in corpus_hooks(root):
            edit_hook(path, hooks.SELF_TEST_FLAG, '--no-corpus-here')
        assert not corpus_hooks(root)
        code, out = gate()
    assert code == 1, out
    assert 'NO CORPUS' in out, out
    assert '0 replay their own --self-test corpus' in out, out


def test_a_hook_whose_own_corpus_now_disagrees_is_a_finding():
    """The point of replaying at all: an edit to a guard must not be able to
    quietly change a verdict its corpus asserts."""
    with hooked_repo(arm=True) as root:
        carrier = corpus_hooks(root)[0]
        edit_hook(carrier, 'exit "$self_test_rc"', 'exit 3')
        code, out = gate()
    assert code == 1, out
    assert 'SELF-TEST' in out and carrier.name in out, out
    assert 'fails its own --self-test corpus (exit 3)' in out, out


def test_a_hook_that_answers_the_flag_and_replays_nothing_is_not_a_pass():
    """Exit 0 is not the contract; `SELF-TEST OK` is. A hook that took the flag
    and returned without running a case would otherwise report a pass over a
    corpus it never opened — the same zero, one level down."""
    with hooked_repo(arm=True) as root:
        carrier = corpus_hooks(root)[0]
        body = carrier.read_text(encoding='utf-8')
        line = next(ln for ln in body.splitlines()
                    if hooks.SELF_TEST_OK in ln and ln.strip().startswith('echo'))
        edit_hook(carrier, line, '\t\t:')
        code, out = gate()
    assert code == 1, out
    assert 'SELF-TEST' in out and carrier.name in out, out
    assert 'does not answer it' in out, out


def test_mentioning_the_flag_is_not_the_same_as_shipping_a_corpus():
    """The text probe that nominates a candidate is deliberately generous, so
    the RUN has to be what proves one. A hook that merely names the flag is fed
    it, falls through to its ordinary path, fails open at 0 and prints no
    marker — a finding, never a silent green. (It also proves the replay cannot
    HANG: every `cc-*.sh` reads its payload from stdin.)"""
    with hooked_repo(arm=True) as root:
        stray = root / HOOKS_DIR / A_CC_HOOK
        assert stray not in corpus_hooks(root)
        edit_hook(stray, 'set -eu\n',
                  f'set -eu\nSELF_TEST_HINT="{hooks.SELF_TEST_FLAG}"\n')
        code, out = gate()
    assert code == 1, out
    assert 'SELF-TEST' in out and A_CC_HOOK in out, out
    assert 'does not answer it' in out, out


# --- K3: what the replay count is a count OF ---------------------------------
# `2 replay their own --self-test corpus` is true and reads as coverage of the
# guards. In the shape this kit ships it is coverage of the two ledger couriers,
# which judge nothing; the three hooks that say no carry no corpus at all. D2
# accepted that cost, so the gate reports it rather than refusing it — and the
# thing being tested is that the line cannot be read as more than it is.
def blocking_hooks(root: Path) -> list[Path]:
    return sorted(p for p in (root / HOOKS_DIR).iterdir()
                  if p.is_file() and hooks.BLOCKS_DECL.search(
                      p.read_text(encoding='utf-8', errors='replace')))


def test_the_verdict_names_how_many_BLOCKING_hooks_the_replay_covers():
    """The stock corpus, measured: every carrier is a courier and no blocker is
    covered. The line has to say so in words — a reader who stops at `2 replay`
    has been told the guards are exercised, and they are not."""
    with hooked_repo(arm=True) as root:
        blockers = blocking_hooks(root)
        carriers = corpus_hooks(root)
        code, out = gate()
    assert code == 0, out
    assert blockers, 'the installed corpus ships no hook that can block'
    assert not set(blockers) & set(carriers), (
        'a blocking hook now ships a corpus — good; this test and the K3 note '
        'in hooks.py both describe the shape where none did')
    assert f'NONE of the {len(blockers)} that can BLOCK' in out, out
    assert f'exit {hooks.BLOCK_EXIT}' in out, out


def test_a_blocking_hook_that_ships_a_corpus_is_counted_as_one():
    """The other direction, so the census cannot report NONE forever: give a
    blocker the courier's corpus and the split must move. Without this, a
    hardcoded `NONE` would pass every case above."""
    with hooked_repo(arm=True) as root:
        blocker = blocking_hooks(root)[0]
        carrier = corpus_hooks(root)[0]
        blocker.write_text(carrier.read_text(encoding='utf-8')
                           + f'\nexit {hooks.BLOCK_EXIT}\n', encoding='utf-8')
        blockers = blocking_hooks(root)
        code, out = gate()
    assert f'1 of {len(blockers)} that can BLOCK' in out, out


def test_the_blocking_probe_reads_shape_not_prose():
    """The couriers document `exit 2` in their headers and never take it. A
    probe that matched the digits anywhere would count all seven hooks as
    blockers and print a ratio that is coverage of nothing."""
    with hooked_repo(arm=True) as root:
        for carrier in corpus_hooks(root):
            body = carrier.read_text(encoding='utf-8')
            assert 'exit 2' in body, carrier.name
            assert not hooks.BLOCKS_DECL.search(body), (
                f'{carrier.name} names exit 2 in prose only and was counted as '
                f'a hook that can block')


# --- the wiring: the gate runs here, and the repair it names is the target ----
def test_this_repo_runs_the_gate_in_its_own_aggregate():
    """A gate registered and never rostered is a gate that runs nowhere. This
    repo is the one that shipped the claim, so it is the one that must be red
    when it is unarmed."""
    config = tomllib.loads((REPO_ROOT / 'devkit.toml').read_text(encoding='utf-8'))
    roster = config.get('checks', {}).get('all', [])
    assert 'hooks' in roster, roster


def test_the_repair_the_gate_names_is_runnable_by_a_CONSUMER():
    """The repair has to work in the tree that TRIPS the gate. `make hooks` is
    this repo's own target and no consumer has it, so naming it sends a consumer
    to `No rule to make target`. The script is shipped by `install-hooks` into
    every tree, which is why it is the one named."""
    assert hooks.ARM_COMMAND == 'bash tools/setup-hooks.sh'
    shipped = REPO_ROOT / 'src/agentic_sdlc/repo/installables/setup-hooks.sh'
    assert shipped.is_file(), shipped
    install = (REPO_ROOT / 'src/agentic_sdlc/repo/install.py').read_text(encoding='utf-8')
    assert "'tools/setup-hooks.sh'" in install, 'the arm script must be an installable'



# --- the OTHER arming, which is not git's ------------------------------------
# `core.hooksPath` arms git's hooks and this module already proves the gate is
# satisfiable by the repair it names. It arms no `cc-*` hook — git never execs
# one — and the verdict said "armed" over the whole corpus anyway, which is the
# tool asserting an outcome for five of seven entries that it never observed.
# Measured while closing 0.6.0: three guard hooks registered, a session rooted
# one directory above the checkout, and `git commit` with no pathspec reaching
# git unblocked by the guard that exists to stop it. Nothing said a word.
def test_a_cc_hook_registered_nowhere_is_NAMED_not_silently_counted_as_armed():
    """`install-hooks` writes the corpus and no settings file, so this is the
    state every fresh adoption is in."""
    with hooked_repo(arm=True):
        code, out = gate()
    assert code == 0, out
    assert 'REGISTERED' in out, out
    assert f'NONE of the {CC_COUNT} {hooks.CC_PREFIX}hook(s) is registered' in out, out
    for rel in SHIPPED:
        name = Path(rel).name
        if name.startswith(hooks.CC_PREFIX):
            assert name in out, f'{name} is registered nowhere and is not named'


def test_write_settings_turns_the_registration_line_green_and_it_still_says_not_in_force():
    """The repair the line names, run — and the half it must NOT claim.

    A registration is a file on disk. Whether a harness READ that file depends
    on the session's project root, which no file in a checkout can decide, so
    the gate counts and never asserts (rule 4). If this line ever starts
    saying a guard IS in force, that is the sin, not a nicer verdict.
    """
    with hooked_repo(arm=True) as root:
        assert install.main('install-hooks', ['--write-settings']) == 0
        assert (root / hooks.SETTINGS_FILES[0]).is_file()
        code, out = gate()
    assert code == 0, out
    assert f'{CC_COUNT} of {CC_COUNT} {hooks.CC_PREFIX}hook(s) registered' in out, out
    assert 'not IN FORCE' in out, out
    assert "session's project root" in out, out


def test_an_allowlist_entry_naming_a_hook_is_not_a_registration():
    """The read is scoped to the `hooks` key, not to the file's TEXT. This
    package's own next-step text tells consumers to allowlist the hook
    commands, so a reader that searched the document for a hook's name would
    report every one of them registered off a permissions list — a gate saying
    a guard is armed because its name appears somewhere is rule 4's first sin
    with extra steps.

    PROVEN against that reader: planting `path.read_text()` in place of the
    scoped walk turns this line into `5 of 5 registered` and this case red.
    A structural walk over the whole DOCUMENT does not trip it — `allow` holds
    strings, not `{command: ...}` nodes — so the text reader is the shape this
    guards, and saying which one is the difference between a probe and a
    claim."""
    with hooked_repo(arm=True) as root:
        settings = root / hooks.SETTINGS_FILES[0]
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({'permissions': {'allow': [
            f'Bash(bash {HOOKS_DIR}/{name})' for name in
            (Path(rel).name for rel in SHIPPED)]}}), encoding='utf-8')
        code, out = gate()
    assert code == 0, out
    assert f'NONE of the {CC_COUNT} {hooks.CC_PREFIX}hook(s) is registered' in out, out


def test_a_command_node_outside_the_hooks_key_is_not_a_registration():
    """Review S8: the other wrong reader, and the one a refactor reaches for.

    `test_an_allowlist_entry_naming_a_hook_is_not_a_registration` catches a
    TEXT search and cannot catch a structural walk over the whole document,
    because `permissions.allow` holds strings rather than `{command: ...}`
    nodes. But `.claude/settings.json` really does carry command-shaped nodes
    outside `hooks` — `statusLine` is one — and `_commands` recurses over any
    dict, so dropping the `hooks` lookup would pass every other case here.

    PROVEN: with `_commands(data)` in place of `_commands(data['hooks'])` this
    line reads `1 of 5 registered` and this case goes red.
    """
    with hooked_repo(arm=True) as root:
        settings = root / hooks.SETTINGS_FILES[0]
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({'statusLine': {
            'type': 'command',
            'command': f'bash {HOOKS_DIR}/cc-stop-gate.sh --status'}}),
            encoding='utf-8')
        code, out = gate()
    assert code == 0, out
    assert f'NONE of the {CC_COUNT} {hooks.CC_PREFIX}hook(s) is registered' in out, out


def test_a_settings_file_that_is_not_json_is_reported_not_read_as_empty():
    """Unreadable and opted-out look identical from here, and they are
    different facts — the U4 shape, on this surface."""
    with hooked_repo(arm=True) as root:
        settings = root / hooks.SETTINGS_FILES[0]
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text('{not json', encoding='utf-8')
        code, out = gate()
    assert code == 0, out
    assert 'could not be read' in out, out
    assert 'it is not JSON' in out, out
