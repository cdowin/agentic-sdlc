"""`--help` names what ships, and ships what it names.

`_usage()` prints the module docstring on ANY unrecognised command, so a typo
hands the reader a menu. Through 0.1.0 that menu advertised fourteen verbs the
router had no branch for — `scene`, `scene-diff`, `refs`, `orphans`,
`autoloads`, `tiles` and eight `scene` subverbs — every one of them left behind
by the extraction. A wrong menu is worse than a bare error, because it reads as
documentation rather than as a mistake.

Both directions are asserted, and the verb list is PARSED out of the docstring
rather than restated here. A hand-written roster in a test is the same defect
one layer down: it goes stale in exactly the way the thing it guards does.
"""
from __future__ import annotations

import re

from agentic_sdlc import cli

# Every `agentic-sdlc <verb>` line in the docstring, first token only. The
# docstring also shows sub-verbs (`pm story …`, `check doc`) — those are the
# owning module's surface, and this file is about what `main()` routes.
_INVOCATION = re.compile(r'^\s*agentic-sdlc ([a-z][a-z0-9-]*)', re.M)


def documented_verbs() -> set[str]:
    return set(_INVOCATION.findall(cli.__doc__ or ''))


def routed_verbs() -> set[str]:
    """What `main()` dispatches, read off the router's own branches.

    The two ROSTERS are asked, never listed — `install_commands()` reads the
    installer's `PLANS` and `conveyor_verbs()` reads the driver's `OPERATIONS`,
    exactly as `main()` does. So a fifth installer or a third operation is
    documented-or-flagged the moment it exists, with nothing to update here.

    The four singletons below are the branches `main()` writes out longhand.
    They are the one hand-maintained list in this file, and the test that keeps
    them honest is `test_a_documented_verb_is_not_answered_with_unknown_command`,
    which asks the router rather than this set.
    """
    return {'pm', 'init', 'gates-extra', 'check', 'verify',
            *cli.install_commands(), *cli.conveyor_verbs()}


class TestTheHelpDescribesWhatShips:

    def test_every_documented_verb_is_routed(self):
        """The direction that was broken: a menu entry with no code behind it."""
        phantom = sorted(documented_verbs() - routed_verbs())
        assert phantom == [], (
            f'--help advertises {phantom}, which main() does not route; '
            f'a typo prints this menu')

    def test_every_routed_verb_is_documented(self):
        """The direction that goes wrong next: a verb nobody can discover."""
        undocumented = sorted(routed_verbs() - documented_verbs())
        assert undocumented == [], (
            f'main() routes {undocumented} and --help never mentions them')

    def test_a_documented_verb_is_not_answered_with_unknown_command(self, capsys):
        """Proven by running the router, not by reading its source.

        Each verb gets `--help`, which every family answers without doing work.
        The assertion is narrow on purpose — the exit code differs per family
        (an installer's plan is 0, `_usage()` is 2) and pinning those here would
        duplicate each family's own tests. What must never appear is the
        router's own miss.
        """
        for verb in sorted(documented_verbs()):
            capsys.readouterr()
            cli.main([verb, '--help'])
            out = capsys.readouterr()
            assert 'unknown command' not in (out.out + out.err), (
                f'main() answered documented verb {verb!r} with '
                f'"unknown command"')

    def test_the_docstring_names_no_scene_surgery(self):
        """The specific corpse this story buried, named so it stays buried."""
        doc = (cli.__doc__ or '').lower()
        for gone in ('.tscn', '.tres', 'scene-diff', 'autoloads', 'tilemap',
                     'sub_resource', 'canonicalize', 'reparent'):
            assert gone not in doc, f'--help still describes {gone!r}'

    def test_an_unknown_command_still_exits_2(self, capsys):
        """Rule 6: the exit codes are contract. Do not tidy them."""
        assert cli.main(['nonsense-verb']) == 2
        assert 'unknown command' in capsys.readouterr().err

    def test_help_asked_for_exits_0(self, capsys):
        for flag in ('-h', '--help', 'help'):
            assert cli.main([flag]) == 0
            assert capsys.readouterr().out.strip()

    def test_no_arguments_is_usage_not_help(self):
        assert cli.main([]) == 2
