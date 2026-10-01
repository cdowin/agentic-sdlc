"""check repo-hygiene — close-time git-state guard; runs a network `git fetch --prune`.

HARD: working tree clean outside `[pm] roadmap_dir`; no stashes; no dangling worktrees; no
merged-but-undeleted branches (local + remote, protected and archive/* exempt). WARN: unmerged
branches; dirt under `[pm] roadmap_dir`, as one line naming the commit to run (the belts'
`tree-clean` and `committed` exclude the same paths, through the same helper).

devkit.toml: [repo_hygiene] mainline = "origin/main"
             protected = "^(main|staging|archive/.*)$"
"""
from __future__ import annotations

import re
import sys

from agentic_sdlc.core import spawn
from agentic_sdlc.core.project import git_lines, repo_root
from agentic_sdlc.core.config import config_section, pattern, relpath, text


def read_config() -> tuple[str, 're.Pattern[str]']:
    """`[repo_hygiene]`'s two keys, refused before `run()` prints; `adopt` reads them here too."""
    cfg = config_section('repo_hygiene')
    return (
        text(cfg, 'repo_hygiene', 'mainline', 'origin/main'),
        re.compile(pattern(cfg, 'repo_hygiene', 'protected',
                           r'^(main|staging|archive/.*)$')),
    )


def roadmap_dir() -> str:
    """`[pm] roadmap_dir`, read alone: this gate runs in a repo with no flow
    declared, so it cannot ask for the whole `[pm]` config."""
    return relpath(config_section('pm'), 'pm', 'roadmap_dir', 'pm/roadmap')


def dirt_lines(dirty: list[str], roadmap: str) -> tuple[list[str], int]:
    """CHECK 1's lines and its hard count. Dirt under the roadmap is the PM
    tree's own writes: one WARN line with the commit to run, never a failure.
    Any other dirt fails, listed."""
    from agentic_sdlc.repo.belts import split_roadmap

    outside, inside, prefix = split_roadmap(dirty, roadmap)
    lines = []
    if inside:
        lines.append(f'  WARN  {len(inside)} uncommitted path(s) under {prefix} '
                     f'— commit them: git add {roadmap} && git commit -m "pm: …"')
    if outside:
        lines.append('  DIRTY  uncommitted/untracked changes present:')
        lines.extend(f'    {ln}' for ln in outside)
    return lines, 1 if outside else 0


def run() -> int:
    mainline, protected = read_config()
    roadmap = roadmap_dir()
    hard = 0
    warn = 0

    print('[check:repo-hygiene] refreshing remote refs (git fetch --prune)…')
    fetch = spawn.run(['git', 'fetch', '--prune', 'origin', '--quiet'],
                      cwd=repo_root(), capture_output=True)
    if fetch.returncode != 0:
        print('  WARN: git fetch failed — the merged-remote-branch check may be stale')

    print('[check:repo-hygiene] CHECK 1 — working tree clean')
    dirty = git_lines('status', '--porcelain')
    found, dirt = dirt_lines(dirty, roadmap)
    if found:
        print('\n'.join(found))
    hard += dirt

    print('[check:repo-hygiene] CHECK 2 — no stashes')
    stashes = git_lines('stash', 'list')
    if stashes:
        print('  STASHES  present (a close carries none):')
        print('\n'.join(f'    {ln}' for ln in stashes))
        hard += 1

    print('[check:repo-hygiene] CHECK 3 — no dangling worktrees')
    # `git worktree prune -n -v` reports on stderr; the porcelain listing is on stdout.
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
    # An unresolvable mainline makes every `--merged` query return [], which is exit 2, not clean.
    if not git_lines('rev-parse', '--verify', '--quiet', f'{mainline}^{{commit}}'):
        print(f"  ERROR  mainline '{mainline}' does not resolve — CHECK 4 cannot run", file=sys.stderr)
        print("[check:repo-hygiene] CONFIG ERROR — fix [repo_hygiene] mainline in devkit.toml")
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
