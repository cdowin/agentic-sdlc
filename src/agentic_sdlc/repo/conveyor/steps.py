"""steps.py — the four step lists, as registries the driver walks.

`driver.py` is the machine; this is what it walks. Four lists — `release`,
`adopt`, and the two INNER belts `story` and `feature` (SDLC.md §0) — each with
a `check()` that is a QUESTION ABOUT THE TREE and — where the kind allows one —
a `do()` whose return value the driver discards. That discard is the contract
this module is written against: **no `check()` here reads a flag its own `do()`
set.** A step that answered "done" because it remembered doing something would
be the report-without-the-postcondition rule 4 calls the cardinal sin, wearing
a step machine's clothes.

## Where the list came from, and the one step that was missing

The shipped default reconciles two prose copies of the same protocol —
`SDLC.md` § *Close protocol (ordered)* and `.claude/skills/release/SKILL.md` —
against each other. They disagreed, which is the drift this feature exists to
end. The reconciliation found one step present in the prose and absent from the
feature's planned list: `findings-resolved` (SDLC.md close protocol step 5 —
every `docs/reviews/` record for the milestone resolved and DELETED). A machine
shipping a protocol shorter than the paragraph it replaces is this feature's own
risk 2 arriving on day one, so it is a step and the default list is 21, not 20.

## What is deliberately NOT a step

Risk 1 is over-encoding: a step earns its place by having a checkable
postcondition, and everything else is guidance the generated document carries
(`sdlc_doc.py` renders `GUIDANCE` below beside the list).

- the negative probe for a gate whose scoping changed — the artifact is a
  judgement made in scratch, with nothing in the tree to check;
- the consumer-pin reminder — instructions for somebody in another repo, and
  hard rule 8 forbids gating on one;
- opening the next milestone — it happens after the tag and needs a name only a
  human has.

## The three that cannot be Python

Hard rule 1 is stdlib-only, forever: no `gh`, no HTTP client, no transitive
dependency in a consumer's pre-push hook. So `pr-open`, `ci-green` and
`prove-artifact` ship with **no default command**. Each is a JUDGEMENT whose
`check()` runs `[release.commands] <step>` if the project supplies one and
answers UNVERIFIABLE if it does not — a refusal to advance, never a pass.
`prove-artifact` additionally cannot have a default because the proof names a
git URL, and a URL is a project's own fact (rule 8): a default naming a
repository would put a consumer's provenance in this package's source, which is
`bugs/consumer-names-and-provenance-in-code` all over again. `merge` is a
judgement too, but its artifact is local — the mainline containing this
branch's tip is a question `git` answers.

## No step re-implements a predicate that has a verb

`review-landed`, `features-done` and `stories-done` go through
`pm ready-for tag|milestone|feature`. `narrow-verified` and `feature-verified`
go through `verify --story|--feature`. None of them parses a verdict block,
reads frontmatter with a regex, or names a test command of its own. Two readers
of "is every finding dispositioned" are two answers, and the second one is the
permissive one on the day they disagree — the argument `gates_extra.py` already
makes about a second TOML reader.

**The one place this module reads a review record itself is the feature belt**,
and it does it through `pm/verdict.py` — the SAME parser `ready_for` reads,
never a second one. There is no `pm ready-for` at feature grain that answers
"does this record parse and is every finding dispositioned" (`ready-for tag`
asks it of a whole milestone), so `review-recorded` and `findings-landed` ask
`verdict.parse` directly and INHERIT its rulings whole: a record whose block
does not parse is UNVERIFIABLE — a refusal to advance — and never a pass, and a
finding at `disposition: open` blocks. Softening either one here would be the
second, permissive answer this section exists to refuse.

## Config (rule 5 — a repo with no `devkit.toml` behaves identically)

    [release]
    steps       = [...]                    # default: DEFAULT_RELEASE_STEPS
    pin_files   = ["README.md"]            # where readme-pins looks
    changelog   = "CHANGELOG.md"
    command_timeout = 1800                 # seconds, per configured command

    [release.commands]
    gate      = "make milestone"           # the ONE shipped default command
    ci-green  = "gh pr checks --required"  # the PROJECT supplies gh

    [release.version_files]
    "pyproject.toml"           = '^version = "(.*)"$'
    "src/pkg/__init__.py"      = "^__version__ = '(.*)'$"

    [adopt]
    steps          = [...]                 # default: DEFAULT_ADOPT_STEPS
    pin_file       = "Makefile"            # where DEVKIT_VERSION lives
    runner_targets = ["check", "precommit", "milestone"]

    [story]                                # default: DEFAULT_STORY_STEPS
    [feature]                              # default: DEFAULT_FEATURE_STEPS
    steps = [...]                          # both take the same two keys as
                                           # above; a repo declaring NEITHER
                                           # section closes exactly the way a
                                           # repo declaring the stock lists
                                           # does (rule 5)

Every refusal here exits 2 through `ConfigError`: a typo is a config mistake,
not a finding, and a release list that quietly got shorter is the cardinal sin
with a config file in front of it. The step that vanishes is `review-landed`.

## `adopt` — the subtraction, which is the whole second list

A pin bump is verified as a PIN BUMP. `checks-pass` runs **this package's**
`check all` and never the consumer's `make check`: measured, `check all` is
~1 s here and a consumer's `make check` also runs its own twenty gates, which
verify the CONSUMER'S code against the CONSUMER'S rules — and a version bump in
this package cannot change their verdict. Running them during adoption
re-verifies the game, not the adoption. That is one line of code, it is easy to
write correctly and easy to regress into `make check` by somebody being
helpful, so `tests/test_conveyor_adopt.py::test_checks_pass_never_runs_make`
names it with a command recorder AND a sentinel file.

Hard rule 8 is the live hazard here rather than a background rule: `adopt` runs
IN a consumer, on the consumer's own tree, which is fine and is the point. What
it must never do is read a second repo or gate on one. Every step below is a
question about the LOCAL tree — `pin-bumped` included, which compares the
consumer's own `DEVKIT_VERSION` line to the version of the package that is
RUNNING, needing no network and no second checkout.

A step this package cannot perform states precisely what the operator must do
and refuses to advance until its `check()` is true. `pin-bumped` edits nothing:
the line it names is in a file this package does not own.

## `story` and `feature` — the belts that run constantly

**The line, and it is the whole design: the entry conditions are ENFORCED, the
judgement is EXPRESSED.** `stories-done` is a fact about the tree and it blocks.
`review-recorded` can check only that a record EXISTS and PARSES — whether the
review was any good is not a thing to encode, and a step that pretended to
check it would be this package's cardinal sin wearing a protocol. So every
JUDGEMENT step below says, in its `do()`, what a human must do AND why the
machine is not doing it.

Two things follow from `close story` running dozens of times a day:

1. **It has to be fast.** Four of its five steps read a status line, a git
   porcelain listing or a file already open; the fifth shells out once to the
   narrow rung. A belt slower than closing by hand is a belt that gets skipped,
   and a skipped belt is worse than none because it looks like control.
2. **It must not falsify its own preconditions.** `claimed` writes a status
   line into the PM tree, so `committed` — two steps later — asks about the
   worktree OUTSIDE the roadmap directory. A machine whose first step reddens
   its third is `state.py` point 2 arriving one grain down.

`evidence-written` READS the `done:` line and never writes it. The sentence is
the author's — `.claude/rules/pm-execution.md` step 6 — and a machine-written
one would be a second scoreboard saying what the commit already says.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from agentic_sdlc import __version__
from agentic_sdlc.core import apply, walk
from agentic_sdlc.core.config import ConfigError, config_section
from agentic_sdlc.repo.conveyor.driver import (Answer, Context, Step, StepKind,
                                               grain_path)
from agentic_sdlc.repo.pm import model, verdict

# --- the shipped default ------------------------------------------------------
DEFAULT_RELEASE_STEPS = (
    'tree-clean',
    'on-milestone-branch',
    'main-merged',
    'changelog-unreleased-nonempty',
    'review-landed',
    'version-sync',
    'readme-pins',
    'features-done',
    'milestone-reviewing',
    'gate',
    'milestone-accepted',
    'changelog-retitle',
    'milestone-packaging',
    'findings-resolved',
    'milestone-done',
    'push-branch',
    'pr-open',
    'ci-green',
    'merge',
    'tag',
    'prove-artifact',
)

# The adopt list. Eight steps, and two of them are here because a human list
# keeps forgetting them and both have bitten this package:
#
#   `hooks-self-test`        `install-hooks` rewrites guard scripts, and a
#                            guard that fails OPEN is not there. This package
#                            has already shipped a hook that was installed,
#                            executable, and stopping nothing — a config diff
#                            cannot show that, and no amount of reading can.
#   `runner-targets-resolve` `Makefile.devkit` `-include`s the tier file, and
#                            an `-include` of a missing file is SILENT. A tier
#                            named with no tier file must FAIL here rather than
#                            yield a `precommit` that is quietly `check` alone.
DEFAULT_ADOPT_STEPS = (
    'pin-bumped',
    'installables-diffed',
    'installable-decisions-recorded',
    'config-updated',
    'hooks-self-test',
    'runner-targets-resolve',
    'checks-pass',
    'pm-validates',
)

# The story list. FIVE steps, four of which are already-computed facts, because
# this is the belt that runs dozens of times a day — and a story close that is
# slower than closing by hand gets skipped, which is worse than no belt at all
# because it looks like control. The one step that runs anything is
# `narrow-verified`, and what it runs is the narrow rung `[verify]` already
# names: seconds on a changed tree, ~0.1 s on a committed one, where it says
# "no changed paths" rather than pretending to have proven something.
DEFAULT_STORY_STEPS = (
    'claimed',
    'narrow-verified',
    'committed',
    'evidence-written',
    'story-done',
)

# The feature list. The level the orchestrator that built this milestone SKIPPED
# — 28 stories parked at `reviewing` and one review over the whole milestone —
# which is the omission this list makes impossible: `close feature` cannot
# advance past `stories-done`, and `stories-done` IS `pm ready-for feature`.
DEFAULT_FEATURE_STEPS = (
    'stories-done',
    'feature-reviewing',
    'feature-verified',
    'review-recorded',
    'findings-landed',
    'feature-done',
)

# One table rather than a branch per operation: an operation with no default
# list answers `()`, and `plan_defect` then refuses to walk it, which is the
# true sentence rather than a plausible one.
DEFAULT_STEPS: dict[str, tuple[str, ...]] = {
    'release': DEFAULT_RELEASE_STEPS,
    'adopt': DEFAULT_ADOPT_STEPS,
    'story': DEFAULT_STORY_STEPS,
    'feature': DEFAULT_FEATURE_STEPS,
}

# The ONE command this package ships a default for. `make milestone` is the
# target `install-gates` writes and `install-ci` runs, so a stock consumer's
# gate step is answerable the day it installs. Everything else is the
# project's: a default `gh` line would be a network dependency in the package
# that promised never to have one, and a default artifact URL would be a
# consumer's provenance in this package's source (rule 8).
DEFAULT_COMMANDS: dict[str, str] = {'gate': 'make milestone'}

# The judgements that CANNOT ship a default command, named so the census test
# can assert the shipped table holds none of them.
NO_DEFAULT_COMMAND = ('pr-open', 'ci-green', 'prove-artifact')

# A step name is a path-free, markdown-free token: the renderer puts it in a
# table cell and a heading, and the driver puts it in a line shape consumers
# grep. Anchored whole, so `gate;rm -rf /` is a name that does not exist rather
# than a name with a tail.
STEP_NAME = re.compile(r'^[a-z][a-z0-9-]*$')
STEP_NAME_MAX = 40

# How much of a command's output reaches a line. A gate that writes 100 MB to
# stdout must produce a bounded refusal, not a transcript.
OUTPUT_LIMIT = 400
DEFAULT_COMMAND_TIMEOUT = 1800

# --- what the adopt steps look at, all of it inside the checkout ---------------
DEFAULT_PIN_FILE = 'Makefile'
DEFAULT_RUNNER_TARGETS = ('check', 'precommit', 'milestone')
# `install-gates` writes this; `adopt` READS it and installs nothing.
FRAMEWORK_MAKEFILE = 'Makefile.devkit'
# Where `install-hooks` puts the corpus in every consumer.
HOOKS_DIR = 'tools/hooks'
# The drift report `installables-diffed` produces and
# `installable-decisions-recorded` reads. It sits beside the run state, is
# gitignored with it, and losing it costs one re-run.
REPORT_REL = '.agentic-sdlc/run/adopt-installables.md'
CENSUS_OPEN = '<!-- census -->'
CENSUS_CLOSE = '<!-- /census -->'
DECISIONS_HEADING = '## decisions'
# `DEVKIT_VERSION := v1.2.3`, `=`, `?=` and `+=` included — it is somebody
# else's makefile and this only ever READS the line.
PIN_LINE = re.compile(r'^\s*DEVKIT_VERSION\s*[:?+]?=\s*(\S+)')
# Enough of a file's bytes to notice it changed since the census was written.
DIGEST_LENGTH = 12

_SEMVER_TAG = re.compile(r'v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?')

# --- what the close steps look at ---------------------------------------------
# The three lifecycle words the inner belts compare against, DERIVED from the
# tracker's own vocabulary rather than respelled here. A second spelling of a
# state name goes stale in silence, which is exactly how `ready_for`'s D2 tuple
# used to drift. A project whose `[pm] story_states` cannot express one of them
# is told so by name (`_grain_status_at_or_past`) rather than answered.
CLAIMED = model.BUILDING
REVIEWING = model.REVIEWING
DONE = model.LIFECYCLE[-1]

# `done: <hash(es)> — <what shipped>` — pm-execution.md step 6, at the grain
# that closed. Case-insensitive and whitespace-tolerant, because the shape being
# checked is "the author left evidence", not "the author typed it exactly".
EVIDENCE_LINE = re.compile(r'^\s*done\s*:\s*(?P<body>\S.*)$', re.IGNORECASE)
# What "shipped" looks like: a commit hash, or the literal `in-place` for work
# that is not committed yet. BOTH forms are `pm/verdict.py`'s, inherited rather
# than re-decided — reviewers in this SDLC fix in place and never commit, so a
# hash-only rule would refuse the honest half of the corpus.
HASH_MIN, HASH_MAX = verdict.HASH_MIN_LEN, verdict.HASH_MAX_LEN
IN_PLACE = verdict.IN_PLACE
EVIDENCE_LANDED = re.compile(
    rf'\b(?:[0-9a-fA-F]{{{HASH_MIN},{HASH_MAX}}}|{IN_PLACE})\b', re.IGNORECASE)
# The budget the rule states. NOT enforced here: how long a human's evidence
# needs to be is not a fact about anything (`model.record_resolves` made the
# same call about review records), so the number is QUOTED in the refusal and
# `check grain-shape` owns caps.
EVIDENCE_BUDGET = 5
# A review record is read whole to be parsed, so the read is bounded — the same
# bound `ready-for` puts on the same files, and for the same reason: a 10 MB
# record is REPORTED rather than consumed.
MAX_RECORD_BYTES = 1 << 20


# --- small helpers ------------------------------------------------------------
def _clip(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """One bounded line of somebody else's output."""
    flat = ' '.join(str(text).split())
    return flat if len(flat) <= limit else flat[:limit] + '…'


def _read(path: Path) -> str:
    """A file's text with its line endings INTACT — `\\r\\n` survives a rewrite.

    Rule 3: a write verb preserves every byte it was not asked to change,
    including the file's line endings. `Path.read_text` normalises them away
    on 3.11, and the rewrite would then land as a whole-file diff.
    """
    with open(path, encoding='utf-8', newline='') as handle:
        return handle.read()


def _pm_cfg(ctx: Context) -> 'model.PmConfig':
    return replace(model.load(), root=ctx.root)


def _git(ctx: Context, *args: str, strip: bool = True) -> tuple[int, str]:
    """`git` in the checkout. A missing git is an exit code, never a crash.

    `strip=False` for any porcelain format whose COLUMNS carry meaning.
    `git status --porcelain` writes `XY<space>PATH`, and X is a space for a
    worktree-only change — so a blanket `.strip()` ate one character off the
    FIRST line and only the first: `SDLC.md` was reported as `DLC.md` while
    every path below it was right. Found 2026-09-05 by running the conveyor on
    this repo. A path that is wrong by one character sends an operator looking
    for a file that does not exist, and it is wrong in the direction that looks
    plausible.
    """
    try:
        done = subprocess.run(('git',) + args, cwd=str(ctx.root),
                              capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return 127, 'git is not on PATH'
    except subprocess.TimeoutExpired:
        return 124, 'git timed out'
    except OSError as err:
        return 126, str(err)
    out = done.stdout + done.stderr
    return done.returncode, out.strip() if strip else out.rstrip('\n')


def _branch(ctx: Context) -> str:
    code, out = _git(ctx, 'rev-parse', '--abbrev-ref', 'HEAD')
    return out if code == 0 else ''


def _make(ctx: Context, *args: str) -> tuple[int, str]:
    """`make` in the checkout. A missing make is an exit code, never a crash."""
    try:
        done = subprocess.run(('make',) + args, cwd=str(ctx.root),
                              capture_output=True, text=True,
                              timeout=_timeout(ctx.operation))
    except FileNotFoundError:
        return 127, 'make is not on PATH'
    except subprocess.TimeoutExpired:
        return 124, 'make timed out'
    except OSError as err:
        return 126, str(err)
    return done.returncode, (done.stdout + done.stderr).strip()


def _own_cli(ctx: Context, *argv: str) -> tuple[int, str, tuple[str, ...]]:
    """This package's OWN verb, as a subprocess, in the checkout.

    A subprocess and not an import: nothing under `repo/` may import
    `agentic_sdlc.cli` — that is the layering primitive
    `tests/test_boundaries.py` enforces — and a copy of `check all`'s roster
    here would be a second answer to which gates run. `PYTHONPATH` names the
    package that is RUNNING, so the answer comes from this build rather than
    from whatever else happens to be installed on the box.

    It returns the argv it ran, so a test can assert WHAT was run rather than
    what the transcript says was run. `checks-pass` is one line that regresses
    into `make check`, and a claim about output is not a claim about what ran.
    """
    import agentic_sdlc

    parent = str(Path(agentic_sdlc.__file__).resolve().parent.parent)
    env = dict(os.environ)
    existing = env.get('PYTHONPATH')
    env['PYTHONPATH'] = f'{parent}{os.pathsep}{existing}' if existing else parent
    command = (sys.executable, '-m', 'agentic_sdlc.cli') + argv
    try:
        done = subprocess.run(command, cwd=str(ctx.root), capture_output=True,
                              text=True, env=env,
                              timeout=_timeout(ctx.operation))
    except subprocess.TimeoutExpired:
        return 124, (f'`agentic-sdlc {" ".join(argv)}` did not finish inside '
                     f'{_timeout(ctx.operation)}s'), argv
    except OSError as err:
        return 126, f'`agentic-sdlc {" ".join(argv)}` could not be run ({err})', argv
    return done.returncode, _clip(done.stdout + done.stderr), argv


def _own_verdict(ctx: Context, *argv: str, found: str = '') -> Answer:
    """One of this package's own gates, answered as a step.

    Exit 2 is NOT exit 1: a config or usage error decided nothing, and saying
    so with the same sentence as a finding is how an operator comes to fix the
    wrong thing.
    """
    code, said, _ = _own_cli(ctx, *argv)
    spoken = f'`agentic-sdlc {" ".join(argv)}`'
    if code == 0:
        return Answer.yes(f'{spoken} exited 0{f" — {found}" if found else ""}'
                          + (f': {said}' if said else ''))
    if code == 2:
        return Answer.no(
            f'{spoken} exited 2 — a CONFIG or usage error, not a finding, so '
            f'nothing was decided: {said}')
    return Answer.no(f'{spoken} exited {code}: {said}')


def _pm_run(ctx: Context, *argv: str) -> tuple[int, str]:
    """One `pm` verb, in process, with its exit code. `pm` is `repo/`, so it is
    imported rather than spawned — the layering allows it and a spawn would pay
    an interpreter for a question already in memory."""
    import contextlib
    import io

    from agentic_sdlc.repo.pm import cli as pm_cli
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = pm_cli.main(list(argv))
    return code, _clip(buffer.getvalue())


# --- config -------------------------------------------------------------------
def _section(operation: str) -> dict:
    return config_section(operation)


def name_defect(value: object, where: str) -> str:
    """'' when `value` may be a step name, else why not."""
    if not isinstance(value, str):
        return f'{where} must be a string, got {value!r}'
    if len(value) > STEP_NAME_MAX:
        return (f'{where} names a step {len(value)} characters long; the '
                f'limit is {STEP_NAME_MAX}')
    if not STEP_NAME.match(value):
        return (f'{where} is not a step name: {value!r} — a step name is '
                f'lowercase letters, digits and hyphens, starting with a '
                f'letter')
    return ''


def steps_for(operation: str, registry: dict | None = None) -> tuple[str, ...]:
    """The ordered step list for `operation`, from `[<operation>] steps`.

    A repo with NO `devkit.toml` and a repo declaring exactly the stock list
    produce the same tuple, byte for byte — rule 5, and the reason the default
    is a named constant rather than a literal inside this function.

    Duplicates COLLAPSE in declaration order, the way `gates_extra.targets()`
    already rules, and the collapse is REPORTED rather than silent: a list a
    project wrote and a list this walked that differ without a word is the
    quiet narrowing this whole module refuses.
    """
    sect = _section(operation)
    known = registry_for(operation) if registry is None else registry
    raw = sect.get('steps')
    if raw is None:
        # No default list for an operation this package ships no registry for.
        # `plan_defect` then refuses "the list is empty" — which is the true
        # sentence, and better than inventing a plausible one.
        return DEFAULT_STEPS.get(operation, ())
    if not isinstance(raw, list):
        raise ConfigError(
            f'[{operation}] steps must be a list of strings, got {raw!r}'
            + (f' — write steps = [{raw!r}]' if isinstance(raw, str) else ''))
    if not raw:
        raise ConfigError(
            f'[{operation}] steps is empty — remove the key to take the '
            f'default ({" ".join(DEFAULT_STEPS.get(operation, ()))}) rather '
            f'than declaring nothing')
    seen: list[str] = []
    duplicates: list[str] = []
    for index, value in enumerate(raw, start=1):
        defect = name_defect(value, f'[{operation}] steps #{index}')
        if defect:
            raise ConfigError(defect)
        if value in seen:
            duplicates.append(value)
            continue
        seen.append(value)
    unknown = [n for n in seen if n not in known]
    if unknown:
        raise ConfigError(
            f'[{operation}] steps names {", ".join(repr(u) for u in unknown)}, '
            f'which no step is registered for — the known steps are: '
            f'{", ".join(sorted(known))}')
    if duplicates:
        # Reported, not silent, and not fatal: the collapse is well-defined.
        print(f'[{operation}] steps names '
              f'{", ".join(repr(d) for d in dict.fromkeys(duplicates))} more '
              f'than once — collapsed in declaration order')
    return tuple(seen)


def commands_for(operation: str, names: tuple[str, ...] | None = None,
                 registry: dict | None = None) -> dict[str, str]:
    """`[<operation>.commands]`, merged over the shipped defaults.

    A command string is REFUSED OR RUN WHOLE — it is never sanitised into
    safety. It is the project's own command, written into the project's own
    file, and this package adds no shell of its own beyond handing the string
    to one. What is refused is the shape that cannot be what it claims: a
    non-string, an empty string, a key naming a step that is not in the list,
    and a key naming a step whose kind cannot take a command at all.

    A JUDGEMENT step with NO entry here is **not** a config error. It is the
    legal shape: the operator is asked, and the driver refuses to advance. That
    sentence is in this docstring because "it passed and I do not know why" is
    the shape of a false PASS.
    """
    known = registry_for(operation) if registry is None else registry
    listed = steps_for(operation, known) if names is None else names
    sect = _section(operation)
    raw = sect.get('commands')
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f'[{operation}.commands] must be a table of step = "command", got '
            f'{raw!r}')
    out = {k: v for k, v in DEFAULT_COMMANDS.items() if k in listed}
    for key, value in raw.items():
        defect = name_defect(key, f'[{operation}.commands] key')
        if defect:
            raise ConfigError(defect)
        if not isinstance(value, str):
            raise ConfigError(
                f'[{operation}.commands] {key} must be one command string, '
                f'got {value!r}')
        if not value.strip():
            raise ConfigError(
                f'[{operation}.commands] {key} is empty — an empty command is '
                f'not "no command", it is a mistake; remove the key')
        step = known.get(key)
        if step is None:
            raise ConfigError(
                f'[{operation}.commands] {key} names no registered step — the '
                f'known steps are: {", ".join(sorted(known))}')
        if step.kind is StepKind.AUTOMATIC:
            raise ConfigError(
                f'[{operation}.commands] {key} is an AUTOMATIC step, which '
                f'this code performs — a command here would be two '
                f'authorities over one postcondition')
        if key not in listed:
            raise ConfigError(
                f'[{operation}.commands] {key} is not in [{operation}] steps, '
                f'so it never runs — a command for a step that never runs is a '
                f'belief about the release that is not true')
        out[key] = value
    return out


def validate_config(operation: str, names: tuple[str, ...],
                    registry: dict) -> None:
    """Read EVERY `[<operation>]` key this module will need, and refuse now.

    A config value that is only read when its step is reached is a config error
    that surfaces halfway through a release — after `version-sync` has written
    two files. Every key is therefore read before the first step runs, which is
    the same rule `main` already applies to the run-state destination: a run
    that performs half a release and then refuses has broken the promise.
    """
    commands_for(operation, names, registry)
    _timeout(operation)
    if 'readme-pins' in names:
        _pin_files_of(operation)
    if 'changelog-unreleased-nonempty' in names or 'changelog-retitle' in names:
        _changelog_of(operation)
    if 'pin-bumped' in names:
        _pin_file_of(operation)
    if 'runner-targets-resolve' in names:
        _runner_targets_of(operation)


def _timeout(operation: str) -> int:
    value = _section(operation).get('command_timeout', DEFAULT_COMMAND_TIMEOUT)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(
            f'[{operation}] command_timeout must be a positive integer number '
            f'of seconds, got {value!r}')
    return value


def _pin_files_of(operation: str) -> tuple[str, ...]:
    raw = _section(operation).get('pin_files', ['README.md'])
    if (not isinstance(raw, list) or not raw
            or not all(isinstance(v, str) and v.strip() for v in raw)):
        raise ConfigError(
            f'[{operation}] pin_files must be a non-empty list of paths, '
            f'got {raw!r}')
    return tuple(raw)


def _pin_files(ctx: Context) -> tuple[str, ...]:
    return _pin_files_of(ctx.operation)


def _changelog_of(operation: str) -> str:
    raw = _section(operation).get('changelog', 'CHANGELOG.md')
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(
            f'[{operation}] changelog must be a path, got {raw!r}')
    return raw


def _changelog(ctx: Context) -> Path:
    return ctx.root / _changelog_of(ctx.operation)


def _pin_file_of(operation: str) -> str:
    """Where the consumer's `DEVKIT_VERSION` line lives. Its own file, in its
    own repo, and this package reads it and never writes it."""
    raw = _section(operation).get('pin_file', DEFAULT_PIN_FILE)
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(
            f'[{operation}] pin_file must be one path, got {raw!r}')
    return raw


def _runner_targets_of(operation: str) -> tuple[str, ...]:
    """The make targets `runner-targets-resolve` asks make to compose."""
    raw = _section(operation).get('runner_targets',
                                  list(DEFAULT_RUNNER_TARGETS))
    if (not isinstance(raw, list) or not raw
            or not all(isinstance(v, str) and v.strip() for v in raw)):
        raise ConfigError(
            f'[{operation}] runner_targets must be a non-empty list of make '
            f'targets, got {raw!r}')
    return tuple(raw)


def _version_files(ctx: Context) -> dict[str, str]:
    """path -> a regex with ONE group holding the version.

    The default is `[pm] version_file` / `version_pattern` — the pair D8 and
    the semver gate already read. One fact, one home: a second default here
    would be a second answer to "where does this project's version live", and
    a project that moved it would have moved it in one place only.
    """
    cfg = _pm_cfg(ctx)
    raw = _section(ctx.operation).get('version_files')
    if raw is None:
        return {cfg.version_file: cfg.version_pattern}
    if not isinstance(raw, dict) or not raw:
        raise ConfigError(
            f'[{ctx.operation}.version_files] must be a non-empty table of '
            f'path = pattern, got {raw!r}')
    out: dict[str, str] = {}
    for path, pattern in raw.items():
        if not isinstance(pattern, str) or not pattern.strip():
            raise ConfigError(
                f'[{ctx.operation}.version_files] {path} must be a regex '
                f'string, got {pattern!r}')
        try:
            compiled = re.compile(pattern)
        except re.error as err:
            raise ConfigError(
                f'[{ctx.operation}.version_files] {path} is not a valid '
                f'regex: {err}') from err
        if compiled.groups != 1:
            raise ConfigError(
                f'[{ctx.operation}.version_files] {path} must carry exactly '
                f'one capture group holding the version, got '
                f'{compiled.groups}')
        out[path] = pattern
    return out


# --- running a project's command ----------------------------------------------
def run_command(ctx: Context, step: str, command: str) -> Answer:
    """Run `command` in the checkout; exit 0 is TRUE and nothing else is.

    A non-zero exit, a timeout and an unspawnable command are three different
    sentences and none of them is a pass. Output is BOUNDED into the detail:
    a step's line is a line, and a command that writes 100 MB to stdout must
    still produce something a human reads.
    """
    try:
        done = subprocess.run(command, cwd=str(ctx.root), shell=True,
                              capture_output=True, text=True,
                              timeout=_timeout(ctx.operation))
    except subprocess.TimeoutExpired:
        return Answer.no(
            f'`{_clip(command, 120)}` did not finish inside '
            f'{_timeout(ctx.operation)}s — the step is not done and the run '
            f'stops')
    except OSError as err:
        return Answer.unverifiable(
            f'`{_clip(command, 120)}` could not be run ({err})')
    tail = _clip(done.stdout + done.stderr)
    if done.returncode == 0:
        return Answer.yes(f'`{_clip(command, 120)}` exited 0')
    return Answer.no(f'`{_clip(command, 120)}` exited {done.returncode}'
                     + (f' — {tail}' if tail else ''))


# One walk's answer to `[<operation>.commands]`, keyed by the checkout, the
# operation, and the BYTES of the devkit.toml it was derived from — see
# `_configured`. Not an lru_cache: the key has to include the file's content or
# the memo would outlive the config it caches, and a test that rewrites
# devkit.toml under one root would then grade the next case against the last
# one's answer.
_COMMANDS_MEMO: dict[tuple[str, str, bytes | None], dict[str, str]] = {}


def _configured(ctx: Context, step: str) -> str:
    """`[<operation>.commands] <step>`, or '' — asked ONCE per run.

    A3 (`docs/reviews/2026-09-05-adopt-is-a-conveyor.md`): this was
    `commands_for(ctx.operation)` with no `names`, so every one of the ten
    steps that asks it re-entered `steps_for` -> `registry_for` -> `_section`,
    and `load_config` re-parses `devkit.toml` from disk on every call (it is
    deliberately not cached — `tests/test_boundaries.py` primitive 6 refuses
    config bound at import). The visible half was noise: a `[adopt] steps` list
    with a duplicate name printed `steps names 'x' more than once — collapsed
    in declaration order` once per asking step rather than once per run.

    Memoised on the config's own bytes rather than passed down from
    `validate_config`, which already computed it: the driver builds `Context`
    frozen and empty (`driver.py:899`), so there is no seam to pass it through
    without changing what every step is handed. The key makes the memo a
    DERIVATION and not a memory — same checkout, same operation, same
    devkit.toml bytes is the same answer by construction, and any of the three
    changing re-derives it.
    """
    from agentic_sdlc.core.project import CONFIG_NAME, repo_root

    path = repo_root() / CONFIG_NAME
    try:
        raw: bytes | None = path.read_bytes() if path.is_file() else None
    except OSError:
        raw = None
    key = (str(ctx.root), ctx.operation, raw)
    if key not in _COMMANDS_MEMO:
        _COMMANDS_MEMO[key] = commands_for(ctx.operation)
    return _COMMANDS_MEMO[key].get(step, '')


def _judged_by_command(ctx: Context, step: str, must: str) -> Answer:
    """The shape of `pr-open` / `ci-green` / `prove-artifact`.

    With a command, the command decides. WITHOUT one the answer is
    UNVERIFIABLE, which is a refusal to advance — never a pass. That is the
    whole difference between this machine and the prose it replaces.
    """
    command = _configured(ctx, step)
    if not command:
        return Answer.unverifiable(
            f'no [{ctx.operation}.commands] {step} is configured, and this '
            f'package ships no default for it — {must}')
    return run_command(ctx, step, command)


# --- the pm predicates this module CALLS --------------------------------------
def ready_for(ctx: Context, target: str) -> Answer:
    """`pm ready-for <target> <milestone>`, reported — never re-implemented.

    Called through `pm.cli.main`, which is the published contract (0 ready,
    1 not ready naming the blockers, 2 usage). Reaching past it into the
    module's internals would couple this registry to a shape that is somebody
    else's to change.
    """
    import contextlib
    import io

    try:
        from agentic_sdlc.repo.pm import cli as pm_cli
    except ImportError as err:                      # pragma: no cover - defence
        return Answer.unverifiable(f'pm is not importable ({err})')
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(buffer):
            code = pm_cli.main(['ready-for', target, ctx.version])
    except ImportError as err:
        # `pm ready-for` is shipped by `0.2.0/the-belts-refuse-to-advance`. If
        # it is not in the tree yet, this is UNVERIFIABLE — a refusal to
        # advance — and never an optimistic pass.
        return Answer.unverifiable(
            f'`pm ready-for {target}` is not available in this build ({err}); '
            f'the conveyor will not advance past a predicate it cannot ask')
    said = _clip(buffer.getvalue())
    if code == 0:
        return Answer.yes(said or f'`pm ready-for {target}` exited 0')
    if code == 1:
        return Answer.no(said or f'`pm ready-for {target}` exited 1')
    return Answer.unverifiable(
        f'`pm ready-for {target}` exited {code} — a usage or config error, so '
        f'nothing was decided: {said}')


def _pm(ctx: Context, *argv: str) -> str:
    """One `pm` verb, run in process. A status flip goes through the CLI, never
    a regex over frontmatter — `check pm` is the drift gate and it reads what
    the CLI writes."""
    import contextlib
    import io

    from agentic_sdlc.repo.pm import cli as pm_cli
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = pm_cli.main(list(argv))
    return f'`pm {" ".join(argv)}` exited {code}: {_clip(buffer.getvalue())}'


def _status_at_or_past(ctx: Context, wanted: str) -> Answer:
    cfg = _pm_cfg(ctx)
    path = model.milestone_file(cfg, ctx.version)
    if path is None:
        return Answer.unverifiable(
            f'no milestone document for {ctx.version} under '
            f'{cfg.roadmap_dir}/ — nothing carries a status to read')
    status = model.field_of(path, 'status')
    states = cfg.milestone_states
    if status not in states:
        return Answer.unverifiable(
            f'{cfg.rel(path)} carries status {status!r}, which is not one of '
            f'{", ".join(states)}')
    if states.index(status) >= states.index(wanted):
        return Answer.yes(f'{cfg.rel(path)} is {status!r}')
    return Answer.no(f'{cfg.rel(path)} is {status!r}, not {wanted!r} or later')


# --- the steps ----------------------------------------------------------------
def _belt_written(ctx: Context) -> str:
    """The one TRACKED path a walk of this belt dirties by itself, or ''.

    R6 (`docs/reviews/2026-09-05-the-release-is-a-conveyor.md`). Story 04's
    reasoning — *"the ledger is tracked, so a row per completed step would
    dirty the tree and falsify `tree-clean`"* — is why the driver writes only
    deviations. The driver honours it; step 10 does not. `gate` runs the
    project's gate command, the installed `gdk_gate.sh` recorder files a
    `{"kind":"gate",…}` cost row per gate through `GDK_LEDGER_CMD`, and those
    rows land in the same TRACKED `<milestone>/ledger.jsonl`. Measured on a
    stock consumer with the milestone `building`, ledger committed clean:

        $ make check           # one gate, through the shipped runner
        $ git status --porcelain
         M pm/roadmap/1.0.0-m/ledger.jsonl

    Nothing here can stop that write, and nothing here should: the cost rows
    are the record `pm ledger report` is built on. What it CAN stop is the
    false attribution — `tree-clean` counted that path with the operator's own
    and `do()` told them to "commit or stash your own paths" about a file the
    belt wrote. The census is unchanged (rule 4: nothing is excluded, nothing
    is un-counted); only the sentence knows whose path it is.
    """
    from agentic_sdlc.repo.pm import ledger

    cfg = _pm_cfg(ctx)
    path = model.milestone_file(cfg, ctx.version)
    return '' if path is None else cfg.rel(ledger.ledger_path(path.parent))


def check_tree_clean(ctx: Context) -> Answer:
    # `strip=False`: column 0 is a space for a worktree-only change, and a
    # stripped first line loses it — see `_git`.
    code, out = _git(ctx, 'status', '--porcelain', strip=False)
    if code != 0:
        return Answer.unverifiable(f'git status failed: {_clip(out)}')
    if not out.strip():
        return Answer.yes('no modified paths')
    paths = [line[3:] for line in out.split('\n') if len(line) > 3]
    mine = _belt_written(ctx)
    said = f'{len(paths)} modified path(s): {_clip(", ".join(paths))}'
    if mine and mine in paths:
        # Named, never subtracted (R6): the count above still holds every path.
        said += (f' — {mine} is the belt\'s OWN, the gate cost rows `gate` '
                 f'filed on this run')
    return Answer.no(said)


def do_tree_clean(ctx: Context) -> str:
    mine = _belt_written(ctx)
    return ('commit or stash your own paths — this machine never commits for '
            'you, and a release cut from a tree it changed is a release '
            'nobody reviewed'
            + (f'. {mine} is not one of yours: `gate` filed its cost rows '
               f'there this run, and they are a record worth committing (R6)'
               if mine else ''))


def check_on_milestone_branch(ctx: Context) -> Answer:
    cfg = _pm_cfg(ctx)
    path = model.milestone_file(cfg, ctx.version)
    if path is None:
        return Answer.unverifiable(
            f'no milestone document for {ctx.version} to read a branch: from')
    declared = model.field_of(path, 'branch')
    if not declared:
        return Answer.unverifiable(
            f'{cfg.rel(path)} carries no `branch:` stamp — D9 exists so a '
            f'fresh session never has to guess at `git branch -a`, and this '
            f'step will not assume the current branch is the right one')
    here = _branch(ctx)
    if here == declared:
        return Answer.yes(f'HEAD is {here!r}')
    return Answer.no(f'HEAD is {here!r}; {cfg.rel(path)} declares '
                     f'branch: {declared!r}')


def do_on_milestone_branch(ctx: Context) -> str:
    cfg = _pm_cfg(ctx)
    path = model.milestone_file(cfg, ctx.version)
    declared = model.field_of(path, 'branch') if path is not None else ''
    return f'switch to {declared!r} — `git switch {declared}`' if declared \
        else 'stamp `branch:` on the milestone document (D9), then re-run'


def _refresh(ctx: Context, branch: str) -> str:
    """'' when `origin/<branch>` now matches the remote, else why it does not.

    A remote-tracking ref is a CACHE of somebody else's repository, and git
    refreshes it only when asked. `check repo-hygiene`
    (`repo/checks/repo_hygiene.py:39-44`) already opens with
    `git fetch --prune origin --quiet` for exactly this reason, and it costs no
    rule here: rule 2 forbids booting an engine and reading generated cache
    state, not asking git a question — `check_tag` below already calls
    `git ls-remote`.
    """
    code, out = _git(ctx, 'fetch', '--quiet', 'origin', branch)
    return '' if code == 0 else (_clip(out, 120) or f'git fetch exited {code}')


def check_main_merged(ctx: Context) -> Answer:
    """The mainline is an ancestor of HEAD — asked of a REFRESHED ref.

    R7 (`docs/reviews/2026-09-05-the-release-is-a-conveyor.md`): this read
    `origin/<mainline>` and never fetched, while its own `do()` says
    `git fetch origin && git merge origin/<mainline>`. Measured on a clone
    whose `origin/main` was two commits behind the remote's `main`:

        local origin/main: 6c12867…   remote main: 041fc6e…
        -> Answer(TRUE, 'origin/main is an ancestor of HEAD')

    TRUE for "the mainline is in this tree" about a mainline that had moved on
    — a gate that missed real drift and printed PASS, off a ref nothing
    updated. So the ref is refreshed first, and if it cannot be, the answer is
    UNVERIFIABLE rather than a guess: `check_tag` (:1281-1284) already rules
    that shape — what the remote holds is a fact about the remote and this will
    not answer it from the local ref.
    """
    mainline = model.mainline_branch()
    stale = _refresh(ctx, mainline)
    for ref in (f'origin/{mainline}', mainline):
        code, _ = _git(ctx, 'rev-parse', '--verify', '--quiet', ref)
        if code != 0:
            continue
        if stale and ref.startswith('origin/'):
            return Answer.unverifiable(
                f'{ref} could not be refreshed ({stale}) — what the mainline '
                f'contains is a fact about the remote, and a remote-tracking '
                f'ref nothing updated is a guess at it, not an answer')
        code, out = _git(ctx, 'merge-base', '--is-ancestor', ref, 'HEAD')
        if code == 0:
            return Answer.yes(f'{ref} is an ancestor of HEAD')
        return Answer.no(f'{ref} is not an ancestor of HEAD — merge it in '
                         f'before the release reads this tree')
    # No `origin/<mainline>` AND no local `<mainline>`: a fetch failure here is
    # the ordinary shape of a repo with no remote at all, so it is not the
    # sentence — the missing ref is.
    return Answer.unverifiable(
        f'neither origin/{mainline} nor {mainline} resolves in this checkout')


def do_main_merged(ctx: Context) -> str:
    mainline = model.mainline_branch()
    return (f'`git fetch origin && git merge origin/{mainline}` — the release '
            f'answers for a tree that contains the mainline')


def _unreleased_span(text: str) -> tuple[int, int, list[str]] | str:
    """(start, end, body-lines) of the ONE `## Unreleased` section, or why not.

    Two headings is a refusal, not a choice of the first: a retitle that picked
    one of them would leave the other behind and the file would carry two
    stories about the same release.
    """
    lines = text.split('\n')
    at = [i for i, line in enumerate(lines)
          if line.strip().lower().startswith('## unreleased')]
    if not at:
        return 'there is no `## Unreleased` heading'
    if len(at) > 1:
        return (f'there are {len(at)} `## Unreleased` headings (lines '
                f'{", ".join(str(i + 1) for i in at)}) — ambiguous, and this '
                f'never retitles the first one')
    start = at[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('## '):
            end = i
            break
    return start, end, lines[start + 1:end]


def check_changelog_unreleased_nonempty(ctx: Context) -> Answer:
    path = _changelog(ctx)
    if not path.is_file():
        return Answer.unverifiable(
            f'{path.name} is not at {path} — this step reads the release '
            f'notes and never creates the file')
    span = _unreleased_span(_read(path))
    if isinstance(span, str):
        return Answer.no(f'{path.name}: {span}')
    _, _, body = span
    bullets = [line for line in body
               if line.lstrip().startswith(('-', '*', '+'))]
    if bullets:
        return Answer.yes(f'{path.name} `## Unreleased` holds '
                          f'{len(bullets)} bullet(s)')
    return Answer.no(f'{path.name} `## Unreleased` holds no bullet — the '
                     f'notes are written as the work lands, one bullet per '
                     f'consumer-visible change')


def do_changelog_unreleased_nonempty(ctx: Context) -> str:
    return ('write the notes now, from the diff since the last tag — this '
            'machine does not invent release notes')


def check_review_landed(ctx: Context) -> Answer:
    return ready_for(ctx, 'tag')


def do_review_landed(ctx: Context) -> str:
    return ('land or explicitly defer every finding the review raised, then '
            're-run — the gate answers for the tree the review passed')


def _version_in(ctx: Context, rel: str, pattern: str) -> tuple[str | None, str]:
    path = ctx.root / rel
    if not path.is_file():
        return None, f'{rel} is not in this checkout'
    compiled = re.compile(pattern)
    for line in _read(path).split('\n'):
        match = compiled.match(line.strip())
        if match:
            return match.group(1), ''
    return None, f'{rel} carries no line matching {pattern!r}'


def check_version_sync(ctx: Context) -> Answer:
    files = _version_files(ctx)
    found: list[str] = []
    wrong: list[str] = []
    for rel, pattern in files.items():
        value, defect = _version_in(ctx, rel, pattern)
        if value is None:
            return Answer.unverifiable(defect)
        found.append(f'{rel} says {value}')
        if value != ctx.version:
            wrong.append(f'{rel} says {value}')
    if not files:
        return Answer.unverifiable('no version file is configured')
    if not wrong:
        return Answer.yes(f'{len(files)} version site(s) say {ctx.version}')
    return Answer.no(f'{"; ".join(found)} — the release is {ctx.version}')


def do_version_sync(ctx: Context) -> str:
    plan = apply.Plan()
    touched: list[str] = []
    for rel, pattern in _version_files(ctx).items():
        path = ctx.root / rel
        if not path.is_file():
            continue
        compiled = re.compile(pattern)
        lines = _read(path).split('\n')
        out: list[str] = []
        changed = False
        for line in lines:
            match = compiled.match(line.strip())
            if match and match.group(1) != ctx.version:
                start, end = match.span(1)
                offset = line.index(line.strip())
                out.append(line[:offset + start] + ctx.version
                           + line[offset + end:])
                changed = True
            else:
                out.append(line)
        if changed:
            plan.overwrite(path, '\n'.join(out), newline=None, label=rel)
            touched.append(rel)
    if not touched:
        return 'no version site needed rewriting'
    plan.apply(decide=False)
    return f'rewrote {", ".join(touched)} to {ctx.version}'


def _pin_sites(text: str) -> list[tuple[int, str]]:
    """The `vX.Y.Z` tokens inside FENCED CODE BLOCKS, with their line numbers.

    A pin is a string a consumer COPY-PASTES, and copy-pasted strings live in
    fenced blocks. Prose naming an older tag ("v0.2.0 is this package's first
    tag") is HISTORY and is never rewritten — a release that edited it would
    make the document say something false, which is the write-side cardinal
    sin with a regex in front of it.
    """
    from agentic_sdlc.core import markdown

    lines = text.split('\n')
    fenced, _ = markdown.fenced_flags(lines)
    sites: list[tuple[int, str]] = []
    for number, (line, inside) in enumerate(zip(lines, fenced), 1):
        if not inside:
            continue
        for token in _SEMVER_TAG.findall(line):
            sites.append((number, token))
    return sites


def check_readme_pins(ctx: Context) -> Answer:
    want = f'v{ctx.version}'
    census = 0
    stale: list[str] = []
    missing: list[str] = []
    for rel in _pin_files(ctx):
        path = ctx.root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        for number, token in _pin_sites(_read(path)):
            census += 1
            if token != want:
                stale.append(f'{rel}:{number} {token}')
    if missing:
        return Answer.unverifiable(
            f'[{ctx.operation}] pin_files names {", ".join(missing)}, which '
            f'this checkout does not have')
    if stale:
        return Answer.no(f'{len(stale)} of {census} pin site(s) do not say '
                         f'{want}: {_clip(", ".join(stale))}')
    # Rule 4: a census of zero is REPORTED, loudly, rather than passed over.
    if census == 0:
        return Answer.unverifiable(
            f'{", ".join(_pin_files(ctx))} carries no vX.Y.Z pin inside a '
            f'fenced block — a scan of zero sites is not a pass; set '
            f'[{ctx.operation}] pin_files, or remove the step')
    return Answer.yes(f'{census} pin site(s) say {want}')


def do_readme_pins(ctx: Context) -> str:
    from agentic_sdlc.core import markdown

    want = f'v{ctx.version}'
    plan = apply.Plan()
    touched: list[str] = []
    for rel in _pin_files(ctx):
        path = ctx.root / rel
        if not path.is_file():
            continue
        lines = _read(path).split('\n')
        fenced, _ = markdown.fenced_flags(lines)
        out = [(_SEMVER_TAG.sub(want, line) if inside else line)
               for line, inside in zip(lines, fenced)]
        if out != lines:
            plan.overwrite(path, '\n'.join(out), newline=None, label=rel)
            touched.append(rel)
    if not touched:
        return 'no pin site needed rewriting'
    plan.apply(decide=False)
    return f'rewrote the pins in {", ".join(touched)} to {want}'


def check_features_done(ctx: Context) -> Answer:
    return ready_for(ctx, 'milestone')


def do_features_done(ctx: Context) -> str:
    return ('close each feature through the pm CLI — `pm feature done <fid> '
            '--review-record <path>` — never by editing frontmatter')


def _flip(wanted: str):
    def check(ctx: Context) -> Answer:
        return _status_at_or_past(ctx, wanted)

    def do(ctx: Context) -> str:
        return _pm(ctx, 'milestone', wanted, ctx.version)

    return check, do


def check_gate(ctx: Context) -> Answer:
    command = _configured(ctx, 'gate')
    if not command:
        return Answer.unverifiable(
            f'no [{ctx.operation}.commands] gate is configured — name the '
            f'full gate this project runs')
    return run_command(ctx, 'gate', command)


def check_changelog_retitle(ctx: Context) -> Answer:
    path = _changelog(ctx)
    if not path.is_file():
        return Answer.unverifiable(f'{path} is not in this checkout')
    text = _read(path)
    heading = re.compile(
        rf'^## v{re.escape(ctx.version)} — \d{{4}}-\d{{2}}-\d{{2}}\s*$')
    lines = text.split('\n')
    at = [i for i, line in enumerate(lines) if heading.match(line.rstrip('\r'))]
    if not at:
        return Answer.no(
            f'{path.name} has no `## v{ctx.version} — <ISO date>` heading')
    span = _unreleased_span(text)
    if isinstance(span, str):
        return Answer.no(f'{path.name}: {span} above the release heading')
    start, _, body = span
    if start > at[0]:
        return Answer.no(f'{path.name}: `## Unreleased` sits BELOW '
                         f'`## v{ctx.version}` — a fresh section goes above')
    if any(line.strip() for line in body):
        return Answer.no(f'{path.name}: the `## Unreleased` section above '
                         f'`## v{ctx.version}` is not empty')
    return Answer.yes(f'{path.name} carries `## v{ctx.version}` under a fresh '
                      f'`## Unreleased`')


def do_changelog_retitle(ctx: Context) -> str:
    from datetime import date

    path = _changelog(ctx)
    if not path.is_file():
        return f'{path} is not in this checkout'
    text = _read(path)
    span = _unreleased_span(text)
    if isinstance(span, str):
        return f'{path.name}: {span} — refusing to retitle'
    start, _, _ = span
    lines = text.split('\n')
    eol = '\r' if lines[start].endswith('\r') else ''
    lines[start] = f'## v{ctx.version} — {date.today().isoformat()}{eol}'
    fresh = [f'## Unreleased{eol}', eol]
    lines[start:start] = fresh
    apply.Plan().overwrite(path, '\n'.join(lines), newline=None,
                           label=path.name).apply(decide=False)
    return (f'retitled `## Unreleased` to `## v{ctx.version}` and opened a '
            f'fresh empty one above it')


def check_findings_resolved(ctx: Context) -> Answer:
    """SDLC.md close protocol step 5: every `docs/reviews/` record for this
    milestone RESOLVED AND DELETED. It had no step in the planned list, so the
    machine would have shipped a protocol shorter than the prose it replaces.
    """
    cfg = _pm_cfg(ctx)
    base = ctx.root / cfg.review_dir
    if not base.is_dir():
        return Answer.yes(f'{cfg.review_dir}/ holds no review record')
    # `core.walk`, not `rglob`: a walk that returns one list has nowhere to put
    # what it DROPPED, and this step's whole job is to notice a record that is
    # still there. `.md` is a UNIVERSE declaration here, so `<REPORT>.MD` is
    # seen — a review record nobody's glob matched is exactly the finding this
    # would otherwise report as resolved.
    found = walk.descendants(base, walk.Kind.FILE, suffix='.md')
    naming: list[str] = []
    for path in found:
        try:
            text = _read(path)
        except (OSError, UnicodeDecodeError):
            return Answer.unverifiable(f'{cfg.rel(path)} could not be read')
        if ctx.version in path.name or ctx.version in text:
            naming.append(cfg.rel(path))
    if naming:
        return Answer.no(f'{len(naming)} review record(s) still name '
                         f'{ctx.version}: {_clip(", ".join(naming))}')
    return Answer.yes(f'no record under {cfg.review_dir}/ names {ctx.version}')


def do_findings_resolved(ctx: Context) -> str:
    return ('resolve each record and DELETE it (create → resolve → delete) — '
            'the resolution belongs in the grain\'s decisions.md, and a '
            'review doc left behind outlives the milestone it answered')


def check_push_branch(ctx: Context) -> Answer:
    here = _branch(ctx)
    mainline = model.mainline_branch()
    if here == mainline:
        return Answer.unverifiable(
            f'HEAD is {mainline!r} — a release is a PR merge and a tag, never '
            f'a push of the mainline, which is what the pre-push hook exists '
            f'to block; nothing was pushed')
    code, upstream = _git(ctx, 'rev-parse', '--abbrev-ref', '@{u}')
    if code != 0:
        return Answer.no(f'{here!r} has no upstream yet — `git push -u origin '
                         f'{here}`')
    local = _git(ctx, 'rev-parse', 'HEAD')[1]
    remote = _git(ctx, 'rev-parse', upstream)[1]
    if local and local == remote:
        return Answer.yes(f'{here!r} matches {upstream} at {local[:12]}')
    return Answer.no(f'{here!r} is at {local[:12]}; {upstream} is at '
                     f'{remote[:12]}')


def do_push_branch(ctx: Context) -> str:
    here = _branch(ctx)
    mainline = model.mainline_branch()
    if here == mainline:
        return f'refusing to push {mainline!r}; nothing was pushed'
    code, out = _git(ctx, 'push', '-u', 'origin', here)
    return f'`git push -u origin {here}` exited {code}: {_clip(out)}'


def check_pr_open(ctx: Context) -> Answer:
    mainline = model.mainline_branch()
    return _judged_by_command(
        ctx, 'pr-open',
        f'open (or update) the PR from {_branch(ctx)!r} to {mainline!r} and '
        f're-run, or configure a command that answers it')


def do_pr_open(ctx: Context) -> str:
    return ('open the PR against the mainline — this package has no GitHub '
            'client and never will (hard rule 1)')


def check_ci_green(ctx: Context) -> Answer:
    return _judged_by_command(
        ctx, 'ci-green',
        'confirm the required checks on this PR are green and re-run, or '
        'configure a command that answers it')


def do_ci_green(ctx: Context) -> str:
    return 'wait for the required checks on the PR to go green'


def check_merge(ctx: Context) -> Answer:
    mainline = model.mainline_branch()
    head = _git(ctx, 'rev-parse', 'HEAD')[1]
    for ref in (f'origin/{mainline}', mainline):
        code, _ = _git(ctx, 'rev-parse', '--verify', '--quiet', ref)
        if code != 0:
            continue
        code, _ = _git(ctx, 'merge-base', '--is-ancestor', 'HEAD', ref)
        if code == 0:
            return Answer.yes(f'{ref} contains {head[:12]}')
        return Answer.no(f'{ref} does not contain {head[:12]}')
    return Answer.unverifiable(
        f'neither origin/{mainline} nor {mainline} resolves in this checkout')


def do_merge(ctx: Context) -> str:
    return ('merge the PR as a MERGE COMMIT — the mainline is '
            'merge-commit-only at close, and a squash loses the milestone\'s '
            'range')


def check_tag(ctx: Context) -> Answer:
    tag = f'v{ctx.version}'
    code, _ = _git(ctx, 'rev-parse', '--verify', '--quiet', f'refs/tags/{tag}')
    local = code == 0
    code, out = _git(ctx, 'ls-remote', '--tags', 'origin', tag)
    if code != 0:
        return Answer.unverifiable(
            f'the remote could not be asked about {tag} ({_clip(out)}) — '
            f'"published" is a fact about the remote and this will not guess '
            f'it from the local ref')
    remote = bool(out.strip())
    if local and remote:
        return Answer.yes(f'{tag} exists locally and on origin')
    return Answer.no(f'{tag} is '
                     f'{"present" if local else "absent"} locally and '
                     f'{"present" if remote else "absent"} on origin')


def do_tag(ctx: Context) -> str:
    tag = f'v{ctx.version}'
    code, _ = _git(ctx, 'rev-parse', '--verify', '--quiet', f'refs/tags/{tag}')
    said = []
    if code != 0:
        said.append(f'`git tag {tag}` exited {_git(ctx, "tag", tag)[0]}')
    # The TAG ref only. `git push origin <mainline>` is exactly what the
    # pre-push hook exists to block, and the merge already put the commits
    # there. A published tag is never force-moved: a bad release is a new
    # patch version.
    code, out = _git(ctx, 'push', 'origin', f'refs/tags/{tag}')
    said.append(f'`git push origin refs/tags/{tag}` exited {code}: '
                f'{_clip(out)}')
    return '; '.join(said)


def check_prove_artifact(ctx: Context) -> Answer:
    return _judged_by_command(
        ctx, 'prove-artifact',
        f'run whatever proves the PUBLISHED artifact is {ctx.version} and '
        f're-run — the proof names a git URL, which is this project\'s own '
        f'fact and not something this package may ship a default for '
        f'(hard rule 8)')


def do_prove_artifact(ctx: Context) -> str:
    return ('prove the published artifact reports the new version, from a '
            'cold cache')


# --- the adopt steps ----------------------------------------------------------
# Every one of these is a question about the LOCAL tree. Hard rule 8 is not
# background here: `adopt` is the verb that RUNS in somebody else's repo, and
# the temptation to read a second one is `pin-bumped`'s — answered by comparing
# the consumer's own line to the version of the package that is running.
def check_pin_bumped(ctx: Context) -> Answer:
    rel = _pin_file_of(ctx.operation)
    path = ctx.root / rel
    want = f'v{__version__}'
    if not path.is_file():
        return Answer.unverifiable(
            f'{rel} is not in this checkout, so there is no `DEVKIT_VERSION` '
            f'line to read — this step never creates one; write '
            f'`DEVKIT_VERSION := {want}` above `include {FRAMEWORK_MAKEFILE}`, '
            f'or point [{ctx.operation}] pin_file at the file that carries it')
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError):
        return Answer.unverifiable(f'{rel} could not be read as text')
    for number, line in enumerate(text.split('\n'), start=1):
        match = PIN_LINE.match(line)
        if not match:
            continue
        found = match.group(1).strip('"\'')
        if found.lstrip('v') == __version__:
            return Answer.yes(f'{rel}:{number} pins {found}, which is the '
                              f'version running here')
        return Answer.no(
            f'{rel}:{number} pins {found}; the package running here is '
            f'{__version__} — edit that ONE line to `DEVKIT_VERSION := {want}`. '
            f'It is in a file this package does not own, so nothing here will '
            f'write it')
    return Answer.unverifiable(
        f'{rel} carries no `DEVKIT_VERSION` line — this step reads the pin and '
        f'does not add one')


def do_pin_bumped(ctx: Context) -> str:
    rel = _pin_file_of(ctx.operation)
    return (f'edit `DEVKIT_VERSION` in {rel} to v{__version__} yourself — this '
            f'package edits no file outside its own checkout, and the pin is '
            f'the one line of yours it would have to touch')


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:DIGEST_LENGTH]


def _installable_drift(ctx: Context) -> list[tuple[str, str, str, str]]:
    """(verb, path, verdict, digest) for every file the `install-*` verbs write.

    Asked of `install.PLANS` rather than of a list here: a second inventory of
    the installables would be a second answer to what this version ships, and
    the one that goes stale is this one. A file the consumer never installed is
    `not-installed` and is NOT drift — `adopt` diffs and decides, it does not
    install (that is what the `install-*` verbs are for).
    """
    from agentic_sdlc.repo import install

    out: list[tuple[str, str, str, str]] = []
    for verb, plan in install.PLANS.items():
        for name, rel in plan:
            target = ctx.root / rel
            if not target.is_file():
                out.append((verb, rel, 'not-installed', '-'))
                continue
            digest = _digest(target.read_bytes())
            text, defect = install.read_destination(target)
            try:
                body = install.resolve_body(name, rel)
            except (OSError, UnicodeDecodeError, ConfigError) as err:
                out.append((verb, rel, f'unrenderable({_clip(str(err), 60)})',
                            digest))
                continue
            if text is None:
                out.append((verb, rel, 'unreadable', digest))
                continue
            if text == body:
                out.append((verb, rel, 'current', digest))
            elif install.header_only_difference(text, body):
                # The operator's own project-config header, and the rest of the
                # file byte-current. It is a difference and it is not one to
                # decide about.
                out.append((verb, rel, 'header-only', digest))
            else:
                out.append((verb, rel, 'differs', digest))
    return out


def _drifted(ctx: Context) -> list[str]:
    return [rel for _, rel, verdict, _ in _installable_drift(ctx)
            if verdict == 'differs' or verdict.startswith(
                ('unreadable', 'unrenderable'))]


def _census_block(ctx: Context) -> str:
    rows = '\n'.join(f'- `{rel}` {verdict} {digest} ({verb})'
                     for verb, rel, verdict, digest in _installable_drift(ctx))
    return (f'{CENSUS_OPEN}\n'
            f'installables of agentic-sdlc {__version__}\n\n{rows}\n'
            f'{CENSUS_CLOSE}')


def _report_path(ctx: Context) -> Path:
    return ctx.root / REPORT_REL


def _recorded_census(text: str) -> str:
    if CENSUS_OPEN not in text or CENSUS_CLOSE not in text:
        return ''
    head, _, rest = text.partition(CENSUS_OPEN)
    body, _, _ = rest.partition(CENSUS_CLOSE)
    return f'{CENSUS_OPEN}{body}{CENSUS_CLOSE}'


def check_installables_diffed(ctx: Context) -> Answer:
    """The diff for THIS version has been produced, and it still describes the
    tree.

    The report is not a flag its own `do()` set — it carries the census, each
    file with a digest of the bytes on disk, and this re-derives that census
    and compares. A file edited after the diff was produced makes the report
    STALE and this answers no, which is the whole difference between an
    artifact and a memory.
    """
    path = _report_path(ctx)
    if not path.is_file():
        return Answer.no(
            f'{REPORT_REL} has not been produced — the diff between what this '
            f'version ships and what is installed here is what the next step '
            f'decides about')
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError):
        return Answer.no(f'{REPORT_REL} could not be read as text')
    fresh = _census_block(ctx)
    if _recorded_census(text) != fresh:
        return Answer.no(
            f'{REPORT_REL} does not describe this tree — it was written for a '
            f'different version or the files have changed since; the diff is '
            f'produced again')
    drift = _drifted(ctx)
    return Answer.yes(
        f'{REPORT_REL} holds the census for {__version__}: '
        f'{len(drift)} file(s) differ from what this version ships')


def do_installables_diffed(ctx: Context) -> str:
    """PRINT the diff, and record the census beside the run state.

    Everything from `## decisions` down is the OPERATOR'S and is preserved
    byte-for-byte (rule 3): a regenerated census must not eat the decisions
    somebody wrote under it.
    """
    from agentic_sdlc.repo import install

    path = _report_path(ctx)
    kept = ''
    if path.is_file():
        try:
            existing = _read(path)
        except (OSError, UnicodeDecodeError):
            existing = ''
        _, marker, tail = existing.partition(DECISIONS_HEADING)
        if marker:
            kept = marker + tail
    if not kept:
        kept = (f'{DECISIONS_HEADING}\n\n'
                f'One line per file above marked `differs`, written by YOU:\n'
                f'`<path>: take|hand-applied|keep — why`. `--force` is '
                f'whole-set and has no per-file option, so which replacement '
                f'to take is a decision this package cannot make for you.\n')
    for verb, rel, verdict, _digest_of in _installable_drift(ctx):
        if verdict in ('current', 'not-installed'):
            continue
        name = next(n for n, r in install.PLANS[verb] if r == rel)
        install.print_diff(rel, ctx.root / rel, install.resolve_body(name, rel))
    # The directory too, through the plan: nothing outside `core/apply.py`
    # touches the filesystem, and a writer that decides as it goes lands half
    # a plan when the third step refuses.
    plan = apply.Plan()
    if not path.parent.is_dir():
        plan.make_dir(path.parent, label=str(path.parent.name))
    plan.overwrite(path, f'{_census_block(ctx)}\n\n{kept}', newline=None,
                   label=REPORT_REL).apply(decide=False)
    return f'printed the diff and wrote the census to {REPORT_REL}'


# What may sit LEFT of the path on a decision line and still leave it a
# decision for that path: list markers, quote markers, and the backtick the
# `do()` sentence writes the shape in. Anything else means the path is being
# mentioned inside prose rather than decided.
_DECISION_LEAD = re.compile(r'^[\s>*+-]*`?')


def _decides(line: str, rel: str) -> bool:
    """Is this line a decision FOR `rel` — the whole path, then a verdict?

    A2 (`docs/reviews/2026-09-05-adopt-is-a-conveyor.md`): the test was
    `rel in line and line.split(rel, 1)[1].strip(' :')` — a SUBSTRING anywhere
    on the line with any text after it. Measured on a scratch consumer with
    `tools/hooks/pre-push` drifted and one line written under `## decisions`:

        tools/hooks/pre-push-extra: keep — this is a DIFFERENT file
        -> JUDGEMENT ALREADY-TRUE — 1 drifted file(s), each decided in …

    A decision written for one file satisfied another, and any prose quoting a
    path with a trailing word counted as a decision for it. `install.PLANS`
    holds no substring pair TODAY, which is what kept this latent — and "no
    two shipped paths are prefixes of each other" is not an invariant anything
    asserts, so it goes live the first time a verb ships `a/b` beside `a/b.md`.

    Anchored to the documented shape instead: the line STARTS with the path
    (after a list/quote marker or the `do()` sentence's backtick), the path is
    followed by `:`, and something non-empty follows that colon. Rule 4's
    write-side twin — a record that looks like a decision and is not.
    """
    head = _DECISION_LEAD.sub('', line, count=1)
    if not head.startswith(rel):
        return False
    rest = head[len(rel):].lstrip('`')
    if not rest.startswith(':'):
        return False
    return bool(rest[1:].strip(' :'))


def check_installable_decisions_recorded(ctx: Context) -> Answer:
    """Every file that differs is named in the run's record with a decision.

    A JUDGEMENT because `--force` is whole-set (there is no per-file option),
    so whether to take a replacement or hand-apply the diff is a call only the
    consumer can make. What is checked is the ARTIFACT of that call.
    """
    drift = _drifted(ctx)
    if not drift:
        return Answer.yes(f'no installed file differs from what {__version__} '
                          f'ships — there is nothing to decide')
    path = _report_path(ctx)
    if not path.is_file():
        return Answer.no(
            f'{len(drift)} file(s) differ and {REPORT_REL} is not there — the '
            f'diff is produced first, then decided')
    try:
        _, _, decisions = _read(path).partition(DECISIONS_HEADING)
    except (OSError, UnicodeDecodeError):
        return Answer.no(f'{REPORT_REL} could not be read as text')
    undecided = [rel for rel in drift
                 if not any(_decides(line, rel)
                            for line in decisions.split('\n'))]
    if undecided:
        return Answer.no(
            f'{len(undecided)} of {len(drift)} drifted file(s) carry no '
            f'decision in {REPORT_REL}: {_clip(", ".join(undecided))}')
    return Answer.yes(f'{len(drift)} drifted file(s), each decided in '
                      f'{REPORT_REL}')


def do_installable_decisions_recorded(ctx: Context) -> str:
    return (f'write one line per drifted file under `{DECISIONS_HEADING}` in '
            f'{REPORT_REL} — `<path>: take|hand-applied|keep — why`. Taking a '
            f'replacement is `agentic-sdlc install-<verb> --force`, which is '
            f'whole-set: the per-file call is yours')


def _config_readers() -> tuple[tuple[str, str, object], ...]:
    """The `devkit.toml` sections THIS version still reads: the section NAME
    the census reports it under, the label a refusal is spoken under, and the
    reader that refuses a value this version cannot use.

    **ONE LIST.** A1 (`docs/reviews/2026-09-05-adopt-is-a-conveyor.md`): this
    returned SIX readers and `check_config_updated` built its report line from
    a SECOND, hand-written list of TEN section names eleven lines below, so
    four sections it NAMED were never asked. Measured, one broken section per
    scratch repo, all four reported `TRUE — 6 reader(s) accept this repo's
    devkit.toml; declared here: <the broken section>`:

        [checks] all = ["doc", "wombat"]     `check all`         exits 2
        [verify] milestone = 42              `verify --check`    exits 2
        [grain_shape] caps = "nonsense"      `check grain-shape` exits 2
        [repo_hygiene] protected = "^(["     `check repo-hygiene` exits 2

    Rule 4's read side with the broken section's own name printed under the
    word "accept" — and the second-list defect CLAUDE.md names by hand. The
    census is now DERIVED from this tuple, so the number in the line is the
    number that was asked, and the next config section is named for free by
    adding a row here.

    There is deliberately no table of RETIRED keys. A section this package no
    longer reads is either dead or another kit's — `[uid]` left with the Godot
    half and that kit reads it now — and this package cannot tell those two
    apart without knowing its consumers, which hard rule 8 forbids. What it CAN
    ask is the question that actually breaks an adoption: does every value this
    version still reads parse under this version?
    """
    from agentic_sdlc.repo import gates_extra

    return (
        ('checks', '[checks] all', _read_checks),
        ('gates', '[gates] extra', gates_extra.targets),
        ('pm', '[pm]', model.load),
        ('release', '[release] steps / commands',
         lambda: _read_operation('release')),
        ('adopt', '[adopt] steps / commands',
         lambda: _read_operation('adopt')),
        ('story', '[story] steps / commands',
         lambda: _read_operation('story')),
        ('feature', '[feature] steps / commands',
         lambda: _read_operation('feature')),
        ('grain_shape', '[grain_shape] caps', _read_grain_shape),
        ('repo_hygiene', '[repo_hygiene] mainline / protected',
         _read_repo_hygiene),
        ('verify', '[verify] rungs / narrow rules', _read_verify),
    )


def _read_operation(operation: str) -> None:
    known = registry_for(operation)
    names = steps_for(operation, known)
    validate_config(operation, names, known)


def gate_universe() -> frozenset[str]:
    """Every gate name `check all` can dispatch, DERIVED from what ships.

    `cli.all_roster()` is the authority and `repo/` may never import
    `agentic_sdlc.cli` — `tests/test_boundaries.py` LAYER_RULES, and the same
    edge `_own_cli` above spawns a subprocess to respect. So the universe is
    derived from below, by the one mapping `cli._check_module` already applies
    to the name it is handed (`x-y` -> `checks/x_y.py`), and a `_`-prefixed
    module is a shared helper rather than a gate by the convention `check
    hooks` already uses for `tools/hooks/_*`.

    This is a DERIVATION, not a second roster: `tests/test_gate_roster.py`
    asserts `shipped_check_modules() == set(cli.KNOWN_GATES)` as an equality in
    both directions, so a module and a roster key that disagree fail there
    before they can reach here and make this the permissive answer.
    """
    from agentic_sdlc.repo import checks as checks_pkg

    # `core.walk`, not `glob` — `tests/test_boundaries.py` single-homes every
    # enumeration there, because a walk that returns one list has nowhere to
    # put what it DROPPED, and the `_`-prefix drop below is exactly that.
    found = walk.matching(Path(checks_pkg.__file__).resolve().parent, '*.py',
                          walk.Kind.FILE)
    return frozenset(path.stem.replace('_', '-') for path in found
                     if not path.name.startswith('_'))


def _read_checks() -> None:
    """`[checks] all` — the roster `check all` runs here, refused as it refuses.

    Two refusals, both `cli.all_roster()`'s: the SHAPE goes through `str_tuple`
    (a bare string is iterable, and iterating one is how seven gates shipped a
    silent empty census in v0.9.0), and an unknown name is refused rather than
    skipped, because a typo that narrowed the aggregate in silence is the
    cardinal sin with a config file in front of it.

    The fallback is `()` and not the shipped default roster: this asks whether
    what the repo DECLARED parses, and an absent key declares nothing.
    """
    from agentic_sdlc.core.config import str_tuple

    roster = str_tuple(config_section('checks'), 'checks', 'all', ())
    known = gate_universe()
    unknown = [name for name in roster if name not in known]
    if unknown:
        raise ConfigError(
            f'[checks] all names unknown gate(s) {", ".join(unknown)} — '
            f'known gates are {" ".join(sorted(known))}')


def _read_grain_shape() -> None:
    """`[grain_shape] caps`, through the gate's OWN reader.

    `_caps` is private and it is still what is called: it holds four refusals
    (`number_table`, an empty table, an unknown kind, a cap below 1) and a copy
    of them here would be the second answer this whole function list exists to
    end — the permissive one on the day they disagree.
    """
    from agentic_sdlc.repo.checks import grain_shape

    grain_shape._caps()


def _read_repo_hygiene() -> None:
    """`[repo_hygiene] mainline / protected`, through the gate's own reader.

    This spelled the two keys a SECOND TIME, because `repo_hygiene.py` read
    them inline at the top of `run()` — which then fetches from the remote and
    walks the tree, so there was nothing pure to call the way
    `grain_shape._caps` is called above. A second list survives only while
    something fails when it drifts, and a test that pins it is a worse answer
    than not having one.

    `repo_hygiene.read_config()` now exists for exactly this, and the keys are
    spelled once, in the module that owns them.
    """
    from agentic_sdlc.repo.checks import repo_hygiene

    repo_hygiene.read_config()


def _read_verify() -> None:
    """`[verify]`, through `verify/rules.py` — the grammar the verb itself reads.

    An ABSENT `[verify]` is not refused here. `verify` itself exits 2 on one
    (`repo/verify/main.py:316-325`) because a verb that printed nothing and
    exited 0 would report success for work it never checked — but that is a
    fact about running the verb, and this step asks the adoption question:
    does what this repo DECLARED still parse under this version? Refusing the
    absent section here would redden `config-updated` on every repo with no
    devkit.toml, which is rule 5 exactly backwards.

    The section is read HERE and passed IN, which is the boundary
    `tests/test_boundaries.py` draws around `repo/verify/`: that package is off
    the config-import allowlist on purpose, so its whole grammar can be
    exercised without a devkit.toml on disk.
    """
    from agentic_sdlc.core.config import section_declared
    from agentic_sdlc.repo.verify import rules

    if not section_declared(rules.SECTION):
        return
    rules.read(config_section(rules.SECTION))


def check_config_updated(ctx: Context) -> Answer:
    from agentic_sdlc.core.config import section_declared

    asked: list[str] = []
    refused: list[str] = []
    for name, label, reader in _config_readers():
        asked.append(name)
        try:
            reader()
        except ConfigError as err:
            # EVERY reader is asked, and every refusal is reported (D8: a step
            # is a check and a check reports). Returning at the first one would
            # hand the operator one broken section per run of a step whose
            # whole subject is "what does this version no longer accept".
            refused.append(f'{label}: {_clip(str(err), 160)}')
    if refused:
        return Answer.no(
            f'{len(refused)} of {len(asked)} section(s) hold a value '
            f'{__version__} does not accept — {"; ".join(refused)}')
    declared = [name for name in asked if section_declared(name)]
    # Rule 4: the census is REPORTED, and it is the census that was ASKED —
    # `asked` is the same list `declared` is filtered from, so the count and
    # the names can no longer describe different sets (A1).
    # Zero declared sections is legitimate (rule 5 — a repo with no devkit.toml
    # behaves identically) and it is said rather than passed over in silence.
    return Answer.yes(
        f'{len(asked)} reader(s) accept this repo\'s devkit.toml; '
        + (f'declared here: {", ".join(declared)}' if declared
           else 'no section is declared here, which is the stock default'))


def do_config_updated(ctx: Context) -> str:
    return ('fix the key named above in devkit.toml — a value this version '
            'refuses is exit 2 from every gate that reads it, not a finding')


def check_hooks_self_test(ctx: Context) -> Answer:
    """The installed guards still return the verdicts their own corpus asserts.

    `install-hooks` rewrites guard scripts, and a guard that fails OPEN is not
    there. This package has already shipped a hook that was installed,
    executable and stopping nothing — a config diff cannot show that. `check
    hooks` owns the replay (the kit that installs the corpus owns the gate over
    it), so this asks it rather than enumerating `tools/hooks/` a second time.
    """
    command = _configured(ctx, 'hooks-self-test')
    if command:
        return run_command(ctx, 'hooks-self-test', command)
    if not (ctx.root / HOOKS_DIR).is_dir():
        return Answer.no(
            f'{HOOKS_DIR}/ is not in this checkout — `install-hooks` writes the '
            f'corpus and this step installs nothing; run the verb, or drop '
            f'`hooks-self-test` from [{ctx.operation}] steps')
    return _own_verdict(ctx, 'check', 'hooks',
                        found=f'{HOOKS_DIR}/ replayed')


def check_runner_targets_resolve(ctx: Context) -> Answer:
    """Every composed gate target resolves in THIS repo's make.

    `Makefile.devkit` `-include`s `$(GDK_TIERS_MK)`, and an `-include` of a
    missing file is SILENT — which is what makes "no tiers at all" a supported
    shape and is also how a typo'd tier file turns a five-gate `precommit` into
    a one-gate one that exits 0. The two are held apart by make itself: a tier
    NAMED with no tier file is a parse-time `$(error)` that names the file, and
    an EMPTY tier list prints its `[TIERS] … is empty` line and resolves. This
    step reports which of the two it saw, and never treats the silence as a
    pass.
    """
    command = _configured(ctx, 'runner-targets-resolve')
    if command:
        return run_command(ctx, 'runner-targets-resolve', command)
    if not (ctx.root / FRAMEWORK_MAKEFILE).is_file():
        return Answer.no(
            f'{FRAMEWORK_MAKEFILE} is not in this checkout — `install-gates` '
            f'writes it and this step installs nothing; run the verb, or drop '
            f'`runner-targets-resolve` from [{ctx.operation}] steps')
    targets = _runner_targets_of(ctx.operation)
    # `-n` composes everything and RUNS nothing: the framework spells its one
    # sub-make `$${MAKE:-make}` precisely so a dry run keeps that promise.
    code, out = _make(ctx, '-n', *targets)
    if code == 127:
        return Answer.unverifiable('make is not on PATH')
    if code != 0:
        return Answer.no(
            f'`make -n {" ".join(targets)}` exited {code} — every later gate '
            f'runs through these targets: {_clip(out)}')
    empty = [line for line in out.split('\n') if '[TIERS]' in line]
    if empty:
        return Answer.yes(f'{len(targets)} target(s) resolve, and the tier '
                          f'lists are empty: {_clip(" ".join(empty), 200)}')
    return Answer.yes(f'{len(targets)} target(s) resolve with their tiers: '
                      f'{", ".join(targets)}')


def check_checks_pass(ctx: Context) -> Answer:
    """THIS package's `check all` — never the consumer's `make check`.

    The subtraction, and the whole feature. A consumer's `make check` also runs
    its own twenty gates; they verify the CONSUMER'S code against the
    CONSUMER'S rules and a version bump here cannot change their verdict, so
    running them during adoption re-verifies the game rather than the adoption.
    They run when the consumer changes its own code, which is what they are for.
    """
    command = _configured(ctx, 'checks-pass')
    if command:
        return run_command(ctx, 'checks-pass', command)
    return _own_verdict(ctx, 'check', 'all',
                        found='the roster this version ships')


def check_pm_validates(ctx: Context) -> Answer:
    """`pm validate` — the tree is still good against the new version."""
    command = _configured(ctx, 'pm-validates')
    if command:
        return run_command(ctx, 'pm-validates', command)
    cfg = _pm_cfg(ctx)
    if not (ctx.root / cfg.roadmap_dir).is_dir():
        return Answer.no(
            f'{cfg.roadmap_dir}/ is not in this checkout — a repo with no PM '
            f'tree is not vacuously fine here; scaffold one with `pm new`, or '
            f'drop `pm-validates` from [{ctx.operation}] steps')
    code, said = _pm_run(ctx, 'validate')
    if code == 0:
        return Answer.yes(said or '`pm validate` exited 0')
    if code == 2:
        return Answer.no(f'`pm validate` exited 2 — a usage or config error, '
                         f'so nothing was decided: {said}')
    return Answer.no(f'`pm validate` exited {code}: {said}')


# --- the story and feature steps ----------------------------------------------
# The two INNER belts. Every question below is asked of the grain named on the
# command line — `ctx.version` is a story or feature id here, resolved by the
# tracker's own resolvers so this file and `pm story done` can never disagree
# about which file they mean.
def _grain_file(ctx: Context) -> Path | None:
    return grain_path(_pm_cfg(ctx), ctx.operation, ctx.version)


def _grain_states(cfg: 'model.PmConfig', operation: str) -> tuple[str, ...]:
    return (cfg.story_states if operation == 'story' else cfg.feature_states)


def _grain_status_at_or_past(ctx: Context, wanted: str) -> Answer:
    """`_status_at_or_past`, one and two grains down.

    Same three answers and the same reason for each: a grain with no document
    and a status outside the project's own vocabulary are both UNVERIFIABLE —
    a question nobody can answer — while a status EARLIER than `wanted` is a
    plain no with the word the file actually holds.
    """
    cfg = _pm_cfg(ctx)
    path = _grain_file(ctx)
    if path is None:
        return Answer.unverifiable(
            f'no {ctx.operation} document for {ctx.version} under '
            f'{cfg.roadmap_dir}/ — nothing carries a status to read')
    status = model.field_of(path, 'status')
    states = _grain_states(cfg, ctx.operation)
    if status not in states:
        return Answer.unverifiable(
            f'{cfg.rel(path)} carries status {status!r}, which is not one of '
            f'{", ".join(states)}')
    if wanted not in states:
        return Answer.unverifiable(
            f'devkit.toml [pm] {ctx.operation}_states does not carry '
            f'{wanted!r} ({", ".join(states)}), so this step has no answer in '
            f'this project')
    if states.index(status) >= states.index(wanted):
        return Answer.yes(f'{cfg.rel(path)} is {status!r}')
    return Answer.no(f'{cfg.rel(path)} is {status!r}, not {wanted!r} or later')


def _grain_flip(wanted: str):
    """An AUTOMATIC status step at story or feature grain.

    `_flip`'s shape exactly, one grain down: the flip goes through the pm CLI
    so `check pm` — the drift gate — reads what the CLI wrote, and never
    through a regex over frontmatter.
    """
    def check(ctx: Context) -> Answer:
        return _grain_status_at_or_past(ctx, wanted)

    def do(ctx: Context) -> str:
        return _pm(ctx, ctx.operation, wanted, ctx.version)

    return check, do


# --- story --------------------------------------------------------------------
_claimed_check, _claimed_do = _grain_flip(CLAIMED)


def check_narrow_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --story` — the narrow rung, whatever it is HERE.

    The command is never named in this step. `[verify]`'s `[[verify.narrow]]`
    rules are a function of the changed paths, they are the project's own, and
    a step that hard-coded `pytest` would be a second answer to what proves an
    edit in a repo that may not be Python at all.

    On a tree whose work is already committed the rung reports `no changed
    paths` and exits 0. That is the verb's own honest answer and it is QUOTED
    into the line rather than summarised as a pass — a reader who wants to know
    whether anything ran can see that nothing did.
    """
    command = _configured(ctx, 'narrow-verified')
    if command:
        return run_command(ctx, 'narrow-verified', command)
    return _own_verdict(ctx, 'verify', '--story',
                        found='the narrow rung [verify] names')


def check_committed(ctx: Context) -> Answer:
    """No uncommitted work OUTSIDE the roadmap directory.

    Two things this deliberately does not do. It does not commit — no verb in
    this package does, and a story closed by a machine that also wrote the
    commit is a story nobody reviewed. And it does not claim to know WHICH
    paths are this story's: nothing in the tree records that, so the honest
    question is about the worktree and the answer NAMES what is outstanding.

    The roadmap directory is excluded because the belt writes there itself —
    `claimed` moved a status line two steps ago, and a step that reddened on
    its own machine's write would be `state.py` point 2 one grain down.
    """
    code, out = _git(ctx, 'status', '--porcelain', strip=False)
    if code != 0:
        return Answer.unverifiable(f'git status failed: {_clip(out)}')
    cfg = _pm_cfg(ctx)
    paths = [line[3:] for line in out.split('\n') if len(line) > 3]
    tree_paths = [p for p in paths
                  if not p.startswith(f'{cfg.roadmap_dir}/')]
    if not tree_paths:
        return Answer.yes(
            f'no modified path outside {cfg.roadmap_dir}/'
            + (f' ({len(paths)} inside it, which this belt writes)'
               if paths else ''))
    return Answer.no(f'{len(tree_paths)} uncommitted path(s): '
                     f'{_clip(", ".join(tree_paths))}')


def do_committed(ctx: Context) -> str:
    return ('commit your own paths, by explicit pathspec — this machine never '
            'commits for you, and it cannot know which of the paths above '
            'belong to this story; if some of them are another agent\'s work '
            'in the same worktree, that is what --skip --reason records')


def check_evidence_written(ctx: Context) -> Answer:
    """The story file carries the `done:` line pm-execution.md step 6 asks for.

    READ, never written. `done: <hash(es)> — <what shipped>` is the author's
    sentence at the grain that closed, and a machine-written one would say
    exactly what the commit already says while looking like independent
    evidence — a second scoreboard, which is the thing this tree keeps proving
    lies.

    Two refusals, because they send the author to two different places: a file
    with no `done:` line at all, and one whose line names no commit or says
    nothing about what shipped.
    """
    cfg = _pm_cfg(ctx)
    path = _grain_file(ctx)
    if path is None:
        return Answer.unverifiable(
            f'no story document for {ctx.version} — nothing to read evidence '
            f'from')
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError):
        return Answer.unverifiable(f'{cfg.rel(path)} could not be read as text')
    lines = [m.group('body').strip()
             for m in (EVIDENCE_LINE.match(raw) for raw in text.split('\n'))
             if m is not None]
    if not lines:
        return Answer.no(
            f'{cfg.rel(path)} carries no `done:` line — step 6 of '
            f'pm-execution.md: `done: <hash(es)> — <what shipped>`, at most '
            f'{EVIDENCE_BUDGET} lines, so a fresh session picks this story up '
            f'from the tree alone')
    for body in lines:
        landed = EVIDENCE_LANDED.search(body)
        if landed is None:
            continue
        said = EVIDENCE_LANDED.sub('', body).strip(' \t—–-:;,.')
        if not said:
            return Answer.no(
                f'{cfg.rel(path)} `done: {_clip(body, 80)}` names what landed '
                f'and not what shipped — the second half of the line is the '
                f'part a fresh session reads')
        return Answer.yes(f'{cfg.rel(path)} carries `done: {_clip(body, 80)}`')
    return Answer.no(
        f'{cfg.rel(path)} `done: {_clip(lines[0], 80)}` names no commit — a '
        f'hash of {HASH_MIN}-{HASH_MAX} hex characters, or the literal '
        f'`{IN_PLACE}` for a fix that has not been committed yet (the form '
        f'`pm/verdict.py` already rules for exactly this case)')


def do_evidence_written(ctx: Context) -> str:
    return ('write the `done:` line yourself, in the story file: '
            '`done: <hash(es)> — <what shipped>`. This step will not write it '
            '— the sentence is your account of the work, and one generated '
            'from the commit would be a second scoreboard saying what the '
            'commit already says')


_story_done_check, _story_done_do = _grain_flip(DONE)


# --- feature ------------------------------------------------------------------
def check_stories_done(ctx: Context) -> Answer:
    """`pm ready-for feature <fid>` — never re-implemented.

    THE step this feature exists for. An orchestrator parked 28 finished
    stories at `reviewing` and reviewed the whole milestone in one pass, in the
    milestone that built the levels; `pm ready-for feature` had been answering
    NOT READY with every blocker named for hours. A belt cannot walk past that.
    """
    return ready_for(ctx, 'feature')


def do_stories_done(ctx: Context) -> str:
    return ('close each story named above through `agentic-sdlc close story '
            '<id>` — the belt below this one, and it is five steps and under a '
            'second')


_feature_reviewing_check, _feature_reviewing_do = _grain_flip(REVIEWING)


def check_feature_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --feature` — the range rung, whatever it is HERE."""
    command = _configured(ctx, 'feature-verified')
    if command:
        return run_command(ctx, 'feature-verified', command)
    return _own_verdict(ctx, 'verify', '--feature',
                        found='the range rung [verify] names')


def _record_of(ctx: Context) -> tuple[Path | None, str]:
    """(the feature's review record, '' or why there is none).

    `model.review_record_for` is the resolver `pm feature done` already uses,
    so the pointer this reads and the pointer that verb stamps are one fact.
    What is added here is hard rule 8: an ABSOLUTE pointer is refused rather
    than followed, because a step answering about a file outside the checkout
    is a step answering about somebody else's machine.
    """
    cfg = _pm_cfg(ctx)
    pointer = model.review_record_for(cfg, ctx.version)
    if not pointer:
        return None, (f'{ctx.version} points at no review record — '
                      f'`reviewed:` is blank, and a feature closed without one '
                      f'is a feature nobody read')
    if pointer.startswith('/') or pointer.startswith('~'):
        return None, (f'reviewed: {pointer!r} is not repo-relative — nothing '
                      f'outside this checkout is read (hard rule 8)')
    path = cfg.root / pointer
    if not path.is_file():
        return None, f'reviewed: names no file ({pointer})'
    size = path.stat().st_size
    if size > MAX_RECORD_BYTES:
        return None, (f'reviewed: the record is {size} bytes, over the '
                      f'{MAX_RECORD_BYTES}-byte read bound ({pointer})')
    return path, ''


def _passes(ctx: Context, path: Path) -> tuple[list, str]:
    """(the record's verdict blocks, '' or why they could not be read).

    `verdict.parse`'s rulings, inherited whole: no block and a block that does
    not parse are both a REFUSAL to advance, never a pass. This is the single
    easiest place in the belt to get a false green.
    """
    cfg = _pm_cfg(ctx)
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError):
        return [], f'{cfg.rel(path)} could not be read as text'
    try:
        return verdict.parse(text), ''
    except (verdict.NoVerdict, verdict.MalformedVerdict) as err:
        return [], f'{cfg.rel(path)}: {" ".join(str(err).split())}'


def check_review_recorded(ctx: Context) -> Answer:
    """A review record EXISTS and its verdict block PARSES. Nothing more.

    Whether the review was any good is not encodable, and a step that pretended
    to check it would be this package's cardinal sin wearing a protocol. What a
    machine can hold is that the artifact is there and machine-readable, and
    that is exactly what this holds.
    """
    path, defect = _record_of(ctx)
    if path is None:
        return Answer.no(defect)
    cfg = _pm_cfg(ctx)
    passes, why = _passes(ctx, path)
    if why:
        return Answer.unverifiable(
            f'{why} — a record whose verdict block does not parse is '
            f'UNVERIFIABLE, which is a refusal to advance and never a pass')
    return Answer.yes(f'{cfg.rel(path)} parses: {len(passes)} pass(es), '
                      f'{sum(len(p.findings) for p in passes)} finding(s)')


def do_review_recorded(ctx: Context) -> str:
    return ('run the feature review — a fresh reviewer over this feature\'s '
            'whole commit range — and stamp the record with `pm feature done '
            '<id> --review-record <path>`, or `pm set <id> reviewed <path>` '
            'first. This step reads the ARTIFACT of that pass and cannot '
            'perform it: whether a review was thorough has no postcondition, '
            'and a machine claiming to check it would be lying in the one '
            'place this belt exists to stop lying')


def check_findings_landed(ctx: Context) -> Answer:
    """No finding in the record sits at `disposition: open`.

    `verdict.OPEN` is the token, `verdict.parse` is the reader, and both are
    inherited rather than restated — `ready-for tag` asks the same question one
    grain up and the two must not be able to disagree.
    """
    path, defect = _record_of(ctx)
    if path is None:
        return Answer.no(defect)
    cfg = _pm_cfg(ctx)
    passes, why = _passes(ctx, path)
    if why:
        return Answer.unverifiable(why)
    opened = [f.id for p in passes for f in p.findings
              if f.disposition_kind == verdict.OPEN]
    total = sum(len(p.findings) for p in passes)
    if opened:
        return Answer.no(f'{len(opened)} finding(s) open in {cfg.rel(path)}: '
                         f'{_clip(", ".join(opened))}')
    # Rule 4: a census of zero is SAID. A record contributing no findings must
    # not read identically to one this step never opened.
    return Answer.yes(f'{cfg.rel(path)}: {total} finding(s), none open')


def do_findings_landed(ctx: Context) -> str:
    return ('land each finding above, or defer it explicitly in writing — '
            '`landed <hash>`, `landed in-place`, `rejected: <why>` or '
            '`deferred: <grain-id>` in the record\'s verdict block. `open` is '
            'the honest disposition for a finding nobody has acted on, which '
            'is why it blocks here rather than being quietly counted as done')


def check_feature_done(ctx: Context) -> Answer:
    return _grain_status_at_or_past(ctx, DONE)


def do_feature_done(ctx: Context) -> str:
    """`pm feature done <id> --review-record <path>`.

    The record pointer is passed even though `review-recorded` already proved
    it resolves: the verb stamps `reviewed:` from that flag, and a close that
    left the stamp to a previous run's memory would be the belt trusting
    something other than the tree.
    """
    cfg = _pm_cfg(ctx)
    pointer = model.review_record_for(cfg, ctx.version)
    if not pointer:
        return ('no review record is stamped, so `pm feature done` is not run '
                '— `review-recorded` is the step that says what to do')
    return _pm(ctx, 'feature', 'done', ctx.version, '--review-record', pointer)


# --- the registry -------------------------------------------------------------
_reviewing_check, _reviewing_do = _flip('reviewing')
_accepted_check, _accepted_do = _flip('accepted')
_packaging_check, _packaging_do = _flip('packaging')
_done_check, _done_do = _flip('done')

RELEASE_STEPS: dict[str, Step] = {
    step.name: step for step in (
        Step('tree-clean', StepKind.JUDGEMENT, check_tree_clean, do_tree_clean),
        Step('on-milestone-branch', StepKind.JUDGEMENT,
             check_on_milestone_branch, do_on_milestone_branch),
        Step('main-merged', StepKind.JUDGEMENT, check_main_merged,
             do_main_merged),
        Step('changelog-unreleased-nonempty', StepKind.JUDGEMENT,
             check_changelog_unreleased_nonempty,
             do_changelog_unreleased_nonempty),
        Step('review-landed', StepKind.JUDGEMENT, check_review_landed,
             do_review_landed),
        Step('version-sync', StepKind.AUTOMATIC, check_version_sync,
             do_version_sync),
        Step('readme-pins', StepKind.AUTOMATIC, check_readme_pins,
             do_readme_pins),
        Step('features-done', StepKind.JUDGEMENT, check_features_done,
             do_features_done),
        Step('milestone-reviewing', StepKind.AUTOMATIC, _reviewing_check,
             _reviewing_do),
        Step('gate', StepKind.GATE, check_gate),
        Step('milestone-accepted', StepKind.AUTOMATIC, _accepted_check,
             _accepted_do),
        Step('changelog-retitle', StepKind.AUTOMATIC, check_changelog_retitle,
             do_changelog_retitle),
        Step('milestone-packaging', StepKind.AUTOMATIC, _packaging_check,
             _packaging_do),
        Step('findings-resolved', StepKind.JUDGEMENT, check_findings_resolved,
             do_findings_resolved),
        Step('milestone-done', StepKind.AUTOMATIC, _done_check, _done_do),
        Step('push-branch', StepKind.AUTOMATIC, check_push_branch,
             do_push_branch),
        Step('pr-open', StepKind.JUDGEMENT, check_pr_open, do_pr_open),
        Step('ci-green', StepKind.JUDGEMENT, check_ci_green, do_ci_green),
        Step('merge', StepKind.JUDGEMENT, check_merge, do_merge),
        Step('tag', StepKind.AUTOMATIC, check_tag, do_tag),
        Step('prove-artifact', StepKind.JUDGEMENT, check_prove_artifact,
             do_prove_artifact),
    )
}

ADOPT_STEPS: dict[str, Step] = {
    step.name: step for step in (
        Step('pin-bumped', StepKind.JUDGEMENT, check_pin_bumped,
             do_pin_bumped),
        Step('installables-diffed', StepKind.AUTOMATIC,
             check_installables_diffed, do_installables_diffed),
        Step('installable-decisions-recorded', StepKind.JUDGEMENT,
             check_installable_decisions_recorded,
             do_installable_decisions_recorded),
        Step('config-updated', StepKind.JUDGEMENT, check_config_updated,
             do_config_updated),
        Step('hooks-self-test', StepKind.GATE, check_hooks_self_test),
        Step('runner-targets-resolve', StepKind.GATE,
             check_runner_targets_resolve),
        Step('checks-pass', StepKind.GATE, check_checks_pass),
        Step('pm-validates', StepKind.GATE, check_pm_validates),
    )
}

STORY_STEPS: dict[str, Step] = {
    step.name: step for step in (
        Step('claimed', StepKind.AUTOMATIC, _claimed_check, _claimed_do),
        Step('narrow-verified', StepKind.GATE, check_narrow_verified),
        Step('committed', StepKind.JUDGEMENT, check_committed, do_committed),
        Step('evidence-written', StepKind.JUDGEMENT, check_evidence_written,
             do_evidence_written),
        Step('story-done', StepKind.AUTOMATIC, _story_done_check,
             _story_done_do),
    )
}

FEATURE_STEPS: dict[str, Step] = {
    step.name: step for step in (
        Step('stories-done', StepKind.JUDGEMENT, check_stories_done,
             do_stories_done),
        Step('feature-reviewing', StepKind.AUTOMATIC,
             _feature_reviewing_check, _feature_reviewing_do),
        Step('feature-verified', StepKind.GATE, check_feature_verified),
        Step('review-recorded', StepKind.JUDGEMENT, check_review_recorded,
             do_review_recorded),
        Step('findings-landed', StepKind.JUDGEMENT, check_findings_landed,
             do_findings_landed),
        Step('feature-done', StepKind.AUTOMATIC, check_feature_done,
             do_feature_done),
    )
}

# The postcondition, in a sentence, for the GENERATED document. It lives beside
# the step rather than in the renderer: story 05's whole point is that the
# renderer holds no per-step text of its own, so there is exactly one place a
# step's meaning is written and it is the file that also runs it.
STEP_DOC: dict[str, str] = {
    'tree-clean': '`git status --porcelain` is empty.',
    'on-milestone-branch':
        'HEAD is the branch the milestone document stamps in `branch:` (D9).',
    'main-merged': 'the mainline is an ancestor of HEAD.',
    'changelog-unreleased-nonempty':
        'the changelog\'s `## Unreleased` section holds at least one bullet.',
    'review-landed':
        '`pm ready-for tag <milestone>` exits 0 — every review finding is '
        'dispositioned. This is the step that makes the gate\'s position '
        'structural rather than remembered.',
    'version-sync':
        'every configured version site names the release version.',
    'readme-pins':
        'every `vX.Y.Z` pin inside a fenced code block names the release '
        'version. Prose naming an older tag is history and is never rewritten.',
    'features-done': '`pm ready-for milestone <milestone>` exits 0.',
    'milestone-reviewing': 'the milestone status is `reviewing` or later.',
    'gate':
        'the configured gate command exits 0. It has no `do()`: a gate is not '
        'made true by running it again.',
    'milestone-accepted': 'the milestone status is `accepted` or later.',
    'changelog-retitle':
        'a `## v<version> — <ISO date>` heading exists with a fresh empty '
        '`## Unreleased` above it.',
    'milestone-packaging': 'the milestone status is `packaging` or later.',
    'findings-resolved':
        'no document under the review directory names this milestone — every '
        'record resolved and deleted.',
    'milestone-done': 'the milestone status is `done`.',
    'push-branch':
        'the branch tip equals its upstream tip. It refuses on the mainline '
        'and pushes nothing there.',
    'pr-open':
        'the configured `pr-open` command exits 0. With none, the operator is '
        'asked and the run refuses to advance.',
    'ci-green':
        'the configured `ci-green` command exits 0. With none, the operator '
        'is asked and the run refuses to advance.',
    'merge': 'the mainline contains this branch\'s tip.',
    'tag': 'the tag exists locally AND on the remote. It is never force-moved.',
    'prove-artifact':
        'the configured `prove-artifact` command exits 0. This package ships '
        'no default: the proof names a git URL, and a URL is the project\'s '
        'own fact (hard rule 8).',
    # --- adopt ---
    'pin-bumped':
        'the `DEVKIT_VERSION` line in this repo\'s own makefile names the '
        'version of the package that is running. It is a line in a file this '
        'package does not own, so the step states the edit and writes nothing.',
    'installables-diffed':
        'the diff between what this version ships and what is installed here '
        'has been produced, and the recorded census still describes the tree '
        '(each file with a digest, so an edit made after the diff makes it '
        'stale).',
    'installable-decisions-recorded':
        'every file that differs carries a decision in the run\'s record. '
        '`--force` is whole-set and has no per-file option, so take / '
        'hand-apply / keep is a call only the consumer can make.',
    'config-updated':
        'every devkit.toml section this version still READS accepts what this '
        'repo declares. There is no retired-key table: a section this package '
        'no longer reads may be another kit\'s, and telling those apart would '
        'mean knowing the consumer (hard rule 8).',
    'hooks-self-test':
        '`check hooks` exits 0 — the installed guards are armed, executable, '
        'still start, and still return the verdicts their own corpus asserts. '
        'A guard that fails OPEN is not there, and a config diff cannot see it.',
    'runner-targets-resolve':
        'the composed gate targets resolve under `make -n`. A tier named with '
        'no tier file FAILS here naming the file; an empty tier list passes '
        'and SAYS it was empty — `-include`\'s silence is never a pass.',
    'checks-pass':
        'this package\'s `agentic-sdlc check all` exits 0. NOT `make check`, '
        'not `make precommit`, not `[gates] extra`: those verify the '
        'consumer\'s code against the consumer\'s rules, and a version bump '
        'here cannot change their verdict.',
    'pm-validates':
        '`pm validate` exits 0 — the PM tree is still good against the new '
        'version. A repo with no PM tree is refused, never vacuously fine.',
    # --- story ---
    'claimed':
        f'the story\'s status is `{CLAIMED}` or later. The flip goes through '
        f'`pm story {CLAIMED} <id>`, never a regex over frontmatter.',
    'narrow-verified':
        'the narrow rung exits 0 — `agentic-sdlc verify --story`, which is a '
        'function of the CHANGED PATHS and of `[[verify.narrow]]`. The command '
        'is never named in the step: what proves an edit is the project\'s own '
        'fact. On a committed tree the rung says `no changed paths` and that '
        'sentence is quoted rather than summarised as a pass.',
    'committed':
        'nothing is uncommitted outside the roadmap directory. It NAMES what '
        'is, and it never commits — a story closed by a machine that also '
        'wrote the commit is a story nobody reviewed. The roadmap directory is '
        'excluded because this belt writes there itself.',
    'evidence-written':
        'the story file carries `done: <hash(es)> — <what shipped>` '
        '(pm-execution.md step 6). READ, never written: the sentence is the '
        'author\'s, and a generated one would be a second scoreboard saying '
        'what the commit already says.',
    'story-done': 'the story\'s status is `done`, through `pm story done`.',
    # --- feature ---
    'stories-done':
        '`pm ready-for feature <id>` exits 0 — every story under this feature '
        'is `done`, and each one that is not is NAMED. Never re-implemented: '
        'the verb owns that question.',
    'feature-reviewing':
        f'the feature\'s status is `{REVIEWING}` or later — the hand-off that '
        f'says a reviewer runs now, once, over the whole feature.',
    'feature-verified':
        'the range rung exits 0 — `agentic-sdlc verify --feature`, the '
        'composition the project names for that rung.',
    'review-recorded':
        'the feature\'s `reviewed:` record exists, is repo-relative, and its '
        'verdict block PARSES (`pm/verdict.py`). Whether the review was any '
        'good is NOT checked and must not be: a step pretending to check it '
        'would be this package\'s cardinal sin wearing a protocol. A record '
        'that does not parse is UNVERIFIABLE — a refusal, never a pass.',
    'findings-landed':
        'no finding in that record sits at `disposition: open`. The same '
        'question `pm ready-for tag` asks one grain up, through the same '
        'parser, so the two cannot disagree.',
    'feature-done':
        'the feature\'s status is `done`, through `pm feature done <id> '
        '--review-record <path>`.',
}

# What a step DOES when the project configures no command for it. Only the
# steps that ship an action of their own are here: a step with no entry and no
# configured command is the operator's, which is what the renderer says. It
# lives beside the step for the same reason `STEP_DOC` does — the renderer
# holds no per-step text — and `checks-pass` is the row a reader most needs,
# because "this package's `check all`, not your `make check`" is the whole
# subtraction and it belongs in the document the protocol is read from.
SHIPPED_ACTION: dict[str, str] = {
    'hooks-self-test': 'agentic-sdlc check hooks',
    'runner-targets-resolve': 'make -n <[adopt] runner_targets>',
    'checks-pass': 'agentic-sdlc check all',
    'pm-validates': 'agentic-sdlc pm validate',
    'narrow-verified': 'agentic-sdlc verify --story',
    'feature-verified': 'agentic-sdlc verify --feature',
    'stories-done': 'agentic-sdlc pm ready-for feature <id>',
}

# What is guidance rather than a step — rendered into the document beside the
# list, because it is real protocol with no checkable postcondition.
GUIDANCE: tuple[tuple[str, str], ...] = (
    ('The judgement runs first, and the gate answers for its result',
     'When a gate and a judgement both bear on one decision, the judgement '
     'runs first. A gate that runs before the review answers for a tree '
     'nobody will ship, and every fix landed afterwards voids it while it '
     'still reads as readiness. `review-landed` sits above `gate` in the list '
     'for exactly this reason, and the machine will not walk past it.'),
    ('Pick the bump yourself',
     'Patch, minor or major is a semver judgement about the interface, and no '
     'step can make it. Output-line-shape changes are minor at least; '
     'anything a consumer must edit for is major.'),
    ('The negative probe for a gate whose scoping changed',
     'Introduce the drift class into a scratch copy of a fixture repo and '
     'confirm the gate FAILS. It is not a step: the artifact is a judgement '
     'made in scratch, with nothing in the tree to check.'),
    ('The consumer follow-up',
     'A consumer bumps its pin, runs `install-* --diff`, and decides PER '
     'FILE. It is not a step: those are instructions for somebody in another '
     'repo, and this package gates on no other repo\'s state (hard rule 8).'),
    ('Forward only',
     'Nothing pushed is ever amended, rebased, reset or force-pushed. A '
     'botched commit is repaired with another commit, and a bad release is a '
     'new patch version — never a rewritten tag.'),
    ('Open the next milestone',
     'After the tag, so the next release\'s notes have somewhere to go from '
     'the first commit. It is not a step: it needs a name only a human has.'),
)

REGISTRIES: dict[str, dict[str, Step]] = {'release': RELEASE_STEPS,
                                          'adopt': ADOPT_STEPS,
                                          'story': STORY_STEPS,
                                          'feature': FEATURE_STEPS}


def registry_for(operation: str) -> dict[str, Step]:
    """The steps this package SHIPS for `operation`, by name.

    The two registries are SEPARATE. `[adopt] steps = ["tag"]` is exit 2, not a
    release step borrowed into an adoption: an operation whose list can name
    another's steps has no shape at all, and the name in that list is a typo
    every time. An operation with no registry answers {} and `plan_defect` then
    refuses to walk it, which is the true sentence rather than a plausible one.
    """
    return dict(REGISTRIES.get(operation, {}))
