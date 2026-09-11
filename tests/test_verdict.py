"""test_verdict.py — the verdict block: what it reads, and what it refuses.

An INPUT SURFACE (SDLC.md §5), and the one place a milestone's right to tag is
decided by a parse. The two ways to get this wrong are both worse than a crash:
reading a nearly-right block as "no verdict" prints a clean number over a pass
nobody counted (rule 4's read side), and reading a partly-right one as a partial
list is the write-side twin — a yield figure that looks legitimate and is not.

So what survives here is one of three claims:

    it parses      the shape the shipped agent definitions emit, whitespace,
                   case, CRLF and multi-pass records included;
    it refuses     whole, with the line number and the offending line, for
                   every near-miss the grammar admits;
    it is there    the shipped definitions' own example block is one THIS
                   parser accepts — a parser for a block nobody is told to
                   write is a parser that always returns NoVerdict.

**Cut in 0.2.0 (feature `the-proof-is-named-in-the-criterion`, phase B):** the
per-word re-proofs of one grammar (one parametrized family over the vocabulary
proves it), and the assertions on refusal WORDING — which sentence a refusal
uses is not what gates a tag; that it refuses at all, wholly, and names its
line is. The refusal families below are parametrized rather than deleted: an
unreadable disposition and a mis-shaped row are the cases a review record
actually arrives in.
"""
from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402,F401  (puts src/ on the path)

from agentic_sdlc.repo import install  # noqa: E402
from agentic_sdlc.repo.pm import verdict  # noqa: E402

# Every definition that instructs the block — all installables, no repo-local
# copy (one restating `reviewer.md` left in 0.2.0).
INSTALLED_REVIEWERS = ('reviewer.md', 'simplifier.md',
                       'milestone-reviewer.md', 'verification-reviewer.md')
ALL_DEFINITIONS = INSTALLED_REVIEWERS

HEADER_ROW = '| id | severity | disposition |'
FENCE = '```'


def block(*rows: str, verdict_line: str = 'verdict: SHIP-WITH-FIXES',
          header: str = HEADER_ROW, info: str = 'text') -> str:
    """A review record: prose, the fenced block, prose."""
    return '\n'.join((
        '# Feature Review — a thing',
        '',
        'Some prose the human reads, which mentions a verdict in passing.',
        '',
        f'{FENCE}{info}',
        verdict_line,
        header,
        *rows,
        FENCE,
        '',
        'A trailing paragraph.',
        ''))


def one(text: str) -> verdict.Verdict:
    """The single pass a one-block fixture carries — and a check that it IS one.

    `parse` returns a list because a record has as many verdict blocks as it
    had review passes. Every fixture below that means "the block" says so here
    rather than by indexing `[0]`, which would read a first block out of a
    record that grew a second one and call the difference nothing.
    """
    passes = verdict.parse(text)
    assert len(passes) == 1, passes
    return passes[0]


def malformed(text: str) -> verdict.MalformedVerdict:
    """The refusal — and the contract EVERY refusal owes its caller.

    The line number and the line are asserted here rather than in a case of
    their own, so no refusal can arrive without them: a `MalformedVerdict` the
    caller maps to exit 2 without them sends a reader to grep a 400-line record
    for a block they cannot describe.
    """
    with pytest.raises(verdict.MalformedVerdict) as caught:
        verdict.parse(text)
    error = caught.value
    assert error.lineno > 0, error
    assert text.split('\n')[error.lineno - 1] == error.line, error
    assert str(error.lineno) in str(error) and error.line in str(error)
    # NOTHING PARTIAL SURVIVES. A block whose first row is perfect and whose
    # second is not yields no findings at all — a yield number built from the
    # rows that happened to parse is the write-side sin, in a report.
    assert not hasattr(error, 'findings'), error
    return error


# --- what it reads ------------------------------------------------------------
@pytest.mark.parametrize('name', verdict.VERDICTS)
def test_every_verdict_in_the_closed_set_parses(name):
    """All six, each proven — a set with an untested member is a set with a
    typo in it, and the typo surfaces the day a reviewer uses that verdict.
    The header row alone is a complete block, so a clean pass is a Verdict with
    no rows and never indistinguishable from a record that wrote none."""
    parsed = one(block(verdict_line=f'verdict: {name}'))
    assert parsed == verdict.Verdict(name, [])


@pytest.mark.parametrize('severity', verdict.SEVERITIES)
def test_every_severity_in_the_closed_set_parses(severity):
    """The set is the union of the shipped definitions' grades. A severity an
    installed agent is told to assign and this parser rejects would be a parser
    that exits 2 on its own tooling's correct output."""
    parsed = one(block(f'| F1 | {severity} | landed 3a42f19ad |'))
    assert parsed.findings[0].severity == severity


def test_every_disposition_kind_and_its_raw_value():
    """The story's own example, field for field. `disposition_value` is the
    RAW thing (D5): the hash, the reason, the grain id — nothing inferred."""
    parsed = one(block(
        '| W1 | WARNING | landed 3a42f19ad |',
        '| S3 | SUGGESTION | rejected: pause regression |',
        '| D2 | DELTA | deferred: 0.90.3/throwable-as-behavior |',
        '| Q5 | QUESTION | open |'))
    assert parsed.verdict == 'SHIP-WITH-FIXES'
    assert parsed.findings == [
        verdict.Finding('W1', 'WARNING', 'landed', '3a42f19ad'),
        verdict.Finding('S3', 'SUGGESTION', 'rejected', 'pause regression'),
        verdict.Finding('D2', 'DELTA', 'deferred', '0.90.3/throwable-as-behavior'),
        verdict.Finding('Q5', 'QUESTION', 'open', ''),
    ]
    assert {f.disposition_kind for f in parsed.findings} == set(verdict.DISPOSITION_KINDS)


def test_open_and_landed_in_place_are_read_as_themselves():
    """R2 and `open`, the two dispositions a record written HERE actually
    carries, and the two a lazy grammar would lose.

    A record written BEFORE the landing pass has findings nobody has acted on;
    without a kind for that an honest author misfiles them as `rejected:` (this
    repo's own 0.23.0 records did) and the yield column reads a lie. And
    reviewers in this SDLC fix in place and never commit, so at the moment the
    record is written a landed fix HAS no hash — `landed <hex>` alone
    under-counts exactly the findings that were acted on.

    Both are fixed tokens that fold case, both keep their raw note, and both sit
    in the closed set the refusals name.
    """
    assert verdict.OPEN in verdict.DISPOSITION_KINDS
    parsed = one(block('| C1 | CRITICAL | OPEN |',
                       '| M1 | MAJOR | open: awaiting the landing pass |',
                       '| W1 | WARNING | landed 3a42f19ad |',
                       '| M4 | MAJOR | LANDED In-Place |'))
    assert parsed.findings == [
        verdict.Finding('C1', 'CRITICAL', verdict.OPEN, ''),
        verdict.Finding('M1', 'MAJOR', verdict.OPEN, 'awaiting the landing pass'),
        verdict.Finding('W1', 'WARNING', 'landed', '3a42f19ad'),
        verdict.Finding('M4', 'MAJOR', 'landed', verdict.IN_PLACE),
    ]


def test_the_block_is_found_with_prose_and_other_fenced_blocks_around_it():
    """A real record is mostly prose and quotes commands. Neither may hide the
    block, and neither may be mistaken for one."""
    text = ('# Review\n\nEvidence:\n\n```console\n$ make precommit\n'
            'PASS\n```\n\nMore prose.\n\n' + block('| N1 | NIT | rejected: taste |')
            + '\n```python\nverdict = "not this one"\n```\n')
    parsed = one(text)
    assert parsed.verdict == 'SHIP-WITH-FIXES'
    assert [f.id for f in parsed.findings] == ['N1']


def test_ragged_whitespace_case_and_CRLF_all_read_as_one_record():
    """Tolerant on the cells, strict on the shape — the one rule the module
    states, and the three ways a real record differs from the canonical bytes:
    ragged column padding is how a human edits a markdown table, a CRLF record
    is one round-tripped through a Windows editor, and case folds because the
    author typed `Verdict:`. Detection is generous so nothing is silently
    missed; the stored value is canonical so the report groups `Warning` and
    `WARNING` as one severity instead of two rows in its own output.
    """
    canonical = block('| W1 | WARNING | landed 3a42f19ad |',
                      '| D2 | DELTA | deferred: 0.22.0/review-record-shape |')
    # The id is raw — it is not a closed set — so only the FIXED keywords fold.
    ragged = block('|   W1    |   Warning   |   LANDED 3a42f19ad   |',
                   '',
                   '|D2|delta|Deferred: 0.22.0/review-record-shape|',
                   verdict_line='Verdict: ship-with-fixes')
    assert verdict.parse(ragged) == verdict.parse(canonical)
    assert verdict.parse(canonical.replace('\n', '\r\n')) == verdict.parse(canonical)
    # `core.markdown` owns the fence rules; this module must not have quietly
    # re-implemented half of them as 'a line of three backticks'.
    assert one('# R\n\n~~~\nverdict: HOLD\n' + HEADER_ROW + '\n~~~\n').verdict == 'HOLD'
    # ...and the raw half of a folded cell stays raw: a hash is not a closed set.
    assert verdict.parse(ragged)[0].findings[0].disposition_value == '3a42f19ad'


# --- multi-pass: one record, one Verdict per PASS -----------------------------
def test_three_passes_over_one_record_each_keep_their_own_findings():
    """The shape the re-ordered protocol produces: raised, landed, cleared.

    This replaced `test_two_blocks_refuse_and_name_the_second`, which encoded a
    reading that made the package unable to parse the record its own SDLC
    produces — three review passes append three blocks to one record, and the
    refusal turned `pm ledger report` into exit 2 at the moment the third
    landed. Flattening them loses the fact that findings were acted on BETWEEN
    passes, which is the one thing a multi-pass record is evidence of.
    """
    text = '\n'.join((
        block('| C1 | CRITICAL | open |', '| m1 | MINOR | open |',
              verdict_line='verdict: RELEASE-WITH-FIXES'),
        block('| C1 | CRITICAL | landed 3a42f19ad |',
              verdict_line='verdict: RELEASE-WITH-FIXES'),
        block(verdict_line='verdict: RELEASE-SAFE')))
    passes = verdict.parse(text)
    assert [p.verdict for p in passes] == [
        'RELEASE-WITH-FIXES', 'RELEASE-WITH-FIXES', 'RELEASE-SAFE']
    assert [len(p.findings) for p in passes] == [2, 1, 0]
    assert [f.disposition_kind for f in passes[0].findings] == ['open', 'open']
    assert passes[1].findings[0].disposition_kind == 'landed'


def test_a_malformed_LATER_block_refuses_the_whole_record():
    """A good first pass does not make a bad third one readable. Returning the
    two that parsed would print a yield number over a pass nobody counted —
    the read-side sin, arriving through a record that grew."""
    error = malformed(block('| W1 | WARNING | landed 3a42f19ad |') + '\n'
                      + block('| S3 | WHATEVER | rejected: no |',
                              verdict_line='verdict: HOLD'))
    assert error.line == '| S3 | WHATEVER | rejected: no |'


# --- no block is a FACT, not a failure ----------------------------------------
@pytest.mark.parametrize('text', (
    # nothing block-shaped at all
    '# Review\n\nAll good.\n\n```\nmake precommit\n```\n',
    # the corpus's own shape: `**Verdict: RELEASE-WITH-FIXES**` heads two
    # milestone records. Reading the narration is the one source this package's
    # SDLC refuses to trust, so the fence is load-bearing, not decoration.
    '# Review\n\n**Verdict: RELEASE-WITH-FIXES** — one MAJOR.\n\nFindings follow.\n',
    # a lone unfenced `verdict:` far from any header is prose, and claiming it
    # would turn every record that DISCUSSES verdicts into exit 2
    '# R\n\nverdict: HOLD\n\n\n\n\nprose\n\n' + HEADER_ROW + '\n',
    # an unterminated fence over something else is `check doc`'s finding, not
    # this module's — claiming it makes every malformed markdown file a verdict
    # error
    '# R\n\n' + FENCE + 'text\n$ make precommit\n',
))
def test_a_record_with_no_block_is_NoVerdict_and_not_a_refusal(text):
    """The two failures are different questions for a human: "nobody wrote one
    yet" is a line in the report, "this one is broken" is exit 2. A caller
    cannot tell them apart if they arrive as the same exception."""
    with pytest.raises(verdict.NoVerdict):
        verdict.parse(text)


# --- what it refuses: a block that cannot be read correctly -------------------
@pytest.mark.parametrize('row, why', (
    ('| S3 | rejected: no |', '2 cell(s)'),
    ('| W1 | WARNING | landed 3a42f19ad | extra |', '4 cell(s)'),
    ('| W1 | SEVERE | landed 3a42f19ad |', "unknown severity 'SEVERE'"),
    ('|  | WARNING | landed 3a42f19ad |', 'id cell is empty'),
    ('| W 1 | WARNING | landed 3a42f19ad |', 'one token'),
    ('| ' + 'W' * (verdict.MAX_ID_LEN + 1) + ' | WARNING | landed 3a42f19ad |',
     f'{verdict.MAX_ID_LEN + 1} characters'),
    # a line in the block that is not a row at all
    ('W1 | WARNING | landed 3a42f19ad', 'opens and closes'),
    ('| W1 | WARNING | landed 3a42f19ad', 'opens and closes'),
    ('W1 | WARNING | landed 3a42f19ad |', 'opens and closes'),
    ('|', 'opens and closes'),
    ('a sentence that wandered into the block', 'opens and closes'),
))
def test_a_row_the_grammar_cannot_read_refuses_whole(row, why):
    """The closed sets and the fixed width are the point: a free-text severity
    column makes "findings by severity" a column of one-off strings, and a row
    the parser silently dropped is a finding that left the count."""
    assert why in malformed(block(row)).why


@pytest.mark.parametrize('verdict_line, why', (
    ('verdict: LGTM', "unknown verdict 'LGTM'"),
    ('verdict:', "unknown verdict ''"),
))
def test_an_unreadable_verdict_word_refuses_and_lists_the_set(verdict_line, why):
    error = malformed(block(verdict_line=verdict_line))
    assert why in error.why
    for name in verdict.VERDICTS:
        assert name in error.why


@pytest.mark.parametrize('disposition', (
    # `landed` without a usable hash: a disposition nobody can follow up, which
    # is worse than a missing row because it reads as evidence.
    'landed',                          # no hash at all
    'landed ',                         # the separator and nothing after it
    'landed 3a42f1',                   # six — shorter than git's short hash
    'landed ' + 'a' * 41,              # longer than a full hash
    'landed zzzzzzz',                  # right length, not hex
    'landed 3a42f19ad and also 9b1',   # two, so which one
    'landed: 3a42f19ad',               # the colon form; the grammar uses a space
    # `landed in-place` is a FIXED token, not free text: `landed <anything>`
    # would make the column unreadable, which is why the hash form is bounded.
    'landed inplace',
    'landed in place',
    'landed in-place 3a42f19ad',
    'in-place',                        # without the keyword it is not one
    # `open` admits the bare word or a noted form, and nothing that merely
    # starts or ends with the token.
    'open:',
    'open awaiting',
    'opened',
    'reopen',
    # the two kinds whose value is the whole point of the row
    'deferred: ',
    'rejected: ',
    # and a kind that is not in the closed set at all
    'wontfix',
))
def test_an_unreadable_disposition_refuses(disposition):
    """The disposition column is what makes yield computable. Every near-miss
    here would otherwise land as a row the report counts as something it is
    not — a rejected finding read as landed, or a hash nobody can resolve."""
    assert 'unreadable disposition' in malformed(
        block(f'| M4 | MAJOR | {disposition} |')).why


@pytest.mark.parametrize('target', (
    '..',                     # traversal
    '../0.21.0',
    '0.22.0/../../etc',
    '.',                      # the dot segment
    '0.22.0//story',          # an empty segment
    '/0.22.0',                # absolute
    '0.90.3/*',               # a glob
    '0.90.3/throw[ab]le',
    'a\\b',                   # a backslash
    'a/b/c/d',                # deeper than milestone/feature/story
))
def test_a_deferred_that_is_not_a_grain_id_refuses(target):
    """A deferral names the grain that will carry the finding, so the segment
    guard is the resolvers' own: what `pm` refuses to RESOLVE this refuses to
    RECORD. A deferral to `../../etc` is a pointer the next milestone follows."""
    error = malformed(block(f'| D2 | DELTA | deferred: {target} |'))
    assert 'is not a grain id' in error.why or 'unreadable disposition' in error.why


@pytest.mark.parametrize('row', (
    '|---|---|---|',                  # the tight spelling
    '| --- | --- | --- |',            # the padded one
    '|:---|:---:|---:|',              # column alignment
    '| - | - | - |',                  # one hyphen is a legal separator too
    '|---|---|',                      # the wrong width — still a separator row
    '|---|---|---|---|',
))
def test_a_markdown_separator_row_is_named_as_one_at_every_spelling(row):
    """`| --- | --- | --- |` is the habit every markdown table trains, and it is
    not in the shape. The refusal has to NAME it: `unknown severity '---'` is a
    true sentence about a row nobody meant to write, and it sends the author
    looking for a severity they never typed while the whole row is the mistake.
    Widths where the cell count is ALSO wrong are included for the same reason —
    "2 cell(s)" sends them to add a column to a row that should not exist.
    """
    error = malformed(block(row, '| W1 | WARNING | landed 3a42f19ad |'))
    assert 'a markdown separator row is not a finding — drop it' in error.why
    assert 'severity' not in error.why, (
        'the refusal still blames the severity cell for a row that has none')


@pytest.mark.parametrize('row', (
    '| W1 | WARNING | landed 3a42f19ad |',    # a real finding, hyphen-free
    '| -1 | WARNING | landed 3a42f19ad |',    # an id that merely starts with one
    '| --- | WARNING | landed 3a42f19ad |',   # only ONE cell is separator-shaped
))
def test_a_row_that_is_not_a_separator_is_not_called_one(row):
    """The other side of the shape: every cell has to be separator-shaped, so a
    finding is never mistaken for the row above it."""
    try:
        verdict.parse(block(row))
    except verdict.MalformedVerdict as error:
        assert 'separator row' not in error.why


@pytest.mark.parametrize('header', (
    None,                                     # no header row at all
    '| id | severity |',
    '| id | grade | disposition |',
    '| severity | id | disposition |',
    '| W1 | WARNING | landed 3a42f19ad |',
))
def test_a_wrong_or_missing_header_row_refuses(header):
    """The header is part of the shape. Without it the first finding silently
    becomes the header and vanishes from the count."""
    if header is None:
        text = '# R\n\n' + FENCE + 'text\nverdict: SHIP\n' + FENCE + '\n'
        assert 'no header row' in malformed(text).why
        return
    error = malformed(block(header=header))
    assert 'header row must read' in error.why or 'cell(s)' in error.why


# --- the quiet misses: a block that is nearly there --------------------------
def test_an_unterminated_fence_over_a_verdict_refuses_instead_of_reporting_none():
    """An unclosed fence masks nothing, so the block is in no block list at all
    — and NoVerdict over a record whose verdict is sitting right there is the
    read-side cardinal sin."""
    text = '# R\n\n' + FENCE + 'text\nverdict: SHIP\n' + HEADER_ROW + '\n'
    error = malformed(text)
    assert 'never closed' in error.why
    assert error.lineno == 3


def test_an_unfenced_verdict_followed_by_the_header_refuses():
    """R3, the same miss by the second route. A reviewer who forgot the fence
    wrote a verdict; reporting "no verdict block" over it prints a clean number
    for a pass nobody counted."""
    text = ('# Review\n\nProse.\n\nverdict: SHIP-WITH-FIXES\n'
            + HEADER_ROW + '\n| W1 | WARNING | landed in-place |\n')
    error = malformed(text)
    assert 'not fenced' in error.why
    assert error.line == 'verdict: SHIP-WITH-FIXES'


def test_a_properly_fenced_block_is_not_disturbed_by_an_unfenced_near_miss():
    """The near-miss check runs only on the path that would otherwise report
    NONE. A record that quotes an example beside its real block still parses —
    a refusal there would redden every record that documents the shape."""
    text = block('| W1 | WARNING | landed in-place |') + (
        '\nFor reference the shape is\n\nverdict: HOLD\n' + HEADER_ROW + '\n')
    assert one(text).verdict == 'SHIP-WITH-FIXES'


# --- it is there: the shipped definitions ask for the block -------------------
def definition(name: str) -> str:
    """Any of the four installables, read the way `install.py` reads it."""
    return resources.files(install.PACKAGE).joinpath(name).read_text(encoding='utf-8')


@pytest.mark.parametrize('name', ALL_DEFINITIONS)
def test_the_example_block_in_each_definition_is_one_this_parser_accepts(name):
    """The shipped example, fed to the shipped parser — the strong form of "the
    instruction is half the feature". A definition demonstrating a block the
    parser rejects is how every review record in a consumer starts exiting 2,
    and it is pinned per file because a rewrite drops one file at a time.

    The example also has to show every disposition the parser knows, `landed
    in-place` included: an agent copies the shape it is shown, and the form
    exists for exactly the case these agents are in.
    """
    parsed = one(definition(name))
    assert parsed.verdict == 'SHIP-WITH-FIXES'
    assert {f.disposition_kind for f in parsed.findings} == set(verdict.DISPOSITION_KINDS)
    assert verdict.IN_PLACE in [f.disposition_value for f in parsed.findings]


def _verdict_paragraph(body: str) -> str:
    """The shared verdict paragraph out of one definition.

    ONE extractor, used for the reference and for every subject. It was two:
    the subjects were cut at the next `## ` heading and the REFERENCE ran to
    end of file, so the two agreed only while `reviewer.md` happened to end
    with this section. The first block appended after it made all five cases
    fail — against a paragraph that had not changed.

    A comparison whose two sides are built by different rules is a second
    scoreboard the size of a function.
    """
    start = body.rindex('### The verdict block')
    end = body.find('\n## ', start)
    return (body[start:] if end == -1 else body[start:end]).rstrip('\n')


PARAGRAPH = _verdict_paragraph(definition('reviewer.md'))


@pytest.mark.parametrize('name', ALL_DEFINITIONS)
def test_every_definition_carries_the_same_verdict_paragraph(name):
    """Five files, one contract. Near-copies drift, and the drift lands as a
    record the report cannot read months later — the reviewers especially,
    which has no installable, so nothing else in the suite would notice it."""
    assert _verdict_paragraph(definition(name)) == PARAGRAPH, (
        f'{name} has drifted from the shared paragraph')


# R1: one verdict vocabulary per definition, not two. These are the words these
# files used to end on, twenty lines above a block that demanded different ones.
# A reader cannot obey both, and the report reads the BLOCK — so the prose was
# the half that had to move.
@pytest.mark.parametrize('name, retired', (
    ('reviewer.md', 'PASS | PASS WITH WARNINGS | FAIL'),
    ('milestone-reviewer.md', 'EXECUTION-READY'),
    ('milestone-reviewer.md', 'READY-WITH-FIXES'),
    ('milestone-reviewer.md', 'NOT-READY'),
))
def test_the_second_verdict_vocabulary_is_gone(name, retired):
    assert retired not in definition(name), (
        f'{name} still offers {retired!r} — a prose verdict in words the '
        f'block refuses, which is two answers to one question')
