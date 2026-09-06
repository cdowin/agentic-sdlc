---
id: "0.3.0"
name: the bump explains itself
status: planning
depends_on: []
branch: milestone/0.3.0-the-bump-explains-itself
---

# 0.3.0 — the bump explains itself

> ## Northstar: **the tool teaches the conveyor.**
> Expressing the flow is the power (0.2.0's northstar). This milestone is the next sentence: a
> project that has just adopted the flow should be able to SEE whether it is using it. Every
> finding below came from a real adoption of the same split on 2026-09-06 — **two of them,
> independently, and they failed in mirror-image ways.**
>
> **The Appalachian Trail** (v0.24.0 single kit → agentic-sdlc v0.2.0 + godot-devkit v1.0.0) ran
> `pm init`, watched `check pm` go green, and never noticed the tree used three of its eight
> declared states. `docs/lessons/2026-09-06-adopting-the-two-kit-split.md` in that repo is the
> write-up.
>
> **NullBound** (same bump, same day) never declared a flow at all, and shipped a green
> `make check` over a PM CLI that was refusing every work-moving verb. It followed godot-devkit's
> "Install — two pins", which names two installers and one config key and never mentions the
> flow; the error it did get was about unknown GATE NAMES, which routed the whole adoption at the
> roster; and the one error that would have named the flow was queued behind a retired key.
>
> One tree declared the flow and did not use it. The other used a flow it never declared. **Both
> passed every gate**, which is the milestone in one sentence.

## Two halves

**The bump reports itself** (seven features) — everything above, from the two adoptions.

**The milestone becomes a release the plan can order** (three). The adoptions exposed a hole
underneath them: this package has a `release` BELT, a `[pm] version_file` and D8 welding the
project version to a milestone's ID — three facts about versions, and no way to plan, order or
point at one. `0.3.0/bugs/the-first-milestone-never-closed` is the cost: 0.1.0's work shipped
inside `v0.2.0` and its milestone has said `planning` ever since, because every rule asks a
question INSIDE the tree.

A first draft added a release grain. That was a second name for a fact the tree already holds —
`accepted` and `packaging` are milestone-only states, words that mean nothing for a body of work
and everything for a release; the milestone carries `branch:`; the belt already writes its status.
**The milestone IS the release**, and what it lacks is one field and one list.

`version:` separates the number from the id, so `0.90.4.1` — a version contorted to express where
work sits — becomes a slug plus a field. `releases.md` declares `order`, because order is a
decision and sorting versions would need a comparator that cannot sort `0.90.3.2` and would
re-couple the two facts anyway. Authoring and scheduling become separate acts: a milestone
declares a version, `pm order --append` puts it on the plan, and the pair of lint rules catches an
entry nobody claims or a version nobody scheduled. The engine never parses a version string —
"did it increase" is a position in a list.

The consumer-visible theme is **a bump that reports itself completely**. An installer that says
which files it touched AND which targets it removed; a config error that names the namespace it
read the key in; an `adopt` that can be satisfied by a project which deliberately owns some of
its installed files; documentation whose exit codes are the ones the code returns. And, first
among them, a `pm init` that reports a MEANING rather than a write, plus a drift rule for the
state a project declares and never uses — because at 0.2.0 a tree using two of eight states is
indistinguishable, to every gate, from one using all eight.

## Ship criterion

A consumer bumping to this version can answer three questions without reading source: *what did
this change in my repo*, *what did it take away*, and *am I actually using the flow I declared*.
Concretely: every installer's `--diff` accounts for every file it owns; a removed target is named
by the installer that used to ship it; `check pm` reports a declared-but-unused state; `pm init`
prints the ladder it wrote against the tree's current usage; `adopt` passes on a tree that has
declared which installed files are its own; and no `--help` in the package documents an exit code
the code does not return.

## Risks

- **The unused-state rule must be a WARN, not a finding.** A tree mid-adoption legitimately has
  unused states, and 0.2.0 just moved D2/D3/D5/D6 to warnings for the same reason. A new rule
  that reddens every fresh consumer would be undone within a version.
- **`[adopt] ours` is a hole if it is not visible.** A project can silence the check by claiming
  every file. The list has to be printed in the belt's own output, every run, so that claiming
  a file is a thing somebody sees.
- **Installer output has consumers.** Line shapes are grepped (rule 6); adding an `[install]`
  header to the modified-file path changes what a `grep -c` returns. Minor bump at least.
