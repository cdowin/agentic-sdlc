---
id: bg-a-scaffold-name-injects-frontmatter
kind: bug
milestone: "ms-a-consumer-can-take-the-bump"
name: a newline or a flag in a scaffold name is written into the new grain
status: closed
caused_by:
changelog: A `pm new` name carrying a newline, or starting with `-`, is refused at exit 2 for every grain kind — a newline used to inject a second frontmatter line (a grain could be born reading `done`), and `--name X` was written as the name.
---

# a newline or a flag in a scaffold name is written into the new grain

Found by the `ft-the-pm-surface-has-no-dead-ends` review (Q16, and M2's neighbour),
`docs/reviews/2026-09-11-0.8.0-the-pm-surface-has-no-dead-ends.md`. It predates 0.8.0.

## Symptom

    pm new feature 0.1 x $'Title\nstatus: done'   → the new grain carries a second `status: done`
                                                    line and reads `done` a second after it exists
    pm new feature 0.1 x --name 'Title'           → `name: --name Title`, exit 0

`pm new bug` already refuses a multi-line name (`pm/cli.py` `NAME_ARG` guard). `new feature`,
`new story` and `new milestone` do not, and none of the four refuses a flag-shaped name.

**This is rule 4's second sin:** a write that looks legitimate and is not. A grain can be born
reading `done`.

## Fix

One guard shared by all four scaffolds: a name with a CR or LF is refused at exit 2, and so is a name
whose first word starts with `-`, naming the positional form. Nothing is written in either case.
The same bar `pm set` and `cmd_decide` already hold.
