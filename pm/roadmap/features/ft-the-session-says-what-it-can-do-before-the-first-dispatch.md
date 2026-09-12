---
id: ft-the-session-says-what-it-can-do-before-the-first-dispatch
kind: feature
milestone: ms-a-session-starts-knowing-what-it-can-do
name: the session says what it can do before the first dispatch
status: reviewing
reviewed:
depends_on: []
consumed_by: []
changelog: New read verb `agentic-sdlc preflight` says what a session can do before the first dispatch (subagent resume, hook wiring, ledger attribution, the dispatch channel), and `install-hooks` ships `cc-session-preflight.sh`, a SessionStart hook that prints it into the session — land its new settings entry (#40).
---

# the session says what it can do before the first dispatch

Issue: #40. Scheduled for 0.11.0. It is a feature request, so it was kept out of 0.9.0's bug-and-debt scope.

The kit's flow assumes harness capabilities it never checks. It assumes a stopped subagent can be
resumed with `SendMessage`, that the courier will attribute a dispatch, and that the hooks are
wired. In one consumer milestone the orchestrator ran in a host that launches every session with
`--disallowedTools SendMessage`. Nobody knew until a call failed, and every stopped builder was
re-dispatched cold, at roughly 300k tokens each.

The ask is a read verb (`preflight`, or `doctor --session`), run from a SessionStart hook, that
reports into the session before anything is dispatched: can a subagent be resumed, which host this
is, will attribution work (stories in progress: 0, 1 or more), what `check hooks` knows, and that the
rendered `dispatch` preamble is the only channel to a subagent (#15). Optionally, `dispatch` carries
a one-line capability summary.

**Open questions for the 0.11.0 scout:**

- **Rule 2.** Walking the parent process chain and reading a process's argv is not "reading git,
  markdown and shell as text". Is that inside the rule, or the part left to the consumer?
- **Rule 8.** Naming one host's restrictions is knowledge about a consumer's tooling, not about this
  package. What is stated as a capability, and what is left out as trivia?
- **Overlap.** The attribution check shrinks to nothing once `ft-a-concurrent-dispatch-attributes-itself`
  (0.10.0) ships.

## Ship criterion

At SessionStart, before any dispatch, a session in a tree whose `install-hooks` corpus is current and
registered receives four rows from `preflight`: `subagent-resume` (denied/allowed/unknown — read from
`.claude/settings*.json` permissions, never a process's argv, rule 2), `hooks` (wired/not wired,
missing ones named, through `check hooks`' own reader), `attribution` (0/1/N stories in progress and
what the courier's fallback does with it), and `subagent-channel`. Each row is read as text, `unknown`
where a fact is not readable, exit 0; a usage or config error exits 2. Decided at dispatch
(2026-09-12): a launch flag such as `--disallowedTools` is not readable as text, so it is `unknown`,
never a guess.

## Proof budget

  cases: 3 new, plus 5 amended and the hook's 6-row `--self-test` corpus
  tier: unit (`tests/test_preflight.py`), integration (the `HEADERED` row, `check hooks` replay)
  lands in: tests/test_preflight.py, cc-session-preflight.sh --self-test
  what already covers this: `check hooks` covers the wiring half (preflight calls its reader);
    test_install's self-hosting cases cover the SessionStart registration.
