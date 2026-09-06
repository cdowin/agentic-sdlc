"""ready_for.py — the three belt-entry conditions, each answering with an exit
code.

    ready-for feature   <feature-id>    every story in `done`?
    ready-for milestone <milestone-id>  every feature in `done` with a
                                        non-empty record, and no open bug?
    ready-for tag       <milestone-id>  every finding not `open`?

Exit 0 ready · 1 not ready, naming each blocker · 2 usage or config.
Nothing is written. A feature with no stories is vacuously ready; a
milestone with no features, or no records, is not. UNVERIFIABLE is never a
pass.
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
def _answer(subject: str, blockers: list[str], census: str) -> int:
    """Print the verdict for one question and return its exit code — the one
    place the 0/1 contract is spelled.
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
    """The grain file `gid` names, of the right kind, or exit 2; a story id
    handed to `ready-for feature` would get the wrong question answered.
    """
    path = _grain_file(cfg, gid)
    if path.name != doc:
        raise Usage(f'{gid!r} is a {_grain_kind(gid)}, not a {noun} — '
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


# --- story -> feature ---------------------------------------------------------
def ready_for_feature(cfg: model.PmConfig, fid: str) -> int:
    """Is every story under this feature in the `done` category? Exit 1 names
    each that is not, with the word the file holds; no stories is vacuously
    ready.
    """
    ffile = _grain(cfg, FEATURE, fid, model.FEATURE_DOC, FEATURE,
                   "about a feature's stories")
    walk = model.slot_walk(ffile.parent / model.STORIES_DIR)
    held = model.holds(
        cfg, 'story',
        ((model.unquote(model.field_of(sfile, 'id')) or cfg.rel(sfile),
          model.field_of(sfile, 'status') or '(no status:)')
         for sfile in walk.kept),
        DONE)
    blockers = list(held.names)
    census = walk.census('story/ies')
    if not walk.kept:
        census += (f' — {VACUOUS}: an empty set is satisfied, and refusing it '
                   f'would make this verb unusable on a doc-only feature')
    elif not blockers:
        census += f', all {DONE}'
    return _answer(f'{FEATURE} {fid}', blockers, census)


# --- feature -> milestone -----------------------------------------------------
def _features(cfg: model.PmConfig, mdir: Path) -> list[tuple[str, Path]]:
    """(id, path) per feature under this milestone, in reading order; `bugs/`
    cannot enter.
    """
    return [(model.unquote(model.field_of(ff, 'id')) or cfg.rel(ff), ff)
            for ff in model.feature_files(mdir)]


def _bugs_against(cfg: model.PmConfig, mid: str) -> tuple[list, int]:
    """((id, status) for every bug whose `fix_milestone:` is `mid`), scanned
    across the whole active tree — a bug is filed where it was caught.
    """
    against = []
    scanned = 0
    for mdir in model.milestone_dirs(cfg):
        for bfile in model.bug_files(mdir):
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
    mfile = _grain(cfg, MILESTONE, mid, model.MILESTONE_DOC, MILESTONE,
                   "about a milestone's features")
    features = _features(cfg, mfile.parent)
    subject = f'{MILESTONE} {mid}'
    if not features:
        return _answer(subject,
                       # Worded to share no phrase with the feature belt's
                       # empty-set line; the two rulings are opposite.
                       [f'{mid} has no features — an empty feature set does '
                        f'not satisfy this belt; a mis-typed id looks exactly '
                        f'like this'],
                       '0 feature(s)')
    # Asked of the feature flow, not the story flow.
    held = model.holds(
        cfg, 'feature',
        ((fid, model.field_of(ffile, 'status') or '(no status:)')
         for fid, ffile in features),
        DONE)
    unfinished = dict(held.blockers)
    blockers = []
    for fid, ffile in features:
        if fid in unfinished:
            blockers.append(f'{fid} is {unfinished[fid]}')
            continue
        _, defect = _record(cfg, model.unquote(model.field_of(ffile, 'reviewed')))
        if defect is not None:
            blockers.append(f'{fid} is {DONE}, {defect}')
    bugs, scanned = _bugs_against(cfg, mid)
    open_bugs = model.holds(cfg, 'bug', bugs, DONE).blockers
    for bid, status in open_bugs:
        blockers.append(f'{bid} is {status} — a bug whose fix_milestone is '
                        f'{mid}')
    census = (f'{len(features)} feature(s), {len(bugs)} bug(s) naming '
              f'fix_milestone {mid} of {scanned} read')
    if not blockers:
        census += f', all {DONE}' + (' with a record' if features else '')
    return _answer(subject, blockers, census)


# --- milestone -> tag ---------------------------------------------------------
def _pointers(cfg: model.PmConfig, mid: str,
              mfile: Path) -> list[tuple[str, str]]:
    """(owner, pointer) for every record this milestone points at: the
    features' plus the milestone document's own, never a `review_dir`
    sweep.
    """
    owned = [(fid, model.unquote(model.field_of(ffile, 'reviewed')))
             for fid, ffile in _features(cfg, mfile.parent)]
    owned.append((mid, model.unquote(model.field_of(mfile, 'reviewed'))))
    return owned


def ready_for_tag(cfg: model.PmConfig, mid: str) -> int:
    """Is every finding in every record this milestone points at not `open`?
    An unparseable record is UNVERIFIABLE and blocks; no records blocks.
    """
    mfile = _grain(cfg, TAG, mid, model.MILESTONE_DOC, MILESTONE,
                   "about a milestone's review records")
    blockers: list[str] = []
    records: dict[Path, Record] = {}
    for owner, pointer in _pointers(cfg, mid, mfile):
        if not pointer or pointer == 'null':
            # Whether the review happened is `ready-for milestone`'s question,
            # one rung down.
            continue
        record, defect = _record(cfg, pointer)
        if defect is not None:
            blockers.append(f'{owner}: {defect}')
        elif record is not None:
            records.setdefault(record.real, record)

    findings = 0
    for record in records.values():
        rel = cfg.rel(record.path)
        try:
            passes = verdict.parse(record.text)
        except (verdict.NoVerdict, verdict.MalformedVerdict) as err:
            # The parser's own message, flattened to one line.
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
            # Printed on the passing path too, so an unopened record cannot
            # look like a clean one.
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
