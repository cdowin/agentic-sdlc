---
id: bg-the-new-verbs-mint-a-compound-id
kind: bug
milestone: "ms-a-move-is-an-event"
name: `pm new` bakes the binding into the identity
status: open
caught_in: "ms-a-move-is-an-event"
fix_milestone:
caused_by:
---

# `pm new` bakes the binding into the identity

**Not a naming-style complaint.** A version in a filename or in an id is nobody's business but the
author's — nothing reads a path as schema, and the engine stopped using either as a version. This is
about a functional coupling that 0.4.0 deleted and the create path put back.

    pm new feature ms-x the-slug   ->  id: ms-x/the-slug
    pm new bug     ms-x the-slug   ->  id: ms-x/bugs/the-slug

The id **contains the parent**. `milestone: ms-x` is right there in the frontmatter as the
authoritative binding, and the id restates it — so re-binding the grain to a different milestone is
no longer `pm set`, it is `pm rename` plus a whole-tree ref sweep. That is the exact cost 0.4.0
removed when it retired `pm move`, and the reason it gave: *"once a binding is a field, `pm move` is
`pm set` and deletes itself."*

It is also unstable in the one field that is supposed to be stable for life and is cited from commit
messages: a grain that re-parents changes identity, which is what `ft-identity-lives-in-frontmatter`
was built to stop.

## It already happened in the shipped tree

Four bugs authored during 0.4.0 — after the migration ran — carry a parent inside their id today:

    ms-0.4.0/bugs/a-belt-merges-stderr-into-stdout
    ms-0.4.0/bugs/a-proof-row-names-a-case-that-proves-half
    ms-0.4.0/bugs/the-seed-census-drops-a-kwargs-call
    ms-0.4.0/bugs/two-names-for-one-shared-doc-location

Each is bound twice — once in `milestone:`, once inside its own id — and the two can now disagree.

## The milestone verb has the argument backwards

`pm new milestone <ver>` takes a VERSION positionally, makes it the identity, and leaves `version:`
empty. The one argument that names a release becomes the one field that is not the release. R2 then
correctly reports the milestone as BACKLOG for declaring no version — while its id is the version.

## And the auto-loaded rule says the scaffold is right

`.claude/rules/pm-execution.md` — written by `install-skills`, shipped to every consumer, loaded into
every session — says:

> Creation too: `pm new milestone|feature|story|bug` scaffolds to the schema.

That is the sentence an operator trusts instead of checking, and it is why this survived a release:
the scaffold hands back a shape the tree does not use, and the only loaded rule on the subject
vouches for it. `ft-documented-behaviour-is-the-behaviour` (0.4.0) is the rule it breaks. The fix
below makes the sentence true; nothing here asks for a new gate.

## Fix

`pm new <kind> <slug>` mints the slug it was given and nothing else. The parent stops being
positional identity; binding is `pm add`, which already does bind-and-sequence in one act and is what
the 0.4.0 body said the verb family would collapse to:

    write   pm new <kind> <slug>       the parent argument is gone at every level

The four existing compound ids go through `pm rename`, once, as a visible commit.

## What this bug does NOT ask for

A gate on id shape. The tool does not get an opinion about what a project's ids look like (rule 9) —
prefixes, versions, and filenames are the project's own taste, and `check pm` grading them would be
the tool deciding rather than reading. The defect here is a coupling the ENGINE creates, not a
convention a human chose.
