---
id: ft-adopt-grades-what-the-project-owns
milestone: ms-0.3.0
name: adopt grades the files the project did not claim
status: done
reviewed: docs/reviews/0.3.0-adopt-grades-what-the-project-owns.md
phase:
depends_on: []
consumed_by: []
kind: feature
order:
  - "st-a-project-claims-the-files-it-owns"
---


# adopt grades the files the project did not claim

**The finding.** `adopt`'s `installables-current` check is all-or-nothing across 27 files. On the
Trail adoption it was the single false check out of seven, and it can never become true: that
repo deliberately keeps local work in eleven installed files — its CI workflow (a two-job sharded
build) and ten agent briefs it has customised over many milestones. The agents were preserved on
purpose, file by file, after diffing each against the archived previous version to prove which
carried real local work.

The friction is that **the installables invite exactly this**. Each ships a `Project config`
section, "yours to edit after install", and each roster file says the file is the repo's after the
write. The belt then fails on the files the package told the consumer to make their own. The
result is not a project that conforms; it is a project for which `adopt` is permanently advisory
at 6/7, which is the same as no belt at all.

## Ship criterion

A project can declare which installed files it owns — `[adopt] ours = [...]` — and
`installables-current` grades the rest, reporting the claimed files as a named, counted line
rather than passing over them in silence. Claiming a file is visible in the belt's output on
every run, so the list is a statement rather than a hiding place. An unclaimed drifted file is
still false, with its `install-* --diff` named as it is today.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: the adopt-belt test module, beside the existing check-list cases
  what already covers this: the belt's check list is covered end to end, but every
    `installables-current` case asserts on drift vs no-drift. There is no case for a project that
    deliberately owns an installed file, because there is no way to express one.
