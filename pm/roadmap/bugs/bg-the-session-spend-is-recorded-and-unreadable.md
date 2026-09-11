---
id: bg-the-session-spend-is-recorded-and-unreadable
kind: bug
milestone: 
name: pm ledger report omits session rows, and a session row is a cumulative snapshot nothing labels
status: open
caused_by:
changelog: none
---

# the session spend is recorded and unreadable

Found answering "where are we with telemetry" off the ledger rather than by
hand — which is the one question this surface exists for.

## Symptom

Two defects in one family, and the second is why the first matters.

**1. `pm ledger report` does not surface `session` rows at all.** The tree holds
14 of them for one session carrying 185.2M tokens, 301 tool calls and 1h 46m of
wall clock. The report's `rows naming no grain` block reconciles EXACTLY to the
three `dispatch` rows — 263 tool calls, 3,543s, to the unit — so the session
rows are written by `cc-ledger-session.sh`, committed, and read by nothing.

**The orchestration is the majority of the spend.** 185.2M against the
dispatches' 51.5M: the read verb omits 78% of the milestone's tokens.

**2. A `session` row is a CUMULATIVE SNAPSHOT, and nothing says so.** All 14
carry one `session_id` and the numbers climb monotonically:

    21:49   1,113s   109 tools    33.3M
    22:39   4,123s   173 tools    71.9M
    23:17   6,375s   301 tools   185.2M

So the rows are a time series of one session, not a log of many. **Anything that
sums them reports 14 sessions and ~1.1 billion tokens.** Nothing in the row says
which reading is right, and `dispatch` rows — which ARE one-per-event and DO
sum — sit in the same file under the same `kind:` grammar.

## Root cause

The courier fires on `Stop`, and `Stop` fires on every turn, not once per
session. Each firing re-reads the whole transcript and files the total so far.
That is the only thing a hook at that event CAN do — it cannot know whether a
later turn is coming — so the row is correct and its INTERPRETATION is what is
missing.

Rule 11 from the read side: `pm ledger report` grew a `dispatch` column family
when dispatch rows arrived, and the session rows that arrived in the same
milestone never got one. A capability nobody can find is a capability you do
not have.

## Fix

  * **Report the session rows**, as their own block beside `rows naming no
    grain`. Newest-per-`session_id` is the total; the earlier rows of that id
    are its history.
  * **Say in the row which kind of number it is.** A `cumulative: true` key, or
    a `seq`, so a reader and a script do not have to know that `dispatch` sums
    and `session` does not. The grammar currently makes two opposite things look
    identical.

## Out of scope

Changing when the courier fires. A `Stop` hook that waited for a real end of
session is a hook that never files anything.

Attribution. That a session row names no grain is `GDK_LEDGER_GRAIN` not being
exported, which is a different defect and is the 0.6.0 handoff's own U4 note.
