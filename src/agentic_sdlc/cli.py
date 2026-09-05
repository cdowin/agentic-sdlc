"""agentic-sdlc CLI — one entry point, subcommand per tool.

Every verb this docstring names is routed by `main()` below, and a test proves
that both ways round. A `--help` advertising a verb the tool does not have is
worse than a bare error, because it reads as documentation: this file printed a
menu of fourteen absent scene verbs for the whole of 0.1.0.

Project management (the PM tree is markdown + frontmatter):
    agentic-sdlc pm story <status> <story-id>
    agentic-sdlc pm feature <status> <feature-id>
    agentic-sdlc pm feature done <feature-id> [--review-record <path>]
    agentic-sdlc pm milestone <status> <milestone-id>
    agentic-sdlc pm status [<milestone>]
    agentic-sdlc pm list [--status …] [--owner …] [--milestone …]
    agentic-sdlc pm vocabulary [--json]  # the closed state set + the rule ids
    agentic-sdlc pm validate             # ids/parentage/refs/graph integrity
    agentic-sdlc pm decide <grain-id> <title...>
    agentic-sdlc pm ledger record|show|report
    agentic-sdlc pm install-skills       # the shared rule + operations skill
    agentic-sdlc pm init                 # stand up a tree in a repo with none
    agentic-sdlc pm new <milestone|feature|story|bug> ...
    (`pm --help` is the full verb list. A status moves through code rather than
     a regex; `check pm` reports a tree whose statuses contradict each other,
     off the SAME predicates)

Installers (write the file once; after that it is the repo's):
    agentic-sdlc init               # a repo wired for this kit: every installer
                                    # below in order, plus the two files nothing
                                    # else writes (devkit.toml and your two-line
                                    # Makefile), the PM tree, the .gitignore
                                    # entries and a CLAUDE.md skeleton.
                                    # Idempotent; --force touches the
                                    # devkit-owned files only
    agentic-sdlc install-ci         # the workflow that runs `make milestone`
    agentic-sdlc install-agents     # the review + build contract, as agent
                                    # definitions (a rules file never reaches
                                    # a subagent's spawn context; a definition
                                    # does)
    agentic-sdlc install-hooks      # the agent-workflow guard corpus and
                                    # setup-hooks.sh
    agentic-sdlc install-runners    # the sandboxed headless-run shell library
                                    # and the standard target set that calls it
    (each takes --force to overwrite a differing destination, and --diff to
     print what would change without writing. `install-<what> --help` is that
     installer's plan.)

Static gates (exit 1 on findings; run from anywhere inside the repo):
    agentic-sdlc check doc | shell | repo-hygiene | pm | hooks
    agentic-sdlc check <gate> --help  # that gate's contract, config and scope
    agentic-sdlc check all          # the default roster (doc + shell); every
                                    # other gate stays explicit — see
                                    # KNOWN_GATES for the reason each is out.
                                    # `[checks] all` in devkit.toml names the
                                    # roster for THIS repo.
    agentic-sdlc gates-extra        # `[gates] extra`, one make target per line:
                                    # the project's OWN gate targets, which
                                    # Makefile.devkit's `check` runs after the
                                    # devkit ones. The include shells out to
                                    # this rather than parsing TOML in make.

Per-project config: devkit.toml at the consuming repo root (see each tool's
module docstring for its section).
"""
from __future__ import annotations

import sys

from agentic_sdlc import __version__
from agentic_sdlc.core.config import ConfigError, config_section, str_tuple

FIX_FLAG = '--fix'
HELP_FLAGS = ('-h', '--help')

# THE gate roster: {name: in the default `check all`?}. One list, because two
# were one list with the answer to a single question split across them — and a
# gate added to one and forgotten in the other is either undispatchable or
# invisible to `[checks] all`'s own typo refusal.
#
# EVERY NAME HERE MUST DISPATCH. `tests/test_gate_roster.py` asserts this dict's
# keys equal the set `_check_module` resolves, and it asks the function rather
# than restating the answer. That test is the deliverable, not the list: eight
# phantom names — `uid`, `tres`, `props`, `defaults`, `rng`, `tres-comment`,
# `unit-disk`, `test-shape` — survived the extraction that touched every other
# surface in this file, and three of them sat at `True`, so a stock consumer's
# `check all` exited 2 while the error message named the gate it had just
# refused as a known one. Pruning them was the small half. Nothing had ever
# asserted that the roster equalled what runs, which is why nothing noticed.
#
# The `False` gates are out of the DEFAULT aggregate, each for its own reason:
# `repo-hygiene` is close-time and hits the network; `pm` would fail a repo for
# not having a PM tree at all; `hooks` would fail one that has not run
# `install-hooks`, and arming is a decision a consumer makes once — the gate is
# for a repo that HAS decided, and would otherwise be told so by a red run on
# the day it upgraded.
KNOWN_GATES = {
    'doc': True, 'shell': True,
    'repo-hygiene': False, 'pm': False, 'hooks': False,
}

# The gates that accept `--fix`. Empty since 0.2.0 — `uid` was the only one and
# it left with the Godot half. Kept rather than inlined, because the PLUMBING is
# a shipped contract with its own tests: `_run_check` refuses an unknown flag at
# exit 2 instead of silently ignoring it, and a consumer that thinks it asked
# for a repair and got a read-only run has been lied to. A second fixable gate
# is a row here, not a new inline condition.
FIXABLE_CHECKS: frozenset[str] = frozenset()


def all_roster() -> tuple[str, ...]:
    """Which gates `check all` runs HERE — `[checks] all`, else the defaults.

    Applicability is per-repo and the aggregate is where it shows. `shell` reads
    scripts under `tools/`, so a repo holding none gets a 0-file census and rule
    4 correctly turns it red. That is not drift and it is not a reason to weaken
    a gate — it is the roster being wrong for the repo, which is exactly the
    kind of variation rule 5 puts in devkit.toml.

    An unknown name is REFUSED rather than skipped: a typo would otherwise
    narrow the aggregate in silence, which is the cardinal sin with a config
    file in front of it.
    """
    default = tuple(name for name, on in KNOWN_GATES.items() if on)
    roster = str_tuple(config_section('checks'), 'checks', 'all', default)
    unknown = [c for c in roster if c not in KNOWN_GATES]
    if unknown:
        raise ConfigError(
            f'[checks] all names unknown gate(s) {", ".join(unknown)} — '
            f'known gates are {" ".join(KNOWN_GATES)}')
    # `all` naming itself would recurse forever; it is the one name that cannot
    # appear, and KNOWN_GATES already excludes it.
    return tuple(dict.fromkeys(roster))


def install_commands() -> tuple[str, ...]:
    """The `install-*` verbs, from the installer's own plan table.

    Asked rather than restated: a second list here would be a second name for
    the same fact, and the failure mode is a verb documented in one place and
    dispatched in neither.
    """
    from agentic_sdlc.repo.install import PLANS
    return tuple(PLANS)


def _usage() -> int:
    print(__doc__.strip())
    return 2


def _run_check(name: str, flags: list[str]) -> int:
    # One try around the whole body: `_check_module` can now raise on a broken
    # install, and it is reached from the `--help` path as well as the dispatch.
    # A devkit.toml mistake is exit 2, never 1 (findings) and never 0.
    try:
        return _run_check_inner(name, flags)
    except ConfigError as err:
        print(f'agentic-sdlc: {err}', file=sys.stderr)
        return 2


def _run_check_inner(name: str, flags: list[str]) -> int:
    if any(flag in HELP_FLAGS for flag in flags):
        # A gate's contract, its config section and its honest scope are in its
        # module docstring — the one copy, so `--help` cannot drift from it.
        module = _check_module(name)
        if module is None:
            return _unknown_check(name)
        print((module.__doc__ or '').strip())
        return 0
    # Only the FIXABLE_CHECKS take a flag today. An unknown one is a usage
    # error, never a silently-ignored argument: a consumer that thinks it asked
    # for a repair and got a read-only run has been lied to.
    unknown = [f for f in flags
               if not (name in FIXABLE_CHECKS and f == FIX_FLAG)]
    if unknown:
        print(f'agentic-sdlc: check {name}: unexpected argument(s) '
              f'{" ".join(unknown)}', file=sys.stderr)
        return 2
    return _dispatch_check(name, fix=FIX_FLAG in flags)


def _check_module(name: str):
    """The module implementing one gate, or None.

    DERIVED, not tabulated. A gate named `x-y` in KNOWN_GATES is
    `agentic_sdlc.repo.checks.x_y`, so the roster and the dispatch cannot
    disagree — which is the whole defect this replaced: an `if` chain beside a
    dict is two lists answering one question, and eight names lived in the dict
    with no branch for two releases.

    KNOWN_GATES membership is checked FIRST and it is the refusal, not a
    convenience: `name` reaches here from argv and from `[checks] all`, and an
    import derived from unvalidated input is an import of whatever the caller
    named. A name outside the roster never becomes a module path.

    Still lazy, for the reason it always was: a gate nobody asked for is a gate
    nobody imports.
    """
    if name not in KNOWN_GATES:
        return None
    from importlib import import_module
    try:
        return import_module(
            f'agentic_sdlc.repo.checks.{name.replace("-", "_")}')
    except ModuleNotFoundError:
        # A roster entry whose module is missing is a packaging fault, not a
        # user error. Returning None would print "unknown check" and send the
        # reader to look for their own typo.
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
    # `all` never repairs: an aggregate that writes is the last place a
    # consumer expects one, so `--fix` is asked for on the gate itself.
    return module.run(fix=fix) if name in FIXABLE_CHECKS else module.run()


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
