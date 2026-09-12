"""`shell` is derived here, from the source at collection, never by hand.

A module carries the mark when its source imports `subprocess` or binds a
`tests/support` name that reaches it (the helper set is a call-graph fixpoint).
Decided by AST, not grep, so a docstring naming `subprocess` is not a spawn. A
hand-written `shell` mark is refused by name: one mechanism is the point.
"""
from __future__ import annotations

import ast
import functools
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

MARK = 'shell'
SPAWN_MODULE = 'subprocess'
TESTS = Path(__file__).resolve().parent
SUPPORT = TESTS / 'support'


def _rel(path: Path) -> str:
    """`tests/test_x.py` for a file in this repo; the full path for anything else."""
    try:
        return str(path.relative_to(TESTS.parent))
    except ValueError:
        return str(path)


def _touches_subprocess(node: ast.AST) -> bool:
    """Does anything under `node` reach through the `subprocess` module?

    An attribute off the name, so `subprocess.run(...)` and `subprocess.Popen`
    both count and the string `'subprocess'` in a docstring does not.
    """
    return any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
               and n.value.id == SPAWN_MODULE
               for n in ast.walk(node))


def _called_names(node: ast.AST) -> set[str]:
    """Every name called under `node`, bare (`git(...)`) or attributed (`x.git(...)`)."""
    called: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                called.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                called.add(n.func.attr)
    return called


def _assigned_names(stmt: ast.stmt) -> set[str]:
    """The module-level names a top-level assignment binds."""
    if isinstance(stmt, ast.Assign):
        return {t.id for t in stmt.targets if isinstance(t, ast.Name)}
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return {stmt.target.id}
    return set()


def _attribute_root(node: ast.Attribute) -> str | None:
    """`support` for `support.pm.tree`; None when the chain is not rooted in a name."""
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


@functools.cache
def support_spawn_names() -> frozenset[str]:
    """Every name importable from `tests/support` whose use means a spawn.

    Three passes over the package. Each function's own body first: a
    `subprocess.<anything>` under it spawns. Then a fixpoint over the call
    graph, so `commit` joins `git` and a future wrapper of either joins on the
    collection after it is written. Then import time: a support module whose
    module-level code spawns promotes its own name and everything it defines,
    because importing it IS the spawn and the caller never names a helper.

    The graph is keyed by bare function name across the whole package, which
    over-approximates if two support modules ever define the same name.
    Over-marking costs one module its skip on three interpreters; under-marking
    costs the matrix a silent hole. The over-approximation is the safe side.
    """
    graph: dict[str, set[str]] = {}
    spawns: set[str] = set()
    defines: dict[str, set[str]] = {}
    module_level: dict[str, list[ast.stmt]] = {}
    for path in sorted(SUPPORT.glob('*.py')):
        module = SUPPORT.name if path.stem == '__init__' else path.stem
        defined = defines.setdefault(module, set())
        body = module_level.setdefault(module, [])
        for stmt in ast.parse(path.read_text(encoding='utf-8')).body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(stmt.name)
                graph[stmt.name] = _called_names(stmt)
                if _touches_subprocess(stmt):
                    spawns.add(stmt.name)
            else:
                if isinstance(stmt, ast.ClassDef):
                    defined.add(stmt.name)
                defined |= _assigned_names(stmt)
                body.append(stmt)
    changed = True
    while changed:
        changed = False
        for function, called in graph.items():
            if function not in spawns and called & spawns:
                spawns.add(function)
                changed = True
    for module, body in module_level.items():
        if any(_touches_subprocess(s) or (_called_names(s) & spawns) for s in body):
            spawns |= defines[module] | {module}
    return frozenset(spawns)


@functools.cache
def module_spawns(path: Path) -> bool:
    """Does this test module's source spawn a process?

    Not a guess about runtime: the two ways a module in this suite can reach a
    spawn are importing `subprocess` and binding a `tests/support` name that
    does. Source is read once per module and cached — pytest asks per item, and
    a file does not change under a running session.
    """
    tree = ast.parse(path.read_text(encoding='utf-8'))
    bound: set[str] = set()
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split('.')
                if parts[0] == SPAWN_MODULE:
                    return True
                if SUPPORT.name not in parts:
                    continue
                # `import support` binds `support`; `import support.pm as sp`
                # binds `sp`. Either way the bound name and the module's own
                # name both matter, for an import-time spawner.
                aliases.add(alias.asname or parts[0])
                bound |= {alias.asname or parts[0], parts[-1]}
        elif isinstance(node, ast.ImportFrom):
            parts = (node.module or '').split('.')
            if parts[0] == SPAWN_MODULE:
                return True
            if SUPPORT.name not in parts:
                continue
            for alias in node.names:
                bound.add(alias.name)
                if (SUPPORT / f'{alias.name}.py').exists():
                    aliases.add(alias.asname or alias.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and _attribute_root(node) in aliases:
            bound.add(node.attr)
    return bool(bound & support_spawn_names())


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Apply the derived mark, and refuse a hand-written one by name.

    `tryfirst`, because pytest's own `-m` filtering is a
    `pytest_collection_modifyitems` too: the mark has to be on the items before
    the expression is evaluated, or `-m shell` selects nothing.
    """
    hand_applied = sorted({_rel(item.path) for item in items
                           if item.get_closest_marker(MARK)})
    if hand_applied:
        raise pytest.UsageError(
            f'hand-applied `{MARK}` mark in: {", ".join(hand_applied)}. '
            f'`{MARK}` is DERIVED in tests/conftest.py from what the module '
            f'source does — it imports `{SPAWN_MODULE}`, or it uses a '
            'tests/support helper that spawns. Delete the mark: if the module '
            'really shells out the mark is already there, and if it does not, '
            'the mark is a claim the source does not support.')
    for item in items:
        if module_spawns(item.path):
            item.add_marker(MARK)


# --- the derivation is STATIC, so a runtime guard stands behind it -----------
# `module_spawns` reads a module's SOURCE. It cannot see a spawn reached
# INDIRECTLY — a unit test calling a library function that, four frames down,
# runs the real belt whose `gate` check is `make milestone`. That happened
# (0.3.0/bugs/a-unit-test-can-spawn-the-full-gate): `release ''` stopped being
# refused, resolved a version from the plan instead, and the refusal-matrix
# case started running the FULL MATRIX GATE inside the unit tier. `make unit`
# went from 7 s to 153 s, and nothing said why — it just got slow.
#
# That is the 170x this package exists to end, reached from inside its own
# suite. The static mark cannot catch it and no amount of prose in a brief did.
# So the tier's definition is ENFORCED rather than merely derived: outside the
# `shell` tier, a spawn fails the test that made it, immediately, by nodeid.
#
# `subprocess.Popen` is the one chokepoint — `run`, `call`, `check_output` and
# `check_call` all construct one — and `SPAWN_MODULE` above is what the
# derivation already looks for, so the guard and the mark police one mechanism.
def _spawn_refusal(item) -> str:
    return (f'{item.nodeid} is in the `not {MARK}` tier and tried to spawn a '
            f'process.\n'
            f'Either it reaches a spawn INDIRECTLY — which is the defect: a '
            f'unit test must not run a gate, a make target or a belt with its '
            f'real registry — or the module genuinely shells out, in which '
            f'case make the reach VISIBLE to tests/conftest.py `module_spawns` '
            f'(import `{SPAWN_MODULE}` at module level, or go through a '
            f'tests/support helper that does) so the mark is derived and the '
            f'case runs in the right tier.\n'
            f'Never hand-apply the mark; it is refused by name.')


@pytest.fixture(autouse=True)
def _no_spawn_outside_the_shell_tier(request, monkeypatch):
    """Outside the `shell` tier, a spawn is an immediate, named failure.

    Rule 4's shape: the alternative is a suite that silently gets 20x slower
    and a reader who has to think to run `--durations` to find out why.
    """
    if request.node.get_closest_marker(MARK):
        return
    real = subprocess.Popen
    item = request.node

    def refused(*args, **kwargs):
        raise AssertionError(_spawn_refusal(item)
                             + f'\n  the call: {args[0] if args else kwargs.get("args")!r}')

    monkeypatch.setattr(subprocess, 'Popen', refused)
    # A helper holding its own reference is still the same object; this is the
    # class every caller constructs, so rebinding the module attribute is what
    # every `subprocess.run(...)` in the tree goes through.
    assert real is not refused


# --- the suite records what its own tail cost ---------------------------------
# `make unit` / `make integration` / `make test` already file a `gate` row
# carrying the TIER's duration. That answers "did it get slower" and not "where"
# — and where is the half you can act on. Two cases in this suite were once 47
# of 96 seconds, and no artifact anywhere recorded that fact; it took a
# `--durations` run somebody thought to do.
#
# So the slowest few of every gated run land in the ledger as `test` rows.
#
# ONLY THE SLOWEST FEW. A row per test is ~1850 rows per run into a file that
# persists, and a ledger that doubles every afternoon is one somebody deletes.
# The tail is where a suite's wall clock lives, so the tail is what earns
# durable space.
#
# GUARDED ON AN ENV VAR the make targets set, and never on by default. An
# ad-hoc `pytest -k something` would otherwise file a "slowest test" list from a
# run of four tests, which is a measurement of nothing recorded as though it
# were one — rule 4's zero census, wearing a stopwatch.
#
# `pytest_terminal_summary` rather than `pytest_sessionfinish`: under xdist the
# latter fires on every worker AND the controller, so each worker would file its
# own partial tail. The terminal summary runs once, on the controller, over the
# reports every worker sent back.
TIER_ENV = 'GDK_TEST_TIER'
SLOWEST = 5


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    tier = os.environ.get(TIER_ENV, '')
    if not tier or hasattr(config, 'workerinput'):
        return
    calls = [r for r in terminalreporter.stats.get('passed', [])
             if getattr(r, 'when', '') == 'call']
    if not calls:
        return
    slowest = sorted(calls, key=lambda r: r.duration, reverse=True)[:SLOWEST]
    try:
        from agentic_sdlc.repo.pm import ledger, vocabulary
        cfg = vocabulary.load()
        # THE TREE's ledger, and both sides of this merge were reaching for
        # the same thing: 0.3.0's review C2 asked that these land WHERE THE
        # GATE ROWS LAND, because a slowest-tier line and the gate row it sits
        # beside must describe one run. 0.4.0/D3 then made that one file for
        # both — a `test` row names no grain, like a `gate` row — so the
        # agreement C2 asked for is now structural rather than a resolution
        # copied into two places. #48 moved that file to the gitignored
        # `ledger.local.jsonl`, and both still land in the same one.
        for rank, report in enumerate(slowest, start=1):
            ledger.append_to(ledger.local_path(cfg.roadmap),
                             ledger.test_row(
                                 tier, report.nodeid,
                                 int(report.duration * 1000), rank))
    except Exception as err:  # noqa: BLE001 — telemetry never fails a suite
        # FAILING OPEN, deliberately. A suite that went red because it could
        # not write its own cost row would be telemetry outranking the thing it
        # measures, which is the ruling `check budget` is built on one layer up.
        terminalreporter.write_line(
            f'[tier:{tier}] could not record slow-test rows: '
            f'{type(err).__name__}: {err}')


# --- the suite never reaches the repository it is gating ----------------------
# 0.8.0 (bg-the-suite-run-in-a-worktree-mutates-the-host-repo): `git bisect run`
# EXPORTS `GIT_DIR` into its child, and in a linked worktree that is
# `.git/worktrees/<name>`. Every `git init -q <tmp>` in the suite then
# re-initialised THAT repository instead of the temp tree — and because the path
# does not end in `/.git`, git guesses the result is bare and writes
# `core.bare = true` into the COMMON config, which every checkout shares. The
# `git add -A; git commit -qm scratch` after it committed the temp tree onto the
# worktree's HEAD. All 12 git-spawning modules, each run so, flipped the bit;
# the per-call `cwd=` the boundary test enforces does not help, because
# `GIT_DIR` outranks cwd. A `pre-commit` hook is the same hazard: measured on
# git 2.50.1, it inherits `GIT_INDEX_FILE` everywhere and, in a linked
# worktree, `GIT_DIR` as well.
#
# So the session removes what git itself says to clear before reaching a
# repository other than the one it was started for — `git rev-parse
# --local-env-vars`, which `tests/test_host_guard.py` holds this list to — plus
# `GIT_NAMESPACE`, which that list omits and which still re-roots a ref write.
# And it sets `GIT_CEILING_DIRECTORIES` to the temp root, so a spawn in a temp
# tree that never ran `git init` cannot walk up into a repository that holds
# the temp directory. Done at `pytest_configure`, before collection, because a
# support module may spawn at import; xdist workers inherit the result.
GIT_LOCAL_ENV = (
    'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG', 'GIT_CONFIG_PARAMETERS',
    'GIT_CONFIG_COUNT', 'GIT_OBJECT_DIRECTORY', 'GIT_DIR', 'GIT_WORK_TREE',
    'GIT_IMPLICIT_WORK_TREE', 'GIT_GRAFT_FILE', 'GIT_INDEX_FILE',
    'GIT_NO_REPLACE_OBJECTS', 'GIT_REPLACE_REF_BASE', 'GIT_PREFIX',
    'GIT_SHALLOW_FILE', 'GIT_COMMON_DIR', 'GIT_NAMESPACE',
)
CEILING = 'GIT_CEILING_DIRECTORIES'


def scrub_git_env(environ) -> None:
    for name in GIT_LOCAL_ENV:
        environ.pop(name, None)
    temp_root = os.path.realpath(tempfile.gettempdir())
    ceilings = [c for c in environ.get(CEILING, '').split(os.pathsep) if c]
    if temp_root not in ceilings:
        environ[CEILING] = os.pathsep.join([*ceilings, temp_root])


def pytest_configure(config) -> None:
    scrub_git_env(os.environ)


# --- and a session that moved it anyway FAILS, by name ------------------------
# The guard removes the one mechanism reproduced. The ratchet catches the next
# one: the host's `core.bare`, its `HEAD` and the branch `HEAD` names are read at
# session start and again at the end, and any that moved turns the session red
# naming the field. READ AS TEXT, never by spawning git: a `git` pointed at this
# checkout is exactly what `NoTestSpawnsGitAgainstThisCheckout` refuses, and
# reading three files boots nothing in the unit tier. The HOST is the checkout
# this conftest sits in, so a copy of it under a scratch repo holds that repo.
HOST = TESTS.parent
HOST_AT_START = pytest.StashKey[dict]()


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeDecodeError):
        return ''


def _gitdirs(root: Path) -> tuple[Path, Path] | None:
    """(this checkout's gitdir, the common dir). A linked worktree's `.git` is
    a FILE naming its gitdir, whose `commondir` names where config and
    branches live."""
    dot = root / '.git'
    if dot.is_dir():
        return dot, dot
    pointed = _text(dot)
    if not pointed.startswith('gitdir:'):
        return None
    gitdir = (root / pointed[len('gitdir:'):].strip()).resolve()
    common = _text(gitdir / 'commondir')
    return gitdir, (gitdir / common).resolve() if common else gitdir


def _core_bare(config: str) -> str:
    """The last `bare` under `[core]`, as written — or `unset`."""
    section, value = '', 'unset'
    for raw in config.splitlines():
        line = raw.strip()
        if line.startswith('['):
            section = (line[1:].split(']', 1)[0].split() or [''])[0].lower()
            continue
        key, sep, rest = line.partition('=')
        if section == 'core' and key.strip().lower() == 'bare':
            value = rest.split('#', 1)[0].split(';', 1)[0].strip() if sep else 'true'
    return value


def host_state(root: Path) -> dict[str, str]:
    """`core.bare`, `HEAD`, and the branch HEAD names — each as its file says."""
    dirs = _gitdirs(root)
    if dirs is None:
        return {'.git': f'no git checkout at {root}'}
    gitdir, common = dirs
    head = _text(gitdir / 'HEAD')
    state = {'core.bare': _core_bare(_text(common / 'config')), 'HEAD': head}
    if head.startswith('ref:'):
        ref = head[len('ref:'):].strip()
        packed = [line.split(' ', 1)[0]
                  for line in _text(common / 'packed-refs').splitlines()
                  if line.endswith(f' {ref}')]
        state[ref] = _text(common / ref) or ''.join(packed[-1:]) or 'unreadable'
    return state


def host_moved(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return [f'  {field}: {before.get(field, "absent")} -> {after.get(field, "absent")}'
            for field in dict.fromkeys([*before, *after])
            if before.get(field) != after.get(field)]


def pytest_sessionstart(session) -> None:
    if not hasattr(session.config, 'workerinput'):
        session.config.stash[HOST_AT_START] = host_state(HOST)


def pytest_sessionfinish(session, exitstatus) -> None:
    """Under xdist this fires on every worker too; only the controller holds
    a snapshot, and it runs after the workers are done."""
    before = session.config.stash.get(HOST_AT_START, None)
    if before is None:
        return
    reporter = session.config.pluginmanager.get_plugin('terminalreporter')

    def write(line: str) -> None:
        if reporter is None:
            print(line)
            return
        reporter.ensure_newline()
        reporter.write_line(line)

    unheld = [f'{k} ({v})' for k, v in before.items() if k == '.git' or v == 'unreadable']
    if unheld:
        write(f'host ratchet: nothing held for {", ".join(unheld)}')
    moved = host_moved(before, host_state(HOST))
    if not moved:
        return
    write(f'THE SUITE MOVED ITS HOST REPOSITORY — {HOST}')
    for line in moved:
        write(line)
    write('A test reached this checkout with git: an inherited GIT_DIR, a spawn '
          'with no cwd=, a temp tree that never ran `git init`. This ratchet '
          'reads state, not authorship — a commit YOU made here during the run '
          'moves HEAD too; `git log -1 <sha>` says whose it is. A flipped bare '
          'is restored with `git config core.bare false`.')
    if session.exitstatus in (pytest.ExitCode.OK,
                              pytest.ExitCode.NO_TESTS_COLLECTED):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
