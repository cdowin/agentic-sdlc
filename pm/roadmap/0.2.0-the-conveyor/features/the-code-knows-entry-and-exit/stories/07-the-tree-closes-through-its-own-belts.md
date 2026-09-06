---
id: 0.2.0/the-code-knows-entry-and-exit/07-the-tree-closes-through-its-own-belts
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Every story, feature and the milestone close through the belts they built
status: building
owner:
depends_on: []
---

# Every story, feature and the milestone close through the belts they built

## Acceptance criteria

- Every story of 0.2.0 reaches `done` through `close story`, every feature through `close feature` with its record, and the milestone through `agentic-sdlc release 0.2.0` up to the push step; the push, tag and artifact proof run only on Chris's go.
- `pm ledger show` carries a status row written by a belt step for every grain.
- `HANDOFF.md` is deleted along with its rule-8 exemption, because the migration it recorded is over.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | n/a | the tree itself: `pm ledger show`, `pm status 0.2.0` | not a test |

## Out of scope

Doing any of it by hand.

## Close

done: bc06971 a7c5598 2fee466 693d409 — 39 stories through close story, 15 features through close feature, HANDOFF.md gone; the milestone through release
