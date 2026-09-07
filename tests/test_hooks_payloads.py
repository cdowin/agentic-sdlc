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

import json
import os
import shutil
import subprocess
import sys
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


def fire(root: Path, hook: str, command: str) -> int:
    event = json.dumps({'tool_name': 'Bash',
                        'tool_input': {'command': command},
                        'cwd': str(root)})
    return subprocess.run(['bash', str(root / hook)], input=event,
                          text=True, capture_output=True).returncode


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
)
BLOCKED = (
    'git commit -m "fix: x"',
    'git commit -am "sweep"',
    'git commit --all -m "sweep"',
)


def test_pathspec_allows_every_path_naming_spelling_and_blocks_the_pathless(
        hooks_repo):
    """Twelve rows, one case, both directions: a hook that blocks everything
    and a hook that is disarmed are equally broken, and only the pair tells
    them apart. A row that answers wrongly names itself."""
    wrong = ([f'BLOCKED: {c}' for c in ALLOWED
              if fire(hooks_repo, PATHSPEC, c) != 0]
             + [f'allowed: {c}' for c in BLOCKED
                if fire(hooks_repo, PATHSPEC, c) != 2])
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


def corpus_repo(parent: Path, name: str = 'repo') -> Path:
    """A git repo with the full corpus installed, armed, committed, and one
    commit on `main` — the smallest tree every scenario below can build on."""
    root = parent / name
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
    return root


def git(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *argv], cwd=root, capture_output=True,
                          text=True, env=CLEAN_ENV)


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
    assert fire_stop(root).returncode == 0


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
    subprocess.run(['git', 'init', '-q', '--bare', str(origin)], check=True)
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
    root = corpus_repo(tmp_path)
    origin = with_origin(root, tmp_path)
    write_makefile(root, check_ok=True)
    assert git(root, 'checkout', '-q', '-b', 'staging').returncode == 0
    done = git(root, 'push', 'origin', 'staging')
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


# --- prepare-commit-msg: agents stamped, the human never -----------------------
def last_message(root: Path) -> str:
    return git(root, 'log', '-1', '--format=%B').stdout


def test_prepare_commit_msg_stamps_agent_commits(tmp_path):
    root = corpus_repo(tmp_path)
    (root / MARKER).write_text('branch=feat/x\nbase=main\n', encoding='utf-8')
    assert git(root, 'commit', '-q', '--allow-empty',
               '-m', 'feat: x').returncode == 0
    assert 'Co-Authored-By: Claude' in last_message(root)


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
def worktree(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(['bash', str(root / WORKTREE), *argv], cwd=root,
                          capture_output=True, text=True, env=CLEAN_ENV)


def test_worktree_new_creates_branch_marker_and_prints_the_path(tmp_path):
    root = corpus_repo(tmp_path)
    assert git(root, 'branch', 'staging').returncode == 0
    done = worktree(root, 'new', 'sluga')
    assert done.returncode == 0, done.stderr
    path = Path(done.stdout.strip())
    assert path == root / '.claude/worktrees/sluga'
    marker = (path / MARKER).read_text(encoding='utf-8')
    assert 'branch=feat/sluga' in marker
    assert 'base=staging' in marker
    assert git(path, 'branch', '--show-current').stdout.strip() == 'feat/sluga'


def test_worktree_done_refuses_while_work_is_uncommitted(tmp_path):
    """The property the tool exists for: teardown must never eat work. The
    planted marker itself must NOT count as dirt — only real files do."""
    root = corpus_repo(tmp_path)
    assert git(root, 'branch', 'staging').returncode == 0
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
    assert git(root, 'branch', 'staging').returncode == 0
    path = Path(worktree(root, 'new', 'keeper').stdout.strip())
    (path / 'landed.gd').write_text('# done\n', encoding='utf-8')
    assert git(path, 'add', 'landed.gd').returncode == 0
    assert git(path, 'commit', '-q', '-m', 'feat: landed',
               '--', 'landed.gd').returncode == 0
    done = worktree(root, 'done', 'keeper')
    assert done.returncode == 0, done.stderr
    assert 'NOT merged' in done.stderr
    assert git(root, 'show-ref', '--verify',
               'refs/heads/feat/keeper').returncode == 0, 'commits were lost'
    # Merge it, re-run done: now the branch goes too.
    assert git(root, 'checkout', '-q', 'staging').returncode == 0
    assert git(root, 'merge', '-q', 'feat/keeper').returncode == 0
    assert git(root, 'branch', '-d', 'feat/keeper').returncode == 0


def _pm_tree(root: Path, status: str, flow: str = FLOW_TOML) -> None:
    """A PM tree the worktree script can ASK about: one milestone at `status`
    declaring `branch: feat/integration`, the flow, and the `make pm` target
    the script's `PM_CMD` runs — routed to the CLI from source, the same
    Makefile `ledger_repo` below plants."""
    (root / 'devkit.toml').write_text(flow, encoding='utf-8')
    (root / 'Makefile').write_text(
        PM_MAKEFILE.format(src=REPO_ROOT / 'src', python=sys.executable),
        encoding='utf-8')
    milestone = root / 'pm/roadmap/milestones/0.1.0.md'
    milestone.parent.mkdir(parents=True)
    milestone.write_text(f'---\nid: "0.1.0"\nstatus: {status}\n'
                         f'branch: feat/integration\n---\n', encoding='utf-8')


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
    """
    for status, flow in (('building', FLOW_TOML),
                         ('doing', FLOW_TOML.replace('"building"',
                                                     '"doing"'))):
        root = corpus_repo(tmp_path, name=f'repo-{status}')
        assert git(root, 'branch', 'staging').returncode == 0
        assert git(root, 'branch', 'feat/integration').returncode == 0
        _pm_tree(root, status, flow)
        done = worktree(root, 'new', 'based')
        assert done.returncode == 0, done.stderr
        marker = (Path(done.stdout.strip()) / MARKER).read_text(
            encoding='utf-8')
        assert 'base=feat/integration' in marker, (status, done.stderr)
        assert 'could not answer' not in done.stderr, done.stderr


def test_worktree_new_falls_back_when_the_cli_cannot_answer(tmp_path):
    """No PM tree, no flow, no `make pm` — the three trees above start this
    way — is not an error the worktree tool should die on: it says so on
    stderr and bases off FALLBACK_BASE, which is what a tree with no PM
    records means. A milestone the CLI cannot read (no flow declared) is the
    same answer, said the same way, never a silent trunk base."""
    root = corpus_repo(tmp_path)
    assert git(root, 'branch', 'staging').returncode == 0
    milestone = root / 'pm/roadmap/milestones/0.1.0.md'
    milestone.parent.mkdir(parents=True)
    milestone.write_text('---\nid: "0.1.0"\nstatus: building\n'
                         'branch: feat/integration\n---\n', encoding='utf-8')
    done = worktree(root, 'new', 'unasked')
    assert done.returncode == 0, done.stderr
    assert 'could not answer' in done.stderr, done.stderr
    assert 'basing off staging' in done.stderr, done.stderr
    marker = (Path(done.stdout.strip()) / MARKER).read_text(encoding='utf-8')
    assert 'base=staging' in marker


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
    # (model.py:718 `flow_of`) — so a tree without it would fail the hook for a
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
@pytest.mark.parametrize('hook,event', [
    (LEDGER_SUBAGENT, 'agent_transcript_path'),
    (LEDGER_SESSION, 'transcript_path'),
])
def test_a_payload_with_no_transcript_path_writes_no_row_and_says_why(
        tmp_path, hook, event):
    """An older Claude Code, or an event shape that carries no path. No row —
    and never an invented one — but the operator must be able to find out why
    the ledger is empty."""
    root = ledger_repo(tmp_path)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    done = fire_ledger(root, hook, build(root, transcript=None))
    assert done.returncode == 0
    assert ledger_rows(root) == []
    assert f'carries no {event}' in done.stderr, done.stderr
    assert len(done.stderr.strip().splitlines()) == 1, done.stderr


@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_payload_that_is_not_json_writes_no_row_and_says_why(tmp_path, hook):
    root = ledger_repo(tmp_path)
    done = fire_ledger(root, hook, 'not json {{{')
    assert done.returncode == 0
    assert ledger_rows(root) == []
    assert 'not JSON this hook can read' in done.stderr, done.stderr


@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_a_repo_with_no_makefile_writes_no_row_and_says_why(tmp_path, hook):
    """Installed ahead of the dev loop there is no vehicle to reach the verb
    through. Fail OPEN, out loud — and never pretend a row was written."""
    root = ledger_repo(tmp_path, with_makefile=False)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    done = fire_ledger(root, hook, build(root))
    assert done.returncode == 0
    assert ledger_rows(root) == []
    assert 'has no Makefile' in done.stderr, done.stderr


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
@pytest.mark.parametrize('directory', HOSTILE_DIRS)
def test_a_hostile_transcript_path_still_records_under_a_dash_vehicle(
        tmp_path, hook, directory):
    """Both couriers, because the transport is duplicated in both files and
    "fixed in one of them" is the failure mode a duplicated fix has."""
    root = ledger_repo(tmp_path, shell=DASH)
    holder = tmp_path / 'transcripts' / directory
    holder.mkdir(parents=True)
    transcript = holder / 't.jsonl'
    shutil.copy(DISPATCH_JSONL if hook == LEDGER_SUBAGENT else SESSION_JSONL,
                transcript)
    build = subagent_event if hook == LEDGER_SUBAGENT else session_event
    done = fire_ledger(root, hook, build(root, transcript=transcript),
                       env={**CLEAN_ENV, **VEHICLE_ENV})
    assert done.returncode == 0, done.stderr
    rows = ledger_rows(root)
    # The verb refuses a `--from-transcript` that is not a file, so a row at
    # all proves the vehicle handed it THIS path byte-exact; the numbers prove
    # it read the file rather than inventing one.
    assert len(rows) == 1, f'no row landed. the vehicle said: {done.stderr}'
    assert rows[0]['tool_calls'] > 0, rows[0]


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


@pytest.mark.parametrize('hook', [LEDGER_SUBAGENT, LEDGER_SESSION])
def test_the_ledger_hooks_replay_their_own_corpus(tmp_path, hook):
    """`--self-test` is the shipped proof, and it must pass as INSTALLED."""
    root = ledger_repo(tmp_path)
    done = subprocess.run(['bash', str(root / hook), '--self-test'],
                          capture_output=True, text=True, cwd=root,
                          env=CLEAN_ENV)
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'SELF-TEST OK' in done.stdout, done.stdout


