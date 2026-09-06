---
id: "0.4.0"
name: authoring is separate from binding
status: building
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

## Pre-work — the telemetry, before anything else is built

Four features were added after the milestone opened, and they run FIRST, because everything after
them should be measured and today nothing is.

The trigger: asked for telemetry on this build, the agent hand-wrote a markdown table while the
package sat on `pm ledger` — seven row kinds, automatic per-session token and tool-call capture
off the transcript, and a per-grain spend report. Investigating why turned up that the recording
had been **off for the whole of 0.3.0 and nobody could tell**.

    recording-is-on-or-the-gate-is-red   a fail-open courier needs a fail-loud gate; there is none
    every-row-names-its-grain            hook rows carry no `grain:`, so nothing attributes
    the-surface-says-telemetry           the word "telemetry" is in no discovery surface at all
    telemetry-arrives-with-the-bump      settings.json is printed, never written — so a consumer
                                         bumps to 0.4.0 and records nothing, as this tree did

They belong in THIS milestone rather than a later one for two reasons. The first is ordinary: the
migration is the riskiest work here and it should be the best-measured thing this package has ever
done — so `the-migration-is-whole-or-nothing` depends on them, and the numbers for it will exist.

The second is that they are the same defect. `every-row-names-its-grain` is a binding — a row's
membership in a grain — that is today neither a field nor derived, but absent; that is the
northstar with a different noun. And `the-surface-says-telemetry` is the fourth instance of the
shape `the-read-verbs-compose` already named twice: a capability that shipped, and a surface that
did not admit to it at the moment of need. Four instances is a class, and this milestone is where
it gets stated once instead of rediscovered.

**Write-once, use-many.** These fix this tree; only the fourth makes them reach NullBound,
godot-devkit and whatever bumps next. A telemetry feature that lands here and not downstream has
solved the wrong half.

## Ship criterion

A grain's identity, kind and bindings are read from its frontmatter and from nowhere else; a file's
location is convention the tool does not interpret. Every binding reports both directions it can
be unbound, as a counted line and never a failure. `pm move` is gone. `pm list --unbound` answers
"what have I written and not scheduled" for every kind.

## Risks

- **This is a tree-format migration for every consumer**, unlike anything in 0.3.0 —
  `the-migration-is-whole-or-nothing` is the only feature here that touches an existing tree, and
  it is the riskiest work in the milestone. The CHANGELOG has to be honest that a consumer cannot
  half-adopt it.
- **Slug uniqueness lands on existing trees.** NullBound has 254 stories with reused names — its
  own CLAUDE.md records "S4" meaning three different stories in one session. The migration reports
  those collisions and refuses to guess: an auto-picked id is a name nobody chose, in the one field
  that is stable for life and cited from commit messages. Resolution goes through `pm rename`,
  which is the same ref-sweep problem stated once — and the thing `pm move` gets wrong today.
- **Losing `ls`.** A milestone's directory is currently a browsable answer to "what is in this".
  `pm status` answers it, but a human in an editor loses something real, and 254 files in one pool
  is a directory nobody scrolls.
- **A prefix is not a namespace.** `ft-`/`st-` makes a bare id self-describing; it does not make
  ids unique across repos. Cross-repo disambiguation stays a display concern, never a filename.
