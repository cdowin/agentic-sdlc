"""steps.py — the four check lists, as registries the driver runs.

A check is a question about the tree with a one-line answer; nothing here
performs anything (D12), and no check re-implements a predicate that has a
verb — `pm ready-for` and `verify` are called, never copied. Config lives in
`[<op>] steps`, `[<op>] skippable`, `[<op>.commands]`, `[<op>]
command_timeout`, `[release] changelog` / `version_files`, `[adopt] pin_file` /
`runner_targets` / `ours` (README); a repo with no `devkit.toml` runs the
shipped defaults byte-identically.
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
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      relpath_tuple, str_tuple)
from agentic_sdlc.repo.conveyor import lessons
from agentic_sdlc.repo.conveyor.driver import (Answer, Check, Context,
                                              OP_FEATURE, OP_STORY,
                                              grain_path)
from agentic_sdlc.repo.pm import model, remote, verdict

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

# `hooks-self-test` and `runner-targets-resolve` are here because both have
# bitten: a guard that fails open, and a silent `-include` of a missing file.
DEFAULT_ADOPT_STEPS = (
    'pin-bumped',
    'installables-current',
    'config-updated',
    'hooks-self-test',
    # After `hooks-self-test`, which proves the corpus replays, and before
    # the gates: this asks whether the couriers are WIRED and the vehicle they
    # call answers. A consumer bumping the pin pastes the settings block by
    # hand and nothing verified the paste — so the failure is files present,
    # hooks unarmed, no rows, no complaint.
    'telemetry-live',
    'runner-targets-resolve',
    'checks-pass',
    'pm-validates',
)

# The belt that runs dozens of times a day.
DEFAULT_STORY_STEPS = (
    'story-exists',
    'story-verified',
    'committed',
    'evidence-written',
)

DEFAULT_FEATURE_STEPS = (
    'stories-done',
    'feature-verified',
    'review-recorded',
    'findings-landed',
)

DEFAULT_STEPS: dict[str, tuple[str, ...]] = {
    'release': DEFAULT_RELEASE_STEPS,
    'adopt': DEFAULT_ADOPT_STEPS,
    OP_STORY: DEFAULT_STORY_STEPS,
    OP_FEATURE: DEFAULT_FEATURE_STEPS,
}

# WHICH CHECKS ARE DISPOSITIONABLE IS A DECLARATION, and the stock declaration
# is nothing (0.5.0/D5). `--skip <check> "<why>"` is refused BY NAME for any
# check `[<op>] skippable` does not name, so a project declaring nothing gets
# today's belt byte for byte — which keeps this key inside rule 9. A project
# that lists `tree-clean` is making a mistake the tool will let it make.
DEFAULT_SKIPPABLE: tuple[str, ...] = ()

# The one shipped default: the target `install-gates` writes.
DEFAULT_COMMANDS: dict[str, str] = {'gate': 'make milestone'}

# The checks that run something and so may take a command; a command for a
# tree-reading check would be two authorities over one fact.
COMMANDABLE = frozenset((
    'gate', 'hooks-self-test', 'runner-targets-resolve', 'checks-pass',
    'pm-validates', 'story-verified', 'feature-verified'))

# THE ENTRY EDGE. A belt's list above is what it asks at the CLOSE; this names
# the subset decidable BEFORE the work, which `pm ready-for <rung>` READS from
# here — never a list of its own, so a project declaring different
# `[<op>] steps` gets its own answer back.
#
# The story belt contributes exactly one: `story-verified` runs a command and
# `ready-for` boots nothing (hard rule 2); `evidence-written` is the author's
# `done:` line, which cannot be true before the story is built.
#
# `committed`'s exclusion is a RULING rather than a fact, and one word here
# reverses it, so the argument lives in full. It is NOT that reading git is
# forbidden — `check_committed` below reads it as text, as does `tree-clean`.
# Two legs:
#
#   (i)  up front it asks a DIFFERENT QUESTION. At the close: "this story's
#        work is committed." Up front it could only mean "start from a clean
#        tree" — one check meaning two things at two edges is the tool
#        deciding what a check MEANS (rule 9's edge), and they would drift.
#   (ii) `SDLC.md` states this project's execution model: N builders share one
#        worktree and builders never commit, so `git status --porcelain` is
#        dirty with other builders' edits during any real inner-loop call and
#        `ready-for story` would answer NOT READY on nearly every one. A rung
#        that cries wolf is one an agent learns to ignore, and the ignoring
#        generalises to the rungs that do work. (The git call is a COST, not a
#        rule, and is not what decides this.)
#
# `stories-done`, `features-done` and `findings-resolved` are absent because
# each IS a rung (`SHIPPED_ACTION` names `pm ready-for feature|milestone|tag`),
# and a check that is a rung cannot also be that rung's entry condition.
#
# A check named in no set is not an entry condition, and `ready-for` NAMES it
# as one it did not ask, rather than passing over it in silence (rule 11).
ENTRY_CONDITIONS = frozenset(('story-exists',))

# Caller commands printed on the after-list; a `[release.commands]` entry for
# one is accepted and shown there.
AFTER_COMMANDS: dict[str, str] = {'pr-open': 'pr_open', 'ci-green': 'ci_green',
                                  'prove-artifact': 'prove'}

# `{version}` is the belt's subject; `${HOME}`, `{}` and `{print $1}` pass
# through untouched, and an unknown identifier is exit 2.
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


# A check name lands in a table cell and in a line shape consumers grep.
STEP_NAME = re.compile(r'^[a-z][a-z0-9-]*$')
STEP_NAME_MAX = 40

# A gate writing 100 MB to stdout must still produce a bounded line. The
# narrower budgets are per MESSAGE, and they differ because the sentence around
# them differs: a command echoed back beside its exit code, a `done:` line
# quoted inside a longer finding, an exception rendered as an aside.
OUTPUT_LIMIT = 400
COMMAND_LIMIT = 120
QUOTED_LIMIT = 80
ASIDE_LIMIT = 160
LIST_LIMIT = 200
RENDER_ERROR_LIMIT = 60

# NOT exit codes but SECONDS: `git` is the one command here with its own
# timeout, because it runs outside a belt's `[<op>] timeout`.
GIT_TIMEOUT = 120

# The SHELL's codes for a command that never ran, synthesised so a caller
# cannot mistake "the tool said no" for "the tool is not installed": 127 not on
# PATH, 126 found and not executable, 124 killed by a timeout (`timeout(1)`'s).
# A command that DID run returns its own code and none of these are invented.
NOT_ON_PATH = 127
CANNOT_RUN = 126
TIMED_OUT = 124

# How many names a census line prints before it says how many more there are.
SHOWN_MAX = 5

# `git status --porcelain` is COLUMNAR: two status columns and a space, then
# the path. A blanket strip eats the first character of a path.
PORCELAIN_PREFIX = 3
DEFAULT_COMMAND_TIMEOUT = 1800

# --- what the adopt checks look at, all of it inside the checkout --------------
DEFAULT_PIN_FILE = 'Makefile'
DEFAULT_RUNNER_TARGETS = ('check', 'precommit', 'milestone')
# `[<op>] ours`: the installed files the project has taken over. Empty by
# default, because a file is claimed only by being named — the installables
# INVITE local edits (each ships a `Project config` section), so the belt
# grades what the project did not claim and NAMES what it did.
DEFAULT_OURS: tuple[str, ...] = ()
# The verdicts `_installable_drift` files each planned destination under.
CURRENT = 'current'
HEADER_ONLY = 'header-only'
NOT_INSTALLED = 'not-installed'
CLAIMED = 'claimed'
# What is not drift: byte-current, the operator's own project-config header,
# never installed, or claimed by the project under `[<op>] ours`.
NOT_DRIFT = (CURRENT, HEADER_ONLY, NOT_INSTALLED, CLAIMED)
# What the "N installed file(s)" count leaves out: a file that is not there,
# and a file this belt does not grade.
UNCOUNTED = (NOT_INSTALLED, CLAIMED)
# Written by `install-gates`; `adopt` only reads it.
FRAMEWORK_MAKEFILE = 'Makefile.devkit'
# Where `install-hooks` puts the corpus in every consumer.
HOOKS_DIR = 'tools/hooks'
# `:=`, `=`, `?=` and `+=` — somebody else's makefile, only ever read.
PIN_LINE = re.compile(r'^\s*DEVKIT_VERSION\s*[:?+]?=\s*(\S+)')

# --- what the close checks look at --------------------------------------------
# `done: <hash(es)> — <what shipped>` (pm-execution.md step 6), tolerant of
# case and whitespace because the shape checked is "evidence was left".
EVIDENCE_LINE = re.compile(r'^\s*done\s*:\s*(?P<body>\S.*)$', re.IGNORECASE)
# A commit hash or the literal `in-place`, both `pm/verdict.py`'s forms.
HASH_MIN, HASH_MAX = verdict.HASH_MIN_LEN, verdict.HASH_MAX_LEN
IN_PLACE = verdict.IN_PLACE
EVIDENCE_LANDED = re.compile(
    rf'\b(?:[0-9a-fA-F]{{{HASH_MIN},{HASH_MAX}}}|{IN_PLACE})\b', re.IGNORECASE)
# Quoted in the refusal; `check grain-shape` enforces caps.
EVIDENCE_BUDGET = 5
# The same read bound `ready-for` puts on a review record.
MAX_RECORD_BYTES = 1 << 20


# --- small helpers ------------------------------------------------------------
_SALIENT = re.compile(r'FAILED|^E {2,}|\bERROR\b|error:|Traceback|  DRIFT |\] FAIL|exited [1-9]')


def _clip(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """One bounded line of somebody else's output, preferring the lines that
    say what broke."""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    salient = [ln for ln in lines if _SALIENT.search(ln)]
    flat = ' '.join(' '.join(salient or lines).split())
    return flat if len(flat) <= limit else flat[:limit] + '…'


def _read(path: Path) -> str:
    """A file's text with its line endings INTACT."""
    with open(path, encoding='utf-8', newline='') as handle:
        return handle.read()


def _pm_cfg(ctx: Context) -> 'model.PmConfig':
    return replace(model.load(), root=ctx.root)


def _git(ctx: Context, *args: str, strip: bool = True) -> tuple[int, str]:
    """`git` in the checkout; a missing git is an exit code. `strip=False`
    keeps porcelain columns whose leading space carries meaning."""
    try:
        done = subprocess.run(('git',) + args, cwd=str(ctx.root),
                              capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except FileNotFoundError:
        return NOT_ON_PATH, 'git is not on PATH'
    except subprocess.TimeoutExpired:
        return TIMED_OUT, 'git timed out'
    except OSError as err:
        return CANNOT_RUN, str(err)
    out = done.stdout + done.stderr
    return done.returncode, out.strip() if strip else out.rstrip('\n')


def _branch(ctx: Context) -> str:
    code, out = _git(ctx, 'rev-parse', '--abbrev-ref', 'HEAD')
    return out if code == 0 else ''


def _run(ctx: Context, argv: list[str]) -> tuple[int, str]:
    """Any command in the checkout, with `_make`'s failure vocabulary — a
    missing binary is an exit code, never a crash."""
    try:
        done = subprocess.run(argv, cwd=str(ctx.root), capture_output=True,
                              text=True, timeout=_timeout(ctx.operation))
    except FileNotFoundError:
        return NOT_ON_PATH, f'{argv[0]} is not on PATH'
    except subprocess.TimeoutExpired:
        return TIMED_OUT, f'{argv[0]} timed out'
    except OSError as err:
        return CANNOT_RUN, str(err)
    return done.returncode, (done.stdout + done.stderr).strip()


def _read_text(path) -> str:
    """A file's text, or `''` — this module reads to DECIDE, and a file it
    cannot open is a check that says so rather than a traceback."""
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return ''


def _make(ctx: Context, *args: str) -> tuple[int, str]:
    """`make` in the checkout. A missing make is an exit code, never a crash."""
    try:
        done = subprocess.run(('make',) + args, cwd=str(ctx.root),
                              capture_output=True, text=True,
                              timeout=_timeout(ctx.operation))
    except FileNotFoundError:
        return NOT_ON_PATH, 'make is not on PATH'
    except subprocess.TimeoutExpired:
        return TIMED_OUT, 'make timed out'
    except OSError as err:
        return CANNOT_RUN, str(err)
    return done.returncode, (done.stdout + done.stderr).strip()


def _own_cli(ctx: Context, *argv: str) -> tuple[int, str, tuple[str, ...]]:
    """This package's own verb as a subprocess (`repo/` may not import
    `cli`), with `PYTHONPATH` naming the running package; returns the argv
    it ran so a test can assert what was run."""
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
        return TIMED_OUT, (f'`agentic-sdlc {" ".join(argv)}` did not finish inside '
                     f'{_timeout(ctx.operation)}s'), argv
    except OSError as err:
        return CANNOT_RUN, f'`agentic-sdlc {" ".join(argv)}` could not be run ({err})', argv
    return done.returncode, _clip(done.stdout + done.stderr), argv


def _own_verdict(ctx: Context, *argv: str, found: str = '') -> Answer:
    """One of this package's own gates as a check: exit 2 is UNVERIFIABLE
    (D11) — only for this callee, since a configured command is any shell."""
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


def _pm_run(ctx: Context, *argv: str, clip: bool = True) -> tuple[int, str]:
    """One `pm` verb in process with its exit code — `pm` is `repo/`, so it
    is imported rather than spawned.

    `clip=False` hands back what the verb printed. `_clip` is right for a
    DETAIL, which rule 6 bounds to one line, and wrong for anything READ out of
    the output: it keeps only the `_SALIENT` lines when any line matches, and
    cuts at `OUTPUT_LIMIT`.
    """
    import contextlib
    import io

    from agentic_sdlc.repo.pm import cli as pm_cli
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = pm_cli.main(list(argv))
    said = buffer.getvalue()
    return code, _clip(said) if clip else said


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
    """The ordered check list from `[<operation>] steps`, the stock default
    when absent (rule 5); duplicates collapse in declaration order and the
    collapse is reported."""
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


def skippable_for(operation: str, names: tuple[str, ...] | None = None,
                  registry: dict | None = None) -> tuple[str, ...]:
    """The checks this project will answer ITSELF — `[<operation>] skippable`,
    stock empty (`DEFAULT_SKIPPABLE`).

    Read through `str_tuple`, the same door every other list key uses, so a
    bare string is refused rather than iterated into four one-letter check
    names. An entry that is not a check of this belt, or one its `steps` does
    not run, is exit 2 by name: a declaration this machine cannot act on is a
    reading failure (rule 9), and the alternative is `--skip review-recrded`
    refused for a reason the caller cannot see. What a listed check MEANS is
    the project's business — `tree-clean` is a fact rather than a judgement,
    and a project that lists it gets exactly what it declared.
    """
    known = registry_for(operation) if registry is None else registry
    listed = steps_for(operation, known) if names is None else names
    declared = str_tuple(_section(operation), operation, 'skippable',
                         DEFAULT_SKIPPABLE)
    out: list[str] = []
    for index, value in enumerate(declared, start=1):
        defect = name_defect(value, f'[{operation}] skippable #{index}')
        if defect:
            raise ConfigError(defect)
        if value not in known:
            raise ConfigError(
                f'[{operation}] skippable names {value!r}, which no check is '
                f'registered for — the known checks are: '
                f'{", ".join(sorted(known))}')
        if value not in listed:
            raise ConfigError(
                f'[{operation}] skippable names {value!r}, which is not in '
                f'[{operation}] steps, so it never runs — declaring a check '
                f'skippable when nothing asks it is a belief about this belt '
                f'that is not true')
        if value not in out:
            out.append(value)
    return tuple(out)


def commands_for(operation: str, names: tuple[str, ...] | None = None,
                 registry: dict | None = None) -> dict[str, str]:
    """`[<operation>.commands]` merged over the shipped defaults; a command
    is refused or run whole, never sanitised."""
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
    """Read every `[<operation>]` key this module will need, so a typo is
    exit 2 before the first check runs."""
    commands_for(operation, names, registry)
    skippable_for(operation, names, registry)
    _timeout(operation)
    if 'changelog-unreleased-nonempty' in names:
        _changelog_retired(operation)
    if 'pin-bumped' in names:
        _pin_file_of(operation)
    if 'runner-targets-resolve' in names:
        _runner_targets_of(operation)
    if 'installables-current' in names:
        _ours_of(operation)


def _timeout(operation: str) -> int:
    value = _section(operation).get('command_timeout', DEFAULT_COMMAND_TIMEOUT)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(
            f'[{operation}] command_timeout must be a positive integer number '
            f'of seconds, got {value!r}')
    return value


def _changelog_retired(operation: str) -> None:
    """`[<op>] changelog` named the FILE this step counted bullets in. Named
    at exit 2, never ignored: a consumer still declaring it would keep a path
    nothing reads and believe they had pointed it somewhere."""
    if 'changelog' in _section(operation):
        raise ConfigError(
            f'[{operation}] changelog was retired in 0.6.0 — the step grades '
            f'every grain\'s `changelog:` field instead of counting bullets '
            f'in a file, so there is no path to name. `agentic-sdlc changelog '
            f'<id>` renders them. Remove the key')


def _pin_file_of(operation: str) -> str:
    """Where the consumer's `DEVKIT_VERSION` line lives. Read, never written."""
    raw = _section(operation).get('pin_file', DEFAULT_PIN_FILE)
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(
            f'[{operation}] pin_file must be one path, got {raw!r}')
    return raw


def _ours_of(operation: str) -> tuple[str, ...]:
    """The installed files this project has taken over — `[<op>] ours`.

    Read through `relpath_tuple`, the SAME path grammar every other path key
    in this package uses (`core/config.py`), so a bare string, an empty list,
    a traversal, a URL or an absolute path is exit 2 — a claim this machine
    cannot read is a reading failure (rule 9), never a silent claim.
    `installables-current` does not grade a claimed file; it names it.
    """
    claims = relpath_tuple(_section(operation), operation, 'ours', DEFAULT_OURS)
    # `relpath_tuple` guards what LEAVES the checkout; these two stay inside
    # it and still name no file (review O3): an empty string claims nothing, a
    # `.` claims the repo root, and both read like a claim while matching no
    # installed path.
    for claim in claims:
        if not claim.strip() or claim.strip() in ('.', './'):
            raise ConfigError(
                f'[{operation}] ours contains {claim!r}, which names no file — '
                f'a claim is one installed path this project has taken over, '
                f'e.g. ".github/workflows/verify.yml". Remove the entry, or '
                f'remove the key to claim nothing')
    return claims


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
    """path -> a regex with one group holding the version; the default is
    `[pm] version_file` / `version_pattern`."""
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
    """Run `command` in the checkout; exit 0 is true and nothing else is, with
    the output bounded into the detail."""
    try:
        done = subprocess.run(command, cwd=str(ctx.root), shell=True,
                              capture_output=True, text=True,
                              timeout=_timeout(ctx.operation))
    except subprocess.TimeoutExpired:
        return Answer.no(
            f'`{_clip(command, COMMAND_LIMIT)}` did not finish inside '
            f'{_timeout(ctx.operation)}s')
    except OSError as err:
        return Answer.unverifiable(
            f'`{_clip(command, COMMAND_LIMIT)}` could not be run ({err})')
    tail = _clip(done.stdout + done.stderr)
    if done.returncode == 0:
        return Answer.yes(f'`{_clip(command, COMMAND_LIMIT)}` exited 0')
    return Answer.no(f'`{_clip(command, COMMAND_LIMIT)}` exited {done.returncode}'
                     + (f' — {tail}' if tail else ''))


# Keyed by root, operation and the config bytes, so a rewritten devkit.toml
# re-derives rather than remembers.
_COMMANDS_MEMO: dict[tuple[str, str, bytes | None], dict[str, str]] = {}


def _configured(ctx: Context, step: str) -> str:
    """`[<operation>.commands] <step>`, or '' — asked once per run."""
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
def subject_grain(ctx: Context) -> str:
    """The GRAIN this operation is about — `ctx.version` for a close, and for
    `release`/`adopt` the milestone CLAIMING that version. One name, because
    the driver's WRITE asks the same question its checks do."""
    if ctx.operation not in ('release', 'adopt'):
        return ctx.version
    try:
        cfg = _pm_cfg(ctx)
    except Exception:  # noqa: BLE001 - a config this cannot read decides nothing
        return ctx.version
    return model.milestone_of_version(cfg, ctx.version) or ctx.version


def ready_for(ctx: Context, target: str) -> Answer:
    """`pm ready-for <target> <grain>` through `pm.cli.main` (0 ready, 1 not
    ready naming the blockers, 2 usage), never re-implemented.

    The blockers it NAMED ride on the answer, so a lesson recorded against one
    surfaces beside this check — read off the verb's own marker, never guessed
    from the sentence around it. Blockers off the WHOLE output, detail off the
    clipped one: `_clip` drops every line that does not look like a failure,
    and a blocker dropped that way takes its lesson with it.
    """
    code, printed = _pm_run(ctx, 'ready-for', target, subject_grain(ctx),
                            clip=False)
    said = _clip(printed)
    if code == 0:
        answer = Answer.yes(said or f'`pm ready-for {target}` exited 0')
    elif code == 1:
        answer = Answer.no(said or f'`pm ready-for {target}` exited 1')
    else:
        answer = Answer.unverifiable(
            f'`pm ready-for {target}` exited {code} — a usage or config error, '
            f'so nothing was decided: {said}')
    return replace(answer, names=lessons.blockers_named(printed))


# --- cleanliness, asked once for both belts -----------------------------------
class _GitUnreadable(Exception):
    """git itself did not answer — UNVERIFIABLE, never a false."""


def _uncommitted(ctx: Context) -> tuple[list[str], str]:
    """(the paths modified outside the roadmap directory, that directory).

    ONE reading for `tree-clean` and `committed`. They asked the same question
    and answered it differently — only `committed` excluded the roadmap
    directory — so a tree could satisfy the story belt and never `release`,
    and a belt writes in that directory BY DESIGN (the status, `gate` cost
    rows, `[emit]` events, a surfaced lesson). Nothing INSIDE is counted,
    deliberately: a tally would move with the belt's own writes, and rule 6's
    line shapes may not depend on what a run happened to record.
    """
    code, out = _git(ctx, 'status', '--porcelain', strip=False)
    if code != 0:
        raise _GitUnreadable(f'git status failed: {_clip(out)}')
    cfg = _pm_cfg(ctx)
    # `line[3:]`, not a strip: porcelain is COLUMNAR and column 0 carries
    # meaning, so a blanket strip eats the first character of the first path.
    paths = [line[PORCELAIN_PREFIX:] for line in out.split('\n')
             if len(line) > PORCELAIN_PREFIX]
    inside = f'{cfg.roadmap_dir}/'
    return [p for p in paths if not p.startswith(inside)], inside


# --- the release checks -------------------------------------------------------
def check_tree_clean(ctx: Context) -> Answer:
    """Nothing modified OUTSIDE the roadmap directory — the same ruling
    `committed` makes on the story belt, from the same reading."""
    try:
        outside, inside = _uncommitted(ctx)
    except _GitUnreadable as err:
        return Answer.unverifiable(str(err))
    if not outside:
        return Answer.yes(f'no modified path outside {inside}')
    return Answer.no(f'{len(outside)} modified path(s) outside {inside}: '
                     f'{_clip(", ".join(outside))}')


def check_on_milestone_branch(ctx: Context) -> Answer:
    cfg = _pm_cfg(ctx)
    path = model.milestone_file(cfg, subject_grain(ctx))
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
    if here != declared:
        return Answer.no(f'HEAD is {here!r}; {cfg.rel(path)} declares '
                         f'branch: {declared!r}')
    # REPORTED, never refused: refusing would change a shipped exit code for a
    # condition that has always been tolerated (rule 6).
    return Answer.yes(f'HEAD is {here!r}{_published(cfg.root, here)}')


def _published(root: Path, branch: str) -> str:
    """Whether the branch is anywhere but this disk, as a clause. Refs only.
    '' when the tree has no remote — quiet, not broken."""
    state = remote.read(root)
    if state is None:
        return ''
    if state.in_sync:
        return ', published'
    seen = 'ahead of' if state.published else 'on no'
    return f', {seen} remote — `{remote.push_command(branch)}`' 


def _unreleased_span(text: str) -> tuple[int, int, list[str]] | str:
    """(start, end, body-lines) of the one `## Unreleased` section, or why
    not; two headings is a refusal."""
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
    """Every grain closing here answered the changelog question — a sentence,
    or `none` (0.6.0).

    It counted BULLETS IN A FILE: one bullet passed a release of forty grains,
    and nothing bound a bullet to the work it described. It names the GRAIN
    now. The step KEEPS its name — a step id is contract (rule 6).
    """
    from agentic_sdlc.repo.pm import changelog as clog
    cfg = _pm_cfg(ctx)
    mid = subject_grain(ctx)
    if mid not in model.grain_index(cfg):
        return Answer.unverifiable(
            f'no grain resolves from {mid!r} to read `{clog.FIELD}:` from')
    entries = clog.collect(cfg, mid)
    if not entries:
        return Answer.unverifiable(f'{mid} holds no grains to read')
    silent = clog.unanswered(cfg, entries)
    if silent:
        named = ', '.join(e.gid for e in silent[:SHOWN_MAX])
        more = (f' (+{len(silent) - SHOWN_MAX} more)'
            if len(silent) > SHOWN_MAX else '')
        return Answer.no(
            f'{len(silent)} closed grain(s) answered neither: {named}{more} — '
            f'`agentic-sdlc pm set <id> {clog.FIELD} "<sentence>"`, or '
            f'`{clog.NEEDS_NONE}` to say it earned no consumer-visible line')
    said = clog.rows(entries)
    # Rule 4: `declined` is what a grain SAID, never the arithmetic remainder —
    # a grain that is simply not closed yet answered nothing and is neither.
    declined = sum(1 for e in entries if e.declined)
    return Answer.yes(f'{len(said)} entry/ies across {len(entries)} grain(s), '
                      f'{declined} declined with `{clog.NEEDS_NONE}`; every '
                      f'closed grain answered')


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
    """Every configured version site names the release; read, never bumped
    (D12)."""
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
    return ready_for(ctx, model.GRAIN_MILESTONE)


def check_findings_resolved(ctx: Context) -> Answer:
    """`pm ready-for tag`'s question, asked of the verb; the record stays
    because `reviewed:` points at it."""
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
    """(verb, path, verdict) for every file the `install-*` verbs write, from
    `install.PLANS`; `not-installed` is not drift, and a path the project
    claimed in `[<op>] ours` is CLAIMED — never read, never graded."""
    from agentic_sdlc.repo import install

    from agentic_sdlc.repo.pm import skills

    claimed = frozenset(_ours_of(ctx.operation))
    out: list[tuple[str, str, str]] = []
    # All SIX installers (CLAUDE.md's self-hosting list), not the five that
    # happen to share a module: the two guidance files drifted invisibly here,
    # with no `ours` key in play at all (review O2).
    everything = list(install.PLANS.items()) + [
        (skills.GUIDANCE_VERB, list(skills.GUIDANCE_PLAN))]
    for verb, plan in everything:
        for name, rel in plan:
            if rel in claimed:
                # The project declared this file its own. Grading it would be
                # this package holding an opinion about somebody else's file
                # — and the claim is printed, so it hides nothing.
                out.append((verb, rel, CLAIMED))
                continue
            target = ctx.root / rel
            if not target.is_file():
                out.append((verb, rel, NOT_INSTALLED))
                continue
            text, _defect = install.read_destination(target)
            try:
                body = (skills.guidance_body(name)
                        if verb == skills.GUIDANCE_VERB
                        else install.resolve_body(name, rel))
            except (OSError, UnicodeDecodeError, ConfigError) as err:
                out.append((verb, rel,
                            f'unrenderable({_clip(str(err), RENDER_ERROR_LIMIT)})'))
                continue
            if text is None:
                out.append((verb, rel, 'unreadable'))
            elif text == body:
                out.append((verb, rel, CURRENT))
            elif install.header_only_difference(text, body):
                # The operator's own project-config header; not drift.
                out.append((verb, rel, HEADER_ONLY))
            else:
                out.append((verb, rel, 'differs'))
    return out


def _claim_clause(operation: str,
                  drift: list[tuple[str, str, str]]) -> str:
    """What `[<op>] ours` claimed, counted and named, for the end of the
    `installables-current` line — on EVERY run, pass or fail.

    A claim that is never printed is a hiding place: eleven files could leave
    the belt's attention and the line would still read like a clean pass
    (rule 4). A claim naming a path this version does not install is reported
    rather than refused, because install plans change between versions. Empty
    when nothing is claimed, so a repo declaring no `ours` prints
    byte-identically to one with no devkit.toml at all (rule 5).
    """
    claimed = [rel for _, rel, verdict in drift if verdict == CLAIMED]
    planned = {rel for _, rel, _ in drift}
    unplanned = [rel for rel in _ours_of(operation) if rel not in planned]
    clause = ''
    if claimed:
        clause += (f'; {len(claimed)} claimed by [{operation}] ours and not '
                   f'graded: ' + _clip(', '.join(claimed)))
    if unplanned:
        clause += (f'; {len(unplanned)} claim(s) in [{operation}] ours name '
                   f'no file {__version__} installs: '
                   + _clip(', '.join(unplanned)))
    return clause


def check_installables_current(ctx: Context) -> Answer:
    """Every installed file the project did not claim is byte-current or
    header-only different; each that is not is named with the verb that shows
    the diff, and what `[<op>] ours` claimed is counted and named beside it.
    """
    drift = _installable_drift(ctx)
    stale = [(verb, rel, verdict) for verb, rel, verdict in drift
             if verdict not in NOT_DRIFT]
    counted = sum(1 for _, _, v in drift if v not in UNCOUNTED)
    # After the clip, never inside it: the claim is the one part of this line
    # that must survive a hundred drifted files.
    claims = _claim_clause(ctx.operation, drift)
    if stale:
        return Answer.no(
            f'{len(stale)} of {counted} installed file(s) differ from what '
            f'{__version__} ships: '
            + _clip(', '.join(f'{rel} ({verdict}; `agentic-sdlc {verb} '
                              f'--diff`)' for verb, rel, verdict in stale))
            + claims)
    if not counted:
        # Review O1, and milestone risk 2 as written: "a project can silence
        # the check by claiming every file." Claiming all leaves NOTHING
        # graded, and `ok — 0 installed file(s) are current` is rule 4's zero
        # census wearing a pass. Naming the claims makes the list a statement;
        # refusing to grade nothing stops it being a hiding place.
        return Answer.no(
            f'every installed file this belt would grade is claimed in '
            f'[{ctx.operation}] ours, so NOTHING was graded — a verdict over an '
            f'empty census is not a pass (CLAUDE.md rule 4). Un-claim the files '
            f'this project has not actually taken over' + claims)
    return Answer.yes(f'{counted} installed file(s) are current with '
                      f'{__version__}' + claims)


def _config_readers() -> tuple[tuple[str, str, object], ...]:
    """The `devkit.toml` sections this version reads: census name, refusal
    label, reader. No retired-key table — a section this package no longer
    reads may be another kit's (rule 8)."""
    from agentic_sdlc.repo import gates_extra

    return (
        ('checks', '[checks] all', _read_checks),
        ('gates', '[gates] extra', gates_extra.targets),
        ('pm', '[pm]', model.load),
        ('release', '[release] steps / commands',
         lambda: _read_operation('release')),
        ('adopt', '[adopt] steps / commands',
         lambda: _read_operation('adopt')),
        (OP_STORY, '[story] steps / commands',
         lambda: _read_operation(OP_STORY)),
        (OP_FEATURE, '[feature] steps / commands',
         lambda: _read_operation(OP_FEATURE)),
        ('grain_shape', '[grain_shape] caps', _read_grain_shape),
        ('repo_hygiene', '[repo_hygiene] mainline / protected',
         _read_repo_hygiene),
        ('verify', '[verify] rungs', _read_verify),
    )


def _read_operation(operation: str) -> None:
    known = registry_for(operation)
    names = steps_for(operation, known)
    validate_config(operation, names, known)


def gate_universe() -> frozenset[str]:
    """Every gate name `check all` can dispatch, derived from `checks/` by
    `cli._check_module`'s mapping; `tests/test_gate_roster.py` holds the two
    equal."""
    from agentic_sdlc.repo import checks as checks_pkg

    found = walk.matching(Path(checks_pkg.__file__).resolve().parent, '*.py',
                          walk.Kind.FILE)
    return frozenset(path.stem.replace('_', '-') for path in found
                     if not path.name.startswith('_'))


def _read_checks() -> None:
    """`[checks] all`, refused as `check all` refuses it."""
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
    """`[verify]` through `verify/rules.py`; an absent section is not
    refused."""
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
            # Every reader is asked, every refusal reported.
            refused.append(f'{label}: {_clip(str(err), ASIDE_LIMIT)}')
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
    """`check hooks` owns the replay; this asks it."""
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


def _recorded_phrase(ctx: Context) -> str:
    """`'dispatch, 3h ago'`, `'never'`, or why neither could be answered.

    Read through `check pm`'s U4 reader rather than spelled a second time here:
    two readers of one fact is how a belt and a gate come to disagree about
    whether a tree is recording. A tree this process cannot read as a PM tree
    is a named non-answer, never a silent 'never'.
    """
    from agentic_sdlc.repo.checks import pm as pm_check
    try:
        cfg = _pm_cfg(ctx)
    except ConfigError as err:
        return f'UNVERIFIABLE (the ledgers could not be located: {_clip(str(err), QUOTED_LIMIT)})'
    return pm_check.recording_phrase(pm_check.hook_recording(cfg))


def check_telemetry_live(ctx: Context) -> Answer:
    """Is this tree RECORDING — and if not, which of the four ways.

    **A probe, not an inspection.** Reading `.claude/settings.json` proves a
    string is present; this runs THIS TREE'S vehicle, `make -s pm
    ARGS="vocabulary"`. Not `--self-test`, which builds its own `mktemp` repo
    with its own stub `pm:` target and exits 0 from an empty directory.

    Three ways a bumping consumer records nothing, each silent, each named:
    the wiring was never registered with the harness (`install-hooks` prints
    the block and `--write-settings` lands it); the `pm` target is not
    `.PHONY`, and a PM tree IS a `pm/` directory, so make treats it as up to
    date; or `[pm.states.<kind>]` is undeclared, which makes every work-moving
    verb refuse by name.

    **The fourth was found by this build recording nothing**, and it is why the
    verdict line now carries the last hook-written ROW. Every check above reads
    CONFIG; whether the harness ever LOADS `.claude/settings.json` depends on
    the session's project root, so a session rooted above the checkout records
    nothing while all three answers stay green — six dispatches here produced
    zero `SubagentStop` rows and no surface said so, because the ledgers held
    status, decision and gate rows this checkout writes itself and nothing
    counted the KINDS. `wired` alone is the tool asserting an outcome it did
    not observe (rule 4).

    **It never refuses an adoption on its own.** The posture is *clearly
    available, warned when absent, never mandatory* (0.4.0/D5); what it must
    never be is SILENTLY opted out, so a tree that has recorded nothing is
    reported in the line rather than in the verdict. The wiring answer is
    `check pm`'s reader and the LEDGER outranks it: a tree registered in a
    settings file above this checkout is recording, and reading only the
    config called it dead.
    """
    command = _configured(ctx, 'telemetry-live')
    if command:
        return run_command(ctx, 'telemetry-live', command)
    from agentic_sdlc.repo.pm import model as pm_model
    absent = [name for name in pm_model.LEDGER_COURIERS
              if not (ctx.root / HOOKS_DIR / name).is_file()]
    if absent:
        return Answer.unverifiable(
            f'{", ".join(absent)} not in {HOOKS_DIR}/, so whether this tree '
            f'records cannot be probed — `install-hooks` writes the corpus, or '
            f'drop `telemetry-live` from [adopt] steps if this tree does not '
            f'record')
    # BOTH couriers, through `check pm`'s reader: it parses the `hooks` block
    # of both settings files, so an allowlist mention is not wiring and a
    # gitignored registration is not invisible.
    from agentic_sdlc.repo import install
    from agentic_sdlc.repo.checks import pm as pm_check
    registered = pm_check.wired_couriers(ctx.root)
    if registered.unread:
        return Answer.unverifiable(
            f'{registered.unread}, so whether this tree\'s couriers are '
            f'registered cannot be read — not a finding, and not a pass either')
    unwired = [name for name in pm_model.LEDGER_COURIERS
               if name not in registered.couriers]
    # The vehicle, in THIS tree: `vocabulary` is a read that needs make to
    # reach the CLI *and* the CLI to have a flow to answer with, which is
    # modes 2 and 3 in one call.
    code, out = _run(ctx, ['make', '-s', 'pm', 'ARGS=vocabulary'])
    if code == NOT_ON_PATH:
        return Answer.unverifiable('make is not on PATH')
    reached = code == 0 and any(kind in out for kind in pm_model.FLOW_KINDS)
    if not reached:
        return Answer.no(
            f'no ledger setup for this tree, no telemetry — `make -s pm '
            f'ARGS=vocabulary` did not reach the verb, so neither will a '
            f'courier. The usual causes are a `pm` target that is not .PHONY '
            f'(a PM tree IS a `pm/` directory, so make exits 0 without running '
            f'the recipe) and an undeclared [pm.states.*], which makes every '
            f'verb refuse by name: {_clip(out)}')
    recorded = _recorded_phrase(ctx)
    # The third answer, which branching on two of them dropped through to
    # `yes`: this said "telemetry is live" over a ledger it could not read
    # while U4 called that tree UNVERIFIABLE — one fact, two verdicts.
    if recorded.startswith(pm_check.UNVERIFIABLE):
        return Answer.unverifiable(
            f'the couriers are on disk and the vehicle answers, but the last '
            f'hook-written row cannot be read: {recorded}. Not a finding, and '
            f'not a pass either — `check pm` U4 says the same')
    if unwired and recorded == pm_check.NEVER:
        return Answer.no(
            f'no ledger setup for this tree, no telemetry — the vehicle '
            f'answers, nothing in this checkout registers '
            f'{", ".join(unwired)}, and no courier row has ever landed. '
            f'`install-hooks {install.SETTINGS_FLAG}` writes '
            f'{pm_model.AGENT_SETTINGS} when nothing is in the way, and prints '
            f'the block for whatever settings file your harness actually reads '
            f'when something is; a session rooted outside this tree also needs '
            f'`GDK_LEDGER_ROOT={ctx.root}`. Nothing here is mandatory — a tree '
            f'that has opted out is not broken, only quiet')
    where = (f'both couriers are registered in {registered.where}'
             if not unwired else
             'nothing in this checkout registers the couriers, so the settings '
             'file the harness loaded is above it — the LEDGER is what proves '
             'the path, and it did')
    wiring = f'{where} and `make -s pm` reaches the verb in this tree'
    if recorded == pm_check.NEVER:
        # TRUE, and honest: the wiring is right and nothing has come through.
        # Telemetry is never mandatory (0.4.0/D5), so the fact goes in the
        # line — but the line may not call it live, because no row was seen.
        return Answer.yes(
            f'{wiring}, and NOTHING has come through — last hook-written row: '
            f'{recorded}. Wiring is a CONFIG fact: whether a harness loads '
            f'{registered.where} depends on the session\'s project '
            f'root, so a session rooted above this checkout records nothing '
            f'while every wiring answer here stays green. `check pm` U4 '
            f'reports the same row on every run')
    return Answer.yes(f'telemetry is live: {wiring}, and the last hook-written '
                      f'row is {recorded}')


def check_runner_targets_resolve(ctx: Context) -> Answer:
    """Every composed gate target resolves under `make -n`; an empty tier
    list passes and says so."""
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
    if code == NOT_ON_PATH:
        return Answer.unverifiable('make is not on PATH')
    if code != 0:
        return Answer.no(
            f'`make -n {" ".join(targets)}` exited {code} — every later gate '
            f'runs through these targets: {_clip(out)}')
    empty = [line for line in out.split('\n') if '[TIERS]' in line]
    if empty:
        return Answer.yes(f'{len(targets)} target(s) resolve, and the tier '
                          f'lists are empty: {_clip(" ".join(empty), LIST_LIMIT)}')
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
# `ctx.version` is a story or feature id here, resolved by the tracker's own
# resolvers so this file and `pm story done` cannot disagree.
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


def check_story_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --story`, the story rung — the same call
    `feature-verified` makes one rung up; no range, no path census."""
    command = _configured(ctx, 'story-verified')
    if command:
        return run_command(ctx, 'story-verified', command)
    return _own_verdict(ctx, 'verify', '--story',
                        found='the story rung [verify] names')


def check_committed(ctx: Context) -> Answer:
    """No uncommitted work outside the roadmap directory; names what is
    outstanding and never commits. `_uncommitted` is the shared reading —
    `tree-clean` asks the same question of the same paths."""
    try:
        outside, inside = _uncommitted(ctx)
    except _GitUnreadable as err:
        return Answer.unverifiable(str(err))
    if not outside:
        return Answer.yes(f'no modified path outside {inside}')
    return Answer.no(f'{len(outside)} uncommitted path(s) outside {inside}: '
                     f'{_clip(", ".join(outside))} — commit by explicit '
                     f'pathspec; this belt never commits')


def check_evidence_written(ctx: Context) -> Answer:
    """The story file carries a `done:` line (pm-execution.md step 6); read,
    never written, because the sentence is the author's."""
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
                f'{cfg.rel(path)} `done: {_clip(body, QUOTED_LIMIT)}` names what landed '
                f'and not what shipped — the second half of the line is the '
                f'part a fresh session reads')
        return Answer.yes(f'{cfg.rel(path)} carries `done: {_clip(body, QUOTED_LIMIT)}`')
    return Answer.no(
        f'{cfg.rel(path)} `done: {_clip(lines[0], QUOTED_LIMIT)}` names no commit — a '
        f'hash of {HASH_MIN}-{HASH_MAX} hex characters, or the literal '
        f'`{IN_PLACE}` for a fix that has not been committed yet')


# --- the feature checks -------------------------------------------------------
def check_stories_done(ctx: Context) -> Answer:
    """`pm ready-for feature <fid>`, never re-implemented."""
    return ready_for(ctx, model.GRAIN_FEATURE)


def check_feature_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --feature`, the feature rung; not in the shipped
    list."""
    command = _configured(ctx, 'feature-verified')
    if command:
        return run_command(ctx, 'feature-verified', command)
    return _own_verdict(ctx, 'verify', '--feature',
                        found='the feature rung [verify] names')


def _record_of(ctx: Context) -> tuple[Path | None, str]:
    """(the feature's review record, '' or why there is none), through
    `model.review_record_for`; an absolute pointer is refused (rule 8)."""
    cfg = _pm_cfg(ctx)
    pointer = model.review_record_for(cfg, ctx.version)
    if not pointer:
        return None, (f'{ctx.version} points at no review record — '
                      f'`reviewed:` is blank; run the feature review and '
                      f'`pm set {ctx.version} reviewed <path>`')
    # `model.pointer_escapes`, not a local spelling of it: this hand-rolled
    # `/` + `~` pair accepted `../outside.md` and `file:x.md`, which the shared
    # predicate refuses. F1's class, in a second verb.
    if model.pointer_escapes(pointer):
        return None, (f'reviewed: {pointer!r} is not repo-relative — nothing '
                      f'outside this checkout is read (hard rule 8)')
    path = model.record_path(cfg, pointer)
    if not path.is_file():
        return None, f'reviewed: names no file ({pointer})'
    size = path.stat().st_size
    if size > MAX_RECORD_BYTES:
        return None, (f'reviewed: the record is {size} bytes, over the '
                      f'{MAX_RECORD_BYTES}-byte read bound ({pointer})')
    return path, ''


def _passes(ctx: Context, path: Path) -> tuple[list, str]:
    """(the record's verdict blocks, '' or why they could not be read), with
    `verdict.parse`'s rulings inherited whole."""
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
    """A review record exists and its verdict block parses; whether the
    review was any good is not encodable."""
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
    """No finding in the record sits at `disposition: open`, through the same
    reader `ready-for tag` uses one grain up."""
    path, defect = _record_of(ctx)
    if path is None:
        return Answer.no(defect)
    cfg = _pm_cfg(ctx)
    passes, why = _passes(ctx, path)
    if why:
        return Answer.unverifiable(why)
    opened = [f for p in passes for f in p.findings
               if f.disposition_kind == verdict.OPEN]
    blocking = [f.id for f in opened
                if f.severity in verdict.BLOCKING_SEVERITIES]
    minor = [f.id for f in opened
             if f.severity not in verdict.BLOCKING_SEVERITIES]
    total = sum(len(p.findings) for p in passes)
    # SEVERITY gates the hold. An open NIT used to block a close as hard as a
    # shipping bug, so a review that did its job — writing down the cheap
    # observations too — cost more to clear than it was worth, and the next
    # reviewer learns to stop writing them.
    if blocking:
        return Answer.no(
            f'{len(blocking)} blocking finding(s) open in {cfg.rel(path)}: '
            f'{_clip(", ".join(blocking))} — land each, or defer it in writing'
            + (f' ({len(minor)} non-blocking also open, which do not hold this '
               f'close)' if minor else ''))
    said = f'{cfg.rel(path)}: {total} finding(s), none blocking'
    if minor:
        # Reported on every run: not blocking is not the same as not there.
        said += (f'; {len(minor)} open below MAJOR carried forward: '
                 + _clip(', '.join(minor)))
    return Answer.yes(said)


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
    Check('telemetry-live', check_telemetry_live),
    Check('runner-targets-resolve', check_runner_targets_resolve),
    Check('checks-pass', check_checks_pass),
    Check('pm-validates', check_pm_validates),
)

STORY_STEPS: dict[str, Check] = _registry(
    Check('story-exists', check_story_exists),
    Check('story-verified', check_story_verified),
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
                                           OP_STORY: STORY_STEPS,
                                           OP_FEATURE: FEATURE_STEPS}


def registry_for(operation: str) -> dict[str, Check]:
    """The checks shipped for `operation`, by name; the registries are
    separate, so `[adopt] steps = ["gate"]` is exit 2."""
    return dict(REGISTRIES.get(operation, {}))


# One sentence per check for the rendered document, beside the check that
# runs it.
STEP_DOC: dict[str, str] = {
    'telemetry-live':
        'BOTH ledger couriers are registered with your harness AND `make -s '
        'pm` reaches the verb in THIS tree — a probe of your vehicle, not a '
        'file read and not the courier\'s own hermetic self-test, which '
        'passes from an empty directory. The registration is read out of '
        '`.claude/settings.json` and `.claude/settings.local.json`, and a '
        'courier row in the ledger outranks both: it proves the path wherever '
        'the config lives. Never mandatory: a tree that has opted out is '
        'quiet, not broken.',
    'tree-clean':
        '`git status --porcelain` names no path outside the roadmap '
        'directory — the same reading `committed` makes on the story belt. '
        'What is modified INSIDE it is neither read nor counted, because the '
        'belt writes there by design: the status it lands, `gate`\'s cost '
        'rows, every `[emit]` event.',
    'on-milestone-branch':
        'HEAD is the branch the milestone document stamps in `branch:` (D9).',
    'changelog-unreleased-nonempty':
        'the changelog\'s `## Unreleased` section holds at least one bullet.',
    'features-done':
        '`pm ready-for milestone <milestone>` exits 0 — every feature is in '
        'the `done` category and no open bug names the milestone.',
    'findings-resolved':
        '`pm ready-for tag <milestone>` exits 0 — no finding in any record '
        'the milestone\'s grains point at is `open`.',
    'version-sync':
        'every configured version site names the release version; read, '
        'never bumped.',
    'gate': 'the configured gate command exits 0.',
    # --- adopt ---
    'pin-bumped':
        'the `DEVKIT_VERSION` line in this repo\'s own makefile names the '
        'version of the package that is running.',
    'installables-current':
        'every installed file the project has not claimed in `[<op>] ours` is '
        'byte-current with what this version ships, or differs only in its '
        'project-config header; each that differs is named with the '
        '`install-* --diff` that shows it, and what was claimed is counted and '
        'named beside it, on every run.',
    'config-updated':
        'every devkit.toml section this version reads accepts what this repo '
        'declares.',
    'hooks-self-test':
        '`check hooks` exits 0 — the installed guards still return the '
        'verdicts their own corpus asserts.',
    'runner-targets-resolve':
        'the composed gate targets resolve under `make -n`; an empty tier '
        'list passes and says so.',
    'checks-pass':
        'this package\'s `agentic-sdlc check all` exits 0 — not '
        '`make check`, which verifies your code against your rules.',
    'pm-validates':
        '`pm validate` exits 0; a repo with no PM tree is refused.',
    # --- story ---
    'story-exists': 'the story id resolves to exactly one document.',
    'story-verified':
        '`agentic-sdlc verify --story` exits 0 — the make target '
        '`[verify] story` names, the way `feature-verified` runs its rung.',
    'committed':
        'nothing is uncommitted outside the roadmap directory; it names what '
        'is and never commits — the same reading `tree-clean` makes on '
        '`release`, so the two belts cannot disagree about one tree.',
    'evidence-written':
        'the story file carries `done: <hash(es)> — <what shipped>`; read, '
        'never written.',
    # --- feature ---
    'stories-done':
        '`pm ready-for feature <id>` exits 0 — every story under this feature '
        'is in the `done` category.',
    'review-recorded':
        'the feature\'s `reviewed:` record exists, is repo-relative, and its '
        'verdict block parses.',
    'findings-landed':
        'no finding in that record sits at `disposition: open`.',
    'feature-verified':
        '`agentic-sdlc verify --feature` exits 0; not in the shipped list, '
        'add it to `[feature] steps`.',
}

# What a check runs when the project configures no command for it.
SHIPPED_ACTION: dict[str, str] = {
    'hooks-self-test': 'agentic-sdlc check hooks',
    'telemetry-live': 'make -s pm ARGS=vocabulary',
    'runner-targets-resolve': 'make -n <[adopt] runner_targets>',
    'checks-pass': 'agentic-sdlc check all',
    'pm-validates': 'agentic-sdlc pm validate',
    'story-verified': 'agentic-sdlc verify --story',
    'feature-verified': 'agentic-sdlc verify --feature',
    'stories-done': 'agentic-sdlc pm ready-for feature <id>',
    'features-done': 'agentic-sdlc pm ready-for milestone <id>',
    'findings-resolved': 'agentic-sdlc pm ready-for tag <id>',
}

# The other value a check's `runs` column takes, and the whole vocabulary with
# it: a check either runs a shipped command or reads the tree. Spelled once,
# for the rendered protocol table and for the `ran` field of every
# `check.verdict` event, which are the same fact in two carriers.
READS_THE_TREE = 'reads the tree'


def ran_of(check: str, commands: dict[str, str]) -> str:
    """What this check RAN: the project's command, the shipped one, or the
    literal. `commands` is `commands_for(operation)`, already merged."""
    return commands.get(check) or SHIPPED_ACTION.get(check) or READS_THE_TREE

# What the caller does after a write, printed on success and rendered into the
# document; `{version}`, `{branch}` and `{mainline}` are filled by the driver.
AFTER: dict[str, tuple[str, ...]] = {
    OP_STORY: (
        'commit the roadmap directory — the status line and the ledger row '
        'this belt wrote',
        'when every story of the feature is done: `agentic-sdlc close feature '
        '<feature-id>`',
    ),
    OP_FEATURE: (
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
    """`AFTER[operation]` with the tree's words filled in — one function for
    the driver's `next:` lines and the rendered document."""
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

# Real protocol with no checkable postcondition, rendered beside the lists.
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
