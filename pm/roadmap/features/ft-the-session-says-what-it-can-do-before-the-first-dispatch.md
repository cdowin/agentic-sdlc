---
id: ft-the-session-says-what-it-can-do-before-the-first-dispatch
kind: feature
milestone: 
name: the session says what it can do before the first dispatch
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the session says what it can do before the first dispatch

Issue: #40. Pool: a feature request, kept out of 0.9.0's bug-and-debt scope.

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

**Open questions for whoever schedules it:**

- **Rule 2.** Walking the parent process chain and reading a process's argv is not "reading git,
  markdown and shell as text". Is that inside the rule, or the part left to the consumer?
- **Rule 8.** Naming one host's restrictions is knowledge about a consumer's tooling, not about this
  package. What is stated as a capability, and what is left out as trivia?
- **Overlap.** The attribution check shrinks to nothing once `ft-a-concurrent-dispatch-attributes-itself`
  (0.10.0) ships.

## Ship criterion

<!-- Written when it is scheduled. -->

## Proof budget

  cases:
  tier:
  lands in:
  what already covers this: `check hooks` covers the wiring half.
