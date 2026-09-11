---
id: st-pm-new-bug-takes-a-name
kind: story
feature: ft-the-pm-surface-has-no-dead-ends
milestone: "ms-a-consumer-can-take-the-bump"
name: pm new bug takes a name, like every other scaffold
status: planning
owner:
depends_on: []
changelog:
---

# pm new bug takes a name, like every other scaffold

Issue: #24.

```
new milestone <slug> <name...> [--version <ver>]
new feature <milestone> <slug> <name...>
new story <feature-id> <slug> <name...>
new bug <milestone> <slug> [--caused-by <feature-id>]      ← no name
```

`pm new bug` writes `name:` empty, so every bug needs a second write before it has a title. The
obvious spelling, `--name '…'`, falls into `rest` and `len(rest) != 2` raises Usage
(`pm/cli.py:1949-1968`), so it exits 2 and writes nothing.

**Sizing trap, from verification:** consumer templates copied out by `pm templates` have no `{name}`
slot in `bug.md`. Rendering the name through the template would silently drop it for those consumers.
Stamp it with `_stamp_field` after the render, the way `--version` is stamped on a milestone.

## Acceptance criteria

1. `pm new bug <milestone> <slug> <name...>` writes `name:`, including under a consumer template
   with no `{name}` slot.
2. `pm new bug <milestone> <slug>` with no name either keeps working and prints a `next:` line naming
   the empty `name:`, or is refused the way `new feature` refuses it. The builder matches `new
   feature`'s behaviour exactly. Being consistent matters more than which choice.
3. The usage line matches the other scaffolds' shape.
4. Idempotent: re-running on an existing bug with the same name is a no-op.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | temp tree, stock template and a slot-less override template | amend the `new bug` case |
| 2, 4 | unit | the same case, no-name and re-run variants | amend |

## Semver

Minor: a new positional argument.
