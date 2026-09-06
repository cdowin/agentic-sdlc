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
import subprocess
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
        for rel, body in (files or {'src/a.py': 'x\n'}).items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        if verify is not None:
            # THROUGH `with_flow`: `--plan` reads the building milestone's
            # ledger through `pm.model`, which has no fallback behind
            # `[pm.states.*]` and swallows every failure as "unknown".
            (self.root / 'devkit.toml').write_text(
                with_flow(f'[verify]\n{verify}'), encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)

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


class TheRungs(unittest.TestCase):
    """Each flag runs exactly the target its rung names."""

    def test_each_rung_runs_its_own_target_and_nothing_wider(self):
        # Every sentinel assertion stays INSIDE the context manager: the
        # fixture's tempdir is removed on exit, and `.exists()` on a deleted
        # tree is False — which would make every "did it run" check pass by
        # never finding the file.
        for name in ALL_RUNGS:
            with self.subTest(rung=name), Repo(LADDER + STORY_RULE) as repo:
                code, out = run(f'--{name}')
                self.assertEqual(0, code, out)
                self.assertEqual([name], repo.ran_any(),
                                 f'--{name} runs its target and no other')
                self.assertIn(f'verify --{name}: make {name}', out)

    def test_a_failed_target_is_exit_1_with_the_targets_own_code_beside_it(self):
        with Repo(STORY_RULE + 'milestone = "make boom"\n'):
            code, out = run('--milestone')
        self.assertEqual(1, code, 'a failed verification is 1, never 2')
        self.assertIn('exit 2', out, "the target's own code is printed — make "
                                     'exits 2 on a failed recipe, which is '
                                     'exactly the code rule 6 reserves for '
                                     'config, so it must not be passed through')

    def test_a_rung_with_no_config_entry_is_named_and_exits_2(self):
        # Rule 4: `verify --story` with no `[verify] story` is never a pass,
        # and never the rung above it instead.
        for name in ('story', 'feature'):
            with self.subTest(rung=name), \
                    Repo('milestone = "make milestone"\n') as repo:
                code, out = run(f'--{name}')
                self.assertEqual(2, code, 'never a silent skip that reports '
                                          'success for a rung nobody ran')
                self.assertIn(f'[verify] declares no {name} rung', out)
                self.assertEqual([], repo.ran_any())


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


@contextlib.contextmanager
def _in_this_repo():
    """cwd'd into THIS checkout with the config caches cleared both ways —
    under xdist a worker's cwd is wherever the previous fixture left it."""
    previous = Path.cwd()
    os.chdir(REPO_ROOT)
    _clear_caches()
    try:
        yield
    finally:
        os.chdir(previous)
        _clear_caches()


class SelfHosting(unittest.TestCase):
    """This repo's OWN `[verify]` section, held to the tree it describes."""

    def test_verify_check_passes_on_this_tree(self):
        with _in_this_repo():
            code, out = run('--check')
        self.assertEqual(0, code, f'this repo self-hosts the ladder:\n{out}')
        self.assertIn('3 of 3 rung(s) declared', out)

    def test_the_story_rung_here_is_the_unit_tier(self):
        # CLAUDE.md's ladder row says `make unit`; the config is the fact.
        with _in_this_repo():
            ladder = rules.read(cli._verify_section())
            targets, _ = verb.make_targets(verb.repo_root())
        self.assertEqual('make unit', ladder.story)
        for name in rules.RUNGS:
            self.assertIn(rules.rung_target(ladder.rung(name)), targets)

    def test_the_cli_and_the_grammar_spell_the_section_once(self):
        self.assertEqual(rules.SECTION, cli.VERIFY_SECTION)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
