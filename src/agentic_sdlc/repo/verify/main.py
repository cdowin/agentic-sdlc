"""verify — one rung of the ladder, the make target `[verify]` names for it.

    agentic-sdlc verify --story        # the inner loop, e.g. `make unit`
    agentic-sdlc verify --feature      # the close of a feature, e.g. `make test`
    agentic-sdlc verify --milestone    # the close, e.g. `make milestone`
    agentic-sdlc verify --plan         # print all three, run NOTHING
    agentic-sdlc verify --check        # hold the three targets to the Makefile

Each rung runs the make target `[verify] <rung>` names — three lines, one
shape, and the Makefile stays the authority on what a target RUNS (D3). A
rung the section does not declare is exit 2 naming the key, never a pass and
never the rung above. `--plan` prints each rung's measured cost from the
ledger's `gate` rows, or the word `unknown` — never a guess. `--check` reads
the Makefile as text and reports a rung naming a target it does not declare.
An absent `[verify]` section is exit 2 for every flag.

Exit: 0 pass | 1 the target failed or `--check` found drift | 2 usage or
config. A target's own exit 2 is reported as 1, with its code beside it.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from agentic_sdlc.core import makefile
from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo.verify import rules
from agentic_sdlc.repo.verify.rules import (EXIT_CONFIG, FEATURE, MILESTONE,
                                            RUNGS, STORY, Ladder, rung_target)

EXIT_OK = 0
EXIT_FINDINGS = 1

RUNG_BLURB = {STORY: 'the edit', FEATURE: 'the feature', MILESTONE: 'the close'}

# `--check` reads the Makefile as text, never `make -n` (rule 2).
MAKEFILE = makefile.MAKEFILE
MAKE_PROGRAM = 'make'

USAGE = """usage: agentic-sdlc verify (--story|--feature|--milestone|--plan|--check)

  --story        run the `[verify] story` rung
  --feature      run the `[verify] feature` rung
  --milestone    run the `[verify] milestone` rung
  --plan         print all three rungs and their measured cost; runs nothing
  --check        hold each rung's make target to the Makefile

Exactly one mode. Exit: 0 pass | 1 findings or a failed target | 2 usage or
config."""

MODES = ('plan', 'check', *RUNGS)


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
        mode = _parse(list(argv))
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
    return _run_rung(ladder, root, mode)


# --- argv ---------------------------------------------------------------------
def _parse(argv: list[str]) -> str:
    """Exactly one mode, and nothing else."""
    modes: list[str] = []
    for token in argv:
        if token.startswith('--') and token[2:] in MODES:
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
    return modes[0]


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
    return subprocess.run(command, shell=True, cwd=str(root),
                          check=False).returncode


def _run_rung(ladder: Ladder, root: Path, name: str) -> int:
    command = ladder.rung(name)
    if command is None:
        print(f'agentic-sdlc verify: [verify] declares no {name} rung, so '
              f'--{name} has nothing to run. Skipping it would report success '
              f'for a rung nobody ran; running the rung above it would charge '
              f'a {name} close for a wider gate. Declare '
              f'`{name} = "make <target>"`', file=sys.stderr)
        return EXIT_CONFIG
    print(f'verify --{name}: {command}')
    code = _run(command, root)
    if code != 0:
        print(f'agentic-sdlc verify: FAILED (exit {code}) — {command}',
              file=sys.stderr)
        return EXIT_FINDINGS
    return EXIT_OK


# --- the ledger, and the ratio ------------------------------------------------
def gate_costs(root: Path) -> tuple[dict[str, Cost], str]:
    """(target -> its most recent `gate` row, the ledger path as a string).
    Anything unreadable yields no costs and the plan says `unknown`, because
    an invented cost gets quoted."""
    import json

    try:
        from agentic_sdlc.repo.pm import ledger, model
        cfg = model.load()
        mdir, _why = model.release_ledger_dir(cfg)
        if mdir is None:
            return {}, ''
        path = ledger.ledger_path(mdir)
        raw = path.read_text(encoding='utf-8')
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
        if not isinstance(row, dict) or row.get('kind') != 'gate':
            continue
        name, duration = row.get('gate'), row.get('duration_ms')
        if not isinstance(name, str) or not isinstance(duration, int) \
                or isinstance(duration, bool):
            continue
        census = row.get('census')
        costs[name] = Cost(duration_ms=duration,
                           census=census if isinstance(census, int) else None,
                           verdict=str(row.get('verdict', '?')))
    return costs, str(path)


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
    return EXIT_OK


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
