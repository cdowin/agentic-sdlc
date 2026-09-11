Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ms-a-consumer-can-take-the-bump a consumer can take the bump — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-11 — this ships as 0.8.0, whole

Planned as 0.7.1. By hard rule 7, 12 of the 16 stories need a minor bump: new flags (`--only`, the
`pm retire` backfill), a new positional (`pm new bug <name...>`), a new `Makefile.devkit` target,
changed WARN and hint lines (rule 6), and `check doc` failing a tree it passed (#26). Only the words,
the semver-gate fix and the README are patch-shaped.

**Rejected: split into a patch-shaped 0.7.1 and the rest as 0.8.0.** Two branches, two releases and
two `adopt` runs for every consumer, to ship four text fixes a few days early. The consumers who filed
these hit the minor-shaped defects (`--force`, the vehicle, D11 going silent), so a text-only 0.7.1
would fix nothing they reported as blocking. Re-versioning was one `pm set` plus a branch rename; the
id and slug did not change.

Chris, 2026-09-11: go with the recommendation.

Also scoped in on the same call: three open pool bugs that sit right next to issues here, each bound
to this milestone and ordered after the feature it neighbours:
`bg-the-release-belt-and-the-render-verb-disagree-about-changelog` (#33, the same check),
`bg-the-gate-help-names-one-of-its-four-rule-families` (#25, the same help shape on `check pm`), and
`bg-the-bump-belt-does-not-run-the-gate-a-consumer-armed` (the bump belt this milestone is about).
