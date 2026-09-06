"""test_verify_main.py — the verb: the ladder, the fallback, the exit codes.

Every case runs against a REAL scratch git repo with a REAL Makefile whose
recipes touch sentinel files, because the two claims worth attacking here are
both about whether something ran:

  * `--plan` runs NOTHING — proven by a rule set whose `run` would create a
    sentinel, then asserting the file is absent. Not by patching a spawn and
    trusting the patch to be the only route to one.
  * a miss falls back to the widest rung and the wide command ACTUALLY RAN —
    proven by the sentinel the wide target writes, not by an exit code of 0,
    which is what a run of nothing also produces.

The grammar bans `;`, `>` and `$` in a `run`, so a sentinel cannot be written
with a redirect. That is not an obstacle to work around: it is the reason the
fixtures are make targets, which also makes `--check`'s "does this target
exist" question real rather than mocked.

Every fixture here spawns git and make, so a case that could be answered by
`rules.read` or `select.select` belongs in their files and not this one.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support.pm import with_flow

from agentic_sdlc import cli
from agentic_sdlc.repo.verify import main as verb
from agentic_sdlc.repo.verify import rules

MAKEFILE = """\
precommit:
\t@touch precommit.ran

milestone:
\t@touch milestone.ran

story:
\t@echo ran >> story.runs

boom:
\t@exit 3
"""

LADDER = 'feature   = "make precommit"\nmilestone = "make milestone"\n'
STORY_RULE = ('[[verify.narrow]]\n'
              'paths = "src/**"\n'
              'run   = "make story"\n')


def rule(paths: str, run: str) -> str:
    return f'[[verify.narrow]]\npaths = "{paths}"\nrun   = "{run}"\n'


class Repo:
    """A scratch git repo with a Makefile, a devkit.toml and some tracked files.

    cwd'd into, because `core.project.repo_root()` answers from the cwd and is
    `lru_cache`d — the caches are cleared on entry and exit, the way
    `support.pm.run_cli` does, since production never moves the cwd mid-run and
    every case here does.
    """

    def __init__(self, verify: str | None, files: dict[str, str] | None = None):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / 'repo'
        self.root.mkdir()
        # RESOLVED, because `git rev-parse --show-toplevel` answers with the
        # physical path and macOS's tempdir is a symlink (`/var` ->
        # `/private/var`). Left unresolved, every sentinel this fixture looks
        # for would be written one directory away from where it looked, and
        # every "did it run" assertion would pass by never seeing the file.
        self.root = self.root.resolve()
        (self.root / MAKEFILE_NAME).write_text(MAKEFILE, encoding='utf-8')
        for rel, body in (files or {'src/a.py': 'x\n', 'README.md': 'x\n'}).items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        if verify is not None:
            # THROUGH `with_flow`. `verify --plan` reads the building
            # milestone's ledger for the measured ratio, and that read goes
            # through `pm.model` — which has no fallback behind `[pm.states.*]`
            # and swallows every failure as "unknown" (verify/main.py:568). A
            # tree that declared no flow would therefore print `unknown` for a
            # config reason and pass the "no rows" case while silently gutting
            # the measured one. See tests/support/pm.py `with_flow`.
            (self.root / 'devkit.toml').write_text(
                with_flow(f'[verify]\n{verify}'), encoding='utf-8')
        self._git('init', '-q')
        self._git('add', '-A')
        self._git('-c', 'user.name=t', '-c', 'user.email=t@t.invalid',
                  '-c', 'commit.gpgsign=false', 'commit', '-qm', 'seed')

    def _git(self, *args: str) -> str:
        done = subprocess.run(['git', *args], cwd=self.root,
                              capture_output=True, text=True)
        assert done.returncode == 0, f'git {args}: {done.stderr}{done.stdout}'
        return done.stdout

    def edit(self, *rels: str) -> None:
        for rel in rels:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('a', encoding='utf-8') as handle:
                handle.write('# edited\n')

    def ran(self, name: str) -> bool:
        return (self.root / f'{name}.ran').exists()

    def runs(self, name: str) -> int:
        log = self.root / f'{name}.runs'
        return len(log.read_text(encoding='utf-8').splitlines()) \
            if log.exists() else 0

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


MAKEFILE_NAME = 'Makefile'


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


class TheLoudMissRunsTheWidestRung(unittest.TestCase):
    """The dangerous case, first: a miss must never exit 0 having run nothing."""

    RULES = LADDER + rule('src/**', 'make story')

    def test_a_missed_path_is_named_and_the_milestone_command_really_ran(self):
        # Every sentinel assertion stays INSIDE the context manager: the
        # fixture's tempdir is removed on exit, and `.exists()` on a deleted
        # tree is False — which would make every "did it run" check pass by
        # never finding the file.
        with Repo(self.RULES) as repo:
            repo.edit('README.md')
            code, out = run('--changed')
            self.assertIn('README.md', out,
                          'the missed path is named, on its own line')
            self.assertTrue(repo.ran('milestone'),
                            'the wide command must ACTUALLY have run — an exit '
                            'code of 0 is also what a run of nothing produces')
            self.assertEqual(0, code)

    def test_a_run_where_every_path_missed_never_exits_zero_having_run_nothing(self):
        with Repo(LADDER + rule('nothing/**', 'make story')) as repo:
            repo.edit('src/a.py', 'README.md')
            code, out = run('--changed')
            self.assertEqual(0, repo.runs('story'),
                             'the narrow rung must not run')
            self.assertTrue(repo.ran('milestone'))
            self.assertIn('src/a.py', out)
            self.assertIn('README.md', out)
            self.assertEqual(0, code)

    def test_the_fallback_carries_the_wide_commands_failure(self):
        with Repo('milestone = "make boom"\n'
                  + rule('nothing/**', 'make story')) as repo:
            repo.edit('README.md')
            code, out = run('--changed')
        self.assertEqual(1, code, 'a failed verification is 1, never 2')
        self.assertIn('exit 2', out, "and the command's own code is printed — "
                                     'make exits 2 on a failed recipe, which '
                                     'is exactly the code rule 6 reserves for '
                                     'config, so it must not be passed through')


class TheStoryRungNeverReachesForTheMilestone(unittest.TestCase):
    """Story 05 criterion 1, as an assertion. This is the 170x."""

    def test_a_matched_story_rung_runs_only_the_narrow_command(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            repo.edit('src/a.py')
            code, _ = run('--story')
            self.assertEqual(1, repo.runs('story'))
            self.assertFalse(repo.ran('milestone'),
                             '--story must never invoke the milestone command')
            self.assertFalse(repo.ran('precommit'))
            self.assertEqual(0, code)

    def test_five_files_under_one_capture_run_the_slice_once(self):
        files = {f'src/pm/f{n}.py': 'x\n' for n in range(5)}
        files['README.md'] = 'x\n'
        with Repo(LADDER + rule('src/<area>/**', 'make story'), files) as repo:
            repo.edit(*[f'src/pm/f{n}.py' for n in range(5)])
            code, out = run('--changed')
            self.assertEqual(1, repo.runs('story'),
                             'five files under one captured directory are ONE '
                             'run — that is the entire 170x')
            self.assertIn('5 changed path(s) -> 1 command(s)', out)
            self.assertEqual(0, code)

    def test_an_empty_diff_says_so_rather_than_passing_in_silence(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            code, out = run('--story')
            self.assertEqual(0, code)
            self.assertIn('no changed paths', out)
            self.assertEqual(0, repo.runs('story'))
            self.assertFalse(repo.ran('milestone'), 'and no fallback either')


class TheRungs(unittest.TestCase):

    def test_feature_and_milestone_each_run_the_target_they_name(self):
        with Repo(LADDER + STORY_RULE) as repo:
            self.assertEqual(0, run('--feature')[0])
            self.assertTrue(repo.ran('precommit'))
            self.assertFalse(repo.ran('milestone'), 'and nothing above it')
            self.assertEqual(0, run('--milestone')[0])
            self.assertTrue(repo.ran('milestone'))

    def test_a_rung_with_no_config_entry_is_named_and_exits_2(self):
        with Repo('milestone = "make milestone"\n' + STORY_RULE) as repo:
            code, out = run('--feature')
            self.assertEqual(2, code, 'never a silent skip that reports success '
                                      'for a rung nobody ran')
            self.assertIn('feature', out)
            self.assertFalse(repo.ran('milestone'),
                             'and never the rung above it instead')


class AConfigProblemIsExitTwoAndNeverANarrowerRun(unittest.TestCase):
    """A malformed or absent `[verify]` must not degrade into a smaller run."""

    def test_every_flag_exits_2_when_the_section_is_absent_or_incomplete(self):
        flags = ('--story', '--changed', '--feature', '--milestone', '--plan',
                 '--check')
        # No section at all. A `--plan` that prints nothing and exits 0 is the
        # same lie as a `--story` that runs nothing and exits 0.
        with Repo(None) as repo:
            for flag in flags:
                with self.subTest(flag=flag, section='absent'):
                    code, out = run(flag)
                    self.assertEqual(2, code)
                    self.assertIn('[verify]', out)
            self.assertFalse(repo.ran('milestone'))
            self.assertEqual(0, repo.runs('story'))
        # A section with rules but no close: the grammar's refusal has to reach
        # the caller as 2, not be swallowed into a narrow run.
        with Repo(STORY_RULE) as repo:
            for flag in ('--story', '--plan', '--check'):
                with self.subTest(flag=flag, section='no milestone rung'):
                    code, out = run(flag)
                    self.assertEqual(2, code)
                    self.assertIn('milestone', out)
            self.assertEqual(0, repo.runs('story'))
        # And a malformed rung value — the D3 refusal, through the real CLI.
        with Repo('milestone = "make check test"\n' + STORY_RULE) as repo:
            self.assertEqual(2, run('--check')[0])
            self.assertEqual(2, run('--story')[0])
            self.assertEqual(0, repo.runs('story'))


class PlanRunsNothing(unittest.TestCase):

    def test_a_plan_over_a_rule_set_whose_run_writes_creates_no_sentinel(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            repo.edit('src/a.py')
            code, out = run('--plan')
            self.assertEqual(0, code)
            self.assertEqual(0, repo.runs('story'))
            self.assertFalse(repo.ran('precommit'))
            self.assertFalse(repo.ran('milestone'))
            self.assertIn('make story', out,
                          'it printed the command it did not run')


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
                tree['pm/roadmap/0.1/ledger.jsonl'] = ledger
            with self.subTest(case=label):
                with Repo(LADDER + rule('src/**', 'make story'), tree) as repo:
                    repo.edit('src/a.py')
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
        tree['pm/roadmap/0.1/ledger.jsonl'] = self._with_ledger(
            {'ts': '2026-09-05T10:00:00Z', 'kind': 'gate', 'gate': 'story',
             'verdict': 'PASS', 'duration_ms': 900, 'census': 5},
            {'ts': '2026-09-05T10:01:00Z', 'kind': 'gate', 'gate': 'milestone',
             'verdict': 'PASS', 'duration_ms': 154_000, 'census': 182},
        )
        with Repo(LADDER + rule('src/**', 'make story'), tree) as repo:
            repo.edit('src/a.py')
            _, out = run('--plan')
        self.assertIn('900 ms (census 5, PASS)', out)
        self.assertIn('154000 ms (census 182, PASS)', out)
        self.assertIn('171x', out, 'the ratio is the measurement, not a guess')


REVERSE_RULE = ('[[verify.narrow]]\ndeclares = "## covers:"\n'
                'scan = "scen/**"\nrun   = "make story"\n')


class Check(unittest.TestCase):
    """`--check` reports dead config, and prints its census on the pass too."""

    def test_a_valid_rule_set_exits_0_and_prints_its_census(self):
        with Repo(LADDER + rule('src/**', 'make story')):
            code, out = run('--check')
        self.assertEqual(0, code)
        self.assertIn('PASS', out)
        self.assertIn('rule(s)', out)
        self.assertIn('tracked file(s) matched by a rule', out,
                      'a check that reports OK over a rule set it did not '
                      'resolve is this package\'s cardinal sin')

    def test_a_glob_matching_zero_tracked_files_is_a_finding_naming_its_index(self):
        # A rule pointed at a path that was renamed away rots into a rule that
        # quietly matches nothing, forever.
        with Repo(LADDER + rule('src/**', 'make story')
                  + rule('renamed_away/**', 'make story')):
            code, out = run('--check')
        self.assertEqual(1, code, 'a finding about the TREE is 1, not 2')
        self.assertIn('#2', out)
        self.assertIn('renamed_away/**', out)

    def test_a_target_no_makefile_declares_is_a_finding_for_a_rung_and_a_run(self):
        with Repo('milestone = "make absent-target"\n'
                  + rule('src/**', 'make story')
                  + rule('README.md', 'make no-such-target')):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('absent-target', out, 'the rung')
        self.assertIn('no-such-target', out, "and the rule's own run")
        self.assertIn('#2', out)

    def test_a_reverse_rule_that_can_select_nothing_is_a_finding(self):
        for label, section, files in (
                ('the louder zero: the scan matches no tracked file',
                 LADDER + rule('src/**', 'make story')
                 + REVERSE_RULE.replace('scen/**', 'gone/**'),
                 None),
                ('files found, none declaring',
                 LADDER + rule('src/**', 'make story') + REVERSE_RULE,
                 {'src/a.py': 'x\n', 'scen/a.md': '# nothing\n'})):
            with self.subTest(case=label):
                with Repo(section, files):
                    code, out = run('--check')
                self.assertEqual(1, code)
                self.assertIn('#2', out)


class ARuleThatCanNeverBeFirst(unittest.TestCase):
    """S1: `--check` asks whether a rule can ever be SELECTED, not whether its
    glob matches.

    A rule under one that already claims its paths matches files forever and
    runs never, and the checker whose whole job is that the declaration does
    not rot used to report PASS over it. Measured before the fix, three rules
    all claiming the one file under `src/`:
    `PASS — 3 rule(s), 3 matched file(s) scanned of 4 tracked`, exit 0.
    """

    def test_a_shadowed_rule_is_a_finding_naming_it_and_the_rule_above_it(self):
        with Repo(LADDER + rule('src/**', 'make story')
                  + rule('src/a.py', 'make precommit')):
            code, out = run('--check')
        self.assertEqual(1, code, 'a rule that can never run is drift, not a pass')
        self.assertIn('#2', out, "the shadowed rule's own index")
        self.assertIn('#1', out, 'and the one claiming its paths first — an '
                                 'author who is not told which rule shadows '
                                 'this one has to re-derive the whole order')
        self.assertIn('FIRST for NONE', out)
        self.assertIn('src/a.py', out)

    def test_two_rules_sharing_ONE_command_are_both_first_and_neither_is_drift(self):
        # The trap in the obvious implementation, and the reason `_first_claims`
        # asks the selector one path at a time. `select` deduplicates by
        # COMMAND, so a whole-corpus Selection collapses these two into one
        # Match carrying #1's index — and a checker reading `matched` as "the
        # rules that fired" files a shadowing finding against #2, which fires
        # for README.md on every run. Four of this repo's own twenty rules
        # collapse into an earlier one's Match that way, so the naive fix
        # reddens a correct rule set — which teaches the same lesson as missing
        # the drift: turn the gate off.
        with Repo(LADDER + rule('src/**', 'make story')
                  + rule('README.md', 'make story')) as repo:
            code, out = run('--check')
            self.assertEqual(0, code, f'both rules fire:\n{out}')
            repo.edit('README.md')
            self.assertEqual(0, run('--changed')[0])
            self.assertEqual(1, repo.runs('story'),
                             'and #2 really is the rule that claims README.md')

    def test_a_reverse_rule_whose_covered_paths_are_claimed_above_it_is_drift(self):
        files = {'src/a.py': 'x\n', 'scen/a.md': '## covers: src/a.py\n'}
        with Repo(LADDER + rule('src/**', 'make precommit') + REVERSE_RULE,
                  files):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('#2', out)
        self.assertIn('FIRST for NONE', out)

    def test_a_reverse_rule_declaring_only_untracked_paths_is_drift(self):
        # The reverse direction's other route to "can never be first": the scan
        # found files, they carry the header, and every path they declare is
        # gone. Neither zero-census fires — `scanned` and `declaring` are both
        # 1 — so before S1 this rule passed while covering nothing that exists.
        files = {'src/a.py': 'x\n', 'scen/a.md': '## covers: gone/x.py\n'}
        with Repo(LADDER + REVERSE_RULE, files):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('#1', out)
        self.assertIn('moved on', out)


class TheCensusIsCountedInOneUnit(unittest.TestCase):
    """S2: the numerator and the denominator are both DISTINCT TRACKED FILES."""

    def test_six_rules_claiming_one_file_count_that_file_once(self):
        # Measured before the fix, six rules all naming `src/a.py` in a repo
        # tracking three files: `6 matched file(s) scanned of 3 tracked`. A
        # census that can exceed its own denominator is not counting what it
        # scanned (hard rule 4), and this is the line a consumer reads to decide
        # whether the gate looked at anything.
        with Repo(LADDER + rule('src/a.py', 'make story') * 6) as repo:
            code, out = run('--check')
            tracked = len(verb.tracked(repo.root))
        self.assertEqual(1, code, 'five of the six are shadowed')
        self.assertIn(f'1 of {tracked} tracked file(s) matched by a rule', out,
                      'one file exists that any rule matched')
        self.assertNotIn('6 of', out)


class ANonMakeRunIsCountedAndNotValidated(unittest.TestCase):
    """S3, ruled in `main.py`'s docstring: `--check` holds a make target to the
    Makefile and asks nothing else of a command — and SAYS how many it did not
    hold, rather than being silent about the gap story 05's `## Close` found."""

    RULES = LADDER + rule('src/**', 'uv run python -m pytest tests/ -q')

    def test_it_is_a_counted_note_on_a_pass_and_still_counted_on_a_fail(self):
        with Repo(self.RULES):
            code, out = run('--check')
        self.assertEqual(0, code, 'a finding here would redden every repo whose '
                                  'narrow rules are a real command line')
        self.assertIn('1 run(s) unvalidated', out,
                      'the count is in the verdict line a consumer greps, not '
                      'only in the prose above it')
        self.assertIn('NOTE', out)
        self.assertNotIn('DRIFT', out)
        with Repo(self.RULES + rule('README.md', 'make no-such-target')):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('no-such-target', out)
        self.assertIn('1 run(s) unvalidated', out,
                      'the unvalidated one is still counted on a FAIL run')


class TheRefusalMatrix(unittest.TestCase):
    """argv is an input surface (SDLC.md §5), and this verb owns that grammar."""

    REFUSED = (
        (),                                     # no mode: never a default
        ('--story', '--plan'),                  # two modes
        ('--story', '--feature', '--milestone'),
        ('--story', '--ref'),                   # --ref with no value
        ('--story', '--ref', ''),               # '' names the INDEX to git
        ('--story', '--ref', 'HEAD', '--ref', 'HEAD'),
        ('--story', '--ref', '--plan'),         # the next flag is never a rev
        ('--story', '--ref', 'a b'),            # one argument spelling two
        ('--story', '--ref', 'no-such-rev'),    # refused in git's own words
        ('--feature', '--ref', 'HEAD'),         # a rung reads no diff
        ('--nope',),                            # never silently ignored
        ('--changed=1',),
        ('positional',),
        ('--story', 'extra'),
    )

    def test_each_exits_2_and_runs_nothing(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            for argv in self.REFUSED:
                with self.subTest(argv=argv):
                    code, _ = run(*argv)
                    self.assertEqual(2, code)
            self.assertEqual(0, repo.runs('story'))
            self.assertFalse(repo.ran('milestone'))
            self.assertFalse(repo.ran('precommit'))

    def test_a_valid_ref_is_accepted_and_scopes_the_diff(self):
        # Without this, a `--ref` that refused everything would pass the matrix.
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            base = repo._git('rev-parse', 'HEAD').strip()
            repo.edit('src/a.py')
            code, out = run('--plan', '--ref', base)
        self.assertEqual(0, code)
        self.assertIn('make story', out)


class GitAbsentOrNotARepo(unittest.TestCase):
    """Never "no changes, nothing to verify" — that is a pass over an unread diff."""

    def test_a_directory_that_is_not_a_git_repo_exits_2_naming_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'plain'
            root.mkdir()
            (root / 'Makefile').write_text(MAKEFILE, encoding='utf-8')
            (root / 'devkit.toml').write_text(
                f'[verify]\n{LADDER}{STORY_RULE}', encoding='utf-8')
            previous = Path.cwd()
            os.chdir(root)
            _clear_caches()
            try:
                code, out = run('--changed')
            finally:
                os.chdir(previous)
                _clear_caches()
        self.assertEqual(2, code)
        self.assertIn('git', out)

    def test_git_missing_from_PATH_exits_2_naming_it(self):
        with Repo(LADDER + STORY_RULE):
            saved = os.environ.get('PATH', '')
            os.environ['PATH'] = ''
            try:
                self.assertIsNone(shutil.which('git'))
                code, out = run('--changed')
            finally:
                os.environ['PATH'] = saved
        self.assertEqual(2, code)
        self.assertIn('git', out)


class SelfHosting(unittest.TestCase):
    """This repo's OWN `[verify]` section, held to the tree it describes."""

    def test_verify_check_passes_on_this_tree_with_a_census_it_can_be_argued_from(self):
        code, out = run('--check')
        self.assertEqual(0, code, f'this repo self-hosts the ladder:\n{out}')
        got = re.search(r'(\d+) of (\d+) tracked file\(s\) matched', out)
        self.assertIsNotNone(got, out)
        matched, total = int(got.group(1)), int(got.group(2))
        self.assertLessEqual(matched, total)
        self.assertEqual(total, len(verb.tracked(verb.repo_root())),
                         'the denominator is `git ls-files`, and the line can '
                         'be argued from against it')

    def test_a_change_under_repo_pm_selects_exactly_one_command(self):
        ruleset = rules.read(cli._verify_section())
        got = verb.select.select(ruleset.narrow,
                                 ['src/agentic_sdlc/repo/pm/ledger.py',
                                  'src/agentic_sdlc/repo/pm/model.py'])
        self.assertEqual((), got.missed)
        self.assertEqual(1, len(got.commands))
        self.assertIn('tests/test_pm_', got.commands[0])


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
