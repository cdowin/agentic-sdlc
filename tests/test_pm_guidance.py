"""The files the pm family installs into a consumer — `pm init` seeding,
`pm install-skills`, and the shape those skills must keep.

Split from test_pm.py by concern; the shared harness is tests/support/pm.py.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from support.pm import put_ledger, run_cli, status_line, tree, write

from agentic_sdlc.repo.pm import cli, skills, vocabulary

class Guidance(unittest.TestCase):
    """`pm install-skills` / `pm init` — the shared doctrine, and only that."""

    def test_the_install_twins_share_their_refusal_helpers(self):
        # `cmd_install_skills` and `install.main` are deliberate sibling
        # COPIES of the decide/apply/report skeleton (they diverge on
        # ownership, refusal channel and wording — skills.py's docstring says
        # why a shared driver was rejected). What must never diverge is the
        # refusal DECISIONS, so this pins that the pm side reaches every one
        # of them through `repo/install.py` rather than re-rolling a copy.
        source = Path(skills.__file__).read_text(encoding='utf-8')
        for helper in ('install.collision_refusal',
                       'install.destination_defect',
                       'install.read_destination',
                       'install.print_diff'):
            self.assertIn(helper, source,
                          f'{helper} is no longer the single home')

    def test_install_writes_a_rule_and_a_skill(self):
        with tree() as root:
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 0, out)
            rule = root / '.claude/rules/pm-execution.md'
            skill = root / '.claude/skills/pm-operations/SKILL.md'
            self.assertTrue(rule.is_file())
            self.assertTrue(skill.is_file())
            # The rule must AUTO-LOAD: without a paths: header it only applies
            # when someone thinks to ask for it, which defeats the purpose.
            self.assertIn('paths:', rule.read_text().split('---')[1])

    def test_the_handoff_skill_is_findable_by_the_words_people_type(self):
        """A skill is selected by its DESCRIPTION, and this one exists because
        nothing else fires at the moment someone asks for a handoff: a template
        guides only once you open it, a header only once the file exists, a cap
        only after you have written too much.

        So the description is the feature. If it stops carrying the words a
        person actually says, the skill is unreachable and the 194-line
        hand-authored handoff happens again.
        """
        with tree() as root:
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 0, out)
            skill = root / '.claude/skills/handoff/SKILL.md'
            self.assertTrue(skill.is_file(), out)
            text = skill.read_text(encoding='utf-8')
            description = text.split('---')[1]
            for said in ('handoff', 'context clear', 'cold', 'fresh session'):
                self.assertIn(said, description.lower(), description)
            # It ROUTES. A skill that restates the template has reproduced the
            # bug it exists to prevent (0.4.0 decisions.md D6).
            self.assertIn('pm new handoff', text)
            self.assertLess(
                len(text.splitlines()), 100,
                'the handoff skill is restating the template instead of '
                'pointing at it')

    def test_the_operations_skill_is_findable_by_the_telemetry_words(self):
        """0.4.0/the-surface-says-telemetry. Asked for "full telemetry —
        phasing, timings, token use, tool calls", the agent building that
        milestone HAND-WROTE A MARKDOWN TABLE while the package sat on
        `pm ledger`: seven row kinds, automatic per-session capture off the
        transcript, and a per-grain spend report.

        `grep -ril telemetry` over the package hit five design documents, four
        tests and a vendored lexer — the archaeology of the feature, never the
        verb that shipped from it. A skill is selected by its DESCRIPTION, so
        the words a person actually types have to be in that block and not in
        the body.
        """
        with tree() as root:
            self.assertEqual(run_cli(root, 'install-skills')[0], 0)
            text = (root / '.claude/skills/pm-operations/SKILL.md').read_text(
                encoding='utf-8')
            description = text.split('---')[1].lower()
            for said in ('telemetry', 'spend', 'cost', 'how long did this take',
                         'tokens'):
                self.assertIn(said, description, description)
            # And the description is not a promise the body does not keep.
            self.assertIn('pm ledger report', text)
            self.assertIn('pm ledger show', text)

    def test_the_execution_rule_names_the_ledger_read_verbs(self):
        """The file that AUTO-LOADS on every tree edit, and its read-verb list
        omitted the ledger entirely — the word appeared twice in it, both times
        as a side effect of a different verb, so it read as a passive byproduct
        rather than something you can ask.
        """
        with tree() as root:
            self.assertEqual(run_cli(root, 'install-skills')[0], 0)
            rule = (root / '.claude/rules/pm-execution.md').read_text(
                encoding='utf-8')
            honest = rule.split('## Keeping the tree honest')[1]
            for said in ('pm ledger show', 'pm ledger report', 'telemetry'):
                self.assertIn(said, honest.lower() if said == 'telemetry'
                              else honest, honest)

    def test_the_rule_names_who_exports_the_grain(self):
        """Rule 11's literal case, caught in review: the couriers read
        `GDK_LEDGER_GRAIN` and NOTHING in this package sets it — not the
        printed settings block, not a hook, not a skill, not the README. It is
        the only `GDK_LEDGER_*` the courier cannot take off the payload, and an
        orchestrator dispatching a subagent had nowhere to learn it exists.

        The fix is a word where somebody is standing, not a capability: the
        rule that auto-loads on every tree edit, and `install-hooks`' own next
        step.
        """
        with tree() as root:
            self.assertEqual(run_cli(root, 'install-skills')[0], 0)
            rule = (root / '.claude/rules/pm-execution.md').read_text(
                encoding='utf-8')
            self.assertIn('GDK_LEDGER_GRAIN', rule)
            self.assertIn('nothing exports it', rule.lower())

    def test_install_is_idempotent(self):
        with tree() as root:
            run_cli(root, 'install-skills')
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 0)
            self.assertIn('already current', out)

    def test_diff_shows_what_an_install_would_change_and_writes_nothing(self):
        """The fourth install verb answers --diff off the SAME helper the
        install-* verbs use, so the four cannot print four kinds of diff."""
        with tree() as root:
            rule = root / '.claude/rules/pm-execution.md'
            rule.parent.mkdir(parents=True, exist_ok=True)
            rule.write_text('# our own version\n', encoding='utf-8')
            code, out = run_cli(root, 'install-skills', '--diff')
            self.assertEqual(code, 0, out)
            self.assertIn('--- a/.claude/rules/pm-execution.md', out)
            self.assertIn('-# our own version', out)
            self.assertIn('.claude/skills/pm-operations/SKILL.md does not exist',
                          out)
            self.assertEqual(rule.read_text(), '# our own version\n')
            self.assertFalse(
                (root / '.claude/skills/pm-operations/SKILL.md').exists())

    def test_install_refuses_to_clobber_a_file_it_did_not_write(self):
        with tree() as root:
            rule = root / '.claude/rules/pm-execution.md'
            rule.parent.mkdir(parents=True, exist_ok=True)
            rule.write_text('# our own version\n', encoding='utf-8')
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 1)
            self.assertIn('differs from what this would write', out)
            self.assertEqual(rule.read_text(), '# our own version\n')

    def test_a_collision_on_the_SECOND_entry_installs_neither(self):
        """The rule installed, the skill refused, and the operator was told
        nothing was written about a repo that now held one of the two. Every
        collision in the plan is decided before the first write."""
        with tree() as root:
            rule = root / '.claude/rules/pm-execution.md'
            skill = root / '.claude/skills/pm-operations/SKILL.md'
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text('# our own operations manual\n', encoding='utf-8')
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 1, out)
            self.assertFalse(
                rule.exists(),
                'the FIRST entry was installed before the SECOND was refused')
            self.assertEqual(skill.read_text(), '# our own operations manual\n')
            self.assertNotIn('installed', out)

    def test_both_collisions_are_named_in_one_refusal(self):
        with tree() as root:
            for rel in ('.claude/rules/pm-execution.md',
                        '.claude/skills/pm-operations/SKILL.md'):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('# ours\n', encoding='utf-8')
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 1)
            self.assertIn('pm-execution.md', out)
            self.assertIn('SKILL.md', out)

    def test_the_plural_refusal_reads_as_a_sentence(self):
        """It did not. With two collisions this printed

            "    .claude/rules/pm-execution.md
                 .claude/skills/pm-operations/SKILL.md exist and were not
                 generated by this tool"

        — the list where the subject goes, so the sentence trails off. The
        install verbs in repo/install.py formatted the same refusal correctly
        and this was a second copy; both now come from one formatter."""
        with tree() as root:
            for rel in ('.claude/rules/pm-execution.md',
                        '.claude/skills/pm-operations/SKILL.md'):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('# ours\n', encoding='utf-8')
            code, out = run_cli(root, 'install-skills')
        self.assertEqual(code, 1)
        self.assertIn('2 destinations exist and differ from what this', out)
        # The count opens the sentence; the paths are listed under it.
        head = out.partition('2 destinations')[2].partition('\n')[0]
        self.assertNotIn('.claude', head, out)

    def test_a_destination_that_cannot_be_written_refuses_before_any_write(self):
        """The all-or-nothing property covered collisions only: a destination
        that is a DIRECTORY tracebacked out of `write_text` with the first file
        already on disk."""
        with tree() as root:
            skill = root / '.claude/skills/pm-operations/SKILL.md'
            skill.mkdir(parents=True)
            code, out = run_cli(root, 'install-skills')
            self.assertEqual(code, 1, out)
            self.assertIn('is a directory', out)
            self.assertIn('Nothing was written', out)
            self.assertFalse((root / '.claude/rules/pm-execution.md').exists(),
                             'the FIRST entry was written before the SECOND '
                             'was found unwritable')

    def test_force_overwrites_and_updates_a_stale_generated_file(self):
        with tree() as root:
            rule = root / '.claude/rules/pm-execution.md'
            rule.parent.mkdir(parents=True, exist_ok=True)
            rule.write_text('# ours\n', encoding='utf-8')
            self.assertEqual(run_cli(root, 'install-skills', '--force')[0], 0)
            # A file we DID generate, merely stale, updates without --force.
            rule.write_text(rule.read_text().replace('agentic-sdlc v', 'agentic-sdlc v0.0.1 v'),
                            encoding='utf-8')
            self.assertEqual(run_cli(root, 'install-skills')[0], 0)

    def test_init_stands_up_a_usable_tree_from_nothing(self):
        # THE ONE FIXTURE HERE THAT STARTS FLOW-LESS ON PURPOSE. `flow_of`'s
        # refusal names `agentic-sdlc pm init` as the command that writes
        # `[pm.states.*]`, and since story 06 of the-code-knows-entry-and-exit
        # it does (F3 of the flow's review: the refusal named a command that
        # left the file untouched). FROM NOTHING is the claim: a bare repo
        # with no devkit.toml at all, `init`, then the `new` calls init's own
        # next-steps print, then a verb that ASKS the flow — `pm milestone
        # ready`, which `_movable` routes through `flow_of` — so this cannot
        # pass on a verb that never asked. Handing this tree a devkit.toml
        # would make it pass by removing the thing it measures.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            root.mkdir()
            (root / '.git').mkdir(exist_ok=True)  # a MARKER, not a repo: `repo_root` walks for it
            previous = Path.cwd()
            os.chdir(root)
            try:
                code, out = run_cli(root, 'init')
                self.assertEqual(code, 0, out)
                self.assertIn('wrote the flow into devkit.toml', out)
                config = (root / 'devkit.toml').read_text(encoding='utf-8')
                self.assertTrue(config.endswith(vocabulary.render_seed()), config)
                # The flow init tells the user to run must actually work.
                self.assertEqual(
                    run_cli(root, 'new', 'milestone', '0.1', 'First')[0], 0)
                self.assertEqual(
                    run_cli(root, 'new', 'feature', 'ms-0.1', 'gw', 'GW')[0], 0)
                self.assertEqual(run_cli(root, 'validate')[0], 0)
                code, out = run_cli(root, 'milestone', 'ready', 'ms-0.1')
                self.assertEqual(code, 0, out)
                # Idempotent: a second init leaves the declaration alone.
                code, out = run_cli(root, 'init')
                self.assertEqual(code, 0, out)
                self.assertIn('already declares [pm.states.*]', out)
                self.assertEqual(
                    (root / 'devkit.toml').read_text(encoding='utf-8'), config)
            finally:
                os.chdir(previous)
            # 0.3.0: no ROADMAP.md. `init` stands up the DIRECTORY; the live
            # index is derived by `pm roadmap` and what outlives a retired
            # milestone is `order` in releases.md.
            self.assertTrue((root / 'pm/roadmap').is_dir())
            self.assertFalse((root / 'pm/roadmap/ROADMAP.md').exists())
            self.assertTrue((root / '.claude/rules/pm-execution.md').is_file())

    def test_init_prints_the_ladder_against_the_tree(self):
        """Review P1: the ladder IS this feature's ship criterion, and nothing
        gated it — deleting `print_ladder(cfg)` from `cmd_init` passed every
        test in the suite. A criterion nothing asserts is a criterion that
        leaves on the next refactor.
        """
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'init')
            self.assertEqual(code, 0, out)
            self.assertIn('against the tree it has', out)
            # Counted against the tree, not just recited from the config: this
            # fixture holds one milestone, one feature and one story.
            self.assertIn('milestone  declares 8; this tree uses 1 (building)', out)
            self.assertIn('never held:', out)
            # And the sentence that makes it a MEANING rather than a write —
            # what was READ, since #30; "a flow you are not running" was an
            # inference from a snapshot, and one consumer narrowed its ladder
            # over it.
            self.assertIn('current status plus the ledger', out)
            self.assertNotIn('a flow you are not running', out)
            story = [ln for ln in out.splitlines()
                     if ln.startswith('  story ')]
            self.assertIn('this tree uses 1 (ready)', story[0])
            # #30: a state a ledger row shows was held is not "never held".
            put_ledger(root, status_line('2026-09-01T00:00:00Z', '0.1/alpha/s0',
                                         'planning', 'ready'))
            code, out = run_cli(root, 'init')
            self.assertEqual(code, 0, out)
            self.assertIn('story      declares 5; this tree uses 2 '
                          '(planning, ready)', out)

    def test_the_ladder_says_a_kind_has_no_grains_rather_than_all_unused(self):
        """Review P3: `U1` skips a kind with no grains because "every state
        unused" means the tree holds none of that kind — a different fact. The
        ladder must agree, or the consumer meets the misleading surface FIRST,
        at adoption, when nothing has been written yet."""
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'init')
            self.assertEqual(code, 0, out)
            self.assertIn('bug        declares 3; this tree holds no bug yet', out)
            self.assertNotIn('never held: open, fixed, closed', out)

    def test_init_is_non_destructive_on_an_existing_tree(self):
        # It fills gaps but must never disturb grains that are already there.
        with tree(story_statuses=('ready',)) as root:
            ff = root / 'pm/roadmap/features/alpha.md'
            before = ff.read_bytes()
            index = root / 'pm/roadmap/ROADMAP.md'
            index.write_text('# Ours\n', encoding='utf-8')
            code, out = run_cli(root, 'init')
            self.assertEqual(code, 0, out)
            self.assertEqual(ff.read_bytes(), before)
            self.assertEqual(index.read_text(), '# Ours\n')  # not reseeded
            self.assertEqual(run_cli(root, 'validate')[0], 0)


class SkillShape(unittest.TestCase):
    """A flat `.claude/skills/<name>.md` does not load as a skill.

    The one mechanically-decidable FACT the retired `check agents` held: where
    the file sits decides whether its description ever fires, so an otherwise
    perfect skill written flat is inert. It lives in `check doc` now, beside
    the other "does this resolve" facts, and it INFERS nothing — it lists one
    directory.

    Its three neighbours in that gate did infer, and are gone: A1/A2 failed a
    build because a markdown file DESCRIBED a workflow, guessed the subject of
    a line by "exactly one grain word appears" (6 of 8 real mentions came back
    UNVERIFIED), and suppressed an identical finding because the line happened
    to contain the word "not".
    """

    def _doc(self, root: Path) -> tuple[int, str]:
        import importlib
        from agentic_sdlc.repo.checks import doc
        from agentic_sdlc.core.project import load_config, repo_root
        repo_root.cache_clear()
        load_config.cache_clear()
        # `doc` binds its root and scope at IMPORT, where production resolves
        # them once per process and the cwd never moves. Tests move it.
        importlib.reload(doc)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = doc.run()
        return code, buf.getvalue()

    def _write(self, root: Path, rel: str, body: str = '# s\n') -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')

    def test_a_flat_skill_file_is_a_finding(self):
        with tree() as root:
            self._write(root, 'CLAUDE.md', '# c\n')
            self._write(root, '.claude/skills/mine.md')
            code, out = self._doc(root)
            self.assertEqual(code, 1, out)
            self.assertIn('.claude/skills/mine.md', out)
            self.assertIn('does NOT load as a skill', out)

    def test_a_correctly_shaped_skill_and_its_supporting_files_pass(self):
        with tree() as root:
            self._write(root, 'CLAUDE.md', '# c\n')
            self._write(root, '.claude/skills/mine/SKILL.md')
            self._write(root, '.claude/skills/mine/references/api.md')
            code, out = self._doc(root)
            self.assertEqual(code, 0, out)

    def test_the_census_says_what_it_listed(self):
        # Rule 4: "no flat skills" out of an empty directory and out of twelve
        # correctly-shaped ones are different reports.
        with tree() as root:
            self._write(root, 'CLAUDE.md', '# c\n')
            self._write(root, '.claude/skills/one/SKILL.md')
            self._write(root, '.claude/skills/two/SKILL.md')
            code, out = self._doc(root)
            self.assertEqual(code, 0, out)
            self.assertIn('2 .claude/skills/ entr(ies)', out)


class TheAgentsGateIsGone(unittest.TestCase):
    """`check agents` gated ENGLISH PROSE, and it inferred. Both are removed.

    A1 failed a build for a `pm <grain> <verb>` spelling inside a backtick
    span; A2 for a `<state> -> <state>` a graph refused — in a file whose job
    is to DESCRIBE the workflow. A4 was a project-supplied regex over prose.
    None of them is a fact about the tree.
    """

    def test_it_is_not_a_gate_name(self):
        with tree() as root:
            from agentic_sdlc.core.project import load_config, repo_root
            repo_root.cache_clear()
            load_config.cache_clear()
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                from agentic_sdlc import cli as top
                code = top.main(['check', 'agents'])
            self.assertEqual(code, 2, buf.getvalue())
            self.assertIn('unknown check', buf.getvalue())

    def test_a_definition_describing_a_workflow_reddens_nothing(self):
        # The exact text A2 failed on, and the near-identical line it let pass
        # because the word "not" appeared in it.
        with tree() as root:
            d = root / '.claude' / 'rules'
            d.mkdir(parents=True)
            (d / 'r.md').write_text(
                'The milestone lifecycle is planning -> ready -> done.\n'
                'When the story is verified, flip `status: review -> done`.\n'
                'A story does not go review -> done on its own.\n',
                encoding='utf-8')
            (root / 'CLAUDE.md').write_text('# c\n', encoding='utf-8')
            import importlib
            from agentic_sdlc.repo.checks import doc
            from agentic_sdlc.core.project import load_config, repo_root
            repo_root.cache_clear()
            load_config.cache_clear()
            importlib.reload(doc)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(doc.run(), 0, buf.getvalue())
        # And there is no other gate left to redden it: the module that held
        # A1/A2/A4 and the two inference helpers is gone, not narrowed.
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module('agentic_sdlc.repo.checks.agents')
