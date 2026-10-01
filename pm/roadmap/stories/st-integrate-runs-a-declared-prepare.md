---
id: st-integrate-runs-a-declared-prepare
kind: story
feature: ft-the-batch-starts-warm
milestone: "ms-integrate-takes-the-whole-batch"
name: integrate runs [integrate] prepare once, before the first merge
status: building
owner:
depends_on: []
changelog: integrate runs the [integrate] prepare make targets once in a new batch worktree, so a proof never starts cold.
---

# integrate runs [integrate] prepare once, before the first merge

## Acceptance criteria

1. `[integrate] prepare` is a list of make targets read through `core/config.py` beside
   `per_merge` and `proof` (`integrate::settings`). Absent means none. A wrong shape is exit 2 by name.
2. On a NEW batch worktree, each target runs once, streamed, after `_add_worktree` and before the
   first `_merge`. A resumed batch does not run it again.
3. A red prepare stops the batch, names the target, merges nothing and closes nothing.
4. The seed (`installables/project-devkit.toml`) carries the key commented, and
   `tests/test_config_seed.py` holds it.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | test_integrate.py settings case | amend |
| 2, 3 | integration | test_integrate.py: a prepare target that writes a marker file; a red one | new |
| 4 | unit | test_config_seed.py | existing |

## Out of scope

Copying cache dirs the way `agent-worktree.sh new` does. The consumer declares what warms it.
