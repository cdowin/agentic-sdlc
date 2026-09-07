---
id: st-the-couriers-carry-the-grain
feature: ft-every-row-names-its-grain
milestone: "ms-0.4.0"
name: The couriers carry the grain they were dispatched against
status: done
owner: claude
depends_on: []
kind: story
---

# The couriers carry the grain they were dispatched against

<!-- What is observable when this ships. A story is an observation, not a task. -->

A dispatch that was told what it is working on files a row that says so. `pm ledger record
--from-transcript … --grain <id>` accepts the flag, and both couriers pass it when the environment
carries one, so a `dispatch` or `session` row lands with `grain:` filled and appears on that
grain's line in `pm ledger report` instead of in `rows naming no grain`.

**The information already exists** — an agent is told its grain in the prompt that starts it. This
story copies a known fact; it does not derive one. That is why the dispatch is the primary source
in D2 rather than the fallback.

## The mechanism the couriers already have

Both hooks ferry values through `make` without spelling them into `ARGS`, because `ARGS` crosses
make and then a recipe shell that may not be bash:

```sh
env_arg() {
	export "$2=$3"
	ARGS="$ARGS $1 \"\$\$$2\""
}
env_arg --session-id GDK_LEDGER_SESSION_ID "$SESSION_ID"
```

**`--grain` is a fourth of exactly the same.** `GDK_LEDGER_GRAIN`, `env_arg`, done. Do not invent a
second transport, and do not spell the value into `ARGS` directly — a grain id contains `/` and a
consumer's vehicle may be `dash` under `LC_ALL=C`, which is the case `cc-ledger-session.sh`'s
self-test already covers.

**Where the value comes from is the open half.** A `SubagentStop` payload does not carry a grain.
Candidates, in the order I would try them: an env var the dispatcher sets before spawning; a value
the agent itself recorded earlier in the session. **An absent grain is an OMITTED FLAG, never an
empty one** — both hooks already implement exactly this discipline for `--session-id`, and their
self-tests already assert it. Copy that; do not restate it.

## Files this story may touch

- `tools/hooks/cc-ledger-session.sh`, `tools/hooks/cc-ledger-subagent.sh` — the `env_arg` call and
  its self-test cases. **Each hook's `--self-test` must gain a case**: the grain travels, and an
  absent grain passes no flag. The corpus is the point of these files.
- `src/agentic_sdlc/repo/pm/cli.py` — `cmd_ledger_record`'s `--from-transcript` form accepts
  `--grain`, with the same validation the hand-entry form already applies at 1567.
- `src/agentic_sdlc/repo/install.py` — if the printed settings block or the hook docs name the
  flags a courier passes, they change here too.
- `tests/test_hooks_payloads.py`, `tests/test_pm_ledger_record.py`.

## Files it must stay out of

`src/agentic_sdlc/repo/pm/ledger.py` — `grain` is already in `ROW_KEYS` and `usage_row` already
accepts it; **if this story needs to edit `ledger.py`, something has been misunderstood.**
`report.py`, `.gitattributes`, and everything under story 02 of this feature.

**`cli.py` is shared with `one-rule-routes-a-row/01`**, which edits the same function's routing.
SERIAL: that story lands first.

## Acceptance criteria

1. `pm ledger record --from-transcript <t> --event Stop --grain <valid-id>` writes a row whose
   `grain` key is that id, in the position `ROW_KEYS` declares. Proven in
   `tests/test_pm_ledger_record.py`.
2. The same call with `--grain` naming an id no grain carries is **refused, exit 1, no write** —
   the same bar the hand-entry form applies. A bad grain must not degrade to an omitted key; that
   is how a typo becomes silent data loss.
3. Both hooks pass `--grain` when `GDK_LEDGER_GRAIN` (or whatever the source turns out to be) is
   set, and **pass no flag at all when it is unset**. Proven by a new case in each hook's own
   `--self-test`, asserting the `ARG[...]` corpus the existing cases assert against — including
   the negative, which is how the `--session-id` case is already written.
4. A grain id containing `/` survives the vehicle intact, including under the `dash` +`LC_ALL=C`
   case both self-tests already run. Every real grain id contains `/`, so this is the common case,
   not an edge.
5. `pm ledger report` shows the row on the grain's line rather than in `rows naming no grain`.
   Proven in `tests/test_pm_ledger_report_sections.py`.
6. Fail-open is unchanged: a hook whose grain lookup fails still exits 0 and still files its row
   without the key. **Nothing in this story may make a courier able to block a stop.**

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_pm_ledger_record.py::…a_transcript_row_carries_the_grain_it_was_given` — value, `ROW_KEYS` position, and the transcript's own numbers untouched | new |
| 2 | unit | `RECORD_REFUSALS` gains the unresolvable id ON THE TRANSCRIPT FORM; the `are exclusive` row leaves | amend |
| 3 | shell | each courier's own `--self-test`: the grain travels, and an unset one passes NO flag. Both proven able to fail — delete the `env_arg` call, and pass the flag unconditionally | amend the corpus, which is what these files are |
| 4 | shell | the same self-tests, whose `dash` + `LC_ALL=C` case already runs; the id used holds a `/` | existing case, new value |
| 5 | unit | `test_pm_ledger_report_sections.py::…a_row_that_names_its_grain_is_on_that_grains_line`, over an EMPTY snapshot so `grain:` is the only attributor | new |
| 6 | integration | `test_hooks_payloads.py` — the whole fail-open matrix unchanged and green, plus `…the_dispatchers_grain_travels_the_whole_vehicle_and_beats_the_lookup` | existing, unamended; that IS the claim |

## Out of scope

Resolving a grain the dispatch did not supply — story 02. Where the row is stored —
`one-rule-routes-a-row`. Any new row kind or key: `grain` already exists in `ROW_KEYS`.

## Close

done: 0af3a2e a201bb5 — `GDK_LEDGER_GRAIN` -> `env_arg --grain` in both couriers; the verb takes
`--grain` on the transcript form; the report reads it.
finding: **AC5 could not be met inside the stated file boundary.** `report.named_grains` read the
`tree` snapshot ALONE while `ledger.row_names` read `grain` and `tree` — a fifth instance of this
milestone's thesis, in the reader. Without the `report.py` edit the couriers would have filled the
key and the spend table would still have printed 0 per story. Crossed deliberately, and the two
functions are still separate: they answer different questions (`does this row name any of these` vs
`which grains under this milestone`) with different signatures. Worth one look at feature review.
deviation: AC2 says exit 1 for an unresolvable `--grain`; it is **exit 2**, which is what the
hand form already does and what rule 9 requires — an id that names nothing is a fact about the
INPUT. The bar the AC asked for (refused, no write, never degraded to an omitted key) holds.
finding: `self_test_fire` now builds the child environment (`env` / `env -u`). **Corrected at
review (W2): inheriting it made those cases a spurious FAIL, not a false pass.** The negative
asserts `--grain` is ABSENT from the argv, so a leaked variable turns the case RED — demonstrated.
The change is right and load-bearing; the reason first recorded here graded a noisy failure as rule
4's cardinal sin, and that is the one word this repo cannot spend loosely.
review W1: the same hazard was unfixed in the pytest twin — `test_hooks_payloads.CLEAN_ENV` passed
the operator's environment through, so the stock dispatch case failed for anyone with the variable
exported. It now strips it beside `DEVKIT_AGENT_SCOPE`.
review W3: AC4's `dash` + `LC_ALL=C` case did not carry a grain at all, so the value this story
ADDED was proven only under bash. It carries one now — and the comment says it is a REACHABILITY
proof rather than a quoting one, because the id grammar forbids the spaces that case exists to
catch.
review M4: **nothing in this package exported `GDK_LEDGER_GRAIN`**, which is rule 11's literal case
— a courier wired to write a value with no producer and no surface naming one. `pm-execution.md`
and `install-hooks`' next step now say who exports it and when. UNVERIFIED, and stated as such:
whether a `SubagentStop` hook's environment can carry a PER-DISPATCH value under Claude Code, or
only one per session. If it is the latter, D2's primary clause wants re-deciding rather than
documenting.
