---
id: bg-two-gate-runs-share-one-log-and-inflate-its-census
kind: bug
milestone: ms-the-ledger-is-a-stamp
name: two concurrent make check runs share .gate-reports/check.log and the verdict counts 10 of a 5-gate roster
status: open
caused_by:
changelog: none
---

# two gate runs share one log and inflate its census

0.7.0 review M4, reproduced on demand. A SHIPPED installable, and rule 4's first
sin: a verdict line claiming a census larger than the roster it ran.

## Symptom

Two concurrent `make check` runs in one checkout, verdict lines:

    [CHECK] 5 check(s) PASS
    [CHECK] 10 check(s) PASS      <- over a roster of FIVE

Seen three times this session at 9 and 10, each time with two agents gating at
once. `src/agentic_sdlc/repo/installables/Makefile.devkit:49` gives every
composition ONE log path per gate name, so two runs append to the same
`.gate-reports/check.log` and the census is counted off the file.

It also took down `test_makefile_gates.py::test_a_gate_prints_exactly_one_verdict_line_naming_its_log@the-real-repo`,
which reads that log and is green in isolation.

## Why it is a finding rather than an artefact of how this session ran

**Hard rule 2 says these verbs are "safe anywhere, any time, in parallel."** The
composition layer is what makes that false, and the number it gets wrong is a
CENSUS — the one thing rule 4 says a gate must never overstate. An operator
reading `10 check(s) PASS` has been told more was verified than was.

`tools/dev/agent-worktree.sh` exists to give each agent its own checkout and
would avoid it; that is a mitigation, not the fix, and nothing in the gate says
the log is single-writer.

## Fix

A per-run log, or a per-run temp file the composition appends under a lock, and
the census read from the run rather than the file. The verdict must count what
THIS invocation ran.

## Not fixed in 0.7.0

It dates to 0.2.0, it is in a shipped installable every consumer runs, and the
fix changes a log path and a verdict line — rule 6 output-shape territory, so it
wants its own minor bump and its own probe rather than riding a structural
milestone's close. Carried at MINOR by the feature review, which is what the
severity rule permits.
