"""ready_for.py — the four belt-entry conditions, each answering with an exit code.

    ready-for story     <story-id>      the story belt's own checks, narrowed
                                        to what the registry declares an entry
                                        condition
    ready-for feature   <feature-id>    every story in `done`?
    ready-for milestone <milestone-id>  every feature in `done` with a
                                        non-empty record, and no open bug?
    ready-for tag       <milestone-id>  every finding not `open`?

Exit 0 ready · 1 not ready, naming each blocker · 2 usage or config.
Nothing is written. A feature with no stories is vacuously ready; a
milestone with no features and no bugs, or no records, is not. UNVERIFIABLE is never a
pass.

**The story rung's condition is DECLARED, never spelled here** — the derivation
is `_entry_condition`, and every check this verb does not ask is NAMED in the
census with why (rule 11).

Every rung emits `rung.enter` — `{rung, grain, ready, blockers}` — to the sink
`[emit]` declares, and nothing at all where a tree declares none. Emission is
never load-bearing: see `_emit_enter`.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo import emit, vehicle
from agentic_sdlc.repo.pm import inventory, ledger, verdict, vocabulary
from agentic_sdlc.repo.pm.cli import Usage, _grain_of, _ok

# The closed set of questions; an unknown kind names all four. Three ARE grain
# kinds, read from their one home; `tag` has no grain behind it.
STORY, FEATURE, MILESTONE = (vocabulary.GRAIN_STORY, vocabulary.GRAIN_FEATURE,
                             vocabulary.GRAIN_MILESTONE)
TAG = 'tag'
KINDS = (STORY, FEATURE, MILESTONE, TAG)

# A rung a BELT exists for and this verb deliberately does not answer, with the
# why (rule 11: an absence gets a NAMED line). `unknown kind 'adopt'` reads as a
# typo and sends the reader hunting a misspelling instead of the ruling — the
# failure `cli.py`'s `RETIRED_COMMANDS` handling exists to prevent.
ADOPT = 'adopt'
NO_ENTRY_EDGE: dict[str, str] = {
    ADOPT: 'every check in the adopt belt is either the work the bump itself '
           'DOES (pin-bumped, installables-current, config-updated — true only '
           'after) or one that runs a command, and `ready-for` runs nothing '
           '(hard rule 2). The derived entry condition is therefore EMPTY, so '
           'this rung could only ever answer NOT READY, on every tree, '
           'forever. It was declined rather than hand-written: see D4 in the '
           "milestone's decisions log. "
           f'`{vehicle.command(ADOPT, vehicle.Slot("<version>"))}` runs the '
           'checks and writes nothing, which is the answer you wanted',
}

# A category, asked through `vocabulary.holds` so this and `check pm` D2 cannot
# disagree.
DONE = vocabulary.DONE_CATEGORY

# Named blockers are capped; the remainder is disclosed, never dropped.
MAX_NAMED = 50

# Both bounds are refusals, not truncations.
MAX_POINTER_LEN = 512
MAX_RECORD_BYTES = 1 << 20

READY, NOT_READY = ledger.READY, ledger.NOT_READY
BLOCKED = '  BLOCKED  '
RECORD = '  RECORD   '
VACUOUS = 'vacuously ready'
UNVERIFIABLE = 'UNVERIFIABLE'


# --- reporting ----------------------------------------------------------------
class Blocker(NamedTuple):
    """One reason a rung is not ready.

    `check` is '' when the blocker is the RUNG's own answer rather than a named
    check's — a milestone with no features has no check to blame, and inventing
    a name would put a word in the registry's mouth.
    """

    check: str
    why: str


def _check_answered_by(rung: str) -> str:
    """The belt check this rung IS, read from the registry's shipped actions;
    '' for a rung no check names.

    DERIVED, so a blocker here carries the name `close feature` will print
    rather than a word chosen in this module.
    """
    from agentic_sdlc.repo.conveyor import steps as step_defs
    named = [name for name, action in step_defs.SHIPPED_ACTION.items()
             if f'ready-for {rung} ' in action]
    return named[0] if len(named) == 1 else ''


def _enter_row(rung: str, grain: str, blockers: list[Blocker]) -> dict:
    """The `rung.enter` payload, with the blockers as the caller's work queue
    (ft-one-event-shape-serves-three-readers). Every field is the invocation or
    a check name — nothing here decides anything.
    """
    return dict(zip(ledger.ENTER_KEYS, (
        ledger.utc_now(), ledger.KIND_ENTER, grain, rung, not blockers,
        [{'check': b.check, 'why': b.why} for b in blockers])))


def _emit_enter(cfg: vocabulary.PmConfig, rung: str, grain: str,
                blockers: list[Blocker]) -> None:
    """Write the entry event, or nothing, and never change the answer.

    A tree with no `[emit]` opted out and is owed no line — which is how this
    verb keeps its "writes nothing" contract. Every failure below is a finding
    on stderr and never the exit code: a code that moved because a SINK was
    unwritable would make this verb unusable as a predicate.

    Building the row is INSIDE the guard, so "every failure below" is true of
    the whole body; the case that holds it is
    `StoryBelt::test_a_broken_emit_is_a_finding_on_stderr_and_never_the_answer`.
    """
    try:
        row = _enter_row(rung, grain, blockers)
        if emit.declared():
            emit.emit(cfg, emit.TAP_ENTER, row)
    except Exception as err:  # noqa: BLE001 — a finding, never the answer
        print(f'{emit.FINDING_PREFIX} WARNING — the {emit.TAP_ENTER} event for '
              f'{rung} {grain} was not recorded ({type(err).__name__}: {err}); '
              f'the answer above is unaffected', file=sys.stderr)


def _answer(cfg: vocabulary.PmConfig, rung: str, grain: str, subject: str,
            blockers: list[Blocker], census: str) -> int:
    """Print the verdict for one question and return its exit code — the one
    place the 0/1 contract is spelled, and the one place `rung.enter` is
    emitted from, so no rung answers without an event or emits one it did not
    print.
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
def _kind_of(grain: inventory.Grain) -> str:
    """The grain's own `kind:` since 0.4.0, with the filename as the fallback
    for a document that declares none — it used to come from the FILENAME,
    which is the path being schema.
    """
    found = grain.field(vocabulary.FIELD_KIND)
    if not found:
        # A nested tree's documents declare no `kind:`; there the slot name IS
        # the kind — the derivation 0.4.0 deletes, surviving here alone.
        found = {vocabulary.MILESTONE_DOC: vocabulary.GRAIN_MILESTONE,
                 vocabulary.FEATURE_DOC: vocabulary.GRAIN_FEATURE}.get(grain.path.name,
                                                             vocabulary.GRAIN_STORY)
    return found


def _grain(cfg: vocabulary.PmConfig, kind: str, gid: str, want: str, noun: str,
           asks: str) -> inventory.Grain:
    """The grain `gid` names, of the right kind, or exit 2; a story id handed
    to `ready-for feature` would get the wrong question answered.

    `_kind_of`'s kind, whose filename fallback reads anything that is not a
    milestone or feature document as a story — which is why the story rung asks
    the grain INDEX instead.
    """
    grain = _grain_of(cfg, gid)
    found = _kind_of(grain)
    if found != want:
        raise Usage(f'{gid!r} is a {found}, not a {noun} — '
                    f'`ready-for {kind}` asks {asks}')
    return grain


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

    RICHER than `pointer_escapes`, deliberately: this belt names WHICH
    shape is wrong so the operator can fix it, where the predicate answers
    yes/no for a caller that only refuses. They must never DISAGREE about the
    verdict, and `tests/test_contracts.py` holds them to that.
    """
    if not pointer or pointer == 'null':
        return 'reviewed: is blank — no review record is named'
    if len(pointer) > MAX_POINTER_LEN:
        return (f'reviewed: is {len(pointer)} characters — a pointer is a '
                f'repo-relative path of at most {MAX_POINTER_LEN}')
    if pointer.strip() != pointer or any(ch.isspace() for ch in pointer):
        return f'reviewed: {pointer!r} carries whitespace — it names one file'
    if not inventory.id_is_literal(pointer):
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


def _record(cfg: vocabulary.PmConfig, pointer: str) -> tuple[Record | None, str | None]:
    """(record, defect) for one `reviewed:` pointer — exactly one is not None.
    The single resolver behind `milestone` and `tag`; empty is a defect."""
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
def _story_subject(cfg: vocabulary.PmConfig, sid: str) -> None:
    """Refuse what cannot be a story id, and an id naming another kind.

    An id that names NOTHING is deliberately NOT refused here: `story-exists`
    is the belt's own check for that, and this rung answering 2 where the belt
    answers 1 would be two rulings about one fact. The shape check comes first
    so a hostile id is refused without a grain being read.
    """
    defect = inventory.id_defect(sid)
    if defect:
        raise Usage(f'no grain resolves from id {sid!r} — {defect}')
    # The INDEX's kind, not the document name's: `_kind_of`'s fallback is right
    # for the rungs that want a milestone or a feature, and would let a bug
    # through here.
    grain = inventory.grain_index(cfg).get(sid)
    if grain is None:
        return
    if grain.kind != STORY:
        raise Usage(f'{sid!r} is a {grain.kind}, not a {STORY} — '
                    f'`ready-for {STORY}` asks what the story belt asks '
                    f'before the work')


class Derived(NamedTuple):
    """What `_entry_condition` composed: the checks to ask, the passed-over
    names in their two buckets, and the whole declared list.

    THREE buckets and not two, because the two reasons a check is passed over
    are different facts, and one label over both states a reason this module
    did not derive.
    """

    asked: list[tuple[str, object]]
    not_declared: list[str]
    """Not in `ENTRY_CONDITIONS`, each with the close action where there is
    one."""
    runs_a_command: list[str]
    """In it, but a command answers them — and this verb runs nothing."""
    names: tuple[str, ...]

    @property
    def over(self) -> list[str]:
        return self.not_declared + self.runs_a_command


def _entry_condition(operation: str) -> Derived:
    """The checks to ask, the ones passed over in their two buckets, and the
    whole declared list — the reason this rung is not a list of ids.

    Three runtime sources, no fourth: `driver.step_names` for the project's own
    `[<op>] steps` (a narrowed list is the list), `driver.registry_for` for the
    check objects, and `steps.ENTRY_CONDITIONS` for which of them the registry
    DECLARES decidable before the work. An entry condition that still runs a
    command is passed over too: `ready-for` boots nothing (hard rule 2), and a
    rung that shelled out would stop being safe to ask dozens of times a day.

    **What the census says about a check it did not ask is what this function
    KNOWS, and no more.** It used to say *"answers after the work"* of
    everything outside `ENTRY_CONDITIONS` — true of `evidence-written`, FALSE
    of `committed`, which reads `git status --porcelain` and answers fine up
    front and is excluded on the ruling written at `ENTRY_CONDITIONS`. Rule 4
    is a gate printing PASS over what it did not measure; a verb printing a
    reason it did not derive is that shape one size down.
    """
    from agentic_sdlc.repo.conveyor import driver
    from agentic_sdlc.repo.conveyor import steps as step_defs
    names = driver.step_names(operation)
    known = driver.registry_for(operation)
    commands = step_defs.commands_for(operation, names, known)
    derived = Derived([], [], [], names)
    for name in names:
        runs = commands.get(name) or step_defs.shown_action(
            step_defs.SHIPPED_ACTION.get(name, ''))
        if name not in step_defs.ENTRY_CONDITIONS:
            derived.not_declared.append(
                name + (f' (by `{runs}`)' if runs else ''))
        elif runs:
            derived.runs_a_command.append(f'{name} (runs `{runs}`)')
        else:
            derived.asked.append((name, known[name]))
    return derived


def ready_for_story(cfg: vocabulary.PmConfig, sid: str) -> int:
    """The inner loop's entry edge: the story belt's own checks that are
    decidable before the work, ASKED rather than re-implemented, so a blocker
    here carries the sentence `close story` will print.
    """
    from agentic_sdlc.repo.conveyor import driver
    _story_subject(cfg, sid)
    derived = _entry_condition(STORY)
    asked, names = derived.asked, derived.names
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
        # Rule 4's floor: nothing was asked, so READY would be a claim about a
        # question nobody put.
        blockers.append(Blocker(
            '', f'nothing was asked — [{STORY}] steps declares {len(names)} '
                f'check(s) and the registry declares none of them decidable '
                f'before the work, so this rung has no entry condition in '
                f'this tree; a READY over nothing asked is not a pass'))
    # Rule 11: one clause per REASON, so the reason is stated once and each
    # name carries only what is true of it.
    if derived.not_declared:
        census += (f'; {len(derived.not_declared)} the registry does not '
                   f'declare an entry condition, asked at the close: '
                   f'{", ".join(derived.not_declared)}')
    if derived.runs_a_command:
        census += (f'; {len(derived.runs_a_command)} declared an entry '
                   f'condition but answered by a command, and this verb runs '
                   f'nothing: {", ".join(derived.runs_a_command)}')
    return _answer(cfg, STORY, sid, f'{STORY} {sid}', blockers, census)


# --- story -> feature ---------------------------------------------------------
def ready_for_feature(cfg: vocabulary.PmConfig, fid: str) -> int:
    """Is every story under this feature in the `done` category? Exit 1 names
    each that is not, with the word the file holds; no stories is vacuous."""
    return _answer(cfg, FEATURE, fid, *_feature_verdict(cfg, fid))


def _feature_verdict(cfg: vocabulary.PmConfig,
                     fid: str) -> tuple[str, list[Blocker], str]:
    """`ready_for_feature`'s (subject, blockers, census), printed nowhere."""
    feature = _grain(cfg, FEATURE, fid, vocabulary.GRAIN_FEATURE, FEATURE,
                     "about a feature's stories")
    # The stories BOUND to this feature, not the ones in a directory beneath
    # it: membership is the child's field.
    kept = inventory.story_grains(cfg, feature.field(vocabulary.FIELD_ID) or fid)
    held = vocabulary.holds(
        cfg, vocabulary.GRAIN_STORY,
        ((story.field(vocabulary.FIELD_ID) or cfg.rel(story.path),
          story.field(vocabulary.FIELD_STATUS) or '(no status:)')
         for story in kept),
        DONE)
    check = _check_answered_by(FEATURE)
    blockers = [Blocker(check, name) for name in held.names]
    skipped = inventory.pool_skipped(cfg, vocabulary.GRAIN_STORY)
    census = (f'{len(kept)} story/ies'
              + (f', {skipped} file(s) skipped (no frontmatter — not a '
                 f'grain)' if skipped else ''))
    if not kept:
        census += (f' — {VACUOUS}: an empty set is satisfied, and refusing it '
                   f'would make this verb unusable on a doc-only feature')
    elif not blockers:
        census += f', all {DONE}'
    return f'{FEATURE} {fid}', blockers, census


# --- feature -> milestone -----------------------------------------------------
def _features(cfg: vocabulary.PmConfig,
              milestone: inventory.Grain) -> list[tuple[str, inventory.Grain]]:
    """(id, grain) per feature BOUND TO this milestone, in its declared order.

    Takes the GRAIN, not a directory: a pooled tree has none, and membership is
    the child's field.
    """
    mid = milestone.field(vocabulary.FIELD_ID)
    return [(ff.field(vocabulary.FIELD_ID) or cfg.rel(ff.path), ff)
            for ff in inventory.feature_grains(cfg, mid)]


def _bugs_against(cfg: vocabulary.PmConfig, mid: str) -> tuple[list, int]:
    """((id, status) for every bug NESTED IN `mid`), and the pool count.

    The bug walk IS the feature walk; it scanned for `fix_milestone:`, a field
    nothing wrote, so this could not fail for four releases (0.6.0/D11). The
    POOL is the second number, not a scan total — it separates
    zero-because-none-nested from zero-because-none-matched.
    """
    against = [(bug.field(vocabulary.FIELD_ID) or cfg.rel(bug.path),
                bug.field(vocabulary.FIELD_STATUS) or '(no status:)')
               for bug in inventory.bug_grains(cfg, mid)]
    return against, len(inventory.unbound(cfg, vocabulary.GRAIN_BUG))


def ready_for_milestone(cfg: vocabulary.PmConfig, mid: str) -> int:
    """Every feature in `done` with a resolving, non-empty record, and no bug
    promised to this milestone outside `done`. Zero features AND zero bugs
    exits 1, deliberately opposite to the empty-story ruling; zero features
    with bugs bound is a bug-only milestone, graded on its bugs alone."""
    return _answer(cfg, MILESTONE, mid, *_milestone_verdict(cfg, mid))


def _milestone_verdict(cfg: vocabulary.PmConfig,
                       mid: str) -> tuple[str, list[Blocker], str]:
    """`ready_for_milestone`'s (subject, blockers, census), printed nowhere."""
    milestone = _grain(cfg, MILESTONE, mid, vocabulary.GRAIN_MILESTONE, MILESTONE,
                       "about a milestone's features")
    features = _features(cfg, milestone)
    subject = f'{MILESTONE} {mid}'
    check = _check_answered_by(MILESTONE)
    bugs, pooled = _bugs_against(cfg, mid)
    if not features and not bugs:
        # Worded to share no phrase with the feature belt's empty-set line;
        # the two rulings are opposite.
        return (subject,
                [Blocker('', f'{mid} has no features — an empty feature set '
                             f'does not satisfy this belt; a mis-typed id '
                             f'looks exactly like this')],
                '0 feature(s)')
    # Asked of the feature flow, not the story flow.
    held = vocabulary.holds(
        cfg, vocabulary.GRAIN_FEATURE,
        ((fid, ff.field(vocabulary.FIELD_STATUS) or '(no status:)')
         for fid, ff in features),
        DONE)
    unfinished = dict(held.blockers)
    blockers: list[Blocker] = []
    for fid, ff in features:
        if fid in unfinished:
            blockers.append(Blocker(check, f'{fid} is {unfinished[fid]}'))
            continue
        _, defect = _record(cfg, ff.field('reviewed'))
        if defect is not None:
            blockers.append(Blocker(check, f'{fid} is {DONE}, {defect}'))
    open_bugs = vocabulary.holds(cfg, vocabulary.GRAIN_BUG, bugs, DONE).blockers
    for bid, status in open_bugs:
        blockers.append(Blocker(check, f'{bid} is {status} — a bug nested in '
                                       f'{mid}'))
    # A patch release: no features, and the bugs bound to it ARE the census.
    shape = '' if features else ' — a bug-only milestone,'
    census = (f'{len(features)} feature(s), {len(bugs)} bug(s){shape} '
              f'nested in {mid}'
              # Rule 11: so "none here" is not read as "none at all".
              + (f', {pooled} bug(s) attached to no milestone' if pooled
                 else ''))
    if not blockers:
        census += f', all {DONE}' + (' with a record' if features else '')
    return subject, blockers, census


# --- milestone -> tag ---------------------------------------------------------
def _pointers(cfg: vocabulary.PmConfig, mid: str,
              milestone: inventory.Grain) -> list[tuple[str, str]]:
    """(owner, pointer) for every record this milestone points at: the
    features' plus the milestone's own, never a `review_dir` sweep."""
    owned = [(fid, ff.field('reviewed'))
             for fid, ff in _features(cfg, milestone)]
    owned.append((mid, milestone.field('reviewed')))
    return owned


def ready_for_tag(cfg: vocabulary.PmConfig, mid: str) -> int:
    """Is every finding in every record this milestone points at not `open`?
    An unparseable record is UNVERIFIABLE and blocks; no records blocks."""
    milestone = _grain(cfg, TAG, mid, vocabulary.GRAIN_MILESTONE, MILESTONE,
                       "about a milestone's review records")
    check = _check_answered_by(TAG)
    blockers: list[Blocker] = []
    records: dict[Path, Record] = {}
    for owner, pointer in _pointers(cfg, mid, milestone):
        if not pointer or pointer == 'null':
            # Whether the review happened is `ready-for milestone`'s question.
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
            # look like a clean one, and the non-blocking findings are NAMED:
            # not holding the tag is not the same as not existing.
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

# The two rungs a pm WRITE can cross, and the verdict each verb prints.
_VERDICTS = {FEATURE: _feature_verdict, MILESTONE: _milestone_verdict}


def blockers(cfg: vocabulary.PmConfig, kind: str, gid: str) -> list[Blocker]:
    """What `pm ready-for <kind> <gid>` names, empty when READY, printed and
    emitted nowhere — for the arrival's `ready:` line, which must agree with
    this edge (S12). Raises `Usage` as the verb does."""
    return _VERDICTS[kind](cfg, gid)[1]


def cmd_ready_for(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """`pm ready-for <kind> <id>` — one kind, one id, no flags. Every refusal
    is exit 2, so 1 keeps meaning "the belt below is not finished"."""
    if not args:
        raise Usage(f'ready-for needs a kind — one of {", ".join(KINDS)}')
    kind, rest = args[0], args[1:]
    if kind in NO_ENTRY_EDGE:
        raise Usage(f'{kind} has no entry condition — {NO_ENTRY_EDGE[kind]}. '
                    f'ready-for asks one of {", ".join(KINDS)}')
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
