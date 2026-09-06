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

## What this deletes, by name

The addressing layer exists BECAUSE the path is the schema, and it is roughly twenty functions
that are one function with a kind baked in. Naming them here so whoever builds this can see the
payoff rather than take it on faith.

**Path arithmetic — gone outright.** An id no longer names a location, so nothing joins it to one.

    id_is_literal          segment_is_literal     milestone_dir     milestone_file
    feature_dir            feature_file           story_file        story_slug_of
    milestone_dir_of       AmbiguousStory

Six resolvers become one `grain_file(cfg, kind, gid)` — walk the pool, read `id:`, match.
`milestone_dir_of` ("which milestone holds this document") becomes `field_of(path, 'milestone')`.
`AmbiguousStory` — *"two files claim one story id"* — cannot occur once slugs are unique, so a
whole failure mode leaves with it.

**And the sharpest one is a security note, not a tidiness note.** `model.py` today: *"Ids reach
glob() as patterns, so an id must be a literal, never a pattern."* **An id is currently
interpolated into a glob pattern and joined onto a directory**, which is why
`segment_is_literal` has to reject `.`, `..`, `/`, `\` and every glob character. Match-by-field
never builds a path from user input, so the guard has nothing left to guard and the attack
surface goes with it.

**Per-kind child listings — five become one.** Children are found by their binding field, not by
which directory they sit in:

    feature_files(mdir)    story_files(ffile)    bug_files(mdir)
    grain_docs(gdir)       slot_walk(gdir)                → children(cfg, kind, parent_id)

**Directory-shape validation — gone.** There are no grain directories left to be malformed:

    orphan_dirs    _has_milestone_file    _has_feature_file    _milestone_candidates

The real check survives in simpler form — `_is_grain_doc` already asks "does this file open
frontmatter", which is the flat-pool version of the same question.

**Pool walking — three become one.** `milestone_walk`, `milestone_dirs` and `known_milestones`
become `pool_walk(cfg, kind)`.

## This is MORE flexible, not less

The count going down is not the point and could be read backwards. **The twenty are the hard
opinions**: `milestone_dir` works for milestones and nothing else; `story_file` knows one
three-segment shape; adding a fifth kind means writing four more functions and a fifth `*_files`.
The three that replace them take `kind` as an argument and work for a kind nobody has invented
yet, with `[pm.contains]` declaring the shape instead of the code assuming it.

**No user-facing verb is removed by this feature.** These are internal resolvers. The verb surface
gets more general, not smaller — `pm set <id> <key> <value>` already works for any key; the
resolvers are what stop the same generality reaching any KIND.

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
