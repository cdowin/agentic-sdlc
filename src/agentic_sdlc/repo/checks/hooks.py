"""check hooks — the tracked hook corpus under `tools/hooks/` is armed and every hook runs.

Five questions per entry: `core.hooksPath` points here; the entry is a regular file;
it carries an exec bit; it starts (a `cc-*` hook fails open on unreadable input, any
other parses under `bash -n`); and one naming `--self-test` replays its corpus and
prints `SELF-TEST OK`. Which hooks carry a corpus, and which can block (`exit 2`), is
derived from each hook's text, never a roster. `_*` and `*.local` are excluded and
disclosed. Zero hooks, or zero replays, is a finding.

TWO ARMINGS, and only one is git's. `core.hooksPath` arms the git hooks and is
verified. A `cc-*` hook is a Claude Code hook that git never execs; what arms it is
a settings file, and whether a harness READ that file depends on the session's
project root. So its registration is COUNTED on a REGISTERED line and never
asserted — the same sentence `check pm` U4 owes the ledger couriers.

No devkit.toml section: `tools/hooks/` is where `install-hooks` writes in every consumer.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from agentic_sdlc.core import spawn, walk
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.core.walk import Kind, SkipReason, Walk

HOOKS_DIR = 'tools/hooks'
CC_PREFIX = 'cc-'
# A consumer must be able to run the repair; no make target wraps it.
ARM_COMMAND = 'bash tools/setup-hooks.sh'

# Every Claude Code hook promises exit 0 and a reason on stderr for this.
UNREADABLE_PAYLOAD = 'not json {{{'
FAIL_OPEN = 0
LABEL_WIDTH = len('NOT EXECUTABLE')

# The marker matters as much as the exit code: an unhandled flag falls through to exit 0.
SELF_TEST_FLAG = '--self-test'
SELF_TEST_OK = 'SELF-TEST OK'
# A non-comment line naming the flag nominates a candidate; the run is the proof.
SELF_TEST_DECL = re.compile(rf'^(?![ \t]*#).*{re.escape(SELF_TEST_FLAG)}',
                            re.MULTILINE)

# A statement-initial `exit 2`, because the couriers name the digit only in prose.
BLOCK_EXIT = 2
BLOCKS_DECL = re.compile(rf'^[ \t]*exit[ \t]+{BLOCK_EXIT}\b', re.MULTILINE)


# --- the OTHER arming, and it is not git's (0.6.0/D6) -------------------------
SETTINGS_FILES = ('.claude/settings.json', '.claude/settings.local.json')


def _commands(node: object) -> list[str]:
    """Every `command` string under a settings file's `hooks` key — never the
    document's text, where an allowlist entry reads as a registration."""
    found: list[str] = []
    if isinstance(node, dict):
        command = node.get('command')
        if isinstance(command, str):
            found.append(command)
        for key, value in node.items():
            if key != 'command':
                found.extend(_commands(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_commands(item))
    return found


def settings_commands(path: Path) -> tuple[tuple[str, ...], str]:
    """(the hook commands this one settings file registers, why it was unread).

    Absent is `((), '')` and never a defect: a tree that registers nothing has
    opted out (0.4.0/D5). `check pm`'s courier rules read through this too.
    """
    if not path.is_file():
        return (), ''
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError) as err:
        return (), err.__class__.__name__
    except ValueError as err:
        return (), f'it is not JSON: {err}'
    return tuple(_commands(data.get('hooks') if isinstance(data, dict)
                           else None)), ''


def _registered(root: Path, names: list[str]) -> tuple[set[str], str, str]:
    """(which of `names` a settings file registers, where, why unread)."""
    found: set[str] = set()
    where: list[str] = []
    unread: list[str] = []
    for rel in SETTINGS_FILES:
        commands, why = settings_commands(root / rel)
        if why:
            unread.append(f'{rel} could not be read ({why})')
            continue
        here = {name for name in names
                if any(name in command for command in commands)}
        if here:
            found |= here
            where.append(rel)
    return found, ' and '.join(where), '; '.join(unread)


def _arming(root: Path, agent_hooks: list[str]) -> str:
    """What is registered for the `cc-*` half, and what registration is worth.

    Counted, never asserted, and the measurement that ruled it: 0.6.0/D6.
    """
    registered, where, unread = _registered(root, agent_hooks)
    missing = sorted(set(agent_hooks) - registered)
    said = [f'{len(registered)} of {len(agent_hooks)} {CC_PREFIX}hook(s) '
            f'registered in {where}' if registered else
            f'NONE of the {len(agent_hooks)} {CC_PREFIX}hook(s) is registered '
            f'in a settings file in this checkout']
    if missing:
        said.append(f'{", ".join(missing)} registered nowhere here')
    if unread:
        said.append(unread)
    return (f'{"; ".join(said)} — `install-hooks --write-settings` lands the '
            f'block. Registered is not IN FORCE: whether a harness reads that '
            f'file depends on the session\'s project root, so this is counted, '
            f'never asserted')


def _entries(directory: Path) -> Walk:
    """The hook entry points, `Kind.ANY` so a directory or broken symlink is a finding, not a subtraction."""
    return walk.children(directory, Kind.ANY).filter(
        lambda path: not path.name.startswith('_')
        and not path.name.endswith('.local'),
        SkipReason.EXCLUDED_PATH)


def _not_a_file(path: Path) -> str:
    """What an entry git cannot exec actually is."""
    if path.is_dir():
        return 'is a directory'
    if path.is_symlink():
        return f'is a symlink to {os.readlink(path)}, which does not resolve'
    if not path.exists():
        return 'does not resolve'
    return 'is not a regular file'


def _hooks_path(root: Path) -> str:
    done = spawn.run(['git', 'config', '--get', 'core.hooksPath'],
                     cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ''


def _runs(path: Path, root: Path) -> str:
    """'' when the hook started and answered; the finding text when it did not."""
    if path.name.startswith(CC_PREFIX):
        done = spawn.run(['bash', str(path)], input=UNREADABLE_PAYLOAD,
                         text=True, capture_output=True, cwd=root)
        if done.returncode != FAIL_OPEN:
            said = (done.stderr or done.stdout).strip().splitlines()
            return (f'exited {done.returncode} on a payload it cannot read, '
                    f'where every Claude Code hook fails OPEN at '
                    f'{FAIL_OPEN} — it is installed and it stops nothing'
                    + (f': {said[-1]}' if said else ''))
        return ''
    done = spawn.run(['bash', '-n', str(path)], capture_output=True,
                     text=True, cwd=root)
    if done.returncode != 0:
        return f'does not parse: {done.stderr.strip().splitlines()[-1]}'
    return ''


def _source(path: Path) -> str:
    """The hook's text, or '' when unreadable (already a finding from `_runs`)."""
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def _self_test(path: Path, root: Path) -> str:
    """'' when the hook's own corpus replayed clean; the finding text when not.

    `input=''` keeps a hook that reads stdin from blocking on a terminal.
    """
    done = spawn.run(['bash', str(path), SELF_TEST_FLAG], input='',
                     text=True, capture_output=True, cwd=root)
    said = (done.stderr or done.stdout).strip().splitlines()
    tail = f': {said[-1]}' if said else ''
    if done.returncode != 0:
        return (f'fails its own {SELF_TEST_FLAG} corpus (exit '
                f'{done.returncode}){tail}')
    if SELF_TEST_OK not in done.stdout:
        return (f'names {SELF_TEST_FLAG} and does not answer it — exit 0 with '
                f'no {SELF_TEST_OK!r} line, so nothing was replayed and the '
                f'zero it reports is not a pass{tail}')
    return ''


def run() -> int:
    root = repo_root()
    hooks = root / HOOKS_DIR
    findings: list[tuple[str, str]] = []

    configured = _hooks_path(root)
    if not configured:
        findings.append((
            'UNARMED',
            f'core.hooksPath is unset, so git runs nothing under {HOOKS_DIR}/ '
            f'whatever is in it — `{ARM_COMMAND}`'))
    elif Path(os.path.normpath(root / configured)) != hooks:
        findings.append((
            'MISDIRECTED',
            f'core.hooksPath is {configured!r} — that is '
            f'{os.path.normpath(root / configured)}, not {hooks} — '
            f'`{ARM_COMMAND}`'))

    if not hooks.is_dir():
        print(f'[check:hooks] FAIL — there is no {HOOKS_DIR}/ directory; '
              f'`agentic-sdlc install-hooks` ships the corpus and '
              f'`{ARM_COMMAND}` arms it')
        return 1
    entries = _entries(hooks)
    census = entries.census(f'hook(s) under {HOOKS_DIR}/')
    if not entries.kept:
        print(f'[check:hooks] FAIL — {census}, so this reports on nothing; '
              f'`agentic-sdlc install-hooks` ships the corpus')
        return 1
    if shutil.which('bash') is None:
        # The corpus is bash, so no bash is the finding, not a caveat.
        print(f'[check:hooks] FAIL — bash is not on PATH, so not one of the '
              f'{census} can run')
        return 1

    ran = parsed = replayed = 0
    agent_hooks: list[str] = []
    # Counted only over hooks that started, like every other number in the verdict.
    blockers = blockers_replayed = 0
    for path in entries:
        rel = path.relative_to(root)
        if not path.is_file():
            findings.append((
                'NOT A FILE',
                f'{rel} {_not_a_file(path)} — git cannot exec it, so whatever '
                f'guard that name stands for runs nothing; `_`-prefix it if it '
                f'is not a hook — `{ARM_COMMAND}`'))
            continue
        if not os.access(path, os.X_OK):
            findings.append((
                'NOT EXECUTABLE',
                f'{rel} — core.hooksPath skips it in silence — '
                f'`{ARM_COMMAND}`'))
            continue
        broken = _runs(path, root)
        if broken:
            # One finding per hook: a dead hook cannot replay a corpus either.
            findings.append(('DEAD', f'{rel} {broken}'))
            continue
        if path.name.startswith(CC_PREFIX):
            ran += 1
            agent_hooks.append(path.name)
        else:
            parsed += 1
        source = _source(path)
        blocks = bool(BLOCKS_DECL.search(source))
        if blocks:
            blockers += 1
        if SELF_TEST_DECL.search(source):
            replayed += 1
            if blocks:
                blockers_replayed += 1
            failed = _self_test(path, root)
            if failed:
                findings.append(('SELF-TEST', f'{rel} {failed}'))

    if not replayed:
        # An uninstalled corpus and a passing one look identical from here.
        findings.append((
            'NO CORPUS',
            f'not one hook under {HOOKS_DIR}/ declares a {SELF_TEST_FLAG} '
            f'corpus, so nothing was replayed — an uninstalled corpus and a '
            f'passing one print the same word from here'))

    # Spelled in words on the two shapes a bare ratio reads wrong.
    if not blockers:
        covered = f'no hook here can BLOCK at exit {BLOCK_EXIT}'
    elif not blockers_replayed:
        covered = (f'NONE of the {blockers} that can BLOCK (exit {BLOCK_EXIT}) '
                   f'— the replay covers only hooks that always allow')
    else:
        covered = f'{blockers_replayed} of {blockers} that can BLOCK'
    scope = (f'{census}; {ran} fail open on a payload they cannot read, '
             f'{parsed} parse, {replayed} replay their own {SELF_TEST_FLAG} '
             f'corpus, {covered}')
    # NAMED, never asserted (rule 4): a registration is not a hook that ran.
    if agent_hooks:
        print(f'  {"REGISTERED":<{LABEL_WIDTH}} {_arming(root, agent_hooks)}')
    if findings:
        for label, said in findings:
            print(f'  {label:<{LABEL_WIDTH}} {said}')
        print(f'[check:hooks] FAIL — {len(findings)} finding(s) across {scope}')
        return 1
    print(f'[check:hooks] PASS — git-armed at {configured}; {scope}')
    return 0
