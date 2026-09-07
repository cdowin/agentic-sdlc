"""ready_for.py — the four belt-entry conditions, each answering with an exit
code.

    ready-for story     <story-id>      the story belt's own checks, minus the
                                        ones that answer only after the work
    ready-for feature   <feature-id>    every story in `done`?
    ready-for milestone <milestone-id>  every feature in `done` with a
                                        non-empty record, and no open bug?
    ready-for tag       <milestone-id>  every finding not `open`?

Exit 0 ready · 1 not ready, naming each blocker · 2 usage or config.
Nothing is written. A feature with no stories is vacuously ready; a
milestone with no features, or no records, is not. UNVERIFIABLE is never a
pass.

**The story rung's condition is DECLARED, never spelled here.** It is the
project's own `[story] steps` — `driver.step_names`, so a narrowed list is the
list — intersected with `steps.ENTRY_CONDITIONS`, the registry's own statement
of which checks are decidable before the work. Every check this verb does not
ask is NAMED in the census with why (rule 11), and the ones it does ask are the
belt's own check objects, asked rather than re-implemented.

Every rung emits `rung.enter` — `{rung, grain, ready, blockers}` — to the sink
`[emit]` declares, and nothing at all where a tree declares no `[emit]`, which
is how this verb keeps writing nothing. Emission is never load-bearing: it
changes no exit code and no printed line, and a sink that could not be written
is a finding on stderr (rule 11).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo import emit
from agentic_sdlc.repo.pm import ledger, model, verdict
from agentic_sdlc.repo.pm.cli import Usage, _grain_file, _ok

# The closed set of questions. Four, and an unknown one names all four; the
# story rung is first because it is the one an agent asks dozens of times a
# milestone.
STORY, FEATURE, MILESTONE, TAG = 'story', 'feature', 'milestone', 'tag'
KINDS = (STORY, FEATURE, MILESTONE, TAG)

# The row kind the entry tap writes. `emit.TAP_ENTER` is WHICH tap; this is
# what the row calls itself, in the `<rung>.<edge>` spelling `rung.leave` uses.
KIND_ENTER = 'rung.enter'

# The payload's boolean key, a CONSTANT because `ready` is also a word the
# story seed spells and `tests/test_pm_flow.py` holds every state literal to a
# named assignment. This is a HOMONYM, like `verdict.OPEN`: it is the ANSWER
# this verb gave, and it says nothing about any grain's status.
READY_KEY = 'ready'

# The question is a category, asked through `model.holds` so this and `check
# pm` D2 cannot disagree.
DONE = model.DONE_CATEGORY

# Named blockers are capped; the remainder is disclosed, never silently
# dropped.
MAX_NAMED = 50

# Both bounds are refusals, not truncations.
MAX_POINTER_LEN = 512
MAX_RECORD_BYTES = 1 << 20

READY = 'READY'
NOT_READY = 'NOT READY'
BLOCKED = '  BLOCKED  '
RECORD = '  RECORD   '
VACUOUS = 'vacuously ready'
UNVERIFIABLE = 'UNVERIFIABLE'


# --- reporting ----------------------------------------------------------------
class Blocker(NamedTuple):
    """One reason a rung is not ready: the check it belongs to, and the
    sentence printed for it.

    `check` is '' when the blocker is the RUNG's own answer rather than a
    named check's — a milestone with no features has no check to blame, and
    inventing a name for it would put a word in the registry's mouth.
    """

    check: str
    why: str


def _check_answered_by(rung: str) -> str:
    """The belt check this rung IS, read from the registry's shipped actions.

    `SHIPPED_ACTION` declares what answers each check, and three of its entries
    are `agentic-sdlc pm ready-for <rung> <id>` — so `stories-done` is the name
    the feature rung's blockers carry, DERIVED, and the emitted payload names
    the check `close feature` will print rather than a word chosen here. '' for
    a rung no check names.
    """
    from agentic_sdlc.repo.conveyor import steps as step_defs
    named = [name for name, action in step_defs.SHIPPED_ACTION.items()
             if f'ready-for {rung} ' in action]
    return named[0] if len(named) == 1 else ''


def _enter_row(rung: str, grain: str, blockers: list[Blocker]) -> dict:
    """The `rung.enter` payload: which rung was asked, of what, the answer,
    and the blockers as the caller's work queue (ft-one-event-shape-serves-
    three-readers). Every field is the invocation or a check name — nothing
    here decides anything.
    """
    return {'ts': ledger.utc_now(), 'kind': KIND_ENTER, 'grain': grain,
            'rung': rung, READY_KEY: not blockers,
            'blockers': [{'check': b.check, 'why': b.why} for b in blockers]}


def _emit_enter(cfg: model.PmConfig, rung: str, grain: str,
                blockers: list[Blocker]) -> None:
    """Write the entry event, or nothing, and never change the answer.

    A tree with no `[emit]` section opted out and is owed no line
    (`emit.declared`) — which is also how this verb keeps its "writes nothing"
    contract on a tree that asked for nothing. Every failure below is a finding
    said once on stderr, in `emit`'s own prefix, because an exit code that
    moved because a SINK was unwritable would make this verb unusable as a
    predicate.
    """
    row = _enter_row(rung, grain, blockers)
    try:
        if emit.declared():
            emit.emit(cfg, emit.TAP_ENTER, row)
    except Exception as err:  # noqa: BLE001 — a finding, never the answer
        print(f'{emit.FINDING_PREFIX} WARNING — the {emit.TAP_ENTER} event for '
              f'{rung} {grain} was not recorded ({type(err).__name__}: {err}); '
              f'the answer above is unaffected', file=sys.stderr)


def _answer(cfg: model.PmConfig, rung: str, grain: str, subject: str,
            blockers: list[Blocker], census: str) -> int:
    """Print the verdict for one question and return its exit code — the one
    place the 0/1 contract is spelled, and the one place `rung.enter` is
    emitted from, so no rung can answer without an event or emit one it did
    not print.
    """
    if not blockers:
        _ok(f'{READY} — {subject}: {census}')
        _emit_enter(cfg, rung, grain, blockers)
        return 0
    for blocker in blockers[:MAX_NAMED]:
        print(f'{BLOCKED}{blocker.why}')
    if len(blockers) > MAX_NAMED:
        print(f'{BLOCKED}... and {len(blockers) - MAX_NAMED} more not named '
              f'(cap {MAX_NAMED}) — every one of them blocks')
    _ok(f'{NOT_READY} — {subject}: {len(blockers)} blocker(s) named above, '
        f'across {census}')
    # The whole list, never the printed cap: the row is the work queue, and a
    # reader that had to re-run the verb to see blocker 51 has half an event.
    _emit_enter(cfg, rung, grain, blockers)
    return 1


# --- grain resolution ---------------------------------------------------------
def _kind_of(path: Path) -> str:
    """What the document at `path` says it is.

    The grain's own `kind:` since 0.4.0, with the filename as the fallback for
    a document that declares none — it used to come from the FILENAME, which is
    the path being schema.
    """
    found = model.unquote(model.field_of(path, 'kind'))
    if not found:
        # A nested tree's documents declare no `kind:`; there the slot name IS
        # the kind, which is the derivation 0.4.0 deletes and this is the last
        # place it survives.
        found = {model.MILESTONE_DOC: 'milestone',
                 model.FEATURE_DOC: 'feature'}.get(path.name, 'story')
    return found


def _grain(cfg: model.PmConfig, kind: str, gid: str, want: str, noun: str,
           asks: str) -> Path:
    """The grain file `gid` names, of the right kind, or exit 2; a story id
    handed to `ready-for feature` would get the wrong question answered.

    The kind is `_kind_of`'s, so an absent one falls back to the document name
    — which reads anything that is not a milestone or a feature document as a
    story, and is why the story rung asks the grain INDEX instead.
    """
    path = _grain_file(cfg, gid)
    found = _kind_of(path)
    if found != want:
        raise Usage(f'{gid!r} is a {found}, not a {noun} — '
                    f'`ready-for {kind}` asks {asks}')
    return path


# --- the review-record payload ------------------------------------------------
@dataclass
class Record:
    """One resolved review record: where it was pointed at from, and its text."""

    pointer: str
    path: Path
    text: str
    real: Path
    """`path` resolved. B4: the containment check already computes this, and
    keying the dedupe on `path` counted one file twice when two features spelled
    the pointer differently — `docs/reviews/r.md` and `docs/Reviews/r.md` on a
    case-insensitive filesystem. The census is what the verb prints as its proof
    of what it read, so an over-count is a false census (rule 4)."""


def _pointer_defect(pointer: str) -> str | None:
    """Why this `reviewed:` value may not be followed, decided by shape before
    anything is opened (hard rule 8).
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
    The single resolver behind `milestone` and `tag`; an empty record is a
    defect.
    """
    defect = _pointer_defect(pointer)
    if defect is not None:
        return None, defect
    target = cfg.root / pointer
    if target.is_symlink():
        return None, (f'reviewed: {pointer!r} is a symlink — it is not '
                      f'followed, because where it lands is not this tree')
    root = Path(os.path.realpath(cfg.root))
    real = Path(os.path.realpath(target))
    if not real.is_relative_to(root):
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
    return Record(pointer, target, text, real), None


# --- the edit -> story --------------------------------------------------------
def _story_subject(cfg: model.PmConfig, sid: str) -> None:
    """Refuse what cannot be a story id, and an id naming another kind.

    An id that names NOTHING is deliberately NOT refused here: `story-exists`
    is the belt's own check for exactly that, `close story` answers it at exit
    1, and this rung answering 2 to the same tree would be two rulings about
    one fact. The shape check comes first so a hostile id is still refused
    without a grain being read.
    """
    defect = model.id_defect(sid)
    if defect:
        raise Usage(f'no grain resolves from id {sid!r} — {defect}')
    # The INDEX's kind, not the document name's: the index carries the kind the
    # grain was read as, where the filename fallback in `_kind_of` reads
    # anything that is not a milestone or feature document as a story — which
    # is right for the rungs that want one of those two and would let a bug
    # through here.
    grain = model.grain_index(cfg).get(sid)
    if grain is None:
        return
    if grain.kind != STORY:
        raise Usage(f'{sid!r} is a {grain.kind}, not a {STORY} — '
                    f'`ready-for {STORY}` asks what the story belt asks '
                    f'before the work')


def _entry_condition(operation: str) -> tuple[list, list[str], tuple[str, ...]]:
    """(the checks to ask, one sentence per check NOT asked, the whole declared
    list) — the derivation, and the reason this rung is not a list of ids.

    Three runtime sources, no fourth: `driver.step_names` for the project's own
    `[<op>] steps` (a narrowed list is the list), `driver.registry_for` for the
    check objects behind those names, and `steps.ENTRY_CONDITIONS` for which of
    them the registry DECLARES decidable before the work. A check that is an
    entry condition and still runs a command is passed over too, with that as
    the reason: `ready-for` boots nothing (hard rule 2), and a rung that shelled
    out would stop being safe to ask dozens of times a milestone.
    """
    from agentic_sdlc.repo.conveyor import driver
    from agentic_sdlc.repo.conveyor import steps as step_defs
    names = driver.step_names(operation)
    known = driver.registry_for(operation)
    commands = step_defs.commands_for(operation, names, known)
    asked: list[tuple[str, object]] = []
    over: list[str] = []
    for name in names:
        runs = commands.get(name) or step_defs.SHIPPED_ACTION.get(name, '')
        if name not in step_defs.ENTRY_CONDITIONS:
            over.append(f'{name} (answers after the work'
                        + (f', by `{runs}`' if runs else '') + ')')
        elif runs:
            over.append(f'{name} (an entry condition that runs `{runs}`, and '
                        f'this verb runs nothing)')
        else:
            asked.append((name, known[name]))
    return asked, over, names


def ready_for_story(cfg: model.PmConfig, sid: str) -> int:
    """The inner loop's entry edge: the story belt's own checks that are
    decidable before the work, asked of the tree as it stands.

    The checks are ASKED, never re-implemented — `close story` and this rung
    read one registry, so the sentence a blocker carries here is the sentence
    that belt will print.
    """
    from agentic_sdlc.repo.conveyor import driver
    _story_subject(cfg, sid)
    asked, over, names = _entry_condition(STORY)
    ctx = driver.Context(root=cfg.root, operation=STORY, version=sid)
    blockers: list[Blocker] = []
    for name, check in asked:
        answer = driver.ask(check, ctx)
        if answer.is_true:
            continue
        word = (f'{UNVERIFIABLE} '
                if answer.truth is driver.Truth.UNVERIFIABLE else '')
        blockers.append(Blocker(name, f'{word}{name}: {answer.detail}'))
    census = (f'{len(asked)} of {len(names)} [{STORY}] check(s) decidable '
              f'before the work')
    if asked:
        census += f' ({", ".join(name for name, _ in asked)})'
        if not blockers:
            census += ', all true'
    else:
        # Rule 4's floor: a verdict over a census of zero is not a pass. The
        # belt declared checks and none of them can be answered yet, so nothing
        # was asked — and READY would be a claim about a question nobody put.
        blockers.append(Blocker(
            '', f'nothing was asked — [{STORY}] steps declares {len(names)} '
                f'check(s) and the registry declares none of them decidable '
                f'before the work, so this rung has no entry condition in '
                f'this tree; a READY over nothing asked is not a pass'))
    if over:
        census += f'; {len(over)} at the close: {", ".join(over)}'
    return _answer(cfg, STORY, sid, f'{STORY} {sid}', blockers, census)


# --- story -> feature ---------------------------------------------------------
def ready_for_feature(cfg: model.PmConfig, fid: str) -> int:
    """Is every story under this feature in the `done` category? Exit 1 names
    each that is not, with the word the file holds; no stories is vacuously
    ready.
    """
    ffile = _grain(cfg, FEATURE, fid, 'feature', FEATURE,
                   "about a feature's stories")
    # The stories BOUND to this feature, not the ones in a directory beneath
    # it: membership is the child's field since 0.4.0.
    kept = model.story_files(cfg, model.unquote(model.field_of(ffile, 'id'))
                             or fid)
    held = model.holds(
        cfg, 'story',
        ((model.unquote(model.field_of(sfile, 'id')) or cfg.rel(sfile),
          model.field_of(sfile, 'status') or '(no status:)')
         for sfile in kept),
        DONE)
    # One check answers this whole rung — `stories-done`, read from the
    # registry — so every blocker carries the name `close feature` will print.
    check = _check_answered_by(FEATURE)
    blockers = [Blocker(check, name) for name in held.names]
    skipped = model.pool_skipped(cfg, 'story')
    census = (f'{len(kept)} story/ies'
              + (f', {skipped} file(s) skipped (no frontmatter — not a '
                 f'grain)' if skipped else ''))
    if not kept:
        census += (f' — {VACUOUS}: an empty set is satisfied, and refusing it '
                   f'would make this verb unusable on a doc-only feature')
    elif not blockers:
        census += f', all {DONE}'
    return _answer(cfg, FEATURE, fid, f'{FEATURE} {fid}', blockers, census)


# --- feature -> milestone -----------------------------------------------------
def _features(cfg: model.PmConfig, mfile: Path) -> list[tuple[str, Path]]:
    """(id, path) per feature BOUND TO this milestone, in its declared order.

    Takes the milestone's DOCUMENT, not its directory: a pooled tree has no
    per-milestone directory, and membership is the child's field.
    """
    mid = model.unquote(model.field_of(mfile, 'id'))
    return [(model.unquote(model.field_of(ff, 'id')) or cfg.rel(ff), ff)
            for ff in model.feature_files(cfg, mid)]


def _bugs_against(cfg: model.PmConfig, mid: str) -> tuple[list, int]:
    """((id, status) for every bug whose `fix_milestone:` is `mid`), scanned
    across the whole active tree — a bug is filed where it was caught.
    """
    against = []
    scanned = 0
    for milestone in model.milestones(cfg):
        for bfile in model.bug_files(cfg, milestone.gid):
            scanned += 1
            if model.unquote(model.field_of(bfile, 'fix_milestone')) != mid:
                continue
            bid = model.unquote(model.field_of(bfile, 'id')) or cfg.rel(bfile)
            against.append((bid, model.field_of(bfile, 'status')
                            or '(no status:)'))
    return against, scanned


def ready_for_milestone(cfg: model.PmConfig, mid: str) -> int:
    """Every feature in `done` with a resolving, non-empty record, and no bug
    promised to this milestone outside `done`. Zero features exits 1,
    deliberately opposite to the empty-story ruling.
    """
    mfile = _grain(cfg, MILESTONE, mid, 'milestone', MILESTONE,
                   "about a milestone's features")
    features = _features(cfg, mfile)
    subject = f'{MILESTONE} {mid}'
    check = _check_answered_by(MILESTONE)
    if not features:
        return _answer(cfg, MILESTONE, mid, subject,
                       # Worded to share no phrase with the feature belt's
                       # empty-set line; the two rulings are opposite. No check
                       # is blamed: the rung itself is the one answering.
                       [Blocker('', f'{mid} has no features — an empty feature '
                                    f'set does not satisfy this belt; a '
                                    f'mis-typed id looks exactly like this')],
                       '0 feature(s)')
    # Asked of the feature flow, not the story flow.
    held = model.holds(
        cfg, 'feature',
        ((fid, model.field_of(ffile, 'status') or '(no status:)')
         for fid, ffile in features),
        DONE)
    unfinished = dict(held.blockers)
    blockers: list[Blocker] = []
    for fid, ffile in features:
        if fid in unfinished:
            blockers.append(Blocker(check, f'{fid} is {unfinished[fid]}'))
            continue
        _, defect = _record(cfg, model.unquote(model.field_of(ffile, 'reviewed')))
        if defect is not None:
            blockers.append(Blocker(check, f'{fid} is {DONE}, {defect}'))
    bugs, scanned = _bugs_against(cfg, mid)
    open_bugs = model.holds(cfg, 'bug', bugs, DONE).blockers
    for bid, status in open_bugs:
        blockers.append(Blocker(check, f'{bid} is {status} — a bug whose '
                                       f'fix_milestone is {mid}'))
    census = (f'{len(features)} feature(s), {len(bugs)} bug(s) naming '
              f'fix_milestone {mid} of {scanned} read')
    if not blockers:
        census += f', all {DONE}' + (' with a record' if features else '')
    return _answer(cfg, MILESTONE, mid, subject, blockers, census)


# --- milestone -> tag ---------------------------------------------------------
def _pointers(cfg: model.PmConfig, mid: str,
              mfile: Path) -> list[tuple[str, str]]:
    """(owner, pointer) for every record this milestone points at: the
    features' plus the milestone document's own, never a `review_dir`
    sweep.
    """
    owned = [(fid, model.unquote(model.field_of(ffile, 'reviewed')))
             for fid, ffile in _features(cfg, mfile)]
    owned.append((mid, model.unquote(model.field_of(mfile, 'reviewed'))))
    return owned


def ready_for_tag(cfg: model.PmConfig, mid: str) -> int:
    """Is every finding in every record this milestone points at not `open`?
    An unparseable record is UNVERIFIABLE and blocks; no records blocks.
    """
    mfile = _grain(cfg, TAG, mid, 'milestone', MILESTONE,
                   "about a milestone's review records")
    check = _check_answered_by(TAG)
    blockers: list[Blocker] = []
    records: dict[Path, Record] = {}
    for owner, pointer in _pointers(cfg, mid, mfile):
        if not pointer or pointer == 'null':
            # Whether the review happened is `ready-for milestone`'s question,
            # one rung down.
            continue
        record, defect = _record(cfg, pointer)
        if defect is not None:
            blockers.append(Blocker(check, f'{owner}: {defect}'))
        elif record is not None:
            records.setdefault(record.real, record)

    findings = 0
    for record in records.values():
        rel = cfg.rel(record.path)
        try:
            passes = verdict.parse(record.text)
        except (verdict.NoVerdict, verdict.MalformedVerdict) as err:
            # The parser's own message, flattened to one line.
            blockers.append(Blocker(check, f'{UNVERIFIABLE} {rel}: '
                                           f'{" ".join(str(err).split())}'))
            continue
        opened = [f for p in passes for f in p.findings
                   if f.disposition_kind == verdict.OPEN]
        blocking = [f.id for f in opened
                    if f.severity in verdict.BLOCKING_SEVERITIES]
        carried = [f.id for f in opened
                   if f.severity not in verdict.BLOCKING_SEVERITIES]
        mine = sum(len(p.findings) for p in passes)
        findings += mine
        if blocking:
            blockers.append(Blocker(check,
                                    f'{", ".join(blocking)} open in {rel}'))
        else:
            # Printed on the passing path too, so an unopened record cannot
            # look like a clean one — and the non-blocking ones are NAMED, not
            # swallowed: not holding the tag is not the same as not existing.
            said = f'{RECORD}{rel} — {mine} finding(s), none blocking'
            if carried:
                said += (f'; {len(carried)} open below MAJOR carried forward: '
                         f'{", ".join(carried)}')
            print(said)
    if not records:
        blockers.append(Blocker(
            check,
            f'{mid} points at no review record — the record set was empty, '
            f'which is not a pass; a tag over an unreviewed milestone is the '
            f'failure this verb exists to refuse'))
    census = f'{len(records)} record(s), {findings} finding(s)'
    if not blockers:
        census += ', none blocking'
    return _answer(cfg, TAG, mid, f'{TAG} {mid}', blockers, census)


# --- the verb -----------------------------------------------------------------
PREDICATES = {STORY: ready_for_story, FEATURE: ready_for_feature,
              MILESTONE: ready_for_milestone, TAG: ready_for_tag}


def cmd_ready_for(cfg: model.PmConfig, args: list[str]) -> int:
    """`pm ready-for <kind> <id>` — one kind, one id, no flags. Every refusal
    is exit 2, so 1 keeps meaning "the belt below is not finished".
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
