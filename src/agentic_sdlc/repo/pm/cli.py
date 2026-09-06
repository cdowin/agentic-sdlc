"""cli.py — the PM-tree status CLI.

Moves a story/feature/milestone `status:` through code rather than a regex: the
verb validates the value against that grain's DECLARED flow (`model.move_defect`
— is this a state the project named in `[pm.states.<kind>]`?), writes ONLY the
`status:` line (plus `reviewed:` on a feature close), preserves every other
byte and line ending, and is idempotent.

EVERY QUESTION THIS CLI ASKS OF A STATUS IS ASKED OF ITS CATEGORY — `todo`,
`in_progress` or `done` — through `model.holds`, never of the word. "Is this
feature's work finished" is `holds(stories, done)`; "which state is the close"
is `category_of(to) == done`; which WORDS sit in those categories is the
project's declaration, and a project that renames every one of them gets this
CLI's behaviour unchanged. The seed's words appear in this file's prose for
reading only.

It does NOT own a transition graph. Nothing checks an EDGE — D3/D4/D5 check the
tree's END STATE — so a graph here would only tax whoever used the sanctioned
tool while a `sed` of the same line reached the state it refused. A verb writes
the ONE grain it was named; a feature close touches no story file, so a closed
feature over unclosed stories is the DEFAULT outcome and an intended one — what
the tree is then left holding is D5's question, asked of the tree. Every close
reports the stories it did not touch. (The `--cascade` that used to close a
feature's `reviewing` stories is gone: which stories to move and to what was the
engine's opinion about two words, and the feature belt closes stories through
the story belt, one at a time, by name.)

Its companion is `agentic-sdlc check pm`, which imports the same predicates
from model.py and makes an inconsistent END STATE loud.

Every verb here that CHANGES a grain also appends one timestamped row to that
milestone's `ledger.jsonl` (D6/D8), after its own write lands and never before
— see `_stamp` below. The row is a side effect on disk: no verb's output line
or exit code depends on it.

Exit codes: 0 ok (incl. idempotent no-op) · 1 a refusal — a precondition said
no and nothing was written (`--review-record` naming no file is the one that
ships) · 2 usage / resolution error.
"""
from __future__ import annotations

import json
import sys
import textwrap
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
  feature <status> <feature-id>           (any state in [pm.states.feature];
                                           a move into in_progress reports the
                                           stories not in `done`)
  feature <done-state> <feature-id> [--review-record <path>]
                                          (a state in the `done` category
                                           closes: stamps `reviewed:` from the
                                           flag and reports the stories not in
                                           `done`. No story file is touched —
                                           the story belt closes each by name)
  milestone <status> <milestone-id>       (any state; a move into `done`
                                           reports the features not there)
  retire <milestone-id> [<summary...>] [--dry-run]
                                          (removes the milestone directory and
                                           appends its row to ROADMAP.md;
                                           reports an undone status or live
                                           children rather than refusing on
                                           their account — refuses only when
                                           the id or ROADMAP.md itself is
                                           missing)
  move <story-id> <feature-id>            (re-parents a story: renames its
                                           file under the target feature and
                                           rewrites id/feature/milestone —
                                           whole, or not at all)
  status [<milestone>]
  list [--status <s>[,<s>…]] [--owner <name>] [--milestone <id>]
                                          (one tab-separated line per story:
                                           id, status, owner, feature)
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
  set <grain-id> <key> <value>            (write one frontmatter field)
  templates [--force]                     (copy the templates into the project to edit)
  sync [--check]                          (re-render the execution lists)
  vocabulary [--json]                     (this version's declared surface: the
                                           closed state sets, the flow this
                                           project declared, the conveyor step
                                           names a [pm.transitions.<kind>] may
                                           key on, and the rule ids. A tree
                                           declaring no flow is REPORTED, with
                                           the seed `init` would write)
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



# A heading ENDING in one of these is what a consumer's unquoted `make ARGS`
# leaves behind when its shell cuts the title in half — see cmd_decide.
SHELL_SPLITTERS = (';', '&', '|')


class Refused(Exception):
    """A precondition said no. Exit 1."""


class Usage(Exception):
    """Bad arguments, or an id that resolves to nothing. Exit 2."""


def _ok(msg: str) -> None:
    print(f'[pm] {msg}')


def _check_slug(kind: str, value: str) -> str:
    """A slug becomes a path component AND half an id. Reject anything else.

    `_slugify` was applied to a grain's NAME only, never to the slug or version
    argument, and `id_is_literal` guards resolution rather than creation — so
    `pm new bug 0.1 ../../../pwned` wrote outside the repo root and exited 0.
    A write verb that touches what it was not asked to is the cardinal sin.
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
    """`Path.exists()` that answers False for a path the FILESYSTEM refuses.

    A component longer than the filesystem's NAME_MAX raises `OSError` out of
    `stat` on 3.11, 3.12 and 3.13, and is swallowed into False from 3.14 on. So
    one `pm new` came out as a traceback or as a refusal depending on which
    interpreter `uvx` picked, and a tool whose behaviour depends on that is not
    a tool. False is the answer both readings want: nothing is there, and the
    write that follows refuses with the reason.
    """
    try:
        return path.exists()
    except OSError:
        return False


def _mint(cfg: model.PmConfig, path: Path, body: str) -> None:
    """Write one new grain FILE, turning a filesystem refusal into a REFUSED.

    `new story` and `new bug` write straight rather than through the idempotent
    scaffolder, so neither guard that verb grew covers them: a slug the
    filesystem will not take, or an unwritable `stories/`, came out as an
    `OSError` traceback under exit 1 — the code a consumer's pre-push hook
    reads as "drift found".
    """
    try:
        templates.write(path, body)
    except OSError as err:
        raise Refused(f'{cfg.rel(path)} could not be written ({err}) — nothing '
                      f'was written; shorten the slug, or make '
                      f'{cfg.rel(path.parent)}/ writable') from err


def _slugify(text: str) -> str:
    """ASCII-only, because the result becomes a permanent directory name.

    `str.isalnum()` is Unicode-aware, so it would happily mint `café-niño` or a
    CJK path — an NFC/NFD and Windows-encoding hazard for something that is an
    id forever after.
    """
    keep = 'abcdefghijklmnopqrstuvwxyz0123456789'
    out = ''.join(c if c in keep else '-' for c in text.lower())
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')


def _was(path: Path) -> str:
    """The status a grain currently carries, FOR THE MESSAGE ONLY.

    Never for a decision. A status verb validates the state it was ASKED for
    against the closed vocabulary and writes it; what the file held before is
    posterity, printed as `wombat -> done`. Gating on it made the verb refuse
    exactly the drift D4 reports — the gate diagnosed a hand-edited `wombat`
    and the tool that exists to spare a person the hand-edit declined to
    repair it, leaving the editor as the only way out. `(none)` when the key is
    absent, which is the same fact and equally repairable.
    """
    return model.field_of(path, 'status') or '(none)'


def _set_status(cfg: model.PmConfig, path: Path, value: str, note: str = '') -> None:
    if not model.set_field(path, 'status', value):
        raise Usage(f'could not rewrite status in {cfg.rel(path)} '
                    f'(malformed frontmatter, or the file is not writable)'
                    + (f'. {note}' if note else ''))


# --- the ledger ---------------------------------------------------------------
# Every verb below that CHANGES the tree appends one row to the milestone's
# `ledger.jsonl` (D6/D8). Three rules hold everywhere, and the tests pin all
# three:
#
#   * AFTER the write, never before. A row is the record of a write that
#     landed; a row for a refused flip is rule 4's cardinal sin with a
#     timestamp on it.
#   * A NO-OP still appends. Somebody ran the verb at that instant, and the
#     ledger records what happened, not what changed.
#   * The row never changes the verb's OUTPUT or its EXIT CODE (hard rule 6).
#     A ledger that cannot be written is said out loud on stderr and does not
#     turn a landed status write into a failure — the flip is what the caller
#     asked for and it is already on disk.
def _ledger_id(path: Path, fallback: str,
               src: report.Source | None = None) -> str:
    """The id a row names: the grain's OWN `id:`, the caller's when absent.

    The frontmatter id is the file's own claim about itself, which is what a
    report joins rows on. A grain missing the key at all (the drift V2 and D4
    report) still gets a row, under the id the caller resolved it by — an
    unnamed row would be worse than an imperfectly-named one.

    `src` is where the document is READ from — the working tree for every
    writer here, and `report.GitSource` for `ledger report --from <rev>`, whose
    milestone document is not in the tree at all. One definition either way: a
    report of a retired milestone must name it the same id its rows do.
    """
    reader = report.DiskSource() if src is None else src
    return model.unquote(reader.field_of(path, 'id')) or fallback


def _stamp(cfg: model.PmConfig, path: Path, row: dict) -> None:
    """Append one row to the ledger of the milestone that owns `path`.

    Never raises, and never changes an exit code: by the time this runs the
    tree has already been changed and the verb has already reported it. The
    two ways it can come up empty — a grain that resolves outside any
    milestone directory, and a ledger that cannot be written — are both
    printed on stderr naming the path, because a missing row is a fact the
    next report needs and silence here is the one thing that would hide it.
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
    """Exit 2 unless `to` is a state this project declared for `kind`.

    `model.move_defect` is the engine's whole opinion about a move, and every
    status verb asks it BEFORE resolving the grain — a target outside the
    declaration used to dispatch first, so a custom vocabulary had the
    sanctioned tool writing the exact word D4 then reported.
    """
    defect = model.move_defect(cfg, kind, to)
    if defect:
        raise Usage(defect)


def _unfinished(cfg: model.PmConfig, kind: str,
                grains) -> list[str]:
    """`<name>(<status>)` for every grain NOT in `done` — `holds`' blockers.

    The one shape every advisory in this file prints, so `feature`,
    `milestone` and `retire` cannot describe "not finished" three ways.
    """
    held = model.holds(cfg, kind, grains, model.DONE_CATEGORY)
    return [f'{name}({status})' for name, status in held.blockers]


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
    """Move a bug's `status:` through code — exactly `cmd_story`'s shape.

    A bug's status is the one fact that "matters most" (its own docstring in
    `checks/pm.py`), and today only a hand edit or the untyped `pm set`
    reaches it — a typo'd status the vocabulary would have refused going
    straight into the file the vocabulary exists to police. This closes that.

    `bid` must NAME a bug (contain `/bugs/`) before `_grain_file` ever runs:
    `_grain_file` resolves a milestone/feature/story id too when `/bugs/` is
    absent, and a bug verb resolving to a FEATURE file would flip that
    file's `status:` to a word validated against the bug flow instead of its
    own — a cross-grain write no caller asked for.
    """
    if len(args) != 2:
        raise Usage(USAGE)
    to, bid = args
    _movable(cfg, 'bug', to)
    if f'/{model.BUGS_DIR}/' not in bid:
        raise Usage(f'no bug resolves from id {bid!r} '
                    f'(expected <milestone>/bugs/<slug>)')
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


def _story_states(cfg: model.PmConfig, fid: str) -> list[tuple[str, str]]:
    ff = model.feature_file(cfg, fid)
    assert ff is not None
    return [(s.name, model.field_of(s, 'status')) for s in model.story_files(ff)]


def cmd_feature_simple(cfg: model.PmConfig, to: str, args: list[str]) -> int:
    """Any feature move that is not a close. One write, one advisory.

    The advisory — the stories not in `done`, named with the word each file
    holds — prints on every move INTO `in_progress`. It used to print on
    `reviewing` alone (B3), which was the engine knowing that one word is the
    hand-off; under categories "work has started on this feature" is the
    honest trigger, and `holds(stories, done)` is the one question
    `pm ready-for feature` asks too, so the two cannot name different sets.
    Reported, never refused: "a feature cannot be under review while its own
    work is unfinished" is a claim about how a team works, and which stories
    are where is a fact for the caller to act on.
    """
    if len(args) != 1:
        raise Usage(USAGE)
    fid = args[0]
    ff, cur = _feature_or_usage(cfg, fid)
    if cur == to:
        _ok(f'feature {fid} already {to} (no-op)')
        _stamp_status(cfg, ff, cur, to, fid)
        return 0
    pending = (_unfinished(cfg, 'story', _story_states(cfg, fid))
               if model.category_of(cfg, 'feature', to) == model.IN_PROGRESS
               else [])
    _set_status(cfg, ff, to)
    _ok(f'feature {fid}: {cur} -> {to}')
    _stamp_status(cfg, ff, cur, to, fid)
    if pending:
        _ok(f'  {len(pending)} story/ies not finished: {" ".join(pending)}')
    return 0


def _resolve_record(cfg: model.PmConfig, rec: str) -> Path:
    return Path(rec) if rec.startswith('/') else cfg.root / rec


def _take_flags(args: list[str], flags: tuple[str, ...],
                noun: str = 'a value') -> tuple[list[tuple[str, str]],
                                                list[str]]:
    """Parse `--flag value` / `--flag=value` out of `args`, in order.

    One home for the loop `feature done` and `list` each hand-rolled. Returns
    (the (flag, value) pairs seen, everything else in its original order). A
    flag with nothing after it refuses, naming what it needed; an EMPTY value
    is the caller's question — the `=` spelling with nothing after it once
    stored '' and silently skipped `--review-record`'s stamp, so that caller
    refuses it where a filter flag folds it away.
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
    """Close a feature — a move into the `done` CATEGORY, by whichever word.

    `done`, `obe`, or anything the project lists there: the close is the
    category, and what makes it a close rather than a plain move is the record
    stamp and the report. Touches the feature's own `status:` (plus `reviewed:`
    from `--review-record`) and nothing else. A story is closed by the story
    belt, by name — `agentic-sdlc close story <id>` — never by a command aimed
    at its feature: writing to files the caller did not name is the tool
    acting on its own initiative.

    The verb REPORTS what it saw — the stories not finished, with the word
    each holds — and refuses nothing on their account. What the tree is left
    holding is D5's question, and D5 asks it of the tree rather than of the
    caller.

    A feature that is ALREADY closed is not a short circuit. The flip is the
    idempotent part; the record stamp and the report each run on their own
    terms, so every run answers for the whole tree it was pointed at.
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
    # What it noticed, said out loud. Never a refusal: the caller asked for a
    # feature to be closed, and this is a fact about its stories.
    untouched = _unfinished(cfg, 'story', _story_states(cfg, fid))

    if rec:
        # The one thing checked about a record: the path RESOLVES. Whether the
        # prose under it is long enough is not this tool's question — the floor
        # it replaced refused an honest 15-byte "LGTM. Ship it.".
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
    if untouched:
        _ok(f'  {len(untouched)} story/ies not done and NOT touched: '
            f'{" ".join(untouched)} (close each through '
            f'`agentic-sdlc close story <id>`)')
    return 0


def cmd_feature(cfg: model.PmConfig, args: list[str]) -> int:
    if not args:
        raise Usage(USAGE)
    sub, rest = args[0], args[1:]
    # The TARGET state is validated against the declaration before ANY
    # dispatch — `done` and `reviewing` used to dispatch first, so a project
    # whose flow excluded them had the sanctioned tool writing the exact
    # undeclared status D4 reports. (The CURRENT state is still never gated
    # on — repair from any state stays.)
    _movable(cfg, 'feature', sub)
    # A move into the `done` CATEGORY is the close — the record stamp and the
    # report — by whichever word the project put there.
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
    pending: list[str] = []
    if model.category_of(cfg, 'milestone', to) == model.DONE_CATEGORY:
        mdir = model.milestone_dir(cfg, mid)
        assert mdir is not None
        pending = _unfinished(
            cfg, 'feature',
            ((ff.parent.name, model.field_of(ff, 'status'))
             for ff in model.feature_files(mdir)))
    _set_status(cfg, mf, to)
    _ok(f'milestone {mid}: {cur} -> {to}')
    _stamp_status(cfg, mf, cur, to, mid)
    # Reported, never refused — and D3 asks the same question of the tree, so
    # the state this leaves is not unwatched.
    if pending:
        _ok(f'  {len(pending)} feature(s) not done: {" ".join(pending)}')
    return 0


def _known_milestone_ids(cfg: model.PmConfig) -> list[str]:
    return sorted(mid or mdir.name
                  for mdir, mid in model.known_milestones(cfg))


def cmd_retire(cfg: model.PmConfig, args: list[str]) -> int:
    """Retire a shipped milestone: remove its directory, record its row.

    `pm init` seeds ROADMAP.md's table (`skills.ROADMAP_SEED`) and nothing
    used to fill it — a retirement was a hand-rolled `git rm -r` plus a
    hand-typed row, the two ever agreeing only by care. This is the one
    write that fills the table the tool itself mints.

    Refuses on exactly two impossibilities, both named: an id that resolves
    to no milestone, and no ROADMAP.md to append to. What it does NOT refuse
    on — the milestone not being `done`, or still holding a feature that
    isn't — is a fact about the tree, not a precondition; it is REPORTED the
    same way `milestone done` already reports its own unfinished features,
    below the line that says what moved. The caution that removed `pm prune`
    was about an AUTOMATIC sweep over every closed milestone, with no name
    in the command at all; this is the opposite shape — one milestone, named
    by the caller, on the command line, every time.

    `--dry-run` runs every decision (which id, which row, which notices) and
    prints them, then returns before the plan is ever built — the same
    "decide everything, write nothing" the whole-or-nothing verbs use, so a
    dry run is byte-identical to not having run it at all.
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
    index = cfg.roadmap / model.ROADMAP_DOC
    if not index.is_file():
        raise Refused(f'{cfg.rel(index)} does not exist — looked in '
                      f'{cfg.rel(cfg.roadmap)} (run `pm init` first; it seeds '
                      f'the table this command appends to)')

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
    # "Still open" is "not in `done`": a bug at `fixed` is work that remains
    # (the fix is not yet closed out), and a project's word for that is its
    # own. The 0.2.0 verb asked for the literal `open`, so a `fixed` bug was
    # silently not reported.
    open_bugs = sorted(
        name for name, _ in model.holds(
            cfg, 'bug',
            ((bf.stem, model.field_of(bf, 'status'))
             for bf in model.bug_files(mdir)),
            model.DONE_CATEGORY).blockers)
    if open_bugs:
        notices.append(f'{len(open_bugs)} bug(s) still open: '
                       f'{" ".join(open_bugs)}')

    date = (model.field_of(mfile, 'actual_date') if mfile.is_file() else '') \
        or datetime.now(timezone.utc).date().isoformat()
    summary = ' '.join(summary_words)
    row = f'| {canonical_id} | {name} | {date} | {summary} |'

    existing = model.read_raw(index)
    eol = '\r\n' if '\r\n' in existing else '\n'
    padded = existing if not existing or existing.endswith(('\n', '\r')) \
        else existing + eol
    new_index_text = padded + row + eol

    if dry_run:
        _ok(f'[dry-run] would remove {cfg.rel(mdir)}')
        _ok(f'[dry-run] would append to {cfg.rel(index)}: {row}')
        for n in notices:
            _ok(f'  noticed: {n}')
        return 0

    plan = apply.Plan()
    plan.delete_tree(mdir, label=cfg.rel(mdir))
    plan.overwrite(index, new_index_text, newline='', label=cfg.rel(index))
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
    _ok(f'milestone {mid}: retired — {cfg.rel(mdir)} removed, '
        f'{cfg.rel(index)} carries the row')
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
    """Re-parent a story to a different feature. Whole, or not at all.

    Two things happen — the file is renamed under the target feature's
    `stories/`, and its `id`/`feature`/`milestone` are rewritten to match —
    and a caller must never see only one of them: an id that still claims
    the old feature after the file moved, or a file sitting in the old
    feature's directory with a new feature's id, is worse than either half
    alone. Everything is DECIDED — the rename's every obstruction — before
    either byte is written, so a decided obstruction (a same-named story
    already at the destination, an unwritable target directory, …) refuses
    with nothing touched: `sf` is unread past resolution, `dest` is never
    created. Only once that decision comes back clean does the frontmatter
    get rewritten (still at the OLD path, through `model.set_fields` — one
    read, one write, all three keys together) and the file renamed last, so
    the one failure mode neither `decide()` nor a permissions check can rule
    out — an OS failure between the two writes — is reported by name rather
    than left to look like a clean move.
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

    dest = target_ff.parent / 'stories' / sf.name
    # `stories/` is minted on first write, never scaffolded (`pm new` mints
    # no empty directory) — so the target feature's OWN first story lands
    # here with no `stories/` to rename into yet. `Plan.move` renames; it
    # does not `mkdir -p` a missing destination parent the way OVERWRITE
    # does, so that has to be its own decided, idempotent step.
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
    # The same census discipline `pm list` already has: an empty print at
    # exit 0 is what a wrong `roadmap_dir`, an emptied tree, and a typo'd
    # milestone id all used to produce, and rule 4 says a scan that saw
    # nothing must say so rather than pass in silence.
    known = model.known_milestones(cfg)
    if not known:
        raise Usage(f'{cfg.roadmap_dir} holds no milestone at all — nothing to '
                    f'report, so this is a scope problem (wrong [pm] '
                    f'roadmap_dir, or an empty tree?), not a status')
    if only and only not in {mid for _, mid in known}:
        ids = sorted(mid for _, mid in known if mid)
        raise Usage(f'{only!r} is not a milestone in {cfg.roadmap_dir} '
                    f'({" ".join(ids)})')
    for mdir, mid in known:
        mfile = mdir / model.MILESTONE_DOC
        if only and only != mid:
            continue
        print(f'milestone {mid:<10} [{model.field_of(mfile, "status")}]')
        rows = []
        for ffile in model.feature_files(mdir):
            view = model.read_feature(cfg, ffile)
            # Drift markers reuse the SAME predicates the gate runs on, so the
            # report and the gate can never describe drift differently.
            reason = (model.drift_dangling_record(cfg, view.fid)
                      or model.drift_stalled(cfg, view))
            drift = f'  <DRIFT: {reason}>' if reason else ''
            # Numbered phases first, then the named ones, then unphased — the
            # reading order of the milestone's own board, and `model.phase_key`
            # is the one spelling of it (the execution list sorts by it too).
            rows.append((model.phase_key(view.phase), view.phase, view,
                         f'  feature {view.fid.partition("/")[2]:<40} '
                         f'[{view.status:<8}] stories {view.done_n}/{view.total} done{drift}'))
        if not rows:
            continue
        buckets: list[str] = []
        for _, phase, _, _ in sorted(rows, key=lambda r: r[0]):
            if phase not in buckets:
                buckets.append(phase)
        # A milestone that declares no phases prints exactly as it always did:
        # the lone `unphased` bucket suppresses its own header.
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
    """One tab-separated line per story, filtered. A view over facts.

    `pm status` answers "what is the whole tree doing" and prints 165 lines on
    one consumer. The question a person actually arrives with is "what is open
    right now", and there the real answer was two stories. This is that filter
    and nothing more — no ranking, no scoring, no verb that picks THE next
    thing, because a tool with an opinion about your priorities is the thing
    this release removes.

    Rows go to stdout so the output pipes into `cut`/`grep`/`wc` unchanged; the
    census goes to stderr, so a run that matched nothing is still
    distinguishable from a run that SCANNED nothing (a wrong `roadmap_dir`).
    """
    pairs, rest = _take_flags(args, ('--status', '--owner', '--milestone'))
    if rest:
        raise Usage(USAGE if not rest[0].startswith('-')
                    else f'unknown flag {rest[0]!r}')
    statuses: set[str] = set()
    owner = ''
    milestone = ''
    for flag, value in pairs:
        if flag == '--status':
            statuses |= {v for v in value.split(',') if v}
        elif flag == '--owner':
            owner = value
        else:
            milestone = value
    for status in sorted(statuses):
        _movable(cfg, 'story', status)

    # Enumerated ONCE, and used both to refuse a typo and to filter. A
    # `--milestone` naming nothing used to print `0 of 0` at exit 0, which is
    # what an emptied milestone and a wrong `roadmap_dir` also print. The ids
    # are right there in the tree, so the set gets named the way `--status`
    # already names its own.
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
                if owner and who != owner:
                    continue
                shown += 1
                print(f'{model.unquote(model.field_of(sfile, "id"))}\t{status}'
                      f'\t{who or "-"}\t{view.fid}')
    print(f'[pm] {shown} of {scanned} story/ies', file=sys.stderr)
    return 0


def _grain_file(cfg: model.PmConfig, gid: str) -> Path:
    """Resolve any grain id — milestone, feature, story or bug — to its file."""
    if '/bugs/' in gid:
        mid, _, rest = gid.partition('/bugs/')
        # The resolution twin of _check_slug's creation guard. bugs/ is
        # walked recursively, so nested slugs are legal — but a `..` (or an
        # empty) segment would resolve OUTSIDE bugs/ and hand the status
        # write to a sibling grain, the cross-grain write the docstring
        # above promises cannot happen.
        parts = rest.replace('\\', '/').split('/')
        if not rest or any(p in ('', '.', '..') for p in parts):
            raise Usage(f'no bug resolves from id {gid!r} '
                        f'(a bug slug holds no dot or empty segments)')
        mdir = model.milestone_dir(cfg, mid)
        bf = (mdir / 'bugs' / f'{rest}.md') if mdir else None
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
    """Set one frontmatter field. The point is that a tool does this, not a regex.

    Every hand-rolled `sed` over frontmatter is a chance to rewrite a line
    ending, drop a field, or move a `status:` that had preconditions on it.
    """
    if len(args) != 3:
        raise Usage(USAGE)
    gid, key, value = args
    if not key or not key.replace('_', '').isalnum():
        raise Usage(f'{key!r} is not a frontmatter key')
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
    """Re-render every execution list from the tree.

    The list a milestone/feature shows is generated, never authored — which is
    what makes it safe to have one at all. `--check` reports without writing
    (the same predicate V6 gates on).
    """
    check = '--check' in args
    for a in args:
        if a != '--check':
            raise Usage(f'unknown flag {a!r}')
    from agentic_sdlc.repo.pm import execlist
    # Zero grains refuses in BOTH modes. `--check` used to print
    # `all 0 execution list(s) current` at exit 0 over an empty or
    # mis-scoped tree — a gate that scanned nothing, passing.
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


# The one line of prose that says whose the transitions KEY SET is. Spelled
# once, printed by the plain renderer and carried by `--json`, because a reader
# who only ever sees one of the two must still see it (plan review finding P6:
# a table presented as pure project declaration would be the engine's opinion
# with a config file in front of it — what makes it honest is that the keys are
# a PUBLISHED vocabulary the project selects from).
PUBLISHED_STEPS_NOTE = (
    'the keys a [pm.transitions.<kind>] table may use. The key set is the '
    'ENGINE\'s: these are the step names this package registers in '
    'conveyor/steps.py, read from that registry rather than restated here, '
    'and a project SELECTS from them and cannot invent one — the same shape '
    '`[<operation>] steps` already works in')


def _published_steps() -> dict[str, tuple[str, ...]]:
    """Every conveyor step name this package registers, by operation.

    READ FROM THE REGISTRY, never re-listed. A literal here would be a second
    spelling of `conveyor/steps.py`'s `REGISTRIES`, and the whole value of
    printing it at a pin bump is that it cannot disagree with what the belt
    will actually accept. The registry dicts are insertion-ordered, so the
    names come out in the order the shipped lists walk them.

    Imported INSIDE the verb, like `execlist` and `validate` above: `pm` runs
    dozens of times a day off the story belt, and `conveyor.steps` is the
    largest module in the package. `conveyor.steps` imports `pm.model`, never
    `pm.cli`, so there is no cycle — but a module-level import here would put
    the belt's whole import cost on `pm set`.
    """
    from agentic_sdlc.repo.conveyor import steps as _steps
    return {operation: tuple(_steps.registry_for(operation))
            for operation in sorted(_steps.REGISTRIES)}


def cmd_vocabulary(cfg: model.PmConfig, args: list[str]) -> int:
    """Print what this version's declared surface IS, machine-readably too.

    Its audience is the pin bump. This toolkit ships a shape, a project bumps
    its pin, and then has to see what changed and decide — so the states a
    grain may hold, the flow the project declared, the conveyor step names a
    transitions table may key on, and the rule ids `[pm] checks` may name all
    have to be readable FROM the tool rather than scraped out of help text or a
    changelog. That is the same need `check pm`\'s roster refusal serves from
    the other side, and the reason this verb keeps running when `[pm] checks`
    names an id this release retired.

    THIS DOCSTRING USED TO SAY "there are no TRANSITIONS to print". Phase 6
    falsified it: `[pm.states.<kind>]` and `[pm.transitions.<kind>]` are read
    every run (`model._load_flows`) and there is no fallback behind them. What
    survives unchanged is the narrower true statement — there is no EDGE graph.
    `[pm.transitions]` maps a conveyor STEP to a state, never a state to a
    state, so nothing here decides which state may follow which and `check pm`
    still reports an inconsistent END STATE. (Plan review finding P6.)

    IT REPORTS AN ABSENT FLOW RATHER THAN REFUSING IT, which is why it reads
    `cfg.flows` directly and never goes through `model.flow_of`. `flow_of` is
    the WORKFLOW refusal — a verb that creates, moves or locates work cannot
    proceed on states the project never declared. This verb is the one you run
    to find out WHAT TO DECLARE, and a discovery verb that refuses until you
    have already discovered the answer is a closed loop. So an undeclared tree
    gets the absence named and the exact bytes `init` would write.
    """
    as_json = '--json' in args
    for a in args:
        if a != '--json':
            raise Usage(f'unknown flag {a!r}')
    # THE FLAT SETS STAY, and the lines they print are unchanged (hard rule 6).
    # They are the flow's ORDER — category-major, then the project's own list
    # order — which is what `check pm` D4 names when it reports an undeclared
    # word and what a conveyor status step compares in. Empty for a tree that
    # declared nothing: printing the seed there would be the runtime fallback
    # this reader does not have.
    grains = {
        'milestone': cfg.milestone_states,
        'feature': cfg.feature_states,
        'story': cfg.story_states,
        'bug': cfg.bug_states,
    }
    published = _published_steps()
    close_note = ('a feature close is a move into the `done` CATEGORY, by '
                  'whichever word this project lists there: `pm feature '
                  '<done-state> <id>` stamps `reviewed:` and reports the '
                  'stories not in `done`, never refuses on them, and touches '
                  'no story file — the story belt closes each by name')
    transitions_note = ('there is no EDGE graph — any state in a grain\'s own '
                        'set is reachable directly, and `check pm` reports an '
                        'inconsistent END STATE. [pm.transitions.<kind>] maps '
                        'a conveyor STEP to the exact state that step writes, '
                        'never a state to a state')
    if as_json:
        print(json.dumps({
            'categories': list(model.CATEGORIES),
            'flow_kinds': list(model.FLOW_KINDS),
            # The absence is a VALUE in the payload, not a missing key: a
            # consumer diffing two pin versions has to be able to tell "this
            # tree declares nothing" from "this release dropped the field".
            'flow_declared': bool(cfg.flows),
            'grains': {
                g: {
                    'states': list(states),
                    'flow': (None if g not in cfg.flows else {
                        'categories': {
                            cat: list(cfg.flows[g].by_category.get(cat, ()))
                            for cat in model.CATEGORIES},
                        'order': list(cfg.flows[g].order),
                        'transitions': dict(cfg.flows[g].transitions),
                    }),
                }
                for g, states in grains.items()},
            'published_steps': {op: list(names)
                                for op, names in published.items()},
            # The seed travels in EVERY payload, declared or not. Declared, it
            # is what a pin bump diffs its own declaration against; undeclared,
            # it is what `init` would write. One key, both readings.
            'seed': model.render_seed(),
            'notes': {
                'transitions': transitions_note,
                'published_steps': PUBLISHED_STEPS_NOTE,
                'states': 'the flat per-kind `states` list is the declared '
                          'flow\'s order — category-major, then the project\'s '
                          'own list order — and is empty for a tree that '
                          'declared nothing; `flow` is what the project '
                          'declared in [pm.states.<kind>], and every question '
                          'the engine asks is asked of a category',
                'feature_done': close_note,
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
    print('declared — the categories every state maps into, and the transitions')
    print('a conveyor step reads. The category set is closed and is exactly')
    print(f'{" ".join(model.CATEGORIES)}.')
    print()
    if not cfg.flows:
        print('This tree declares NO flow: [pm.states.*] is not in')
        print('devkit.toml, and there is no default behind it — the states and')
        print('the transitions are how THIS project works (hard rule 5).')
        print('Every verb that creates, moves or locates work refuses by name')
        print('until it is there. `agentic-sdlc pm init` writes exactly this,')
        print('appending to a devkit.toml it did not create:')
        print()
        # INDENTED by two, so nothing here is mistaken for the tree's own
        # config, and `render_seed()` is the ONLY source of the bytes — the
        # verb that tells you what to declare cannot show you a table the
        # writer does not write.
        for line in model.render_seed().splitlines():
            print(f'  {line}' if line else '')
        print()
    else:
        cat_width = max(len(c) for c in model.CATEGORIES)
        for kind in model.FLOW_KINDS:
            # Indexed, never `.get`: `_load_flows` refuses a PARTIAL
            # declaration by name, so `cfg.flows` is all four kinds or none.
            # A defensive default here would print an empty flow for a tree
            # the reader had already decided it could not read.
            flow = cfg.flows[kind]
            print(f'[pm.states.{kind}]')
            for category in model.CATEGORIES:
                states = flow.by_category.get(category, ())
                print(f'  {category:<{cat_width}}  {" ".join(states)}')
            print(f'[pm.transitions.{kind}]')
            if not flow.transitions:
                print('  (this project declares none)')
            for step, target in flow.transitions.items():
                print(f'  {step} -> {target}')
            print()
    # WRAPPED, not re-spelled. The three notes are single strings so that the
    # plain renderer and `--json` cannot say different things; `textwrap` is
    # what keeps that from printing a 300-column line (stdlib, rule 1).
    step_width = max(len(op) for op in published)
    print(textwrap.fill(f'published steps — {PUBLISHED_STEPS_NOTE}.', width=76))
    for operation, names in published.items():
        # `release` ships 21 names; unwrapped that is a 280-column line, and a
        # reader who has to scroll sideways to see the key set does not read it.
        # `break_on_hyphens=False` because every step name IS hyphenated:
        # the default split `changelog-unreleased-nonempty` across two lines,
        # which is a name a reader cannot paste into `[pm.transitions.*]`.
        print(textwrap.fill(' '.join(names), width=76,
                            break_on_hyphens=False, break_long_words=False,
                            initial_indent=f'  {operation:<{step_width}}  ',
                            subsequent_indent=' ' * (step_width + 4)))
    print()
    for note in (transitions_note, close_note):
        print(textwrap.fill(f'{note[0].upper()}{note[1:]}.', width=76))
    print()
    print(f'rules  {" ".join(model.KNOWN_CHECKS)}')
    return 0


def cmd_validate(cfg: model.PmConfig, args: list[str]) -> int:
    """Structural + referential integrity. The same predicates `check pm` runs."""
    if args:
        raise Usage(USAGE)
    # Same placement as the gate's: `pm validate` is the other reader a stale
    # rule id would silently narrow, and the only two that must refuse it.
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
# `caused_by:` — the feature whose change produced a bug. The FIELD name and
# the FLAG that sets it, spelled once each: `caught_in:` says which milestone
# found the bug, this says which feature made it, and an escape needs both.
CAUSED_BY = 'caused_by'
CAUSED_BY_FLAG = '--caused-by'


def _caused_by(cfg: model.PmConfig, pairs: list[tuple[str, str]]) -> str:
    """The `--caused-by` value, proven to name a feature that EXISTS. Or ''.

    RESOLUTION is the whole gate, and it runs before anything is written. A
    traversal, an absolute path, a glob, a backslash, a whitespace segment, a
    name longer than the filesystem takes, a story id and a milestone id all
    name no feature, so all of them exit 2 with the value in the message —
    `feature_file` refuses the first four through `segment_is_literal` and the
    filesystem answers the rest. There is no second grammar to keep in sync
    with the resolver, which is the only way the two cannot disagree.

    ANY status resolves: `done`, `building`, `planning` alike. What counts as
    an ESCAPE is the report's question (a bug caused by a CLOSED feature); this
    verb records which change produced the bug and holds no opinion about it.
    Refusing a non-`done` feature here would make the record unwritable in the
    one case it is most often known — during the build that caused it.

    An OSError is False, never a traceback: a value the filesystem itself
    refuses names no feature either, and `pm new bug` came out as a traceback
    or as a refusal depending on the interpreter before `_exists` settled the
    same question for paths (see it).
    """
    value = ''
    for _, raw in pairs:
        # Both spellings refuse an empty value the same way: `--caused-by=`
        # storing '' would file the bug with the field silently unset, at
        # exit 0, after the caller asked for it.
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
        # A template the project cannot even decode is a REFUSAL, not a
        # traceback: rule 6 reserves exit 1 for findings a consumer's hook can
        # print, and a stack trace is not one.
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
    # `new milestone` and `new feature` are IDEMPOTENT: run against an existing
    # grain they fill the missing slots and leave every existing byte alone.
    # That is how a consumer migrates a tree of 22 milestones and 136 features
    # to the canonical shape, which is why the name is optional there — the
    # name only ever mints the directory, and the directory already exists.
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
        # The milestone comes from the FEATURE's own frontmatter — single
        # source, never re-derived from the id string.
        mid = model.field_of(fdir / model.FEATURE_DOC, 'milestone')
        # The FILE may carry an ordering prefix (`01-`); the ID never does.
        # Stamping the prefix into `id:` scaffolded a story that `pm validate`
        # V2 rejected against that same file's path — the tool minting the
        # drift its own gate reports.
        sid_slug = model.story_slug_of(cfg, slug)
        if not sid_slug:
            raise Refused(f'story slug {slug!r} is an ordering prefix and '
                          f'nothing else — the number sequences the build, the '
                          f'slug after it is the id')
        sf = fdir / 'stories' / f'{slug}.md'
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
        # Resolved BEFORE the slug guard and before any write: a bug filed with
        # an unresolvable cause is a bug filed with a lie in it, and the file
        # that would carry it is not created at all.
        cause = _caused_by(cfg, pairs)
        mid, slug = rest[0], _check_slug('bug slug', rest[1])
        mdir = model.milestone_dir(cfg, mid)
        if mdir is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        bf = mdir / 'bugs' / f'{slug}.md'
        if _exists(bf):
            raise Refused(f'bug {mid}/bugs/{slug!r} already exists')
        # Bugs anchor to where they were CAUGHT, not where they get fixed —
        # the file path preserves the catch history.
        body = templates.render(
            templates.load(cfg, 'bug'),
            {'id': f'{mid}/bugs/{slug}', 'milestone': mid, 'slug': slug})
        _mint(cfg, bf, body)
        _ok(f'created {cfg.rel(bf)}')
        if cause:
            # Stamped through `set_field` rather than a template placeholder,
            # so a project that overrides bug.md still gets the field it asked
            # for: `set_fields` rewrites the key in place if the template
            # carries it and inserts it before the closing fence if not. A
            # template with no frontmatter at all can hold no field, and that
            # is said out loud rather than dropped at exit 0.
            if not model.set_field(bf, CAUSED_BY, cause):
                raise Refused(
                    f'{cfg.rel(bf)} was created, but {CAUSED_BY}: could not be '
                    f'written into it (the bug template has no frontmatter '
                    f'block) — set it with `pm set {mid}/bugs/{slug} '
                    f'{CAUSED_BY} {cause}`')
            _ok(f'{mid}/bugs/{slug}: {CAUSED_BY} {cause!r}')
        return 0
    raise Usage(USAGE)


# --- decide -------------------------------------------------------------------
def _decision_log(cfg: model.PmConfig, gid: str) -> tuple[Path, str]:
    """(the decisions.md of the grain `gid` names, its text — MINTED if absent).

    The log is minted on FIRST WRITE, from the same template `pm templates`
    copies out, rather than at scaffold time. An empty decisions.md in every
    grain is sprawl the tool made: 204 such files, ~1,900 lines, a quarter of
    one consumer's PM tree, minted by the verb that exists to stop sprawl.

    Nothing is written here — the body comes back and the caller writes once,
    so a refusal further down still leaves the grain byte-identical.
    """
    depth = gid.count('/')
    gdir = (model.milestone_dir(cfg, gid) if depth == 0 else
            model.feature_dir(cfg, gid) if depth == 1 else None)
    if depth > 1 or '/bugs/' in gid:
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
    """Append one dated, ordinal-stamped heading. The prose is the author's.

    The two things an author writing this by hand gets wrong are the DATE and
    the ORDINAL — a duplicate `D7` in one log is invisible until somebody cites
    it — so the verb stamps both and stops. It does NOT impose a field schema:
    the four-field one this replaced produced zero conforming entries across a
    consumer's 158 decision logs and 320 hand-written headings, so what it
    actually gated was whether anyone used the verb at all.

    The title is every remaining argv token, joined with one space — so a `;`
    a caller ESCAPED (`a\\; b`, two tokens) rebuilds intact, and a `;` a caller
    QUOTED arrives whole and is written verbatim. A `;` a caller left BARE was
    consumed by their own shell before this process started; what that leaves
    behind is refused rather than written, as far as it is visible from here.

    Refuses WHOLE: every path out of here that is not a write leaves the log
    byte-identical.
    """
    if not args:
        raise Usage(USAGE)
    gid, title = args[0], ' '.join(args[1:]).strip()
    if gid.startswith('-'):
        raise Usage(f'unknown flag {gid!r}')
    if not title:
        raise Usage('decide needs a title — the heading is the entry')
    if title.split()[0].startswith('--'):
        # The one caller who leads the title with a flag is a caller speaking
        # the retired four-field interface — writing their flag soup into a
        # durable log at exit 0 would be a quiet lie.
        raise Usage(f'{title.split()[0]!r} looks like a flag — decide takes '
                    f'none: everything after the grain id is the heading')
    if '\n' in title or '\r' in title:
        raise Refused('a heading is one line — put the reasoning under it')
    if title[-1] in SHELL_SPLITTERS:
        # The residue of a shell split. `make pm ARGS="decide <id> a; b"`
        # expands UNQUOTED, so the consumer's shell cuts at the `;`, hands this
        # process `a`, and runs `b` as a command of its own — which is how one
        # consumer's log ended up carrying two half-headings. A cut that lands
        # BETWEEN words is invisible from in here and always will be; a cut
        # that leaves the operator dangling on the end is not, and that is the
        # one shape this can refuse instead of writing a truncated heading.
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
    # The heading is on disk; the row records that it is. `decisions.md` is
    # per-grain and the ledger is per-milestone (D6), so a feature's decision
    # lands in its milestone's file, named by the grain it was made about.
    _stamp(cfg, log, ledger.decision_row(gid, eid, title))
    return 0


# --- ledger -------------------------------------------------------------------
# `pm ledger record` is the ONE way a dispatch's cost reaches the tree (D4): the
# installed SubagentStop/Stop hooks call it with the transcript path, and a hand
# run files the row for a dispatch no hook saw. Chris, 2026-09-03: *"the ledger
# is actually very very simple. It shouldn't judge or infer or even guard really
# anything … It just timestamps transitions and stamps whatever hook data.
# Judgement/inference is left to the caller."*
#
# So this verb copies what the transcript holds, omits what it lacks, and labels
# nothing. What it DOES refuse is input hygiene on its own surface (SDLC § 5) —
# a path that is not a file, a line that is not JSON, a number that is not a
# number, an unknown `--event`, a `--grain` that resolves to nothing — plus the
# one question it genuinely cannot answer: WHICH milestone ledger, when two are
# building. It says so and stops rather than picking.
LEDGER_FLAGS = ('--from-transcript', '--event', '--agent-id', '--agent-type',
                '--session-id', '--grain', '--tokens-in', '--tokens-out',
                '--tool-calls', '--duration-s', '--duration-ms',
                '--gate', '--verdict',
                '--census')

# The three record FORMS, by the flag that opens each, and the flags each one
# accepts. Named as a table rather than checked ad hoc because the failure this
# prevents is silent: a `--census` on the transcript form, or a `--tokens-in`
# on the gate form, would be parsed and then dropped, and a flag a caller wrote
# that changed nothing is the write-side sin with a shrug on it.
GATE_FLAGS = ('--gate', '--verdict', '--duration-ms', '--census')
GATE_ONLY_FLAGS = ('--verdict', '--census')

DIGITS = frozenset('0123456789')

# `--json` is the one ledger flag that takes no value, so it never reaches
# `_take_flags` (which would eat the id after it).
JSON_FLAG = '--json'


def _count_flag(flag: str, raw: str) -> int:
    """A non-negative integer, or exit 2. `int()` is not the test.

    `int()` accepts `-3`, ` 7 `, `1_0` and Unicode digits like `٣`, and a token
    count is a decimal integer written by a machine. A number this verb cannot
    read is a refusal and never a zero: zero is a MEASUREMENT, and the row it
    would land in is indistinguishable afterwards from a real one (hard rule 4).
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
    """The milestone directory whose ledger `subject` belongs to (D6).

    The one thing `record` cannot work out for itself, and the default for
    `report`. Exactly one milestone in `in_progress` is the answer; none and
    several are both refusals that NAME the situation, because a verb that
    picked would attribute a real dispatch's cost to whichever milestone
    sorted first and nothing downstream could detect it. Decision D5: the
    engine never chooses among several; a project that wants one narrows its
    own declaration.
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
    """The ACTIVE tree's live state, verbatim, at the instant of the row (D3).

    Every id the frontmatter carries, sorted, empty lists when empty — no
    ranking, no single "most likely" grain, no `?`. Attribution is the report's
    job and every candidate is on the row, which is what makes a report's rule
    re-derivable later when the question changes.

    The walkers are the ones `check pm` and `pm status` use, so `zz_archive/` is
    excluded here for the same reason it is there: an archived milestone is not
    something a dispatch can have been working on. A grain whose frontmatter
    carries no `id:` is left out — an unnamed grain cannot be named.

    TWO KEY FAMILIES, one row (decision D7 — "keep and extend").

    The CATEGORY keys — `milestones_in_progress`, `features_in_progress`,
    `stories_in_progress` — are what the row MEANS: every grain of that kind
    whose status is in this project's `in_progress` category, whatever the
    words. `pm ledger report` attributes a dispatch by them.

    The FROZEN keys — `milestones_building`, `features_building`,
    `features_review`, `stories_wip`, `stories_review` — are **DEPRECATED,
    kept for one reason and removed at the next major**: they are inside JSONL
    rows already written in every consumer tree, and rows are never rewritten.
    They match the SEED's words by name (`building`, `reviewing` — the one
    place outside the seed this package still compares against a word, dated
    2026-09-05 and named in `tests/test_pm_flow.py`'s census as D7's
    exception). A reader of an old row — this package's own `report` included
    — still finds them; a project with a renamed vocabulary records empty
    frozen lists beside full category lists, which is a true statement about
    what each key can spell.
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
    """Append one row — a dispatch/session from a transcript or by hand, or a GATE.

    The forms are exclusive because they answer different questions from
    different sources, and a run naming two would leave which one won as an
    implementation detail sitting in a durable log.

    Every number in the hand form is OPTIONAL and an omitted one is an omitted
    KEY, never a zero — `--tool-calls` unset means nobody counted, and a `0` in
    that slot would read forever after as a dispatch that called no tool. The
    gate form keeps that rule for `--census` and breaks it for `--duration-ms`
    on purpose: a gate row with no duration is the write-only column this
    feature's own risk register condemns, so it refuses instead.
    """
    pairs, rest = _take_flags(args, LEDGER_FLAGS, noun='a value')
    if rest:
        raise Usage(f'ledger record takes flags only, not {" ".join(rest)!r}')
    flags = dict(pairs)
    # Presence, not truth: `--gate=''` names the form and is refused BY the
    # form, rather than falling through to "needs --from-transcript".
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
        # Only ever the flag. The transcript does not carry the agent TYPE, so
        # reading one out of it would be inference wearing a field's name.
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
    """The gate form: what ONE gate run cost, as one row.

    The caller is a shell wrapper on the path of every gate in every consumer,
    and it DISCARDS this exit code — a ledger that cannot be written is never a
    gate failure. That is exactly why nothing here may exit 0 having written
    nothing: a verb that lied about recording would make the discarded failure
    unauditable, and the missing rows would read as gates that never ran.
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
    # MILLISECONDS here and SECONDS on the dispatch form above, deliberately.
    # A dispatch is a model turn and is never sub-second; fourteen of twenty
    # measured GATES are, and the narrow-vs-wide pair the story belt rests on
    # is 0.9 s against 154 s — which an integer-second row records as 0 (ratio
    # undefined) or rounds to 1 (154x for a measured 170x).
    duration = _count_flag('--duration-ms', flags['--duration-ms'])
    # ABSENT, never 0. The same gate is legitimately slower on a bigger tree,
    # so the census is what stops a duration reading as a regression — and a
    # `0` there is the zero-file census hard rule 4 calls a cardinal sin.
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
    """A make-target name, or exit 2 — the string story 03's report JOINS on.

    `fullmatch`, never `match`: `$` matches BEFORE a trailing newline, so
    `TARGET.match('check\\n')` SUCCEEDS, and a name carrying one would write a
    forged second row into a file whose whole contract is one row per line.
    """
    if raw and len(raw) <= ledger.GATE_NAME_MAX and ledger.GATE_NAME.fullmatch(
            raw):
        return raw
    raise Usage(f'--gate takes a make-target name '
                f'([A-Za-z0-9][A-Za-z0-9._+-]*, at most '
                f'{ledger.GATE_NAME_MAX} characters), not {raw!r}')


def _gate_verdict(flags: dict[str, str]) -> str:
    """One of the closed set, or exit 2.

    A gate's console line is prose — `PASS (12 files)`, `FAIL — 3 findings` —
    and a durable column is not: free text there gives one outcome five
    spellings, and a report that groups by it counts none of them twice.
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
    """Where a gate row lands, or a REFUSAL naming which of the two it was.

    Exit 1, not 2: neither of these is a bad argument. There is nothing to
    record INTO, which is a precondition, and the caller (a gate) can tell a
    "your tree has no milestone building" from a "you spelled that wrong"
    without parsing either message. Two milestones building keeps
    `_building_ledger_dir`'s own answer, so the ambiguity has ONE wording
    wherever it is met.
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
    """Sum the transcript at `source`, and take its ids only where a flag is silent.

    The path is used as given — the hook hands over an absolute one under
    `~/.claude/projects/`, outside the repo entirely, so there is no tree to
    contain it to. It must be an existing FILE; a directory or a missing path is
    a refusal rather than an empty summary.
    """
    path = Path(source).expanduser()
    if not path.is_file():
        raise Usage(f'--from-transcript {source!r} is not a file')
    try:
        summary = ledger.transcript_summary(ledger.records_of(path))
        # A second pass rather than a second copy: the summary streams, and the
        # ids are only wanted when the caller did not state them.
        for name, key in (('session_id', 'sessionId'), ('agent_id', 'agentId')):
            if not flags.get(f'--{name.replace("_", "-")}'):
                summary[name] = ledger.id_from_records(
                    ledger.records_of(path), key)
    except ledger.TranscriptError as err:
        raise Usage(f'{err}') from err
    return {k: v for k, v in summary.items() if v is not None}


def _by_hand(cfg: model.PmConfig, grain: str, flags: dict[str, str]) -> dict:
    """The hand form's fields. `--grain` must RESOLVE; a typo would be a lie.

    Every other verb here resolves an id before it writes, and a ledger row is
    the one write whose subject nothing downstream can check — a report joining
    on `grain` would carry the typo forever and read it as a grain that cost
    something. `_grain_file` is the same resolver `pm get`/`pm set` use, so
    traversal, globs, absolute paths and empty segments refuse here exactly as
    they refuse there.
    """
    path = _grain_file(cfg, grain)
    usage = {}
    for key, flag in (('input', '--tokens-in'), ('output', '--tokens-out')):
        if flag in flags:
            usage[key] = _count_flag(flag, flags[flag])
    fields: dict[str, object] = {'grain': _ledger_id(path, grain)}
    if usage:
        # Only the keys the caller gave. `cache_creation`/`cache_read` are
        # ABSENT rather than 0: nobody counted them, and a 0 would say they were
        # counted and were none.
        fields['usage'] = usage
    for key, flag in (('tool_calls', '--tool-calls'),
                      ('duration_s', '--duration-s')):
        if flag in flags:
            fields[key] = _count_flag(flag, flags[flag])
    return fields


def _grain_kind(gid: str) -> str:
    """Which vocabulary an id answers to, by the shape `_grain_file` resolves by.

    The kind, not the state: `ledger.ends_grain` owns WHICH states end a
    grain (its kind's `done` category), so a report and this verb cannot come
    to different answers about where one finished.
    """
    if f'/{model.BUGS_DIR}/' in gid:
        return ledger.GRAIN_BUG
    depth = gid.count('/')
    return 'milestone' if depth == 0 else 'feature' if depth == 1 else 'story'


def cmd_ledger_show(cfg: model.PmConfig, args: list[str]) -> int:
    """One grain's rows, oldest first, with the seconds between status rows.

    The human form is one line per row and nothing else: `ts`, `kind`, and for a
    status row `from -> to` plus the seconds since that grain's PREVIOUS status
    row — which is D8's "time in each state", by subtraction over raw rows. The
    total line prints only when the grain actually reached its vocabulary's last
    state; a grain still in flight gets no total, because a running clock is not
    a duration.

    No rows is exit 0. "This grain has no rows" is a FACT about the tree — a
    grain nothing has happened to yet — and answering a true question with an
    error code would make every caller treat silence as breakage.
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
    # Both spellings: the id the caller typed, and the id the FILE claims —
    # which is the one `_stamp` wrote into every row.
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
    """Whole seconds between two rows' stamps, or None when either will not parse.

    A row whose `ts` is not a timestamp still PRINTS — it is a fact somebody
    wrote — but it contributes no arithmetic, because a fabricated interval is
    worse than a missing one.
    """
    if earlier is None:
        return None
    start = ledger.parse_ts(earlier.data.get('ts'))
    end = ledger.parse_ts(later.data.get('ts'))
    if start is None or end is None:
        return None
    return int((end - start).total_seconds())


# --- ledger report ------------------------------------------------------------
# The ledger records and never judges; the REPORT is the caller D3 and D4 left
# the judgement to, and everything it may do is arithmetic over rows that are
# already on disk — sum, count, subtract, group. What it may not do is D5: no
# size weight (`size:` is a column, never a divisor), no dollar figure, no
# score, no label. It reads and never writes, and nothing in it exits non-zero
# on a NUMBER: the one refusal on content is a ledger line that will not parse,
# which is the same refusal `show` already makes, by line number.
REPORT_SUBJECT = 'this report'
REPORT_HINT = ', or name one: `pm ledger report <milestone-id>`'

# `--from <rev>` reads the milestone out of git instead of off disk (D6). The
# rev is always the CALLER's: `ROADMAP.md`'s prune log is where a reader finds
# the anchor in projects that keep one, and this verb never searches history
# for it — nothing is inferred.
FROM_FLAG = '--from'


def cmd_ledger_report(cfg: model.PmConfig, args: list[str]) -> int:
    """One milestone's rows, added up per grain. See report.py for the rules.

    The milestone is the building one by default and an explicit id otherwise,
    resolved by `_grain_file` — the resolver every other verb here uses, so
    traversal, globs, absolute paths and empty segments refuse identically. A
    milestone with no `ledger.jsonl` prints one line and exits 0: nothing has
    been recorded for it yet, which is a fact about the tree and not an error.

    `--from <rev>` reads the same files out of GIT at that rev instead of off
    disk (D6: a retired milestone's history is git's job) — the ledger, the
    milestone document, every feature, story and bug under it, and the review
    records the features point at, each through `git show <rev>:<path>`.
    Nothing is written, nothing is checked out and the index is never touched;
    the rev is the caller's and is never searched for. The report itself is the
    SAME `report.build` the live path runs, over `report.GitSource` instead of
    `report.DiskSource` — the heading says `— at <rev>` and `--json` carries a
    `rev` key so the two cannot be mistaken for one another, and nothing else
    about the output differs, because nothing else about it is computed
    differently.
    """
    as_json = JSON_FLAG in args
    rest = [a for a in args if a != JSON_FLAG]
    # WHETHER `--from` was given and WHAT it was given are two questions, and
    # collapsing them is how `pm ledger report 0.23.0 --from` printed a live
    # report and exited 0: the value came back empty, the empty read as "no
    # rev", and the verb answered a question about the working tree that the
    # caller had asked about history. `given` is the switch; `rev` is only the
    # value, and an empty one is refused by `check_rev` rather than defaulted.
    given = FROM_FLAG in rest
    rev = ''
    if given:
        if rest.count(FROM_FLAG) > 1:
            raise Usage(f'{FROM_FLAG} was given {rest.count(FROM_FLAG)} times '
                        f'— a report reads ONE rev, and which of two it should '
                        f'have been is not a thing this verb may pick')
        # The value is whatever sits in the NEXT position, taken positionally
        # and never searched for: `--from` at the end of the line is a missing
        # value, not a licence to adopt the milestone id as a rev.
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
        # "The building milestone" is a fact about TODAY's tree, and a report
        # at a rev that resolved its subject from today would be reading two
        # trees at once and saying so nowhere.
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
            # The second document this verb parses, and the same refusal shape
            # as the first: a review record whose verdict block EXISTS and
            # cannot be read correctly, named by record and by line. A record
            # with no block is not this — it is a row in the yield table saying
            # so. A record git does not hold at the rev arrives here too, since
            # "could not be read" is one fact however the read was attempted.
            raise Usage(f'{err}') from err
    except report.GitError as err:
        # Every git refusal, one exit code and one shape: a rev that does not
        # resolve carries git's own words verbatim, and a path the report needs
        # and cannot get names the path. Nothing was written either way,
        # because this verb has nothing to write with.
        raise Usage(f'{err}') from err
    if as_json:
        print(json.dumps(data, ensure_ascii=False))
        return 0
    if not src.is_file(path):
        # No ledger is a fact about SECTION 1's source, so say it where the
        # table would have been — and still say WHICH tree it is one fact
        # about. Sections 2 and 4 read the review records and the bug
        # frontmatter, documents this file has nothing to do with: stopping
        # here when THOSE hold something would tell a reader there is nothing
        # measured while a verdict block and an escape sit in the tree. When
        # they hold nothing, the one quiet line is still the whole report.
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

    Resolved by the version PREFIX over `git ls-tree`, exactly as
    `model.milestone_dir` globs `<mid>-*` on disk and for the same reason: the
    human suffix (`0.23.0-telemetry`) is not part of the id, and the suffix at
    the rev may not be the suffix today. The active roadmap first, then the
    archive — the same two places, in the same order.

    Two refusals, and both name what was looked for: an id that is not a
    milestone id at all, and a milestone that is not in the tree at that rev.
    The second is the ordinary mistake — a rev from AFTER the close that
    retired the directory — so the message says which rev to reach for.
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
    """The directory of an explicitly named milestone, or exit 2.

    A feature or story id resolves to a real file and is still the wrong noun:
    the ledger is per MILESTONE (D6), and reporting the milestone somebody's
    story happens to live in would answer a question nobody asked.
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
    # Deferred: `ready_for` and `skills` import this module's shared vocabulary
    # (Usage, Refused, _ok, `_grain_file`), so binding them at call time keeps
    # the load order a non-question whichever module a caller imports first.
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
        'ledger': cmd_ledger,
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
    except (Usage, model.AmbiguousStory) as err:
        print(f'[pm] ERROR — {err}', file=sys.stderr)
        return 2
