Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# 0.4.0 authoring is separate from binding — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-06 — A row is routed by its grain, not by which milestone is in progress

`cli.py` ships two routing functions and they disagree:

    _stamp()                line  255   milestone_dir_of(cfg, path) — the milestone that owns
                                        the GRAIN'S FILE. No status check at all.
    _building_ledger_dir()  line 1303   exactly one milestone in `in_progress`; refuses on
                                        none, refuses on several.

Status and decision rows take the first. The telemetry rows — `ledger record
--from-transcript` (1433), `--gate` (1525) and `ledger report` (1706) — take the second. That
is why `pm milestone building 0.4.0` wrote its own status row into 0.4.0's ledger while 0.4.0
was still `planning` at the instant of the call: `_stamp` never asked.

**One rule survives: a row goes to the ledger of the milestone that owns the row's grain.**
Status is never consulted. `_building_ledger_dir` is deleted, and with it the refusal path,
the "several milestones are in progress" failure, and the coupling between recording and
workflow state.

**Rejected: keeping the `in_progress` lookup for telemetry rows only**, on the argument that a
session row genuinely does not know its grain. It loses because D2 gives the session a grain,
and because the lookup was never a routing rule — it was a guess dressed as one, in a package
whose stated position (D5) is that the engine never picks. Two mechanisms for one fact is the
defect this whole milestone exists to delete; the telemetry layer does not get an exemption
from its own thesis.

**What it buys, beyond tidiness.** Work on a `planning` milestone records. Shaping a feature
before anyone has claimed it records against that feature. Two milestones in flight stop being
a refusal, which matters immediately: 0.3.0 and 0.4.0 are both live right now.

## D2 — 2026-09-06 — A session learns its grain from the dispatch, falling back to the tree

**The dispatch carries `--grain`; when it does not, the verb resolves the grain from the tree;
when that is ambiguous, the key is omitted.** In that order.

The dispatch wins as primary because *the information already exists at the moment of
dispatch* — an agent is told what it is working on in the prompt that starts it — so passing it
is copying a known fact, not re-deriving one. The hooks already carry `GDK_LEDGER_*` values
through `make` byte-exact, so the courier needs a fourth of the same, not a new mechanism.

Tree resolution is the fallback because an orchestrator session nobody dispatched has no
prompt to read it from, and that is the session type most of this milestone's work happens in.

**Rejected: a session→grain marker written by the claim** (`pm story building <id>` records the
session id, and the report joins on it). It is the only option that is exact for an
undispatched orchestrator under concurrency, and it still loses: it is new durable state whose
only job is to relate two things that both already exist, which is the "second name for the
same fact" smell, and it puts a write into the claim path that can fail after the status
already moved. Revisit only if tree resolution proves ambiguous in practice often enough to
matter — and the ambiguous case is not silent, so we will be able to count it.

**The invariant that outranks all three: an unresolvable grain is an OMITTED KEY.** Never a
zero, never a guess. A row filed against the wrong story is uncorrectable; a row filed against
none is visible in the bucket that already exists and can be fixed later.

## D3 — 2026-09-06 — Unattributed rows go to a root ledger, not to whichever milestone was building

`pm/roadmap/ledger.jsonl` — one file at the root of the tree — is where a row naming no grain
lands. `pm ledger report` already prints a `rows naming no grain` bucket; this gives that
bucket a home instead of scattering its contents into whichever milestone happened to be
`in_progress` at the time.

**The `check pm` D6 RULE survives intact** (not decision D6 below — the ids are two
namespaces). The ledger is still per-milestone for every attributed row, `retire`
still removes it with the directory, git is still the archive. Only unattributed rows outlive a
milestone, which is correct: they were never about it.

**Rejected: refusing the unattributed row.** It is the tidier model and it loses on the same
ground every time in this package — a refusal here means the data is gone, and the failure mode
we are fixing in this very milestone is telemetry that vanished without saying so. Loud absence
beats no record.

**Rejected: ledgers under features.** Considered because per-feature spend is the thing people
actually want to read. It loses because a row already names its feature in `grain:` — a
per-feature file adds a "which file" question without adding information, multiplies the walk
`ledger report` has to do, and answers with storage what `pm ledger show <feature-id>` already
answers with a query. This is the third instance in one session of the shape
`the-read-verbs-compose` names: **when the view is missing, the fix is a column or a query,
never a new place to put bytes.**

## D4 — 2026-09-06 — The design decisions that predate this log, carried forward

**These were settled in the 0.4.0 design conversation, before this file existed.** The date is
when they were written down, not when they were decided. Recorded here because they were living
only in a handoff message, which is not durable — and because a handoff should point at this log
rather than restate it.

**Kind-prefixed slugs (`ft-`, `st-`), never a counter.** A counter needs an allocator and a git
repo has none. Scan-and-take-max+1 gives two agents on two branches the same number, invisibly,
until merge; a counter file makes every branch that creates a grain conflict on one line. Both
fail hardest in the workflow this package is built for. **Uniqueness is a gate finding, not a
runtime lock.**

**`add` AND `set` both stay.** Not two spellings of one thing: `set` writes one field, `add` does
strictly more — bind AND sequence, one intent. `add` must remain exactly `set` plus a list insert.
*The day it grows behaviour neither primitive has, it is a second mechanism* — catch that in
review.

**`pm add <parent-id> <child-id>` — neither argument names a kind.** Ids carry their kind as a
prefix, so both are derivable and `[pm.contains]` validates the pair. `pm move` and `pm order`
both retire into it: the first because position stops being parentage, the second because it was
`add` against the root wearing a different name.

**`order` lists child IDs at every level.** The same list everywhere, so renaming a version never
touches the plan.

**Block-style `order:`, not inline.** Reordering is the main edit and a block diff shows what
moved. This is the one genuinely new primitive — a list-aware sibling to `set_field`.

**No YAML, and no JSONL for grains.** No YAML in the stdlib (hard rule 1), and a YAML round-trip
is load-then-dump, which strips the comments where the arguments live. JSONL stays the ledger's.

**The migration never auto-resolves a slug collision.** An auto-picked id is a name nobody chose,
in the one field that is stable for life and cited from commit messages. Report and refuse;
resolution goes through `pm rename`.

## D5 — 2026-09-06 — Telemetry is clearly available and warned when absent, never mandatory

Decided with Chris while filing the telemetry pre-work, and it governs both
`recording-is-on-or-the-gate-is-red` (this tree) and `telemetry-arrives-with-the-bump` (every
consumer).

A tree or a consumer that has not wired the couriers **is not broken** — it opted out, and this
package does not conscript. What it must never be is *silently* opted out, which is the state this
tree was in for the whole of 0.3.0: hooks installed and firing, every call refused, the refusal
printed to a stderr nobody reads, zero rows, zero complaints.

So both surfaces WARN and neither refuses. In Chris's words, near enough to the literal probe text:

> no ledger setup for milestone, no telemetry

**Rejected: making the wiring a hard requirement of adoption** — writing `.claude/settings.json`
on a consumer's behalf, or failing `adopt` when the hooks are absent. `install.py` already states
the reasoning for not writing that file (*"hand-maintained and there is no merge"*) and that
reasoning stands. Loud absence, not a forced install.

## D6 — 2026-09-06 — A handoff is a breadcrumb map, and the size cap is the gate that says so

**The observation.** The 0.4.0 handoff was written at 194 lines and restated the tree: the feature
list (`pm status`), the dependency graph (`grep depends_on`), the rung costs (`ledger report`), the
prior decisions (which were nowhere else, and are now D4), and summaries of commits whose messages
already carried the argument.

`[grain_shape]` rejected it at a 120-line cap. **Twice.** Both times the response was to shave
prose, which is treating a gate as an obstacle. Chris named the actual defect: *lean on git and the
tree, point agents at where to look rather than telling them; leave breadcrumbs everywhere as truth
rather than re-writing things over and over.*

Rewritten as a pointer document it came to **93 lines and lost nothing that was not derivable**.

**The rule.**

> **A document carries only what nothing else holds. Everything derivable is a command it names.**
> If the document and the tree disagree, the tree is right — it is maintained by gates; the
> document is maintained by whoever remembered.

What survived the rewrite is exactly the non-derivable residue, and it is a short list: the
absolute worktree path (in no file, only in `git worktree list`); environment hazards (another
agent in the main tree, `core.bare`, the write-confinement block); the reading ORDER, which is a
pointer and not a copy; and facts nobody had written down anywhere — that 0.3.0 records nothing,
that `check` runs ~36s cold against a 2.2s median.

**The cap was right, and that is the generalisable part.** `pm-execution.md` already says *"never
write what is already derivable"*, but only about tallies in feature and milestone files. The
`[grain_shape]` caps turn out to enforce the same rule everywhere, by proxy: **a document that
keeps hitting its cap is usually restating something, and the cap is the cheapest detector of it we
have.** Treat a repeated cap failure as a finding about the document, not a number to raise.

**Rejected: raising the `handoff` cap to 200.** It is not in this tree's `[grain_shape] caps`
override, so 120 is stock, and this tree's stated direction (0.2.0's story 09) is back *toward*
stock, not away.

**Rejected: a `pm handoff` verb that assembles the derivable parts.** Tempting — it would emit
status, graph, spend and log in one call. It loses to this package's own rule
(`the-read-verbs-compose`): read verbs emit lines and composition is the shell's job. **The handoff
naming the pipeline IS the composition**, and it costs nothing to maintain. A verb here would be
the fifth instance of the class in `/improvements.md` — reaching for a new capability when the
existing ones already compose.

**A handoff skill IS being built** — Chris's call, after the argument below was put and answered.
The objection was that a skill is a fourth name for what three constructs already carry. What
overrides it: **none of those three fire at the moment someone types "write me a handoff".** A
template guides only once you open it, a header only once the file exists, a cap only after you
have written too much. A skill description is the one surface that matches on the words a person
actually says. So it is built as a **router** — run `pm new milestone <id>`, the template is the
answer, here is what counts as derivable — and a skill that restates the template instead of
pointing at it has reproduced the very bug it exists to prevent. Review rejects it on that ground.

The argument, kept because it decides the skill's SHAPE. `src/agentic_sdlc/repo/pm/templates/handoff.md` is a handoff template with the right
three-section shape and *"Not a status dump"* written into it;
`model.SLOT_HEADER['handoff.md']` is **"Cold-start only. Never restate what `pm status`
computes."**, described in source as *"the one channel that reaches a dispatched subagent"*; and
`[grain_shape]`'s cap caught the violation twice.

**And building the fix turned up something sharper than a missed lookup: NO CODE PATH WROTE THAT
TEMPLATE.** `scaffold()` renders a template only for `file_slots` — for a milestone, `milestone.md`
alone. Optional slots get the header of an EXISTING file repaired and are never created.
`decisions.md` had a minting verb (`pm decide`); `handoff.md` had none, so the template was
reachable only through `pm templates --install`, which copies it out for a consumer to edit. It
shipped, `SLOT_TEMPLATE` registered it, `[grain_shape]` capped it — and nothing could produce it.

So the correction to the paragraph above: it was not bypassed guidance. **A skill would have been
a fourth name for a fact three constructs carried, except the constructs were not connected to a
caller.** What was missing was a minting path AND enforcement — `pm new handoff <id>`, plus a
`check pm` WARN on the absence and a `check grain-shape` finding on a missing header. The header
comparison already existed in `templates/__init__.py:79-83` and ran only on `pm new`; it now runs
on files on disk.

**The standing lesson: if you need a shared doc, scaffold it — don't author it.** This was the
fifth instance in one session of a capability that shipped and was not found at the moment of need,
and the first where the guidance was in the file's own first line.

## D7 — 2026-09-06 — The gate and test rows join the grainless family, and release_ledger_dir stops routing writes

**Created by the merge, not by the design.** D1 was written against a tree where
`_building_ledger_dir` routed every telemetry write. 0.3.0 then shipped
`model.release_ledger_dir` — "the milestone holding the current release, from `order` plus
`version_at`, with the in-progress lookup as fallback" — and moved the gate row onto it. That is
a strictly better answer to the question D1 deletes, and it is still an answer to it: a second
mechanism for *which ledger owns this row*, reading tree state rather than the row.

**The rule is unchanged and now covers three row kinds.** A row goes to the ledger of the
milestone that owns the row's GRAIN; a row naming no grain goes to `pm/roadmap/ledger.jsonl`.
`gate_row` carries no `grain` key by design and `test_row` carries none either, so both are
grainless by construction and both land at the root. There is now one routing function for
writes, and its input is the row.

**Three writers move, and the third was not on anybody's list.** `_gate_ledger_dir` (cli.py) and
the two readers that must follow the rows — `verify.main.gate_costs` and `checks.budget._rows` —
were known. `tests/conftest.py:278` was not: it files the slow-test rows through
`in_progress_milestones` directly, which made **three** functions answering one question in a
milestone whose thesis is that there should be one. It joins the rule with the rest.

**Neither reader loses anything.** Both take the NEWEST row per gate name — `verify` by file
order, `budget` by parsed `ts` — so a root ledger accumulating across releases does not blunt
either, and it gains: `retire` no longer destroys a milestone's gate history, so a budget has
numbers on the day a milestone opens instead of after its first run.

**`release_ledger_dir` survives, narrowed to reading.** It stops choosing where a row is WRITTEN
and keeps one job: which milestone `pm ledger report` is about when nobody named one. That is a
subject, not a route — the caller asked a question with a missing argument, and answering it from
the plan is the same act as `pm next`. A milestone report reads its own ledger AND the root's, so
the gate-cost section and the `rows naming no grain` bucket keep their contents.

**Rejected: keeping gate rows bound to the current release.** It is 0.3.0's shipped answer and
the argument for it is real — *"what did the gate cost during 0.3.0"* is a question people ask,
and a root file cannot answer it per milestone. It loses on the milestone's own thesis: a binding
is a FIELD, and `gate_row` has no field to bind by, so routing it by the plan is the path being
the schema one level down. It also keeps a refusal path — a tree with no `order` and no single
in-progress milestone refuses every gate row, which is the silent-loss mode D5 forbids. The
question it answers stays answerable: a gate row carries `ts`, and `ledger report <mid> --from
<tag>` reads the tree at that release.

**Rejected: giving `gate_row` a `grain` key.** It would put gate rows back under a milestone
without a second mechanism. It loses because a gate run is not work on a grain — `_record_gate`
already refuses `--grain` with *"a gate run is not a dispatch, and one row has one subject"* —
and inventing a binding so the routing rule has something to read is the tail wagging the dog.
