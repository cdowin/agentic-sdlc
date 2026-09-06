"""test_conveyor_state.py — the run-state file is a CACHE, and a hostile payload.

Two things are proven here and nowhere else.

**It is a cache, never the authority.** The driver re-`check()`s every step the
file records as done; this module proves the file's own half of that — it
round-trips, it refuses a payload it cannot read correctly, and it never starts
from step 0 over a file it did not understand. A run state that can assert a
step is done while the tree says otherwise is the lie the conveyor exists to
end, and half of that lie would be told here.

**It is read from disk, so it is a payload parser and hostile by default.**
Every row of the story's second refusal matrix is a test below, each asserting
the refusal AND that nothing was written.

Deliberately non-spawning: no `subprocess`, none of `tests/support`'s spawning
helpers. The state file is JSON and a path — neither needs a process, and the
`shell` derivation in `tests/conftest.py` reads this module's source to decide.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from agentic_sdlc.repo.conveyor import driver as dr
from agentic_sdlc.repo.conveyor import state as st

KNOWN = ('tree-clean', 'gate', 'tag')


class _Scripted:
    """A fixture `check()` that answers from a script and counts its calls."""

    def __init__(self, *answers) -> None:
        self.answers = list(answers)
        self.calls = 0

    def __call__(self, ctx):
        self.calls += 1
        return self.answers[min(self.calls - 1, len(self.answers) - 1)]


def _blank(root: Path) -> st.RunState:
    return st.RunState(operation='release', version='0.2.0')


def _written(root: Path) -> list[str]:
    """Every path under `root`, relative and posix — the "nothing was written"
    assertion's other half. A refusal that leaves a file behind is not one."""
    out: list[str] = []
    for base, dirs, files in os.walk(root):
        for name in sorted(files):
            out.append(Path(base, name).relative_to(root).as_posix())
    return sorted(out)


class ThePathIsTheDecision(unittest.TestCase):
    """Where it lands, said as an assertion rather than as a docstring."""

    def test_the_state_file_is_under_the_gitignored_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = st.path_for(root, 'release')
            self.assertEqual(
                '.agentic-sdlc/run/release.json',
                path.relative_to(root).as_posix())

    def test_one_file_per_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertNotEqual(st.path_for(root, 'release'),
                                st.path_for(root, 'adopt'))

    def test_this_repo_gitignores_the_run_directory(self):
        """Point 5 of the story's placement argument, as a fact about the tree:
        losing the file costs nothing only if the file is not tracked."""
        from support import REPO_ROOT
        body = (REPO_ROOT / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('.agentic-sdlc/', body.split('\n'))


class ItRoundTrips(unittest.TestCase):

    def test_save_then_load_returns_the_same_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = _blank(root)
            run.record('tree-clean', st.TRUE, 'no modified paths')
            run.record('gate', st.FALSE, '12 failures')
            st.save(root, run)
            back = st.load(root, 'release', '0.2.0', KNOWN)
            self.assertEqual(['tree-clean', 'gate'], list(back.records))
            self.assertEqual(st.TRUE, back.records['tree-clean'].answer)
            self.assertEqual('12 failures', back.records['gate'].reason)

    def test_a_missing_file_is_a_blank_run_not_a_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = st.load(root, 'release', '0.2.0', KNOWN)
            self.assertEqual({}, dict(run.records))
            self.assertEqual([], _written(root))

    def test_a_reason_carrying_u2028_round_trips_as_one_record(self):
        """`ledger.LINE_BREAKERS`, one layer up. U+2028/U+2029 are legal inside
        a JSON string and are LINE TERMINATORS to anything that reads by line,
        so a raw one in the file splits one record into two for the next reader."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hostile = 'a\u2028b\u2029c'
            run = _blank(root)
            run.record('gate', st.FALSE, hostile)
            st.save(root, run)
            raw = st.path_for(root, 'release').read_text(encoding='utf-8')
            self.assertNotIn('\u2028', raw)
            self.assertNotIn('\u2029', raw)
            back = st.load(root, 'release', '0.2.0', KNOWN)
            self.assertEqual(hostile, back.records['gate'].reason)

    def test_writing_twice_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = _blank(root)
            run.record('tree-clean', st.TRUE, 'clean')
            run.at = '2026-09-05T00:00:00Z'
            st.save(root, run)
            first = st.path_for(root, 'release').read_bytes()
            st.save(root, run)
            self.assertEqual(first, st.path_for(root, 'release').read_bytes())


class TheRefusalMatrix(unittest.TestCase):
    """Every row of the story's run-state matrix. Each refuses, and each leaves
    the file exactly as it found it — a parser that repaired what it could not
    read would be inventing a position."""

    def _defect(self, body: str, *, operation='release', version='0.2.0',
                known=KNOWN) -> tuple[str, list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = st.path_for(root, 'release')
            path.parent.mkdir(parents=True)
            path.write_text(body, encoding='utf-8')
            before = path.read_bytes()
            with self.assertRaises(st.StateDefect) as caught:
                st.load(root, operation, version, known)
            self.assertEqual(before, path.read_bytes())
            return str(caught.exception), _written(root)

    @staticmethod
    def _file(**over) -> str:
        body = {'format': st.FORMAT, 'operation': 'release',
                'version': '0.2.0', 'steps': []}
        body.update(over)
        return json.dumps(body)

    def test_every_unreadable_file_refuses_naming_the_defect(self):
        """Eleven rows, one case: each was `_defect(body)` plus the words the
        refusal must carry, and the collected count was the only difference.
        The step-not-in-the-list row is the one that bites hardest — a
        renamed step must not resume into a hole."""
        rows = (
            ('not JSON at all', 'this is not json', ('release.json', 'not JSON')),
            ('truncated mid-object', '{"operation": "release", "steps": [',
             ('not JSON',)),
            ('a list', '[]', ('list',)),
            ('a number', '3', ('int',)),
            ('a string', '"x"', ('str',)),
            ("another operation's file", self._file(operation='adopt'),
             ('adopt', 'release')),
            ("another version's file", self._file(version='0.3.0'), ('0.3.0',)),
            ('a step not in the configured list',
             self._file(steps=[{'step': 'reviw-landed', 'answer': 'true', 'at': 'x'}]),
             ('reviw-landed',)),
            ('an unreadable answer word',
             self._file(steps=[{'step': 'gate', 'answer': 'probably', 'at': 'x'}]),
             ('probably',)),
            ('a step entry that is not an object', self._file(steps=['gate']),
             ('steps',)),
            ('a format from the future', self._file(format=st.FORMAT + 1),
             (str(st.FORMAT),)),
        )
        for label, body, names in rows:
            with self.subTest(label):
                message, _ = self._defect(body)
                for needle in names:
                    self.assertIn(needle, message)

    def test_a_duplicate_entry_is_corrected_and_the_correction_is_printed(self):
        """The one row that is not a refusal: the tree wins, so a duplicate is
        deduplicated in favour of the LAST answer and the correction is carried
        out for the driver to print."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = st.path_for(root, 'release')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                'format': st.FORMAT, 'operation': 'release', 'version': '0.2.0',
                'steps': [{'step': 'gate', 'answer': 'true', 'at': 'a'},
                          {'step': 'gate', 'answer': 'false', 'at': 'b'}]}),
                encoding='utf-8')
            run = st.load(root, 'release', '0.2.0', KNOWN)
            self.assertEqual(st.FALSE, run.records['gate'].answer)
            self.assertEqual(1, len(run.corrections))
            self.assertIn('gate', run.corrections[0])

    def test_the_state_file_is_a_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            st.path_for(root, 'release').mkdir(parents=True)
            with self.assertRaises(st.StateDefect) as caught:
                st.load(root, 'release', '0.2.0', KNOWN)
            self.assertIn('directory', str(caught.exception))

    def test_the_run_directorys_parent_is_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.agentic-sdlc').write_text('not a directory')
            defect = st.destination_defect(root, 'release')
            self.assertIn('.agentic-sdlc', defect)
            self.assertEqual(['.agentic-sdlc'], _written(root))

    @unittest.skipIf(os.geteuid() == 0, 'root ignores the write bit')
    def test_an_unwritable_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = st.path_for(root, 'release').parent
            run_dir.mkdir(parents=True)
            run_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
            try:
                defect = st.destination_defect(root, 'release')
                self.assertIn('writable', defect)
            finally:
                run_dir.chmod(stat.S_IRWXU)

    def test_a_writable_destination_reports_no_defect(self):
        """The refusal's other half: a gate that refused everything would pass
        every row above while checking nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual('', st.destination_defect(Path(tmp), 'release'))


class LosingItCostsNothing(unittest.TestCase):
    """Point 5 of the placement argument, proven at this layer: `clear` removes
    the file and `load` then answers blank rather than refusing."""

    def test_clear_then_load_is_a_blank_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = _blank(root)
            run.record('tree-clean', st.TRUE, 'clean')
            st.save(root, run)
            self.assertTrue(st.path_for(root, 'release').is_file())
            st.clear(root, 'release')
            self.assertFalse(st.path_for(root, 'release').exists())
            self.assertEqual({}, dict(st.load(root, 'release', '0.2.0',
                                              KNOWN).records))


class TheFileIsACacheNeverTheAuthority(unittest.TestCase):
    """The driver's half, and the reason this file can be deleted safely.

    A step the file records as DONE is re-`check()`ed before the driver moves
    past it. Disagreement is resolved in favour of the TREE, the file is
    corrected, and the correction is PRINTED — a run state that can assert a
    step is done while the tree says otherwise is the lie this feature exists
    to end.
    """

    def _steps(self, gate_answer):
        first = dr.Step('tree-clean', dr.StepKind.GATE,
                        check=_Scripted(dr.Answer.yes('no modified paths')))
        second = dr.Step('gate', dr.StepKind.GATE,
                         check=_Scripted(gate_answer))
        return first, second

    def test_a_stale_done_is_re_checked_and_the_file_is_corrected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = st.RunState(operation='release', version='0.2.0')
            stale.record('tree-clean', st.TRUE, 'no modified paths')
            stale.record('gate', st.TRUE, '157/157')
            st.save(root, stale)

            first, second = self._steps(dr.Answer.no('12 failures'))
            run = st.load(root, 'release', '0.2.0', ('tree-clean', 'gate'))
            result = dr.walk({'tree-clean': first, 'gate': second},
                             ('tree-clean', 'gate'),
                             dr.Context(root=root, operation='release',
                                        version='0.2.0'),
                             run)
            st.save(root, run)

            # The tree was ASKED, not trusted.
            self.assertEqual(1, second.check.calls)
            self.assertEqual(1, result.exit_code)
            self.assertEqual('gate', result.stopped)
            report = '\n'.join(result.lines)
            self.assertIn('CORRECTED', report)
            self.assertIn('gate', report)
            self.assertIn('12 failures', report)

            # …and the file now agrees with the tree.
            back = st.load(root, 'release', '0.2.0', ('tree-clean', 'gate'))
            self.assertEqual(st.FALSE, back.records['gate'].answer)

    def test_an_agreeing_done_is_still_re_checked_but_prints_no_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior = st.RunState(operation='release', version='0.2.0')
            prior.record('tree-clean', st.TRUE, 'no modified paths')
            st.save(root, prior)

            first, second = self._steps(dr.Answer.yes('157/157'))
            run = st.load(root, 'release', '0.2.0', ('tree-clean', 'gate'))
            result = dr.walk({'tree-clean': first, 'gate': second},
                             ('tree-clean', 'gate'),
                             dr.Context(root=root, operation='release',
                                        version='0.2.0'), run)
            self.assertEqual(1, first.check.calls)
            self.assertEqual(0, result.exit_code)
            self.assertNotIn('CORRECTED', '\n'.join(result.lines))


class ADeletedStateFileCostsNothing(unittest.TestCase):
    """Point 5 of the placement argument, which is what makes the gitignore
    decision right: every `check()` is a question about the TREE, so the next
    run re-derives the position by asking."""

    def _report(self, root: Path, answers) -> tuple[int, str]:
        steps = {name: dr.Step(name, dr.StepKind.GATE, check=_Scripted(ans))
                 for name, ans in answers}
        run = st.load(root, 'release', '0.2.0', tuple(steps))
        result = dr.walk(steps, tuple(steps),
                         dr.Context(root=root, operation='release',
                                    version='0.2.0'), run)
        st.save(root, run)
        return result.exit_code, '\n'.join(result.lines)

    def test_the_position_is_re_derived_byte_identically(self):
        answers = (('tree-clean', dr.Answer.yes('no modified paths')),
                   ('review-landed', dr.Answer.yes('0 open')),
                   ('gate', dr.Answer.no('12 failures')))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_code, first_report = self._report(root, answers)
            self.assertTrue(st.path_for(root, 'release').is_file())

            # Resume with the file intact.
            resumed_code, resumed_report = self._report(root, answers)

            # Now throw the file away.
            st.clear(root, 'release')
            again_code, again_report = self._report(root, answers)

        self.assertEqual(1, first_code)
        self.assertEqual((first_code, first_report),
                         (resumed_code, resumed_report))
        self.assertEqual((first_code, first_report),
                         (again_code, again_report))


if __name__ == '__main__':
    unittest.main()
