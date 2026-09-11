"""cli.py — the `pm` router, and the verbs it owns: create, move, bind, read, record.

A STATUS verb validates the target against the grain's declared flow, writes
only the `status:` line (plus `reviewed:` on a feature close), preserves every
other byte, and is idempotent; every question is asked of a status's category,
never of the word, and there is no transition graph — `check pm` reports the
end state. Exit 0 ok · 1 refused, nothing written · 2 usage.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from agentic_sdlc.core import apply, frontmatter
from agentic_sdlc.core.config import pointer_escapes
from agentic_sdlc.repo.pm import (arrive, inventory, ledger, rename, report,
                                  templates, validate, vocabulary)

PROG = 'agentic-sdlc pm'

USAGE = """usage: agentic-sdlc pm <command>

Every question asked of a status is asked of its CATEGORY — todo, in_progress
or done — never of the word. Which words sit in which category is this
project's [pm.states.<kind>] in devkit.toml, written by `pm init` and read
every run; a state the project never declared is refused by name.

THERE IS ONE EVENT HERE AND IT IS ARRIVAL: a grain reaches a state. Every
`<kind> <status> <id>` write is one, and an arrival writes the status, asks the
question [pm.arrive.<kind>.<status>] declares with both answers already typed,
records the answer (or `none`), names the installed capabilities that table
binds to the state, and reports the tree's open work. All of it on STDERR, all
of it derived, none of it a refusal. There is no transition table: the unit is
the state ARRIVED AT, never the pair, so a move backwards is a move like any
other. `[pm] pressure = false` silences the fork and the census; `[pm]
breadcrumbs = false` silences `next:` and `have:`; the ROW is written either
way. `pm config --seed` shows the whole declaration with an example.

  <kind> <status> <id> [<answer>...]      (an ANSWER is whichever flag
                                           [pm.arrive.<kind>.<status>] answers
                                           declares — `--by agent <type>`,
                                           `--skip review "<why>"`, whatever
                                           this project chose. It is recorded
                                           as a claim and never verified; a
                                           flag the state does not declare is
                                           refused naming the ones it does, and
                                           a move with no answer still writes
                                           and records `none`)

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
  retire <milestone-id> --version <ver> --name <name> [<summary...>]
         [--dry-run]
                                          (the BACKFILL form, for a milestone
                                           pruned before retire filed rows: no
                                           document is left to read, so YOU
                                           supply the version and the name,
                                           both required, and the row is marked
                                           `backfilled: true` so it never reads
                                           as a recorded retirement. Accepted
                                           ONLY for an id no grain in the tree
                                           claims — one that is there is refused
                                           naming the form above. The same
                                           backfill twice is one row; a
                                           different one supersedes a
                                           backfilled row and never a recorded
                                           one. `pm roadmap` prints it
                                           `retired` once the id is in `order`)
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
                                           feature and `caused_by` for a bug.
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
  set <grain-id> <key> <value>            (write one frontmatter field. NOT
                                           status (a move) and NOT order (a
                                           block list `add`/`remove` own). A
                                           list-shaped field — depends_on,
                                           consumed_by — is written AS the
                                           inline list `check pm` grades, so a
                                           bare id, a comma-separated pair and
                                           ["a", "b"] all land as ["a", "b"]
                                           and an empty value as [])
  rename <old-id> <new-id>                (rewrite the grain's own `id:` AND
                                           every inbound reference in the tree
                                           — depends_on, consumed_by, reviewed,
                                           caused_by,
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
  install-skills [--force] [--diff] [<path>...]
                                          (write the shared rule + operations skill;
                                           a file [adopt] ours claims is left
                                           alone and named — name its path to
                                           take it)
  init                                    (scaffold a fresh tree + install guidance)
  new milestone <slug> <name...> [--version <ver>]
                                          (mints id `ms-<slug>` — the kind
                                           prefix and the slug you typed, and
                                           NOTHING ELSE. THE SLUG IS A NAME,
                                           NOT A VERSION: --version is where a
                                           version goes, stamped on `version:`,
                                           the field `pm next`, `pm roadmap`
                                           and R5 read, and a milestone with
                                           none is BACKLOG rather than a
                                           finding. Typing the version as the
                                           slug is how `ms-0.6.0` got minted
                                           and hand-renamed. A parent is a
                                           binding, never identity, so it is
                                           not in an id and re-parenting stays
                                           one `pm set`. <name...> is REQUIRED
                                           to create; give an id already in the
                                           tree and omit it to fill missing
                                           slots instead — that path is
                                           idempotent, --version re-stamped
                                           with the same value is a no-op, and
                                           a shared doc appears on first WRITE)
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
  new bug <milestone> <slug> [<name...>] [--caused-by <feature-id>]
                                          (mints `bg-<slug>`; <milestone> is the
                                           PARENT, written to `milestone:`
                                           alone; it must close before the
                                           milestone does, and `pm remove`
                                           returns it to the pool. <name...>
                                           is stamped on `name:` after the
                                           render, so a template with no
                                           {name} slot still gets it; omitted,
                                           `name:` is left empty and a `next:`
                                           line names it. A bug is ONE
                                           authored file: a second `new bug`
                                           for its id refuses and writes
                                           nothing — `pm set <bug-id> name` is
                                           the edit.
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
  ledger record --grain <id> [--agent-type T] [--tokens-in N] [--tokens-out N |
                --tokens-total N] [--tool-calls N] [--duration-s N] [--event E]
                                          (hand entry for a dispatch no hook
                                           saw; a number not given is a key the
                                           row does not carry, never a zero.
                                           --tokens-total is what a subagent
                                           completion actually reports — ONE
                                           number — and it lands in its own
                                           `tokens_total` key: `ledger report`
                                           sums it in the `tokens_total`
                                           column, never into `in`/`out`, and
                                           says how many rows reported which
                                           beside the summary that sums the
                                           split. It is EXCLUSIVE
                                           with the split flags and with
                                           --from-transcript, because a row
                                           carrying both can disagree with
                                           itself. It is not evidence a courier
                                           ran: `check pm` U4 wants a
                                           session_id too)
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
                                           grain's rows oldest first, columns
                                           IN ORDER:
                                             ts  kind  <what the kind says>
                                           a `status` row says
                                           `<from> -> <to>  +<n>s` since the
                                           previous one; a `disposition` says
                                           `<state>  <answer> [<value>]` and
                                           then `skipped: <check> — "<why>"`
                                           for every check a belt answered
                                           instead of asking; a `lesson` says
                                           `<rule>  <text>  (source: <path>)`,
                                           and `agentic-sdlc lesson show
                                           --grain <id>` is the verb that
                                           filters those. --json prints the
                                           raw lines. Reads the grain's
                                           milestone ledger AND the tree's, so
                                           it and `ledger report` cannot
                                           disagree about a row)
  ledger report [<grain-id>...] [--json] [--from <rev>]
                                          (THE TELEMETRY REPORT — token spend,
                                           tool calls, wall-clock and gate cost,
                                           per grain, from rows the tree already
                                           recorded. Ask this before writing a
                                           table of timings by hand.
                                           Spend per grain from that milestone's
                                           rows: dispatches, tokens, tool calls,
                                           wall-clock and seconds in each
                                           CATEGORY (todo / in_progress / done),
                                           per story/feature/bug. `in`/`out`
                                           are the MEASURED split; a row that
                                           reported one number instead is summed
                                           in `tokens_total` and folded into
                                           neither, and the summary line says
                                           how many did. With no id it
                                           reports the CURRENT release's
                                           milestone (`pm next`'s answer, from
                                           the plan) — the rows themselves are
                                           routed by their grain, never by a
                                           status. Never exits non-zero on a
                                           number.
                                           A MILESTONE id reports all of it; a
                                           feature or story id reports the clock
                                           at that level — that grain and its
                                           descendants, rolled — since the LEVEL
                                           is the id's and the ledger is still
                                           the milestone's.
                                           MORE THAN ONE MILESTONE ID COMPARES
                                           THEM, which is the comparative
                                           question this verb exists for: every
                                           block below gets one row per
                                           milestone and a `delta` row,
                                           `last - first`, marked * where the
                                           census under it moved — `gate cost`'s
                                           own arithmetic, across grains instead
                                           of within one. WHICH milestones is
                                           yours to name; the plan's `order`
                                           SEQUENCES the ids you gave when it
                                           holds every one of them, and the
                                           heading says `plan` or `given` so the
                                           basis is never guessed at.
                                           `--json` then prints ONE JOINED
                                           document — {"milestones": [<id>...],
                                           "order": plan|given, "blocks":
                                           [{"block", "columns", "census",
                                           "moved", "note", "rows", "delta"}]} —
                                           rather than a nested report per
                                           milestone for you to join by hand.
                                           ONE id still prints that nested
                                           document, byte for byte.
                                           Two blocks carry the SAME rows under
                                           every milestone and say so on the
                                           line: a gate row and an unattributed
                                           row names no grain, so both live in
                                           the tree's ledger and both deltas are
                                           0 by construction.
                                           Refused at exit 2: one id named
                                           twice, a feature or story id beside
                                           another id, and --from with more than
                                           one.
                                           EVERY BLOCK IT PRINTS, in print order.
                                           A (heading) carries a census rather
                                           than a table, and those same words
                                           are its row in the comparison, so
                                           this is one roster and not two —
                                           columns IN ORDER:
                                             spend per grain (heading)
                                               dispatch_rows status_rows
                                               grains
                                             story / feature / bug
                                               grain size dispatches in out
                                               cache_create cache_read
                                               tokens_total tool_calls
                                               duration_s todo in_progress
                                               done total_s
                                             time per state
                                               grain <state>_s closed_s
                                               open_s open_state
                                             time per actor
                                               actor arrivals grains seconds
                                             rows naming no grain
                                               dispatches in out
                                               cache_create cache_read
                                               tokens_total tool_calls
                                               duration_s
                                             yield per review pass (heading)
                                               records passes findings
                                             verdict
                                               feature record pass verdict
                                               findings landed rejected
                                               deferred open
                                             findings by severity
                                               feature pass severity
                                               findings
                                             deferred to
                                               target feature pass findings
                                             rework (heading)
                                               passes
                                             verdict distribution
                                               verdict passes
                                             escapes (heading)
                                               bugs features
                                             bugs naming a cause
                                               caused_by bug status
                                               feature_status
                                             overhead shape (heading)
                                               dispatch_rows decision_rows
                                               session_rows
                                             story
                                               story dispatches
                                               before_first_write calls
                                             decisions per grain
                                               grain decisions
                                             decision to next status row
                                               grain entry ts next_status_s
                                             session deltas
                                               session_id ts out tool_calls
                                             gate cost (heading)
                                               rows gates incomparable
                                               unusable
                                             gate
                                               gate runs first_ms last_ms
                                               delta_ms census
                                             rows this section could not use
                                               gate why ts
                                             milestone comparison (heading)
                                               milestones order blocks
                                               marked
                                           `<state>_s` is one column per state
                                           this milestone's rows HELD, so
                                           `… | awk` is the filter and no flag
                                           is grown for a sum.
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


# The checks a BELT answered with `--skip`, handed to the arrival its write
# makes: one arrival, one row, and the skip is a field on it (0.5.0/D6). Only
# a verb that ARRIVES can carry them.
Skipped = Sequence[tuple[str, str]]
ARRIVES = (vocabulary.GRAIN_STORY, vocabulary.GRAIN_BUG, vocabulary.GRAIN_FEATURE,
           vocabulary.GRAIN_MILESTONE)


def _skipped_defect(cmd: str, skipped: Skipped) -> str:
    """'' when these answered checks have an arrival to be recorded on, else
    why not. A skip dropped in silence would be the record `--skip` exists to
    make, missing.
    """
    if not skipped:
        return ''
    if cmd not in ARRIVES:
        return (f'{cmd!r} arrives nowhere, so there is no disposition row for '
                f'{", ".join(repr(c) for c, _ in skipped)} to be a field on — '
                f'the verbs that arrive are {", ".join(ARRIVES)}')
    for check, why in skipped:
        defect = ledger.reason_defect(why)
        if defect:
            return f'the answer given for {check!r} is not a reason: {defect}'
    return ''


class Refused(Exception):
    """A precondition said no. Exit 1."""


class Usage(Exception):
    """Bad arguments, or an id that resolves to nothing. Exit 2."""


def _ok(msg: str) -> None:
    print(f'[pm] {msg}')


# WHICH BELT CLOSES WHICH GRAIN, and the derivation that reads it, live in
# `arrive.py`: one `derive_next` feeds the printed breadcrumb and the emitted
# `rung.leave` row, so a change reaching one and not the other cannot happen.


def _unresolved(cfg: vocabulary.PmConfig, kind: str, gid: str, hint: str = '') -> Usage:
    """The refusal for an id that resolves to nothing, carrying the damage. A
    grain is found by `id:`, so a document whose frontmatter cannot be read is
    in no index and "no story resolves from id" is true and useless — those
    documents are listed by path, so the fix is the next thing read."""
    parts = [f'no {kind} resolves from id {gid!r}']
    if hint:
        parts.append(f'({hint})')
    try:
        damaged = inventory.unkeyed_documents(cfg)
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
    defect = inventory.id_defect(value)
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


def _mint(cfg: vocabulary.PmConfig, path: Path, body: str) -> None:
    """Write one new grain file, turning a filesystem refusal into a REFUSED
    rather than a traceback under exit 1.
    """
    try:
        templates.write(path, body)
    except OSError as err:
        raise Refused(f'{cfg.rel(path)} could not be written ({err}) — nothing '
                      f'was written; shorten the slug, or make '
                      f'{cfg.rel(path.parent)}/ writable') from err


def _was(grain: inventory.Grain) -> str:
    """The status a grain currently carries, for the message only; the verb
    never gates on it, so a hand-edited word is repaired rather than
    refused. `(none)` when absent.
    """
    return grain.field(vocabulary.FIELD_STATUS) or '(none)'


def _set_status(cfg: vocabulary.PmConfig, grain: inventory.Grain, value: str,
                note: str = '') -> None:
    """Write the `status:` line and validate nothing; every caller has already
    asked `_movable`.
    """
    if not frontmatter.set_field(grain.path, vocabulary.FIELD_STATUS, value):
        raise Usage(f'could not rewrite status in {cfg.rel(grain.path)} '
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
    return reader.field_of(path, vocabulary.FIELD_ID) or fallback


def _ledger_of(cfg: vocabulary.PmConfig, gid: str) -> Path | None:
    """The ledger file a grain's row belongs in, followed through its
    bindings — a story to its feature to its milestone (D1). None when the
    grain names no milestone, which is the row that lands at the root. The two
    hops live in `ledger.ledger_of_grain` because `repo/emit.py` routes its
    events the same way, and one question with two answers is what a lookup
    was once spent deleting."""
    return ledger.ledger_of_grain(cfg, gid)


def _stamp(cfg: vocabulary.PmConfig, grain: inventory.Grain, *rows: dict) -> None:
    """Append rows to the ledger of the milestone that owns `grain`. Never
    raises and never changes an exit code; a missing row is said on stderr.
    Varargs because ONE arrival mints two rows — the status and its
    disposition — and the ledger is resolved once for both: a grain no
    milestone owns is one WARNING about the event, not one per row."""
    target = _ledger_of(cfg, grain.field(vocabulary.FIELD_ID))
    if target is None:
        print(f'[pm] WARNING — no milestone owns {cfg.rel(grain.path)}, so '
              f'no {ledger.LEDGER_FILE_NAME} row was appended for it; the '
              f'write itself landed', file=sys.stderr)
        return
    for row in rows:
        try:
            ledger.append_to(target, row)
        except OSError as err:
            print(f'[pm] WARNING — {cfg.rel(target)} could not be '
                  f'appended to ({err}); the write itself landed, but this '
                  f'transition is NOT in the ledger', file=sys.stderr)
            return


def _arrived(cfg: vocabulary.PmConfig, kind: str, grain: inventory.Grain, gid: str,
             frm: str,
             to: str, said: 'arrive.Said' = arrive.NOTHING,
             skipped: Skipped = ()) -> None:
    """THE ONE EVENT — a grain reached a state, and everything else reads it.
    The status is already on disk when this runs and nothing here can change it
    or the exit code: an arrival RECORDS and REPORTS. The disposition row lands
    BEFORE the census, so the grain just answered is not counted as unanswered
    on its own write, and it carries `skipped` because a belt's close is an
    arrival like any other (0.5.0/D6).

    **A no-op is not an arrival**: nothing transitioned, so no `status` row,
    and a bare re-run may not replace an ANSWERED state's disposition with
    `none` — every reader takes the LAST row per (grain, state), so that
    write would look legitimate and not be (rule 4). With an answer it still
    records: that is how a skipped fork is answered.
    """
    lid = _ledger_id(grain.path, gid)
    moved = frm != to
    # One clock read for both rows: a pair straddling a second is two events.
    stamp = ledger.utc_now()
    answered = bool(said) or (not moved and arrive.answered_at(cfg, lid, to))
    rows = [ledger.status_row(lid, frm, to, ts=stamp)] if moved else []
    if moved or skipped or not answered:
        rows.append(ledger.disposition_row(lid, to, said, skipped, ts=stamp))
    if rows:
        _stamp(cfg, grain, *rows)
    arrive.emit_leave(cfg, arrive.report(cfg, kind, gid, to, said, answered))


def _answered(cfg: vocabulary.PmConfig, kind: str, args: list[str],
              other: tuple[str, ...] = ()) -> tuple['arrive.Said', list[str]]:
    """Split the arrival's declared answer off the command line. The target
    state is `args[0]` for every status verb, so the node — and therefore which
    flags this move accepts — is read before the grain is resolved, exactly as
    `_movable` reads the state. `other` names the flags the verb parses for
    itself; anything else is refused BY NAME, carrying the answers this arrival
    DOES declare rather than the useless truth that the flag is unknown
    (rule 11)."""
    to = args[0] if args else ''
    node = vocabulary.arrival_at(cfg, kind, to) if to else None
    try:
        said, rest = arrive.take(node, list(args))
    except arrive.Incomplete as err:
        raise Usage(str(err)) from err
    stray = [a for a in rest
             if a.startswith(vocabulary.ANSWER_PREFIX) and a not in other]
    if stray:
        raise Usage(f'unknown flag {stray[0]!r}'
                    + (arrive.unknown_flag_hint(node)
                       or f' — this project declares no arrival action for '
                          f'{kind} {to!r}, so the move takes no answer'))
    return said, rest


def _movable(cfg: vocabulary.PmConfig, kind: str, to: str) -> None:
    """Exit 2 unless `to` is a state this project declared for `kind` — asked
    before the grain is resolved.
    """
    defect = vocabulary.move_defect(cfg, kind, to)
    if defect:
        raise Usage(defect)


# --- story --------------------------------------------------------------------
def cmd_story(cfg: vocabulary.PmConfig, args: list[str],
              skipped: Skipped = ()) -> int:
    said, rest = _answered(cfg, vocabulary.GRAIN_STORY, args)
    if len(rest) != 2:
        raise Usage(USAGE)
    to, sid = rest
    _movable(cfg, vocabulary.GRAIN_STORY, to)
    story = inventory.story_grain(cfg, sid)
    if story is None:
        raise _unresolved(cfg, vocabulary.GRAIN_STORY, sid,
                          'expected <milestone>/<feature-slug>/<story-slug>')
    cur = _was(story)
    if cur == to:
        _ok(f'story {sid} already {to} (no-op)')
    else:
        _set_status(cfg, story, to)
        _ok(f'story {sid}: {cur} -> {to}')
    _arrived(cfg, vocabulary.GRAIN_STORY, story, sid, cur, to, said, skipped)
    return 0


# --- bug ------------------------------------------------------------------
def cmd_bug(cfg: vocabulary.PmConfig, args: list[str],
            skipped: Skipped = ()) -> int:
    """Move a bug's `status:` through code, `cmd_story`'s shape. **The guard is
    `kind:`, not the id's shape**: `/bugs/` in the id was a path test standing
    in for the kind test `grain_file(..., 'bug')` does properly, and it refused
    every flat `bg-` id the migration mints."""
    said, rest = _answered(cfg, vocabulary.GRAIN_BUG, args)
    if len(rest) != 2:
        raise Usage(USAGE)
    to, bid = rest
    _movable(cfg, vocabulary.GRAIN_BUG, to)
    defect = inventory.id_defect(bid)
    if defect:
        raise _unresolved(cfg, vocabulary.GRAIN_BUG, bid, defect)
    bug = inventory.grain(cfg, bid, vocabulary.GRAIN_BUG)
    if bug is None:
        raise _unresolved(cfg, vocabulary.GRAIN_BUG, bid)
    cur = _was(bug)
    if cur == to:
        _ok(f'bug {bid} already {to} (no-op)')
    else:
        _set_status(cfg, bug, to)
        _ok(f'bug {bid}: {cur} -> {to}')
    _arrived(cfg, vocabulary.GRAIN_BUG, bug, bid, cur, to, said, skipped)
    return 0


# --- feature ------------------------------------------------------------------
def _feature_or_usage(cfg: vocabulary.PmConfig,
                      fid: str) -> tuple[inventory.Grain, str]:
    feature = inventory.grain(cfg, fid, vocabulary.GRAIN_FEATURE)
    if feature is None:
        raise _unresolved(cfg, vocabulary.GRAIN_FEATURE, fid)
    return feature, _was(feature)


def cmd_feature_simple(cfg: vocabulary.PmConfig, to: str, args: list[str],
                       said: 'arrive.Said' = arrive.NOTHING,
                       skipped: Skipped = ()) -> int:
    """Any feature move that is not a close: one write, and it says so. A
    feature ahead of or behind its stories is `check pm`'s WARN, not this
    verb's.
    """
    if len(args) != 1:
        raise Usage(USAGE)
    fid = args[0]
    feature, cur = _feature_or_usage(cfg, fid)
    if cur == to:
        _ok(f'feature {fid} already {to} (no-op)')
    else:
        _set_status(cfg, feature, to)
        _ok(f'feature {fid}: {cur} -> {to}')
    _arrived(cfg, vocabulary.GRAIN_FEATURE, feature, fid, cur, to, said, skipped)
    return 0


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


def cmd_feature_done(cfg: vocabulary.PmConfig, to: str, args: list[str],
                     said: 'arrive.Said' = arrive.NOTHING,
                     skipped: Skipped = ()) -> int:
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
    feature, cur = _feature_or_usage(cfg, fid)

    if rec:
        # Escape FIRST: a pointer outside the checkout is refused before it is
        # resolved, so a file that happens to exist there cannot be stamped
        # (hard rule 8). This verb checked only that the path resolved.
        if pointer_escapes(rec):
            raise Refused(
                f'feature {fid} -> {to}: review record {rec!r} names a path '
                f'outside this checkout — nothing outside it is read (hard '
                f'rule 8), and nothing was written')
        # The one thing checked about a record: the path resolves. Length is
        # not this tool's question.
        target = inventory.record_path(cfg, rec)
        if not inventory.record_resolves(target):
            raise Refused(
                f'feature {fid} -> {to}: review record {rec!r} names no file '
                f'({cfg.rel(target)}). Nothing was written — stamping a pointer '
                f'to nothing is the drift D1 reports.')
        if not frontmatter.set_field(feature.path, 'reviewed', rec):
            raise Usage(f'could not stamp reviewed: in {cfg.rel(feature.path)}')
        _ok(f'feature {fid}: reviewed -> {rec}')
    record = inventory.review_record_for(cfg, fid)

    if cur == to:
        _ok(f'feature {fid} already {to} (no-op)')
    else:
        _set_status(cfg, feature, to)
        _ok(f'feature {fid}: {cur} -> {to}'
            + (f' (review record: {record})' if record
               else ' (no review record)'))
    _arrived(cfg, vocabulary.GRAIN_FEATURE, feature, fid, cur, to, said, skipped)
    return 0


def cmd_feature(cfg: vocabulary.PmConfig, args: list[str],
                skipped: Skipped = ()) -> int:
    if not args:
        raise Usage(USAGE)
    said, kept = _answered(cfg, vocabulary.GRAIN_FEATURE, args,
                           other=('--review-record',))
    if not kept:
        raise Usage(USAGE)
    sub, rest = kept[0], kept[1:]
    # The target is validated before any dispatch; the current state is never
    # gated on, so repair from any state stays.
    _movable(cfg, vocabulary.GRAIN_FEATURE, sub)
    # A move into the `done` category is the close, by whichever word.
    if vocabulary.category_of(cfg, vocabulary.GRAIN_FEATURE, sub) == vocabulary.DONE_CATEGORY:
        return cmd_feature_done(cfg, sub, rest, said, skipped)
    return cmd_feature_simple(cfg, sub, rest, said, skipped)


# --- milestone ----------------------------------------------------------------
def cmd_milestone(cfg: vocabulary.PmConfig, args: list[str],
                  skipped: Skipped = ()) -> int:
    said, rest = _answered(cfg, vocabulary.GRAIN_MILESTONE, args)
    if len(rest) != 2:
        raise Usage(USAGE)
    to, mid = rest
    _movable(cfg, vocabulary.GRAIN_MILESTONE, to)
    milestone = inventory.grain(cfg, mid, vocabulary.GRAIN_MILESTONE)
    if milestone is None:
        raise Usage(f'no milestone resolves from id {mid!r}')
    cur = _was(milestone)
    if cur == to:
        _ok(f'milestone {mid} already {to} (no-op)')
    else:
        _set_status(cfg, milestone, to)
        _ok(f'milestone {mid}: {cur} -> {to}')
    _arrived(cfg, vocabulary.GRAIN_MILESTONE, milestone, mid, cur, to, said,
             skipped)
    # No advisory about the features left behind: D3 asks that of the tree.
    return 0


def _known_milestone_ids(cfg: vocabulary.PmConfig) -> list[str]:
    return sorted(mid or mdir.name
                  for mdir, mid in inventory.known_milestones(cfg))


def _retired_files(cfg: vocabulary.PmConfig, milestone) -> list[Path]:
    """Every file `retire` removes for one milestone, in delete order: the
    milestone, everything bound to it, everything bound to THOSE, each grain's
    shared documents, and the milestone's ledger. The tree's own ledger is not
    touched — those rows were never about this milestone (0.4.0/D3)."""
    grains = [milestone]
    for kind in (vocabulary.GRAIN_FEATURE, vocabulary.GRAIN_BUG):
        for child in inventory.children(cfg, kind, milestone.gid):
            grains.append(child)
            if kind == vocabulary.GRAIN_FEATURE:
                grains.extend(inventory.children(cfg, vocabulary.GRAIN_STORY,
                                             child.gid))
    out: list[Path] = []
    for grain in grains:
        out.append(grain.path)
        for slot in (vocabulary.DECISION_FILE_NAME, vocabulary.REVIEW_FILE_NAME,
                     vocabulary.HANDOFF_FILE_NAME):
            shared = inventory.shared_doc(cfg, grain, slot)
            if shared != grain.path and shared.is_file():
                out.append(shared)
    ledger_path = ledger.ledger_for(cfg, milestone.gid)
    if ledger_path.is_file():
        out.append(ledger_path)
    return [p for p in out if p.is_file()]


# The BACKFILL form of `pm retire` (#31): the two facts nothing else holds once
# a milestone's documents are gone, supplied by the caller because the tree
# no longer can.
RETIRE_VERSION_FLAG = '--version'
RETIRE_NAME_FLAG = '--name'
BACKFILL_FLAGS = (RETIRE_VERSION_FLAG, RETIRE_NAME_FLAG)


def _plan_note(cfg: vocabulary.PmConfig, mid: str, *,
               has_grain: bool = True) -> str:
    """'' when `mid` is on the plan, else the line saying `pm roadmap` will not
    print it and what would. `pm add` resolves its child to a grain, so for an
    id no grain claims it is not the answer, and the line does not offer it."""
    if mid in inventory.declared_order(cfg):
        return ''
    if not has_grain:
        return (f'; {mid} is on no plan, so `pm roadmap` will not print it — '
                f'`pm add` schedules only an id a grain claims, so add {mid} '
                f'to the `order:` list in '
                f'{cfg.rel(inventory.releases_file(cfg))} by hand')
    return (f'; {mid} is on no plan, so `pm roadmap` will not print it — '
            f'`agentic-sdlc pm add {inventory.root_id(cfg)} {mid}` before '
            f'retiring gives it a row there')


def _backfill_retire(cfg: vocabulary.PmConfig, mid: str,
                     pairs: list[tuple[str, str]], summary_words: list[str],
                     dry_run: bool) -> int:
    """File the `retire` row a milestone pruned before 0.5.0 never got.

    Every fact in it is the CALLER'S and the tree cannot check one, which is
    close to rule 4's second sin — a write that looks legitimate and is not.
    So before anything is written: the id resolves to NO grain (one that does
    takes the normal path, which reads its version and name off the
    document); `--version` and `--name` are both given, once each, and
    well-formed; and the row carries `backfilled: true`, so a reader can tell
    a recorded retirement from a reconstructed one. The same backfill twice is
    one row; a backfill never supersedes a RECORDED row.
    """
    # Deferred: `pm/` imports nothing from `conveyor/` at load. ONE grammar
    # for a version and a milestone id, the one the belts join onto the tree.
    from agentic_sdlc.repo.conveyor import driver
    defect = driver.version_defect(mid)
    if defect:
        raise Usage(f'retire: {defect} — nothing was written')
    held = inventory.grain_index(cfg).get(mid)
    if held is not None:
        raise Usage(
            f'{mid!r} is a {held.kind or "grain"} in this tree '
            f'({cfg.rel(held.path)}), so there is nothing to backfill — '
            f'{RETIRE_VERSION_FLAG} and {RETIRE_NAME_FLAG} are for a milestone '
            f'whose documents are already gone. Retire it the normal way, '
            f'which reads its version and name off the document: '
            f'`{PROG} retire {mid} [<summary...>]`. Nothing was written')
    given: dict[str, str] = {}
    for flag, value in pairs:
        if flag in given:
            raise Usage(f'{flag} given twice — a backfill records one value '
                        f'per fact. Nothing was written')
        given[flag] = value
    missing = [flag for flag in BACKFILL_FLAGS if not given.get(flag, '').strip()]
    if missing:
        raise Usage(
            f'the backfill form needs both {RETIRE_VERSION_FLAG} <version> and '
            f'{RETIRE_NAME_FLAG} <name> — the two facts nothing else holds '
            f'once the documents are gone; missing or empty: '
            f'{", ".join(missing)}. Nothing was written')
    version = given[RETIRE_VERSION_FLAG]
    defect = driver.version_defect(version)
    if defect:
        raise Usage(f'{RETIRE_VERSION_FLAG}: {defect} — nothing was written')
    if '\n' in given[RETIRE_NAME_FLAG] or '\r' in given[RETIRE_NAME_FLAG]:
        raise Usage(f'{RETIRE_NAME_FLAG}: a name is one line — nothing was '
                    f'written')
    # Collapsed at the WRITE, like the summary: both print in the
    # tab-separated row `pm roadmap` reads back.
    name = ' '.join(given[RETIRE_NAME_FLAG].split())
    summary = ' '.join(' '.join(summary_words).split())
    ledger_file = ledger.grainless_path(cfg.roadmap)
    try:
        prior = ledger.retired_releases(cfg).get(mid)
    except ledger.LedgerError as err:
        raise Usage(f'{err}') from err
    row = ledger.retire_row(mid, version, name, summary, backfilled=True)
    facts = ', '.join(f'{key} {row[key]!r}' for key in ledger.RETIRE_FIELDS
                      if key in row)
    plan_note = _plan_note(cfg, mid, has_grain=False)
    superseded = ''
    if prior is not None:
        if all(prior.get(key, '') == row.get(key, '')
               for key in ledger.RETIRE_FIELDS):
            _ok(f'{cfg.rel(ledger_file)} already records {mid} retired with '
                f'{facts} — nothing was written (no-op){plan_note}')
            return 0
        when = prior.get(ledger.TS_FIELD, '?')
        if not prior.get(ledger.BACKFILLED_FIELD):
            raise Refused(
                f'{mid} already has a RECORDED retire row ({when}), written by '
                f'`pm retire` off the document itself; a backfill never '
                f'supersedes one. Nothing was written')
        # A backfilled row is the caller's word, and `pm roadmap` reads the
        # LAST row: correcting one is appending one, and the line says so.
        superseded = f'; it supersedes the backfilled row of {when}'
    if dry_run:
        _ok(f'[dry-run] would backfill a retire row for {mid} in '
            f'{cfg.rel(ledger_file)}: {facts}{superseded}{plan_note}')
        return 0
    try:
        ledger.append_to(ledger_file, row)
    except OSError as err:
        raise Refused(f'{cfg.rel(ledger_file)} could not be appended to '
                      f'({err}) — nothing was written') from err
    _ok(f'milestone {mid}: retire row BACKFILLED — no grain in this tree '
        f'claims the id; {cfg.rel(ledger_file)} keeps {facts}, marked '
        f'`{ledger.BACKFILLED_FIELD}: true` because the caller supplied them '
        f'and the tree cannot check them{superseded}{plan_note}')
    return 0


def cmd_retire(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Retire a finished milestone: remove its grains, and FILE what outlived
    them.

    **`ROADMAP.md` retired in 0.3.0 and this verb no longer appends to it.**
    `pm roadmap` derives the index it was half of; the other half — one row per
    shipped release: version, name, one sentence — is not derivable once the
    documents are gone, so it is a `retire` row in the tree's own
    `ledger.jsonl`, which this verb removes nothing from
    (`bg-retire-drops-the-summary-it-accepts`). Refuses only on an unresolvable
    id; an unfinished milestone is reported. `--dry-run` writes nothing.

    `--version` and `--name` are the BACKFILL form, for a milestone whose
    documents were pruned before this verb filed rows (#31) — see
    `_backfill_retire`.
    """
    pairs, args = _take_flags(args, BACKFILL_FLAGS, noun='a value')
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
    if pairs:
        return _backfill_retire(cfg, mid, pairs, summary_words, dry_run)
    grain = inventory.grain_index(cfg).get(mid)
    if grain is None or grain.kind != vocabulary.GRAIN_MILESTONE:
        known = _known_milestone_ids(cfg)
        raise Usage(f'{mid!r} is not a milestone in {cfg.roadmap_dir} '
                    f'({" ".join(known) if known else "none scaffolded"})')
    mfile = grain.path
    notices: list[str] = []
    if not mfile.is_file():
        notices.append(f'{cfg.rel(mfile)} is missing')
        status, canonical_id, name = '', mid, ''
    else:
        status = grain.field(vocabulary.FIELD_STATUS)
        canonical_id = grain.field(vocabulary.FIELD_ID) or mid
        name = grain.field(vocabulary.FIELD_NAME)
        if not vocabulary.holds(cfg, vocabulary.GRAIN_MILESTONE, [(mid, status)],
                           vocabulary.DONE_CATEGORY):
            notices.append(f'milestone {mid} is {status or "(no status)"}, '
                           f'not done')
    # By ID, never by the directory the document sits in: under pools that is
    # the pool, so every unfinished feature reported as `features`.
    open_features = sorted(
        name for name, _ in vocabulary.holds(
            cfg, vocabulary.GRAIN_FEATURE,
            ((ff.field(vocabulary.FIELD_ID) or cfg.rel(ff.path),
              ff.field(vocabulary.FIELD_STATUS))
             for ff in inventory.feature_grains(cfg, mid)),
            vocabulary.DONE_CATEGORY).blockers)
    if open_features:
        notices.append(f'{len(open_features)} feature(s) not done: '
                       f'{" ".join(open_features)}')
    # "Still open" is "not in `done`": a bug at `fixed` is work that remains.
    open_bugs = sorted(
        name for name, _ in vocabulary.holds(
            cfg, vocabulary.GRAIN_BUG,
            ((bug.path.stem, bug.field(vocabulary.FIELD_STATUS))
             for bug in inventory.bug_grains(cfg, mid)),
            vocabulary.DONE_CATEGORY).blockers)
    if open_bugs:
        notices.append(f'{len(open_bugs)} bug(s) still open: '
                       f'{" ".join(open_bugs)}')

    # Whitespace collapsed at the WRITE, so the stored sentence can never forge
    # a column in the tab-separated row `pm roadmap` prints it in.
    summary = ' '.join(' '.join(summary_words).split())
    version = grain.field('version').strip() if mfile.is_file() else ''
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
    plan_note = _plan_note(cfg, canonical_id)

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
    # docs beside each.
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
    # AFTER the removal: the row records what happened, not what was about
    # to. The refusal below carries the three facts by value, so a hand-repair
    # does not need the deleted document back.
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


# --- status -------------------------------------------------------------------
def _short(mid: str, gid: str) -> str:
    """A child's id with the parent's prefix taken off, when it has one. A
    nested id was `<milestone>/<slug>` and this column printed the slug; a
    pooled id is `ft-<slug>` and there is nothing to strip. One function, so
    the board reads the same in either layout."""
    head = f'{mid}/'
    return gid[len(head):] if gid.startswith(head) else gid


def _open_for(cfg: vocabulary.PmConfig, mid: str) -> dict[str, str]:
    """{grain id: how long it has been open}, for the grains in one milestone
    that have not reached a terminal state. Read once per milestone off the two
    ledgers its rows can be in, so `pm status` costs one pass over each file
    rather than one per grain. A grain with no status row is absent here and
    prints `-`: not having been moved is a different fact from having been
    moved a moment ago (rule 4)."""
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
        if row.data.get(ledger.KIND_FIELD) != ledger.KIND_STATUS:
            continue
        gid = row.data.get(ledger.GRAIN_FIELD)
        if isinstance(gid, str) and gid:
            by_grain.setdefault(gid, []).append(row)
    out = {}
    for gid, status in by_grain.items():
        status.sort(key=lambda r: str(r.data.get(ledger.TS_FIELD) or ''))
        kind = _grain_kind(cfg, gid)
        if not kind:
            # A row naming a grain the tree does not hold: there is no
            # vocabulary to ask, so it is UNMEASURED rather than open.
            continue
        seconds = ledger.open_seconds(cfg, kind, status)
        if seconds is not None:
            out[gid] = ledger.human_duration(seconds)
    return out


def _age_cell(cfg: vocabulary.PmConfig, kind: str, gid: str, status: str,
              opened: dict[str, str]) -> str:
    """`  open 3d 4h`, `  open -`, or nothing — nothing only for a grain that
    has REACHED a done state. An OPEN grain nobody has moved is `-`:
    unmeasured is a different fact from young, and omitting the cell made it
    indistinguishable from finished (rule 4)."""
    if vocabulary.category_of(cfg, kind, status) == vocabulary.DONE_CATEGORY:
        return ''
    return f'  open {opened.get(gid) or ledger.human_duration(None)}'


def cmd_status(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    only = args[0] if args else ''
    # Rule 4: a scan that saw nothing says so instead of an empty print at exit
    # 0.
    known = inventory.known_milestone_grains(cfg)
    if not known:
        raise Usage(f'{cfg.roadmap_dir} holds no milestone at all — nothing to '
                    f'report, so this is a scope problem (wrong [pm] '
                    f'roadmap_dir, or an empty tree?), not a status')
    if only and only not in {g.gid for _, g in known}:
        ids = sorted(g.gid for _, g in known if g.gid)
        raise Usage(f'{only!r} is not a milestone in {cfg.roadmap_dir} '
                    f'({" ".join(ids)})')
    # As wide as the longest declared feature word; an undeclared word still
    # prints whole.
    width = max(len(word) for word in vocabulary.flow_of(cfg,
                                                    vocabulary.GRAIN_FEATURE).order)
    for mdir, milestone in known:
        mid = milestone.gid
        if only and only != mid:
            continue
        # 0.4.0/every-grain-is-on-a-stopwatch: how long each open grain has
        # been open, so "what is aging" is a question the tree answers. A
        # REPORT — nothing is gated on it, because a ceiling on how long a
        # feature may stay open is this package having an opinion (rule 9).
        opened = _open_for(cfg, mid)
        mstat = milestone.field(vocabulary.FIELD_STATUS)
        print(f'milestone {mid:<10} [{mstat}]'
              + _age_cell(cfg, vocabulary.GRAIN_MILESTONE, mid, mstat, opened))
        rows = []
        for feature in inventory.feature_grains(cfg, mid):
            view = inventory.feature_view(cfg, feature)
            # The markers reuse the gate's predicates, so report and gate
            # cannot describe a tree differently.
            dangling = inventory.drift_dangling_record(cfg, view.fid)
            stalled = inventory.drift_stalled(cfg, view)
            drift = (f'  <DRIFT: {dangling}>' if dangling
                     else f'  <WARN: {stalled}>' if stalled else '')
            rows.append((view,
                         f'  feature {_short(mid, view.fid):<40} '
                         f'[{view.status:<{width}}] stories '
                         f'{view.done_n}/{view.total} done'
                         + _age_cell(cfg, vocabulary.GRAIN_FEATURE, view.fid,
                                     view.status,
                                     opened) + drift))
        if not rows:
            continue
        # IN THE MILESTONE'S DECLARED ORDER — `feature_files` reads the
        # parent's `order:` and falls back to id. `phase:` grouped this board
        # until 0.4.0 and retired with the execution list (D-note).
        finished = vocabulary.holds(cfg, vocabulary.GRAIN_FEATURE,
                               ((v.fid, v.status) for v, _ in rows),
                               vocabulary.DONE_CATEGORY)
        print(f'  -- {finished.counted - len(finished.blockers)}/{len(rows)} '
              f'feature(s) done')
        for _, line in rows:
            print(line)
    return 0


def cmd_list(cfg: vocabulary.PmConfig, args: list[str]) -> int:
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
    kind = vocabulary.GRAIN_STORY
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
    if category and category not in vocabulary.CATEGORIES:
        raise Usage(f'--category names {category!r} — the set is closed and '
                    f'is exactly {" ".join(vocabulary.CATEGORIES)}')
    for status in sorted(statuses):
        _movable(cfg, kind, status)
    if kind == vocabulary.GRAIN_MILESTONE:
        if owner or milestone:
            raise Usage('--owner and --milestone filter stories; '
                        '--kind milestone takes --status and --category')
        return _list_milestones(cfg, statuses, category, as_json)
    if kind in (vocabulary.GRAIN_FEATURE, vocabulary.GRAIN_BUG):
        if owner:
            raise Usage(f'--owner filters stories; a {kind} carries no owner:')
        return _list_bound(cfg, kind, statuses, category, milestone, as_json)

    # Enumerated once, to refuse a typo'd `--milestone` as well as to filter.
    known = inventory.known_milestones(cfg)
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
        for feature in inventory.feature_grains(cfg, mid):
            view = inventory.feature_view(cfg, feature)
            for story in view.stories:
                scanned += 1
                status = story.field(vocabulary.FIELD_STATUS)
                who = story.field(vocabulary.FIELD_OWNER)
                if statuses and status not in statuses:
                    continue
                if category and vocabulary.category_of(cfg, vocabulary.GRAIN_STORY,
                                                  status) != category:
                    continue
                if owner and who != owner:
                    continue
                rows.append((story.field(vocabulary.FIELD_ID),
                             status, who or DASH, view.fid,
                             story.field(vocabulary.FIELD_NAME) or DASH))
    _emit_rows(vocabulary.GRAIN_STORY, rows, as_json)
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
    over the SAME tuples through `LIST_COLUMNS`. One function because the
    failure that matters is the two diverging — a JSON payload carrying a field
    the columns do not is what a consumer discovers at the worst moment. Here
    they cannot: the rows are built once and the keys are zipped onto them."""
    columns = LIST_COLUMNS[kind]
    if as_json:
        print(json.dumps([dict(zip(columns, row)) for row in rows],
                         ensure_ascii=False))
        return
    for row in rows:
        # A tab inside a cell would forge a column, and `name` is free text a
        # human typed. The JSON payload above keeps the byte; a forged column
        # silently shifts every field after it.
        print('\t'.join(cell.replace('\t', ' ') for cell in row))


# Every kind is listable, so a script asks the CLI instead of grepping a
# status word. It was story and milestone, so "show me what is unbound" looked
# like it needed a flag: there was nothing to pipe (rule 11).
LIST_KINDS = (vocabulary.GRAIN_STORY, vocabulary.GRAIN_MILESTONE, vocabulary.GRAIN_FEATURE,
              vocabulary.GRAIN_BUG)

# The columns each `--kind` emits, IN ORDER, spelled once. Three things read
# this — the rows, `--json`'s keys and the `--help` line — and a column list
# living in three places is the drift `--json` exists to make unhideable.
LIST_COLUMNS = {
    vocabulary.GRAIN_STORY: ('id', 'status', 'owner', 'feature', 'name'),
    vocabulary.GRAIN_MILESTONE: ('id', 'status', 'category', 'branch', 'name'),
    # A grain that BINDS emits its binding, so `$4 == "-"` is "unbound" and
    # every other question about the edge is a pipe away.
    vocabulary.GRAIN_FEATURE: ('id', 'status', 'milestone', 'reviewed', 'name'),
    vocabulary.GRAIN_BUG: ('id', 'status', 'milestone', 'caused_by', 'name'),
}


def _list_bound(cfg: vocabulary.PmConfig, kind: str, statuses: set[str],
                category: str, milestone: str, as_json: bool) -> int:
    """Features or bugs, one line each, with the binding as a COLUMN — `-`
    there is "written and not yet scheduled", answered by a pipe rather than a
    flag, which composes with every other filter (rule 11)."""
    scanned = 0
    rows = []
    for gid, grain in sorted(inventory.grain_index(cfg).items()):
        if grain.kind != kind:
            continue
        scanned += 1
        status = grain.field(vocabulary.FIELD_STATUS)
        bound = grain.field(vocabulary.GRAIN_MILESTONE)
        if statuses and status not in statuses:
            continue
        if category and vocabulary.category_of(cfg, kind, status) != category:
            continue
        if milestone and bound != milestone:
            continue
        second = 'reviewed' if kind == vocabulary.GRAIN_FEATURE else 'caused_by'
        rows.append((gid, status or DASH, bound or DASH,
                     grain.field(second) or DASH,
                     grain.field(vocabulary.FIELD_NAME) or DASH))
    _emit_rows(kind, rows, as_json)
    print(f'[pm] {len(rows)} of {scanned} {kind}(s)', file=sys.stderr)
    return 0


def _list_milestones(cfg: vocabulary.PmConfig, statuses: set[str],
                     category: str, as_json: bool = False) -> int:
    """One tab-separated `<id> <status> <category> <branch> <name>` per
    milestone, `-` for an absent one, so a shell `read` gets a fixed column
    count. `LIST_COLUMNS['milestone']` is the order.
    """
    known = inventory.known_milestone_grains(cfg)
    if not known:
        raise Usage(f'{cfg.roadmap_dir} holds no milestone at all — nothing to '
                    f'list, so this is a scope problem (wrong [pm] '
                    f'roadmap_dir, or an empty tree?), not an empty set')
    rows = []
    for mdir, milestone in known:
        status = milestone.field(vocabulary.FIELD_STATUS)
        cat = vocabulary.category_of(cfg, vocabulary.GRAIN_MILESTONE, status)
        if statuses and status not in statuses:
            continue
        if category and cat != category:
            continue
        rows.append((milestone.gid or mdir.name, status or DASH, cat or DASH,
                     milestone.field('branch') or DASH,
                     milestone.field(vocabulary.FIELD_NAME) or DASH))
    _emit_rows(vocabulary.GRAIN_MILESTONE, rows, as_json)
    print(f'[pm] {len(rows)} of {len(known)} milestone(s)', file=sys.stderr)
    return 0


def _grain_of(cfg: vocabulary.PmConfig, gid: str) -> inventory.Grain:
    """Resolve any grain id — milestone, feature, story or bug — to the GRAIN.
    ONE lookup for all four kinds, because a grain declares its `id:` and the
    index is keyed on it. The four-branch version this replaced did arithmetic
    on a path, which is why a `..` or an empty segment had to be caught before
    a join could hand a write to a sibling grain. Nothing is joined now.

    A grain and not a file, so a verb that wants a FIELD asks `.field(key)`
    instead of handing storage the path this used to return."""
    defect = inventory.id_defect(gid)
    if defect:
        raise Usage(f'no grain resolves from id {gid!r} — {defect}')
    found = inventory.grain(cfg, gid)
    if found is None:
        raise Usage(f'no grain resolves from id {gid!r}')
    return found


def _grain_file(cfg: vocabulary.PmConfig, gid: str) -> Path:
    """`_grain_of`'s document, for the verbs that WRITE it or name it."""
    return _grain_of(cfg, gid).path


def cmd_get(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    if len(args) != 2:
        raise Usage(USAGE)
    gid, key = args
    print(_grain_of(cfg, gid).field(key))
    return 0


def _binding_defect(cfg: vocabulary.PmConfig, gid: str, key: str,
                    value: str) -> None:
    """Refuse a binding that names no grain, or one of the wrong kind — a fact
    about the INPUT, so exit 2 and nothing written (rule 9). Empty UNBINDS and
    is never refused; only the fields `BINDS_TO` names are asked, so `set`
    writes every other key with no opinion."""
    want = {field: parent for parent, field in vocabulary.BINDS_TO.values()}.get(key)
    if want is None or not value:
        return
    found = inventory.grain_index(cfg).get(frontmatter.unquote(value))
    if found is None:
        raise Usage(f'{key}: {value!r} names no grain in {cfg.roadmap_dir} — '
                    f'a binding that resolves to nothing is drift, not a plan; '
                    f'leave it empty to say "not bound yet". Nothing was '
                    f'written')
    if found.kind != want:
        raise Usage(f'{key}: {value!r} is a {found.kind}, not a {want} — '
                    f'a {inventory.kind_of(cfg, gid) or "grain"} names its '
                    f'{want} in {key}:. Nothing was written')


def _shaped(key: str, value: str) -> str:
    """`value` in the shape `check pm` grades `key` in — `validate.REF_KEYS` is
    the one answer, and a bare id is bracketed and re-read by the gate's own
    parser, so every rejection the reader has is a refusal here (rule 4)."""
    try:
        if key in validate.REF_KEYS:
            raw = value.strip()
            if raw in validate.EMPTY:
                return '[]'
            return validate.render_refs(validate.refs_in(
                key, raw if raw.startswith('[') else f'[{raw}]'))
        if key == validate.CAUSED_BY:
            validate.scalar_ref_in(key, value)
    except validate.Unparseable as err:
        raise Usage(f'{err}. Nothing was written') from err
    return value


def cmd_set(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Set one frontmatter field through a tool rather than a regex. `status`
    is refused by name: a status is a move, and only the status verbs ask
    `move_defect` and stamp the ledger; `order` likewise, being a block list
    `pm add` owns. Every other field is written in its `_shaped` form.
    """
    if len(args) != 3:
        raise Usage(USAGE)
    gid, key, value = args
    if not key or not key.replace('_', '').isalnum():
        raise Usage(f'{key!r} is not a frontmatter key')
    if key == vocabulary.FIELD_STATUS:
        # The grain's own kind when the tree holds it; the hint names a verb,
        # and a verb for a kind nobody declared would be a worse hint than a
        # generic one.
        kind = _grain_kind(cfg, gid) or vocabulary.GRAIN_STORY
        raise Usage(f'status is a move, not a field: run `{PROG} {kind} '
                    f'{value} {gid}` — the {kind} verb checks {value!r} '
                    f'against [pm.states.{kind}] and stamps the ledger; '
                    f'`set` would do neither')
    if key == vocabulary.ORDER_KEY:
        raise Usage(f'{key} is a sequence, not a field: run `{PROG} add '
                    f'<parent-id> <child-id> [--position N | --before <id> | '
                    f'--after <id>]` (or `{PROG} remove`) — `{key}` is a BLOCK '
                    f'list, and the scalar `set` writes is a form `pm add` '
                    f'refuses and every reader of the sequence sees as empty')
    if '\n' in value or '\r' in value:
        raise Refused('a frontmatter scalar is one line')
    value = _shaped(key, value)
    grain = _grain_of(cfg, gid)
    path = grain.path
    _binding_defect(cfg, gid, key, value)
    before = grain.field(key)
    if not frontmatter.set_field(path, key, value):
        raise Usage(f'could not write {key}: in {cfg.rel(path)} '
                    f'(malformed frontmatter, or the file is not writable)')
    _ok(f'{gid}: {key} {before!r} -> {value!r}')
    return 0


def cmd_rename(cfg: vocabulary.PmConfig, args: list[str]) -> int:
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


def cmd_vocabulary(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Print this version's declared surface — each kind's states with their
    category, and the rule ids `[pm] checks` may name — for the pin bump.
    Reads `cfg.flows` directly so an undeclared tree is reported, with the
    bytes `init` would write, rather than refused."""
    as_json = '--json' in args
    for a in args:
        if a != '--json':
            raise Usage(f'unknown flag {a!r}')
    # The flat sets stay (rule 6): category-major, then the project's order;
    # empty for a tree that declared nothing.
    grains = {
        vocabulary.GRAIN_MILESTONE: cfg.milestone_states,
        vocabulary.GRAIN_FEATURE: cfg.feature_states,
        vocabulary.GRAIN_STORY: cfg.story_states,
        vocabulary.GRAIN_BUG: cfg.bug_states,
    }
    if as_json:
        print(json.dumps({
            'categories': list(vocabulary.CATEGORIES),
            'flow_kinds': list(vocabulary.FLOW_KINDS),
            # The absence is a value, not a missing key, so two pin versions
            # diff cleanly.
            'flow_declared': bool(cfg.flows),
            'grains': {
                g: {
                    'states': list(states),
                    'flow': (None if g not in cfg.flows else {
                        'categories': {
                            cat: list(cfg.flows[g].by_category.get(cat, ()))
                            for cat in vocabulary.CATEGORIES},
                        'order': list(cfg.flows[g].order),
                    }),
                }
                for g, states in grains.items()},
            # The seed travels in every payload: what a declaration diffs
            # against, or what `init` would write.
            'seed': vocabulary.render_seed(),
            'notes': {
                'states': 'the flat per-kind `states` list is the declared '
                          'flow\'s order — category-major, then the project\'s '
                          'own list order — and is empty for a tree that '
                          'declared nothing; `flow` is what the project '
                          'declared in [pm.states.<kind>], and every question '
                          'the engine asks is asked of a category',
            },
            'checks': list(vocabulary.KNOWN_CHECKS),
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
    print(f'closed and is exactly {" ".join(vocabulary.CATEGORIES)}.')
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
        for line in vocabulary.render_seed().splitlines():
            print(f'  {line}' if line else '')
        print()
    else:
        cat_width = max(len(c) for c in vocabulary.CATEGORIES)
        for kind in vocabulary.FLOW_KINDS:
            # Indexed, never `.get`: `_load_flows` refuses a partial
            # declaration, so it is all four kinds or none.
            flow = cfg.flows[kind]
            print(f'[pm.states.{kind}]')
            for category in vocabulary.CATEGORIES:
                states = flow.by_category.get(category, ())
                print(f'  {category:<{cat_width}}  {" ".join(states)}')
            print()
    print(f'rules  {" ".join(vocabulary.KNOWN_CHECKS)}')
    return 0


def cmd_validate(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Structural + referential integrity. The same predicates `check pm` runs."""
    if args:
        raise Usage(USAGE)
    # Same placement as the gate's: the two readers a stale rule id would
    # silently narrow.
    stale = vocabulary.config_complaints(cfg)
    if stale:
        raise Usage('\n         '.join(stale))
    from agentic_sdlc.repo.pm import validate as _validate
    findings, census = _validate.run(cfg, set(cfg.checks) & set(vocabulary.VALIDATE_CHECKS))
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
# `caused_by:` relates two grains, like `depends_on:` — never a second copy of
# `milestone:`, the binding, which is the only one.
CAUSED_BY = 'caused_by'
CAUSED_BY_FLAG = '--caused-by'

# A milestone's version is a FIELD, never its id: it is optional (a milestone
# with none is backlog), it re-versions without a rename, and no reader here
# parses it.
VERSION = 'version'
VERSION_FLAG = '--version'


def _stamp_field(cfg: vocabulary.PmConfig, path: Path, gid: str, key: str,
                 value: str) -> None:
    """Write one frontmatter field onto a grain `new` just minted or filled,
    through `set_field` so a project's own template still gets it, and ECHO
    it: a field the caller asked for and never sees confirmed is one they have
    to go read the file to trust."""
    if not frontmatter.set_field(path, key, value):
        raise Refused(
            f'{cfg.rel(path)} was created, but {key}: could not be written '
            f'into it — its frontmatter has no `---` block to put the field '
            f'in; add one, or set it with `pm set {gid} {key} {value}`')
    _ok(f'{key} {value!r} stamped on {cfg.rel(path)}')


def _version(pairs: list[tuple[str, str]]) -> str:
    """The `--version` value, or ''. Refused BEFORE any write: a multi-line
    scalar would inject lines into the frontmatter it lands in, which is the
    same bar `pm set` holds."""
    value = ''
    for _, raw in pairs:
        value = raw
    if '\n' in value or '\r' in value:
        raise Refused(f'{VERSION_FLAG}: a frontmatter scalar is one line — '
                      f'nothing was written')
    return value.strip()


def _caused_by(cfg: vocabulary.PmConfig, pairs: list[tuple[str, str]]) -> str:
    """The `--caused-by` value, proven to name a feature that exists, or ''.
    Resolution is the whole gate, through the resolver the verbs use; any
    status resolves, since escape is the report's question. An OSError is
    False, never a traceback."""
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
        found = inventory.feature_file(cfg, value)
    except OSError:
        found = None
    if found is None:
        raise Usage(f'{CAUSED_BY_FLAG} {value!r} resolves to no feature in '
                    f'this tree — {CAUSED_BY} names the FEATURE whose change '
                    f'produced the bug (a milestone id or a story id is not '
                    f'one), and nothing was written')
    return value


def _scaffold(cfg: vocabulary.PmConfig, kind: str, doc: Path,
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


def _mint_path(cfg: vocabulary.PmConfig, kind: str, gid: str, name: str = '',
               parent_id: str = '') -> Path:
    """The file a NEW grain is written to, in whichever layout the tree is in.
    A NESTED tree keeps its shape: minting into a pool there flips `is_pooled`,
    and every reader then sees the one new file and none of the tree behind it.
    `gid` is the MINTED ID and the stem; nothing READS a stem (rule 9)."""
    if not inventory.is_nested(cfg):
        return inventory.pool_dir(cfg, kind) / f'{gid}.md'
    if kind == vocabulary.GRAIN_MILESTONE:
        stem = f'{gid}-{_slugify(name)}' if name else gid
        return cfg.roadmap / stem / vocabulary.MILESTONE_DOC
    parent = (inventory.milestone_dir(cfg, parent_id) if kind != vocabulary.GRAIN_STORY
              else inventory.feature_dir(cfg, parent_id))
    if parent is None:
        return inventory.pool_dir(cfg, kind) / f'{gid}.md'
    if kind == vocabulary.GRAIN_FEATURE:
        return parent / vocabulary.FEATURES_DIR / gid / vocabulary.FEATURE_DOC
    if kind == vocabulary.GRAIN_STORY:
        return parent / vocabulary.STORIES_DIR / f'{gid}.md'
    return parent / vocabulary.BUGS_DIR / f'{gid}.md'


NAME_ARG = '<name...>'   # a create's last argument, for the refusal and the synopsis


def _retired_id(kind: str, parent_id: str, slug: str) -> str:
    """The compound id 0.4.0's `pm new` minted from these arguments, or ''.
    **READ, never minted**: on a tree authored then, `pm new feature <mid>
    <slug>` must keep filling that document rather than creating a second one
    beside it, so the pin bump is not a duplicate factory (rule 3)."""
    if not parent_id:
        return ''
    if kind == vocabulary.GRAIN_BUG:
        return f'{parent_id}/{vocabulary.BUGS_DIR}/{slug}'
    return f'{parent_id}/{slug}' if kind in (vocabulary.GRAIN_FEATURE,
                                             vocabulary.GRAIN_STORY) else ''


def _claim(cfg: vocabulary.PmConfig, kind: str, slug: str,
           parent_id: str = '') -> tuple[str, inventory.Grain | None]:
    """(the id this call is about, the GRAIN already holding it or None).
    Three spellings LOOKED UP, one MINTED: the argument as a literal id, the id
    `mint_id` makes of it, and the retired compound one — first hit wins, and
    none means the minted id is created. `story_grain` for a story: only it
    resolves the nested layout's slug-plus-ordinal."""
    minted = inventory.mint_id(kind, slug)
    for gid in (slug, minted, _retired_id(kind, parent_id, slug)):
        found = (inventory.story_grain(cfg, gid) if kind == vocabulary.GRAIN_STORY
                 else inventory.grain(cfg, gid, kind)) if gid else None
        if found is not None:
            return gid, found
    return minted, None


def _name_required(kind: str, gid: str, typed: str) -> 'Usage':
    """The refusal for a CREATE with no name, leading with the ARGUMENT that
    was omitted: *"feature 'x' does not exist yet"* read as *this grain is
    missing from your tree* and sent readers looking for a lost file."""
    return Usage(f'{NAME_ARG} is required: `agentic-sdlc pm new {kind} {typed} '
                 f'{NAME_ARG}`. Nothing in this tree declares {gid!r}, so this '
                 f'call CREATES a {kind} rather than filling the missing slots '
                 f'of one that is already there, and the name is the one slot '
                 f'that cannot be derived')


def cmd_new(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Scaffold one grain, minting its id through `inventory.mint_id`.

    **The parent argument BINDS; it is not identity** — it goes to the child's
    `milestone:`/`feature:` field, the fact `pm add` writes, and never into the
    id, so re-parenting stays one `pm set`. It stays positional and required:
    dropping it breaks every caller, and reading the first argument as a
    parent-or-slug would be inferring intent (rule 9)."""
    if not args:
        raise Usage(USAGE)
    grain, rest = args[0], args[1:]
    # `new milestone` and `new feature` are idempotent — they fill missing
    # slots — so the name is optional when the grain is already there.
    if grain == vocabulary.GRAIN_MILESTONE:
        pairs, rest = _take_flags(rest, (VERSION_FLAG,), noun='a version')
        if not rest:
            raise Usage(USAGE)
        version = _version(pairs)
        slug, name = _check_slug('milestone slug', rest[0]), ' '.join(rest[1:])
        mid, found = _claim(cfg, vocabulary.GRAIN_MILESTONE, slug)
        if found is None and not name:
            raise _name_required(vocabulary.GRAIN_MILESTONE, mid, slug)
        target = (found.path if found is not None
                  else _mint_path(cfg, vocabulary.GRAIN_MILESTONE, mid, name))
        # `found is None` implies a non-empty `name` (the refusal above), so
        # the short-circuit is the whole of the None guard.
        name = name or found.field(vocabulary.FIELD_NAME)
        code = _scaffold(cfg, vocabulary.GRAIN_MILESTONE, target,
                         {vocabulary.FIELD_ID: mid,
                          vocabulary.FIELD_KIND: vocabulary.GRAIN_MILESTONE, vocabulary.FIELD_NAME: name})
        if version:
            _stamp_field(cfg, target, mid, VERSION, version)
        return code
    if grain == vocabulary.GRAIN_FEATURE:
        if len(rest) < 2:
            raise Usage(USAGE)
        mid, slug = rest[0], _check_slug('feature slug', rest[1])
        name = ' '.join(rest[2:])
        if inventory.milestone_file(cfg, mid) is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        fid, found = _claim(cfg, vocabulary.GRAIN_FEATURE, slug, mid)
        if found is None and not name:
            raise _name_required(vocabulary.GRAIN_FEATURE, fid, f'{mid} {slug}')
        target = (found.path if found is not None
                  else _mint_path(cfg, vocabulary.GRAIN_FEATURE, fid, name, mid))
        name = name or found.field(vocabulary.FIELD_NAME)
        return _scaffold(cfg, vocabulary.GRAIN_FEATURE, target,
                         {vocabulary.FIELD_ID: fid,
                          vocabulary.FIELD_KIND: vocabulary.GRAIN_FEATURE, vocabulary.GRAIN_MILESTONE: mid,
                          vocabulary.FIELD_NAME: name})
    if grain == vocabulary.GRAIN_STORY:
        if len(rest) < 3:
            raise Usage(USAGE)
        fid, slug = rest[0], _check_slug('story slug', rest[1])
        name = ' '.join(rest[2:])
        feature = inventory.grain(cfg, fid, vocabulary.GRAIN_FEATURE)
        if feature is None:
            raise Usage(f'no feature resolves from id {fid!r}')
        # The milestone comes from the feature's own frontmatter, never
        # re-derived from the id.
        mid = feature.field(vocabulary.GRAIN_MILESTONE)
        sid, claimed = _claim(cfg, vocabulary.GRAIN_STORY, slug, fid)
        if claimed is not None:
            raise Refused(f'story id {sid!r} is already held by '
                          f'{cfg.rel(claimed.path)} — two files claiming one '
                          f'id is addressable by neither')
        sf = _mint_path(cfg, vocabulary.GRAIN_STORY, sid, '', fid)
        if _exists(sf):
            raise Refused(f'{cfg.rel(sf)} already exists')
        body = templates.render(
            templates.load(cfg, vocabulary.GRAIN_STORY),
            {vocabulary.FIELD_ID: sid, vocabulary.FIELD_KIND: vocabulary.GRAIN_STORY,
             vocabulary.GRAIN_FEATURE: fid, vocabulary.GRAIN_MILESTONE: mid,
             vocabulary.FIELD_NAME: name})
        _mint(cfg, sf, body)
        _ok(f'created {cfg.rel(sf)}')
        return 0
    if grain == vocabulary.GRAIN_BUG:
        pairs, rest = _take_flags(rest, (CAUSED_BY_FLAG,), noun='a feature id')
        if len(rest) < 2:
            raise Usage(USAGE)
        # Resolved before the slug guard and any write: a bug with an
        # unresolvable cause is not created.
        cause = _caused_by(cfg, pairs)
        mid, slug = rest[0], _check_slug('bug slug', rest[1])
        name = ' '.join(rest[2:])
        if '\n' in name or '\r' in name:
            # The same bar `pm set` holds: a multi-line scalar injects lines
            # into the frontmatter it is stamped on.
            raise Refused(f'{NAME_ARG}: a frontmatter scalar is one line — '
                          f'nothing was written')
        if inventory.milestone_file(cfg, mid) is None:
            raise Usage(f'no milestone resolves from {mid!r}')
        bid, held = _claim(cfg, vocabulary.GRAIN_BUG, slug, mid)
        if held is not None:
            raise Refused(f'bug {bid!r} already exists')
        bf = _mint_path(cfg, vocabulary.GRAIN_BUG, bid, '', mid)
        if _exists(bf):
            raise Refused(f'{cfg.rel(bf)} already exists')
        # The argument is the PARENT, written to `milestone:` alone. `{name}`
        # is offered to a template that has the slot, and the name is STAMPED
        # after the render either way: the packaged bug.md has no slot, nor
        # does any copy `pm templates` wrote out, and a render alone would drop
        # the name for every one of those trees without a word.
        values = {vocabulary.FIELD_ID: bid,
                  vocabulary.FIELD_KIND: vocabulary.GRAIN_BUG,
                  vocabulary.GRAIN_MILESTONE: mid, 'slug': slug}
        if name:
            values[vocabulary.FIELD_NAME] = name
        body = templates.render(templates.load(cfg, vocabulary.GRAIN_BUG),
                                values)
        _mint(cfg, bf, body)
        _ok(f'created {cfg.rel(bf)}')
        if name:
            _stamp_field(cfg, bf, bid, vocabulary.FIELD_NAME, name)
        elif cfg.breadcrumbs:
            # The no-name form stays: scripts written against it exit 0 and a
            # refusal would break them (rule 7). The gap is NAMED instead (rule
            # 11), on stderr, so stdout stays the one line the write wrote.
            print(f"[pm] next: `pm set {bid} name '<name>'` — `name:` is "
                  f'empty, so the bug is addressable by its id alone',
                  file=sys.stderr)
        if cause:
            _stamp_field(cfg, bf, bid, CAUSED_BY, cause)
        return 0
    if grain == 'handoff':
        # ON DEMAND ONLY. `new milestone` deliberately does NOT mint this
        # doc: an absent handoff.md is the signal `check pm` warns on when a
        # milestone moves into an `in_progress` state, and auto-writing one
        # into every milestone would destroy it. This verb is what the
        # warning's hint names, so the fix stays one command.
        if len(rest) != 1:
            raise Usage(USAGE)
        mid = rest[0]
        grain = inventory.grain_index(cfg).get(mid)
        if grain is None or grain.kind != vocabulary.GRAIN_MILESTONE:
            raise Usage(f'no milestone resolves from {mid!r}')
        doc = inventory.shared_doc(cfg, grain, vocabulary.HANDOFF_FILE_NAME)
        if doc.is_file():
            # Never clobbered: the traps section is the one thing in the tree
            # no command can regenerate.
            _ok(f'{cfg.rel(doc)} already exists (no-op) — `pm new milestone '
                f'{mid}` restores its header line if that is what is missing')
            return 0
        try:
            body = templates.render(
                templates.load(cfg,
                               vocabulary.SLOT_TEMPLATE[vocabulary.HANDOFF_FILE_NAME]),
                {vocabulary.FIELD_ID: mid,
                 vocabulary.FIELD_NAME: grain.field(vocabulary.FIELD_NAME)})
        except (OSError, UnicodeDecodeError, templates.MissingTemplate) as err:
            raise Usage(f'the handoff template cannot be read ({err}) — '
                        f'{cfg.rel(doc)} was not created') from err
        _mint(cfg, doc, body)
        _ok(f'created {cfg.rel(doc)}')
        return 0
    raise Usage(USAGE)


# --- decide -------------------------------------------------------------------
def _decision_log(cfg: vocabulary.PmConfig, gid: str) -> tuple[Path, str]:
    """(the decisions.md the grain `gid` names, its text — minted from the
    template if absent). Nothing is written here; the caller writes once.
    """
    depth = gid.count('/')
    grain = inventory.grain_index(cfg).get(gid)
    if grain is not None and grain.kind not in (vocabulary.GRAIN_MILESTONE,
                                                vocabulary.GRAIN_FEATURE):
        raise Refused(f'{gid!r} is a {grain.kind} — those have no decision '
                      f'log; name the feature or milestone that owns the choice')
    if grain is None and (depth > 1 or f'/{vocabulary.BUGS_DIR}/' in gid):
        raise Refused(f'{gid!r} is a story or a bug — those have no decision '
                      f'log; name the feature or milestone that owns the choice')
    if grain is None:
        raise Usage(f'no milestone or feature resolves from id {gid!r}')
    log = inventory.shared_doc(cfg, grain, vocabulary.DECISION_FILE_NAME)
    if log.is_file():
        try:
            return log, frontmatter.read_raw(log)
        except (OSError, UnicodeDecodeError) as err:
            raise Usage(f'cannot read {cfg.rel(log)} ({err})') from err
    try:
        return log, templates.render(
            templates.load(cfg, vocabulary.SLOT_TEMPLATE[vocabulary.DECISION_FILE_NAME]),
            # The GRAIN's name. This read used to join `milestone.md` onto the
            # log's own parent, which is the grain's directory in a NESTED tree
            # and the pool in a pooled one — so every decisions log minted
            # since 0.4.0 got `name:` as the empty string.
            {vocabulary.FIELD_ID: gid,
             vocabulary.FIELD_NAME: grain.field(vocabulary.FIELD_NAME)})
    except (OSError, UnicodeDecodeError, templates.MissingTemplate) as err:
        raise Usage(f'the decisions template cannot be read ({err}) — '
                    f'{cfg.rel(log)} was not created') from err


def cmd_decide(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Append one dated, ordinal-stamped heading; the prose is the author's
    and no field schema is imposed. The title is the remaining argv joined
    with one space; a dangling operator left by a shell split is refused.
    Refuses whole."""
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
    eid = inventory.next_entry_id(text)
    when = datetime.now(timezone.utc).date().isoformat()
    try:
        frontmatter.write_raw(log, inventory.append_heading(text, eid, when, title))
    except OSError as err:
        raise Usage(f'could not append to {cfg.rel(log)} ({err})') from err
    _ok(f'{cfg.rel(log)}: {eid} — {when} — {title}')
    # The ledger is per-milestone (D6), so a feature's decision lands in its
    # milestone's file, named by the grain.
    # The GRAIN's document, not the log's: a decisions.md declares no
    # `id:`, and the row belongs to the grain that made the choice.
    _stamp(cfg, _grain_of(cfg, gid), ledger.decision_row(gid, eid, title))
    return 0


# --- ledger -------------------------------------------------------------------
# `pm ledger record` copies what the transcript holds, omits what it lacks, and
# labels nothing; it refuses only input it cannot read, and the one question it
# cannot answer — which ledger, when two milestones are building.
SPLIT_FLAGS = ('--tokens-in', '--tokens-out')
# The ledger's own sub-roster. Spelled once: the refusal used to carry
# `(record, show, report)` as a literal beside the branches that implement it,
# which is the second scoreboard this milestone kept finding — and it left
# `tests/test_install.py`'s verb resolver blind to the family, so a definition
# citing `pm ledger frobnicate` resolved silently (0.6.0 review S4).
LEDGER_RECORD, LEDGER_SHOW, LEDGER_REPORT = 'record', 'show', 'report'


def ledger_commands() -> tuple[str, ...]:
    """The sub-verbs `pm ledger` dispatches, in the order its help names them."""
    return (LEDGER_RECORD, LEDGER_SHOW, LEDGER_REPORT)


TOTAL_FLAG = '--tokens-total'
LEDGER_FLAGS = ('--from-transcript', '--event', '--agent-id', '--agent-type',
                '--session-id', '--grain', *SPLIT_FLAGS, TOTAL_FLAG,
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


def _row_ledger(cfg: vocabulary.PmConfig, grain: inventory.Grain | None) -> Path:
    """The ledger this row belongs to: the milestone that owns the row's GRAIN,
    read from the grain's own document and from nothing else (D1).

    **No status is consulted on any write path.** The lookup this replaced
    asked which milestone was `in_progress` and refused on none and on several,
    so a tree mid-planning lost every row it wrote, silently. `path` is the
    row's grain document, or None when the row names none (those land
    grainless, D3); the caller passes the PATH because resolution also stamps
    `grain`, so the id a reader sees and the ledger cannot disagree."""
    if grain is None:
        if not cfg.roadmap.is_dir():
            raise Refused(f'there is no PM tree at {cfg.rel(cfg.roadmap)}, so '
                          f'there is no ledger a row naming no grain belongs '
                          f'to; no row was written')
        return ledger.grainless_path(cfg.roadmap)
    found = _ledger_of(cfg, grain.field(vocabulary.FIELD_ID))
    if found is None:
        raise Refused(f'{cfg.rel(grain.path)} names no milestone, so there is '
                      f'no ledger its row belongs to; no row was written')
    return found


def _tree_snapshot(cfg: vocabulary.PmConfig) -> dict:
    """The active tree's live state, verbatim, at the instant of the row (D3):
    every id sorted, empty lists when empty, no ranking. The category keys
    (`*_in_progress`) are what the row means; the frozen seed-word keys below
    are deprecated — kept because written rows are never rewritten, removed at
    the next major (D7)."""
    frozen: dict[str, list[str]] = {
        'milestones_building': [], 'features_building': [], 'features_review': [],
        'stories_wip': [], 'stories_review': [],
    }
    live: dict[str, list[str]] = {
        'milestones_in_progress': [], 'features_in_progress': [],
        ledger.STORIES_IN_PROGRESS: [],
    }

    def add(snap: dict, bucket: str, found: inventory.Grain) -> None:
        gid = found.field(vocabulary.FIELD_ID)
        if gid:
            snap[bucket].append(gid)

    def in_progress(kind: str, status: str) -> bool:
        return vocabulary.category_of(cfg, kind, status) == vocabulary.IN_PROGRESS

    for _milestone in inventory.milestones(cfg):
        mstat = _milestone.field(vocabulary.FIELD_STATUS)
        if in_progress(vocabulary.GRAIN_MILESTONE, mstat):
            add(live, 'milestones_in_progress', _milestone)
        if mstat == vocabulary.BUILDING:
            add(frozen, 'milestones_building', _milestone)
        for feature in inventory.feature_grains(cfg, _milestone.gid):
            fstat = feature.field(vocabulary.FIELD_STATUS)
            if in_progress(vocabulary.GRAIN_FEATURE, fstat):
                add(live, 'features_in_progress', feature)
            if fstat == vocabulary.BUILDING:
                add(frozen, 'features_building', feature)
            elif fstat == vocabulary.REVIEWING:
                add(frozen, 'features_review', feature)
            for story in inventory.story_grains(
                    cfg, feature.field(vocabulary.FIELD_ID)):
                sstat = story.field(vocabulary.FIELD_STATUS)
                if in_progress(vocabulary.GRAIN_STORY, sstat):
                    add(live, ledger.STORIES_IN_PROGRESS, story)
                if sstat == vocabulary.BUILDING:
                    add(frozen, 'stories_wip', story)
                elif sstat == vocabulary.REVIEWING:
                    add(frozen, 'stories_review', story)
    return {bucket: sorted(ids)
            for bucket, ids in (*frozen.items(), *live.items())}


def cmd_ledger(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    if not args:
        raise Usage(USAGE)
    sub, rest = args[0], args[1:]
    table = {LEDGER_RECORD: cmd_ledger_record, LEDGER_SHOW: cmd_ledger_show,
             LEDGER_REPORT: cmd_ledger_report}
    if sub in table:
        return table[sub](cfg, rest)
    raise Usage(f'unknown ledger subcommand {sub!r} '
                f'({", ".join(ledger_commands())})')


def cmd_ledger_record(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Append one row — dispatch/session from a transcript or by hand, or a
    gate. The forms are exclusive; every hand-form number is optional and an
    omitted one is an omitted key, never a zero, except the gate form's
    `--duration-ms`, which is required."""
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
    split = [flag for flag in SPLIT_FLAGS if flag in flags]
    if TOTAL_FLAG in flags and (split or '--from-transcript' in flags):
        raise Usage(f'{TOTAL_FLAG} is exclusive with '
                    f'{" ".join(split or ["--from-transcript"])}: one total '
                    f'reported and a split measured are two measurements, and '
                    f'a row carrying both is a row that can disagree with '
                    f'itself. Name whichever one you actually have')
    # `--from-transcript` and `--grain` answer two questions and both may be
    # asked at once: the transcript is where the NUMBERS come from, `--grain`
    # is what the work was ON. A dispatched agent is TOLD its grain in the
    # prompt that starts it, so the courier copies a known fact rather than
    # guessing (D2), and refusing the pair refuses the point of the flag.
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
    named = _grain_of(cfg, grain) if grain else None
    if source:
        kind = _event_kind(_required(flags, '--event'))
        fields.update(_from_transcript(source, flags))
        if named is not None:
            # The id the GRAIN declares, not the string the caller typed —
            # `_ledger_id` is what every other row is stamped with, so two rows
            # naming one grain cannot spell it two ways.
            fields[ledger.GRAIN_FIELD] = _ledger_id(named.path, grain)
        else:
            # A resolved grain ROUTES the row as well as naming it — one rule
            # (D1), whichever way the grain arrived.
            named = _resolved_grain(cfg, _grain_from_tree(fields['tree']))
            if named is not None:
                fields[ledger.GRAIN_FIELD] = _ledger_id(named.path, '')
    else:
        kind = _event_kind(flags.get('--event', 'SubagentStop'))
        fields.update(_by_hand(named, grain, flags))
    row = ledger.usage_row(kind, **fields)
    target = _row_ledger(cfg, named)
    try:
        ledger.append_to(target, row)
    except OSError as err:
        raise Usage(f'{cfg.rel(target)} could not be appended '
                    f'to ({err}); no row was written') from err
    _ok(f'ledger {kind} row appended to {cfg.rel(target)}')
    return 0


def _record_gate(cfg: vocabulary.PmConfig, flags: dict[str, str]) -> int:
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
    # Nowhere to file a gate row is a TRUE and unremarkable fact; reporting
    # it as a REFUSAL made every gate print `the recorder exited 1`, which
    # reads as a broken install (0.3.0 review X1). Information, not a failure:
    # one line on stderr, exit 0, no row. 0.4.0/D3 narrows WHEN to one case — a
    # gate row names no grain, so the only way to have nowhere to file is to
    # have no PM tree at all.
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


def _resolved_grain(cfg: vocabulary.PmConfig, gid: str) -> inventory.Grain | None:
    """The grain a VERB resolved, or None. A refusal here
    would be a row lost to a lookup nobody asked for, so an id that will not
    resolve is treated as no resolution at all: the key is omitted and the row
    lands in `rows naming no grain`, a bucket somebody can read. `--grain` is
    the opposite case and still refuses — a caller who named a grain must be
    told the name is wrong."""
    if not gid:
        return None
    try:
        return _grain_of(cfg, gid)
    except (Usage, inventory.AmbiguousStory) as err:
        # BOTH, and the second is why this is not `except Usage`.
        # `inventory.story_file` raises `AmbiguousStory`, a plain `Exception`, when
        # two files claim one id — so a duplicated id turned a lookup nobody
        # asked for into exit 2 with NO ROW WRITTEN ANYWHERE, breaking the
        # fail-open promise the couriers depend on. And it SAYS SO (W4): a
        # single candidate that will not resolve was the silent third case.
        print(f'[pm] the tree named a grain this verb could not resolve '
              f'({err}) — the row is filed without one and lands in `rows '
              f'naming no grain`; `agentic-sdlc check pm` reports the tree '
              f'defect', file=sys.stderr)
        return None


def _grain_from_tree(snap: dict) -> str:
    """The grain a row with no `--grain` is about, or `''` — D2's fallback.

        exactly one story in progress   use it
        none / several                  omit the key (several are NAMED)

    The orchestrator's path: an agent nobody dispatched has no prompt to read a
    grain out of. Read off the row's OWN `tree` snapshot, so the grain a row
    names and the tree it recorded cannot disagree, and STORIES ONLY — billing
    a container is the same guess one level coarser. **An unresolvable grain is
    an OMITTED KEY**, never a guess: a row filed against the wrong story is
    uncorrectable, one filed against none is visible in an existing bucket.
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


def _by_hand(found: inventory.Grain, grain: str, flags: dict[str, str]) -> dict:
    """The hand form's fields, over the already-resolved GRAIN — `--grain`
    resolves through `_grain_of` in the caller, because a typo'd id in a ledger
    row is a lie nothing downstream can check, and the same resolution routes
    the row."""
    usage = {}
    for key, flag in zip(('input', 'output'), SPLIT_FLAGS):
        if flag in flags:
            usage[key] = _count_flag(flag, flags[flag])
    fields: dict[str, object] = {
        ledger.GRAIN_FIELD: _ledger_id(found.path, grain)}
    if usage:
        # Only the keys the caller gave: absent, not 0, means nobody counted.
        fields['usage'] = usage
    if TOTAL_FLAG in flags:
        fields[ledger.TOTAL_KEY] = _count_flag(TOTAL_FLAG, flags[TOTAL_FLAG])
    for key, flag in (('tool_calls', '--tool-calls'),
                      ('duration_s', '--duration-s')):
        if flag in flags:
            fields[key] = _count_flag(flag, flags[flag])
    return fields


def _grain_kind(cfg: vocabulary.PmConfig, gid: str) -> str:
    """Which vocabulary an id answers to — the kind the GRAIN declares. It
    used to count slashes, the nested id shape, so every pooled id read as a
    milestone and `open_seconds` asked the milestone vocabulary whether a
    feature had finished: harmless while two flows share a `done` word, a
    growing age beside `[shipped]` when they do not."""
    return inventory.kind_of(cfg, gid)


def cmd_ledger_show(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """One grain's rows, oldest first, with the seconds between status rows; a
    total only once the grain reached a finished state. No rows is exit 0 — a
    fact, not an error."""
    rest = [a for a in args if a != JSON_FLAG]
    as_json = JSON_FLAG in args
    if len(rest) != 1:
        raise Usage(USAGE)
    gid = rest[0]
    found = _grain_of(cfg, gid)
    path = found.path
    owner = _ledger_of(cfg, found.field(vocabulary.FIELD_ID) or gid)
    if owner is None:
        raise Usage(f'{cfg.rel(path)} names no milestone, so no ledger owns '
                    f'{gid!r}')
    # Both spellings: the id the caller typed and the id the file claims, which
    # is what `_stamp` wrote.
    names = {gid, _ledger_id(path, gid)}
    # BOTH ledgers, the same pair `ledger report` reads. The milestone's holds
    # every attributed row; the tree's holds the rows naming no grain (D3), one
    # of which can still NAME this grain through its `tree` snapshot. Reading
    # only the first made `report` bill the story for a row `show` printed as
    # `no rows`, and D3's argument against per-feature ledgers rests on this
    # verb answering.
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
    rows.sort(key=lambda r: str(r.data.get(ledger.TS_FIELD) or ''))
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
        kind = row.data.get(ledger.KIND_FIELD, '')
        line = f'{row.data.get(ledger.TS_FIELD, "")}  {kind:<{KIND_COLUMN}}'
        if kind == ledger.KIND_STATUS:
            line += f'  {row.data.get("from")} -> {row.data.get("to")}'
            gap = ledger._gap(previous, row)
            if previous is not None and gap is not None:
                line += f'  +{gap}s'
            previous = row
        elif arrive.disposition_of(row.data):
            line += ledger._disposition_cells(row.data)
        elif kind in ledger.ROW_CELLS:
            line += ledger.ROW_CELLS[kind](row.data)
        print(line.rstrip())
    status = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_STATUS]
    total = ledger.total_seconds(cfg, _grain_kind(cfg, gid), status)
    if total is not None:
        print(f'first row → terminal row: {total}s')
    return 0


# How wide the kind column this verb prints is, off `ledger`'s own kinds —
# `{kind:<8}` predated `check.verdict` (13). It stays here, with the only line
# that formats against it, and it has to: `vars(ledger)` is a question only a
# module OUTSIDE `ledger` can ask of it. The cells it lines up moved to
# `ledger.py`, beside the `*_row` minters whose keys they read.
KIND_COLUMN = max(len(word) for name, word in vars(ledger).items()
                  if name.startswith('KIND_') and isinstance(word, str))


# --- ledger report ------------------------------------------------------------
# The report is the caller the ledger leaves judgement to: sum, count, subtract
# and group over rows on disk, and nothing else (D5 — no weight, price, score
# or label). It reads and never writes.
REPORT_HINT = ', or name one: `pm ledger report <milestone-id>`'

# `--from <rev>` reads the milestone out of git (D6); the rev is always the
# caller's, never searched for.
FROM_FLAG = '--from'


def cmd_ledger_report(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """One milestone's rows, added up per grain — see report.py. The building
    milestone by default, an explicit id otherwise; no `ledger.jsonl` prints
    one line at exit 0. `--from <rev>` runs the same `report.build` over
    `report.GitSource`, writing nothing and touching no index. MORE THAN ONE
    milestone id compares them — `_ledger_compare` below, the same sections'
    totals side by side."""
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
                        f'{JSON_FLAG}, {FROM_FLAG} <rev> and a grain id)')
    if given and len(rest) > 1:
        # Two subjects, one rev: the pair is only comparable if both were read
        # at the SAME moment, and one `--from` cannot say which moment each
        # milestone should be read at without picking for the caller.
        raise Usage(f'{FROM_FLAG} reads ONE rev and {len(rest)} milestone ids '
                    f'were named — which rev each should be read at is not a '
                    f'thing one {FROM_FLAG} can say. Report them one at a '
                    f'time, or drop {FROM_FLAG} to compare them on the tree')
    if given and not rest:
        # "The building milestone" is a fact about today's tree, not about a
        # rev.
        raise Usage(f'{FROM_FLAG} needs a milestone id: which milestone is '
                    f'`building` is a fact about the tree NOW, and a report at '
                    f'a rev may not take its subject from one tree and its '
                    f'rows from another — `pm ledger report <milestone-id> '
                    f'{FROM_FLAG} <rev>`')
    if len(rest) > 1:
        return _ledger_compare(cfg, rest, as_json)
    try:
        src: report.Source = (report.GitSource(cfg.root, rev) if given
                              else report.DiskSource())
        focus = ''
        if given:
            mdir = _report_milestone_dir_at(cfg, src, rest[0])
        elif rest:
            mdir, focus = _report_grain_dir(cfg, rest[0])
        else:
            mdir = _report_default_dir(cfg)
        # `mdir` is the milestone's DOCUMENT since 0.4.0 — a pooled tree has
        # no per-milestone directory — so the id comes off it and the ledger is
        # addressed by that id. Both joins are asked of `src`: a rev read
        # against today's disk would look for a retired milestone's rows in the
        # layout the retire left behind.
        mid = _ledger_id(src.milestone_doc(mdir), mdir.stem, src)
        path = src.ledger_for(cfg, mid)
        # Two files, one report. The milestone's ledger holds every
        # ATTRIBUTED row; the tree's root ledger holds the rows naming no grain
        # (D3), where `gate` and `test` rows live by construction. Reading only
        # the first would empty that bucket and the gate-cost section for every
        # milestone — the report going quiet about rows that exist.
        root = ledger.grainless_path(cfg.roadmap)
        try:
            rows = src.ledger_rows(path)
            if root != path:
                rows += src.ledger_rows(root)
        except ledger.LedgerError as err:
            raise Usage(f'{err}') from err
        try:
            data = (report.clock_report(cfg, mid, mdir, rows, src, focus)
                    if focus else report.build(cfg, mid, mdir, rows, src))
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
        # documents, so the report still prints when those hold something — and
        # a focused report is section 1's clock alone, so it stops here.
        print(f'{report.HEADING_PREFIX} {report.heading_id(data)} — '
              f'{report.NO_LEDGER}')
        if focus or not report.beyond_ledger(data):
            return 0
    for line in (report.clock_render(cfg, data) if focus
                 else report.render(cfg, data)):
        print(line)
    return 0


def _report_milestone_dir_at(cfg: vocabulary.PmConfig, src: report.GitSource,
                             mid: str) -> Path:
    """The milestone's handle at a rev, or exit 2 naming what is not there —
    its document in the pool, or the `<mid>-*` directory a rev from before the
    migration holds. A rev after the retirement is the ordinary mistake, so
    the message says which rev to reach for."""
    # Graded against TODAY's tree, so the refusal says which of the two it
    # is: the tree takes any grain id, and what refuses here is the rev.
    grain = inventory.grain_index(cfg).get(mid)
    if grain is not None and grain.kind != vocabulary.GRAIN_MILESTONE:
        raise Usage(f'{mid!r} is a {grain.kind} in this tree, and {FROM_FLAG} '
                    f'reads ONE milestone out of git (D6) — name the milestone '
                    f'that held it; a report on the tree takes any grain id')
    if not inventory.segment_is_literal(mid):
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


def _report_nothing_declares(cfg: vocabulary.PmConfig, src: report.GitSource,
                             mid: str) -> str:
    """Where the rev was looked in, and what was not there."""
    if src.is_pooled(cfg):
        pool = src.spec(inventory.pool_dir(cfg, vocabulary.GRAIN_MILESTONE))
        return f'no document in {pool} declares `id: {mid}`'
    return (f'no milestone directory {mid}-* under {cfg.roadmap_dir}/ or '
            f'{cfg.roadmap_dir}/{vocabulary.ARCHIVE_DIR_NAME}/ at {src.rev}')


def _report_default_dir(cfg: vocabulary.PmConfig) -> Path:
    """Which milestone a bare `ledger report` is ABOUT — the current release's,
    from `order` plus `[pm] version_at`. Not a routing rule and not
    `_row_ledger`'s twin: no row is placed by this (D1/D7). It answers a
    MISSING ARGUMENT from the plan, the same act as `pm next`, and refuses with
    the plan's own words when the plan cannot answer."""
    mdir, why = inventory.release_milestone(cfg)
    if mdir is None:
        raise Usage(f'{why}{REPORT_HINT}')
    return mdir


def _report_grain_dir(cfg: vocabulary.PmConfig, gid: str) -> tuple[Path, str]:
    """(the milestone document the report reads, the grain it is NARROWED to).
    The id names the LEVEL; a feature or story reports through the milestone
    that owns it, because that is where its rows are (D6). '' is a milestone
    and the whole report, anything else the clock at that level."""
    # `_grain_file` first, so an id that resolves to nothing gets the ONE
    # refusal every verb gives it — the shared grammar and the shared
    # sentence — rather than a second wording invented here.
    _grain_file(cfg, gid)
    grain = inventory.grain_index(cfg).get(gid)
    if grain is None:
        raise Usage(f'no grain resolves from id {gid!r}')
    if grain.kind == vocabulary.GRAIN_MILESTONE:
        return grain.path, ''
    owner = inventory.milestone_of(cfg, gid)
    holder = inventory.grain_index(cfg).get(owner) if owner else None
    if holder is None:
        raise Usage(f'{gid!r} is a {grain.kind} bound to no milestone in this '
                    f'tree, so none of its rows is in a ledger — bind it with '
                    f'`pm set {gid} milestone <id>`, or name a milestone')
    return holder.path, gid


def _ledger_compare(cfg: vocabulary.PmConfig, ids: list[str],
                    as_json: bool) -> int:
    """More than one milestone, side by side — one `report.build` per id, then
    `report.compare_data`. Reads and writes nothing, like the one-id form.

    WHICH milestones is the caller's to say (rule 9); what the tree may supply
    is the SEQUENCE, and only when it declared one for every id named.
    """
    twice = [gid for i, gid in enumerate(ids) if gid in ids[:i]]
    if twice:
        raise Usage(f'{twice[0]!r} was named twice — a milestone compared with '
                    f'itself is a delta of zero by construction, and which '
                    f'other one was meant is not a thing this verb may pick')
    src = report.DiskSource()
    handles: dict[str, Path] = {}
    for gid in ids:
        # The shared refusal for an id that resolves to nothing comes from
        # `_report_grain_dir`, so two ids get the one sentence every verb
        # gives a bad id rather than a second wording invented here.
        mdir, focus = _report_grain_dir(cfg, gid)
        if focus:
            kind = inventory.grain_index(cfg)[gid].kind
            raise Usage(f'{gid!r} is a {kind} and a comparison is between '
                        f'MILESTONES — a ledger is per milestone (D6), so two '
                        f'{kind}s under one milestone would be one ledger read '
                        f'twice. Name the milestones, or one id alone for the '
                        f'clock at that level')
        handles[gid] = mdir
    order = inventory.declared_order(cfg)
    # All of them or none: sequencing HALF the list by the plan and the rest by
    # the argument line is a rule nobody could read off the output.
    planned = all(gid in order for gid in ids)
    basis = report.ORDER_PLAN if planned else report.ORDER_GIVEN
    root = ledger.grainless_path(cfg.roadmap)
    documents: list[tuple[str, dict]] = []
    missing: list[str] = []
    for gid in (sorted(ids, key=order.index) if planned else ids):
        mdir = handles[gid]
        mid = _ledger_id(src.milestone_doc(mdir), mdir.stem, src)
        path = src.ledger_for(cfg, mid)
        try:
            rows = src.ledger_rows(path)
            if root != path:
                rows += src.ledger_rows(root)
        except ledger.LedgerError as err:
            raise Usage(f'{err}') from err
        if not src.is_file(path):
            missing.append(mid)
        try:
            documents.append((mid, report.build(cfg, mid, mdir, rows, src)))
        except report.RecordError as err:
            raise Usage(f'{err}') from err
    data = report.compare_data(cfg, documents, basis)
    if as_json:
        print(json.dumps(data, ensure_ascii=False))
        return 0
    lines = report.compare_lines(cfg, data)
    print(lines[0])
    # Under the heading rather than at the end: a milestone contributing no
    # rows of its own is why a column is 0, and a reader meets the zero first.
    for mid in missing:
        print(f'   {mid} — {report.NO_LEDGER}')
    for line in lines[1:]:
        print(line)
    return 0


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


def _plan_path(cfg: vocabulary.PmConfig) -> Path:
    return inventory.releases_file(cfg)


def _mint_plan(cfg: vocabulary.PmConfig) -> Path:
    """The plan document, created from the scaffold if this is the first entry."""
    path = _plan_path(cfg)
    if not path.is_file():
        # Through `core.apply`, like every other mutation.
        apply.raise_on_error(apply.make_dir(path.parent))
        frontmatter.write_raw(path, _PLAN_SCAFFOLD)
    return path


def _resolve(cfg: vocabulary.PmConfig, gid: str, role: str) -> inventory.Grain:
    """One id to its grain, or exit 2 naming which argument."""
    defect = inventory.id_defect(gid)
    if defect:
        raise Usage(f'the {role} id {gid!r} names no grain — {defect}')
    found = inventory.grain_index(cfg).get(gid)
    if found is None:
        raise Usage(f'no grain resolves from the {role} id {gid!r}')
    return found


def _parent(cfg: vocabulary.PmConfig, gid: str) -> tuple[inventory.Grain, bool]:
    """(the parent grain, whether the plan has to be minted for it) — the ROOT
    does not exist until something is scheduled."""
    if inventory.root_grain(cfg) is None and gid == vocabulary.ROOT_ID:
        return inventory.Grain(gid=gid, kind=vocabulary.ROOT_KIND,
                           path=inventory.releases_file(cfg)), True
    return _resolve(cfg, gid, 'parent'), False


def _sequence(cfg: vocabulary.PmConfig, parent: inventory.Grain) -> list[str]:
    """The parent's declared `order`, refusing a list this writer cannot rewrite."""
    defect = parent.sequence_defect(vocabulary.ORDER_KEY)
    if defect:
        raise Refused(f'{cfg.rel(parent.path)} {defect} — nothing was written')
    return parent.list_field(vocabulary.ORDER_KEY)


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


def cmd_add(cfg: vocabulary.PmConfig, args: list[str]) -> int:
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
    refusal = vocabulary.may_hold(cfg, parent.kind, child.kind)
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
    bind = vocabulary.BINDS_TO.get(child.kind)
    wrote = []
    if bind is not None:
        field = bind[1]
        before = child.field(field)
        if before != parent.gid:
            if not frontmatter.set_field(child.path, field, parent.gid):
                raise Refused(f'{cfg.rel(child.path)} has no frontmatter block '
                              f'to put `{field}:` in — nothing was written')
            wrote.append(f'{child.gid}: {field} {before!r} -> {parent.gid!r}')
            # ONLY when the old parent really lists it (0.6.0/D11).
            former = inventory.grain_index(cfg).get(before) if before else None
            if former is not None and child.gid in _sequence(cfg, former):
                wrote.append(f'  noticed: {before} still lists {child.gid} in '
                             f'its `order` — that entry is now DANGLING; '
                             f'`agentic-sdlc pm remove {before} {child.gid}` '
                             f'takes it out')

    # THE SEQUENCE — the parent's list, through the byte-honest writer.
    if placed != entries:
        if not frontmatter.set_list_field(parent.path, vocabulary.ORDER_KEY, placed):
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


def cmd_remove(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """Unbind a child AND unsequence it, together — the pair `add` writes,
    taken back. `pm set <id> <field> ""` still unbinds alone."""
    if len(args) != 2:
        raise Usage(f'remove takes <parent-id> <child-id>, got '
                    f'{len(args)} argument(s)')
    parent = _resolve(cfg, args[0], 'parent')
    child = _resolve(cfg, args[1], 'child')
    rel = cfg.rel(parent.path)
    entries = _sequence(cfg, parent)
    bind = vocabulary.BINDS_TO.get(child.kind)
    field = bind[1] if bind is not None else ''
    bound = (child.field(field)
             if field else '')
    elsewhere = bool(field and bound and bound != parent.gid)
    if elsewhere and child.gid not in entries:
        raise Refused(f'{child.gid} names {bound} as its {bind[0]}, not '
                      f'{parent.gid} — nothing was written')
    wrote = []
    if field and bound and not elsewhere:
        if not frontmatter.set_field(child.path, field, ''):
            raise Refused(f'{cfg.rel(child.path)} could not be rewritten — '
                          f'nothing was written')
        wrote.append(f'{child.gid}: {field} {bound!r} -> \'\'')
    if child.gid in entries:
        if not frontmatter.set_list_field(parent.path, vocabulary.ORDER_KEY,
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


# `pm roadmap`'s columns IN ORDER — the DECLARATION `tests/test_contracts.py`
# holds the `--help` line to and `tests/test_pm_order.py` holds the row width
# to. `name` and `summary` are here because a RETIRED release has to print
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


def cmd_roadmap(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """The plan: every scheduled milestone, then the backlog. Writes nothing —
    what `pm status` does for one milestone, for the SEQUENCE, and what
    replaced the hand-maintained `ROADMAP.md`. A retired entry prints from its
    `retire` row in the tree's own `ledger.jsonl`, the only copy of a shipped
    release's version, name and summary once its documents are gone."""
    if args:
        raise Usage(f'roadmap takes no arguments, got {" ".join(args)}')
    entries = inventory.declared_order(cfg)
    path = inventory.releases_file(cfg)
    defect = inventory.plan_defect(cfg)
    if defect is not None:
        raise Refused(f'{cfg.rel(path)} {defect}')
    try:
        retired = ledger.retired_releases(cfg)
    except ledger.LedgerError as err:
        raise Usage(f'{err}') from err
    if not entries:
        print(f'[pm] {cfg.rel(path)} declares no order — '
              f'`agentic-sdlc pm add {inventory.root_id(cfg)} <milestone-id>` '
              f'starts the plan')
    else:
        print(f'[pm] {len(entries)} scheduled release(s) in {cfg.rel(path)}')
        for mid in entries:
            milestone = inventory.grain(cfg, mid, vocabulary.GRAIN_MILESTONE)
            if milestone is None:
                row = retired.get(mid, {})
                print(_roadmap_row((
                    row.get('version', ''), mid,
                    RETIRED_STATE if row else DANGLING_STATE,
                    row.get('name', ''), row.get('summary', ''))))
                continue
            version = inventory.milestone_version(cfg, mid)
            state = ('shipped' if inventory.entry_is_shipped(cfg, mid)
                     else milestone.field(vocabulary.FIELD_STATUS) or DASH)
            print(_roadmap_row((version or NO_VERSION, mid, state,
                                milestone.field(vocabulary.FIELD_NAME), '')))
    scheduled = set(entries)
    backlog = sorted(mid for _, mid in inventory.known_milestones(cfg)
                     if mid and mid not in scheduled)
    if backlog:
        print(f'[pm] {len(backlog)} in backlog (on no plan — not scheduled '
              f'as a release)')
        for mid in backlog:
            milestone = inventory.grain(cfg, mid, vocabulary.GRAIN_MILESTONE)
            print(_roadmap_row((
                inventory.milestone_version(cfg, mid), mid,
                milestone.field(vocabulary.FIELD_STATUS) if milestone else '',
                milestone.field(vocabulary.FIELD_NAME) if milestone else '',
                '')))
    return 0


def cmd_next(cfg: vocabulary.PmConfig, args: list[str]) -> int:
    """The first entry in `order` that has not shipped, and what it claims."""
    if args:
        raise Usage(f'next takes no arguments, got {" ".join(args)}')
    entries = inventory.declared_order(cfg)
    if not entries:
        print(f'[pm] {cfg.rel(_plan_path(cfg))} declares no order — '
              f'`agentic-sdlc pm add {inventory.root_id(cfg)} <milestone-id>` '
              f'starts the plan')
        return 0
    # ONE resolver. `pm next` answering differently from what `release` and the
    # ledger resolve, over the same tree, is two scoreboards (review B1).
    mid = inventory.current_milestone(cfg)
    if mid is None:
        dangling = [g for g in entries if inventory.entry_is_dangling(cfg, g)]
        if dangling:
            print(f'[pm] every release in {cfg.rel(_plan_path(cfg))} has '
                  f'shipped; {len(dangling)} entry/ies are DANGLING (they name '
                  f'no milestone in the tree): {", ".join(dangling)}')
        else:
            print(f'[pm] every release in {cfg.rel(_plan_path(cfg))} has shipped')
        return 0
    milestone = inventory.grain(cfg, mid, vocabulary.GRAIN_MILESTONE)
    print(f'{inventory.milestone_version(cfg, mid) or NO_VERSION}\t{mid}\t'
          f'{milestone.field(vocabulary.FIELD_STATUS) if milestone else ""}')
    return 0


def _table() -> dict:
    # Deferred: `ready_for` and `skills` import this module's shared
    # vocabulary, so binding at call time keeps load order a non-question.
    from agentic_sdlc.repo.pm import ready_for, skills
    return {
        'ready-for': ready_for.cmd_ready_for,
        vocabulary.GRAIN_STORY: cmd_story, vocabulary.GRAIN_BUG: cmd_bug, vocabulary.GRAIN_FEATURE: cmd_feature,
        vocabulary.GRAIN_MILESTONE: cmd_milestone, 'retire': cmd_retire,
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


def commands() -> tuple[str, ...]:
    """The sub-verbs this router dispatches, off the router's own table."""
    return tuple(_table())


# `<verb> --help` / `-h`, ANYWHERE after the verb. Not the bare word `help`:
# that is a legal value in a title, a summary or a name, and the two flags are
# not (a flag-shaped title is already refused).
HELP_FLAGS = ('-h', '--help')

# The block `<kind> <status> <id> [<answer>...]` in USAGE describes every verb
# that ARRIVES, so each of those verbs' help carries it.
_GENERIC_ARRIVAL_HEAD = '<kind>'


def _usage_blocks() -> list[list[str]]:
    """USAGE cut into its entries: a line at a two-space indent opens one, a
    deeper line continues it, and a blank or any other line closes it."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in USAGE.splitlines():
        if line.startswith('  ') and not line.startswith('   '):
            current = [line]
            blocks.append(current)
        elif current is not None and line.startswith('   '):
            current.append(line)
        else:
            current = None
    return blocks


def verb_help(verb: str, rest: Sequence[str] = ()) -> str:
    """`verb`'s own entries out of USAGE — the router's help, one verb at a
    time, so there is ONE text and it cannot drift from the full roster. A
    second word that names a sub-form (`new bug`, `ledger report`) narrows to
    that form's entries. '' when USAGE documents no entry for the verb."""
    words = [(b, b[0].split()) for b in _usage_blocks()]
    mine = [(b, w) for b, w in words
            if w[0] == verb
            or (w[0] == _GENERIC_ARRIVAL_HEAD and verb in ARRIVES)]
    sub = next((a for a in rest if not a.startswith('-')), '')
    narrowed = [(b, w) for b, w in mine if len(w) > 1 and w[1] == sub]
    chosen = narrowed or mine
    return '\n\n'.join('\n'.join(b) for b, _ in chosen)


def _own_help() -> dict[str, str]:
    """A verb whose module carries a fuller help than its USAGE entry, printed
    AFTER the entry. Deferred for the same reason `_table` is."""
    from agentic_sdlc.repo.pm import skills
    return {'config': skills.CONFIG_USAGE}


def _help_for(verb: str, rest: Sequence[str]) -> str:
    entry = verb_help(verb, rest)
    if not entry:
        # A verb the table routes and USAGE never describes: the whole roster
        # rather than nothing, and `tests/test_pm_verbs.py` fails on it by name.
        return USAGE
    own = _own_help().get(verb, '')
    return (f'usage: {PROG}\n\n{entry}\n'
            + (f'\n{own}\n' if own else '')
            + f'\n`{PROG} --help` prints every verb.')


def main(argv: list[str], *, skipped: Skipped = ()) -> int:
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(USAGE)
        return 0 if argv else 2
    # Before the config is read: help is answered from constants, so it works
    # in a tree that declares nothing, and a `retire 0.1 --help` never retires.
    if argv[0] in _table() and any(a in HELP_FLAGS for a in argv[1:]):
        print(_help_for(argv[0], argv[1:]))
        return 0
    try:
        cfg = vocabulary.load()
    except vocabulary.ConfigError as err:
        # EVERY defect, flow first — one line each, exit 2 once. `load()` stops
        # at the first, and the first is rarely the one that matters: the tree
        # that motivated this was told about a retired key while its PM CLI was
        # refusing every work-moving verb for want of a flow (review D1).
        try:
            defects = vocabulary.all_config_defects()
        except Exception:  # noqa: BLE001 - the collector never masks the error
            defects = []
        for msg in defects or [str(err)]:
            print(f'[pm] ERROR — {msg}', file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    defect = _skipped_defect(cmd, skipped)
    if defect:
        print(f'[pm] ERROR — {defect}', file=sys.stderr)
        return 2
    fn = _table().get(cmd)
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
        return (fn(cfg, rest, tuple(skipped)) if cmd in ARRIVES
                else fn(cfg, rest))
    except Refused as err:
        print(f'[pm] REFUSED — {err}', file=sys.stderr)
        return 1
    except (Usage, inventory.AmbiguousStory, vocabulary.ConfigError) as err:
        # `ConfigError` here is the declaration's lazy half — `flow_of` refuses
        # mid-walk — and it must be one line at exit 2, since a traceback at
        # exit 1 reads as findings.
        print(f'[pm] ERROR — {err}', file=sys.stderr)
        return 2
