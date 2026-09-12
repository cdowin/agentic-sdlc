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
LADDER = '[verify]\nstory = "make unit"\nfeature = "make test"\nmilestone = "make milestone"\n'
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

    def test_the_contract_is_POINTED_AT_and_never_copied(self):
        """The whole placement argument. A 163-line paste in every brief is the
        volume this milestone rejected; naming the file is the rule 11 fix."""
        with tree(contracts={'RULES.md': 'SECRET-CONTRACT-BODY\n' * 40}):
            code, out, _ = run()
            self.assertEqual(code, 0)
            self.assertIn('RULES.md', out)
            self.assertNotIn('SECRET-CONTRACT-BODY', out)

    def test_the_ladder_follows_the_declaration_rather_than_a_copy(self):
        """THE PROBE for the property this feature exists to hold: change the
        declaration and the preamble must change with it. A hand-typed ladder
        would pass the case above and fail this one."""
        with tree(config=DECLARED):
            _, before, _ = run()
        moved = ('[dispatch]\nproject = "p"\ncontracts = ["RULES.md"]\n'
                 '[checks]\nall = ["doc", "pm"]\n'
                 '[gates]\nextra = ["my-lint", "my-scan"]\n')
        ladder = ('[verify]\nstory = "make quick"\nfeature = "make wide"\n'
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
        self.assertIn('make unit', before)
        self.assertNotIn('make unit', after)
        self.assertIn('make quick', after)
        self.assertIn('make everything', after)
        # STATIC GATES follows BOTH lists `make check` runs: an agent that
        # trusted `[checks] all` alone ran 4 of one consumer's 25 gates (#22).
        self.assertIn('[checks] all   doc pm\n', after)
        self.assertIn('[gates] extra  my-lint my-scan\n', after)
        self.assertNotIn('stock roster', after)


class TheDispatchCanBeRECORDED(unittest.TestCase):
    """Measured in this milestone: six agents dispatched, zero dispatch rows.

    `GDK_LEDGER_GRAIN` is the one `GDK_LEDGER_*` value no hook payload carries,
    so nothing exports it and nobody reached for `pm ledger record` once. This
    verb stands at the moment a dispatch begins, so it is where both lines are
    NAMED (rule 11). It renders them; the operator runs them (D1).
    """

    def test_the_export_and_the_record_line_arrive_with_the_grain(self):
        with grain_tree():
            code, out, err = run('--grain', STORY, '--role', 'developer')
        self.assertEqual(code, 0, err)
        self.assertIn(f'export GDK_LEDGER_GRAIN={STORY}', out)
        # Through the stock wiring: nothing on a consumer's PATH is named
        # `agentic-sdlc` (#36).
        self.assertIn(f"make pm ARGS='ledger record --grain {STORY} "
                      f"--agent-type developer'", out)
        # #39: the id is what joins the hand row to its courier twin, so the
        # preamble and the rule that auto-loads both ask for it.
        flag = '--agent-id <the id the Agent tool returned>'
        self.assertIn(f'what the agent reported: {flag} --tokens-total N', out)
        guidance = Path(dispatch.__file__).parent / 'pm/guidance/pm-execution.md'
        self.assertIn(flag, guidance.read_text(encoding='utf-8'))

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

    def test_no_grain_renders_no_record_line_at_all(self):
        """`pm ledger record` with no `--grain` and no transcript REFUSES, and
        a preamble that printed it anyway would teach the paste that errors."""
        with tree():
            code, out, _ = run()
        self.assertEqual(code, 0)
        self.assertNotIn('ledger record', out)
        self.assertNotIn('GDK_LEDGER_GRAIN', out)


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

    def test_an_unknown_flag_is_exit_2_and_renders_nothing(self):
        with tree():
            code, out, err = run('--wat')
            self.assertEqual(code, 2)
            self.assertIn('--wat', err)
            self.assertEqual(out, '')


if __name__ == '__main__':
    unittest.main()
