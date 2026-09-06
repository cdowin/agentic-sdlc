"""cli.py — the PM-tree status CLI.

A verb validates the target against the grain's declared flow, writes only
the `status:` line (plus `reviewed:` on a feature close), preserves every
other byte, and is idempotent; every question is asked of a status's
category, never of the word, and there is no transition graph — `check pm`
reports the end state. Exit 0 ok · 1 refused, nothing written · 2 usage.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentic_sdlc.core import apply
from agentic_sdlc.repo.pm import ledger, model, report, templates

PROG = 'agentic-sdlc pm'

USAGE = """usage: agentic-sdlc pm <command>

Every question asked of a status is asked of its CATEGORY — todo, in_progress
or done — never of the word. Which words sit in which category is this
project's [pm.states.<kind>] in devkit.toml, written by `pm init` and read
every run; a state the project never declared is refused by name.

  story <status> <story-id>               (any state in [pm.states.story])
  bug <status> <bug-id>                   (any state in [pm.states.bug];
                                           bug-id is <milestone>/bugs/<slug>)
  feature <status> <feature-id>           (any state in [pm.states.feature].
                                           A write prints what it wrote and
                                           nothing else; a parent behind its
                                           children is `check pm`'s WARN)
  feature <done-state> <feature-id> [--review-record <path>]
                                          (a state in the `done` category
                                           closes: stamps `reviewed:` from the
                                           flag. No story file is touched —
                                           the story belt closes each by name)
  milestone <status> <milestone-id>       (any state in [pm.states.milestone])
  retire <milestone-id> [<summary...>] [--dry-run]
                                          (removes the milestone directory and
                                           the version stays on the plan;
                                           reports an undone status or live
                                           children rather than refusing on
                                           their account — refuses only when
                                           the id is missing)
  move <story-id> <feature-id>            (re-parents a story: renames its
                                           file under the target feature and
                                           rewrites id/feature/milestone —
                                           whole, or not at all)
  status [<milestone>]
  list [--status <s>[,<s>…]] [--owner <name>] [--milestone <id>]
       [--category todo|in_progress|done]
                                          (one tab-separated line per story:
                                           id, status, owner, feature)
  list --kind milestone [--status <s>[,<s>…]] [--category <c>]
                                          (one tab-separated line per
                                           milestone: id, status, category,
                                           branch — `-` for none. What a script
                                           asks instead of grepping a status
                                           word out of milestone.md)
  ready-for feature|milestone|tag <id>    (the belt-entry condition below that
                                           rung, as an EXIT CODE: 0 ready,
                                           1 not ready — naming every blocker,
                                           never a tally — 2 usage. feature:
                                           every story in the `done` CATEGORY
                                           ([pm.states.story] done — `obe` too,
                                           never the bare word). milestone:
                                           every feature in `done` with a
                                           non-empty review record. tag: every
                                           finding in the records the milestone
                                           points at at a disposition other
                                           than `open`. Writes nothing)
  get <grain-id> <key>                    (read one frontmatter field)
  set <grain-id> <key> <value>            (write one frontmatter field — not status)
  templates [--force]                     (copy the templates into the project to edit)
  sync [--check]                          (re-render the execution lists)
  vocabulary [--json]                     (this version's declared surface:
                                           each kind's states with their
                                           category, and the rule ids. A tree
                                           declaring no flow is REPORTED, with
                                           the seed `init` would write)
  order [--append <v> | --insert <v> --before <v> | --remove <v>]
                                          (the release plan — `order` in
                                           pm/roadmap/releases.md. Bare, it
                                           prints the plan. Authoring and
                                           SCHEDULING are separate acts: a
                                           milestone declares `version:` without
                                           joining the plan, and this verb puts
                                           it on one. It does NOT interrogate
                                           the tree — a version is a fact about
                                           the INPUT, valid whether or not a
                                           milestone claims it yet; the R rules
                                           in `check pm` report the
                                           contradiction. Refuses only a
                                           duplicate, an empty string and an
                                           insert before an entry that is not
                                           there)
  next                                    (the first entry in `order` that has
                                           not shipped, with the milestone that
                                           claims it. Writes nothing)
  roadmap                                 (the whole plan: every scheduled
                                           release with its milestone and state,
                                           then the backlog. What `pm status`
                                           does for one milestone, for the
                                           sequence — and what replaced the
                                           hand-maintained ROADMAP.md. Writes
                                           nothing)
  validate                                (structural + referential integrity)
  install-skills [--force] [--diff]       (write the shared rule + operations skill)
  init                                    (scaffold a fresh tree + install guidance)
  new milestone <ver> [<name...>]         (scaffold the grain file in its own dir;
                                           no sub-slot dirs, and a shared doc appears
                                           on first WRITE. Idempotent — re-run to fill)
  new feature <milestone> <slug> [<name...>]
  new story <feature-id> <slug> <name...>
                                          (under [pm] story_ordinal_prefix
                                           a slug may lead with `NN-`: the
                                           FILE keeps it, the id never does)
  new bug <milestone> <slug> [--caused-by <feature-id>]
                                          (--caused-by stamps caused_by: — the
                                           feature whose change produced the
                                           bug, any status; it must resolve, and
                                           an unresolvable one writes nothing)
  ledger record --from-transcript <path> --event SubagentStop|Stop
                [--agent-id X] [--agent-type Y] [--session-id Z]
                                          (sum one Claude Code transcript and
                                           append a dispatch (SubagentStop) or
                                           session (Stop) row to the ONE
                                           in_progress milestone's ledger.jsonl
                                           — none or several is a refusal that
                                           names them)
  ledger record --grain <id> [--agent-type T] [--tokens-in N] [--tokens-out N]
                [--tool-calls N] [--duration-s N] [--event E]
                                          (hand entry for a dispatch no hook
                                           saw; a number not given is a key the
                                           row does not carry, never a zero)
  ledger record --gate <name> --verdict PASS|FAIL|HANG|SKIP --duration-ms <n>
                [--census <n>]
                                          (what ONE gate run cost: the make
                                           target's name, how it went, its wall
                                           seconds, and the corpus it walked.
                                           --census is OPTIONAL and an omitted
                                           one is an absent key, never a zero —
                                           a duration without a census is not
                                           comparable across trees. Refuses
                                           rather than filing a row with no
                                           duration)
  ledger show <grain-id> [--json]         (that grain's rows oldest first, with
                                           the seconds since the previous status
                                           row; --json prints the raw lines)
  ledger report [<milestone-id>] [--json] [--from <rev>]
                                          (spend per grain from that milestone's
                                           rows: dispatches, tokens, tool calls,
                                           wall-clock and seconds in each
                                           CATEGORY (todo / in_progress / done),
                                           per story/feature/bug. Defaults to the
                                           one in_progress milestone. Never
                                           exits non-zero on a number.
                                           --from <rev> reads the ledger and the
                                           grain docs out of git at that rev
                                           instead of the tree, for a milestone
                                           already retired — name the rev, it is
                                           never inferred (D6), and the release
                                           tag vX.Y.Z is the usual anchor
                                           because a milestone is still in the
                                           tree at its own release)
  decide <grain-id> <title...>            (append one dated, ordinal-stamped
                                           heading, minting decisions.md if this is
                                           the first; the prose under it is yours.
                                           A title containing ; & | must be QUOTED
                                           all the way through — through `make pm
                                           ARGS=` too, whose shell cuts an unquoted
                                           title in half and runs the remainder:
                                           ARGS='decide <id> "a; b"')"""



# A heading ending in one of these is a shell's cut at an unquoted `;` — see
# cmd_decide.
SHELL_SPLITTERS = (';', '&', '|')


class Refused(Exception):
    """A precondition said no. Exit 1."""


class Usage(Exception):
    """Bad arguments, or an id that resolves to nothing. Exit 2."""


def _ok(msg: str) -> None:
    print(f'[pm] {msg}')


def _check_slug(kind: str, value: str) -> str:
    """A slug becomes a path component and half an id; reject anything else
    before a write can leave the repo root.
    """
    if not value:
        raise Usage(f'{kind} may not be empty')
    if value in ('.', '..') or any(c in value for c in '/\\'):
        raise Refused(f'{kind} {value!r} contains a path separator — a slug is '
                      f'one path component, never a path')
    if '..' in value:
        raise Refused(f'{kind} {value!r} contains "..", which would escape the '
                      f'tree')
    if value.startswith('-') or any(c in value for c in '*?[]!'):
        raise Refused(f'{kind} {value!r} contains a glob or leading dash — ids '
                      f'are literals')
    return value


def _exists(path: Path) -> bool:
    """`Path.exists()` that answers False for a path the filesystem refuses:
    `stat` raises on an over-long component before 3.14 and answers False
    after.
    """
    try:
        return path.exists()
    except OSError:
        return False


def _mint(cfg: model.PmConfig, path: Path, body: str) -> None:
    """Write one new grain file, turning a filesystem refusal into a REFUSED
    rather than a traceback under exit 1.
    """
    try:
        templates.write(path, body)
    except OSError as err:
        raise Refused(f'{cfg.rel(path)} could not be written ({err}) — nothing '
                      f'was written; shorten the slug, or make '
                      f'{cfg.rel(path.parent)}/ writable') from err


def _slugify(text: str) -> str:
    """ASCII-only, because the result becomes a permanent directory name and
    `str.isalnum()` is Unicode-aware.
    """
    keep = 'abcdefghijklmnopqrstuvwxyz0123456789'
    out = ''.join(c if c in keep else '-' for c in text.lower())
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')


def _was(path: Path) -> str:
    """The status a grain currently carries, for the message only; the verb
    never gates on it, so a hand-edited word is repaired rather than
    refused. `(none)` when absent.
    """
    return model.field_of(path, 'status') or '(none)'


def _set_status(cfg: model.PmConfig, path: Path, value: str, note: str = '') -> None:
    """Write the `status:` line and validate nothing; every caller has already
    asked `_movable`.
    """
    if not model.set_field(path, 'status', value):
        raise Usage(f'could not rewrite status in {cfg.rel(path)} '
                    f'(malformed frontmatter, or the file is not writable)'
                    + (f'. {note}' if note else ''))


# --- the ledger ---------------------------------------------------------------
# Every changing verb appends one ledger row: after the write, never before; a
# no-op still appends; the row never changes the verb's output or exit code
# (rule 6).
def _ledger_id(path: Path, fallback: str,
               src: report.Source | None = None) -> str:
    """The id a row names: the grain's own `id:`, or the caller's when the key
    is absent. `src` may be `report.GitSource` for `ledger report --from`.
    """
    reader = report.DiskSource() if src is None else src
    return model.unquote(reader.field_of(path, 'id')) or fallback


def _stamp(cfg: model.PmConfig, path: Path, row: dict) -> None:
    """Append one row to the ledger of the milestone that owns `path`. Never
    raises and never changes an exit code; a missing row is said on stderr.
    """
    mdir = model.milestone_dir_of(cfg, path)
    if mdir is None:
        print(f'[pm] WARNING — no milestone directory owns {cfg.rel(path)}, so '
              f'no {ledger.LEDGER_FILE_NAME} row was appended for it; the '
              f'write itself landed', file=sys.stderr)
        return
    try:
        ledger.append_row(mdir, row)
    except OSError as err:
        print(f'[pm] WARNING — {cfg.rel(ledger.ledger_path(mdir))} could not be '
              f'appended to ({err}); the write itself landed, but this '
              f'transition is NOT in the ledger', file=sys.stderr)


def _stamp_status(cfg: model.PmConfig, path: Path, frm: str, to: str,
                  gid: str) -> None:
    """One status row for a flip that has already landed on disk."""
    _stamp(cfg, path, ledger.status_row(_ledger_id(path, gid), frm, to))


def _movable(cfg: model.PmConfig, kind: str, to: str) -> None:
    """Exit 2 unless `to` is a state this project declared for `kind` — asked
    before the grain is resolved.
    """
    defect = model.move_defect(cfg, kind, to)
    if defect:
        raise Usage(defect)


# --- story --------------------------------------------------------------------
def cmd_story(cfg: model.PmConfig, args: list[str]) -> int:
    if len(args) != 2:
        raise Usage(USAGE)
    to, sid = args
    _movable(cfg, 'story', to)
    sf = model.story_file(cfg, sid)
    if sf is None:
        raise Usage(f'no story resolves from id {sid!r} '
                    f'(expected <milestone>/<feature-slug>/<story-slug>)')
    cur = _was(sf)
    if cur == to:
        _ok(f'story {sid} already {to} (no-op)')
        _stamp_status(cfg, sf, cur, to, sid)
        return 0
    _set_status(cfg, sf, to)
    _ok(f'story {sid}: {cur} -> {to}')
    _stamp_status(cfg, sf, cur, to, sid)
    return 0


# --- bug ------------------------------------------------------------------
def cmd_bug(cfg: model.PmConfig, args: list[str]) -> int:
    """Move a bug's `status:` through code, `cmd_story`'s shape. `bid` must
    contain `/bugs/` before `_grain_file` runs, or a feature file could be
    written under the bug flow.
    """
    if len(args) != 2:
        raise Usage(USAGE)
    to, bid = args
    _movable(cfg, 'bug', to)
    if f'/{model.BUGS_DIR}/' not in bid:
        raise Usage(f'no bug resolves from id {bid!r} '
                    f'(expected <milestone>/{model.BUGS_DIR}/<slug>)')
    bf = _grain_file(cfg, bid)
    cur = _was(bf)
    if cur == to:
        _ok(f'bug {bid} already {to} (no-op)')
        _stamp_status(cfg, bf, cur, to, bid)
        return 0
    _set_status(cfg, bf, to)
    _ok(f'bug {bid}: {cur} -> {to}')
    _stamp_status(cfg, bf, cur, to, bid)
    return 0


# --- feature ------------------------------------------------------------------
def _feature_or_usage(cfg: model.PmConfig, fid: str) -> tuple[Path, str]:
    ff = model.feature_file(cfg, fid)
    if ff is None:
        raise Usage(f'no feature resolves from id {fid!r}')
    return ff, _was(ff)


def cmd_feature_simple(cfg: model.PmConfig, to: str, args: list[str]) -> int:
    """Any feature move that is not a close: one write, and it says so. A
    feature ahead of or behind its stories is `check pm`'s WARN, not this
    verb's.
    """
    if len(args) != 1:
        raise Usage(USAGE)
    fid = args[0]
    ff, cur = _feature_or_usage(cfg, fid)
    if cur == to:
        _ok(f'feature {fid} already {to} (no-op)')
        _stamp_status(cfg, ff, cur, to, fid)
        return 0
    _set_status(cfg, ff, to)
    _ok(f'feature {fid}: {cur} -> {to}')
    _stamp_status(cfg, ff, cur, to, fid)
    return 0


def _resolve_record(cfg: model.PmConfig, rec: str) -> Path:
    return Path(rec) if rec.startswith('/') else cfg.root / rec


def _take_flags(args: list[str], flags: tuple[str, ...],
                noun: str = 'a value') -> tuple[list[tuple[str, str]],
                                                list[str]]:
    """Parse `--flag value` / `--flag=value` out of `args`; returns (pairs
    seen, the rest in order). A flag with nothing after it refuses; an
    empty `=` value is the caller's to judge.
    """
    pairs: list[tuple[str, str]] = []
    rest: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        for flag in flags:
            if a == flag:
                if i + 1 >= len(args):
                    raise Usage(f'{flag} needs {noun}')
                pairs.append((flag, args[i + 1]))
                i += 2
                break
            if a.startswith(f'{flag}='):
                pairs.append((flag, a.split('=', 1)[1]))
                i += 1
                break
        else:
            rest.append(a)
            i += 1
    return pairs, rest


def cmd_feature_done(cfg: model.PmConfig, to: str, args: list[str]) -> int:
    """Close a feature: a move into the `done` category, by whichever word,
    plus `reviewed:` from `--review-record`. Touches no story; an
    already-closed feature still runs the record stamp.
    """
    pairs, rest = _take_flags(args, ('--review-record',), noun='a path')
    rec = ''
    for _, value in pairs:
        # Both spellings refuse an empty path the same way (see _take_flags).
        if not value:
            raise Usage('--review-record needs a path')
        rec = value
    fid = ''
    for a in rest:
        if a.startswith('-'):
            raise Usage(f'unknown flag {a!r}')
        elif fid:
            raise Usage(f'unexpected arg {a!r}')
        else:
            fid = a
    if not fid:
        raise Usage(USAGE)
    ff, cur = _feature_or_usage(cfg, fid)

    if rec:
        # The one thing checked about a record: the path resolves. Length is
        # not this tool's question.
        target = _resolve_record(cfg, rec)
        if not model.record_resolves(target):
            raise Refused(
                f'feature {fid} -> {to}: review record {rec!r} names no file '
                f'({cfg.rel(target)}). Nothing was written — stamping a pointer '
                f'to nothing is the drift D1 reports.')
        if not model.set_field(ff, 'reviewed', rec):
            raise Usage(f'could not stamp reviewed: in {cfg.rel(ff)}')
        _ok(f'feature {fid}: reviewed -> {rec}')
    record = model.review_record_for(cfg, fid)

    if cur == to:
        _ok(f'feature {fid} already {to} (no-op)')
    else:
        _set_status(cfg, ff, to)
        _ok(f'feature {fid}: {cur} -> {to}'
            + (f' (review record: {record})' if record
               else ' (no review record)'))
    _stamp_status(cfg, ff, cur, to, fid)
    return 0


def cmd_feature(cfg: model.PmConfig, args: list[str]) -> int:
    if not args:
        raise Usage(USAGE)
    sub, rest = args[0], args[1:]
    # The target is validated before any dispatch; the current state is never
    # gated on, so repair from any state stays.
    _movable(cfg, 'feature', sub)
    # A move into the `done` category is the close, by whichever word.
    if model.category_of(cfg, 'feature', sub) == model.DONE_CATEGORY:
        return cmd_feature_done(cfg, sub, rest)
    return cmd_feature_simple(cfg, sub, rest)


# --- milestone ----------------------------------------------------------------
def cmd_milestone(cfg: model.PmConfig, args: list[str]) -> int:
    if len(args) != 2:
        raise Usage(USAGE)
    to, mid = args
    _movable(cfg, 'milestone', to)
    mf = model.milestone_file(cfg, mid)
    if mf is None:
        raise Usage(f'no milestone resolves from id {mid!r}')
    cur = _was(mf)
    if cur == to:
        _ok(f'milestone {mid} already {to} (no-op)')
        _stamp_status(cfg, mf, cur, to, mid)
        return 0
    _set_status(cfg, mf, to)
    _ok(f'milestone {mid}: {cur} -> {to}')
    _stamp_status(cfg, mf, cur, to, mid)
    # No advisory about the features left behind: D3 asks that of the tree.
    return 0


def _known_milestone_ids(cfg: model.PmConfig) -> list[str]:
    return sorted(mid or mdir.name
                  for mdir, mid in model.known_milestones(cfg))


def cmd_retire(cfg: model.PmConfig, args: list[str]) -> int:
    """Retire a finished milestone: remove its directory.

    **`ROADMAP.md` retired in 0.3.0 and this verb no longer appends to it.** It
    was two things wearing one name — a hand-maintained index of milestones
    still in the tree, which is the second scoreboard the tool forbids one grain
    down, and the only surviving record of milestones this verb deleted.
    `pm roadmap` derives the first. The second needs no file: `order` keeps the
    version, and R1 reports it UNVERIFIABLE once the directory is gone, so the
    row survives its milestone without anyone maintaining it.

    Refuses only on an unresolvable id; an unfinished milestone is reported, not
    refused. `--dry-run` decides everything and writes nothing.
    """
    dry_run = False
    mid = ''
    summary_words: list[str] = []
    for a in args:
        if a == '--dry-run':
            dry_run = True
        elif not mid:
            mid = a
        else:
            summary_words.append(a)
    if not mid:
        raise Usage(USAGE)
    mdir = model.milestone_dir(cfg, mid)
    if mdir is None:
        known = _known_milestone_ids(cfg)
        raise Usage(f'{mid!r} is not a milestone in {cfg.roadmap_dir} '
                    f'({" ".join(known) if known else "none scaffolded"})')
    mfile = mdir / model.MILESTONE_DOC
    notices: list[str] = []
    if not mfile.is_file():
        notices.append(f'{cfg.rel(mfile)} is missing')
        status, canonical_id, name = '', mid, ''
    else:
        status = model.field_of(mfile, 'status')
        canonical_id = model.unquote(model.field_of(mfile, 'id')) or mid
        name = model.field_of(mfile, 'name')
        if not model.holds(cfg, 'milestone', [(mid, status)],
                           model.DONE_CATEGORY):
            notices.append(f'milestone {mid} is {status or "(no status)"}, '
                           f'not done')
    open_features = sorted(
        name for name, _ in model.holds(
            cfg, 'feature',
            ((ff.parent.name, model.field_of(ff, 'status'))
             for ff in model.feature_files(mdir)),
            model.DONE_CATEGORY).blockers)
    if open_features:
        notices.append(f'{len(open_features)} feature(s) not done: '
                       f'{" ".join(open_features)}')
    # "Still open" is "not in `done`": a bug at `fixed` is work that remains.
    open_bugs = sorted(
        name for name, _ in model.holds(
            cfg, 'bug',
            ((bf.stem, model.field_of(bf, 'status'))
             for bf in model.bug_files(mdir)),
            model.DONE_CATEGORY).blockers)
    if open_bugs:
        notices.append(f'{len(open_bugs)} bug(s) still open: '
                       f'{" ".join(open_bugs)}')

    summary = ' '.join(summary_words)
    ended = f'{status or "(no status)"}' + (f' — {summary}' if summary else '')
    version = model.unquote(model.field_of(mfile, 'version')) \
        if mfile.is_file() else ''
    # What outlives the directory. `order` keeps the version and R1 reports it
    # UNVERIFIABLE from here, so the row survives its milestone with nobody
    # maintaining it — which is the half of ROADMAP.md that was real.
    kept = (f'{cfg.rel(model.releases_file(cfg))} `order` keeps {version}, and '
            f'R1 reports it UNVERIFIABLE from here'
            if version and version in model.declared_order(cfg)
            else f'{canonical_id} ({ended}) is on no plan, so nothing outlives '
                 f'this directory — `agentic-sdlc pm order --append <version>` '
                 f'before retiring keeps a row')

    if dry_run:
        _ok(f'[dry-run] would remove {cfg.rel(mdir)}')
        _ok(f'[dry-run] {kept}')
        for n in notices:
            _ok(f'  noticed: {n}')
        return 0

    plan = apply.Plan()
    plan.delete_tree(mdir, label=cfg.rel(mdir))
    blocked = plan.decide()
    if blocked:
        raise Refused('; '.join(b.describe() for b in blocked)
                      + ' — nothing was retired')
    applied = plan.apply(decide=False)
    if applied.failed is not None:
        raise Refused(
            f'{applied.failed.label} could not be written ({applied.error}) — '
            + ('nothing was written' if not applied.landed else
               'ALREADY LANDED: ' + ', '.join(s.label for s in applied.landed))
            + '. Fix the obstruction and re-run.')
    _ok(f'milestone {mid}: retired — {cfg.rel(mdir)} removed; {kept}')
    for n in notices:
        _ok(f'  noticed: {n}')
    return 0


# --- move -----------------------------------------------------------------
def _known_feature_ids(cfg: model.PmConfig) -> list[str]:
    out = []
    for mdir in model.milestone_dirs(cfg):
        mid = model.unquote(model.field_of(mdir / model.MILESTONE_DOC, 'id')) \
            or mdir.name
        out.extend(f'{mid}/{ff.parent.name}' for ff in model.feature_files(mdir))
    return sorted(out)


def cmd_move(cfg: model.PmConfig, args: list[str]) -> int:
    """Re-parent a story to a different feature, whole or not at all: every
    obstruction is decided before a byte moves, the frontmatter is
    rewritten at the old path, and the rename is last, so an OS failure
    between the two writes is reported by name.
    """
    if len(args) != 2:
        raise Usage(USAGE)
    sid, target_fid = args
    sf = model.story_file(cfg, sid)
    if sf is None:
        raise Usage(f'no story resolves from id {sid!r} '
                    f'(expected <milestone>/<feature-slug>/<story-slug>)')
    target_ff = model.feature_file(cfg, target_fid)
    if target_ff is None:
        known = _known_feature_ids(cfg)
        raise Usage(f'no feature resolves from id {target_fid!r} '
                    f'({" ".join(known) if known else "none scaffolded"})')
    target_mid = model.unquote(model.field_of(target_ff, 'milestone')) \
        or target_fid.partition('/')[0]
    target_fslug = target_ff.parent.name
    canonical_fid = f'{target_mid}/{target_fslug}'
    if sf.parent.parent == target_ff.parent:
        _ok(f'story {sid} already under feature {canonical_fid} (no-op)')
        return 0

    dest = target_ff.parent / model.STORIES_DIR / sf.name
    # `stories/` is minted on first write and `Plan.move` does not create a
    # missing parent, so that is its own decided step.
    plan = apply.Plan()
    plan.make_dir(dest.parent, label=f'{cfg.rel(dest.parent)}/')
    plan.move(sf, dest, label=f'{cfg.rel(sf)} -> {cfg.rel(dest)}')
    blocked = plan.decide()
    if blocked:
        raise Refused('; '.join(b.describe() for b in blocked)
                      + ' — nothing was moved')

    orig_id = model.field_of(sf, 'id')
    story_slug = orig_id.rpartition('/')[2] or sf.stem
    updates = {'id': f'{canonical_fid}/{story_slug}', 'feature': canonical_fid,
               'milestone': f'"{target_mid}"'}
    if not model.set_fields(sf, updates):
        raise Usage(f'could not rewrite id/feature/milestone in {cfg.rel(sf)} '
                    f'(malformed frontmatter, or the file is not writable) — '
                    f'nothing was moved')

    applied = plan.apply(decide=False)
    if applied.failed is not None:
        raise Refused(
            f'{applied.failed.label} could not be written ({applied.error}) — '
            f'the frontmatter at {cfg.rel(sf)} was ALREADY rewritten to '
            f'{canonical_fid}; move the file to {cfg.rel(dest)} by hand, or '
            f'clear the obstruction and re-run (the rewrite is idempotent).')
    _ok(f'story {sid}: moved to {canonical_fid} '
        f'({cfg.rel(sf)} -> {cfg.rel(dest)})')
    return 0


# --- status -------------------------------------------------------------------
def cmd_status(cfg: model.PmConfig, args: list[str]) -> int:
    only = args[0] if args else ''
    # Rule 4: a scan that saw nothing says so instead of an empty print at exit
    # 0.
    known = model.known_milestones(cfg)
    if not known:
        raise Usage(f'{cfg.roadmap_dir} holds no milestone at all — nothing to '
                    f'report, so this is a scope problem (wrong [pm] '
                    f'roadmap_dir, or an empty tree?), not a status')
    if only and only not in {mid for _, mid in known}:
        ids = sorted(mid for _, mid in known if mid)
        raise Usage(f'{only!r} is not a milestone in {cfg.roadmap_dir} '
                    f'({" ".join(ids)})')
    # As wide as the longest declared feature word; an undeclared word still
    # prints whole.
    width = max(len(word) for word in model.flow_of(cfg, 'feature').order)
    for mdir, mid in known:
        mfile = mdir / model.MILESTONE_DOC
        if only and only != mid:
            continue
        print(f'milestone {mid:<10} [{model.field_of(mfile, "status")}]')
        rows = []
        for ffile in model.feature_files(mdir):
            view = model.read_feature(cfg, ffile)
            # The markers reuse the gate's predicates, so report and gate
            # cannot describe a tree differently.
            dangling = model.drift_dangling_record(cfg, view.fid)
            stalled = model.drift_stalled(cfg, view)
            drift = (f'  <DRIFT: {dangling}>' if dangling
                     else f'  <WARN: {stalled}>' if stalled else '')
            # `model.phase_key` is the one spelling of the board's reading
            # order.
            rows.append((model.phase_key(view.phase), view.phase, view,
                         f'  feature {view.fid.partition("/")[2]:<40} '
                         f'[{view.status:<{width}}] stories {view.done_n}/{view.total} done{drift}'))
        if not rows:
            continue
        buckets: list[str] = []
        for _, phase, _, _ in sorted(rows, key=lambda r: r[0]):
            if phase not in buckets:
                buckets.append(phase)
        # A milestone that declares no phases prints as it always did: the lone
        # bucket hides its header.
        for phase in buckets:
            members = [r for r in rows if r[1] == phase]
            finished = model.holds(cfg, 'feature',
                                   ((r[2].fid, r[2].status) for r in members),
                                   model.DONE_CATEGORY)
            n_done = finished.counted - len(finished.blockers)
            if phase or buckets != ['']:
                print(f'  -- {model.phase_label(phase)} '
                      f'({n_done}/{len(members)} done)')
            for r in members:
                print(r[3])
    return 0


def cmd_list(cfg: model.PmConfig, args: list[str]) -> int:
    """One tab-separated line per story, filtered — a view over facts, no
    ranking. Rows go to stdout and the census to stderr, so matching
    nothing and scanning nothing stay distinguishable.
    """
    pairs, rest = _take_flags(args, ('--status', '--owner', '--milestone',
                                     '--kind', '--category'))
    if rest:
        raise Usage(USAGE if not rest[0].startswith('-')
                    else f'unknown flag {rest[0]!r}')
    statuses: set[str] = set()
    owner = ''
    milestone = ''
    kind = 'story'
    category = ''
    for flag, value in pairs:
        if flag == '--status':
            statuses |= {v for v in value.split(',') if v}
        elif flag == '--owner':
            owner = value
        elif flag == '--kind':
            kind = value
        elif flag == '--category':
            category = value
        else:
            milestone = value
    if kind not in LIST_KINDS:
        raise Usage(f'--kind names {kind!r}; this verb lists '
                    f'{" or ".join(LIST_KINDS)}')
    if category and category not in model.CATEGORIES:
        raise Usage(f'--category names {category!r} — the set is closed and '
                    f'is exactly {" ".join(model.CATEGORIES)}')
    for status in sorted(statuses):
        _movable(cfg, kind, status)
    if kind == 'milestone':
        if owner or milestone:
            raise Usage('--owner and --milestone filter stories; '
                        '--kind milestone takes --status and --category')
        return _list_milestones(cfg, statuses, category)

    # Enumerated once, to refuse a typo'd `--milestone` as well as to filter.
    known = model.known_milestones(cfg)
    if milestone and milestone not in {mid for _, mid in known}:
        ids = sorted(mid for _, mid in known if mid)
        raise Usage(f'--milestone names {milestone!r}, which is not a milestone '
                    + (f'in {cfg.roadmap_dir} ({" ".join(ids)})' if ids else
                       f'— {cfg.roadmap_dir} holds no milestone at all, so this '
                       f'is a scope problem, not a typo'))

    shown = 0
    scanned = 0
    for mdir, mid in known:
        if milestone and milestone != mid:
            continue
        for ffile in model.feature_files(mdir):
            view = model.read_feature(cfg, ffile)
            for sfile in view.stories:
                scanned += 1
                status = model.field_of(sfile, 'status')
                who = model.unquote(model.field_of(sfile, 'owner'))
                if statuses and status not in statuses:
                    continue
                if category and model.category_of(cfg, 'story',
                                                  status) != category:
                    continue
                if owner and who != owner:
                    continue
                shown += 1
                print(f'{model.unquote(model.field_of(sfile, "id"))}\t{status}'
                      f'\t{who or "-"}\t{view.fid}')
    print(f'[pm] {shown} of {scanned} story/ies', file=sys.stderr)
    return 0


# `milestone` is here so a script can ask the CLI instead of grepping a status
# word.
LIST_KINDS = ('story', 'milestone')


def _list_milestones(cfg: model.PmConfig, statuses: set[str],
                     category: str) -> int:
    """One tab-separated `<id> <status> <category> <branch>` per milestone,
    `-` for an absent branch or undeclared category, so a shell `read` gets
    a fixed column count.
    """
    known = model.known_milestones(cfg)
    if not known:
        raise Usage(f'{cfg.roadmap_dir} holds no milestone at all — nothing to '
                    f'list, so this is a scope problem (wrong [pm] '
                    f'roadmap_dir, or an empty tree?), not an empty set')
    shown = 0
    for mdir, mid in known:
        mfile = mdir / model.MILESTONE_DOC
        status = model.field_of(mfile, 'status')
        cat = model.category_of(cfg, 'milestone', status)
        if statuses and status not in statuses:
            continue
        if category and cat != category:
            continue
        shown += 1
        branch = model.unquote(model.field_of(mfile, 'branch'))
        print(f'{mid or mdir.name}\t{status or "-"}\t{cat or "-"}'
              f'\t{branch or "-"}')
    print(f'[pm] {shown} of {len(known)} milestone(s)', file=sys.stderr)
    return 0


def _grain_file(cfg: model.PmConfig, gid: str) -> Path:
    """Resolve any grain id — milestone, feature, story or bug — to its file."""
    if f'/{model.BUGS_DIR}/' in gid:
        mid, _, rest = gid.partition(f'/{model.BUGS_DIR}/')
        # The resolution twin of _check_slug: a `..` or empty segment would
        # hand the write to a sibling grain.
        parts = rest.replace('\\', '/').split('/')
        if not rest or any(p in ('', '.', '..') for p in parts):
            raise Usage(f'no bug resolves from id {gid!r} '
                        f'(a bug slug holds no dot or empty segments)')
        mdir = model.milestone_dir(cfg, mid)
        bf = (mdir / model.BUGS_DIR / f'{rest}.md') if mdir else None
        if bf and bf.is_file():
            return bf
        raise Usage(f'no bug resolves from id {gid!r}')
    depth = gid.count('/')
    found = (model.milestone_file(cfg, gid) if depth == 0 else
             model.feature_file(cfg, gid) if depth == 1 else
             model.story_file(cfg, gid))
    if found is None:
        raise Usage(f'no grain resolves from id {gid!r}')
    return found


def cmd_get(cfg: model.PmConfig, args: list[str]) -> int:
    if len(args) != 2:
        raise Usage(USAGE)
    gid, key = args
    print(model.field_of(_grain_file(cfg, gid), key))
    return 0


def cmd_set(cfg: model.PmConfig, args: list[str]) -> int:
    """Set one frontmatter field through a tool rather than a regex. `status`
    is refused by name: a status is a move, and only the status verbs ask
    `move_defect` and stamp the ledger.
    """
    if len(args) != 3:
        raise Usage(USAGE)
    gid, key, value = args
    if not key or not key.replace('_', '').isalnum():
        raise Usage(f'{key!r} is not a frontmatter key')
    if key == 'status':
        kind = _grain_kind(gid)
        raise Usage(f'status is a move, not a field: run `{PROG} {kind} '
                    f'{value} {gid}` — the {kind} verb checks {value!r} '
                    f'against [pm.states.{kind}] and stamps the ledger; '
                    f'`set` would do neither')
    if '\n' in value or '\r' in value:
        raise Refused('a frontmatter scalar is one line')
    path = _grain_file(cfg, gid)
    before = model.field_of(path, key)
    if not model.set_field(path, key, value):
        raise Usage(f'could not write {key}: in {cfg.rel(path)} '
                    f'(malformed frontmatter, or the file is not writable)')
    _ok(f'{gid}: {key} {before!r} -> {value!r}')
    return 0


def cmd_sync(cfg: model.PmConfig, args: list[str]) -> int:
    """Re-render every execution list from the tree; `--check` reports without
    writing (V6's predicate).
    """
    check = '--check' in args
    for a in args:
        if a != '--check':
            raise Usage(f'unknown flag {a!r}')
    from agentic_sdlc.repo.pm import execlist
    # Zero grains refuses in both modes: a gate that scanned nothing must not
    # pass.
    if not execlist.targets(cfg):
        raise Usage(f'no grains found under {cfg.roadmap_dir}/ '
                    f'(wrong [pm] roadmap_dir, or an empty tree?)')
    try:
        results = execlist.sync(cfg, write=not check, existing_only=check)
    except execlist.Refusal as err:
        raise Refused(str(err)) from err
    changed = [p for p, c in results if c]
    for path in changed:
        _ok(f'{"stale" if check else "updated"} {cfg.rel(path)}')
    if not changed:
        _ok(f'all {len(results)} execution list(s) current')
        return 0
    if check:
        print(f'[pm] {len(changed)} stale execution list(s) — run `pm sync`',
              file=sys.stderr)
        return 1
    _ok(f'{len(changed)} of {len(results)} updated')
    return 0


def cmd_vocabulary(cfg: model.PmConfig, args: list[str]) -> int:
    """Print this version's declared surface — each kind's states with their
    category, and the rule ids `[pm] checks` may name — for the pin bump.
    Reads `cfg.flows` directly so an undeclared tree is reported, with the
    bytes `init` would write, rather than refused.
    """
    as_json = '--json' in args
    for a in args:
        if a != '--json':
            raise Usage(f'unknown flag {a!r}')
    # The flat sets stay (rule 6): category-major, then the project's order;
    # empty for a tree that declared nothing.
    grains = {
        'milestone': cfg.milestone_states,
        'feature': cfg.feature_states,
        'story': cfg.story_states,
        'bug': cfg.bug_states,
    }
    if as_json:
        print(json.dumps({
            'categories': list(model.CATEGORIES),
            'flow_kinds': list(model.FLOW_KINDS),
            # The absence is a value, not a missing key, so two pin versions
            # diff cleanly.
            'flow_declared': bool(cfg.flows),
            'grains': {
                g: {
                    'states': list(states),
                    'flow': (None if g not in cfg.flows else {
                        'categories': {
                            cat: list(cfg.flows[g].by_category.get(cat, ()))
                            for cat in model.CATEGORIES},
                        'order': list(cfg.flows[g].order),
                    }),
                }
                for g, states in grains.items()},
            # The seed travels in every payload: what a declaration diffs
            # against, or what `init` would write.
            'seed': model.render_seed(),
            'notes': {
                'states': 'the flat per-kind `states` list is the declared '
                          'flow\'s order — category-major, then the project\'s '
                          'own list order — and is empty for a tree that '
                          'declared nothing; `flow` is what the project '
                          'declared in [pm.states.<kind>], and every question '
                          'the engine asks is asked of a category',
            },
            'checks': list(model.KNOWN_CHECKS),
        }, indent=2))
        return 0
    width = max(len(g) for g in grains)
    for g, states in grains.items():
        print(f'{g:<{width}}  {" ".join(states) if states else "(undeclared)"}')
    print()
    print('Those are the declared states in their reading order — the words')
    print('`check pm` D4 holds a grain to. Every question the engine asks is')
    print('asked of a CATEGORY, never of a word. Below is the FLOW this project')
    print('declared — the category every state maps into. The category set is')
    print(f'closed and is exactly {" ".join(model.CATEGORIES)}.')
    print()
    if not cfg.flows:
        print('This tree declares NO flow: [pm.states.*] is not in')
        print('devkit.toml, and there is no default behind it — the states are')
        print('how THIS project works (hard rule 5). Every verb that creates,')
        print('moves or locates work refuses by name until it is there.')
        print('`agentic-sdlc pm init` writes exactly this, appending to a')
        print('devkit.toml it did not create:')
        print()
        # Indented by two so it is not mistaken for the tree's own config;
        # `render_seed()` is the only source.
        for line in model.render_seed().splitlines():
            print(f'  {line}' if line else '')
        print()
    else:
        cat_width = max(len(c) for c in model.CATEGORIES)
        for kind in model.FLOW_KINDS:
            # Indexed, never `.get`: `_load_flows` refuses a partial
            # declaration, so it is all four kinds or none.
            flow = cfg.flows[kind]
            print(f'[pm.states.{kind}]')
            for category in model.CATEGORIES:
                states = flow.by_category.get(category, ())
                print(f'  {category:<{cat_width}}  {" ".join(states)}')
            print()
    print(f'rules  {" ".join(model.KNOWN_CHECKS)}')
    return 0


def cmd_validate(cfg: model.PmConfig, args: list[str]) -> int:
    """Structural + referential integrity. The same predicates `check pm` runs."""
    if args:
        raise Usage(USAGE)
    # Same placement as the gate's: the two readers a stale rule id would
    # silently narrow.
    stale = model.config_complaints(cfg)
    if stale:
        raise Usage('\n         '.join(stale))
    from agentic_sdlc.repo.pm import validate as _validate
    findings, census = _validate.run(cfg, set(cfg.checks) & set(model.VALIDATE_CHECKS))
    for msg in findings:
        print(f'  INVALID  {msg}')
    if not census['grains']:
        # Rule 4 again: a scan that saw nothing must say so, not print VALID.
        print(f'[pm] ERROR — no grains found under {cfg.roadmap_dir}/ '
              f'(wrong [pm] roadmap_dir, or an empty tree?)', file=sys.stderr)
        return 2
    summary = (f'{census["grains"]} grain(s), {census["refs"]} ref(s)')
    if census['unverifiable']:
        summary += (f' ({census["unverifiable"]} UNVERIFIABLE — the ref names a '
                    f'milestone no longer in the tree; git history is the archive)')
    print()
    if findings:
        print(f'[pm] INVALID — {len(findings)} problem(s) across {summary}')
        return 1
    print(f'[pm] VALID — {summary}')
    return 0


# --- new ----------------------------------------------------------------------
# `caused_by:` names the feature whose change produced the bug; `caught_in:`
# names the milestone that found it.
CAUSED_BY = 'caused_by'
CAUSED_BY_FLAG = '--caused-by'


def _caused_by(cfg: model.PmConfig, pairs: list[tuple[str, str]]) -> str:
    """The `--caused-by` value, proven to name a feature that exists, or ''.
    Resolution is the whole gate, through the resolver the verbs use; any
    status resolves, since escape is the report's question. An OSError is
    False, never a traceback.
    """
    value = ''
    for _, raw in pairs:
        # Both spellings refuse an empty value: `--caused-by=` must not file
        # the bug with the field silently unset.
        if not raw:
            raise Usage(f'{CAUSED_BY_FLAG} needs a feature id')
        value = raw
    if not value:
        return ''
    try:
        found = model.feature_file(cfg, value)
    except OSError:
        found = None
    if found is None:
        raise Usage(f'{CAUSED_BY_FLAG} {value!r} resolves to no feature in '
                    f'this tree — {CAUSED_BY} names the FEATURE whose change '
                    f'produced the bug (a milestone id or a story id is not '
                    f'one), and nothing was written')
    return value


def _scaffold(cfg: model.PmConfig, kind: str, gdir: Path,
              values: dict[str, str]) -> int:
    """Fill a grain's canonical slots and report only what CHANGED."""
    try:
        templates.render(templates.load(cfg, kind), values)
    except templates.MissingTemplate as err:
        raise Usage(str(err)) from err
    except (OSError, UnicodeDecodeError) as err:
        # An undecodable template is a refusal, not a traceback: exit 1 is for
        # findings.
        raise Refused(f'the {kind} template cannot be read ({err}) — nothing '
                      f'was written') from err
    try:
        actions = templates.scaffold(cfg, kind, gdir, values)
    except templates.ScaffoldRefused as err:
        raise Refused(str(err)) from err
    except templates.MissingTemplate as err:
        raise Usage(str(err)) from err
    for what, path in actions:
        _ok(f'{what} {cfg.rel(path)}')
    if not actions:
        _ok(f'{cfg.rel(gdir)}/ already has every canonical slot (no-op)')
    else:
        _ok(f'{cfg.rel(gdir)}/: {len(actions)} slot(s) filled')
    return 0


def cmd_new(cfg: model.PmConfig, args: list[str]) -> int:
    if not args:
        raise Usage(USAGE)
    grain, rest = args[0], args[1:]
    # `new milestone` and `new feature` are idempotent — they fill missing
    # slots — so the name is optional there.
    if grain == 'milestone':
        if not rest:
            raise Usage(USAGE)
        ver, name = _check_slug('milestone version', rest[0]), ' '.join(rest[1:])
        mdir = model.milestone_dir(cfg, ver)
        if mdir is None:
            if not name:
                raise Usage(f'milestone {ver!r} does not exist yet — a new one '
                            f'needs a name (the name mints the directory)')
            mdir = cfg.roadmap / f'{ver}-{_slugify(name)}'
            if _exists(mdir):
                raise Refused(f'{cfg.rel(mdir)} already exists')
        name = name or model.field_of(mdir / model.MILESTONE_DOC, 'name')
        return _scaffold(cfg, 'milestone', mdir, {'id': ver, 'name': name})
    if grain == 'feature':
        if len(rest) < 2:
            raise Usage(USAGE)
        mid, slug = rest[0], _check_slug('feature slug', rest[1])
        name = ' '.join(rest[2:])
        mdir = model.milestone_dir(cfg, mid)
        if mdir is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        fdir = mdir / 'features' / slug
        if not _exists(fdir / model.FEATURE_DOC) and not name:
            raise Usage(f'feature {mid}/{slug!r} does not exist yet — a new one '
                        f'needs a name')
        name = name or model.field_of(fdir / model.FEATURE_DOC, 'name')
        return _scaffold(cfg, 'feature', fdir,
                         {'id': f'{mid}/{slug}', 'milestone': mid, 'name': name})
    if grain == 'story':
        if len(rest) < 3:
            raise Usage(USAGE)
        fid, slug = rest[0], _check_slug('story slug', rest[1])
        name = ' '.join(rest[2:])
        fdir = model.feature_dir(cfg, fid)
        if fdir is None:
            raise Usage(f'no feature resolves from id {fid!r}')
        # The milestone comes from the feature's own frontmatter, never
        # re-derived from the id.
        mid = model.field_of(fdir / model.FEATURE_DOC, 'milestone')
        # The file may carry an ordering prefix (`01-`); the id never does.
        sid_slug = model.story_slug_of(cfg, slug)
        if not sid_slug:
            raise Refused(f'story slug {slug!r} is an ordering prefix and '
                          f'nothing else — the number sequences the build, the '
                          f'slug after it is the id')
        sf = fdir / model.STORIES_DIR / f'{slug}.md'
        if _exists(sf):
            raise Refused(f'story {fid}/{slug!r} already exists')
        sid = f'{fid}/{sid_slug}'
        claimed = model.story_file(cfg, sid)
        if claimed is not None:
            raise Refused(f'story id {sid!r} is already held by '
                          f'{cfg.rel(claimed)} — two files claiming one id is '
                          f'addressable by neither')
        body = templates.render(
            templates.load(cfg, 'story'),
            {'id': sid, 'feature': fid, 'milestone': mid, 'name': name})
        _mint(cfg, sf, body)
        _ok(f'created {cfg.rel(sf)}')
        return 0
    if grain == 'bug':
        pairs, rest = _take_flags(rest, (CAUSED_BY_FLAG,), noun='a feature id')
        if len(rest) != 2:
            raise Usage(USAGE)
        # Resolved before the slug guard and any write: a bug with an
        # unresolvable cause is not created.
        cause = _caused_by(cfg, pairs)
        mid, slug = rest[0], _check_slug('bug slug', rest[1])
        mdir = model.milestone_dir(cfg, mid)
        if mdir is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        bf = mdir / model.BUGS_DIR / f'{slug}.md'
        bid = f'{mid}/{model.BUGS_DIR}/{slug}'
        if _exists(bf):
            raise Refused(f'bug {bid!r} already exists')
        # Bugs anchor to where they were caught; the path preserves the catch
        # history.
        body = templates.render(
            templates.load(cfg, 'bug'),
            {'id': bid, 'milestone': mid, 'slug': slug})
        _mint(cfg, bf, body)
        _ok(f'created {cfg.rel(bf)}')
        if cause:
            # Stamped through `set_field`, so a project's own bug.md still gets
            # the field; a template with no frontmatter is refused out loud.
            if not model.set_field(bf, CAUSED_BY, cause):
                raise Refused(
                    f'{cfg.rel(bf)} was created, but {CAUSED_BY}: could not be '
                    f'written into it (the bug template has no frontmatter '
                    f'block) — set it with `pm set {bid} '
                    f'{CAUSED_BY} {cause}`')
            _ok(f'{bid}: {CAUSED_BY} {cause!r}')
        return 0
    raise Usage(USAGE)


# --- decide -------------------------------------------------------------------
def _decision_log(cfg: model.PmConfig, gid: str) -> tuple[Path, str]:
    """(the decisions.md the grain `gid` names, its text — minted from the
    template if absent). Nothing is written here; the caller writes once.
    """
    depth = gid.count('/')
    gdir = (model.milestone_dir(cfg, gid) if depth == 0 else
            model.feature_dir(cfg, gid) if depth == 1 else None)
    if depth > 1 or f'/{model.BUGS_DIR}/' in gid:
        raise Refused(f'{gid!r} is a story or a bug — those have no decision '
                      f'log; name the feature or milestone that owns the choice')
    if gdir is None:
        raise Usage(f'no milestone or feature resolves from id {gid!r}')
    log = gdir / model.DECISION_FILE_NAME
    if model.dir_entries(gdir).get(model.DECISION_FILE_NAME) == 'file':
        try:
            return log, model.read_raw(log)
        except (OSError, UnicodeDecodeError) as err:
            raise Usage(f'cannot read {cfg.rel(log)} ({err})') from err
    try:
        return log, templates.render(
            templates.load(cfg, model.SLOT_TEMPLATE[model.DECISION_FILE_NAME]),
            {'id': gid, 'name': model.field_of(
                gdir / f'{"milestone" if depth == 0 else "feature"}.md', 'name')})
    except (OSError, UnicodeDecodeError, templates.MissingTemplate) as err:
        raise Usage(f'the decisions template cannot be read ({err}) — '
                    f'{cfg.rel(log)} was not created') from err


def cmd_decide(cfg: model.PmConfig, args: list[str]) -> int:
    """Append one dated, ordinal-stamped heading; the prose is the author's
    and no field schema is imposed. The title is the remaining argv joined
    with one space; a dangling operator left by a shell split is refused.
    Refuses whole.
    """
    if not args:
        raise Usage(USAGE)
    gid, title = args[0], ' '.join(args[1:]).strip()
    if gid.startswith('-'):
        raise Usage(f'unknown flag {gid!r}')
    if not title:
        raise Usage('decide needs a title — the heading is the entry')
    if title.split()[0].startswith('--'):
        # A title led by a flag is the retired four-field interface; refuse
        # rather than write flag soup.
        raise Usage(f'{title.split()[0]!r} looks like a flag — decide takes '
                    f'none: everything after the grain id is the heading')
    if '\n' in title or '\r' in title:
        raise Refused('a heading is one line — put the reasoning under it')
    if title[-1] in SHELL_SPLITTERS:
        # The residue of an unquoted `;` cut by the caller's shell: a cut
        # between words is invisible, a dangling operator is not, and that one
        # shape is refused.
        raise Refused(
            f'the heading ends with {title[-1]!r} — a shell cut it there and '
            f'the rest never reached this process; nothing was written. Quote '
            f'the whole title: make pm ARGS=\'decide {gid} "first half; '
            f'second half"\'')
    log, text = _decision_log(cfg, gid)
    eid = model.next_entry_id(text)
    when = datetime.now(timezone.utc).date().isoformat()
    try:
        model.write_raw(log, model.append_heading(text, eid, when, title))
    except OSError as err:
        raise Usage(f'could not append to {cfg.rel(log)} ({err})') from err
    _ok(f'{cfg.rel(log)}: {eid} — {when} — {title}')
    # The ledger is per-milestone (D6), so a feature's decision lands in its
    # milestone's file, named by the grain.
    _stamp(cfg, log, ledger.decision_row(gid, eid, title))
    return 0


# --- ledger -------------------------------------------------------------------
# `pm ledger record` copies what the transcript holds, omits what it lacks, and
# labels nothing; it refuses only input it cannot read, and the one question it
# cannot answer — which ledger, when two milestones are building.
LEDGER_FLAGS = ('--from-transcript', '--event', '--agent-id', '--agent-type',
                '--session-id', '--grain', '--tokens-in', '--tokens-out',
                '--tool-calls', '--duration-s', '--duration-ms',
                '--gate', '--verdict',
                '--census')

# The three record forms and the flags each accepts, as a table, so a flag on
# the wrong form is refused rather than silently dropped.
GATE_FLAGS = ('--gate', '--verdict', '--duration-ms', '--census')
GATE_ONLY_FLAGS = ('--verdict', '--census')

DIGITS = frozenset('0123456789')

# `--json` takes no value, so it never reaches `_take_flags`.
JSON_FLAG = '--json'


def _count_flag(flag: str, raw: str) -> int:
    """A non-negative decimal integer, or exit 2; `int()` accepts `-3`, ` 7 `,
    `1_0` and Unicode digits, and a zero here would be a measurement.
    """
    if not raw or not DIGITS.issuperset(raw):
        raise Usage(f'{flag} takes a non-negative integer, not {raw!r}')
    return int(raw)


def _event_kind(raw: str) -> str:
    """`SubagentStop` -> dispatch, `Stop` -> session. Nothing else is an event."""
    kind = ledger.EVENT_KINDS.get(raw)
    if kind is None:
        raise Usage(f'{raw!r} is not a hook event '
                    f'({" ".join(ledger.EVENT_KINDS)})')
    return kind


def _building_ledger_dir(cfg: model.PmConfig, subject: str = 'this row',
                        hint: str = '') -> Path:
    """The milestone directory whose ledger `subject` belongs to (D6): exactly
    one milestone in `in_progress`. None and several are refusals that name
    the situation — the engine never picks (D5).
    """
    live = model.in_progress_milestones(cfg)
    if not live:
        words = ', '.join(model.flow_of(cfg, 'milestone')
                          .by_category.get(model.IN_PROGRESS, ()))
        raise Usage(f'no milestone in {cfg.roadmap_dir} is in progress '
                    f'({words}), so there is no ledger {subject} belongs to — '
                    f'move one there with `pm milestone <state> <id>`{hint} '
                    f'and re-run')
    if len(live) > 1:
        ids = ' '.join(sorted(model.unquote(mid) for mid, _, _ in live))
        raise Usage(f'{len(live)} milestones are in progress ({ids}) — which '
                    f'one owns {subject} is the one thing this verb cannot '
                    f'know, so it is not guessing; run it where exactly one '
                    f'milestone is in progress{hint}')
    return live[0][2].parent


def _tree_snapshot(cfg: model.PmConfig) -> dict:
    """The active tree's live state, verbatim, at the instant of the row (D3):
    every id sorted, empty lists when empty, no ranking. The category keys
    (`*_in_progress`) are what the row means; the frozen seed-word keys
    (`milestones_building`, `features_building`, `features_review`,
    `stories_wip`, `stories_review`) are deprecated — kept because written
    rows are never rewritten, removed at the next major (D7).
    """
    frozen: dict[str, list[str]] = {
        'milestones_building': [], 'features_building': [], 'features_review': [],
        'stories_wip': [], 'stories_review': [],
    }
    live: dict[str, list[str]] = {
        'milestones_in_progress': [], 'features_in_progress': [],
        'stories_in_progress': [],
    }

    def add(snap: dict, bucket: str, path: Path) -> None:
        gid = model.unquote(model.field_of(path, 'id'))
        if gid:
            snap[bucket].append(gid)

    def in_progress(kind: str, status: str) -> bool:
        return model.category_of(cfg, kind, status) == model.IN_PROGRESS

    for mdir in model.milestone_dirs(cfg):
        mfile = mdir / model.MILESTONE_DOC
        mstat = model.field_of(mfile, 'status')
        if in_progress('milestone', mstat):
            add(live, 'milestones_in_progress', mfile)
        if mstat == model.BUILDING:
            add(frozen, 'milestones_building', mfile)
        for ffile in model.feature_files(mdir):
            fstat = model.field_of(ffile, 'status')
            if in_progress('feature', fstat):
                add(live, 'features_in_progress', ffile)
            if fstat == model.BUILDING:
                add(frozen, 'features_building', ffile)
            elif fstat == model.REVIEWING:
                add(frozen, 'features_review', ffile)
            for sfile in model.story_files(ffile):
                sstat = model.field_of(sfile, 'status')
                if in_progress('story', sstat):
                    add(live, 'stories_in_progress', sfile)
                if sstat == model.BUILDING:
                    add(frozen, 'stories_wip', sfile)
                elif sstat == model.REVIEWING:
                    add(frozen, 'stories_review', sfile)
    return {bucket: sorted(ids)
            for bucket, ids in (*frozen.items(), *live.items())}


def cmd_ledger(cfg: model.PmConfig, args: list[str]) -> int:
    if not args:
        raise Usage(USAGE)
    sub, rest = args[0], args[1:]
    if sub == 'record':
        return cmd_ledger_record(cfg, rest)
    if sub == 'show':
        return cmd_ledger_show(cfg, rest)
    if sub == 'report':
        return cmd_ledger_report(cfg, rest)
    raise Usage(f'unknown ledger subcommand {sub!r} (record, show, report)')


def cmd_ledger_record(cfg: model.PmConfig, args: list[str]) -> int:
    """Append one row — dispatch/session from a transcript or by hand, or a
    gate. The forms are exclusive; every hand-form number is optional and
    an omitted one is an omitted key, never a zero, except the gate form's
    `--duration-ms`, which is required.
    """
    pairs, rest = _take_flags(args, LEDGER_FLAGS, noun='a value')
    if rest:
        raise Usage(f'ledger record takes flags only, not {" ".join(rest)!r}')
    flags = dict(pairs)
    # Presence, not truth: `--gate=''` names the form and is refused by the
    # form.
    if '--gate' in flags:
        return _record_gate(cfg, flags)
    stray = [flag for flag in GATE_ONLY_FLAGS if flag in flags]
    if stray:
        raise Usage(f'{" ".join(stray)} belongs to the gate form — name '
                    f'--gate <name> as well, or drop it: a flag this run '
                    f'parsed and dropped would change nothing and say so '
                    f'nowhere')
    source, grain = flags.get('--from-transcript'), flags.get('--grain')
    if source and grain:
        raise Usage('--from-transcript and --grain are exclusive: one row has '
                    'one source, and a transcript already carries what --grain '
                    'would be guessing at')
    if not source and not grain:
        raise Usage('ledger record needs --from-transcript <path> (a hook run) '
                    'or --grain <id> (a hand entry)')
    fields: dict[str, object] = {
        'session_id': flags.get('--session-id', ''),
        'agent_id': flags.get('--agent-id', ''),
        # Only ever the flag: the transcript does not carry the agent type.
        'agent_type': flags.get('--agent-type', ''),
        'tree': _tree_snapshot(cfg),
    }
    if source:
        kind = _event_kind(_required(flags, '--event'))
        fields.update(_from_transcript(source, flags))
    else:
        kind = _event_kind(flags.get('--event', 'SubagentStop'))
        fields.update(_by_hand(cfg, grain, flags))
    row = ledger.usage_row(kind, **fields)
    mdir = _building_ledger_dir(cfg)
    try:
        ledger.append_row(mdir, row)
    except OSError as err:
        raise Usage(f'{cfg.rel(ledger.ledger_path(mdir))} could not be appended '
                    f'to ({err}); no row was written') from err
    _ok(f'ledger {kind} row appended to '
        f'{cfg.rel(ledger.ledger_path(mdir))}')
    return 0


def _record_gate(cfg: model.PmConfig, flags: dict[str, str]) -> int:
    """The gate form: what one gate run cost, as one row. The calling shell
    wrapper discards this exit code, so nothing here may exit 0 having
    written nothing.
    """
    for other in ('--from-transcript', '--grain'):
        if other in flags:
            raise Usage(f'--gate and {other} are exclusive: a gate run is not '
                        f'a dispatch, and one row has one subject')
    stray = sorted(flag for flag in flags if flag not in GATE_FLAGS)
    if stray:
        raise Usage(f'the gate form takes {" ".join(GATE_FLAGS)} only, not '
                    f'{" ".join(stray)} — a gate run has no agent, no session '
                    f'and no token count, and a flag parsed then dropped is a '
                    f'caller told nothing')
    gate = _gate_name(flags['--gate'])
    verdict = _gate_verdict(flags)
    if '--duration-ms' not in flags:
        raise Usage('--duration-ms is required with --gate: a cost row with no '
                    'cost is a column nothing can read, and the cost is the '
                    'whole point of the row')
    # Milliseconds here, seconds on the dispatch form: most gates finish inside
    # a second and an integer-second row cannot resolve them.
    duration = _count_flag('--duration-ms', flags['--duration-ms'])
    # Absent, never 0: a `0` census is the zero-file scan rule 4 names.
    census = (_count_flag('--census', flags['--census'])
              if '--census' in flags else None)
    mdir = _gate_ledger_dir(cfg)
    try:
        ledger.append_row(mdir, ledger.gate_row(gate, verdict, duration,
                                                census))
    except OSError as err:
        raise Usage(f'{cfg.rel(ledger.ledger_path(mdir))} could not be appended '
                    f'to ({err}); no row was written') from err
    _ok(f'ledger gate row appended to {cfg.rel(ledger.ledger_path(mdir))}')
    return 0


def _gate_name(raw: str) -> str:
    """A make-target name, or exit 2 — the string the report joins on.
    `fullmatch`, because `$` matches before a trailing newline and a
    newline would forge a second row.
    """
    if raw and len(raw) <= ledger.GATE_NAME_MAX and ledger.GATE_NAME.fullmatch(
            raw):
        return raw
    raise Usage(f'--gate takes a make-target name '
                f'([A-Za-z0-9][A-Za-z0-9._+-]*, at most '
                f'{ledger.GATE_NAME_MAX} characters), not {raw!r}')


def _gate_verdict(flags: dict[str, str]) -> str:
    """One of the closed set, or exit 2: a durable column cannot be free
    text.
    """
    if '--verdict' not in flags:
        raise Usage('--verdict is required with --gate '
                    f'({" ".join(ledger.GATE_VERDICTS)})')
    raw = flags['--verdict']
    if raw not in ledger.GATE_VERDICTS:
        raise Usage(f'--verdict is one of {" ".join(ledger.GATE_VERDICTS)}, '
                    f'not {raw!r} — the summary line is prose, this column is '
                    f'a vocabulary')
    return raw


def _gate_ledger_dir(cfg: model.PmConfig) -> Path:
    """Where a gate row lands, or a refusal naming which of the two it was.
    Exit 1, not 2: nothing to record into is a precondition, not a bad
    argument.
    """
    if not cfg.roadmap.is_dir():
        raise Refused(f'there is no PM tree at {cfg.rel(cfg.roadmap)}, so '
                      f'there is no ledger this gate row belongs to; no row '
                      f'was written')
    live = model.in_progress_milestones(cfg)
    if not live:
        raise Refused(f'no milestone in {cfg.rel(cfg.roadmap)} is in '
                      f'progress, so there is no ledger this gate row '
                      f'belongs to; no row was written')
    if len(live) > 1:
        _building_ledger_dir(cfg, 'this gate row')
    return live[0][2].parent


def _required(flags: dict[str, str], name: str) -> str:
    value = flags.get(name)
    if not value:
        raise Usage(f'{name} is required here')
    return value


def _from_transcript(source: str, flags: dict[str, str]) -> dict:
    """Sum the transcript at `source`, taking its ids only where a flag is
    silent. The path is used as given — the hook hands over one outside the
    repo — and must be an existing file.
    """
    path = Path(source).expanduser()
    if not path.is_file():
        raise Usage(f'--from-transcript {source!r} is not a file')
    try:
        summary = ledger.transcript_summary(ledger.records_of(path))
        # A second pass rather than a second copy: the ids are only wanted when
        # the caller did not state them.
        for name, key in (('session_id', 'sessionId'), ('agent_id', 'agentId')):
            if not flags.get(f'--{name.replace("_", "-")}'):
                summary[name] = ledger.id_from_records(
                    ledger.records_of(path), key)
    except ledger.TranscriptError as err:
        raise Usage(f'{err}') from err
    return {k: v for k, v in summary.items() if v is not None}


def _by_hand(cfg: model.PmConfig, grain: str, flags: dict[str, str]) -> dict:
    """The hand form's fields; `--grain` must resolve through `_grain_file`,
    because a typo'd id in a ledger row is a lie nothing downstream can
    check.
    """
    path = _grain_file(cfg, grain)
    usage = {}
    for key, flag in (('input', '--tokens-in'), ('output', '--tokens-out')):
        if flag in flags:
            usage[key] = _count_flag(flag, flags[flag])
    fields: dict[str, object] = {'grain': _ledger_id(path, grain)}
    if usage:
        # Only the keys the caller gave: absent, not 0, means nobody counted.
        fields['usage'] = usage
    for key, flag in (('tool_calls', '--tool-calls'),
                      ('duration_s', '--duration-s')):
        if flag in flags:
            fields[key] = _count_flag(flag, flags[flag])
    return fields


def _grain_kind(gid: str) -> str:
    """Which vocabulary an id answers to, by the shape `_grain_file` resolves
    by; `ledger.ends_grain` owns which states end it.
    """
    if f'/{model.BUGS_DIR}/' in gid:
        return ledger.GRAIN_BUG
    depth = gid.count('/')
    return 'milestone' if depth == 0 else 'feature' if depth == 1 else 'story'


def cmd_ledger_show(cfg: model.PmConfig, args: list[str]) -> int:
    """One grain's rows, oldest first, with the seconds between status rows; a
    total only once the grain reached a finished state. No rows is exit 0 —
    a fact, not an error.
    """
    rest = [a for a in args if a != JSON_FLAG]
    as_json = JSON_FLAG in args
    if len(rest) != 1:
        raise Usage(USAGE)
    gid = rest[0]
    path = _grain_file(cfg, gid)
    mdir = model.milestone_dir_of(cfg, path)
    if mdir is None:
        raise Usage(f'{cfg.rel(path)} is not inside a milestone directory, so '
                    f'no ledger owns {gid!r}')
    # Both spellings: the id the caller typed and the id the file claims, which
    # is what `_stamp` wrote.
    names = {gid, _ledger_id(path, gid)}
    try:
        rows = [r for r in ledger.read_rows(ledger.ledger_path(mdir))
                if ledger.row_names(r.data, names)]
    except ledger.LedgerError as err:
        raise Usage(f'{err}') from err
    if not rows:
        print(f'[pm] no rows for {gid}',
              file=sys.stderr if as_json else sys.stdout)
        return 0
    if as_json:
        for row in rows:
            print(row.line)
        return 0
    previous = None
    for row in rows:
        line = f'{row.data.get("ts", "")}  {row.data.get("kind", ""):<8}'
        if row.data.get('kind') == ledger.KIND_STATUS:
            line += f'  {row.data.get("from")} -> {row.data.get("to")}'
            gap = _gap(previous, row)
            if previous is not None and gap is not None:
                line += f'  +{gap}s'
            previous = row
        print(line.rstrip())
    status = [r for r in rows if r.data.get('kind') == ledger.KIND_STATUS]
    total = ledger.total_seconds(cfg, _grain_kind(gid), status)
    if total is not None:
        print(f'first row → terminal row: {total}s')
    return 0


def _gap(earlier, later) -> int | None:
    """Whole seconds between two rows' stamps, or None when either will not
    parse — a fabricated interval is worse than a missing one.
    """
    if earlier is None:
        return None
    start = ledger.parse_ts(earlier.data.get('ts'))
    end = ledger.parse_ts(later.data.get('ts'))
    if start is None or end is None:
        return None
    return int((end - start).total_seconds())


# --- ledger report ------------------------------------------------------------
# The report is the caller the ledger leaves judgement to: sum, count, subtract
# and group over rows on disk, and nothing else (D5 — no weight, price, score
# or label). It reads and never writes.
REPORT_SUBJECT = 'this report'
REPORT_HINT = ', or name one: `pm ledger report <milestone-id>`'

# `--from <rev>` reads the milestone out of git (D6); the rev is always the
# caller's, never searched for.
FROM_FLAG = '--from'


def cmd_ledger_report(cfg: model.PmConfig, args: list[str]) -> int:
    """One milestone's rows, added up per grain — see report.py. The building
    milestone by default, an explicit id otherwise; no `ledger.jsonl`
    prints one line at exit 0. `--from <rev>` runs the same `report.build`
    over `report.GitSource`, writing nothing and touching no index.
    """
    as_json = JSON_FLAG in args
    rest = [a for a in args if a != JSON_FLAG]
    # Whether `--from` was given and what it was given are two questions: an
    # empty value once read as "no rev" and was answered about the working
    # tree.
    given = FROM_FLAG in rest
    rev = ''
    if given:
        if rest.count(FROM_FLAG) > 1:
            raise Usage(f'{FROM_FLAG} was given {rest.count(FROM_FLAG)} times '
                        f'— a report reads ONE rev, and which of two it should '
                        f'have been is not a thing this verb may pick')
        # Taken positionally, never searched for: `--from` at the end of the
        # line is a missing value.
        at = rest.index(FROM_FLAG)
        rev = rest[at + 1] if at + 1 < len(rest) else ''
        rest = rest[:at] + rest[at + 2:]
    for arg in rest:
        if arg.startswith('-'):
            raise Usage(f'unknown flag {arg!r} (ledger report takes '
                        f'{JSON_FLAG}, {FROM_FLAG} <rev> and a milestone id)')
    if len(rest) > 1:
        raise Usage(f'ledger report takes one milestone id, not '
                    f'{" ".join(rest)!r}')
    if given and not rest:
        # "The building milestone" is a fact about today's tree, not about a
        # rev.
        raise Usage(f'{FROM_FLAG} needs a milestone id: which milestone is '
                    f'`building` is a fact about the tree NOW, and a report at '
                    f'a rev may not take its subject from one tree and its '
                    f'rows from another — `pm ledger report <milestone-id> '
                    f'{FROM_FLAG} <rev>`')
    try:
        src: report.Source = (report.GitSource(cfg.root, rev) if given
                              else report.DiskSource())
        if given:
            mdir = _report_milestone_dir_at(cfg, src, rest[0])
        else:
            mdir = (_report_milestone_dir(cfg, rest[0]) if rest
                    else _building_ledger_dir(cfg, REPORT_SUBJECT, REPORT_HINT))
        mid = _ledger_id(mdir / model.MILESTONE_DOC, mdir.name, src)
        path = ledger.ledger_path(mdir)
        try:
            rows = src.ledger_rows(path)
        except ledger.LedgerError as err:
            raise Usage(f'{err}') from err
        try:
            data = report.build(cfg, mid, mdir, rows, src)
        except report.RecordError as err:
            # The second document this verb parses, refused the same way as the
            # first: a verdict block that exists and cannot be read, named by
            # record and line.
            raise Usage(f'{err}') from err
    except report.GitError as err:
        # Every git refusal, one exit code: a bad rev carries git's own words,
        # a missing path names the path.
        raise Usage(f'{err}') from err
    if as_json:
        print(json.dumps(data, ensure_ascii=False))
        return 0
    if not src.is_file(path):
        # No ledger is a fact about section 1 only; sections 2 and 4 read other
        # documents, so the report still prints when those hold something.
        print(f'{report.HEADING_PREFIX} {report.heading_id(data)} — '
              f'{report.NO_LEDGER}')
        if not report.beyond_ledger(data):
            return 0
    for line in report.render(cfg, data):
        print(line)
    return 0


def _report_milestone_dir_at(cfg: model.PmConfig, src: report.Source,
                             mid: str) -> Path:
    """The milestone directory at a rev, or exit 2 naming what is not there.
    Resolved by version prefix over `git ls-tree`, active tree then
    archive, as `model.milestone_dir` globs on disk; a rev after the
    retirement is the ordinary mistake, so the message says which rev to
    reach for.
    """
    if not model.segment_is_literal(mid):
        raise Usage(f'no milestone resolves from id {mid!r} — the ledger is '
                    f'per milestone (D6), so {FROM_FLAG} reports a milestone '
                    f'id (`0.23.0`) and never a feature, story or bug')
    mdir = src.milestone_dir(cfg, mid)
    if mdir is None:
        raise Usage(f'no milestone directory {mid}-* under {cfg.roadmap_dir}/ '
                    f'or {cfg.roadmap_dir}/{model.ARCHIVE_DIR_NAME}/ at '
                    f'{src.rev} — a milestone is retired at the close AFTER '
                    f'its own, so name the rev it was still in the tree at '
                    f'(usually its release tag)')
    doc = mdir / model.MILESTONE_DOC
    if not src.is_file(doc):
        raise Usage(f'{src.spec(doc)} is not there, so {mid!r} is a directory '
                    f'at {src.rev} and not a milestone')
    return mdir


def _report_milestone_dir(cfg: model.PmConfig, mid: str) -> Path:
    """The directory of an explicitly named milestone, or exit 2; a feature or
    story id is the wrong noun, since the ledger is per milestone.
    """
    path = _grain_file(cfg, mid)
    if path.name != model.MILESTONE_DOC:
        raise Usage(f'{mid!r} is a {_grain_kind(mid)}, not a milestone — the '
                    f'ledger is per milestone (D6), so name one (or run it '
                    f'with no id where exactly one milestone is building)')
    mdir = model.milestone_dir_of(cfg, path)
    if mdir is None:
        raise Usage(f'{cfg.rel(path)} is not inside a milestone directory, so '
                    f'no ledger owns {mid!r}')
    return mdir


# --- dispatch -----------------------------------------------------------------
_PLAN_SCAFFOLD = """---
order:
---

# The release plan

The order releases ship in. It is a DECISION, not a sort: versions are strings
this package never parses, and `agentic-sdlc pm order` is what edits this list.

A milestone joins the plan by declaring `version:` and being appended here; the
two are separate acts, so a draft milestone is not accidentally on the roadmap.
"""


def _plan_path(cfg: model.PmConfig) -> Path:
    return model.releases_file(cfg)


def _version_arg(value: str) -> str:
    """A version is a fact about the INPUT: non-empty, and a literal.

    Reuses `model.segment_is_literal` (SDLC.md §5 — the matrix belongs to the
    grammar) rather than spelling a second refusal list here: the same grammar
    guards every id segment this package joins onto a path or prints.
    """
    if not value or not value.strip():
        raise Usage('a version may not be empty')
    if not model.segment_is_literal(value):
        raise Usage(f'{value!r} is not a literal version — no glob character, '
                    f'no path separator, and neither `.` nor `..`')
    return value


def _write_plan(cfg: model.PmConfig, entries: list[str]) -> None:
    path = _plan_path(cfg)
    if not path.is_file():
        # Through `core.apply`, like every other mutation: a writer that
        # decides as it goes lands half a plan when a later step refuses.
        apply.raise_on_error(apply.make_dir(path.parent))
        model.write_raw(path, _PLAN_SCAFFOLD)
    if not model.set_list_field(path, model.ORDER_KEY, entries):
        raise Refused(f'{cfg.rel(path)} could not be rewritten — it has no '
                      f'frontmatter block, or `{model.ORDER_KEY}:` carries a '
                      f'scalar rather than a list; nothing was written')


def _print_plan(cfg: model.PmConfig) -> None:
    entries = model.declared_order(cfg)
    path = _plan_path(cfg)
    if not entries:
        print(f'[pm] {cfg.rel(path)} declares no order — '
              f'`agentic-sdlc pm order --append <version>` starts the plan')
        return
    print(f'[pm] {len(entries)} release(s) in {cfg.rel(path)}')
    for version in entries:
        mid = model.milestone_of_version(cfg, version)
        shipped = 'shipped' if model.release_is_shipped(cfg, version) else '-'
        print(f'{version}\t{mid or "(unclaimed)"}\t{shipped}')


def cmd_order(cfg: model.PmConfig, args: list[str]) -> int:
    """Read or edit the release plan. One entry per invocation: the list is a
    decision, and a bulk rewrite is an editor's job, not a verb's.
    """
    flags = {'--append': None, '--insert': None, '--remove': None,
             '--before': None}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in flags:
            raise Usage(f'unknown flag {flag!r}')
        if i + 1 >= len(args):
            raise Usage(f'{flag} takes a version')
        if flags[flag] is not None:
            raise Usage(f'{flag} given twice')
        flags[flag] = _version_arg(args[i + 1])
        i += 2

    named = [f for f in ('--append', '--insert', '--remove') if flags[f]]
    if len(named) > 1:
        raise Usage(f'{" and ".join(named)} are three different edits — one '
                    f'per invocation')
    if not named:
        if flags['--before']:
            raise Usage('--before belongs to --insert')
        _print_plan(cfg)
        return 0

    entries = model.declared_order(cfg)
    path = _plan_path(cfg)

    if flags['--append']:
        version = flags['--append']
        if flags['--before']:
            raise Usage('--before belongs to --insert, not --append')
        if version in entries:
            # Idempotent, and it SAYS so: re-running a plan edit is normal.
            print(f'[pm] {version} is already in {cfg.rel(path)} at position '
                  f'{entries.index(version) + 1} — nothing was written')
            return 0
        _write_plan(cfg, entries + [version])
        print(f'[pm] appended {version} to {cfg.rel(path)} '
              f'(position {len(entries) + 1})')
        return 0

    if flags['--insert']:
        version = flags['--insert']
        before = flags['--before']
        if not before:
            raise Usage('--insert needs --before <version> — where in the plan '
                        'is the decision, and this verb never guesses it')
        if version in entries:
            print(f'[pm] {version} is already in {cfg.rel(path)} at position '
                  f'{entries.index(version) + 1} — nothing was written')
            return 0
        if before not in entries:
            raise Refused(f'--before {before!r} is not in {cfg.rel(path)} — '
                          f'nothing was written')
        at = entries.index(before)
        _write_plan(cfg, entries[:at] + [version] + entries[at:])
        print(f'[pm] inserted {version} before {before} in {cfg.rel(path)} '
              f'(position {at + 1})')
        return 0

    version = flags['--remove']
    if flags['--before']:
        raise Usage('--before belongs to --insert, not --remove')
    if version not in entries:
        print(f'[pm] {version} is not in {cfg.rel(path)} — nothing was written')
        return 0
    _write_plan(cfg, [v for v in entries if v != version])
    print(f'[pm] removed {version} from {cfg.rel(path)}')
    return 0


def cmd_roadmap(cfg: model.PmConfig, args: list[str]) -> int:
    """The plan: every scheduled release, then the backlog. Writes nothing.

    What `pm status` does for one milestone, for the SEQUENCE — and the verb
    that replaced `ROADMAP.md`, which was a hand-maintained second scoreboard
    of exactly this.
    """
    if args:
        raise Usage(f'roadmap takes no arguments, got {" ".join(args)}')
    entries = model.declared_order(cfg)
    path = model.releases_file(cfg)
    defect = model.plan_defect(cfg)
    if defect is not None:
        raise Refused(f'{cfg.rel(path)} {defect}')
    if not entries:
        print(f'[pm] {cfg.rel(path)} declares no order — '
              f'`agentic-sdlc pm order --append <version>` starts the plan')
    else:
        print(f'[pm] {len(entries)} scheduled release(s) in {cfg.rel(path)}')
        for version in entries:
            claimants = model.milestones_of_version(cfg, version)
            if len(claimants) == 1:
                mid = claimants[0]
                mfile = model.milestone_file(cfg, mid)
                status = model.field_of(mfile, 'status') if mfile else ''
                state = ('shipped' if model.release_is_shipped(cfg, version)
                         else status or '-')
            elif claimants:
                mid, state = ' '.join(claimants), 'CLAIMED TWICE'
            else:
                mid, state = '(unclaimed)', 'unverifiable'
            print(f'{version}\t{mid}\t{state}')
    bound = {mid for _, mid in model.version_claims(cfg)}
    backlog = sorted(mid for _, mid in model.known_milestones(cfg)
                     if mid and mid not in bound)
    if backlog:
        print(f'[pm] {len(backlog)} in backlog (no version: — not proposed '
              f'as a release)')
        for mid in backlog:
            mfile = model.milestone_file(cfg, mid)
            print(f'-\t{mid}\t{model.field_of(mfile, "status") if mfile else ""}')
    return 0


def cmd_next(cfg: model.PmConfig, args: list[str]) -> int:
    """The first entry in `order` that has not shipped, and who claims it."""
    if args:
        raise Usage(f'next takes no arguments, got {" ".join(args)}')
    entries = model.declared_order(cfg)
    if not entries:
        print(f'[pm] {cfg.rel(_plan_path(cfg))} declares no order — '
              f'`agentic-sdlc pm order --append <version>` starts the plan')
        return 0
    for version in entries:
        if model.release_is_shipped(cfg, version):
            continue
        mid = model.milestone_of_version(cfg, version)
        if mid is None:
            print(f'{version}\t(unclaimed)\t'
                  f'no milestone declares version: {version}')
            return 0
        mfile = model.milestone_file(cfg, mid)
        status = model.field_of(mfile, 'status') if mfile else ''
        print(f'{version}\t{mid}\t{status}')
        return 0
    print(f'[pm] every release in {cfg.rel(_plan_path(cfg))} has shipped')
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(USAGE)
        return 0 if argv else 2
    try:
        cfg = model.load()
    except model.ConfigError as err:
        print(f'[pm] ERROR — {err}', file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    # Deferred: `ready_for` and `skills` import this module's shared
    # vocabulary, so binding at call time keeps load order a non-question.
    from agentic_sdlc.repo.pm import ready_for, skills
    table = {
        'ready-for': ready_for.cmd_ready_for,
        'story': cmd_story, 'bug': cmd_bug, 'feature': cmd_feature,
        'milestone': cmd_milestone, 'retire': cmd_retire, 'move': cmd_move,
        'status': cmd_status, 'list': cmd_list, 'new': cmd_new,
        'validate': cmd_validate, 'install-skills': skills.cmd_install_skills,
        'init': skills.cmd_init, 'set': cmd_set, 'get': cmd_get,
        'templates': skills.cmd_templates, 'sync': cmd_sync,
        'vocabulary': cmd_vocabulary, 'decide': cmd_decide,
        'ledger': cmd_ledger, 'order': cmd_order, 'next': cmd_next,
        'roadmap': cmd_roadmap,
    }
    fn = table.get(cmd)
    if fn is None:
        print(f'{PROG}: unknown command {cmd!r}', file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    try:
        return fn(cfg, rest)
    except Refused as err:
        print(f'[pm] REFUSED — {err}', file=sys.stderr)
        return 1
    except (Usage, model.AmbiguousStory, model.ConfigError) as err:
        # `ConfigError` here is the declaration's lazy half — `flow_of` refuses
        # mid-walk — and it must be one line at exit 2, since a traceback at
        # exit 1 reads as findings.
        print(f'[pm] ERROR — {err}', file=sys.stderr)
        return 2
