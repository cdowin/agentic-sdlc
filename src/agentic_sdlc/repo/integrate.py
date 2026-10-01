"""agentic-sdlc integrate — merge a batch of lanes, prove it once, close it.

usage: agentic-sdlc integrate <slug>... [--batch <name>] [--base <branch>] [--keep-lanes]

Fetches origin, then merges each `origin/<agent prefix><slug>` (`--no-ff`)
into branch `integrate/<batch>` (default `<UTC date>-<n>`, or the newest one a
red run left), in a worktree beside the primary checkout, cut from the
in-progress milestone's `branch:` or `--base`. `[integrate] per_merge` runs
after each merge and `[integrate] proof` runs ONE time, both streamed; the
proof line says what ran and how long, and a `gate` row named `integrate`
goes to the ledger. A slug with no origin branch counts as integrated only
when `st-<slug>` is in a `done`-category state; otherwise it is exit 1.
Red (a conflict, a red check): the lane is named, nothing is closed, every
branch stays, and the same command again resumes. Green: each `st-<slug>`
gets the first story `done` state through `pm story`, committed in the batch;
the base fast-forwards (refused while its checkout has uncommitted tracked
changes); unless `--keep-lanes`, each lane's worktree, branch and origin
branch go, then the batch. Nothing is pushed: `next: git push origin <base>`.

`[integrate]` is a DECLARATION in devkit.toml, with no default:
    per_merge = []                # make targets after each merge; may be empty
    proof     = ["check", "unit"] # make targets run once over the batch

Exit: 0 green, or nothing to do | 1 conflict, red check, dirty checkout,
an unknown lane, a lane not removed | 2 usage, config, or no base to integrate into.
"""
from __future__ import annotations

import os
import re
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agentic_sdlc.core import frontmatter, spawn
from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import gates_extra
from agentic_sdlc.repo.pm import inventory, vocabulary

SECTION, PER_MERGE, PROOF = 'integrate', 'per_merge', 'proof'
TAG = '[integrate]'
GATE = 'integrate'
BATCH = 'refs/heads/integrate/'
HEADS, REMOTE = 'refs/heads/', 'refs/remotes/origin/'
EXIT_OK, EXIT_RED, EXIT_USAGE = 0, 1, 2
SAFE = re.compile(r'^[A-Za-z0-9._-]+$')
DATED = re.compile(r'^(\d{4}-\d{2}-\d{2})-(\d+)$')
TAIL_LINES = 40
# `agent-worktree.sh`'s teardown subcommand; not a state word.
WORKTREE_DONE = 'done'


class Red(Exception):
    """Exit 1: a conflict, a red check, or a checkout that is not clean."""


class Usage(Exception):
    """Exit 2."""


@dataclass(frozen=True)
class Request:
    slugs: tuple[str, ...]
    batch: str
    base: str
    keep_lanes: bool


def settings(section: dict | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`(per_merge, proof)`. A DECLARATION: no key has a default, and an absent
    section or key is refused by name. A bare string is one target name."""
    if section is None:
        raise ConfigError(
            f'[{SECTION}] is not declared in devkit.toml — this verb runs YOUR '
            f'make targets and cannot invent them. Declare `{PER_MERGE} = []` '
            f'and `{PROOF} = ["check", "unit"]` with your target names')
    out = []
    for key in (PER_MERGE, PROOF):
        if key not in section:
            raise ConfigError(f'[{SECTION}] {key} is not declared, and it has '
                              f'no default — write {key} = ["<make target>"]')
        raw = section[key]
        names = [raw] if isinstance(raw, str) else raw
        if not isinstance(names, list) or not all(
                isinstance(n, str) and gates_extra.TARGET.fullmatch(n) for n in names):
            raise ConfigError(f'[{SECTION}] {key} must be a make target name or '
                              f'a list of them, got {raw!r}')
        if key == PROOF and not names:
            raise ConfigError(f'[{SECTION}] {PROOF} is empty — a batch proved '
                              f'by nothing would close on no evidence')
        out.append(tuple(names))
    return out[0], out[1]


def parse(argv: list[str]) -> Request:
    slugs: list[str] = []
    flags = {'--batch': '', '--base': ''}
    keep, i = False, 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--keep-lanes':
            keep = True
        elif arg in flags:
            if i + 1 >= len(argv) or argv[i + 1].startswith('-'):
                raise Usage(f'{arg} needs a value')
            i += 1
            flags[arg] = argv[i]
        elif arg.startswith('-'):
            raise Usage(f'unknown flag {arg!r}')
        elif arg not in slugs:
            slugs.append(arg)
        i += 1
    if not slugs:
        raise Usage('name at least one lane slug')
    for value in (*slugs, flags['--batch'] or 'x'):
        if not SAFE.fullmatch(value):
            raise Usage(f'{value!r} has characters outside a-z A-Z 0-9 . _ -')
    return Request(tuple(slugs), flags['--batch'], flags['--base'], keep)


def main(argv: list[str], section: Callable[[], dict | None]) -> int:
    if any(a in ('-h', '--help') for a in argv):
        print(__doc__.strip())
        return EXIT_OK
    try:
        request = parse(list(argv))
        per_merge, proof = settings(section())
        return _run(request, per_merge, proof)
    except (Usage, ConfigError) as err:
        print(f'agentic-sdlc integrate: {err}', file=sys.stderr)
        return EXIT_USAGE
    except Red as err:
        print(f'{TAG} STOPPED — {err}', file=sys.stderr)
        return EXIT_RED
    except (OSError, spawn.SubprocessError) as err:
        print(f'{TAG} STOPPED — {type(err).__name__}: {err}', file=sys.stderr)
        return EXIT_RED


def _run(req: Request, per_merge: tuple[str, ...], proof: tuple[str, ...]) -> int:
    root = repo_root()
    cfg = vocabulary.load()
    prefix = cfg.agent_branch_prefix
    if not prefix:
        raise Usage('[pm] agent_branch_prefix is empty, so a lane has no branch')
    base = req.base or _milestone_branch(cfg)
    fetched = _git(root, 'fetch', '-q', '--prune', 'origin')
    if fetched.returncode:
        raise Red(f'git fetch origin failed: {fetched.stderr.strip()}')
    refs = _refs(root)
    lanes = {s: f'origin/{prefix}{s}' for s in req.slugs}
    present = [s for s in req.slugs if f'{REMOTE}{prefix}{s}' in refs]
    batch = req.batch or _default_batch(refs)
    branch = BATCH[len(HEADS):] + batch
    exists = HEADS + branch in refs
    _refuse_unknown(cfg, prefix, [s for s in req.slugs if s not in present])
    if not present and not exists:
        print(f'{TAG} nothing to integrate — every lane is already integrated')
        return EXIT_OK
    base_ref = base if HEADS + base in refs else f'origin/{base}'
    if f'refs/remotes/{base_ref}' not in refs and HEADS + base not in refs:
        raise Usage(f'base {base!r} is neither a local nor an origin branch')
    primary, held = _worktrees(root)
    checkout = held.get(base)
    _refuse_dirty(checkout)
    wt = held.get(branch) or _add_worktree(root, primary, branch, batch,
                                           base_ref, exists)
    print(f'{TAG} batch {branch} in {wt}, base {base}')
    _refuse_foreign(wt, base_ref, req.slugs, prefix)
    if not _ancestor(wt, base_ref, 'HEAD'):
        _merge(wt, base_ref, f'integrate {batch}: merge {base_ref}', base_ref)
    for slug in present:
        if _ancestor(wt, lanes[slug], 'HEAD'):
            print(f'{TAG} {slug}: already in the batch')
            continue
        _merge(wt, lanes[slug], f'integrate {batch}: merge {prefix}{slug}', slug)
        print(f'{TAG} {slug}: merged {lanes[slug]}')
        if per_merge and _make(wt, PER_MERGE, per_merge):
            raise Red(f'lane {slug}: per_merge failed after its merge. Nothing '
                      f'closed; fix the lane, push, rerun')
    if _ancestor(wt, 'HEAD', base_ref):
        print(f'{TAG} the batch is already in {base} — proof not run again')
    else:
        out = _make(wt, PROOF, proof, record=True)
        if out:
            named = [s for s in present if any(p in out for p in _lines(
                wt, 'diff', '--name-only', f'{base_ref}...{lanes[s]}'))]
            raise Red(f'proof failed; lanes to look at: '
                      f'{", ".join(named or present)}'
                      f'{"" if named else " (the output names no lane file)"}. '
                      f'Nothing closed; {wt} and every branch kept')
    _close(wt, batch, req.slugs)
    _advance(root, checkout, base, branch)
    failed = (0 if req.keep_lanes else
              _remove_lanes(root, primary, held, base, prefix, req.slugs))
    if _lines(wt, 'status', '--porcelain', '--untracked-files=no'):
        print(f'{TAG} {wt} has uncommitted changes — kept, with {branch}')
    else:
        _git(root, 'worktree', 'remove', '--force', str(wt))
        _git(root, 'branch', '-D', branch)
        print(f'{TAG} batch worktree and {branch} removed')
    print(f'next: git push origin {base}')
    return EXIT_RED if failed else EXIT_OK


# --- the base and the batch ---------------------------------------------------
def _milestone_branch(cfg: vocabulary.PmConfig) -> str:
    found = []
    for milestone in inventory.milestones(cfg):
        status = milestone.field(vocabulary.FIELD_STATUS) or ''
        branch = frontmatter.unquote(milestone.field('branch') or '').strip()
        if branch and vocabulary.category_of(
                cfg, vocabulary.GRAIN_MILESTONE, status) == vocabulary.IN_PROGRESS:
            found.append(f'{milestone.gid} ({branch})')
    if len(found) != 1:
        raise Usage(f'{len(found)} in-progress milestone(s) declare a branch: '
                    f'{", ".join(found) or "none"} — pass --base <branch>')
    return found[0].rsplit(' (', 1)[1][:-1]


def _refuse_unknown(cfg: vocabulary.PmConfig, prefix: str,
                    missing: list[str]) -> None:
    """A lane with no origin branch is integrated only when its story is in
    a `done`-category state; anything else is a typo or an unpushed lane, and
    a green line for it would be a false PASS (rule 4)."""
    unknown = []
    for slug in missing:
        sid = inventory.mint_id(vocabulary.GRAIN_STORY, slug)
        story = inventory.story_grain(cfg, sid)
        status = story.field(vocabulary.FIELD_STATUS) if story else ''
        if story and vocabulary.category_of(
                cfg, vocabulary.GRAIN_STORY, status) == vocabulary.DONE_CATEGORY:
            print(f'{TAG} {slug}: no origin/{prefix}{slug} and {sid} is '
                  f'{status} — already integrated')
        else:
            unknown.append(f'no origin/{prefix}{slug} and {sid} is not done')
    if unknown:
        raise Red('; '.join(unknown) + ' — typo, or not pushed?')


def _default_batch(refs: dict[str, str]) -> str:
    """The newest dated batch a red run left (a green run deletes its own),
    else the first one today."""
    dated = sorted((m.group(1), int(m.group(2))) for ref in refs
                   if ref.startswith(BATCH)
                   and (m := DATED.fullmatch(ref[len(BATCH):])))
    if dated:
        print(f'{TAG} resuming batch {dated[-1][0]}-{dated[-1][1]}')
        return f'{dated[-1][0]}-{dated[-1][1]}'
    return datetime.now(timezone.utc).strftime('%Y-%m-%d') + '-1'


def _add_worktree(root: Path, primary: Path, branch: str, batch: str,
                  base_ref: str, exists: bool) -> Path:
    """Placed where `agent-worktree.sh` places a lane: `<primary>.worktrees/`."""
    path = Path(f'{primary}.worktrees') / f'integrate-{batch}'
    argv = (['worktree', 'add', '-q', str(path), branch] if exists else
            ['worktree', 'add', '-q', '--no-track', '-b', branch, str(path),
             base_ref])
    made = _git(root, *argv)
    if made.returncode:
        raise Red(f'git worktree add failed: {made.stderr.strip()}')
    return path


def _refuse_foreign(wt: Path, base_ref: str, slugs: tuple[str, ...],
                    prefix: str) -> None:
    said = re.compile(r'^integrate \S+: merge ' + re.escape(prefix) + r'(\S+)$')
    merged = {m.group(1) for s in _lines(wt, 'log', '--merges', '--format=%s',
                                         f'{base_ref}..HEAD')
              if (m := said.fullmatch(s))}
    foreign = sorted(merged - set(slugs))
    if foreign:
        raise Red(f'this batch already holds {", ".join(foreign)}, which this '
                  f'command does not name — name the same lanes, or pass --batch')


def _merge(wt: Path, ref: str, message: str, lane: str) -> None:
    done = _git(wt, 'merge', '-q', '--no-ff', '--no-edit', '-m', message, ref)
    if done.returncode:
        _git(wt, 'merge', '--abort')
        _tail(done.stdout + done.stderr)
        raise Red(f'lane {lane}: {ref} conflicts with the batch, and the merge '
                  f'was aborted. Merge the base into the lane, push, rerun')


def _make(wt: Path, key: str, targets: tuple[str, ...],
          record: bool = False) -> str:
    """Run `make <targets>` in the batch, streamed to the terminal and teed
    into the worktree's git dir for lane naming: '' when green, else the output."""
    gitdir = _lines(wt, 'rev-parse', '--absolute-git-dir')
    if not gitdir:
        raise Red(f'{wt} has no git dir')
    log = Path(gitdir[0]) / f'integrate-{key}.log'
    print(f'{TAG} {key}: make {" ".join(targets)} …', flush=True)
    sys.stderr.flush()
    started = time.monotonic()
    code = spawn.run(['bash', '-c', 'set -o pipefail; make "$@" 2>&1 | tee "$0"',
                      str(log), *targets], cwd=wt).returncode
    ms = int((time.monotonic() - started) * 1000)
    verdict = 'PASS' if code == 0 else 'FAIL'
    print(f'{TAG} {key}: make {" ".join(targets)} — {verdict} in '
          f'{ms / 1000:.1f} s', flush=True)
    if record:
        # The one gate-row writer: `pm ledger record --gate`.
        from agentic_sdlc.repo.pm import cli as pm_cli
        pm_cli.main(['ledger', 'record', '--gate', GATE, '--verdict', verdict,
                     '--duration-ms', str(ms)])
    if code == 0:
        return ''
    try:
        out = log.read_text(encoding='utf-8', errors='replace')
    except OSError:
        out = ''
    return out or f'exit {code}'


# --- green --------------------------------------------------------------------
@contextmanager
def _inside(path: Path):
    """cwd in `path` and its config loaded, both restored after: a pm verb
    reads the tree it stands in."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield vocabulary.reload()
    finally:
        os.chdir(previous)
        vocabulary.reload()


def _close(wt: Path, batch: str, slugs: tuple[str, ...]) -> None:
    """Each lane's story to its kind's first `done` state by `pm story`, then
    one commit in the batch. A slug with no story is named."""
    from agentic_sdlc.repo.pm import cli as pm_cli
    before = set(_dirty(wt))
    with _inside(wt) as cfg:
        done = vocabulary.flow_of(cfg, vocabulary.GRAIN_STORY).by_category.get(
            vocabulary.DONE_CATEGORY, ('',))[0]
        ids = []
        for slug in slugs:
            sid = inventory.mint_id(vocabulary.GRAIN_STORY, slug)
            if inventory.story_grain(cfg, sid) is None:
                print(f'{TAG} no story {sid}: merged, nothing closed')
            else:
                ids.append(sid)
        if ids and pm_cli.main([vocabulary.GRAIN_STORY, done, *ids]):
            raise Red(f'`pm story {done} {" ".join(ids)}` failed; the base '
                      f'did not move')
    paths = [p for p in _dirty(wt) if p not in before]
    if paths:
        _git(wt, 'add', '--', *paths)
        made = _git(wt, 'commit', '-q', '-m',
                    f'integrate {batch}: {done} {" ".join(ids)}', '--', *paths)
        if made.returncode:
            raise Red(f'the commit of the closed stories failed: '
                      f'{made.stderr.strip()}')


def _advance(root: Path, checkout: Path | None, base: str, branch: str) -> None:
    refs = _refs(root)
    new, old = refs[HEADS + branch], refs.get(HEADS + base, '')
    if old == new:
        print(f'{TAG} {base} is already at {new[:12]}')
        return
    if old and not _ancestor(root, old, new):
        raise Red(f'{base} moved past the batch; rerun to merge it in')
    if checkout is not None:
        _refuse_dirty(checkout)
        moved = _git(checkout, 'merge', '--ff-only', '-q', branch)
    else:
        moved = _git(root, 'update-ref', HEADS + base, new, old)
    if moved.returncode:
        raise Red(f'{base} could not fast-forward to {branch}: '
                  f'{moved.stderr.strip()}')
    print(f'{TAG} {base}: {old[:12] or "(new)"} -> {new[:12]} (fast-forward)')


def _remove_lanes(root: Path, primary: Path, held: dict[str, Path], base: str,
                  prefix: str, slugs: tuple[str, ...]) -> int:
    """Each lane's worktree (by `agent-worktree.sh done` when the lane sits
    where it places lanes), local branch and origin branch. A branch with
    commits the base lacks is kept. Returns how many lanes were kept."""
    from agentic_sdlc.repo import install
    script = root / dict(install.PLANS['install-hooks'])['agent-worktree.sh']
    placed = {Path(f'{primary}.worktrees'), primary / '.claude' / 'worktrees'}
    refs, kept = _refs(root), 0
    for slug in slugs:
        branch, lane = prefix + slug, held.get(prefix + slug)
        why = ''
        if HEADS + branch in refs and not _ancestor(root, branch, base):
            why = f'{branch} has commits that {base} does not'
        elif lane is not None:
            argv = (['bash', str(script), WORKTREE_DONE, slug]
                    if script.is_file() and lane.name == slug
                    and lane.parent in placed
                    else ['git', 'worktree', 'remove', str(lane)])
            gone = spawn.run(argv, cwd=root, capture_output=True, text=True)
            why = '' if gone.returncode == 0 else (
                f'worktree {lane}: {(gone.stderr or gone.stdout).strip()}')
        if not why:
            _git(root, 'branch', '-q', '-D', branch)
            if REMOTE + branch in refs:
                pushed = _git(root, 'push', '-q', 'origin', '--delete', branch)
                why = pushed.stderr.strip() if pushed.returncode else ''
        if why:
            print(f'{TAG} lane {slug}: kept — {why}')
            kept += 1
        else:
            print(f'{TAG} lane {slug}: worktree, branch and origin branch removed')
    return kept


# --- git ----------------------------------------------------------------------
def _git(cwd: Path, *args: str) -> spawn.CompletedProcess:
    return spawn.run(['git', *args], cwd=cwd, capture_output=True, text=True)


def _lines(cwd: Path, *args: str) -> list[str]:
    done = _git(cwd, *args)
    return ([ln for ln in done.stdout.splitlines() if ln.strip()]
            if done.returncode == 0 else [])


def _refs(cwd: Path) -> dict[str, str]:
    """{full ref name: commit} for every branch, local and remote."""
    return {name: sha for sha, _, name in (
        ln.partition(' ') for ln in _lines(
            cwd, 'for-each-ref', '--format=%(objectname) %(refname)',
            'refs/heads/', 'refs/remotes/'))}


def _ancestor(cwd: Path, older: str, newer: str) -> bool:
    return _git(cwd, 'merge-base', '--is-ancestor', older, newer).returncode == 0


def _dirty(cwd: Path) -> list[str]:
    raw = _git(cwd, 'status', '--porcelain', '-z', '--untracked-files=all').stdout
    return [entry[3:] for entry in raw.split('\0') if len(entry) > 3]


def _worktrees(root: Path) -> tuple[Path, dict[str, Path]]:
    """(the primary checkout, {branch: path}). Git lists the primary first from
    every linked worktree; `agent-worktree.sh` reads its MAIN_ROOT the same way."""
    paths: list[Path] = []
    held: dict[str, Path] = {}
    for line in _lines(root, 'worktree', 'list', '--porcelain'):
        if line.startswith('worktree '):
            paths.append(Path(line[len('worktree '):]))
        elif line.startswith('branch ' + HEADS) and paths:
            held[line[len('branch ' + HEADS):]] = paths[-1]
    return (paths[0] if paths else root), held


def _refuse_dirty(checkout: Path | None) -> None:
    if checkout is None:
        return
    dirty = _lines(checkout, 'status', '--porcelain', '--untracked-files=no')
    if dirty:
        raise Red(f'{checkout} has uncommitted changes: '
                  f'{", ".join(line[3:] for line in dirty[:8])} — commit or '
                  f'stash them, then rerun')


def _tail(out: str) -> None:
    for line in out.splitlines()[-TAIL_LINES:]:
        print(f'  {line}', file=sys.stderr)
