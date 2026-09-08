"""Is this branch's work anywhere but this disk? Answered by READING REFS.

0.5.0 ran five hours and thirty-four commits with nothing on the remote and
nothing in the conveyor looked.

**NOTHING HERE SPAWNS (hard rule 2)**, so `census` may call it on every `pm`
write; D3 on `ms-the-rule-reaches-the-work` records what that cost. Local refs
only, never a fetch — `check repo-hygiene` owns the network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_GIT_DIR = '.git'
_PACKED = 'packed-refs'
_HEAD = 'HEAD'
_REF_PREFIX = 'ref: '
_HEADS = 'refs/heads/'
_REMOTES = 'refs/remotes/'


@dataclass(frozen=True)
class Unpushed:
    """`published` — a tracking ref names it; `in_sync` — one points where
    HEAD does. Pushed-then-advanced is not never-pushed."""

    branch: str
    published: bool
    in_sync: bool

    def __bool__(self) -> bool:
        """Truthy when there is something to SAY: work only on this disk."""
        return not self.in_sync


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return ''


def _git_dir(root: Path) -> Path | None:
    """`root/.git`, or None. A worktree's is a FILE naming the real dir."""
    candidate = root / _GIT_DIR
    if candidate.is_dir():
        return candidate
    text = _read(candidate).strip()
    if text.startswith('gitdir: '):
        pointed = Path(text[len('gitdir: '):].strip())
        resolved = pointed if pointed.is_absolute() else (root / pointed)
        return resolved if resolved.is_dir() else None
    return None


def _packed(git: Path) -> dict[str, str]:
    """{refname: sha} from `packed-refs`: a ref `git gc` moved lives ONLY
    here, and a reader of `refs/` alone calls a pushed branch unpushed."""
    out: dict[str, str] = {}
    for line in _packed_lines(git):
        if line.startswith('#') or line.startswith('^'):
            continue
        sha, _, name = line.partition(' ')
        if name:
            out[name.strip()] = sha.strip()
    return out


def _packed_lines(git: Path) -> list[str]:
    return [ln for ln in _read(git / _PACKED).splitlines() if ln.strip()]


def _sha(git: Path, refname: str, packed: dict[str, str]) -> str:
    loose = _read(git / refname).strip()
    return loose or packed.get(refname, '')


_REMOTE_SECTION = re.compile(r'^\[remote\s+"([^"]+)"\]', re.MULTILINE)


def remote_names(root: Path) -> list[str]:
    """READ, not enumerated: each ref is probed by path (PRIMITIVE 1)."""
    git = _git_dir(root)
    return [] if git is None else _REMOTE_SECTION.findall(_read(git / 'config'))


def has_a_remote(root: Path) -> bool:
    """No remote configured is QUIET, not broken — `[emit]`'s posture."""
    return bool(remote_names(root))


def read(root: Path) -> Unpushed | None:
    """None when the question does not apply: no `.git`, no remote, detached."""
    git = _git_dir(root)
    if git is None or not remote_names(root):
        return None
    head = _read(git / _HEAD).strip()
    if not head.startswith(_REF_PREFIX):
        return None  # detached: there is no branch to be behind
    refname = head[len(_REF_PREFIX):].strip()
    if not refname.startswith(_HEADS):
        return None
    branch = refname[len(_HEADS):]
    packed = _packed(git)
    local = _sha(git, refname, packed)
    if not local:
        return None  # an unborn branch has no commits to lose
    tracking = _tracking(git, remote_names(root), branch, packed)
    return Unpushed(branch=branch, published=bool(tracking),
                    in_sync=local in tracking)


def _tracking(git: Path, names: list[str], branch: str,
              packed: dict[str, str]) -> set[str]:
    """Every tracking sha for `branch`: one probe per remote, both homes."""
    found = set()
    for name in names:
        refname = f'{_REMOTES}{name}/{branch}'
        sha = _sha(git, refname, packed)
        if sha:
            found.add(sha)
    return found


def push_command(branch: str) -> str:
    """The operator runs it. THE TOOL NEVER DOES (rule 2)."""
    return f'git push -u origin {branch}'
