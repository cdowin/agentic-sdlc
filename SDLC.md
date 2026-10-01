# The SDLC — build wide, integrate once

The PM tree is packed context. It holds the work, its state and its record. It infers nothing and
it does not police. The why lives in the decisions logs under `pm/roadmap/` and in
[the 2.0.0 design](docs/design/2.0.0-build-wide-integrate-once.md). The agents that run this loop
in a consumer are installed by `agentic-sdlc install-agents`; this repo installs its own copies.

## Roles

| role | does |
|---|---|
| architect (the lead) | talks to Chris; writes stories, moves them, dispatches builders, integrates batches, releases |
| builder (`developer`) | one story or lane, in its own worktree on `feat/<slug>`: spot check, commit, push, report, stop |
| integrator | the architect, or one agent it sends: merges a batch, proves it once, writes `done` |
| reviewer | optional: one per batch, when the risk asks for one |

Nothing runs above effort `high`. A builder that re-writes code is cheaper than one that ruminates.

## The loop

    1. pm new story <feature> <slug> <name>   the story file is the brief; write its body
    2. pm story building <id>                 it is in flight
    3. dispatch --grain <id>                  print the brief; start the builder with it
    4. builder: edit; spot check; commit; git push -u origin feat/<slug>; report; stop
    5. make sdlc ARGS='integrate <slug>...'   merge the batch, prove once, write `done`, delete the lanes
    6. release <version>                      every feature done; write the milestone; CI runs the full tiers

- **The brief is decided.** A story, a bug's Fix or a feature file that outlines the work goes
  straight to a builder. The architect answers open questions in the brief. No planning pass.
- **One builder per story or lane.** Lanes on disjoint files run at once. Two builders that split
  one area get one written contract, in both briefs.
- **The spot check is the builder's only gate**: `[verify] spot`, lint plus one unit slice, under
  30 s. Here it is `make unit`. A PASS is a receipt. The builder runs no wide gate, opens no PR and
  merges nothing.
- **The builder reports in 15 lines or fewer**: branch and hash, files, one changelog sentence,
  NEEDS YOU, NOT verified.
- **Integrate a batch at a time.** The `integrate` verb lands in batch 2 of 2.0.0; until then the
  integrator does its steps by hand:
  1. make an `integrate/<batch>` worktree from the milestone branch;
  2. merge each `origin/feat/<slug>` with `--no-ff`, with a cheap check after each merge;
  3. run ONE proof over the batch (check, full unit, the changed integration slice);
  4. on green: fast-forward the milestone branch, write `done` on each merged story, delete the
     lane worktrees and branches, local and origin;
  5. on red: stop, name the lane whose files the failure touches, close nothing.
- **Every dispatch is measured** by the SubagentStop courier. Compare milestones with
  `pm ledger report <previous> <this>`.

## Validate once

A PASS is a receipt keyed on the tree. Nothing re-runs a gate on a tree that has a receipt. A
close, a push and a release write status and run no gate. CI runs the full tiers one time, on the
release PR.

## Hooks guard, agents trust

A hook refuses only an act that cannot be undone or that harms another tree. A hook never runs a
gate. A builder does not re-check what the integrator will prove. Agents commit and stop.

## Reviews

A review is a judgement, not a step. The lead sends one reviewer over a batch when the batch
touches state, a schema, a persisted format or input. A finding is a bug in the tree
(`pm new bug`). A close does not read a review record.

## Branches

- `main` is the released product. A milestone has `milestone/<version>-<slug>`, named by its
  `branch:` frontmatter. A lane is `feat/<slug>`, cut from the milestone branch.
- The milestone merges to `main` by a merge-commit PR when Chris calls it ready. The version bump
  is at close here (D8 is off in `devkit.toml`).
- Forward only: nothing pushed is amended, rebased, reset or force-pushed.

## Release

`agentic-sdlc release <version>` checks that every feature is `done` and the version sites agree,
writes the milestone `done` and prints the `next:` lines: push, PR, merge, tag. The semver call is
yours (hard rule 7). The `/release` skill runs it.
