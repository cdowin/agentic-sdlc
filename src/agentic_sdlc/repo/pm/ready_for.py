"""ready_for.py — the three belt-entry conditions, each answering with an exit code.

A belt refuses to start until the belt below it is finished. All three
conditions were already computable — `pm status` knows the story states,
`check pm` D1 already asserts a `reviewed:` pointer resolves, and
`verdict.parse` already returns dispositions. **Nothing here re-implements any
of that.** What was missing is a verb that answers with an EXIT CODE, so a step
machine can gate on it and an operator cannot mis-read it (D3's ladder: these
are the gates BETWEEN rungs, not rungs themselves).

    ready-for feature   <feature-id>    is every story `done`?
    ready-for milestone <milestone-id>  is every feature `done`, each with a
                                        non-empty review record?
    ready-for tag       <milestone-id>  is every finding at a disposition other
                                        than `open`?

Exit 0 ready · 1 not ready · 2 usage or config. Nothing is written, ever: all
three are read verbs over a tree, and `pm vocabulary` is unchanged because
these introduce no state.

**Exit 1 NAMES the blockers. It never counts them.** `3 stories not at
reviewing` sends someone to `pm status` to re-derive what the machine already
had in hand; `0.1/alpha/s1 is building` is actionable. The count survives only
as the trailing census line, the same shape `check pm` prints under its
`  DRIFT  ` findings — and the named lines are capped at MAX_NAMED with the
remainder DISCLOSED, never silently shortened.

The blockers are labelled `  BLOCKED  ` rather than `  DRIFT  `: a story at
`building` is a perfectly consistent tree, and calling it drift would say
something false about it in the one word a consumer's gate regex greps for.

## The two vacuity rulings, deliberately opposite, stated together

A reader who finds one of these and not the other will assume the other is a
bug, so both live here:

- **A feature with NO stories is READY** — an empty set is vacuously satisfied,
  and refusing it would make the verb unusable on doc-only features. The output
  says `vacuously ready` in those words, because "it passed and I do not know
  why" is the shape of a false PASS.
- **A milestone with ZERO features is NOT ready**, and so is one whose features
  point at zero review records. Far more likely a mis-typed id than a real
  state, so it is loud.

`stories/` is walked by `model.slot_walk`, which keeps only documents that OPEN
frontmatter — so a `stories/` directory holding nothing but a README yields
zero stories and IS vacuously ready. That is not a hidden narrowing: the census
line carries the walk's own disclosures, so "0 story/ies" never reads as a fact
about the directory when it is a fact about the filter.

## What blocks, and what is the belt below's question

`ready-for feature` blocks on any story not at `done`.

**It asked for `reviewing` until 2026-09-05, and that was wrong.** The belt
design said "every story at `reviewing`", so this verb did too, and a whole
milestone's stories were parked there — finished work, committed and green,
described by a status that says it is waiting for something. Chris, on being
shown a tree in exactly that state:

> *"We wanna capture work. We want things to be DONE. So we wanna rip through
> stories really fast. Get a story into done. Its unit tests are done. It's
> good. … And then when all the stories are done, the feature flips to
> reviewing, and then the review happens."*

`reviewing` at STORY grain is a hand-off waystation — the builder saying "look
at this" — and a hand-off is not a terminus. `done` is. Asking for `done` here
is also the STRICTER question, which is the tell that it was the right one:
a story at `reviewing` is genuinely unfinished, and a belt that admitted it
would start the feature's review over work still in motion.

A tree that closes stories through `pm feature done --cascade` — the flow where
the ORCHESTRATOR flips them, which `pm-execution.md` still permits — gets each
still-`reviewing` story named here. That is the verb telling it the cascade has
not run yet, which is a fact worth seeing rather than one to absorb.

`ready-for milestone` reads `features/` only. **Bugs do not block a
milestone**: an open bug that silently blocked a milestone whose features were
all closed would leave nobody able to find out why from the output. If bugs
should block, that is a ruling to make, not a defect to fix here.

`ready-for tag` reads the features' `reviewed:` pointers PLUS any record the
milestone document itself points at — NOT a sweep of `[pm] review_dir`, which
would read records belonging to other milestones. A feature with a BLANK
pointer is not a blocker for `tag`: whether the review happened is
`ready-for milestone`'s question, one rung down, and answering it twice in two
places is how the two answers drift apart. A pointer that is PRESENT and
unusable is a blocker in both.

## UNVERIFIABLE is never a pass

`verdict.parse` raises `NoVerdict` for a record with no verdict block and
`MalformedVerdict` for a broken one. **Both are blockers here**, reported as
`UNVERIFIABLE` with the record path and the parser's own message — inherited,
not softened. A record whose verdict block does not parse is the single easiest
way to get a false green out of this verb, and a false PASS here is exactly the
failure that let 0.24.0 run its gate before its review. A record that parses to
ZERO findings is a pass for that record and is printed anyway, because a record
the verb never opened must not look identical to a clean one.

Every verdict block in a record is read (`parse` returns a list, one per pass):
a clean first block does not excuse a malformed or open-carrying second one.
A block that is a header row with no rows under it is zero findings and a pass
— exactly what `parse` returns for it, unreinterpreted. A separator row under
the header is `MalformedVerdict` and therefore UNVERIFIABLE, also `parse`'s
own ruling.

## The pointer is a payload, and it is refused like one

`_record` is the ONE resolver both `milestone` and `tag` read a `reviewed:`
pointer through, so the two cannot come to different answers about the same
value. It refuses — as a BLOCKER, naming the feature, never as a crash and
never by reaching for the file — anything absolute, home-relative, schemed,
glob-shaped, backslash-separated, dot-segmented, over-long, or symlinked; and
it bounds the read, so a 10 MB record is reported rather than consumed. This is
stricter than `model.record_resolves`, which D1 reads and which accepts an
absolute pointer: hard rule 8 says nothing here reads a path outside this
checkout, and a gate answering about `/etc/passwd` would.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agentic_sdlc.repo.pm import model, verdict
from agentic_sdlc.repo.pm.cli import Usage, _grain_file, _grain_kind, _ok

# The closed set of questions. Three, and an unknown one names all three.
FEATURE, MILESTONE, TAG = 'feature', 'milestone', 'tag'
KINDS = (FEATURE, MILESTONE, TAG)

# Derived, never re-listed: a second spelling of the vocabulary goes stale in
# silence, which is how D2's tuple used to drift.
DONE = model.LIFECYCLE[-1]

# How many blockers are NAMED before the rest are disclosed as a remainder. A
# cap is needed (200 blocking stories is a scroll, not a report) and a silent
# one would be the tally this verb exists to refuse, so the truncation says so.
MAX_NAMED = 50

# A `reviewed:` pointer is a repo-relative path to one prose file. Both bounds
# are refusals, not truncations: an over-long pointer and an over-large record
# are each reported rather than followed.
MAX_POINTER_LEN = 512
MAX_RECORD_BYTES = 1 << 20

READY = 'READY'
NOT_READY = 'NOT READY'
BLOCKED = '  BLOCKED  '
RECORD = '  RECORD   '
VACUOUS = 'vacuously ready'
UNVERIFIABLE = 'UNVERIFIABLE'


# --- reporting ----------------------------------------------------------------
def _answer(subject: str, blockers: list[str], census: str) -> int:
    """Print the verdict for one question and return its exit code.

    The one place the 0/1 contract is spelled, so the three predicates cannot
    disagree about which is which.
    """
    if not blockers:
        _ok(f'{READY} — {subject}: {census}')
        return 0
    for msg in blockers[:MAX_NAMED]:
        print(f'{BLOCKED}{msg}')
    if len(blockers) > MAX_NAMED:
        print(f'{BLOCKED}... and {len(blockers) - MAX_NAMED} more not named '
              f'(cap {MAX_NAMED}) — every one of them blocks')
    _ok(f'{NOT_READY} — {subject}: {len(blockers)} blocker(s) named above, '
        f'across {census}')
    return 1


# --- grain resolution ---------------------------------------------------------
def _grain(cfg: model.PmConfig, kind: str, gid: str, doc: str, noun: str,
           asks: str) -> Path:
    """The grain file `gid` names, or exit 2 — and it must be the RIGHT kind.

    `_grain_file` is the resolver every other verb here uses, so traversal,
    globs, absolute paths, backslashes, dot and empty segments, over-long ids
    and control characters refuse identically; a second grammar would be a
    second answer. What this adds is the kind check, because a story id handed
    to `ready-for feature` resolves to a real file and would get the wrong
    question answered about it — the quietest way this verb could lie.

    Neither half reads a grain's CONTENT: resolution stats, and the kind is
    decided by the id's shape and the file's slot name.
    """
    path = _grain_file(cfg, gid)
    if path.name != doc:
        raise Usage(f'{gid!r} is a {_grain_kind(gid)}, not a {noun} — '
                    f'`ready-for {kind}` asks {asks}')
    return path


def _needs_state(state: str, states: tuple[str, ...], grain: str,
                 key: str) -> None:
    """Refuse (exit 2) when the project's vocabulary cannot express the question.

    A project that renamed its lifecycle out from under `reviewing` or `done`
    leaves this predicate with nothing to compare, and a predicate that reports
    nothing must say why — silence over an unanswerable question reads as a
    clean tree (rule 4).
    """
    if state not in states:
        raise Usage(f'devkit.toml [pm] {key} does not carry {state!r} '
                    f'({", ".join(states)}), '
                    f'so "is every {grain} at {state}" has no answer in this '
                    f'project — this verb cannot report on a vocabulary that '
                    f'cannot express it')


# --- the review-record payload ------------------------------------------------
@dataclass
class Record:
    """One resolved review record: where it was pointed at from, and its text."""

    pointer: str
    path: Path
    text: str


def _pointer_defect(pointer: str) -> str | None:
    """Why this `reviewed:` value may not be followed, by SHAPE alone.

    Every branch decides before anything is opened, so a traversal, a scheme or
    a glob is refused without a stat — hard rule 8 is a claim about what this
    package reads, and a claim tested by trying is not the claim.
    """
    if not pointer or pointer == 'null':
        return 'reviewed: is blank — no review record is named'
    if len(pointer) > MAX_POINTER_LEN:
        return (f'reviewed: is {len(pointer)} characters — a pointer is a '
                f'repo-relative path of at most {MAX_POINTER_LEN}')
    if pointer.strip() != pointer or any(ch.isspace() for ch in pointer):
        return f'reviewed: {pointer!r} carries whitespace — it names one file'
    if not model.id_is_literal(pointer):
        return (f'reviewed: {pointer!r} is a glob — a pointer that matches two '
                f'records proves neither')
    if '://' in pointer or pointer.lower().startswith('file:'):
        return f'reviewed: {pointer!r} is a URL — nothing is fetched'
    if pointer.startswith('/'):
        return (f'reviewed: {pointer!r} is absolute — a pointer is '
                f'repo-relative, and nothing outside the checkout is read')
    if pointer.startswith('~'):
        return f'reviewed: {pointer!r} is home-relative — nothing is expanded'
    if '\\' in pointer:
        return f'reviewed: {pointer!r} — a backslash is not a path separator'
    if any(seg in ('', '.', '..') for seg in pointer.split('/')):
        return (f'reviewed: {pointer!r} carries an empty or dot segment — a '
                f'pointer names a file under this checkout')
    return None


def _record(cfg: model.PmConfig, pointer: str) -> tuple[Record | None, str | None]:
    """(record, defect) for one `reviewed:` pointer — exactly one is not None.

    The single resolver behind both `ready-for milestone` and `ready-for tag`
    (criterion 6 of story 03): two copies would be two rulings about the same
    bytes. A defect is a BLOCKER string, never an exception — an unreadable
    pointer is a fact about the tree, and this verb reports facts.

    An EMPTY record is a defect. `check pm` D1 asks only whether the pointer
    resolves, which a zero-byte file satisfies while proving nothing.
    """
    defect = _pointer_defect(pointer)
    if defect is not None:
        return None, defect
    target = cfg.root / pointer
    if target.is_symlink():
        return None, (f'reviewed: {pointer!r} is a symlink — it is not '
                      f'followed, because where it lands is not this tree')
    root = Path(os.path.realpath(cfg.root))
    if not Path(os.path.realpath(target)).is_relative_to(root):
        return None, (f'reviewed: {pointer!r} resolves outside the checkout '
                      f'— nothing there is read')
    if not target.exists():
        return None, f'reviewed: names no file ({pointer})'
    if target.is_dir():
        return None, f'reviewed: names a directory, not a record ({pointer})'
    if not target.is_file():
        return None, f'reviewed: names something that is not a file ({pointer})'
    size = target.stat().st_size
    if size > MAX_RECORD_BYTES:
        return None, (f'reviewed: the record is {size} bytes, over the '
                      f'{MAX_RECORD_BYTES}-byte read bound ({pointer})')
    try:
        text = target.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as err:
        return None, (f'reviewed: the record cannot be read as UTF-8 '
                      f'({pointer}): {err}')
    if not text.strip():
        return None, (f'reviewed: the record is empty ({pointer}) — a file '
                      f'that is there proves the pointer, not the review')
    return Record(pointer, target, text), None


# --- story -> feature ---------------------------------------------------------
def ready_for_feature(cfg: model.PmConfig, fid: str) -> int:
    """Is every story under this feature `done`?

    `done`, not `reviewing` — see the module docstring for the day that changed
    and why the stricter question was the right one.

    Exit 1 names each story that is not, with the status word the file
    ACTUALLY holds — including one outside the vocabulary (the D4 drift
    `check pm` reports). This verb reports what the file says and never
    repairs it.

    A feature with NO stories is READY; see the module docstring for why both
    vacuity rulings are stated together.
    """
    _needs_state(DONE, cfg.story_states, 'story', 'story_states')
    ffile = _grain(cfg, FEATURE, fid, model.FEATURE_DOC, FEATURE,
                   "about a feature's stories")
    walk = model.slot_walk(ffile.parent / 'stories')
    blockers = []
    for sfile in walk.kept:
        status = model.field_of(sfile, 'status') or '(no status:)'
        if status != DONE:
            sid = model.unquote(model.field_of(sfile, 'id')) or cfg.rel(sfile)
            blockers.append(f'{sid} is {status}')
    census = walk.census('story/ies')
    if not walk.kept:
        census += (f' — {VACUOUS}: an empty set is satisfied, and refusing it '
                   f'would make this verb unusable on a doc-only feature')
    elif not blockers:
        census += f', all {DONE}'
    return _answer(f'{FEATURE} {fid}', blockers, census)


# --- feature -> milestone -----------------------------------------------------
def _features(cfg: model.PmConfig, mdir: Path) -> list[tuple[str, Path]]:
    """(id, path) per feature under this milestone, in reading order.

    `model.feature_files` walks `features/` and nothing else, which is why
    `bugs/` cannot enter either predicate — a file under `bugs/` shaped exactly
    like a feature is still not one.
    """
    return [(model.unquote(model.field_of(ff, 'id')) or cfg.rel(ff), ff)
            for ff in model.feature_files(mdir)]


def ready_for_milestone(cfg: model.PmConfig, mid: str) -> int:
    """Is every feature `done`, each with a resolving, NON-EMPTY review record?

    Exit 1 names each blocker and which of the two conditions it failed. A
    milestone with ZERO features exits 1 — the opposite of the empty-story
    ruling one rung down, and deliberately so (module docstring).

    Bugs do not participate. An open bug that blocked a milestone whose
    features were all closed would be unexplainable from this output.
    """
    _needs_state(DONE, cfg.feature_states, 'feature', 'feature_states')
    mfile = _grain(cfg, MILESTONE, mid, model.MILESTONE_DOC, MILESTONE,
                   "about a milestone's features")
    features = _features(cfg, mfile.parent)
    subject = f'{MILESTONE} {mid}'
    if not features:
        return _answer(subject,
                       # Worded to share NO phrase with the feature belt's
                       # empty-set wording: the two rulings are opposite, and a
                       # grep of a transcript must not be able to confuse them.
                       [f'{mid} has no features — an empty feature set does '
                        f'not satisfy this belt; a mis-typed id looks exactly '
                        f'like this'],
                       '0 feature(s)')
    blockers = []
    for fid, ffile in features:
        status = model.field_of(ffile, 'status') or '(no status:)'
        if status != DONE:
            blockers.append(f'{fid} is {status}')
            continue
        _, defect = _record(cfg, model.unquote(model.field_of(ffile, 'reviewed')))
        if defect is not None:
            blockers.append(f'{fid} is {DONE}, {defect}')
    census = f'{len(features)} feature(s)'
    if not blockers:
        census += f', all {DONE} with a record'
    return _answer(subject, blockers, census)


# --- milestone -> tag ---------------------------------------------------------
def _pointers(cfg: model.PmConfig, mid: str,
              mfile: Path) -> list[tuple[str, str]]:
    """(owner, pointer) for every record this milestone points at.

    The features' `reviewed:` pointers plus the milestone document's own, so a
    milestone-level cross-cutting review — the pass that files the findings
    this verb reads — is not invisible to the verb that gates on it. A
    `[pm] review_dir` sweep would also read other milestones' records, which is
    why it is not the source.
    """
    owned = [(fid, model.unquote(model.field_of(ffile, 'reviewed')))
             for fid, ffile in _features(cfg, mfile.parent)]
    owned.append((mid, model.unquote(model.field_of(mfile, 'reviewed'))))
    return owned


def ready_for_tag(cfg: model.PmConfig, mid: str) -> int:
    """Is every finding in every record this milestone points at NOT `open`?

    Exit 1 names the finding ids and the record each came from. This is the
    question 0.24.0's release did not ask: it ran `make milestone` before the
    reviewer, twice, over six findings sitting at `disposition: open`.

    A record that cannot be parsed is UNVERIFIABLE and blocks; a record that
    parses clean is printed with its finding count. A milestone pointing at NO
    records blocks. See the module docstring for all three rulings.
    """
    mfile = _grain(cfg, TAG, mid, model.MILESTONE_DOC, MILESTONE,
                   "about a milestone's review records")
    blockers: list[str] = []
    records: dict[Path, Record] = {}
    for owner, pointer in _pointers(cfg, mid, mfile):
        if not pointer or pointer == 'null':
            # One rung down's question: whether the review HAPPENED is
            # `ready-for milestone`. Answering it here too is a second answer.
            continue
        record, defect = _record(cfg, pointer)
        if defect is not None:
            blockers.append(f'{owner}: {defect}')
        elif record is not None:
            records.setdefault(record.path, record)

    findings = 0
    for record in records.values():
        rel = cfg.rel(record.path)
        try:
            passes = verdict.parse(record.text)
        except (verdict.NoVerdict, verdict.MalformedVerdict) as err:
            # The parser's own message, flattened to one line: it names the
            # line number and the offending text, and a blocker is one line.
            blockers.append(f'{UNVERIFIABLE} {rel}: '
                            f'{" ".join(str(err).split())}')
            continue
        opened = [f.id for p in passes for f in p.findings
                  if f.disposition_kind == verdict.OPEN]
        mine = sum(len(p.findings) for p in passes)
        findings += mine
        if opened:
            blockers.append(f'{", ".join(opened)} open in {rel}')
        else:
            # Printed on the PASSING path too: a record contributing nothing
            # must be visibly counted, or a record the verb never opened looks
            # identical to a clean one.
            print(f'{RECORD}{rel} — {mine} finding(s), none open')
    if not records:
        blockers.append(
            f'{mid} points at no review record — the record set was empty, '
            f'which is not a pass; a tag over an unreviewed milestone is the '
            f'failure this verb exists to refuse')
    census = f'{len(records)} record(s), {findings} finding(s)'
    if not blockers:
        census += ', none open'
    return _answer(f'{TAG} {mid}', blockers, census)


# --- the verb -----------------------------------------------------------------
PREDICATES = {FEATURE: ready_for_feature, MILESTONE: ready_for_milestone,
              TAG: ready_for_tag}


def cmd_ready_for(cfg: model.PmConfig, args: list[str]) -> int:
    """`pm ready-for <kind> <id>` — one kind, one id, no flags, no defaults.

    Every refusal here is exit 2 and writes nothing: a typo is a usage error,
    never a finding, and 1 has to keep meaning "the belt below is not
    finished" or a step machine cannot tell the two apart.
    """
    if not args:
        raise Usage(f'ready-for needs a kind — one of {", ".join(KINDS)}')
    kind, rest = args[0], args[1:]
    if kind not in KINDS:
        raise Usage(f'unknown kind {kind!r} — ready-for asks one of '
                    f'{", ".join(KINDS)}')
    flags = [a for a in rest if a.startswith('-')]
    if flags:
        raise Usage(f'ready-for takes no flags and {flags[0]!r} is not '
                    f'silently ignored — the answer IS the exit code '
                    f'(0 ready, 1 not ready, 2 usage)')
    if len(rest) != 1:
        raise Usage(f'ready-for {kind} needs exactly one id, got {len(rest)} — '
                    f'it never adopts the building milestone as a default '
                    f'subject, and which of two ids was meant is not this '
                    f"verb's to pick")
    return PREDICATES[kind](cfg, rest[0])
