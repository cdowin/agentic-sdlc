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

**D6 survives intact.** The ledger is still per-milestone for every attributed row, `retire`
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
