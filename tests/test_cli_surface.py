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

## And the same question asked of the EXIT CODES

Through 0.2.0 every case here asked whether a help text NAMES what ships. None
asked whether what it names is what happens, and the gap cost a consumer a
day: `check budget --help` said a tier with no `gate` row was a finding, "never
a pass", and the code exited 0 for it. The claim had arrived in a docs-only
commit that compressed the docstring to one screen; nothing read the sentence
and the exit code together, so it outlived the behaviour by a milestone and the
consumer had to run the binary to learn the contract.

So the second half of this module reads both. It enumerates every `--help` this
package prints, extracts the exit codes each one CLAIMS, and — for the claims a
temp tree can realise — runs the condition and compares. The expected code is
never written down here: it is read out of the help text at run time, so the
pair under test is the documentation and the binary rather than the
documentation and a second copy of itself.
"""
from __future__ import annotations

import ast
import contextlib
import dataclasses
import functools
import inspect
import io
import re
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

# The budget fixture, not a second one (hard rule 10): `tree()` writes a
# marked tree with a ledger and a devkit.toml and calls the gate in it, which
# is exactly what a probe here needs. A parallel copy would drift from the
# module that actually gates `check budget`.
from test_check_budget import BUDGET, check as budget_check, gate_row, tree

import pytest

from agentic_sdlc import cli

# Every `agentic-sdlc <verb>` line in the docstring, first token only. The
# docstring also shows sub-verbs (`pm story …`, `check doc`) — those are the
# owning module's surface, and this file is about what `main()` routes.
_INVOCATION = re.compile(r'^\s*agentic-sdlc ([a-z][a-z0-9-]*)', re.M)


# Rule 11's read side, package-wide. The floor is what the tree holds today:
# `pm cli` (6) plus `lesson show` (1). It is a FLOOR, so a verb that stops
# naming its columns reddens wherever it lives.
NAMES_COLUMNS = 'columns IN ORDER:'
READ_VERBS_NAMING_COLUMNS = 7


def _package_sources() -> list[tuple[str, str]]:
    """(relative path, source text) for every module the verbs live in."""
    root = Path(__file__).resolve().parents[1] / 'src/agentic_sdlc/repo'
    found = [(path.name, path.read_text(encoding='utf-8'))
             for path in sorted(root.rglob('*.py'))]
    assert len(found) > 10, 'the census lost the package'
    return found


def documented_verbs() -> set[str]:
    return set(_INVOCATION.findall(cli.__doc__ or ''))


# The rosters `main()` resolves rather than spells: `install_commands()` reads
# the installer's `PLANS`, `conveyor_verbs()` the driver's `OPERATIONS`.
# `CONVEYOR_VERBS` is a LAZY tuple — iterating it yields nothing, which is why
# the branch is named here by the function behind it rather than read as a
# value.
_ROSTER_CALLS = {'install_commands': cli.install_commands,
                 'conveyor_verbs': cli.conveyor_verbs}
_ROSTER_NAMES = {'CONVEYOR_VERBS': cli.conveyor_verbs}
_VERB = re.compile(r'^[a-z][a-z0-9-]*$')


def _resolve(node: ast.expr) -> tuple[set[str], list[str]]:
    """(the verbs this comparator routes, the shapes that could not be read)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}, []
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        verbs: set[str] = set()
        unread: list[str] = []
        for element in node.elts:
            found, missed = _resolve(element)
            verbs |= found
            unread += missed
        return verbs, unread
    if isinstance(node, ast.Name):
        if node.id in _ROSTER_NAMES:
            return set(_ROSTER_NAMES[node.id]()), []
        value = getattr(cli, node.id, None)
        if isinstance(value, str):
            return {value}, []
        return set(), [f'cli.{node.id}']
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _ROSTER_CALLS):
        return set(_ROSTER_CALLS[node.func.id]()), []
    return set(), [ast.dump(node)[:60]]


def routed_verbs() -> set[str]:
    """What `main()` dispatches, read off the router's own BRANCHES.

    This used to be a hand-written set beside a docstring claiming another test
    kept it honest. It did not: that test walks `documented_verbs()`, so a verb
    missing from BOTH is invisible to both. Finding E2 caught `version` that
    way once, by hand. 0.6.0 shipped `dispatch` and `changelog` routed and
    undocumented, and every test stayed green — the same class, twice, in the
    milestone whose northstar is that a gate which cannot fail is not a gate.

    So the router is READ. Every `cmd == X` / `cmd in X` comparison in `main()`
    contributes its verbs, and a comparator shape this cannot resolve FAILS by
    name rather than dropping out silently: an unreadable branch is the defect,
    not an exemption from it. Flag spellings (`-V`, `--version`) are not verbs
    and are filtered by the same grammar `--help` lines are read with.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(cli.main)))
    verbs: set[str] = set()
    unread: list[str] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name)
                and node.left.id == 'cmd'):
            for comparator in node.comparators:
                found, missed = _resolve(comparator)
                verbs |= found
                unread += missed
    assert not unread, (
        f'routed_verbs() cannot read {len(unread)} branch(es) of cli.main(): '
        f'{unread}; teach it the shape rather than letting a verb go unseen')
    assert len(verbs) > 5, f'the router census collapsed to {sorted(verbs)}'
    return {verb for verb in verbs if _VERB.match(verb)}


# --- the exit-code surface, enumerated the same way the verbs are ------------

# `check` is a FAMILY, not a surface: `check --help` reads `--help` as a gate
# name and exits 2 naming the roster. Its menu is the root docstring's "Static
# gates" block, and every gate answers `check <gate> --help` for itself, which
# is what the census below walks.
FAMILY_VERBS = frozenset({'check'})


def help_surfaces() -> dict[str, tuple[str, ...]]:
    """{what a reader types: the argv that prints it}.

    Derived from the same two rosters `routed_verbs()` asks, plus one entry per
    gate in `KNOWN_GATES`. A new verb or a new gate joins this census the day it
    ships, with nothing to update here.
    """
    surfaces = {'agentic-sdlc --help': ('--help',)}
    for verb in sorted(routed_verbs() - FAMILY_VERBS):
        surfaces[f'{verb} --help'] = (verb, '--help')
    for gate in cli.KNOWN_GATES:
        surfaces[f'check {gate} --help'] = ('check', gate, '--help')
    return surfaces


@functools.cache
def help_corpus() -> dict[str, tuple[int, str]]:
    """{surface: (exit code, everything it printed)}, from RUNNING each one.

    Off the run rather than off `__doc__`, because two of the biggest surfaces
    print a module-level `USAGE` constant instead — a corpus built from
    docstrings would silently skip `pm` and `gates-extra`, which is this
    module's own cardinal sin.

    Cached, and every caller reads it BEFORE entering a temp tree: a `--help`
    is answered from constants, but building the corpus inside somebody's
    fixture would make the cache hold whatever that tree said.
    """
    corpus: dict[str, tuple[int, str]] = {}
    for name, argv in help_surfaces().items():
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        corpus[name] = (code, out.getvalue() + err.getvalue())
    return corpus


# --- reading the exit codes a help text CLAIMS -------------------------------

# Rule 6's closed vocabulary; a help naming anything else documents a code the
# router cannot produce.
CONTRACT_CODES = frozenset({0, 1, 2})

# The sentence a surface states its exit codes in — `Exit codes: …` or `Exit: …`
# — to the end of its paragraph. Both spellings are in the shipped corpus.
# Case-INSENSITIVE, and both spellings this package actually uses. `pm --help`
# writes `EXIT CODE:` and the reader could not see it, so eleven surfaces that
# DO state a contract were counted as stating none (review X3) — a census that
# reported 5 of 21 and looked like a fact about the help rather than about the
# regex reading it.
_EXIT_CONTRACT = re.compile(
    r'(?mi)^[ \t]*Exit(?:\s+codes?)?:(?P<body>.*(?:\n(?![ \t]*\n).*)*)')

# A code in CLAIM POSITION: opening the contract, or introduced by a clause
# separator. `verify`'s "A target's own exit 2 is reported as 1" is prose
# INSIDE a clause and opens none, which is why a digit has to be introduced
# rather than merely present.
# A PERIOD ends a clause too, and a contract written `0 pass. 1 findings.`
# hid every code after the first from the rule-6 guard (review X6).
_CODE_MARK = re.compile(r'(?:\A|[;|·,.]\s*)(?P<code>\d+)(?=[\s=])')


def exit_contract(text: str) -> str:
    """The exit-code sentence in `text`, whitespace-normalised, or ''.

    Normalised because the sentence wraps: a clause quoted in CLAIMS would
    otherwise have to carry whichever line break the source happens to have.
    """
    found = _EXIT_CONTRACT.search(text)
    return ' '.join(found.group('body').split()) if found else ''


def claimed_codes(contract: str) -> list[int]:
    """Every exit code the contract opens a clause with, in order."""
    return [int(m.group('code')) for m in _CODE_MARK.finditer(contract)]


def claimed_code(contract: str, clause: str) -> int:
    """The exit code the contract states FOR `clause` — the one opening the
    clause the phrase sits in. Read out of the help, never restated in a test.
    """
    assert clause in contract, (
        f'the help no longer says {clause!r}. Its exit contract now reads:\n'
        f'  {contract}\n'
        f'A reworded claim needs its probe looked at, which is why the clause '
        f'is quoted rather than paraphrased.')
    at = contract.index(clause)
    opened = [m for m in _CODE_MARK.finditer(contract) if m.end() <= at]
    assert opened, (
        f'{clause!r} sits in front of every exit code in {contract!r}, so the '
        f'help states no code for it')
    return int(opened[-1].group('code'))


# --- the claims a temp tree can realise --------------------------------------
@dataclasses.dataclass(frozen=True)
class ExitClaim:
    """One clause of one `--help`, and the cheapest way to make it come true.

    No expected code: it is read out of the live help text, so what is compared
    is the documentation against the binary.
    """
    surface: str
    says: str
    probe: Callable[[Path], int]


def _budget_unmeasured(tmp_path: Path) -> int:
    """`integration` is declared and has no `gate` row anywhere in the ledger."""
    with tree(tmp_path, [gate_row('unit', 1_000)], BUDGET):
        return budget_check()[0]


def _budget_not_graded(tmp_path: Path) -> int:
    """Both tiers have a row, and the newest `unit` one ended FAIL."""
    with tree(tmp_path, [gate_row('unit', 1_000, verdict='FAIL'),
                         gate_row('integration', 1_000)], BUDGET):
        return budget_check()[0]


def _gates_extra_silent(tmp_path: Path) -> int:
    """A tree that declares no `[gates]` section at all."""
    with tree(tmp_path, []):
        return cli.main(['gates-extra'])


def _gates_extra_unusable(tmp_path: Path) -> int:
    """`extra` holding a number, which is not a roster of make targets."""
    with tree(tmp_path, [], '[gates]\nextra = 5\n'):
        return cli.main(['gates-extra'])


# Two surfaces, and both directions of each: a clause the help files under 0
# and one it files under 1 or 2. `check budget` is the finding this section was
# written for; `gates-extra` is here because one surface proves a reader, two
# prove it is not shaped around one docstring.
CLAIMS = (
    ExitClaim('check budget --help',
              'a declared tier with no row is reported as unmeasured',
              _budget_unmeasured),
    ExitClaim('check budget --help', 'not graded', _budget_not_graded),
    ExitClaim('gates-extra --help', 'printed (possibly nothing)',
              _gates_extra_silent),
    ExitClaim('gates-extra --help', 'the value is not a usable roster',
              _gates_extra_unusable),
)


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

    def test_every_help_surface_asked_for_exits_0_and_prints_something(self):
        """The same claim, over the whole surface rather than the root.

        Widened rather than duplicated: the root was the only surface asked,
        and a family whose `--help` exits 2 or prints nothing is a menu the
        reader cannot get to. `check` itself is excluded and why is at
        FAMILY_VERBS.
        """
        for name, (code, text) in sorted(help_corpus().items()):
            assert code == 0, f'`{name}` exited {code}: {text.strip()[:200]}'
            assert text.strip(), f'`{name}` printed nothing'

    def test_no_arguments_is_usage_not_help(self):
        assert cli.main([]) == 2


class TestAReadVerbNamesItsColumns:
    """0.4.0/the-read-verbs-compose.

    The rule is *read verbs emit lines; composition is the shell's job* — and
    it only works if a reader can see the columns without opening the source.
    So the column list exists THREE times: the rows, `--json`'s keys, and the
    `--help` line. The first two are one tuple zipped two ways and cannot
    diverge; the third is prose and can, which is what these cases hold.

    The defect that produced the rule: `pm list` emitted no `name`, so
    `pm list | grep "<a name>"` returned nothing, and the agent that tried it
    concluded the tool could not search and proposed `pm list --grep`. The
    capability was there; the payload made it look absent.
    """

    def columns_in_help(self, kind: str) -> tuple[str, ...]:
        """The column names off the `pm --help` line for one `--kind`, parsed
        rather than restated — a hand-written roster here goes stale exactly
        the way the thing it guards does."""
        from agentic_sdlc.repo.pm import cli as pm_cli
        after = (pm_cli.USAGE or '').split('columns IN ORDER:')
        # `>= 3`, not `== 3`: the ship criterion says EVERY read verb names its
        # columns, so an exact count reddened on its own fix — a case that
        # punishes the criterion being met is worse than no case (review M1).
        assert len(after) >= 3, 'the help stopped naming its columns in order'
        which = after[1] if kind == 'story' else after[2]
        return tuple(which.strip().split('\n')[0].split())

    @pytest.mark.parametrize('kind', ['story', 'milestone'])
    def test_the_help_names_the_columns_the_rows_carry(self, kind):
        from agentic_sdlc.repo.pm import cli as pm_cli
        assert self.columns_in_help(kind) == pm_cli.LIST_COLUMNS[kind]

    def test_the_help_states_the_composition_rule(self):
        from agentic_sdlc.repo.pm import cli as pm_cli
        said = (pm_cli.USAGE or '').lower()
        assert 'composition is the shell' in said
        assert 'is a column, not a verb' in said or 'a column' in said

    def test_no_filter_flag_was_added(self):
        """The rule's cheaper half: every filter flag not added is a flag not
        documented, not tested and not kept in sync with the fields. This
        feature adds a COLUMN and a serialisation, and the flag roster is the
        one it inherited."""
        from agentic_sdlc.repo.pm import cli as pm_cli
        with_json = {'--status', '--owner', '--milestone', '--kind',
                     '--category'}
        said = pm_cli.USAGE or ''
        # Everything from the first `list` line to the next verb: BOTH list
        # forms, since `--kind` only appears on the second.
        listing = said[said.index('  list '):said.index('  ready-for')]
        found = {tok for tok in re.findall(r'--[a-z-]+', listing)}
        assert found - {'--json'} == with_json, sorted(found)


class TestTheSurfaceSaysTelemetry:
    """0.4.0/the-surface-says-telemetry. Not a missing column — a MISSING WORD.

    `pm --help`'s ledger lines said what the verbs do and never what they are,
    so an agent asked for "telemetry — phasing, timings, token use, tool calls"
    grepped the package for that word, found five design documents and a
    vendored lexer, and hand-wrote a markdown table over a package that ships
    `pm ledger report`.
    """

    LEDGER_VOCABULARY = ('telemetry', 'spend', 'cost', 'tokens', 'tool calls')

    def test_the_help_names_the_ledger_in_the_words_people_search_for(self):
        from agentic_sdlc.repo.pm import cli as pm_cli
        said = (pm_cli.USAGE or '').lower()
        for word in self.LEDGER_VOCABULARY:
            assert word in said, f'`pm --help` never says {word!r}'

    def test_the_help_names_the_grainless_ledger_by_path(self):
        """Rule 11: the second home is where a row goes when nobody could
        attribute it, and a reader standing at `--help` must not have to find
        that out from a runtime message."""
        from agentic_sdlc.repo.pm import cli as pm_cli
        assert 'ledger.jsonl' in (pm_cli.USAGE or '')

    ROUTED_AT_0_4_0 = 14

    # Every verb routed SINCE that criterion was met, one line per decision.
    # The number stays 14 because it is a claim about a milestone that shipped;
    # what a later verb has to do is name itself here, which is the argument it
    # would otherwise never have to make.
    ROUTED_SINCE = {
        # 0.5.0/ft-a-lesson-is-a-row-bound-to-a-grain: a lesson is written by
        # whoever just learned it, not as part of moving a grain, so it is not
        # a `pm` subcommand.
        'lesson',
        # 0.6.0/ft-the-dispatch-carries-the-contract: it renders a preamble at
        # the moment a dispatch begins and moves no grain, so it is neither a
        # `pm` subcommand nor a belt.
        'dispatch',
        # 0.6.0/ft-the-changelog-is-a-field-and-a-verb: `CHANGELOG.md` retired
        # into `changelog:` on the grain, and rendering those in `order:` is a
        # read over the whole tree rather than a read of one grain.
        'changelog',
    }

    def test_this_feature_added_no_verb(self):
        """The ship criterion, asserted. Review M2: `documented == routed` is
        the conjunction of the two cases above and would pass a verb that was
        added AND documented — it proved the wrong thing. The COUNT is what the
        criterion actually claims."""
        assert len(routed_verbs()) == self.ROUTED_AT_0_4_0 + len(
            self.ROUTED_SINCE), sorted(routed_verbs())
        assert self.ROUTED_SINCE <= routed_verbs(), (
            f'{sorted(self.ROUTED_SINCE - routed_verbs())} is written down as '
            f'a verb this package added and the router does not dispatch it')

    def test_every_read_verb_names_its_columns(self):
        """Review M1: the criterion says EVERY read verb, and `next` and
        `roadmap` both emit tab-separated rows. Asserted as a count against the
        verbs that emit them, so a fifth such verb has to name its columns too.
        Bare `order` was one of them until 0.4.0 retired the verb into
        `pm add`; reading the plan is `pm roadmap`.

        The census read `pm_cli.USAGE` alone, so a read verb outside the `pm`
        family — `lesson show` was the first — sat outside it entirely (N3).
        It is the package's SOURCE now, so wherever the next one lands it is
        counted, and a verb that drops its columns line goes red anywhere."""
        from agentic_sdlc.repo.pm import cli as pm_cli
        said = pm_cli.USAGE or ''
        assert said.count(NAMES_COLUMNS) >= 4, said.count(NAMES_COLUMNS)
        found = {rel: text.count(NAMES_COLUMNS)
                 for rel, text in _package_sources()
                 if NAMES_COLUMNS in text}
        assert sum(found.values()) >= READ_VERBS_NAMING_COLUMNS, found
        assert len(found) > 1, (
            f'{sorted(found)} — every declaration is in one module again, so '
            f'this is `pm_cli.USAGE` with extra steps')

    def test_the_clock_help_names_its_columns_in_the_order_it_prints_them(self):
        """Rule 11's read side for `ledger report`'s clock: the two column
        tuples the block renders from, in order, in `--help`, so a total is
        `… | awk` and never a flag this verb grew. `CLOCK_COLUMNS` shipped
        carrying that claim in a comment and referenced by nothing."""
        from agentic_sdlc.repo.pm import cli as pm_cli, report
        entry = (pm_cli.USAGE or '').split('THE TELEMETRY REPORT')[-1]
        flat = ' '.join(entry.split())
        for columns in (report.CLOCK_COLUMNS, report.ACTOR_COLUMNS):
            assert ' '.join(columns) in flat, (columns, flat)
class TestTheDocumentedExitCodeIsTheOneThatRuns:
    """No `--help` documents an exit code the code does not return."""

    def test_the_exit_contract_census_is_not_zero(self):
        """Hard rule 4: a gate scanning 0 files FAILS and says so.

        The reader below is a regex over prose, and the way it dies is
        silently — one reworded `Exit codes:` line and it matches nothing,
        passes everything, and says PASS over a corpus it never read. So the
        census is asserted before anything is graded, and the surfaces the
        CLAIMS name are asserted to be inside it.
        """
        corpus = help_corpus()
        assert corpus, 'help_surfaces() enumerated nothing to read'
        with_contract = sorted(name for name, (_code, text) in corpus.items()
                               if exit_contract(text))
        assert with_contract, (
            f'the exit-contract reader matched 0 of {len(corpus)} `--help` '
            f'surfaces. Either every surface stopped stating its exit codes, '
            f'or _EXIT_CONTRACT stopped matching the sentence they state them '
            f'in — and a reader with a zero census that passes is the sin '
            f'this module exists to catch.')
        unread = sorted({c.surface for c in CLAIMS} - set(with_contract))
        assert unread == [], (
            f'{unread} carry a claim in CLAIMS and no exit contract the '
            f'reader can find; every claim below would be graded against '
            f'nothing')

    def test_no_help_names_an_exit_code_outside_the_contract(self):
        """Rule 6: 0 pass, 1 findings, 2 usage or config, and nothing else.

        A fourth code in a help text is a code the router has no branch for —
        the same phantom as a menu entry with no verb behind it, one column
        over.
        """
        strays = {}
        for name, (_code, text) in sorted(help_corpus().items()):
            named = set(claimed_codes(exit_contract(text)))
            if named - CONTRACT_CODES:
                strays[name] = sorted(named - CONTRACT_CODES)
        assert strays == {}, (
            f'{strays} document exit codes outside {sorted(CONTRACT_CODES)}')

    @pytest.mark.parametrize(
        'claim', CLAIMS, ids=[f'{c.surface}::{c.says}'[:60] for c in CLAIMS])
    def test_the_documented_exit_code_is_the_one_the_code_returns(
            self, claim, tmp_path):
        """The whole point: the sentence and the exit code, read together.

        `check budget --help` said an unmeasured tier was a finding "never a
        pass" while `run()` returned 0 for it, and every case in this suite
        agreed with one side or the other without ever comparing them.
        """
        # The corpus is read BEFORE the probe builds a tree and chdirs into it.
        contract = exit_contract(help_corpus()[claim.surface][1])
        documented = claimed_code(contract, claim.says)
        actual = claim.probe(tmp_path)
        assert actual == documented, (
            f'`{claim.surface}` documents exit {documented} for '
            f'{claim.says!r} and the code returned {actual}. One of the two is '
            f'wrong, and a consumer reads the help.')

    def test_a_help_that_files_a_condition_under_the_wrong_code_is_caught(self):
        """The deliberately-broken probe: this reader is a gate, so it is shown
        FAILING on the drift class it exists for.

        The text below is the shape `check budget` shipped through 0.2.0 — the
        unmeasured condition filed under 1. Against it, `_budget_unmeasured`'s
        real 0 is a mismatch the case above would report, rather than the
        agreement it reports today. The third assertion is the other way this
        reader can rot: a clause quietly reworded out of the help must be a
        loud failure, never a claim that silently stops being checked.
        """
        planted = exit_contract(
            'Exit codes: 0 every declared tier is graded; 1 a tier is over, '
            'under its floor, or unmeasured; 2 usage or config.\n')
        assert claimed_codes(planted) == [0, 1, 2], planted
        assert claimed_code(planted, 'every declared tier is graded') == 0
        assert claimed_code(planted, 'unmeasured') == 1, (
            'the reader must attribute a clause to the code that OPENS it, or '
            'a condition filed under the wrong one reads as agreement')
        with pytest.raises(AssertionError, match='no longer says'):
            claimed_code(planted, 'reported as unmeasured')


# `pm --help` is the pm module's own surface rather than one `main()` routes to,
# and it is here for the reason the rest of this file exists: it is the menu a
# reader is handed, and what it leaves out is what they do not know.
#
# THIS FAILS UNTIL THE USAGE REPLACEMENT IS APPLIED. The builder that wrote it
# does not own `src/agentic_sdlc/repo/pm/cli.py`, so the text ships in the
# report and the marker below disarms itself the moment it lands — no XPASS to
# chase, nothing to remember.
_BELT_NAMED_IN_PM_HELP = 'close feature' in help_corpus()['pm --help'][1]


class TestTheHelpNamesTheBeltBesideThePathThatBypassesIt:

    @pytest.mark.xfail(not _BELT_NAMED_IN_PM_HELP, strict=True,
                       reason='pending: the `pm --help` USAGE replacement for '
                              '0.3.0/documented-behaviour-is-the-behaviour is '
                              'not applied yet')
    def test_the_feature_close_entry_names_close_feature_and_the_bypass(self):
        """Two ways to close a feature, and the shorter one skips the belt.

        `pm feature done <id> --review-record <path>` writes the status and
        stamps `reviewed:` in one go, skipping `close feature`'s `stories-done`
        and `findings-landed`. It is also the command every older consumer doc
        already contains, so a bump leaves the belt-skipping path as the
        well-trodden one — and nothing in the menu said the belt existed.
        """
        text = help_corpus()['pm --help'][1]
        entry = text.split('feature <done-state>', 1)[-1]
        entry = entry.split('\n  milestone ', 1)[0]
        for named in ('close feature', 'stories-done', 'findings-landed'):
            assert named in entry, (
                f'the `feature <done-state>` entry in `pm --help` never says '
                f'{named!r}:\n{entry}')
