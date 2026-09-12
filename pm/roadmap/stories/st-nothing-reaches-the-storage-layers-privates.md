---
id: st-nothing-reaches-the-storage-layers-privates
kind: story
feature: ft-frontmatter-has-one-grammar-and-one-way-in
milestone: "ms-the-tool-agrees-with-itself"
name: nothing outside core/frontmatter reaches its private names, and the gate says so
status: planning
owner:
depends_on: ["st-rename-rewrites-through-the-storage-layer"]
changelog:
---

# nothing outside core/frontmatter reaches its private names, and the gate says so

Closes `bg-the-storage-layers-privates-are-reached-from-outside-it`. Read its Symptom (the 14 sites,
by path) and its Fix first.

0.7.0's ship criterion said `tests/test_boundaries.py` *"forbids its internals being reached from
outside it"*. What shipped (`OneStorage`) forbids RE-BINDING one of the 8 `FRONTMATTER_INTERNALS`,
which bans a second implementation and nothing more. Fourteen sites reach them. The rename story
removes 7. The 5 in `pm/inventory.py` each ask one of three questions the owner already answers
internally: where the fence sits, whether a line is a list item, and what a line is without its
trailing comment. Each gets a public name on the owner.

**The gate and the migration land together, or neither does.** A widened gate with an exemption
roster naming every offender is a gate that cannot fail. That was the feature's own M1, and it is
rule 4's first sin.

## Acceptance criteria

1. Re-count the reaches first. The bug's 14 is a number from 0.7.0's review, and the close says what
   the count was at the start of this story.
2. `pm/inventory.py` uses public names on `core/frontmatter.py` for its three questions. Behaviour
   does not change, and the existing inventory cases pass unamended.
3. `OneStorage` fails a reach (an attribute access or an import of a name in
   `FRONTMATTER_INTERNALS`) from any module outside `core/frontmatter.py`, with an EMPTY offender
   list.
4. **Deliberately-broken probe:** plant one reach in a scratch copy, and confirm the gate FAILS by
   path.
5. A census of 0 scanned modules FAILS, as rule 4 requires.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 2 | unit | the existing inventory cases | existing |
| 3, 5 | unit | `OneStorage` in `tests/test_boundaries.py`, widened | amend |
| 4 | unit | the gate's own violation corpus, one planted reach | amend, if `OneStorage` declares a corpus |

## Semver

Patch. Nothing a consumer imports changes, and the new public names are internal to the package.
