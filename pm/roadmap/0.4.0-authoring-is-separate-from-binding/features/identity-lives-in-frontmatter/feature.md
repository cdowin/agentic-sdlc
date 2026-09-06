---
id: 0.4.0/identity-lives-in-frontmatter
milestone: "0.4.0"
name: Identity and kind live in frontmatter, and the path stops being schema
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# Identity and kind live in frontmatter, and the path stops being schema

`model.py`: *"a grain's kind is read from which slot its document sits in."* So a grain's kind, its
id and its parent are all functions of where the file sits, and `id:`/`milestone:`/`feature:` in
frontmatter are copies. **V2 exists to keep the copies in agreement**, which is a rule whose job is
to police a duplication the design created.

Frontmatter becomes the only source:

```yaml
id:   ft-two-pin-toolkit-adoption
kind: feature
```

## The id is a kind-prefixed slug, not a number

Unique within its kind, stable for life, and **never allocated**.

A sequential id (`nul-ft-123`) needs an allocator and a git repo has none. Scan-and-take-max+1
gives two agents on two branches the same number, invisibly, until merge. A counter file makes
every branch that creates a grain conflict with every other branch on one line. Both fail hardest
in exactly the workflow this package is built for — parallel agents on branches.

So uniqueness is a GATE FINDING, not a runtime lock: the tool does what it is asked and reports
contradictions, which is its stated split. Two agents choosing the same slug produce a merge
conflict a human can see, rather than a duplicate id nobody can.

The `ft-`/`st-`/`ms-`/`bg-` prefix earns its place once the path means nothing: a bare id in a
commit message, a dispatch or a review says what kind of thing it is without its location. That is
the job the prefix does — the number never did it. `kind:` in frontmatter is what the TOOL reads;
the prefix is for the human reading the id alone.

**A prefix is not a namespace.** It does not make ids unique across repos, and a project prefix
(`nul-`) is constant within a repo so it earns nothing on disk. Cross-repo disambiguation is a
display concern — a config for output and export, never part of a filename.

## Ship criterion

`id:` and `kind:` are read from frontmatter and the path is not consulted for either. A grain whose
`kind:` is not one the project declares is refused by name. Slug uniqueness within a kind is a
`check pm` rule naming every file that shares a slug. V2 is retired BY NAME with the CHANGELOG
saying what replaced it — a consumer whose `[pm] checks` still lists it is told, never silently
ungated. Ids are stable under re-parenting: nothing in the tool derives an id from a location.

## Proof budget

  cases: 4-5
  tier: pyunit
  lands in: the model's grain-reading module, and `test_pm_gate.py` for the uniqueness rule
  what already covers this: V2 has cases for id-matches-path and id-does-not, which invert rather
    than extend — they become cases proving the path is NOT consulted. New: an unknown `kind:`,
    a duplicate slug within a kind, and the same slug in two different kinds passing.

## Out of scope

Where the files sit — that is `the-pools-are-the-tables`. This feature makes the location
uninterpreted; the next one moves it.
