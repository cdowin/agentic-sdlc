"""What this session can do, said before the first dispatch.

The kit's flow assumes harness capabilities it never checked: that a stopped
subagent can be resumed with `SendMessage`, that the ledger couriers can
attribute a dispatch, that the hooks are wired. A host that launched every
session with `SendMessage` disallowed was found out only when a call failed,
and every stopped builder was re-dispatched cold (issue #40).

So this reports each assumption as one row BEFORE anything is dispatched —
run from a SessionStart hook, whose stdout is what the session reads. It reads
two settings files and the PM tree as text and starts nothing (a process tree
and a launch flag are not text, so they stay `unknown` rather than a guess),
and it gates nothing: the value is the fact, the meaning is what the kit's
flow does with it, and the caller decides.
"""
from __future__ import annotations

import sys
from pathlib import Path

from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import vehicle
from agentic_sdlc.repo.checks import hooks

VERB = 'preflight'
HELP_WORDS = ('-h', '--help', 'help')
COLUMNS = ('capability', 'value', 'meaning')
UNKNOWN = 'unknown'
WIRED, NOT_WIRED = 'wired', 'not wired'

# The tool whose absence cost a milestone, and the two rule lists that name it.
RESUME_TOOL = 'SendMessage'
DENY, ALLOW = 'deny', 'allow'
HOOK_SETTINGS = vehicle.command('install-hooks', '--write-settings')
CHANNEL = vehicle.command('dispatch', '--grain', vehicle.Slot('<id>'))
REDISPATCH = (f'a stopped builder is re-dispatched with `{CHANNEL}`, so keep '
              f'dispatches small')

USAGE = f"""usage: agentic-sdlc {VERB}

What this session can do, said BEFORE the first dispatch: one tab-separated
row per capability on STDOUT, always these four in this order, columns IN ORDER:
    {'  '.join(COLUMNS)}

  subagent-resume   denied | allowed | {UNKNOWN} — `{RESUME_TOOL}` in
                    `permissions.deny` / `permissions.allow` of
                    {' and '.join(hooks.SETTINGS_FILES)}, a deny in either
                    winning. {UNKNOWN} when neither names it: a launch flag
                    (--disallowedTools) is not readable as text, and a
                    settings file outside this checkout is not read.
  hooks             {WIRED} | {NOT_WIRED} — every cc-* hook under
                    {hooks.HOOKS_DIR}/ registered in one of those files, the
                    missing ones named. The wiring half of `check hooks`, read
                    and never run: that gate also starts each hook and asks git.
  attribution       how many stories sit in an in_progress state, and what the
                    ledger couriers' fallback makes of it: exactly 1 is
                    attributed, 0 and several are not. {UNKNOWN} with no PM
                    tree or no [pm.states.*].
  subagent-channel  dispatch — the rendered `dispatch --grain <id>` preamble
                    is the only channel to a subagent.

It reports and never gates, reads text, runs nothing and writes nothing, so a
SessionStart hook can run it: `install-hooks` ships cc-session-preflight.sh,
which prints these rows into the session.

Exit codes: 0 the report was read, {UNKNOWN} rows included; 2 usage or config
error."""


def _names_tool(rule: object) -> bool:
    """A permission rule naming the resume tool, bare or with a specifier."""
    return isinstance(rule, str) and (rule == RESUME_TOOL
                                      or rule.startswith(f'{RESUME_TOOL}('))


def resume(root: Path) -> tuple[str, str]:
    """(value, meaning) for resuming a stopped subagent."""
    said: dict[str, list[str]] = {DENY: [], ALLOW: []}
    unread: list[str] = []
    for rel in hooks.SETTINGS_FILES:
        data, why = hooks.settings_document(root / rel)
        if why:
            unread.append(f'{rel} could not be read ({why})')
            continue
        permissions = data.get('permissions')
        if not isinstance(permissions, dict):
            continue
        for key in said:
            rules = permissions.get(key)
            if isinstance(rules, list) and any(map(_names_tool, rules)):
                said[key].append(rel)
    tail = f'; {"; ".join(unread)}' if unread else ''
    if said[DENY]:
        return 'denied', (f'{" and ".join(said[DENY])} denies {RESUME_TOOL}, '
                          f'so a stopped subagent cannot be resumed — '
                          f'{REDISPATCH}{tail}')
    if said[ALLOW]:
        return 'allowed', (f'{" and ".join(said[ALLOW])} allows '
                           f'{RESUME_TOOL}; a launch flag can still remove it '
                           f'and is not readable as text{tail}')
    return UNKNOWN, (f'a launch flag is not readable as text, and no '
                     f'settings file here names {RESUME_TOOL} — if a resume '
                     f'fails, {REDISPATCH}{tail}')


def wiring(root: Path) -> tuple[str, str]:
    """(value, meaning) for the cc-* hooks, off `check hooks`' own reader."""
    names, registered, where, unread = hooks.cc_registration(root)
    tail = f'; {unread}' if unread else ''
    if not names:
        return NOT_WIRED, (f'no {hooks.CC_PREFIX}* hook under '
                           f'{hooks.HOOKS_DIR}/ — '
                           f'`{hooks.INSTALL_COMMAND}` ships the corpus{tail}')
    missing = [name for name in names if name not in registered]
    if missing:
        return NOT_WIRED, (f'{", ".join(missing)} registered in no settings '
                           f'file here — `{HOOK_SETTINGS}` lands the '
                           f'block{tail}')
    return WIRED, (f'all {len(names)} {hooks.CC_PREFIX}* hook(s) registered in '
                   f'{where}; registered is not in force — '
                   f'`{vehicle.command("check", "hooks")}` starts each one')


def attribution(stories: list[str] | None, why: str = '') -> tuple[str, str]:
    """(value, meaning) for the couriers' fallback over `stories` in progress;
    None is a tree that could not be asked, and `why` says so."""
    grain = 'GDK_LEDGER_GRAIN'
    if stories is None:
        return UNKNOWN, why
    if len(stories) == 1:
        return '1', (f'{stories[0]} is the one story in progress, so a ledger '
                     f'row with no --grain is filed against it — right for '
                     f'its own work, wrong for any other dispatch; '
                     f'`{CHANNEL}` renders the {grain} export that overrides '
                     f'it')
    lost = ('a ledger row with no --grain names none and lands in `rows '
            f'naming no grain` — `{CHANNEL}` renders the {grain} export each '
            f'dispatch needs')
    if not stories:
        return '0', f'no story is in progress, so {lost}'
    return str(len(stories)), (f'{" ".join(stories)} are in progress, so the '
                               f'fallback picks none of them: {lost}')


def _stories_in_progress() -> tuple[list[str] | None, str]:
    """The ids the couriers' fallback reads, off the same snapshot a ledger
    row records — so this row and that fallback cannot disagree."""
    from agentic_sdlc.repo.pm import cli as pm_cli, ledger, vocabulary
    cfg = vocabulary.load()
    if not cfg.flows:
        return None, ('no [pm.states.*] is declared, so no state is '
                      'in_progress and `pm` cannot run here')
    if not cfg.roadmap.is_dir():
        return None, f'there is no PM tree at {cfg.rel(cfg.roadmap)}'
    return pm_cli._tree_snapshot(cfg)[ledger.STORIES_IN_PROGRESS], ''


def rows(root: Path, stories: list[str] | None,
         why: str = '') -> list[tuple[str, ...]]:
    """The report, one (capability, value, meaning) per capability, in order."""
    return [('subagent-resume', *resume(root)),
            ('hooks', *wiring(root)),
            ('attribution', *attribution(stories, why)),
            ('subagent-channel', 'dispatch',
             f'the rendered `{CHANNEL}` preamble is the only channel to a '
             f'subagent — nothing repo-specific reaches one at spawn '
             f'(devkit issue #15)')]


def main(argv: list[str]) -> int:
    if argv and argv[0] in HELP_WORDS:
        print(USAGE)
        return 0
    if argv:
        print(f'agentic-sdlc {VERB}: unexpected argument(s) {" ".join(argv)} '
              f'— it takes none', file=sys.stderr)
        return 2
    try:
        stories, why = _stories_in_progress()
        report = rows(repo_root(), stories, why)
    except ConfigError as err:
        print(f'agentic-sdlc {VERB}: {err}', file=sys.stderr)
        return 2
    for row in report:
        # One row is one line whatever a settings file's error text held.
        print('\t'.join(' '.join(field.split()) for field in row))
    return 0
