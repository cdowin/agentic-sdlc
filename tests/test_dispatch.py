"""`agentic-sdlc dispatch` — the preamble an agent gets before its first call.

Measured in this repo: nothing repo-specific reaches an agent at spawn, and ~35
dispatches during 0.5.0 each hand-pasted the house rules. The load-bearing
property here is that the RENDERED half comes from the same declaration the
verb it describes reads, so a case that hand-typed an expected ladder would be
the second copy this feature deletes.

Every case builds its tree (rule 8): asserting against this repo's own
`devkit.toml` would grade one run against the last one's edits.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

from support.pm import run_cli, tree as pm_tree

from agentic_sdlc.cli import stock_roster
from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo import dispatch, vehicle
from agentic_sdlc.repo.pm import vocabulary

FLOW = vocabulary.render_seed()
LADDER = '[verify]\nspot = "make unit"\nmilestone = "make milestone"\n'
DECLARED = ('[dispatch]\nproject = "A worked example, and its stack."\n'
            'contracts = ["RULES.md"]\n')
# The story `support.pm.tree` builds, in progress — the grain a dispatch is on.
STORY = '0.1/alpha/s0'


@contextmanager
def tree(config: str = DECLARED, contracts: dict[str, str] | None = None):
    """A repo declaring `[dispatch]`, cwd'd into. `RULES.md` exists unless a
    case replaces the mapping — an absent contract is its own case."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / 'pm' / 'roadmap').mkdir(parents=True)
        (root / '.git').mkdir()
        (root / 'devkit.toml').write_text(config + LADDER + FLOW,
                                          encoding='utf-8')
        for rel, body in ({'RULES.md': '# rules'} if contracts is None
                          else contracts).items():
            (root / rel).write_text(body, encoding='utf-8')
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


@contextmanager
def grain_tree():
    """A REAL pool tree declaring `[dispatch]` — `--grain` resolves against
    documents, so the stub above cannot serve a case about one."""
    with pm_tree(config=DECLARED, story_statuses=('building',)) as root:
        (root / 'RULES.md').write_text('# rules', encoding='utf-8')
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            repo_root.cache_clear()
            load_config.cache_clear()


def run(*args) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = dispatch.main(list(args), stock_roster())
    return code, out.getvalue(), err.getvalue()


class ThePreambleIsRenderedNotRetyped(unittest.TestCase):

    def test_it_carries_the_project_line_the_pointers_and_the_derived_halves(self):
        """One pass over everything the ship criterion names, because the
        failure that matters is a section silently missing — not a wording."""
        with tree():
            code, out, err = run()
            self.assertEqual(code, 0, err)
            self.assertIn('A worked example, and its stack.', out)
            self.assertIn('RULES.md', out)
            # DERIVED from `[verify]`, not typed here.
            self.assertIn('make unit', out)
            self.assertIn('make milestone', out)
            # DERIVED from `[pm.states.*]`.
            self.assertIn('open | fixed | closed', out)
            self.assertIn('0 pass   1 findings   2 usage or config error', out)
            # Through make, the verb's code is make's `Error N` (D2, M1).
            self.assertIn("the verb's own code is the N in make's `Error N`",
                          out)
            # m4: nothing declared is the STOCK roster, named as such, and
            # both lists `make check` runs are there (criteria 4, 9).
            self.assertIn(f'[checks] all   {" ".join(stock_roster())}   '
                          f'(the stock roster', out)
            self.assertIn('[gates] extra  (none declared)', out)
            self.assertNotIn('agentic-sdlc check', out)
            # The builder's rules, inlined and DERIVED: the tree from `[pm]
            # roadmap_dir`; the spot check is the stock one, since nothing
            # here declares `[verify] spot` (#119).
            self.assertIn('THE GRAIN FILE IS THE BRIEF: build it; do not '
                          'write a plan.', out)
            self.assertIn('no stash, reset, checkout -- ., restore, clean', out)
            self.assertIn('never touch pm/roadmap/', out)
            self.assertIn('run the spot check: `make unit`', out)
            self.assertNotIn('never `make milestone`', out)

    def test_the_read_verbs_are_named_and_each_is_one_the_router_takes(self):
        """#63: an agent that is never told `pm list` exists greps the tree.
        A named verb the router does not take teaches a paste that errors."""
        from test_cli_surface import routed_verbs

        from agentic_sdlc.repo.pm import cli as pm_cli
        with tree():
            code, out, err = run()
        self.assertEqual(code, 0, err)
        self.assertIn('READ THE TREE THROUGH THE KIT', out)
        named = {argv[:3] if argv[:2] == ('pm', 'ledger') else argv[:2]
                 if argv[0] == 'pm' else argv[:1]
                 for argv, _ in dispatch.READ_VERBS}
        self.assertEqual(named, {('changelog',), ('pm', 'status'),
                                 ('pm', 'list'), ('pm', 'ledger', 'show'),
                                 ('pm', 'ledger', 'report')})
        for argv, _ in dispatch.READ_VERBS:
            self.assertIn(vehicle.command(*argv), out)
            if argv[0] != 'pm':
                self.assertIn(argv[0], routed_verbs())
                continue
            self.assertIn(argv[1], pm_cli.commands())
            if argv[1] == 'ledger':
                self.assertIn(argv[2], pm_cli.ledger_commands())

    def test_the_contract_is_POINTED_AT_and_never_copied(self):
        """The whole placement argument. A 163-line paste in every brief is the
        volume this milestone rejected; naming the file is the rule 11 fix.
        And CLAUDE.md, which the harness already loaded, is not a reading list
        item at all (0.9.0): the rest is reference, never required reading."""
        config = ('[dispatch]\nproject = "p"\n'
                  'contracts = ["CLAUDE.md", "RULES.md"]\n')
        with tree(config=config,
                  contracts={'CLAUDE.md': '# c', 'RULES.md':
                             'SECRET-CONTRACT-BODY\n' * 40}):
            code, out, _ = run()
            self.assertEqual(code, 0)
            self.assertIn('CLAUDE.md is already in your context', out)
            self.assertIn('Reference, open when a question needs it: '
                          'RULES.md\n', out)
            self.assertNotIn('SECRET-CONTRACT-BODY', out)
            self.assertNotIn('READ THESE', out)

    def test_the_ladder_follows_the_declaration_rather_than_a_copy(self):
        """THE PROBE for the property this feature exists to hold: change the
        declaration and the preamble must change with it. A hand-typed ladder
        would pass the case above and fail this one."""
        with tree(config=DECLARED):
            _, before, _ = run()
        moved = ('[dispatch]\nproject = "p"\ncontracts = ["RULES.md"]\n'
                 '[checks]\nall = ["doc", "pm"]\n'
                 '[gates]\nextra = ["my-lint", "my-scan"]\n')
        ladder = ('[verify]\nspot = "make quick"\n'
                  'milestone = "make everything"\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            (root / 'pm' / 'roadmap').mkdir(parents=True)
            (root / '.git').mkdir()
            (root / 'devkit.toml').write_text(moved + ladder + FLOW,
                                              encoding='utf-8')
            (root / 'RULES.md').write_text('# rules', encoding='utf-8')
            previous = Path.cwd()
            os.chdir(root)
            repo_root.cache_clear()
            load_config.cache_clear()
            try:
                _, after, _ = run()
            finally:
                os.chdir(previous)
                repo_root.cache_clear()
                load_config.cache_clear()
        # The ladder's line, not the bare command: the stock spot check is
        # `make unit` in both trees, since neither declares `[verify] spot`.
        self.assertIn('  spot       make unit\n', before)
        self.assertNotIn('  spot       make unit\n', after)
        self.assertIn('make quick', after)
        self.assertIn('make everything', after)
        # STATIC GATES follows BOTH lists `make check` runs: an agent that
        # trusted `[checks] all` alone ran 4 of one consumer's 25 gates (#22).
        self.assertIn('[checks] all   doc pm\n', after)
        self.assertIn('[gates] extra  my-lint my-scan\n', after)
        self.assertNotIn('stock roster', after)


class TheDispatchCanBeRECORDED(unittest.TestCase):
    """Measured in this milestone: six agents dispatched, zero dispatch rows.

    Nobody reached for `pm ledger record` once. This verb stands at the moment
    a dispatch begins, so it is where the stamp and the record line are NAMED
    (rule 11). It renders them; the operator runs the record (D1).
    """

    def test_the_stamp_and_the_record_line_arrive_with_the_grain(self):
        with grain_tree():
            code, out, err = run('--grain', STORY, '--role', 'developer')
        self.assertEqual(code, 0, err)
        # Review R4: the stamp attributes the dispatch, so an export beside it
        # taught a second mechanism that does the same job.
        self.assertIn(f'\nGDK-STAMP grain={STORY}\n', out)
        self.assertNotIn('GDK_LEDGER_GRAIN', out)
        # Through the stock wiring: nothing on a consumer's PATH is named
        # `agentic-sdlc` (#36).
        self.assertIn(f"make pm ARGS='ledger record --grain {STORY} "
                      f"--agent-type developer'", out)
        # #39: the id is what joins the hand row to its courier twin, so the
        # preamble and the rule that auto-loads both ask for it.
        flag = '--agent-id <the id the Agent tool returned>'
        self.assertIn(f'what the agent reported: {flag} --tokens-total N', out)
        # The rule that auto-loads no longer asks for the hand row: the
        # SubagentStop courier files the dispatch, and the preamble's record
        # line is the tool for a dispatch no courier saw.
        guidance = Path(dispatch.__file__).parent / 'pm/guidance/pm-execution.md'
        self.assertIn('courier files the dispatch', guidance.read_text(encoding='utf-8'))

    def test_the_record_line_it_prints_is_one_the_verb_ACCEPTS(self):
        """A printed command that errors is worse than none, so the line is
        lifted out of the preamble and RUN. Every number `pm ledger record`
        takes is optional, which is why the pasteable form carries none."""
        with grain_tree() as root:
            _, out, err = run('--grain', STORY, '--role', 'developer')
            self.assertEqual(err, '')
            line = next(raw.strip() for raw in out.splitlines()
                        if 'ledger record' in raw
                        and not raw.strip().startswith('#'))
            argv = vehicle.argv_of(line)
            self.assertEqual(argv[0], 'pm')
            code, said = run_cli(root, *argv[1:])
        self.assertEqual(code, 0, said)
        self.assertIn('ledger dispatch row appended', said)

    def test_the_stamp_it_prints_is_what_the_transcript_row_copies_back(self):
        """ft-a-concurrent-dispatch-attributes-itself: the preamble IS the
        prompt, so the row names its grain and issue with no environment and
        with two stories live — the case the one-story guess cannot answer."""
        with grain_tree() as root:
            self.assertEqual(run_cli(root, 'set', STORY, 'issue', '42')[0], 0)
            write_doc = root / 'pm/roadmap/stories/s9.md'
            write_doc.write_text(
                '---\nid: 0.1/alpha/s9\nkind: story\nfeature: 0.1/alpha\n'
                'milestone: "0.1"\nname: S9\nstatus: building\nowner:\n---\n',
                encoding='utf-8')
            code, out, err = run('--grain', STORY)
            self.assertEqual(code, 0, err)
            self.assertIn(f'\nGDK-STAMP grain={STORY} issue=42\n', out)
            transcript = root / 't.jsonl'
            transcript.write_text('\n'.join(json.dumps(r) for r in (
                {'type': 'user', 'timestamp': '2026-09-03T10:00:00Z',
                 'message': {'role': 'user', 'content': out}},
                {'type': 'assistant', 'timestamp': '2026-09-03T10:01:00Z',
                 'message': {'model': 'm', 'usage': {'input_tokens': 1}}},
            )) + '\n', encoding='utf-8')
            code, said = run_cli(root, 'ledger', 'record', '--from-transcript',
                                 str(transcript), '--event', 'SubagentStop')
            self.assertEqual(code, 0, said)
            row = json.loads((root / 'pm/roadmap/ledgers/0.1.jsonl')
                             .read_text(encoding='utf-8'))
        self.assertEqual((row['grain'], row['issue']), (STORY, ['42']))

    def test_no_grain_renders_no_record_line_at_all(self):
        """`pm ledger record` with no `--grain` and no transcript REFUSES, and
        a preamble that printed it anyway would teach the paste that errors.
        No grain is still a brief (#125): a research agent has none, and the
        dispatch renders without attribution rather than refusing."""
        with tree():
            code, out, err = run('--role', 'researcher')
        self.assertEqual((code, err), (0, ''))
        self.assertIn('=== PROJECT CONTRACT — for: researcher ===', out)
        self.assertNotIn('ledger record', out)
        self.assertNotIn('GDK-STAMP', out)
        self.assertNotIn('GDK_LEDGER_GRAIN', out)


class TheLoopIsTheBuildersWholeJob(unittest.TestCase):
    """#119, #125: one loop for every builder — its own worktree on
    `feat/<slug>`, the spot check, a commit, a push, a report, and stop. The
    integrator merges; nothing in the brief hands the builder a merge."""

    def test_the_architect_brief_passes_the_output_verbatim(self):
        from agentic_sdlc.repo import install
        self.assertIn('Pass its output verbatim; add only what the grain file '
                      'cannot know.', install.body_of('architect.md'))

    def test_the_loop_renders_on_the_milestone_branch_with_the_spot_check(self):
        with grain_tree() as root:
            self.assertEqual(run_cli(root, 'set', '0.1', 'branch',
                                     'milestone/0.1')[0], 0)
            code, out, err = run('--grain', STORY)
            main = str(repo_root())
        self.assertEqual(code, 0, err)
        slug = '0.1-alpha-s0'    # the id, spelled as agent-worktree takes it
        for line in (f'cd {main} && bash tools/dev/agent-worktree.sh new '
                     f'{slug} milestone/0.1',
                     f'creates feat/{slug}',
                     # A harness worktree is adopted, not duplicated.
                     'already in a harness worktree on feat/* (e.g. '
                     '.claude/worktrees/agent-*)? run '
                     '`bash tools/dev/agent-worktree.sh adopt` there instead '
                     'of `new`',
                     f'on any other branch, `git switch -c feat/{slug}` '
                     'first, then adopt',
                     'run the spot check: `make unit`',
                     f'git push -u origin feat/{slug}',
                     'report your branch and commit hash(es), then stop',
                     'commit only by pathspec: git add <paths>; git commit '
                     '-m "…" -- <paths>',
                     # #77: the finish the pathspec rule does not cover.
                     'a merge in progress finishes with `git commit` and no '
                     'pathspec, or `git merge --continue`'):
            self.assertIn(line, out)
        for gone in ('merge --no-ff', 'serial: on the milestone branch',
                     'the orchestrator merges', 'verify with the story rung'):
            self.assertNotIn(gone, out)


class TheDeclarationIsRefusedByName(unittest.TestCase):
    """A WORKFLOW key: nothing stands behind it (hard rule 5)."""

    def test_an_absent_section_is_exit_2_naming_both_keys(self):
        with tree(config=''):
            code, out, err = run()
            self.assertEqual(code, 2)
            self.assertIn('[dispatch] is not declared', err)
            self.assertIn('contracts', err)
            self.assertEqual(out, '', 'a refusal prints no preamble')

    def test_a_contract_that_resolves_to_nothing_is_exit_2(self):
        """A pointer to a file nobody can open is worse than naming none — the
        D1 defect, in the one surface whose whole job is pointing."""
        with tree(contracts={}):
            code, out, err = run()
            self.assertEqual(code, 2)
            self.assertIn('resolve to nothing', err)
            self.assertIn('RULES.md', err)
            self.assertEqual(out, '')

    def test_an_empty_project_line_is_exit_2(self):
        with tree(config='[dispatch]\nproject = ""\ncontracts = ["RULES.md"]\n'):
            code, _, err = run()
            self.assertEqual(code, 2)
            self.assertIn('project', err)

    def test_a_bare_string_contracts_is_refused_never_iterated(self):
        """Rule: never `tuple(cfg.get(...))` — a bare string is iterable, and
        iterating it would name one contract per CHARACTER."""
        with tree(config='[dispatch]\nproject = "p"\ncontracts = "RULES.md"\n'):
            code, _, err = run()
            self.assertEqual(code, 2)
            self.assertIn('list of strings', err)

    def test_a_removed_key_or_flag_is_exit_2_by_name_with_its_replacement(self):
        """2.0.0 removed the guard (#125): a key that silently did nothing
        would read as a guard still on duty."""
        refusals = (
            (DECLARED.replace('contracts =', 'guard = true\ncontracts ='), (),
             '[dispatch] guard was removed in 2.0.0', 'Delete the key'),
            (DECLARED, ('--preflight',), '--preflight was removed in 2.0.0',
             'Run `dispatch`'),
            (DECLARED, ('--mode', 'parallel'), '--mode was removed in 2.0.0',
             'feat/<slug>'))
        for config, argv, named, instead in refusals:
            with tree(config=config):
                code, out, err = run(*argv)
            self.assertEqual((code, out), (2, ''), named)
            self.assertIn(named, err)
            self.assertIn(instead, err)

    def test_an_unknown_flag_is_exit_2_and_renders_nothing(self):
        with tree():
            code, out, err = run('--wat')
            self.assertEqual(code, 2)
            self.assertIn('--wat', err)
            self.assertEqual(out, '')


if __name__ == '__main__':
    unittest.main()
