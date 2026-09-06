---
id: 0.3.0/bugs/the-first-milestone-never-closed
milestone: "0.3.0"
name: 0.1.0 is still planning, and nothing in the package can tell
status: open
severity: medium
caught_in: "0.3.0"
---

# 0.1.0 is still planning, and nothing in the package can tell

`pm list --kind milestone` on this repo:

```
0.1.0	planning	todo	-
0.2.0	done	done	milestone/0.2.0-the-conveyor
0.3.0	planning	todo	milestone/0.3.0-the-bump-explains-itself
```

**0.1.0's work shipped.** `7ae552e Green the suite, self-install, and start 0.1.0` and
`cb37e51 Merge pull request #1 from cdowin/setup/0.1.0-standing-alone` are in the mainline; the
package stood alone, the suite was green and it self-installed, which is what the milestone was
named for. There is no `v0.1.0` tag — the only tag is `v0.2.0` — so whatever 0.1.0 covered went out
inside the 0.2.0 release.

**The record never moved.** `milestone.md` is the untouched scaffold: `status: planning`, an empty
`branch:`, and every template comment still in place (`<!-- Theme: one paragraph… -->`). It has no
features, so `ready-for milestone` would call it vacuously blocked and `check pm` D3 has no
children to contradict.

## Why no gate caught it

Every existing rule asks a question **inside** the tree — is this status contradicted by a child,
does this ref resolve, does the version match the in-progress milestone. **Nothing relates a
milestone to a RELEASE.** So a milestone whose work shipped under someone else's version is
invisible: it has no children to contradict it, it is not in progress so D8 ignores it, and the
`v0.2.0` tag is not connected to any grain at all.

The lexical listing then makes it actively misleading: `0.1.0` sorts FIRST, so anything answering
"what is next" off that order names a milestone that finished months ago. (String order has a
second defect on its own account — `0.90.10` sorts before `0.90.4` — filed separately if the
ordering work does not subsume it.)

## Fix

Two parts, and the second is the real one.

1. **Immediately:** close 0.1.0 honestly — `done`, with a `covers`/evidence line naming
   `7ae552e` and `cb37e51` and the fact that it went out inside `v0.2.0`. It is not `obe`: the
   work happened.
2. **Structurally:** this is the motivating case for the release-plan work. A version bound to a
   grain, an ordered list of those bindings, and a cross-check that a `done` milestone has a
   release row and a shipped release row has a `done` milestone. Under that rule this bug is a
   finding on the first run rather than something a human notices a version later.

## Verified when

`pm list --kind milestone` shows 0.1.0 `done`; the release record names which version carried it;
and a rule reports the inverse case (a milestone that shipped with no release row) so this class
cannot recur silently.
