"""test_pm_ledger_report_git.py — `pm ledger report <ms> --from <rev>`.

D6 gave every milestone its own ledger and said the rest out loud: `retire`
removes it with the milestone's grains, and a retired milestone's rows are read
from GIT. So this verb's whole claim is an EQUALITY — the table a reader gets
out of history is the table they would have got the day before the close — and
an equality is only tested by capturing both sides and comparing the bytes.
Every shape case here does exactly that: run the live report, commit the tree,
tag it, retire the milestone, run `--from <tag>`, and compare byte-for-byte
after stripping the one thing that is meant to differ.

A paraphrase would not do. "The numbers match" is what a report with a whole
section missing also says, and a section that silently stopped printing is hard
rule 4's read-side sin — a gate that misses real drift and prints PASS.

0.4.0 sharpened the equality rather than replacing it. The pools moved every
grain out of a per-milestone directory, so WHICH LAYOUT a tree is in is now a
fact the reader has to ask — and `retire` leaves today's disk in a different
layout from the rev being read, which is the exact shape of "the live tree
leaking into a question about history". Every join that branches on the layout
(the ledger's home, the milestone's document)
is therefore asked of the SOURCE, and the equality case is what proves it.

**Every case here spawns git**, which is why the set is small and each member
guards a SILENT wrong answer rather than a loud one: a census that does not
match the disk walk's, today's disk leaking into a read about history, CRLF
producing a second table for one milestone, and a read verb that writes. The refusals kept are the ones where
the alternative is not a crash — a rev that is really a git flag, and an empty
`--from` quietly answering from the working tree.
"""
from __future__ import annotations

import json
import shutil

from support.pm import (LEDGER_REL, bug, commit, dispatch_line, git,
                        porcelain, put_ledger, run_cli, snapshot, status_line,
                        write)
from support.pm import git_tree as tree



STORY, QUIET, FEATURE, BUG = ('0.1/alpha/s0', '0.1/alpha/s1', '0.1/alpha',
                              '0.1/bugs/crash')
# The tree, not a milestone's directory: 0.4.0 left the pools under it and
# nothing under a per-milestone name. `pm/roadmap/` outlives every retire.
ROADMAP = 'pm/roadmap'
TAG = 'v9.9.9'

def report(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'report', *argv)


def capture(root, *argv) -> str:
    code, out = report(root, *argv)
    assert code == 0, out
    return out


def seeded(root) -> None:
    """The tree every equality case reads: one story worked and closed, one
    story nothing touched, the feature that owns them, one bug, and a stamp
    pair beside the dispatch and status rows.

    Every block has content on purpose. A `--from` read that lost ONE of the
    file kinds it has to open — the milestone document, a feature, a story, a
    bug, the ledger — must fail loudly here.
    """
    bug(root, 'crash', 'closed', caused_by=FEATURE)
    put_ledger(
        root,
        status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
        json.dumps({'ts': '2026-09-03T10:01:00Z', 'kind': 'stamp',
                    'grain': STORY, 'edge': 'start', 'issue': ['#41'],
                    'agent': 'developer'}),
        json.dumps({'ts': '2026-09-03T10:09:00Z', 'kind': 'stamp',
                    'grain': STORY, 'edge': 'stop', 'issue': ['#41'],
                    'tokens': 6000, 'outcome': 'landed'}),
        dispatch_line('2026-09-03T10:05:00Z', agent_type='developer',
                      tool_calls=37, duration_s=812, tokens_total=4000,
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


def grains_left(root) -> list[str]:
    """Every grain document still under the roadmap, as posix paths.

    `retire` deletes N FILES since 0.4.0 — a pooled tree has no per-milestone
    directory to remove — so "it retired" is a claim about documents, and
    `pm/roadmap/` being gone would be a different (and wrong) outcome.
    """
    base = root / ROADMAP
    return sorted(p.relative_to(base).as_posix()
                  for p in base.rglob('*.md') if p.is_file())


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
    the milestone's grains and its ledger (D6), which is exactly the state
    this whole story exists for — and once the retire has emptied the pools,
    today's disk answers "nested" for a rev that is pooled.

    The milestone document is RENAMED off its id for the same reason: a pooled
    filename is convention and `id:` is identity, so a report that fell back
    to the stem would head the table with `ms-demo` and read a ledger nobody
    wrote — and it would only do so at the rev, where the document is not on
    disk to be read.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        (root / ROADMAP / 'milestones/0.1.md').rename(
            root / ROADMAP / 'milestones/ms-demo.md')
        live = capture(root, '0.1')
        live_json = capture(root, '0.1', '--json')
        commit(root, 'the milestone, still in the tree')
        git(root, 'tag', TAG)
        code, out = run_cli(root, 'retire', '0.1')
        assert code == 0, out
        assert grains_left(root) == [], out
        assert (root / ROADMAP).is_dir(), out
        commit(root, 'retire 0.1')
        at_tag = capture(root, '0.1', '--from', TAG)
        at_tag_json = capture(root, '0.1', '--json', '--from', TAG)
    assert '#41' in live and 'landed' in live
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
    exercises every one of `inventory.pool_scan`'s decisions at once.

    A census read out of git that quietly counted MORE than the disk walk (a
    note, a hidden document) or LESS (a bug nested inside its pool, an
    uppercase extension) would be hard rule 4 exactly: a table whose grain
    list is not the tree's, printed with no sign that it isn't.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        base = root / ROADMAP
        # In scope, and only the recursive walk finds it: a pool is a table,
        # not a flat directory, and a subdirectory inside one is filing.
        write(base / 'bugs/regressions/nested.md',
              {'id': '0.1/bugs/regressions/nested', 'kind': 'bug',
               'milestone': '"0.1"', 'name': '', 'status': 'open',
               'caused_by': FEATURE})
        # In scope: `.md` is compared case-INSENSITIVELY.
        write(base / 'stories/LOUD.MD',
              {'id': '0.1/alpha/LOUD', 'kind': 'story', 'feature': FEATURE,
               'milestone': '"0.1"', 'name': 'Loud', 'status': 'todo'})
        # Out of scope: a note beside the grains, no frontmatter at all.
        (base / 'bugs/README.md').write_text(
            'How bugs are filed here.\n', encoding='utf-8')
        # Out of scope: dot-prefixed, files and directories alike.
        write(base / 'bugs/.hold/parked.md',
              {'id': '0.1/bugs/parked', 'kind': 'bug', 'milestone': '"0.1"',
               'name': '', 'status': 'open'})
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


def test_crlf_terminators_read_the_same_from_git_as_from_disk():
    """`git show` hands over the bytes as they are; `Path.read_text` — the
    reader `ledger.read_rows` uses — translates. A ledger whose terminators
    are CRLF must still produce ONE table either way, or the same milestone
    has two reports and nothing says which is which."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        path = root / LEDGER_REL
        path.write_bytes(path.read_text(encoding='utf-8')
                         .replace('\n', '\r\n').encode('utf-8'))
        live = capture(root, '0.1')
        commit(root, 'CRLF terminators on the ledger')
        git(root, 'tag', TAG)
        at_tag = capture(root, '0.1', '--from', TAG)
    assert '#41' in live
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
    # A report on the TREE takes a feature id (the level is the id's); one at
    # a rev reads one milestone, and the refusal says which of the two.
    ((FEATURE, '--from', 'HEAD'), 'reads ONE milestone out of git'),
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
    leaves the reader nowhere to go.

    0.4.0 changed what "not there" LOOKS like, so the staging changed with it:
    the pools survive the retire (the next milestone's grains are in them) and
    what is gone is the one document declaring this id. The message has to say
    that — a tree still holding `pm/roadmap/milestones/` is not one where "no
    `0.1-*` directory" tells the reader anything true.
    """
    with tree() as root:
        # The milestone whose close retires 0.1; without it the pools would be
        # empty and the rev would read as a pre-migration tree.
        write(root / ROADMAP / 'milestones/0.2.md',
              {'id': '"0.2"', 'kind': 'milestone', 'name': 'Next',
               'status': 'building'})
        commit(root, 'the milestone, in the tree')
        code, out = run_cli(root, 'retire', '0.1')
        assert code == 0, out
        gone = commit(root, 'retired')
        git(root, 'tag', TAG)
        for rev in (gone, TAG):
            out = refuses(root, '0.1', '--from', rev,
                          needle='declares `id: 0.1`')
            # `<rev>:<path>` — the pool it looked in, spelled so a reader can
            # paste it after `git show` and see for themselves.
            assert f'{rev}:{ROADMAP}/milestones' in out
            assert 'release tag' in out


def test_a_path_the_report_needs_and_the_rev_does_not_hold():
    """The directory is there and `milestone.md` is not. Say which.

    Only a PRE-MIGRATION rev can be in that state — a pooled handle IS the
    document, so there is no directory to find without one — and that is the
    case worth keeping rather than substituting: reading a consumer's history
    from before they moved to pools is half of what `--from` is for, and this
    is the only case that walks the nested resolution at a rev.
    """
    with tree() as root:
        # Nothing is committed yet, so the pools are dropped from the DISK and
        # `commit`'s `-A` never sees them: the rev holds the nested shape and
        # only that.
        shutil.rmtree(root / ROADMAP)
        write(root / f'{ROADMAP}/0.1-demo/features/alpha/feature.md',
              {'id': FEATURE, 'name': 'Alpha', 'status': 'done'})
        commit(root, 'a milestone directory with no milestone document')
        git(root, 'tag', TAG)
        out = refuses(root, '0.1', '--from', TAG,
                      needle=f'{ROADMAP}/0.1-demo/milestone.md')
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
    too deep to reach it, and named after a FILE the pools no longer have (a
    milestone's ledger is `<roadmap>/ledgers/<id>.jsonl`). Every branch appends
    to one of the two, so a pattern that misses either conflicts on every
    parallel branch, quietly, as a merge conflict nobody connects to the change
    that caused it.

    Asked of `git check-attr` over a real repo rather than of the pattern
    STRING, because a string assertion passes on a pattern that matches
    nothing — which is precisely the bug.
    """
    with tree() as root:
        assert run_cli(root, 'init')[0] == 0
        for rel in (f'{ROADMAP}/ledger.jsonl', f'{ROADMAP}/ledgers/0.1.jsonl'):
            said = git(root, 'check-attr', 'merge', '--', rel)
            assert said.strip() == f'{rel}: merge: union', said
        # The negatives, so the pattern is not simply `**`: a grain document
        # beside a ledger is left alone, and a ledger OUTSIDE the roadmap dir
        # is not claimed by a pattern anchored to it.
        for rel in (f'{ROADMAP}/milestones/0.1.md', 'pm/ledger.jsonl',
                    'ledger.jsonl'):
            said = git(root, 'check-attr', 'merge', '--', rel)
            assert said.strip().endswith(': unspecified'), said
        # And the depth the glob DOES reach, asserted rather than assumed:
        # `**` matches any number of directories, so a ledger filed deeper in
        # its pool would be covered too. Harmless — D3 gives a milestone one
        # ledger — and it is here so that narrowing the pattern later fails
        # HERE rather than in somebody's merge.
        deep = f'{ROADMAP}/ledgers/archived/0.1.jsonl'
        said = git(root, 'check-attr', 'merge', '--', deep)
        assert said.strip() == f'{deep}: merge: union', said
