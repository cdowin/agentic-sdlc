"""`pm new` / `pm templates` — scaffolding, slug hygiene, template minting,
and the no-deleter contract over the caller\'s own tree.

Split from test_pm.py by concern; the shared harness is tests/support/pm.py.

**Cut in 0.2.0 (feature `the-proof-is-named-in-the-criterion`, phase B):** the
per-kind and per-verb re-proofs of one templating rule — a slot filled for a
milestone and again for a feature, a header repaired and again not stacked, an
undecodable template refused by `new` and again by `decide`. What survives is
the shape rule 3 is about: **a refusal that writes NOTHING**, and a second run
that is a no-op. Every case here that builds a tree pays a `git init`, so a
case that re-proves a rule one kind over costs a spawn and buys no coverage.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from support.pm import cfg_for, frontmatter, run_cli, run_gate, write_config
from support.pm import git_tree as tree


from agentic_sdlc.repo.pm import cli, model, templates

LEGACY_LOG = '# legacy log\n\nM1 said something.\n'

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
                run_cli(root, 'new', 'story', '0.1/beta', 'first', 'First')[0], 0)
            ff = root / 'pm/roadmap/features/beta.md'
            self.assertEqual(model.field_of(ff, 'id'), '0.1/beta')
            self.assertEqual(model.field_of(ff, 'milestone'), '0.1')
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
            doc = shared(root, '0.1', model.HANDOFF_FILE_NAME)
            self.assertFalse(doc.exists())
            code, out = run_cli(root, 'new', 'handoff', '0.1')
            self.assertEqual(code, 0, out)
            body = doc.read_text(encoding='utf-8')
            # Rendered, not copied: the placeholders are filled from the tree.
            self.assertTrue(
                body.startswith(model.SLOT_HEADER[model.HANDOFF_FILE_NAME]),
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
            doc = shared(root, '0.1', model.HANDOFF_FILE_NAME)
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
            model.write_raw(legacy, LEGACY_LOG)
            code, out = run_cli(root, 'new', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('REFUSED', out)
            self.assertIn('0.1-DECISIONS.md', out)
            self.assertIn('0.1-decisions.md', out)
            self.assertIn('nothing was written', out)
            entries = model.dir_entries(pool)
            # EXACT names: on macOS `exists('0.1-decisions.md')` answers True
            # off the 0.1-DECISIONS.md sitting there, so only a listing can
            # prove no twin was minted and no rename ran.
            self.assertEqual(entries.get('0.1-DECISIONS.md'), 'file')
            self.assertNotIn('0.1-decisions.md', entries)
            self.assertNotIn('0.1-handoff.md', entries)
            self.assertEqual(model.read_raw(legacy), LEGACY_LOG)

    def test_new_refuses_a_file_slot_that_exists_as_a_directory(self):
        # Rule 6 reserves exit 1 for FINDINGS, so an uncaught IsADirectoryError
        # reads to a consumer's hook as "drift found" with a traceback attached.
        # ScaffoldRefused is the shape, and it refuses before anything moves.
        with tree(story_statuses=('ready',)) as root:
            shared(root, '0.1', model.DECISION_FILE_NAME).mkdir()
            code, out = run_cli(root, 'new', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('REFUSED', out)
            self.assertIn('is a DIRECTORY', out)
            self.assertIn('nothing was written', out)
            self.assertFalse(shared(root, '0.1', 'handoff.md').exists())

    def test_new_refuses_a_slot_it_cannot_prepend_a_header_to(self):
        # `_fill_header` guarded the READ and not the write, so a read-only
        # legacy doc raised `PermissionError` — a traceback, exit 1, and the
        # remaining slots never created. Writability is inspectable up front.
        with tree(story_statuses=('ready',)) as root:
            handoff = shared(root, '0.1', 'handoff.md')
            decisions = shared(root, '0.1', 'decisions.md')
            model.write_raw(handoff, 'legacy prose\n')
            model.write_raw(decisions, LEGACY_LOG)
            handoff.chmod(0o444)
            try:
                code, out = run_cli(root, 'new', 'milestone', '0.1')
                self.assertEqual(code, 1, out)
                self.assertIn('is not writable', out)
                self.assertIn('nothing was written', out)
                self.assertNotIn('Traceback', out)
                self.assertEqual(model.read_raw(decisions), LEGACY_LOG)
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
            doc = root / MILESTONES / '0.2.md'
            real = templates.write

            def flaky(path: Path, text: str) -> None:
                if path.name == '0.2.md':
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
            model.write_raw(outside, 'OUTSIDE\n')
            shared(root, '0.1', 'decisions.md').symlink_to(outside)
            code, out = run_cli(root, 'new', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('is a SYMLINK', out)
            self.assertIn('nothing was written', out)
            self.assertEqual(model.read_raw(outside), 'OUTSIDE\n')
            self.assertFalse(shared(root, '0.1', 'handoff.md').exists())

    def test_new_mints_no_shared_doc_and_repairs_the_header_of_one_present(self):
        # BOTH halves. `pm new` stopped CREATING a shared doc — that scaffolded
        # 204 empty files into one consumer's tree — and still MANAGES one that
        # exists, which is what a migration needs. And the repair is
        # idempotent: a doc that already carries its header never gets a second
        # one stacked on it.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
            for slot in model.MILESTONE_OPTIONAL_SLOTS:
                self.assertFalse(shared(root, '0.1', slot).exists(), slot)
            for slot, want in model.SLOT_HEADER.items():
                doc = shared(root, '0.1', slot)
                doc.write_text('# headerless\n', encoding='utf-8')
                self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
                self.assertEqual(model.header_of(doc), want, slot)
                self.assertIn('# headerless', doc.read_text(encoding='utf-8'))
                repaired = doc.read_text(encoding='utf-8')
                self.assertEqual(run_cli(root, 'new', 'milestone', '0.1')[0], 0)
                self.assertEqual(doc.read_text(encoding='utf-8'), repaired,
                                 f'{slot} grew a second header')

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
                [f.name for f in model.pool_walk(cfg_for(root), 'milestone')],
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


class OrdinalPrefixedStoriesScaffoldValid(unittest.TestCase):
    """`pm new story` under `story_ordinal_prefix` must mint a VALIDATING file.

    It stamped the ordering prefix into `id:` as well as the filename, so V2 —
    which compares the id to the STRIPPED stem — rejected every story the
    scaffolder wrote. A consumer hand-fixed each one, which is the tool minting
    exactly the drift its own gate reports.
    """

    ORDINAL_ON = '[pm]\nstory_ordinal_prefix = true\n'

    def _enable(self, root: Path) -> None:
        # Through `write_config`, so the flow declaration rides along: a
        # status verb asks `move_defect`, which reads `[pm.states.story]`.
        write_config(root, self.ORDINAL_ON)

    def test_the_id_drops_the_prefix_and_validate_passes(self):
        with tree(story_statuses=('ready',)) as root:
            self._enable(root)
            code, out = run_cli(root, 'new', 'story', '0.1/alpha',
                                '01-a-world-is-a-named-saved-thing', 'A world')
            self.assertEqual(code, 0, out)
            sf = (root / 'pm/roadmap/stories'
                  / '01-a-world-is-a-named-saved-thing.md')
            self.assertTrue(sf.is_file(), out)
            self.assertEqual(model.field_of(sf, 'id'),
                             '0.1/alpha/a-world-is-a-named-saved-thing')
            code, out = run_cli(root, 'validate')
            self.assertEqual(code, 0, out)
            # And the id the file now carries is the one the CLI addresses it by.
            self.assertEqual(
                run_cli(root, 'story', 'building',
                        '0.1/alpha/a-world-is-a-named-saved-thing')[0], 0)

    def test_the_prefix_stays_in_the_id_when_the_flag_is_off(self):
        # No devkit.toml: a file really named `01-boots.md` owns that id, and
        # validate agrees. Defaults-vs-declared equivalence — a strip that ran
        # unconditionally would hand every consumer NOT using the flag an id
        # that does not match its own file.
        with tree(story_statuses=('ready',)) as root:
            self.assertEqual(
                run_cli(root, 'new', 'story', '0.1/alpha', '01-boots', 'B')[0], 0)
            sf = root / 'pm/roadmap/stories/01-boots.md'
            self.assertEqual(model.field_of(sf, 'id'), '0.1/alpha/01-boots')
            self.assertEqual(run_cli(root, 'validate')[0], 0)

    def test_a_second_file_claiming_one_id_refuses_without_writing(self):
        with tree(story_statuses=('ready',)) as root:
            self._enable(root)
            self.assertEqual(
                run_cli(root, 'new', 'story', '0.1/alpha', '01-boots', 'B')[0], 0)
            sdir = root / 'pm/roadmap/stories'
            before = sorted(p.name for p in sdir.iterdir())
            code, out = run_cli(root, 'new', 'story', '0.1/alpha', '02-boots', 'B')
            self.assertEqual(code, 1, out)
            self.assertIn('already held by', out)
            self.assertEqual(sorted(p.name for p in sdir.iterdir()), before)
            # ...and a slug that is ONLY a prefix has no id to claim at all.
            code, out = run_cli(root, 'new', 'story', '0.1/alpha', '01-', 'B')
            self.assertEqual(code, 1, out)
            self.assertEqual(sorted(p.name for p in sdir.iterdir()), before)


class BugNamesItsCause(unittest.TestCase):
    """`caused_by:` — the feature whose change produced the bug.

    `caught_in:` says which milestone FOUND it; `caused_by:` says which feature
    MADE it. Different facts, and an escape needs both — which is the whole
    reason the field is not a second spelling of the one already there.
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
            self.assertEqual(run_cli(root, 'new', 'bug', '0.1', 'unattributed')[0], 0)
            self.assertEqual(frontmatter(root / self.BUGS / 'unattributed.md'), [
                'id: 0.1/bugs/unattributed',
                # 0.4.0: a grain states its own kind, so nothing has to infer
                # one from where the file happens to sit.
                'kind: bug',
                'milestone: "0.1"',
                'name:',
                'status: open',
                'caught_in: "0.1"',
                'fix_milestone:',
                'caused_by:',
            ])
            code, out = run_cli(root, 'new', 'bug', '0.1', 'seed-is-zero',
                                '--caused-by', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertEqual(frontmatter(root / self.BUGS / 'seed-is-zero.md'), [
                'id: 0.1/bugs/seed-is-zero',
                'kind: bug',
                'milestone: "0.1"',
                'name:',
                'status: open',
                'caught_in: "0.1"',
                'fix_milestone:',
                'caused_by: 0.1/alpha',
            ])
            self.assertIn("caused_by '0.1/alpha'", out)
            self.assertEqual(run_cli(root, 'new', 'bug', '0.1', 'joined',
                                     '--caused-by=0.1/alpha')[0], 0)
            self.assertEqual(
                model.field_of(root / self.BUGS / 'joined.md', 'caused_by'),
                '0.1/alpha')
            self.assertEqual(run_cli(root, 'validate')[0], 0)
            self.assertEqual(run_gate(root)[0], 0)

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
        # <id>` is consumed as a PAIR, so what is left has to be exactly the
        # milestone and the slug, never three positional args.
        with tree() as root:
            for argv in (('new', 'bug', '0.1', 'x', '--caused-by', ''),
                         ('new', 'bug', '0.1', 'x', '--caused-by='),
                         ('new', 'bug', '0.1', '--caused-by')):
                with self.subTest(argv=argv):
                    code, out = run_cli(root, *argv)
                    self.assertEqual(code, 2, out)
                    self.assertIn('needs a feature id', out)
                    self.assertEqual(self._bug_dir(root), [])
            code, out = run_cli(root, 'new', 'bug', '0.1', 'x', 'y',
                                '--caused-by', '0.1/alpha')
            self.assertEqual(code, 2, out)
            self.assertEqual(self._bug_dir(root), [])


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


class Templates(unittest.TestCase):
    def test_a_new_milestone_gets_its_grain_file_under_the_exact_name(self):
        # EXACT names, from a listing: `is_file()` here passed on macOS against
        # the OLD uppercase spellings long after the rename landed, and would
        # have failed in CI on Linux. The slot names are the assertion.
        with tree() as root:
            run_cli(root, 'new', 'milestone', '0.2', 'Second')
            entries = model.dir_entries(root / MILESTONES)
            self.assertEqual(entries.get('0.2.md'), 'file', entries)
            # And no shared doc rode along beside it.
            for slot in model.MILESTONE_OPTIONAL_SLOTS:
                self.assertNotIn(f'0.2-{slot}', entries)
            self.assertIn('# 0.2 — Second',
                          (root / MILESTONES / '0.2.md').read_text())

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
            model.write_raw(tdir / 'DECISIONS.md', mine)
            code, out = run_cli(root, 'templates')
            self.assertEqual(code, 0, out)
            self.assertIn('is a case variant of decisions.md', out)
            self.assertIn('git mv --force', out)
            self.assertEqual(model.read_raw(tdir / 'DECISIONS.md'), mine)
            self.assertNotIn('decisions.md', model.dir_entries(tdir))

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
            self.assertEqual(run_cli(root, 'decide', '0.3', 'a choice')[0], 0)
            self.assertIn('MINE', model.read_raw(
                shared(root, '0.3', 'decisions.md')))

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
            sf = root / 'pm/roadmap/stories/s.md'
            self.assertEqual(model.field_of(sf, 'house_field'), 'yes')
            self.assertEqual(model.field_of(sf, 'status'), 'done')
            # feature.md is not in the project's dir: the packaged one is used.
            self.assertEqual(run_cli(root, 'new', 'feature', '0.1', 'z', 'Z')[0], 0)


class YourMilestoneDirectoryIsYours(unittest.TestCase):
    """D13 is gone, both halves, and `pm new` mints no directory.

    D13b — "extra slot" — FAILED your gate for keeping a file in your own
    milestone directory. `plans/`, `findings/`, `AUDIT-REPORT.md`: those are a
    project's own notes in a project's own tree, and a tracker with an opinion
    about them is a tracker deciding what you may write down.

    D13a — a grain dir with no grain file — was already reported twice over:
    `orphan_dirs` says it (always on, never gated by `[pm] checks`) because a
    dropped directory takes every descendant out of the scan, and V1 says a
    grain file with no `id:`/`status:` is malformed. This pins BOTH so the
    coverage cannot quietly leave with the rule.

    And `pm new` no longer mints `features/ bugs/ design/ stories/`. Git does
    not store an empty directory: across one consumer's tree that produced 158
    `design/` dirs, 11 of which hold anything.
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
        for retired in ('D13', 'D14'):
            self.assertNotIn(retired, model.KNOWN_CHECKS)
        with tree(story_statuses=('ready',)) as root:
            (root / 'devkit.toml').write_text(
                '[pm]\nchecks = ["D13"]\n', encoding='utf-8')
            self.assertEqual(run_gate(root)[0], 2)

    def test_new_mints_no_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            root.mkdir()
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
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
                    ['0.1.md'])
                self.assertEqual(run_cli(root, 'new', 'feature', '0.1', 'f', 'F')[0], 0)
                self.assertEqual(
                    sorted(p.name for p in (root / FEATURES).iterdir()),
                    ['f.md'])
                self.assertEqual(
                    run_cli(root, 'new', 'story', '0.1/f', 's0', 'S0')[0], 0)
                self.assertTrue(
                    (root / 'pm/roadmap/stories/s0.md').is_file())
            finally:
                os.chdir(previous)
