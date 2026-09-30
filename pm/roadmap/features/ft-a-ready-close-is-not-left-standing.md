---
id: ft-a-ready-close-is-not-left-standing
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: a ready close is not left standing
status: done
reviewed: docs/reviews/2026-09-30-1.0.0-close-now.md
depends_on: []
consumed_by: []
changelog: A ready close is named where the operator looks: `check pm` and `make check` verdict lines end `; N close(s) ready to run — <command>` (a close whose rung last failed is held on its own line, never named ready), `close feature <id> --review-record <path>` stamps the record and closes in one command, the stock stop gate holds a session's stop while such a close stands open (`CLOSE_READY="block"`; a header already set to `inform` keeps it), and the auto-loaded rule says close each grain the moment it is ready, not in a batch.
---

# a ready close is not left standing

Chris, 2026-09-30, and not the first time: features are knocked down one by one as they are built
and validated. In 1.0.0 the orchestrator held seven features to the end and closed them in one
call. The kit taught that: the auto-loaded `pm-execution` rule says "Run the belts once per merge
batch … ONE `close feature <id> <id> …`", contradicting run-the-sdlc's "a lane closes the day it
merges". `check pm`'s CLOSE line exists but sits above the verdict line an operator reads; the
stop gate ships `CLOSE_READY="inform"`; and `reviewed:` is a separate `pm set` before a close can
even be seen as ready.

## Decided (do not re-plan)

- **The rule says close one by one.** In `src/agentic_sdlc/repo/pm/guidance/pm-execution.md`
  and `run-the-sdlc.md`: a feature closes the moment its review record lands (a lane with no
  reviewer: the moment it merges and its record is written); the many-id form is for grains that
  become ready TOGETHER, never a reason to wait. Remove "once per merge batch". Re-install
  (`pm install-skills --force`, `install-sdlc --force` if docs/sdlc-protocol.md carries it).
- **The verdict line carries it.** When `check pm` finds ready closes, the `[CHECK]` verdict
  line `make check` prints ends with `; N close(s) ready to run — <command>` (a close whose rung last
  recorded FAIL is held on its own CLOSE line, never named ready) (the ONE next
  command, ids named, clipped like other lists). Also on `check pm`'s own verdict line. It stays
  a count, never the exit code (rule 9: pm moves and reports; the belt is the operator's act).
  Rule 6: a changed verdict line shape is in the changelog.
- **One command closes on a landed record.** `close feature <id> --review-record <path>` stamps
  `reviewed:` and runs the belt in one act; the stamp is written only if the belt writes `done`
  (a refused close writes nothing, rule 3). `review-recorded` reads the given path.
- **The stop gate holds a ready close.** Stock `cc-stop-gate.sh` ships `CLOSE_READY="block"`:
  a session cannot stop while a close the belts would accept stands open; the message names the
  command. A project that wants the old behaviour sets `inform` in its header. Re-install here.
- Proof: a tree with one feature ready: `make check`'s last line names it; `close feature <id>
  --review-record <path>` closes it in one command; the stop gate exits 2 naming it; with it
  closed, all three are quiet.

## Ship criterion

- The four proofs above hold; the two guidance texts agree and say one by one.

## Proof budget

  cases: ~4 (verdict line, --review-record close, refused close writes no stamp, stop gate block)
  tier: unit where possible; the stop gate through its own --self-test corpus
  lands in: tests for checks/pm.py, conveyor/driver.py, the stop-gate corpus
  what already covers this: the CLOSE WARN line cases; nothing puts it on the verdict line.
