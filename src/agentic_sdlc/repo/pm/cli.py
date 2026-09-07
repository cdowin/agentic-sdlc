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
from agentic_sdlc.repo.pm import ledger, model, rename, report, templates

PROG = 'agentic-sdlc pm'

USAGE = """usage: agentic-sdlc pm <command>

Every question asked of a status is asked of its CATEGORY — todo, in_progress
or done — never of the word. Which words sit in which category is this
project's [pm.states.<kind>] in devkit.toml, written by `pm init` and read
every run; a state the project never declared is refused by name.

  story <status> <story-id>               (any state in [pm.states.story])
  bug <status> <bug-id>                   (any state in [pm.states.bug];
                                           bug-id is whatever the document
                                           declares — the id is read off
                                           `id:`/`kind:`, never off the path)
  feature <status> <feature-id>           (any state in [pm.states.feature].
                                           A write prints what it wrote and
                                           nothing else; a parent behind its
                                           children is `check pm`'s WARN)
  feature <done-state> <feature-id> [--review-record <path>]
                                          (a state in the `done` category
                                           closes: stamps `reviewed:` from the
                                           flag. No story file is touched —
                                           the story belt closes each by name.
                                           This is the BARE WRITE and it
                                           BYPASSES the belt: `agentic-sdlc
                                           close feature <id>` is the same
                                           close with its checks run first —
                                           stories-done, findings-landed — and
                                           it writes nothing when one of them
                                           is false. Reach for this only when
                                           the belt has already answered, or
                                           say `close feature --force`, which
                                           writes anyway and records the
                                           deviation on the ledger)
  milestone <status> <milestone-id>       (any state in [pm.states.milestone])
  retire <milestone-id> [<summary...>] [--dry-run]
                                          (removes every grain the milestone
                                           owns, and APPENDS a `retire` row to
                                           <roadmap>/ledger.jsonl carrying its
                                           version, its name and <summary...> —
                                           the three facts the tree keeps no
                                           other copy of once the documents are
                                           gone. `pm roadmap` prints them, so a
                                           shipped release still has a full row
                                           after its files do not. The id stays
                                           on the plan. Reports an undone
                                           status or live children rather than
                                           refusing on their account — refuses
                                           only when the id is missing)
  status [<milestone>]
  list [--status <s>[,<s>…]] [--owner <name>] [--milestone <id>]
       [--category todo|in_progress|done] [--json]
                                          (one tab-separated line per story,
                                           columns IN ORDER:
                                             id  status  owner  feature  name
                                           `-` for an empty cell, so a shell
                                           `read` gets a fixed count. --json
                                           emits the same fields keyed by those
                                           names and nothing else)
  list --kind milestone [--status <s>[,<s>…]] [--category <c>] [--json]
                                          (one tab-separated line per
                                           milestone, columns IN ORDER:
                                             id  status  category  branch  name
                                           What a script asks instead of
                                           grepping a status word out of
                                           milestone.md)
  list --kind feature|bug [--status <s>[,<s>…]] [--category <c>]
       [--milestone <id>] [--json]
                                          (one line per feature or bug,
                                           columns IN ORDER:
                                             id  status  milestone  <2nd>  name
                                           where <2nd> is `reviewed` for a
                                           feature and `caught_in` for a bug.
                                           The BINDING is a column, so "what
                                           have I written and not scheduled"
                                           is a pipe:
                                             pm list --kind feature |
                                               awk -F'\t' '$3 == "-"')

  READ VERBS EMIT LINES; COMPOSITION IS THE SHELL'S JOB. If you want a filter
  this package does not have, pipe it — the columns above are named so a
  pipeline is writable without reading source. **If you cannot pipe it, the
  missing thing is a COLUMN, not a verb**: `pm list | grep` failed once for
  want of the `name` field and the conclusion drawn was that the tool could not
  search. The filter flags that predate this rule stay; it governs the next
  one.
  ready-for story|feature|milestone|tag <id>
                                           (the belt-entry condition below that
                                           rung, as an EXIT CODE: 0 ready, 1
                                           not ready — naming every blocker,
                                           never a tally — 2 usage. story: the
                                           story belt's own checks that are
                                           decidable BEFORE the work — its
                                           `[story] steps` narrowed to what the
                                           registry declares an entry
                                           condition, with every check it did
                                           NOT ask named and why. feature:
                                           every story in the `done` CATEGORY
                                           ([pm.states.story] done — `obe` too,
                                           never the bare word). milestone:
                                           every feature in `done` with a
                                           non-empty review record. tag: every
                                           finding in the records the milestone
                                           points at at a disposition other
                                           than `open`. Writes nothing; emits
                                           `rung.enter` where `[emit]` declares
                                           a sink)
  get <grain-id> <key>                    (read one frontmatter field)
  set <grain-id> <key> <value>            (write one frontmatter field — not status)
  rename <old-id> <new-id>                (rewrite the grain's own `id:` AND
                                           every inbound reference in the tree
                                           — depends_on, consumed_by, reviewed,
                                           caused_by, caught_in, fix_milestone,
                                           the bindings (milestone:/feature:)
                                           and every `order` entry — in one
                                           pass, WHOLE OR NOT AT ALL: one
                                           reference this verb cannot rewrite
                                           and nothing at all is written.
                                           Matched whole-token, so 0.1/alphabet
                                           is not a reference to 0.1/alpha.
                                           FRONTMATTER ONLY: prose naming the
                                           id is yours, the ledger keeps its
                                           rows under the old id because history
                                           is not rewritten, and the document
                                           keeps its FILENAME — nothing reads a
                                           path as schema. A <new-id> failing
                                           the id grammar is refused before the
                                           tree is read; one another grain
                                           already holds is refused naming that
                                           grain, never auto-resolved)
  config --seed                           (the seed devkit.toml this pinned
                                           tool ships — every gate key
                                           commented at its real default.
                                           Writes nothing)
  templates [--force]                     (copy the templates into the project to edit)
  vocabulary [--json]                     (this version's declared surface:
                                           each kind's states with their
                                           category, and the rule ids. A tree
                                           declaring no flow is REPORTED, with
                                           the seed `init` would write)
  add <parent-id> <child-id> [--position N | --before <id> | --after <id>]
                                          (BIND the child to the parent and
                                           SEQUENCE it there, in one write pair
                                           — `set` plus a list insert, and
                                           nothing else. Bare, it appends.
                                           NEITHER ARGUMENT NAMES A KIND: each
                                           id resolves to the grain that
                                           declares one, and [pm.contains] says
                                           whether a parent of that kind holds a
                                           child of this one — a roadmap holds
                                           milestones, a milestone holds
                                           features and bugs, a feature holds
                                           stories. Off that mapping it refuses
                                           naming BOTH kinds and writes nothing.
                                           The ROOT is a parent like any other:
                                           pm/roadmap/releases.md declares its
                                           own `id:`, and adding a milestone to
                                           it schedules a release. Membership is
                                           the child's field; SEQUENCE is the
                                           parent's `order:` list, and `order`
                                           is optional — a bound child that is
                                           not in it is UNSEQUENCED, which is a
                                           counted line and never a finding)
  remove <parent-id> <child-id>           (unbind AND unsequence, together. `pm
                                           set <id> <field> ""` unbinds alone,
                                           which leaves the parent sequencing a
                                           child it no longer holds — the
                                           DANGLING entry `check pm` reports)
  next                                    (the first entry in `order` that has
                                           not shipped. columns IN ORDER:
                                             version  milestone  status
                                           Writes nothing)
  roadmap                                 (the whole plan: every scheduled
                                           milestone with its version and state,
                                           then the backlog. columns IN ORDER:
                                             version  milestone  state  name
                                             summary
                                           `-` for an empty cell, so a shell
                                           `read` gets a fixed count. A plan
                                           entry whose milestone has been
                                           RETIRED prints `retired` with the
                                           version, name and summary its
                                           `retire` row kept; one that names no
                                           grain and has no row is DANGLING.
                                           What `pm status` does for one
                                           milestone, for the sequence — and
                                           what replaced the hand-maintained
                                           ROADMAP.md. Writes nothing)
  validate                                (structural + referential integrity)
  install-skills [--force] [--diff]       (write the shared rule + operations skill)
  init                                    (scaffold a fresh tree + install guidance)
  new milestone <slug> <name...>          (mints id `ms-<slug>` — the kind
                                           prefix and the slug you typed, and
                                           NOTHING ELSE. A parent is a binding,
                                           never identity, so it is not in an
                                           id and re-parenting stays one `pm
                                           set`. <name...> is REQUIRED to
                                           create; give an id already in the
                                           tree and omit it to fill missing
                                           slots instead — that path is
                                           idempotent, and a shared doc appears
                                           on first WRITE)
  new feature <milestone> <slug> <name...>
                                          (mints `ft-<slug>`; <milestone> is
                                           written to `milestone:` — the same
                                           binding `pm add` writes — and is not
                                           part of the id. <name...> required
                                           to create, omitted to re-scaffold)
  new story <feature-id> <slug> <name...> (mints `st-<slug>`)
  new handoff <milestone>                 (mint handoff.md from the template, ON
                                           DEMAND — `new milestone` never creates
                                           it, because an absent handoff is what
                                           `check pm` warns on once a milestone is
                                           in progress. Never clobbers an existing
                                           one)
  new bug <milestone> <slug> [--caused-by <feature-id>]
                                          (mints `bg-<slug>`; <milestone> is the
                                           one that will FIX it and is written
                                           to `milestone:` and `caught_in:`.
                                           --caused-by stamps caused_by: — the
                                           feature whose change produced the
                                           bug, any status; it must resolve, and
                                           an unresolvable one writes nothing)
  ledger record --from-transcript <path> --event SubagentStop|Stop
                [--agent-id X] [--agent-type Y] [--session-id Z] [--grain <id>]
                                          (sum one Claude Code transcript and
                                           append a dispatch (SubagentStop) or
                                           session (Stop) row. A row is filed
                                           against the milestone that owns its
                                           GRAIN, at any status; no status is
                                           read, so a `planning` milestone
                                           records and two in flight are not a
                                           refusal. --grain says what the work
                                           was ON — the couriers pass it from
                                           GDK_LEDGER_GRAIN; with none, exactly
                                           one story in progress resolves it and
                                           zero or several OMIT the key. An id
                                           that resolves to nothing is refused
                                           rather than dropped. A row naming no
                                           grain lands in the tree's own
                                           <roadmap>/ledger.jsonl, with every
                                           gate and test row, and is reported in
                                           `rows naming no grain`)
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
  ledger show <grain-id> [--json]         (TELEMETRY for one grain — what it
                                           cost and how long it took. That
                                           grain's rows oldest first, with the
                                           seconds since the previous status
                                           row; --json prints the raw lines.
                                           Reads the grain's milestone ledger
                                           AND the tree's, so it and `ledger
                                           report` cannot disagree about a row)
  ledger report [<milestone-id>] [--json] [--from <rev>]
                                          (THE TELEMETRY REPORT — token spend,
                                           tool calls, wall-clock and gate cost,
                                           per grain, from rows the tree already
                                           recorded. Ask this before writing a
                                           table of timings by hand.
                                           Spend per grain from that milestone's
                                           rows: dispatches, tokens, tool calls,
                                           wall-clock and seconds in each
                                           CATEGORY (todo / in_progress / done),
                                           per story/feature/bug. With no id it
                                           reports the CURRENT release's
                                           milestone (`pm next`'s answer, from
                                           the plan) — the rows themselves are
                                           routed by their grain, never by a
                                           status. Never exits non-zero on a
                                           number.
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



# A verb this package used to route, named so it errors rather than reading as
# a typo. Each entry names its replacement.
RETIRED_COMMANDS = {
    'move': 're-parenting is one line now — `agentic-sdlc pm set <story-id> '
            'feature <feature-id>` — because membership is a FIELD and the id '
            'never changes, so there is nothing to rewrite. `pm move` renamed '
            'the file and did NOT rewrite the refs pointing AT the moved '
            'story; `pm rename <old> <new>` is the verb that sweeps those',
    'order': 'the plan is `order` on pm/roadmap/releases.md like any other '
             'parent\'s, so `agentic-sdlc pm add <plan-id> <milestone-id> '
             '[--position N | --before <id> | --after <id>]` schedules a '
             'release and `pm remove` takes one off. The plan lists MILESTONE '
             'IDS now, not versions — each milestone\'s own `version:` says '
             'which release it is. Reading the plan is still `pm roadmap`',
    'sync': 'the generated execution list (`<!-- pm:execution -->`) is retired '
            'with V6, which existed to keep it in agreement with the tree. '
            'The sequence it rendered is `order:` on the parent, written by '
            '`pm add` and read by `pm status` and `pm roadmap`',
}

# A heading ending in one of these is a shell's cut at an unquoted `;` — see
# cmd_decide.
SHELL_SPLITTERS = (';', '&', '|')


class Refused(Exception):
    """A precondition said no. Exit 1."""


class Usage(Exception):
    """Bad arguments, or an id that resolves to nothing. Exit 2."""


def _ok(msg: str) -> None:
    print(f'[pm] {msg}')


# Which belt closes a grain of each kind, and which belt the grain ABOVE it
# needs next. Both are `steps.registry_for` keys, and that is the whole of the
# mapping this module holds: the CHECKS each belt asks are read from the
# registry at runtime and never restated here, so a check added to a belt turns
# up in the breadcrumb without anybody remembering to add it.
CLOSES = {'story': 'story', 'feature': 'feature', 'milestone': 'release'}
# A milestone's `done` names nothing above it — there is no belt over a
# milestone, and inventing a sentence for that case would be the engine having
# an opinion about what somebody does after a release.
ABOVE = {'story': 'feature', 'feature': 'release'}


def _breadcrumb(cfg: model.PmConfig, kind: str, to: str) -> None:
    """One line after a status write: what the conveyor asks NEXT, DERIVED.

    Rule 9 says the tool never decides what a move MEANS, and a breadcrumb
    survives that only by being READ. Three runtime sources: the project's
    `[pm.states.<kind>]` for the category, `driver.step_names(<belt>)` for the
    checks that belt will ask, and `driver.SUBJECT` for its argument — so
    `close feature asks stories-done, …` is the engine reading back what it
    will run, where *"you should review now"* would be an opinion.

    `step_names` and not `registry_for`, because the registry is what SHIPS and
    the belt runs `[<belt>] steps`: reading the registry told a consumer who
    had narrowed that list four checks it had said it did not want.

    Why at the move at all: prose in three documents had already failed to stop
    a builder batching nine reviews to the end of a milestone.
    """
    if not cfg.breadcrumbs:
        return
    category = model.flow_of(cfg, kind).category(to)
    belt = (CLOSES.get(kind) if category == model.IN_PROGRESS
            else ABOVE.get(kind) if category == model.DONE_CATEGORY else None)
    if belt is None:
        return
    from agentic_sdlc.repo.conveyor import driver
    try:
        checks = list(driver.step_names(belt))
    except Exception:
        # A breadcrumb is a courtesy on top of a write that already happened.
        # A `[<belt>] steps` the belt itself would refuse is that belt's
        # finding to report when it runs, not this line's to raise after the
        # status is on disk.
        return
    if not checks:
        return
    verb = 'release' if belt == 'release' else f'close {belt}'
    # The belt's own subject, so the sentence can be copied: `release` takes a
    # VERSION and would refuse a grain id.
    subject = driver.SUBJECT.get(belt, (0, '', '<id>'))[2]
    print(f'[pm] next: `agentic-sdlc {verb} {subject}` asks '
          f'{", ".join(checks)}', file=sys.stderr)


def _unresolved(cfg: model.PmConfig, kind: str, gid: str, hint: str = '') -> Usage:
    """The refusal for an id that resolves to nothing, carrying the damage.

    A grain is found by `id:`, so a document whose frontmatter cannot be read
    is in no index and "no story resolves from id" is true and useless. Those
    documents are listed by path, so the fix is the next thing read.
    """
    parts = [f'no {kind} resolves from id {gid!r}']
    if hint:
        parts.append(f'({hint})')
    try:
        damaged = model.unkeyed_documents(cfg)
    except OSError:
        damaged = []
    if damaged:
        named = '; '.join(f'{cfg.rel(path)} {why}' for path, why in damaged)
        parts.append(f'— and {len(damaged)} document(s) in this tree cannot be '
                     f'keyed on, so a grain in one of them is addressable by '
                     f'nothing: {named}')
    return Usage(' '.join(parts))


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
    # The same guard every resolver runs, so a name the filesystem would refuse
    # is a refusal here rather than an OSError from the first write. It answers
    # without opening a file, which is why it can run before the pool is walked.
    defect = model.id_defect(value)
    if defect:
        raise Refused(f'{kind} {value!r} cannot name a grain: {defect} — '
                      f'nothing was written')
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


def _ledger_of(cfg: model.PmConfig, gid: str) -> Path | None:
    """The ledger file a grain's row belongs in, followed through its
    bindings — a story to its feature to its milestone (D1). None when the
    grain names no milestone, which is the row that lands at the root.

    The two hops live in `ledger.ledger_of_grain`, beside the addressing they
    are part of, because `repo/emit.py` routes its events the same way and one
    question with two answers is what 0.4.0 spent a lookup deleting."""
    return ledger.ledger_of_grain(cfg, gid)


def _stamp(cfg: model.PmConfig, path: Path, row: dict) -> None:
    """Append one row to the ledger of the milestone that owns `path`. Never
    raises and never changes an exit code; a missing row is said on stderr.
    """
    target = _ledger_of(cfg, model.unquote(model.field_of(path, 'id')))
    if target is None:
        print(f'[pm] WARNING — no milestone owns {cfg.rel(path)}, so '
              f'no {ledger.LEDGER_FILE_NAME} row was appended for it; the '
              f'write itself landed', file=sys.stderr)
        return
    try:
        ledger.append_to(target, row)
    except OSError as err:
        print(f'[pm] WARNING — {cfg.rel(target)} could not be '
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
        raise _unresolved(cfg, 'story', sid,
                          'expected <milestone>/<feature-slug>/<story-slug>')
    cur = _was(sf)
    if cur == to:
        _ok(f'story {sid} already {to} (no-op)')
        _stamp_status(cfg, sf, cur, to, sid)
        _breadcrumb(cfg, 'story', to)
        return 0
    _set_status(cfg, sf, to)
    _ok(f'story {sid}: {cur} -> {to}')
    _stamp_status(cfg, sf, cur, to, sid)
    _breadcrumb(cfg, 'story', to)
    return 0


# --- bug ------------------------------------------------------------------
def cmd_bug(cfg: model.PmConfig, args: list[str]) -> int:
    """Move a bug's `status:` through code, `cmd_story`'s shape.

    **The guard is `kind:`, not the id's shape.** `/bugs/` in the id was a path
    test standing in for the kind test `grain_file(..., 'bug')` does properly,
    and it refused every flat `bg-` id the migration mints — so no bug on a
    migrated tree was movable at all, and `pm new bug` now mints those.
    """
    if len(args) != 2:
        raise Usage(USAGE)
    to, bid = args
    _movable(cfg, 'bug', to)
    defect = model.id_defect(bid)
    if defect:
        raise _unresolved(cfg, 'bug', bid, defect)
    bf = model.grain_file(cfg, bid, 'bug')
    if bf is None:
        raise _unresolved(cfg, 'bug', bid)
    cur = _was(bf)
    if cur == to:
        _ok(f'bug {bid} already {to} (no-op)')
        _stamp_status(cfg, bf, cur, to, bid)
        _breadcrumb(cfg, 'bug', to)
        return 0
    _set_status(cfg, bf, to)
    _ok(f'bug {bid}: {cur} -> {to}')
    _stamp_status(cfg, bf, cur, to, bid)
    _breadcrumb(cfg, 'bug', to)
    return 0


# --- feature ------------------------------------------------------------------
def _feature_or_usage(cfg: model.PmConfig, fid: str) -> tuple[Path, str]:
    ff = model.feature_file(cfg, fid)
    if ff is None:
        raise _unresolved(cfg, 'feature', fid)
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
        _breadcrumb(cfg, 'feature', to)
        return 0
    _set_status(cfg, ff, to)
    _ok(f'feature {fid}: {cur} -> {to}')
    _stamp_status(cfg, ff, cur, to, fid)
    _breadcrumb(cfg, 'feature', to)
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
    _breadcrumb(cfg, 'feature', to)
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
        _breadcrumb(cfg, 'milestone', to)
        return 0
    _set_status(cfg, mf, to)
    _ok(f'milestone {mid}: {cur} -> {to}')
    _stamp_status(cfg, mf, cur, to, mid)
    _breadcrumb(cfg, 'milestone', to)
    # No advisory about the features left behind: D3 asks that of the tree.
    return 0


def _known_milestone_ids(cfg: model.PmConfig) -> list[str]:
    return sorted(mid or mdir.name
                  for mdir, mid in model.known_milestones(cfg))


def _retired_files(cfg: model.PmConfig, milestone) -> list[Path]:
    """Every file `retire` removes for one milestone, in delete order.

    The milestone, everything bound to it, everything bound to THOSE, each
    grain's shared documents, and the milestone's ledger. The tree's own ledger
    is not touched: those rows were never about this milestone (0.4.0/D3).
    """
    grains = [milestone]
    for kind in ('feature', 'bug'):
        for child in model.children(cfg, kind, milestone.gid):
            grains.append(child)
            if kind == 'feature':
                grains.extend(model.children(cfg, 'story', child.gid))
    out: list[Path] = []
    for grain in grains:
        out.append(grain.path)
        for slot in (model.DECISION_FILE_NAME, model.REVIEW_FILE_NAME,
                     model.HANDOFF_FILE_NAME):
            shared = model.shared_doc(cfg, grain, slot)
            if shared != grain.path and shared.is_file():
                out.append(shared)
    ledger_path = ledger.ledger_for(cfg, milestone.gid)
    if ledger_path.is_file():
        out.append(ledger_path)
    return [p for p in out if p.is_file()]


def cmd_retire(cfg: model.PmConfig, args: list[str]) -> int:
    """Retire a finished milestone: remove its grains, and FILE what outlived
    them.

    **`ROADMAP.md` retired in 0.3.0 and this verb no longer appends to it.**
    `pm roadmap` derives the index it was half of. The other half — one row per
    shipped release: version, name, one sentence — is not derivable from a tree
    the documents have left, so it is a `retire` row in the tree's own
    `ledger.jsonl`, which this verb removes nothing from
    (`bg-retire-drops-the-summary-it-accepts`). The summary used to be joined,
    interpolated into a sentence and printed; only the id survived.

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
    grain = model.grain_index(cfg).get(mid)
    if grain is None or grain.kind != 'milestone':
        known = _known_milestone_ids(cfg)
        raise Usage(f'{mid!r} is not a milestone in {cfg.roadmap_dir} '
                    f'({" ".join(known) if known else "none scaffolded"})')
    mfile = grain.path
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
    # By ID, never by the directory the document sits in: under pools that is
    # the pool, so every unfinished feature reported as `features`.
    open_features = sorted(
        name for name, _ in model.holds(
            cfg, 'feature',
            ((model.unquote(model.field_of(ff, 'id')) or cfg.rel(ff),
              model.field_of(ff, 'status'))
             for ff in model.feature_files(cfg, mid)),
            model.DONE_CATEGORY).blockers)
    if open_features:
        notices.append(f'{len(open_features)} feature(s) not done: '
                       f'{" ".join(open_features)}')
    # "Still open" is "not in `done`": a bug at `fixed` is work that remains.
    open_bugs = sorted(
        name for name, _ in model.holds(
            cfg, 'bug',
            ((bf.stem, model.field_of(bf, 'status'))
             for bf in model.bug_files(cfg, mid)),
            model.DONE_CATEGORY).blockers)
    if open_bugs:
        notices.append(f'{len(open_bugs)} bug(s) still open: '
                       f'{" ".join(open_bugs)}')

    # Whitespace collapsed at the WRITE, so the stored sentence can never forge
    # a column in the tab-separated row `pm roadmap` prints it in.
    summary = ' '.join(' '.join(summary_words).split())
    version = model.field_of(mfile, 'version').strip() if mfile.is_file() else ''
    row = ledger.retire_row(canonical_id, version, name, summary)
    ledger_file = ledger.grainless_path(cfg.roadmap)
    # What outlives the documents, and where. `order` keeps the id; the ledger
    # row keeps the three facts the tree has no other copy of.
    kept = (f'{cfg.rel(ledger_file)} keeps '
            + ', '.join(f'{key} {row[key]!r}' for key in ledger.RETIRE_FIELDS
                        if key in row)
            if any(key in row for key in ledger.RETIRE_FIELDS)
            else f'{cfg.rel(ledger_file)} keeps the id and the date — this '
                 f'milestone declares no version and no name, and no summary '
                 f'was given, so there is nothing else to keep')
    plan_note = ('' if canonical_id in model.declared_order(cfg)
                 else f'; {canonical_id} is on no plan, so `pm roadmap` will '
                      f'not print it — `agentic-sdlc pm add '
                      f'{model.root_id(cfg)} {canonical_id}` before retiring '
                      f'gives it a row there')

    if dry_run:
        _ok(f'[dry-run] would remove '
            f'{len(_retired_files(cfg, grain))} file(s), '
            f'starting {cfg.rel(mfile)}')
        _ok(f'[dry-run] {kept}{plan_note}')
        for n in notices:
            _ok(f'  noticed: {n}')
        return 0

    # The GRAINS this milestone owns, and its ledger — not a directory, which
    # a pooled tree has none of. The same set either way: every feature and bug
    # bound to it, every story bound to those, its own document, and the shared
    # docs sitting beside each. `pm retire` deletes N files instead of one
    # directory, and that is the tool's work rather than a human's.
    doomed = _retired_files(cfg, grain)
    plan = apply.Plan()
    for path in doomed:
        plan.delete_file(path, label=cfg.rel(path))
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
    # AFTER the removal, because the row is a record of what happened, not of
    # what was about to. `append_to` raises when the caller has already changed
    # the tree, and the refusal below carries the three facts by value so a
    # hand-repair does not need the deleted document back.
    try:
        ledger.append_to(ledger_file, row)
    except OSError as err:
        raise Refused(
            f'{len(doomed)} file(s) were removed, and the retire row could not '
            f'be appended to {cfg.rel(ledger_file)} ({err}) — nothing now '
            f'records {ledger.dumps(row)}. Fix the obstruction and append that '
            f'line by hand') from err
    _ok(f'milestone {mid}: retired — {len(doomed)} file(s) removed; '
        f'{kept}{plan_note}')
    for n in notices:
        _ok(f'  noticed: {n}')
    return 0


# --- move -----------------------------------------------------------------
def _known_feature_ids(cfg: model.PmConfig) -> list[str]:
    out = []
    for milestone in model.milestones(cfg):
        out.extend(model.unquote(model.field_of(ff, 'id'))
                   or f'{milestone.gid}/{ff.parent.name}'
                   for ff in model.feature_files(cfg, milestone.gid))
    return sorted(out)


# --- status -------------------------------------------------------------------
def _short(mid: str, gid: str) -> str:
    """A child's id with the parent's prefix taken off, when it has one.

    A nested id was `<milestone>/<slug>` and this column printed the slug; a
    pooled id is `ft-<slug>` and there is nothing to strip. One function, so
    the board reads the same in either layout.
    """
    head = f'{mid}/'
    return gid[len(head):] if gid.startswith(head) else gid


def _open_for(cfg: model.PmConfig, mid: str) -> dict[str, str]:
    """{grain id: how long it has been open}, for the grains in one milestone
    that have not reached a terminal state.

    Read once per milestone, off the two ledgers that milestone's rows can be
    in, so `pm status` costs one pass over each file rather than one per grain.
    A grain with no status row is simply absent here and prints `-`: it has not
    been moved, which is a different fact from having been moved a moment ago
    (rule 4).
    """
    rows: list = []
    for path in (ledger.ledger_for(cfg, mid),
                 ledger.grainless_path(cfg.roadmap)):
        try:
            rows += ledger.read_rows(path)
        except ledger.LedgerError:
            # A ledger this reader cannot parse costs the DURATION column, not
            # `pm status`: the statuses are in the frontmatter and are what the
            # verb is actually for.
            continue
    by_grain: dict[str, list] = {}
    for row in rows:
        if row.data.get('kind') != ledger.KIND_STATUS:
            continue
        gid = row.data.get('grain')
        if isinstance(gid, str) and gid:
            by_grain.setdefault(gid, []).append(row)
    out = {}
    for gid, status in by_grain.items():
        status.sort(key=lambda r: str(r.data.get('ts') or ''))
        kind = _grain_kind(cfg, gid)
        if not kind:
            # A row naming a grain the tree does not hold: there is no
            # vocabulary to ask, so it is UNMEASURED rather than open.
            continue
        seconds = ledger.open_seconds(cfg, kind, status)
        if seconds is not None:
            out[gid] = ledger.human_duration(seconds)
    return out


def _age_cell(cfg: model.PmConfig, kind: str, gid: str, status: str,
              opened: dict[str, str]) -> str:
    """`  open 3d 4h`, `  open -`, or nothing — nothing only for a grain that
    has REACHED a done state. An OPEN grain nobody has moved is `-`: unmeasured
    is a different fact from young, and omitting the cell made it
    indistinguishable from finished (rule 4)."""
    if model.category_of(cfg, kind, status) == model.DONE_CATEGORY:
        return ''
    return f'  open {opened.get(gid) or ledger.human_duration(None)}'


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
        mfile = model.milestone_doc(mdir)
        if only and only != mid:
            continue
        # 0.4.0/every-grain-is-on-a-stopwatch: how long each open grain has
        # been open, so "what is aging" is a question the tree answers rather
        # than one somebody reconstructs after the fact. A REPORT — nothing is
        # gated on it, because a ceiling on how long a feature may stay open is
        # this package having an opinion about somebody's week (rule 9).
        opened = _open_for(cfg, mid)
        mstat = model.field_of(mfile, 'status')
        print(f'milestone {mid:<10} [{mstat}]'
              + _age_cell(cfg, 'milestone', mid, mstat, opened))
        rows = []
        for ffile in model.feature_files(cfg, mid):
            view = model.read_feature(cfg, ffile)
            # The markers reuse the gate's predicates, so report and gate
            # cannot describe a tree differently.
            dangling = model.drift_dangling_record(cfg, view.fid)
            stalled = model.drift_stalled(cfg, view)
            drift = (f'  <DRIFT: {dangling}>' if dangling
                     else f'  <WARN: {stalled}>' if stalled else '')
            rows.append((view,
                         f'  feature {_short(mid, view.fid):<40} '
                         f'[{view.status:<{width}}] stories '
                         f'{view.done_n}/{view.total} done'
                         + _age_cell(cfg, 'feature', view.fid, view.status,
                                     opened) + drift))
        if not rows:
            continue
        # IN THE MILESTONE'S DECLARED ORDER — `feature_files` reads the
        # parent's `order:` and falls back to id. `phase:` grouped this board
        # until 0.4.0 and retired with the execution list (D-note).
        finished = model.holds(cfg, 'feature',
                               ((v.fid, v.status) for v, _ in rows),
                               model.DONE_CATEGORY)
        print(f'  -- {finished.counted - len(finished.blockers)}/{len(rows)} '
              f'feature(s) done')
        for _, line in rows:
            print(line)
    return 0


def cmd_list(cfg: model.PmConfig, args: list[str]) -> int:
    """One tab-separated line per story, filtered — a view over facts, no
    ranking. Rows go to stdout and the census to stderr, so matching
    nothing and scanning nothing stay distinguishable.
    """
    as_json = JSON_FLAG in args
    args = [a for a in args if a != JSON_FLAG]
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
        return _list_milestones(cfg, statuses, category, as_json)
    if kind in ('feature', 'bug'):
        if owner:
            raise Usage(f'--owner filters stories; a {kind} carries no owner:')
        return _list_bound(cfg, kind, statuses, category, milestone, as_json)

    # Enumerated once, to refuse a typo'd `--milestone` as well as to filter.
    known = model.known_milestones(cfg)
    if milestone and milestone not in {mid for _, mid in known}:
        ids = sorted(mid for _, mid in known if mid)
        raise Usage(f'--milestone names {milestone!r}, which is not a milestone '
                    + (f'in {cfg.roadmap_dir} ({" ".join(ids)})' if ids else
                       f'— {cfg.roadmap_dir} holds no milestone at all, so this '
                       f'is a scope problem, not a typo'))

    scanned = 0
    rows = []
    for mdir, mid in known:
        if milestone and milestone != mid:
            continue
        for ffile in model.feature_files(cfg, mid):
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
                rows.append((model.unquote(model.field_of(sfile, 'id')),
                             status, who or DASH, view.fid,
                             model.unquote(model.field_of(sfile, 'name'))
                             or DASH))
    _emit_rows('story', rows, as_json)
    print(f'[pm] {len(rows)} of {scanned} story/ies', file=sys.stderr)
    return 0


# One cell with nothing in it, so a shell `read` gets a fixed column count and
# an empty field is never mistaken for a short row.
DASH = '-'

# What a version cell holds when the milestone declares none. Not `-`: a
# milestone without a version is BACKLOG rather than an empty cell (R2), and
# `pm next` and `pm roadmap` have to say the same thing.
NO_VERSION = '(no version)'


def _emit_rows(kind: str, rows: list[tuple[str, ...]], as_json: bool) -> None:
    """The listing verbs' one output path: tab-separated cells, or `--json`
    over the SAME tuples through `LIST_COLUMNS`.

    One function because the failure that matters is the two diverging — a
    JSON payload carrying a field the columns do not, or vice versa, is the
    thing a consumer discovers at the worst moment. Here they cannot: the rows
    are built once and the keys are zipped onto them.
    """
    columns = LIST_COLUMNS[kind]
    if as_json:
        print(json.dumps([dict(zip(columns, row)) for row in rows],
                         ensure_ascii=False))
        return
    for row in rows:
        # A tab inside a cell would forge a column, and `name` is free text a
        # human typed. The JSON payload above keeps the byte; this one cannot,
        # and a forged column is worse than a substituted space because it
        # silently shifts every field after it.
        print('\t'.join(cell.replace('\t', ' ') for cell in row))


# `milestone` is here so a script can ask the CLI instead of grepping a status
# word.
# Every kind is listable. It was story and milestone, so "show me what is
# unbound" looked like it needed a flag: there was nothing to pipe (rule 11).
LIST_KINDS = ('story', 'milestone', 'feature', 'bug')

# The columns each `--kind` emits, IN ORDER, spelled once. Three things read
# this — the rows, `--json`'s keys and the `--help` line — and a column list
# that lived in three places is exactly the drift `--json` exists to make
# impossible to hide.
LIST_COLUMNS = {
    'story': ('id', 'status', 'owner', 'feature', 'name'),
    'milestone': ('id', 'status', 'category', 'branch', 'name'),
    # A grain that BINDS emits its binding, so `$4 == "-"` is "unbound" and
    # every other question about the edge is a pipe away.
    'feature': ('id', 'status', 'milestone', 'reviewed', 'name'),
    'bug': ('id', 'status', 'milestone', 'caught_in', 'name'),
}


def _list_bound(cfg: model.PmConfig, kind: str, statuses: set[str],
                category: str, milestone: str, as_json: bool) -> int:
    """Features or bugs, one line each, with the binding as a COLUMN — `-`
    there is "written and not yet scheduled", answered by a pipe rather than a
    flag, which composes with every other filter (rule 11)."""
    scanned = 0
    rows = []
    for gid, grain in sorted(model.grain_index(cfg).items()):
        if grain.kind != kind:
            continue
        scanned += 1
        status = model.field_of(grain.path, 'status')
        bound = model.unquote(model.field_of(grain.path, 'milestone'))
        if statuses and status not in statuses:
            continue
        if category and model.category_of(cfg, kind, status) != category:
            continue
        if milestone and bound != milestone:
            continue
        second = 'reviewed' if kind == 'feature' else 'caught_in'
        rows.append((gid, status or DASH, bound or DASH,
                     model.unquote(model.field_of(grain.path, second)) or DASH,
                     model.unquote(model.field_of(grain.path, 'name')) or DASH))
    _emit_rows(kind, rows, as_json)
    print(f'[pm] {len(rows)} of {scanned} {kind}(s)', file=sys.stderr)
    return 0


def _list_milestones(cfg: model.PmConfig, statuses: set[str],
                     category: str, as_json: bool = False) -> int:
    """One tab-separated `<id> <status> <category> <branch> <name>` per
    milestone, `-` for an absent one, so a shell `read` gets a fixed column
    count. `LIST_COLUMNS['milestone']` is the order.
    """
    known = model.known_milestones(cfg)
    if not known:
        raise Usage(f'{cfg.roadmap_dir} holds no milestone at all — nothing to '
                    f'list, so this is a scope problem (wrong [pm] '
                    f'roadmap_dir, or an empty tree?), not an empty set')
    rows = []
    for mdir, mid in known:
        mfile = model.milestone_doc(mdir)
        status = model.field_of(mfile, 'status')
        cat = model.category_of(cfg, 'milestone', status)
        if statuses and status not in statuses:
            continue
        if category and cat != category:
            continue
        rows.append((mid or mdir.name, status or DASH, cat or DASH,
                     model.unquote(model.field_of(mfile, 'branch')) or DASH,
                     model.unquote(model.field_of(mfile, 'name')) or DASH))
    _emit_rows('milestone', rows, as_json)
    print(f'[pm] {len(rows)} of {len(known)} milestone(s)', file=sys.stderr)
    return 0


def _grain_file(cfg: model.PmConfig, gid: str) -> Path:
    """Resolve any grain id — milestone, feature, story or bug — to its file.

    ONE lookup for all four kinds, because a grain declares its `id:` and the
    index is keyed on it. The four-branch version this replaced did arithmetic
    on a path, which is why a `..` or an empty segment had to be caught before
    a join could hand a write to a sibling grain. Nothing is joined now.
    """
    defect = model.id_defect(gid)
    if defect:
        raise Usage(f'no grain resolves from id {gid!r} — {defect}')
    found = model.grain_file(cfg, gid)
    if found is None:
        raise Usage(f'no grain resolves from id {gid!r}')
    return found


def cmd_get(cfg: model.PmConfig, args: list[str]) -> int:
    if len(args) != 2:
        raise Usage(USAGE)
    gid, key = args
    print(model.field_of(_grain_file(cfg, gid), key))
    return 0


def _binding_defect(cfg: model.PmConfig, gid: str, key: str,
                    value: str) -> None:
    """Refuse a binding that names no grain, or one of the wrong kind — a fact
    about the INPUT, so exit 2 and nothing written (rule 9). Empty UNBINDS and
    is never refused; only the fields `BINDS_TO` names are asked, so `set`
    writes every other key without an opinion."""
    want = {field: parent for parent, field in model.BINDS_TO.values()}.get(key)
    if want is None or not value:
        return
    found = model.grain_index(cfg).get(model.unquote(value))
    if found is None:
        raise Usage(f'{key}: {value!r} names no grain in {cfg.roadmap_dir} — '
                    f'a binding that resolves to nothing is drift, not a plan; '
                    f'leave it empty to say "not bound yet". Nothing was '
                    f'written')
    if found.kind != want:
        raise Usage(f'{key}: {value!r} is a {found.kind}, not a {want} — '
                    f'a {model.kind_of(cfg, gid) or "grain"} names its '
                    f'{want} in {key}:. Nothing was written')


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
        # The grain's own kind when the tree holds it; the hint names a verb,
        # and a verb for a kind nobody declared would be a worse hint than a
        # generic one.
        kind = _grain_kind(cfg, gid) or 'story'
        raise Usage(f'status is a move, not a field: run `{PROG} {kind} '
                    f'{value} {gid}` — the {kind} verb checks {value!r} '
                    f'against [pm.states.{kind}] and stamps the ledger; '
                    f'`set` would do neither')
    if '\n' in value or '\r' in value:
        raise Refused('a frontmatter scalar is one line')
    path = _grain_file(cfg, gid)
    _binding_defect(cfg, gid, key, value)
    before = model.field_of(path, key)
    if not model.set_field(path, key, value):
        raise Usage(f'could not write {key}: in {cfg.rel(path)} '
                    f'(malformed frontmatter, or the file is not writable)')
    _ok(f'{gid}: {key} {before!r} -> {value!r}')
    return 0


def cmd_rename(cfg: model.PmConfig, args: list[str]) -> int:
    """Rewrite one grain's `id:` and every reference naming it, whole or not
    at all. `rename.sweep` decides against the tree; this maps its verdict onto
    the exit codes and prints what moved.
    """
    if len(args) != 2:
        raise Usage(USAGE)
    swept = rename.sweep(cfg, args[0], args[1])
    if swept.defect:
        raise Usage(swept.defect)
    if swept.blockers:
        raise Refused('; '.join(swept.blockers) + ' — nothing was written')
    if swept.noop:
        _ok(swept.noop)
        return 0
    applied = swept.plan.apply(decide=False)
    if applied.failed is not None:
        raise Refused(
            f'{applied.failed.label} could not be written ({applied.error}) — '
            + ('nothing was written' if not applied.landed else
               'ALREADY LANDED: ' + ', '.join(s.label for s in applied.landed))
            + '. Fix the obstruction and re-run.')
    _ok(f'renamed {swept.old} -> {swept.new} in {len(swept.edits)} file(s)')
    for edit in swept.edits:
        _ok(f'  {cfg.rel(edit.path)}\t{" ".join(edit.fields)}')
    # Rule 11: what a rename does NOT touch, said where somebody is standing.
    _ok(f'  noticed: the ledger keeps its rows under {swept.old} — telemetry '
        f'is history, and history is not rewritten')
    _ok(f'  noticed: prose naming {swept.old} is yours; only frontmatter was '
        f'swept, and the document keeps its filename')
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


def _scaffold(cfg: model.PmConfig, kind: str, doc: Path,
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
        actions = templates.scaffold(cfg, kind, doc, values)
    except templates.ScaffoldRefused as err:
        raise Refused(str(err)) from err
    except templates.MissingTemplate as err:
        raise Usage(str(err)) from err
    for what, path in actions:
        _ok(f'{what} {cfg.rel(path)}')
    if not actions:
        _ok(f'{cfg.rel(doc)} already has every canonical slot (no-op)')
    else:
        _ok(f'{cfg.rel(doc)}: {len(actions)} slot(s) filled')
    return 0


def _slugify(text: str) -> str:
    """ASCII-only: it becomes a permanent directory name, and `str.isalnum()`
    is Unicode-aware."""
    keep = 'abcdefghijklmnopqrstuvwxyz0123456789'
    out = ''.join(c if c in keep else '-' for c in text.lower())
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')


def _mint_path(cfg: model.PmConfig, kind: str, gid: str, name: str = '',
               parent_id: str = '') -> Path:
    """The file a NEW grain is written to, in whichever layout the tree is in.
    A NESTED tree keeps its shape: minting into a pool there flips `is_pooled`,
    and every reader then sees the one new file and none of the tree behind it.

    `gid` is the MINTED ID and the stem, as in the migration; nothing READS a
    stem (`pm rename` never moves a file, rule 9).
    """
    if not model.is_nested(cfg):
        return model.pool_dir(cfg, kind) / f'{gid}.md'
    if kind == 'milestone':
        stem = f'{gid}-{_slugify(name)}' if name else gid
        return cfg.roadmap / stem / model.MILESTONE_DOC
    parent = (model.milestone_dir(cfg, parent_id) if kind != 'story'
              else model.feature_dir(cfg, parent_id))
    if parent is None:
        return model.pool_dir(cfg, kind) / f'{gid}.md'
    if kind == 'feature':
        return parent / model.FEATURES_DIR / gid / model.FEATURE_DOC
    if kind == 'story':
        return parent / model.STORIES_DIR / f'{gid}.md'
    return parent / model.BUGS_DIR / f'{gid}.md'


NAME_ARG = '<name...>'   # a create's last argument, for the refusal and the synopsis


def _retired_id(kind: str, parent_id: str, slug: str) -> str:
    """The compound id 0.4.0's `pm new` minted from these arguments, or ''.
    **READ, never minted**: on a tree authored then, `pm new feature <mid>
    <slug>` must keep filling that document rather than creating a second one
    beside it, so the pin bump is not a duplicate factory (rule 3).
    """
    if not parent_id:
        return ''
    if kind == 'bug':
        return f'{parent_id}/{model.BUGS_DIR}/{slug}'
    return f'{parent_id}/{slug}' if kind in ('feature', 'story') else ''


def _claim(cfg: model.PmConfig, kind: str, slug: str,
           parent_id: str = '') -> tuple[str, Path | None]:
    """(the id this call is about, the document already holding it or None).

    Three spellings LOOKED UP, one MINTED: the argument as a literal id, the id
    `mint_id` makes of it, and the retired compound one — first hit wins, and
    none means the minted id is created. `story_file` for a story: only it
    resolves the nested layout's slug-plus-ordinal.
    """
    minted = model.mint_id(kind, slug)
    for gid in (slug, minted, _retired_id(kind, parent_id, slug)):
        found = (model.story_file(cfg, gid) if kind == 'story'
                 else model.grain_file(cfg, gid, kind)) if gid else None
        if found is not None:
            return gid, found
    return minted, None


def _name_required(kind: str, gid: str, typed: str) -> 'Usage':
    """The refusal for a CREATE with no name, leading with the ARGUMENT that
    was omitted: *"feature 'x' does not exist yet"* read as *this grain is
    missing from your tree* and sent readers looking for a lost file.
    """
    return Usage(f'{NAME_ARG} is required: `agentic-sdlc pm new {kind} {typed} '
                 f'{NAME_ARG}`. Nothing in this tree declares {gid!r}, so this '
                 f'call CREATES a {kind} rather than filling the missing slots '
                 f'of one that is already there, and the name is the one slot '
                 f'that cannot be derived')


def cmd_new(cfg: model.PmConfig, args: list[str]) -> int:
    """Scaffold one grain, minting its id through `model.mint_id`.

    **The parent argument BINDS; it is not identity** — it goes to the child's
    `milestone:`/`feature:` field, the fact `pm add` writes, and never into the
    id, so re-parenting stays one `pm set`. It stays positional and required:
    dropping it breaks every caller, and reading the first argument as a
    parent-or-slug would be inferring intent (rule 9).
    """
    if not args:
        raise Usage(USAGE)
    grain, rest = args[0], args[1:]
    # `new milestone` and `new feature` are idempotent — they fill missing
    # slots — so the name is optional when the grain is already there.
    if grain == 'milestone':
        if not rest:
            raise Usage(USAGE)
        slug, name = _check_slug('milestone slug', rest[0]), ' '.join(rest[1:])
        mid, found = _claim(cfg, 'milestone', slug)
        if found is None and not name:
            raise _name_required('milestone', mid, slug)
        target = found or _mint_path(cfg, 'milestone', mid, name)
        name = name or model.field_of(target, 'name')
        return _scaffold(cfg, 'milestone', target,
                         {'id': mid, 'kind': 'milestone', 'name': name})
    if grain == 'feature':
        if len(rest) < 2:
            raise Usage(USAGE)
        mid, slug = rest[0], _check_slug('feature slug', rest[1])
        name = ' '.join(rest[2:])
        if model.milestone_file(cfg, mid) is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        fid, found = _claim(cfg, 'feature', slug, mid)
        if found is None and not name:
            raise _name_required('feature', fid, f'{mid} {slug}')
        target = found or _mint_path(cfg, 'feature', fid, name, mid)
        name = name or model.field_of(target, 'name')
        return _scaffold(cfg, 'feature', target,
                         {'id': fid, 'kind': 'feature', 'milestone': mid,
                          'name': name})
    if grain == 'story':
        if len(rest) < 3:
            raise Usage(USAGE)
        fid, slug = rest[0], _check_slug('story slug', rest[1])
        name = ' '.join(rest[2:])
        ffile = model.feature_file(cfg, fid)
        if ffile is None:
            raise Usage(f'no feature resolves from id {fid!r}')
        # The milestone comes from the feature's own frontmatter, never
        # re-derived from the id.
        mid = model.field_of(ffile, 'milestone')
        sid, claimed = _claim(cfg, 'story', slug, fid)
        if claimed is not None:
            raise Refused(f'story id {sid!r} is already held by '
                          f'{cfg.rel(claimed)} — two files claiming one id is '
                          f'addressable by neither')
        sf = _mint_path(cfg, 'story', sid, '', fid)
        if _exists(sf):
            raise Refused(f'{cfg.rel(sf)} already exists')
        body = templates.render(
            templates.load(cfg, 'story'),
            {'id': sid, 'kind': 'story', 'feature': fid, 'milestone': mid,
             'name': name})
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
        if model.milestone_file(cfg, mid) is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        bid, held = _claim(cfg, 'bug', slug, mid)
        if held is not None:
            raise Refused(f'bug {bid!r} already exists')
        bf = _mint_path(cfg, 'bug', bid, '', mid)
        if _exists(bf):
            raise Refused(f'{cfg.rel(bf)} already exists')
        # Bugs anchor to where they were CAUGHT; `caught_in:` carries that now
        # that the path does not.
        body = templates.render(
            templates.load(cfg, 'bug'),
            {'id': bid, 'kind': 'bug', 'milestone': mid, 'slug': slug})
        _mint(cfg, bf, body)
        _ok(f'created {cfg.rel(bf)}')
        if cause:
            # Stamped through `set_field`, so a project's own bug.md still gets
            # the field; a template with no frontmatter is refused out loud.
            if not model.set_field(bf, CAUSED_BY, cause):
                raise Refused(
                    f'{cfg.rel(bf)} was created, but {CAUSED_BY}: could not be '
                    f'written into it — its frontmatter has no `---` block to '
                    f'put the field in; add one, or set it with `pm set {bid} '
                    f'{CAUSED_BY} {cause}`')
            # Echoed, because a field the caller asked for and never sees
            # confirmed is a field they have to go read the file to trust.
            _ok(f'{CAUSED_BY} {cause!r} stamped on {cfg.rel(bf)}')
        return 0
    if grain == 'handoff':
        # ON DEMAND ONLY. `new milestone` deliberately does NOT mint this doc:
        # an absent handoff.md is the signal `check pm` warns on when a
        # milestone moves into an `in_progress` state, and a template auto-
        # written into every milestone would destroy that signal — every tree
        # would carry a handoff nobody wrote. This verb is what the warning's
        # hint names, so the absence stays meaningful and the fix stays one
        # command.
        if len(rest) != 1:
            raise Usage(USAGE)
        mid = rest[0]
        grain = model.grain_index(cfg).get(mid)
        if grain is None or grain.kind != 'milestone':
            raise Usage(f'no milestone resolves from {mid!r}')
        doc = model.shared_doc(cfg, grain, model.HANDOFF_FILE_NAME)
        if doc.is_file():
            # Never clobbered: the traps section is the one thing in the tree
            # no command can regenerate.
            _ok(f'{cfg.rel(doc)} already exists (no-op) — `pm new milestone '
                f'{mid}` restores its header line if that is what is missing')
            return 0
        try:
            body = templates.render(
                templates.load(cfg,
                               model.SLOT_TEMPLATE[model.HANDOFF_FILE_NAME]),
                {'id': mid,
                 'name': model.field_of(grain.path, 'name')})
        except (OSError, UnicodeDecodeError, templates.MissingTemplate) as err:
            raise Usage(f'the handoff template cannot be read ({err}) — '
                        f'{cfg.rel(doc)} was not created') from err
        _mint(cfg, doc, body)
        _ok(f'created {cfg.rel(doc)}')
        return 0
    raise Usage(USAGE)


# --- decide -------------------------------------------------------------------
def _decision_log(cfg: model.PmConfig, gid: str) -> tuple[Path, str]:
    """(the decisions.md the grain `gid` names, its text — minted from the
    template if absent). Nothing is written here; the caller writes once.
    """
    depth = gid.count('/')
    grain = model.grain_index(cfg).get(gid)
    if grain is not None and grain.kind not in ('milestone', 'feature'):
        raise Refused(f'{gid!r} is a {grain.kind} — those have no decision '
                      f'log; name the feature or milestone that owns the choice')
    if grain is None and (depth > 1 or f'/{model.BUGS_DIR}/' in gid):
        raise Refused(f'{gid!r} is a story or a bug — those have no decision '
                      f'log; name the feature or milestone that owns the choice')
    if grain is None:
        raise Usage(f'no milestone or feature resolves from id {gid!r}')
    log = model.shared_doc(cfg, grain, model.DECISION_FILE_NAME)
    gdir = log.parent
    if log.is_file():
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
    # The GRAIN's document, not the log's: a decisions.md declares no
    # `id:`, and the row belongs to the grain that made the choice.
    _stamp(cfg, _grain_file(cfg, gid), ledger.decision_row(gid, eid, title))
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


def _row_ledger(cfg: model.PmConfig, path: Path | None) -> Path:
    """The ledger this row belongs to: the milestone that owns the row's GRAIN,
    read from the grain's own document and from nothing else (D1).

    **No status is consulted on any write path.** The lookup this replaced
    asked which milestone was `in_progress` and refused on none and on several,
    so a tree mid-planning lost every row it wrote, silently.

    `path` is the row's grain document, or None when the row names none — a
    `gate` row, or a session nothing could attribute; those land grainless
    (D3). The caller passes the PATH because resolution also stamps `grain`,
    so the id a reader sees and the ledger it sits in cannot disagree.
    """
    if path is None:
        if not cfg.roadmap.is_dir():
            raise Refused(f'there is no PM tree at {cfg.rel(cfg.roadmap)}, so '
                          f'there is no ledger a row naming no grain belongs '
                          f'to; no row was written')
        return ledger.grainless_path(cfg.roadmap)
    found = _ledger_of(cfg, model.unquote(model.field_of(path, 'id')))
    if found is None:
        raise Refused(f'{cfg.rel(path)} names no milestone, so there is no '
                      f'ledger its row belongs to; no row was written')
    return found


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
        ledger.STORIES_IN_PROGRESS: [],
    }

    def add(snap: dict, bucket: str, path: Path) -> None:
        gid = model.unquote(model.field_of(path, 'id'))
        if gid:
            snap[bucket].append(gid)

    def in_progress(kind: str, status: str) -> bool:
        return model.category_of(cfg, kind, status) == model.IN_PROGRESS

    for _milestone in model.milestones(cfg):
        mfile = _milestone.path
        mstat = model.field_of(mfile, 'status')
        if in_progress('milestone', mstat):
            add(live, 'milestones_in_progress', mfile)
        if mstat == model.BUILDING:
            add(frozen, 'milestones_building', mfile)
        for ffile in model.feature_files(cfg, _milestone.gid):
            fstat = model.field_of(ffile, 'status')
            if in_progress('feature', fstat):
                add(live, 'features_in_progress', ffile)
            if fstat == model.BUILDING:
                add(frozen, 'features_building', ffile)
            elif fstat == model.REVIEWING:
                add(frozen, 'features_review', ffile)
            for sfile in model.story_files(
                    cfg, model.unquote(model.field_of(ffile, 'id'))):
                sstat = model.field_of(sfile, 'status')
                if in_progress('story', sstat):
                    add(live, ledger.STORIES_IN_PROGRESS, sfile)
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
    # `--from-transcript` and `--grain` answer two different questions and both
    # may be asked at once: the transcript is where the NUMBERS come from, and
    # `--grain` is what the work was ON. They were exclusive while a grain was
    # something a hand entry supplied; a dispatched agent is TOLD its grain in
    # the prompt that starts it, so the courier is copying a known fact rather
    # than guessing (D2), and refusing the pair is refusing the whole point of
    # the flag.
    source, grain = flags.get('--from-transcript'), flags.get('--grain')
    if not source and not grain:
        raise Usage('ledger record needs --from-transcript <path> (a hook run) '
                    'or --grain <id> (a hand entry), or both — a transcript '
                    'carries the numbers and --grain carries what they were '
                    'spent on')
    fields: dict[str, object] = {
        'session_id': flags.get('--session-id', ''),
        'agent_id': flags.get('--agent-id', ''),
        # Only ever the flag: the transcript does not carry the agent type.
        'agent_type': flags.get('--agent-type', ''),
        'tree': _tree_snapshot(cfg),
    }
    # Resolved BEFORE the row is built, because it is both the row's `grain`
    # and the row's address: one resolution, so the id a reader sees and the
    # ledger it sits in cannot disagree.
    gpath = _grain_file(cfg, grain) if grain else None
    if source:
        kind = _event_kind(_required(flags, '--event'))
        fields.update(_from_transcript(source, flags))
        if gpath is not None:
            # The id the GRAIN declares, not the string the caller typed —
            # `_ledger_id` is what every other row is stamped with, so two rows
            # naming one grain cannot spell it two ways.
            fields['grain'] = _ledger_id(gpath, grain)
        else:
            # A resolved grain ROUTES the row as well as naming it — one rule
            # (D1), whichever way the grain arrived.
            gpath = _resolved_grain_file(cfg, _grain_from_tree(fields['tree']))
            if gpath is not None:
                fields['grain'] = _ledger_id(gpath, '')
    else:
        kind = _event_kind(flags.get('--event', 'SubagentStop'))
        fields.update(_by_hand(gpath, grain, flags))
    row = ledger.usage_row(kind, **fields)
    target = _row_ledger(cfg, gpath)
    try:
        ledger.append_to(target, row)
    except OSError as err:
        raise Usage(f'{cfg.rel(target)} could not be appended '
                    f'to ({err}); no row was written') from err
    _ok(f'ledger {kind} row appended to {cfg.rel(target)}')
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
    # A tree with nowhere to file a gate row is a TRUE and unremarkable
    # fact, and reporting it as a REFUSAL made every gate of every run
    # print `the recorder exited 1`, which reads as a broken install
    # (0.3.0 review X1). Information, not a failure: one line on stderr,
    # exit 0, no row.
    #
    # 0.4.0/D3 narrows WHEN that happens to one case. A gate row names no
    # grain, so it lands in the tree's own ledger — there is no plan to
    # consult and no milestone to pick, and the only way to have nowhere
    # to file is to have no PM tree at all.
    if not cfg.roadmap.is_dir():
        print(f'[pm] no gate row filed — there is no PM tree at '
              f'{cfg.rel(cfg.roadmap)}', file=sys.stderr)
        return 0
    target = _row_ledger(cfg, None)
    try:
        ledger.append_to(target, ledger.gate_row(gate, verdict, duration,
                                                 census))
    except OSError as err:
        raise Usage(f'{cfg.rel(target)} could not be appended '
                    f'to ({err}); no row was written') from err
    _ok(f'ledger gate row appended to {cfg.rel(target)}')
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


def _resolved_grain_file(cfg: model.PmConfig, gid: str) -> Path | None:
    """The document for a grain the VERB resolved, or None.

    A refusal here would be a row lost to a lookup nobody asked for, so an id
    that will not resolve is treated as no resolution at all: the key is
    omitted and the row lands in `rows naming no grain`, which is a bucket
    somebody can read. `--grain` is the opposite case and still refuses — a
    caller who named a grain must be told the name is wrong.
    """
    if not gid:
        return None
    try:
        return _grain_file(cfg, gid)
    except (Usage, model.AmbiguousStory) as err:
        # BOTH, and the second is why this is not `except Usage`.
        # `model.story_file` raises `AmbiguousStory`, a plain `Exception`, when
        # two files claim one id — so a tree with a duplicated id turned a
        # lookup nobody asked for into exit 2 with NO ROW WRITTEN ANYWHERE,
        # which is the fail-open promise the couriers depend on, broken by the
        # convenience that was meant to help.
        #
        # And it SAYS SO (W4): the ambiguous branch already speaks, and a
        # single candidate that will not resolve was the silent third case.
        print(f'[pm] the tree named a grain this verb could not resolve '
              f'({err}) — the row is filed without one and lands in `rows '
              f'naming no grain`; `agentic-sdlc check pm` reports the tree '
              f'defect', file=sys.stderr)
        return None


def _grain_from_tree(snap: dict) -> str:
    """The grain a row with no `--grain` is about, or `''` — D2's fallback.

        exactly one story in progress   use it
        none                            omit the key
        several                         omit the key, and NAME the candidates

    The orchestrator's path: an agent nobody dispatched has no prompt to read a
    grain out of. **Read off the row's OWN `tree` snapshot**, so the grain a row
    names and the tree it recorded cannot disagree, and **stories only** —
    billing a container for a session is the same guess one level coarser.

    **An unresolvable grain is an OMITTED KEY**, never a guess: a row filed
    against the wrong story is uncorrectable, one filed against none is visible
    in a bucket that already exists.
    """
    live = snap.get(ledger.STORIES_IN_PROGRESS) or []
    if len(live) == 1:
        return live[0]
    if len(live) > 1:
        print(f'[pm] {len(live)} stories are in progress '
              f'({" ".join(live)}) — which one this row is about is not '
              f'something this verb may pick, so the row names none of them '
              f'and lands in `rows naming no grain`. Pass --grain <id> from '
              f'the dispatch (GDK_LEDGER_GRAIN) to attribute it',
              file=sys.stderr)
    return ''


def _by_hand(path: Path, grain: str, flags: dict[str, str]) -> dict:
    """The hand form's fields, over the already-resolved grain document —
    `--grain` resolves through `_grain_file` in the caller, because a typo'd id
    in a ledger row is a lie nothing downstream can check, and because the same
    path is what routes the row.
    """
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


def _grain_kind(cfg: model.PmConfig, gid: str) -> str:
    """Which vocabulary an id answers to — the kind the GRAIN declares.

    It used to count slashes, which is the nested id shape: every pooled id
    read as a milestone, so `open_seconds` asked the milestone vocabulary
    whether a feature had finished. Harmless while two flows share a `done`
    word, and a growing age beside `[shipped]` when they do not.
    """
    return model.kind_of(cfg, gid)


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
    owner = _ledger_of(cfg, model.unquote(model.field_of(path, 'id')) or gid)
    if owner is None:
        raise Usage(f'{cfg.rel(path)} names no milestone, so no ledger owns '
                    f'{gid!r}')
    # Both spellings: the id the caller typed and the id the file claims, which
    # is what `_stamp` wrote.
    names = {gid, _ledger_id(path, gid)}
    # BOTH ledgers, the same pair `ledger report` reads. The milestone's holds
    # every attributed row; the tree's holds the rows that named no grain
    # (D3) — and one of those can still NAME this grain through its `tree`
    # snapshot, which `row_names` reads. Reading only the first made `show` and
    # `report` disagree about the same row: `report` billed the story for it
    # and `show` printed `no rows`. D3's argument against per-feature ledgers
    # rests on this verb answering.
    files = [owner]
    grainless = ledger.grainless_path(cfg.roadmap)
    if grainless not in files:
        files.append(grainless)
    try:
        rows = [r for f in files for r in ledger.read_rows(f)
                if ledger.row_names(r.data, names)]
    except ledger.LedgerError as err:
        raise Usage(f'{err}') from err
    # Two files, one timeline: `show` subtracts consecutive status stamps, so
    # rows read in file order would produce negative gaps the moment a
    # grainless row falls between two of them.
    rows.sort(key=lambda r: str(r.data.get('ts') or ''))
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
    total = ledger.total_seconds(cfg, _grain_kind(cfg, gid), status)
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
                    else _report_default_dir(cfg))
        # `mdir` is the milestone's DOCUMENT since 0.4.0 — a pooled tree has
        # no per-milestone directory — so the id comes off it directly and the
        # ledger is addressed by that id. Both joins are asked of `src`: a rev
        # read that asked today's disk would look for a retired milestone's
        # rows in the layout the retire left behind.
        mid = _ledger_id(src.milestone_doc(mdir), mdir.stem, src)
        path = src.ledger_for(cfg, mid)
        # Two files, one report. The milestone's ledger holds every ATTRIBUTED
        # row; the tree's root ledger holds the rows that name no grain (D3),
        # which is where `gate` and `test` rows live by construction. Reading
        # only the first would empty the `rows naming no grain` bucket and the
        # gate-cost section for every milestone — the report going quiet about
        # rows that exist, which is rule 4's first sin.
        root = ledger.grainless_path(cfg.roadmap)
        try:
            rows = src.ledger_rows(path)
            if root != path:
                rows += src.ledger_rows(root)
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
    if not src.is_file(path) and not src.is_file(root):
        # No ledger is a fact about section 1 only; sections 2 and 4 read other
        # documents, so the report still prints when those hold something.
        print(f'{report.HEADING_PREFIX} {report.heading_id(data)} — '
              f'{report.NO_LEDGER}')
        if not report.beyond_ledger(data):
            return 0
    for line in report.render(cfg, data):
        print(line)
    return 0


def _report_milestone_dir_at(cfg: model.PmConfig, src: report.GitSource,
                             mid: str) -> Path:
    """The milestone's handle at a rev, or exit 2 naming what is not there —
    its document in the pool, or the `<mid>-*` directory a rev from before
    the migration holds. A rev after the retirement is the ordinary mistake,
    so the message says which rev to reach for.
    """
    if not model.segment_is_literal(mid):
        raise Usage(f'no milestone resolves from id {mid!r} — the ledger is '
                    f'per milestone (D6), so {FROM_FLAG} reports a milestone '
                    f'id (`0.23.0`) and never a feature, story or bug')
    mdir = src.milestone_dir(cfg, mid)
    if mdir is None:
        # Named in the layout THAT REV is in: naming a directory the pools
        # replaced sends the reader looking for one nobody has.
        raise Usage(f'{_report_nothing_declares(cfg, src, mid)} — a milestone '
                    f'is retired at the close AFTER its own, so name the rev '
                    f'it was still in the tree at (usually its release tag)')
    doc = src.milestone_doc(mdir)
    if not src.is_file(doc):
        raise Usage(f'{src.spec(doc)} is not there, so {mid!r} is a directory '
                    f'at {src.rev} and not a milestone')
    return mdir


def _report_nothing_declares(cfg: model.PmConfig, src: report.GitSource,
                             mid: str) -> str:
    """Where the rev was looked in, and what was not there."""
    if src.is_pooled(cfg):
        pool = src.spec(model.pool_dir(cfg, 'milestone'))
        return f'no document in {pool} declares `id: {mid}`'
    return (f'no milestone directory {mid}-* under {cfg.roadmap_dir}/ or '
            f'{cfg.roadmap_dir}/{model.ARCHIVE_DIR_NAME}/ at {src.rev}')


def _report_default_dir(cfg: model.PmConfig) -> Path:
    """Which milestone a bare `ledger report` is ABOUT — the current release's,
    from `order` plus `[pm] version_at`.

    Not a routing rule and not `_row_ledger`'s twin: no row is placed by
    this, and nothing here decides where anything is written (D1/D7). It
    answers a MISSING ARGUMENT from the plan, which is the same act as
    `pm next`, and it refuses with the plan's own words when the plan cannot
    answer.
    """
    mdir, why = model.release_milestone(cfg)
    if mdir is None:
        raise Usage(f'{why}{REPORT_HINT}')
    return mdir


def _report_milestone_dir(cfg: model.PmConfig, mid: str) -> Path:
    """The directory of an explicitly named milestone, or exit 2; a feature or
    story id is the wrong noun, since the ledger is per milestone.
    """
    # `_grain_file` first, so an id that resolves to nothing gets the ONE
    # refusal every verb gives it — the shared grammar and the shared
    # sentence — rather than a second wording invented here.
    _grain_file(cfg, mid)
    grain = model.grain_index(cfg).get(mid)
    if grain is None:
        raise Usage(f'no grain resolves from id {mid!r}')
    if grain.kind != 'milestone':
        raise Usage(f'{mid!r} is a {grain.kind}, not a milestone — the '
                    f'ledger is per milestone (D6), so name one (or run it '
                    f'bare for the current release\'s)')
    return grain.path


# --- dispatch -----------------------------------------------------------------
_PLAN_SCAFFOLD = """---
id: roadmap
kind: roadmap
order:
---

# The release plan

The order releases ship in. It is a DECISION, not a sort: `order` lists the
MILESTONE IDS, in sequence, and each milestone's own `version:` says which
release it is — so a milestone that re-versions never touches this file.

`agentic-sdlc pm add <this-id> <milestone-id>` schedules one, exactly as it
sequences a feature under a milestone or a story under a feature. Authoring and
scheduling stay separate acts: a milestone declares `version:` without joining
the plan.
"""


def _plan_path(cfg: model.PmConfig) -> Path:
    return model.releases_file(cfg)


def _mint_plan(cfg: model.PmConfig) -> Path:
    """The plan document, created from the scaffold if this is the first entry."""
    path = _plan_path(cfg)
    if not path.is_file():
        # Through `core.apply`, like every other mutation.
        apply.raise_on_error(apply.make_dir(path.parent))
        model.write_raw(path, _PLAN_SCAFFOLD)
    return path


def _resolve(cfg: model.PmConfig, gid: str, role: str) -> model.Grain:
    """One id to its grain, or exit 2 naming which argument."""
    defect = model.id_defect(gid)
    if defect:
        raise Usage(f'the {role} id {gid!r} names no grain — {defect}')
    found = model.grain_index(cfg).get(gid)
    if found is None:
        raise Usage(f'no grain resolves from the {role} id {gid!r}')
    return found


def _parent(cfg: model.PmConfig, gid: str) -> tuple[model.Grain, bool]:
    """(the parent grain, whether the plan has to be minted for it) — the ROOT
    does not exist until something is scheduled."""
    if model.root_grain(cfg) is None and gid == model.ROOT_ID:
        return model.Grain(gid=gid, kind=model.ROOT_KIND,
                           path=model.releases_file(cfg)), True
    return _resolve(cfg, gid, 'parent'), False


def _sequence(cfg: model.PmConfig, parent: model.Grain) -> list[str]:
    """The parent's declared `order`, refusing a list this writer cannot rewrite."""
    defect = model.sequence_defect(parent.path)
    if defect:
        raise Refused(f'{cfg.rel(parent.path)} {defect} — nothing was written')
    return model.list_field_of(parent.path, model.ORDER_KEY)


def _placed(entries: list[str], child: str, where: tuple[str, str],
            rel: str) -> list[str]:
    """`entries` with `child` at the asked-for place — the LIST INSERT, and the
    whole of what `add` does beyond `set`."""
    rest = [gid for gid in entries if gid != child]
    flag, value = where
    if not flag:
        return rest + [child] if child not in entries else list(entries)
    if flag == '--position':
        try:
            at = int(value)
        except ValueError:
            raise Usage(f'--position takes a number, got {value!r}') from None
        if at < 1:
            raise Usage(f'--position counts from 1, got {at}')
        if at > len(rest) + 1:
            raise Refused(f'--position {at} is past the end: {rel} sequences '
                          f'{len(rest)} other(s), so 1..{len(rest) + 1} are '
                          f'the places — nothing was written')
        return rest[:at - 1] + [child] + rest[at - 1:]
    if value not in rest:
        raise Refused(f'{flag} {value!r} is not in {rel} `order` — nothing was '
                      f'written')
    at = rest.index(value) + (1 if flag == '--after' else 0)
    return rest[:at] + [child] + rest[at:]


PLACE_FLAGS = ('--position', '--before', '--after')


def _where(args: list[str]) -> tuple[list[str], tuple[str, str]]:
    """(the positional ids, the one placement flag and its value)."""
    ids: list[str] = []
    where = ('', '')
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith('-'):
            if arg not in PLACE_FLAGS:
                raise Usage(f'unknown flag {arg!r}')
            if i + 1 >= len(args):
                raise Usage(f'{arg} takes a value')
            if where[0]:
                raise Usage(f'{where[0]} and {arg} are two different places — '
                            f'one per invocation')
            where = (arg, args[i + 1])
            i += 2
            continue
        ids.append(arg)
        i += 1
    return ids, where


def cmd_add(cfg: model.PmConfig, args: list[str]) -> int:
    """Bind a child to a parent AND sequence it there — `set` plus a list
    insert, and nothing else. The KINDS come off the two ids, so one verb
    serves every level and `[pm.contains]` answers for all of them."""
    ids, where = _where(args)
    if len(ids) != 2:
        raise Usage(f'add takes <parent-id> <child-id>, got {len(ids)} id(s)')
    child = _resolve(cfg, ids[1], 'child')
    parent, mint = _parent(cfg, ids[0])
    if parent.gid == child.gid:
        raise Refused(f'{parent.gid} cannot hold itself')
    refusal = model.may_hold(cfg, parent.kind, child.kind)
    if refusal:
        raise Refused(f'{parent.gid} is a {parent.kind} and {child.gid} is a '
                      f'{child.kind}: {refusal} — nothing was written')
    # Minted only once every refusal above has passed: a verb that says no
    # leaves no file behind (hard rule 3).
    if mint:
        _mint_plan(cfg)
    rel = cfg.rel(parent.path)
    entries = _sequence(cfg, parent)
    placed = _placed(entries, child.gid, where, rel)

    # THE BIND — `set`, verbatim. A kind that binds to nothing (a milestone
    # under the root) is sequenced only: there is no field to write.
    bind = model.BINDS_TO.get(child.kind)
    wrote = []
    if bind is not None:
        field = bind[1]
        before = model.unquote(model.field_of(child.path, field))
        if before != parent.gid:
            if not model.set_field(child.path, field, parent.gid):
                raise Refused(f'{cfg.rel(child.path)} has no frontmatter block '
                              f'to put `{field}:` in — nothing was written')
            wrote.append(f'{child.gid}: {field} {before!r} -> {parent.gid!r}')
            if before:
                # Rule 11: `add` does not reach into a grain it was not given,
                # so it says what it left behind.
                wrote.append(f'  noticed: {before} still lists {child.gid} in '
                             f'its `order` — that entry is now DANGLING; '
                             f'`agentic-sdlc pm remove {before} {child.gid}` '
                             f'takes it out')

    # THE SEQUENCE — the parent's list, through the byte-honest writer.
    if placed != entries:
        if not model.set_list_field(parent.path, model.ORDER_KEY, placed):
            raise Refused(f'{rel} could not be rewritten — it has no '
                          f'frontmatter block'
                          + (f'; {"; ".join(wrote)} DID land'
                             if wrote else ', and nothing was written'))
        wrote.append(f'{parent.gid}: {child.gid} sequenced at position '
                     f'{placed.index(child.gid) + 1} of {len(placed)} in {rel}')
    for line in wrote:
        _ok(line)
    if not wrote:
        _ok(f'{parent.gid} already holds {child.gid} at position '
            f'{placed.index(child.gid) + 1} — nothing was written')
    return 0


def cmd_remove(cfg: model.PmConfig, args: list[str]) -> int:
    """Unbind a child AND unsequence it, together — the pair `add` writes,
    taken back. `pm set <id> <field> ""` still unbinds alone."""
    if len(args) != 2:
        raise Usage(f'remove takes <parent-id> <child-id>, got '
                    f'{len(args)} argument(s)')
    parent = _resolve(cfg, args[0], 'parent')
    child = _resolve(cfg, args[1], 'child')
    rel = cfg.rel(parent.path)
    entries = _sequence(cfg, parent)
    bind = model.BINDS_TO.get(child.kind)
    field = bind[1] if bind is not None else ''
    bound = (model.unquote(model.field_of(child.path, field))
             if field else '')
    elsewhere = bool(field and bound and bound != parent.gid)
    if elsewhere and child.gid not in entries:
        raise Refused(f'{child.gid} names {bound} as its {bind[0]}, not '
                      f'{parent.gid} — nothing was written')
    wrote = []
    if field and bound and not elsewhere:
        if not model.set_field(child.path, field, ''):
            raise Refused(f'{cfg.rel(child.path)} could not be rewritten — '
                          f'nothing was written')
        wrote.append(f'{child.gid}: {field} {bound!r} -> \'\'')
    if child.gid in entries:
        if not model.set_list_field(parent.path, model.ORDER_KEY,
                                    [g for g in entries if g != child.gid]):
            raise Refused(f'{rel} could not be rewritten'
                          + (f'; {"; ".join(wrote)} DID land'
                             if wrote else ', and nothing was written'))
        wrote.append(f'{parent.gid}: {child.gid} unsequenced from {rel}')
    for line in wrote:
        _ok(line)
    if elsewhere:
        # The DANGLING entry, cleared. The binding is NOT touched: it names a
        # parent this command was not given, and reaching into it is the thing
        # `add` refuses to do too.
        _ok(f'  noticed: {child.gid} stays bound to {bound}; only '
            f'{parent.gid}\'s entry was removed')
    if not wrote:
        _ok(f'{parent.gid} does not hold {child.gid} — nothing was written')
    return 0


# `pm roadmap`'s columns IN ORDER, spelled once for the rows and the `--help`
# line. `name` and `summary` are here because a RETIRED release has to print
# fully — version, name, one sentence — and the consumer deleting a
# hand-maintained ROADMAP.md has nowhere else to read those from.
ROADMAP_COLUMNS = ('version', 'milestone', 'state', 'name', 'summary')

# The state cell for a plan entry naming no grain in the tree. R1 calls the
# pair UNVERIFIABLE because the tree could not tell a retirement from a
# milestone nobody wrote; a `retire` row is the tree telling them apart.
RETIRED_STATE = 'retired'
DANGLING_STATE = 'DANGLING'


def _roadmap_row(cells: tuple[str, ...]) -> str:
    """One plan row, tab-separated, `-` for an empty cell so a shell `read`
    gets a fixed column count. A tab inside free text would forge a column."""
    return '\t'.join((cell or DASH).replace('\t', ' ') for cell in cells)


def cmd_roadmap(cfg: model.PmConfig, args: list[str]) -> int:
    """The plan: every scheduled milestone, then the backlog. Writes nothing —
    what `pm status` does for one milestone, for the SEQUENCE, and what
    replaced the hand-maintained `ROADMAP.md`.

    A retired entry prints from its `retire` row in the tree's own
    `ledger.jsonl`, which is the only copy of a shipped release's version, name
    and summary once its documents are gone.
    """
    if args:
        raise Usage(f'roadmap takes no arguments, got {" ".join(args)}')
    entries = model.declared_order(cfg)
    path = model.releases_file(cfg)
    defect = model.plan_defect(cfg)
    if defect is not None:
        raise Refused(f'{cfg.rel(path)} {defect}')
    try:
        retired = ledger.retired_releases(cfg)
    except ledger.LedgerError as err:
        raise Usage(f'{err}') from err
    if not entries:
        print(f'[pm] {cfg.rel(path)} declares no order — '
              f'`agentic-sdlc pm add {model.root_id(cfg)} <milestone-id>` '
              f'starts the plan')
    else:
        print(f'[pm] {len(entries)} scheduled release(s) in {cfg.rel(path)}')
        for mid in entries:
            mfile = model.milestone_file(cfg, mid)
            if mfile is None:
                row = retired.get(mid, {})
                print(_roadmap_row((
                    row.get('version', ''), mid,
                    RETIRED_STATE if row else DANGLING_STATE,
                    row.get('name', ''), row.get('summary', ''))))
                continue
            version = model.milestone_version(cfg, mid)
            state = ('shipped' if model.entry_is_shipped(cfg, mid)
                     else model.field_of(mfile, 'status') or DASH)
            print(_roadmap_row((version or NO_VERSION, mid, state,
                                model.unquote(model.field_of(mfile, 'name')),
                                '')))
    scheduled = set(entries)
    backlog = sorted(mid for _, mid in model.known_milestones(cfg)
                     if mid and mid not in scheduled)
    if backlog:
        print(f'[pm] {len(backlog)} in backlog (on no plan — not scheduled '
              f'as a release)')
        for mid in backlog:
            mfile = model.milestone_file(cfg, mid)
            print(_roadmap_row((
                model.milestone_version(cfg, mid), mid,
                model.field_of(mfile, 'status') if mfile else '',
                model.unquote(model.field_of(mfile, 'name')) if mfile else '',
                '')))
    return 0


def cmd_next(cfg: model.PmConfig, args: list[str]) -> int:
    """The first entry in `order` that has not shipped, and what it claims."""
    if args:
        raise Usage(f'next takes no arguments, got {" ".join(args)}')
    entries = model.declared_order(cfg)
    if not entries:
        print(f'[pm] {cfg.rel(_plan_path(cfg))} declares no order — '
              f'`agentic-sdlc pm add {model.root_id(cfg)} <milestone-id>` '
              f'starts the plan')
        return 0
    # ONE resolver. `pm next` answering differently from what `release` and the
    # ledger resolve, over the same tree, is two scoreboards (review B1).
    mid = model.current_milestone(cfg)
    if mid is None:
        dangling = [g for g in entries if model.entry_is_dangling(cfg, g)]
        if dangling:
            print(f'[pm] every release in {cfg.rel(_plan_path(cfg))} has '
                  f'shipped; {len(dangling)} entry/ies are DANGLING (they name '
                  f'no milestone in the tree): {", ".join(dangling)}')
        else:
            print(f'[pm] every release in {cfg.rel(_plan_path(cfg))} has shipped')
        return 0
    mfile = model.milestone_file(cfg, mid)
    print(f'{model.milestone_version(cfg, mid) or NO_VERSION}\t{mid}\t'
          f'{model.field_of(mfile, "status") if mfile else ""}')
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(USAGE)
        return 0 if argv else 2
    try:
        cfg = model.load()
    except model.ConfigError as err:
        # EVERY defect, flow first — one line each, exit 2 once. `load()` stops
        # at the first, and the first is rarely the one that matters: the tree
        # that motivated this was told about a retired key while its PM CLI was
        # refusing every work-moving verb for want of a flow (review D1).
        try:
            defects = model.all_config_defects()
        except Exception:  # noqa: BLE001 - the collector never masks the error
            defects = []
        for msg in defects or [str(err)]:
            print(f'[pm] ERROR — {msg}', file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    # Deferred: `ready_for` and `skills` import this module's shared
    # vocabulary, so binding at call time keeps load order a non-question.
    from agentic_sdlc.repo.pm import ready_for, skills
    table = {
        'ready-for': ready_for.cmd_ready_for,
        'story': cmd_story, 'bug': cmd_bug, 'feature': cmd_feature,
        'milestone': cmd_milestone, 'retire': cmd_retire,
        'status': cmd_status, 'list': cmd_list, 'new': cmd_new,
        'validate': cmd_validate, 'install-skills': skills.cmd_install_skills,
        'init': skills.cmd_init, 'set': cmd_set, 'get': cmd_get,
        'rename': cmd_rename,
        'templates': skills.cmd_templates,
        'vocabulary': cmd_vocabulary, 'decide': cmd_decide,
        'config': skills.cmd_config,
        'ledger': cmd_ledger, 'add': cmd_add, 'remove': cmd_remove,
        'next': cmd_next, 'roadmap': cmd_roadmap,
    }
    fn = table.get(cmd)
    if fn is None:
        # A retired verb is named with where it WENT. "Unknown command" reads
        # as a typo, and a consumer whose Makefile still calls one would go
        # looking for a misspelling instead of for the replacement.
        if cmd in RETIRED_COMMANDS:
            print(f'{PROG}: {cmd} was retired — {RETIRED_COMMANDS[cmd]}',
                  file=sys.stderr)
            return 2
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
