"""steps.py — the release step list, as a registry the driver walks.

`driver.py` is the machine; this is what it walks. Twenty-one steps, each with
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

## Two predicates this module CALLS rather than re-implements

`review-landed` and `features-done` go through `pm ready-for tag|milestone`.
They do not parse a verdict block and do not read frontmatter with a regex. Two
readers of "is every finding dispositioned" are two answers, and the second one
is the permissive one on the day they disagree — the argument `gates_extra.py`
already makes about a second TOML reader. This module does not import
`agentic_sdlc.repo.pm.verdict` at all, and a test asserts it.

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

Every refusal here exits 2 through `ConfigError`: a typo is a config mistake,
not a finding, and a release list that quietly got shorter is the cardinal sin
with a config file in front of it. The step that vanishes is `review-landed`.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import replace
from pathlib import Path

from agentic_sdlc.core import apply, walk
from agentic_sdlc.core.config import ConfigError, config_section
from agentic_sdlc.repo.conveyor.driver import Answer, Context, Step, StepKind
from agentic_sdlc.repo.pm import model

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

_SEMVER_TAG = re.compile(r'v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?')


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


def _git(ctx: Context, *args: str) -> tuple[int, str]:
    """`git` in the checkout. A missing git is an exit code, never a crash."""
    try:
        done = subprocess.run(('git',) + args, cwd=str(ctx.root),
                              capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return 127, 'git is not on PATH'
    except subprocess.TimeoutExpired:
        return 124, 'git timed out'
    except OSError as err:
        return 126, str(err)
    return done.returncode, (done.stdout + done.stderr).strip()


def _branch(ctx: Context) -> str:
    code, out = _git(ctx, 'rev-parse', '--abbrev-ref', 'HEAD')
    return out if code == 0 else ''


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
        if operation == 'release':
            return DEFAULT_RELEASE_STEPS
        # No default list for an operation this package ships no registry for.
        # `plan_defect` then refuses "the list is empty" — which is the true
        # sentence, and better than inventing a plausible one.
        return ()
    if not isinstance(raw, list):
        raise ConfigError(
            f'[{operation}] steps must be a list of strings, got {raw!r}'
            + (f' — write steps = [{raw!r}]' if isinstance(raw, str) else ''))
    if not raw:
        raise ConfigError(
            f'[{operation}] steps is empty — remove the key to take the '
            f'default ({" ".join(DEFAULT_RELEASE_STEPS)}) rather than '
            f'declaring nothing')
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


def _configured(ctx: Context, step: str) -> str:
    return commands_for(ctx.operation).get(step, '')


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
def check_tree_clean(ctx: Context) -> Answer:
    code, out = _git(ctx, 'status', '--porcelain')
    if code != 0:
        return Answer.unverifiable(f'git status failed: {_clip(out)}')
    if not out:
        return Answer.yes('no modified paths')
    paths = [line[3:] for line in out.split('\n') if len(line) > 3]
    return Answer.no(f'{len(paths)} modified path(s): {_clip(", ".join(paths))}')


def do_tree_clean(ctx: Context) -> str:
    return ('commit or stash your own paths — this machine never commits for '
            'you, and a release cut from a tree it changed is a release '
            'nobody reviewed')


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


def check_main_merged(ctx: Context) -> Answer:
    mainline = model.mainline_branch()
    for ref in (f'origin/{mainline}', mainline):
        code, _ = _git(ctx, 'rev-parse', '--verify', '--quiet', ref)
        if code != 0:
            continue
        code, out = _git(ctx, 'merge-base', '--is-ancestor', ref, 'HEAD')
        if code == 0:
            return Answer.yes(f'{ref} is an ancestor of HEAD')
        return Answer.no(f'{ref} is not an ancestor of HEAD — merge it in '
                         f'before the release reads this tree')
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

REGISTRIES: dict[str, dict[str, Step]] = {'release': RELEASE_STEPS}


def registry_for(operation: str) -> dict[str, Step]:
    """The steps this package SHIPS for `operation`, by name.

    `adopt` has its own feature and its own list; an operation with no registry
    yet answers {} and `plan_defect` then refuses to walk it, which is the true
    sentence rather than a plausible one.
    """
    return dict(REGISTRIES.get(operation, {}))
