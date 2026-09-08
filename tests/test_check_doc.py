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
from agentic_sdlc.repo.pm import model

FLOW = model.render_seed()


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
        declared = model.render_seed(
            {**model.DEFAULT_FLOWS,
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
