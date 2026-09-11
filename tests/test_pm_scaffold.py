"""`pm new` / `pm templates` — scaffolding, slug hygiene, template minting,
and the no-deleter contract over the caller\'s own tree.

Split from test_pm.py by concern; the shared harness is tests/support/pm.py.

**Cut in 0.2.0 (feature `the-proof-is-named-in-the-criterion`, phase B):** the
per-kind and per-verb re-proofs of one templating rule — a slot filled for a
milestone and again for a feature, a header repaired and again not stacked, an
undecodable template refused by `new` and again by `decide`. What survives is
the shape rule 3 is about: **a refusal that writes NOTHING**, and a second run
that is a no-op.

**0.7.0: this module builds through `tree`, not `git_tree`.** It asks git no
question — `repo_root` walks up for a `.git` directory and no longer shells
out, so a marker is all a tree needs to be found (`support.pm._mark`). The
alias `git_tree as tree` used to sit on line 28 and bought every case here a
process it never used, which put 38 cases in the `shell` tier.
"""
from __future__ import annotations

import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

# The helper is aliased, not the module: `frontmatter` is the storage
# module every other caller spells, and a test file is not the place to
# teach a second name for it.
from support.pm import cfg_for, frontmatter as frontmatter_lines
from support.pm import run_cli, run_gate, write_config
from support.pm import tree


from agentic_sdlc.core import frontmatter
from agentic_sdlc.repo import vehicle
from agentic_sdlc.repo.pm import cli, inventory, templates, vocabulary

LEGACY_LOG = '# legacy log\n\nM1 said something.\n'


def both_streams(root: Path) -> tuple[int, str]:
    """`run_gate` with stderr too — a config REFUSAL prints there, so a
    stdout-only read would assert against an empty string."""
    import contextlib
    import io

    from agentic_sdlc.core.project import load_config, repo_root
    from agentic_sdlc.repo.checks import pm as pm_check
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = pm_check.run()
    return code, buf.getvalue()

# The pools, and where a grain's shared docs sit now: beside the document,
# under the document's own stem. `0.1.md` owns `0.1-decisions.md`, and that is
# the whole of the 0.4.0 rule these cases exercise — a grain is a DOCUMENT, so
# a slot is a sibling rather than a child.
MILESTONES = 'pm/roadmap/milestones'
FEATURES = 'pm/roadmap/features'


def shared(root: Path, gid: str, slot: str, pool: str = MILESTONES) -> Path:
    return root / pool / f'{gid}-{slot}'


class Scaffolding(unittest.TestCase):
    def test_new_grains_round_trip_into_a_clean_gate(self):
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'new', 'feature', '0.1', 'beta', 'Beta')[0], 0)
            self.assertEqual(
                run_cli(root, 'new', 'story', 'ft-beta', 'first', 'First')[0], 0)
            ff = root / 'pm/roadmap/features/ft-beta.md'
            # The MINTED id is the kind prefix and the slug; the parent is the
            # BINDING and is not in it.
            self.assertEqual(frontmatter.field_of(ff, 'id'), 'ft-beta')
            self.assertEqual(frontmatter.field_of(ff, 'milestone'), '0.1')
            self.assertEqual(run_cli(root, 'validate')[0], 0)
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('2 feature(s), 2 story/ies', out)

    def test_new_is_idempotent_over_an_existing_grain(self):
        # This is how a consumer MIGRATES. A tree of 22 milestones and 136
        # features cannot be hand-shaped, so re-running the scaffolder has to
        # fill gaps and leave every existing byte alone.
        with tree(story_statuses=('ready',)) as root:
            ff = root / 'pm/roadmap/features/alpha.md'
            before = ff.read_text(encoding='utf-8')
            code, out = run_cli(root, 'new', 'feature', '0.1', 'alpha')
            self.assertEqual(code, 0, out)
            self.assertEqual(ff.read_text(encoding='utf-8'), before)
            # The one file slot IS the document now, so "every slot is filled"
            # is the document being there.
            self.assertTrue(ff.is_file())

            # Second run: nothing left to do, and it says so.
            code, out = run_cli(root, 'new', 'feature', '0.1', 'alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('already has every canonical slot', out)
            self.assertEqual(ff.read_text(encoding='utf-8'), before)

    def test_new_handoff_mints_the_template_and_never_clobbers(self):
        """The gap that made 0.4.0's handoff a hand-authored 194-line restatement
        of `pm status`: the template SHIPPED, `SLOT_TEMPLATE` registered it, and
        no code path wrote it. `decisions.md` had a minting verb (`pm decide`);
        `handoff.md` had none, so an absent one was an empty canvas rather than
        an unfilled slot.

        Both halves matter. It mints from the template — otherwise the shape is
        reinvented every time. And it never clobbers: section 3 (`Traps this
        milestone has already sprung`) is the one thing in the tree no command
        can regenerate.
        """
        with tree(story_statuses=('ready',)) as root:
            doc = shared(root, '0.1', vocabulary.HANDOFF_FILE_NAME)
            self.assertFalse(doc.exists())
            code, out = run_cli(root, 'new', 'handoff', '0.1')
            self.assertEqual(code, 0, out)
            body = doc.read_text(encoding='utf-8')
            # Rendered, not copied: the placeholders are filled from the tree.
            self.assertTrue(
                body.startswith(vocabulary.SLOT_HEADER[vocabulary.HANDOFF_FILE_NAME]),
                body)
            self.assertIn('0.1', body)
            self.assertNotIn('{id}', body)
            self.assertNotIn('{name}', body)
            self.assertIn('Traps this milestone has already sprung', body)

            # Second run is a no-op over the author's own bytes.
            doc.write_text(body + '\n- the trap that cost two hours\n',
                           encoding='utf-8')
            keep = doc.read_text(encoding='utf-8')
            code, out = run_cli(root, 'new', 'handoff', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('already exists', out)
            self.assertEqual(doc.read_text(encoding='utf-8'), keep)

    def test_new_milestone_does_NOT_mint_a_handoff(self):
        """Deliberate, and the whole reason `check pm` can warn on the absence:
        a handoff auto-written into every milestone would put an unwritten
        template in every tree and destroy the signal. If this case ever fails,
        the warning it protects has become noise.
        """
        with tree(story_statuses=('ready',)) as root:
            doc = shared(root, '0.1', vocabulary.HANDOFF_FILE_NAME)
            doc.unlink(missing_ok=True)
            self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
            self.assertFalse(doc.exists(),
                             'new milestone minted a handoff nobody wrote')

    def test_a_legacy_uppercase_slot_is_refused_never_renamed_or_twinned(self):
        # The uppercase->lowercase migration is COMPLETE in every consumer and
        # the rename machinery is retired. The CHOSEN successor behavior: a
        # leftover case variant is a refusal that names it and the canonical
        # name — never a rename, and never a `decisions.md` minted beside
        # `DECISIONS.md` (a twin on a case-sensitive filesystem, a truncation
        # of the legacy bytes on an insensitive one).
        with tree(story_statuses=('ready',)) as root:
            pool = root / MILESTONES
            legacy = pool / '0.1-DECISIONS.md'
            frontmatter.write_raw(legacy, LEGACY_LOG)
            code, out = run_cli(root, 'new', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('REFUSED', out)
            self.assertIn('0.1-DECISIONS.md', out)
            self.assertIn('0.1-decisions.md', out)
            self.assertIn('nothing was written', out)
            entries = inventory.dir_entries(pool)
            # EXACT names: on macOS `exists('0.1-decisions.md')` answers True
            # off the 0.1-DECISIONS.md sitting there, so only a listing can
            # prove no twin was minted and no rename ran.
            self.assertEqual(entries.get('0.1-DECISIONS.md'), 'file')
            self.assertNotIn('0.1-decisions.md', entries)
            self.assertNotIn('0.1-handoff.md', entries)
            self.assertEqual(frontmatter.read_raw(legacy), LEGACY_LOG)

    def test_new_refuses_a_file_slot_that_exists_as_a_directory(self):
        # Rule 6 reserves exit 1 for FINDINGS, so an uncaught IsADirectoryError
        # reads to a consumer's hook as "drift found" with a traceback attached.
        # ScaffoldRefused is the shape, and it refuses before anything moves.
        with tree(story_statuses=('ready',)) as root:
            shared(root, '0.1', vocabulary.DECISION_FILE_NAME).mkdir()
            code, out = run_cli(root, 'new', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('REFUSED', out)
            self.assertIn('is a DIRECTORY', out)
            self.assertIn('nothing was written', out)
            self.assertFalse(shared(root, '0.1', 'handoff.md').exists())

    def test_new_refuses_a_slot_it_cannot_prepend_a_header_to(self):
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            return  # permission bits are not an obstruction as root
        # `_fill_header` guarded the READ and not the write, so a read-only
        # legacy doc raised `PermissionError` — a traceback, exit 1, and the
        # remaining slots never created. Writability is inspectable up front.
        with tree(story_statuses=('ready',)) as root:
            handoff = shared(root, '0.1', 'handoff.md')
            decisions = shared(root, '0.1', 'decisions.md')
            frontmatter.write_raw(handoff, 'legacy prose\n')
            frontmatter.write_raw(decisions, LEGACY_LOG)
            handoff.chmod(0o444)
            try:
                code, out = run_cli(root, 'new', 'milestone', '0.1')
                self.assertEqual(code, 1, out)
                self.assertIn('is not writable', out)
                self.assertIn('nothing was written', out)
                self.assertNotIn('Traceback', out)
                self.assertEqual(frontmatter.read_raw(decisions), LEGACY_LOG)
            finally:
                handoff.chmod(0o644)
            # And it goes through once the mode allows it.
            self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
            self.assertTrue(handoff.is_file())

    def test_new_refuses_an_undecodable_template_before_the_first_write(self):
        # A latin-1 byte in a project's `template_dir` raised
        # `UnicodeDecodeError` from inside the slot loop, two files in. Every
        # template the grain needs is loaded and decoded before anything lands.
        with tree(story_statuses=('ready',)) as root:
            (root / 'devkit.toml').write_text(
                '[pm]\ntemplate_dir = "pm/templates"\n', encoding='utf-8')
            self.assertEqual(run_cli(root, 'templates')[0], 0)
            (root / 'pm/templates/milestone.md').write_bytes(b'caf\xe9\n')
            (root / 'pm/roadmap/milestones/0.1.md').unlink()
            code, out = run_cli(root, 'new', 'milestone', '0.1', 'First')
            self.assertEqual(code, 1, out)
            self.assertIn('template cannot be read', out)
            self.assertIn('nothing was written', out)
            self.assertNotIn('Traceback', out)
            self.assertFalse((root / 'pm/roadmap/milestones/0.1.md').exists())

    def test_new_reports_a_write_that_no_listing_could_have_predicted(self):
        # Not everything is pre-inspectable — a mode changed under us, a disk
        # that fills. Rule 6 still holds: exit 1 is a finding a consumer's hook
        # can print, so the escaping exception becomes a refusal that names
        # exactly which slots did land rather than a stack trace over them.
        with tree(story_statuses=('ready',)) as root:
            doc = root / MILESTONES / 'ms-0.2.md'
            real = templates.write

            def flaky(path: Path, text: str) -> None:
                if path.name == 'ms-0.2.md':
                    raise OSError(28, 'No space left on device')
                real(path, text)

            with unittest.mock.patch.object(templates, 'write', flaky):
                code, out = run_cli(root, 'new', 'milestone', '0.2', 'Second')
            self.assertEqual(code, 1, out)
            self.assertNotIn('Traceback', out)
            self.assertIn('No space left on device', out)
            self.assertIn('PART-FILLED', out)
            # The grain file is the FIRST write, so the honest report is that
            # nothing had landed — the claim has to track the truth in both
            # directions, not only when something did.
            self.assertIn('nothing had been written yet', out)
            self.assertFalse(doc.exists())

    def test_new_refuses_a_slot_that_is_a_symlink_out_of_the_grain(self):
        # `_fill_header` followed it and rewrote a file the verb was never
        # pointed at. A write verb stays inside the grain it was asked to fill.
        with tree(story_statuses=('ready',)) as root:
            outside = root / 'outside.md'
            frontmatter.write_raw(outside, 'OUTSIDE\n')
            shared(root, '0.1', 'decisions.md').symlink_to(outside)
            code, out = run_cli(root, 'new', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('is a SYMLINK', out)
            self.assertIn('nothing was written', out)
            self.assertEqual(frontmatter.read_raw(outside), 'OUTSIDE\n')
            self.assertFalse(shared(root, '0.1', 'handoff.md').exists())

    def test_new_mints_no_shared_doc_and_repairs_the_header_of_one_present(self):
        # BOTH halves. `pm new` stopped CREATING a shared doc — that scaffolded
        # 204 empty files into one consumer's tree — and still MANAGES one that
        # exists, which is what a migration needs. And the repair is
        # idempotent: a doc that already carries its header never gets a second
        # one stacked on it.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
            for slot in vocabulary.MILESTONE_OPTIONAL_SLOTS:
                self.assertFalse(shared(root, '0.1', slot).exists(), slot)
            for slot, want in vocabulary.SLOT_HEADER.items():
                doc = shared(root, '0.1', slot)
                doc.write_text('# headerless\n', encoding='utf-8')
                self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
                self.assertEqual(inventory.header_of(doc), want, slot)
                self.assertIn('# headerless', doc.read_text(encoding='utf-8'))
                repaired = doc.read_text(encoding='utf-8')
                self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
                self.assertEqual(doc.read_text(encoding='utf-8'), repaired,
                                 f'{slot} grew a second header')
            # And over a RETIRED wording, which is the half the gate case
            # cannot reach. `test_a_doc_opening_with_a_RETIRED_header_still_
            # passes` (tests/test_grain_shape.py) only runs `check grain-shape`,
            # and the gate reads `KNOWN_SLOT_HEADERS` independently of the
            # writer — so `_header_wanted` could stop honouring a retired
            # wording, both tiers stayed green, and `pm new` stacked a second
            # header onto every doc written under the old words on upgrade day
            # (bg-a-proof-row-names-a-case-that-proves-half).
            retired = sorted(vocabulary.RETIRED_SLOT_HEADERS)
            self.assertTrue(retired, 'a retired wording must stay recognised '
                                     'once one exists — with the set empty '
                                     'the loop below asks nothing')
            for header in retired:
                for slot in vocabulary.SLOT_HEADER:
                    doc = shared(root, '0.1', slot)
                    doc.write_text(f'{header}\n\n# 0.1 demo\n',
                                   encoding='utf-8')
                    before = doc.read_bytes()
                    self.assertEqual(
                        run_cli(root, 'new', 'milestone', '0.1')[0], 0)
                    self.assertEqual(
                        doc.read_bytes(), before,
                        f'{slot} grew a second header over the retired '
                        f'wording {header!r}')
                    self.assertEqual(inventory.header_of(doc), header, slot)

    def test_a_name_the_filesystem_refuses_is_a_refusal_not_a_traceback(self):
        # The grain's own filename is the last unguarded write: a name too
        # long for the filesystem came out as an OSError traceback under exit
        # 1, and exit 1 is what a consumer's pre-push hook reads as "drift
        # found". `id_defect` answers it before the pool is even walked.
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'new', 'milestone', '0.2-' + 'a' * 300,
                                'Too Long')
            self.assertEqual(code, 1, out)
            self.assertNotIn('Traceback', out)
            self.assertIn('REFUSED', out)
            self.assertIn('past the', out)
            self.assertIn('nothing was written', out)
            self.assertEqual(
                [f.name for f in inventory.pool_walk(cfg_for(root), 'milestone')],
                ['0.1.md'])

    def test_new_story_and_new_bug_refuse_a_name_the_filesystem_rejects(self):
        # Those two write straight rather than through the scaffolder, so
        # neither guard `new` grew ever covered them.
        with tree(story_statuses=('ready',)) as root:
            for argv in (('new', 'story', '0.1/alpha', 'a' * 300, 'S'),
                         ('new', 'bug', '0.1', 'a' * 300)):
                code, out = run_cli(root, *argv)
                self.assertEqual(code, 1, out)
                self.assertNotIn('Traceback', out)
                self.assertIn('nothing was written', out)

    def test_the_same_pm_new_refuses_on_every_supported_python(self):
        # `Path.exists()` raises OSError on an over-long name up to 3.13 and
        # answers False from 3.14 on, so the verb came out as a traceback or as
        # a refusal depending on which interpreter `uvx` picked.
        from agentic_sdlc.repo.pm import cli as pm_cli
        with tree(story_statuses=('ready',)) as root:
            self.assertFalse(pm_cli._exists(root / ('a' * 300)))


class NewKeepsTheTreesOwnLayout(unittest.TestCase):
    """`pm new` on a NESTED tree must not mint into a pool.

    `is_pooled` is "does any pool hold a document", so one `pm new story` on an
    unmigrated checkout made it TRUE — and every reader then saw that one file
    and none of the tree behind it. Measured on the real pre-migration tree:
    `check pm` went from PASS over 4 milestones / 44 features / 79 stories to
    `FAIL — no milestones found under pm/roadmap/ (wrong [pm] roadmap_dir…)`,
    blaming a config key that was correct.

    The compat promise is that a consumer's tree works the day they bump, and a
    scaffold that blinds it is the loudest possible way to break that.
    """

    def _nested(self, root: Path) -> Path:
        """The pooled fixture, moved back to grain directories."""
        rm = root / 'pm/roadmap'
        mdir = rm / '0.1-demo'
        (mdir / 'features/alpha/stories').mkdir(parents=True)
        (rm / 'milestones/0.1.md').rename(mdir / 'milestone.md')
        (rm / 'features/alpha.md').rename(mdir / 'features/alpha/feature.md')
        (rm / 'stories/s0.md').rename(mdir / 'features/alpha/stories/s0.md')
        for pool in ('milestones', 'features', 'stories'):
            for leftover in (rm / pool).iterdir():
                leftover.unlink()
            (rm / pool).rmdir()
        return mdir

    def test_a_nested_tree_keeps_its_shape_and_stays_readable(self):
        with tree(story_statuses=('ready',)) as root:
            mdir = self._nested(root)
            self.assertFalse(inventory.is_pooled(cfg_for(root)))
            code, out = run_cli(root, 'new', 'story', '0.1/alpha', 'probe', 'P')
            self.assertEqual(code, 0, out)
            self.assertTrue(
                (mdir / 'features/alpha/stories/st-probe.md').is_file(), out)
            self.assertFalse((root / 'pm/roadmap/stories').exists(), out)
            # The tree is still READ as nested, which is the half that broke.
            self.assertFalse(inventory.is_pooled(cfg_for(root)))
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)
            self.assertIn('2 story/ies', out)

    def test_a_POOLED_tree_still_mints_into_the_pool(self):
        # The other half, so the fix cannot be "always nested".
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(
                run_cli(root, 'new', 'story', '0.1/alpha', 'probe', 'P')[0], 0)
            self.assertTrue((root / 'pm/roadmap/stories/st-probe.md').is_file())


class NoDeleter(unittest.TestCase):
    """The tracker mostly REPORTS; the one verb that deletes NAMES its target.

    Reproduced on the default roster before `prune` was removed: an OPEN bug
    filed under a `done` milestone, `check pm` PASS, `pm prune`, and the bug
    file was gone. The rule that was supposed to make that impossible (an open
    bug under a done milestone) was opt-in and neither consumer enabled it, so
    nothing at all stood between the two commands. `prune` stays gone, and the
    guard below is what keeps it gone: the tree-level reproduction cost a `git
    init` and a commit to prove what an AST-shaped read of the CLI proves
    outright.

    If archive sprawl needs an answer it is a READ verb — that is still true.
    `pm retire <milestone-id>` is the OPPOSITE shape from `prune`: one
    milestone, spelled out on the command line by the caller every time,
    never a sweep the tool decides the scope of on its own.
    """

    # `cmd_retire` and the helper that NAMES its targets. Under pools a
    # milestone is not a directory, so retiring it is N file deletes rather
    # than one tree delete — the same set of bytes, addressed by binding. Both
    # functions are exempt; every other line in the CLI is not.
    RETIRE_FUNCTIONS = ('def cmd_retire(', 'def _retired_files(')

    def test_the_pm_cli_carries_no_recursive_delete_OUTSIDE_cmd_retire(self):
        # The shape, not the instance: any function OTHER than the two that
        # ARE `pm retire`'s implementation reaching for one of these is
        # `prune` wearing a different name. Narrowed to those bodies — not
        # dropped — so the guard still catches a delete that turns up in
        # `cmd_bug` or anywhere else future work adds a verb.
        source = Path(cli.__file__).read_text(encoding='utf-8')
        lines = source.split('\n')
        retire_body, rest = [], list(lines)
        for opener in self.RETIRE_FUNCTIONS:
            start = next(i for i, line in enumerate(rest)
                         if line.startswith(opener))
            end = next(i for i in range(start + 1, len(rest))
                       if rest[i].startswith('def '))
            retire_body.extend(rest[start:end])
            rest = rest[:start] + rest[end:]
        retire_body = '\n'.join(retire_body)
        rest = '\n'.join(rest)
        for spelling in ('remove_tree', 'rmtree', "'rm'", 'unlink',
                         'delete_tree', 'delete_file'):
            self.assertNotIn(spelling, rest,
                             f'{spelling} is back in the pm CLI outside '
                             f'cmd_retire')
        self.assertIn('delete_file', retire_body,
                      "cmd_retire no longer deletes anything — this test's "
                      'own fixture has gone stale')


class TheMintedIdIsThePrefixAndTheSlug(unittest.TestCase):
    """`bg-the-new-verbs-mint-a-compound-id`, GitHub #8.

    `pm new` minted `<mid>/<slug>` while `tools/dev/pm_migrate.py` minted
    `<kind-prefix>-<slug>` off `inventory.KIND_PREFIX`, so a migrated tree grew
    BOTH vocabularies, one grain at a time, and nothing went red. The id also
    restated the binding that `milestone:`/`feature:` already carried, which
    made re-parenting a `pm rename` plus a whole-tree ref sweep — the cost
    0.4.0 deleted when it retired `pm move`.

    Nothing here grades an id's SHAPE and nothing should: a prefix or a version
    in an id is the project's taste (rule 9). What is asserted is that the
    ENGINE has one minting path.
    """

    def _milestone(self, root: Path) -> None:
        self.assertEqual(run_cli(root, 'new', 'milestone', 'later', 'Later')[0], 0)

    def test_every_kind_mints_what_the_migration_would_have_minted(self):
        # Compared against `inventory.mint_id` rather than four literals: the claim
        # is that the two paths are ONE function, and two hard-coded strings
        # would still pass the day they diverge again.
        with tree(story_statuses=('ready',)) as root:
            for argv, kind, slug, doc in (
                    (('new', 'milestone', 'later', 'Later',
                      '--version', '9.9'),
                     'milestone', 'later', MILESTONES),
                    (('new', 'feature', '0.1', 'census', 'Census'),
                     'feature', 'census', FEATURES),
                    (('new', 'story', '0.1/alpha', 'boots', 'Boots'),
                     'story', 'boots', 'pm/roadmap/stories'),
                    (('new', 'bug', '0.1', 'oops'),
                     'bug', 'oops', 'pm/roadmap/bugs')):
                with self.subTest(kind=kind):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 0, out)
                    gid = inventory.mint_id(kind, slug)
                    self.assertEqual(gid, f'{inventory.KIND_PREFIX[kind]}-{slug}')
                    path = root / doc / f'{gid}.md'
                    self.assertTrue(path.is_file(), out)
                    self.assertEqual(frontmatter.unquote(frontmatter.field_of(path, 'id')),
                                     gid)
                    # The PARENT is not in it, at any level.
                    self.assertNotIn('/', gid)
            # The unlanded half of #8: a milestone's VERSION is the same shape
            # of fact as a parent — a field the scaffold writes, never a piece
            # of the id it mints.
            mfile = root / MILESTONES / 'ms-later.md'
            self.assertEqual(frontmatter.field_of(mfile, 'version'), '9.9')
            self.assertNotIn('9.9', frontmatter.unquote(frontmatter.field_of(mfile, 'id')))
            self.assertEqual(run_cli(root, 'validate')[0], 0)

    def test_the_parent_is_the_binding_field_and_re_parenting_is_one_set(self):
        # The functional claim the bug is actually about: the id is stable for
        # life, so moving a grain to another milestone is `pm set`, not
        # `pm rename` plus a ref sweep.
        with tree(story_statuses=('ready',)) as root:
            self._milestone(root)
            self.assertEqual(
                run_cli(root, 'new', 'feature', '0.1', 'census', 'C')[0], 0)
            ff = root / FEATURES / 'ft-census.md'
            self.assertEqual(
                frontmatter.unquote(frontmatter.field_of(ff, 'milestone')), '0.1')
            before = frontmatter.unquote(frontmatter.field_of(ff, 'id'))
            self.assertEqual(
                run_cli(root, 'set', 'ft-census', 'milestone', 'ms-later')[0], 0)
            self.assertEqual(
                frontmatter.unquote(frontmatter.field_of(ff, 'milestone')), 'ms-later')
            self.assertEqual(frontmatter.unquote(frontmatter.field_of(ff, 'id')), before)

    def test_a_version_is_optional_idempotent_and_refused_whole(self):
        # The write verb's three obligations for the new flag, on one tree:
        # omitting it is BACKLOG rather than a finding (R2), re-stamping the
        # same value is a no-op to the byte (rule 3), and a value that would
        # inject a line into the frontmatter is refused with nothing written —
        # the bar `pm set` already holds for a scalar.
        with tree(story_statuses=('ready',)) as root:
            backlog = root / MILESTONES / 'ms-backlog.md'
            code, out = run_cli(root, 'new', 'milestone', 'backlog', 'Backlog')
            self.assertEqual(code, 0, out)
            self.assertEqual(frontmatter.field_of(backlog, 'version'), '')

            code, out = run_cli(root, 'new', 'milestone', 'backlog',
                                '--version', '0.2')
            self.assertEqual(code, 0, out)
            self.assertIn('stamped on', out)
            stamped = frontmatter.read_raw(backlog)
            self.assertEqual(frontmatter.field_of(backlog, 'version'), '0.2')
            code, out = run_cli(root, 'new', 'milestone', 'backlog',
                                '--version', '0.2')
            self.assertEqual(code, 0, out)
            self.assertEqual(frontmatter.read_raw(backlog), stamped)

            code, out = run_cli(root, 'new', 'milestone', 'oops', 'Oops',
                                '--version', '0.3\nowner: someone-else')
            self.assertEqual(code, 1, out)
            self.assertIn('one line', out)
            self.assertIn('nothing was written', out)
            self.assertNotIn('Traceback', out)
            self.assertFalse((root / MILESTONES / 'ms-oops.md').exists())

    def test_a_slug_already_carrying_its_prefix_is_not_doubled(self):
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(
                run_cli(root, 'new', 'bug', '0.1', 'bg-already')[0], 0)
            self.assertTrue((root / 'pm/roadmap/bugs/bg-already.md').is_file())
            self.assertFalse(
                (root / 'pm/roadmap/bugs/bg-bg-already.md').exists())

    def test_a_bug_this_verb_mints_is_movable_by_the_bug_verb(self):
        # Collateral, and load-bearing: `pm bug <status> <id>` required
        # `/bugs/` IN THE ID, so every flat `bg-` id the migration mints was
        # unmovable — and this verb now mints those. A create path whose
        # product no verb can move is a create path that does not work.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'new', 'bug', '0.1', 'oops')[0], 0)
            code, out = run_cli(root, 'bug', 'fixed', 'bg-oops')
            self.assertEqual(code, 0, out)
            self.assertEqual(
                frontmatter.field_of(root / 'pm/roadmap/bugs/bg-oops.md', 'status'),
                'fixed')
            # And the kind guard the id-shape test stood in for still holds:
            # a FEATURE id cannot be written through the bug flow.
            code, out = run_cli(root, 'bug', 'fixed', '0.1/alpha')
            self.assertEqual(code, 2, out)
            self.assertIn('no bug resolves', out)

    def test_a_grain_authored_on_0_4_0_is_re_scaffolded_not_duplicated(self):
        # The compat half. A consumer's tree holds `<mid>/<slug>` ids; the same
        # `pm new` they ran before the bump must keep FILLING that document
        # rather than minting a second one beside it (rule 3).
        with tree(story_statuses=('ready',)) as root:
            fdir = root / FEATURES
            before = sorted(p.name for p in fdir.iterdir())
            code, out = run_cli(root, 'new', 'feature', '0.1', 'alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('already has every canonical slot', out)
            self.assertEqual(sorted(p.name for p in fdir.iterdir()), before)
            self.assertFalse((fdir / 'ft-alpha.md').exists())

    def test_a_create_with_no_name_names_the_argument_not_a_missing_grain(self):
        # *"feature 'x' does not exist yet — a new one needs a name"* read as
        # THIS GRAIN IS MISSING and sent readers looking for a lost file. The
        # refusal leads with the argument that was omitted.
        with tree(story_statuses=('ready',)) as root:
            for argv in (('new', 'milestone', 'nameless'),
                         ('new', 'feature', '0.1', 'nameless')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 2, out)
                    self.assertIn(cli.NAME_ARG, out)
                    self.assertIn('is required', out)
                    self.assertNotIn('does not exist yet', out)
                    self.assertNotIn('needs a name', out)
                    # Review R3: the words held while the printed command did
                    # not run — the feature's parent and slug went out as ONE
                    # quoted argument. The argv it hands the verb is the proof.
                    printed = out.split(f'{cli.NAME_ARG} is required: `', 1)[1]
                    self.assertEqual(
                        vehicle.argv_of(printed.split('`', 1)[0]),
                        ['pm', *argv, cli.NAME_ARG], out)

    def test_the_help_marks_the_name_required_on_every_create(self):
        # Rule 11's read side: the synopsis showed `[<name...>]` while the verb
        # refused without it, so the flag people omitted looked optional.
        for line in ('new milestone <slug> <name...>',
                     'new feature <milestone> <slug> <name...>',
                     'new story <feature-id> <slug> <name...>'):
            with self.subTest(line=line):
                self.assertIn(line, cli.USAGE)
                self.assertNotIn(line.replace(cli.NAME_ARG,
                                              f'[{cli.NAME_ARG}]'), cli.USAGE)


class TheScaffolderNeverMintsATwiceClaimedId(unittest.TestCase):
    """`pm new story` refuses rather than overwriting, and writes nothing.

    This class was `OrdinalPrefixedStoriesScaffoldValid`: `story_ordinal_prefix`
    made the scaffolder stamp a STRIPPED id, and V2 — which compared the id to
    the stripped stem — then rejected every story it wrote. The key and the rule
    both retired in 0.4.0 (identity is `id:`, and sequence is the parent's
    `order:`), so what is left is the guard that was never about ordinals: two
    files claiming one id is addressable by neither.
    """

    def test_a_second_file_claiming_one_id_refuses_without_writing(self):
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(
                run_cli(root, 'new', 'story', '0.1/alpha', 'boots', 'B')[0], 0)
            sdir = root / 'pm/roadmap/stories'
            before = sorted(p.name for p in sdir.iterdir())
            code, out = run_cli(root, 'new', 'story', '0.1/alpha', 'boots', 'B')
            self.assertEqual(code, 1, out)
            self.assertIn('already', out)
            self.assertEqual(sorted(p.name for p in sdir.iterdir()), before)

    def test_a_leading_ordinal_is_part_of_the_slug_and_validates(self):
        # No stripping anywhere: the file is `01-boots.md`, the id ends in
        # `01-boots`, and every reader keys on the id it actually carries.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(
                run_cli(root, 'new', 'story', '0.1/alpha', '01-boots', 'B')[0], 0)
            sf = root / 'pm/roadmap/stories/st-01-boots.md'
            self.assertEqual(frontmatter.field_of(sf, 'id'), 'st-01-boots')
            self.assertEqual(run_cli(root, 'validate')[0], 0)
            self.assertEqual(
                run_cli(root, 'story', 'building', 'st-01-boots')[0], 0)


class BugNamesItsCause(unittest.TestCase):
    """`caused_by:` — the feature whose change produced the bug.

    `milestone:` says which parent HOLDS it; `caused_by:` says which feature
    MADE it. Different facts — the first is the binding every kind has, the
    second is a relation between two grains like `depends_on:` — which is the
    whole reason the field is not a second spelling of the one already there.

    The frontmatter assertions below are the scaffold's contract, and at
    0.6.0/D11 they lost `caught_in:` and `fix_milestone:`: the argument is the
    PARENT and is written to `milestone:` alone.
    """

    BUGS = 'pm/roadmap/bugs'

    def _bug_dir(self, root: Path) -> list[str]:
        bugs = root / self.BUGS
        return sorted(p.name for p in bugs.iterdir()) if bugs.is_dir() else []

    def test_the_field_is_minted_empty_stamped_when_asked_and_validates(self):
        # The template's default is an empty `caused_by:` (no trailing space):
        # the honest record of a cause nobody has named. The field exists so
        # `pm set` and the report have somewhere to look, not so it gets
        # guessed at. Both flag spellings stamp the same value, and the stamped
        # bug leaves `validate` and the gate clean.
        with tree(story_statuses=('ready',)) as root:
            code, out = run_cli(root, 'new', 'bug', '0.1', 'unattributed')
            self.assertEqual(code, 0, out)
            # No name given: still created (the form scripts rely on), and the
            # empty `name:` is NAMED with the write that fills it (rule 11).
            # Free text, single-quoted at both parses (D2).
            self.assertIn("next: `make pm ARGS='set bg-unattributed name "
                          "'\"'\"'<name>'\"'\"''`", out)
            self.assertEqual(frontmatter_lines(root / self.BUGS / 'bg-unattributed.md'), [
                'id: bg-unattributed',
                # 0.4.0: a grain states its own kind, so nothing has to infer
                # one from where the file happens to sit.
                'kind: bug',
                'milestone: "0.1"',
                'name:',
                'status: open',
                'caused_by:',
                'changelog:',
            ])
            code, out = run_cli(root, 'new', 'bug', '0.1', 'seed-is-zero',
                                '--caused-by', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertEqual(frontmatter_lines(root / self.BUGS / 'bg-seed-is-zero.md'), [
                'id: bg-seed-is-zero',
                'kind: bug',
                'milestone: "0.1"',
                'name:',
                'status: open',
                'caused_by: 0.1/alpha',
                'changelog:',
            ])
            self.assertIn("caused_by '0.1/alpha'", out)
            self.assertEqual(run_cli(root, 'new', 'bug', '0.1', 'joined',
                                     '--caused-by=0.1/alpha')[0], 0)
            self.assertEqual(
                frontmatter.field_of(root / self.BUGS / 'bg-joined.md', 'caused_by'),
                '0.1/alpha')
            # #24: `<name...>` after the slug is written to `name:`, and the
            # flag still pairs wherever it sits.
            code, out = run_cli(root, 'new', 'bug', '0.1', 'named', 'the',
                                'seed', '--caused-by', '0.1/alpha', 'is', 'zero')
            self.assertEqual(code, 0, out)
            named = root / self.BUGS / 'bg-named.md'
            self.assertEqual(frontmatter.field_of(named, 'name'),
                             'the seed is zero')
            self.assertEqual(frontmatter.field_of(named, 'caused_by'), '0.1/alpha')
            # A multi-line name would inject frontmatter: refused, unwritten,
            # at exit 2 like the backfill's `--name` (N10).
            code, out = run_cli(root, 'new', 'bug', '0.1', 'forged',
                                'x\nstatus: fixed')
            self.assertEqual(code, 2, out)
            self.assertIn('nothing was written', out)
            self.assertFalse((root / self.BUGS / 'bg-forged.md').exists())
            # Whitespace collapses, as the backfill's name does (N7): a blank
            # name is no name, and a tab never reaches a `pm list` column.
            for slug, words, want in (('blank', ('   ',), ''),
                                      ('tabbed', ('a\tb ', ' c'), 'a b c')):
                self.assertEqual(run_cli(root, 'new', 'bug', '0.1', slug,
                                         *words)[0], 0)
                self.assertEqual(frontmatter.field_of(
                    root / self.BUGS / f'bg-{slug}.md', 'name'), want)
            self.assertEqual(run_cli(root, 'validate')[0], 0)
            self.assertEqual(run_gate(root)[0], 0)
            # The sizing trap: a project template with NO `{name}` slot and
            # no `name:` line at all — what a render alone would silently drop.
            write_config(root, '[pm]\ntemplate_dir = "pm/templates"\n')
            tdir = root / 'pm/templates'
            tdir.mkdir(parents=True)
            (tdir / 'bug.md').write_text(
                '---\nid: {id}\nkind: {kind}\nmilestone: "{milestone}"\n'
                'status: open\n---\n\n# {slug}\n', encoding='utf-8')
            code, out = run_cli(root, 'new', 'bug', '0.1', 'slotless',
                                'Nameless', 'template')
            self.assertEqual(code, 0, out)
            self.assertEqual(frontmatter_lines(root / self.BUGS / 'bg-slotless.md'), [
                'id: bg-slotless', 'kind: bug', 'milestone: "0.1"',
                'status: open', 'name: Nameless template'])
            # A template WITH the slot and no name given: the slot renders
            # empty, which is what the `next:` line says, never `{name}` (M6).
            (tdir / 'bug.md').write_text(
                '---\nid: {id}\nkind: {kind}\nmilestone: "{milestone}"\n'
                'name: {name}\nstatus: open\n---\n\n# {name}\n',
                encoding='utf-8')
            code, out = run_cli(root, 'new', 'bug', '0.1', 'slotq0')
            self.assertEqual(code, 0, out)
            self.assertIn('`name:` is empty', out)
            slotted = root / self.BUGS / 'bg-slotq0.md'
            self.assertNotIn('{name}', slotted.read_text(encoding='utf-8'))
            self.assertEqual(frontmatter.field_of(slotted, 'name'), '')

    # --- the refusal matrix ---------------------------------------------------
    # Every one of these exits 2 naming the value, and NONE of them writes: the
    # cause is resolved before the slug is checked and long before the file is
    # minted, so a bug is never filed carrying an unresolvable attribution.
    UNRESOLVABLE = (
        ('traversal', '../../../pwned'),
        ('traversal-inside-an-id', '0.1/../../oops'),
        ('dot-segment', '0.1/.'),
        ('absolute', '/etc/passwd'),
        ('glob', '0.1/*'),
        ('glob-in-the-milestone', '*/alpha'),
        ('backslash', '0.1\\alpha'),
        ('leading-whitespace', '0.1/ alpha'),
        ('trailing-whitespace', '0.1/alpha '),
        ('inner-whitespace', '0.1/al pha'),
        ('newline', '0.1/alpha\nname: pwned'),
        ('over-long', '0.1/' + 'a' * 300),
        ('a-story-id', '0.1/alpha/s0'),
        ('a-milestone-id', '0.1'),
        ('a-bug-id', '0.1/bugs/other'),
        ('no-such-feature', '0.1/never-existed'),
        ('scheme', 'file:///etc/passwd'),
    )

    def test_an_unresolvable_cause_exits_2_and_writes_nothing(self):
        with tree(story_statuses=('ready',)) as root:
            before_tree = sorted(p.name for p in root.iterdir())
            for label, value in self.UNRESOLVABLE:
                with self.subTest(case=label):
                    code, out = run_cli(root, 'new', 'bug', '0.1', 'x',
                                        '--caused-by', value)
                    self.assertEqual(code, 2, out)
                    self.assertNotIn('Traceback', out)
                    self.assertIn('resolves to no feature', out)
                    self.assertIn('nothing was written', out)
                    self.assertEqual(self._bug_dir(root), [])
            self.assertEqual(sorted(p.name for p in root.iterdir()), before_tree)

    def test_a_flag_that_carries_no_id_refuses_and_never_eats_the_slug(self):
        # `--caused-by=` storing '' would file the bug with the field silently
        # unset, at exit 0, after the caller asked for it — and `--caused-by
        # <id>` is consumed as a PAIR, so what is left is the milestone, the
        # slug and the name: the id never becomes a word of the name (#24).
        with tree() as root:
            positional = "make pm ARGS='new bug <milestone> <slug>"
            for argv, phrase in (
                    (('new', 'bug', '0.1', 'x', '--caused-by', ''),
                     'needs a feature id'),
                    (('new', 'bug', '0.1', 'x', '--caused-by='),
                     'needs a feature id'),
                    (('new', 'bug', '0.1', '--caused-by'), 'needs a feature id'),
                    # M2: #24's own spelling. There is no `--name`; a flag in
                    # the name is refused naming the positional form, never
                    # stamped as `name: --name The Title`.
                    (('new', 'bug', '0.1', 'x', '--name', 'The Title'),
                     positional),
                    (('new', 'bug', '0.1', 'x', '--name=The Title'), positional)):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 2, out)
                    self.assertIn(phrase, out)
                    self.assertEqual(self._bug_dir(root), [])
            code, out = run_cli(root, 'new', 'bug', '0.1', 'x', 'y',
                                '--caused-by', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertEqual(self._bug_dir(root), ['bg-x.md'])
            bug = root / self.BUGS / 'bg-x.md'
            self.assertEqual(frontmatter.field_of(bug, 'name'), 'y')
            self.assertEqual(frontmatter.field_of(bug, 'caused_by'), '0.1/alpha')


class NewRefusesUnsafeSlugs(unittest.TestCase):
    def test_a_slug_is_one_path_component_never_a_path(self):
        with tree() as root:
            before = sorted(p.name for p in root.iterdir())
            for bad in ('../../../pwned', 'a/b', '..', '-dash', 'glob*'):
                with self.subTest(bad=bad):
                    code, _ = run_cli(root, 'new', 'bug', '0.1', bad)
                    self.assertEqual(code, 1)
            # The milestone VERSION goes through the same guard.
            self.assertEqual(
                run_cli(root, 'new', 'milestone', '../../oops', 'Name')[0], 1)
            self.assertEqual(sorted(p.name for p in root.iterdir()), before)

    # The NAME, every create's last input (`bg-a-scaffold-name-injects-
    # frontmatter`): a CR or LF writes a second frontmatter line — a grain
    # born reading `done` — and a flag-shaped first word is a flag no create
    # takes. One guard for all four kinds, exit 2, nothing written.
    NAME_REFUSED = (
        ('LF', ('Title\nstatus: done',)),
        ('CR', ('Title\rstatus: done',)),
        ('CRLF in a later word', ('Title', 'x\r\nstatus: done')),
        ('--name', ('--name', 'The Title')),
        ('--name=', ('--name=The Title',)),
        ('short flag', ('-x', 'Title')),
        ('bare dash', ('-',)),
        ('flag behind whitespace', ('  --name Title',)),
    )
    CREATES = (('milestone', ('inj',)), ('feature', ('0.1', 'inj')),
               ('story', ('0.1/alpha', 'inj')), ('bug', ('0.1', 'inj')))

    def test_a_name_is_one_line_and_never_a_flag_on_every_create(self):
        with tree() as root:
            def snapshot():
                return sorted((p.relative_to(root), p.read_bytes())
                              for p in root.rglob('*') if p.is_file())
            before = snapshot()
            for kind, head in self.CREATES:
                for label, words in self.NAME_REFUSED:
                    with self.subTest(kind=kind, case=label):
                        code, out = run_cli(root, 'new', kind, *head, *words)
                        self.assertEqual(code, 2, out)
                        self.assertIn('nothing was written', out)
                        if ' '.join(words).split()[0].startswith('-'):
                            self.assertIn(f"make pm ARGS='new {kind} ", out)
                            self.assertIn(cli.NAME_ARG, out)
            # The FILL path — an id already in the tree — holds the same bar.
            code, out = run_cli(root, 'new', 'feature', '0.1', 'alpha',
                                'x\nstatus: done')
            self.assertEqual(code, 2, out)
            self.assertEqual(snapshot(), before)
            # Adversarial, against "one line": U+2028 is a line break to
            # `str.splitlines`, and it collapses to a space like any other
            # whitespace, so it never becomes a line either.
            code, out = run_cli(root, 'new', 'feature', '0.1', 'sep',
                                'Title\u2028status: done')
            self.assertEqual(code, 0, out)
            feature = root / 'pm/roadmap/features/ft-sep.md'
            self.assertEqual(frontmatter.field_of(feature, 'name'),
                             'Title status: done')
            self.assertNotEqual(frontmatter.field_of(feature, 'status'), 'done')


class Templates(unittest.TestCase):
    def test_a_new_milestone_gets_its_grain_file_under_the_exact_name(self):
        # EXACT names, from a listing: `is_file()` here passed on macOS against
        # the OLD uppercase spellings long after the rename landed, and would
        # have failed in CI on Linux. The slot names are the assertion.
        with tree() as root:
            run_cli(root, 'new', 'milestone', '0.2', 'Second')
            entries = inventory.dir_entries(root / MILESTONES)
            self.assertEqual(entries.get('ms-0.2.md'), 'file', entries)
            # And no shared doc rode along beside it.
            for slot in vocabulary.MILESTONE_OPTIONAL_SLOTS:
                self.assertNotIn(f'ms-0.2-{slot}', entries)
            self.assertIn('# ms-0.2 — Second',
                          (root / MILESTONES / 'ms-0.2.md').read_text())

    def test_templates_command_refuses_to_write_past_a_case_variant(self):
        # `is_file()` on macOS answers `decisions.md` with a leftover
        # `DECISIONS.md`, so the install skipped the very name `load` reads —
        # the project's customised template silently ignored, and no message
        # naming the spelling to port it to. Writing it anyway is worse still:
        # `open('decisions.md', 'w')` TRUNCATES the variant sitting there.
        with tree() as root:
            (root / 'devkit.toml').write_text(
                '[pm]\ntemplate_dir = "pm/templates"\n', encoding='utf-8')
            tdir = root / 'pm/templates'
            tdir.mkdir(parents=True)
            mine = 'MINE — a customised decisions template\n'
            frontmatter.write_raw(tdir / 'DECISIONS.md', mine)
            code, out = run_cli(root, 'templates')
            self.assertEqual(code, 0, out)
            self.assertIn('is a case variant of decisions.md', out)
            self.assertIn('git mv --force', out)
            self.assertEqual(frontmatter.read_raw(tdir / 'DECISIONS.md'), mine)
            self.assertNotIn('decisions.md', inventory.dir_entries(tdir))

            # The same rule for a template that is merely CUSTOMISED: copying
            # them out a second time never clobbers what a project edited.
            (tdir / 'feature.md').write_text('mine\n', encoding='utf-8')
            self.assertEqual(run_cli(root, 'templates')[0], 0)
            self.assertEqual((tdir / 'feature.md').read_text(), 'mine\n')

            # Renamed, it is the template the log is MINTED from — the whole
            # point. Through a temp name: a direct rename is a no-op on macOS.
            (tdir / 'DECISIONS.md').rename(tdir / 'x.tmp')
            (tdir / 'x.tmp').rename(tdir / 'decisions.md')
            self.assertEqual(run_cli(root, 'new', 'milestone', '0.3', 'Third')[0], 0)
            self.assertEqual(run_cli(root, 'decide', 'ms-0.3', 'a choice')[0], 0)
            self.assertIn('MINE', frontmatter.read_raw(
                shared(root, 'ms-0.3', 'decisions.md')))

    def test_a_project_template_is_used_verbatim_and_owns_only_its_own_grain(self):
        # Three claims about one template dir, because they are one rule: the
        # project's file wins, whatever it says wins with it (the guard here
        # forbade a project's OWN template from minting a grain past
        # `planning` — the tool overruling a project about its own scaffold),
        # and overriding ONE grain must not make the project own all of them.
        with tree() as root:
            (root / 'devkit.toml').write_text(
                '[pm]\ntemplate_dir = "pm/templates"\n', encoding='utf-8')
            tdir = root / 'pm/templates'
            tdir.mkdir(parents=True)
            (tdir / 'story.md').write_text(
                '---\nid: {id}\nfeature: {feature}\nmilestone: "{milestone}"\n'
                'name: {name}\nstatus: done\nhouse_field: yes\n---\n\n# {name}\n',
                encoding='utf-8')
            self.assertEqual(
                run_cli(root, 'new', 'story', '0.1/alpha', 's', 'S')[0], 0)
            sf = root / 'pm/roadmap/stories/st-s.md'
            self.assertEqual(frontmatter.field_of(sf, 'house_field'), 'yes')
            self.assertEqual(frontmatter.field_of(sf, 'status'), 'done')
            # feature.md is not in the project's dir: the packaged one is used.
            self.assertEqual(run_cli(root, 'new', 'feature', '0.1', 'z', 'Z')[0], 0)


class YourMilestoneDirectoryIsYours(unittest.TestCase):
    """D13 is gone, both halves, and `pm new` mints no directory.

    D13b — "extra slot" — FAILED your gate for keeping a file in your own
    milestone directory. `plans/`, `findings/`, `AUDIT-REPORT.md`: those are a
    project's own notes in a project's own tree, and a tracker with an opinion
    about them is a tracker deciding what you may write down.

    D13a — a grain dir with no grain file — was reported twice over, by
    `orphan_dirs` and by V1. **0.4.0 deleted the subject**: a pool has no grain
    directories, so `orphan_dirs` went with them and V1 answers the flat
    version of the same question — a document with no readable `id:` is
    reported by name and counted as skipped. This pins the successor, so the
    coverage cannot quietly leave with the rule.

    And `pm new` mints no directory at all beyond the pool. Git does not store
    an empty directory: across one consumer's tree the old behaviour produced
    158 `design/` dirs, 11 of which hold anything.
    """

    def test_your_own_files_in_your_own_milestone_dir_are_not_findings(self):
        # ONE tree holding every shape at once: five trees proved five times
        # that the gate has no opinion about a directory it does not own, and
        # each one cost a `git init`.
        with tree(story_statuses=('ready',)) as root:
            mdir = root / 'pm/roadmap'
            for name in ('plans', 'findings', 'design'):
                (mdir / name).mkdir()
            for name in ('AUDIT-REPORT.md', 'DELETED-SCENARIO-LEDGER.md'):
                (mdir / name).write_text('# notes\n', encoding='utf-8')
            # ...and a shared doc that lost its header is not a finding either.
            shared(root, '0.1', 'decisions.md').write_text(
                '# log\n\n## D1 — 2026-01-01 — a thing\n', encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 0, out)

    def test_a_document_with_no_id_is_STILL_reported_and_STILL_counted(self):
        # The fold-in, proven, in its 0.4.0 shape. A grain DIRECTORY with no
        # grain file was D13a's finding; a pool has no such thing, and the
        # successor defect is a document whose frontmatter names no `id:` —
        # which drops out of the index by construction, so it has to be
        # reported by NAME and counted as skipped or the census is lying about
        # what it scanned.
        with tree(story_statuses=('ready',)) as root:
            (root / 'pm/roadmap/features/gamma.md').write_text(
                '---\nname: Gamma\n---\n\nprose\n', encoding='utf-8')
            code, out = run_gate(root)
            self.assertEqual(code, 1, out)
            self.assertIn('gamma.md', out)
            self.assertIn('declares no `id:`', out)
            self.assertIn('SKIPPED', out)

    def test_a_retired_rule_is_not_a_silently_accepted_name(self):
        # A retired id must not linger in KNOWN_CHECKS: a name that parses but
        # runs nothing is a gate a consumer believes is on — and naming one in
        # `[pm] checks` is a config error, not a quiet no-op.
        # D13/D14 never shipped as ids a consumer could name; V2, V3 and V6 DID,
        # so a config still listing one has to be told where the rule went
        # rather than that it does not exist. "Unknown rule" reads as a typo
        # and silently ungates.
        for retired in ('D13', 'D14'):
            self.assertNotIn(retired, vocabulary.KNOWN_CHECKS)
        for retired in ('V2', 'V3', 'V6', 'D7', 'D8'):
            self.assertNotIn(retired, vocabulary.KNOWN_CHECKS, retired)
            self.assertIn(retired, vocabulary.RETIRED_CHECKS, retired)
        with tree(story_statuses=('ready',)) as root:
            for named, says in (('D13', ''), ('V2', 'identity'),
                                ('V3', 'membership is now the field'),
                                # V6 graded the generated execution list; its
                                # replacement is the parent's own `order:`.
                                ('V6', '`order:` on the parent')):
                with self.subTest(named=named):
                    (root / 'devkit.toml').write_text(
                        f'[pm]\nchecks = ["{named}"]\n', encoding='utf-8')
                    code, out = both_streams(root)
                    self.assertEqual(code, 2, out)
                    self.assertIn(named, out)
                    # A retired id is told where the rule WENT; an id that
                    # never existed only gets named.
                    if says:
                        self.assertIn(says, out)

    def test_new_mints_no_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            root.mkdir()
            (root / '.git').mkdir()  # a MARKER: `repo_root` walks for it
            previous = Path.cwd()
            os.chdir(root)
            try:
                self.assertEqual(run_cli(root, 'new', 'milestone', '0.1', 'M')[0], 0)
                # ONE pool, holding ONE document. The empty `features/`,
                # `bugs/`, `design/` and `stories/` a grain dir used to sprout
                # cannot exist: a pool appears when the first grain of that
                # kind goes into it, and never before.
                self.assertEqual(
                    sorted(p.name for p in (root / 'pm/roadmap').iterdir()),
                    ['milestones'])
                self.assertEqual(
                    sorted(p.name for p in (root / MILESTONES).iterdir()),
                    ['ms-0.1.md'])
                self.assertEqual(
                    run_cli(root, 'new', 'feature', 'ms-0.1', 'f', 'F')[0], 0)
                self.assertEqual(
                    sorted(p.name for p in (root / FEATURES).iterdir()),
                    ['ft-f.md'])
                self.assertEqual(
                    run_cli(root, 'new', 'story', 'ft-f', 's0', 'S0')[0], 0)
                self.assertTrue(
                    (root / 'pm/roadmap/stories/st-s0.md').is_file())
            finally:
                os.chdir(previous)
