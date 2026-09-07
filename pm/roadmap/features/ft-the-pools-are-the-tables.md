---
id: ft-the-pools-are-the-tables
milestone: ms-0.4.0
name: Each kind gets a pool, and the config says where it is
status: building
reviewed:
phase:
depends_on: ["ft-identity-lives-in-frontmatter"]
consumed_by: []
kind: feature
order:
  - "st-each-kind-has-a-configured-pool"
---

# Each kind gets a pool, and the config says where it is

Once the path is uninterpreted, nesting is ceremony. Each kind gets one directory — the tables of
the database, as directories — and the config names them:

```toml
[pm]
roadmap_dir   = "pm/roadmap"              # the root the rest default under
milestone_dir = "pm/roadmap/milestones"   # each shown at its DERIVED default
feature_dir   = "pm/roadmap/features"
story_dir     = "pm/roadmap/stories"
bug_dir       = "pm/roadmap/bugs"
ledger_dir    = "pm/roadmap/ledgers"
```

**Granular in the file, derived in the code.** Each key defaults to
`<roadmap_dir>/<kind>s`, so adopting costs zero edits and moving one table costs one line — but
the config still SHOWS that there are four kinds and they are peers, which one `roadmap_dir` never
could. The shape of the config is the shape of the model; that is the point of spelling all six
out rather than only the root.

**Relative to the repo root, which the tool already discovers** (`core.project.repo_root`). An
absolute root in a committed config is wrong in every worktree, on every other machine and in CI,
so there is no `project_root_dir` key and asking for one is exit 2 with that reason.

## Two things fall out, and both need a decision rather than a discovery

**The `NN-` ordinal prefix retires.** `[pm] story_ordinal_prefix` sequences stories *within a
feature*; in a flat pool `01-` appears a hundred times and orders nothing. Sequence moves to the
parent's `order` — see `the-order-is-one-mechanism`, which makes that the same list at every
level. The key is retired by name, and so is the `<!-- pm:execution -->` block it shared the job
with.

**`ledger.jsonl` needs an address.** It is milestone-scoped machine state, not a grain, and it
currently lives in the milestone's directory. `pm/roadmap/ledgers/<milestone>.jsonl` — a table of
its own, named by the same config mechanism.

## What is lost, honestly

`git log -- pm/roadmap/<milestone>/` stops answering "this milestone's history", and `ls` stops
answering "what is in this milestone". The first becomes a `pm` verb over the grains that name the
milestone; the second is `pm status <id>`, which already exists. Neither is free, and a consumer
should be told in the CHANGELOG rather than discovering it.

`pm retire` deletes N files across pools instead of one directory. That is the tool's work, not a
human's, and it is the same set either way.

## Ship criterion

Each kind is read from its configured pool, relative to the discovered repo root; no key takes an
absolute path. `story_ordinal_prefix` is retired by name and build order is the feature's execution
list. The ledger has a configured home. A migration verb moves an existing nested tree into pools
idempotently, reports every file it moved, and refuses rather than half-moving.

## Proof budget

  cases: 4
  tier: pyunit, plus one shell case for the migration over a fixture tree
  lands in: the walk/config modules; a new migration test beside `test_replay_migration.py`
  what already covers this: `[pm] roadmap_dir` is already a configured path with cases, so the
    four keys extend that. Genuinely new: the migration, and the absolute-path refusal.

## Out of scope

Slug collisions surfaced by flattening. The migration reports them; resolving them is the
consumer's, and renaming safely is `binding-is-a-field`'s ref-rewriting work.
