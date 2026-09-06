---
id: 0.4.0/a-document-points-at-what-it-cannot-hold
milestone: "0.4.0"
name: A shared doc is scaffolded, and its absence is visible
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# A shared doc is scaffolded, and its absence is visible

**The trace, and it is the sharpest of the session.** Asked for a handoff, the agent wrote 194
lines restating `pm status`, the dependency graph, the rung costs and the commit log. The
`[grain_shape]` cap rejected it twice. Only afterwards did it emerge that the package **already
ships a handoff template** with the right three-section shape, opening with the exact instruction
being violated.

## How it was missed, precisely

Not "didn't know the file existed" — the failure is more useful than that.

1. `model.py`'s slot constants were read in the first survey: `HANDOFF_FILE_NAME`,
   `MILESTONE_OPTIONAL_SLOTS`, `SLOT_TEMPLATE`, `SLOT_HEADER`. **The word "slot" was in four
   constant names.**
2. `pm --help` was read while scaffolding features. `new milestone`'s entry says, verbatim:
   *"scaffold the grain file in its own dir; no sub-slot dirs, and a shared doc appears on first
   WRITE. **Idempotent — re-run to fill**"*.
3. `ls pm/roadmap/0.4.0-…/` returned `features`, `ledger.jsonl`, `milestone.md`. No `handoff.md`.
4. **From "the file is absent" the conclusion was "I author it."** The question *"how does this
   file normally come into existence?"* was never asked.

So the guidance was read and did not fire. The reason it did not is worth naming, because it is a
naming defect and it will recur:

> **`pm new <kind>` is also `pm repair <kind>`, and its name only describes the first use.**

"new milestone" reads as *create a milestone*. 0.4.0 already existed, so the verb looked
inapplicable. Its second job — refilling empty slots in a grain that already exists — is real,
idempotent, and disclosed only in a parenthetical clause on a verb whose name argues against it.

**And the tree could not help.** `MILESTONE_OPTIONAL_SLOTS` is read by exactly one module,
`templates/__init__.py` — the *writer*. No gate and no read verb knows that `handoff.md` is a slot.
`pm status 0.4.0` prints thirteen features and does not mention that a `building` milestone has no
handoff. The knowledge lives only on the path you take if you already knew to take it.

## Four layers, cheapest first

**1. The absence is visible.** A milestone in an `in_progress` category with no `handoff.md` is a
`check pm` WARN naming `pm new milestone <id>`. This is the layer that would actually have caught
it: the absence was on screen, in an `ls`, and read as *nothing to see*. `MILESTONE_OPTIONAL_SLOTS`
already enumerates what should be there — the reader side just never asks.

**2. The header is enforced.** A shared doc not opening with its `SLOT_HEADER` is a finding.
`templates/__init__.py:79-83` already computes the wanted header and returns it when absent; that
logic runs only on `pm new`. This points the same comparison at files on disk, so a doc that was
hand-authored, copied from another milestone, or edited until its first line went, is caught. It
must not be stricter than the writer, which accepts any known header.

**3. The template carries the breadcrumbs.** Section 2 says *"Not a status dump"* — it says what
NOT to do and leaves the alternative to be invented. It should carry the pipeline pre-written, so
the right thing is the default and the author deletes what does not apply:

```bash
git log --oneline <base>..HEAD    # the commit messages carry the arguments
pm status <id>                    # every feature, state, story count
pm ledger report                  # spend per grain; what gates have cost
verify --plan                     # the rungs, with measured costs
```

The header changes with it. Today it names one verb (`pm status`); it should name the class,
because it is *"the one channel that reaches a dispatched subagent"* and its words are the most
expensive in the package. Section 1's **Tree** row should prompt for the absolute path — that is
the single most non-derivable fact in a worktree setup, and its absence cost three tool calls and a
standing hazard on this milestone.

**4. The skill.** Triggered on "handoff", "pick this up cold", "hand this to a fresh agent".

*Recorded once and then dropped:* the argument against was that a skill is a fourth name for what
three constructs carry, in the milestone about deleting second names. **Chris's call is to build
it, and the reason it survives that objection is layer 1 through 3 do not fire at the moment
someone types "write me a handoff" — a skill description is the only surface that does.** So its
job is not to teach handoff-writing. It is to **route**: run `pm new milestone <id>` first, the
template is the answer, here is what counts as derivable. A skill that restates the template's
content instead of pointing at it has reproduced this feature's own bug, and review should reject
it on exactly that ground.

## Ship criterion

`check pm` WARNs on an `in_progress` milestone with no `handoff.md`, and on a shared doc missing
its `SLOT_HEADER`; both name `pm new <kind> <id>` as the repair. `templates/handoff.md` carries the
orient pipeline in section 2 and prompts for the absolute tree path in section 1. The header names
the class of derivable content, not one verb. A `handoff` skill exists whose description carries the
words someone types, and whose body routes to the template rather than restating it. All of it
reaches consumers on bump, because the templates and the gate live in the wheel.

## Proof budget

  cases: 4-5
  tier: pyunit
  lands in: `tests/test_pm_gate.py` (two rules), `tests/test_pm_scaffold.py` (template text),
    `tests/test_pm_guidance.py` (the skill's description)
  what already covers this: `test_pm_scaffold.py` already asserts `pm new` writes the header and
    template, so both text changes extend existing cases. `test_pm_guidance.py` already asserts
    shipped skill text. New: a `building` milestone with no handoff is a finding; a doc missing its
    header is a finding; a doc carrying a DIFFERENT slot's known header is silent (matching
    `templates/__init__.py:83` — the gate must not out-strict the writer).

## Out of scope

Making `handoff.md` a required slot. It is optional by design and a milestone nobody hands off
does not need one — the WARN is for a milestone that is `in_progress`, which is when someone might.
Renaming `pm new`. The naming defect is real and named here, but a rename is a verb-surface change
with consumer cost, and layer 1 removes the need to know the verb at all.
