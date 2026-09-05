"""agentic-sdlc CLI — one entry point, subcommand per tool.

Introspection (pure parse, never boots Godot):
    agentic-sdlc scene <file.tscn|.tres> [--props] [--paths]
    agentic-sdlc scene-diff <file> [--git <ref>]  |  scene-diff <old> <new>
    agentic-sdlc refs <symbol> [--tests]
    agentic-sdlc orphans [--tests]
    agentic-sdlc autoloads
    agentic-sdlc tiles <file.tscn> [--layer NAME]
                       [--cols] [--rows] [--at X,Y] [--region X0,Y0,X1,Y1]
                                    # a TileMapLayer's grid: cell count, bounds,
                                    # tile-kind histogram, per-column/row counts

Scene surgery (pure parse; edits only the lines it was asked to, or refuses):
    agentic-sdlc scene set      <file> <node-path> <prop> <value>
    agentic-sdlc scene set      <file> --resource <prop> <value>
    agentic-sdlc scene set      <file> --sub-resource <id> <prop> <value>
                                    # the [resource] body of a .tres, or a
                                    # [sub_resource] by the id `scene --props`
                                    # prints — read output is write input
    agentic-sdlc scene rename   <file> <node-path> <new-name>
    agentic-sdlc scene add      <file> <parent-path> <name> <type> [--script ...]
    agentic-sdlc scene add      <file> <parent-path> <name> --instance res://x.tscn
                                    # an instance node (no type=); its ref is
                                    # minted from the scene's own uid, or refused
    agentic-sdlc scene rm       <file> <node-path>
    agentic-sdlc scene reparent <file> <node-path> <new-parent>
    agentic-sdlc scene connect    <file> <signal> <from> <to> <method> [--flags N]
    agentic-sdlc scene disconnect <file> <signal> <from> <to> <method> [--flags N]
                                    # author / remove one [connection]; ambiguous
                                    # matches are refused, --flags names one
    agentic-sdlc refs --retarget <old-res-path> <new-res-path> [--dry-run]
                                    # after a git mv: rewrite every ext_resource
                                    # path attr + exact preload/load literal that
                                    # names old; anything unprovable is SKIPPED
                                    # with a reason, and skips exit 1
    agentic-sdlc scene canonicalize <file>... [--elide-defaults]
                                    # restore what PackedScene.pack() drops:
                                    # uid-in-refs, the header uid, index= on
                                    # instance children; --elide-defaults also
                                    # removes assignments equal to the script's
                                    # @export default (what the editor omits)
    agentic-sdlc tiles paint <file> --layer NAME --region X0,Y0,X1,Y1
                                    --tile SRC/AX,AY[/ALT]
    agentic-sdlc tiles erase <file> --layer NAME --region X0,Y0,X1,Y1
                                    # fill / clear a rectangle of one
                                    # TileMapLayer; only that one property's
                                    # base64 is regenerated
    (every verb takes --dry-run, prints a unified diff, and is idempotent)

Project management (engine-agnostic; the PM tree is markdown + frontmatter):
    agentic-sdlc pm story <wip|review|blocked> <story-id>
    agentic-sdlc pm feature <ready|building|review> <feature-id>
    agentic-sdlc pm feature done <feature-id> [--review-record <path>]
    agentic-sdlc pm milestone <ready|building|done> <milestone-id>
    agentic-sdlc pm status [<milestone>]
    agentic-sdlc pm vocabulary --json   # the closed state set + the rule ids
    agentic-sdlc pm validate            # ids/parentage/refs/graph integrity
    agentic-sdlc pm install-skills      # the shared rule + operations skill
    agentic-sdlc pm init                # stand up a tree in a repo with none
    agentic-sdlc pm new <milestone|feature|story|bug> ...
    (moves a `status:` through code rather than a regex; `check pm` reports a
     tree whose statuses contradict each other, off the SAME predicates)

Installers (write the file once; after that it is the repo's):
    agentic-sdlc init               # a blank Godot 4 project, wired: every
                                    # installer below in order, plus the two
                                    # files nothing else writes (devkit.toml
                                    # and your two-line Makefile), the PM tree,
                                    # the .gitignore entries and a CLAUDE.md
                                    # skeleton. Idempotent; --force touches the
                                    # devkit-owned files only
    agentic-sdlc install-ci         # the workflow that runs `make milestone`
    agentic-sdlc install-agents     # the review + build contract, as agent
                                    # definitions (a rules file never reaches
                                    # a subagent's spawn context; a definition
                                    # does)
    agentic-sdlc install-hooks      # the shared-tree commit guard, the
                                    # raw-engine-boot guard, and setup-hooks.sh
    agentic-sdlc install-runners    # the sandboxed headless-run shell library
                                    # + the import-cache runner (gdk_* library)
    (each takes --force to overwrite a differing destination, and --diff to
     print what would change without writing)

Static gates (exit 1 on findings; run from anywhere inside the repo):
    agentic-sdlc check uid [--fix] | tres | props | defaults | doc | shell
                      | repo-hygiene | pm | hooks | rng | tres-comment
                      | unit-disk | test-shape
    agentic-sdlc check <gate> --help  # that gate's contract, config and scope
                                    # `uid --fix` applies the repairs the gate
                                    # already computes: stale Script ref uids
                                    # rewritten to the sidecar's, non-canonical
                                    # spellings canonicalized (same id), and
                                    # orphan .gd.uid sidecars deleted
    agentic-sdlc check all          # the offline fast set (uid+tres+props+doc+shell).
                                    # Every other gate stays explicit — see
                                    # KNOWN_GATES for the reason each is out.
                                    # `[checks] all` in devkit.toml names the
                                    # roster for THIS repo — a repo with no
                                    # Godot tree runs the repo-family gates
                                    # instead of failing five Godot ones over a
                                    # 0-file census.
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
RETARGET_FLAG = '--retarget'

# THE gate roster: {name: in the default `check all`?}. One list, because two
# were one list with the answer to a single question split across them — and a
# gate added to one and forgotten in the other is either undispatchable or
# invisible to `[checks] all`'s own typo refusal.
#
# The `False` gates are out of the DEFAULT aggregate, each for its own reason:
# `defaults` reports thousands of findings on a tree that has never been
# canonicalized, so folding it in would redden every existing consumer on a
# version bump — wire it explicitly, after the one-time cleanup pass;
# `repo-hygiene` is close-time and hits the network; `pm` would fail a repo for
# not having a PM tree at all; `hooks` would fail one that has not run
# `install-hooks`, and arming is a decision a consumer makes once — the gate is
# for a repo that HAS decided, and would otherwise be told so by a red run on
# the day it upgraded.
# The four ported project scans are all False for one shared reason and one
# each: none of them can state a stock scope that is true of every repo. `rng`
# defaults to the WHOLE tree and would redden a consumer's cosmetic jitter on a
# pin bump; `unit-disk` and `test-shape` name test roots a fresh project does
# not have yet, and rule 4 correctly reddens a 0-file census; `tres-comment`
# would redden any tree that has never been swept. Each is one `[checks] all`
# entry away, once the repo has declared its scope — which is the adoption step,
# not a default.
KNOWN_GATES = {
    'uid': True, 'tres': True, 'props': True, 'doc': True, 'shell': True,
    'defaults': False, 'repo-hygiene': False, 'pm': False, 'hooks': False,
    'rng': False, 'tres-comment': False, 'unit-disk': False,
    'test-shape': False,
}

# The gates that accept `--fix`. A second fixable gate is a row here, not a
# new inline condition in `_run_check`.
FIXABLE_CHECKS = frozenset({'uid'})


def all_roster() -> tuple[str, ...]:
    """Which gates `check all` runs HERE — `[checks] all`, else the defaults.

    Applicability is per-repo and the aggregate is where it shows. Five of the
    eight gates read `.tscn`/`.tres`/shell, so a repo holding none of those
    (this package itself; a PM-tree-only consumer) gets five 0-file censuses,
    and rule 4 correctly turns every one of them red. That is not drift and it
    is not a reason to weaken a gate — it is the roster being wrong for the
    repo, which is exactly the kind of variation rule 5 puts in devkit.toml.

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
    try:
        return _dispatch_check(name, fix=FIX_FLAG in flags)
    except ConfigError as err:
        # A devkit.toml mistake is exit 2, never 1 (findings) and never 0.
        print(f'agentic-sdlc: {err}', file=sys.stderr)
        return 2


def _check_module(name: str):
    """The module implementing one gate, or None.

    Split out of the dispatch so `--help` can reach a gate's docstring without a
    second table naming the same modules — the import chain IS the roster, and
    it is lazy on purpose: a gate nobody asked for is a gate nobody imports.
    """
    if name == 'doc':
        from agentic_sdlc.repo.checks import doc
        return doc
    if name == 'shell':
        from agentic_sdlc.repo.checks import shell
        return shell
    if name == 'repo-hygiene':
        from agentic_sdlc.repo.checks import repo_hygiene
        return repo_hygiene
    if name == 'pm':
        from agentic_sdlc.repo.checks import pm
        return pm
    if name == 'hooks':
        from agentic_sdlc.repo.checks import hooks
        return hooks
    return None


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
