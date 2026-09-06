"""verify — what proves THIS edit, at the altitude you are working at.

    agentic-sdlc verify --story [--ref <rev>]   # the edit. Alias: --changed
    agentic-sdlc verify --feature               # the range, one step wider
    agentic-sdlc verify --milestone             # everything, once
    agentic-sdlc verify --plan  [--ref <rev>]   # print all three, run NOTHING
    agentic-sdlc verify --check                 # validate [verify] vs the tree

THE LADDER HAS THREE RUNGS (decision D3), and `--plan` is why this is a verb
and not a make target: an orchestrator writing a dispatch can ASK THE REPO what
the narrow command is instead of guessing, and the answer stays true as the
tree grows. The measured case that made this necessary: a full suite is 154 s
and a single module 0.9 s, and an agent fixing eleven failures ran the full
suite after each one — 31 minutes — because the dispatch named one command and
nothing told it there was another.

  * `--story` is a FUNCTION of the changed paths: the diff is read from git,
    each path is matched against `[[verify.narrow]]`, and the deduplicated
    commands run in declaration order.
  * `--feature` and `--milestone` run the make target `[verify]` names. The
    Makefile stays the authority on what a target RUNS.

`--feature` DOES NOT CLAIM TO BE RANGE-SCOPED. It runs the composition the
project names for that rung; scoping to a feature's commit range needs that
feature's first commit, which is derivable from the ledger and is not derived
in 0.2.0. A rung that claimed a narrowing it does not perform would be a false
PASS with a scope on it, which is worse than an honest wide one.

A MISS IS LOUD AND FALLS BACK TO THE WIDEST RUNG. A changed path matching no
rule is printed on its own line, and then `milestone` runs — its exit code is
the answer. A narrow verifier that matches nothing and exits 0 is worse than no
verifier: it reports success for work it never checked, which is hard rule 4's
read-side cardinal sin. That is the single most dangerous failure in this
design, so the fallback is unconditional and not a heuristic.

THE RATIO IS MEASURED OR IT IS `unknown`. `--plan` reads `gate` rows out of
`pm/roadmap/<building>/ledger.jsonl` — `duration_ms` (MILLISECONDS), `census`
and `verdict` — and prints the cost beside each rung. Where no row exists the
cost is the literal word `unknown`, and so is the ratio. **A fabricated ratio
is worse than no ratio, because it gets quoted.** Never a guess, never an
assumed 1.0.

`--plan` RUNS NOTHING. Not the rungs, not the narrow commands, not `make -n`.
It reads git, config, the tree and the ledger, and it prints.

EXIT CODES ARE CONTRACT (hard rule 6):

    0  the rung passed, the plan printed, or `--check` found nothing
    1  a verification command failed, or `--check` found something
    2  usage, a `[verify]` config problem, or git missing/unusable

A command exiting 2 is reported as 1 with its own code printed beside it. Rule
6 reserves 2 for "you or your config are wrong", and a `make` that happens to
exit 2 must never reach a caller looking like a devkit config error.

`run` IS PASSED TO A SHELL, deliberately: a project's verification IS a command
line, and `python3 -m pytest tests/test_pm_*.py` needs the glob expanded. The
guard is threefold and it is stated here because it is the riskiest thing this
package does. First, `run` comes from a tracked file the repo owns. Second,
`rules.py` refuses every spelling that makes one command into two — `;` `|`
`&` `$` backtick `(` `)` `<` `>` `#` `\\` and any newline — so what reaches the
shell is one command by construction. Third, `--plan` exists so a caller can
READ the command before anything runs it.

THE REFUSAL MATRIX — argv is an input surface (SDLC.md §5):

    no flag                     exit 2 with usage. NOT a default to --story,
                                which would run commands nobody asked for
    two modes, or three         exit 2 — which one it should have been is not
                                a thing this verb may pick
    --ref with no value         exit 2
    --ref twice                 exit 2 (WHETHER and WHAT are two questions)
    --ref ''                    exit 2 — an empty rev names the INDEX to git,
                                a different tree from any commit's
    --ref '--plan'              exit 2 — the next flag is never adopted as a
                                rev; position in argv is the only thing
                                between a value and git running an option
    --ref with whitespace,      exit 2 — one argument that spells two
      a newline, or a NUL
    --ref that does not resolve exit 2, in git's own words
    --ref beside --feature,     exit 2 — those rungs have no diff, and a
      --milestone or --check    silently-ignored flag is a lie about scope
    -x, --nope, --changed=1     exit 2 naming it, never silently ignored
    a positional argument       exit 2 — this verb takes none
    --help                      the module docstring, exit 0, runs nothing

The rev reaches git as ONE argv element and never through a shell.

`[verify]` ABSENT IS EXIT 2 FOR ALL FIVE FLAGS, naming the section. A `--plan`
that prints nothing and exits 0 is the same lie one step earlier than a
`--story` that runs nothing and exits 0.

WHAT `--check` CAN ANSWER, AND WHAT IT SAYS IT DID NOT (finding S3, ruled here
because story 05's `## Close` found the same gap by other means):

  * a rung's or a `run`'s `make <target>` is held against the Makefile — TEXT
    in this checkout, parsed, never `make -n`.
  * a `run` that is not `make <target>` is NOT validated, and the census says
    how many of those there were. "Is `uv run … python -m pytest` runnable" is
    a fact about the MACHINE — PATH, an interpreter's installed packages — and
    a gate whose verdict moves with the machine answers differently in CI than
    in a checkout, which is hard rule 8's reason for vendoring fixtures. The
    cheap version does not even catch the case we have MEASURED: story 05's
    fifteen rules spelled `python3 -m pytest`, and `python3` is on PATH, so a
    `shutil.which` on the first word passes all fifteen. What catches it is
    importing pytest under that interpreter, which boots something (hard rule
    2). A validation that passes the only case we have observed is worse than
    none, because it turns an unchecked thing into a checked-LOOKING one.
  * a rule that can never be FIRST is a finding (S1). The property that matters
    is a whole-set one — first matching rule wins per path — so it is asked by
    running the selector over the tracked corpus, not by asking each glob in
    isolation whether it matches anything.
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

# The story rung's own name in output and in `--plan`. `--changed` is the
# alias the feature file introduced it under, kept because a dispatch that
# already quotes it must not break.
STORY = 'story'
CHANGED = 'changed'

# Ladder order, narrow to wide. Printed in this order and run in this order,
# so "which is the loop and which is the close" is visible rather than known.
LADDER = (STORY, FEATURE, MILESTONE)
RUNG_BLURB = {STORY: 'the edit', FEATURE: 'the range', MILESTONE: 'the close'}

# What `--check` reads to answer "does this target exist". TEXT, parsed — never
# `make -n`, which would run a build to answer a question about a name (hard
# rule 2: nothing here boots anything).
MAKEFILE = makefile.MAKEFILE
MAKE_PROGRAM = 'make'

# A rev arrives from argv and goes to git as one element. These three shapes
# are refused HERE rather than trusted to stay a value — `report.check_rev`'s
# reasoning, and the same three refusals.
REV_MAX = 256

USAGE = """usage: agentic-sdlc verify (--story|--feature|--milestone|--plan|--check)
                          [--ref <rev>]

  --story [--ref <rev>] [--ignore <path>]...
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


# `[verify]`, or None when devkit.toml declares no such section. Supplied by
# `cli.py`, which is the module `tests/test_boundaries.py` allowlists to read
# raw config — `repo/verify/` is deliberately not on that list, so the section
# is passed IN and this module stays a pure function of it.
SectionReader = Callable[[], 'dict | None']


def main(argv: Sequence[str], section: SectionReader) -> int:
    """The verb. `section` is called only after argv parses, so `--help` and a
    usage error never touch devkit.toml."""
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
        # Hostile TREE contents: no plan could be produced. That is the same
        # class of answer as a malformed section, never a finding about code.
        print(f'agentic-sdlc verify: {err}', file=sys.stderr)
        return EXIT_CONFIG


def _dispatch(args: Args, ruleset: RuleSet, root: Path) -> int:
    if args.mode == 'plan':
        return _plan(ruleset, root, args.ref)
    if args.mode == 'check':
        return _check(ruleset, root)
    if args.mode == STORY:
        return _run_story(ruleset, root, args.ref, args.ignore)
    return _run_rung(ruleset, root, args.mode)


# --- argv ---------------------------------------------------------------------
def _parse(argv: list[str]) -> Args:
    """One mode, an optional `--ref` for the two modes that read a diff."""
    modes: list[str] = []
    ref: str | None = None
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
    return Args(mode=mode, ref=ref, ignore=tuple(ignore))


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


def changed(root: Path, ref: str | None) -> list[str]:
    """The diff, plus untracked files: a new file is a changed path.

    Order is git's, deduplicated, because a path can appear in both halves.
    With no `--ref` the base is HEAD; in a repo with no commits yet there is no
    HEAD, and every tracked file is new.
    """
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
    paths = _nul(_git(root, ['diff', '--name-only', '-z', base])) if base \
        else _nul(_git(root, ['ls-files', '-z']))
    paths += _nul(_git(root, ['ls-files', '-z', '--others',
                              '--exclude-standard']))
    return list(dict.fromkeys(paths))


# --- selection ----------------------------------------------------------------
def _scans(ruleset: RuleSet, root: Path,
           files: Sequence[str]) -> list[declares.Scan]:
    """Every reverse rule's read of the tree, or [] when there are none.

    Nothing is scanned for a rule set with no reverse rules: reading files to
    answer a question nobody asked is the spawn-per-file defect this feature
    exists to end, one layer up.
    """
    return [declares.scan(rule, files, root)
            for rule in ruleset.narrow if rule.kind == REVERSE]


def _resolver(scans: Sequence[declares.Scan]) -> select.ReverseResolver | None:
    """`select`'s reverse resolver over these scans, or None when there are none.

    One spelling, used by `plan_for` and by `--check`, because the two ask the
    selector the SAME question against the same rule set — S1's finding was
    `--check` answering a per-rule question where the verb answers a whole-set
    one, and two resolvers would let them drift apart again.
    """
    if not scans:
        return None
    return lambda rule, path: declares.resolve(scans, rule, path)


def plan_for(ruleset: RuleSet, root: Path, ref: str | None,
             ignore: Sequence[str] = ()) -> select.Selection:
    """The story rung's selection for the current diff.

    `ignore` is the CALLER's own writes — see the comment below.
    """
    paths = changed(root, ref)
    if ignore:
        # THE CALLER'S OWN WRITES, and only a caller can know which those are.
        #
        # I3: `close story`'s first step moves a `status:` line inside
        # `pm/roadmap/` and appends to the tracked `ledger.jsonl`, and its
        # SECOND step is this rung — so the belt's own writes arrive here as
        # changed paths, match no `[[verify.narrow]]` rule in a project that
        # never wrote one for its PM tree, and send the story close to the
        # MILESTONE rung. Measured on a fresh consumer: a full gate inside the
        # step advertised as "four of its five steps are already-computed
        # facts", which is risk 2 of that feature arriving by construction.
        #
        # This is NOT the verb deciding that a PM tree needs no verification —
        # that is the project's call, made by declaring a narrow rule for it
        # (rule 9). It is the verb letting a caller say which paths IT wrote
        # during this run, which is exactly the ruling `check_committed`
        # already makes one step later.
        prefixes = tuple(p.rstrip('/') + '/' for p in ignore)
        paths = [p for p in paths
                 if not p.startswith(prefixes) and p not in ignore]
    scans = _scans(ruleset, root, tracked(root)) if paths else []
    return select.select(ruleset.narrow, paths, reverse=_resolver(scans))


# --- running ------------------------------------------------------------------
def _run(command: str, root: Path) -> int:
    """One verification command, through a shell, in the repo root.

    A shell DELIBERATELY: a project's verification is a command line, and
    `tests/test_pm_*.py` needs the glob expanded. `rules.py` has already
    refused every spelling that makes one command into two.
    """
    print(f'  $ {command}', flush=True)
    return subprocess.run(command, shell=True, cwd=str(root),
                          check=False).returncode


def _run_all(commands: Sequence[str], root: Path) -> int:
    """In declaration order, stopping at the FIRST failure, naming it.

    Not parallel and not continue-on-error: a runner that hides which command
    failed is worse than a slow one.
    """
    for command in commands:
        code = _run(command, root)
        if code != 0:
            print(f'agentic-sdlc verify: FAILED (exit {code}) — {command}',
                  file=sys.stderr)
            return EXIT_FINDINGS
    return EXIT_OK


def _run_story(ruleset: RuleSet, root: Path, ref: str | None,
               ignore: Sequence[str] = ()) -> int:
    selection = plan_for(ruleset, root, ref, ignore=ignore)
    if not selection.matched and not selection.missed:
        print('verify --story: no changed paths against '
              f'{ref or "HEAD"} — nothing to verify')
        return EXIT_OK
    if selection.missed:
        # THE dangerous case. Named, one path per line, then the widest rung.
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

    Read from the BUILDING milestone's ledger, which is where
    `every-gate-reports-its-cost` writes. Anything that goes wrong — no PM
    tree, no milestone building, an unreadable line — yields no costs and the
    plan says `unknown`. A cost this cannot read is a cost it does not have,
    and inventing one is the failure this whole feature is against.
    """
    import json

    try:
        from agentic_sdlc.repo.pm import ledger, model
        cfg = model.load()
        building = model.building_milestones(cfg)
        if len(building) != 1:
            return {}, ''
        path = ledger.ledger_path(building[0][2].parent)
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
    """The story rung's commands. Returns their total ms, or None if any is
    unknown — a partial total would be a made-up number wearing a real one's
    clothes."""
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
    """(every target the root Makefile and its includes declare, the file read).

    `core.makefile` is the one reader; `check doc` asks it the same question.
    """
    path = root / MAKEFILE
    if not path.is_file():
        return frozenset(), ''
    return makefile.targets(root), str(path)
def _first_claims(ruleset: RuleSet, files: Sequence[str],
                  resolver: select.ReverseResolver | None) -> dict[str, int]:
    """tracked path -> the index of the rule that is FIRST for it. S1's answer.

    ONE PATH PER `select` CALL, and that is the trap this function exists to
    avoid rather than an oversight. A whole-corpus `Selection` CANNOT say which
    rules fired: `select` deduplicates by COMMAND (select.py:172-190), so two
    rules whose `run` substitutes to the same string collapse into one `Match`
    carrying the FIRST one's index. Measured on this repo's own section — #3
    and #4 both run the whole suite, and #15, #16, #17 and #19 all run
    `make gates`, so four of its twenty rules are collapsed into an earlier
    one's Match. Reading `{m.index for m in selection.matched}` as "the rules
    that fired" therefore files four shadowing findings against a rule set in
    which every one of the twenty fires for some path, and a gate that invents
    drift teaches the same lesson as one that misses it: turn it off.

    Asked THROUGH `select` rather than re-derived here, because first-match-wins
    is the selector's ruling (select.py:35-38) and a second spelling of it in
    the checker is how the checker comes to validate a selection nobody runs.
    A tracked path the selector refuses (a control character, a capture binding
    a value that cannot go on a command line) raises SelectionError and is exit
    2 at the verb, which is the same answer `--changed` gives for that tree —
    the two agreeing is the point.
    """
    winner: dict[str, int] = {}
    for path in files:
        found = select.select(ruleset.narrow, [path], reverse=resolver)
        if found.matched:
            winner[path] = found.matched[0].index
    return winner


def _shadowed(where: str, rule: Rule, claims: Sequence[str],
              winner: dict[str, int]) -> str:
    """S1: a rule that claims tracked files and never gets to select any of them.

    `claims` is what this rule would select IN ISOLATION — the paths `paths`
    matches, or, in the reverse direction, the paths the scanned files DECLARE.
    The two are named differently on purpose: `scan 'tests/integration/**'`
    does not MATCH the source path it covers, so rendering the glob as the
    thing that matched would be a lie about which file is which.
    """
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
    """Every rule and every rung, held against the tree. Findings are exit 1.

    A `--check` that reports OK over a rule set it did not actually RESOLVE is
    this package's cardinal sin, so the census prints on the pass too — and
    every number in it is in ONE unit, DISTINCT TRACKED FILES, which is finding
    S2's fix. It used to sum each rule's own match count and render that with a
    noun meaning distinct files, against a denominator that was distinct files:
    six rules all naming `src/a.py` in a repo tracking three files printed
    `6 matched file(s) scanned of 3 tracked`. A census that can EXCEED its own
    denominator is not counting what it scanned (hard rule 4), and this is the
    line a consumer reads to decide whether the gate looked at anything.

    The union is counted rather than the column renamed, because the union is
    the number a reader was already trying to get out of the line — how much of
    the tree a rule covers — and because `_first_claims` has to compute the
    same selection anyway for S1. It is exact, not an approximation: a path is
    claimed by SOME rule exactly when it is claimed by its FIRST one, so
    `len(winner)` is both, and `len(winner) + len(unclaimed) == len(files)`.
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
            # S3, ruled in the module docstring: a `run` that is not
            # `make <target>` is counted and named, never validated. Whether it
            # is runnable is a fact about the machine, and the cheap spelling
            # (`which` on the first word) passes the only case we have measured.
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
            # The reverse direction reaches S1's question by two routes: every
            # path its declarations cover is claimed above it (shadowed), or
            # they cover nothing that is tracked at all — a scanned corpus that
            # declares only paths the tree no longer has. Both are "this rule
            # can never be selected"; only the first has a rule to name.
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
        # NOTE, not DRIFT: rule 9 — it reports the fact and the caller decides.
        # A finding here would redden every repo whose narrow rules are a real
        # command line (this one's are), and a gate nobody can pass is a gate
        # that gets turned off.
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
