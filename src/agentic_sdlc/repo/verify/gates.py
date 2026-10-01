"""gates.py — a static gate reused by the hash of what it reads (#98).

`check all` runs every gate in its roster. A gate whose module DECLARES its
inputs — an `inputs()` function returning `Inputs` — is keyed on exactly those:
the content of the paths it reads, the NAMES git lists when it resolves a path
anywhere in the tree, and the facts no file carries (a binary's path and
version, `core.hooksPath`). Every key also carries the TOOL: this package's
version and a digest of its own source, so a new rule re-runs its gate over a
tree whose files did not move. No HEAD: a commit that moves no input is not a
new input.

What a gate asks the filesystem beyond those — `exists()` on a path git does
not list, because git ignores it, it is outside the tree or it was deleted —
goes through `probe.py`, and the PASS row files each probe with what it saw. A
reuse asks every one again; one that sees something else runs the gate (review
F1). A gate that walks a directory reads what git ignores there too, so every
ignored file under a gate's scope is an input as well.

A PASS is recorded against that key in the tree's local ledger — a `verify`
row, the rung cache's own record (`cache.py`), with rung `check` and target
`check:<gate>`, carrying EVERYTHING the gate printed — and the next `check all`
over the same key prints that output again byte for byte, its PASS line
followed by `; reused — green at <ts> on inputs <short>`, and runs nothing. A
reused gate reads as a fresh one but for that clause: its WARN, READY and
census lines are the run's findings too (rule 11). A FAIL is never recorded, so it is never reused. A gate that
declares nothing (`repo-hygiene`, `budget`) always runs; so does a gate whose
inputs come to 0 files, which then fails its own census as it always did;
`check <gate>` alone always runs. CI starts with no local ledger, so it runs
every gate.

A run that reused anything measured less than the gate costs. Makefile.devkit's
`check` names a file in `GDK_GATE_UNMEASURED`; `check all` creates it when it
reused anything AND every gate passed, and the gate library then files no
`gate` cost row for that run. A reused green `make check` therefore moves no
digest `verify --milestone` grades; a FAIL is always filed (review F3).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

from agentic_sdlc.repo.verify import cache, probe

# The `rung` a static gate's row carries, and the targets it is filed under:
# no make target spells a `:`, so none of these can match a rung's row.
RUNG = 'check'
GATE_KEY = 'check:'
EXTRA_KEY = 'extra:'

# Every line this module prints on its own behalf.
TAG = '[check:cache]'

# The file Makefile.devkit's `check` names; created when this run reused.
UNMEASURED_ENV = 'GDK_GATE_UNMEASURED'

REUSED = '; reused — green at {ts} on inputs {short}'

MS_PER_SECOND = 1000


@dataclass(frozen=True)
class Inputs:
    """What one static gate reads. `scope`: repo-relative path prefixes, each
    covering itself and everything under it. `also`: files read whether or not
    git lists them (a gitignored settings file). `names`: the gate resolves a
    path ANYWHERE, so the name of every listed path is an input. `facts`:
    what no file carries."""

    scope: tuple[str, ...]
    also: tuple[str, ...] = ()
    names: bool = False
    facts: tuple[str, ...] = ()


def prefix(path: str) -> str:
    """One input entry as a prefix: no leading `./` and no trailing slash."""
    path = path.strip()
    while path.startswith('./'):
        path = path[2:]
    return path.rstrip('/')


def pm_scope(cfg) -> tuple[str, ...]:
    """Every directory and file a PM config names, for a gate reading the PM
    tree: the roadmap, each kind's own pool, the ledgers, the reviews, the
    templates and the version file."""
    return tuple(path for path in (
        cfg.roadmap_dir, cfg.milestone_dir_key, cfg.feature_dir_key,
        cfg.story_dir_key, cfg.bug_dir_key, cfg.ledger_dir_key,
        cfg.review_dir, cfg.template_dir, cfg.version_file) if path)


@lru_cache(maxsize=1)
def tool() -> str:
    """This package, as a key: its version and the digest of every file it
    ships. A rule changed in a working tree re-runs its gate with the version
    unchanged."""
    import agentic_sdlc
    from agentic_sdlc.core import walk
    from agentic_sdlc.core.walk import Kind
    package = Path(agentic_sdlc.__file__).resolve().parent
    digest = hashlib.new(cache.STATE_ALGO)
    digest.update(agentic_sdlc.__version__.encode('utf-8'))
    for path in walk.descendants(package, Kind.FILE):
        rel = path.relative_to(package).as_posix()
        if '__pycache__' in rel.split('/') or rel.endswith('.pyc'):
            continue
        try:
            body = path.read_bytes()
        except OSError:
            body = cache.MARK_ABSENT
        digest.update(rel.encode('utf-8') + cache.SEP
                      + hashlib.new(cache.STATE_ALGO, body).digest())
    return f'{agentic_sdlc.__version__}+{digest.hexdigest()}'


class _Tee(io.TextIOBase):
    """stdout as it was, and a copy — a gate prints its verdict line itself."""

    def __init__(self, out):
        self.out = out
        self.text = io.StringIO()

    def write(self, chunk: str) -> int:
        self.out.write(chunk)
        self.text.write(chunk)
        return len(chunk)

    def flush(self) -> None:
        self.out.flush()


def _pass_at(lines: list[str], name: str) -> int:
    """The index of the LAST `[check:<name>] PASS` line a gate printed, or
    -1. `lines` keep their endings."""
    head = f'[check:{name}] PASS'
    found = -1
    for index, line in enumerate(lines):
        if line.startswith(head):
            found = index
    return found


def _replayed(said: str, name: str, clause: str) -> str:
    """What a reused gate prints: every byte the recorded run printed, its
    PASS line ending in `clause`; '' when that output holds no PASS line."""
    lines = said.splitlines(keepends=True)
    at = _pass_at(lines, name)
    if at < 0:
        return ''
    line = lines[at]
    body = line.rstrip('\r\n')
    lines[at] = body + clause + line[len(body):]
    return ''.join(lines)


class Session:
    """One `check all`: one listing, one read of each path, one read of the
    record. `defect` says why nothing is reused or recorded, when so.
    `lister` is git's listing, asked again after each run."""

    def __init__(self, root: Path,
                 lister: Callable[[Path], bytes | None] = cache.listing,
                 ignored: Callable[[Path, tuple[str, ...]], bytes | None]
                 = cache.ignored_listing):
        self.root = root
        self.lister = lister
        self.ignored = ignored
        self.listed = lister(root)
        self.hidden: dict = {}
        self.memo: dict = {}
        self.found: dict = {}
        self.graded: cache.Graded | None = None
        self.reused: list[str] = []
        self.defect = ''
        if self.listed is None:
            self.defect = ('git could not list this tree, so no gate can be '
                           'keyed on its inputs')
            return
        where = cache.ledger_file(root)
        if where is None or not where.parent.is_dir():
            self.defect = ('this tree has no PM config and roadmap directory, '
                           'so there is nowhere to record a gate\'s PASS')
            return
        raw = cache.telemetry(root)
        if raw is None:
            self.defect = ('the tree\'s ledgers could not be read, so no '
                           'recorded PASS can be found')
            return
        self.found = cache.verdicts(raw)
        self.graded = cache.graded_of(raw)

    # --- the state ------------------------------------------------------------
    def state(self, inputs: Inputs, fresh: bool = False
              ) -> tuple[cache.State | None, str]:
        """The state of `inputs`; `fresh` re-lists and re-reads every path,
        for the check AFTER a run."""
        listed = self.lister(self.root) if fresh else self.listed
        if listed is None:
            return None, 'git could not list this tree'
        scope = tuple(sorted({prefix(p) for p in inputs.scope if prefix(p)}))
        also = tuple(sorted({prefix(p) for p in inputs.also if prefix(p)}))
        hidden = self.hidden.get(scope) if not fresh else None
        if hidden is None:
            hidden = self.ignored(self.root, scope)
            if hidden is None:
                return None, 'git could not list the ignored files here'
            if not fresh:
                self.hidden[scope] = hidden
        salt = (tool().encode('utf-8'),
                *(fact.encode('utf-8', 'surrogateescape')
                  for fact in inputs.facts))
        return cache.inputs_state(self.root, listed, scope, also=also,
                                  names=inputs.names, salt=salt,
                                  memo=None if fresh else self.memo,
                                  ignored=hidden)

    def recorded(self, key: str, state: cache.State) -> cache.Verdict | None:
        found = self.found.get((key, state.digest))
        return found if found is not None and found.verdict == cache.PASS \
            else None

    def probes_hold(self, name: str, found: cache.Verdict) -> bool:
        """Does every path the recorded run probed see what it saw? A row
        that filed no probes cannot say, so it is not reused."""
        if found.probed is None:
            return False
        moved = probe.holds(self.root, found.probed)
        if moved:
            print(f'{TAG} check:{name}: {moved} is not what the recorded PASS '
                  f'saw there — it runs')
        return not moved

    def record(self, key: str, inputs: Inputs, state: cache.State,
               elapsed_ms: int, said: str = '',
               probed: list[list[str]] | None = None) -> None:
        """File a PASS, against a state RE-READ after the run: a tree edited
        while the gate read it was never wholly read by it."""
        after, _ = self.state(inputs, fresh=True)
        if after is None or after.digest != state.digest:
            print(f'{TAG} the inputs of {key} MOVED while it ran, so this PASS '
                  f'is not recorded')
            return
        defect = cache.record(self.root, RUNG, key, state, cache.PASS, 0,
                              elapsed_ms, None, said=said, graded=self.graded,
                              probed=probed)
        if defect:
            print(f'{TAG} {defect}')

    # --- a gate ---------------------------------------------------------------
    def gate(self, name: str, module, run: Callable[[], int]) -> int:
        """One gate: its recorded PASS when its inputs have not moved, else
        the gate, recorded when it prints a PASS line and exits 0."""
        inputs = self._inputs(module)
        if inputs is None or self.defect:
            return run()
        state, _ = self.state(inputs)
        if state is None:
            # 0 files, or a submodule git could not state: the gate runs and
            # says what it found, as it did before any of this.
            return run()
        key = GATE_KEY + name
        found = self.recorded(key, state)
        said = _replayed(found.said, name, REUSED.format(
            ts=found.ts, short=state.short())) if found is not None else ''
        if said and self.probes_hold(name, found):
            sys.stdout.write(said)
            self.reused.append(name)
            return 0
        tee = _Tee(sys.stdout)
        started = time.monotonic()
        with contextlib.redirect_stdout(tee), probe.recording() as seen:
            code = run()
        elapsed = int((time.monotonic() - started) * MS_PER_SECOND)
        # The WHOLE output, not the PASS line: a reuse that dropped the WARN
        # lines would make every run after the first one quiet (rule 11).
        said = tee.text.getvalue()
        if code == 0 and _pass_at(said.splitlines(), name) >= 0:
            self.record(key, inputs, state, elapsed, said,
                        probe.filed(self.root, seen))
        return code

    @staticmethod
    def _inputs(module) -> Inputs | None:
        declare = getattr(module, 'inputs', None)
        if declare is None:
            return None
        try:
            got = declare()
        except (Exception, SystemExit):  # noqa: BLE001 - the gate says why
            # A config the gate cannot read is the GATE's to report, by name.
            return None
        return got if isinstance(got, Inputs) else None

    # --- a `[gates] extra` target ---------------------------------------------
    def extra(self, target: str, paths: Sequence[str],
              run: Callable[[], tuple[int, str]]) -> int:
        """One `[gates] extra` target with `[gates.inputs]` declared: its
        recorded PASS while those paths are byte-identical, else the target —
        `run` gives back its exit code and the last line it printed."""
        inputs = Inputs(scope=tuple(paths))
        state, why = (None, self.defect) if self.defect \
            else self.state(inputs)
        if state is None:
            print(f'{TAG} {target}: {why} — it runs')
            return run()[0]
        key = EXTRA_KEY + target
        found = self.recorded(key, state)
        if found is not None:
            said = found.said or f'[{target}] PASS'
            print(said + REUSED.format(ts=found.ts, short=state.short()))
            return 0
        started = time.monotonic()
        code, said = run()
        if code == 0:
            self.record(key, inputs, state,
                        int((time.monotonic() - started) * MS_PER_SECOND),
                        said or f'[{target}] PASS')
        return code

    # --- the close ------------------------------------------------------------
    def close(self, asked: int, worst: int = 0) -> None:
        """Say what was reused, and tell the gate library this run measured
        less than the gate costs — only when `worst`, the run's exit, is 0:
        a run that FAILed is the verdict the ledger must carry (review F3)."""
        if self.defect:
            print(f'{TAG} {self.defect}' + ('' if self.defect == NO_CACHE
                                            else ' — every gate runs'))
            return
        reused = len(self.reused)
        if not reused:
            return
        print(f'{TAG} reused {reused} of {asked} gate(s) whose inputs are '
              f'byte-identical to a recorded PASS ({" ".join(self.reused)}) '
              f'— `check <gate>` alone runs one whatever is recorded')
        if worst == 0:
            mark_unmeasured()


def mark_unmeasured() -> None:
    """Create the file `GDK_GATE_UNMEASURED` names, if one is named: the gate
    library files no cost row for a run that reused (#98)."""
    target = os.environ.get(UNMEASURED_ENV, '')
    if not target:
        return
    from agentic_sdlc.core import apply
    try:
        apply.write(Path(target), 'reused\n')
    except OSError:
        # A cost row too many is a measurement, never a gate failure.
        pass


NO_CACHE = ('--no-cache — every gate runs, and no PASS is read or recorded')


def run_all(root: Path, roster: Sequence[str], module_of,
            dispatch: Callable[[str], int], reuse: bool = True,
            session: Session | None = None) -> int:
    """`check all`: every gate in `roster`, each reused when its inputs have
    not moved; the worst exit any gate gave. `reuse=False` (`--no-cache`)
    runs every gate and reads and writes no record. `session` is one over
    git's listing unless given."""
    if not reuse:
        session = Session(root, lambda _: None)
        session.defect = NO_CACHE
    elif session is None:
        session = Session(root)
    worst = 0
    for name in roster:
        module = module_of(name)
        worst = max(worst, session.gate(name, module,
                                        lambda n=name: dispatch(n)))
        print()
    session.close(len(roster), worst)
    return worst

