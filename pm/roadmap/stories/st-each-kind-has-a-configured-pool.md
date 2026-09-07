---
id: st-each-kind-has-a-configured-pool
feature: ft-the-pools-are-the-tables
milestone: "ms-0.4.0"
name: Each kind is read from its configured pool, relative to the repo root
status: planning
owner:
depends_on: ["st-the-resolvers-collapse-and-V2-retires"]
kind: story
---

# Each kind is read from its configured pool, relative to the repo root
Each kind is read from one directory the config names, relative to the repo root the tool already
discovers. `[pm] milestone_dir`, `feature_dir`, `story_dir`, `bug_dir` and `ledger_dir` each
default to `<roadmap_dir>/<kind>s`, so adopting costs zero edits — but the file SHOWS four peer
kinds, which one `roadmap_dir` never could.

## Acceptance criteria

1. The five keys exist, each defaulting to `<roadmap_dir>/<kind>s`, each read through
   `core/config.py` like every other path key. A tree declaring none behaves byte-identically to
   one declaring every stock value.
2. **An absolute path is exit 2, naming the reason**: a committed absolute root is wrong in every
   worktree, on every other machine and in CI. There is no `project_root_dir` key and asking for
   one says so. The path grammar is the shared one — a surface that reuses it proves that it
   reuses it with one case (SDLC § 5).
3. `[pm] story_ordinal_prefix` **retires by name**, through `RETIRED_KEYS`, with its replacement:
   in a flat pool `01-` appears a hundred times and orders nothing, so sequence moves to the
   parent's `order`.
4. The ledger has a configured home. Both of them: a milestone's, and the tree's own for rows
   naming no grain (D3).
5. The CHANGELOG is honest about what is LOST — `git log -- pm/roadmap/<milestone>/` stops
   answering "this milestone's history" and `ls` stops answering "what is in this milestone" — and
   names what answers each instead. A consumer should be told, not discover it.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `[pm] roadmap_dir` is already a configured path with cases | amend — the five extend it |
| 2 | unit | one case proving the shared path grammar is REUSED, not a second matrix | the grammar's matrix exists; inventing another is a finding |
| 3 | unit | `test_pm_gate.py`'s retired-key case | amend |
| 4 | unit | both ledger paths resolve from config | amend the story-02 root-ledger cases |

## Out of scope

The migration itself — `0.4.0/the-migration-is-whole-or-nothing`. Slug collisions surfaced by
flattening: the migration reports them, `pm rename` resolves them.
