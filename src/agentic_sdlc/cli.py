"""agentic-sdlc — one entry point, one verb per tool.

Project management (markdown + frontmatter; `pm --help` is the full list):
    agentic-sdlc pm story|feature|milestone <status> <id>
    agentic-sdlc pm status|list|validate|vocabulary|decide|ledger|new|init|install-skills

Installers (write a file once; `--force` overwrites, `--diff` prints):
    agentic-sdlc init               # a repo wired for this kit: every installer below plus devkit.toml
    agentic-sdlc install-ci         # the workflow that runs `make milestone`
    agentic-sdlc install-agents     # the review + build contract as agent definitions
    agentic-sdlc install-hooks      # the agent-workflow guard corpus and setup-hooks.sh
    agentic-sdlc install-gates      # the gate shell library and the standard targets
    agentic-sdlc install-sdlc       # the SDLC document, rendered from your step lists

Verification (`[verify]` in devkit.toml; `verify --help` is the ladder):
    agentic-sdlc verify --story|--feature|--milestone|--plan|--check

Static gates (exit 1 on findings; `check <gate> --help` is that gate's contract):
    agentic-sdlc check doc|shell|grain-shape|pm|hooks|repo-hygiene|budget|all
    agentic-sdlc gates-extra        # `[gates] extra`, one make target per line

Belts (checks, then one status write or a clean error; `--force` writes anyway on the record):
    agentic-sdlc release <version>
    agentic-sdlc adopt <version>    # a devkit PIN bump, not a grain: pin, installables, config
    agentic-sdlc close story|feature <id>

Lessons (an append-only row bound to a grain and a rule; recorded, never inferred):
    agentic-sdlc lesson record --grain <id> --rule <id> --source <path> "<text>"
    agentic-sdlc lesson show [--grain <id> | --rule <id>]

    agentic-sdlc version            # also -V / --version

Per-project config is devkit.toml at the consuming repo root.
"""
from __future__ import annotations

import sys

from agentic_sdlc import __version__
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      section_declared, str_tuple)

FIX_FLAG = '--fix'
HELP_FLAGS = ('-h', '--help')

# Its own verb rather than a `pm` subcommand: a lesson is written by whoever
# just learned it — a reviewer, a belt's caller — and never as part of moving a
# grain, which is what everything under `pm` is.
LESSON_VERB = 'lesson'
CHANGELOG_VERB = 'changelog'
DISPATCH_VERB = 'dispatch'

# {gate: in the default `check all`?}; tests/test_gate_roster.py holds every key to a module.
# The OFF gates would redden a consumer that has no PM tree, no hooks or no budget declared.
KNOWN_GATES = {
    'doc': True, 'shell': True, 'grain-shape': True,
    'repo-hygiene': False, 'pm': False, 'hooks': False,
    'budget': False,
}

# Empty, and kept because `_run_check` refuses an unknown flag through it.
FIXABLE_CHECKS: frozenset[str] = frozenset()


def all_roster() -> tuple[str, ...]:
    """`[checks] all`, else the stock default; an unknown name is refused, never skipped."""
    default = tuple(name for name, on in KNOWN_GATES.items() if on)
    roster = str_tuple(config_section('checks'), 'checks', 'all', default)
    unknown = [c for c in roster if c not in KNOWN_GATES]
    if unknown:
        # A roster error must not HIDE the config errors of the gates that were
        # named correctly. The adoption that motivated this hit exactly one
        # message — about gate NAMES — routed the whole bump at the roster, and
        # never learned that its PM tree declared no flow at all. A green
        # aggregate over a dead conveyor is the failure this milestone names.
        raise ConfigError(
            f'[checks] all names unknown gate(s) {", ".join(unknown)} — '
            f'known gates are {" ".join(KNOWN_GATES)}'
            + _also_wrong(roster))
    return tuple(dict.fromkeys(roster))


def _also_wrong(roster: tuple[str, ...]) -> str:
    """What the correctly-named gates would have said about their own config.

    Best effort by construction: this runs while the roster is already known to
    be broken, so a reader that itself explodes is skipped rather than replacing
    the message the caller came for.
    """
    said: list[str] = []
    if 'pm' in roster:
        try:
            from agentic_sdlc.repo.pm import model
            said.extend(model.all_config_defects())
        except Exception:  # noqa: BLE001 - never mask the roster error
            pass
    if not said:
        return ''
    lines = ''.join(f'\n  ALSO: {m}' for m in said)
    return (f'\n\nThe gates you DID name correctly have their own config to '
            f'report, and fixing the roster alone would not have shown you '
            f'{"this" if len(said) == 1 else "these"}:{lines}')


def install_commands() -> tuple[str, ...]:
    """The `install-*` verbs, read off the installer's plan table so the two cannot drift."""
    from agentic_sdlc.repo.install import PLANS
    return tuple(PLANS)


# Read here because tests/test_boundaries.py allowlists only this module for a raw config read.
VERIFY_SECTION = 'verify'


def _verify_section() -> dict | None:
    """The `[verify]` table, or None when the section is absent (exit 2 upstream)."""
    if not section_declared(VERIFY_SECTION):
        return None
    return config_section(VERIFY_SECTION)


def _usage() -> int:
    print(__doc__.strip())
    return 2


def _run_check(name: str, flags: list[str]) -> int:
    # A devkit.toml mistake is exit 2, never 1 (findings) and never 0.
    try:
        return _run_check_inner(name, flags)
    except ConfigError as err:
        print(f'agentic-sdlc: {err}', file=sys.stderr)
        return 2


def _run_check_inner(name: str, flags: list[str]) -> int:
    if any(flag in HELP_FLAGS for flag in flags):
        module = _check_module(name)
        if module is None:
            return _unknown_check(name)
        print((module.__doc__ or '').strip())
        return 0
    # An unknown flag is a usage error, never silently ignored.
    unknown = [f for f in flags
               if not (name in FIXABLE_CHECKS and f == FIX_FLAG)]
    if unknown:
        print(f'agentic-sdlc: check {name}: unexpected argument(s) '
              f'{" ".join(unknown)}', file=sys.stderr)
        return 2
    return _dispatch_check(name, fix=FIX_FLAG in flags)


def _check_module(name: str):
    """The module implementing one gate, or None; the roster is checked before any import."""
    if name not in KNOWN_GATES:
        return None
    from importlib import import_module
    try:
        return import_module(
            f'agentic_sdlc.repo.checks.{name.replace("-", "_")}')
    except ModuleNotFoundError:
        # A rostered gate with no module is a broken install, not a user typo.
        raise ConfigError(
            f'gate {name!r} is in the roster but its module is not installed — '
            f'this is a broken install, not a config mistake') from None


def _unknown_check(name: str) -> int:
    print(f'agentic-sdlc: unknown check {name!r} '
          f'(expected: {", ".join((*KNOWN_GATES, "all"))})',
          file=sys.stderr)
    return 2


def _dispatch_check(name: str, fix: bool = False) -> int:
    if name == 'all':
        worst = 0
        for check in all_roster():
            worst = max(worst, _dispatch_check(check))
            print()
        return worst
    module = _check_module(name)
    if module is None:
        return _unknown_check(name)
    # `all` never repairs; `--fix` is asked of the gate itself.
    return module.run(fix=fix) if name in FIXABLE_CHECKS else module.run()


# `driver.VERBS`, not `OPERATIONS`: `story` and `feature` are reached through `close`.
def conveyor_verbs() -> tuple[str, ...]:
    from agentic_sdlc.repo.conveyor import driver
    return driver.VERBS


class _Lazy(tuple):
    """The conveyor verbs, resolved on first membership test so `pm` never imports the driver."""
    def __contains__(self, item: object) -> bool:
        return item in conveyor_verbs()


CONVEYOR_VERBS = _Lazy()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _usage()
    if args[0] in ('-h', '--help', 'help'):
        print(__doc__.strip())
        return 0
    cmd, rest = args[0], args[1:]
    if cmd in ('-V', '--version', 'version'):
        print(f'agentic-sdlc {__version__}')
        return 0
    if cmd == 'pm':
        from agentic_sdlc.repo.pm import cli as pm_cli
        return pm_cli.main(rest)
    if cmd == 'init':
        from agentic_sdlc.repo import init
        return init.main(rest)
    if cmd == 'gates-extra':
        from agentic_sdlc.repo import gates_extra
        return gates_extra.main(rest)
    if cmd == 'verify':
        from agentic_sdlc.repo.verify import main as verify_main
        return verify_main.main(rest, _verify_section)
    if cmd == DISPATCH_VERB:
        from agentic_sdlc.repo import dispatch
        return dispatch.main(rest)
    if cmd == CHANGELOG_VERB:
        from agentic_sdlc.repo.pm import changelog
        return changelog.main(rest)
    if cmd == LESSON_VERB:
        from agentic_sdlc.repo.conveyor import lessons
        return lessons.main(rest)
    if cmd in CONVEYOR_VERBS:
        # The whole argv passes through: `close` picks its grain beside the driver's table.
        from agentic_sdlc.repo.conveyor import driver
        return driver.main([cmd, *rest])
    if cmd in install_commands():
        from agentic_sdlc.repo import install
        return install.main(cmd, rest)
    if cmd == 'check':
        if not rest:
            return _usage()
        return _run_check(rest[0], rest[1:])
    print(f'agentic-sdlc: unknown command {cmd!r}', file=sys.stderr)
    return _usage()


if __name__ == '__main__':
    raise SystemExit(main())
