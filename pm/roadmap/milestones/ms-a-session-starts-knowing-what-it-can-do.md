---
id: "ms-a-session-starts-knowing-what-it-can-do"
kind: milestone
name: a session starts knowing what it can do
status: done
depends_on: ["ms-the-ledger-is-a-stamp"]
branch: milestone/0.11.0-a-session-starts-knowing-what-it-can-do
version: 0.11.0
changelog: none
order:
  - "ft-the-session-says-what-it-can-do-before-the-first-dispatch"
  - "ft-the-kit-ships-its-planning-skills"
  - "ft-use-the-sdlc-get-to-work"
  - "ft-the-kit-says-one-loop"
reviewed: docs/reviews/2026-09-12-0.11.0-milestone-review.md
---

# 0.11.0 — a session starts knowing what it can do

Two consumer requests from 2026-09-11. Both are about what an orchestrating session knows before its
first dispatch, and both were measured in one consumer milestone where most of the spend went to
work that never landed:

- **#40: what the harness allows.** Whether a stopped subagent can be resumed, whether a dispatch
  will be attributed, and whether the hooks are wired. In that consumer every stopped builder was
  re-dispatched cold because `SendMessage` was denied, and nobody knew until a call failed.
- **#42: how much to plan and when to stop.** "Plan only when needed" and "file and continue", as
  kit-owned rules, not something each consumer rewrites for itself.

Minted as a scheduling decision only. **Features stay in the shape they were filed in, and
decomposition happens after 0.10.0 ships**, by the same flow: a scout against the code at that
point, then stories.

## Ship criterion

A session in a consumer with the kit installed is told, before anything is dispatched, what it can
and cannot do, and what each gap changes about how to dispatch. It never has to find out from a
failed call. The two planning rules ship where they reach the role that has to obey them. Each
feature's own criterion is written when it is decomposed.

## Risks

- **Rules 2 and 8 bound #40.** Reading a process's argv and naming one host's restrictions are both
  outside "pure text about this package". The scout decides what is a stated capability and what is
  left to the consumer.
- **#15 bounds #42.** A skill body never reaches a dispatched agent. A rule that has to bind a
  builder belongs in the role brief or the `dispatch` preamble, and a skill is the wrong carrier for
  it.
- **0.10.0 moves the ground.** `ft-the-flow-is-boring-by-construction` rewrites the dispatch loop,
  and `ft-a-concurrent-dispatch-attributes-itself` makes #40's attribution check unnecessary. Re-read
  both features against what 0.10.0 actually shipped before decomposing.
- **Candidate to pull in at decomposition:** pool `ft-a-phase-declares-what-it-hands-an-agent` (#15's
  remainder) is the same theme, but it depends on the unscheduled `ft-an-agent-is-a-registered-kind`.
