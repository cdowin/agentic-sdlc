"""check repo-hygiene — close-time git-state guard.

A milestone/release does not close clean if the repo carries leftover git
state — WIP stashes, dangling worktrees, dead (merged-but-undeleted)
branches, or an unclean tree. That cruft is invisible to content/test gates
yet accumulates until someone hand-sweeps it; this makes the swept-clean
end-state a failing gate.

CLOSE-TIME ONLY — it runs a network `git fetch --prune` for the remote-branch
check, so wire it into your close gate, not your per-change gate.

CHECK 1 (HARD): working tree clean.       CHECK 2 (HARD): no stashes.
CHECK 3 (HARD): no dangling worktrees.    CHECK 4 (HARD): no merged-but-
undeleted branches (local + remote), protected lines + archive/* exempt.
REPORT  (WARN): unmerged branches needing a human keep/delete call.

devkit.toml: [repo_hygiene] mainline = "origin/main"
             protected = "^(main|staging|archive/.*)$"
"""
from __future__ import annotations

import re
import subprocess
import sys

from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.core.config import config_section, pattern, text


def read_config() -> tuple[str, 're.Pattern[str]']:
    """`[repo_hygiene]`'s two keys, read and refused without touching the tree.

    PURE, and that is the whole reason it exists as a function. These two keys
    used to be read inline at the top of `run()`, which then fetches from the
    remote and walks the tree — so `adopt`'s `config-updated`, whose entire job
    is asking whether every section this version still READS parses under this
    version, had nowhere to call and spelled the two keys a second time
    (A1, and `steps._read_repo_hygiene`'s own docstring named it as the one
    second list in the package). One reader, called from both, and the second
    list is gone rather than pinned by a test.

    A malformed value raises `ConfigError` here, before `run()` prints its
    first line — which is also the honest order: a config error is exit 2 and
    it should not arrive after a gate has already announced itself.
    """
    cfg = config_section('repo_hygiene')
    return (
        text(cfg, 'repo_hygiene', 'mainline', 'origin/main'),
        re.compile(pattern(cfg, 'repo_hygiene', 'protected',
                           r'^(main|staging|archive/.*)$')),
    )


def run() -> int:
    mainline, protected = read_config()
    hard = 0
    warn = 0

    print('[check:repo-hygiene] refreshing remote refs (git fetch --prune)…')
    fetch = subprocess.run(['git', 'fetch', '--prune', 'origin', '--quiet'],
                           cwd=repo_root(), capture_output=True)
    if fetch.returncode != 0:
        print('  WARN: git fetch failed — the merged-remote-branch check may be stale')

    print('[check:repo-hygiene] CHECK 1 — working tree clean')
    dirty = git_lines('status', '--porcelain')
    if dirty:
        print('  DIRTY  uncommitted/untracked changes present:')
        print('\n'.join(f'    {ln}' for ln in dirty))
        hard += 1

    print('[check:repo-hygiene] CHECK 2 — no stashes')
    stashes = git_lines('stash', 'list')
    if stashes:
        print('  STASHES  present (a close carries none):')
        print('\n'.join(f'    {ln}' for ln in stashes))
        hard += 1

    print('[check:repo-hygiene] CHECK 3 — no dangling worktrees')
    # `git worktree prune -n -v` reports on STDERR (a silent false-PASS trap);
    # the porcelain listing marks prunable entries on stdout — parse that.
    dangling = []
    current = ''
    for ln in git_lines('worktree', 'list', '--porcelain'):
        if ln.startswith('worktree '):
            current = ln.removeprefix('worktree ')
        elif ln == 'prunable' or ln.startswith('prunable '):
            reason = ln.removeprefix('prunable').strip() or 'prunable'
            dangling.append(f'{current}  ({reason})')
    if dangling:
        print('  WORKTREES  a prune would remove:')
        print('\n'.join(f'    {ln}' for ln in dangling))
        hard += 1

    def branch_names(*args: str) -> list[str]:
        names = []
        for ln in git_lines('branch', *args):
            name = ln.lstrip('*+ ').strip()
            if name and 'HEAD' not in name:
                names.append(name)
        return names

    print(f'[check:repo-hygiene] CHECK 4 — no merged-but-undeleted branches (merged into {mainline})')
    # An unresolvable mainline would make every `--merged` query return [],
    # silently disabling this check — that's a config error, not a clean tree.
    if not git_lines('rev-parse', '--verify', '--quiet', f'{mainline}^{{commit}}'):
        print(f"  ERROR  mainline '{mainline}' does not resolve — CHECK 4 cannot run", file=sys.stderr)
        print(f"[check:repo-hygiene] CONFIG ERROR — fix [repo_hygiene] mainline in devkit.toml")
        return 2
    for b in branch_names('--merged', mainline):
        if protected.search(b):
            continue
        print(f'  MERGED-LOCAL   {b} is merged into {mainline} but not deleted')
        hard += 1
    for b in branch_names('-r', '--merged', mainline):
        b = b.removeprefix('origin/')
        if protected.search(b):
            continue
        print(f'  MERGED-REMOTE  origin/{b} is merged into {mainline} but not deleted')
        hard += 1

    print('[check:repo-hygiene] REPORT — unmerged branches needing a keep/delete decision (warn only)')
    for b in branch_names('--no-merged', mainline):
        if protected.search(b):
            continue
        print(f'  UNMERGED  {b} (keep -> rename archive/*, or delete)')
        warn += 1

    print()
    if hard:
        print(f'[check:repo-hygiene] FAIL — {hard} repo-state violation(s); {warn} unmerged branch(es) to review')
        return 1
    print(f'[check:repo-hygiene] PASS — clean tree, no stashes, no dangling worktrees, '
          f'no dead branches ({warn} unmerged branch(es) to review)')
    return 0
