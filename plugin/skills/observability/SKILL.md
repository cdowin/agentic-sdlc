---
name: observability
description: Use when reviewing a state-changing action, async boundary, background job or diagnostic output. Checks whether a person can trace what was requested, what happened, and why, without harming privacy or real-time work.
---

# Observability: follow an action to its result

Review the evidence a developer can collect from a real run. A replayable record can prove an applied change, but it may omit rejected requests and the path to the result. Pure calculations with no boundary or side effect do not need a trace.

## Lens

- Prefix: OBS
- Owner: tech lead
- Trigger: a change to a state-changing action, async boundary, background job or diagnostic output
- Packs: none

## Rules

| ID | Rule | Severity | Check | Evidence to inspect |
|---|---|---|---|---|
| OBS-1 | Link request to result | major | review | For a state change across a boundary, one identifier joins the request, acceptance or rejection, and applied result. A real-run trace shows the old and new state or a reason it did not change. |
| OBS-2 | Give each severity a job | major | review | Debug explains decisions when enabled. Info records meaningful transitions. Warn names a recoverable problem and its response. Error names a failed operation. Inspect one example at each level the change emits; routine events do not flood warnings or errors. |
| OBS-3 | Bound and protect diagnostics | major | review | A diagnostic buffer or export has a size limit and a clear on/off and lifetime. Inspect an exported example for secrets, personal data, full URLs, file paths and other unneeded input; use safe identifiers or hashes where possible. No trace is sent elsewhere without an explicit product requirement. |
| OBS-4 | Keep the audio or real-time path quiet | critical | review | A callback with a time budget does no console or file logging, formatting, or network work. It updates bounded counters or a preallocated signal. Inspect the hot path and a run that reads those measurements outside it. |

## In review

Score each rule pass, fail or n/a with a file and line, a trace, or a run result. For OBS-1, follow one successful action and one rejected action across the boundary. For OBS-2, mark unused levels n/a. For OBS-4, mark n/a when the change has no real-time path. Report a missing trace as a finding only when the changed action needs one to confirm its outcome; do not add logs to deterministic Core functions just to satisfy this lens.

## Checklist

- [ ] OBS-1 Request linked to result
- [ ] OBS-2 Severity has a clear meaning
- [ ] OBS-3 Diagnostics bounded and protected
- [ ] OBS-4 Real-time path stays quiet
