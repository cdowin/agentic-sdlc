"""test_verify_main.py — the verb: three rungs, each a make target, and the
exit codes.

Every case runs against a scratch repo with a REAL Makefile whose recipes
touch sentinel files, because the claims worth attacking here are all about
whether something ran:

  * `--story` runs the story target and NOTHING wider — proven by the
    sentinel the story target writes and the absence of the ones the other
    two write, not by an exit code of 0, which is what a run of nothing also
    produces;
  * `--plan` runs NOTHING — proven by a ladder whose every target would
    create a sentinel, then asserting none exists;
  * a rung the section does not declare, a retired `narrow` table, or no
    section at all is exit 2 and runs nothing — never the rung above.

The verb reads no diff any more: the story rung is a target, so the fixture
needs a `.git` for `repo_root` and no history at all.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT
from support.pm import with_flow

from agentic_sdlc import cli
from agentic_sdlc.repo.verify import main as verb
from agentic_sdlc.repo.verify import rules

MAKEFILE = """\
story:
\t@touch story.ran

feature:
\t@touch feature.ran

milestone:
\t@touch milestone.ran

boom:
\t@exit 3
"""

LADDER = 'feature   = "make feature"\nmilestone = "make milestone"\n'
STORY_RULE = 'story     = "make story"\n'
NARROW_TABLE = '[[verify.narrow]]\npaths = "src/**"\nrun   = "make story"\n'
ALL_RUNGS = ('story', 'feature', 'milestone')
FLAGS = ('--story', '--feature', '--milestone', '--plan', '--check')


# The sentinels are what the recipes WRITE, so they are ignored the way a real
# tree ignores `.gate-reports/`: a rung re-reads the state after its target and
# records nothing when the two disagree, and a gate's own leavings are not
# drift. Every case still proves the run by the file on disk.
SENTINELS = '*.ran\n'

# A PM tree, because `verify` records where one already IS and refuses to mint
# one (a verb that runs a make target has no business creating `pm/`). Empty:
# git lists no empty directory, so it is not in the state either.
ROADMAP = 'pm/roadmap'
LEDGER = f'{ROADMAP}/ledger.jsonl'


class Repo:
    """A scratch repo with a Makefile, a devkit.toml and a file or two.

    cwd'd into, because `core.project.repo_root()` answers from the cwd and is
    `lru_cache`d — the caches are cleared on entry and exit, the way
    `support.pm.run_cli` does, since production never moves the cwd mid-run and
    every case here does.
    """

    def __init__(self, verify: str | None, files: dict[str, str] | None = None,
                 makefile: str | None = MAKEFILE):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / 'repo'
        self.root.mkdir()
        # RESOLVED: macOS's tempdir is a symlink (`/var` -> `/private/var`),
        # and a sentinel looked for through the other spelling is never seen.
        self.root = self.root.resolve()
        if makefile is not None:
            (self.root / 'Makefile').write_text(makefile, encoding='utf-8')
        (self.root / ROADMAP).mkdir(parents=True, exist_ok=True)
        payload = dict(files or {'src/a.py': 'x\n'})
        payload.setdefault('.gitignore', '')
        payload['.gitignore'] += SENTINELS
        for rel, body in payload.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        if verify is not None:
            # THROUGH `with_flow`: `--plan` reads the building milestone's
            # ledger through `pm.vocabulary`, which has no fallback behind
            # `[pm.states.*]` and swallows every failure as "unknown".
            (self.root / 'devkit.toml').write_text(
                with_flow(f'[verify]\n{verify}'), encoding='utf-8')
        (self.root / '.git').mkdir(exist_ok=True)  # a MARKER: repo_root walks for it

    def ran(self, name: str) -> bool:
        return (self.root / f'{name}.ran').exists()

    def ran_any(self) -> list[str]:
        return [name for name in ALL_RUNGS if self.ran(name)]

    def __enter__(self):
        self._previous = Path.cwd()
        os.chdir(self.root)
        _clear_caches()
        return self

    def __exit__(self, *exc):
        os.chdir(self._previous)
        _clear_caches()
        self._tmp.cleanup()
        return False


def _clear_caches() -> None:
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()


def run(*argv: str) -> tuple[int, str]:
    """The verb through the REAL cli route, so the config read is the shipped one."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = cli.main(['verify', *argv])
    return code, buf.getvalue()


class AConfigProblemIsExitTwoAndNeverAWiderRun(unittest.TestCase):
    """A malformed, retired or absent `[verify]` must not degrade into a run."""

    def test_every_flag_exits_2_when_the_section_is_absent(self):
        # A `--plan` that prints nothing and exits 0 is the same lie as a
        # `--story` that runs nothing and exits 0.
        with Repo(None) as repo:
            for flag in FLAGS:
                with self.subTest(flag=flag):
                    code, out = run(flag)
                    self.assertEqual(2, code)
                    self.assertIn('[verify]', out)
            self.assertEqual([], repo.ran_any())

    def test_a_retired_narrow_table_is_refused_by_name_on_every_flag(self):
        # The consumer-visible edge of this change: a devkit.toml still
        # carrying the path-selection tables is told what replaced them.
        with Repo(LADDER + STORY_RULE + NARROW_TABLE) as repo:
            for flag in FLAGS:
                with self.subTest(flag=flag):
                    code, out = run(flag)
                    self.assertEqual(2, code)
                    self.assertIn('[verify] narrow is retired', out)
                    self.assertIn('story = "make <target>"', out)
            self.assertEqual([], repo.ran_any())

    def test_a_malformed_rung_is_2_through_the_real_cli(self):
        with Repo('milestone = "make check test"\n' + STORY_RULE) as repo:
            self.assertEqual(2, run('--check')[0])
            self.assertEqual(2, run('--story')[0])
            self.assertEqual([], repo.ran_any())


class PlanRunsNothing(unittest.TestCase):

    def test_a_plan_over_a_ladder_whose_targets_write_creates_no_sentinel(self):
        with Repo(LADDER + STORY_RULE) as repo:
            code, out = run('--plan')
            self.assertEqual(0, code)
            self.assertEqual([], repo.ran_any())
        for name in ALL_RUNGS:
            self.assertIn(f'make {name}', out,
                          'it printed the command it did not run')

    def test_an_undeclared_rung_is_printed_as_not_configured(self):
        with Repo('milestone = "make milestone"\n') as repo:
            code, out = run('--plan')
            self.assertEqual(0, code)
            self.assertEqual([], repo.ran_any())
        self.assertIn('story      (not configured) — --story exits 2', out)
        self.assertIn('feature    (not configured)', out)


class TheRatioIsMeasuredOrUnknown(unittest.TestCase):
    """A fabricated ratio is worse than no ratio, because it gets quoted.

    `TREE` is read by `tests/test_fixture_flows.py`, which replays this
    fixture's builder — the name is a reference, not only a label.
    """

    TREE = {
        'src/a.py': 'x\n',
        'pm/roadmap/0.1/milestone.md':
            '---\nid: "0.1"\nname: D\nstatus: building\nbranch: milestone/0.1\n'
            '---\n\nbody\n',
    }

    def _with_ledger(self, *rows: dict) -> str:
        return ''.join(json.dumps(row, separators=(',', ':')) + '\n'
                       for row in rows)

    def test_a_cost_that_cannot_be_read_is_the_word_unknown_and_never_a_guess(self):
        for label, ledger in (
                ('no gate rows at all', None),
                # A row with no `duration_ms` is not a cost: reading `verdict`
                # and assuming a duration is how a made-up number gets quoted.
                ('a row with no duration', self._with_ledger(
                    {'ts': '2026-09-05T10:00:00Z', 'kind': 'gate',
                     'gate': 'milestone', 'verdict': 'SKIP'}))):
            tree = dict(self.TREE)
            if ledger is not None:
                tree['pm/roadmap/ledger.jsonl'] = ledger
            with self.subTest(case=label):
                with Repo(LADDER + STORY_RULE, tree):
                    _, out = run('--plan')
                self.assertIn('unknown', out)
                ratio = out.split('ratio')[-1].split('\n')[0]
                self.assertNotIn('x —', ratio.replace('unknown', ''),
                                 'no ratio is invented where no rows exist')

    def test_a_roster_gate_with_no_cost_row_is_named_beside_the_measured_ones(self):
        """`[checks] all` names GATES and the ledger records what runs COST,
        and nothing had ever joined them — so a roster entry that never runs
        reads exactly like one that passes. This project has already paid for
        that: the toolkit is two pinned packages and each refuses a gate name
        it does not know.

        **All-missing is its own sentence, not silence.** A tree running its
        gates inside a composed `check` target has cost rows for the
        composition and none per gate, so naming each of them there would be a
        nag — but printing NOTHING is worse, because it is byte-identical to a
        roster fully measured. On this package's own tree the two namespaces do
        not overlap at all, so the suppression was permanent: `verify --plan`
        said nothing about five unmeasured gates, forever, and that silence
        read as "measured" (rule 4).
        """
        rows = self._with_ledger(
            {'ts': '2026-09-05T10:00:00Z', 'kind': 'gate', 'gate': 'doc',
             'verdict': 'PASS', 'duration_ms': 900})
        # (roster, is there a line, the word that says WHICH case it is)
        for roster, expect, says in (
                ('["doc", "pm"]', True, 'while the others have'),
                ('["doc"]', False, ''),                  # all measured
                ('["pm", "shell"]', True, 'two namespaces')):  # none measured
            with self.subTest(roster=roster):
                tree = dict(self.TREE)
                tree['pm/roadmap/ledger.jsonl'] = rows
                # The roster rides in the `[verify]` block Repo writes, since
                # that is the one devkit.toml this fixture produces.
                with Repo(LADDER + STORY_RULE
                          + f'\n[checks]\nall = {roster}\n', tree):
                    code, out = run('--plan')
                self.assertEqual(code, 0, out)
                self.assertEqual('unrun' in out, expect, out)
                if says:
                    self.assertIn(says, out)

    def test_a_roster_this_cannot_read_is_reported_rather_than_silent(self):
        # `except Exception: return []` swallowed a MALFORMED roster too, so a
        # `[checks] all` that `check all` refuses at exit 2 read here as a
        # clean plan. A bare string is the shape `core.config` exists to catch.
        tree = dict(self.TREE)
        with Repo(LADDER + STORY_RULE + '\n[checks]\nall = "doc"\n', tree):
            code, out = run('--plan')
        self.assertEqual(code, 0, out)
        self.assertIn('unrun', out)
        self.assertIn('could not be read', out)
        self.assertIn('check all', out)

    def test_with_gate_rows_the_plan_prints_the_measured_numbers(self):
        # The counterpart to the case above: without this, an implementation
        # that answered `unknown` unconditionally would pass every other
        # assertion in this class.
        tree = dict(self.TREE)
        tree['pm/roadmap/ledger.jsonl'] = self._with_ledger(
            {'ts': '2026-09-05T10:00:00Z', 'kind': 'gate', 'gate': 'story',
             'verdict': 'PASS', 'duration_ms': 900, 'census': 5},
            {'ts': '2026-09-05T10:01:00Z', 'kind': 'gate', 'gate': 'milestone',
             'verdict': 'PASS', 'duration_ms': 154_000, 'census': 182},
        )
        with Repo(LADDER + STORY_RULE, tree):
            _, out = run('--plan')
        self.assertIn('900 ms (census 5, PASS)', out)
        self.assertIn('154000 ms (census 182, PASS)', out)
        self.assertIn('171x', out, 'the ratio is the measurement, not a guess')


class Check(unittest.TestCase):
    """`--check` holds each rung's target to the Makefile, and prints its
    census on the pass too."""

    def test_a_valid_ladder_exits_0_and_prints_its_census(self):
        with Repo(LADDER + STORY_RULE) as repo:
            code, out = run('--check')
            self.assertEqual([], repo.ran_any(), '--check runs nothing')
        self.assertEqual(0, code)
        self.assertIn('[verify:check] PASS — 3 of 3 rung(s) declared', out)
        with Repo(LADDER):
            code, out = run('--check')
        self.assertEqual(0, code)
        self.assertIn('2 of 3 rung(s) declared', out,
                      'an undeclared rung is counted, not invented')

    def test_a_target_no_makefile_declares_is_a_finding_naming_the_rung(self):
        with Repo(LADDER + 'story = "make absent-target"\n'):
            code, out = run('--check')
        self.assertEqual(1, code, 'a finding about the TREE is 1, not 2')
        self.assertIn('[verify] story', out)
        self.assertIn('absent-target', out)
        self.assertIn('[verify:check] FAIL — 1 finding(s)', out)

    def test_no_makefile_at_all_is_a_finding_not_a_pass(self):
        with Repo(LADDER + STORY_RULE, makefile=None):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('no Makefile', out)


class TheRefusalMatrix(unittest.TestCase):
    """argv is an input surface (SDLC.md §5), and this verb owns that grammar.
    The four flags the path-selection engine took are refused with it."""

    REFUSED = (
        (),                                     # no mode: never a default
        ('--no-cache',),                        # a rung flag is not a mode
        ('--plan', '--no-cache'),               # …and --plan runs no rung
        ('--check', '--no-cache'),
        ('--story', '--plan'),                  # two modes
        ('--story', '--feature', '--milestone'),
        ('--story', '--story'),
        ('--story', '--ref', 'HEAD'),           # the verb reads no diff
        ('--story', '--to', 'HEAD'),
        ('--story', '--ignore', 'pm/roadmap'),
        ('--changed',),                         # the old alias
        ('--nope',),                            # never silently ignored
        ('--story=1',),
        ('positional',),
        ('--story', 'extra'),
    )

    def test_each_exits_2_and_runs_nothing(self):
        with Repo(LADDER + STORY_RULE) as repo:
            for argv in self.REFUSED:
                with self.subTest(argv=argv):
                    code, out = run(*argv)
                    self.assertEqual(2, code, out)
                    self.assertIn('usage:', out)
            self.assertEqual([], repo.ran_any())

    def test_help_never_touches_the_config(self):
        with Repo(None):
            code, out = run('--help')
        self.assertEqual(0, code)
        self.assertIn('--story', out)

