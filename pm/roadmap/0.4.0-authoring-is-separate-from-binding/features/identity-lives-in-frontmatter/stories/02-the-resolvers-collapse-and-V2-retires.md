---
id: 0.4.0/identity-lives-in-frontmatter/02-the-resolvers-collapse-and-V2-retires
feature: 0.4.0/identity-lives-in-frontmatter
milestone: "0.4.0"
name: One grain_file, one children, one pool_walk, and V2 retires by name
status: planning
owner:
depends_on: ["0.4.0/identity-lives-in-frontmatter/01-a-grain-reads-its-id-and-kind-from-its-own-frontmatter"]
---

# One grain_file, one children, one pool_walk, and V2 retires by name
Six resolvers become `grain_file(cfg, kind, gid)`, five child listings become
`children(cfg, kind, parent_id)`, three pool walks become `pool_walk(cfg, kind)`, and four
directory-shape validators leave with the directories they validated. **Roughly twenty functions
that are one function with a kind baked in.**

The feature file names all twenty. The count going down is not the point: the twenty are the hard
opinions — `story_file` knows one three-segment shape, and a fifth kind means writing four more
functions. The three that replace them take `kind` as an argument.

**And the sharpest one is a security note.** `model.py` today: *"Ids reach `glob()` as patterns, so
an id must be a literal."* An id is interpolated into a glob and joined onto a directory, which is
why `segment_is_literal` must reject `.`, `..`, `/`, `\` and every glob character. Match-by-field
never builds a path from user input, so the guard has nothing left to guard.

## Acceptance criteria

1. `grain_file`, `children` and `pool_walk` exist, each taking `kind`, and every caller of the
   twenty named in the feature file goes through them. The twenty are gone from `src/`, proven by
   name the way `_building_ledger_dir` was.
2. **No user-facing verb is removed by this story.** These are internal resolvers; the verb surface
   gets more general, not smaller.
3. `AmbiguousStory` — *"two files claim one story id"* — is gone with the failure mode. Uniqueness
   is story 01's gate finding, so the runtime case cannot occur.
4. **No user input is joined onto a path or reaches `glob()` as a pattern** on any resolution path.
   Proven by a boundary case over `src/`, in the module that already polices this class.
5. `segment_is_literal` survives only where a path is still BUILT from input (a `pm new` slug), or
   it retires too. Whichever it is, say which in the close — a guard left behind with nothing to
   guard is the dead code rule 11 asks about.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | unit | a name gate over `src/`, beside `OneRuleRoutesALedgerRow` in `test_boundaries.py` | amend that class's neighbour |
| 2 | unit | `test_cli_surface.py`'s verb roster is unchanged | existing, unamended — that IS the claim |
| 4 | unit | `test_boundaries.py` already scans `src/` for path arithmetic classes | amend |
| 5 | unit | the grammar's matrix moves or is deleted with it | amend |

## Out of scope

Pools, bindings, order, the migration. This story only collapses resolution over the tree that
exists.
