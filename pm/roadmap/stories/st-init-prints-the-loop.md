---
id: st-init-prints-the-loop
kind: story
feature: ft-init-ends-on-the-loop
milestone: "ms-the-loop-proves-itself"
name: init's last lines are the loop, spelled with the declared states
status: done
owner:
depends_on: []
changelog: init ends by printing the loop with the tree's declared state names and adopt as the setup check.
---

# init's last lines are the loop, spelled with the declared states

## Acceptance criteria

1. The last block `init` prints names, in order: `pm new`, `dispatch --grain`, `[verify] spot`,
   `integrate`, `release`, each as the command a consumer types.
2. Each state in the block is read from the written `devkit.toml`, never a literal in the code.
3. The block names `agentic-sdlc adopt <version>` as the check of the whole setup.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | unit | test_init_verb.py next-steps case | amend |
| 2 | unit | test_init_verb.py: a seed with renamed states shows the renamed words | new |

Files: `src/agentic_sdlc/repo/init.py`.

## Out of scope

`init` running `adopt` itself. `init` writes; `adopt` reads.
