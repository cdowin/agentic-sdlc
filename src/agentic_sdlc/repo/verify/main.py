"""verify — one rung of the ladder, the make target `[verify]` names for it.

    agentic-sdlc verify --story        # the inner loop, e.g. `make unit`
    agentic-sdlc verify --feature      # the close of a feature, e.g. `make test`
    agentic-sdlc verify --milestone    # the close, e.g. `make milestone`
    agentic-sdlc verify --plan         # print all three, run NOTHING
    agentic-sdlc verify --check        # hold the three targets to the Makefile
    agentic-sdlc verify --story --no-cache   # re-run, whatever is recorded

Each rung runs the make target `[verify] <rung>` names — three lines, one
shape, and the Makefile stays the authority on what a target RUNS (D3). A
rung the section does not declare is exit 2 naming the key, never a pass and
never the rung above. `--plan` prints each rung's measured cost from the
ledger's `gate` rows, or the word `unknown` — never a guess — plus an `unrun`
line joining `[checks] all` to those rows, because a roster gate that never
filed a cost row reads exactly like one that passes. `--check` reads the
Makefile as text and reports a rung naming a target it does not declare. An
absent `[verify]` section is exit 2 for every flag.

A RUNG RECORDS ITS VERDICT against the tree state it ran on — HEAD plus a
digest over every file git lists, tracked and untracked — and a later run whose
tree is byte-identical prints `[verify:cache] REUSED …` with that run's age,
census and cost and exits with its code, instead of running the target. One
byte anywhere re-runs it, and so does `--no-cache`, a rung flag refused beside
`--plan` or `--check`. Ignored files and the ledger rows a run files about
ITSELF are not in the digest — a state covering what a gate writes while it
runs could never repeat — so the rows `check budget` grades are DIGESTED into
the row instead, and a reuse over a ledger whose graded rows moved runs the
target and says so (`verify/cache.py`).

Exit: 0 pass | 1 the target failed or `--check` found drift | 2 usage or
config. A target's own exit 2 is reported as 1, with its code beside it.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from agentic_sdlc.core import makefile, spawn
from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import vehicle
from agentic_sdlc.repo.pm import ledger
from agentic_sdlc.repo.verify import cache, rules
from agentic_sdlc.repo.verify.rules import (EXIT_CONFIG, FEATURE, MILESTONE,
                                            RUNGS, STORY, Ladder, rung_target)

# A rung's cost is RECORDED in milliseconds, the ledger's unit.
MS_PER_SECOND = 1000

EXIT_OK = 0
EXIT_FINDINGS = 1

RUNG_BLURB = {STORY: 'the edit', FEATURE: 'the feature', MILESTONE: 'the close'}

# `--check` reads the Makefile as text, never `make -n` (rule 2).
MAKEFILE = makefile.MAKEFILE

USAGE = """usage: agentic-sdlc verify (--story|--feature|--milestone|--plan|--check)
                          [--no-cache]

  --story        run the `[verify] story` rung
  --feature      run the `[verify] feature` rung
  --milestone    run the `[verify] milestone` rung
  --plan         print all three rungs and their measured cost; runs nothing
  --check        hold each rung's make target to the Makefile
  --no-cache     with a rung: run the target even when this exact tree state
                 already has a recorded verdict

Exactly one mode. A rung reuses a verdict recorded against a byte-identical
tree, says so, and exits with the recorded code. Exit: 0 pass | 1 findings or
a failed target | 2 usage or config."""

MODES = ('plan', 'check', *RUNGS)

# A rung flag, not a mode: it changes what a rung does with the record, and
# `--plan`/`--check` run no rung at all.
NO_CACHE = '--no-cache'


@dataclass(frozen=True)
class Cost:
    """One rung's MEASURED cost, from a ledger `gate` row. Never derived."""

    duration_ms: int
    census: int | None
    verdict: str

    def render(self) -> str:
        extra = [f'census {self.census}'] if self.census is not None else []
        extra.append(self.verdict)
        return f'{self.duration_ms} ms ({", ".join(extra)})'


# `[verify]` or None, passed in by `cli.py` — the one module allowed to read
# raw config — so this module stays a pure function of it.
SectionReader = Callable[[], 'dict | None']


def main(argv: Sequence[str], section: SectionReader) -> int:
    """The verb; `section` is called only after argv parses, so `--help` and
    a usage error never touch devkit.toml."""
    if any(flag in ('-h', '--help') for flag in argv):
        print(__doc__.strip())
        return EXIT_OK
    try:
        mode, no_cache = _parse(list(argv))
    except ValueError as err:
        return _usage_error(str(err))

    try:
        ladder = _ladder(section)
    except ConfigError as err:
        print(f'agentic-sdlc verify: {err}', file=sys.stderr)
        return EXIT_CONFIG

    root = repo_root()
    if mode == 'plan':
        return _plan(ladder, root)
    if mode == 'check':
        return _check(ladder, root)
    return _run_rung(ladder, root, mode, no_cache=no_cache)


# --- argv ---------------------------------------------------------------------
def _parse(argv: list[str]) -> tuple[str, bool]:
    """Exactly one mode, and nothing else but `--no-cache`."""
    modes: list[str] = []
    no_cache = False
    for token in argv:
        if token == NO_CACHE:
            no_cache = True
        elif token.startswith('--') and token[2:] in MODES:
            modes.append(token[2:])
        elif token.startswith('-'):
            raise ValueError(
                f'unknown flag {token!r} — a flag this verb does not know is '
                f'refused rather than ignored: a caller that thinks it asked '
                f'for something and got a different run has been lied to')
        else:
            raise ValueError(
                f'unexpected argument {token!r} — this verb takes no '
                f'positional arguments')
    if not modes:
        raise ValueError(
            'no mode given. There is no default: defaulting to --story would '
            'run a target nobody asked for')
    if len(modes) > 1:
        raise ValueError(
            f'{" ".join(sorted(set(f"--{m}" for m in modes)))} — exactly one '
            f'mode, and which one it should have been is not a thing this '
            f'verb may pick')
    if no_cache and modes[0] not in RUNGS:
        raise ValueError(
            f'{NO_CACHE} says what a RUNG does with a recorded verdict, and '
            f'--{modes[0]} runs no rung — a flag this run parsed and then '
            f'dropped is a caller who thinks it asked for something')
    return modes[0], no_cache


def _usage_error(why: str) -> int:
    print(f'agentic-sdlc verify: {why}', file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return EXIT_CONFIG


def _ladder(section: SectionReader) -> Ladder:
    got = section()
    if got is None:
        raise ConfigError(
            'devkit.toml declares no [verify] section, so nothing here knows '
            'what proves a change. That is a config error and not a pass: a '
            'verb that printed nothing and exited 0 would report success for '
            'work it never checked. Declare [verify] story, feature and '
            'milestone, each `make <target>`')
    return rules.read(got)


# --- running ------------------------------------------------------------------
def _run(command: str, root: Path) -> int:
    """One rung's target through a shell in the repo root — `rules.py`
    already refused every spelling that is not `make <target>`."""
    print(f'  $ {command}', flush=True)
    return spawn.run(command, shell=True, cwd=str(root),
                     check=False).returncode


def _run_rung(ladder: Ladder, root: Path, name: str,
              no_cache: bool = False) -> int:
    """One rung: the recorded verdict when the tree has not moved, else the
    target — and either way this run's verdict is recorded."""
    command = ladder.rung(name)
    if command is None:
        print(f'agentic-sdlc verify: [verify] declares no {name} rung, so '
              f'--{name} has nothing to run. Skipping it would report success '
              f'for a rung nobody ran; running the rung above it would charge '
              f'a {name} close for a wider gate. Declare '
              f'`{name} = "make <target>"`', file=sys.stderr)
        return EXIT_CONFIG
    print(f'verify --{name}: {command}')
    target = rung_target(command)
    # BEFORE the run: the state a verdict is about is the tree the target read,
    # not the one it left behind.
    state, defect = cache.tree_state(root)
    if state is None:
        print(f'{cache.CACHE_TAG} no state for this tree ({defect}), so no '
              f'verdict is read or recorded — `{command}` runs')
    elif no_cache:
        print(f'{cache.CACHE_TAG} {NO_CACHE} — `{command}` runs whatever is '
              f'recorded; this run replaces it')
    else:
        found, graded = cache.recorded(root, target, state.digest)
        if found is not None and graded is not None \
                and found.graded == graded.digest:
            return _reuse(found, command, state, graded)
        if found is not None:
            # The state matches and the reuse is refused anyway: what moved is
            # the one input no state can carry, and saying so is the difference
            # between a guard and a cache that looks broken.
            print(cache.stale_line(found, graded, command))
    started = time.monotonic()
    # Where this run's own rows begin, so the census a reused verdict quotes is
    # the GATE's rather than one this verb invented (rule 4).
    mark = cache.ledger_size(root)
    code = _run(command, root)
    elapsed = int((time.monotonic() - started) * MS_PER_SECOND)
    if state is not None:
        _record(root, name, target, state, code, elapsed, mark)
    if code != 0:
        print(f'agentic-sdlc verify: FAILED (exit {code}) — {command}',
              file=sys.stderr)
        return EXIT_FINDINGS
    return EXIT_OK


def _reuse(found: cache.Verdict, command: str, state: cache.State,
           graded: cache.Graded) -> int:
    """The recorded verdict, its provenance and its own exit code. The FAILED
    line keeps the shape a fresh failure prints — one grep either way — and the
    cache lines above it say which run this was."""
    for line in cache.reuse_lines(found, command, state, graded):
        print(line)
    if found.verdict == cache.PASS:
        return EXIT_OK
    print(f'agentic-sdlc verify: FAILED (exit {found.exit_code}) — {command}',
          file=sys.stderr)
    return EXIT_FINDINGS


def _record(root: Path, name: str, target: str, state: cache.State, code: int,
            elapsed: int, mark: int) -> None:
    """File what this run decided, against a state RE-READ after the target —
    a tree edited during a 90 s suite was never wholly read by it, and a
    verdict keyed to a state the target only half saw is rule 4's first sin
    with a record behind it. Disagreement records NOTHING, and says so; a
    record that could not be written is SAID and never fails the run."""
    after, defect = cache.tree_state(root)
    if after is None or after.digest != state.digest:
        moved = after.short() if after is not None else f'none ({defect})'
        print(f'{cache.CACHE_TAG} the tree MOVED while `{target}` ran (state '
              f'{state.short()} -> {moved}), so this run proved a tree no '
              f'later run can be keyed on and no verdict is recorded',
              file=sys.stderr)
        return
    verdict = cache.PASS if code == 0 else cache.FAIL
    defect = cache.record(root, name, target, state, verdict, code, elapsed,
                          cache.census_since(root, target, mark))
    if defect:
        print(f'{cache.CACHE_TAG} {defect}', file=sys.stderr)


# --- the ledger, and the ratio ------------------------------------------------
def gate_costs(root: Path) -> tuple[dict[str, Cost], str]:
    """(target -> its most recent `gate` row, the ledger paths as a string).
    Anything unreadable yields no costs and the plan says `unknown`, because
    an invented cost gets quoted."""
    import json

    try:
        from agentic_sdlc.repo.pm import ledger, vocabulary
        cfg = vocabulary.load()
        # The TREE's ledgers, not a milestone's: a `gate` row names no grain,
        # so 0.4.0/D3 filed it at `<roadmap>/ledger.jsonl`, and #48 files every
        # new one in the gitignored `ledger.local.jsonl` beside it. Read in
        # that order, so the LAST row per target is the newest. That also
        # survives `pm retire`, which used to take a milestone's gate history
        # away with its directory and leave the next milestone printing
        # `unknown` for a week.
        paths = ledger.telemetry_paths(cfg.roadmap)
        raw = ''.join(path.read_text(encoding='utf-8') + '\n'
                      for path in paths if path.is_file())
    except Exception:  # noqa: BLE001 - every failure means the same: unknown
        return {}, ''
    costs: dict[str, Cost] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if (not isinstance(row, dict)
                or row.get(ledger.KIND_FIELD) != ledger.KIND_GATE):
            continue
        name, duration = row.get('gate'), row.get('duration_ms')
        if not isinstance(name, str) or not isinstance(duration, int) \
                or isinstance(duration, bool):
            continue
        census = row.get('census')
        costs[name] = Cost(duration_ms=duration,
                           census=census if isinstance(census, int) else None,
                           verdict=str(row.get('verdict', '?')))
    return costs, ' and '.join(str(path) for path in paths)


def _cost_of(command: str, costs: dict[str, Cost]) -> Cost | None:
    return costs.get(rung_target(command))


# --- --plan -------------------------------------------------------------------
def _plan(ladder: Ladder, root: Path) -> int:
    """All three rungs, their targets and their MEASURED costs. Runs nothing."""
    costs, ledger_at = gate_costs(root)
    print('[verify] plan — three rungs, narrow to wide')
    print()
    measured: dict[str, int | None] = {}
    for name in RUNGS:
        command = ladder.rung(name)
        if command is None:
            print(f'  {name:<10} (not configured) — --{name} exits 2')
            measured[name] = None
            continue
        cost = _cost_of(command, costs)
        print(f'  {name:<10} {command:<24}  '
              f'{cost.render() if cost else "unknown"}   [{RUNG_BLURB[name]}]')
        measured[name] = cost.duration_ms if cost else None
    print()
    print(f'  {_ratio(measured[STORY], measured[MILESTONE], ledger_at)}')
    for line in _roster_without_rows(root, costs):
        print(f'  {line}')
    return EXIT_OK


def _roster_without_rows(root: Path, costs: dict) -> list[str]:
    """Gates named in `[checks] all` that have produced no cost row here.

    `[checks] all` names gates and the ledger records what each gate COST, and
    nothing had ever joined them — so a roster entry that never runs looks
    exactly like one that passes. That is a failure mode this project has
    already paid for: the toolkit is two pinned packages and each refuses a
    gate name it does not know, so a name in the roster is not proof of a gate.

    The other direction of `verify --plan`'s own rule. It prints `unknown`
    rather than guessing a cost; this says which gates have never given it one.
    A REPORT — no exit code moves (rule 9), and a fresh checkout legitimately
    has none of them, which it SAYS rather than passing over in silence.
    """
    try:
        # `core.config` and not `cli.all_roster`: this package's layers point
        # DOWNWARD only, and `verify` reaching up into the router would be the
        # import the boundary gate exists to refuse. The roster is a config
        # value; validating the NAMES is the router's job and not this line's.
        from agentic_sdlc.core.config import config_section, str_tuple
        roster = str_tuple(config_section('checks'), 'checks', 'all', ())
    except Exception as err:  # noqa: BLE001 - reported, never swallowed
        # A roster `check all` refuses at exit 2 read here as a clean plan.
        return [f'unrun     [checks] all could not be read ({err}), so no '
                f'gate was joined to a cost row — '
                f'`{vehicle.command("check", "all")}` is the verb that '
                f'refuses this by name']
    if not roster:
        return []
    missing = [name for name in roster if name not in costs]
    if not missing:
        return []
    # `[checks] all` names GATES and a `gate` row names a MAKE TARGET — two
    # namespaces (`gates_extra.py` says so) — so a tree running its gates
    # inside a composed `check` target has rows for the composition and none
    # per gate. Reporting each of them THERE would be a nag; reporting nothing
    # is worse, because it reads exactly like a roster fully measured. So the
    # all-missing case says which it is, in one line, and the partial case
    # names the gates: that join is the one that means something.
    if len(missing) == len(roster):
        return [f'unrun     no gate in [checks] all has filed a cost row here '
                f'({" ".join(roster)}) — a gate name and a `gate` row\'s make '
                f'target are two namespaces, so this tree most likely measures '
                f'composed targets; the join says nothing either way']
    return [f'unrun     {len(missing)} of {len(roster)} gate(s) in [checks] '
            f'all have filed no cost row here while the others have: '
            f'{" ".join(missing)} — a roster entry that never runs reads '
            f'exactly like one that passes']


def _ratio(story_ms: int | None, milestone_ms: int | None,
           ledger_at: str) -> str:
    """narrow-vs-wide, or an honest silence naming what is missing."""
    if story_ms and milestone_ms:
        return (f'ratio      {milestone_ms / story_ms:.0f}x — the '
                f'{MILESTONE} rung costs {milestone_ms} ms against the '
                f'{STORY} rung\'s {story_ms} ms')
    where = ledger_at or 'the building milestone\'s ledger.jsonl'
    return (f'ratio      unknown — no `gate` rows with these targets in '
            f'{where}. A fabricated ratio is worse than no ratio, because it '
            f'gets quoted')


# --- --check ------------------------------------------------------------------
def make_targets(root: Path) -> tuple[frozenset[str], str]:
    """(every target the root Makefile and its includes declare, the file
    read), through `core.makefile`."""
    path = root / MAKEFILE
    if not path.is_file():
        return frozenset(), ''
    return makefile.targets(root), str(path)


def _check(ladder: Ladder, root: Path) -> int:
    """Every declared rung's target held to the Makefile; findings are exit 1.
    The census prints on the pass too, so a reader can tell whether the gate
    looked at anything."""
    targets, found = make_targets(root)
    findings: list[str] = []
    if not targets:
        findings.append(
            f'no {MAKEFILE} at the repo root, so no rung naming a make target '
            f'can be resolved — a ladder nobody can resolve is a ladder nobody '
            f'has run')
    declared = [(name, ladder.rung(name)) for name in RUNGS
                if ladder.rung(name) is not None]
    for name, command in declared:
        target = rung_target(command)
        if targets and target not in targets:
            findings.append(
                f'[verify] {name}: {command!r} names make target {target!r}, '
                f'which {found} does not declare')
    for finding in findings:
        print(f'  DRIFT  {finding}')
    census = (f'{len(declared)} of {len(RUNGS)} rung(s) declared, held to '
              f'{len(targets)} target(s) in {found or MAKEFILE}')
    if findings:
        print(f'[verify:check] FAIL — {len(findings)} finding(s); {census}')
        return EXIT_FINDINGS
    print(f'[verify:check] PASS — {census}')
    return EXIT_OK
