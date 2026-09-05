# The protocol, as the machine runs it

<!-- Written by `agentic-sdlc install-sdlc`. Do not hand-edit: the ordered
     lists below are RENDERED from `[story]`, `[feature]`, `[release]` and
     `[adopt]` steps in this repo's devkit.toml and from the step registry
     that walks them, so
     the only way to change them is to change the config or the code and
     re-run the verb. A hand-written document describing the steps is the
     second home for the protocol, and a second home drifts — which is the
     failure this file exists to end. -->

Run it — one verb per level, and none of them is "run the biggest thing":

```
agentic-sdlc close story   <story-id>      the inner loop, seconds
agentic-sdlc close feature <feature-id>    once its stories are done
agentic-sdlc release       <version>       once its features are done
agentic-sdlc adopt         <version>       a devkit pin bump, scoped to the adoption
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
| 21 | `prove-artifact` | JUDGEMENT | `uvx --from git+https://github.com/cdowin/agentic-sdlc@v{version} agentic-sdlc --version` | the configured `prove-artifact` command exits 0. This package ships no default: the proof names a git URL, and a URL is the project's own fact (hard rule 8). |

## `adopt` — the ordered list

| # | step | kind | command | what makes it true |
|---|---|---|---|---|
| 1 | `pin-bumped` | JUDGEMENT | — *(operator)* | the `DEVKIT_VERSION` line in this repo's own makefile names the version of the package that is running. It is a line in a file this package does not own, so the step states the edit and writes nothing. |
| 2 | `installables-diffed` | AUTOMATIC | — | the diff between what this version ships and what is installed here has been produced, and the recorded census still describes the tree (each file with a digest, so an edit made after the diff makes it stale). |
| 3 | `installable-decisions-recorded` | JUDGEMENT | — *(operator)* | every file that differs carries a decision in the run's record. `--force` is whole-set and has no per-file option, so take / hand-apply / keep is a call only the consumer can make. |
| 4 | `config-updated` | JUDGEMENT | — *(operator)* | every devkit.toml section this version still READS accepts what this repo declares. There is no retired-key table: a section this package no longer reads may be another kit's, and telling those apart would mean knowing the consumer (hard rule 8). |
| 5 | `hooks-self-test` | GATE | `agentic-sdlc check hooks` *(shipped)* | `check hooks` exits 0 — the installed guards are armed, executable, still start, and still return the verdicts their own corpus asserts. A guard that fails OPEN is not there, and a config diff cannot see it. |
| 6 | `runner-targets-resolve` | GATE | `make -n <[adopt] runner_targets>` *(shipped)* | the composed gate targets resolve under `make -n`. A tier named with no tier file FAILS here naming the file; an empty tier list passes and SAYS it was empty — `-include`'s silence is never a pass. |
| 7 | `checks-pass` | GATE | `agentic-sdlc check all` *(shipped)* | this package's `agentic-sdlc check all` exits 0. NOT `make check`, not `make precommit`, not `[gates] extra`: those verify the consumer's code against the consumer's rules, and a version bump here cannot change their verdict. |
| 8 | `pm-validates` | GATE | `agentic-sdlc pm validate` *(shipped)* | `pm validate` exits 0 — the PM tree is still good against the new version. A repo with no PM tree is refused, never vacuously fine. |

## `story` — the ordered list

| # | step | kind | command | what makes it true |
|---|---|---|---|---|
| 1 | `claimed` | AUTOMATIC | — | the story's status is `building` or later. The flip goes through `pm story building <id>`, never a regex over frontmatter. |
| 2 | `narrow-verified` | GATE | `agentic-sdlc verify --story` *(shipped)* | the narrow rung exits 0 — `agentic-sdlc verify --story`, which is a function of the CHANGED PATHS and of `[[verify.narrow]]`. The command is never named in the step: what proves an edit is the project's own fact. On a committed tree the rung says `no changed paths` and that sentence is quoted rather than summarised as a pass. |
| 3 | `committed` | JUDGEMENT | — *(operator)* | nothing is uncommitted outside the roadmap directory. It NAMES what is, and it never commits — a story closed by a machine that also wrote the commit is a story nobody reviewed. The roadmap directory is excluded because this belt writes there itself. |
| 4 | `evidence-written` | JUDGEMENT | — *(operator)* | the story file carries `done: <hash(es)> — <what shipped>` (pm-execution.md step 6). READ, never written: the sentence is the author's, and a generated one would be a second scoreboard saying what the commit already says. |
| 5 | `story-done` | AUTOMATIC | — | the story's status is `done`, through `pm story done`. |

## `feature` — the ordered list

| # | step | kind | command | what makes it true |
|---|---|---|---|---|
| 1 | `stories-done` | JUDGEMENT | `agentic-sdlc pm ready-for feature <id>` *(shipped)* | `pm ready-for feature <id>` exits 0 — every story under this feature is `done`, and each one that is not is NAMED. Never re-implemented: the verb owns that question. |
| 2 | `feature-reviewing` | AUTOMATIC | — | the feature's status is `reviewing` or later — the hand-off that says a reviewer runs now, once, over the whole feature. |
| 3 | `feature-verified` | GATE | `agentic-sdlc verify --feature` *(shipped)* | the range rung exits 0 — `agentic-sdlc verify --feature`, the composition the project names for that rung. |
| 4 | `review-recorded` | JUDGEMENT | — *(operator)* | the feature's `reviewed:` record exists, is repo-relative, and its verdict block PARSES (`pm/verdict.py`). Whether the review was any good is NOT checked and must not be: a step pretending to check it would be this package's cardinal sin wearing a protocol. A record that does not parse is UNVERIFIABLE — a refusal, never a pass. |
| 5 | `findings-landed` | JUDGEMENT | — *(operator)* | no finding in that record sits at `disposition: open`. The same question `pm ready-for tag` asks one grain up, through the same parser, so the two cannot disagree. |
| 6 | `feature-done` | AUTOMATIC | — | the feature's status is `done`, through `pm feature done <id> --review-record <path>`. |

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
