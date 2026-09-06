"""The one place this package mutates a filesystem.

A `Plan` is an explicit list of `Step`s; `decide()` names every `Blocked` step before
anything runs, and `apply()` refuses whole or reports exactly which steps landed.
`tests/test_boundaries.py` forbids the raw mutators elsewhere in `src/`.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Act(Enum):
    """What one step does. Closed: a plan holds nothing else."""

    MKDIR = 'create directory'
    OVERWRITE = 'overwrite'
    RENAME = 'rename'
    DELETE_TREE = 'delete directory tree'
    DELETE_FILE = 'delete file'


class Obstruction(Enum):
    """Why a step cannot run; every one is answerable by looking before a write."""

    EXISTS = 'already exists'
    IS_A_DIRECTORY = 'is a directory'
    IS_A_SYMLINK = 'is a symlink'
    NOT_WRITABLE = 'is not writable'
    PARENT_NOT_WRITABLE = 'its directory is not writable'
    PARENT_IS_A_FILE = 'its parent is a file, not a directory'
    MISSING_SOURCE = 'does not exist'
    NOT_A_DIRECTORY = 'is not a directory'
    NOT_A_REGULAR_FILE = 'is not a regular file'


class Symlink(Enum):
    """What a step does at a symlinked destination: REFUSE (a scaffolder must not
    write outside its grain) or FOLLOW (an installer respects a deliberate link)."""

    REFUSE = 'refuse'
    FOLLOW = 'follow'


@dataclass(frozen=True)
class Step:
    """One intended operation, fully named at plan time.

    `newline=''` writes the bytes given so a CRLF template stays CRLF; `None` translates.
    `executable` is part of the step because a file with the wrong mode is not written.
    """

    act: Act
    dest: Path
    body: str | None = None
    src: Path | None = None
    newline: str | None = ''
    label: str = ''
    symlink: Symlink = Symlink.REFUSE
    executable: bool = False

    def describe(self) -> str:
        if self.act is Act.RENAME:
            return f'{self.act.value} {self.src} -> {self.dest}'
        return f'{self.act.value} {self.dest}'


@dataclass(frozen=True)
class Blocked:
    step: Step
    path: Path
    reason: Obstruction

    def describe(self) -> str:
        return f'{self.path} {self.reason.value}'


@dataclass(frozen=True)
class Applied:
    """What `Plan.apply` did: `blocked` means nothing ran; `failed` names the step
    that broke mid-apply, and `landed` then says how far it got."""

    landed: tuple[Step, ...] = ()
    blocked: tuple[Blocked, ...] = ()
    failed: Step | None = None
    error: str = ''



@dataclass
class Plan:
    """An explicit list of intended operations. Decide, then apply."""

    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> 'Plan':
        self.steps.append(step)
        return self

    def overwrite(self, dest: Path, body: str, *, newline: str | None = '',
                  label: str = '', symlink: Symlink = Symlink.REFUSE,
                  executable: bool = False) -> 'Plan':
        return self.add(Step(Act.OVERWRITE, dest, body=body, newline=newline,
                             label=label, symlink=symlink,
                             executable=executable))

    # Named `make_dir`/`move` because the boundary test cannot tell `plan.mkdir()` from `Path.mkdir()`.
    def make_dir(self, dest: Path, *, label: str = '') -> 'Plan':
        return self.add(Step(Act.MKDIR, dest, label=label))

    def move(self, src: Path, dest: Path, *, label: str = '') -> 'Plan':
        return self.add(Step(Act.RENAME, dest, src=src, label=label))

    def delete_tree(self, dest: Path, *, label: str = '') -> 'Plan':
        return self.add(Step(Act.DELETE_TREE, dest, label=label))

    def delete_file(self, dest: Path, *, label: str = '') -> 'Plan':
        return self.add(Step(Act.DELETE_FILE, dest, label=label))

    # --- phase one ------------------------------------------------------------
    def decide(self) -> list[Blocked]:
        """Every step that cannot run, read against the filesystem plus the plan's own MKDIRs."""
        out: list[Blocked] = []
        planned_dirs = {s.dest for s in self.steps if s.act is Act.MKDIR}
        for step in self.steps:
            out.extend(self._obstructions(step, planned_dirs))
        return out

    def _obstructions(self, step: Step, planned_dirs: set[Path]) -> list[Blocked]:
        out: list[Blocked] = []
        dest = step.dest
        if step.act in (Act.OVERWRITE, Act.MKDIR, Act.RENAME):
            out.extend(self._parent_obstructions(step, dest, planned_dirs))
        if step.act is Act.OVERWRITE:
            if step.symlink is Symlink.REFUSE and dest.is_symlink():
                out.append(Blocked(step, dest, Obstruction.IS_A_SYMLINK))
            elif dest.exists() and not dest.is_file():
                out.append(Blocked(step, dest, Obstruction.IS_A_DIRECTORY
                                   if dest.is_dir()
                                   else Obstruction.NOT_A_REGULAR_FILE))
            elif dest.is_file() and not os.access(dest, os.W_OK):
                out.append(Blocked(step, dest, Obstruction.NOT_WRITABLE))
        elif step.act is Act.MKDIR:
            if dest.exists() and not dest.is_dir():
                out.append(Blocked(step, dest, Obstruction.NOT_A_DIRECTORY))
        elif step.act is Act.RENAME:
            src = step.src
            if src is None or not (src.exists() or src.is_symlink()):
                out.append(Blocked(step, src or dest, Obstruction.MISSING_SOURCE))
            elif src != dest and dest.exists() and not _case_respelling(src, dest):
                out.append(Blocked(step, dest, Obstruction.EXISTS))
            elif src is not None and not os.access(src.parent, os.W_OK):
                # A rename writes the directory, not the file.
                out.append(Blocked(step, src.parent, Obstruction.PARENT_NOT_WRITABLE))
        elif step.act is Act.DELETE_TREE:
            if dest.exists() and not dest.is_dir():
                out.append(Blocked(step, dest, Obstruction.NOT_A_DIRECTORY))
        elif step.act is Act.DELETE_FILE:
            if dest.exists() and not dest.is_file():
                out.append(Blocked(step, dest, Obstruction.NOT_A_REGULAR_FILE))
            elif dest.is_file() and not os.access(dest.parent, os.W_OK):
                # An unlink writes the directory, like a rename does.
                out.append(Blocked(step, dest.parent,
                                   Obstruction.PARENT_NOT_WRITABLE))
        return out

    def _parent_obstructions(self, step: Step, dest: Path,
                             planned_dirs: set[Path]) -> list[Blocked]:
        """Whether the destination's directory can be created; walks up to the first
        existing ancestor, as `mkdir(parents=True)` does."""
        parent = dest.parent
        if parent in planned_dirs or parent == dest:
            return []
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if not parent.is_dir():
            return [Blocked(step, parent, Obstruction.PARENT_IS_A_FILE)]
        if not os.access(parent, os.W_OK):
            return [Blocked(step, parent, Obstruction.PARENT_NOT_WRITABLE)]
        return []

    # --- phase two ------------------------------------------------------------
    def apply(self, *, decide: bool = True) -> Applied:
        """Run the plan, refusing whole when `decide` finds anything; `decide=False` is
        for a caller that already refused in its own vocabulary, and still reports."""
        if decide:
            blocked = self.decide()
            if blocked:
                return Applied(blocked=tuple(blocked))
        landed: list[Step] = []
        for step in self.steps:
            try:
                _run(step)
            except OSError as err:
                return Applied(tuple(landed), failed=step,
                               error=str(err.strerror or err))
            landed.append(step)
        return Applied(tuple(landed))


def _case_respelling(src: Path, dest: Path) -> bool:
    """True when `dest` is the same file as `src` under a case-variant name, which is
    the one `dest.exists()` collision that is not one."""
    if src.name.lower() != dest.name.lower():
        return False
    try:
        return os.path.samefile(src, dest)
    except OSError:
        return False


def _make_executable(dest: Path) -> None:
    """`chmod +x`: the execute bit joins every class that can already read, never a flat 0o755."""
    mode = os.stat(dest).st_mode
    os.chmod(dest, mode | ((mode & 0o444) >> 2))


def _run(step: Step) -> None:
    """The only place a byte moves. Every branch is one `Act`."""
    if step.act is Act.MKDIR:
        step.dest.mkdir(parents=True, exist_ok=True)
    elif step.act is Act.OVERWRITE:
        step.dest.parent.mkdir(parents=True, exist_ok=True)
        with step.dest.open('w', encoding='utf-8', newline=step.newline) as fh:
            fh.write(step.body or '')
        if step.executable:
            _make_executable(step.dest)
    elif step.act is Act.RENAME:
        assert step.src is not None
        step.src.rename(step.dest)
    elif step.act is Act.DELETE_TREE:
        # Already gone is the idempotent end state; any other failure surfaces as `failed`.
        if step.dest.exists() or step.dest.is_symlink():
            shutil.rmtree(step.dest)
    elif step.act is Act.DELETE_FILE:
        step.dest.unlink(missing_ok=True)


# --- the one-step conveniences ------------------------------------------------

def write(path: Path, text: str, *, newline: str | None = '') -> Applied:
    """Write one file, creating its directory; raw newlines by default."""
    return Plan().overwrite(path, text, newline=newline).apply(decide=False)


def write_translated(path: Path, text: str) -> Applied:
    """`Path.write_text` semantics — `\\n` translated on write."""
    return write(path, text, newline=None)


def make_dir(path: Path) -> Applied:
    return Plan().make_dir(path).apply(decide=False)


def remove_file(path: Path) -> Applied:
    return Plan().delete_file(path).apply(decide=False)


def raise_on_error(applied: Applied) -> None:
    """Re-raise a mid-apply failure as the `OSError` older callers' handlers expect."""
    if applied.failed is not None:
        raise OSError(applied.error)
