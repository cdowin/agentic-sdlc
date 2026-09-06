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
> finding below came from one real adoption — The Appalachian Trail, v0.24.0 (single kit) to
> agentic-sdlc v0.2.0 + godot-devkit v1.0.0, 2026-09-06 — and the biggest one is that the
> adopting agent ran `pm init`, watched `check pm` go green, and never noticed the tree used
> three of its eight declared states. `docs/lessons/2026-09-06-adopting-the-two-kit-split.md`
> in that repo is the write-up.

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
