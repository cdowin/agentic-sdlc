"""steps.py — the four check lists, as registries the driver runs.

A check is a question about the tree with a one-line answer; nothing here
performs anything (D12), and no check re-implements a predicate that has a
verb — `pm ready-for` and `verify` are called, never copied. Config lives in
`[<op>] steps`, `[<op>.commands]`, `[<op>] command_timeout`, `[release]
changelog` / `version_files`, `[adopt] pin_file` / `runner_targets` (README);
a repo with no `devkit.toml` runs the shipped defaults byte-identically.
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

# `hooks-self-test` and `runner-targets-resolve` are here because both have
# bitten: a guard that fails open, and a silent `-include` of a missing file.
DEFAULT_ADOPT_STEPS = (
    'pin-bumped',
    'installables-current',
    'config-updated',
    'hooks-self-test',
    'runner-targets-resolve',
    'checks-pass',
    'pm-validates',
)

# The belt that runs dozens of times a day.
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

# The one shipped default: the target `install-gates` writes.
DEFAULT_COMMANDS: dict[str, str] = {'gate': 'make milestone'}

# The checks that run something and so may take a command; a command for a
# tree-reading check would be two authorities over one fact.
COMMANDABLE = frozenset((
    'gate', 'hooks-self-test', 'runner-targets-resolve', 'checks-pass',
    'pm-validates', 'narrow-verified', 'feature-verified'))

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

# A gate writing 100 MB to stdout must still produce a bounded line.
OUTPUT_LIMIT = 400
DEFAULT_COMMAND_TIMEOUT = 1800

# --- what the adopt checks look at, all of it inside the checkout --------------
DEFAULT_PIN_FILE = 'Makefile'
DEFAULT_RUNNER_TARGETS = ('check', 'precommit', 'milestone')
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
        return 124, (f'`agentic-sdlc {" ".join(argv)}` did not finish inside '
                     f'{_timeout(ctx.operation)}s'), argv
    except OSError as err:
        return 126, f'`agentic-sdlc {" ".join(argv)}` could not be run ({err})', argv
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


def _pm_run(ctx: Context, *argv: str) -> tuple[int, str]:
    """One `pm` verb in process with its exit code — `pm` is `repo/`, so it
    is imported rather than spawned."""
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
def ready_for(ctx: Context, target: str) -> Answer:
    """`pm ready-for <target> <grain>` through `pm.cli.main` (0 ready, 1 not
    ready naming the blockers, 2 usage), never re-implemented."""
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
    """The one tracked path a gate run dirties by itself, or '': `gdk_gate.sh`
    files gate cost rows into the milestone ledger."""
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
    return ready_for(ctx, 'milestone')


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
    `install.PLANS`; `not-installed` is not drift."""
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
                # The operator's own project-config header; not drift.
                out.append((verb, rel, 'header-only'))
            else:
                out.append((verb, rel, 'differs'))
    return out


def check_installables_current(ctx: Context) -> Answer:
    """Every installed file is byte-current or header-only different; each
    that is not is named with the verb that shows the diff."""
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


def check_narrow_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --story` over the story's own commit range,
    ignoring the roadmap directory; an empty selection is UNVERIFIABLE
    (rule 4)."""
    command = _configured(ctx, 'narrow-verified')
    if command:
        return run_command(ctx, 'narrow-verified', command)
    ignore = _belt_written_paths(ctx)
    base, head = _story_range(ctx)
    empty, why = _narrow_selects_nothing(ctx, ignore, base, head)
    if empty:
        return Answer.unverifiable(why)
    argv = ['verify', '--story']
    if base:
        argv += ['--ref', base]
    if head:
        argv += ['--to', head]
    for path in ignore:
        argv += ['--ignore', path]
    return _own_verdict(ctx, *argv,
                        found='the narrow rung [verify] names')


def _story_range(ctx: Context) -> tuple[str, str]:
    """(`<earliest done: hash>^`, `<latest hash>`), each '' when none — the
    story's own range, so a late close verifies the same edits."""
    try:
        path = _grain_file(ctx)
    except model.AmbiguousStory:
        return '', ''
    if path is None:
        return '', ''
    try:
        text = _read(path)
    except (OSError, UnicodeDecodeError):
        return '', ''
    hashes: list[str] = []
    for raw in text.split('\n'):
        match = EVIDENCE_LINE.match(raw)
        if match is None:
            continue
        for token in EVIDENCE_LANDED.findall(match.group('body')):
            if token.lower() != IN_PLACE.lower():
                hashes.append(token)
    resolved = []
    for candidate in hashes:
        code, out = _git(ctx, 'rev-parse', '--verify', f'{candidate}^{{commit}}')
        if code == 0 and out:
            resolved.append(out.split('\n')[0].strip())
    if not resolved:
        return '', ''
    code, out = _git(ctx, 'rev-parse', '--verify', f'{resolved[0]}^')
    base = out.split('\n')[0].strip() if code == 0 and out else ''
    return base, resolved[-1]


def _belt_written_paths(ctx: Context) -> tuple[str, ...]:
    """The PM tree — the one directory `committed` also excludes."""
    cfg = _pm_cfg(ctx)
    return (cfg.roadmap_dir,)


def _narrow_selects_nothing(ctx: Context, ignore: tuple[str, ...],
                            base: str = '', head: str = '') -> tuple[bool, str]:
    """(is the narrow selection empty, the sentence saying why), asked of
    `verify`'s own library."""
    from agentic_sdlc.repo.verify import main as verify_main
    from agentic_sdlc.repo.verify import rules as verify_rules

    try:
        ruleset = verify_rules.read(config_section('verify'))
        selection = verify_main.plan_for(ruleset, ctx.root, base or None,
                                         ignore=list(ignore), to=head or None)
    except Exception as err:  # noqa: BLE001 — an answer, not a swallow
        # It could not decide; `_own_verdict` answers with the verb's code.
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
    """No uncommitted work outside the roadmap directory; names what is
    outstanding and never commits."""
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
    """`pm ready-for feature <fid>`, never re-implemented."""
    return ready_for(ctx, 'feature')


def check_feature_verified(ctx: Context) -> Answer:
    """`agentic-sdlc verify --feature`, the range rung; not in the shipped
    list."""
    command = _configured(ctx, 'feature-verified')
    if command:
        return run_command(ctx, 'feature-verified', command)
    return _own_verdict(ctx, 'verify', '--feature',
                        found='the range rung [verify] names')


def _record_of(ctx: Context) -> tuple[Path | None, str]:
    """(the feature's review record, '' or why there is none), through
    `model.review_record_for`; an absolute pointer is refused (rule 8)."""
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
    """The checks shipped for `operation`, by name; the registries are
    separate, so `[adopt] steps = ["gate"]` is exit 2."""
    return dict(REGISTRIES.get(operation, {}))


# One sentence per check for the rendered document, beside the check that
# runs it.
STEP_DOC: dict[str, str] = {
    'tree-clean': '`git status --porcelain` is empty.',
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
        'every installed file is byte-current with what this version ships, '
        'or differs only in its project-config header; each that differs is '
        'named with the `install-* --diff` that shows it.',
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
    'narrow-verified':
        '`agentic-sdlc verify --story` exits 0 over the story\'s own commit '
        'range; a census of zero is unverifiable, never a pass.',
    'committed':
        'nothing is uncommitted outside the roadmap directory; it names what '
        'is and never commits.',
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
    'runner-targets-resolve': 'make -n <[adopt] runner_targets>',
    'checks-pass': 'agentic-sdlc check all',
    'pm-validates': 'agentic-sdlc pm validate',
    'narrow-verified': 'agentic-sdlc verify --story',
    'feature-verified': 'agentic-sdlc verify --feature',
    'stories-done': 'agentic-sdlc pm ready-for feature <id>',
    'features-done': 'agentic-sdlc pm ready-for milestone <id>',
    'findings-resolved': 'agentic-sdlc pm ready-for tag <id>',
}

# What the caller does after a write, printed on success and rendered into the
# document; `{version}`, `{branch}` and `{mainline}` are filled by the driver.
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
