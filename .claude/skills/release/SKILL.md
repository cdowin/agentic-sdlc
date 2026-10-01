---
name: release
description: Cut a agentic-sdlc release by running the belt — `agentic-sdlc release <version>` runs every release check, names each one that is false, and writes the milestone `done` only when all are true (or on `--force`, on the record); then it prints what is yours to do. Use whenever changes are ready to ship to consumers.
---

# Release

**Bump the version sites first, commit, then run the verb.**

```
agentic-sdlc release <version>
```

It checks six facts, runs no gate, and prints one line per check —
`ok: <check> — <detail>` or `error: <check>: <what is false>` — and then does
exactly one of two things (D12): all true → the milestone's status is written
to the first state of its `done` category, exit `0`, followed by `next:` lines;
any false → nothing is written, exit `1`, every false check named. Re-run
after fixing: every check is a read of the tree, so nothing is carried between
runs. `--force` writes the status anyway and the milestone's `ledger.jsonl`
gets one `deviation` row naming the checks that were false. Exit `2` is a
declaration the machine could not read — a bad version, a config value of the
wrong shape, a key 2.0.0 retired.

The checks themselves — all of them, in order — are in
`make sdlc ARGS='release --help'`. They are deliberately not restated here: a
protocol re-copied into a skill file recreates drift on day one.

## What the belt does not do, and prints as `next:`

The belt writes the milestone's status and nothing else. After `ok`, in the
order it prints them:

- commit the roadmap directory as the release commit — **there is no changelog
  file to retitle (0.6.0)**: the changelog is a `changelog:` field on each grain
  and `agentic-sdlc changelog <milestone-id>` renders the release notes in the
  `order:` the milestone declares. Redirect it if you want a file;
- push the branch — never the mainline;
- open the PR; CI runs the full tiers on it;
- merge as a MERGE COMMIT;
- tag the merge commit and push the TAG ref only;
- sync the local mainline.

Then, by hand: prove the published artifact from a cold cache, and open the
next milestone.

## What the machine cannot do at all

- **Pick the bump.** Patch / minor / major is a semver judgement about the
  interface ([`CLAUDE.md`](../../../CLAUDE.md) rule 7): an output-line-shape
  change is minor at least, and anything a consumer's Makefile or hook must be
  edited for is major. Write the number you chose into every version site
  before the belt runs — `version-sync` reads them and bumps nothing.
- **Run the negative probe** for any gate whose SCOPING changed: introduce the
  drift class into a scratch copy of a `tests/fixtures/` repo and confirm the
  gate FAILS with the expected line shape, plus the config-equivalence pass (no
  `devkit.toml` versus one declaring the stock defaults — byte-identical
  output). It stays in scratch and never reaches outside this checkout.

## Deviating

`--force`, and nothing else. A release over a false check is allowed — descoped,
a hotfix, deliberate — and the `deviation` row the belt writes carries every
false check's own sentence, so a close report quotes the machine rather than
somebody's memory (`pm ledger report` reads it). Deviation stays possible;
**invisible** deviation does not. If the same check is false every release,
that check is wrong — say so rather than forcing past it again.

## The consumer follow-up, after the tag

Report it as INSTRUCTIONS for whoever maintains a consuming repo — never as
work this session does, and never naming a particular repo.

The follow-up, in one sentence a consumer can act on: `uv add --dev agentic-sdlc==X.Y.Z` (the pin is `uv.lock`), run `install-* --diff` to see what the release shipped, and then decide **per file** — `--force` with no path replaces every file that verb writes, including ones you deliberately edited (measured on real adoptions: an installed `verify.yml` grown into a two-job sharded workflow 177 lines from the installable), so `install-* --force <path>` is right for a file you never touched and hand-applying the diff is right for one you did. `agentic-sdlc adopt <version>` then reads the result: checks only, nothing written.

Then re-run `pm init` once (a `.gitattributes` line a release added reaches an
existing tree only that way), run the gate set, and commit the diff.
Integration is proven in the consumer's repo by the consumer's gates (hard
rule 8) — it is not a precondition of this tag, and do NOT edit a consumer
repo from this session.

## Never

Tag without the version-sync commit. Force-move a published tag — a bad
release gets a new patch version, not a rewritten tag. Make a tag wait on
another repo's working state. Tag a version whose grains answered the
changelog question neither way — a sentence or `none` (`check pm` D12 names
each). Write a milestone `done` over a false check without `--force` saying
so.
