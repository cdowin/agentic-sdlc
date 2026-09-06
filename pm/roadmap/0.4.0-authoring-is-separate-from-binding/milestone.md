---
id: "0.4.0"
name: authoring is separate from binding
status: planning
depends_on: ["0.3.0"]
branch: milestone/0.4.0-authoring-is-separate-from-binding
---

# 0.4.0 — authoring is separate from binding

> ## Northstar: **the path is where a file lives; the frontmatter is what it is and what it
> belongs to.** Today those are the same fact, and the tool ships a rule (V2) whose whole job is
> keeping two copies of it in agreement — which is the thing this package forbids everywhere else.

0.3.0 separated one binding: a milestone declares a `version:`, `order` schedules it, and a rule
reports either half without the other. **This milestone is that shape, everywhere.**

Today you cannot write a feature without binding it, because you must put the file somewhere and
**where you put it is the parent**. `model.py` says it plainly: *"a grain's kind is read from which
slot its document sits in."* The `milestone:` field in frontmatter is a duplicate of the path, and
V2 exists to police the duplication.

It already costs. `pm move` re-parents a story by renaming its file, because moving it changes its
identity — and it **does not rewrite the refs pointing at it**, so every `depends_on` naming that
story goes stale in silence. The verb is complicated precisely because position is parentage; once
a binding is a field, `pm move` is `pm set` and deletes itself.

## What changes

An id becomes a **kind-prefixed slug** — `ft-two-pin-toolkit-adoption`, `st-two-pins-one-make` —
unique within its kind and stable for life. Not an allocated number: a counter needs an allocator
and a git repo has none, so `nul-st-255` either collides across branches (max+1) or conflicts on
every branch (a counter file). Uniqueness becomes a gate finding instead — do what you are asked,
report contradictions.

Each kind gets a pool directory the config names. `milestone:` and `feature:` become the
authoritative bindings and are OPTIONAL, so a grain written and not yet bound is normal, expected,
and reported as a census line rather than an error. Planning gets cheap in exactly the way
`pm-execution.md` already argues it should be.

Sequence generalises with it. 0.3.0 built `order` for one edge; **membership is the child's field
and sequence is the parent's list** at every level, which retires two ad-hoc answers the tool
already ships — the `pm:execution` block with the V6 rule policing it (the same defect as V2 and
the path), and `story_ordinal_prefix`. What a container may hold stops being written per level and
becomes `[pm.contains]`, which is the config stating the model.

What is left is four kinds of verb and nothing else:

    write   pm new <kind> <slug>                     the parent argument is gone at every level
    bind    pm set <id> <rel> <target>               one field, the primitive
            pm add|remove <parent-id> <child-id>     bind AND sequence, one intent
    read    pm list | status | roadmap | next | ready-for
    check   check pm

Neither `add` nor `set` names a KIND: an id carries its own as a prefix, so both are derivable and
`[pm.contains]` validates the pair. `pm move` and `pm order` both retire into `pm add` — the first
because position stops being parentage, the second because it was `add` against the root wearing a
different name. Belts sit on top unchanged — their checks, then one write. And the read verbs emit every field somebody
would filter on, because the shell is the filter and a withheld column is what makes a consumer
believe otherwise.

## Ship criterion

A grain's identity, kind and bindings are read from its frontmatter and from nowhere else; a file's
location is convention the tool does not interpret. Every binding reports both directions it can
be unbound, as a counted line and never a failure. `pm move` is gone. `pm list --unbound` answers
"what have I written and not scheduled" for every kind.

## Risks

- **This is a tree-format migration for every consumer**, unlike anything in 0.3.0. It needs a
  migration verb that is idempotent and reversible, and the CHANGELOG has to be honest that a
  consumer cannot half-adopt it.
- **Slug uniqueness lands on existing trees.** NullBound has 254 stories with reused names — its
  own CLAUDE.md records "S4" meaning three different stories in one session. The migration will
  surface real collisions, and renaming a grain is a ref-rewriting problem, which is the thing
  `pm move` gets wrong today. The migration verb must do what `pm move` does not.
- **Losing `ls`.** A milestone's directory is currently a browsable answer to "what is in this".
  `pm status` answers it, but a human in an editor loses something real, and 254 files in one pool
  is a directory nobody scrolls.
- **A prefix is not a namespace.** `ft-`/`st-` makes a bare id self-describing; it does not make
  ids unique across repos. Cross-repo disambiguation stays a display concern, never a filename.
