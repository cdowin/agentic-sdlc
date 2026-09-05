# The release protocol, as the machine runs it

<!-- Written by `agentic-sdlc install-sdlc`. Do not hand-edit: the ordered
     lists below are RENDERED from `[release] steps` and `[adopt] steps` in
     this repo's devkit.toml and from the step registry that walks them, so
     the only way to change them is to change the config or the code and
     re-run the verb. A hand-written document describing the steps is the
     second home for the protocol, and a second home drifts — which is the
     failure this file exists to end. -->

Run it:

```
agentic-sdlc release <version>
```

It walks the list below in order and **stops at the first step whose
postcondition is not true**, saying what would make it true. It is resumable:
the position is a cache under `.agentic-sdlc/run/`, every step is re-checked
against the tree on every run, and deleting that file costs nothing. Exit `0`
the run completed, `1` it stopped on a step, `2` a usage or config error.

Three kinds of step, and the third one is the honest limit:

- **AUTOMATIC** — code performs it, then re-asks the postcondition. `do()`'s
  own report is never what marks it done.
- **GATE** — a command; exit 0 is true. It has no `do()`, because a gate is not
  made true by running it again.
- **JUDGEMENT** — code cannot perform it. It reads the ARTIFACT of a judgement,
  or a command the project configures. With neither, it answers UNVERIFIABLE,
  which is a refusal to advance and never a pass.

To deviate: `--skip <step> --reason "<why>"`. The pair is written to the
milestone's `ledger.jsonl` as a `deviation` row. Deviation stays possible;
invisible deviation does not. `--status` prints what has been recorded.

## `release` — the ordered list

| # | step | kind | command | what makes it true |
|---|---|---|---|---|
| 1 | `tree-clean` | JUDGEMENT | — *(operator)* | `git status --porcelain` is empty. |
| 2 | `on-milestone-branch` | JUDGEMENT | — *(operator)* | HEAD is the branch the milestone document stamps in `branch:` (D9). |
| 3 | `main-merged` | JUDGEMENT | — *(operator)* | the mainline is an ancestor of HEAD. |
| 4 | `changelog-unreleased-nonempty` | JUDGEMENT | — *(operator)* | the changelog's `## Unreleased` section holds at least one bullet. |
| 5 | `review-landed` | JUDGEMENT | — *(operator)* | `pm ready-for tag <milestone>` exits 0 — every review finding is dispositioned. This is the step that makes the gate's position structural rather than remembered. |
| 6 | `version-sync` | AUTOMATIC | — | every configured version site names the release version. |
| 7 | `readme-pins` | AUTOMATIC | — | every `vX.Y.Z` pin inside a fenced code block names the release version. Prose naming an older tag is history and is never rewritten. |
| 8 | `features-done` | JUDGEMENT | — *(operator)* | `pm ready-for milestone <milestone>` exits 0. |
| 9 | `milestone-reviewing` | AUTOMATIC | — | the milestone status is `reviewing` or later. |
| 10 | `gate` | GATE | `make milestone` | the configured gate command exits 0. It has no `do()`: a gate is not made true by running it again. |
| 11 | `milestone-accepted` | AUTOMATIC | — | the milestone status is `accepted` or later. |
| 12 | `changelog-retitle` | AUTOMATIC | — | a `## v<version> — <ISO date>` heading exists with a fresh empty `## Unreleased` above it. |
| 13 | `milestone-packaging` | AUTOMATIC | — | the milestone status is `packaging` or later. |
| 14 | `findings-resolved` | JUDGEMENT | — *(operator)* | no document under the review directory names this milestone — every record resolved and deleted. |
| 15 | `milestone-done` | AUTOMATIC | — | the milestone status is `done`. |
| 16 | `push-branch` | AUTOMATIC | — | the branch tip equals its upstream tip. It refuses on the mainline and pushes nothing there. |
| 17 | `pr-open` | JUDGEMENT | — *(operator)* | the configured `pr-open` command exits 0. With none, the operator is asked and the run refuses to advance. |
| 18 | `ci-green` | JUDGEMENT | — *(operator)* | the configured `ci-green` command exits 0. With none, the operator is asked and the run refuses to advance. |
| 19 | `merge` | JUDGEMENT | — *(operator)* | the mainline contains this branch's tip. |
| 20 | `tag` | AUTOMATIC | — | the tag exists locally AND on the remote. It is never force-moved. |
| 21 | `prove-artifact` | JUDGEMENT | — *(operator)* | the configured `prove-artifact` command exits 0. This package ships no default: the proof names a git URL, and a URL is the project's own fact (hard rule 8). |

## `adopt` — the ordered list

> `[adopt] steps` is not configured in this repo, and this package ships no default list for `adopt`. Nothing walks it.

## Not steps, and why

A step earns its place by having a CHECKABLE POSTCONDITION. What follows is real protocol with none, so the machine states it and does not pretend to enforce it.

**The judgement runs first, and the gate answers for its result.** When a gate and a judgement both bear on one decision, the judgement runs first. A gate that runs before the review answers for a tree nobody will ship, and every fix landed afterwards voids it while it still reads as readiness. `review-landed` sits above `gate` in the list for exactly this reason, and the machine will not walk past it.

**Pick the bump yourself.** Patch, minor or major is a semver judgement about the interface, and no step can make it. Output-line-shape changes are minor at least; anything a consumer must edit for is major.

**The negative probe for a gate whose scoping changed.** Introduce the drift class into a scratch copy of a fixture repo and confirm the gate FAILS. It is not a step: the artifact is a judgement made in scratch, with nothing in the tree to check.

**The consumer follow-up.** A consumer bumps its pin, runs `install-* --diff`, and decides PER FILE. It is not a step: those are instructions for somebody in another repo, and this package gates on no other repo's state (hard rule 8).

**Forward only.** Nothing pushed is ever amended, rebased, reset or force-pushed. A botched commit is repaired with another commit, and a bad release is a new patch version — never a rewritten tag.

**Open the next milestone.** After the tag, so the next release's notes have somewhere to go from the first commit. It is not a step: it needs a name only a human has.

## Changing this document

Edit `[release] steps` (or `[release.commands]`) in `devkit.toml` and re-run
`agentic-sdlc install-sdlc --force`. There is nothing to edit here: every line
of the lists above is derived from the config and the registry that runs it.
