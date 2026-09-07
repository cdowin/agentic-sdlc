---
id: bg-the-milestone-scaffold-still-mints-the-version
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name: pm new milestone still mints the version as the id
status: closed
caused_by:
changelog: BREAKING: `pm new milestone` takes the version on `--version <ver>` and stamps it on `version:`; the first positional is the slug the id is minted from, so a version no longer becomes a milestone's id.
---

# the-milestone-scaffold-still-mints-the-version

The unlanded half of `bg-the-new-verbs-mint-a-compound-id` (GitHub #8), named in this milestone's
own Risks section: `ms-0.6.0` was minted by the scaffold and renamed by hand to get these files.

## Symptom

`pm new milestone <ver> <name...>` mints `ms-<ver>` and writes `version:` nowhere — the milestone
template did not carry the field at all. The only place a version could land was the id, so every
milestone this package has scaffolded is named after a release number, and re-versioning one is a
`pm rename` plus a whole-tree ref sweep: exactly the cost #8 deleted for the parent binding.

## Root cause

#8 landed for the PARENT and stopped there. `pm new feature|story|bug` each take a first argument
that is a FACT ABOUT the grain, write it to a field, and mint the id from the second argument
alone. A milestone has no parent, so its first argument fell through to the slug — and the fact a
milestone carries in that position is its VERSION. `ft-a-milestone-declares-its-version` shipped
the READER (`model.milestone_version`, R5, `pm next`, `pm roadmap`) and no writer, so the field
existed for everything except the verb that creates the grain.

## Fix

  * `src/agentic_sdlc/repo/pm/templates/milestone.md` — a `version:` slot beside `branch:`. Empty
    is BACKLOG, never a finding (R2).
  * `src/agentic_sdlc/repo/pm/cli.py` — `--version <ver>` on `pm new milestone`, stamped onto
    `version:` through `model.set_field` and echoed, the shape `--caused-by` already had; both now
    go through one `_stamp_field`. Refused whole, before any write, when the value is not one line
    — the bar `pm set` holds for a scalar.
  * The first positional is a SLUG, and `pm --help`, `pm init`'s next steps, `agentic-sdlc init`'s
    and `README.md`'s quickstart now say so with a name-shaped example.

**Breaking.** `pm new milestone 0.7.0 "Name"` still parses and still mints `ms-0.7.0`; it is no
longer how a version is recorded, and a caller who wants the version in the field has to move it
onto the flag.

Nothing here parses, compares or increments the string — `--version` copies it, so
`ft-a-milestone-declares-its-version`'s no-parser gate still holds.

## How this is proven

| claim | case |
|---|---|
| the id is prefix + slug, the version is a field | `tests/test_pm_scaffold.py::TheMintedIdIsThePrefixAndTheSlug::test_every_kind_mints_what_the_migration_would_have_minted` (amended) |
| optional, idempotent, refused whole | `tests/test_pm_scaffold.py::TheMintedIdIsThePrefixAndTheSlug::test_a_version_is_optional_idempotent_and_refused_whole` |
| `version:` is not a ref `pm rename` sweeps | `tests/test_pm_rename.py` `NOT_REFS` |
