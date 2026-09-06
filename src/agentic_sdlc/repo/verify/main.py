"""verify — what proves THIS edit, at the altitude you are working at.

    agentic-sdlc verify --story [--ref <rev>] [--to <rev>] [--ignore <path>]...
    agentic-sdlc verify --feature               # the range rung
    agentic-sdlc verify --milestone             # the close
    agentic-sdlc verify --plan  [--ref <rev>]   # print all three, run NOTHING
    agentic-sdlc verify --check                 # validate [verify] vs the tree

`--story` (alias `--changed`) runs the `[[verify.narrow]]` commands the changed
paths select, deduplicated, in declaration order; a path matching no rule is
named and the `milestone` rung runs instead. `--feature` and `--milestone` run
the make target `[verify]` names. `--plan` prints each rung's measured cost
from the ledger's `gate` rows, or the word `unknown` — never a guess. `--ignore`
drops a path the caller wrote during this run; `--to` closes the range at a
commit. A `[verify]` section that is absent is exit 2 for every flag.

Exit: 0 pass | 1 a command failed or `--check` found drift | 2 usage, config,
or git. A command's own exit 2 is reported as 1, with its code beside it.
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
from agentic_sdlc.repo.verify import declares, rules, select
from agentic_sdlc.repo.verify.rules import (EXIT_CONFIG, FEATURE, FORWARD,
                                            MILESTONE, REVERSE, Rule, RuleSet,
                                            rung_target)
from agentic_sdlc.repo.verify.select import SelectionError

EXIT_OK = 0
EXIT_FINDINGS = 1

GIT = 'git'
GIT_MISSING = (f'{GIT} is not on PATH, so `verify` cannot read what changed — '
               f'and "no changes, nothing to verify" would be a pass over an '
               f'unread diff')
NOT_A_REPO = ('this is not a git repository, so there is no diff to read — '
              'the story rung is a function of the changed paths and there '
              'are none to compute from')

# `--changed` is the alias a dispatch may already quote.
STORY = 'story'
CHANGED = 'changed'

# Ladder order, narrow to wide — printed and run in this order.
LADDER = (STORY, FEATURE, MILESTONE)
RUNG_BLURB = {STORY: 'the edit', FEATURE: 'the range', MILESTONE: 'the close'}

# `--check` reads the Makefile as text, never `make -n` (rule 2).
MAKEFILE = makefile.MAKEFILE
MAKE_PROGRAM = 'make'

# A rev is one argv element to git; the refusals are `report.check_rev`'s.
REV_MAX = 256

USAGE = """usage: agentic-sdlc verify (--story|--feature|--milestone|--plan|--check)
                          [--ref <rev>]

  --story [--ref <rev>] [--to <rev>] [--ignore <path>]...
                          run what proves the changed paths (alias: --changed).
                          --ignore drops a path the CALLER wrote during this
                          run, so a belt's own writes do not read as the
                          operator's edit. It is not a claim that the path
                          needs no verification — that is the project's, made
                          by declaring a [[verify.narrow]] rule for it.
  --feature               run the `[verify] feature` rung
  --milestone             run the `[verify] milestone` rung
  --plan  [--ref <rev>]   print all three rungs and their measured cost; runs
                          nothing at all
  --check                 validate `[verify]` against the tree

Exactly one mode. Exit: 0 pass | 1 findings or a failed command | 2 usage,
config, or git."""


class GitError(Exception):
    """A git invocation that failed, carrying git's OWN message where it has one."""


@dataclass(frozen=True)
class Args:
    mode: str
    ref: str | None = None
    ignore: tuple[str, ...] = ()
    # The far end of the range, so a late close proves the story's edits and
    # not what followed them.
    to: str | None = None


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
        args = _parse(list(argv))
    except ValueError as err:
        return _usage_error(str(err))

    try:
        ruleset = _ruleset(section)
    except ConfigError as err:
        print(f'agentic-sdlc verify: {err}', file=sys.stderr)
        return EXIT_CONFIG

    root = repo_root()
    try:
        return _dispatch(args, ruleset, root)
    except GitError as err:
        print(f'agentic-sdlc verify: {err}', file=sys.stderr)
        return EXIT_CONFIG
    except SelectionError as err:
        # Hostile tree contents: no plan, so exit 2 like a malformed section.
        print(f'agentic-sdlc verify: {err}', file=sys.stderr)
        return EXIT_CONFIG


def _dispatch(args: Args, ruleset: RuleSet, root: Path) -> int:
    if args.mode == 'plan':
        return _plan(ruleset, root, args.ref)
    if args.mode == 'check':
        return _check(ruleset, root)
    if args.mode == STORY:
        return _run_story(ruleset, root, args.ref, args.ignore, args.to)
    return _run_rung(ruleset, root, args.mode)


# --- argv ---------------------------------------------------------------------
def _parse(argv: list[str]) -> Args:
    """One mode, an optional `--ref` for the two modes that read a diff."""
    modes: list[str] = []
    ref: str | None = None
    to: str | None = None
    ignore: list[str] = []
    seen_ref = False
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ('--story', f'--{CHANGED}'):
            modes.append(STORY)
        elif token in (f'--{FEATURE}', f'--{MILESTONE}'):
            modes.append(token[2:])
        elif token == '--plan':
            modes.append('plan')
        elif token == '--check':
            modes.append('check')
        elif token == '--ref':
            if seen_ref:
                raise ValueError(
                    '--ref given twice — WHETHER a base was named and WHAT it '
                    'is are two questions, and answering the first with the '
                    'last value silently discards the other')
            seen_ref = True
            index += 1
            if index >= len(argv):
                raise ValueError('--ref needs a rev — a tag, a hash or a ref')
            ref = argv[index]
        elif token == '--to':
            if to is not None:
                raise ValueError('--to given twice')
            index += 1
            if index >= len(argv):
                raise ValueError('--to needs a rev — the far end of the range')
            to = argv[index]
        elif token == '--ignore':
            index += 1
            if index >= len(argv):
                raise ValueError('--ignore needs a repo-relative path')
            value = argv[index]
            if value.startswith('-'):
                raise ValueError(
                    f'--ignore {value!r} starts with "-": position in argv is '
                    f'the only thing between a value and this verb reading it '
                    f'as a flag')
            if value.startswith('/') or '..' in Path(value).parts:
                raise ValueError(
                    f'--ignore {value!r} is not repo-relative — this verb '
                    f'reads no path outside the checkout (hard rule 8)')
            ignore.append(value)
        elif token.startswith('-'):
            raise ValueError(
                f'unknown flag {token!r} — a flag this verb does not know is '
                f'refused rather than ignored: a caller that thinks it asked '
                f'for something and got a different run has been lied to')
        else:
            raise ValueError(
                f'unexpected argument {token!r} — this verb takes no '
                f'positional arguments')
        index += 1

    if not modes:
        raise ValueError(
            'no mode given. There is no default: defaulting to --story would '
            'run commands nobody asked for')
    if len(set(modes)) > 1 or len(modes) > 1:
        raise ValueError(
            f'{" ".join(sorted(set(f"--{m}" for m in modes)))} — exactly one '
            f'mode, and which one it should have been is not a thing this '
            f'verb may pick')
    mode = modes[0]
    if seen_ref:
        if mode not in (STORY, 'plan'):
            raise ValueError(
                f'--ref has no meaning with --{mode}: that rung runs the make '
                f'target the project names and reads no diff. Ignoring the '
                f'flag would be a lie about the scope that ran')
        _check_rev(ref or '')
    if ignore and mode != STORY:
        raise ValueError(
            f'--ignore has no meaning with --{mode}: that rung runs the make '
            f'target the project names and reads no diff')
    if to is not None:
        if mode != STORY:
            raise ValueError(f'--to has no meaning with --{mode}: only the '
                             f'story rung reads a range')
        _check_rev(to)
    return Args(mode=mode, ref=ref, ignore=tuple(ignore), to=to)


def _check_rev(rev: str) -> None:
    """The `--ref` grammar. Whether it RESOLVES is git's answer, not this one."""
    if not rev:
        raise ValueError(
            "--ref is empty — an empty rev makes `<rev>:<path>` name the "
            "INDEX to git, a different tree from any commit's")
    if rev.startswith('-'):
        raise ValueError(
            f'--ref {rev!r} starts with "-" — position in argv is the only '
            f'thing between a value and git running it as an option, so a '
            f'leading dash is refused here rather than trusted downstream')
    if len(rev) > REV_MAX:
        raise ValueError(f'--ref is {len(rev)} characters — at most {REV_MAX}')
    if any(char.isspace() for char in rev) or '\x00' in rev:
        raise ValueError(
            f'--ref {rev!r} contains whitespace or a NUL — that is one '
            f'argument that spells two, and a NUL truncates at the exec '
            f'boundary past anything this code could see')


def _usage_error(why: str) -> int:
    print(f'agentic-sdlc verify: {why}', file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return EXIT_CONFIG


def _ruleset(section: SectionReader) -> RuleSet:
    got = section()
    if got is None:
        raise ConfigError(
            'devkit.toml declares no [verify] section, so nothing here knows '
            'what proves a change. That is a config error and not a pass: a '
            'verb that printed nothing and exited 0 would report success for '
            'work it never checked. Declare [verify] milestone (and, for the '
            'middle rung, feature) plus the [[verify.narrow]] rules')
    return rules.read(got)


# --- git ----------------------------------------------------------------------
def _git(root: Path, args: list[str]) -> str:
    """One git run in the repo root. Every element is argv — never a shell."""
    try:
        done = subprocess.run([GIT, '-C', str(root), *args],
                              capture_output=True, check=False)
    except FileNotFoundError as err:
        raise GitError(GIT_MISSING) from err
    if done.returncode != 0:
        why = done.stderr.decode('utf-8', 'replace').strip()
        raise GitError(why or f'`{GIT} {" ".join(args)}` failed '
                              f'(exit {done.returncode})')
    return done.stdout.decode('utf-8', 'replace')


def _nul(out: str) -> list[str]:
    """`-z` output as paths. NUL-separated because a rename can carry a newline."""
    return [part for part in out.split('\0') if part]


def _require_repo(root: Path) -> None:
    try:
        _git(root, ['rev-parse', '--show-toplevel'])
    except GitError as err:
        if str(err) == GIT_MISSING:
            raise
        raise GitError(NOT_A_REPO) from err


def tracked(root: Path) -> list[str]:
    """Every tracked path, repo-relative posix. The census `--check` answers over."""
    _require_repo(root)
    return _nul(_git(root, ['ls-files', '-z']))


def changed(root: Path, ref: str | None, to: str | None = None) -> list[str]:
    """The diff plus untracked files, git's order, deduplicated. No HEAD
    means every tracked file is new; with `to` the range is `ref..to` and
    untracked files are not in it."""
    _require_repo(root)
    if ref is not None:
        _git(root, ['rev-parse', '--verify', ref])
        base = ref
    else:
        try:
            _git(root, ['rev-parse', '--verify', 'HEAD'])
            base = 'HEAD'
        except GitError:
            base = ''
    if to is not None:
        _git(root, ['rev-parse', '--verify', to])
        ranged = list(dict.fromkeys(
            _nul(_git(root, ['diff', '--name-only', '-z', base or to, to]))))
        # A path the range touched that no longer exists cannot be run, so it
        # is named and left out.
        gone = [path for path in ranged if not (root / path).exists()]
        if gone:
            print(f'verify --story: {len(gone)} path(s) in {base or to}..{to} '
                  f'no longer exist in this tree and are not verified: '
                  + ', '.join(gone))
        return [path for path in ranged if path not in gone]
    paths = _nul(_git(root, ['diff', '--name-only', '-z', base])) if base \
        else _nul(_git(root, ['ls-files', '-z']))
    paths += _nul(_git(root, ['ls-files', '-z', '--others',
                              '--exclude-standard']))
    return list(dict.fromkeys(paths))


# --- selection ----------------------------------------------------------------
def _scans(ruleset: RuleSet, root: Path,
           files: Sequence[str]) -> list[declares.Scan]:
    """Every reverse rule's read of the tree, or [] — nothing is scanned when
    no rule asks."""
    return [declares.scan(rule, files, root)
            for rule in ruleset.narrow if rule.kind == REVERSE]


def _resolver(scans: Sequence[declares.Scan]) -> select.ReverseResolver | None:
    """One reverse resolver for `plan_for` and `--check`, so the two cannot
    drift apart; None when there are no scans."""
    if not scans:
        return None
    return lambda rule, path: declares.resolve(scans, rule, path)


def plan_for(ruleset: RuleSet, root: Path, ref: str | None,
             ignore: Sequence[str] = (),
             to: str | None = None) -> select.Selection:
    """The story rung's selection for the current diff; `ignore` is the
    caller's own writes."""
    paths = changed(root, ref, to)
    if ignore:
        # A belt's own writes must not read as the operator's edit and send a
        # story close to the milestone rung.
        prefixes = tuple(p.rstrip('/') + '/' for p in ignore)
        paths = [p for p in paths
                 if not p.startswith(prefixes) and p not in ignore]
    scans = _scans(ruleset, root, tracked(root)) if paths else []
    return select.select(ruleset.narrow, paths, reverse=_resolver(scans))


# --- running ------------------------------------------------------------------
def _run(command: str, root: Path) -> int:
    """One verification command through a shell in the repo root — `rules.py`
    already refused every spelling that makes one command into two."""
    print(f'  $ {command}', flush=True)
    return subprocess.run(command, shell=True, cwd=str(root),
                          check=False).returncode


def _run_all(commands: Sequence[str], root: Path) -> int:
    """In declaration order, stopping at the first failure and naming it."""
    for command in commands:
        code = _run(command, root)
        if code != 0:
            print(f'agentic-sdlc verify: FAILED (exit {code}) — {command}',
                  file=sys.stderr)
            return EXIT_FINDINGS
    return EXIT_OK


def _run_story(ruleset: RuleSet, root: Path, ref: str | None,
               ignore: Sequence[str] = (), to: str | None = None) -> int:
    selection = plan_for(ruleset, root, ref, ignore=ignore, to=to)
    if not selection.matched and not selection.missed:
        print('verify --story: no changed paths against '
              f'{ref or "HEAD"}{f" up to {to}" if to else ""} — nothing to verify')
        return EXIT_OK
    if selection.missed:
        # The dangerous case: named, then the widest rung.
        print(f'verify --story: {len(selection.missed)} changed path(s) match '
              f'no [[verify.narrow]] rule:')
        for path in selection.missed:
            print(f'  {path}')
        print(f'verify --story: falling back to the {MILESTONE} rung — a '
              f'narrow run that skipped these would report success for work '
              f'it never checked')
        return _run_all([ruleset.milestone], root)
    print(f'verify --story: {len(selection.matched_paths)} changed path(s) -> '
          f'{len(selection.commands)} command(s)')
    return _run_all(selection.commands, root)


def _run_rung(ruleset: RuleSet, root: Path, name: str) -> int:
    command = ruleset.rung(name)
    if command is None:
        print(f'agentic-sdlc verify: [verify] declares no {name} rung, so '
              f'--{name} has nothing to run. Skipping it would report success '
              f'for a rung nobody ran; running the rung above it would charge '
              f'a {name} close for a milestone gate. Declare '
              f'`{name} = "make <target>"`', file=sys.stderr)
        return EXIT_CONFIG
    print(f'verify --{name}: {command}')
    return _run_all([command], root)


# --- the ledger, and the ratio ------------------------------------------------
def gate_costs(root: Path) -> tuple[dict[str, Cost], str]:
    """(target -> its most recent `gate` row, the ledger path as a string).
    Anything unreadable yields no costs and the plan says `unknown`, because
    an invented cost gets quoted."""
    import json

    try:
        from agentic_sdlc.repo.pm import ledger, model
        cfg = model.load()
        live = model.in_progress_milestones(cfg)
        if len(live) != 1:
            return {}, ''
        path = ledger.ledger_path(live[0][2].parent)
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


def _target_of(command: str) -> str | None:
    """The make target a command names, or None when it is not a make call."""
    words = command.split()
    if len(words) >= 2 and words[0] == MAKE_PROGRAM \
            and makefile.TARGET.match(words[1] + ':'):
        return words[1]
    return None


def _cost_of(command: str, costs: dict[str, Cost]) -> Cost | None:
    target = _target_of(command)
    return costs.get(target) if target else None


# --- --plan -------------------------------------------------------------------
def _plan(ruleset: RuleSet, root: Path, ref: str | None) -> int:
    """All three rungs, their commands and their MEASURED costs. Runs nothing."""
    selection = plan_for(ruleset, root, ref)
    costs, ledger_at = gate_costs(root)
    print(f'[verify] plan — three rungs, narrow to wide ({ref or "HEAD"})')
    print()

    story_ms = _print_story_rung(selection, costs)
    wide_ms: dict[str, int | None] = {}
    for name in (FEATURE, MILESTONE):
        command = ruleset.rung(name)
        if command is None:
            print(f'  {name:<10} (not configured) — --{name} exits 2')
            wide_ms[name] = None
            continue
        cost = _cost_of(command, costs)
        print(f'  {name:<10} {command:<46}  '
              f'{cost.render() if cost else "unknown"}   [{RUNG_BLURB[name]}]')
        wide_ms[name] = cost.duration_ms if cost else None

    print()
    print(f'  {_ratio(story_ms, wide_ms[MILESTONE], ledger_at)}')
    return EXIT_OK


def _print_story_rung(selection: select.Selection,
                      costs: dict[str, Cost]) -> int | None:
    """The story rung's commands; their total ms, or None when any is unknown."""
    if selection.missed:
        print(f'  {STORY:<10} (falls back: {len(selection.missed)} changed '
              f'path(s) match no rule)   [{RUNG_BLURB[STORY]}]')
        for path in selection.missed:
            print(f'  {"":<10}   {path}')
        return None
    if not selection.commands:
        print(f'  {STORY:<10} (nothing changed)   [{RUNG_BLURB[STORY]}]')
        return None
    total = 0
    known = True
    for match in selection.matched:
        cost = _cost_of(match.command, costs)
        print(f'  {STORY:<10} {match.command:<46}  '
              f'{cost.render() if cost else "unknown"}   '
              f'[{RUNG_BLURB[STORY]}, {len(match.paths)} path(s)]')
        if cost is None:
            known = False
        else:
            total += cost.duration_ms
    return total if known else None


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
def _first_claims(ruleset: RuleSet, files: Sequence[str],
                  resolver: select.ReverseResolver | None) -> dict[str, int]:
    """tracked path -> the index of the rule that is FIRST for it (S1).

    One path per `select` call: a whole-corpus Selection dedupes by command
    and so cannot say which rules fired.
    """
    winner: dict[str, int] = {}
    for path in files:
        found = select.select(ruleset.narrow, [path], reverse=resolver)
        if found.matched:
            winner[path] = found.matched[0].index
    return winner


def _shadowed(where: str, rule: Rule, claims: Sequence[str],
              winner: dict[str, int]) -> str:
    """S1: a rule that claims tracked files and is first for none of them.
    `claims` is what the rule would select in isolation."""
    example = claims[0]
    what = (f'paths {rule.glob!r} matches' if rule.kind == FORWARD
            else f'the files scan {rule.glob!r} found declare')
    return (f'{where}: {what} {len(claims)} tracked file(s), and this rule is '
            f'FIRST for NONE of them — [verify.narrow] #{winner[example]} '
            f'claims {example!r} already, and the first matching rule wins per '
            f'path, so this rule can never run for any diff. Same rot as a rule '
            f'pointed at a path that was renamed away, arriving by the likelier '
            f'route: nobody re-adds a rule for a path they renamed away, and '
            f'everybody adds a specific rule under a general one. Move it above '
            f'the rule that shadows it, or delete it')


def _check(ruleset: RuleSet, root: Path) -> int:
    """Every rule and rung held against the tree; findings are exit 1.

    The census prints on the pass too, in one unit — distinct tracked files
    (S2) — so a reader can tell whether the gate looked at anything.
    """
    files = tracked(root)
    targets, makefile = make_targets(root)
    findings: list[str] = []
    if not targets:
        findings.append(
            f'no {MAKEFILE} at the repo root, so no rung or `run` naming a '
            f'make target can be resolved — a rule set nobody can resolve is '
            f'a rule set nobody has run')

    for name in (FEATURE, MILESTONE):
        command = ruleset.rung(name)
        if command is None:
            continue
        target = rung_target(command)
        if targets and target not in targets:
            findings.append(
                f'[verify] {name}: {command!r} names make target {target!r}, '
                f'which {makefile} does not declare')

    scans = _scans(ruleset, root, files)
    resolver = _resolver(scans)
    winner = _first_claims(ruleset, files, resolver)
    first_for = set(winner.values())
    unvalidated = 0

    for rule in ruleset.narrow:
        where = f'[verify.narrow] #{rule.index}'
        target = _target_of(rule.run)
        if target is None:
            # S3: a `run` that is not `make <target>` is counted, never
            # validated — whether it is runnable is a fact about the machine.
            unvalidated += 1
        elif targets and target not in targets:
            findings.append(
                f'{where}: run {rule.run!r} names make target {target!r}, '
                f'which {makefile} does not declare')
        if rule.kind == FORWARD:
            claims = [path for path in files if rule.pattern.fullmatch(path)]
            if not claims:
                findings.append(
                    f'{where}: paths {rule.glob!r} matches ZERO tracked files '
                    f'— a rule pointed at a path that was renamed away rots '
                    f'into a rule that quietly matches nothing, forever')
            elif rule.index not in first_for:
                findings.append(_shadowed(where, rule, claims, winner))
            continue
        found = next(one for one in scans if one.index == rule.index)
        findings.extend(found.findings)
        if found.empty_scan:
            findings.append(
                f'{where}: scan {rule.glob!r} matches ZERO tracked files — the '
                f'louder zero: this rule can never select anything')
        elif found.empty_corpus:
            findings.append(
                f'{where}: scan {rule.glob!r} matched {found.scanned} file(s) '
                f'and NONE declares {rule.declares!r} — a corpus that has '
                f'drifted away from the rule reading it')
        elif rule.index not in first_for:
            # Shadowed by an earlier rule, or covering nothing the tree still
            # tracks; only the first has a rule to name.
            claims = [path for path in files
                      if declares.resolve(scans, rule, path) is not None]
            if claims:
                findings.append(_shadowed(where, rule, claims, winner))
            else:
                findings.append(
                    f'{where}: scan {rule.glob!r} matched {found.scanned} '
                    f'file(s) declaring {rule.declares!r}, and NONE of what '
                    f'they declare is a tracked path — the declarations name a '
                    f'tree that has moved on, so this rule can never select '
                    f'anything')

    for finding in findings:
        print(f'  DRIFT  {finding}')
    if unvalidated:
        # NOTE, not DRIFT (rule 9): a finding here would redden every repo
        # whose narrow rules are a real command line.
        print(f'  NOTE   {unvalidated} rule(s) name a `run` that is not '
              f'`{MAKE_PROGRAM} <target>`; this gate holds a make target to '
              f'{makefile or MAKEFILE} and asks nothing else of a command — '
              f'whether one is runnable is a fact about the machine, not about '
              f'this checkout, and answering it would mean booting something')
    census = (f'{len(ruleset.narrow)} rule(s), {len(winner)} of {len(files)} '
              f'tracked file(s) matched by a rule, {unvalidated} run(s) '
              f'unvalidated')
    if findings:
        print(f'[verify:check] FAIL — {len(findings)} finding(s); {census}')
        return EXIT_FINDINGS
    print(f'[verify:check] PASS — {census}')
    return EXIT_OK
