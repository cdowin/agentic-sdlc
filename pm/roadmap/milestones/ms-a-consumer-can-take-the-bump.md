---
id: "ms-a-consumer-can-take-the-bump"
kind: milestone
name: a consumer can take the bump
status: building
depends_on: ["ms-nothing-is-hand-rolled"]
branch: milestone/0.8.0-a-consumer-can-take-the-bump
version: 0.8.0
changelog:
order:
  - "ft-the-shipped-words-match-the-shipped-tool"
  - "bg-the-release-belt-and-the-render-verb-disagree-about-changelog"
  - "ft-install-force-keeps-what-the-project-owns"
  - "ft-the-pm-surface-has-no-dead-ends"
  - "bg-the-gate-help-names-one-of-its-four-rule-families"
  - "ft-a-gate-verdict-is-true-of-the-tree"
  - "bg-the-bump-belt-does-not-run-the-gate-a-consumer-armed"
  - "ft-every-printed-command-runs-in-a-stock-consumer"
---

# 0.8.0 — a consumer can take the bump

> ## Northstar: **a consumer bumping the pin follows what the kit prints, and ends up with a correct
> tree without restoring anything from git.** Every command the kit prints runs, every sentence it
> installs is true, every gate verdict is true of the tree, and `--force` touches only what the kit owns.

## Where this came from

Eighteen issues, #19 to #36, all filed on 2026-09-11 by two consumers taking the 0.4.0 → 0.7.0 bump.
One is a Godot project with its own agent roster (`[adopt] ours` claims 9 to 11 agents), and one
carries a 4-segment per-PR version. The issue numbers are listed on each story. #15 also comes in, but
only its unfinished `pm-execution.md` audit, because that story edits the same file.

Checked against `origin/main` (4dae916 = v0.7.0) before writing this milestone. **18 of 18 are still
valid.** #28 has the same root cause as #21 (`install.py` `retired_since()`), #29 is contained in #20,
and #36 is the sharpest case of #22. Each pair is one story, and every issue number stays on it.
#12 and #14 were already fixed in 0.6.0 and were closed with evidence instead of being pulled in.

**Many sources, few causes.** Five causes account for all of it, and each is one feature:

    the words        the installed rule, two role briefs, the rendered protocol and the README
                     describe 0.4/0.5 behaviour                            #32 #23 #33 #34 #35 (#15)
    the installer    --force overwrites what [adopt] ours and the config header
                     say is the project's, and its census scans an empty span   #20 #29 #21 #28
    the pm surface   pm <verb> --help exits 2, pm new bug has no name, retire
                     has no path for older history                                  #25 #24 #31
    the gates        a PASS over a silenced rule, a wrapped span nobody reads, a hotfix
                     refused, a WARN that says "never held" about held states    #19 #26 #27 #30
    the vehicle      ~109 shipped `agentic-sdlc <verb>` citations plus the rendered
                     lines, and a stock consumer has no such command on PATH         #22 #36

## Ship criterion

A scratch consumer wired exactly as the README says (`DEVKIT_VERSION` + `include Makefile.devkit`,
nothing else on PATH) does a 0.4.0 → 0.8.0 bump by following only what the kit prints. At the end:

- every command it pasted exited 0 or 1 and never with `command not found`;
- every `[adopt] ours` file and every project-config header is byte-identical to before the bump;
- `install-*` named the `changelog-writer.md` withdrawal, or said it could not see the span;
- `check pm` on a roster written before 0.6.0 either grades D11/D12 or says by name that it does not;
- the rule `pm install-skills` installs contains no sentence the tool contradicts.

Every GH issue listed above is closed when its feature is accepted, with a comment citing the
feature and the fixing commit hash(es), following SDLC.md §2. The GitHub milestone `0.8.0` has no
open issues left, and the three pool bugs bound here are `closed`.

## Semver: 0.8.0, a minor bump (D1)

This was planned as 0.7.1. By rule 7, 12 of its 16 stories need a minor bump: new flags, a new
positional, a new `Makefile.devkit` target, changed WARN and hint lines, and a gate that now fails a
tree it passed. It ships whole as 0.8.0. The reasoning and the rejected split are in
`ms-a-consumer-can-take-the-bump-decisions.md` D1. Each story's `## Semver` line still says which
shape it is, for the changelog.

## Also bound here

Three bugs from the pool that sit right next to issues here, each ordered after the feature it
neighbours (D1):

    bg-the-release-belt-and-the-render-verb-disagree-about-changelog   next to #33, the same check
    bg-the-gate-help-names-one-of-its-four-rule-families               next to #25, check pm's help
    bg-the-bump-belt-does-not-run-the-gate-a-consumer-armed            the bump belt itself

## Risks

- **The vehicle is decided: `make sdlc ARGS="…"`** (`ft-every-printed-command-runs-in-a-stock-consumer`
  D1). Every story that rewrites shipped text spells commands through it, even though the sweep lands last.
- **#26 before #32 turns consumers red on a file they cannot edit.** Closing the gate hole flags the
  wrapped `pm feature reviewing` in the installed rule for any project with no `reviewing` feature
  state. The words land first: `st-check-doc-reads-a-code-span-across-a-line-break` depends on
  `st-the-auto-loaded-rule-is-true-at-this-version`.
- **Splicing the config header was a rule-3 question**, and it is decided:
  `ft-install-force-keeps-what-the-project-owns` D1 records why a carried block is still a whole-file
  write. The review should hold the builder to exactly that boundary: carry bytes, compute nothing.
- **"Fix the message" can be the whole fix, and that is fine.** Rule 11 says to fix at the cheapest
  layer. A named line is preferred over a new verb in every story here.
