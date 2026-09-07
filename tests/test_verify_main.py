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


class VerifyRemembersItsLastGreen(unittest.TestCase):
    """A rung records its verdict against the TREE STATE it ran on, and a run
    over a byte-identical tree reports that verdict instead of buying the same
    answer again — the seven-closes-one-suite case (issue #10).

    **Every case here is hard rule 4's first cardinal sin waiting to happen**: a
    reused verdict IS a gate that missed drift and printed PASS, if the state
    ever misses a byte or the reuse is ever quiet. So the sentinel files do the
    proving, exactly as they do for the rungs above — `story.ran` present is a
    run, absent is a read — and the untracked-file case is the one that must
    exist, because a new module that breaks collection is the cheapest way to
    make a green tree red without touching a tracked byte.
    """

    # `boom` exits 3 AND leaves a sentinel, so a reused FAIL can be told from a
    # re-run one; the module's own `boom` recipe cannot say which happened.
    MAKEFILE = MAKEFILE.replace('boom:\n\t@exit 3',
                                'boom:\n\t@touch boom.ran\n\t@exit 3')

    @staticmethod
    def row(**over) -> dict:
        """A whole `verify` row for this fixture's story rung; `over` is the
        one field a case is about."""
        base = {'ts': '2026-09-05T10:00:00Z', 'kind': 'verify',
                'rung': 'story', 'gate': 'story', 'verdict': 'PASS',
                'exit_code': 0, 'duration_ms': 5, 'graded': 0}
        base.update(over)
        return base

    def _first_run(self, repo, sentinel='story.ran', code=0):
        """Run the story rung once, prove it RAN, and put the tree back
        byte-for-byte by removing the sentinel it left."""
        got, out = run('--story')
        self.assertEqual(code, got, out)
        path = repo.root / sentinel
        self.assertTrue(path.exists(), f'the first run must run the target:\n{out}')
        path.unlink()
        return out

    def test_a_second_run_on_an_unchanged_tree_reuses_the_verdict_and_its_code(self):
        # The ship criterion, for a green rung and a red one: the recorded
        # verdict, its provenance, its age, and the recorded EXIT CODE — a
        # cache that only remembered greens would re-run every red tree N-1
        # times and call that safety.
        for label, rule, sentinel, code, verdict in (
                ('a green rung', STORY_RULE, 'story.ran', 0, 'PASS'),
                ('a red rung', 'story = "make boom"\n', 'boom.ran', 1, 'FAIL')):
            with self.subTest(case=label), \
                    Repo(LADDER + rule, makefile=self.MAKEFILE) as repo:
                self._first_run(repo, sentinel, code)
                got, out = run('--story')
                self.assertEqual(code, got, out)
                self.assertFalse((repo.root / sentinel).exists(),
                                 'the target must NOT have run the second time')
                self.assertNotIn('  $ ', out, 'nothing was spawned')
                # Loud, and naming the run it came from: a reused green that
                # reads like a fresh green is the sin this feature could add.
                self.assertIn(f'REUSED {verdict}', out)
                self.assertIn('ago) by `verify --story`: make', out)
                self.assertIn('did NOT run', out)
                self.assertIn('--no-cache', out)
                if verdict == 'FAIL':
                    # `make` exits 2 on a failed recipe, and 2 is the code rule
                    # 6 reserves for config — so the recorded code is printed
                    # in the same shape a fresh failure prints it, and the
                    # verb's own exit stays 1.
                    self.assertIn('FAILED (exit 2)', out,
                                  "the TARGET's own code is the recorded one")

    def test_an_untracked_file_invalidates_the_verdict_and_an_ignored_one_does_not(self):
        """THE case this feature can commit rule 4's first sin with.

        A file git has never seen is not in `git diff`, not in the index and
        not in HEAD — and it is exactly what a new test module is, five seconds
        before it breaks collection. An ignored file is the deliberate other
        side: `.gitignore` names what the build itself writes, and a state
        covering the gate's own leavings could never repeat.
        """
        with Repo(LADDER + STORY_RULE,
                  {'src/a.py': 'x\n', '.gitignore': 'junk/\n'}) as repo:
            self._first_run(repo)
            (repo.root / 'tests_new_case.py').write_text('raise SystemExit(1)\n',
                                                         encoding='utf-8')
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertTrue(repo.ran('story'),
                            'a file that would break collection MUST re-run')
            self.assertNotIn('REUSED', out)
            # …and with that file gone the tree is the recorded one again,
            # which is what makes the assertion above about the FILE and not
            # about the cache being broken.
            (repo.root / 'tests_new_case.py').unlink()
            (repo.root / 'story.ran').unlink()
            (repo.root / 'junk').mkdir()
            (repo.root / 'junk' / 'gate.log').write_text('PASS\n', encoding='utf-8')
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertFalse(repo.ran('story'), 'an IGNORED file is the build\'s '
                                                'own leavings, not the tree')
            self.assertIn('REUSED PASS', out)

    def test_one_byte_anywhere_else_moves_the_state_too(self):
        # Tracked-or-not is not the axis: CONTENT is, plus HEAD. Each of these
        # leaves the file COUNT unchanged, so a state that hashed the listing
        # rather than the bytes would reuse all three.
        def edit(repo):
            (repo.root / 'src' / 'a.py').write_text('y\n', encoding='utf-8')

        def delete(repo):
            (repo.root / 'src' / 'a.py').unlink()

        def commit(repo):
            subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@e',
                            'commit', '-q', '--allow-empty', '-m', 'x'],
                           cwd=repo.root, check=True)

        for label, change in (('one edited byte', edit),
                              ('a file removed', delete),
                              ('a new commit under an unchanged tree', commit)):
            with self.subTest(case=label), Repo(LADDER + STORY_RULE) as repo:
                self._first_run(repo)
                change(repo)
                code, out = run('--story')
                self.assertEqual(0, code, out)
                self.assertTrue(repo.ran('story'), f'{label} must re-run')
                self.assertNotIn('REUSED', out)

    def test_no_cache_runs_the_target_and_records_what_it_found(self):
        # Property 3, and the half that is easy to miss: `--no-cache` must also
        # RECORD, or a CI run with the flag would leave the next local run
        # paying full price for an answer that was just bought.
        with Repo(LADDER + STORY_RULE) as repo:
            self._first_run(repo)
            code, out = run('--story', '--no-cache')
            self.assertEqual(0, code, out)
            self.assertTrue(repo.ran('story'), '--no-cache always runs')
            self.assertNotIn('REUSED', out)
            self.assertIn('--no-cache', out)
            (repo.root / 'story.ran').unlink()
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertFalse(repo.ran('story'))
            self.assertIn('REUSED PASS', out)

    def test_a_hand_written_row_over_this_state_is_read_whole_and_reused(self):
        """The control the pure `_verdict` table stands on.

        Seven malformed rows are refused by a FUNCTION CALL in
        `tests/test_verify_cache.py`, in the unit tier where the trust boundary
        belongs. This is the one case that needs the wiring: a row this verb
        never wrote, naming this tree's exact state, found in the ledger, read
        whole and reported instead of the target.
        """
        from agentic_sdlc.repo.verify import cache

        with Repo(LADDER + STORY_RULE) as repo:
            state, defect = cache.tree_state(repo.root)
            self.assertIsNotNone(state, defect)
            path = repo.root / LEDGER
            path.parent.mkdir(parents=True, exist_ok=True)
            # A `verify` row is telemetry a run files about ITSELF, so writing
            # it leaves the digest above true — the exclusion under test too.
            path.write_text(json.dumps(self.row(state=state.digest)) + '\n',
                            encoding='utf-8')
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertFalse(repo.ran('story'), out)
            self.assertIn('REUSED PASS', out)

    def test_a_ledgers_work_rows_are_in_the_state_and_its_telemetry_is_not(self):
        """E1's first half: the digest reads a ledger ROW BY ROW.

        A whole-FILE exclusion took the rows `check pm` grades — a status
        flip, a decision, a deviation — out of the state along with the rows a
        run files about its own execution. A `verify` row must leave the state
        alone (or no run could ever repeat); a `status` row must move it.
        """
        with Repo(LADDER + STORY_RULE) as repo:
            self._first_run(repo)
            path = repo.root / LEDGER
            self.assertTrue(path.is_file(), 'the first run records its verdict')
            with path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(self.row(state='0' * 64)) + '\n')
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertFalse(repo.ran('story'), f'telemetry is not drift:\n{out}')
            self.assertIn('REUSED PASS', out)
            with path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(
                    {'ts': '2026-09-05T11:00:00Z', 'kind': 'status',
                     'grain': 'st-x', 'from': 'building', 'to': 'done'}) + '\n')
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertTrue(repo.ran('story'),
                            f'a status row is a fact about the tree:\n{out}')
            self.assertNotIn('REUSED', out)

    def test_a_row_check_budget_grades_landing_since_refuses_the_reuse(self):
        """E1's second half, and the reviewer's own probe.

        `check budget` grades the NEWEST `gate` row per target and `make
        milestone` — the milestone rung itself — runs it, so ONE appended row
        flips that gate PASS -> FAIL over a byte-identical tree. Those rows
        cannot be in the digest (every gate writes one, so no state would ever
        repeat), so the verdict row COUNTS them and a count that moved runs the
        target. The state still matches: only the count refuses.
        """
        with Repo(LADDER + STORY_RULE) as repo:
            self._first_run(repo)
            path = repo.root / LEDGER
            with path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(
                    {'ts': '2026-09-05T12:00:00Z', 'kind': 'gate',
                     'gate': 'unit', 'verdict': 'PASS',
                     'duration_ms': 99000}) + '\n')
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertTrue(repo.ran('story'),
                            f'a row `check budget` grades moved:\n{out}')
            self.assertNotIn('REUSED', out)
            self.assertIn('`check budget` grades', out)
            # …and the guard is not a permanent kill: this run counted the new
            # row, so the tree is reusable again.
            (repo.root / 'story.ran').unlink()
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertFalse(repo.ran('story'), out)
            self.assertIn('REUSED PASS', out)

    def test_a_submodules_own_checkout_is_in_the_state(self):
        """E2: a directory git lists is another checkout, not a constant.

        Rolling a submodule back one commit is `M lib` to the superproject's
        own `git status`, and a consumer vendoring code that way would have
        reused a green over a tree that changed.
        """
        with Repo(LADDER + STORY_RULE) as repo:
            lib = repo.root.parent / 'lib'
            first = _a_repo_with_two_commits(lib)
            _git_in(repo.root, '-c', 'protocol.file.allow=always',
                    'submodule', 'add', '-q', str(lib), 'lib')
            self._first_run(repo)
            _git_in(repo.root / 'lib', 'checkout', '-q', first)
            code, out = run('--story')
            self.assertEqual(0, code, out)
            self.assertTrue(repo.ran('story'),
                            f'a rolled-back submodule must re-run:\n{out}')
            self.assertNotIn('REUSED', out)


def _git_in(root: Path, *args: str) -> str:
    """git, in a scratch tree, with an identity: these fixtures commit."""
    done = subprocess.run(
        ['git', '-c', 'user.name=t', '-c', 'user.email=t@e', *args],
        cwd=root, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _a_repo_with_two_commits(root: Path) -> str:
    """A repo to be vendored, and the hash of its FIRST commit."""
    root.mkdir(parents=True)
    (root / 'f.txt').write_text('one\n', encoding='utf-8')
    _git_in(root, 'init', '-q', '.')
    _git_in(root, 'add', '-A')
    _git_in(root, 'commit', '-qm', 'one')
    first = _git_in(root, 'rev-parse', 'HEAD')
    (root / 'f.txt').write_text('two\n', encoding='utf-8')
    _git_in(root, 'commit', '-qam', 'two')
    return first


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
