---
id: "ms-the-loop-proves-itself"
kind: milestone
name: The loop proves itself
status: building
depends_on: []
branch: milestone/2.1.0-the-loop-proves-itself
mode:
version: 2.1.0
changelog:
order:
  - "ft-adopt-names-what-is-absent"
  - "ft-init-ends-on-the-loop"
  - "ft-a-rerun-names-its-cause"
  - "ft-the-loop-is-one-test"
  - "ft-python-has-a-lint-gate"
  - "ft-tools-names-what-ships"
  - "bg-the-sixth-installer-cannot-describe-itself"
  - "bg-a-readme-test-checks-nothing"
  - "bg-adopt-unarmed-reads-one-config"
  - "bg-adopt-absent-every-installer"
  - "bg-init-diff-omits-inputs-ignore"
  - "bg-verify-inputs-lost-update"
  - "bg-verify-miss-wiring-untested"
  - "bg-verify-silent-miss"
---

# ms-the-loop-proves-itself — The loop proves itself

Source: a DeepWiki review of this repo on 2026-10-01, graded against the code at 2.0.0. Of 14
proposals, 7 are taken here.

- The review and its plan:
  https://deepwiki.com/search/thinking-about-the-goal-of-thi_1585e35b-fbd7-4455-9d41-754bf4a98112?mode=deep
- The generated wiki it read: https://deepwiki.com/cdowin/agentic-sdlc (overview:
  https://deepwiki.com/cdowin/agentic-sdlc/1-overview)

DeepWiki indexed commit `33a78bd`; each proposal was checked against the code, not taken on its
word. The rejected 7 are decisions in this milestone's decisions file.
The theme: a consumer sees what its setup lacks, sees the loop it runs, and a re-run says why.
One test proves the whole loop, and the numbers the tool prints about this repo are recomputed.

## Ship criterion

- `adopt <version>` names every absent installable, unarmed hooks, and a `[dispatch]` contract
  that is missing or outside `[doc]` scope. Nothing it checks is skipped silently.
- `init` ends by printing the loop with the tree's declared states.
- A `verify` cache miss prints one line per input that changed.
- One integration test runs init → new → dispatch → spot → integrate → release in a temp tree.
- `make unit` holds a ruff gate at a pinned version; `tools/README.md` names what ships.

## Risks

- Minor bump: new output lines on `adopt`, `init` and `verify`. Consumers grep line shapes
  (rule 6). Each new line takes a new shape; no existing line changes.
- The `verify` receipt row gains per-input digests. Old rows must still read (a miss, never a
  crash).
- The end-to-end test spawns git and make. It must fit the integration tier's budget.
