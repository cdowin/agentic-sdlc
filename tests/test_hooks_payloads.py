"""test_hooks_payloads.py — the installed Claude Code hooks, fired at real
PreToolUse payloads.

test_install.py proves the install verbs and fires one block/allow pair per
hook; this file is the behavior matrix. Each hook is installed into an empty
temp repo — no library, no Makefile, nothing a consumer might lack — and RUN
against the JSON payload shape Claude Code actually delivers. Exit 0 is allow,
exit 2 is a BLOCK.

Every "pre-fix:" annotation below is a case that returned the WRONG verdict at
d76eeea, verified by firing the
HEAD copies of the hooks against these exact payloads before the fix landed:

cc-commit-pathspec.sh — `--pathspec-from-file` (both spellings) IS naming
paths, but the space spelling was consumed as an argument-taking flag without
setting the pathspec verdict, and the `=` spelling fell into the generic
`--*=*` skip: both false-BLOCKED, the one false-positive class the hook's own
header promises must not exist.
"""
from __future__ import annotations

import atexit
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
from support.pm import FLOW_TOML  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import install  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which('bash') is None,
                                reason='needs bash')

PATHSPEC = 'tools/hooks/cc-commit-pathspec.sh'


@pytest.fixture(scope='module')
def hooks_repo(tmp_path_factory) -> Path:
    """One empty repo with the hooks installed; every case fires against it.
    The hooks are read-only over the tree, so sharing one install is safe."""
    root = tmp_path_factory.mktemp('hooks') / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
    previous = Path.cwd()
    os.chdir(root)
    repo_root.cache_clear()
    load_config.cache_clear()
    try:
        assert install.main('install-hooks', []) == 0
    finally:
        os.chdir(previous)
        repo_root.cache_clear()
        load_config.cache_clear()
    return root


def fire(root: Path, hook: str, command: str, cwd: str = '') -> int:
    event = json.dumps({'tool_name': 'Bash',
                        'tool_input': {'command': command},
                        'cwd': cwd or str(root)})
    return subprocess.run(['bash', str(root / hook)], input=event,
                          text=True, capture_output=True).returncode


def test_agent_hook_runs_the_stamped_dispatch_preflight(hooks_repo, tmp_path):
    """The real PreToolUse hook must hand its stamp to the strict CLI check."""
    (hooks_repo / 'Makefile').write_text('sdlc:\n\t@true\n', encoding='utf-8')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    log = tmp_path / 'make-args'
    make = bindir / 'make'
    make.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$HOOK_MAKE_LOG"\n'
                    'echo "feature close is ready"\n'
                    '[ "${HOOK_MAKE_ALLOW:-}" = yes ]\n', encoding='utf-8')
    make.chmod(0o755)
    hook = hooks_repo / 'tools/hooks/cc-agent-isolation.sh'
    payload = json.dumps({'tool_name': 'Agent', 'tool_input': {
        'prompt': 'GDK-STAMP grain=0.1/alpha/s0 issue=112\nBuild the story.'}})
    env = {**os.environ, 'PATH': f'{bindir}{os.pathsep}{os.environ["PATH"]}',
           'HOOK_MAKE_LOG': str(log)}
    blocked = subprocess.run(['bash', str(hook)], cwd=hooks_repo, input=payload,
                             text=True, capture_output=True, env=env)
    assert blocked.returncode == 2, blocked.stdout + blocked.stderr
    assert 'dispatch --preflight --grain 0.1/alpha/s0' in log.read_text()
    assert 'feature close is ready' in blocked.stderr
    allowed = subprocess.run(['bash', str(hook)], cwd=hooks_repo, input=payload,
                             text=True, capture_output=True,
                             env={**env, 'HOOK_MAKE_ALLOW': 'yes'})
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr


def test_agent_hook_fails_closed_for_declared_guard_without_makefile(hooks_repo):
    (hooks_repo / 'Makefile').unlink(missing_ok=True)
    (hooks_repo / 'devkit.toml').write_text(
        '[dispatch]\nguard = true\n', encoding='utf-8')
    hook = hooks_repo / 'tools/hooks/cc-agent-isolation.sh'
    payload = json.dumps({'tool_name': 'Agent', 'tool_input': {'prompt': 'Build.'}})
    blocked = subprocess.run(['bash', str(hook)], cwd=hooks_repo, input=payload,
                             text=True, capture_output=True)
    assert blocked.returncode == 2
    assert 'guard = true' in blocked.stderr
    assert 'no Makefile' in blocked.stderr

    # An unconfigured stock repo retains the hook's default allow behavior.
    (hooks_repo / 'devkit.toml').unlink()
    allowed = subprocess.run(['bash', str(hook)], cwd=hooks_repo, input=payload,
                             text=True, capture_output=True)
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr


# --- cc-commit-pathspec: --pathspec-from-file IS a pathspec -------------------
ALLOWED = (
    # pre-fix: all four false-BLOCKED (exit 2)
    'git commit --pathspec-from-file list.txt',
    'git commit --pathspec-from-file=list.txt -m "msg"',
    'git commit -m "fix: x" --pathspec-from-file list.txt',
    'git commit --pathspec-from-file=- -m "msg"',
    # the exemptions that predate the fix
    'git commit -m "fix: x" -- a.py',      # explicit `--` pathspec
    'git commit -m "fix: x" a.py',         # bare path argument
    'git commit --amend',                  # exempt: another rule's territory
    'git commit --dry-run',                # exempt: writes nothing
    'git status',                          # not a commit at all
    # pre-fix: false-BLOCKED — a scratch probe's repo is not this repository
    'git -C /tmp/x -c user.name=probe commit -qm base',
)
BLOCKED = (
    'git commit -m "fix: x"',
    'git commit -am "sweep"',
    'git commit --all -m "sweep"',
    'git -C sub commit -m "sweep"',        # `-C` inside this repository
    # pre-fix (bb81f46): false-ALLOWED — only an absolute `-C`, in a command
    # that neither points git elsewhere nor makes a link, is a probe's
    'cd src && git -C .. commit -am sweep',
    'git -C ~/scratch commit -m sweep',
    'git -C /tmp --git-dir=/r/.git --work-tree=/r commit -am sweep',
    'GIT_DIR=/r/.git git -C /tmp/x commit -m sweep',
    'ln -s /r /tmp/l && git -C /tmp/l commit -m sweep',
)


def test_pathspec_allows_every_path_naming_spelling_and_blocks_the_pathless(
        hooks_repo, tmp_path):
    """Twenty rows, one case, both directions: a hook that blocks everything
    and a hook that is disarmed are equally broken, and only the pair tells
    them apart. A row that answers wrongly names itself. The last row is the
    hook's own checkout, from a scratch repo a `cd` moved cwd into (pre-fix:
    allowed)."""
    (tmp_path / '.git').mkdir()
    wrong = ([f'BLOCKED: {c}' for c in ALLOWED
              if fire(hooks_repo, PATHSPEC, c) != 0]
             + [f'allowed: {c}' for c in BLOCKED
                if fire(hooks_repo, PATHSPEC, c) != 2]
             + [f'allowed from scratch: {c}' for c in [f'git -C {hooks_repo} commit -am sweep']
                if fire(hooks_repo, PATHSPEC, c, cwd=str(tmp_path)) != 2])
    assert not wrong, wrong


# =============================================================================
# The 0.16.0 corpus: cc-stop-gate, cc-write-confine, pre-push,
# prepare-commit-msg, agent-worktree — installed into temp repos and RUN, the
# same way the hook above is proven. The git hooks and tools are exercised
# through REAL git operations (push, commit, worktree), not by feeding them
# synthetic argv.
# =============================================================================

STOP_GATE = 'tools/hooks/cc-stop-gate.sh'
CONFINE = 'tools/hooks/cc-write-confine.sh'
WORKTREE = 'tools/dev/agent-worktree.sh'
MARKER = '.agent-scope'

# The corpus reads DEVKIT_AGENT_SCOPE; a test machine that happens to export
# it would flip every trunk/agent distinction below.
# `GDK_LEDGER_GRAIN` beside `DEVKIT_AGENT_SCOPE`, and for the same reason one
# layer up: an operator with it exported turns every case here that asserts a
# row's grain — or its absence — into a claim about their shell rather than
# about the courier. Proven: with it set, the stock dispatch case FAILS. The
# couriers' own `--self-test` builds its child environment for exactly this;
# this is the twin that runs in CI and in `make precommit`.
CLEAN_ENV = {k: v for k, v in os.environ.items()
             if k not in ('DEVKIT_AGENT_SCOPE', 'GDK_LEDGER_GRAIN')}


# The corpus repo is built ONCE per process and COPIED per case: the build is
# seven spawns (init, config, arm, add, a commit that fires the armed hook) and
# ~45 cases asked for it, where a copy of its ~80 files is a hundredth of that.
# Nothing in it is absolute — `core.hooksPath` is relative and no worktree is
# registered — so a copy is the same repo. Lazy and fixture-free, because
# test_fixture_flows.py calls `ledger_repo` from outside this module; removed
# when the process exits.
_TEMPLATE: list[Path] = []


def corpus_repo(parent: Path, name: str = 'repo') -> Path:
    """A git repo with the full corpus installed, armed, committed, and one
    commit on `main` — the smallest tree every scenario below can build on.
    A copy of the process's one build."""
    if not _TEMPLATE:
        home = Path(tempfile.mkdtemp(prefix='corpus-template-'))
        atexit.register(shutil.rmtree, home, True)
        _build_corpus_repo(home / 'repo')
        _TEMPLATE.append(home / 'repo')
    root = parent / name
    _copy_corpus_template(_TEMPLATE[0], root)
    return root


def _ignore_transient_git_object_lock(directory: str, names: list[str]) -> set[str]:
    """Skip only Git's ephemeral object-maintenance lock while copying a repo.

    Git may create and remove this lock concurrently during fixture setup or
    another worker's copy. It is never repository content; other files with
    the same basename must still be copied.
    """
    path = Path(directory)
    if path.name == 'objects' and path.parent.name == '.git':
        return {'maintenance.lock'} if 'maintenance.lock' in names else set()
    return set()


def _copy_corpus_template(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, symlinks=True,
                    ignore=_ignore_transient_git_object_lock)


def test_corpus_copy_skips_only_transient_git_maintenance_lock(tmp_path):
    source = tmp_path / 'source'
    objects = source / '.git' / 'objects'
    objects.mkdir(parents=True)
    (objects / 'maintenance.lock').write_text('ephemeral')
    (source / 'maintenance.lock').write_text('ordinary fixture content')
    (source / 'payload').write_text('kept')

    copied = tmp_path / 'copied'
    _copy_corpus_template(source, copied)

    assert not (copied / '.git' / 'objects' / 'maintenance.lock').exists()
    assert (copied / 'maintenance.lock').read_text() == 'ordinary fixture content'
    assert (copied / 'payload').read_text() == 'kept'


def _build_corpus_repo(root: Path) -> None:
    root.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=root, check=True)
    subprocess.run(['git', 'config', 'user.email', 't@t'], cwd=root, check=True)
    subprocess.run(['git', 'config', 'user.name', 'T'], cwd=root, check=True)
    previous = Path.cwd()
    os.chdir(root)
    repo_root.cache_clear()
    load_config.cache_clear()
    try:
        assert install.main('install-hooks', []) == 0
    finally:
        os.chdir(previous)
        repo_root.cache_clear()
        load_config.cache_clear()
    armed = subprocess.run(['bash', 'tools/setup-hooks.sh'], cwd=root,
                           capture_output=True, text=True)
    assert armed.returncode == 0, armed.stderr
    subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'install corpus'],
                   cwd=root, check=True, env=CLEAN_ENV)


def git(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *argv], cwd=root, capture_output=True,
                          text=True, env=CLEAN_ENV)


def test_pathspec_reads_the_merge_in_the_tree_the_command_commits_in(tmp_path):
    """#77: the guard resolved the gitdir from the SESSION's cwd, so a session
    in the main checkout finishing a worktree's merge with `cd <wt> && git
    commit` or `git -C <wt> commit` was blocked — MERGE_HEAD is in the
    worktree's gitdir. The probe: with no merge there, both still block.
    And a `cd` counts only in the `&&`-chain that ends in the commit: one in
    an earlier segment, a subshell or a group moved the tree the guard read
    to the worktree's merge, and a clean tree's sweep passed."""
    root = corpus_repo(tmp_path)
    wt = tmp_path / 'wt'
    assert git(root, 'worktree', 'add', '-q', '-b', 'lane', str(wt)).returncode == 0
    merge_head = Path(git(wt, 'rev-parse', '--absolute-git-dir').stdout.strip()) \
        / 'MERGE_HEAD'
    commands = (f'cd {wt} && git commit -m x', f'git -C {wt} commit -m x',
                f'cd {tmp_path} && cd wt && git commit -m x')
    escapes = (f'(cd {wt} && git status); git commit -m x',
               f'{{ cd {wt} && git status; }}; git commit -m x',
               f'cd {wt}; git commit -m x',
               f'cd {wt} | git commit -m x',
               f'cd {wt} || git commit -m x',
               f'cd {wt} && (git commit -m x)',
               f'cd {tmp_path}; cd wt; git commit -m x')
    blocked = [c for c in commands if fire(root, PATHSPEC, c) != 2]
    merge_head.write_text(git(root, 'rev-parse', 'HEAD').stdout)
    allowed = [c for c in commands if fire(root, PATHSPEC, c) != 0]
    escaped = [c for c in escapes if fire(root, PATHSPEC, c) != 2]
    assert not blocked and not allowed and not escaped, (blocked, allowed, escaped)


def write_makefile(root: Path, check_ok: bool) -> None:
    body = '@true' if check_ok else '@exit 1'
    (root / 'Makefile').write_text(
        f'check:\n\t{body}\nunit:\n\t@true\n', encoding='utf-8')


# --- cc-stop-gate: agent-only, red blocks, green allows -----------------------
def fire_stop(root: Path, cwd: Path | None = None,
              stop_hook_active: bool = False) -> subprocess.CompletedProcess:
    event = json.dumps({'cwd': str(cwd or root),
                        'stop_hook_active': stop_hook_active})
    return subprocess.run(['bash', str(root / STOP_GATE)], input=event,
                          text=True, capture_output=True, env=CLEAN_ENV)


def test_stop_gate_never_gates_the_trunk_session(tmp_path):
    """THE load-bearing safety property: no marker + no env = no gate, even
    over a gate that would be red — a false trigger would wedge the
    orchestrator every turn."""
    root = corpus_repo(tmp_path)
    write_makefile(root, check_ok=False)
    done = fire_stop(root)
    assert (done.returncode, done.stdout) == (0, '')


CLOSE_LINE = ("1 story/ies ready for `close story` — st-x ('building'); next: "
              "`make sdlc ARGS='close story <id>'`, one per story (CLOSE)")
CLOSES = "1 close(s) ready to run — make sdlc ARGS='close story st-x'"
# What the block says of it: what was asked, never that the belt accepts.
ASKED = ("the belt's checks that need no run pass; its rung will run. Run "
         "it, or say why it waits, then stop again:")
VERDICT_LINE = f'[check:pm] PASS — no PM-tree status drift; 1 warning(s); {CLOSES}'
REVIEW_LINE = ("1 feature(s) need a review record — ft-y ('building'); next: the "
               "review, then `make sdlc ARGS='close feature <id> --review-record "
               "<path>'` (CLOSE)")


def test_stop_gate_holds_the_trunk_session_on_a_ready_close(tmp_path):
    """0.8.0 ended sessions with closes ready and nobody told; 1.0.0 held
    seven features to the end. The trunk session is still never GATED, but a
    close ready to run — the `; N close(s) ready to run — <command>` clause
    on `check pm`'s verdict — holds its stop under stock `CLOSE_READY="block"`,
    exactly once, naming the command. `inform` only names it; a feature still
    waiting for its review is only named; nothing ready is silence."""
    root = corpus_repo(tmp_path)
    said = root / 'close.txt'
    (root / 'Makefile').write_text('sdlc:\n\t@cat close.txt\n', encoding='utf-8')
    said.write_text(f'  WARN  not a close (U1)\n  WARN  {CLOSE_LINE}\n\n'
                    f'{VERDICT_LINE}\n', encoding='utf-8')
    held = fire_stop(root)
    assert held.returncode == 2, held
    assert f'BLOCKED (Stop gate): {CLOSES} — {ASKED}' in held.stderr, \
        held.stderr
    assert f'  {CLOSE_LINE}' in held.stderr and 'U1' not in held.stderr
    assert fire_stop(root, stop_hook_active=True).returncode == 0
    # A reused `check pm` carries its reuse clause after the close clause.
    said.write_text(f'{VERDICT_LINE}; reused — green at t on inputs abc\n'
                    f'  WARN  {CLOSE_LINE}\n', encoding='utf-8')
    held = fire_stop(root)
    assert f'{CLOSES} — {ASKED}' in held.stderr and 'reused' not in held.stderr
    # Waiting on a review is not a close ready to run: named only.
    said.write_text(f'  WARN  {REVIEW_LINE}\n[check:pm] PASS — clean\n',
                    encoding='utf-8')
    told = fire_stop(root)
    assert told.returncode == 0, told.stderr
    message = json.loads(told.stdout)['systemMessage']
    assert REVIEW_LINE in message.splitlines() and 'CLOSE_READY' not in message
    # It stands open; it is not ready to run — the header never says so.
    assert message.startswith('Stop gate: a close stands open —'), message
    # Closed: quiet.
    said.write_text('[check:pm] PASS — clean\n', encoding='utf-8')
    assert (fire_stop(root).returncode, fire_stop(root).stdout) == (0, '')
    # `inform` in the header: named, never held.
    said.write_text(f'  WARN  {CLOSE_LINE}\n{VERDICT_LINE}\n', encoding='utf-8')
    hook = root / STOP_GATE
    hook.write_text(hook.read_text(encoding='utf-8').replace(
        'CLOSE_READY="block"\n', 'CLOSE_READY="inform"\n', 1), encoding='utf-8')
    told = fire_stop(root)
    assert told.returncode == 0, told.stderr
    message = json.loads(told.stdout)['systemMessage']
    assert CLOSE_LINE in message.splitlines(), message
    assert 'CLOSE_READY="block"' in message, message


def test_stop_gate_blocks_an_agent_stop_while_the_gate_is_red(tmp_path):
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    write_makefile(root, check_ok=False)
    done = fire_stop(root)
    assert done.returncode == 2
    assert 'BLOCKED (Stop gate)' in done.stderr


def test_stop_gate_allows_an_agent_stop_once_the_gate_is_green(tmp_path):
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    write_makefile(root, check_ok=True)
    assert fire_stop(root).returncode == 0


def test_stop_gate_does_not_loop_on_its_own_block(tmp_path):
    """stop_hook_active means Claude Code is already continuing because of a
    prior block — blocking again would gate-loop forever."""
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    write_makefile(root, check_ok=False)
    assert fire_stop(root, stop_hook_active=True).returncode == 0


def plant_origin_head(root: Path, at: str = 'HEAD') -> None:
    """What a CLONE has and `git init` does not: `origin/main` and an
    `origin/HEAD` pointing at it — the ref an empty `FALLBACK_BASE` /
    `DEFAULT_BASE` reads. Planted, not fetched; no `staging` anywhere."""
    assert git(root, 'update-ref', 'refs/remotes/origin/main', at).returncode == 0
    assert git(root, 'symbolic-ref', 'refs/remotes/origin/HEAD',
               'refs/remotes/origin/main').returncode == 0


STOP_UNRESOLVED = ("cc-stop-gate: base '{}' does not resolve — no unit slice "
                   "can be named, so only the static gate runs (set "
                   "DEFAULT_BASE in tools/hooks/cc-stop-gate.sh, or the "
                   "marker's base=)")


def test_stop_gate_names_a_base_that_does_not_resolve(tmp_path):
    """#37. The stock base is the remote's HEAD, READ, never a branch the
    kit's flow never creates. A base that does not resolve used to be
    swallowed — the gate ran the whole unit tier on every agent stop and said
    nothing; now it names the base and runs the static gate alone. Once `origin/HEAD`
    is there, the same marker slices off it and the line is gone."""
    root = corpus_repo(tmp_path)
    corpus = git(root, 'rev-parse', 'HEAD').stdout.strip()
    for rel in ('src/a.txt', 'tests/unit/src/.keep'):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text('x\n', encoding='utf-8')
    assert git(root, 'add', 'src', 'tests').returncode == 0
    assert git(root, 'commit', '-q', '-m', 'feat: src',
               '--', 'src', 'tests').returncode == 0
    (root / 'Makefile').write_text(
        "check:\n\t@true\nunit:\n\t@printf '%s' '$(SYS)' > sys.out\n",
        encoding='utf-8')
    sys_out = root / 'sys.out'
    for marker, named in (('branch=feat/x\n', 'origin/HEAD'),
                          ('branch=feat/x\nbase=nope\n', 'nope')):
        (root / MARKER).write_text(marker, encoding='utf-8')
        done = fire_stop(root)
        assert done.returncode == 0, done.stderr
        assert STOP_UNRESOLVED.format(named) in done.stderr.splitlines(), \
            done.stderr
        assert not sys_out.exists(), 'no unit tier at all, not the whole one'
    plant_origin_head(root, at=corpus)
    (root / MARKER).write_text('branch=feat/x\n', encoding='utf-8')
    done = fire_stop(root)
    assert done.returncode == 0, done.stderr
    assert 'does not resolve' not in done.stderr, done.stderr
    assert sys_out.read_text(encoding='utf-8') == 'src'


def test_stop_gate_fails_open_without_a_makefile_and_on_garbage(tmp_path):
    """Installed ahead of the dev loop (no Makefile yet), the gate must not
    wedge every agent stop; fed garbage it must not wedge the session."""
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    assert fire_stop(root).returncode == 0    # marker set, but no Makefile
    garbage = subprocess.run(['bash', str(root / STOP_GATE)],
                             input='not json {{{', text=True,
                             capture_output=True, cwd=root, env=CLEAN_ENV)
    assert garbage.returncode == 0


# --- cc-write-confine: cross-repo blocked, everything legitimate passes -------
def fire_confine(hook_root: Path, target: Path | str, cwd: Path,
                 env: dict | None = None) -> subprocess.CompletedProcess:
    event = json.dumps({'tool_name': 'Write',
                        'tool_input': {'file_path': str(target)},
                        'cwd': str(cwd)})
    return subprocess.run(['bash', str(hook_root / CONFINE)], input=event,
                          text=True, capture_output=True,
                          env=env or CLEAN_ENV)


def plain_repo(parent: Path, name: str) -> Path:
    other = parent / name
    other.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=other, check=True)
    return other


def test_confine_blocks_a_write_into_a_different_repository(tmp_path):
    ours = corpus_repo(tmp_path)
    theirs = plain_repo(tmp_path, 'theirs')
    done = fire_confine(ours, theirs / 'stomped.txt', cwd=ours)
    assert done.returncode == 2
    assert 'BLOCKED (write-confinement)' in done.stderr


def test_confine_allows_a_write_inside_the_session_repo(tmp_path):
    ours = corpus_repo(tmp_path)
    assert fire_confine(ours, ours / 'sub/new.txt', cwd=ours).returncode == 0


def test_confine_allows_a_non_repo_target(tmp_path):
    """A scratchpad / tmp / dotfile write is not the cross-tree collision this
    hook guards; blocking it just pushes the agent to Bash heredocs, which the
    hook cannot see anyway."""
    ours = corpus_repo(tmp_path)
    outside = tmp_path / 'scratch'
    outside.mkdir()
    assert fire_confine(ours, outside / 'notes.md', cwd=ours).returncode == 0


def test_confine_allows_the_auto_memory_store_by_path_shape(tmp_path):
    ours = corpus_repo(tmp_path)
    memory = '/somewhere/.claude/projects/p/memory/notes.md'
    assert fire_confine(ours, memory, cwd=ours).returncode == 0


def test_confine_allows_a_sibling_worktree_of_the_same_repo(tmp_path):
    """The dispatched-subagent case: the Agent tool reports the PARENT
    session's cwd, so a worktree-scoped agent's every edit lands 'outside' the
    session tree — same repository must therefore be the boundary, not same
    worktree. One consumer fork fixed this; the other still blocks it."""
    ours = corpus_repo(tmp_path)
    wt = tmp_path / 'wt'
    done = git(ours, 'worktree', 'add', '-b', 'feat/side', str(wt), 'main')
    assert done.returncode == 0, done.stderr
    assert fire_confine(ours, wt / 'edited.txt', cwd=ours).returncode == 0


def test_confine_honors_a_granted_extra_root_exactly(tmp_path):
    ours = corpus_repo(tmp_path)
    theirs = plain_repo(tmp_path, 'theirs')
    grants = ours / 'tools/hooks/extra-write-roots.local'
    grants.write_text(f'# temporary grant\n{theirs}\n', encoding='utf-8')
    assert fire_confine(ours, theirs / 'ok.txt', cwd=ours).returncode == 0
    # The grant is the named toplevel, not a prefix family.
    evil = plain_repo(tmp_path, 'theirs-evil')
    assert fire_confine(ours, evil / 'no.txt', cwd=ours).returncode == 2


def test_confine_scope_env_pins_the_allowed_toplevel(tmp_path):
    ours = corpus_repo(tmp_path)
    theirs = plain_repo(tmp_path, 'theirs')
    pinned = dict(CLEAN_ENV, DEVKIT_AGENT_SCOPE=str(ours))
    outside = tmp_path / 'elsewhere'
    outside.mkdir()
    assert fire_confine(ours, ours / 'mine.txt', cwd=outside,
                        env=pinned).returncode == 0
    assert fire_confine(ours, theirs / 'not-mine.txt', cwd=outside,
                        env=pinned).returncode == 2


def test_confine_fails_open_on_garbage_and_non_write_tools(tmp_path):
    ours = corpus_repo(tmp_path)
    garbage = subprocess.run(['bash', str(ours / CONFINE)],
                             input='not json {{{', text=True,
                             capture_output=True, env=CLEAN_ENV)
    assert garbage.returncode == 0
    event = json.dumps({'tool_name': 'Bash',
                        'tool_input': {'command': 'echo hi'},
                        'cwd': str(ours)})
    bash_tool = subprocess.run(['bash', str(ours / CONFINE)], input=event,
                               text=True, capture_output=True, env=CLEAN_ENV)
    assert bash_tool.returncode == 0


# --- pre-push: main blocked, gate scoped, exact branch match ------------------
def with_origin(root: Path, parent: Path) -> Path:
    origin = parent / 'origin.git'
    # `cwd=parent`, like every other git spawn in this suite: without it this
    # one ran in whatever directory pytest was started in — the real checkout —
    # and `git init --bare` is a verb that WRITES a `.git/config`
    # (bg-the-suite-can-flip-the-host-repo-to-bare).
    subprocess.run(['git', 'init', '-q', '--bare', str(origin)], cwd=parent,
                   check=True)
    assert git(root, 'remote', 'add', 'origin', str(origin)).returncode == 0
    return origin


def origin_heads(origin: Path) -> str:
    return subprocess.run(['git', 'show-ref'], cwd=origin, capture_output=True,
                          text=True).stdout


def test_pre_push_blocks_a_direct_push_to_main_and_nothing_lands(tmp_path):
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    done = git(root, 'push', 'origin', 'main')
    assert done.returncode != 0
    assert 'Direct push to main' in done.stderr
    assert origin_heads(origin).strip() == ''


def test_pre_push_lets_a_green_gate_push_land(tmp_path):
    """And the gate runs with every name `git rev-parse --local-env-vars`
    prints UNSET: an inherited `GIT_DIR` sent a self-test's `git init` into
    the real repository. `GIT_NO_REPLACE_OBJECTS` stands in for it — one name
    off that list, harmless to the push, and not a location this suite's
    boundary forbids a test to export."""
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    (root / 'Makefile').write_text(
        'check:\n\t@test -z "$$GIT_NO_REPLACE_OBJECTS"\n', encoding='utf-8')
    assert git(root, 'checkout', '-q', '-b', 'staging').returncode == 0
    done = subprocess.run(['git', 'push', 'origin', 'staging'], cwd=root,
                          capture_output=True, text=True,
                          env={**CLEAN_ENV, 'GIT_NO_REPLACE_OBJECTS': '1'})
    assert done.returncode == 0, done.stderr
    assert 'refs/heads/staging' in origin_heads(origin)


def test_pre_push_blocks_a_red_gate_push_before_it_lands(tmp_path):
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    write_makefile(root, check_ok=False)
    assert git(root, 'checkout', '-q', '-b', 'staging').returncode == 0
    done = git(root, 'push', 'origin', 'staging')
    assert done.returncode != 0
    assert 'pre-push gate' in done.stderr
    assert 'refs/heads/staging' not in origin_heads(origin)


def test_pre_push_skips_the_gate_for_agent_worktrees(tmp_path):
    """The agent's Stop hook already gates every finish; paying the same gate
    again per push doubles the cost. Red gate + marker must still push."""
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    write_makefile(root, check_ok=False)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    assert git(root, 'checkout', '-q', '-b', 'feat/x').returncode == 0
    done = git(root, 'push', 'origin', 'feat/x')
    assert done.returncode == 0, done.stderr
    assert 'refs/heads/feat/x' in origin_heads(origin)


def test_pre_push_matches_the_protected_branch_exactly(tmp_path):
    """Both consumer forks grep for the substring refs/heads/main, which also
    blocks refs/heads/maintenance. The shipped hook matches the whole name."""
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    write_makefile(root, check_ok=True)
    assert git(root, 'checkout', '-q', '-b', 'maintenance').returncode == 0
    done = git(root, 'push', 'origin', 'maintenance')
    assert done.returncode == 0, done.stderr
    assert 'refs/heads/maintenance' in origin_heads(origin)


def test_pre_push_fails_open_without_a_makefile_but_still_guards_main(tmp_path):
    """Stage 1 (push-safety) always runs; stage 2 (the gate) cannot run in a
    repo with no dev loop yet and must not block every push meanwhile."""
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    assert git(root, 'checkout', '-q', '-b', 'staging').returncode == 0
    assert git(root, 'push', 'origin', 'staging').returncode == 0
    assert 'refs/heads/staging' in origin_heads(origin)
    assert git(root, 'checkout', '-q', 'main').returncode == 0
    assert git(root, 'push', 'origin', 'main').returncode != 0


def test_pre_push_does_not_gate_a_tag_only_push(tmp_path):
    root = corpus_repo(tmp_path)
    with_origin(root, tmp_path)
    write_makefile(root, check_ok=False)   # a red gate that must not run
    assert git(root, 'tag', 'v0').returncode == 0
    done = git(root, 'push', 'origin', 'v0')
    assert done.returncode == 0, done.stderr


def _pushed_then_red(root: Path) -> list[str]:
    """Two commits on `staging`, pushed through a GREEN gate; the gate is then
    turned RED, so any later push that runs Stage 2 is refused. Returns the
    two shas, oldest first."""
    write_makefile(root, check_ok=True)
    assert git(root, 'checkout', '-q', '-b', 'staging').returncode == 0
    assert git(root, 'commit', '-q', '--allow-empty', '-m', 'c2').returncode == 0
    assert git(root, 'push', '-q', 'origin', 'staging').returncode == 0
    write_makefile(root, check_ok=False)
    return git(root, 'rev-list', '--reverse', 'staging').stdout.split()


def _new_branch_at_a_pushed_commit(root: Path, shas: list[str]):
    return git(root, 'push', 'origin', f'{shas[-1]}:refs/heads/lane/x')


def _fast_forward_to_a_pushed_commit(root: Path, shas: list[str]):
    assert git(root, 'push', 'origin',
               f'{shas[0]}:refs/heads/lane/y').returncode == 0
    return git(root, 'push', 'origin', f'{shas[1]}:refs/heads/lane/y')


def _one_new_commit(root: Path, shas: list[str]):
    assert git(root, 'commit', '-q', '--allow-empty', '-m', 'c3').returncode == 0
    return git(root, 'push', 'origin', 'staging')


def _a_rev_list_that_fails(root: Path, shas: list[str]):
    """git never hands the hook an object it lacks, so the hook is fed one:
    rev-list fails, and the push counts as real."""
    ref = f'refs/heads/lane/z {"f" * 40} refs/heads/lane/z {"0" * 40}\n'
    return subprocess.run(['bash', str(root / 'tools/hooks/pre-push'),
                           'origin', 'unused-url'], cwd=root, input=ref,
                          capture_output=True, text=True, env=CLEAN_ENV)


@pytest.mark.parametrize('push,gated', [
    (_new_branch_at_a_pushed_commit, False),
    (_fast_forward_to_a_pushed_commit, False),
    (_one_new_commit, True),
    (_a_rev_list_that_fails, True),
])
def test_pre_push_gates_only_a_commit_the_remote_lacks(tmp_path, push, gated):
    """#93: Stage 2 ran the full gate for a branch cut at a commit the remote
    already had — nine lane branches, 13 minutes. A red gate after a green
    push tells the two apart: a gated push is refused, an ungated one lands."""
    root = corpus_repo(tmp_path)
    with_origin(root, tmp_path)
    done = push(root, _pushed_then_red(root))
    assert (done.returncode != 0) == gated, done.stderr
    assert ('pre-push gate' in done.stderr) == gated, done.stderr


# --- a header carried from an older install still runs (review R1) -----------
# The v0.4.0 `prepare-commit-msg` header, byte for byte: it has no `TRAILER_RE=`.
V040_PREPARE_HEADER = (
    "# --- project config (yours to edit after install — the file is your "
    "repo's) --\n"
    '# The trailer; keep it in step with the model line your agent prompts '
    'name.\n'
    'TRAILER="Co-Authored-By: Claude <noreply@anthropic.com>"\n'
    '# The per-agent worktree marker written by tools/dev/agent-worktree.sh.\n'
    'SCOPE_MARKER=".agent-scope"\n'
    '# ' + '-' * 77 + '\n')
ASSIGNMENT = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=(\(?)')
DEFAULTED = re.compile(r'^declare -p ([A-Za-z_][A-Za-z0-9_]*) >/dev/null 2>&1 \|\| ')
# Every installed file whose packaged header declares a key its body reads.
HEADERED = tuple(
    (name, rel) for name, rel in install.PLANS['install-hooks']
    if (span := install.config_block_span(install.body_of(name)))
    and any(ASSIGNMENT.match(line) for line in
            install.body_of(name).splitlines()[span[0]:span[1]]))


def _settled(text: str, names: list[str], defaulted: bool) -> str:
    """`declare -p` of `names` once `text` has run through its header's close,
    or through its last stock default."""
    lines = text.splitlines()
    upto = (max(n for n, line in enumerate(lines) if DEFAULTED.match(line))
            if defaulted else install.config_block_span(text)[1]) + 1
    script = '\n'.join(lines[:upto] + ['declare -p ' + ' '.join(names)])
    return subprocess.run(['bash', '-c', script], capture_output=True, text=True,
                          env=CLEAN_ENV).stdout


def test_the_census_of_headered_hooks_is_the_eight_that_read_a_key():
    assert [rel for _name, rel in HEADERED] == [
        STOP_GATE, 'tools/hooks/cc-git-allowlist.sh', LEDGER_SUBAGENT,
        LEDGER_SESSION, 'tools/hooks/cc-session-preflight.sh',
        'tools/hooks/pre-push',
        'tools/hooks/prepare-commit-msg', WORKTREE]


@pytest.mark.parametrize('name,rel', HEADERED, ids=[rel for _n, rel in HEADERED])
def test_a_header_lacking_a_key_runs_the_body_on_its_stock_value(name, rel):
    """Review R1: `--force` carries an older header byte for byte (D1), and a
    body reading a key that header lacks aborted under `set -u`. The body
    defaults every key: with NO key in the header each settles at the packaged
    header's value, and a key the header sets — emptied, here — stays set."""
    body = install.body_of(name)
    lines = body.splitlines(keepends=True)
    start, end = install.config_block_span(body)
    names = [m.group(1) for line in lines[start:end]
             if (m := ASSIGNMENT.match(line))]
    assert [m.group(1) for line in lines if (m := DEFAULTED.match(line))] == names

    def carried(swap) -> str:
        return install.carry_config_block(''.join(
            line if (m := ASSIGNMENT.match(line)) is None else swap(m)
            for line in lines[:end + 1]), body)
    stock = _settled(body, names, defaulted=False)
    assert stock.count('declare ') == len(names), stock
    assert _settled(carried(lambda m: ''), names, defaulted=True) == stock
    emptied = carried(lambda m: m.group(1) + ('=()\n' if m.group(2) else "=''\n"))
    kept = _settled(emptied, names, defaulted=True)
    assert kept == _settled(emptied, names, defaulted=False) != stock, kept


# --- prepare-commit-msg: agents stamped, the human never -----------------------
def last_message(root: Path) -> str:
    return git(root, 'log', '-1', '--format=%B').stdout


def test_prepare_commit_msg_stamps_agent_commits(tmp_path):
    """The second commit is review R1's walk: `install-hooks --force` carries
    a v0.4.0 header, which declares no `TRAILER_RE=`, and the body read it
    under `set -eu` — `TRAILER_RE: unbound variable`, every agent commit
    aborted."""
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    assert git(root, 'commit', '-q', '--allow-empty',
               '-m', 'feat: x').returncode == 0
    assert 'Co-Authored-By: Claude' in last_message(root)
    hook = root / 'tools/hooks/prepare-commit-msg'
    hook.write_text(install.carry_config_block(
        V040_PREPARE_HEADER, hook.read_text(encoding='utf-8')),
        encoding='utf-8')
    committed = git(root, 'commit', '-q', '--allow-empty', '-m', 'feat: y')
    assert committed.returncode == 0, committed.stderr
    assert last_message(root).count('Co-Authored-By: Claude') == 1


def test_prepare_commit_msg_never_stamps_the_trunk(tmp_path):
    """The MUST-NEVER property: the human's own commits stay theirs."""
    root = corpus_repo(tmp_path)
    assert git(root, 'commit', '-q', '--allow-empty',
               '-m', 'docs: mine').returncode == 0
    assert 'Co-Authored-By' not in last_message(root)


def test_prepare_commit_msg_is_idempotent(tmp_path):
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    already = ('feat: x\n\n'
               'Co-Authored-By: Claude <noreply@anthropic.com>')
    assert git(root, 'commit', '-q', '--allow-empty',
               '-m', already).returncode == 0
    assert last_message(root).count('Co-Authored-By') == 1


# --- agent-worktree: create, refuse-dirty, keep-unmerged, teardown ------------
def worktree(root: Path, *argv: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(['bash', str(root / WORKTREE), *argv], cwd=root,
                          capture_output=True, text=True, env=env or CLEAN_ENV)


def worktree_at(checkout: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(['bash', str(checkout / WORKTREE), *argv], cwd=checkout,
                          capture_output=True, text=True, env=CLEAN_ENV)


def test_worktree_new_creates_branch_marker_and_prints_the_path(tmp_path):
    """A clone following the kit's flow — `main`, a remote, its HEAD, no
    `staging` — bases off the remote's HEAD, and the branch does NOT track
    it (`--no-track`): a remote-tracking base would otherwise become its
    upstream."""
    root = corpus_repo(tmp_path)
    with_origin(root, tmp_path)
    plant_origin_head(root)
    done = worktree(root, 'new', 'sluga')
    assert done.returncode == 0, done.stderr
    path = Path(done.stdout.strip())
    assert path == Path(str(root) + '.worktrees/sluga')
    marker = (path / MARKER).read_text(encoding='utf-8')
    assert 'branch=feat/sluga' in marker
    assert 'base=origin/main' in marker
    assert git(path, 'branch', '--show-current').stdout.strip() == 'feat/sluga'
    upstream = git(root, 'rev-parse', '--abbrev-ref', 'feat/sluga@{u}')
    assert upstream.returncode != 0, upstream.stdout


def test_worktree_commands_share_identity_from_primary_and_external_checkouts(tmp_path):
    root = corpus_repo(tmp_path, 'repo with spaces')
    plant_origin_head(root)
    created = worktree(root, 'new', 'first')
    assert created.returncode == 0, created.stderr
    first = Path(created.stdout.strip())
    assert first == Path(str(root) + '.worktrees/first')
    from_external = worktree_at(first, 'list')
    assert from_external.returncode == 0, from_external.stderr
    assert str(first) in from_external.stdout
    # `done` must leave the linked checkout before removing its own cwd.
    from_external = worktree_at(first, 'done', 'first')
    assert from_external.returncode == 0, from_external.stderr
    assert not first.exists()
    assert git(root, 'show-ref', '--verify', 'refs/heads/feat/first').returncode != 0

    caller = Path(str(root) + '.worktrees/caller')
    assert git(root, 'worktree', 'add', '--no-track', '-b', 'feat/caller',
               str(caller), 'main').returncode == 0
    _pm_tree(root, 'building', FLOW_TOML, 'milestone/test')
    assert git(root, 'branch', 'milestone/test').returncode == 0
    from_external = worktree_at(caller, 'new', 'second')
    assert from_external.returncode == 0, from_external.stderr
    second = Path(from_external.stdout.strip())
    assert second == Path(str(root) + '.worktrees/second')
    assert 'base=milestone/test' in (second / MARKER).read_text(encoding='utf-8')
    from_primary = worktree(root, 'list')
    assert from_primary.returncode == 0, from_primary.stderr
    assert str(second) in from_primary.stdout
    from_primary = worktree(root, 'done', 'second')
    assert from_primary.returncode == 0, from_primary.stderr
    assert not second.exists()
    assert worktree(root, 'done', 'caller').returncode == 0


def test_worktree_legacy_repo_relative_parent_and_old_lanes_still_work(tmp_path):
    root = corpus_repo(tmp_path)
    plant_origin_head(root)
    script = root / WORKTREE
    script.write_text(script.read_text(encoding='utf-8').replace(
        'WORKTREE_PARENT=""', 'WORKTREE_PARENT="custom worktrees"'),
        encoding='utf-8')
    created = worktree(root, 'new', 'custom')
    assert created.returncode == 0, created.stderr
    custom = Path(created.stdout.strip())
    assert custom == root / 'custom worktrees/custom'
    assert worktree(root, 'done', 'custom').returncode == 0

    legacy = root / '.claude/worktrees/old'
    assert git(root, 'worktree', 'add', '--no-track', '-b', 'feat/old',
               str(legacy), 'main').returncode == 0
    (legacy / MARKER).write_text('branch=feat/old\nbase=origin/main\n',
                                 encoding='utf-8')
    listing = worktree(root, 'list')
    assert str(legacy) in listing.stdout
    retired = worktree(root, 'done', 'old')
    assert retired.returncode == 0, retired.stderr
    assert not legacy.exists()


def test_worktree_cache_warm_uses_isolated_copy_and_skips_linked_worktrees(tmp_path):
    root = corpus_repo(tmp_path)
    plant_origin_head(root)
    old = root / '.claude/worktrees/old'
    assert git(root, 'worktree', 'add', '--no-track', '-b', 'feat/old',
               str(old), 'main').returncode == 0
    cache = root / 'cache with spaces'
    cache.mkdir()
    (cache / 'file').write_text('source', encoding='utf-8')
    script = root / WORKTREE
    script.write_text(script.read_text(encoding='utf-8').replace(
        'WARM_DIRS=()', 'WARM_DIRS=("cache with spaces" ".claude/worktrees")'),
        encoding='utf-8')
    # Simulate a CoW clone implementation that creates its destination and
    # then fails; the fallback must copy contents into it, not nest the source.
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    real_cp = shutil.which('cp')
    assert real_cp
    cp_wrapper = fake_bin / 'cp'
    cp_wrapper.write_text(
        '#!/bin/sh\n'
        f'real_cp={real_cp!r}\n'
        'case "$*" in\n'
        '  *-cR*"cache with spaces"*|*--reflink=auto*"cache with spaces"*)\n'
        '    for arg do target="$arg"; done\n'
        '    mkdir -p "$target"\n'
        '    exit 1\n'
        '    ;;\n'
        'esac\n'
        'exec "$real_cp" "$@"\n', encoding='utf-8')
    cp_wrapper.chmod(0o755)
    test_env = dict(CLEAN_ENV)
    test_env['PATH'] = f'{fake_bin}:{test_env["PATH"]}'
    created = worktree(root, 'new', 'warm', env=test_env)
    assert created.returncode == 0, created.stderr
    warmed = Path(created.stdout.strip())
    assert (warmed / 'cache with spaces/file').read_text(encoding='utf-8') == 'source'
    assert not (warmed / 'cache with spaces/cache with spaces').exists()
    (warmed / 'cache with spaces/file').write_text('changed', encoding='utf-8')
    assert (cache / 'file').read_text(encoding='utf-8') == 'source'
    assert not (warmed / '.claude/worktrees/old').exists()
    assert 'overlaps a linked worktree' in created.stderr
    assert git(root, 'worktree', 'remove', '--force', str(warmed)).returncode == 0
    assert git(root, 'branch', '-D', 'feat/warm').returncode == 0
    assert git(root, 'worktree', 'remove', '--force', str(old)).returncode == 0
    assert git(root, 'branch', '-D', 'feat/old').returncode == 0


def test_worktree_refuses_bare_repository(tmp_path):
    bare = tmp_path / 'bare.git'
    initialized = subprocess.run(['git', 'init', '--bare', str(bare)],
                                 cwd=tmp_path, capture_output=True, text=True)
    assert initialized.returncode == 0, initialized.stderr
    refused = subprocess.run(['bash', str(REPO_ROOT / WORKTREE), 'list'],
                             cwd=bare, capture_output=True, text=True,
                             env=CLEAN_ENV)
    assert refused.returncode != 0
    assert 'bare repositories have no primary checkout' in refused.stderr


WORKTREE_UNRESOLVED = ("agent-worktree: base '{}' does not resolve — set "
                       "FALLBACK_BASE in tools/dev/agent-worktree.sh, pass "
                       "[base-branch], or run git remote set-head origin "
                       "--auto")


def test_worktree_new_refuses_a_base_that_does_not_resolve_without_a_write(
        tmp_path):
    """#37. A `git remote add` tree — `origin/main` fetched, NO `origin/HEAD`
    — is the accepted cost of reading the remote's HEAD: `new` refuses,
    naming the base it tried and where to set one, before `git worktree add`.
    It never GUESSES `origin/main` or `main`, both of which are right there.
    The same line for a `[base-branch]` that does not resolve, each spelling
    refused with no branch, no directory and no registered worktree."""
    root = corpus_repo(tmp_path)
    with_origin(root, tmp_path)
    assert git(root, 'update-ref', 'refs/remotes/origin/main',
               'HEAD').returncode == 0
    registered = git(root, 'worktree', 'list', '--porcelain').stdout
    for argv, named in ((('new', 'x'), 'origin/HEAD'),
                        (('new', 'x', ''), 'origin/HEAD'),
                        (('new', 'x', 'staging'), 'staging'),
                        (('new', 'x', 'main..main'), 'main..main'),
                        (('new', 'x', '--all'), '--all'),
                        (('new', 'x', ' main'), ' main'),
                        (('new', '--no-warm', 'x', 'nope'), 'nope')):
        done = worktree(root, *argv)
        assert done.returncode == 1, (argv, done.stderr)
        assert done.stderr.splitlines()[-1] == \
            WORKTREE_UNRESOLVED.format(named), (argv, done.stderr)
        assert done.stdout == '', argv
        assert git(root, 'show-ref', '--verify', '--quiet',
                   'refs/heads/feat/x').returncode != 0, argv
        assert not Path(str(root) + '.worktrees/x').exists(), argv
        assert git(root, 'worktree', 'list',
                   '--porcelain').stdout == registered, argv


def test_worktree_done_refuses_while_work_is_uncommitted(tmp_path):
    """The property the tool exists for: teardown must never eat work. The
    planted marker itself must NOT count as dirt — only real files do."""
    root = corpus_repo(tmp_path)
    plant_origin_head(root)
    path = Path(worktree(root, 'new', 'dirty').stdout.strip())
    (path / 'half-done.gd').write_text('# wip\n', encoding='utf-8')
    done = worktree(root, 'done', 'dirty')
    assert done.returncode != 0
    assert 'REFUSING' in done.stderr
    assert path.is_dir()
    (path / 'half-done.gd').unlink()
    assert worktree(root, 'done', 'dirty').returncode == 0, 'marker read as dirt'
    assert not path.exists()


def test_worktree_done_keeps_an_unmerged_branch_and_deletes_a_merged_one(
        tmp_path):
    root = corpus_repo(tmp_path)
    with_origin(root, tmp_path)
    plant_origin_head(root)
    path = Path(worktree(root, 'new', 'keeper').stdout.strip())
    (path / 'landed.gd').write_text('# done\n', encoding='utf-8')
    assert git(path, 'add', 'landed.gd').returncode == 0
    assert git(path, 'commit', '-q', '-m', 'feat: landed',
               '--', 'landed.gd').returncode == 0
    done = worktree(root, 'done', 'keeper')
    assert done.returncode == 0, done.stderr
    assert 'NOT merged into origin/main' in done.stderr
    assert git(root, 'show-ref', '--verify',
               'refs/heads/feat/keeper').returncode == 0, 'commits were lost'
    # Merge it into the trunk: `branch -d` asks HEAD, because `new` set no
    # upstream — a tracked `origin/main` would refuse it as unmerged.
    assert git(root, 'checkout', '-q', 'main').returncode == 0
    assert git(root, 'merge', '-q', 'feat/keeper').returncode == 0
    assert git(root, 'branch', '-d', 'feat/keeper').returncode == 0


def test_worktree_done_carries_ledger_rows_and_retires_a_lane_in_the_mainline(
        tmp_path):
    """#48. After a release no milestone is in progress: a lane cut from
    `milestone/x` that landed through `origin/main` is merged, and `done`
    deletes its branch although neither `milestone/x` nor the main checkout's
    HEAD holds it. Gate rows dirtying the lane's ledger — tracked or
    gitignored — are APPENDED to the main checkout's copy, after its own; a
    row CHANGED rather than appended is work, and refuses with nothing
    carried."""
    root = corpus_repo(tmp_path)
    ledger, local = 'pm/roadmap/ledger.jsonl', 'pm/roadmap/ledger.local.jsonl'
    (root / 'pm/roadmap').mkdir(parents=True)
    (root / ledger).write_text('{"row": "head"}\n', encoding='utf-8')
    (root / '.gitignore').write_text(local + '\n', encoding='utf-8')
    assert git(root, 'add', ledger, '.gitignore').returncode == 0
    assert git(root, 'commit', '-q', '-m', 'ledger', '--', ledger,
               '.gitignore').returncode == 0
    plant_origin_head(root)
    assert git(root, 'branch', 'milestone/x').returncode == 0
    path = Path(worktree(root, 'new', '--no-warm', 'lane',
                         'milestone/x').stdout.strip())
    (path / 'landed.gd').write_text('# done\n', encoding='utf-8')
    assert git(path, 'add', 'landed.gd').returncode == 0
    assert git(path, 'commit', '-q', '-m', 'feat: landed',
               '--', 'landed.gd').returncode == 0
    assert git(root, 'update-ref', 'refs/remotes/origin/main',
               'feat/lane').returncode == 0
    with open(root / ledger, 'a', encoding='utf-8') as main_rows:
        main_rows.write('{"row": "main"}\n')

    (path / ledger).write_text('{"row": "edited"}\n', encoding='utf-8')
    refused = worktree(root, 'done', 'lane')
    assert refused.returncode == 1 and f' M {ledger}' in refused.stderr, refused
    assert path.is_dir() and 'edited' not in (root / ledger).read_text(
        encoding='utf-8')

    (path / ledger).write_text('{"row": "head"}\n{"gate": "unit"}\n',
                               encoding='utf-8')
    (path / local).write_text('{"gate": "check"}\n', encoding='utf-8')
    done = worktree(root, 'done', 'lane')
    assert done.returncode == 0, done.stderr
    assert 'deleted merged branch feat/lane' in done.stderr, done.stderr
    assert not path.exists()
    assert git(root, 'show-ref', '--verify', '--quiet',
               'refs/heads/feat/lane').returncode != 0
    assert (root / ledger).read_text(encoding='utf-8') == (
        '{"row": "head"}\n{"row": "main"}\n{"gate": "unit"}\n')
    assert (root / local).is_file(), done.stderr
    assert (root / local).read_text(encoding='utf-8') == '{"gate": "check"}\n'


def _pm_tree(root: Path, status: str, flow: str = FLOW_TOML,
             branch: str = 'feat/integration') -> None:
    """A PM tree the worktree script can ASK about: one milestone at `status`
    declaring `branch: <branch>`, the flow, and the `make pm` target
    the script's `PM_CMD` runs — routed to the CLI from source, the same
    Makefile `ledger_repo` below plants."""
    (root / 'devkit.toml').write_text(flow, encoding='utf-8')
    (root / 'Makefile').write_text(
        PM_MAKEFILE.format(src=REPO_ROOT / 'src', python=sys.executable),
        encoding='utf-8')
    milestone = root / 'pm/roadmap/milestones/0.1.0.md'
    milestone.parent.mkdir(parents=True)
    milestone.write_text(f'---\nid: "0.1.0"\nstatus: {status}\n'
                         f'branch: {branch}\n---\n', encoding='utf-8')


def test_worktree_new_bases_off_the_in_progress_milestones_branch(tmp_path):
    """The devkit PM tree is the source for the integration branch: a
    milestone declaring `branch:` while in progress is where agents branch
    from, not the trunk — basing off the trunk strands the agent behind every
    commit the milestone already landed.

    ASKED OF THE CLI BY CATEGORY, never grepped. The script used to grep
    `status: building` out of milestone.md, so the second tree here — the
    same milestone under a vocabulary that calls the state `doing` — is the
    case the old script could not pass: it found no `building`, based the
    agent off the trunk, and said nothing. `pm list --kind milestone
    --category in_progress` answers both trees the same way.

    The third tree declares `branch: staging`. `staging` is no longer a
    trunk name the scan skips — the trunk is `main` or the fallback — so a
    declared `staging` is honoured, never swapped for `origin/main` in
    silence (#37).
    """
    for status, flow, branch in (
            ('building', FLOW_TOML, 'feat/integration'),
            ('doing', FLOW_TOML.replace('"building"', '"doing"'),
             'feat/integration'),
            ('building', FLOW_TOML, 'staging')):
        root = corpus_repo(tmp_path, name=f'repo-{status}-{branch[:4]}')
        plant_origin_head(root)
        assert git(root, 'branch', branch).returncode == 0
        _pm_tree(root, status, flow, branch)
        done = worktree(root, 'new', 'based')
        assert done.returncode == 0, done.stderr
        marker = (Path(done.stdout.strip()) / MARKER).read_text(
            encoding='utf-8')
        assert f'base={branch}' in marker, (status, done.stderr)
        assert 'could not answer' not in done.stderr, done.stderr


def test_worktree_new_falls_back_when_the_cli_cannot_answer(tmp_path):
    """No PM tree, no flow, no `make pm` — the three trees above start this
    way — is not an error the worktree tool should die on: it says so on
    stderr and bases off FALLBACK_BASE, which is what a tree with no PM
    records means. A milestone the CLI cannot read (no flow declared) is the
    same answer, said the same way, never a silent trunk base."""
    root = corpus_repo(tmp_path)
    plant_origin_head(root)
    milestone = root / 'pm/roadmap/milestones/0.1.0.md'
    milestone.parent.mkdir(parents=True)
    milestone.write_text('---\nid: "0.1.0"\nstatus: building\n'
                         'branch: feat/integration\n---\n', encoding='utf-8')
    done = worktree(root, 'new', 'unasked')
    assert done.returncode == 0, done.stderr
    assert 'could not answer' in done.stderr, done.stderr
    assert 'basing off origin/main' in done.stderr, done.stderr
    marker = (Path(done.stdout.strip()) / MARKER).read_text(encoding='utf-8')
    assert 'base=origin/main' in marker


# --- fail-open posture, the PreToolUse hook -----------------------------------
@pytest.mark.parametrize('hook', [PATHSPEC])
def test_a_hook_fed_garbage_or_another_tool_fails_open(hooks_repo, hook):
    """A broken hook must never wedge the session: unparseable stdin and a
    non-Bash tool event both allow, even when the payload mentions the very
    thing the hook exists to block."""
    garbage = subprocess.run(['bash', str(hooks_repo / hook)],
                             input='not json {{{ git commit',
                             text=True, capture_output=True)
    assert garbage.returncode == 0
    event = json.dumps({'tool_name': 'Write',
                        'tool_input': {'command': 'git commit -m x'},
                        'cwd': str(hooks_repo)})
    other = subprocess.run(['bash', str(hooks_repo / hook)], input=event,
                           text=True, capture_output=True)
    assert other.returncode == 0


# --- setup-hooks.sh: arms by glob, and the whole corpus ------------------------
def test_setup_hooks_arms_every_cc_hook_by_glob(tmp_path):
    """The forks this replaced did it two ways — a `cc-*.sh` glob, and two
    named files. The glob is strictly better: it is tolerant of absence AND does
    not have to be edited when a hook is added. core.hooksPath skips a
    non-executable hook in silence, so a hook this misses is a guard nobody
    knows is off. (From test_install.py, which spawns nothing now.)"""
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
    previous = Path.cwd()
    os.chdir(root)
    repo_root.cache_clear()
    load_config.cache_clear()
    try:
        assert install.main('install-hooks', []) == 0
    finally:
        os.chdir(previous)
        repo_root.cache_clear()
        load_config.cache_clear()
    disarmed = (PATHSPEC, STOP_GATE)
    for rel in disarmed:
        (root / rel).chmod(0o644)
    (root / 'tools' / 'hooks' / 'cc-invented-later.sh').write_text(
        '#!/usr/bin/env bash\nexit 0\n', encoding='utf-8')
    done = subprocess.run(['bash', 'tools/setup-hooks.sh'], cwd=root,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    for rel in (*disarmed, 'tools/hooks/cc-invented-later.sh'):
        assert os.access(root / rel, os.X_OK), rel
    # The whole corpus is armed, not just the cc-* glob: the classic git
    # hooks (skipped by core.hooksPath in silence when unexecutable) and
    # the by-path tools.
    for rel in ('tools/hooks/pre-push', 'tools/hooks/prepare-commit-msg',
                WORKTREE):
        assert os.access(root / rel, os.X_OK), rel
    assert git(root, 'config', 'core.hooksPath').stdout.strip() == 'tools/hooks'


# =============================================================================
# The 0.22.0 corpus: cc-ledger-subagent (SubagentStop) and cc-ledger-session
# (Stop) — the two couriers, installed into a temp repo that has a REAL PM
# tree and a Makefile whose `pm` target runs this source tree's CLI, then fired
# at the exact JSON Claude Code delivers.
#
# The assertion is always the same pair, because it is the whole contract: what
# landed in the ledger and that the hook exited 0 either way. WHICH ledger is
# the routing rule's (0.4.0/D1): this fixture has one story `building`, so a
# row resolves its grain and lands in that grain's milestone; a row that
# resolves none lands in the tree's own `<roadmap>/ledger.jsonl` (D3). A hook that blocks a stop is broken even when it is right, and a hook
# that invents a row is broken even when it exits 0.
# =============================================================================

LEDGER_SUBAGENT = 'tools/hooks/cc-ledger-subagent.sh'
LEDGER_SESSION = 'tools/hooks/cc-ledger-session.sh'
TRANSCRIPTS = Path(__file__).parent / 'fixtures' / 'transcripts'
DISPATCH_JSONL = TRANSCRIPTS / 'subagent-dispatch.jsonl'
SESSION_JSONL = TRANSCRIPTS / 'main-session.jsonl'
LEDGER_REL = 'pm/roadmap/ledgers/0.1.jsonl'
ROOT_LEDGER_REL = 'pm/roadmap/ledger.jsonl'

# The ids the payloads below carry. Spelled once so a test asserting they were
# COPIED cannot accidentally assert against a value the verb derived.
PAYLOAD_SESSION_ID = '11111111-2222-3333-4444-555555555555'
PAYLOAD_AGENT_ID = 'ag-0c097f0217026051'
PAYLOAD_AGENT_TYPE = 'developer'

# `.PHONY: pm` is load-bearing, not decoration: a PM tree IS a `pm/` directory
# at the repo root, so an un-phony `pm` target is one make calls up to date —
# the vehicle would exit 0, print nothing, and write no row. Both hooks say so
# in their config header; this Makefile is the proof it matters.
PM_MAKEFILE = ('.PHONY: pm\n'
               'pm:\n'
               '\t@PYTHONPATH={src} {python} -m agentic_sdlc.cli pm $(ARGS)\n')

FRONTMATTER = {
    'pm/roadmap/milestones/0.1.md':
        {'id': '"0.1"', 'name': 'Demo', 'status': 'building'},
    'pm/roadmap/features/alpha.md':
        {'id': '0.1/alpha', 'milestone': '"0.1"', 'name': 'Alpha',
         'status': 'building', 'reviewed': ''},
    'pm/roadmap/stories/s0.md':
        {'id': '0.1/alpha/s0', 'feature': '0.1/alpha', 'milestone': '"0.1"',
         'name': 'S0', 'status': 'building'},
}


def ledger_repo(tmp_path: Path, name: str = 'repo',
                with_makefile: bool = True, shell: str | None = None) -> Path:
    """The corpus installed into a repo with one `building` milestone.

    Deliberately built by hand rather than through `pm new`: the hooks are the
    thing under test, and a scaffolder failure here would read as a hook
    failure.

    `shell` pins the Makefile's recipe shell. Unset is the stock consumer —
    make's default `/bin/sh`, which on macOS is bash and therefore forgiving of
    a bash-only spelling. A vehicle that names dash is the honest one.
    """
    root = corpus_repo(tmp_path, name)
    # The tree DECLARES its flow. Both couriers reach `pm ledger record` through
    # the Makefile above, and `[pm.states.*]` has no runtime fallback
    # (`vocabulary.flow_of`) — so a tree without it would fail the hook for a
    # config reason and read here as a courier that wrote no row, which is the
    # one failure this module must never mistake for another.
    (root / 'devkit.toml').write_text(FLOW_TOML, encoding='utf-8')
    for rel, front in FRONTMATTER.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        body = ['---'] + [f'{k}: {v}' for k, v in front.items()] + ['---', '', 'x', '']
        path.write_text('\n'.join(body), encoding='utf-8')
    if with_makefile:
        prologue = f'SHELL := {shell}\n' if shell else ''
        (root / 'Makefile').write_text(
            prologue + PM_MAKEFILE.format(src=REPO_ROOT / 'src',
                                          python=sys.executable),
            encoding='utf-8')
    return root


def subagent_event(root: Path, transcript: Path | str | None = DISPATCH_JSONL,
                   **over) -> dict:
    """The SubagentStop payload, every documented key present."""
    event = {
        'session_id': PAYLOAD_SESSION_ID,
        'transcript_path': str(SESSION_JSONL),
        'cwd': str(root),
        'permission_mode': 'acceptEdits',
        'hook_event_name': 'SubagentStop',
        'stop_hook_active': False,
        'agent_id': PAYLOAD_AGENT_ID,
        'agent_type': PAYLOAD_AGENT_TYPE,
        'agent_transcript_path': str(transcript) if transcript else None,
        # Never read — the agent's narration, the one source this SDLC refuses
        # to trust. It is on the payload so a test can prove it is ignored.
        'last_assistant_message': 'I used about 12000 tokens and 4 tools.',
        'background_tasks': [],
        'session_crons': [],
    }
    event.update(over)
    return {k: v for k, v in event.items() if v is not None}


def session_event(root: Path, transcript: Path | str | None = SESSION_JSONL,
                  **over) -> dict:
    """The Stop payload — no agent_id, no agent_type, no agent transcript."""
    event = {
        'session_id': PAYLOAD_SESSION_ID,
        'transcript_path': str(transcript) if transcript else None,
        'cwd': str(root),
        'permission_mode': 'acceptEdits',
        'hook_event_name': 'Stop',
        'stop_hook_active': False,
        'last_assistant_message': 'Done.',
        'background_tasks': [],
        'session_crons': [],
    }
    event.update(over)
    return {k: v for k, v in event.items() if v is not None}


def fire_ledger(root: Path, hook: str, event: dict | str,
                env: dict | None = None) -> subprocess.CompletedProcess:
    payload = event if isinstance(event, str) else json.dumps(event)
    return subprocess.run(['bash', str(root / hook)], input=payload, text=True,
                          capture_output=True, cwd=root, env=env or CLEAN_ENV)


def ledger_rows(root: Path, rel: str = LEDGER_REL) -> list[dict]:
    path = root / rel
    if not path.is_file():
        return []
    return [json.loads(line)
            for line in path.read_text(encoding='utf-8').splitlines() if line]


# --- cc-ledger-subagent: the dispatch row -------------------------------------
def test_a_subagent_stop_payload_records_exactly_one_dispatch_row(tmp_path):
    """The ship criterion, end to end: the event Claude Code delivers goes in,
    one `dispatch` row comes out, and every id on it was COPIED from the
    payload rather than derived from the transcript."""
    root = ledger_repo(tmp_path)
    done = fire_ledger(root, LEDGER_SUBAGENT, subagent_event(root))
    assert done.returncode == 0, done.stderr
    rows = ledger_rows(root)
    assert len(rows) == 1, rows
    row = rows[0]
    assert row['kind'] == 'dispatch'
    assert row['agent_type'] == PAYLOAD_AGENT_TYPE
    assert row['agent_id'] == PAYLOAD_AGENT_ID
    assert row['session_id'] == PAYLOAD_SESSION_ID
    # The transcript it was handed is the AGENT's, not the session's: the two
    # differ, and a hook reading `transcript_path` here would file the
    # orchestrator's totals as a dispatch.
    assert row['tools'] == {'Bash': 22, 'Write': 1}, row
    # D3: the tree's live state, verbatim, at the instant of the row.
    assert row['tree']['stories_wip'] == ['0.1/alpha/s0'], row
    # 0.4.0/D2 end to end, through a REAL hook: one story is in progress, so
    # the row names it — and naming it is what put the row in that milestone's
    # ledger rather than the tree's.
    assert row['grain'] == '0.1/alpha/s0', row
    assert ledger_rows(root, ROOT_LEDGER_REL) == []


def test_the_dispatchers_grain_travels_the_whole_vehicle_and_beats_the_lookup(
        tmp_path):
    """0.4.0/every-row-names-its-grain, end to end and through make.

    `GDK_LEDGER_GRAIN` names a story that is NOT the one in progress, so the
    row can only carry it if the value crossed the courier, `make` and the
    recipe shell intact AND outranked D2's tree fallback. A grain id holds a
    `/`, which is the character a vehicle that re-splits or re-quotes loses —
    the couriers' self-tests assert the argv, and this asserts the row.
    """
    root = ledger_repo(tmp_path)
    other = root / 'pm/roadmap/stories/s9.md'
    other.write_text('---\nid: 0.1/alpha/s9\nfeature: 0.1/alpha\n'
                     'milestone: "0.1"\nname: S9\nstatus: ready\n---\n\nx\n',
                     encoding='utf-8')
    done = fire_ledger(root, LEDGER_SUBAGENT, subagent_event(root),
                       env={**CLEAN_ENV, 'GDK_LEDGER_GRAIN': '0.1/alpha/s9'})
    assert done.returncode == 0, done.stderr
    rows = ledger_rows(root)
    assert len(rows) == 1, (rows, done.stderr)
    assert rows[0]['grain'] == '0.1/alpha/s9', rows[0]


def test_the_subagent_hook_never_reads_the_agents_own_narration(tmp_path):
    """`last_assistant_message` claims 12000 tokens and 4 tools; the row must
    carry the transcript's numbers and none of the agent's."""
    root = ledger_repo(tmp_path)
    assert fire_ledger(root, LEDGER_SUBAGENT,
                       subagent_event(root)).returncode == 0
    row = ledger_rows(root)[0]
    assert row['tool_calls'] == 23, row
    assert row['usage']['output'] == 5829, row


# --- cc-ledger-session: the session row ---------------------------------------
def test_a_stop_payload_records_exactly_one_session_row(tmp_path):
    root = ledger_repo(tmp_path)
    done = fire_ledger(root, LEDGER_SESSION, session_event(root))
    assert done.returncode == 0, done.stderr
    rows = ledger_rows(root)
    assert len(rows) == 1, rows
    assert rows[0]['kind'] == 'session'
    assert rows[0]['session_id'] == PAYLOAD_SESSION_ID
    # A Stop event has no agent, so the row carries neither agent field —
    # absent, never an empty string standing in for one.
    assert 'agent_id' not in rows[0], rows[0]
    assert 'agent_type' not in rows[0], rows[0]


# --- the fail-open matrix: no row, exit 0, and it SAYS SO ----------------------
# One repo per courier and every payload fired at it, each its own process on
# stdin: the repo is the cost, and no payload here writes to it.
NO_TRANSCRIPT_KEY = {LEDGER_SUBAGENT: 'agent_transcript_path',
                     LEDGER_SESSION: 'transcript_path'}


@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_payload_the_courier_cannot_file_writes_no_row_and_says_why(
        tmp_path, hook):
    """Three payloads, each fail OPEN and out loud — never an invented row.

    No transcript path: an older Claude Code, or an event shape that carries
    none; the operator must still be able to find out why the ledger is
    empty, in one line. Not JSON at all. And no Makefile: installed ahead of
    the dev loop, there is no vehicle to reach the verb through."""
    root = ledger_repo(tmp_path)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    key = NO_TRANSCRIPT_KEY[hook]
    wrong = []

    def fired(case: str, payload: dict | str, said: str,
              one_line: bool = False) -> None:
        done = fire_ledger(root, hook, payload)
        if (done.returncode != 0 or ledger_rows(root) != [] or said not in done.stderr
                or (one_line and len(done.stderr.strip().splitlines()) != 1)):
            wrong.append(f'{case}: exit {done.returncode}, '
                         f'{len(ledger_rows(root))} row(s): {done.stderr}')
    fired('no transcript path', build(root, transcript=None),
          f'carries no {key}', one_line=True)
    fired('not JSON', 'not json {{{', 'not JSON this hook can read')
    (root / 'Makefile').unlink()
    fired('no Makefile', build(root), 'has no Makefile')
    assert not wrong, '\n'.join(wrong)


@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_tilde_prefixed_transcript_path_is_expanded(tmp_path, hook):
    """Claude Code may deliver `~/.claude/projects/…`. The shell does not
    expand a tilde that arrives inside a variable, so the hook must — an
    unexpanded one reaches the verb as a relative path that is not a file, and
    the row is silently lost."""
    home = tmp_path / 'home'
    home.mkdir()
    source = DISPATCH_JSONL if hook == LEDGER_SUBAGENT else SESSION_JSONL
    shutil.copy(source, home / 'transcript.jsonl')
    root = ledger_repo(tmp_path)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    done = fire_ledger(root, hook, build(root, transcript='~/transcript.jsonl'),
                       env={**CLEAN_ENV, 'HOME': str(home)})
    assert done.returncode == 0, done.stderr
    assert len(ledger_rows(root)) == 1, done.stderr


# --- the vehicle's shell is not this hook's ------------------------------------
# `make` runs a recipe under `/bin/sh` unless the Makefile says otherwise, and a
# hand-rolled consumer Makefile may say dash. Every word the courier spells INTO
# `ARGS=` is parsed by that shell, so a value spelled as a bash literal is a
# value the vehicle may not decode. The couriers used `printf %q`, which is
# BASH's quoting: a non-ASCII path comes back as `$'…'`, dash keeps the `$` as
# text, the verb refuses "is not a file" at exit 2 — and this hook always exits
# 0, so the row is lost with nothing red anywhere
# (0.24.0/bugs/courier-path-quoting-needs-a-bash-shell).
#
# There is a SECOND dimension, and it is why this was invisible: `printf %q` is
# LOCALE-sensitive. Under `LC_ALL=en_US.UTF-8` bash 3.2 calls `é` printable and
# emits it bare, so the same courier, the same path and the same dash vehicle
# record the row perfectly — while under `C`/`POSIX`, or with the locale simply
# unset, it emits `$'…'` and the row is lost. A hook is spawned by an app, a
# daemon or a CI runner, none of which promise a UTF-8 locale, so `C` is the
# honest vehicle and it is pinned rather than inherited: a case whose verdict
# depends on the runner's locale is a case that proves nothing on the day it
# passes. (`uv run` exports `LC_CTYPE=C.UTF-8`, and it hid this entirely.)
VEHICLE_ENV = {'LC_ALL': 'C'}

# The directories below are the matrix. Every one is a legal name a transcript
# could sit under, and every one must land its row under a vehicle that is not
# bash. `café` is the case that was silently lost; the other six are the rest of
# the grammar the transport now has to be indifferent to, including a newline,
# which no spelling into a make command-line variable can survive at all.
DASH = shutil.which('dash') or '/bin/dash'
needs_dash = pytest.mark.skipif(
    not Path(DASH).exists(),
    reason='needs a POSIX shell that is not bash (dash) to be a real vehicle')

HOSTILE_DIRS = [
    pytest.param('café', id='non-ascii'),
    pytest.param('a b', id='space'),
    pytest.param("it's", id='apostrophe'),
    pytest.param('$HOME', id='dollar'),
    pytest.param('back`tick', id='backtick'),
    pytest.param('semi;colon', id='semicolon'),
    pytest.param('two\nlines', id='newline'),
]


@needs_dash
@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_hostile_transcript_path_still_records_under_a_dash_vehicle(
        tmp_path, hook):
    """Both couriers, because the transport is duplicated in both files and
    "fixed in one of them" is the failure mode a duplicated fix has.

    One repo per courier, every directory fired at it — each payload its own
    process on stdin — and the ledger emptied between fires, so each row
    counted is that payload's. A directory that loses its row names itself."""
    root = ledger_repo(tmp_path, shell=DASH)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    lost = []
    for directory in HOSTILE_DIRS:
        name = directory.values[0]
        holder = tmp_path / 'transcripts' / name
        holder.mkdir(parents=True)
        transcript = holder / 't.jsonl'
        shutil.copy(DISPATCH_JSONL if hook == LEDGER_SUBAGENT else SESSION_JSONL,
                    transcript)
        done = fire_ledger(root, hook, build(root, transcript=transcript),
                           env={**CLEAN_ENV, **VEHICLE_ENV})
        rows = ledger_rows(root)
        (root / LEDGER_REL).unlink(missing_ok=True)
        # The verb refuses a `--from-transcript` that is not a file, so a row
        # at all proves the vehicle handed it THIS path byte-exact; the numbers
        # prove it read the file rather than inventing one.
        if done.returncode != 0 or len(rows) != 1 or rows[0]['tool_calls'] <= 0:
            lost.append(f'{directory.id}: exit {done.returncode}, '
                        f'{len(rows)} row(s); the vehicle said: {done.stderr}')
    assert not lost, '\n'.join(lost)


@needs_dash
@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_dash_vehicle_carries_no_value_inside_the_args_word(tmp_path, hook):
    """The mechanism, not just the outcome: `ARGS=` must hold FIXED words only.

    A courier that merely quoted better would still pass the case above on
    every path somebody thought to list. What removes the class is that the
    path is not in the string at all — so the assertion is on the string.
    """
    root = ledger_repo(tmp_path, shell=DASH)
    holder = tmp_path / 'café dir'
    holder.mkdir()
    transcript = holder / 't.jsonl'
    shutil.copy(DISPATCH_JSONL if hook == LEDGER_SUBAGENT else SESSION_JSONL,
                transcript)
    # A vehicle that echoes the ARGS it was handed, verbatim and UNEXPANDED —
    # single quotes in the recipe, so the recipe shell reads the words rather
    # than resolving them. make expands `$(ARGS)` inside them regardless, which
    # is the whole reason a `'` in ARGS would be a defect of its own.
    (root / 'Makefile').write_text(
        f"SHELL := {DASH}\n.PHONY: pm\npm:\n\t@printf %s '$(ARGS)'\n",
        encoding='utf-8')
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    done = fire_ledger(root, hook, build(root, transcript=transcript),
                       env={**CLEAN_ENV, **VEHICLE_ENV})
    assert done.returncode == 0, done.stderr
    args = done.stderr
    assert 'café' not in args, f'the path is spelled into ARGS: {args}'
    assert '303' not in args, f'the path is spelled into ARGS: {args}'
    assert '"$GDK_LEDGER_TRANSCRIPT"' in args, args


@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_refusal_from_the_verb_is_passed_through_and_still_exits_0(
        tmp_path, hook):
    """`--from-transcript <not a file>` is a refusal the VERB owns. The hook
    neither pre-empts it nor swallows it: the sentence reaches the hook log
    and the stop is not blocked."""
    root = ledger_repo(tmp_path)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    done = fire_ledger(root, hook, build(root, transcript='/nope/absent.jsonl'))
    assert done.returncode == 0
    assert ledger_rows(root) == []
    assert 'is not a file' in done.stderr, done.stderr
