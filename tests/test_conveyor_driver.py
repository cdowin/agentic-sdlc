"""test_conveyor_driver.py — the machine, proved against FIXTURE steps.

The 21 real release steps are a later story. What is proved here is the SHAPE
they plug into, and it is proved against steps built in this file — so the
driver is provable before a single real step exists, and a real step's bug can
never be mistaken for a driver bug.

The two tests that are the whole feature:

  * `test_do_that_lies_does_not_advance` — a fixture `AUTOMATIC` step whose
    `do()` reports success while `check()` still answers no. The run STOPS on
    it. `do()` never decides its own outcome; `check()` decides, and at no
    other moment. Without `verify()` this test passes a lie.
  * `test_judgement_without_artifact_refuses` — no artifact and no configured
    command is UNVERIFIABLE, which is a refusal to advance and never a pass.
    `repo/pm/verdict.py` already rules this way for a record whose block does
    not parse; this inherits the ruling rather than inventing a softer one.

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

    def test_do_that_lies_does_not_advance(self):
        """The feature. `do()` returns success; `check()` still says no.

        The run must STOP on that step and name the postcondition that did not
        hold. A driver that trusted the return value reports DONE over a tree
        where nothing happened — the read-side cardinal sin, printed as PASS.
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
        self.assertEqual('version-sync', result.stopped)
        self.assertEqual((), result.done)
        # It was PERFORMED — the driver is not skipping the work, it is
        # disbelieving the report.
        self.assertEqual(1, liar.calls)
        # …and it asked again afterwards. That second ask is `verify()`.
        self.assertEqual(2, lying.check.calls)
        # The step after it never ran.
        self.assertEqual(0, after.check.calls)
        report = '\n'.join(result.lines)
        self.assertIn('version-sync', report)
        self.assertIn('pyproject.toml still says 0.1.9', report)
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


class AnUnverifiableJudgementIsARefusal(unittest.TestCase):

    def test_judgement_without_artifact_refuses(self):
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
        self.assertEqual('ci-green', result.stopped)
        self.assertEqual((), result.done)
        report = '\n'.join(result.lines)
        self.assertIn('UNVERIFIABLE', report)
        self.assertNotIn('DONE', report)
        # It printed what the operator must do.
        self.assertEqual(1, told.calls)
        self.assertIn('open the PR', report)

    def test_unverifiable_is_not_quietly_false(self):
        """The two refusals print differently, because they are different
        facts: FALSE is "not yet", UNVERIFIABLE is "this cannot be decided"."""
        unk = dr.Step('ci-green', dr.StepKind.JUDGEMENT,
                      check=Scripted(dr.Answer.unverifiable('no artifact')),
                      do=Performed())
        no = dr.Step('merge', dr.StepKind.JUDGEMENT,
                     check=Scripted(NO('no merge commit')), do=Performed())
        with tempfile.TemporaryDirectory() as tmp:
            first = '\n'.join(_walk(Path(tmp), [unk]).lines)
            second = '\n'.join(_walk(Path(tmp), [no]).lines)
        self.assertIn('UNVERIFIABLE', first)
        self.assertNotIn('UNVERIFIABLE', second)
        self.assertIn('STOPPED', second)


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


class AStoppedRunSaysWhatWouldMakeItTrue(unittest.TestCase):

    def test_the_stop_line_names_the_step_its_kind_and_the_detail(self):
        steps = [
            dr.Step('tree-clean', dr.StepKind.GATE, check=Scripted(YES('ok'))),
            dr.Step('review-landed', dr.StepKind.JUDGEMENT,
                    check=Scripted(NO('M1, M2 at disposition: open')),
                    do=Performed('resolve M1 and M2')),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = _walk(Path(tmp), steps)
        stop = [ln for ln in result.lines if ln.startswith('[release] STOPPED')]
        self.assertEqual(1, len(stop), result.lines)
        self.assertIn('review-landed', stop[0])
        self.assertIn('JUDGEMENT', stop[0])
        self.assertIn('M1, M2 at disposition: open', stop[0])
        self.assertIn('2/2', stop[0])


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

    def _assert_refused(self, argv, *, code=2, contains=()):
        got, text, leftovers, _ = self._refuse(argv)
        self.assertEqual(code, got, f'{argv} -> {text}')
        self.assertEqual([], leftovers, f'{argv} wrote {leftovers}')
        for needle in contains:
            self.assertIn(needle, text, f'{argv} -> {text}')

    def test_no_argument_at_all(self):
        self._assert_refused(['release'], contains=['<version>'])

    def test_no_operation_at_all(self):
        self._assert_refused([], contains=['release'])

    def test_an_unknown_operation(self):
        self._assert_refused(['deploy', '0.2.0'], contains=['deploy'])

    def test_traversal(self):
        self._assert_refused(['release', '../../etc/passwd'])
        self._assert_refused(['release', '0.2.0/../0.3.0'])

    def test_absolute_home_and_backslash(self):
        self._assert_refused(['release', '/0.2.0'])
        self._assert_refused(['release', '~/0.2.0'])
        self._assert_refused(['release', 'C:\\0.2.0'])

    def test_globs(self):
        for bad in ('0.2.0*', '0.2.[0-9]', '*', '0.2.?'):
            self._assert_refused(['release', bad])

    def test_empty_whitespace_and_dot_segments(self):
        for bad in ('', '   ', '.', '..', '\t', '0.2 .0'):
            self._assert_refused(['release', bad])

    def test_schemes(self):
        self._assert_refused(['release', 'file:///0.2.0'])
        self._assert_refused(['release', 'https://x/0.2.0'])

    def test_over_length(self):
        self._assert_refused(['release', '0' * 4096],
                             contains=['too long'])

    def test_two_versions(self):
        self._assert_refused(['release', '0.2.0', '0.3.0'])

    def test_an_unknown_flag_is_never_silently_ignored(self):
        self._assert_refused(['release', '0.2.0', '--yolo'],
                             contains=['--yolo'])

    def test_the_skip_flag_is_unknown_until_its_own_story_lands(self):
        self._assert_refused(['release', '0.2.0', '--skip', 'gate'],
                             contains=['--skip'])

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


if __name__ == '__main__':
    unittest.main()
