"""steps.py — the four check lists, as registries the driver runs.

`driver.py` is the machine; this is what it asks. Four lists — `release`,
`adopt`, and the two INNER belts `story` and `feature` (SDLC.md §0) — each a
sequence of CHECKS. A check is a question about the tree with a one-line
answer, and nothing here performs anything: D12 (`decisions.md`) — *"the
actions ARE the checks"* — took every `do()` out of this file. What a caller
must still do after a belt is words, in `AFTER` below, printed on success and
rendered into `docs/sdlc-protocol.md`.

## No check re-implements a predicate that has a verb

`features-done`, `findings-resolved` and `stories-done` go through
`pm ready-for milestone|tag|feature`. `narrow-verified` and `feature-verified`
go through `verify --story|--feature`. None of them parses a verdict block,
reads frontmatter with a regex, or names a test command of its own. Two readers
of "is every finding dispositioned" are two answers, and the second one is the
permissive one on the day they disagree.

**The one place this module reads a review record itself is the feature
belt**, through `pm/verdict.py` — the SAME parser `ready_for` reads. There is
no `pm ready-for` at feature grain, so `review-recorded` and `findings-landed`
ask `verdict.parse` directly and INHERIT its rulings whole: a record whose
block does not parse is UNVERIFIABLE (never true), and a finding at
`disposition: open` is false.

## Config (rule 5 — a repo with no `devkit.toml` behaves identically)

    [release]
    steps       = [...]                    # default: DEFAULT_RELEASE_STEPS
    changelog   = "CHANGELOG.md"
    command_timeout = 1800                 # seconds, per configured command

    [release.commands]
    gate      = "make milestone"           # the ONE shipped default command
                                           # {version} is the belt's subject

    [release.version_files]
    "pyproject.toml"           = '^version = "(.*)"$'
    "src/pkg/__init__.py"      = "^__version__ = '(.*)'$"

    [adopt]
    steps          = [...]                 # default: DEFAULT_ADOPT_STEPS
    pin_file       = "Makefile"            # where DEVKIT_VERSION lives
    runner_targets = ["check", "precommit", "milestone"]

    [story]                                # default: DEFAULT_STORY_STEPS
    [feature]                              # default: DEFAULT_FEATURE_STEPS
    steps = [...]

A `[<operation>.commands]` entry is accepted only for a check in `COMMANDABLE`
— the ones that run something by default. A command for `tree-clean` would be
two authorities over one fact. Every refusal here exits 2 through
`ConfigError`: a typo is a config mistake, not a finding.

## `adopt` — the subtraction, which is the whole second list

A pin bump is verified as a PIN BUMP. `checks-pass` runs **this package's**
`check all` and never the consumer's `make check`: a consumer's `make check`
also runs its own gates, which verify the CONSUMER'S code against the
CONSUMER'S rules — and a version bump in this package cannot change their
verdict. `tests/test_conveyor_adopt.py::test_checks_pass_never_runs_make`
names it with a command recorder AND a sentinel file. Hard rule 8 is the live
hazard: `adopt` runs IN a consumer, on the consumer's own tree, and every check
below is a question about the LOCAL tree — `pin-bumped` compares the
consumer's own `DEVKIT_VERSION` line to the version of the package that is
RUNNING, needing no network and no second checkout.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from agentic_sdlc import __version__
from agentic_sdlc.core import walk
from agentic_sdlc.core.config import ConfigError, config_section
from agentic_sdlc.repo.conveyor.driver import Answer, Check, Context, grain_path
from agentic_sdlc.repo.pm import model, verdict

# --- the shipped defaults -----------------------------------------------------
DEFAULT_RELEASE_STEPS = (
    'tree-clean',
    'on-milestone-branch',
    'changelog-unreleased-nonempty',
    'features-done',
    'findings-resolved',
    'version-sync',
    'gate',
)

# Seven checks. `hooks-self-test` and `runner-targets-resolve` are here because
# a human list keeps forgetting them and both have bitten this package: a guard
# that fails OPEN is not there, and an `-include` of a missing tier file is
# SILENT.
DEFAULT_ADOPT_STEPS = (
    'pin-bumped',
    'installables-current',
    'config-updated',
    'hooks-self-test',
    'runner-targets-resolve',
    'checks-pass',
    'pm-validates',
)

# The belt that runs dozens of times a day. Three of its four checks read a
# file or a porcelain listing; the fourth shells out once to the narrow rung.
DEFAULT_STORY_STEPS = (
    'story-exists',
    'narrow-verified',
    'committed',
    'evidence-written',
)

DEFAULT_FEATURE_STEPS = (
    'stories-done',
    'review-recorded',
    'findings-landed',
)

DEFAULT_STEPS: dict[str, tuple[str, ...]] = {
    'release': DEFAULT_RELEASE_STEPS,
    'adopt': DEFAULT_ADOPT_STEPS,
    'story': DEFAULT_STORY_STEPS,
    'feature': DEFAULT_FEATURE_STEPS,
}

# The ONE command this package ships a default for. `make milestone` is the
# target `install-gates` writes and `install-ci` runs, so a stock consumer's
# gate is answerable the day it installs.
DEFAULT_COMMANDS: dict[str, str] = {'gate': 'make milestone'}

# The checks that RUN something by default, and so may be given a command of
# the project's own. Everything else reads the tree, and a command for one of
# those would be two authorities over one fact.
COMMANDABLE = frozenset((
    'gate', 'hooks-self-test', 'runner-targets-resolve', 'checks-pass',
    'pm-validates', 'narrow-verified', 'feature-verified'))

# The commands a CALLER runs after the release belt — they were judgement
# steps until D12 and are `next:` lines now. A `[release.commands]` entry for
# one is still accepted: it is printed on the after-list (and rendered into
# the protocol document) so the caller has the command in front of them.
AFTER_COMMANDS: dict[str, str] = {'pr-open': 'pr_open', 'ci-green': 'ci_green',
                                  'prove-artifact': 'prove'}

# What a configured command may ask this machine to fill in. `{version}` is
# the belt's SUBJECT — the release or pin version, the grain id on a close
# belt. A brace pair is a placeholder only when it is exactly `{identifier}`
# and not preceded by `$`: `${HOME}`, `{}` and `awk '{print $1}'` pass through
# byte for byte. An identifier this table does not know is refused at exit 2.
PLACEHOLDERS: tuple[str, ...] = ('version',)
_PLACEHOLDER = re.compile(r'(?<!\$)\{([A-Za-z_][A-Za-z0-9_]*)\}')


def unknown_placeholders(command: str) -> tuple[str, ...]:
    """Every `{identifier}` in `command` this machine cannot fill, in order."""
    return tuple(dict.fromkeys(
        name for name in _PLACEHOLDER.findall(command)
        if name not in PLACEHOLDERS))


def substitute(command: str, ctx: Context) -> str:
    """`command` with every known placeholder filled from the belt's subject."""
    values = {'version': ctx.version}
    return _PLACEHOLDER.sub(
        lambda m: values.get(m.group(1), m.group(0)), command)


# A check name is a path-free, markdown-free token: the renderer puts it in a
# table cell and the driver puts it in a line shape consumers grep.
STEP_NAME = re.compile(r'^[a-z][a-z0-9-]*$')
STEP_NAME_MAX = 40

# How much of a command's output reaches a line. A gate that writes 100 MB to
# stdout must produce a bounded line, not a transcript.
OUTPUT_LIMIT = 400
DEFAULT_COMMAND_TIMEOUT = 1800

# --- what the adopt checks look at, all of it inside the checkout --------------
DEFAULT_PIN_FILE = 'Makefile'
DEFAULT_RUNNER_TARGETS = ('check', 'precommit', 'milestone')
# `install-gates` writes this; `adopt` READS it and installs nothing.
FRAMEWORK_MAKEFILE = 'Makefile.devkit'
# Where `install-hooks` puts the corpus in every consumer.
HOOKS_DIR = 'tools/hooks'
# `DEVKIT_VERSION := v1.2.3`, `=`, `?=` and `+=` included — it is somebody
# else's makefile and this only ever READS the line.
PIN_LINE = re.compile(r'^\s*DEVKIT_VERSION\s*[:?+]?=\s*(\S+)')

# --- what the close checks look at --------------------------------------------
# `done: <hash(es)> — <what shipped>` — pm-execution.md step 6, at the grain
# that closed. Case-insensitive and whitespace-tolerant: the shape being
# checked is "the author left evidence", not "the author typed it exactly".
EVIDENCE_LINE = re.compile(r'^\s*done\s*:\s*(?P<body>\S.*)$', re.IGNORECASE)
# What "shipped" looks like: a commit hash, or the literal `in-place`. BOTH
# forms are `pm/verdict.py`'s, inherited rather than re-decided.
HASH_MIN, HASH_MAX = verdict.HASH_MIN_LEN, verdict.HASH_MAX_LEN
IN_PLACE = verdict.IN_PLACE
EVIDENCE_LANDED = re.compile(
    rf'\b(?:[0-9a-fA-F]{{{HASH_MIN},{HASH_MAX}}}|{IN_PLACE})\b', re.IGNORECASE)
# The budget the rule states — QUOTED in the refusal, never enforced here
# (`check grain-shape` owns caps).
EVIDENCE_BUDGET = 5
# A review record is read whole to be parsed, so the read is bounded — the
# same bound `ready-for` puts on the same files.
MAX_RECORD_BYTES = 1 << 20


# --- small helpers ------------------------------------------------------------
def _clip(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """One bounded line of somebody else's output."""
    flat = ' '.join(str(text).split())
    return flat if len(flat) <= limit else flat[:limit] + '…'


def _read(path: Path) -> str:
    """A file's text with its line endings INTACT."""
    with open(path, encoding='utf-8', newline='') as handle:
        return handle.read()


def _pm_cfg(ctx: Context) -> 'model.PmConfig':
    return replace(model.load(), root=ctx.root)


def _git(ctx: Context, *args: str, strip: bool = True) -> tuple[int, str]:
    """`git` in the checkout. A missing git is an exit code, never a crash.

    `strip=False` for any porcelain format whose COLUMNS carry meaning:
    `git status --porcelain` writes `XY<space>PATH`, and X is a space for a
    worktree-only change — a blanket `.strip()` ate one character off the
    FIRST line and reported `SDLC.md` as `DLC.md`.
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
    `agentic_sdlc.cli` (`tests/test_boundaries.py`), and a copy of
    `check all`'s roster here would be a second answer to which gates run.
    `PYTHONPATH` names the package that is RUNNING, so the answer comes from
    this build rather than from whatever else is installed on the box. It
    returns the argv it ran, so a test can assert WHAT was run.
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
    """One of this package's own gates, answered as a check.

    Exit 2 is NOT exit 1, and D11 says which column it lands in: the callee's
    reader failed, so the question was never asked — UNVERIFIABLE, never a
    plain no, and never true. Only THIS callee gets the ruling: it is the one
    that speaks hard rule 6, while a configured `[<operation>.commands]`
    string is any shell at all and `make` exits 2 for a failed recipe — so
    `run_command` reads exit codes as 0-is-true and nothing else.
    """
    code, said, _ = _own_cli(ctx, *argv)
    spoken = f'`agentic-sdlc {" ".join(argv)}`'
    if code == 0:
        return Answer.yes(f'{spoken} exited 0{f" — {found}" if found else ""}'
                          + (f': {said}' if said else ''))
    if code == 2:
        return Answer.unverifiable(
            f'{spoken} exited 2 — a CONFIG or usage error, not a finding, so '
            f'nothing was decided (D11): {said}')
    return Answer.no(f'{spoken} exited {code}: {said}')


def _pm_run(ctx: Context, *argv: str) -> tuple[int, str]:
    """One `pm` verb, in process, with its exit code. `pm` is `repo/`, so it is
    imported rather than spawned — a spawn would pay an interpreter for a
    question already in memory."""
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
    """'' when `value` may be a check name, else why not."""
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
    """The ordered check list for `operation`, from `[<operation>] steps`.

    A repo with NO `devkit.toml` and a repo declaring exactly the stock list
    produce the same tuple, byte for byte (rule 5). Duplicates COLLAPSE in
    declaration order and the collapse is REPORTED: a list a project wrote and
    a list this ran that differ without a word is a quiet narrowing.
    """
    sect = _section(operation)
    known = registry_for(operation) if registry is None else registry
    raw = sect.get('steps')
    if raw is None:
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
            f'which no check is registered for — the known checks are: '
            f'{", ".join(sorted(known))}')
    if duplicates:
        print(f'[{operation}] steps names '
              f'{", ".join(repr(d) for d in dict.fromkeys(duplicates))} more '
              f'than once — collapsed in declaration order')
    return tuple(seen)


def commands_for(operation: str, names: tuple[str, ...] | None = None,
                 registry: dict | None = None) -> dict[str, str]:
    """`[<operation>.commands]`, merged over the shipped defaults.

    A command string is REFUSED OR RUN WHOLE — never sanitised into safety.
    What is refused is the shape that cannot be what it claims: a non-string,
    an empty string, an unfillable placeholder, a key naming a check that is
    not in the list, and a key naming a check that reads the tree rather than
    running anything.
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
        unknown = unknown_placeholders(value)
        if unknown:
            raise ConfigError(
                f'[{operation}.commands] {key} names a placeholder this '
                f'package cannot fill: '
                f'{", ".join("{" + name + "}" for name in unknown)} — the '
                f'known placeholders are '
                f'{", ".join("{" + name + "}" for name in PLACEHOLDERS)}')
        if key in AFTER_COMMANDS and operation == 'release':
            # Not a check: the caller's own command, printed after the write.
            out[key] = value
            continue
        if key not in known:
            raise ConfigError(
                f'[{operation}.commands] {key} names no registered check — '
                f'the known checks are: {", ".join(sorted(known))}'
                + (f'; the after-belt commands are: '
                   f'{", ".join(sorted(AFTER_COMMANDS))}'
                   if operation == 'release' else ''))
        if key not in COMMANDABLE:
            raise ConfigError(
                f'[{operation}.commands] {key} reads the tree and runs '
                f'nothing — a command here would be two authorities over one '
                f'fact; the checks that take one are: '
                f'{", ".join(sorted(COMMANDABLE & set(known)))}')
        if key not in listed:
            raise ConfigError(
                f'[{operation}.commands] {key} is not in [{operation}] steps, '
                f'so it never runs — a command for a check that never runs is '
                f'a belief about the release that is not true')
        out[key] = value
    return out


def validate_config(operation: str, names: tuple[str, ...],
                    registry: dict) -> None:
    """Read EVERY `[<operation>]` key this module will need, and refuse now —
    before the first check, so a typo is exit 2 with nothing run."""
    commands_for(operation, names, registry)
    _timeout(operation)
    if 'changelog-unreleased-nonempty' in names:
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


def _changelog_of(operation: str) -> str:
    raw = _section(operation).get('changelog', 'CHANGELOG.md')
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(
            f'[{operation}] changelog must be a path, got {raw!r}')
    return raw


def _changelog(ctx: Context) -> Path:
    return ctx.root / _changelog_of(ctx.operation)


def _pin_file_of(operation: str) -> str:
    """Where the consumer's `DEVKIT_VERSION` line lives. Read, never written."""
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
    the semver gate already read. One fact, one home.
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
    sentences and none of them is a pass. Output is BOUNDED into the detail.
    """
    try:
        done = subprocess.run(command, cwd=str(ctx.root), shell=True,
                              capture_output=True, text=True,
                              timeout=_timeout(ctx.operation))
    except subprocess.TimeoutExpired:
        return Answer.no(
            f'`{_clip(command, 120)}` did not finish inside '
            f'{_timeout(ctx.operation)}s')
    except OSError as err:
        return Answer.unverifiable(
            f'`{_clip(command, 120)}` could not be run ({err})')
    tail = _clip(done.stdout + done.stderr)
    if done.returncode == 0:
        return Answer.yes(f'`{_clip(command, 120)}` exited 0')
    return Answer.no(f'`{_clip(command, 120)}` exited {done.returncode}'
                     + (f' — {tail}' if tail else ''))


# One run's answer to `[<operation>.commands]`, keyed by the checkout, the
# operation, and the BYTES of the devkit.toml it was derived from. The key
# makes the memo a DERIVATION and not a memory: any of the three changing
# re-derives it, so a test that rewrites devkit.toml under one root is never
# graded against the last case's answer.
_COMMANDS_MEMO: dict[tuple[str, str, bytes | None], dict[str, str]] = {}


def _configured(ctx: Context, step: str) -> str:
    """`[<operation>.commands] <step>`, or '' — asked ONCE per run."""
    from agentic_sdlc.core.project import CONFIG_NAME, repo_root

    path = repo_root() / CONFIG_NAME
    try:
        raw: bytes | None = path.read_bytes() if path.is_file() else None
    except OSError:
        raw = None
    key = (str(ctx.root), ctx.operation, raw)
    if key not in _COMMANDS_MEMO:
        _COMMANDS_MEMO[key] = commands_for(ctx.operation)
    command = _COMMANDS_MEMO[key].get(step, '')
    return substitute(command, ctx) if command else ''


# --- the pm predicates this module CALLS --------------------------------------
def ready_for(ctx: Context, target: str) -> Answer:
    """`pm ready-for <target> <grain>`, reported — never re-implemented.

    Called through `pm.cli.main`, which is the published contract (0 ready,
    1 not ready naming the blockers, 2 usage).
    """
    code, said = _pm_run(ctx, 'ready-for', target, ctx.version)
    if code == 0:
        return Answer.yes(said or f'`pm ready-for {target}` exited 0')
    if code == 1:
        return Answer.no(said or f'`pm ready-for {target}` exited 1')
    return Answer.unverifiable(
        f'`pm ready-for {target}` exited {code} — a usage or config error, so '
        f'nothing was decided: {said}')


# --- the release checks -------------------------------------------------------
def _belt_written(ctx: Context) -> str:
    """The one TRACKED path a gate run dirties by itself, or ''.

    R6: the installed `gdk_gate.sh` files a `gate` cost row per gate into the
    TRACKED `<milestone>/ledger.jsonl`, so the `gate` check of the previous
    run leaves that file modified. The census is unchanged (nothing is
    excluded); only the sentence knows whose path it is.
    """
    from agentic_sdlc.repo.pm import ledger

    cfg = _pm_cfg(ctx)
    path = model.milestone_file(cfg, ctx.version)
    return '' if path is None else cfg.rel(ledger.ledger_path(path.parent))


def check_tree_clean(ctx: Context) -> Answer:
    code, out = _git(ctx, 'status', '--porcelain', strip=False)
    if code != 0:
        return Answer.unverifiable(f'git status failed: {_clip(out)}')
    if not out.strip():
        return Answer.yes('no modified paths')
    paths = [line[3:] for line in out.split('\n') if len(line) > 3]
    mine = _belt_written(ctx)
    said = f'{len(paths)} modified path(s): {_clip(", ".join(paths))}'
    if mine and mine in paths:
        said += (f' — {mine} holds the gate cost rows `gate` filed on the '
                 f'last run; commit them')
    return Answer.no(said)


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
            f'check will not assume the current branch is the right one')
    here = _branch(ctx)
    if here == declared:
        return Answer.yes(f'HEAD is {here!r}')
    return Answer.no(f'HEAD is {here!r}; {cfg.rel(path)} declares '
                     f'branch: {declared!r}')


def _unreleased_span(text: str) -> tuple[int, int, list[str]] | str:
    """(start, end, body-lines) of the ONE `## Unreleased` section, or why not.

    Two headings is a refusal, not a choice of the first: the file would carry
    two stories about the same release.
    """
    lines = text.split('\n')
    at = [i for i, line in enumerate(lines)
          if line.strip().lower().startswith('## unreleased')]
    if not at:
        return 'there is no `## Unreleased` heading'
    if len(at) > 1:
        return (f'there are {len(at)} `## Unreleased` headings (lines '
                f'{", ".join(str(i + 1) for i in at)}) — ambiguous')
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
            f'{path.name} is not at {path} — this check reads the release '
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
    """Every configured version site names the release. READ, never bumped:
    the bump is the release commit, and it is the caller's (D12)."""
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
    return Answer.no(f'{"; ".join(found)} — the release is {ctx.version}; '
                     f'bump each site and commit')


def check_features_done(ctx: Context) -> Answer:
    return ready_for(ctx, 'milestone')


def check_findings_resolved(ctx: Context) -> Answer:
    """Every finding in every record this milestone POINTS AT is dispositioned
    — `pm ready-for tag`'s question, asked of the verb. The RECORD stays: it
    is what `reviewed:` points at, and deleting it leaves `check pm` D1 red."""
    return ready_for(ctx, 'tag')


def check_gate(ctx: Context) -> Answer:
    command = _configured(ctx, 'gate')
    if not command:
        return Answer.unverifiable(
            f'no [{ctx.operation}.commands] gate is configured — name the '
            f'full gate this project runs')
    return run_command(ctx, 'gate', command)


# --- the adopt checks ---------------------------------------------------------
def check_pin_bumped(ctx: Context) -> Answer:
    rel = _pin_file_of(ctx.operation)
    path = ctx.root / rel
    want = f'v{__version__}'
    if not path.is_file():
        return Answer.unverifiable(
            f'{rel} is not in this checkout, so there is no `DEVKIT_VERSION` '
            f'line to read — this check never creates one; write '
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
            f'{__version__} — edit that ONE line to `DEVKIT_VERSION := {want}`')
    return Answer.unverifiable(
        f'{rel} carries no `DEVKIT_VERSION` line — this check reads the pin '
        f'and does not add one')


def _installable_drift(ctx: Context) -> list[tuple[str, str, str]]:
    """(verb, path, verdict) for every file the `install-*` verbs write.

    Asked of `install.PLANS` rather than of a list here: a second inventory
    of the installables would be a second answer to what this version ships.
    A file the consumer never installed is `not-installed` and is NOT drift —
    `adopt` reads and names, it does not install.
    """
    from agentic_sdlc.repo import install

    out: list[tuple[str, str, str]] = []
    for verb, plan in install.PLANS.items():
        for name, rel in plan:
            target = ctx.root / rel
            if not target.is_file():
                out.append((verb, rel, 'not-installed'))
                continue
            text, _defect = install.read_destination(target)
            try:
                body = install.resolve_body(name, rel)
            except (OSError, UnicodeDecodeError, ConfigError) as err:
                out.append((verb, rel, f'unrenderable({_clip(str(err), 60)})'))
                continue
            if text is None:
                out.append((verb, rel, 'unreadable'))
            elif text == body:
                out.append((verb, rel, 'current'))
            elif install.header_only_difference(text, body):
                # The operator's own project-config header, and the rest of
                # the file byte-current. A difference, and not one to act on.
                out.append((verb, rel, 'header-only'))
            else:
                out.append((verb, rel, 'differs'))
    return out


def check_installables_current(ctx: Context) -> Answer:
    """Every installed file is byte-current with what this version ships (or
    differs only in its project-config header). Each that is not is NAMED
    with the verb that shows the diff. `--force` on that verb is whole-set,
    so take / hand-apply / keep is the consumer's call, made per file, outside
    this belt — this reads the result."""
    drift = _installable_drift(ctx)
    stale = [(verb, rel, verdict) for verb, rel, verdict in drift
             if verdict not in ('current', 'header-only', 'not-installed')]
    counted = sum(1 for _, _, v in drift if v != 'not-installed')
    if stale:
        return Answer.no(
            f'{len(stale)} of {counted} installed file(s) differ from what '
            f'{__version__} ships: '
            + _clip(', '.join(f'{rel} ({verdict}; `agentic-sdlc {verb} '
                              f'--diff`)' for verb, rel, verdict in stale)))
    return Answer.yes(f'{counted} installed file(s) are current with '
                      f'{__version__}')


def _config_readers() -> tuple[tuple[str, str, object], ...]:
    """The `devkit.toml` sections THIS version still reads: the section name
    the census reports it under, the label a refusal is spoken under, and the
    reader that refuses a value this version cannot use.

    ONE LIST. The census is DERIVED from this tuple, so the number in the line
    is the number that was asked. There is deliberately no table of RETIRED
    keys: a section this package no longer reads may be another kit's, and
    telling those apart would mean knowing the consumer (hard rule 8).
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
    `agentic_sdlc.cli`, so the universe is derived from below by the one
    mapping `cli._check_module` applies (`x-y` -> `checks/x_y.py`); a
    `_`-prefixed module is a shared helper. `tests/test_gate_roster.py`
    asserts the two sets are equal, so this cannot become the permissive one.
    """
    from agentic_sdlc.repo import checks as checks_pkg

    found = walk.matching(Path(checks_pkg.__file__).resolve().parent, '*.py',
                          walk.Kind.FILE)
    return frozenset(path.stem.replace('_', '-') for path in found
                     if not path.name.startswith('_'))


def _read_checks() -> None:
    """`[checks] all` — the roster `check all` runs here, refused as it
    refuses: the SHAPE through `str_tuple`, an unknown name by name."""
    from agentic_sdlc.core.config import str_tuple

    roster = str_tuple(config_section('checks'), 'checks', 'all', ())
    known = gate_universe()
    unknown = [name for name in roster if name not in known]
    if unknown:
        raise ConfigError(
            f'[checks] all names unknown gate(s) {", ".join(unknown)} — '
            f'known gates are {" ".join(sorted(known))}')


def _read_grain_shape() -> None:
    """`[grain_shape] caps`, through the gate's OWN reader."""
    from agentic_sdlc.repo.checks import grain_shape

    grain_shape._caps()


def _read_repo_hygiene() -> None:
    """`[repo_hygiene] mainline / protected`, through the gate's own reader."""
    from agentic_sdlc.repo.checks import repo_hygiene

    repo_hygiene.read_config()


def _read_verify() -> None:
    """`[verify]`, through `verify/rules.py`. An ABSENT section is not refused
    here: this asks whether what the repo DECLARED still parses."""
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
            # EVERY reader is asked, and every refusal is reported.
            refused.append(f'{label}: {_clip(str(err), 160)}')
    if refused:
        return Answer.no(
            f'{len(refused)} of {len(asked)} section(s) hold a value '
            f'{__version__} does not accept — {"; ".join(refused)}')
    declared = [name for name in asked if section_declared(name)]
    return Answer.yes(
        f'{len(asked)} reader(s) accept this repo\'s devkit.toml; '
        + (f'declared here: {", ".join(declared)}' if declared
           else 'no section is declared here, which is the stock default'))


def check_hooks_self_test(ctx: Context) -> Answer:
    """The installed guards still return the verdicts their own corpus
    asserts. `check hooks` owns the replay; this asks it."""
    command = _configured(ctx, 'hooks-self-test')
    if command:
        return run_command(ctx, 'hooks-self-test', command)
    if not (ctx.root / HOOKS_DIR).is_dir():
        return Answer.no(
            f'{HOOKS_DIR}/ is not in this checkout — `install-hooks` writes the '
            f'corpus and this check installs nothing; run the verb, or drop '
            f'`hooks-self-test` from [{ctx.operation}] steps')
    return _own_verdict(ctx, 'check', 'hooks',
                        found=f'{HOOKS_DIR}/ replayed')


def check_runner_targets_resolve(ctx: Context) -> Answer:
    """Every composed gate target resolves in THIS repo's make. A tier NAMED
    with no tier file is a parse-time `$(error)`; an EMPTY tier list prints
    its `[TIERS] … is empty` line and resolves — `-include`'s silence is never
    read as a pass."""
    command = _configured(ctx, 'runner-targets-resolve')
    if command:
        return run_command(ctx, 'runner-targets-resolve', command)
    if not (ctx.root / FRAMEWORK_MAKEFILE).is_file():
        return Answer.no(
            f'{FRAMEWORK_MAKEFILE} is not in this checkout — `install-gates` '
            f'writes it and this check installs nothing; run the verb, or drop '
            f'`runner-targets-resolve` from [{ctx.operation}] steps')
    targets = _runner_targets_of(ctx.operation)
    # `-n` composes everything and RUNS nothing.
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
    """THIS package's `check all` — never the consumer's `make check`."""
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
        return Answer.unverifiable(
            f'`pm validate` exited 2 — a usage or config error, so nothing '
            f'was decided (D11): {said}')
    return Answer.no(f'`pm validate` exited {code}: {said}')


# --- the story checks ---------------------------------------------------------
# Every question below is asked of the grain named on the command line —
# `ctx.version` is a story or feature id here, resolved by the tracker's own
# resolvers so this file and `pm story done` can never disagree about which
# file they mean.
def _grain_file(ctx: Context) -> Path | None:
    return grain_path(_pm_cfg(ctx), ctx.operation, ctx.version)


def check_story_exists(ctx: Context) -> Answer:
    cfg = _pm_cfg(ctx)
    try:
        path = _grain_file(ctx)
    except model.AmbiguousStory as err:
        return Answer.no(str(err))
    if path is None:
        return Answer.no(f'no story resolves from {ctx.version!r} under '
                         f'{cfg.roadmap_dir}/')
    return Answer.yes(cfg.rel(path))


def check_narrow_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --story` — the narrow rung, whatever it is HERE.

    The command is never named here: `[[verify.narrow]]` is the project's own
    answer to what proves an edit. Two rulings carried from the belt review:

    * **A census of zero is not a pass** (I1). On a committed tree the verb
      says "no changed paths" and exits 0; taken as proof, a story closed with
      its narrow check never run. So the rung is pointed at the STORY's own
      range — the base comes from the author's `done:` line, the same regex
      `evidence-written` reads — and an empty selection is UNVERIFIABLE.
    * **The roadmap directory is ignored** (I3): the operator's own
      `pm story building` is a changed path that matches no narrow rule and
      would send a story close to the milestone rung.
    """
    command = _configured(ctx, 'narrow-verified')
    if command:
        return run_command(ctx, 'narrow-verified', command)
    ignore = _belt_written_paths(ctx)
    base = _story_range_base(ctx)
    empty, why = _narrow_selects_nothing(ctx, ignore, base)
    if empty:
        return Answer.unverifiable(why)
    argv = ['verify', '--story']
    if base:
        argv += ['--ref', base]
    for path in ignore:
        argv += ['--ignore', path]
    return _own_verdict(ctx, *argv,
                        found='the narrow rung [verify] names')


def _story_range_base(ctx: Context) -> str:
    """`<earliest hash in the story's `done:` line>^`, or '' when none.

    `in-place` yields no base, correctly: uncommitted work is still in the
    diff. A hash git cannot resolve yields no base either — `evidence-written`
    is the check with an opinion about the line.
    """
    try:
        path = _grain_file(ctx)
    except model.AmbiguousStory:
        return ''
    if path is None:
        return ''
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError):
        return ''
    hashes: list[str] = []
    for raw in text.split('\n'):
        match = EVIDENCE_LINE.match(raw)
        if match is None:
            continue
        for token in EVIDENCE_LANDED.findall(match.group('body')):
            if token.lower() != IN_PLACE.lower():
                hashes.append(token)
    for candidate in hashes:
        code, out = _git(ctx, 'rev-parse', '--verify', f'{candidate}^')
        if code == 0 and out:
            return out.split('\n')[0].strip()
    return ''


def _belt_written_paths(ctx: Context) -> tuple[str, ...]:
    """The PM tree — the one directory `committed` also excludes, so the two
    exclusions cannot disagree."""
    cfg = _pm_cfg(ctx)
    return (cfg.roadmap_dir,)


def _narrow_selects_nothing(ctx: Context, ignore: tuple[str, ...],
                            base: str = '') -> tuple[bool, str]:
    """(is the narrow selection empty, the sentence saying why) — asked of
    `verify`'s own library rather than by parsing the verb's prose."""
    from agentic_sdlc.repo.verify import main as verify_main
    from agentic_sdlc.repo.verify import rules as verify_rules

    try:
        ruleset = verify_rules.read(config_section('verify'))
        selection = verify_main.plan_for(ruleset, ctx.root, base or None,
                                         ignore=list(ignore))
    except Exception as err:  # noqa: BLE001 — an answer, not a swallow
        # It could not decide; `_own_verdict` answers with the verb's own
        # exit code instead.
        return False, f'{type(err).__name__}: {err}'
    if selection.matched or selection.missed:
        return False, ''
    excluded = ', '.join(ignore) or "the PM tree"
    against = base or 'HEAD'
    tail = ('' if base else
            " — and this story's `done:` line names no commit to range from, "
            'so there was nothing to point it at')
    return True, (
        f'`agentic-sdlc verify --story` has NOTHING to scan: no path changed '
        f'against {against} outside {excluded}, so the narrow rung would exit '
        f'0 over a census of zero{tail}. Rule 4 — a census of zero is '
        f'reported, loudly, rather than passed over.')


def check_committed(ctx: Context) -> Answer:
    """No uncommitted work OUTSIDE the roadmap directory. It does not commit
    (no verb in this package does), and it NAMES what is outstanding rather
    than guessing which paths are this story's."""
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
            + (f' ({len(paths)} inside it)' if paths else ''))
    return Answer.no(f'{len(tree_paths)} uncommitted path(s): '
                     f'{_clip(", ".join(tree_paths))} — commit by explicit '
                     f'pathspec; this belt never commits')


def check_evidence_written(ctx: Context) -> Answer:
    """The story file carries the `done:` line pm-execution.md step 6 asks
    for. READ, never written: the sentence is the author's, and a generated
    one would be a second scoreboard saying what the commit already says."""
    cfg = _pm_cfg(ctx)
    try:
        path = _grain_file(ctx)
    except model.AmbiguousStory as err:
        return Answer.unverifiable(str(err))
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
        f'`{IN_PLACE}` for a fix that has not been committed yet')


# --- the feature checks -------------------------------------------------------
def check_stories_done(ctx: Context) -> Answer:
    """`pm ready-for feature <fid>` — never re-implemented. It accepts a story
    in ANY state of the `done` category and names each one that is not."""
    return ready_for(ctx, 'feature')


def check_feature_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --feature` — the range rung. Not in the shipped
    list (the story's check list does not name it); a project that wants it
    adds it to `[feature] steps`."""
    command = _configured(ctx, 'feature-verified')
    if command:
        return run_command(ctx, 'feature-verified', command)
    return _own_verdict(ctx, 'verify', '--feature',
                        found='the range rung [verify] names')


def _record_of(ctx: Context) -> tuple[Path | None, str]:
    """(the feature's review record, '' or why there is none).

    `model.review_record_for` is the resolver `pm feature done` uses, so the
    pointer this reads and the pointer that verb stamps are one fact. An
    ABSOLUTE pointer is refused rather than followed (hard rule 8).
    """
    cfg = _pm_cfg(ctx)
    pointer = model.review_record_for(cfg, ctx.version)
    if not pointer:
        return None, (f'{ctx.version} points at no review record — '
                      f'`reviewed:` is blank; run the feature review and '
                      f'`pm set {ctx.version} reviewed <path>`')
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
    """(the record's verdict blocks, '' or why they could not be read) —
    `verdict.parse`'s rulings, inherited whole."""
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
    """A review record EXISTS and its verdict block PARSES. Nothing more:
    whether the review was any good is not encodable."""
    path, defect = _record_of(ctx)
    if path is None:
        return Answer.no(defect)
    cfg = _pm_cfg(ctx)
    passes, why = _passes(ctx, path)
    if why:
        return Answer.unverifiable(
            f'{why} — a record whose verdict block does not parse is '
            f'UNVERIFIABLE, never a pass')
    return Answer.yes(f'{cfg.rel(path)} parses: {len(passes)} pass(es), '
                      f'{sum(len(p.findings) for p in passes)} finding(s)')


def check_findings_landed(ctx: Context) -> Answer:
    """No finding in the record sits at `disposition: open` — `verdict.OPEN`
    and `verdict.parse`, the same reader `ready-for tag` uses one grain up."""
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
                         f'{_clip(", ".join(opened))} — land each, or defer '
                         f'it in writing')
    return Answer.yes(f'{cfg.rel(path)}: {total} finding(s), none open')


# --- the registries -----------------------------------------------------------
def _registry(*checks: Check) -> dict[str, Check]:
    return {check.name: check for check in checks}


RELEASE_STEPS: dict[str, Check] = _registry(
    Check('tree-clean', check_tree_clean),
    Check('on-milestone-branch', check_on_milestone_branch),
    Check('changelog-unreleased-nonempty', check_changelog_unreleased_nonempty),
    Check('features-done', check_features_done),
    Check('findings-resolved', check_findings_resolved),
    Check('version-sync', check_version_sync),
    Check('gate', check_gate),
)

ADOPT_STEPS: dict[str, Check] = _registry(
    Check('pin-bumped', check_pin_bumped),
    Check('installables-current', check_installables_current),
    Check('config-updated', check_config_updated),
    Check('hooks-self-test', check_hooks_self_test),
    Check('runner-targets-resolve', check_runner_targets_resolve),
    Check('checks-pass', check_checks_pass),
    Check('pm-validates', check_pm_validates),
)

STORY_STEPS: dict[str, Check] = _registry(
    Check('story-exists', check_story_exists),
    Check('narrow-verified', check_narrow_verified),
    Check('committed', check_committed),
    Check('evidence-written', check_evidence_written),
)

FEATURE_STEPS: dict[str, Check] = _registry(
    Check('stories-done', check_stories_done),
    Check('review-recorded', check_review_recorded),
    Check('findings-landed', check_findings_landed),
    Check('feature-verified', check_feature_verified),
)

REGISTRIES: dict[str, dict[str, Check]] = {'release': RELEASE_STEPS,
                                           'adopt': ADOPT_STEPS,
                                           'story': STORY_STEPS,
                                           'feature': FEATURE_STEPS}


def registry_for(operation: str) -> dict[str, Check]:
    """The checks this package SHIPS for `operation`, by name. The registries
    are SEPARATE: `[adopt] steps = ["gate"]` is exit 2, not a release check
    borrowed into an adoption."""
    return dict(REGISTRIES.get(operation, {}))


# What must be true, in a sentence, for the GENERATED document. It lives beside
# the check rather than in the renderer, so there is exactly one place a
# check's meaning is written and it is the file that also runs it.
STEP_DOC: dict[str, str] = {
    'tree-clean': '`git status --porcelain` is empty.',
    'on-milestone-branch':
        'HEAD is the branch the milestone document stamps in `branch:` (D9).',
    'changelog-unreleased-nonempty':
        'the changelog\'s `## Unreleased` section holds at least one bullet.',
    'features-done':
        '`pm ready-for milestone <milestone>` exits 0 — every feature is in '
        'the `done` category, and no open bug names the milestone; each one '
        'that is not is NAMED.',
    'findings-resolved':
        '`pm ready-for tag <milestone>` exits 0 — every finding in every '
        'record the milestone\'s grains point at has a disposition other than '
        '`open`. The records STAY: they are what `reviewed:` points at.',
    'version-sync':
        'every configured version site names the release version. READ, '
        'never bumped: the bump is the release commit, and it is yours.',
    'gate': 'the configured gate command exits 0.',
    # --- adopt ---
    'pin-bumped':
        'the `DEVKIT_VERSION` line in this repo\'s own makefile names the '
        'version of the package that is running. A line in a file this '
        'package does not own, so it is read and never written.',
    'installables-current':
        'every installed file is byte-current with what this version ships, '
        'or differs only in its project-config header. Each that differs is '
        'named with the `install-* --diff` that shows it; take, hand-apply or '
        'keep is your call per file, and this reads the result.',
    'config-updated':
        'every devkit.toml section this version still READS accepts what this '
        'repo declares. There is no retired-key table: a section this package '
        'no longer reads may be another kit\'s (hard rule 8).',
    'hooks-self-test':
        '`check hooks` exits 0 — the installed guards are armed, executable, '
        'still start, and still return the verdicts their own corpus asserts.',
    'runner-targets-resolve':
        'the composed gate targets resolve under `make -n`. A tier named with '
        'no tier file FAILS here naming the file; an empty tier list passes '
        'and SAYS it was empty.',
    'checks-pass':
        'this package\'s `agentic-sdlc check all` exits 0. NOT `make check`: '
        'that verifies your code against your rules, and a version bump here '
        'cannot change its verdict.',
    'pm-validates':
        '`pm validate` exits 0. A repo with no PM tree is refused, never '
        'vacuously fine.',
    # --- story ---
    'story-exists': 'the story id resolves to exactly one document.',
    'narrow-verified':
        'the narrow rung exits 0 — `agentic-sdlc verify --story` over the '
        'story\'s own commit range (the base is the earliest hash in its '
        '`done:` line). A census of zero is UNVERIFIABLE, never a pass.',
    'committed':
        'nothing is uncommitted outside the roadmap directory. It NAMES what '
        'is, and it never commits.',
    'evidence-written':
        'the story file carries `done: <hash(es)> — <what shipped>` '
        '(pm-execution.md step 6). READ, never written: the sentence is the '
        'author\'s.',
    # --- feature ---
    'stories-done':
        '`pm ready-for feature <id>` exits 0 — every story under this feature '
        'is in the `done` category (any state of it), and each one that is '
        'not is NAMED.',
    'review-recorded':
        'the feature\'s `reviewed:` record exists, is repo-relative, and its '
        'verdict block PARSES (`pm/verdict.py`). Whether the review was any '
        'good is NOT checked and must not be.',
    'findings-landed':
        'no finding in that record sits at `disposition: open` — the same '
        'question `pm ready-for tag` asks one grain up, through the same '
        'parser.',
    'feature-verified':
        'the range rung exits 0 — `agentic-sdlc verify --feature`. Not in the '
        'shipped list; add it to `[feature] steps` to run it here.',
}

# What a check RUNS when the project configures no command for it. Only the
# checks that run something are here; the rest read the tree.
SHIPPED_ACTION: dict[str, str] = {
    'hooks-self-test': 'agentic-sdlc check hooks',
    'runner-targets-resolve': 'make -n <[adopt] runner_targets>',
    'checks-pass': 'agentic-sdlc check all',
    'pm-validates': 'agentic-sdlc pm validate',
    'narrow-verified': 'agentic-sdlc verify --story',
    'feature-verified': 'agentic-sdlc verify --feature',
    'stories-done': 'agentic-sdlc pm ready-for feature <id>',
    'features-done': 'agentic-sdlc pm ready-for milestone <id>',
    'findings-resolved': 'agentic-sdlc pm ready-for tag <id>',
}

# THE AFTER-LIST: what the caller does once a belt has written, as words.
# Every line here used to be a `do()` that performed it (D12 deleted those),
# or a thing the belt never could do. Printed on success and rendered into the
# protocol document. `{version}`, `{branch}` and `{mainline}` are filled by
# the driver from the tree.
AFTER: dict[str, tuple[str, ...]] = {
    'story': (
        'commit the roadmap directory — the status line and the ledger row '
        'this belt wrote',
        'when every story of the feature is done: `agentic-sdlc close feature '
        '<feature-id>`',
    ),
    'feature': (
        'commit the roadmap directory — the status line and the ledger row '
        'this belt wrote',
        'when every feature of the milestone is done: `agentic-sdlc release '
        '<version>`',
    ),
    'release': (
        'retitle the changelog: `## Unreleased` becomes `## v{version} — '
        '<ISO date>`, with a fresh empty `## Unreleased` above it',
        'commit the roadmap directory and the changelog as the release commit',
        'push the branch: `git push -u origin {branch}` — never the mainline',
        'open the PR from {branch} to {mainline}{pr_open}',
        'wait for the required checks on the PR to go green{ci_green}',
        'merge it as a MERGE COMMIT — the mainline is merge-commit-only, and '
        'a squash loses the milestone\'s range',
        'tag the merge commit and push the TAG ref only: `git tag v{version} '
        '&& git push origin refs/tags/v{version}` — a published tag is never '
        'force-moved',
        'prove the published artifact reports {version} from a cold cache'
        '{prove}',
        'open the next milestone, so the next release\'s notes have somewhere '
        'to go from the first commit',
    ),
    'adopt': (
        'commit the pin bump and every installable you took or hand-applied',
    ),
}


def after_lines(operation: str, commands: dict[str, str], *, version: str,
                branch: str, mainline: str) -> list[str]:
    """`AFTER[operation]` with the tree's words and the configured after-belt
    commands filled in — one function, used by the driver's `next:` lines and
    by the rendered document, so the two cannot say different things."""
    words = {'version': version, 'branch': branch, 'mainline': mainline}
    for key, slot in AFTER_COMMANDS.items():
        command = commands.get(key, '')
        if command:
            words[slot] = f': `{command.replace("{version}", version)}`'
        elif key == 'prove-artifact':
            words[slot] = (' — configure `[release.commands] prove-artifact` '
                           'to name how')
        else:
            words[slot] = ''
    return [line.format(**words) for line in AFTER.get(operation, ())]

# What is guidance rather than a check — real protocol with no checkable
# postcondition, rendered into the document beside the lists.
GUIDANCE: tuple[tuple[str, str], ...] = (
    ('Pick the bump yourself',
     'Patch, minor or major is a semver judgement about the interface, and no '
     'check can make it. Output-line-shape changes are minor at least; '
     'anything a consumer must edit for is major.'),
    ('The negative probe for a gate whose scoping changed',
     'Introduce the drift class into a scratch copy of a fixture repo and '
     'confirm the gate FAILS. It is not a check: the artifact is a judgement '
     'made in scratch, with nothing in the tree to read.'),
    ('The consumer follow-up',
     'A consumer bumps its pin, runs `install-* --diff`, and decides PER '
     'FILE. It is not a check: those are instructions for somebody in another '
     'repo, and this package gates on no other repo\'s state (hard rule 8).'),
    ('Forward only',
     'Nothing pushed is ever amended, rebased, reset or force-pushed. A '
     'botched commit is repaired with another commit, and a bad release is a '
     'new patch version — never a rewritten tag.'),
)
