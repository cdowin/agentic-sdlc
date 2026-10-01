"""`agentic-sdlc gates-extra`: `[gates] extra`, the project's own gate targets, one per line.

`Makefile.devkit`'s `check` runs them after `agentic-sdlc check all`; a verb rather than
a grep so there is one TOML reader. Each name is interpolated into a make command line,
so anything that is not a bare make goal is refused at exit 2, never dropped.

Two namespaces sit next to each other in devkit.toml and neither key says
which it is: this one takes MAKE TARGETS, `[checks] all` takes GATE NAMES. A
gate name is a perfectly legal make goal, so the grammar below cannot see it,
and what an adopting agent got for `extra = ["budget"]` was `make[1]: *** No
rule to make target 'budget'. Stop.` — GNU make, three layers under the config
that caused it. `_refuse_gate_names` is that report, moved to the key's own
reader.

`[gates.inputs]` names the paths one of those targets reads (#98):
`lint = ["tools/lint.sh", "src"]`. A declared target runs through
`gates-extra --run <target>`, which reuses its recorded PASS while those paths,
the makefiles and this tool are byte-identical, the way `check all` reuses a
devkit gate. An undeclared target runs every time, exactly as before.
"""
from __future__ import annotations

import os
import re
import sys

from agentic_sdlc.core.config import (ConfigError, config_section,
                                      pointer_escapes, str_tuple,
                                      str_tuple_table)

SECTION = 'gates'
KEY = 'extra'
INPUTS_KEY = 'inputs'
INPUTS_FLAG = '--inputs'
RUN_FLAG = '--run'
FAILED_ENV = 'GDK_EXTRA_FAILED'

USAGE = """usage: agentic-sdlc gates-extra [--inputs | --run <target>...]

Prints `[gates] extra` from devkit.toml, one make target per line — the
project's own gate targets, which Makefile.devkit's `check` runs after the
devkit ones. No section, or no key: prints nothing, exits 0.

  --inputs        print the targets `[gates.inputs]` declares paths for, one
                  per line, in `[gates] extra` order
  --run <target>... run each declared target (`make GDK_IN_CHECK=1 <target>`),
                  or reuse its recorded PASS while the paths it declares, the
                  makefiles and this tool are byte-identical; a reuse prints
                  the PASS line with `; reused — green at <ts> on inputs <id>`

This key is a MAKE TARGET namespace; `[checks] all` next door is the GATE
name one. A devkit gate name here is refused and told which key runs it.

Exit: 0 = printed (possibly nothing), or the target passed | 1 = the target
failed | 2 = the value is not a usable roster, or the target declares no inputs."""

# `fullmatch` below AND the `$`: `$` alone matches before a trailing newline.
TARGET = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]*$')
MAX_LENGTH = 64

# The other namespace, for the message that has to name it: `[checks] all` is
# the gate roster, and `make check` is the target Makefile.devkit gives it.
GATE_TARGET = 'check'
ROSTER_SECTION = 'checks'
ROSTER_KEY = 'all'


def targets() -> tuple[str, ...]:
    """`[gates] extra`, validated; duplicates collapse in declaration order."""
    roster = str_tuple(config_section(SECTION), SECTION, KEY, ())
    # Shape first, namespace second: a value make cannot parse is the more
    # fundamental defect and its repair is a different one, so a roster holding
    # both reports the shape refusal rather than being told about a namespace
    # it never reached.
    _refuse_non_targets(roster)
    _refuse_gate_names(roster)
    return tuple(dict.fromkeys(roster))


def _refuse_non_targets(roster: tuple[str, ...]) -> None:
    """Every value the include could not interpolate as one make goal."""
    bad = [name for name in roster
           if not TARGET.fullmatch(name) or len(name) > MAX_LENGTH]
    if bad:
        raise ConfigError(
            f'[{SECTION}] {KEY} names {len(bad)} value(s) that are not make '
            f'targets: {", ".join(repr(name) for name in bad)} — a target is '
            f'[A-Za-z0-9][A-Za-z0-9._+-]* and at most {MAX_LENGTH} '
            f'characters, because the include interpolates it into a make '
            f'command line')


def _refuse_gate_names(roster: tuple[str, ...]) -> None:
    """A well-formed target name that is a GATE name is the wrong namespace.

    The universe is `gate_universe()`, derived from `repo/checks/`, so a gate
    added later is named here the day it ships and there is no second roster
    to fall out of date. Imported inside the call because `belts`
    reads this module's `targets` — a module-level import either way is a
    cycle — and because a repo declaring no `[gates] extra` should not pay for
    the import to be told nothing (rule 5: stock runs byte-identically).

    Exact membership, never a substring: `budget-check` is an ordinary name
    for a project target that WRAPS a devkit gate, and refusing it would be
    this key's own version of the cardinal sin.
    """
    if not roster:
        return
    from agentic_sdlc.repo.belts import gate_universe

    universe = gate_universe()
    named = [name for name in dict.fromkeys(roster) if name in universe]
    if not named:
        return
    entries = ", ".join(repr(name) for name in named)
    is_are = 'is a gate' if len(named) == 1 else 'are gates'
    them = 'it' if len(named) == 1 else 'them'
    raise ConfigError(
        f'[{SECTION}] {KEY} names make targets, not gate names: {entries} '
        f'{is_are} this package ships, and `make {GATE_TARGET}` is the target '
        f'that runs {them} — declare {them} in [{ROSTER_SECTION}] '
        f'{ROSTER_KEY} instead. [{SECTION}] {KEY} is for targets your OWN '
        f'makefile defines, which `make {GATE_TARGET}` runs after the devkit '
        f'gates')


def inputs() -> dict[str, tuple[str, ...]]:
    """`[gates.inputs]`, validated against `[gates] extra`: target -> the
    path prefixes it reads. Stock: nothing declared, and every target runs."""
    declared = str_tuple_table(config_section(SECTION), SECTION, INPUTS_KEY,
                               {})
    roster = targets()
    stray = [name for name in declared if name not in roster]
    if stray:
        raise ConfigError(
            f'[{SECTION}.{INPUTS_KEY}] names {", ".join(map(repr, stray))}, '
            f'which [{SECTION}] {KEY} does not — inputs for a target `make '
            f'check` never runs are a setting that never applies')
    for name, paths in declared.items():
        bad = [path for path in paths
               if pointer_escapes(path) or not path.strip().strip('./')]
        if bad:
            raise ConfigError(
                f'[{SECTION}.{INPUTS_KEY}] {name} names '
                f'{", ".join(map(repr, bad))} — every input is a non-empty '
                f'path inside this checkout, relative to its root')
    return {name: declared[name] for name in roster if name in declared}


def _run(targets: tuple[str, ...]) -> int:
    """`--run`: each declared target, reused or run, through ONE gate cache
    session: the tree is listed and each path read once for all of them, so
    twenty reused gates cost one hash of the tree, not twenty. Every target
    runs; the exit is the worst."""
    from agentic_sdlc.core import makefile
    from agentic_sdlc.core.project import repo_root
    from agentic_sdlc.repo.verify import gates
    declared = inputs()
    for target in targets:
        if target not in declared:
            print(f'agentic-sdlc gates-extra: {target!r} declares no '
                  f'[{SECTION}.{INPUTS_KEY}], so there is nothing to key a reuse '
                  f'on — `make check` runs it directly', file=sys.stderr)
            return 2
    root = repo_root()
    recipes = []
    for path in makefile.sources(root):
        try:
            recipes.append(path.relative_to(root).as_posix())
        except ValueError:
            continue
    session = gates.Session(root)
    worst = 0
    failed = []
    for target in targets:
        code = _run_one(session, root, target, (*declared[target], *recipes))
        if code:
            failed.append(target)
        worst = max(worst, code)
    # Makefile.devkit's `check` names each failed target in its verdict.
    where = os.environ.get(FAILED_ENV)
    if failed and where:
        from pathlib import Path
        from agentic_sdlc.core import apply
        apply.write(Path(where), '\n'.join(failed) + '\n')
    return worst


def _run_one(session, root, target: str, paths: tuple[str, ...]) -> int:
    from agentic_sdlc.core import spawn
    command = [os.environ.get('MAKE') or 'make', 'GDK_IN_CHECK=1', target]

    def run() -> tuple[int, str]:
        # Captured, then passed on whole: the last line is what a reuse says.
        done = spawn.run(command, cwd=str(root), capture_output=True,
                         text=True)
        out = done.stdout or ''
        sys.stdout.write(out)
        sys.stdout.flush()
        sys.stderr.write(done.stderr or '')
        lines = [line for line in out.splitlines() if line.strip()]
        return done.returncode, lines[-1] if lines else ''

    code = session.extra(target, paths, run)
    if code != 0:
        print(f'agentic-sdlc gates-extra: FAILED (exit {code}) — '
              f'{" ".join(command)}', file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    if any(arg in ('-h', '--help', 'help') for arg in argv):
        print(USAGE)
        return 0
    mode = argv[0] if argv else ''
    if (mode == INPUTS_FLAG and len(argv) == 1) or not argv:
        pass
    elif mode == RUN_FLAG and len(argv) >= 2:
        try:
            return _run(tuple(argv[1:]))
        except ConfigError as err:
            print(f'agentic-sdlc: {err}', file=sys.stderr)
            return 2
    else:
        print(f'agentic-sdlc gates-extra: unexpected argument(s) '
              f'{" ".join(map(repr, argv))}', file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    try:
        roster = tuple(inputs()) if mode == INPUTS_FLAG else targets()
    except ConfigError as err:
        print(f'agentic-sdlc: {err}', file=sys.stderr)
        return 2
    for name in roster:
        print(name)
    return 0
