"""`repo/vehicle.py` — every command the CLI prints for a person to run, spelled through the stock wiring.

The stock wiring never puts `agentic-sdlc` on PATH (#22, #36), so every printed
command is `make pm ARGS=…` or `make sdlc ARGS=…`. The recipe hands `ARGS` to
a second shell (`$(value ARGS)`, D2), so a line is parsed TWICE before the verb
sees its argv, and a quoting mistake is not an error: `costs $5` arrived as
`costs ` and exited 0, rule 4's second sin. The round trip here is `shlex`
twice; `test_makefile_include.py` runs the same lines through real make.
"""
from __future__ import annotations

import ast
import shlex
import unittest

from support import REPO_ROOT
from test_cli_surface import routed_verbs

from agentic_sdlc import __version__
from agentic_sdlc.repo import vehicle

SRC = REPO_ROOT / 'src' / 'agentic_sdlc'
# What a rendered free-text argument or a real id could carry that a shell
# would act on: expansion, substitution, both quote kinds, history, escapes,
# operators, whitespace, the empty string, and a long word.
HOSTILE = ('costs $5', '$(touch pwned)', '`pm list` gains a column', "it's",
           'a "quoted" word', '!bang', 'back\\slash', 'semi; colon', 'a | b',
           'x && y', '  padded  ', '', 'tab\there', '<sentence>', 'naïve',
           'w' * 300)
# Call sites at the time of writing; a census that shrank is a sweep undone.
SITES_FLOOR = 58


def _resolved(node: ast.expr) -> list[str]:
    """One call argument as rendered text: a literal as itself, `Slot('<x>')`
    as a slot, anything computed as EVERY hostile value in turn."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'Slot' and node.args
            and isinstance(node.args[0], ast.Constant)):
        return [vehicle.Slot(node.args[0].value)]
    return list(HOSTILE)


def _sites(source: str, where: str) -> list[tuple[str, str, list[list[str]]]]:
    """(where, 'command'|'pinned', one list of candidates per argument) for
    every `vehicle.command(…)` / `vehicle.pinned(…)` in one module's source."""
    found = []
    for node in ast.walk(ast.parse(source)):
        func = getattr(node, 'func', None)
        if (isinstance(node, ast.Call) and isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == 'vehicle'
                and func.attr in ('command', 'pinned')):
            args = [_resolved(a.value if isinstance(a, ast.Starred) else a)
                    for a in node.args]
            found.append((f'{where}:{node.lineno}', func.attr, args))
    return found


def call_sites() -> list[tuple[str, str, list[list[str]]]]:
    """Every vehicle call site in the package but the helper's own module."""
    return [site for path in sorted(SRC.rglob('*.py'))
            if path.name != 'vehicle.py'
            for site in _sites(path.read_text(encoding='utf-8'),
                               str(path.relative_to(SRC)))]


def rejected(sites, verbs: set[str]) -> list[str]:
    """Each rendered line that does not survive both parses, and each literal
    verb the router does not route — a line naming one runs nothing."""
    out = []
    for where, kind, args in sites:
        for i in range(max((len(a) for a in args), default=1)):
            argv = [a[i % len(a)] for a in args]
            line = getattr(vehicle, kind)(*argv)
            back = (shlex.split(line)[4:] if kind == 'pinned'
                    else vehicle.argv_of(line))
            if back != argv:
                out.append(f'{where}: {line!r} hands the verb {back!r}')
        first = args[0] if args else []
        if (kind == 'command' and len(first) == 1
                and first[0] not in verbs | {vehicle.PM_TARGET}):
            out.append(f'{where}: {first[0]!r} is no verb the router routes')
    return out


class EveryVehicleLineRoundTrips(unittest.TestCase):

    PROTECTS = (
        'every command line the package renders survives both shell parses '
        'with hostile values in every computed argument, and names a routed '
        'verb',
        'load-bearing — sin 2 (a write that looks legitimate and is not): '
        'through a double-quoted ARGS, `costs $5` was written as `costs ` at '
        'exit 0 (feature D2, review M2)',
    )
    CORPUS = (
        ("vehicle.command('wombat', 'x')\n", True),
        ("vehicle.command('close', 'story', gid)\n", False),
        ("vehicle.command('pm', 'set', gid, 'changelog', text)\n", False),
        ("vehicle.pinned('install-gates', '--force')\n", False),
        ("x = vehicle.command('dispatch', '--grain', vehicle.Slot('<id>'))\n",
         False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(rejected(_sites(planted, 'planted'), routed_verbs()))

    def test_hostile_argv_survives_both_parses_and_a_non_line_is_refused(self):
        """The grammar's matrix (SDLC §5), once, where the grammar lives."""
        for value in HOSTILE:
            for argv in (['pm', 'set', 'st-x', 'changelog', value],
                         ['close', 'story', value], [value]):
                line = vehicle.command(*argv)
                with self.subTest(argv=argv, line=line):
                    self.assertEqual(vehicle.argv_of(line), argv)
                    # The operator's shell sees ONE word after the target:
                    # outer quoting that let it split was the leak.
                    self.assertEqual(len(shlex.split(line)), 3)
        slot = vehicle.command('close', 'story', vehicle.Slot('<id>'))
        self.assertEqual(slot, "make sdlc ARGS='close story <id>'")
        self.assertEqual(vehicle.command('pm', 'set', 'st-x', 'changelog',
                                         'costs $5'),
                         "make pm ARGS='set st-x changelog '\"'\"'costs $5'"
                         "\"'\"''")
        self.assertEqual(shlex.split(vehicle.pinned('install-gates', '--force')),
                         ['uvx', '--from', f'{vehicle.SOURCE}@v{__version__}',
                          'agentic-sdlc', 'install-gates', '--force'])
        for line in ('agentic-sdlc pm status', 'make check',
                     "make pm ARGS='a' extra", 'make pm OTHER=x', ''):
            with self.subTest(refused=line), self.assertRaises(ValueError):
                vehicle.argv_of(line)
        with self.assertRaises(ValueError):
            vehicle.command()

    def test_every_call_site_renders_a_line_that_round_trips(self):
        """Read off the SOURCE, so a new call site is graded the day it lands,
        with every computed argument replaced by each hostile value in turn —
        a gid, a role, a sentence."""
        sites = call_sites()
        self.assertGreaterEqual(
            len(sites), SITES_FLOOR,
            f'{len(sites)} vehicle call sites — the census collapsed, so a '
            f'hint went back to naming the bare binary or this reader broke')
        self.assertEqual([], rejected(sites, routed_verbs()))

if __name__ == '__main__':
    unittest.main()
