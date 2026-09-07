---
id: ft-documented-behaviour-is-the-behaviour
milestone: ms-0.3.0
name: Every documented exit code and verb is the one that runs
status: done
reviewed: docs/reviews/0.3.0-documented-behaviour-is-the-behaviour.md
phase:
depends_on: []
consumed_by: []
kind: feature
order:
  - "st-the-help-and-the-code-agree"
---


# Every documented exit code and verb is the one that runs

**Three findings, all of the shape "the surface says one thing and the code does another".**

**1. `check budget --help` documents an exit code the code does not return.** It states that a
tier with no `gate` row is UNMEASURED and that "both are findings, never a pass". v0.2.0 exits 0
for it. The adopting consumer read the help, believed the gate would redden a tree with no
milestone building, and nearly left it out of its gate roster for that reason — then measured the
exit code, found 0, and wired it in with a written warning to re-check on the next bump. A
consumer should not have to run the binary to learn its contract.

**2. Two ways to close a feature, and the shorter one skips the belt.**
`pm feature done <id> --review-record <path>` writes the status and stamps `reviewed:` in one go,
skipping `close feature`'s `stories-done` and `findings-landed`. Nothing in `pm --help` says the
belt exists, or that this path bypasses it. It is also the command every older consumer doc
already contains, so a bump leaves the belt-skipping path as the well-trodden one.

**3. The ledger's REFUSED line fires on every gate of every run.** On a tree with no `building`
milestone, each gate prints `gdk-gate: the recorder exited 1: [pm] REFUSED — no milestone in
pm/roadmap is in progress…`. On a fresh adoption that is once per gate, per run, forever, and it
reads like a broken install rather than a true and unremarkable fact.

## Ship criterion

No `--help` in the package documents an exit code the code does not return, held by a test that
reads the help text and the exit code together. `pm --help` names the belt beside the status-write
path that bypasses it. The no-ledger condition is reported once per run, as information.

## Proof budget

  cases: 3-4
  tier: pyunit
  lands in: the CLI help/contract module and the gate-library shell corpus
  what already covers this: help text is asserted for presence of verbs, never for agreement with
    behaviour. Nothing reads a documented exit code and compares it to a real one.
