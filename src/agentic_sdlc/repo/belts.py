"""belts.py — `release` and `adopt`: facts about the tree, then one write or none.

    agentic-sdlc release <version> [--force]
    agentic-sdlc adopt <version>

`release` checks six facts and runs no gate. CI runs the full tiers on the
release PR, and `integrate` proved each batch before it.

  milestone-resolves   one milestone claims <version> (`version:`), or has it as its id
  features-done        every feature bound to it is in a `done` category
  version-sync         every `[release.version_files]` site says <version>
                       (default: `[pm] version_file` / `version_pattern`)
  tree-clean           nothing is modified outside the roadmap directory
  on-milestone-branch  HEAD is the branch the milestone's `branch:` names
  on-plan              the milestone id is in releases.md `order`, the plan
                       `check pm` R1 reads; false names the `pm add` command

Each check prints `[release] ok: <check> — <detail>` or `[release] error:
<check>: <why>`. When all are true, the milestone takes the first state of
`[pm.states.milestone] done` through `pm milestone <state> <id>`, and the
`next:` lines follow. When one is false, the exit is 1 and nothing is written.
`--force` writes anyway and files one `deviation` row on the milestone's
ledger that names every false check. A second run is a no-op.

`adopt` is checks only and writes nothing:

  pin-bumped            uv.lock pins the version that is running
  installables-current  every installed file is current; a path in
                        `[adopt] ours` is the project's own and is named; a
                        kept hook header name the packaged file never reads
                        is named as a difference
  config-updated        every devkit.toml section this version reads accepts
                        its values ([dispatch] contracts exist and sit in
                        [doc] scope), and every key 2.0.0 retired is named
                        with its replacement

After the checks, one line per thing that is not there. An installer is
taken when any of its files is on disk:

  [adopt] not taken: <installer> (<N> file(s))
                           none of its files is on disk: the project skipped
                           it, a note that does not change the exit
  [adopt] absent: <path>   a file of a taken installer that is not on disk;
                           a path in `[adopt] ours` is never absent
  [adopt] unarmed: <what>; run tools/setup-hooks.sh
                           install-hooks is taken, and `git config core.hooksPath`
                           is not tools/hooks, or a git hook there has no
                           exec bit

Exit 0 every check true and no line above, 1 a check false or a line above,
2 usage or config.
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
from pathlib import Path

from agentic_sdlc import __version__
from agentic_sdlc.core import frontmatter, spawn, walk
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      relpath_tuple, section_declared)
from agentic_sdlc.repo import vehicle
from agentic_sdlc.repo.pm import inventory, ledger, vocabulary

RELEASE, ADOPT = 'release', 'adopt'
VERBS = (RELEASE, ADOPT)
FORCE_FLAG = '--force'
HELP = ('-h', '--help', 'help')
# A milestone id is one path segment; `inventory.segment_is_literal` owns it.
MAX_VERSION = 128
QUOTE_LIMIT = 40
CLIP = 300
SHOWN_MAX = 5
PORCELAIN_PREFIX = 3
FORCED = 'forced'

# Every key 2.0.0 retired, refused BY NAME with what replaces it (rule 11).
# `None` is the whole section. `[verify] story|feature` are `verify/rules.py`'s.
_NO_GATE = ('`release` runs no gate and no command in 2.0.0: it checks facts '
            'and writes the milestone, and CI runs the full tiers on the '
            'release PR')
_FIXED = '`adopt` asks three fixed checks in 2.0.0'
RETIRED_KEYS: dict[tuple[str, str | None], str] = {
    ('story', None): 'the story belt is retired in 2.0.0 — a close is '
                     '`pm story <done-state> <id>`, and `integrate` writes it '
                     'for a batch',
    ('feature', None): 'the feature belt is retired in 2.0.0 — a close is '
                       '`pm feature <done-state> <id>`; `integrate` proves the '
                       'batch',
    (RELEASE, 'steps'): _NO_GATE,
    (RELEASE, 'skippable'): _NO_GATE,
    (RELEASE, 'commands'): _NO_GATE,
    (RELEASE, 'command_timeout'): _NO_GATE,
    (RELEASE, 'changelog'): 'retired in 0.6.0 — `' + vehicle.command(
        'changelog', vehicle.Slot('<milestone-id>')) + '` renders each '
        'grain\'s `changelog:`',
    (ADOPT, 'steps'): _FIXED,
    (ADOPT, 'skippable'): _FIXED,
    (ADOPT, 'commands'): _FIXED,
    (ADOPT, 'command_timeout'): _FIXED,
    (ADOPT, 'runner_targets'): f'{_FIXED}; `runner-targets-resolve` is gone',
    (ADOPT, 'pin_file'): 'the git pin retired in 1.0.0 — `adopt` reads uv.lock '
                         'only',
    **{('tests', key): '`check budget` is retired in 2.0.0 — wall-clock '
                       'ceilings fail under parallel load, and `pm ledger '
                       'report` shows what each tier cost'
       for key in ('budget', 'cases', 'floor')},
    ('emit', None): 'the event sink is retired in 2.0.0 — no verb writes a '
                    '`rung.enter`/`leave` event, so a declared sink could '
                    'only ever be silent',
}


def retired_keys() -> list[str]:
    """One sentence per retired key this repo's devkit.toml still declares."""
    out = []
    for (section, key), instead in RETIRED_KEYS.items():
        if not section_declared(section):
            continue
        if key is None:
            out.append(f'[{section}] is retired: {instead}. Remove the section')
        elif key in config_section(section):
            out.append(f'[{section}] {key} is retired: {instead}. Remove the key')
    return out


# --- small readers others share -----------------------------------------------
def quote(value: str) -> str:
    """`value` quoted back, clipped: a hostile argument is never echoed whole."""
    return repr(value if len(value) <= QUOTE_LIMIT else value[:QUOTE_LIMIT] + '…')


def version_defect(value: str) -> str:
    """'' when `value` may be joined onto the roadmap directory, else why not."""
    if not value:
        return 'the version is empty'
    if len(value) > MAX_VERSION:
        return (f'the version is too long ({len(value)} characters; the limit '
                f'is {MAX_VERSION})')
    if any(ch.isspace() for ch in value):
        return f'{quote(value)} carries whitespace, which no milestone id has'
    if not inventory.segment_is_literal(value):
        return (f'{quote(value)} is not a milestone id — globs, path '
                f'separators, schemes, absolute paths and the "." / ".." '
                f'segments are all refused')
    return ''


def split_roadmap(porcelain: list[str], roadmap_dir: str
                  ) -> tuple[list[str], list[str], str]:
    """(porcelain lines outside `<roadmap_dir>/`, lines inside it, that
    prefix). `tree-clean` and `check repo-hygiene` both read dirt through it.
    `line[3:]`, never a strip: column 0 of porcelain carries meaning."""
    inside = f'{roadmap_dir}/'
    outside, roadmap = [], []
    for line in porcelain:
        if len(line) > PORCELAIN_PREFIX:
            (roadmap if line[PORCELAIN_PREFIX:].startswith(inside)
             else outside).append(line)
    return outside, roadmap, inside


def gate_universe() -> frozenset[str]:
    """Every gate name `check all` can dispatch, derived from `checks/`."""
    from agentic_sdlc.repo import checks as checks_pkg
    found = walk.matching(Path(checks_pkg.__file__).resolve().parent, '*.py',
                          walk.Kind.FILE)
    return frozenset(path.stem.replace('_', '-') for path in found
                     if not path.name.startswith('_'))


def ours_of(operation: str = ADOPT) -> tuple[str, ...]:
    """`[adopt] ours`: the installed files this project has taken over. The ONE
    reader of a claim — the `install-*` verbs leave a claimed file alone through
    it. A claim that names no file (`''`, `.`) is exit 2."""
    claims = relpath_tuple(config_section(operation), operation, 'ours', ())
    for claim in claims:
        if not claim.strip() or claim.strip() in ('.', './'):
            raise ConfigError(
                f'[{operation}] ours contains {claim!r}, which names no file — '
                f'a claim is one installed path this project has taken over, '
                f'e.g. ".github/workflows/verify.yml". Remove the entry')
    return claims


def _every_plan() -> list[tuple[str, list[tuple[str, str]]]]:
    """(verb, plan) for every installer, `install-gates` first: every other
    remedy is spelled through the `Makefile.devkit` it writes."""
    from agentic_sdlc.repo import install
    from agentic_sdlc.repo.pm import skills
    plans = [(verb, list(plan)) for verb, plan in install.PLANS.items()]
    plans.append((skills.GUIDANCE_VERB, list(skills.GUIDANCE_PLAN)))
    return sorted(plans, key=lambda pair: pair[0] != install.BOOTSTRAP_VERB)


def claims_matching_nothing(operation: str = ADOPT) -> str:
    """The line naming claims that match no installed destination, or ''."""
    planned = {rel for _verb, plan in _every_plan() for _name, rel in plan}
    unmatched = [rel for rel in ours_of(operation) if rel not in planned]
    if not unmatched:
        return ''
    return (f'{len(unmatched)} claim(s) in [{operation}] ours name no file '
            f'{__version__} installs, so each matches nothing and leaves '
            f'nothing alone — a claim is a destination spelled exactly as '
            f'--diff heads it: {_clip(", ".join(unmatched))}')


def _clip(text: str, limit: int = CLIP) -> str:
    flat = ' '.join(str(text).split())
    return flat if len(flat) <= limit else flat[:limit] + '…'


def _git(root: Path, *args: str) -> tuple[int, str]:
    """`git` in the checkout; a missing git is an exit code, never a crash."""
    try:
        done = spawn.run(('git', *args), cwd=str(root), capture_output=True,
                         text=True, timeout=120)
    except (OSError, spawn.TimeoutExpired) as err:
        return 127, str(err)
    return done.returncode, (done.stdout + done.stderr).rstrip('\n')


# --- release ------------------------------------------------------------------
def _version_files(cfg) -> dict[str, re.Pattern]:
    """path -> a regex with one group holding the version."""
    raw = config_section(RELEASE).get('version_files')
    if raw is None:
        raw = {cfg.version_file: cfg.version_pattern}
    if not isinstance(raw, dict) or not raw:
        raise ConfigError(f'[{RELEASE}.version_files] must be a non-empty '
                          f'table of path = pattern, got {raw!r}')
    out = {}
    for path, pattern in raw.items():
        try:
            compiled = re.compile(pattern) if isinstance(pattern, str) else None
        except re.error as err:
            raise ConfigError(f'[{RELEASE}.version_files] {path} is not a '
                              f'valid regex: {err}') from err
        if compiled is None or compiled.groups != 1:
            raise ConfigError(f'[{RELEASE}.version_files] {path} must be a '
                              f'regex string with exactly one capture group '
                              f'holding the version, got {pattern!r}')
        out[path] = compiled
    return out


def _milestone(cfg, version: str):
    mid = inventory.milestone_of_version(cfg, version) or version
    return inventory.grain(cfg, mid, vocabulary.GRAIN_MILESTONE)


def _features_done(cfg, mid: str) -> tuple[bool, str]:
    features = inventory.feature_grains(cfg, mid)
    if not features:
        return False, (f'{mid} holds no feature — a release over nothing is '
                       f'not a release')
    open_ = [f'{f.gid} ({f.field(vocabulary.FIELD_STATUS) or "no status"})'
             for f in features
             if vocabulary.category_of(cfg, vocabulary.GRAIN_FEATURE,
                                       f.field(vocabulary.FIELD_STATUS))
             != vocabulary.DONE_CATEGORY]
    if open_:
        return False, (f'{len(open_)} of {len(features)} feature(s) not in '
                       f'`{vocabulary.DONE_CATEGORY}`: {", ".join(open_)}')
    return True, (f'{len(features)} feature(s), every one in '
                  f'`{vocabulary.DONE_CATEGORY}`')


def _version_sync(cfg, version: str) -> tuple[bool, str]:
    found, wrong = [], []
    for rel, pattern in _version_files(cfg).items():
        path = cfg.root / rel
        if not path.is_file():
            return False, f'{rel} is not in this checkout'
        value = next((m.group(1) for m in map(
            pattern.match, (ln.strip() for ln in
                            frontmatter.read_raw(path).split('\n'))) if m), None)
        if value is None:
            return False, f'{rel} carries no line matching {pattern.pattern!r}'
        found.append(f'{rel} says {value}')
        if value != version:
            wrong.append(rel)
    if wrong:
        return False, (f'{"; ".join(found)} — the release is {version}; bump '
                       f'each site and commit')
    return True, f'{len(found)} version site(s) say {version}'


def _tree_clean(cfg) -> tuple[bool, str]:
    code, out = _git(cfg.root, 'status', '--porcelain')
    if code != 0:
        return False, f'git status failed: {_clip(out)}'
    outside, _inside, prefix = split_roadmap(out.split('\n'), cfg.roadmap_dir)
    if outside:
        return False, (f'{len(outside)} modified path(s) outside {prefix}: '
                       + _clip(', '.join(ln[PORCELAIN_PREFIX:]
                                         for ln in outside)))
    return True, f'no modified path outside {prefix}'


def _on_branch(cfg, milestone) -> tuple[bool, str]:
    declared = milestone.field('branch')
    if not declared:
        return False, (f'{cfg.rel(milestone.path)} carries no `branch:` — '
                       f'this check will not assume HEAD is the right branch')
    code, here = _git(cfg.root, 'rev-parse', '--abbrev-ref', 'HEAD')
    if code != 0 or here != declared:
        return False, (f'HEAD is {here!r}; {cfg.rel(milestone.path)} declares '
                       f'branch: {declared!r}')
    return True, f'HEAD is {here!r}'


def _on_plan(cfg, milestone) -> tuple[bool, str]:
    """The plan `check pm` R1 reads: `releases.md` `order`, through the same
    readers. A plan that is there and unreadable is named, never a miss."""
    plan = cfg.rel(inventory.releases_file(cfg))
    defect = inventory.plan_defect(cfg)
    if defect is not None:
        return False, f'{plan} {defect} — the plan was NOT read'
    if milestone.gid in inventory.declared_order(cfg):
        return True, f'{milestone.gid} is in {plan} `order`'
    root = inventory.root_grain(cfg)
    schedule = vehicle.command('pm', 'add',
                               root.gid if root else vocabulary.ROOT_ID,
                               milestone.gid)
    return False, f'{milestone.gid} is on no plan; `{schedule}`'


def release_checks(cfg, version: str) -> list[tuple[str, bool, str]]:
    """(check, true?, detail) for each release fact, in order."""
    milestone = _milestone(cfg, version)
    if milestone is None:
        claims = inventory.milestones_of_version(cfg, version)
        why = (f'{len(claims)} milestones claim {version}: {", ".join(claims)}'
               if claims else f'no milestone claims `version: {version}` or '
               f'has it as its id')
        return [('milestone-resolves', False, why)]
    out = [('milestone-resolves', True, f'{milestone.gid} '
            f'({cfg.rel(milestone.path)})')]
    out.append(('features-done', *_features_done(cfg, milestone.gid)))
    out.append(('version-sync', *_version_sync(cfg, version)))
    out.append(('tree-clean', *_tree_clean(cfg)))
    out.append(('on-milestone-branch', *_on_branch(cfg, milestone)))
    out.append(('on-plan', *_on_plan(cfg, milestone)))
    return out


def _next_lines(cfg, milestone, version: str) -> list[str]:
    branch = milestone.field('branch') or '<branch>'
    try:
        mainline = vocabulary.mainline_branch()
    except ConfigError:
        mainline = '<mainline>'
    notes = vehicle.command('changelog', milestone.gid)
    return [f'next: {line}' for line in (
        f'render the release notes: `{notes}`',
        'commit the roadmap directory as the release commit',
        f'push the branch: `git push -u origin {branch}` — never the mainline',
        f'open the PR from {branch} to {mainline}; CI runs the full tiers on it',
        'merge it as a MERGE COMMIT — the mainline is merge-commit-only',
        f'tag the merge commit and push the TAG ref only: `git tag v{version} '
        f'&& git push origin refs/tags/v{version}`',
        f'sync the local mainline: `git switch {mainline} && git pull '
        f'--ff-only`')]


def _write(cfg, kind: str, state: str, gid: str) -> tuple[int, str]:
    """`pm <kind> <state> <id>` in process, so the CLI mints the status row."""
    from agentic_sdlc.repo.pm import cli as pm_cli
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = pm_cli.main([kind, state, gid])
    return code, buffer.getvalue().strip()


def _deviation(cfg, mid: str, false: list[tuple[str, str]]) -> str:
    """The `deviation` row a forced write files; '' or why it could not."""
    reason = '; '.join(f'{name}: {why}' for name, why in false)
    reason = ' '.join(reason.split())[:ledger.REASON_MAX - 1]
    try:
        ledger.append_to(ledger.ledger_for(cfg, mid), ledger.deviation_row(
            mid, RELEASE, ', '.join(n for n, _ in false), reason,
            outcome=FORCED))
    except (ledger.LedgerError, OSError, ValueError) as err:
        return str(err)
    return ''


def release(version: str, force: bool) -> int:
    cfg = vocabulary.load()
    retired = retired_keys()
    if retired:
        raise ConfigError('; '.join(retired))
    state = vocabulary.flow_of(cfg, vocabulary.GRAIN_MILESTONE).by_category[
        vocabulary.DONE_CATEGORY][0]
    _version_files(cfg)  # a malformed table is exit 2 before any check
    with inventory.reading_tree():
        checks = release_checks(cfg, version)
        milestone = _milestone(cfg, version)
    false = []
    for name, ok, detail in checks:
        print(f'[{RELEASE}] ok: {name} — {detail}' if ok
              else f'[{RELEASE}] error: {name}: {detail}')
        if not ok:
            false.append((name, detail))
    if milestone is None:
        print(f'[{RELEASE}] error — no milestone to write; nothing written')
        return 1
    if false and not force:
        print(f'[{RELEASE}] error — {len(false)} check(s) false; no status '
              f'written')
        return 1
    status = milestone.field(vocabulary.FIELD_STATUS)
    if vocabulary.category_of(cfg, vocabulary.GRAIN_MILESTONE,
                              status) == vocabulary.DONE_CATEGORY:
        # Rule 3: the same command twice is a no-op, a deviation row included.
        print(f'[{RELEASE}] ok — {milestone.gid} is already {status}, a done '
              f'state; nothing written')
        return 0
    code, said = _write(cfg, vocabulary.GRAIN_MILESTONE, state, milestone.gid)
    for line in said.splitlines():
        print(f'[{RELEASE}] write: {line}')
    if code != 0:
        print(f'[{RELEASE}] error — the write was refused; no status written')
        return 1
    if false:
        print(f'[{RELEASE}] forced — {version} → {state} over {len(false)} '
              f'false check(s)')
        blocked = _deviation(cfg, milestone.gid, false)
        if blocked:
            print(f'[{RELEASE}] WARNING — the deviation row naming the forced '
                  f'checks was not written: {blocked}')
    else:
        print(f'[{RELEASE}] ok — {version} → {state}')
    for line in _next_lines(cfg, milestone, version):
        print(line)
    return 0


# --- adopt --------------------------------------------------------------------
def _pin_bumped(root: Path) -> tuple[bool, str]:
    locked = vehicle.locked_version(root)
    if locked is None:
        return False, (f'{vehicle.LOCK_FILE} names no {vehicle.PROGRAM} — '
                       f'`{vehicle.add_line()}` declares it')
    if locked == __version__:
        return True, (f'{vehicle.LOCK_FILE} pins {locked}, which is the '
                      f'version running here')
    return False, (f'{vehicle.LOCK_FILE} pins {locked}; the package running '
                   f'here is {__version__} — `{vehicle.add_line()}` moves it')


def remedy(verb: str) -> str:
    """The command that shows one installer's drifted files."""
    from agentic_sdlc.repo import install
    if verb == install.BOOTSTRAP_VERB:
        return vehicle.pinned(verb, '--force')
    return vehicle.command(*verb.split(), '--diff')


def _installables_current(root: Path) -> tuple[bool, str]:
    from agentic_sdlc.repo import install
    from agentic_sdlc.repo.pm import skills
    claimed = frozenset(ours_of())
    stale, current, named, lacking = [], 0, [], []
    for verb, plan in _every_plan():
        for name, rel in plan:
            target = root / rel
            if rel in claimed:
                named.append(rel)
                continue
            if not target.is_file():
                continue
            text, _defect = install.read_destination(target)
            try:
                body = (skills.guidance_body(name)
                        if verb == skills.GUIDANCE_VERB
                        else install.resolve_body(name, rel))
            except (OSError, UnicodeDecodeError, ConfigError) as err:
                stale.append(f'{rel} (unrenderable: {_clip(err, 60)})')
                continue
            if text == body:
                current += 1
            elif text is not None and install.header_only_difference(text, body):
                # The project's own header: current, and a packaged name its
                # kept block lacks is named — a hook reading an unset name
                # fails OPEN.
                current += 1
                names = install.lacking_names(text, body)
                if names:
                    lacking.append(f'{rel} lacks '
                                   + ', '.join(f'`{n}`' for n in names)
                                   + f' (`{remedy(verb)}`)')
            else:
                # A kept header declaring a name the packaged one retired is a
                # difference: `--force` drops it (#128), so it is named.
                retired = [] if text is None else install.retired_names(text, body)
                why = ('unreadable' if text is None else 'differs' if not retired
                       else 'differs; its header declares '
                       + ', '.join(f'`{n}`' for n in retired)
                       + ', which the packaged file no longer declares or '
                       'reads')
                stale.append(f'{rel} ({why}; `{remedy(verb)}`)')
    claims = (f'; {len(named)} claimed by [{ADOPT}] ours and not graded: '
              f'{_clip(", ".join(named))}' if named else '')
    unmatched = claims_matching_nothing()
    claims += f'; {unmatched}' if unmatched else ''
    if lacking:
        claims += (f'; {len(lacking)} kept header(s) lack a name the packaged '
                   f'one declares: {_clip(", ".join(lacking))}')
    if stale:
        return False, (f'{len(stale)} of {len(stale) + current} installed '
                       f'file(s) differ from what {__version__} ships: '
                       f'{_clip(", ".join(stale))}{claims}')
    if not current:
        return False, (f'NOTHING was graded — no installed file is present, or '
                       f'[{ADOPT}] ours claims every one; a verdict over an '
                       f'empty census is not a pass{claims}')
    return True, (f'{current} installed file(s) are current with '
                  f'{__version__}{claims}')


def _installers(root: Path) -> tuple[list[str], list[tuple[str, int]]]:
    """(absent, not taken), in `_every_plan` order. An installer is taken when
    any of its files is on disk; each missing file of a taken one that no
    claim names is absent. One with no file on disk is not taken (D8): the
    project skipped it, and the tool does not decide which installers a
    project runs."""
    claimed = frozenset(ours_of())
    absent, skipped = [], []
    for verb, plan in _every_plan():
        rels = [rel for _name, rel in plan]
        missing = [rel for rel in rels if not (root / rel).is_file()]
        if len(missing) == len(rels):
            skipped.append((verb, len(rels)))
            continue
        absent += [rel for rel in missing if rel not in claimed]
    return absent, skipped


# What `tools/setup-hooks.sh` writes: `git config core.hooksPath tools/hooks`,
# and the exec bit on each git hook there (git skips one without it, silently).
HOOKS_PATH = 'tools/hooks'
HOOKS_VERB = 'install-hooks'
# The one hook it sets executable that `install-hooks` does not ship; the rest
# are read off the plan.
_GIT_HOOK_NAMES = ('pre-commit',)


def _setup_hooks() -> str:
    from agentic_sdlc.repo import install
    return dict(install.PLANS[HOOKS_VERB])['setup-hooks.sh']


def _hooks_path(root: Path) -> tuple[bool, str | None]:
    """(known, value) of `core.hooksPath` as git resolves it: system, global,
    local, worktree and include config, and the `GIT_CONFIG_*` env. A git
    query, not a build (rule 2). `git config --get` exits 1 when the key is
    unset; any other failure (no git, not a repository) is not known."""
    try:
        done = spawn.run(('git', 'config', '--type=path', '--get',
                          'core.hooksPath'), cwd=str(root),
                         capture_output=True, text=True, timeout=30)
    except (OSError, spawn.TimeoutExpired):
        return False, None
    if done.returncode == 1:
        return True, None
    if done.returncode != 0:
        return False, None
    return True, done.stdout.rstrip('\n')


def _unarmed(root: Path) -> str:
    """What `tools/setup-hooks.sh` would write and this checkout lacks, or ''.
    When git cannot answer, core.hooksPath is not named: no false finding."""
    from agentic_sdlc.repo import install
    lacking = []
    known, value = _hooks_path(root)
    if known and value is None:
        lacking.append('git core.hooksPath is unset')
    elif known and (root / value).resolve() != (root / HOOKS_PATH).resolve():
        # A relative value is relative to the worktree top, which `root` is.
        lacking.append(f'git core.hooksPath is {quote(value)}, not '
                       f'{HOOKS_PATH}')
    hooks = [rel for _name, rel in install.PLANS[HOOKS_VERB]
             if rel.startswith(f'{HOOKS_PATH}/')]
    hooks += [f'{HOOKS_PATH}/{name}' for name in _GIT_HOOK_NAMES]
    lacking += [f'{rel} is not executable' for rel in hooks
                if (root / rel).is_file()
                and not install._is_executable(root / rel)]
    return ', '.join(lacking)


def _named(root: Path) -> tuple[list[str], list[str]]:
    """(notes, findings): the `not taken:` lines, which change no exit, and
    the `absent:` and `unarmed:` lines, each a finding and none a check."""
    absent, skipped = _installers(root)
    notes = [f'[{ADOPT}] not taken: {verb} ({count} file(s))'
             for verb, count in skipped]
    out = [f'[{ADOPT}] absent: {rel}' for rel in absent]
    unarmed = '' if HOOKS_VERB in {v for v, _n in skipped} else _unarmed(root)
    if unarmed:
        out.append(f'[{ADOPT}] unarmed: {unarmed}; run {_setup_hooks()}')
    return notes, out


def _dispatch_contracts():
    """`[dispatch]` through `dispatch.settings`, which refuses a contract that
    resolves to nothing; then each contract `check doc` never reads."""
    from agentic_sdlc.core.project import repo_root
    from agentic_sdlc.repo import dispatch
    from agentic_sdlc.repo.checks import doc
    if not section_declared(dispatch.SECTION):
        return
    _project, contracts = dispatch.settings()
    outside = doc.outside_scope(repo_root(), contracts)
    if outside:
        raise ConfigError(
            f'[{dispatch.SECTION}] {dispatch.CONTRACTS_KEY} names '
            f'{len(outside)} path(s) outside [doc] scope: {", ".join(outside)}'
            f' — `check doc` never reads a contract it does not scope, so a '
            f'dead claim in one goes unseen. Add each to [doc] scope')


def _integrate():
    from agentic_sdlc.repo import integrate
    if section_declared(integrate.SECTION):
        integrate.settings(config_section(integrate.SECTION))


def _config_readers():
    """(label, reader) for every devkit.toml section this version reads."""
    from agentic_sdlc.core.config import str_tuple
    from agentic_sdlc.repo import gates_extra
    from agentic_sdlc.repo.checks import grain_shape, repo_hygiene
    from agentic_sdlc.repo.verify import rules

    def checks_all():
        unknown = [n for n in str_tuple(config_section('checks'), 'checks',
                                        'all', ()) if n not in gate_universe()]
        if unknown:
            raise ConfigError(f'[checks] all names unknown gate(s) '
                              f'{", ".join(unknown)}')

    def verify():
        if section_declared(rules.SECTION):
            rules.read(config_section(rules.SECTION))

    def release_files():
        if section_declared(RELEASE):
            _version_files(vocabulary.load())

    return (('[checks] all', checks_all), ('[gates] extra', gates_extra.targets),
            ('[pm]', vocabulary.load), ('[release] version_files', release_files),
            ('[adopt] ours', ours_of), ('[grain_shape] caps', grain_shape._caps),
            ('[repo_hygiene]', repo_hygiene.read_config), ('[verify]', verify),
            ('[dispatch]', _dispatch_contracts), ('[integrate]', _integrate))


def _config_updated() -> tuple[bool, str]:
    refused = list(retired_keys())
    readers = _config_readers()
    for label, reader in readers:
        try:
            reader()
        except ConfigError as err:
            refused.append(f'{label}: {_clip(err)}')
    if refused:
        return False, (f'{len(refused)} value(s) {__version__} does not accept '
                       f'— {"; ".join(refused)}')
    return True, f'{len(readers)} reader(s) accept this repo\'s devkit.toml'


def adopt(version: str) -> int:
    from agentic_sdlc.core.project import repo_root
    root = repo_root()
    print(f'[{ADOPT}] checks only — this verb sets no status and files no row')
    checks = (('pin-bumped', *_pin_bumped(root)),
              ('installables-current', *_installables_current(root)),
              ('config-updated', *_config_updated()))
    false = 0
    for name, ok, detail in checks:
        print(f'[{ADOPT}] ok: {name} — {detail}' if ok
              else f'[{ADOPT}] error: {name}: {detail}')
        false += not ok
    notes, named = _named(root)
    for line in notes + named:
        print(line)
    if false:
        print(f'[{ADOPT}] error — {false} check(s) false')
        return 1
    if named:
        print(f'[{ADOPT}] error — {len(named)} absent or unarmed line(s); '
              f'{len(checks)} check(s) true')
        return 1
    print(f'[{ADOPT}] ok — {len(checks)} check(s) true; nothing to write')
    print(f'next: commit the pin bump (`pyproject.toml` and `uv.lock`) and '
          f'every installable you took or hand-applied for {version}')
    return 0


# --- the verbs ----------------------------------------------------------------
def _refuse(message: str) -> int:
    print(f'agentic-sdlc: {message}', file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    """`argv[0]` is `release` or `adopt`; the rest is its arguments."""
    verb, rest = argv[0], list(argv[1:])
    if any(arg in HELP for arg in rest):
        print(__doc__.strip())
        return 0
    force = FORCE_FLAG in rest
    rest = [arg for arg in rest if arg != FORCE_FLAG]
    flags = [arg for arg in rest if arg.startswith('-')]
    if flags:
        return _refuse(f'{verb}: unknown flag(s) {" ".join(flags)}')
    if force and verb == ADOPT:
        return _refuse(f'{ADOPT} writes nothing, so there is nothing to force '
                       f'— it is checks only')
    if len(rest) != 1:
        return _refuse(f'{verb} takes exactly one <version>, e.g. '
                       f'`{vehicle.command(verb, "2.0.0")}`; got {len(rest)}')
    defect = version_defect(rest[0])
    if defect:
        return _refuse(f'{verb}: {defect}')
    try:
        return release(rest[0], force) if verb == RELEASE else adopt(rest[0])
    except ConfigError as err:
        return _refuse(f'{verb}: {err}')
