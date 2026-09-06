---
id: 0.2.0/the-release-is-a-conveyor/03-the-gate-cannot-run-before-the-review-landed
feature: 0.2.0/the-release-is-a-conveyor
milestone: "0.2.0"
name: The gate cannot run before the review landed
status: building
owner:
depends_on: ["0.2.0/the-release-is-a-conveyor/01-the-conveyor-refuses-to-advance", "0.2.0/the-release-is-a-conveyor/02-the-step-list-is-the-projects", "0.2.0/the-belts-refuse-to-advance"]
---

# The gate cannot run before the review landed

On a tree whose review record carries a finding at `disposition: open`, `agentic-sdlc release`
stops at `review-landed`, names the finding ids, and **never reaches `gate`**. The ordering
error that cost 0.24.0 two full `make milestone` runs — one at 3:00, one at 3:17, both void
before the tag — becomes structurally impossible rather than a paragraph somebody has to
remember.

This story is the step REGISTRY: every step in the shipped default list, its kind, its
`check()`, its `do()` and what it prints when it refuses. The driver and the kinds are story
01; the list as config is story 02.

## `review-landed` CALLS `pm ready-for tag`. It does not re-implement it.

`0.2.0/the-belts-refuse-to-advance` ships `pm ready-for tag <milestone-id>` in phase 3, exit
`0` ready / `1` not ready (naming the blockers) / `2` usage. `review-landed` imports that
predicate and reports what it returns. It does **not** call `verdict.parse` itself.

Two readers of "is every finding dispositioned" would be two answers, and the second one would
be the permissive one on the day they disagree. That is the same argument
`gates_extra.py`'s docstring makes about a second TOML reader and the same one `checks/pm.py`
makes about importing its predicates from `model.py`. A test asserts `release_steps.py` does
not import `verdict` at all.

The same holds for `features-done` → `pm ready-for milestone`, and for every step that flips a
status → the `pm` CLI, never a regex over frontmatter.

## The default list, reconciled against the prose it replaces

The shipped list is 20 steps, **not the 21 the feature file and the audit both claim** — the
inline TOML in `the-release-is-a-conveyor/feature.md` holds 20 names. The correction lands here.

| # | step | kind | `check()` — the postcondition | `do()` |
|---|---|---|---|---|
| 1 | `tree-clean` | judgement | `git status --porcelain` is empty | states it; this machine never commits for you |
| 2 | `on-milestone-branch` | judgement | HEAD == the milestone's `branch:` frontmatter (D9's stamp) | names the branch to switch to |
| 3 | `main-merged` | judgement | mainline is an ancestor of HEAD | names the merge |
| 4 | `changelog-unreleased-nonempty` | judgement | `## Unreleased` holds ≥1 bullet | states that notes are written as work lands |
| 5 | `review-landed` | judgement | `pm ready-for tag <milestone>` exits 0 | names every open finding id it returned |
| 6 | `version-sync` | automatic | `__init__.py` `__version__` == `pyproject.toml` `version` == `<version>` | writes both, one commit's worth of edit |
| 7 | `readme-pins` | automatic | the pin sites name `<version>` | rewrites them |
| 8 | `features-done` | judgement | `pm ready-for milestone <milestone>` exits 0 | names the features that are not |
| 9 | `milestone-reviewing` | automatic | milestone status is `reviewing` or later | `pm milestone reviewing` |
| 10 | `gate` | gate | the configured gate command exits 0 | none — a gate is not made true by re-running it |
| 11 | `milestone-accepted` | automatic | status is `accepted` or later | `pm milestone accepted` |
| 12 | `changelog-retitle` | automatic | a `## v<version> — <ISO date>` heading exists and a fresh empty `## Unreleased` sits above it | performs the retitle |
| 13 | `milestone-packaging` | automatic | status is `packaging` or later | `pm milestone packaging` |
| 14 | `findings-resolved` | judgement | no `docs/reviews/` document names this milestone | names the ones still there |
| 15 | `milestone-done` | automatic | status is `done` | `pm milestone done` |
| 16 | `push-branch` | automatic | the branch tip equals its upstream tip | pushes the branch (never `main` — the pre-push hook's rule, restated as a refusal) |
| 17 | `pr-open` | judgement | `[release.commands] pr-open`, else the operator confirms | states what to open, against what base |
| 18 | `ci-green` | judgement | `[release.commands] ci-green` | states which run must be green |
| 19 | `merge` | judgement | the mainline contains this branch's tip | states that the merge is a merge commit |
| 20 | `tag` | automatic | the tag exists locally AND on the remote | creates and pushes the TAG ref only |
| 21 | `prove-artifact` | judgement | `[release.commands] prove-artifact` | states what must print the new version |

**`findings-resolved` is new.** `SDLC.md` § *Close protocol* step 5 requires every
`docs/reviews/` doc for the milestone to be resolved and deleted, and the feature's inline list
has no step for it — so the machine would have shipped a protocol shorter than the prose it
replaces. That is the drift this whole feature exists to end, found in its own list.

**Rule 8 governs `prove-artifact`.** The proof command names a git URL, and a URL is a
project's own fact. It ships with **no default command**, so the stock step is a judgement the
operator answers; this repo configures its own in its own `devkit.toml` (story 02's file). A
shipped default naming a repository would put a consumer's provenance in this package's code,
which is `bugs/consumer-names-and-provenance-in-code` all over again.

**Deliberately NOT steps** (risk 1 — a step earns its place by having a checkable
postcondition; everything else is guidance and story 05 renders it into the doc):

- the negative probe for a gate whose scoping changed (`SKILL.md` precondition 3) — the artifact
  is a judgement in scratch, with nothing in the tree to check;
- the consumer-pin reminder (`SKILL.md` step 8) — instructions for someone in another repo, and
  rule 8 forbids gating on one;
- opening the next milestone (`SKILL.md`'s closing paragraph) — it happens after the tag and
  needs a name only a human has.

## Refusal matrix — the step surface (SDLC.md §5)

The steps are the input surface here: each is asked about a tree that may be hostile.

| input | expected |
|---|---|
| `<version>` names a milestone whose `branch:` is empty | `on-milestone-branch` refuses and says D9 has no stamp — never "assume the current branch" |
| a milestone directory with no `CHANGELOG.md` at the root | `changelog-unreleased-nonempty` refuses naming the path; it does not create the file |
| `## Unreleased` present but holding only whitespace or a comment | refuses — an empty section is the case, not the heading's absence |
| two `## Unreleased` headings | refuses as ambiguous; never retitles the first one |
| a review record whose verdict block does not parse | `review-landed` reports UNVERIFIABLE via `ready-for tag`, exit 1 — never a pass (`the-belts-refuse-to-advance` risk 2) |
| `__init__.py` and `pyproject.toml` already disagreeing, neither equal to `<version>` | `version-sync` names both current values before writing |
| `<version>` already tagged | `tag` reports already-true and does not force-move — a bad release is a new patch version (`SKILL.md` § Never) |
| the current branch IS the mainline | `push-branch` refuses, naming the pre-push hook's rule, and pushes nothing |
| a configured command that exits 2, times out, or writes 100 MB to stdout | the step is NOT-DONE with the exit code named; output is bounded and the run stops |
| a step whose `check()` raises | the run stops and names the step — never a traceback, never "advanced anyway" |
| `HOME`/`CI` unset, no git remote, detached HEAD | each names the missing precondition; none of them silently pass |

## Acceptance criteria

1. **The ordering is structural.** A fixture repo whose review record carries `open` findings
   runs `release` and stops at `review-landed`, naming every finding id; the `gate` command is
   never invoked (asserted by a command recorder, not by reading output).
   `tests/test_release_steps.py::test_open_finding_stops_before_gate`. This test must be watched
   FAILING on a registry that omits the dependency.
2. `release_steps.py` imports the `ready-for` predicates and **does not import
   `agentic_sdlc.repo.pm.verdict`** — asserted by a source-level test, the shape
   `tests/test_boundaries.py` already uses.
3. Every step in the registry declares a kind from story 01's closed set, and a census test
   asserts `set(registry) == set(shipped default list)` — the `roster == dispatchable` bar
   `0.2.0/the-extraction-finishes/01` sets for gates, applied to steps.
4. Every AUTOMATIC step is **idempotent**: run it twice on the same fixture, the second run
   reports already-true and writes nothing (byte-compare the tree).
5. Every AUTOMATIC step's `verify()` is proven to catch a `do()` that did not take — one test
   per step, monkeypatching `do()` to a no-op and asserting the run STOPS.
6. `findings-resolved` fails on a fixture repo carrying a `docs/reviews/` document naming the
   milestone, and names the path.
7. `prove-artifact` with no configured command refuses as a judgement and prints what the
   operator must run; a test asserts the shipped default table contains **no** command for it
   and no URL anywhere in the module (rule 8).
8. Every row of the refusal matrix is a test, on a scratch copy of a fixture repo — never on a
   fixture in place (CLAUDE.md § Verification loop).

## Files this story may touch

- `src/agentic_sdlc/repo/conveyor/release_steps.py` — NEW (the registry and every step)
- `tests/test_release_steps.py` — NEW
- `tests/fixtures/` — a new purpose-built repo fixture carrying a milestone, a review record
  with an open finding, a CHANGELOG and a `docs/reviews/` document (vendored here, rule 8)

## Files this story must stay out of

`conveyor/driver.py`, `conveyor/state.py`, `src/agentic_sdlc/cli.py` (story 01),
`conveyor/config.py`, `src/agentic_sdlc/core/config.py`, `devkit.toml` (02), `conveyor/skip.py`
and `src/agentic_sdlc/repo/pm/ledger.py` (04), `conveyor/render.py`,
`src/agentic_sdlc/repo/install.py`, `SDLC.md`, `.claude/skills/release/SKILL.md` (05),
`src/agentic_sdlc/repo/pm/verdict.py` and the `ready-for` implementation
(`0.2.0/the-belts-refuse-to-advance`) — this story is a CALLER of both.

## Out of scope

- Changing `verdict.py`'s parsing, or `pm ready-for`'s exit contract. If `ready-for tag` answers
  wrong, that is a finding against `the-belts-refuse-to-advance`, filed — not patched here.
- The `adopt` registry — `0.2.0/adopt-is-a-conveyor/02`.
- Rendering any of this table into prose — story 05 reads the registry.

## Close

done: 6e9388d — review-landed precedes gate in the shipped list, and a registry omitting the
dependency is a test failure watched failing with the gate's recorder file present. The
ordering that cost 0.24.0 two void gate runs is structural now.
The list is 21, not the planned 20: SDLC.md's resolve-the-findings step had none.
