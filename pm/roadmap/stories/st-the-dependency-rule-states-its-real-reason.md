---
id: st-the-dependency-rule-states-its-real-reason
kind: story
feature: ft-the-dispatch-carries-the-contract
milestone: "ms-the-rule-reaches-the-work"
name: the dependency rule states its real reason
status: building
owner:
depends_on: []
changelog: none
---

# the dependency rule states its real reason

Hard rule 1 says *"Stdlib only, forever… A consumer's hook must never break on a transitive
dependency."* **The reason is true for one half of the package and not the other, and the rule does not
say which.**

**Where it holds absolutely:** `cc-ledger-subagent.sh` parses its payload with bare `python3 -c` — a
consumer's system interpreter, no managed environment. Non-negotiable for the courier corpus.

**Where it does not:** the package runs through `uvx --from …` / `uv run`, which resolve declared deps
into an isolated env. Cold-start cost is real; "a consumer's hook breaks" is not.

**And what actually blocks the useful libraries is HARD RULE 3, not rule 1.** There are 165 lines of
hand-rolled frontmatter I/O in `model.py` — `set_list_field` alone is 70, the function that produced
this milestone's `depends_on` scalar-vs-list defect. Rule 3 requires a write to preserve *every other
byte, line endings included*. PyYAML reserialises. `ruamel.yaml` round-trips comments and formatting
but guarantees SEMANTIC round-tripping, not byte-exact. A CLI framework is blocked by rule 6 (output
line shapes are contract). A validation library is blocked by nothing and unnecessary — `check pm`
already IS the validator.

## Goal

Rule 1's text names the courier corpus as the surface its reason protects and distinguishes the
package's own runtime, **without changing what the rule permits and without moving its number** —
roughly 600 citations depend on the ordinals.

A `pm decide` entry records the audit: each candidate, and the rule that blocks it. It names the one
live trade — relaxing byte-exact to semantic preservation would delete ~165 lines and a class of shape
bugs — as **rule 3's** trade to make, not rule 1's.

## Verification

`check shell`, or the courier corpus itself, asserts no hook's inline interpreter imports outside the
stdlib. That constraint is currently held by convention alone, which is the thing this story is about.

## Out of scope

Taking a dependency. This adds nothing to `pyproject.toml`; it makes the next person argue against the
right rule.

## Evidence

done: c0c8f68 — rule 1's sentence names the hook corpus as the surface its reason protects and
distinguishes the package's own uvx-resolved runtime. The number did not move and what the rule
permits did not change. D4 on the milestone carries the audit: PyYAML and ruamel.yaml are blocked by
rule 3, a CLI framework by rule 6, a validation library by nothing and unnecessary. The one live
trade — byte-exact to semantic preservation, ~165 lines of `model.py` — is recorded as **rule 3's**
to make and is NOT taken here.
