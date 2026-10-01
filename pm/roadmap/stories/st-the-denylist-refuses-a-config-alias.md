---
id: st-the-denylist-refuses-a-config-alias
kind: story
feature: ft-the-denylist-sees-through-an-alias
milestone: "ms-the-open-issues-close"
name: The denylist refuses git -c alias.*
status: done
owner:
depends_on: []
changelog: The git denylist hook refuses git -c alias.*, which could run any denied command under another name.
---

# The denylist refuses git -c alias.*

https://github.com/cdowin/agentic-sdlc/issues/105 part 2.

## Acceptance criteria

1. `installables/cc-git-denylist.sh` refuses any git call carrying `-c alias.<x>=...` (and
   `--config-env=alias.*`), exit 2 with its usual refusal line.
2. The installed copy `tools/hooks/cc-git-denylist.sh` is re-installed byte-current.
3. Corpus rows in the hook payload tests cover the probe from the issue and a plain `-c user.name`
   that still passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1-3 | integration | test_hooks_payloads.py / test_guard_corpus.py rows | amend |
