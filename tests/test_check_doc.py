"""`check doc`'s invocation rule — a shipped sentence naming a call the CLI refuses.

0.5.0 shipped three sentences that contradicted shipped behaviour, and the one
this rule catches is the auto-loaded rules file instructing `pm story
reviewing`, which exits 2 because the seed declares no review word for a STORY.
A make target and a path in a backtick span were already checked here; an
INVOCATION is the same kind of claim about the tree and nothing was reading it.

Every case builds its tree (rule 8) and calls the checker FUNCTION — a temp
tree before a process, and a function call before a temp tree (rule 10).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import run_check  # noqa: E402

from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo.checks import doc
from agentic_sdlc.repo.pm import vocabulary

FLOW = vocabulary.render_seed()


@contextmanager
def tree(config: str = ''):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / 'pm' / 'roadmap').mkdir(parents=True)
        (root / '.git').mkdir()
        (root / 'devkit.toml').write_text(config + FLOW, encoding='utf-8')
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def scan(root: Path, *body: str) -> list[str]:
    """The rule over one document, with the tree's own declared states."""
    path = root / 'DOC.md'
    path.write_text('\n'.join(body) + '\n', encoding='utf-8')
    lines = list(enumerate(body, start=1))
    return doc.check_invocations(path, lines, doc.declared_states())


class AnInvocationIsAClaimAboutTheTree(unittest.TestCase):

    def test_a_state_the_project_never_declared_is_a_FINDING(self):
        """THE BROKEN PROBE, and it is the exact sentence 0.5.0 shipped."""
        with tree() as root:
            found = scan(root, 'Move it with `pm story reviewing <id>` when done.')
            self.assertEqual(len(found), 1, found)
            self.assertIn('[pm.states.story] does not declare', found[0])
            self.assertIn('this exits 2', found[0])
            # The declared set is NAMED, so the fix is in the finding.
            self.assertIn('planning ready building done obe', found[0])

    def test_a_state_the_project_DID_declare_is_silent(self):
        """The other half. `reviewing` is a FEATURE word in the seed, so the
        same shape on a feature must pass — otherwise the rule is just a ban on
        one word rather than a reader of the vocabulary."""
        with tree() as root:
            self.assertEqual(
                scan(root, 'Move it with `pm feature reviewing <id>`.'), [])

    def test_a_project_that_declared_the_word_makes_it_legal(self):
        """RULE 9's edge: this reads what the project declared, it does not
        decide what a story vocabulary should be. Declare `reviewing` for a
        story and the same sentence stops being a finding."""
        declared = vocabulary.render_seed(
            {**vocabulary.DEFAULT_FLOWS,
             'story': {'todo': ('planning', 'ready'),
                       'in_progress': ('building', 'reviewing'),
                       'done': ('done', 'obe')}})
        with tree(config=declared) as root:
            self.assertEqual(
                scan(root, 'Move it with `pm story reviewing <id>`.'), [])

    def test_a_deliberate_negative_citation_is_allowed_out(self):
        """The two in this repo are correct prose SAYING the call exits 2. The
        escape is the gate's existing one, never a code change."""
        with tree() as root:
            found = scan(
                root,
                '`pm story reviewing <id>` exits 2.  <!-- doc-scan:allow -->')
            self.assertEqual(found, [])

    def test_a_tree_with_no_declared_flow_reports_NOTHING(self):
        """It reads a vocabulary; with none to read it invents none. A rule
        that guessed a state list would be deciding what a project should do."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            (root / 'pm' / 'roadmap').mkdir(parents=True)
            (root / '.git').mkdir()
            (root / 'devkit.toml').write_text('', encoding='utf-8')
            previous = Path.cwd()
            os.chdir(root)
            repo_root.cache_clear()
            load_config.cache_clear()
            try:
                self.assertEqual(doc.declared_states(), {})
                self.assertEqual(
                    scan(root, '`pm story reviewing <id>`'), [])
            finally:
                os.chdir(previous)
                repo_root.cache_clear()
                load_config.cache_clear()

    def test_prose_that_is_not_an_invocation_is_not_read_as_one(self):
        """The false-positive floor. A rule that fired on ordinary English
        would be switched off, and then it protects nothing."""
        with tree() as root:
            self.assertEqual(scan(
                root,
                'The `story` kind is reviewed by a person.',
                'See `pm vocabulary` for the words.',
                'A `reviewing` feature is in progress.',
                'Run `make unit` first.'), [])


if __name__ == '__main__':
    unittest.main()


class TheRuleIsWiredIntoTheGate(unittest.TestCase):
    """B1, the 0.6.0 milestone review's blocker: the six cases above prove the
    RULE and nothing proved its WIRING.

    Every one of them calls `doc.check_invocations` directly — a function call
    before a temp tree, which is rule 10 and right. But the rule reaches an
    operator through exactly one line in `run()`, and the reviewer deleted that
    line in a scratch copy: all six stayed green, the unit tier stayed green,
    and `check doc` printed `PASS — 0 unresolved claims` at exit 0 over the
    precise 0.5.0 sentence the rule exists to catch.

    A guard that is correct and unreachable is rule 4's first cardinal sin
    wearing a passing test's clothes, and it sat under the ship criterion this
    rule is the only mechanised slice of. So this case runs the GATE.

    `doc.REPO_ROOT` is bound at import and `scope_files()` reads it, so a gate
    run on a scratch tree would otherwise scan the real checkout — the same
    structural knot that left this module untested until 0.6.0. It is rebound
    for the duration rather than converted; converting it is the vocabulary
    sweep's job and that sweep deferred it in writing.
    """

    # The sentence itself, from `bg-the-shipped-rules-name-retired-behaviour`:
    # the seed declares no review word for a STORY, so this exits 2.
    REFUSED = 'Move it on with `agentic-sdlc pm story reviewing <story-id>`.'

    def _gate(self, root: Path) -> tuple[int, str]:
        original = doc.REPO_ROOT
        doc.REPO_ROOT = root
        try:
            return run_check(doc)
        finally:
            doc.REPO_ROOT = original

    def test_the_gate_itself_reports_an_invocation_the_cli_would_refuse(self):
        with tree() as root:
            (root / 'CLAUDE.md').write_text(self.REFUSED + '\n',
                                            encoding='utf-8')
            code, out = self._gate(root)
        self.assertEqual(code, 1, out)
        self.assertIn('story reviewing', out)
        self.assertIn('unresolved claim', out)

    def test_the_same_gate_is_silent_on_a_state_the_project_DID_declare(self):
        """The other direction, on the same tree and the same surface: without
        it, a gate that reported every invocation would pass the case above."""
        with tree() as root:
            (root / 'CLAUDE.md').write_text(
                'Move it on with `agentic-sdlc pm story building <story-id>`.\n',
                encoding='utf-8')
            code, out = self._gate(root)
        self.assertEqual(code, 0, out)
        self.assertNotIn('story building', out)


def milestone(root: Path, gid: str, version: str, *decisions: str) -> None:
    """A milestone and its decisions file, in the pooled layout the seed declares."""
    pool = root / 'pm' / 'roadmap' / 'milestones'
    pool.mkdir(parents=True, exist_ok=True)
    (pool / f'{gid}.md').write_text(
        f'---\nid: "{gid}"\nkind: milestone\nstatus: done\n'
        f'version: {version}\n---\n\n# {gid}\n', encoding='utf-8')
    body = ''.join(f'## D{n} — a ruling\n\nprose\n\n' for n in decisions)
    (pool / f'{gid}-decisions.md').write_text(
        f'# {gid} — decisions\n\n{body}', encoding='utf-8')


def cite(root: Path, *body: str) -> list[str]:
    """The citation rule over one document, against the tree's own decisions."""
    path = root / 'DOC.md'
    path.write_text('\n'.join(body) + '\n', encoding='utf-8')
    return doc.check_decision_citations(
        path, list(enumerate(body, start=1)), doc.decision_index())


class ADecisionCitationResolvesAgainstTheMilestoneThatOwnsIt(unittest.TestCase):
    """D-numbers restart per milestone, so `D1` alone names five different
    rulings. A grain written during 0.6.0's own close cited bare ``D1
    (`emit`, never execute)``; 0.6.0's D1 is *a parent does not close over
    unresolved children* and the ruling meant was 0.5.0's. The wrong answer
    was available, plausible and silent.
    """

    def test_a_citation_naming_a_decision_the_milestone_does_not_record_is_a_FINDING(self):
        with tree() as root:
            milestone(root, 'ms-one', '0.6.0', '1', '2')
            findings = cite(root, 'the ruling is `0.6.0/D9`')
        self.assertEqual(len(findings), 1, findings)
        self.assertIn('0.6.0/D9', findings[0])
        self.assertIn('ms-one', findings[0])
        self.assertIn('D1 D2', findings[0])

    def test_a_citation_that_resolves_is_SILENT(self):
        with tree() as root:
            milestone(root, 'ms-one', '0.6.0', '1', '2')
            self.assertEqual(cite(root, 'the ruling is `0.6.0/D2`'), [])

    def test_a_version_no_milestone_declares_is_a_FINDING_naming_the_ones_that_do(self):
        with tree() as root:
            milestone(root, 'ms-one', '0.6.0', '1')
            findings = cite(root, 'the ruling is `9.9.9/D1`')
        self.assertEqual(len(findings), 1, findings)
        self.assertIn('9.9.9/D1', findings[0])
        self.assertIn('0.6.0', findings[0])

    def test_the_same_number_resolves_differently_per_milestone(self):
        """The defect's own shape: D1 is legal in one milestone and absent in
        the next, and only the qualifier tells them apart."""
        with tree() as root:
            milestone(root, 'ms-one', '0.5.0', '1', '2', '3')
            milestone(root, 'ms-two', '0.6.0', '1')
            self.assertEqual(cite(root, '`0.5.0/D3` and `0.6.0/D1`'), [])
            self.assertEqual(len(cite(root, '`0.6.0/D3`')), 1)

    def test_a_bare_D_number_is_NOT_read_as_a_citation(self):
        """Deliberate, and the measurement is the argument: `check pm`'s own
        rule ids are D1..D12 in a flat namespace, and 32 of the 33 bare `D<n>`
        in this repo's `[doc] scope` are gate rule ids where bare is correct.
        A rule that flagged the bare form would be wrong far more often than
        right (0.7.0/D1).
        """
        with tree() as root:
            milestone(root, 'ms-one', '0.6.0', '1')
            self.assertEqual(cite(root, 'a belt is its checks (D12)'), [])

    def test_a_deliberate_citation_is_allowed_out(self):
        with tree() as root:
            milestone(root, 'ms-one', '0.6.0', '1')
            self.assertEqual(
                cite(root, 'once `0.6.0/D9` <!-- doc-scan:allow -->'), [])

    def test_a_tree_with_no_decisions_file_reports_NOTHING(self):
        """No index, no rule — the same shape `declared_states` uses. A gate
        that invented a decision namespace would fail every consumer."""
        with tree() as root:
            self.assertEqual(doc.decision_index(), {})
            self.assertEqual(cite(root, 'the ruling is `0.6.0/D9`'), [])

    def test_a_milestone_declaring_no_version_is_unreachable_and_skipped(self):
        with tree() as root:
            milestone(root, 'ms-one', '', '1')
            self.assertEqual(doc.decision_index(), {})
