"""Land one frozen feature lane on its declared milestone branch.

    agentic-sdlc land <feature-id> --branch <branch> --commit <sha>
        --story <story-id>... --review-record <path>
        --gate-owner <name> --actor <name>

This is a resumable transaction. It validates every input before the merge,
then merges the frozen commit, runs the named owner's existing feature
rung, closes the named stories and feature through their existing belts, and
removes the worktree last. A failed phase leaves the branch and worktree in
place. The journal lives in Git's common directory, outside the project tree.
"""
from __future__ import annotations

import errno
import fcntl
import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from agentic_sdlc.core import apply, spawn
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import install, vehicle
from agentic_sdlc.repo.pm import inventory, vocabulary

VERB = 'land'
HELP = """usage: agentic-sdlc land <feature-id> --branch <branch> --commit <sha>
    --story <story-id>... --review-record <path>
    --gate-owner <name> --actor <name>

The actor must be the declared final-gate owner. The branch must still point
at the frozen commit. Land merges it into the feature's milestone branch,
runs the declared feature rung, closes the named stories and feature,
then calls `agent-worktree.sh done <slug>`. A failed phase keeps the worktree
for repair and a later retry. Exit: 0 landed | 1 phase refused | 2 usage/config."""

EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2
HEX_COMMIT = re.compile(r'^[0-9a-f]{40,64}$')
PHASES = ('validated', 'merged', 'gated', 'stories-closed', 'feature-closed',
          'cleanup', 'complete')


@dataclass(frozen=True)
class Request:
    feature: str
    branch: str
    commit: str
    stories: tuple[str, ...]
    review_record: str
    gate_owner: str
    actor: str


@dataclass(frozen=True)
class Context:
    root: Path
    cfg: vocabulary.PmConfig
    feature: inventory.Grain
    milestone: inventory.Grain
    stories: tuple[inventory.Grain, ...]
    worktree: Path | None
    slug: str
    target_branch: str
    before: str
    journal: Path


def parse(argv: list[str]) -> tuple[Request | None, str]:
    if argv and argv[0] in ('-h', '--help', 'help'):
        return None, 'help'
    if not argv:
        return None, 'a feature id is required'
    feature = argv[0]
    values: dict[str, str] = {}
    stories: list[str] = []
    i = 1
    while i < len(argv):
        flag = argv[i]
        if flag == '--story':
            i += 1
            if i >= len(argv) or not argv[i] or argv[i].startswith('--'):
                return None, '--story needs an id'
            stories.append(argv[i])
            i += 1
            continue
        if flag not in ('--branch', '--commit', '--review-record',
                        '--gate-owner', '--actor'):
            return None, f'unexpected argument {flag!r}'
        if flag in values:
            return None, f'{flag} is given twice'
        i += 1
        if i >= len(argv) or not argv[i] or argv[i].startswith('--'):
            return None, f'{flag} needs a value'
        values[flag] = argv[i]
        i += 1
    missing = [flag for flag in ('--branch', '--commit', '--review-record',
                                  '--gate-owner', '--actor')
               if flag not in values]
    if missing:
        return None, 'required argument(s) missing: ' + ', '.join(missing)
    if not stories:
        return None, 'at least one --story is required'
    if len(set(stories)) != len(stories):
        return None, '--story names an id more than once'
    if not HEX_COMMIT.fullmatch(values['--commit']):
        return None, '--commit must be a full 40- or 64-character hexadecimal hash'
    return Request(feature, values['--branch'], values['--commit'],
                   tuple(stories), values['--review-record'],
                   values['--gate-owner'], values['--actor']), ''


def main(argv: list[str]) -> int:
    request, defect = parse(argv)
    if defect == 'help':
        print(HELP)
        return EXIT_OK
    if defect:
        return _usage(defect)
    assert request is not None
    try:
        if request.actor != request.gate_owner:
            return _refuse(f'final-gate owner is {request.gate_owner!r}; '
                           f'actor {request.actor!r} cannot land this batch')
        root = repo_root().resolve()
        common = _git(root, 'rev-parse', '--git-common-dir')
        if not common:
            return _refuse('Git could not name the common directory for the land journal')
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = root / common_path
        with _transaction_lock(common_path.resolve()):
            with inventory.reading_tree():
                context, why = _preflight(request)
            if why:
                return _refuse(why)
            assert context is not None
            return _run(request, context)
    except (ValueError, OSError, spawn.SubprocessError) as err:
        return _refuse(f'{type(err).__name__}: {err}')
    except SystemExit as err:
        # Existing PM config readers use exit 2 for an unreadable declaration.
        code = err.code if isinstance(err.code, int) else EXIT_USAGE
        return EXIT_USAGE if code == EXIT_USAGE else EXIT_REFUSED


def _preflight(request: Request) -> tuple[Context | None, str]:
    root = repo_root().resolve()
    cfg = vocabulary.load()
    index = inventory.grain_index(cfg)
    feature = index.get(request.feature)
    if feature is None or feature.kind != vocabulary.GRAIN_FEATURE:
        return None, f'{request.feature!r} does not resolve to a feature'
    if request.actor != request.gate_owner:
        return None, (f'final-gate owner is {request.gate_owner!r}; actor '
                      f'{request.actor!r} cannot land this batch. The owner '
                      f'runs `{vehicle.command("land", request.feature, "…")}`')
    if not request.actor.strip():
        return None, '--actor and --gate-owner must name the same owner'
    milestone_id = inventory.milestone_of(cfg, feature.gid)
    milestone = index.get(milestone_id)
    if milestone is None:
        return None, f'{feature.gid} has no resolvable milestone binding'
    target_branch = milestone.field('branch')
    if not target_branch:
        return None, (f'{feature.gid} belongs on milestone branch '
                      f'{target_branch!r}; it cannot be landed without one')
    prefix = cfg.agent_branch_prefix
    if not prefix or not request.branch.startswith(prefix):
        return None, (f'{request.branch!r} is not under the declared agent '
                      f'branch prefix {prefix!r}')
    slug = request.branch[len(prefix):]
    if not slug or any(ch not in 'abcdefghijklmnopqrstuvwxyz'
                       'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for ch in slug):
        return None, f'{request.branch!r} has no safe worktree slug'
    if not inventory.segment_is_literal(request.feature):
        return None, f'{request.feature!r} is not a literal feature id'
    stories = []
    for sid in request.stories:
        story = index.get(sid)
        if story is None or story.kind != vocabulary.GRAIN_STORY:
            return None, f'{sid!r} does not resolve to a story'
        if story.binding != feature.gid:
            return None, f'{sid!r} is not bound to feature {feature.gid}'
        stories.append(story)

    common = _git(root, 'rev-parse', '--git-common-dir')
    if not common:
        return None, 'Git could not name the common directory for the land journal'
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = root / common_path
    journal = common_path.resolve() / 'agent-land' / f'{request.commit}.json'
    if journal.parent.is_symlink():
        return None, 'the land journal directory is a symlink; nothing was merged'
    if journal.parent.exists() and not journal.parent.is_dir():
        return None, 'the land journal path is not a directory; nothing was merged'
    if journal.is_symlink():
        return None, 'the land journal file is a symlink; nothing was merged'
    context = Context(root, cfg, feature, milestone, tuple(stories), None,
                      slug, target_branch, '', journal)
    state = _read_journal(journal)
    if state.get('phase') == 'complete':
        defect = _journal_defect(request, context)
        return (None, defect) if defect else (context, '')

    record = Path(request.review_record)
    if record.is_absolute() or '..' in record.parts:
        return None, '--review-record must stay inside the repository'
    record_path = root / record
    if not record_path.resolve().is_relative_to(root):
        return None, '--review-record resolves outside the repository'
    if not record_path.is_file():
        return None, f'review record {request.review_record!r} does not exist'
    from agentic_sdlc.repo.pm import verdict
    from agentic_sdlc.repo.conveyor import steps
    record_size = record_path.stat().st_size
    if record_size > steps.MAX_RECORD_BYTES:
        return None, (f'review record is {record_size} bytes, over the '
                      f'{steps.MAX_RECORD_BYTES}-byte read bound')
    try:
        parsed = verdict.parse(record_path.read_text(encoding='utf-8'))
        _, record_defect = verdict.own_blocks(
            cfg, parsed, record_path, feature.gid, given=True)
    except (OSError, UnicodeDecodeError, verdict.NoVerdict,
            verdict.MalformedVerdict) as err:
        return None, f'review record {request.review_record!r} is unreadable: {err}'
    if record_defect:
        return None, f'review record {request.review_record!r}: {record_defect}'

    before = _git(root, 'rev-parse', '--verify', 'HEAD')
    current = _git(root, 'branch', '--show-current')
    if not before or current != target_branch:
        return None, (f'integration checkout must be on {target_branch!r}; '
                      f'it is {current or "detached"!r}')
    dirty = _git(root, 'status', '--porcelain', '--untracked-files=all')
    expected = _expected_pm_paths(context, state.get('phase', ''))
    changed = {line[3:] for line in dirty.splitlines()}
    unexpected = sorted(changed - expected)
    if unexpected:
        return None, ('integration checkout has uncommitted paths outside this '
                      f'land transaction: {", ".join(unexpected[:8])}')

    lane = _worktree_for_branch(root, request.branch)
    if lane is None and state.get('phase') == 'cleanup':
        context = Context(root, cfg, feature, milestone, tuple(stories), None,
                          slug, target_branch, before, journal)
        defect = _journal_defect(request, context)
        return (None, defect) if defect else (context, '')
    if lane is None:
        return None, f'no registered worktree holds {request.branch!r}'
    lane_head = _git(lane, 'rev-parse', '--verify', 'HEAD')
    if lane_head != request.commit:
        return None, (f'{request.branch} is not frozen at {request.commit}; '
                      f'its HEAD is {lane_head or "unreadable"}')
    marker = lane / '.agent-scope'
    if not marker.is_file():
        return None, f'{request.branch} has no .agent-scope marker'
    marker_fields = _marker(marker)
    if marker_fields.get('branch') != request.branch:
        return None, f'{request.branch} .agent-scope names another branch'
    base_commit = marker_fields.get('base_sha', '')
    base_defect = _base_ancestry_defect(
        root, base_commit, request.commit, before, request.branch,
        target_branch)
    if base_defect:
        return None, base_defect
    if not _git(root, 'merge-base', request.commit, before):
        return None, (f'{request.branch} frozen commit and integration branch '
                      'have no common history')
    if marker_fields.get('path') and Path(marker_fields['path']).resolve() != lane.resolve():
        return None, f'{request.branch} .agent-scope names another worktree path'
    lane_dirty = _git(lane, 'status', '--porcelain', '--untracked-files=all')
    if lane_dirty:
        return None, (f'{request.branch} has uncommitted work; commit or remove '
                      'it before landing')
    if _git(root, 'merge-base', '--is-ancestor', request.commit, before,
            allow_failure=True) == '0':
        # A completed/resumed merge. Journal validation below still decides if
        # this transaction owns that commit.
        pass
    elif lane_head != request.commit:
        return None, 'the lane moved away from its reported frozen commit'
    context = Context(root, cfg, feature, milestone, tuple(stories), lane,
                      slug, target_branch, before, journal)
    why = _journal_defect(request, context)
    return (None, why) if why else (context, '')


def _run(request: Request, context: Context) -> int:
    state = _read_journal(context.journal)
    if state.get('phase') == 'complete':
        print(f'[{VERB}] already complete — {request.commit}')
        return EXIT_OK
    if state.get('phase') and state.get('phase') not in PHASES:
        return _refuse('land journal has an unknown phase; worktree is preserved')
    before = str(state.get('before') or context.before)
    if state.get('phase') == 'cleanup':
        if context.worktree is None or not context.worktree.exists():
            _save_phase(context, request, 'complete', {'before': before})
            print(f'[{VERB}] complete — {request.feature} landed at {request.commit}')
            return EXIT_OK
    gate_head = str(state.get('gate_head') or '')
    if (_at_least(state.get('phase', ''), 'gated')
            and state.get('phase') != 'cleanup' and gate_head
            and _git(context.root, 'rev-parse', 'HEAD') != gate_head):
        # A later merge changes the input tree. Keep the land transaction, but
        # ask the named gate owner to re-prove the new tree before resuming.
        state = _save_phase(context, request, 'merged', {'before': before})
    if not _at_least(state.get('phase', ''), 'merged'):
        gate_command = _gate_command()
        state = _save_phase(context, request, 'validated', {
            'before': before, 'gate_ref': before, 'gate_command': gate_command})
        result = spawn.run(['git', 'merge', '--no-ff', '--no-edit',
                            request.commit], cwd=context.root,
                           capture_output=True, text=True)
        if result.returncode:
            _print_tail(result.stdout, result.stderr)
            return _refuse('merge failed; resolve and commit the merge in the '
                           'integration checkout (or abort it), then resume land. '
                           'Worktree kept.')
        state = _save_phase(context, request, 'merged', {'before': before})
        print(f'[{VERB}] merged {request.commit} into {context.target_branch}')
    if not _at_least(state.get('phase', ''), 'gated'):
        gate_command = _gate_command()
        result = spawn.run(gate_command,
                           cwd=context.root, capture_output=True, text=True)
        if result.returncode:
            _print_tail(result.stdout, result.stderr)
            return _refuse(f'`{vehicle.command("verify", "--feature")}` failed '
                           f'(exit {result.returncode}); repair and resume land. '
                           'Worktree kept.')
        state = _save_phase(context, request, 'gated',
                            {'before': before, 'gate_ref': before,
                             'gate_head': _git(context.root, 'rev-parse', 'HEAD')})
        print(f'[{VERB}] feature rung passed after {before}')
    if not _at_least(state.get('phase', ''), 'stories-closed'):
        from agentic_sdlc.repo.conveyor import driver
        code = driver.main(['close', driver.OP_STORY, *request.stories])
        if code:
            return _refuse('story close failed; repair and resume land. Worktree kept.')
        state = _save_phase(context, request, 'stories-closed')
    if not _at_least(state.get('phase', ''), 'feature-closed'):
        from agentic_sdlc.repo.conveyor import driver
        code = driver.main(['close', driver.OP_FEATURE, request.feature,
                            '--review-record', request.review_record])
        if code:
            return _refuse('feature close failed; repair and resume land. Worktree kept.')
        state = _save_phase(context, request, 'feature-closed')
    if not _at_least(state.get('phase', ''), 'complete'):
        if state.get('phase') != 'cleanup':
            state = _save_phase(context, request, 'cleanup', {'before': before})
        if context.worktree is None or not context.worktree.exists():
            _save_phase(context, request, 'complete', {'before': before})
            print(f'[{VERB}] complete — {request.feature} landed at {request.commit}')
            return EXIT_OK
        tool = dict(install.PLANS['install-hooks'])['agent-worktree.sh']
        result = spawn.run(['bash', tool, ''.join(('do', 'ne')), context.slug],
                           cwd=context.root,
                           capture_output=True, text=True)
        if result.returncode:
            _print_tail(result.stdout, result.stderr)
            return _refuse('worktree cleanup failed; the worktree and branch are '
                           'preserved. Repair and resume land.')
        _save_phase(context, request, 'complete', {'before': before})
    print(f'[{VERB}] complete — {request.feature} landed at {request.commit}')
    return EXIT_OK


def _journal_defect(request: Request, context: Context) -> str:
    state = _read_journal(context.journal)
    if not state:
        return ''
    identity = _identity(request, context)
    expected_keys = {'version', 'identity', 'phase', 'before',
                     'gate_ref', 'gate_command'}
    if state.get('phase') in ('gated', 'stories-closed', 'feature-closed',
                              'cleanup', 'complete'):
        expected_keys.add('gate_head')
    optional_keys = ({'gate_head'} if state.get('phase') in
                     ('merged', 'gated', 'stories-closed', 'feature-closed',
                      'cleanup', 'complete') else set())
    if set(state) - expected_keys - optional_keys or expected_keys - set(state):
        return 'land journal schema is incomplete or contains unknown fields'
    identity_keys = {'commit', 'branch', 'feature_id', 'story_ids',
                     'review_record', 'gate_owner', 'actor', 'milestone_id',
                     'target_branch'}
    saved_identity = state.get('identity')
    if (state.get('version') != 1 or not isinstance(saved_identity, dict)
            or set(saved_identity) != identity_keys):
        return 'land journal version or identity schema is invalid'
    if state.get('identity') != identity:
        return ('a land journal already names this commit with different '
                'feature, stories, record, branch or gate owner')
    phase = state.get('phase', '')
    if phase not in PHASES:
        return f'land journal phase {phase!r} is invalid'
    before = state.get('before')
    if not isinstance(before, str) or not HEX_COMMIT.fullmatch(before):
        return 'land journal before must be a full commit hash'
    if _git(context.root, 'cat-file', '-e', f'{before}^{{commit}}',
            allow_failure=True) != '0':
        return 'land journal before does not name a commit'
    if state.get('gate_ref') != before:
        return 'land journal gate_ref differs from its validated before commit'
    gate_command = _gate_command()
    if state.get('gate_command') != gate_command:
        return 'land journal gate command does not match its validated before commit'
    if 'gate_head' in state and (not isinstance(state['gate_head'], str)
                                  or not HEX_COMMIT.fullmatch(state['gate_head'])):
        return 'land journal gate_head must be a full commit hash'
    if 'gate_head' in state and _git(
            context.root, 'cat-file', '-e', f"{state['gate_head']}^{{commit}}",
            allow_failure=True) != '0':
        return 'land journal gate_head does not name a commit'
    before_ancestor = _git(context.root, 'merge-base', '--is-ancestor',
                           before, 'HEAD', allow_failure=True)
    if before_ancestor != '0':
        return 'land journal before is not an ancestor of integration HEAD'
    if phase in ('merged', 'gated', 'stories-closed', 'feature-closed',
                 'cleanup', 'complete'):
        ancestor = _git(context.root, 'merge-base', '--is-ancestor',
                        request.commit, 'HEAD', allow_failure=True)
        if ancestor != '0':
            return ('the journal says this lane was merged but the frozen '
                    'commit is not in the integration branch')
    return ''


def _save_phase(context: Context, request: Request, phase: str,
                extra: dict | None = None) -> dict:
    identity = _identity(request, context)
    previous = _read_journal(context.journal)
    if previous and previous.get('identity') != identity:
        raise OSError('land journal identity changed; refusing to replace it')
    body = {**previous, 'version': 1, 'identity': identity,
            'phase': phase, **(extra or {})}
    plan = apply.Plan().make_dir(context.journal.parent,
                                 label='land journal directory')
    plan.overwrite(context.journal,
                   json.dumps(body, sort_keys=True, separators=(',', ':')) + '\n',
                   label='land transaction phase')
    landed = plan.apply()
    if landed.blocked or landed.failed:
        detail = (landed.blocked[0].describe() if landed.blocked
                  else landed.error)
        raise OSError(f'cannot save land phase {phase}: {detail}')
    return body


def _identity(request: Request, context: Context) -> dict:
    return {'commit': request.commit, 'branch': request.branch,
            'feature_id': request.feature, 'story_ids': list(request.stories),
            'review_record': request.review_record,
            'gate_owner': request.gate_owner, 'actor': request.actor,
            'milestone_id': context.milestone.gid,
            'target_branch': context.target_branch}


def _gate_command() -> list[str]:
    """The argv for the declared, feature-scoped validation rung."""
    return shlex.split(vehicle.command('verify', '--feature'))


def _expected_pm_paths(context: Context, phase: str) -> set[str]:
    """The only tracked files a successful or refused belt can have changed."""
    if phase not in ('merged', 'gated', 'stories-closed', 'feature-closed', 'cleanup'):
        return set()
    from agentic_sdlc.repo.pm import ledger
    paths = {str(context.cfg.rel(ledger.ledger_for(
        context.cfg, context.milestone.gid)))}
    if phase in ('gated', 'stories-closed', 'feature-closed', 'cleanup'):
        paths.update(context.cfg.rel(grain.path) for grain in context.stories)
    if phase in ('stories-closed', 'feature-closed', 'cleanup'):
        paths.add(context.cfg.rel(context.feature.path))
    return paths


def _read_journal(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {'phase': 'invalid'}
    return value if isinstance(value, dict) else {'phase': 'invalid'}


def _worktree_for_branch(root: Path, branch: str) -> Path | None:
    out = _git(root, 'worktree', 'list', '--porcelain')
    path: Path | None = None
    for line in (*out.splitlines(), ''):
        if line.startswith('worktree '):
            path = Path(line[9:])
        elif line.startswith('branch refs/heads/') and path is not None:
            if line.removeprefix('branch refs/heads/') == branch:
                return path.resolve()
            path = None
        elif not line:
            path = None
    return None


def _marker(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        key, sep, value = line.partition('=')
        if sep and key in ('path', 'branch', 'base', 'base_sha'):
            fields[key] = value
    return fields


def _base_ancestry_defect(root: Path, base_sha: str, lane_commit: str,
                          integration_head: str, branch: str,
                          target_branch: str) -> str:
    if not HEX_COMMIT.fullmatch(base_sha):
        return f'{branch} .agent-scope has no immutable base_sha'
    if _git(root, 'cat-file', '-e', f'{base_sha}^{{commit}}',
            allow_failure=True) != '0':
        return f'{branch} .agent-scope base_sha is not a commit'
    if _git(root, 'merge-base', '--is-ancestor', base_sha, integration_head,
            allow_failure=True) != '0':
        return (f'{branch} immutable base {base_sha} is not an ancestor '
                f'of integration branch {target_branch!r}')
    if _git(root, 'merge-base', '--is-ancestor', base_sha, lane_commit,
            allow_failure=True) != '0':
        return (f'{branch} frozen commit does not descend from its immutable '
                f'base {base_sha}')
    return ''


def _transaction_lock(common: Path):
    """Return a nonblocking flock context for this repository's land journal."""
    lock_dir = common / 'agent-land'
    lock_path = lock_dir / 'transaction.lock'
    if lock_dir.is_symlink() or (lock_dir.exists() and not lock_dir.is_dir()):
        raise OSError('land journal directory is unsafe')
    if not lock_path.exists():
        plan = apply.Plan().make_dir(lock_dir, label='land journal directory')
        plan.overwrite(lock_path, '', label='land transaction lock')
        result = plan.apply()
        if (result.blocked or result.failed) and not (
                lock_path.is_file() and not lock_path.is_symlink()):
            detail = result.blocked[0].describe() if result.blocked else result.error
            raise OSError(f'cannot prepare land transaction lock: {detail}')
    if lock_path.is_symlink() or not lock_path.is_file():
        raise OSError('land transaction lock path is unsafe')
    try:
        handle = lock_path.open('r')
    except OSError as err:
        raise OSError(f'cannot open land transaction lock: {err}') from err
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as err:
            raise OSError('another land transaction is active for this repository') from err
        except OSError as err:
            if err.errno in (errno.EACCES, errno.EAGAIN):
                raise OSError('another land transaction is active for this repository') from err
            raise
        return _LockHandle(handle)
    except BaseException:
        handle.close()
        raise


class _LockHandle:
    def __init__(self, handle):
        self.handle = handle

    def __enter__(self):
        return self

    def __exit__(self, *_):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def _git(cwd: Path, *args: str, allow_failure: bool = False) -> str:
    result = spawn.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode and not allow_failure:
        return ''
    return str(result.returncode) if allow_failure else result.stdout.strip()


def _at_least(found: str, required: str) -> bool:
    try:
        return PHASES.index(found) >= PHASES.index(required)
    except ValueError:
        return False


def _usage(why: str) -> int:
    print(f'agentic-sdlc {VERB}: {why}', file=sys.stderr)
    print(HELP, file=sys.stderr)
    return EXIT_USAGE


def _refuse(why: str) -> int:
    print(f'[{VERB}] refused — {why}', file=sys.stderr)
    return EXIT_REFUSED


def _print_tail(stdout: str, stderr: str, limit: int = 20) -> None:
    lines = (stderr + '\n' + stdout).splitlines()
    for line in lines[-limit:]:
        print(line, file=sys.stderr)
