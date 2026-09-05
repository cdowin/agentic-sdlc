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
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

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
            (self.root / 'devkit.toml').write_text(f'[verify]\n{verify}',
                                                   encoding='utf-8')
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

    def test_changed_is_an_alias_for_story(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            repo.edit('src/a.py')
            self.assertEqual(0, run('--changed')[0])
            self.assertEqual(1, repo.runs('story'))

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


class NoVerifySection(unittest.TestCase):
    """Exit 2 for all five flags. A --plan that prints nothing is the same lie."""

    FLAGS = ('--story', '--changed', '--feature', '--milestone', '--plan',
             '--check')

    def test_every_flag_exits_2_naming_the_section(self):
        with Repo(None):
            for flag in self.FLAGS:
                with self.subTest(flag=flag):
                    code, out = run(flag)
                    self.assertEqual(2, code)
                    self.assertIn('[verify]', out)

    def test_milestone_absent_reaches_the_verb_as_exit_2(self):
        with Repo(STORY_RULE):
            for flag in ('--story', '--plan', '--check'):
                with self.subTest(flag=flag):
                    code, out = run(flag)
                    self.assertEqual(2, code)
                    self.assertIn('milestone', out)

    def test_the_cli_and_the_grammar_spell_the_section_the_same(self):
        self.assertEqual(rules.SECTION, cli.VERIFY_SECTION,
                         'two spellings of one section name is a verb reading '
                         'a table nobody wrote')


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

    def test_the_plan_prints_all_three_rungs_in_ladder_order(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            repo.edit('src/a.py')
            _, out = run('--plan')
        order = [out.index(name) for name in ('story', 'feature', 'milestone')]
        self.assertEqual(sorted(order), order, 'narrow to wide')
        self.assertIn('make precommit', out)
        self.assertIn('make milestone', out)

    def test_an_unconfigured_rung_is_named_in_the_plan_not_omitted(self):
        with Repo('milestone = "make milestone"\n' + STORY_RULE) as repo:
            repo.edit('src/a.py')
            _, out = run('--plan')
        self.assertIn('feature', out)
        self.assertIn('not configured', out)


class TheRatioIsMeasuredOrUnknown(unittest.TestCase):
    """A fabricated ratio is worse than no ratio, because it gets quoted."""

    TREE = {
        'src/a.py': 'x\n',
        'pm/roadmap/0.1/milestone.md':
            '---\nid: "0.1"\nname: D\nstatus: building\nbranch: milestone/0.1\n'
            '---\n\nbody\n',
    }

    def _with_ledger(self, *rows: dict) -> str:
        return ''.join(json.dumps(row, separators=(',', ':')) + '\n'
                       for row in rows)

    def test_with_no_gate_rows_the_cost_and_the_ratio_are_the_word_unknown(self):
        with Repo(LADDER + rule('src/**', 'make story'), dict(self.TREE)) as repo:
            repo.edit('src/a.py')
            _, out = run('--plan')
        self.assertIn('unknown', out)
        self.assertNotIn('x —', out.split('ratio')[-1].split('\n')[0]
                         .replace('unknown', ''))

    def test_with_gate_rows_the_plan_prints_the_measured_numbers(self):
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

    def test_a_row_with_no_duration_is_not_a_cost(self):
        tree = dict(self.TREE)
        tree['pm/roadmap/0.1/ledger.jsonl'] = self._with_ledger(
            {'ts': '2026-09-05T10:00:00Z', 'kind': 'gate', 'gate': 'milestone',
             'verdict': 'SKIP'})
        with Repo(LADDER + rule('src/**', 'make story'), tree) as repo:
            repo.edit('src/a.py')
            _, out = run('--plan')
        self.assertIn('unknown', out)


class Check(unittest.TestCase):

    def test_a_valid_rule_set_exits_0_and_prints_its_census(self):
        with Repo(LADDER + rule('src/**', 'make story')):
            code, out = run('--check')
        self.assertEqual(0, code)
        self.assertIn('PASS', out)
        self.assertIn('rule(s)', out)
        self.assertIn('matched file(s) scanned', out,
                      'a check that reports OK over a rule set it did not '
                      'resolve is this package\'s cardinal sin')

    def test_a_glob_matching_zero_tracked_files_is_a_finding_naming_its_index(self):
        with Repo(LADDER + rule('src/**', 'make story')
                  + rule('renamed_away/**', 'make story')):
            code, out = run('--check')
        self.assertEqual(1, code, 'a finding about the TREE is 1, not 2')
        self.assertIn('#2', out)
        self.assertIn('renamed_away/**', out)

    def test_a_run_naming_a_nonexistent_target_is_a_finding_naming_its_index(self):
        with Repo(LADDER + rule('src/**', 'make story')
                  + rule('README.md', 'make no-such-target')):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('#2', out)
        self.assertIn('no-such-target', out)

    def test_a_rung_naming_a_nonexistent_target_is_a_finding(self):
        with Repo('milestone = "make absent-target"\n'
                  + rule('src/**', 'make story')):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('absent-target', out)

    def test_a_reverse_rule_scanning_zero_files_is_the_louder_finding(self):
        section = (LADDER + rule('src/**', 'make story')
                   + '[[verify.narrow]]\ndeclares = "## covers:"\n'
                     'scan = "gone/**"\nrun = "make story"\n')
        with Repo(section):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('#2', out)
        self.assertIn('ZERO tracked files', out)

    def test_a_reverse_rule_whose_corpus_declares_nothing_is_a_finding(self):
        section = (LADDER + rule('src/**', 'make story')
                   + '[[verify.narrow]]\ndeclares = "## covers:"\n'
                     'scan = "scen/**"\nrun = "make story"\n')
        files = {'src/a.py': 'x\n', 'scen/a.md': '# nothing\n'}
        with Repo(section, files):
            code, out = run('--check')
        self.assertEqual(1, code)
        self.assertIn('NONE declares', out)


class TheRefusalMatrix(unittest.TestCase):
    """argv is an input surface (SDLC.md §5). Every row is exit 2."""

    REFUSED = (
        (), ('--story', '--plan'), ('--changed', '--check'),
        ('--story', '--feature', '--milestone'),
        ('--story', '--ref'), ('--story', '--ref', ''),
        ('--story', '--ref', 'HEAD', '--ref', 'HEAD'),
        ('--story', '--ref', '--plan'),
        ('--story', '--ref', 'a b'), ('--story', '--ref', 'a\nb'),
        ('--story', '--ref', '$(id)'), ('--story', '--ref', '`id`'),
        ('--story', '--ref', 'no-such-rev'),
        ('--story', '--ref', '/etc/passwd'),
        ('--story', '--ref', '../../../etc'),
        ('--feature', '--ref', 'HEAD'), ('--check', '--ref', 'HEAD'),
        ('--milestone', '--ref', 'HEAD'),
        ('-x',), ('--nope',), ('--changed=1',), ('positional',),
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

    def test_help_prints_the_docstring_exits_0_and_runs_nothing(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            code, out = run('--help')
            self.assertEqual(0, code)
            self.assertIn('--plan', out)
            self.assertEqual(0, repo.runs('story'))

    def test_help_works_without_a_verify_section_at_all(self):
        with Repo(None):
            self.assertEqual(0, run('--help')[0])

    def test_a_valid_ref_is_accepted_and_scopes_the_diff(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            base = repo._git('rev-parse', 'HEAD').strip()
            repo.edit('src/a.py')
            code, out = run('--plan', '--ref', base)
        self.assertEqual(0, code)
        self.assertIn('make story', out)


class GitAbsentOrNotARepo(unittest.TestCase):

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
        self.assertEqual(2, code, 'never "no changes, nothing to verify"')
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


class ExitCodesAreContract(unittest.TestCase):
    """Rule 6: 0 pass, 1 findings/verification failure, 2 usage or config."""

    def test_zero_for_a_passing_rung(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            repo.edit('src/a.py')
            self.assertEqual(0, run('--story')[0])

    def test_one_for_a_failing_command_even_when_it_exited_two(self):
        # A `make` that exits 2 must never reach a caller looking like a devkit
        # config error, which is what 2 is reserved for.
        with Repo(LADDER + rule('src/**', 'make boom')) as repo:
            repo.edit('src/a.py')
            code, out = run('--story')
        self.assertEqual(1, code)
        self.assertIn('exit 2', out)

    def test_two_for_a_config_problem(self):
        with Repo('milestone = "make check test"\n' + STORY_RULE):
            self.assertEqual(2, run('--check')[0])

    def test_an_empty_diff_says_so_rather_than_passing_in_silence(self):
        with Repo(LADDER + rule('src/**', 'make story')) as repo:
            code, out = run('--story')
            self.assertEqual(0, code)
            self.assertIn('no changed paths', out)
            self.assertEqual(0, repo.runs('story'))


class SelfHosting(unittest.TestCase):
    """This repo's OWN `[verify]` section, held to the tree it describes."""

    def test_verify_check_passes_on_this_tree(self):
        code, out = run('--check')
        self.assertEqual(0, code, f'this repo self-hosts the ladder:\n{out}')
        self.assertIn('PASS', out)

    def test_a_change_under_repo_pm_selects_exactly_one_command(self):
        ruleset = rules.read(cli._verify_section())
        got = verb.select.select(ruleset.narrow,
                                 ['src/agentic_sdlc/repo/pm/ledger.py',
                                  'src/agentic_sdlc/repo/pm/model.py'])
        self.assertEqual((), got.missed)
        self.assertEqual(1, len(got.commands))
        self.assertIn('tests/test_pm_', got.commands[0])

    def test_the_two_fixed_rungs_are_this_repos_own_make_targets(self):
        ruleset = rules.read(cli._verify_section())
        targets, makefile = verb.make_targets(verb.repo_root())
        self.assertTrue(makefile)
        for command in (ruleset.feature, ruleset.milestone):
            self.assertIn(rules.rung_target(command), targets)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
