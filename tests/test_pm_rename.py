"""`pm rename` — the grain's own id and every inbound reference, or nothing.

**Selection criterion (hard rule 10):** this is a WRITE that touches N files at
once, so what earns a case here is rule 4's write-side sin — a sweep that looks
whole and is not. Nothing else in the suite covers a multi-file grain write:
`pm set` and the status verbs each rewrite ONE line in ONE file, `pm retire`
only deletes, and `tools/dev/pm_migrate.py` carries a SECOND, simpler matcher
that shares no code with this one (`tests/test_pm_migrate.py`, after it swept
past every unquoted ref in a 497-grain tree). So: one
case per ref KIND in one pass (each field is a different reader), the
all-or-nothing refusal, the two ways `<new-id>` is refused, idempotence, and a
census holding the swept key list to the tree's own declarations.

Unit tier by construction — `porcelain` would spawn git and move the module
into the tier that runs on one interpreter, so *nothing was written* is proven
against the PM files' BYTES, which is the same claim one layer cheaper (the
shape `tests/test_pm_ready_for.py` already uses).
"""
from __future__ import annotations

import unittest
from pathlib import Path

from support.pm import bug, cfg_for, damage, run_cli, tree, write

from agentic_sdlc.repo.pm import model, rename, templates, validate

TARGET = '0.1/alpha'
RENAMED = 'ft-alpha'
POOLS = 'pm/roadmap'


def pm_bytes(root: Path) -> dict[Path, bytes]:
    """Every PM file's bytes — *nothing was written*, without spawning git."""
    return {p.relative_to(root): p.read_bytes()
            for p in sorted((root / 'pm').rglob('*')) if p.is_file()}


def referencing(root: Path) -> None:
    """`tree()` plus one document per REF KIND naming the feature `0.1/alpha`,
    and two near-misses that are not references to it.

    `0.1/alphabet` shares its prefix and `0.1/alpha/s0` — the story `tree()`
    already builds — is prefixed BY it, so a sweep that replaced substrings
    would corrupt both.
    """
    pools = root / POOLS
    write(pools / 'features' / 'beta.md',
          {'id': '0.1/beta', 'kind': 'feature', 'milestone': '"0.1"',
           'name': 'Beta', 'status': 'planning', 'reviewed': TARGET,
           'depends_on': f'["{TARGET}", "0.1/alphabet"]',
           'consumed_by': f'["{TARGET}"]'})
    write(pools / 'features' / 'alphabet.md',
          {'id': '0.1/alphabet', 'kind': 'feature', 'milestone': '"0.1"',
           'name': 'Alphabet', 'status': 'planning'})
    bug(root, 'crash', caused_by=TARGET)
    model.set_list_field(pools / 'milestones' / '0.1.md', 'order',
                         [TARGET, '0.1/alphabet'])


class TheSweepIsOnePass(unittest.TestCase):
    """Story criteria 1 and 5: one case per ref kind, because each field is a
    different reader, and the verb reports every file it touched."""

    def test_the_PLAN_is_swept_because_the_root_is_a_container_too(self):
        """`order` on `releases.md` held VERSIONS until the root became a
        container like any other; it holds milestone IDS now.

        The sweep walked the four grain POOLS, and the plan is in none of them
        — so a rename left `order: ["ms-a"]` pointing at an id no grain
        carries, silently, at exit 0, from the verb whose whole promise is
        that no ref is left behind. It is the same dangling-entry class R1
        reports, written by the tool itself.
        """
        with tree() as root:
            plan = root / 'pm/roadmap/releases.md'
            self.assertEqual(run_cli(root, 'add', 'roadmap', '0.1')[0], 0)
            self.assertIn('"0.1"', plan.read_text(encoding='utf-8'))
            code, out = run_cli(root, 'rename', '0.1', 'ms-first')
            self.assertEqual(code, 0, out)
            body = plan.read_text(encoding='utf-8')
            self.assertIn('"ms-first"', body)
            self.assertNotIn('"0.1"', body)
            # The plan is NAMED in the report, so the caller sees it moved.
            self.assertIn('releases.md', out)
            # ...and the tree still validates: no dangling `order` entry.
            self.assertEqual(run_cli(root, 'validate')[0], 0)

    def test_the_root_grain_can_itself_be_renamed(self):
        # It answers to `roadmap` by default and declares its own `id:` once
        # written, so it is addressable like any other grain — and a sweep
        # that could not see the file could not rename it either.
        with tree() as root:
            self.assertEqual(run_cli(root, 'add', 'roadmap', '0.1')[0], 0)
            code, out = run_cli(root, 'rename', 'roadmap', 'the-plan')
            self.assertEqual(code, 0, out)
            self.assertEqual(
                model.field_of(root / 'pm/roadmap/releases.md', 'id'),
                'the-plan')
            self.assertEqual(run_cli(root, 'add', 'the-plan', '0.1')[0], 0)

    def test_every_ref_kind_moves_and_nothing_else_does(self):
        with tree() as root:
            referencing(root)
            self.assertEqual(run_cli(root, 'validate')[0], 0)
            code, out = run_cli(root, 'rename', TARGET, RENAMED)
            self.assertEqual(code, 0, out)
            moved = {
                'features/alpha.md': ('id', RENAMED),
                'stories/s0.md': ('feature', RENAMED),
                'bugs/crash.md': ('caused_by', RENAMED),
                'features/beta.md': ('reviewed', RENAMED),
            }
            for rel, (key, want) in moved.items():
                with self.subTest(rel=rel):
                    self.assertEqual(
                        model.field_of(root / POOLS / rel, key), want)
                    self.assertIn(rel, out)
            beta = root / POOLS / 'features/beta.md'
            self.assertEqual(model.field_of(beta, 'depends_on'),
                             f'["{RENAMED}", "0.1/alphabet"]')
            self.assertEqual(model.field_of(beta, 'consumed_by'),
                             f'["{RENAMED}"]')
            self.assertEqual(
                model.list_field_of(root / POOLS / 'milestones/0.1.md',
                                    model.ORDER_KEY),
                [RENAMED, '0.1/alphabet'])
            # The near-misses, and the whole tree still resolving: a missed
            # binding leaves a story bound to an id nothing holds.
            self.assertEqual(
                model.field_of(root / POOLS / 'stories/s0.md', 'id'),
                f'{TARGET}/s0')
            self.assertEqual(
                model.field_of(root / POOLS / 'features/alpha.md', 'reviewed'),
                'docs/reviews/alpha.md')
            cfg = cfg_for(root)
            self.assertEqual([g.gid for g in
                              model.children(cfg, 'story', RENAMED)],
                             [f'{TARGET}/s0'])
            self.assertEqual(run_cli(root, 'validate')[0], 0)


def as_nested(root: Path) -> None:
    """The same grains in the PRE-0.4.0 layout — no pool holds a document, so
    every resolver falls back to reading the path as schema."""
    pools = root / POOLS
    for path in sorted(pools.rglob('*.md')):
        path.unlink()
    mdir = pools / '0.1-demo'
    write(mdir / 'milestone.md',
          {'id': '"0.1"', 'name': 'Demo', 'status': 'building'})
    write(mdir / 'features' / 'alpha' / 'feature.md',
          {'id': TARGET, 'milestone': '"0.1"', 'name': 'Alpha',
           'status': 'building', 'reviewed': ''})
    write(mdir / 'features' / 'alpha' / 'stories' / 's0.md',
          {'id': f'{TARGET}/s0', 'feature': TARGET, 'milestone': '"0.1"',
           'name': 'S0', 'status': 'ready', 'depends_on': f'["{TARGET}"]'})


class ANestedTreeIsSweptToo(unittest.TestCase):
    """`pm_migrate` reports a slug collision and tells you to run this verb —
    and at that moment the tree is still NESTED. A sweep that walked only the
    pools would report a rename having written nothing, which is rule 4's
    write-side sin on the migration's own recovery path."""

    def test_a_nested_tree_is_renamed_rather_than_reported_over_nothing(self):
        with tree() as root:
            as_nested(root)
            story = root / POOLS / '0.1-demo/features/alpha/stories/s0.md'
            code, out = run_cli(root, 'rename', TARGET, RENAMED)
            self.assertEqual(code, 0, out)
            self.assertNotIn('in 0 file(s)', out)
            self.assertEqual(model.field_of(story, 'feature'), RENAMED)
            self.assertEqual(model.field_of(story, 'depends_on'),
                             f'["{RENAMED}"]')
            self.assertEqual(
                model.field_of(root / POOLS
                               / '0.1-demo/features/alpha/feature.md', 'id'),
                RENAMED)


class WholeOrNotAtAll(unittest.TestCase):
    """Story criterion 2, and rule 4's write-side sin: a half-swept tree has
    refs pointing at an id that exists and refs pointing at one that does not,
    and no gate can tell which was intended."""

    def test_one_unrewritable_ref_writes_nothing_and_names_it(self):
        with tree() as root:
            referencing(root)
            broken = root / POOLS / 'stories' / 'broken.md'
            write(broken, {'id': '0.1/alpha/broken', 'kind': 'story',
                           'feature': TARGET, 'milestone': '"0.1"',
                           'name': 'B', 'status': 'ready'})
            damage(broken, 'no-closing-fence')
            before = pm_bytes(root)
            code, out = run_cli(root, 'rename', TARGET, RENAMED)
            self.assertEqual(code, 1, out)
            self.assertIn('stories/broken.md', out)
            self.assertIn('nothing was written', out)
            self.assertEqual(pm_bytes(root), before)


class TheNewIdIsRefusedNeverResolved(unittest.TestCase):
    """Story criterion 3. An auto-picked id is a name nobody chose, in the one
    field that is stable for life and cited from commit messages (0.4.0/D4)."""

    BAD_IDS = ('', '   ', 'a:b', 'a//b', '../escape', 'glob*', 'x' * 201)

    def test_the_id_grammar_is_the_shared_matrix_and_answers_before_a_read(self):
        with tree() as root:
            original, model.read_raw = model.read_raw, self._no_reads()
            try:
                for gid in self.BAD_IDS:
                    with self.subTest(gid=gid[:20]):
                        code, out = run_cli(root, 'rename', TARGET, gid)
                        self.assertEqual(code, 2, out)
                        # The SHARED matrix, not a second one spelled here.
                        self.assertIn(model.id_defect(gid), out)
            finally:
                model.read_raw = original

    def _no_reads(self):
        def explode(path, *rest):
            raise AssertionError(f'a refusal read {path}')
        return explode

    def test_an_id_another_grain_holds_is_refused_naming_that_grain(self):
        with tree() as root:
            referencing(root)
            before = pm_bytes(root)
            code, out = run_cli(root, 'rename', TARGET, '0.1/beta')
            self.assertEqual(code, 1, out)
            self.assertIn('features/beta.md', out)
            self.assertEqual(pm_bytes(root), before)


class Idempotence(unittest.TestCase):
    """Story criterion 4, and hard rule 3's bar for every write verb."""

    def test_running_it_twice_is_a_no_op_that_says_so(self):
        with tree() as root:
            referencing(root)
            self.assertEqual(run_cli(root, 'rename', TARGET, RENAMED)[0], 0)
            settled = pm_bytes(root)
            code, out = run_cli(root, 'rename', TARGET, RENAMED)
            self.assertEqual(code, 0, out)
            self.assertIn('nothing was written', out)
            self.assertEqual(pm_bytes(root), settled)
            # And the degenerate spelling: the id a grain already has.
            code, out = run_cli(root, 'rename', RENAMED, RENAMED)
            self.assertEqual(code, 0, out)
            self.assertIn('nothing was written', out)
            self.assertEqual(pm_bytes(root), settled)


class TheSweptKeysAreTheTreesOwn(unittest.TestCase):
    """How we know the field list is COMPLETE, rather than remembered.

    A ref this verb does not know about is a stale pointer nothing reports, so
    the list is held to the two places the tree declares its keys: the shipped
    templates, and the readers that resolve an id.
    """

    # Every other frontmatter key the templates carry, named rather than
    # pattern-matched — adding one is a decision about whether it is a ref.
    NOT_REFS = frozenset({'id', 'kind', 'name', 'status', 'owner', 'phase',
                          'branch',
                          # 0.6.0: free prose a human wrote, not an id. A
                          # sentence naming a renamed grain reads fine after
                          # the rename; rewriting inside it would edit English.
                          'changelog'})

    def test_every_template_key_is_swept_or_named_as_not_a_reference(self):
        with tree() as root:
            cfg = cfg_for(root)
            keys = set()
            for kind in model.FLOW_KINDS:
                lines = model._split(templates.load(cfg, kind))
                bounds = model._fence_bounds(lines)
                self.assertIsNotNone(bounds, kind)
                keys |= {line.split(':', 1)[0]
                         for line in lines[bounds[0] + 1:bounds[1]]
                         if ':' in line}
        self.assertTrue(len(keys) > 8, keys)
        self.assertEqual(keys - self.NOT_REFS - set(rename.REF_FIELDS), set())

    def test_every_id_a_reader_resolves_is_swept(self):
        declared = ({model.ORDER_KEY, validate.CAUSED_BY}
                    | set(validate.REF_KEYS)
                    | {field for _, field in model.BINDS_TO.values()})
        self.assertEqual(declared - set(rename.REF_FIELDS), set())
