---
id: 0.2.0/init-can-append-to-a-config-it-did-not-write
milestone: "0.2.0"
name: An existing consumer gets the new section without losing its own
status: planning
reviewed:
phase: 6
depends_on: []
consumed_by: []
risk: high
size: m
---

# An existing consumer gets the new section without losing its own

**The blocker in the 0.3.0 plan**, found by its review, and it is a contradiction I wrote.

- Milestone criterion 5 said *"a consumer declaring nothing sees no behaviour change"* — a
  fallback.
- Feature criterion 5 said *"no fallback; a tree missing the section gets a refusal"*.

Opposites, in one milestone, because I wrote the first before Chris ruled no-fallback and then
updated the design without updating the criterion. **No-fallback is the ruling and it stands.**

But the review found what makes it unshippable as written: **`init.py:158-193` never overwrites an
existing `devkit.toml`, and `--force` is documented as never touching it.** That is correct — it
is the project's file. So on a pin bump every existing consumer is refused by a runtime that will
not fall back, by a verb that will not write the section, with no path between the two.

## What is missing is an APPEND grain

`init` already has the shape: `_write_gitignore` appends entries to a file it does not own,
idempotently, without disturbing what is there. The states-and-transitions section needs the same
treatment.

## Ship criterion

1. `init` on a tree with an existing `devkit.toml` APPENDS the section, idempotently, and touches
   nothing else in the file.
2. A tree that already declares it is left byte-identical and the run says `already current`.
3. **The refusal, when the section is absent, prints the seed to paste.** A refusal naming what is
   missing is a worse experience than the default it replaced; one that hands over the answer is
   better than both.
4. `adopt`'s `config-updated` names this as a finding on a pin bump, with the value, rather than
   letting a release crash three steps in.
