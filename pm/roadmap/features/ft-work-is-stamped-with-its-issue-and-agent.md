---
id: ft-work-is-stamped-with-its-issue-and-agent
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: work is stamped with its start, stop, issue and agent
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# work is stamped with its start, stop, issue and agent

Audit unit 5, plus the bound bug `bg-an-unknown-agent-type-is-recorded-as-a-dispatch`. The owner's
"simple telemetry that someone can stamp. start times, stop times, issue_ids being worked, token use".

What someone can stamp today (the audit's gap table):

    start / stop   only as a grain's status moves; a dispatch only from its transcript.
                   `pm ledger record` has no start/stop
    issue id       NO FIELD ANYWHERE. `pm set <id> issue N` saves a key nothing reads
    tokens         `pm ledger record --tokens-total`, but concurrent rows are unattributed
    agent / role   `--agent-type` is a free string: `wombat` is accepted, exit 0

**One verb, paired rows:** `pm ledger stamp start|stop <grain> [--issue <id>]... [--agent <type>]
[--tokens N]`. It writes to the grain's milestone ledger. An external issue id is a first-class,
repeatable field, and `show` and `report` read it back as a COLUMN (rule 11: a field people filter on
is a column, never a new verb). Agent types come from a roster, so an unknown one is refused at exit 2.
That is the bound bug. The roster is the smallest slice of `ft-an-agent-is-a-registered-kind` (pool);
it does not ship that whole feature.

A `stop` with no open `start` for that grain is refused by name. A second `start` over an open one is
refused, or supersedes it on the record. The builder decides which, and says why in the close. The
stamp records only what it was told, nothing more (rule 9).

## Ship criterion

A person runs `pm ledger stamp start <grain> --issue 42 --agent developer`, does the work, then runs
`pm ledger stamp stop <grain> --tokens 1200`. `pm ledger show <grain>` prints one unit with its start,
stop, duration, issue 42, agent and tokens as columns, and `pm ledger report <milestone> | grep 42`
finds it. `--agent wombat` exits 2 naming the roster.

## Proof budget

  cases: 4–6, plus the refusal matrix for the new flags (SDLC §5: reuse the id and version grammars)
  tier: unit
  lands in: tests/test_pm_ledger_record.py — the stamp is the record verb's sibling
  what already covers this: `record`'s cases cover free-form rows. Nothing pairs a start with a stop,
  and nothing refuses an agent type.
