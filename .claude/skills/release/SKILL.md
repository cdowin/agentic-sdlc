---
name: release
description: Cut a agentic-sdlc release by running the conveyor — `agentic-sdlc release <version>` walks the ordered step list, stops at the first step whose postcondition is not true, and says what would make it true. Use whenever changes are ready to ship to consumers.
---

# Release

**Run the verb.**

```
agentic-sdlc release <version>
```

It walks `[release] steps` in order and stops at the first step that is not
true, naming what would make it true. Re-run after fixing: everything already
true is skipped, and the position survives a context clear, an interruption or
a handoff because it is re-derived from the tree rather than carried in
anyone's head. Exit `0` the run completed, `1` it stopped on a step, `2` a
usage or config error.

The steps themselves — all of them, in order, with each one's kind and its
postcondition — are in [`docs/sdlc-protocol.md`](../../../docs/sdlc-protocol.md),
which is **generated from the list that runs** by `agentic-sdlc install-sdlc`.
They are deliberately not restated here. This file said one thing, `SDLC.md`
said another, and the code did a third; that is the drift the conveyor exists
to end, and a protocol re-copied into a skill file recreates it on day one.

## What the machine cannot do, and hands to you

- **Pick the bump.** Patch / minor / major is a semver judgement about the
  interface ([`CLAUDE.md`](../../../CLAUDE.md) rule 7): an output-line-shape
  change is minor at least, and anything a consumer's Makefile or hook must be
  edited for is major. No step can make this call — pass the version you chose
  as `<version>`.
- **Answer the judgement steps.** `pr-open`, `ci-green` and `prove-artifact`
  need a GitHub client and a published artifact, and hard rule 1 is
  stdlib-only forever. Each runs a command this repo configures in
  `[release.commands]`, and with none it refuses to advance rather than pass.
- **Run the negative probe** for any gate whose SCOPING changed: introduce the
  drift class into a scratch copy of a `tests/fixtures/` repo and confirm the
  gate FAILS with the expected line shape, plus the config-equivalence pass (no
  `devkit.toml` versus one declaring the stock defaults — byte-identical
  output). It stays in scratch and never reaches outside this checkout.
- **Open the next milestone** after the tag, so the notes have somewhere to go
  from the first commit: `agentic-sdlc pm new milestone <next> <name>`, then
  `pm milestone ready|building <next>`.

## Deviating

`--skip <step> --reason "<why>"` writes a `deviation` row to the milestone's
`ledger.jsonl` and walks on. Deviation stays possible; **invisible** deviation
does not. `agentic-sdlc release <version> --status` prints what was recorded,
so a close report quotes the machine rather than somebody's memory. If the same
step is skipped every release, that step is wrong — say so rather than skipping
it again.

## The consumer follow-up, after the tag

Report it as INSTRUCTIONS for whoever maintains a consuming repo — never as
work this session does, and never naming a particular repo.

The follow-up, in one sentence a consumer can act on: bump `DEVKIT_VERSION` in your Makefile, run `install-* --diff` to see what the release shipped, and then decide **per file** — `--force` is whole-set and has no per-file option, so it replaces every file that verb writes, including ones you deliberately edited (measured on real adoptions: an installed `verify.yml` grown into a two-job sharded workflow 177 lines from the installable), which makes `--force` right for a file you never touched and hand-applying the diff right for one you did.

Then re-run `pm init` once (a `.gitattributes` line a release added reaches an
existing tree only that way), run the gate set, and commit the diff.
Integration is proven in the consumer's repo by the consumer's gates (hard
rule 8) — it is not a precondition of this tag, and do NOT edit a consumer
repo from this session.

## Never

Tag without the version-sync commit. Force-move a published tag — a bad
release gets a new patch version, not a rewritten tag. Make a tag wait on
another repo's working state. Tag a version whose `## Unreleased` section is
empty. Flip a milestone `done` before the changelog is written and the findings
are landed. Every one of those is a step's postcondition now; none of them is a
thing to remember.
