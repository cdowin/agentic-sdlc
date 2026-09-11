# 2026-09-11 — ledger telemetry audit (read-only scout for 0.9.0 `ms-the-ledger-is-a-stamp`)

Northstar, in Chris's words: *"The ledger is supposed to be granular, per milestone. It should be
simple telemetry that someone can stamp. start times, stop times, issue_ids being worked, token use,
etc etc."*

The code was read at HEAD `e339c52` (branch `milestone/0.8.0-a-consumer-can-take-the-bump`) and run as
`PYTHONPATH=<git archive HEAD>/src python3 -m agentic_sdlc.cli pm …`. The data is the live tree at the
time of reading, and the ledger was still being appended to, so counts drift by a row or two between
runs. The write probes ran in a scratch copy of `pm/` + `devkit.toml` from HEAD.

## The two defects

### D-A: CONFIRMED. A multi-milestone report puts the root ledger's rows into every milestone

**Where.** Both report paths concatenate the root file onto the milestone's own:

- `src/agentic_sdlc/repo/pm/cli.py:2819-2823` is the one-id report (`rows = …ledger_rows(path)`, then
  `rows += …ledger_rows(root)`).
- `src/agentic_sdlc/repo/pm/cli.py:2964-2974` is the comparison, which repeats the same two lines for
  each id.

Three places then turn the shared rows into per-milestone numbers. `report.py:1118-1120`
(`spend_data`) folds EVERY dispatch row into `totals` "before any narrowing", and `_compare_spend`
(`report.py:1960-1966`) lifts those totals as the milestone's spend row. `_compare_unattributed`
(`report.py:1996-2006`) and the gate block (`report.py:2030`) read the root file, the same for every
id. `overhead_data` counts session rows, and every courier session row lands in the root file.

The code documents this. `--help` (`pm/cli.py:435-440`) and `TREE_WIDE_NOTE`/`NO_GRAIN_NOTE`
(`report.py:1910-1927`) describe it, and `_compare_spend` says "the DELTA cancels it". So it is by
design, and against the northstar it is rule 4's first sin. A milestone's row prints numbers that are
not the milestone's. On top of that, `NO_GRAIN_NOTE` says "the delta is real and not 0" directly above
a delta that is 0 in every column.

**Repro.**

    PYTHONPATH=… python3 -m agentic_sdlc.cli pm ledger report \
        ms-the-rule-reaches-the-work ms-a-consumer-can-take-the-bump --json     # exit 0
    spend per grain       0.6.0  dispatch_rows 28  in 7292 out 322315 cache_create 8136959 cache_read 461833583
                          0.8.0  dispatch_rows 33  in 7292 out 322315 cache_create 8136959 cache_read 461833583
                          delta  in 0  out 0  cache_create 0  cache_read 0
    rows naming no grain  0.6.0 = 0.8.0 = 24 dispatches, 2156 tool_calls, 27427 s    (delta 0 everywhere)
    gate cost             0.6.0 = 0.8.0 = 1181 rows, 8 gates                          (delta 0)

Why the in/out/cache numbers are identical: `ledgers/ms-a-consumer-can-take-the-bump.jsonl` holds 10
dispatch rows and **none carries `usage`** (all are hand-recorded `tokens_total` rows), so 100% of
0.8.0's split comes from the root file. The one-id headline `338306 out / 3008 tool calls / 37659 s
across 35 dispatch row(s)` is the same mix, with 25 of the 35 rows from the root file. The overhead
block reports `53 session row(s)` for 0.8.0, whose own ledger holds 0 session rows.

**The same shape in `ledger show`.** `ledger.row_names` (`ledger.py:765-776`) matches a row when the
grain appears ANYWHERE in the row's `tree` snapshot. That includes rows that STATE a different grain,
which contradicts `report.named_grains`' own rule at `report.py:757-760`. Measured on
`pm ledger show st-every-verb-answers-its-own-help --json`: 32 rows, of which 3 are about the story. The
other 29 are 10 dispatches naming other grains, 10 grainless dispatches and 9 sessions, all printed
because 14 stories were in flight.

### D-B: CONFIRMED. Couriers cannot attribute concurrent work, and the env path has never fired

**Where.** Both couriers pass `--grain` only when their own environment has `GDK_LEDGER_GRAIN`
(`tools/hooks/cc-ledger-subagent.sh:326-328`, `cc-ledger-session.sh:328-330`). The verb then does this:

1. It uses `--grain` if given (`pm/cli.py:2448`, `2452-2456`).
2. Otherwise it falls back to `_grain_from_tree` (`pm/cli.py:2606-2629`). Exactly one story in
   progress gives that story. Zero stories, or more than one, gives `''`.
3. `_row_ledger(cfg, None)` then routes the row to `<roadmap>/ledger.jsonl` (`pm/cli.py:2326-2331`).

The payload carries `agent_id`, `agent_type` and `agent_transcript_path`, and no grain (hook lines
271-286). One env value cannot name N concurrent grains. The closed
`bg-the-export-that-attributes-a-dispatch-cannot-be-run-by-its-operator` records that an orchestrator
cannot export into the hook's environment at all. *I did not verify the harness's hook-env behaviour
myself.*

**Repro (scratch tree from HEAD, 14 stories `building`).**

    pm ledger record --from-transcript tests/fixtures/transcripts/subagent-dispatch.jsonl \
        --event SubagentStop --agent-type verification-builder
    [pm] 14 stories are in progress (st-a-milestone-retired-… …) — … names none of them …
    [pm] ledger dispatch row appended to pm/roadmap/ledger.jsonl        # no `grain` key; root +1
    … same with --grain st-every-verb-answers-its-own-help
    [pm] ledger dispatch row appended to pm/roadmap/ledgers/ms-a-consumer-can-take-the-bump.jsonl

**Today's rows (ts `2026-09-11`), counted by kind and path.**

| rows | name a grain | how |
|---|---|---|
| 74 courier rows (25 dispatch + 49 session) | **12** (4 + 8) | all 12 from the one-story fallback; **0 from `GDK_LEDGER_GRAIN`** |
| 62 unattributed courier rows (21 dispatch + 41 session), all in the root file | 0 | 41 had 0 stories live and 21 had 2-15 |
| 18 hand `pm ledger record --grain` dispatch rows | 18 | typed by the orchestrator |

Across all time, **0 of 89** courier rows were attributed by any route other than the one-story
fallback. `GDK_LEDGER_GRAIN` has never attributed a row in this tree.

**What D-B causes: double counting.** All 18 of today's hand rows have a courier twin: `duration_s`
within 1 s, and a `ts` a few minutes earlier. The hand form writes no `agent_id` (none of the 18 carries
one), so nothing joins a twin to its courier row. In 3 pairs both rows name the same grain, and the
report bills that dispatch twice. For example, `st-the-pm-cli-helpers-find-a-home` in
`pm ledger report ms-nothing-is-hand-rolled` shows `dispatches 2`, `duration_s 3982`, and that was ONE
1991 s dispatch.

## Map of the ledger

**Homes.** A row that names a grain goes to `ledgers/<milestone>.jsonl`, reached through the grain's
bindings (`ledger.ledger_of_grain`, `ledger.py:425-434`). No status is read. A row naming no grain goes
to `<roadmap>/ledger.jsonl` (`grainless_path`, `ledger.py:445`). The file is chosen by **grain only**;
nothing else routes a row. Counts below cover all files as read, as root / milestone.

| kind | fields beyond `ts kind` | written by | home | count |
|---|---|---|---|---|
| status | grain from to | every `pm <kind> <state>` and belt write, `_stamp` (`pm/cli.py:753-760`) | milestone; a grain with no milestone gets no row | 0 / 465 |
| disposition | grain state answer value skipped | same `_stamp`, when the arrival was answered | milestone | 0 / 144 |
| decision | grain entry title | `pm decide` (`pm/cli.py:2258`) | milestone | 0 / 50 |
| rung.enter | grain rung ready blockers | `pm ready-for` (`ready_for.py:109`) through `emit.py`, only if `[emit]` declares a sink | by grain | 0 / 121 |
| check.verdict | rung grain check verdict detail ran | belts (`conveyor/driver.py:251`) through emit | by grain | 0 / 384 |
| rung.leave | grain state answer next_rung next_checks next_actions have value | `arrive.py:459` through emit | by grain | 0 / 121 |
| lesson, lesson.enter, lesson.verdict | grain rule source text / lesson matched rung scope [check] | `lesson record` (`conveyor/lessons.py:352-363`), lesson taps through emit | milestone | 0 / 57 |
| deviation | grain operation step outcome reason | a belt's `--force` (`conveyor/driver.py:740-757` builds it by hand; `ledger.deviation_row` has no caller in `src`) | milestone | 0 / 0 |
| retire | grain version name summary [backfilled] | `pm retire` (`pm/cli.py:1234-1279`, `1117-1147`) | **root** | 0 / 0 |
| dispatch | grain? session_id agent_id agent_type model started_at ended_at duration_s messages tool_calls tools tool_calls_before_first_write usage{input,output,cache_creation,cache_read} tokens_total tree | `pm ledger record`, from the SubagentStop courier or by hand (`pm/cli.py:2401-2474`) | milestone if a grain resolves, else root | 24 / 59 |
| session | as dispatch, minus agent_id and agent_type | Stop courier, through the same verb | same | 53 / 8 |
| gate | gate verdict duration_ms census | `pm ledger record --gate` from `tools/dev/gdk_gate.sh` (`pm/cli.py:2477-2522`) | **root, always** | 1181 / 560 |
| test | tier nodeid duration_ms rank | this repo's `tests/conftest.py:284`, not shipped | **root** | 3321 / 1190 |
| verify | rung gate verdict exit_code duration_ms state graded census | `agentic-sdlc verify` (`verify/cache.py:314`) | **root** | 73 / 0 |

The 560 gate and 1190 test rows in milestone files sit in 0.2.0-0.4.0 and predate 0.4.0/D3.

## Gap table against the northstar

| what the owner wants | stamped today? | verb, or none | gap |
|---|---|---|---|
| **start** of a unit of work | For a grain, yes: the `status` row's `ts` at `pm story building <id>`. For a dispatch or session, only the courier's `started_at`, read from the transcript. | `pm <kind> <state>`; courier | The hand form cannot stamp one (`--started-at` gives exit 2, "takes flags only"). Nothing marks a start that is not a status flip. |
| **stop** of a unit of work | For a grain, the `close story` status row. For a dispatch, the courier's `ended_at`. | belt; courier | The hand form stamps only `--duration-s`, and its `ts` is when someone typed it. |
| **issue id(s)** | **No field on any row.** `pm set <id> issue 19` writes an arbitrary frontmatter key (probed: accepted, exit 0), but no row, column, check or `pm list` reads it. | **none** | The field is missing, from the grain through to the report. |
| **token use** | The courier's measured split. By hand, `--tokens-in/--tokens-out` or `--tokens-total`. | `pm ledger record` | Concurrent courier rows are unattributed (D-B). Hand rows duplicate courier rows with no join key. |
| **agent / role** | `--agent-type` on dispatch rows (free string; `wombat` is accepted, probed). `--by agent <t>` on declared arrivals. Session rows carry none. | `pm ledger record`; arrival `--by` | There is no roster (`bg-an-unknown-agent-type…`). |
| **grain** | Always on status, disposition, decision and lesson rows. On dispatch or session rows, only through `--grain` or the one-story fallback. | `--grain` | 62 of 74 courier rows today name none. |
| **per milestone** | Only through a grain. Gate, test and verify rows, and grainless session and dispatch rows, have no milestone. | none | The report fills the gap by copying the root file into every milestone (D-A). |

## What `pm ledger show|report` can answer per milestone today

**Clean.** These read only status, disposition and decision rows, which always name a grain and live in
the milestone file: `time per state` (rolled up), `time per actor`, the per-grain `todo/in_progress/done`
seconds, `decisions per grain`, and `decision to next status row`. Yield, rework and escapes read review
records and bugs, not ledger rows.

**Contaminated:** the spend summary line and totals (every root dispatch row); `rows naming no grain`
(tree-wide); the overhead block's `session_rows` and `session deltas` (root sessions); `gate cost`
(tree-wide, though its heading says "across the whole tree"); all of these again in the comparison;
and `ledger show <grain>`, which lists any row whose snapshot contains the grain.

**Double counted:** per-grain spend wherever a courier twin and a hand twin both name the grain.

**Cannot answer at all:** a milestone's gate or verify cost, its orchestrator (session) spend, any
external issue id, and the start and stop of a hand-recorded dispatch.

## Pool grains that bear on this (checked at HEAD)

| id | status | one line | still valid |
|---|---|---|---|
| `ft-the-record-is-harvested-not-pushed` | planning, no milestone | A read verb lists candidate transcripts under `[ledger] transcripts`, and the operator pipes the chosen one into `record --from-transcript --grain`. | Yes. The courier is still push-only: no path means no row (`cc-ledger-subagent.sh:288-292`). |
| `bg-an-unknown-agent-type-is-recorded-as-a-dispatch` | open | Agent type is a free string, with no roster. | Yes. `ledger record --agent-type wombat` was accepted, exit 0. |
| `ft-an-agent-is-a-registered-kind` | planning | The roster the bug above needs. | Yes (not probed separately). |
| `bg-two-gate-runs-share-one-log-and-inflate-its-census` | open | Two concurrent gates append to one `<gate>.log`, and the census is counted off that file. | Likely. `gdk_gate.sh:296` is still `$GDK_GATE_REPORT_DIR/$gate.log`. The concurrent run was not re-probed. |
| `bg-a-ledger-reading-test-is-racy-under-xdist` | open, low | A test asserts over the real repo's ledger while other workers append to it. | Not re-probed. |
| `ft-a-phase-declares-what-it-hands-an-agent` | planning | A phase declares the prompt or role a dispatch gets. | Tangential. A dispatch stamp could be rendered from it. |
| `bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty` | closed (0.6.0) | Added the hand-record path. | Closed. The hand path is the source of the twins above. |
| `bg-a-hand-recorded-dispatch-cannot-carry-a-total` | closed (0.6.0) | Added `--tokens-total`. | Closed. |
| `bg-a-second-gate-in-one-checkout-loses-a-cost-row` | closed (0.4.0) | — | Closed. |
| `bg-the-export-that-attributes-a-dispatch-cannot-be-run-by-its-operator` | closed (0.7.0) | Fixed the surface only: it now names the serial path and the hand-record fallback. | Closed. The underlying defect is D-B. |
| `bg-the-telemetry-verb-cannot-compare-two-milestones` | closed (0.7.0) | Shipped the comparison D-A is about. | Closed. |

## Size, so a planner can judge "simple"

**Code, about 4,380 shipped lines:** `pm/ledger.py` **895**, `pm/report.py` **2,133**, the ledger
part of `pm/cli.py` about **757** (`2260-3017`) plus **211** of `--help` (`313-524`), and the couriers
`cc-ledger-session.sh` **347** and `cc-ledger-subagent.sh` **351**. Each courier ships twice,
byte-identical, in `installables/` and `tools/hooks/`. `dispatch.py` (244) is partly ledger.
**Tests:** `test_pm_ledger*` (5 files) plus `test_hooks_payloads.py`, **5,714** lines.

**Report blocks.** The one-id roster in `--help` is **7 headings + 15 table entries** (17 tables with
story/feature/bug split); the 0.8.0 run printed 7 headings, 12 tables and 203 lines. The comparison
is **9 blocks**, 4 of them contaminated (spend, no-grain, overhead, gates). **Dead code:**
`ledger.deviation_row` has no caller in `src`.

## Candidate work units for 0.9.0 (features)

1. **A milestone's numbers are its own rows.** Drop the root-file concatenation from per-milestone
   totals and from the comparison (`pm/cli.py:2819-2823`, `2964-2974`, `report.py:1118-1120`). Tree-wide
   rows get their own, separately headed tree report. `ledger show` attributes by `grain` only, and the
   snapshot is shown as a snapshot. *Covers D-A, the `show` contamination, and "per milestone".*
2. **Every row carries the branch it was filed on, and a milestone claims rows by its declared
   `branch:`.** This gives gate, verify, session and grainless dispatch rows a milestone home without
   inference: the milestone already declares its branch, and HEAD is read as text. *Covers "per
   milestone" for rows naming no grain, and the rest of D-A.*
3. **The dispatch carries its own stamp.** `agentic-sdlc dispatch --grain` renders one exact stamp
   line (grain, and issue ids). `record --from-transcript` copies it from that agent's own transcript,
   which is per-agent, so concurrent dispatches attribute. This replaces `GDK_LEDGER_GRAIN` as the
   primary path, which has attributed 0 of 89 rows. *Covers D-B.* Rule-9 risk: the line must be a
   stamp copied verbatim, never searched for.
4. **One unit of work is one row.** The hand form joins its courier twin by `agent_id` (the flag
   exists, and none of today's 18 rows used it) and annotates that row instead of adding a second
   dispatch. The report counts one dispatch per `agent_id`. *Covers the double counting.*
5. **A stamp verb.** `pm ledger stamp start|stop <grain> [--issue <id>]… [--agent <type>]
   [--tokens N]` writes paired rows to the grain's milestone ledger. An external issue id becomes a
   first-class, repeatable field, read back as a column by `show` and `report`. Agent types come from a
   roster (folds in `ft-an-agent-is-a-registered-kind`). *Covers start, stop, issue ids, agent.*
6. **The report is trimmed to the stamp.** One per-milestone table (unit, grain, issue, agent, start,
   stop, tokens), plus `time per state` and a tree-wide gate table. Yield, rework, escapes and overhead
   leave the telemetry verb or are cut. *Covers "simple": 2,133 lines and 17 tables against what the
   owner listed.*

## Not verified

How the harness builds the hook environment (from the closed bug's text). Concurrent-gate log
inflation and the xdist race (not re-probed). Whether real dispatch prompts in `~/.claude` transcripts
already carry a grain line (outside this checkout). Whether unit 2's branch stamp holds for subagents
running in agent worktrees on other branches.
