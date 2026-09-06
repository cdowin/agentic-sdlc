---
id: 0.3.0/adopt-grades-what-the-project-owns/01-a-project-claims-the-files-it-owns
feature: 0.3.0/adopt-grades-what-the-project-owns
milestone: "0.3.0"
name: a project claims the files it owns and the rest are graded
status: building
owner:
depends_on: []
---

# a project claims the files it owns and the rest are graded

`installables-current` was all-or-nothing across 27 files, and the installables
INVITE local edits — each ships a `Project config` section, "yours to edit after
install". A project owning eleven of them sat at 6/7 forever, which is the same
as no belt at all.

## Acceptance criteria

1. `[adopt] ours` declares the installed files a project owns;
   `installables-current` grades the rest.
2. The claimed files are named and counted **in the belt's own output on every
   run**, pass or fail — so claiming a file is a statement, not a hiding place.
3. An unclaimed drifted file is still false, with its `install-* --diff` named.
4. A claim naming a file this version does not install is REPORTED, not refused.
5. A malformed list is exit 2, before the first check runs.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | integration | `test_installables_current_names_a_drifted_file_and_the_verb_that_shows_it` | AMENDED — the existing drift case gained the claim phase |
| 2 | integration | `test_a_claimed_file_is_named_on_every_run_and_hides_no_other_drift` | new; this is risk 2 of the milestone record, and the reason the line is unconditional |
| 4 | integration | `test_a_claim_naming_no_file_this_version_installs_is_reported_not_refused` | new — install plans change between versions |
| 5 | integration | `test_the_config_refusal_matrix_is_exit_2_and_runs_no_check` (3 new rows) | ROWS on the existing matrix; `ours` is a path list, so it reuses `core/config.relpath_tuple` and the grammar's own matrix is not re-spelled (SDLC §5) |

## Out of scope

Nothing here. The `STEP_DOC` sentence the builder correctly stopped at was
updated by the orchestrator and `install-sdlc --force` re-rendered, because that
string and `docs/sdlc-protocol.md` are held byte-current and had to move together.

## Close

done: 1285784 — a project declares what it owns, the belt grades the rest, and
the claim is printed every run so the list is visible rather than a hiding place.
