---
id: st-the-readme-a-consumer-copies-from-is-current
kind: story
feature: ft-the-shipped-words-match-the-shipped-tool
milestone: "ms-a-consumer-can-take-the-bump"
name: the README a consumer copies from is current, for every release
status: building
owner: agent
depends_on: []
changelog: The README Install and Wiring examples pin `vX.Y.Z` instead of `v0.4.0`, and the adoption steps say the notes for releases before 0.6.0 are `git show v0.5.0:CHANGELOG.md`.
---

# the README a consumer copies from is current, for every release

Issues: #34 #35.

- **#34.** At v0.7.0, `README.md:33`, `:39` and `:342` still pin `v0.4.0`. Pasting the Install block
  installs a tool three minor versions old, carrying the D3 / `fix_milestone:` model 0.6.0 retired.
  `Makefile.devkit`'s header already moved to `vX.Y.Z` for this reason.
- **#35.** `README.md:50` sends a bumping consumer to `agentic-sdlc changelog <milestone-id>`. For
  every release before 0.6.0 that prints `0 entry/ies … N unanswered` (5 milestones, 159 grains, none
  with `changelog:`). Those notes exist only as `git show v0.5.0:CHANGELOG.md` (and v0.4.0, v0.3.0,
  v0.2.0), and the README never mentions it. They carried actions a consumer had to take:
  `pm install-skills --force`, `install-hooks --force`, and re-reading `pm validate`'s UNVERIFIABLE count.

## Acceptance criteria

1. No README example pins a concrete version; each says `vX.Y.Z` (or is held to the current version
   by `version-sync`, if one pattern can hold all three sites).
2. The adoption procedure says where the notes for a release before 0.6.0 live, with the exact command.
3. A consumer bumping from 0.4.0 can reach the 0.5.0 notes from the README alone.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | — | `git grep -n '@v0\.' README.md` returns nothing, quoted in the close | n/a |
| 2, 3 | — | `make check` (`check doc` resolves the command the README names) | yes |

## Semver

Patch.

## Out of scope

Backfilling `changelog:` onto 159 pre-0.6.0 grains. The five milestone-level `pm set` writes are the
cheaper alternative if the README line proves insufficient, and that is a later call.
