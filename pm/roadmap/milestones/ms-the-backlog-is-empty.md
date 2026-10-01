---
id: "ms-the-backlog-is-empty"
kind: milestone
name: The backlog is empty
status: building
depends_on: []
branch: milestone/2.4.0-the-backlog-is-empty
mode:
version: 2.4.0
changelog: The backlog is empty: a release is no longer tied to a milestone (the semver gate asks only whether the version increases, R5 warns), a builder may fan out under its GDK-STAMP, and 39 carried bugs are fixed.
order:
  - "bg-ruff-waives-44-findings"
  - "bg-denylist-misses-an-exported-config-env"
  - "ft-the-release-gate-asks-only-release-questions"
  - "ft-a-nested-dispatch-carries-the-stamp"
  - "ft-the-pool-is-empty"
  - "bg-semver-gate-passes-unparsable-main"
  - "bg-semver-gate-non-numeric-passes-after-decided"
  - "bg-denylist-export-trailing-n-bypass"
  - "bg-collision-refusal-undecodable-note-dropped"
  - "bg-install-collision-note-never-used"
  - "bg-reconcile-comment-eats-fenced-text"
  - "bg-required-body-inline-code-comment"
  - "bg-install-ci-python-leg-toolchain-note"
  - "bg-milestone-skip-not-in-log"
  - "bg-list-writer-hoists-comments"
  - "bg-without-status-drops-duplicates"
  - "bg-shellcheck-pin-leading-v"
  - "bg-ci-shellcheck-arch-hardcoded"
  - "bg-pin-flags-dict-one-entry"
  - "bg-required-fill-before-render"
  - "bg-r5-names-first-unplanned-only"
  - "bg-matrix-legs-oversubscribe"
  - "bg-grain-doc-predicate-too-wide"
  - "bg-tree-state-relative-root"
  - "bg-builder-check-line-close-nudge"
  - "bg-live-dependents-skip-caused-by"
  - "bg-unverifiable-masks-wrong-kind"
  - "bg-release-index-token-in-config"
  - "bg-reused-warn-stale-age"
  - "bg-courier-test-ledger-not-reset"
  - "bg-ledger-append-uncounted"
  - "bg-index-url-spelled-five-times"
  - "bg-devkit-advises-uv-init-bare"
  - "bg-wheel-test-needs-network"
  - "bg-a-belt-merges-stderr-into-stdout"
  - "bg-a-ledger-reading-test-is-racy-under-xdist"
  - "bg-a-pasted-fork-answer-records-nothing"
  - "bg-verdict-names-three-unrelated-things"
  - "bg-a-bare-decision-citation-is-still-ungraded"
  - "bg-a-bare-filename-is-not-checked-as-a-path"
  - "bg-install-skills-has-no-withdrawal-report"
  - "bg-the-seed-census-drops-a-kwargs-call"
  - "bg-two-names-for-one-shared-doc-location"
  - "bg-the-seed-census-cannot-read-a-per-kind-table"
  - "bg-install-agents-diff-calls-a-section-difference-header-only"
  - "bg-the-protects-census-is-scoped-by-mechanism-not-property"
---

# ms-the-backlog-is-empty — The backlog is empty

Finish the cleaning after 2.3.0. Chris decided the three open issues on 2026-10-01:
https://github.com/cdowin/agentic-sdlc/issues/116 the release gate is not tied to a milestone; https://github.com/cdowin/agentic-sdlc/issues/108 closes as superseded by the 2.0.0
cuts, with only live findings filed; https://github.com/cdowin/agentic-sdlc/issues/117 a nested dispatch's spend rolls up into its parent's
grain. The two pool bugs close too, so the tree and the issue list end empty.

## Ship criterion

- `semver-gate.yml` passes any PR whose version increases over main's, and reads no PM tree.
- R5 prints a WARN line, never a FAIL.
- The brief lets a builder start subagents and tells it to pass its GDK-STAMP line first.
- No ruff waiver is left in `pyproject.toml`.
- The denylist refuses an exported `GIT_CONFIG_*`.
- #108's live findings are pool bugs, and #108 is closed.

## Risks

- Minor bump (rule 7): the shipped CI workflow loosens, and R5's line changes from FAIL to WARN.
  A consumer that relied on the milestone-bound gate gets a looser gate after `install-ci --force`.
