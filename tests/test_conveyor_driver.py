"""test_conveyor_driver.py — the machine, proved against FIXTURE steps.

The 21 real release steps are a later story. What is proved here is the SHAPE
they plug into, and it is proved against steps built in this file — so the
driver is provable before a single real step exists, and a real step's bug can
never be mistaken for a driver bug.

The three tests that are the whole feature:

  * `test_do_that_lies_is_not_believed` — a fixture `AUTOMATIC` step whose
    `do()` reports success while `check()` still answers no. It is recorded
    NOT TRUE. `do()` never decides its own outcome; `check()` decides, and at
    no other moment. Without `verify()` this test passes a lie.
  * `test_judgement_without_artifact_is_not_a_pass` — no artifact and no
    configured command is UNVERIFIABLE, counted in its own column and never
    folded into a plain no. `repo/pm/verdict.py` already rules this way for a
    record whose block does not parse; this inherits the ruling.
  * `TheWalkAlwaysFinishes` — D8, 2026-09-05, and the newest of the three.
    Every step is a check, every check reports, and NO step halts the walk.
    Chris: *"Everything is just a check. `release` should release on a red tree
    if I want (we mostly wouldn't but why stop someone?)"* The exit code still
    says what happened; the transcript still names every step that is not true;
    what is gone is the machine deciding on the operator's behalf that the run
    should not continue.

Deliberately non-spawning — no `subprocess`, no spawning `tests/support`
helper. `tests/conftest.py` derives the `shell` mark from this module's source.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from agentic_sdlc.repo.conveyor import driver as dr
from agentic_sdlc.repo.conveyor import state as st

YES = dr.Answer.yes
NO = dr.Answer.no


def _written(root: Path) -> list[str]:
    out: list[str] = []
    for base, _dirs, files in os.walk(root):
        for name in sorted(files):
            out.append(Path(base, name).relative_to(root).as_posix())
    return sorted(out)


class Scripted:
    """A fixture `check()`: answers from a script, counts every call.

    The last entry repeats, so a step that is true forever needs one entry and
    a step that becomes true after `do()` needs two — which is exactly the
    difference between an honest `do()` and a lying one.
    """

    def __init__(self, *answers: dr.Answer) -> None:
        self.answers = list(answers)
        self.calls = 0

    def __call__(self, ctx: dr.Context) -> dr.Answer:
        self.calls += 1
        return self.answers[min(self.calls - 1, len(self.answers) - 1)]


class Performed:
    """A fixture `do()`. Its RETURN VALUE is advisory text and nothing else —
    which is the point: every value below is a claim the driver must ignore."""

    def __init__(self, says: str = 'done') -> None:
        self.says = says
        self.calls = 0

    def __call__(self, ctx: dr.Context) -> str:
        self.calls += 1
        return self.says


def _ctx(root: Path) -> dr.Context:
    return dr.Context(root=root, operation='release', version='0.2.0')


def _walk(root: Path, steps, names=None):
    registry = {s.name: s for s in steps}
    order = tuple(names if names is not None else [s.name for s in steps])
    run = st.RunState(operation='release', version='0.2.0')
    return dr.walk(registry, order, _ctx(root), run)


class TheKindsAreClosed(unittest.TestCase):

    def test_exactly_three_kinds(self):
        self.assertEqual(
            {'AUTOMATIC', 'GATE', 'JUDGEMENT'},
            {k.name for k in dr.StepKind})

    def test_a_gate_may_not_carry_a_do(self):
        """A gate is not made true by running it again."""
        with self.assertRaises(ValueError) as caught:
            dr.Step('g', dr.StepKind.GATE, check=Scripted(YES()),
                    do=Performed())
        self.assertIn('GATE', str(caught.exception))

    def test_an_automatic_step_must_carry_a_do(self):
        with self.assertRaises(ValueError) as caught:
            dr.Step('a', dr.StepKind.AUTOMATIC, check=Scripted(YES()))
        self.assertIn('AUTOMATIC', str(caught.exception))

    def test_every_kind_walks_in_one_pass_with_no_name_special_case(self):
        auto = dr.Step('auto', dr.StepKind.AUTOMATIC,
                       check=Scripted(NO('not yet'), YES('bumped')),
                       do=Performed())
        gate = dr.Step('gate', dr.StepKind.GATE, check=Scripted(YES('0 fail')))
        judge = dr.Step('judge', dr.StepKind.JUDGEMENT,
                        check=Scripted(YES('merge commit 3a42f19')),
                        do=Performed('open the PR'))
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [auto, gate, judge])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(('auto', 'gate', 'judge'), result.done)
        self.assertIsNone(result.stopped)


class DoNeverDecidesItsOwnOutcome(unittest.TestCase):
    """Rule 4 in step-machine clothing."""

    def test_do_that_lies_is_not_believed(self):
        """The feature. `do()` returns success; `check()` still says no.

        The run must record that step as NOT TRUE and name the postcondition
        that did not hold. A driver that trusted the return value reports DONE
        over a tree where nothing happened — the read-side cardinal sin,
        printed as PASS.

        D8 changed what happens NEXT and nothing about this: the walk no longer
        stops, so `tag` below is asked too. Disbelieving `do()` was never the
        same thing as halting.
        """
        liar = Performed('SUCCESS: version bumped to 0.2.0')
        lying = dr.Step('version-sync', dr.StepKind.AUTOMATIC,
                        check=Scripted(NO('pyproject.toml still says 0.1.9')),
                        do=liar)
        after = dr.Step('tag', dr.StepKind.AUTOMATIC,
                        check=Scripted(NO('no tag')), do=Performed())
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [lying, after])
        self.assertEqual(1, result.exit_code)
        self.assertEqual(('version-sync', 'tag'), result.not_true)
        self.assertEqual((), result.done)
        # It was PERFORMED — the driver is not skipping the work, it is
        # disbelieving the report.
        self.assertEqual(1, liar.calls)
        # …and it asked again afterwards. That second ask is `verify()`.
        self.assertEqual(2, lying.check.calls)
        # D8: the step after it DID run. "release should release on a red tree
        # if I want — why stop someone?"
        self.assertEqual(2, after.check.calls)
        report = '\n'.join(result.lines)
        self.assertIn('version-sync', report)
        self.assertIn('pyproject.toml still says 0.1.9', report)
        # …and the scoreboard names both, so nothing is lost by not halting.
        self.assertIn('2 not true: version-sync, tag', report)
        # The claim is QUOTED, attributed to the step, and never becomes a
        # verdict: the transcript shows the lie next to the refusal, which is
        # more use to the operator than swallowing it would be.
        self.assertIn('AUTOMATIC SAID — SUCCESS: version bumped to 0.2.0',
                      report)
        self.assertNotIn('AUTOMATIC DONE', report)
        self.assertNotIn('ALREADY-TRUE', report)

    def test_a_do_that_tells_the_truth_advances(self):
        """The other half: a driver that refused everything would pass the test
        above while proving nothing."""
        honest = dr.Step('version-sync', dr.StepKind.AUTOMATIC,
                         check=Scripted(NO('still 0.1.9'), YES('0.2.0')),
                         do=Performed())
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [honest])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(('version-sync',), result.done)

    def test_an_already_true_step_is_never_performed(self):
        did = Performed()
        step = dr.Step('tree-clean', dr.StepKind.AUTOMATIC,
                       check=Scripted(YES('no modified paths')), do=did)
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [step])
        self.assertEqual(0, did.calls)
        self.assertIn('ALREADY-TRUE', '\n'.join(result.lines))

    def test_a_gates_do_is_never_reached(self):
        gate = dr.Step('gate', dr.StepKind.GATE,
                       check=Scripted(NO('12 failures')))
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [gate])
        self.assertEqual(1, result.exit_code)
        self.assertEqual('gate', result.stopped)
        self.assertEqual(1, gate.check.calls)


class AnUnverifiableJudgementIsNeverAPass(unittest.TestCase):
    """D8 renamed this class's premise and kept its point.

    UNVERIFIABLE used to be *"a REFUSAL to advance"*. It no longer refuses —
    nothing does — but it is still not a pass, it is still counted apart from
    FALSE, and the run still exits 1. `Truth` has three values so that "this
    cannot be decided" is never collapsed into either of the other two, and
    that is unchanged: the scoreboard has a column for it.
    """

    def test_judgement_without_artifact_is_not_a_pass(self):
        """No artifact, no configured command. UNVERIFIABLE — never a pass."""
        told = Performed('open the PR and re-run: agentic-sdlc release 0.2.0')
        step = dr.Step(
            'ci-green', dr.StepKind.JUDGEMENT,
            check=Scripted(dr.Answer.unverifiable(
                "no artifact, and no [release.commands] entry for 'ci-green'")),
            do=told)
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [step])
        self.assertEqual(1, result.exit_code)
        self.assertEqual(('ci-green',), result.unverifiable)
        # Counted APART from a plain no — that is the whole reason `Truth` is
        # an enum, and the scoreboard keeps the two columns separate.
        self.assertEqual((), result.not_true)
        self.assertEqual((), result.done)
        report = '\n'.join(result.lines)
        self.assertIn('UNVERIFIABLE', report)
        self.assertIn('1 unverifiable: ci-green', report)
        self.assertNotIn('DONE', report)
        # It printed what the operator must do.
        self.assertEqual(1, told.calls)
        self.assertIn('open the PR', report)

    def test_unverifiable_is_not_quietly_false(self):
        """The two print differently, because they are different facts:
        FALSE is "not yet", UNVERIFIABLE is "this cannot be decided"."""
        unk = dr.Step('ci-green', dr.StepKind.JUDGEMENT,
                      check=Scripted(dr.Answer.unverifiable('no artifact')),
                      do=Performed())
        no = dr.Step('merge', dr.StepKind.JUDGEMENT,
                     check=Scripted(NO('no merge commit')), do=Performed())
        with tempfile.TemporaryDirectory() as tmp:
            first = '\n'.join(_walk(Path(tmp), [unk]).lines)
            second = '\n'.join(_walk(Path(tmp), [no]).lines)
        self.assertIn('UNVERIFIABLE', first)
        self.assertIn('1 unverifiable: ci-green', first)
        self.assertNotIn('UNVERIFIABLE', second)
        self.assertIn('NOT-TRUE', second)
        self.assertIn('1 not true: merge', second)


class TheCensusIsNeverZeroInSilence(unittest.TestCase):
    """Rule 4: a machine that walked nothing must say so, loudly."""

    def test_an_empty_step_list_is_a_config_error_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [], names=())
        self.assertEqual(2, result.exit_code)
        self.assertIn('no steps', '\n'.join(result.lines))

    def test_a_name_with_no_registered_step_is_a_config_error(self):
        gate = dr.Step('gate', dr.StepKind.GATE, check=Scripted(YES()))
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [gate], names=('gate', 'no-such-step'))
        self.assertEqual(2, result.exit_code)
        self.assertIn('no-such-step', '\n'.join(result.lines))
        # Refused BEFORE anything ran — a plan that cannot be walked whole is
        # not walked at all.
        self.assertEqual(0, gate.check.calls)

    def test_the_report_counts_what_it_walked(self):
        steps = [dr.Step(f's{i}', dr.StepKind.GATE, check=Scripted(YES()))
                 for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        self.assertIn('3/3', '\n'.join(result.lines))


class ANotTrueStepSaysWhatWouldMakeItTrue(unittest.TestCase):
    """`Answer.detail` is not decoration — it is the sentence printed under
    *what would make it true*, and a step answering not-true with an empty one
    has told the operator that something is wrong and nothing about what.

    D8 kept that line and stopped it being a STOP. The run continues; the
    sentence still has to be there.
    """

    def test_the_line_names_the_step_its_kind_and_the_detail(self):
        steps = [
            dr.Step('tree-clean', dr.StepKind.GATE, check=Scripted(YES('ok'))),
            dr.Step('review-landed', dr.StepKind.JUDGEMENT,
                    check=Scripted(NO('M1, M2 at disposition: open')),
                    do=Performed('resolve M1 and M2')),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        said = [ln for ln in result.lines if 'is not true; what would' in ln]
        self.assertEqual(1, len(said), result.lines)
        self.assertIn('review-landed', said[0])
        self.assertIn('JUDGEMENT', said[0])
        self.assertIn('M1, M2 at disposition: open', said[0])
        self.assertIn('2/2', said[0])
        # The walk REACHED the end: one step true, one not, and it says both.
        self.assertIn('1/2 true', result.lines[-1])


class TheVersionRefusalMatrix(unittest.TestCase):
    """SDLC.md §5, for `release <version>`. The argument is a MILESTONE ID and
    reuses the pm id grammar — a second grammar is a second answer.

    Every row asserts the exit code, that no step's `check()` or `do()` ran, and
    that not one byte was written.
    """

    def _refuse(self, argv: list[str]) -> tuple[int, str, list[str], Scripted]:
        probe = Scripted(YES('should never be asked'))
        step = dr.Step('tree-clean', dr.StepKind.GATE, check=probe)
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = dr.main(argv, root=root,
                               registry={'tree-clean': step},
                               steps=('tree-clean',))
            leftovers = _written(root)
        self.assertEqual(0, probe.calls, 'a step ran during a refusal')
        return code, out.getvalue() + err.getvalue(), leftovers, probe

    # (argv, what the refusal must name). One row per usage-error class; the
    # grammar's own spellings ride together because every row asserts the
    # same three things and a row is one `dr.main` call.
    ROWS = (
        ([], ['release']),                              # no operation at all
        (['release'], ['<version>']),                   # no argument at all
        (['deploy', '0.2.0'], ['deploy']),              # an unknown operation
        (['release', '../../etc/passwd'], []),          # traversal
        (['release', '0.2.0/../0.3.0'], []),
        (['release', '/0.2.0'], []),                    # absolute, home, backslash
        (['release', '~/0.2.0'], []),
        (['release', 'C:\\0.2.0'], []),
        (['release', '0.2.0*'], []),                    # globs
        (['release', '0.2.[0-9]'], []),
        (['release', '*'], []),
        (['release', '0.2.?'], []),
        (['release', ''], []),                          # empty, whitespace, dots
        (['release', '   '], []),
        (['release', '.'], []),
        (['release', '..'], []),
        (['release', '\t'], []),
        (['release', '0.2 .0'], []),
        (['release', 'file:///0.2.0'], []),             # schemes
        (['release', 'https://x/0.2.0'], []),
        (['release', '0' * 4096], ['too long']),        # over length
        (['release', '0.2.0', '0.3.0'], []),            # two versions
        (['release', '0.2.0', '--yolo'], ['--yolo']),   # an unknown flag
        (['release', '0.2.0', '--skip', 'gate'], ['--skip']),  # --skip retired (D8)
    )

    def test_every_row_is_exit_2_runs_no_step_and_writes_nothing(self):
        """Twelve cases became one: each was a `dr.main` call asserting the
        same three things, and the collected count was the only difference."""
        for argv, contains in self.ROWS:
            with self.subTest(argv=argv):
                got, text, leftovers, _ = self._refuse(argv)
                self.assertEqual(2, got, f'{argv} -> {text}')
                self.assertEqual([], leftovers, f'{argv} wrote {leftovers}')
                for needle in contains:
                    self.assertIn(needle, text, f'{argv} -> {text}')

    def test_a_version_naming_no_milestone_directory(self):
        """Exit 1, not 2: the grammar was fine, the tree does not hold it. It
        names the directory it looked for and does NOT create it."""
        code, text, leftovers, _ = self._refuse(['release', '0.9.9'])
        self.assertEqual(1, code, text)
        self.assertEqual([], leftovers)
        self.assertIn('0.9.9-', text)

    def test_help_exits_zero_for_both_operations(self):
        for operation in ('release', 'adopt'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = dr.main([operation, '--help'])
            self.assertEqual(0, code)
            self.assertIn(operation, out.getvalue())
            self.assertIn('<version>', out.getvalue())


class TheRunStateIsPreflighted(unittest.TestCase):
    """A destination this cannot write is refused BEFORE a step runs — a run
    that performs half the release and then cannot record where it got to is
    the resumability promise broken at the only moment it matters."""

    def test_an_unwritable_state_destination_refuses_before_any_step(self):
        probe = Scripted(YES())
        step = dr.Step('tree-clean', dr.StepKind.GATE, check=probe)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pm' / 'roadmap' / '0.2.0-the-conveyor').mkdir(parents=True)
            (root / '.agentic-sdlc').write_text('not a directory')
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = dr.main(['release', '0.2.0'], root=root,
                               registry={'tree-clean': step},
                               steps=('tree-clean',))
        self.assertEqual(2, code)
        self.assertEqual(0, probe.calls)
        self.assertIn('.agentic-sdlc', out.getvalue() + err.getvalue())


class TheWalkAlwaysFinishes(unittest.TestCase):
    """D8. Every step is a check, every check reports, nothing halts.

    The ruling, in Chris's words: *"I don't understand tree vs input.
    Everything is just a check. `release` should release on a red tree if I
    want (we mostly wouldn't but why stop someone?)"*

    What replaced the halt is a SCOREBOARD, and criterion 2 says it has to be
    good — a 21-step run prints 21 lines where it used to print five, so the
    final line is what a caller actually reads.
    """

    def test_a_red_gate_does_not_stop_the_run_from_reaching_tag(self):
        """THE test for the ruling, and the one that will be argued about.

        `gate` is red. `tag` runs anyway, and it is PERFORMED — the gate told
        the operator, and the operator decided. `check <gate>` is still the
        thing that fails a tree in CI and pre-push, with an exit-code contract
        for exactly that; the belt is not that thing.
        """
        tagger = Performed('tagged v0.2.0')
        steps = [
            dr.Step('gate', dr.StepKind.GATE,
                    check=Scripted(NO('12 failures'))),
            dr.Step('tag', dr.StepKind.AUTOMATIC,
                    check=Scripted(NO('no tag'), YES('v0.2.0')), do=tagger),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        # It reached `tag`, performed it, and `tag` came out true.
        self.assertEqual(1, tagger.calls)
        self.assertEqual(('tag',), result.done)
        # …and the red gate is still a finding, named, at exit 1.
        self.assertEqual(1, result.exit_code)
        self.assertEqual(('gate',), result.not_true)
        report = '\n'.join(result.lines)
        self.assertIn('[release:gate] GATE NOT-TRUE — 12 failures', report)
        self.assertIn('1/2 true', report)
        self.assertIn('1 not true: gate', report)

    def test_every_step_is_asked_even_after_several_are_not_true(self):
        """R1 in fixture form: the steps AFTER the not-true ones are exactly
        the ones a resumed release most needs to reach."""
        steps = [dr.Step(f's{i}', dr.StepKind.GATE,
                         check=Scripted(NO(f'no {i}') if i % 2 else YES()))
                 for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        for step in steps:
            self.assertEqual(1, step.check.calls, step.name)
        self.assertEqual(('s0', 's2', 's4'), result.done)
        self.assertEqual(('s1', 's3', 's5'), result.not_true)
        self.assertEqual(1, result.exit_code)
        self.assertIn('3/6 true · 3 not true: s1, s3, s5', result.lines[-1])

    def test_the_scoreboard_keeps_not_true_and_unverifiable_apart(self):
        steps = [
            dr.Step('a', dr.StepKind.GATE, check=Scripted(YES())),
            dr.Step('b', dr.StepKind.GATE, check=Scripted(NO('red'))),
            dr.Step('c', dr.StepKind.JUDGEMENT,
                    check=Scripted(dr.Answer.unverifiable('no artifact')),
                    do=Performed()),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        self.assertIn('1/3 true · 1 not true: b · 1 unverifiable: c',
                      result.lines[-1])

    def test_a_clean_run_still_says_PASS_and_exits_0(self):
        """The scoreboard replaces the stop line, not the pass line: a run
        where everything holds reads exactly as it did before."""
        steps = [dr.Step(f's{i}', dr.StepKind.GATE, check=Scripted(YES()))
                 for i in range(4)]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        self.assertEqual(0, result.exit_code)
        self.assertEqual((), result.not_true)
        self.assertEqual('[release] PASS — 4/4 steps', result.lines[-1])


class ACrashIsAnAnswerNotATraceback(unittest.TestCase):
    """The consequence of no longer halting, and it is not defensive padding.

    While the walk stopped at the first not-true step, a step whose `check()`
    raised was usually never reached. Now every step is asked on every run, so
    a latent crash in step 19 surfaces on a tree where step 3 is red — and an
    uncaught exception is exit 1 with a traceback, which hard rule 6 gives to
    FINDINGS and which a consumer's CI reads as drift. R4 is exactly that
    shape.
    """

    def test_a_check_that_raises_is_UNVERIFIABLE_and_the_walk_continues(self):
        def boom(ctx):
            raise ValueError('tuple.index(x): x not in tuple')

        after = dr.Step('after', dr.StepKind.GATE, check=Scripted(YES()))
        steps = [dr.Step('crasher', dr.StepKind.GATE, check=boom), after]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        # UNVERIFIABLE, not FALSE: it did not answer "no", it failed to answer.
        self.assertEqual(('crasher',), result.unverifiable)
        self.assertEqual((), result.not_true)
        self.assertEqual(('after',), result.done)
        self.assertEqual(1, result.exit_code)
        self.assertIn('ValueError while checking: tuple.index',
                      '\n'.join(result.lines))

    def test_a_do_that_raises_is_reported_and_the_postcondition_re_asked(self):
        def boom(ctx):
            raise OSError('git: command not found')

        step = dr.Step('push-branch', dr.StepKind.AUTOMATIC,
                       check=Scripted(NO('not pushed')), do=boom)
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), [step])
        report = '\n'.join(result.lines)
        self.assertIn('SAID — OSError while performing: git: command not found',
                      report)
        # …and the ANSWER still comes from check(), never from do().
        self.assertEqual(('push-branch',), result.not_true)
        self.assertEqual(2, step.check.calls)

    def test_a_ConfigError_met_at_a_step_is_one_line_at_exit_2_from_the_CLI(self):
        """D8's line, asked at the altitude that bites — D11.

        This case used to assert `assertRaises(ConfigError)` around `_walk`
        and stop, one altitude below its own docstring's claim: nothing asked
        `main` whether "exit 2" was what happened, and it was not. Measured
        (B3, `docs/reviews/2026-09-05-the-belt-reports-and-finishes.md`): a
        consumer typo in `[release.version_files]`, read by step 6 DURING the
        walk, was a traceback at exit 1 — hard rule 6's code for FINDINGS —
        with the five steps already walked printing nothing, while the ledger
        row an earlier not-true step wrote had already landed. So this asks
        the CLI: the transcript so far, one REFUSED line naming the step, one
        line on stderr, exit 2, no traceback, and nothing after it walked.
        """
        from agentic_sdlc.core.config import ConfigError

        def bad(ctx):
            raise ConfigError('[release.version_files] pyproject.toml must be '
                              'a regex string, got 42')

        before = Scripted(YES('no modified paths'))
        after = Scripted(YES())
        registry = {
            'tree-clean': dr.Step('tree-clean', dr.StepKind.GATE, check=before),
            'version-sync': dr.Step('version-sync', dr.StepKind.GATE, check=bad),
            'gate': dr.Step('gate', dr.StepKind.GATE, check=after),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pm' / 'roadmap' / '0.2.0-the-conveyor').mkdir(parents=True)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = dr.main(['release', '0.2.0'], root=root,
                               registry=registry,
                               steps=('tree-clean', 'version-sync', 'gate'))
        self.assertEqual(2, code)
        self.assertNotIn('Traceback', out.getvalue() + err.getvalue())
        # The transcript SO FAR is kept — the step before the reader failed
        # is on stdout, by name — and the refusal names the step it met.
        self.assertIn('[release:tree-clean] GATE ALREADY-TRUE — no modified '
                      'paths', out.getvalue())
        self.assertIn("[release] REFUSED — step 2/3 'version-sync' (GATE): "
                      '[release.version_files]', out.getvalue())
        self.assertEqual(1, len(err.getvalue().strip().split('\n')))
        self.assertIn('got 42', err.getvalue())
        # Nothing after the reader failed walked: a walk over a declaration
        # it cannot read is D8's "before the walk" moment arriving late.
        self.assertEqual(0, after.calls)


if __name__ == '__main__':
    unittest.main()
