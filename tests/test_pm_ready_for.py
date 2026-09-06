"""`pm ready-for feature|milestone|tag` — the three belt-entry conditions.

Every tree here is BUILT (rule 8): this repo's own `pm/roadmap/` changes under
the test as the milestone proceeds, so asserting against it would grade one run
against the last one's state. The harness is `tests/support/pm.py`'s, the same
one the rest of the pm quartet uses.

Two properties are pinned everywhere rather than in one case each, because both
are the shapes a false PASS wears:

- exit 1 NAMES its blockers. A case that asserts only the exit code would pass
  over `3 stories not at reviewing`, which is the output this verb exists to
  refuse — so the not-ready cases assert the ids and the statuses.
- exit 0 states the census it CHECKED. A bare "ready" over a set the verb failed
  to enumerate is the read-side cardinal sin, so the ready cases assert the
  count too.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from support.pm import bug, declaring, run_cli, tree, write, write_config

from agentic_sdlc.repo.pm import model, ready_for

FEATURE_STORIES = 'pm/roadmap/0.1-demo/features/alpha/stories'
REVIEWS = 'docs/reviews'


# --- record fixtures ----------------------------------------------------------
# Vendored verdict blocks, in the shape `verdict.py` documents. The fence is
# part of the shape: an unfenced block is a near-miss, which is `parse`'s
# ruling and asserted below rather than re-decided here.
def record(*blocks: str, prose: str = 'A review record.') -> str:
    body = [prose, '']
    for block in blocks:
        body += ['```', block.strip(), '```', '']
    return '\n'.join(body)


CLEAN_BLOCK = """
verdict: SHIP
| id | severity | disposition |
| W1 | WARNING | landed 3a42f19ad |
| S3 | SUGGESTION | rejected: pause regression |
| D2 | DELTA | deferred: 0.1/alpha |
"""
OPEN_BLOCK = """
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| M1 | CRITICAL | open |
| M2 | MAJOR | landed in-place |
"""
# MAJOR, because what this fixture is FOR is proving the second block is read
# at all — and since 0.3.0 severity gates the hold, a below-MAJOR finding would
# make the case pass for the wrong reason.
SECOND_OPEN_BLOCK = """
verdict: HOLD
| id | severity | disposition |
| Q5 | MAJOR | open |
"""

# The other side of that rule: read, reported, and NOT a blocker.
SECOND_NIT_BLOCK = """
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| Q6 | NIT | open |
"""
EMPTY_BLOCK = """
verdict: SHIP
| id | severity | disposition |
"""
MALFORMED_BLOCK = """
verdict: SHIP
| id | severity | disposition |
| W1 | WARNING | landed 3a42f19ad | extra |
"""
NO_VERDICT = 'Just prose. Nobody wrote a block.\n'


def put_record(root: Path, name: str, text: str) -> str:
    """Write a review record; return the repo-relative pointer for it."""
    path = root / REVIEWS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return f'{REVIEWS}/{name}'


def feature(root: Path, slug: str, status: str = 'done', reviewed: str = '',
            stories: dict[str, str] | None = None) -> None:
    """One feature under `tree()`'s 0.1 milestone, with its stories."""
    fdir = root / 'pm/roadmap/0.1-demo/features' / slug
    write(fdir / 'feature.md',
          {'id': f'0.1/{slug}', 'milestone': '"0.1"', 'name': slug.title(),
           'status': status, 'reviewed': reviewed})
    for name, story_status in (stories or {}).items():
        write(fdir / 'stories' / f'{name}.md',
              {'id': f'0.1/{slug}/{name}', 'feature': f'0.1/{slug}',
               'milestone': '"0.1"', 'name': name, 'status': story_status})


def stories(root: Path, **statuses: str) -> None:
    """Replace `tree()`'s alpha stories with exactly these."""
    sdir = root / FEATURE_STORIES
    for existing in sdir.glob('*.md'):
        existing.unlink()
    for name, status in statuses.items():
        write(sdir / f'{name}.md',
              {'id': f'0.1/alpha/{name}', 'feature': '0.1/alpha',
               'milestone': '"0.1"', 'name': name, 'status': status})


def bytes_of(root: Path) -> dict[str, bytes]:
    """Every file under the tree, by relative path — the write-nothing proof.

    `.git/` is out: `model.load()` shells out to `git rev-parse` to find the
    root, and a reflog or index touched by READING is not this verb writing.
    """
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(root).parts}


# What an UNROUTED verb prints. Asserted absent in every refusal case: a
# subcommand that does not exist also exits 2, so a refusal test that checked
# only the code would pass over the verb never having been wired at all.
UNROUTED = 'unknown command'


def named(out: str) -> list[str]:
    return [line.split(ready_for.BLOCKED, 1)[1]
            for line in out.split('\n') if line.startswith(ready_for.BLOCKED)]


# --- story -> feature ---------------------------------------------------------
class FeatureBelt(unittest.TestCase):
    """Is every story under this feature `done`?

    It asked for `reviewing` until 2026-09-05 and the three cases below moved
    with the ruling (`ready_for.py`'s module docstring carries the why):
    `reviewing` at story grain is a HAND-OFF, not a terminus, and a belt that
    admitted it would start the feature's review over work still in motion.
    """

    def test_all_done_passes_and_states_the_count_it_checked(self):
        with tree(story_statuses=('done',) * 4) as root:
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('4 story/ies', out)
            self.assertIn('all done', out)

    def test_exit_1_names_every_blocker_with_the_status_it_holds(self):
        with tree() as root:
            stories(root, s0='building', s1='ready', s2='done')
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 1, out)
            self.assertIn('0.1/alpha/s0 is building', out)
            self.assertIn('0.1/alpha/s1 is ready', out)
            self.assertNotIn('s2', out)

    def test_the_output_is_not_a_tally(self):
        # The rule this verb exists for: `2 stories not at reviewing` sends a
        # reader to `pm status` to re-derive what the machine already had.
        with tree() as root:
            stories(root, s0='building', s1='ready')
            _, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertNotIn('2 stories not at reviewing', out)
            self.assertEqual(len(named(out)), 2, out)

    def test_a_feature_with_no_stories_is_ready_and_the_output_says_why(self):
        with tree(story_statuses=()) as root:
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn(ready_for.VACUOUS, out)
            self.assertIn('0 story/ies', out)

    def test_a_stories_dir_of_non_grain_files_is_zero_stories_and_discloses_it(self):
        # "Is that empty, or a scan that found nothing?" — both, and the census
        # says which: `slot_walk` keeps only documents that OPEN frontmatter.
        with tree(story_statuses=()) as root:
            (root / FEATURE_STORIES).mkdir(parents=True, exist_ok=True)
            (root / FEATURE_STORIES / 'README.txt').write_text('notes\n',
                                                              encoding='utf-8')
            (root / FEATURE_STORIES / 'notes.md').write_text('no frontmatter\n',
                                                             encoding='utf-8')
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn(ready_for.VACUOUS, out)
            self.assertIn('skipped', out.lower())

    def test_a_status_outside_the_vocabulary_is_named_with_the_word_it_holds(self):
        with tree() as root:
            stories(root, s0='wombat')
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 1, out)
            self.assertIn('0.1/alpha/s0 is wombat', out)

    def test_a_story_still_at_reviewing_blocks_and_is_named(self):
        # The direction the ruling reversed. `reviewing` is the builder saying
        # "look at this" — a story parked there is genuinely unfinished, and a
        # feature review started over it reviews work still in motion. The
        # shipped story seed no longer holds the word, so this tree DECLARES
        # it: the question is the category, and a project that keeps a review
        # stint for stories gets the same answer.
        with tree(config=declaring(story={
                'todo': ('planning', 'ready'),
                'in_progress': ('building', 'reviewing'),
                'done': ('done', 'obe')})) as root:
            stories(root, s0='reviewing')
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 1, out)
            self.assertIn('0.1/alpha/s0 is reviewing', out)

    def test_two_hundred_blockers_are_named_and_the_remainder_is_disclosed(self):
        with tree(story_statuses=()) as root:
            stories(root, **{f's{i:03d}': 'building' for i in range(200)})
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 1, out)
            self.assertEqual(len(named(out)), ready_for.MAX_NAMED + 1, out)
            self.assertIn(f'{200 - ready_for.MAX_NAMED} more not named', out)
            self.assertIn('0.1/alpha/s000 is building', out)


# --- feature -> milestone -----------------------------------------------------
class MilestoneBelt(unittest.TestCase):
    """Is every feature `done`, each with a resolving, NON-EMPTY record?"""

    def test_all_done_with_a_record_passes_and_states_the_count(self):
        with tree(feature_status='done') as root:
            feature(root, 'beta', 'done',
                    put_record(root, 'beta.md', 'A real record.\n'))
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('2 feature(s)', out)
            self.assertIn('all done with a record', out)

    def test_the_three_failure_reasons_are_each_named_and_distinct(self):
        with tree(feature_status='reviewing') as root:
            feature(root, 'beta', 'done', 'docs/reviews/gone.md')
            feature(root, 'gamma', 'done',
                    put_record(root, 'gamma.md', '   \n\n'))
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('0.1/alpha is reviewing', out)
            self.assertIn('0.1/beta is done, reviewed: names no file', out)
            self.assertIn('0.1/gamma is done, reviewed: the record is empty', out)
            self.assertEqual(len(named(out)), 3, out)

    def test_a_milestone_with_zero_features_is_LOUD_and_not_vacuously_ready(self):
        with tree() as root:
            shutil.rmtree(root / 'pm/roadmap/0.1-demo/features')
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('has no features', out)
            # The two vacuity rulings are opposite; a transcript must not be
            # able to confuse them.
            self.assertNotIn(ready_for.VACUOUS, out)

    def test_a_blank_pointer_and_a_directory_pointer_read_differently(self):
        with tree(feature_status='done', with_record=False) as root:
            (root / REVIEWS).mkdir(parents=True, exist_ok=True)
            (root / REVIEWS / 'adir').mkdir()
            feature(root, 'beta', 'done', f'{REVIEWS}/adir')
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('0.1/alpha is done, reviewed: is blank', out)
            self.assertIn('0.1/beta is done, reviewed: names a directory', out)

    def test_a_feature_status_outside_the_vocabulary_is_named(self):
        with tree(feature_status='wombat') as root:
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('0.1/alpha is wombat', out)

    def test_an_open_bug_against_the_milestone_blocks_and_is_named(self):
        """Amended from `test_bugs_do_not_block_a_milestone`, which asserted
        the ruling story 05 reversed. An open bug whose `fix_milestone:` is
        this milestone is a BLOCKED line by name; a closed one is not; a bug
        promised to ANOTHER milestone is ignored and COUNTED, so the census
        line cannot read "no bug blocks" over a bug nobody asked about."""
        with tree(feature_status='done') as root:
            bug(root, 'crash', status='open', fix_milestone='0.1')
            bug(root, 'fixed-later', status='fixed', fix_milestone='"0.1"')
            bug(root, 'shut', status='closed', fix_milestone='0.1')
            bug(root, 'theirs', status='open', fix_milestone='0.2')
            bug(root, 'unpromised', status='open')
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 1, out)
            self.assertEqual(named(out), [
                '0.1/bugs/crash is open — a bug whose fix_milestone is 0.1',
                '0.1/bugs/fixed-later is fixed — a bug whose fix_milestone '
                'is 0.1'])
            self.assertIn('3 bug(s) naming fix_milestone 0.1 of 5 read', out)
            self.assertNotIn('theirs', out)
            self.assertNotIn('unpromised', out)
            # Close the two and the milestone is ready, the census intact.
            run_cli(root, 'bug', 'closed', '0.1/bugs/crash')
            run_cli(root, 'bug', 'closed', '0.1/bugs/fixed-later')
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('1 feature(s), 3 bug(s) naming fix_milestone 0.1 '
                          'of 5 read, all done with a record', out)

    def test_a_file_under_bugs_shaped_exactly_like_a_feature_is_still_not_one(self):
        with tree(feature_status='done') as root:
            write(root / 'pm/roadmap/0.1-demo/bugs/feature.md',
                  {'id': '0.1/impostor', 'milestone': '"0.1"',
                   'name': 'Impostor', 'status': 'building', 'reviewed': ''})
            code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('1 feature(s)', out)
            self.assertNotIn('impostor', out)


# --- the `reviewed:` payload --------------------------------------------------
class PointerRefusals(unittest.TestCase):
    """Story 02's matrix: what a `reviewed:` value may not make this verb do.

    Every row is a BLOCKER naming the feature — never a crash, never a pass,
    and never a read outside the checkout.
    """

    MATRIX = (
        ('../../../etc/passwd', 'dot segment'),
        ('/etc/passwd', 'absolute'),
        ('~/notes.md', 'home-relative'),
        ('file:///x', 'URL'),
        ('https://x/y.md', 'URL'),
        (f'{REVIEWS}/*.md', 'glob'),
        ('.', 'dot segment'),
        ('..', 'dot segment'),
        (f'{REVIEWS}//x.md', 'empty segment'),
        (f'{REVIEWS}/./x.md', 'dot segment'),
        ('docs\\reviews\\x.md', 'backslash'),
        ('a' * 4097, 'over-long'),
        (f'{REVIEWS}/x y.md', 'whitespace'),
    )

    def _blocked(self, root: Path, pointer: str) -> str:
        feature(root, 'beta', 'done', pointer)
        code, out = run_cli(root, 'ready-for', 'milestone', '0.1')
        self.assertEqual(code, 1, out)
        line = next(b for b in named(out) if b.startswith('0.1/beta'))
        return line

    def test_every_shape_in_the_matrix_blocks_without_a_crash(self):
        for pointer, why in self.MATRIX:
            with self.subTest(pointer=pointer[:40], why=why):
                with tree(feature_status='done') as root:
                    line = self._blocked(root, pointer)
                    self.assertIn('reviewed:', line)

    def test_a_pointer_out_of_the_checkout_does_not_read_the_file_it_names(self):
        with tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / 'secret.md'
            secret.write_text('THE-SECRET-CONTENT\n', encoding='utf-8')
            for pointer in (str(secret), f'../{secret.name}'):
                with self.subTest(pointer=pointer):
                    with tree(feature_status='done') as root:
                        line = self._blocked(root, pointer)
                        self.assertNotIn('THE-SECRET-CONTENT', line)

    def test_a_symlink_pointing_out_of_the_checkout_is_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / 'secret.md'
            secret.write_text('THE-SECRET-CONTENT\n', encoding='utf-8')
            with tree(feature_status='done') as root:
                (root / REVIEWS).mkdir(parents=True, exist_ok=True)
                link = root / REVIEWS / 'link.md'
                os.symlink(secret, link)
                line = self._blocked(root, f'{REVIEWS}/link.md')
                self.assertIn('symlink', line)

    def test_a_record_that_is_not_utf8_is_a_blocker_and_not_a_crash(self):
        with tree(feature_status='done') as root:
            (root / REVIEWS).mkdir(parents=True, exist_ok=True)
            (root / REVIEWS / 'binary.md').write_bytes(b'\xff\xfe\x00nope')
            line = self._blocked(root, f'{REVIEWS}/binary.md')
            self.assertIn('UTF-8', line)

    def test_an_over_large_record_is_reported_rather_than_read(self):
        with tree(feature_status='done') as root:
            (root / REVIEWS).mkdir(parents=True, exist_ok=True)
            (root / REVIEWS / 'huge.md').write_bytes(
                b'x' * (ready_for.MAX_RECORD_BYTES + 1))
            line = self._blocked(root, f'{REVIEWS}/huge.md')
            self.assertIn('read bound', line)


# --- milestone -> tag ---------------------------------------------------------
class TagBelt(unittest.TestCase):
    """Is every finding at a disposition other than `open`?"""

    def test_an_open_finding_names_the_ids_and_the_record(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md', record(OPEN_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn(f'M1 open in {pointer}', out)
            self.assertNotIn('M2', out)

    def test_a_fully_dispositioned_milestone_passes_and_states_its_census(self):
        with tree(feature_status='done') as root:
            feature(root, 'alpha', 'done',
                    put_record(root, 'x.md', record(CLEAN_BLOCK)))
            feature(root, 'beta', 'done',
                    put_record(root, 'y.md', record(EMPTY_BLOCK)))
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('2 record(s), 3 finding(s), none blocking', out)

    def test_a_record_with_zero_findings_is_counted_out_loud_on_a_passing_run(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'y.md', record(EMPTY_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn(f'{pointer} — 0 finding(s)', out)

    def test_no_verdict_block_is_UNVERIFIABLE_never_zero_findings(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md', NO_VERDICT)
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn(f'{ready_for.UNVERIFIABLE} {pointer}', out)
            self.assertIn('no verdict block', out)

    def test_a_malformed_block_is_UNVERIFIABLE_with_the_parsers_own_message(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md', record(MALFORMED_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn(f'{ready_for.UNVERIFIABLE} {pointer}', out)
            self.assertIn('4 cell(s)', out)

    def test_an_unknown_disposition_word_is_UNVERIFIABLE_naming_the_word(self):
        block = OPEN_BLOCK.replace('| open |', '| pondering |')
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md', record(block))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('pondering', out)
            self.assertIn(ready_for.UNVERIFIABLE, out)

    def test_every_block_is_read_not_just_the_first(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md',
                                 record(CLEAN_BLOCK, SECOND_OPEN_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn(f'Q5 open in {pointer}', out)

    def test_an_open_finding_below_major_is_named_and_does_not_hold_the_tag(self):
        """0.3.0: severity gates the hold. An open NIT used to block a tag
        exactly as hard as a shipping bug, so a reviewer who did the job —
        writing the cheap observations down too — cost more to clear than it
        was worth, and the next one learns to stop writing them. Named on the
        passing path, because not blocking is not the same as not there.
        """
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md',
                                 record(CLEAN_BLOCK, SECOND_NIT_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('Q6', out)
            self.assertIn('carried forward', out)

    def test_a_clean_first_block_does_not_excuse_a_malformed_second(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md',
                                 record(CLEAN_BLOCK, MALFORMED_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn(ready_for.UNVERIFIABLE, out)

    def test_a_milestone_pointing_at_no_record_at_all_exits_1(self):
        with tree(feature_status='done', with_record=False) as root:
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('points at no review record', out)
            self.assertNotIn(ready_for.VACUOUS, out)

    def test_the_milestone_documents_own_pointer_is_read_too(self):
        # The cross-cutting review is filed against the MILESTONE; a verb that
        # read only the features' pointers would be blind to the pass that
        # files the findings it gates on.
        with tree(feature_status='done', with_record=False) as root:
            pointer = put_record(root, 'cross.md', record(OPEN_BLOCK))
            model.set_field(root / 'pm/roadmap/0.1-demo/milestone.md',
                            'reviewed', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn(f'M1 open in {pointer}', out)

    def test_a_blank_feature_pointer_is_the_belt_belows_question_not_this_one(self):
        with tree(feature_status='done', with_record=False) as root:
            feature(root, 'beta', 'done',
                    put_record(root, 'y.md', record(CLEAN_BLOCK)))
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('1 record(s)', out)

    def test_a_bad_pointer_blocks_the_tag_belt_with_story_02s_message(self):
        with tree(feature_status='done') as root:
            feature(root, 'alpha', 'done', f'{REVIEWS}/gone.md')
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 1, out)
            self.assertIn('reviewed: names no file', out)

    def test_two_features_pointing_at_one_record_count_it_once(self):
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md', record(CLEAN_BLOCK))
            feature(root, 'alpha', 'done', pointer)
            feature(root, 'beta', 'done', pointer)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('1 record(s), 3 finding(s)', out)

    def test_one_record_reached_by_two_spellings_still_counts_once(self):
        # B4: the dedupe used to key on the UNRESOLVED path, so one file
        # reached by two spellings counted twice — and the census is what this
        # verb prints as its proof of what it read, so an over-count is a false
        # census (rule 4). `_record` already computes the realpath for the
        # containment check; it is now what the dedupe keys on.
        #
        # A symlinked DIRECTORY rather than a case-insensitive filesystem: the
        # file itself is not a symlink (those are refused by name), the two
        # pointers differ as strings, and this reproduces on any POSIX tree
        # rather than only on macOS, where the finding was measured.
        with tree(feature_status='done') as root:
            pointer = put_record(root, 'x.md', record(CLEAN_BLOCK))
            (root / 'docs' / 'r').symlink_to('reviews', target_is_directory=True)
            alias = pointer.replace('docs/reviews/', 'docs/r/')
            self.assertNotEqual(alias, pointer)
            feature(root, 'alpha', 'done', pointer)
            feature(root, 'beta', 'done', alias)
            code, out = run_cli(root, 'ready-for', 'tag', '0.1')
            self.assertEqual(code, 0, out)
            self.assertIn('1 record(s), 3 finding(s)', out)


# --- the input surface --------------------------------------------------------
class ArgvRefusals(unittest.TestCase):
    """Exit 2 for every one: a typo is a usage error, never a finding."""

    CASES = (
        ([], 'no kind'),
        (['feature'], 'no id'),
        (['milestone'], 'no id'),
        (['tag'], 'no id'),
        (['wombat', '0.1'], 'unknown kind'),
        (['feature', '0.1/alpha', '0.1/beta'], 'two ids'),
        (['feature', '0.1/alpha', '--json'], 'a flag'),
        (['feature', '--json'], 'a flag alone'),
        (['feature', '0.1/alpha', 'extra'], 'a trailing word'),
    )

    def test_every_argv_shape_exits_2(self):
        with tree() as root:
            for argv, why in self.CASES:
                with self.subTest(why=why):
                    code, out = run_cli(root, 'ready-for', *argv)
                    self.assertEqual(code, 2, out)
                    self.assertNotIn(UNROUTED, out)
                    self.assertIn('ready-for', out)

    def test_an_unknown_kind_names_the_closed_set(self):
        with tree() as root:
            _, out = run_cli(root, 'ready-for', 'wombat', '0.1')
            self.assertNotIn(UNROUTED, out)
            self.assertIn('wombat', out)
            for kind in ready_for.KINDS:
                self.assertIn(kind, out)


class IdRefusals(unittest.TestCase):
    """Story 01's matrix. Exit 2, and NOTHING reads a grain file to get there.

    The read-nothing half is proven by making every grain read raise: a case
    that only asserted the exit code would pass over a resolver that opened the
    file first and refused afterwards.
    """

    MATRIX = (
        '', '.', '..', '0.1/', '/0.1/alpha', '0.1//alpha',
        '../../../etc/passwd', '~/x', 'file:///x',
        '0.1/*', '0.1/**', '0.1/?', '0.1\\alpha', 'x' * 300,
        'a\nb', 'a\tb', 'a\0b', '   ', '0.1/does-not-exist',
    )
    WRONG_KIND = (
        ('feature', '0.1'),
        ('feature', '0.1/alpha/s0'),
        ('milestone', '0.1/alpha'),
        ('milestone', '0.1/alpha/s0'),
        ('tag', '0.1/alpha/s0'),
        ('tag', '0.1/alpha'),
    )

    def _no_reads(self):
        def explode(path, *rest):
            raise AssertionError(f'a refusal read {path}')
        return explode

    def test_every_id_in_the_matrix_exits_2_without_reading_a_grain(self):
        with tree() as root:
            original, model.read_raw = model.read_raw, self._no_reads()
            try:
                for kind in ready_for.KINDS:
                    for gid in self.MATRIX:
                        with self.subTest(kind=kind, gid=gid[:20]):
                            code, out = run_cli(root, 'ready-for', kind, gid)
                            self.assertEqual(code, 2, out)
                            self.assertNotIn(UNROUTED, out)
            finally:
                model.read_raw = original

    def test_a_grain_of_the_wrong_kind_exits_2_without_reading_it(self):
        # `field_of`, not `read_raw`: resolving a STORY id walks its siblings
        # through `slot_walk`, which reads each candidate to decide whether it
        # is a grain at all. What must never happen is the wrong QUESTION being
        # asked of the resolved grain, and `field_of` is how this verb asks.
        with tree() as root:
            original, model.field_of = model.field_of, self._no_reads()
            try:
                for kind, gid in self.WRONG_KIND:
                    with self.subTest(kind=kind, gid=gid):
                        code, out = run_cli(root, 'ready-for', kind, gid)
                        self.assertEqual(code, 2, out)
                        self.assertNotIn(UNROUTED, out)
                        self.assertIn(gid, out)
            finally:
                model.field_of = original

    def test_a_bug_id_is_the_wrong_kind_for_all_three(self):
        with tree() as root:
            bug(root, 'crash')
            for kind in ready_for.KINDS:
                with self.subTest(kind=kind):
                    code, out = run_cli(root, 'ready-for', kind, '0.1/bugs/crash')
                    self.assertEqual(code, 2, out)
                    self.assertNotIn(UNROUTED, out)


class NothingIsWritten(unittest.TestCase):
    """All three are read verbs. The tree is byte-identical afterwards."""

    def test_a_run_of_each_subcommand_leaves_the_tree_alone(self):
        with tree(feature_status='done') as root:
            feature(root, 'alpha', 'done',
                    put_record(root, 'x.md', record(OPEN_BLOCK)))
            before = bytes_of(root)
            for kind, gid in (('feature', '0.1/alpha'), ('milestone', '0.1'),
                              ('tag', '0.1')):
                code, out = run_cli(root, 'ready-for', kind, gid)
                # An unrouted verb also writes nothing, so each run has to have
                # ANSWERED (0 or 1) for this case to mean what it claims.
                self.assertIn(code, (0, 1), out)
            self.assertEqual(bytes_of(root), before)

    def test_a_refused_run_writes_nothing_either(self):
        with tree() as root:
            before = bytes_of(root)
            for argv in (('feature', '0.1/nope'), ('wombat', '0.1')):
                code, out = run_cli(root, 'ready-for', *argv)
                self.assertEqual(code, 2, out)
                self.assertNotIn(UNROUTED, out)
            self.assertEqual(bytes_of(root), before)


class TheQuestionIsACategory(unittest.TestCase):
    """A vocabulary without the word `done` can still answer — the question
    is the `done` CATEGORY, which every declaration has. The `ConfigRefusals`
    this replaces exited 2 when `story_states` lacked `done`; that refusal
    was the verb unable to ask about a word, and there is no word to ask
    about now. `obe` is finished by declaration, and a word the project never
    declared is a BLOCKER carrying the file's own spelling."""

    def test_a_renamed_vocabulary_answers_and_obe_is_finished(self):
        renamed = {'todo': ('queued',), 'in_progress': ('doing',),
                   'done': ('shipped', 'dropped')}
        with tree(story_statuses=('shipped', 'dropped')) as root:
            write_config(root, declaring(story=renamed))
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 0, out)
            self.assertIn('all done', out)
        with tree(story_statuses=('done', 'obe', 'wombat')) as root:
            code, out = run_cli(root, 'ready-for', 'feature', '0.1/alpha')
            self.assertEqual(code, 1, out)
            self.assertIn('s2 is wombat', out)
            self.assertNotIn('s1 is obe', out)


if __name__ == '__main__':
    unittest.main()
