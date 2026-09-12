---
id: roadmap
kind: roadmap
order:
  - "ms-0.1.0"
  - "ms-0.2.0"
  - "ms-0.3.0"
  - "ms-0.4.0"
  - "ms-a-move-is-an-event"
  - "ms-the-rule-reaches-the-work"
  - "ms-nothing-is-hand-rolled"
  - "ms-a-consumer-can-take-the-bump"
  - "ms-the-tool-agrees-with-itself"
  - "ms-the-ledger-is-a-stamp"
  - "ms-a-session-starts-knowing-what-it-can-do"
  - "ms-the-host-stays-a-checkout"
---

# The release plan

The order releases ship in. It is a DECISION, not a sort: `order` lists the
MILESTONE IDS, in sequence, and each milestone's own `version:` says which
release it is — so a milestone that re-versions never touches this file.

`agentic-sdlc pm add roadmap <milestone-id>` schedules one, exactly as it
sequences a feature under a milestone or a story under a feature. Authoring and
scheduling stay separate acts: a milestone declares `version:` without joining
the plan.
