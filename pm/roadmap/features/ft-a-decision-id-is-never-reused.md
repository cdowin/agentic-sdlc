---
id: ft-a-decision-id-is-never-reused
kind: feature
milestone: "ms-the-open-issues-close"
name: pm decide never reuses a decision id
status: done
reviewed:
depends_on: []
consumed_by: []
changelog: pm decide numbers past every D-id in the log or the ledger, so a condensed log never gets D1 again.
order:
  - "st-pm-decide-counts-condensed-decisions"
---

# pm decide never reuses a decision id

https://github.com/cdowin/agentic-sdlc/issues/110. After a log is condensed to pointer lines, `pm decide` writes D1 again.
