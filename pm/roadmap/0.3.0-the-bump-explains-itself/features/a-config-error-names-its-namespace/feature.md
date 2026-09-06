---
id: 0.3.0/a-config-error-names-its-namespace
milestone: "0.3.0"
name: A config error names the namespace the key was read in
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---


# A config error names the namespace the key was read in

**The finding.** `[gates] extra` takes **make target names**. The adjacent `[checks] godot` takes
**gate names**. Nothing in either key, or in either error, says which. The adopting agent put
`budget` — a real gate — into `[gates] extra` and got `make[1]: *** No rule to make target
'budget'. Stop.` from GNU make, three layers below the config that caused it.

The same class, in godot-devkit: `[unit_disk] forbidden_literals` must be a reason-to-patterns
TABLE, while the neighbouring `exclude_prefixes` is a LIST. The README shows the list form and the
`forbidden_calls` table form; it never shows `forbidden_literals` at all. A list is exit 2, from a
message that names the key but not the shape it wanted.

Both are the same defect: **a key's value has a domain, and the error does not name it.**

## Ship criterion

A key read from `devkit.toml` that resolves into another namespace says so in its own error —
`[gates] extra` names a MAKE TARGET, and an entry that is a known gate name rather than a target
says exactly that and names the target that would run it. Every documented key shows one example
of its own shape, including the table-valued ones.

## Proof budget

  cases: 2-3
  tier: pyunit
  lands in: the config-reader test module
  what already covers this: `gates-extra` is tested for what it emits, not for what it says when
    handed a plausible non-target. The exit-2 paths are covered by key NAME, not by value shape.
