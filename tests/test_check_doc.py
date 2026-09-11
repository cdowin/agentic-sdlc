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

from agentic_sdlc.core import markdown
from agentic_sdlc.core.markdown import non_fenced_lines
from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo.checks import doc
from agentic_sdlc.repo.pm import skills, vocabulary

FLOW = vocabulary.render_seed()
# #26's consumer: a feature ladder with no `reviewing`.
NO_FEATURE_REVIEW = vocabulary.render_seed(
    {**vocabulary.DEFAULT_FLOWS,
     'feature': {'todo': ('planning', 'ready'), 'in_progress': ('building',),
                 'done': ('done',)}})


@contextmanager
def tree(config: str = '', flow: str = FLOW):
    """`flow` REPLACES the seed's `[pm.states.*]` rather than joining it: two
    declarations of one table are a TOML error, the vocabulary then loads as
    nothing, and every rule reading it passes vacuously."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / 'pm' / 'roadmap').mkdir(parents=True)
        (root / '.git').mkdir()
        (root / 'devkit.toml').write_text(config + flow, encoding='utf-8')
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

    def test_the_vehicle_spellings_are_the_same_claim(self):
        """C2 of the 0.8.0 spec review: the sweep respelled every shipped call
        as `make pm ARGS='…'` / `make sdlc ARGS='pm …'`, and a rule anchored at
        `pm` read none of them — the #26 consumer's refused call would have
        passed again, in every file the sweep touched. Both quote styles reach
        the verb, so both are read; a wrapped vehicle span is one span."""
        refused = ("`make pm ARGS='feature reviewing x'`",
                   '`make pm ARGS="feature reviewing x"`',
                   "`make sdlc ARGS='pm feature reviewing x'`",
                   '`make sdlc ARGS="pm feature reviewing <id>"`')
        with tree(flow=NO_FEATURE_REVIEW) as root:
            for span in refused:
                with self.subTest(span):
                    found = scan(root, f'Review with {span}.')
                    self.assertEqual(len(found), 1, found)
                    self.assertIn('[pm.states.feature] does not declare',
                                  found[0])
            self.assertEqual(len(scan(
                root, "Review with `make pm ARGS='feature", "reviewing x'`.")),
                1)
            self.assertEqual(scan(
                root, "Build with `make pm ARGS='feature building x'`.",
                "Then `make sdlc ARGS='check pm'` and `make pm ARGS=vocabulary`.",
                "A broken quote `make pm ARGS='feature reviewing x` is unread."),
                [])

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
        with tree(flow=declared) as root:
            # Not vacuous: until #26 this tree declared the seed TWICE, loaded
            # as no vocabulary at all, and the rule passed by reading nothing.
            self.assertIn('reviewing', doc.declared_states()['story'])
            self.assertEqual(
                scan(root, 'Move it with `pm story reviewing <id>`.'), [])

    def test_a_deliberate_negative_citation_is_allowed_out(self):
        """The two in this repo are correct prose SAYING the call exits 2. The
        escape is the gate's existing one, never a code change.

        A WRAPPED span binds the marker to the line it STARTS on, which is the
        line its finding names — so a marker never suppresses a finding
        reported on a line that does not carry it (#26)."""
        with tree() as root:
            found = scan(
                root,
                '`pm story reviewing <id>` exits 2.  <!-- doc-scan:allow -->')
            self.assertEqual(found, [])
            self.assertEqual(scan(
                root, '<!-- doc-scan:allow --> So `pm story',
                'reviewing <id>` exits 2.'), [])
            found = scan(
                root, 'So `pm story',
                'reviewing <id>` exits 2.  <!-- doc-scan:allow -->')
            self.assertEqual(len(found), 1, found)
            self.assertIn('DOC.md:1  `pm story reviewing <id>`', found[0])

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


def shown(path: Path, findings: list[str]) -> list[str]:
    """Findings with the scratch path read as the document's name."""
    return [f.replace(str(path), 'DOC.md') for f in findings]


class ACodeSpanIsReadAcrossItsParagraph(unittest.TestCase):
    """#26. The three span rules read `INLINE_CODE` a line at a time, so a span
    wrapped across a line never formed — and every backtick after it on the
    next line paired with the wrong partner. The installed `pm-execution.md`
    shipped `pm feature` + newline + `reviewing <id>`, and a consumer with no
    `reviewing` feature state was told to run a refused command by the one
    file the rule exists to read.
    """

    REAL = '`pm story reviewing <id>`'  # the seed's story ladder has no review word

    def test_a_status_call_wrapped_across_a_line_is_a_FINDING_on_the_line_it_STARTS(self):
        """THE BROKEN PROBE, #26's own pair: the wrapped half passed. The
        QUOTED half is the review's m3: inside a blockquote the join read
        `pm feature > reviewing <id>`, which no status form matches, so the
        container marker is stripped before the join."""
        with tree(flow=NO_FEATURE_REVIEW) as root:
            self.assertNotIn('reviewing', doc.declared_states()['feature'])
            unwrapped = scan(
                root, '# unwrapped', '',
                'Review is `pm feature reviewing <id>` while the record is written.')
            wrapped = scan(
                root, '# wrapped', '', 'Review is `pm feature',
                '   reviewing <id>` while the record is written.')
            quoted = scan(
                root, '# quoted', '', '> Review is `pm feature',
                '> reviewing <id>` while the record is written.')
        for found in (unwrapped, wrapped, quoted):
            self.assertEqual(len(found), 1, found)
            self.assertIn(
                'DOC.md:3  `pm feature reviewing <id>` names a state '
                '[pm.states.feature] does not declare — this exits 2. '
                'Declared: planning ready building done', found[0])

    def test_a_wrapped_make_target_and_a_wrapped_path_are_read(self):
        """The path and make-target rules shared the hole. A path holds no
        space, so its own span wraps only at an edge; the common miss is a
        wrapped span BEFORE it, which left its backticks mispaired.

        The join also put PROSE within reach (the review's m4): GNU make's
        `No rule to make target` wrapped over two lines read as `make target`.
        An invocation is `make` opening the span or following a shell
        separator, a command string's quote or a `NAME=value`, so the quote is
        silent and the three call shapes the old regex read still read."""
        with tree() as root:
            path = root / 'DOC.md'
            (root / 'docs').mkdir()
            (root / 'docs' / 'here.md').write_text('', encoding='utf-8')
            lines = list(enumerate((
                'Before a commit run `make',
                'wombat` and read it; `make unit` is real.',
                '',
                'The call `pm story',
                'building <id>` writes `docs/gone-for-good.md` too.',
                '',
                'The record lives at `',
                'docs/also-gone.md`, and the live one at `',
                'docs/here.md`.',
                '',
                'It printed `make: *** No rule to make',
                "target 'x'.  Stop.` and `cd sub && make",
                'wombat`, `[verify] story = "make wombat"`',
                'and `GDK_TIERS=unit make wombat`.',
                # Review R4: the m4 anchor dropped a make behind a wrapper
                # word, which v0.7.0 read — a PASS over drift. One per line.
                '`time make wombat`', '`sudo -u root make wombat`',
                '`nice -n 5 make wombat`', '`env -i FOO=1 make wombat`',
                '`command make wombat`', '`exec make wombat`',
                '(`nohup make wombat &`)',
                'but `time to make target` is prose.'), start=1))
            targets = doc.check_make_targets(path, lines, {'unit'})
            paths = doc.check_backtick_paths(path, lines)
            # Review N11: a vehicle target the include lacks is one stale
            # `Makefile.devkit` behind every such span, so each finding names
            # the pinned write that adds it; any other target stays bare.
            stale = doc.check_make_targets(
                path, [(1, "Run `make sdlc ARGS='check doc'`.")], {'unit'})
        from agentic_sdlc.repo import vehicle
        self.assertEqual(len(stale), 1, stale)
        self.assertIn(f'`{vehicle.pinned("install-gates", "--force")}`',
                      stale[0])
        self.assertEqual(shown(path, targets), [
            f'DOC.md:{n}  unknown make target: `make wombat`'
            for n in (1, 12, 13, 14, *range(15, 22))])
        self.assertEqual(shown(path, paths), [
            'DOC.md:5  dead path: `docs/gone-for-good.md`',
            'DOC.md:7  dead path: `docs/also-gone.md`'])

    def test_a_span_never_crosses_a_paragraph_break(self):
        """The spec scout's definition (m2), each break shown by a stray
        backtick BEFORE it: joined across the break, the stray would pair with
        the real span's opening backtick and swallow the claim. The first case
        is the control — no break, so the stray does pair, as CommonMark
        renders it — which is what makes every other case able to fail."""
        cases = {
            'no break (control)': (['a stray ` here', self.REAL], 0),
            'blank line': (['a stray ` here', '', self.REAL], 1),
            'heading': (['a stray ` here', f'## {self.REAL}'], 1),
            'after a heading': (['## a stray ` heading', self.REAL], 1),
            'list-item start': (['a stray ` here', f'- {self.REAL}'], 1),
            'ordered item start': (['a stray ` here', f'2. {self.REAL}'], 1),
            'table row': (['a stray ` here', f'| {self.REAL} | x |'], 1),
            'after a table row': (['| a stray ` cell |', self.REAL], 1),
            # A blockquote is a container: its marker is stripped before the
            # join (m3), and a change of quote depth is a break.
            'one quote (control)': (['> a stray ` here', f'> {self.REAL}'], 0),
            'into a quote': (['a stray ` here', f'> {self.REAL}'], 1),
            'out of a quote': (['> a stray ` here', self.REAL], 1),
            'a deeper quote': (['> a stray ` here', f'> > {self.REAL}'], 1),
            'a blank quoted line': (['> a stray ` here', '>', f'> {self.REAL}'], 1),
        }
        with tree() as root:
            for name, (body, expected) in cases.items():
                with self.subTest(name):
                    found = scan(root, *body)
                    self.assertEqual(len(found), expected, found)
                    if expected:
                        self.assertIn(f'DOC.md:{len(body)}  ', found[0])
            path = root / 'DOC.md'
            states = doc.declared_states()
            with self.subTest('a gap in line numbers'):
                found = doc.check_invocations(
                    path, [(1, 'a stray ` here'), (3, self.REAL)], states)
                self.assertEqual(shown(path, found)[0][:9], 'DOC.md:3 ')
            with self.subTest('a fence, which non_fenced_lines drops'):
                lines, _ = non_fenced_lines(
                    f'a stray ` here\n```\ncode\n```\n{self.REAL}\n')
                found = doc.check_invocations(path, lines, states)
                self.assertEqual(shown(path, found)[0][:9], 'DOC.md:5 ')
            with self.subTest('an UNTERMINATED fence, which it keeps'):
                lines, unterminated = non_fenced_lines(
                    f'a stray ` here\n```\n{self.REAL}\n')
                self.assertEqual(unterminated, 2)
                found = doc.check_invocations(path, lines, states)
                self.assertEqual(shown(path, found)[0][:9], 'DOC.md:3 ')

    def test_a_backtick_run_pairs_only_with_a_run_of_its_own_width(self):
        """CommonMark's pairing. One backtick at a time was harmless on one
        line; across a paragraph a ``double`` span or a stray ``` shifted every
        pairing after it and hid the claim — the second line here.

        The per-line reader that paired that way is gone from `core.markdown`
        (the review's n5): it had no caller, and under the name `code_spans` it
        was one import away from reopening #26 in the next rule."""
        with tree() as root:
            found = scan(
                root, 'A ``double `quoted` span`` and a stray ``` run,',
                f'then {self.REAL} on the next line.')
        self.assertEqual(len(found), 1, found)
        self.assertIn('DOC.md:2  `pm story reviewing <id>`', found[0])
        self.assertEqual(
            [name for name in ('code_spans', 'CODE_SPAN')
             if hasattr(markdown, name)], [])

    def test_the_installed_rule_names_no_refused_state_where_feature_review_is_undeclared(self):
        """`st-the-auto-loaded-rule-is-true-at-this-version` criterion 3, and
        #26's own consumer: the INSTALLED `pm-execution.md`, read by the
        paragraph reader, in a tree whose feature ladder omits `reviewing`.

        Its one `doc-scan:allow` still suppresses exactly what it did: strip
        the marker and the only new finding, across all three span rules, is
        `pm story reviewing <id>` on the marked line."""
        body = skills.guidance_body('pm-execution.md')
        marked = [n for n, line in enumerate(body.split('\n'), 1)
                  if doc.ALLOW_MARKER in line]
        self.assertEqual(len(marked), 1, marked)
        with tree(flow=NO_FEATURE_REVIEW) as root:
            path = root / 'pm-execution.md'
            states = doc.declared_states()

            def findings(text: str) -> list[str]:
                lines, unterminated = non_fenced_lines(text)
                self.assertEqual(unterminated, 0)
                return shown(path, doc.check_invocations(path, lines, states)
                             + doc.check_make_targets(path, lines, set())
                             + doc.check_backtick_paths(path, lines))

            as_shipped = findings(body)
            unmarked = findings(body.replace(doc.ALLOW_MARKER, ''))
        self.assertEqual(
            [f for f in as_shipped if 'does not declare' in f], [])
        suppressed = [f for f in unmarked if f not in as_shipped]
        self.assertEqual(len(suppressed), 1, suppressed)
        self.assertTrue(suppressed[0].startswith(
            f'DOC.md:{marked[0]}  `pm story reviewing <id>`'), suppressed)
