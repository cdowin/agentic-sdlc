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

Verification (`[verify]` in devkit.toml; `verify --help` is the ladder):
    agentic-sdlc verify --spot|--milestone|--plan|--check
    agentic-sdlc integrate <slug>... [--merge-only <branch>]... [--batch <name>] [--base <branch>] [--keep-lanes] [--no-cache]
                                    # merge a batch of lanes, prove it once ([integrate]), close it

Static gates (exit 1 on findings; `check <gate> --help` is that gate's contract):
    agentic-sdlc check doc|shell|grain-shape|pm|repo-hygiene|all
                                    # `all` reuses a gate's PASS while its inputs are unchanged
                                    # (`all --no-cache` reads and records none); one gate always runs
    agentic-sdlc gates-extra        # `[gates] extra`, one make target per line; `--inputs`, `--run <target>`

Belts (facts about the tree, then one status write or a clean error; no gate runs):
    agentic-sdlc release <version>  # every feature done, versions in sync, clean, on branch; --force on the record
    agentic-sdlc adopt <version>    # a devkit PIN bump, checks only: pin, installables, config
    A close is a status write: `pm story <done-state> <id>`, `pm feature <done-state> <id>`.

Rendering (writes to stdout, runs nothing — paste it or pipe it):
    agentic-sdlc dispatch [--grain <id>] [--role <name>]   # the contract preamble
    agentic-sdlc changelog <milestone-id>   # the grains' `changelog:` lines, in `order:`


    agentic-sdlc version            # also -V / --version

Per-project config is devkit.toml at the consuming repo root.
"""
from __future__ import annotations

import os
import shlex
import sys

from agentic_sdlc import __version__
from agentic_sdlc.core.config import (ConfigError, config_section,
                                      section_declared, str_tuple)

FIX_FLAG = '--fix'
# `check all` alone: run every gate, and read and record no reuse (#98).
NO_CACHE_FLAG = '--no-cache'
# `check shell` alone: PRINT the `[shell] shellcheck_version` pin and run
# nothing. The stock verify.yml asks it which shellcheck to install, so the
# workflow reads the key through this tool, never a parser of its own.
PIN_FLAG = '--pin'
HELP_FLAGS = ('-h', '--help')

CHANGELOG_VERB = 'changelog'
DISPATCH_VERB = 'dispatch'
# Verbs 2.0.0 removed, refused BY NAME with what replaces each (rule 11):
# "unknown command" reads as a typo and sends the caller looking for the
# right spelling.
RETIRED_VERBS = {
    'close': 'a close is a status write: `pm story <done-state> <id>` or '
             '`pm feature <done-state> <id>`; `integrate` writes it for a batch',
    'land': '`integrate <slug>...` merges a batch, proves it once and closes it',
    'ship': '`release <version>` over a milestone with one feature',
    'lesson': 'a lesson is an issue or a memory note',
    'install-sdlc': 'the SDLC is a short hand-written page; delete '
                    'docs/sdlc-protocol.md',
    'preflight': 'it printed rows nobody acted on. Read what you need where it '
                 'lives: `verify --plan`, `pm status`, `check <gate>`',
    'cite': 'the rules are no longer cited by number in code. `git grep` the '
            'rule text you want',
}

# {gate: in the default `check all`?}; tests/test_gate_roster.py holds every key to a module.
# The OFF gates would redden a consumer that has no PM tree.
KNOWN_GATES = {
    'doc': True, 'shell': True, 'grain-shape': True,
    'repo-hygiene': False, 'pm': False,
}

# Empty, and kept because `_run_check` refuses an unknown flag through it.
FIXABLE_CHECKS: frozenset[str] = frozenset()


def stock_roster() -> tuple[str, ...]:
    """What `check all` runs when `[checks] all` is undeclared."""
    return tuple(name for name, on in KNOWN_GATES.items() if on)


def all_roster() -> tuple[str, ...]:
    """`[checks] all`, else the stock default; an unknown name is refused, never skipped."""
    roster = str_tuple(config_section('checks'), 'checks', 'all', stock_roster())
    unknown = [c for c in roster if c not in KNOWN_GATES]
    if unknown:
        # A roster error must not HIDE the config errors of the gates that were
        # named correctly. The adoption that motivated this hit exactly one
        # message — about gate NAMES — routed the whole bump at the roster, and
        # never learned that its PM tree declared no flow at all. A green
        # aggregate over a tree with no declared flow is the failure named.
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
            from agentic_sdlc.repo.pm import vocabulary
            said.extend(vocabulary.all_config_defects())
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
    if name == 'shell' and flags == [PIN_FLAG]:
        return _check_module(name).print_pin()
    # An unknown flag is a usage error, never silently ignored.
    unknown = [f for f in flags
               if not (name in FIXABLE_CHECKS and f == FIX_FLAG)
               and not (name == 'all' and f == NO_CACHE_FLAG)]
    if unknown:
        print(f'agentic-sdlc: check {name}: unexpected argument(s) '
              f'{" ".join(unknown)}', file=sys.stderr)
        return 2
    return _dispatch_check(name, fix=FIX_FLAG in flags,
                           no_cache=NO_CACHE_FLAG in flags)


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


def _dispatch_check(name: str, fix: bool = False,
                    no_cache: bool = False) -> int:
    if name == 'all':
        # Each gate is reused when what it reads has not moved (#98); the
        # roster, the order and the worst exit are as they always were.
        from agentic_sdlc.core.project import repo_root
        from agentic_sdlc.repo.verify import gates
        return gates.run_all(repo_root(), all_roster(), _check_module,
                             _dispatch_check, reuse=not no_cache)
    module = _check_module(name)
    if module is None:
        return _unknown_check(name)
    # `all` never repairs; `--fix` is asked of the gate itself.
    return module.run(fix=fix) if name in FIXABLE_CHECKS else module.run()


def belt_verbs() -> tuple[str, ...]:
    from agentic_sdlc.repo import belts
    return belts.VERBS


# `Makefile.devkit`'s `pm` and `sdlc` recipes hand `ARGS` over here, never to a
# shell (#60): a `(` or `,` in a grain name was a bash parse error. Popped, so
# no process a verb spawns reads it as its own.
ARGS_ENV = 'AGENTIC_SDLC_ARGS'


def _with_env_args(args: list[str]) -> list[str] | None:
    """`args` plus the words of `AGENTIC_SDLC_ARGS`; None, said on stderr, when they do not split."""
    text = os.environ.pop(ARGS_ENV, None)
    if not text:
        return args
    try:
        return [*args, *shlex.split(text)]
    except ValueError as err:
        print(f'agentic-sdlc: ARGS does not split ({err}): write an apostrophe '
              f"in a name as \\' (The HUD\\'s name), or quote the whole name",
              file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    args = _with_env_args(list(sys.argv[1:] if argv is None else argv))
    if args is None:
        return 2
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
    if cmd == 'integrate':
        from agentic_sdlc.repo import integrate
        # [integrate], and [verify], whose keys key a proof receipt.
        return integrate.main(rest, lambda name: config_section(name)
                              if section_declared(name) else None)
    if cmd == DISPATCH_VERB:
        from agentic_sdlc.repo import dispatch
        return dispatch.main(rest, stock_roster())
    if cmd == CHANGELOG_VERB:
        from agentic_sdlc.repo.pm import changelog
        return changelog.main(rest)
    if cmd in belt_verbs():
        from agentic_sdlc.repo import belts
        return belts.main([cmd, *rest])
    retired = RETIRED_VERBS.get(cmd)
    if retired:
        print(f'agentic-sdlc: {cmd} was retired in 2.0.0 — {retired}',
              file=sys.stderr)
        return 2
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
