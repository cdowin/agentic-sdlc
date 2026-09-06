---
id: 0.2.0/the-release-is-a-conveyor
milestone: "0.2.0"
name: The release protocol is a resumable step machine, not prose to follow correctly
status: done
reviewed: docs/reviews/2026-09-05-the-release-is-a-conveyor.md
risk: high
size: l
phase: 4
depends_on: ["0.2.0/the-belts-refuse-to-advance", "0.2.0/every-gate-reports-its-cost", "0.2.0/the-story-belt-knows-what-verifies-this-edit"]
consumed_by: ["0.2.0/adopt-is-a-conveyor"]
labels: ["release", "sdlc", "installable", "config", "subtraction"]
---

# The release protocol is a resumable step machine, not prose to follow correctly

**Chris, 2026-09-04, after the release protocol got its own ordering wrong for the third time:**

> *"Can we do even better than skills and CLAUDE.md? Can we just encode the steps literally in code? We
> could even make it configurable about which ones to run vs skip etc for a given project. Basically, can
> we just create the conveyor belt? Move to next, move to next, move to next. Then the bot never has to
> infer anything."*

## Why — three incidents, one mistake

The release gate has been coupled to, or ordered against, the wrong thing three separate times:

1. `bugs/the-release-gate-cannot-run-before-the-close-it-gates` — D6 refused a `building` milestone whose
   features were all `done`, so the gate demanded the ship decision it exists to inform.
2. `make smoke` made two consumer checkouts a precondition for this package's tag — CLAUDE.md rule 8 and
   `bugs/consumer-names-and-provenance-in-code`, the latter filed 2026-09-02 and **shipped past in 0.23.0**.
3. **0.24.0's own release**: `make milestone` was run BEFORE the reviewer, twice (3:00 and 3:17), and both
   runs were void the moment the review asked for fixes. The gate answered for a tree nobody was shipping.

Each was fixed in prose. Prose is instructions someone must follow correctly, and following it correctly
is inference. **The rule the third incident produced — *when a gate and a judgement both bear on one
decision, the judgement runs first and the gate answers for its result* — is exactly the kind of thing a
step list expresses structurally and a paragraph does not.**

## What already exists, so this is mostly assembly

Three of the four pieces are shipped:

- **A configurable roster** — `devkit.toml [checks] all` and `[gates] extra`, already per-project.
- **A state machine** — `planning → ready → building → reviewing → accepted → packaging → done`.
- **Machine-readable judgement artifacts** — every review record ends in `| id | severity | disposition |`
  and `verdict.parse` already returns them structured, N passes per record since 0.24.0.

Missing: **a driver that walks the steps and refuses to advance.**

## The shape

`agentic-sdlc release <version>` — a resumable step machine over a config'd list:

```toml
[release]
steps = ["tree-clean", "on-milestone-branch", "main-merged",
         "changelog-unreleased-nonempty", "review-landed",
         "version-sync", "readme-pins", "features-done", "milestone-reviewing",
         "gate", "milestone-accepted", "changelog-retitle",
         "milestone-packaging", "milestone-done",
         "push-branch", "pr-open", "ci-green", "merge", "tag", "prove-artifact"]
```

Each step declares **`check()`** (is this already true?), **`do()`** (make it true, or state precisely what
a human must do), **`verify()`** (prove it took). Resumability falls out: re-run after fixing and it skips
what is already true. **The position lives on disk, not in an operator's head** — which is what makes it
survive a context clear, an interruption, or a handoff.

### Three kinds of step, and the honest limit

- **Automatic** — `version-sync`, `changelog-retitle`, `tag`. Code does it; nothing is inferred.
- **Gate** — run a command, require exit 0.
- **Judgement** — the review, the merge, the semver call. **Code cannot perform these.** It can refuse to
  advance until the ARTIFACT of judgement exists.

That third kind is where all three incidents lived, and it is already checkable: `review-landed` passes
only when a review record carries a verdict block with **zero findings at `disposition: open`**. On 0.24.0
the reviewer filed M1, M2 and m1–m4 as `open`, so the conveyor would have **refused to run `gate`** and the
ordering error becomes structurally impossible rather than a thing to remember.

## Chris's two rulings, both settled 2026-09-04

- **Steps are skippable, and a skip is RECORDED.** `--skip <step> --reason "…"` writes the deviation to the
  ledger. Deviation stays possible; *invisible* deviation does not. A protocol nobody can deviate from gets
  worked around, and a worked-around protocol teaches nothing.
- **The docs are GENERATED from the step list**, and shipped the way everything else is:
  > *"The docs is kind of like the install verbs for agents and skills. You get devkit, write your config,
  > and install the sdlc, install the agents, install the skills."*

  So **`install-sdlc` joins `install-agents` / `install-skills` / `install-hooks` / `install-runners` /
  `install-ci`**, and a consumer's SDLC document is rendered from *their* `[release] steps`. It cannot drift
  from what actually runs — which is the exact failure this milestone fixed by hand in `SDLC.md` and
  `.claude/skills/release/SKILL.md`, in two places, after they disagreed with each other and with the code.

## Scope

| Thing | Action | Purpose |
|---|---|---|
| a `release` verb + step registry | NEW | the driver; one module per step kind |
| `devkit.toml [release]` | NEW | the step list, per project, with a shipped default |
| run state | NEW | on-disk position, so the run is resumable and inspectable |
| `install-sdlc` | NEW | renders the SDLC doc from the step list |
| `.claude/skills/release/SKILL.md` | SHRINK | becomes "run this verb", not a protocol to follow |
| `SDLC.md` § Close protocol | GENERATED | stops being hand-maintained prose that drifts |

## What moved out of this feature on 2026-09-05

This was `size: xl` with four deliverables inside it, which is the shape of a feature that
reports "still building" at close. Three of the four are now their own features and this one
keeps the driver:

| was here | now |
|---|---|
| the `adopt` step list | `0.2.0/adopt-is-a-conveyor` — same driver, different operation |
| the `change` pair | superseded by `design-the-three-belts.md` and built as `0.2.0/the-story-belt-knows-what-verifies-this-edit` |
| the entry-condition verbs | `0.2.0/the-belts-refuse-to-advance` — `pm ready-for`, which `review-landed` then CALLS rather than re-implements |

What stays: **the step machine, its run state, the skip ledger, and `install-sdlc`.** The last
one is not separable — a step machine whose documentation is hand-written is this feature's own
risk 2, so generated docs ship with the driver or the driver ships a second home for the
protocol.

## The three steps that cannot be Python, and the ruling

`pr-open`, `ci-green` and `merge` in the default list all need GitHub. **Hard rule 1 is
stdlib-only, forever** — no `gh`, no HTTP client, no transitive dep in a consumer's pre-push
hook. So they are not automatic steps, and pretending otherwise would put a network dependency
in the one package that promised never to have one.

They are **judgement steps whose `check()` is a command the project configures**:

```toml
[release]
steps = ["...", "pr-open", "ci-green", "merge", "tag", "prove-artifact"]

[release.commands]
ci-green = "gh pr checks --required"      # the PROJECT supplies gh, not this package
```

A judgement step with no configured command still works: it states what the operator must do,
and refuses to advance until told the artifact exists. **That is the honest shape** — the
machine's job is to refuse, not to pretend it can merge.

## The first slice, and why it is that one

**`review-landed` then `gate`, in that order, with the disposition check.** It needs no new parsing —
`verdict.parse` already returns dispositions — and that single ordered pair encodes the lesson of all three
incidents. Everything else is additive once the driver exists.

## Risks

1. **Over-encoding.** Not every instruction is a step. The test: a step must have a checkable
   postcondition. If it does not, it is guidance and belongs in the generated doc, not in the list.
2. **A second home for the protocol** — the failure this feature exists to end. Mitigated only if the docs
   are genuinely generated; a hand-written doc *describing* the steps recreates the drift immediately.
3. **A conveyor that is always skipped is worse than none**, because it looks like control. If the skip
   ledger shows the same step skipped every release, that step is wrong and the feature has to say so.
