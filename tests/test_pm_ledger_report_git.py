"""test_pm_ledger_report_git.py — `pm ledger report <ms> --from <rev>`.

D6 put a milestone's ledger inside the milestone directory and said the rest
out loud: `retire` removes it with the directory, and a retired milestone's
rows are read from GIT. So this verb's whole claim is an EQUALITY — the table a
reader gets out of history is the table they would have got the day before the
close — and an equality is only tested by capturing both sides and comparing
the bytes. Every shape case here does exactly that: run the live report, commit
the tree, tag it, retire the milestone, run `--from <tag>`, and compare
byte-for-byte after stripping the one thing that is meant to differ.

A paraphrase would not do. "The numbers match" is what a report with a whole
section missing also says, and a section that silently stopped printing is hard
rule 4's read-side sin — a gate that misses real drift and prints PASS.

**Every case here spawns git**, which is why the set is small and each member
guards a SILENT wrong answer rather than a loud one: a census that does not
match the disk walk's, a directory listing parsed as a document, today's disk
leaking into a read about history, CRLF producing a second table for one
milestone, and a read verb that writes. The refusals kept are the ones where
the alternative is not a crash — a rev that is really a git flag, and an empty
`--from` quietly answering from the working tree.

ALL of these fail at HEAD~: `--from` did not exist, so every case reported
`unknown flag '--from'` at exit 2.
"""
from __future__ import annotations

import json

from support.pm import (LEDGER_REL, bug, commit, dispatch_line, git,
                        porcelain, put_ledger, run_cli, snapshot, status_line,
                        write)
from support.pm import git_tree as tree



STORY, QUIET, FEATURE, BUG = ('0.1/alpha/s0', '0.1/alpha/s1', '0.1/alpha',
                              '0.1/bugs/crash')
MILESTONE_DIR = 'pm/roadmap/0.1-demo'
RECORD_REL = 'docs/reviews/alpha.md'
TAG = 'v9.9.9'

# A record as the installed reviewer writes one: prose, then the fenced block.
# Present so that sections 2 and 3 have something to print — a `--from` read
# that could not follow a feature's `reviewed:` pointer out of git would print
# an EMPTY yield table, which reads exactly like a milestone nobody reviewed.
RECORD = """\
The pass, in prose.

```text
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| A1 | MAJOR | landed 0badc0f |
| A2 | MINOR | landed in-place |
| A3 | QUESTION | deferred: 0.1/beta |
```
"""


def report(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'report', *argv)


def capture(root, *argv) -> str:
    code, out = report(root, *argv)
    assert code == 0, out
    return out


def seeded(root) -> None:
    """The tree every equality case reads: one story worked and closed, one
    story nothing touched, the feature that owns them, one bug naming a cause,
    a review record with a real verdict block, and rows of all four kinds.

    All five sections have content on purpose. A `--from` read that lost ONE
    of the file kinds it has to open — the milestone document, a feature, a
    story, a bug, a review record, the ledger — must fail loudly here.
    """
    write(root / MILESTONE_DIR / 'features/alpha/stories/s1.md',
          {'id': QUIET, 'feature': FEATURE, 'milestone': '"0.1"', 'name': 'S1',
           'status': 'ready', 'size': 'm'})
    bug(root, 'crash', 'closed', caused_by=FEATURE)
    (root / RECORD_REL).write_text(RECORD, encoding='utf-8')
    put_ledger(
        root,
        status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
        dispatch_line('2026-09-03T10:05:00Z', agent_type='developer',
                      tool_calls=37, duration_s=812,
                      tool_calls_before_first_write=9,
                      usage={'input': 1200, 'output': 38000,
                             'cache_creation': 210000, 'cache_read': 9100000},
                      tree=snapshot(stories_wip=[STORY],
                                    features_building=[FEATURE])),
        status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing'),
        dispatch_line('2026-09-03T10:11:00Z', agent_type='reviewer',
                      usage={'output': 500},
                      tree=snapshot(stories_review=[STORY])),
        status_line('2026-09-03T10:12:00Z', STORY, 'reviewing', 'building'),
        status_line('2026-09-03T10:14:00Z', STORY, 'building', 'done'),
        status_line('2026-09-03T10:20:00Z', BUG, 'open', 'closed'),
        dispatch_line('2026-09-03T10:30:00Z', usage={'input': 5},
                      tool_calls=2),
    )



def roadmap(root) -> None:
    """0.3.0: `ROADMAP.md` retired and `pm retire` no longer appends to it, so
    there is no index to seed. Kept as a no-op rather than deleted from the two
    call sites, because what those cases are ABOUT is reading a report out of
    git at a tag after the milestone directory is gone — the prune row was
    never the subject."""


def stripped(out: str, rev: str = TAG) -> str:
    """The report with the one thing that is MEANT to differ taken back out.

    ` — at <rev>` on every heading is the whole visible difference between the
    two reads, and stripping it is what turns "looks the same" into an
    assertion. Anything else that differs survives the strip and fails the
    comparison, which is the only reason this helper is a `replace` and not a
    per-line rewrite.
    """
    return out.replace(f' — at {rev}', '')


def refuses(root, *argv, needle: str = '') -> str:
    code, out = report(root, *argv)
    assert code == 2, (argv, out)
    if needle:
        assert needle in out, (argv, out)
    # Every refusal is also a claim that the tree is untouched; a verb that
    # refused AFTER writing would pass an exit-code assertion alone.
    assert porcelain(root) == ''
    return out


# --- the equality -------------------------------------------------------------

def test_the_report_at_the_tag_is_the_report_before_the_retire():
    """Text and JSON, byte for byte, through the REAL close: `retire` removes
    the directory and the ledger with it (D6), which is exactly the state this
    whole story exists for."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        live = capture(root, '0.1')
        live_json = capture(root, '0.1', '--json')
        commit(root, 'the milestone, still in the tree')
        git(root, 'tag', TAG)
        code, out = run_cli(root, 'retire', '0.1')
        assert code == 0, out
        assert not (root / MILESTONE_DIR).exists(), out
        commit(root, 'retire 0.1')
        at_tag = capture(root, '0.1', '--from', TAG)
        at_tag_json = capture(root, '0.1', '--json', '--from', TAG)
    assert f' — at {TAG} — ' in at_tag
    assert stripped(at_tag) == live
    payload = json.loads(at_tag_json)
    # `rev` is the ONLY key `--from` adds, and it is absent from a live
    # payload: a `"rev": null` in every report would be a key every consumer
    # has to learn to keep reading (hard rule 6).
    assert payload.pop('rev') == TAG
    assert payload == json.loads(live_json)
    assert 'rev' not in json.loads(live_json)


def test_no_ledger_at_the_rev_is_one_line_and_exit_zero():
    """Not an error. A milestone nothing was recorded for has no file, and
    that is the same fact from history as it is from disk."""
    with tree() as root:
        commit(root, 'a milestone nothing was recorded for')
        git(root, 'tag', TAG)
        out = capture(root, '0.1', '--from', TAG)
    assert out.strip() == f'[ledger:report] 0.1 — at {TAG} — no ledger'


def test_the_census_at_a_rev_narrows_exactly_as_the_disk_walk_does():
    """The claim `GitSource._grain_docs` makes, staged against a tree that
    exercises every one of `model.slot_walk`'s decisions at once.

    A census read out of git that quietly counted MORE than the disk walk (a
    note, a hidden document) or LESS (a nested bug, an uppercase extension)
    would be hard rule 4 exactly: a table whose grain list is not the tree's,
    printed with no sign that it isn't.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        base = root / MILESTONE_DIR
        # In scope, and only the recursive walk finds it.
        write(base / 'bugs/regressions/nested.md',
              {'id': '0.1/bugs/regressions/nested', 'milestone': '"0.1"',
               'name': '', 'status': 'open', 'caused_by': FEATURE})
        # In scope: `.md` is compared case-INSENSITIVELY.
        write(base / 'features/alpha/stories/LOUD.MD',
              {'id': '0.1/alpha/LOUD', 'feature': FEATURE,
               'milestone': '"0.1"', 'name': 'Loud', 'status': 'todo'})
        # Out of scope: a note beside the grains, no frontmatter at all.
        (base / 'bugs/README.md').write_text(
            'How bugs are filed here.\n', encoding='utf-8')
        # Out of scope: dot-prefixed, files and directories alike.
        write(base / 'bugs/.hold/parked.md',
              {'id': '0.1/bugs/parked', 'milestone': '"0.1"', 'name': '',
               'status': 'open'})
        live = capture(root, '0.1')
        commit(root, 'a tree with one of each narrowing')
        git(root, 'tag', TAG)
        at_tag = capture(root, '0.1', '--from', TAG)
    # The two grains that ARE in scope reached the table; the two that are
    # not, did not — and the rev read agrees with the disk read on all four.
    assert '0.1/bugs/regressions/nested' in live
    assert '0.1/alpha/LOUD' in live
    assert 'README' not in live
    assert 'parked' not in live
    assert stripped(at_tag) == live


def test_a_directory_at_the_rev_is_not_a_file():
    """`git show <rev>:<a-directory>` SUCCEEDS and hands back a listing, which
    a reader expecting a document parses as one. `is_file` asks git for the
    object TYPE for exactly that reason, and a `reviewed:` pointing at a
    directory must resolve to no record rather than to a yield built out of
    `git ls-tree` output."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        (root / RECORD_REL).unlink()
        write(root / f'{RECORD_REL}/inside.md',
              {'id': '0.1/nope', 'name': 'not a record'})
        commit(root, 'a pointer that names a directory')
        git(root, 'tag', TAG)
        out = capture(root, '0.1', '--from', TAG)
    assert 'alpha.md' not in out
    assert 'not a record' not in out


def test_an_absolute_reviewed_pointer_never_reads_todays_disk():
    """An absolute path is in no rev. Answering it from the working tree would
    put a file the milestone never shipped with into a report about history —
    the live tree leaking into a historical read."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        outside = root / 'todays-record.md'
        outside.write_text(RECORD.replace('SHIP-WITH-FIXES', 'HOLD'),
                           encoding='utf-8')
        # Resolved: the pointer must be spelled the way git names the root
        # (`rev-parse --show-toplevel` follows symlinks; a macOS tempdir is
        # one), or the mismatch alone hides the file from the rev read and the
        # case passes for the wrong reason. `commit` adds `-A`, so the record
        # IS in the rev — an absolute pointer must still not reach it.
        write(root / f'{MILESTONE_DIR}/features/alpha/feature.md',
              {'id': FEATURE, 'milestone': '"0.1"', 'name': 'Alpha',
               'status': 'done', 'reviewed': str(outside.resolve())})
        commit(root, 'an absolute pointer')
        git(root, 'tag', TAG)
        out = capture(root, '0.1', '--from', TAG)
    assert 'HOLD' not in out
    assert str(outside) not in out


def test_crlf_terminators_read_the_same_from_git_as_from_disk():
    """`git show` hands over the bytes as they are; `Path.read_text` — the
    reader `ledger.read_rows` uses — translates. A ledger and a record whose
    terminators are CRLF must still produce ONE table either way, or the same
    milestone has two reports and nothing says which is which."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        for rel in (LEDGER_REL, RECORD_REL):
            path = root / rel
            path.write_bytes(path.read_text(encoding='utf-8')
                             .replace('\n', '\r\n').encode('utf-8'))
        live = capture(root, '0.1')
        commit(root, 'CRLF terminators on both documents')
        git(root, 'tag', TAG)
        at_tag = capture(root, '0.1', '--from', TAG)
    assert 'SHIP-WITH-FIXES' in live
    assert stripped(at_tag) == live


def test_the_verb_writes_nothing_and_checks_nothing_out():
    """A read verb that stashed or checked out would destroy the working tree
    of whoever asked a question about history."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        commit(root, 'seed')
        git(root, 'tag', TAG)
        before = git(root, 'rev-parse', 'HEAD')
        capture(root, '0.1', '--from', TAG)
        capture(root, '0.1', '--from', TAG, '--json')
        assert porcelain(root) == ''
        assert git(root, 'rev-parse', 'HEAD') == before
        assert git(root, 'stash', 'list') == ''


# --- SDLC § 5's matrix for `--from`. Exit 2, and nothing written. -------------
# One representative per refusal: the milestone-id grammar is the shared
# resolver's and is proven in test_pm_ledger_report.py, and a rev that merely
# fails to resolve crashes nothing. What is kept is the pair whose alternative
# is SILENT — a rev git would read as one of its own flags, and an empty
# `--from` answering from the working tree.

REV_REFUSALS = [
    # git explains a bad rev better than a re-wording would, verbatim.
    (('0.1', '--from', 'nosuchrev'), 'fatal:'),
    (('0.1', '--from', '-x'), 'starts with `-`'),
    (('0.1', '--from', '--upload-pack=touch /tmp/pwned'), 'starts with `-`'),
    (('0.1', '--from', 'HEAD x'), 'whitespace or NUL'),
    (('0.1', '--from', 'HEAD\x00'), 'whitespace or NUL'),
    # The defect this case was written against: an empty value read as "no
    # rev", and the verb answered from the working tree at exit 0 — a live
    # report standing in for a question about history.
    (('0.1', '--from'), 'needs a rev'),
    (('--from', 'HEAD'), 'needs a milestone id'),
]


def test_from_refuses_anything_that_is_not_a_rev():
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        commit(root, 'seed')
        for argv, needle in REV_REFUSALS:
            refuses(root, *argv, needle=needle)


def test_a_milestone_the_rev_does_not_hold_is_named():
    """The ordinary mistake: a rev from AFTER the close that retired it. Both
    spellings of a rev, because both are things a caller types — and the
    message says which rev to reach for instead, since "it is not there" alone
    leaves the reader nowhere to go."""
    with tree() as root:
        commit(root, 'the milestone, in the tree')
        git(root, 'rm', '-r', '-q', MILESTONE_DIR)
        gone = commit(root, 'retired')
        git(root, 'tag', TAG)
        for rev in (gone, TAG):
            out = refuses(root, '0.1', '--from', rev,
                          needle='no milestone directory 0.1-*')
            assert 'release tag' in out


def test_a_path_the_report_needs_and_the_rev_does_not_hold():
    """The directory is there and `milestone.md` is not. Say which."""
    with tree() as root:
        git(root, 'add', '-A')
        (root / MILESTONE_DIR / 'milestone.md').unlink()
        commit(root, 'a milestone directory with no milestone document')
        git(root, 'tag', TAG)
        out = refuses(root, '0.1', '--from', TAG,
                      needle=f'{MILESTONE_DIR}/milestone.md')
        assert f'{TAG}:' in out


def test_a_ledger_line_that_will_not_parse_at_the_rev():
    """Still by LINE NUMBER, and now naming `<rev>:<path>` — the string a
    reader can paste after `git show` to see the line for themselves."""
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root,
                   status_line('2026-09-03T10:00:00Z', STORY, 'ready',
                               'building'),
                   '{not json')
        commit(root, 'a ledger with a bad line')
        git(root, 'tag', TAG)
        out = refuses(root, '0.1', '--from', TAG, needle='line 2')
        assert f'{TAG}:{LEDGER_REL}' in out


# --- the merge attribute, asked of GIT ----------------------------------------
def test_the_merge_attribute_reaches_both_ledger_homes():
    """0.4.0/D3 gave the tree a second ledger at `<roadmap>/ledger.jsonl`, and
    the shipped pattern was `<roadmap>/*/ledger.jsonl` — ONE DIRECTORY LEVEL
    too deep to reach it. Every branch appends to that file, so a pattern that
    misses it conflicts on every parallel branch, quietly, as a merge conflict
    nobody connects to the change that caused it.

    Asked of `git check-attr` over a real repo rather than of the pattern
    STRING, because a string assertion passes on a pattern that matches
    nothing — which is precisely the bug.
    """
    with tree() as root:
        assert run_cli(root, 'init')[0] == 0
        for rel in ('pm/roadmap/ledger.jsonl',
                    f'{MILESTONE_DIR}/ledger.jsonl'):
            said = git(root, 'check-attr', 'merge', '--', rel)
            assert said.strip() == f'{rel}: merge: union', said
        # The negatives, so the pattern is not simply `**`: a grain document
        # beside a ledger is left alone, and a ledger OUTSIDE the roadmap dir
        # is not claimed by a pattern anchored to it.
        for rel in (f'{MILESTONE_DIR}/milestone.md', 'pm/ledger.jsonl',
                    'ledger.jsonl'):
            said = git(root, 'check-attr', 'merge', '--', rel)
            assert said.strip().endswith(': unspecified'), said
        # And the depth the glob DOES reach, asserted rather than assumed:
        # `**` matches any number of directories, so a nested ledger would be
        # covered too. Harmless — D3 rejects nested ledgers — and it is here so
        # that narrowing the pattern later fails HERE rather than in somebody's
        # merge.
        deep = f'{MILESTONE_DIR}/features/f/stories/ledger.jsonl'
        said = git(root, 'check-attr', 'merge', '--', deep)
        assert said.strip() == f'{deep}: merge: union', said
