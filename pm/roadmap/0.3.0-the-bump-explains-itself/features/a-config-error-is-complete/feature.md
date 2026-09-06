---
id: 0.3.0/a-config-error-is-complete
milestone: "0.3.0"
name: A config error reports every defect, and the flow first
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# A config error reports every defect, and the flow first

Sibling to `a-config-error-names-its-namespace`: that one is about a value whose DOMAIN the error
does not name. This is about a config read that stops at the first defect, so the defect that
matters is reported second — or not at all.

**The finding**, measured on the NullBound adoption (v0.24.0 → the two-pin split, 2026-09-06).
That tree had two config defects at once: a retired `[pm] review_slug_fallback`, and no
`[pm.states.*]` at all. `check pm` reports them one at a time, first encountered first:

```
# retired key present, flow absent — what the consumer is told:
[check:pm] ERROR — [pm] review_slug_fallback was retired and does nothing … Remove the key.

# retired key removed, flow still absent — only NOW:
[check:pm] ERROR — this tree declares no flow: [pm.states.bug] is not in devkit.toml,
           and there is no default … Run `agentic-sdlc pm init` …
```

Both messages are excellent. The ordering is the defect: **the retired key is cosmetic and the
missing flow stops every work-moving verb in the package**, and the consumer is told about the
cosmetic one. Fixing it and re-running is a second round trip to learn the thing that mattered.

**And the first message a consumer actually sees is neither of these.** With the pre-split
`[checks] all` still holding both kits' gate names, the run dies earlier still:

```
agentic-sdlc: [checks] all names unknown gate(s) uid, tres, props, defaults, rng,
              tres-comment, unit-disk, test-shape — known gates are doc shell …
```

That is a message about GATE NAMES. It routes the whole adoption at the roster, which is a
twenty-minute fix, and nothing on that path ever mentions the flow. The adopting agent split the
roster, watched `make check` go green, and reported the adoption complete over a tree whose PM
CLI was refusing every verb. **A green aggregate over a dead conveyor is the exact failure this
milestone's northstar names**, and it was reachable because errors arrive one at a time in an
order nothing ranks.

## Ship criterion

A `devkit.toml` read reports EVERY defect it found, not the first — one line each, exit 2 once.
Where several are present the flow is named first, because a tree with no flow has no working
verbs and everything else is cosmetic beside that. `check all` does not let a roster error hide a
gate's own config error: a roster that cannot be parsed is reported WITH whatever the named gates
would have said about their own sections, not instead of it.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: the config-reader test module, beside the existing exit-2 cases
  what already covers this: every config refusal is covered singly — one bad key, one message.
    There is no case with TWO defects present, so nothing asserts what a consumer is told when
    the tree is wrong in more than one way, which is the normal state of a real adoption.

## Out of scope

Changing any individual message. Each one is already better than most tools manage; this is about
how many of them a consumer gets, and in what order.
