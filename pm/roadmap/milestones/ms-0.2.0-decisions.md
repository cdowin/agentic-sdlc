Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# 0.2.0 the conveyor — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-05 — The middle tier splits by -include, not by a third devkit.toml key

`Makefile.devkit` carries the gate framework and a Godot target roster in one file, and that is
what blocks `godot-devkit` 0.25.0. The framework keeps `check`/`precommit`/`milestone`; the
language kit contributes its targets through `-include $(GDK_TIERS_MK)` and two variables,
`GDK_PRECOMMIT_TIERS` / `GDK_MILESTONE_TIERS`.

**Rejected: a `[gates] precommit` / `[gates] milestone` key in devkit.toml**, symmetric with the
`[gates] extra` mechanism that already exists. Three reasons it loses:

1. Make cannot get target *definitions* out of TOML, so the tier file has to exist regardless.
   A config key beside it is a second source of truth that can disagree with the first — a
   target listed in config and absent from the file is a crash naming the wrong thing.
2. The `check` target's sub-make exists because `[gates] extra` is genuinely per-project data
   read at recipe time. Tiers are not: `-include` resolves at parse time, prerequisites stay
   prerequisites, and `make -n` keeps its promise to run nothing.
3. `[gates] extra` keeps meaning exactly one thing — the *project's* own gates. Three
   authorities writing into one list is how a roster stops having an owner.

**The cost accepted:** `-include` of a missing file is silent, which is what makes a
pure-SDLC consumer work with no tier file at all — and is also how a typo'd `GDK_TIERS_MK`
could shorten a gate silently. Bought off by making an *empty* tier list quiet and a *named*
tier that resolves to nothing loud (`0.2.0/the-middle-tier-splits` story 02).

## D2 — 2026-09-05 — An installable belongs to the kit whose artifact it acts on

> An installable belongs to the kit whose **artifact** it acts on — not to the kit whose
> **structure** it borrows.

`milestone.md` and `the-extraction-finishes` both deferred this, separately, as
"the installables' middle tier". It is one question with one answer, and the answer settles
`cc-godot-sandbox.sh`, `doctor.sh`, `ci-verify.yml` and `Makefile.devkit` together:
`cc-godot-sandbox.sh` guards Godot engine boots, so it goes — and `hooks-self-test`, which
exists only to replay its corpus, goes with it. `Makefile.devkit`'s structure is ours and its
roster is not.

**Rejected: "it is a consumer-facing installable and the kit should test what it ships"** —
the argument for keeping the Godot sandbox hook here, offered in `the-extraction-finishes`.
It is true and it proves too much: by that reasoning every runner stays too, and the split
never finishes. Shipping a thing is not the same as owning it.

**Rejected: settling each file on its own merits.** Four independent judgements is four
chances to draw the line differently, and the second one would be argued from the first
rather than from a rule.

**The cost accepted:** `make hooks-self-test` loses a corpus and this repo's
`HOOKS_WITH_CORPUS` narrows to the two ledger couriers. A corpus list that empties out and
still passes would be the exact failure this rule is supposed to prevent, so the census stays
loud on zero.

## D3 — 2026-09-05 — One ladder: [verify] names which rung each composition is, rather than a second set of commands

**Chris, 2026-09-05, mid-milestone:**

> *"There are some actions that are outside of 'dev work' like pinning a new version, but then
> there's the SDLC along three levels. … finishing a story or adopting a new devkit version
> shouldn't be a huge milestone check. The checks should all have their place."*

Two gaps the plan had, found by asking that:

**Gap 1 — the middle rung had no command.** `design-the-three-belts.md` names three belts, and
`[verify]` as designed declared two levels: `narrow` (the edit) and `wide` (the close). The
FEATURE belt — the feature's whole commit range, cross-story duplication, functions grown across
edits — was described and unbuilt. A ladder with a hole in the middle is a ladder where a story
close reaches for `make milestone`, which is the 170x this milestone exists to end.

**Gap 2 — two mechanisms answered one question.** `[verify] narrow`/`wide` in `devkit.toml`, and
`check` / `precommit` / `milestone` in `Makefile.devkit`. Nothing tied them, so they could
disagree about what "wide" means. That is a second scoreboard, and `pm-execution.md` already
rules that a second scoreboard lies.

**The ruling — one ladder, three rungs, and `[verify]` NAMES the composition rather than
replacing it:**

```toml
[verify]
# story  — the inner loop. Rules, not a command: the paths decide.
[[verify.narrow]]
paths = "src/agentic_sdlc/repo/pm/**"
run   = "python3 -m pytest tests/test_pm_*.py"

[verify]
feature   = "make precommit"     # the range, one step wider. Run once per feature.
milestone = "make milestone"     # everything, every interpreter. Run once.
```

`feature` and `milestone` are **the names of existing make targets**, not new commands. The
Makefile composition stays the authority on what a target RUNS; `[verify]` is the authority on
which RUNG it is. One fact each, no overlap, and a project that renames a target changes one
line.

**Rejected: `[verify] wide` as a command string of its own**, which is how the feature was first
written. It reads fine until a project's `wide` and its `make milestone` drift apart, and then
two answers exist to "did the full gate pass" — with the CI workflow running one of them and the
dispatch quoting the other.

**Rejected: three more make targets (`verify-story`, `verify-feature`, `verify-milestone`).**
That is a third naming of the same ladder, in the file that already has two of them, and it
cannot express the story rung at all — the story rung is a FUNCTION of the changed paths, which
make cannot compute.

**What this closes, as a table.** Every operation now has exactly one verb and one scope, and
none of them is "run the biggest thing":

| doing | verb | scope |
|---|---|---|
| editing, inner loop | `verify --changed` | only the paths touched — seconds |
| closing a story | `pm ready-for feature <fid>` | are the sibling stories at `reviewing` |
| closing a feature | `verify --feature` | the feature's range — tens of seconds |
| closing a milestone | `verify --milestone` | everything, once — minutes, paid once |
| tagging | `pm ready-for tag <mid>` | every finding at a disposition other than `open` |
| bumping a pin | `adopt` | the adoption, never the project's own gates |

**The cost accepted:** `verify --feature` cannot, in 0.2.0, scope itself to the feature's commit
RANGE the way `--changed` scopes to a diff — it runs the composition the project names. Scoping
by range needs the feature's first commit, which is derivable from the ledger and is not derived
today. Named as the gap rather than faked: a rung that claims to be range-scoped and is not
would be a false narrowing, which is worse than an honest wide one.

## D4 — 2026-09-05 — The sequencing question is answered by dispositioning, not by choosing an order

**The question, as posed:** phase 6 changes the state model underneath phases 3-5, so landing the
36 open findings first means touching some of that code twice; the alternative is building the
rebuild first and landing the findings onto the final shape.

**The ruling: disposition all 36 against the rebuild BEFORE choosing an order, and the choice
mostly evaporates.** The partition is in `docs/reviews/2026-09-05-0.2.0-plan-audit.md`:
25 independent, 5 bookkeeping, 4 owned by the rebuild, 1 half-dissolving, **0 dissolving
outright**. Thirty of thirty-six do not care which order is picked, and five of the independent
25 are BLOCKERs — every one a hard rule 4 defect. **The order governs four findings**, and paying
for that with thirty findings held open is the worse trade.

**Rejected: build phase 6 first, land everything onto the final shape.** It is the right instinct
about the wrong object. It buys the correct placement of four findings and costs six weeks of a
tree carrying five rule-4 blockers — gates printing PASS over what they did not measure — which is
the failure class this package's every release review has caught.

**Rejected: land all 36 first, then rebuild.** It writes R4, B1, B2 and B3 against predicates the
rebuild deletes, and it does nothing about the actual double-touch.

**The actual double-touch is `the-inner-levels-are-belts-too`**, which nobody was looking at
because it is a feature rather than a finding. It is `planning`, 0 of 3 stories built, and it
specifies belts that REFUSE — written before the report-never-refuse ruling. Building it in place
means writing the halt into two new belts and deleting it, which is a feature's worth of code and
tests. `the-belt-reports-and-finishes` moves ahead of it in the same phase, declared through
`depends_on`. That costs nothing.

**The cost accepted:** four findings sit open until phase 7, and one of them (B1) is user-visible
in `pm --help`. Fixing B1's help text early is a two-line change that the rebuild then rewrites —
cheap enough that if it bothers anyone it should just be done twice.

**And the test for every "dissolves" disposition, which R1 supplies:** removing the halt changes
what a false postcondition COSTS; it does not make the postcondition true. R1's deadlock
dissolves; step 14's demand that every review record be deleted still leaves `check pm`
permanently RED on D1. R1 and R2 are one finding.

## D5 — 2026-09-05 — D8/D9/D10 report over every in_progress milestone, rather than the engine picking one

Under three hard categories, `in_progress` may hold several states **and several milestones**, so
`model.py:995`'s `building_milestones` — one line serving D8, D9 and D10 — has no expression. P4
of the plan review found it; no grain answered it.

**The ruling: D8, D9 and D10 report over EVERY milestone whose status is in `in_progress`.** A
tree with three milestones in progress gets three answers, which is a true statement about that
tree. A project that wants exactly one narrows it by declaring one; the engine does not guess
which. That is `holds(milestones, in_progress)` doing precisely its job, and it costs nothing.

**Rejected: an `active: true` frontmatter field on the milestone.** It is a schema change, and it
re-introduces the same class of engine opinion one level up — the engine would then know there is
such a thing as "the active milestone" and require the project to nominate one, when a project
running two release trains in parallel has two and is not wrong.

**Rejected: keep `building` as a reserved word for this one case.** That is the milestone's whole
premise surviving in the three rules nobody listed, which is how the census got short in the first
place.

**The cost accepted:** a tree with several `in_progress` milestones gets several D8/D9/D10 reports
where it used to get one. That is louder, and it is louder about something true. If it turns out
to be noise in practice, the answer is the project narrowing its own declaration — never the
engine choosing.

## D6 — 2026-09-05 — The two engine verbs get built, and the inference census is their acceptance test

`state-categories.md` §6 states the architecture — `move(grain, to_state)` and
`holds(grains, category|state)` — and `grep -rn "def move(\|def holds(" src/` finds one hit, which
is `core/apply.py`'s file mover. **The architecture the milestone rests on has never been built**,
and the census names `holds(...)` as the destination for six of its ten rows without a grain that
creates it.

**The ruling: the two verbs are `every-question-is-asked-of-a-category`'s deliverable, and the
census is its acceptance test** — enumerated in a test that asserts no state literal survives
outside the config reader, rather than carried as a to-do list in a feature record.

**Rejected: let each call site read the category table directly.** That is ten private
`category_of()` lookups agreeing by convention to behave alike, which is a second scoreboard with
ten columns. It is not hypothetical: the `also_done` shim landed in `ready_for.py:304,334` and not
in `model.py:1155`, so `pm ready-for feature` and `check pm` D2 disagree **today** about whether an
`obe` story is finished. One shim, two call sites, already out of step.

**The cost accepted:** a verb layer between `check pm` and the frontmatter is indirection that a
reader of any single D-rule has to follow one hop further. Bought off by the hop being one
function with one docstring, versus ten sites each restating the same reading of the same table.

## D7 — 2026-09-05 — The ledger keeps its frozen keys and gains category keys beside them

**Chris, 2026-09-05:** *"Keep and extend."*

`pm/cli.py:1524-1557` freezes `building` and `reviewing` as literal bucket keys inside JSONL rows
**already written in every consumer tree**, consumed downstream by `report.py:104-112`. Every other
item in the inference census is a rendering or a predicate — change the code and the next run is
right. This one is a data format.

**The ruling: the frozen keys STAY and category keys land beside them.** Old rows stay readable by
old readers, new rows carry both, and the frozen keys are marked deprecated in the row shape with
removal at the next major — the same posture the 0.24.0 deprecation window took.

**Rejected: migrate the keys to category names.** It leaves a reader that must understand two
shapes forever, or requires a one-shot rewrite verb that every consumer runs — and hard rule 8 says
this package cannot run a migration in somebody else's repo. A migration nobody can be made to run
is a migration that never finishes.

**Rejected: read old rows through the CURRENT declaration.** A row written when `building` meant
something is not re-interpretable through a table written later; that is inventing history, and
`pm ledger report`'s `reopens` column already sets the precedent of printing `-` rather than
guessing.

**The cost accepted:** the milestone that exists to remove hardcoded state opinions ships one, in a
telemetry row, dated and deprecated. It is the honest version of the trade — the row is telemetry,
not the engine, and every question the ENGINE asks is a category after phase 7.

## D8 — 2026-09-05 — Everything is just a check: no belt step ever halts, and exit 2 belongs to the reader

**Chris, 2026-09-05, on being shown the input-versus-tree edge:**

> *"I don't understand tree vs input. Everything is just a check. `release` should release on a red
> tree if I want (we mostly wouldn't but why stop someone?)"*

**He is right and this is simpler than the design was.** `state-categories.md` §7 drew the edge
between facts about the INPUT (refuse, exit 2) and facts about the TREE (report, proceed), and P5
then sized the work as *"re-rule 14 halting steps, each under that edge"* — including the genuinely
hard one, whether a red `make gates` is input or tree.

**There is no such edge, because those are not two kinds of step outcome.** They are two different
moments:

| moment | what it is | answer |
|---|---|---|
| **before the walk** | the engine cannot READ its own declaration — a malformed id, an unknown step name, a config value of the wrong shape, an undeclared transition | **exit 2, and nothing walks.** `validate_config`, `plan_defect` and `subject_defect` already do this, before step 1. |
| **during the walk** | a step's `check()` answered | **it is a check. It reports.** Every time, for every step, with no exceptions and no taxonomy. |

So the 14-step re-ruling evaporates: there is nothing to re-rule, because no step decides whether
to halt. **A red `make gates` reports red and the walk continues to `tag`** — and if you want to
release on a red tree, you can, which is Chris's point. The gate told you. `check` is still the
thing that FAILS in CI and pre-push with an exit-code contract for exactly that.

**Rejected: keep the input/tree taxonomy as a per-step ruling.** Fourteen judgement calls is
fourteen chances to draw the line differently, and the second one would be argued from the first
rather than from a rule — D2's reasoning, applied here. It also puts the engine back in the
business of deciding which facts are serious, which is rule 9's whole subject.

**Rejected: halt on a failed AUTOMATIC step, since an action that did not happen is not a check.**
Tempting, and wrong in the same way: a step's postcondition is a check whether the step tried to
perform it or not. `version-sync` that did not write reports *"pyproject.toml still says 0.1.0"* and
the walk continues; the operator reads the scoreboard. Special-casing one kind is the fourth
StepKind arriving as an `if`.

**What the machine becomes**, and it is smaller: `_walk` stops returning at the first non-true step.
It records every answer, prints every line, walks to the end, and returns a **scoreboard**. Exit
codes keep hard rule 6 exactly — `0` every postcondition holds, `1` one or more do not, `2` the
declaration could not be read.

**The cost accepted:** a long run now prints every step's line rather than stopping at the first
problem, so the transcript is longer and the final scoreboard is doing real work. That line is the
mitigation and it has to be good — a warning nobody reads is worse than a refusal.

**And `--skip` goes.** It exists to escape a refusal; with nothing to escape it is ceremony. The
ledger row it wrote was the honest half, and it becomes what a not-true step records.

## D9 — 2026-09-05 — A composition rung's cost is UNKNOWN until the composition opens its own slot, and the criterion says so

G3, from the `every-gate-reports-its-cost` feature review. `verify --plan` joins a rung's
command to a ledger `gate` row **by make target name**, and `gate_costs` only ever holds names
passed to `gdk_gate_log`. The wide rungs are prerequisite-only targets — `precommit: gates
hooks-self-test test`, `milestone: gates hooks-self-test matrix` — with no recipe, so they never
open a slot and `costs` can never carry a key `precommit` or `milestone`. `_ratio` needs both
ends, so it answers `unknown` forever. Measured on this repo, with 47 gate rows across four gate
names:

```
story      make gates      57 ms (FAIL)
feature    make precommit  unknown
milestone  make milestone  unknown
ratio      unknown
```

**The ruling: the code is right and the CRITERION was wrong.** Criterion 3 read *"the row makes
the narrow-vs-wide ratio derivable"*, and the join makes it underivable for the wide half in
every configuration this package ships. `--plan` saying `unknown` rather than inventing a number
is the behaviour this milestone's whole read side is built on, so the honest correction is to the
sentence that overclaimed, not to the renderer that told the truth.

Criterion 3 becomes: *every gate that OPENS A SLOT records name, duration, verdict and census
through one funnel, and `--plan` reports a cost it does not have as `unknown` rather than
deriving one.* The ratio is a follow-up with its own bug: `0.2.0/bugs/a-composition-has-no-slot`.

**Rejected: sum the members' rows.** `precommit`'s members are a make prerequisite list, and this
package would have to parse a Makefile or shell out to `make -p` to learn them — a build tool
invoked to answer a question, in a package whose rule 2 says every gate reads git, markdown and
shell as TEXT. Worse, summing by timestamp window guesses which rows belonged to which run, and a
number assembled from a guess is exactly what `unknown` exists instead of.

**Rejected: a `[gates] precommit` key listing the members.** D1 already rejected this shape for
the tier roster and the reasons carry: a config list beside the Makefile is a second source of
truth that can disagree with the first, and a member listed in config and absent from the target
is a sum over a gate nobody ran.

**The cost accepted:** the milestone ships with the ratio unmeasurable, which is the number the
economics argument is made from — 170x is quoted from a hand measurement rather than from the
ledger this feature built. Named as the gap rather than faked: a ratio derived from an incomplete
denominator would understate the wide half, which is the direction that makes the wrong decision
look right.

## D10 — 2026-09-05 — The test tier is the ladder's bottom rung, and a tier that got slower is a finding

**Chris, 2026-09-05, on a 240-second suite:**

> *"Testing should be DEAD SIMPLE. … An integration test that takes longer than maybe 30s is too
> long. A unit suite should complete in seconds, it's just a code run. … I'm tired of waiting for
> tests forever."*

**The ruling: the `shell` mark IS the tier, `precommit` is the narrow rung, and a tier over its
declared ceiling is a gate failure.**

The mark already existed — derived at collection from what a module's source reaches — and it
already had a job: letting `make matrix` skip spawning modules on three of four interpreters. What
it never had was a TARGET, so the fast half of the suite was unreachable from the command line and
`make precommit` ran all of it after every edit. That is this milestone's own 170x, in the file
that names it.

```
make unit          no subprocess, one process, 7 s      <- after every edit
make integration   a real repo, make, a hook corpus     <- at the close
make test          both                                 <- and at the close
make milestone     everything, every interpreter        <- once
```

**Rejected: a `[tests] tiers` key naming which modules are which.** D1 rejected that shape for the
tier roster and the reasons carry unchanged — a list beside the thing it describes is a second
source of truth, and a module listed in config and absent from the suite is a census that lies.
The mark is DERIVED from source, so a module that starts spawning changes tier on the next
collection rather than on the next audit.

**Rejected: deleting the slow tests.** The conversion is narrow→cheap, never wide→gone. 419 tests
moved back OUT of the slow tier during this work and the pass count never dropped; a speed-up that
deletes coverage is the write-side cardinal sin wearing a stopwatch.

**Rejected: `check budget` in `[checks] all`.** It grades the LAST recorded run of each tier, and
`check all` is the per-change gate — it runs in `precommit`, in a pre-push hook, and inside
`test_makefile_gates`, which spawns `make gates` against this very tree. Nine tests went red for a
timing number that had nothing to do with what they assert. A gate that reddens on somebody else's
clock is milestone risk 2 with a stopwatch, and it is the kind that gets deleted. It runs in
`make milestone`, once, where a regression is a thing to act on.

**The cost accepted, and it is real: the budget is always one run behind.** It reads a `gate` row
rather than taking a measurement, so a tier's number is only as current as the last time somebody
ran that tier. That is why the gate prints the AGE of every row it grades — `7.2s of 20s, measured
12m ago` — because a ceiling reported against a row from last week is a ceiling reported against
last week's code, and a number without its age reads as a fact about the tree in front of you.

## D11 — 2026-09-05 — A callee's exit 2 is UNVERIFIABLE, and a reader that fails mid-walk is one line at exit 2

Q1 and B3 from `docs/reviews/2026-09-05-the-belt-reports-and-finishes.md`, and they are the one
seam where D8's two moments touch. Measured, both:

```
[story:narrow-verified] GATE NOT-TRUE — `agentic-sdlc verify --story …` exited 2 — a CONFIG or
usage error, not a finding, so nothing was decided: [verify] feature must be a string, got 42
[story:story-done] AUTOMATIC DONE — …01-the-ledger-holds-what-a-gate-cost.md is 'done'

$ uv run -q agentic-sdlc release 0.2.0        # devkit.toml: "pyproject.toml" = 42
Traceback (most recent call last):
  …
agentic_sdlc.core.config.ConfigError: [release.version_files] pyproject.toml must be a regex string
EXIT=1
```

The first: a GATE that subprocesses this same CLI folded the callee's exit 2 into NOT-TRUE, the
step's own detail said *nothing was decided*, and the belt then decided — the story flipped `done`
with its narrow check never run. The second: a `ConfigError` raised by a step's `check()` escaped
`main` as a traceback at exit 1, hard rule 6's code for FINDINGS, with the five steps already
walked printing nothing while the ledger row an earlier step wrote had already landed.

**The ruling, Chris's northstar applied twice — everything is a check, the walk always finishes,
and exit 2 belongs to the READER:**

1. **A callee's exit 2 — a config or usage error — is UNVERIFIABLE, never NOT-TRUE.** The
   callee's reader failed, so the question was never asked; that is the third value of `Truth`,
   kept apart from a plain no for exactly this. The walk still finishes (D8): THIS process read its
   own declaration fine, and a fact a subprocess reports is a fact about the tree. Only the callee
   that speaks hard rule 6 — `agentic-sdlc` itself, through `_own_verdict` — gets the ruling. A
   configured `[<operation>.commands]` string is any shell at all, and `make` exits 2 for a failed
   recipe: reading that as "unverifiable" would launder a red gate into the column that says
   nobody looked. `run_command` stays 0-is-true and nothing else.
2. **A `ConfigError` raised inside `main` is reported as one line and the CLI exits 2** — never a
   traceback, never exit 1. `validate_config` reads every key it knows before step 1; a key only one
   step reads is met AT that step, and `walk` catches it there: every line already on the
   transcript is printed, one `[release] REFUSED — step 6/21 'version-sync' (AUTOMATIC): …` names
   the step and the key, the run state is saved, one line goes to stderr, and nothing after it
   walks. A walk over a declaration it cannot read is D8's "before the walk" moment arriving late,
   and it gets the same answer.

**Rejected: fold the mid-walk `ConfigError` into UNVERIFIABLE and keep walking, for symmetry with
rule 1.** Tempting — it makes the two halves one rule — and wrong on hard rule 6: a consumer typo
would then land at exit 1 in a column beside genuine findings, and a consumer's CI would read a
config mistake as drift. Rule 1 is about a SUBPROCESS's reader; rule 2 is about this one, and the
exit code says whose.

**Rejected: read every configured command's exit 2 as UNVERIFIABLE too.** `make` — the one
shipped default, `gate = "make milestone"` — says 2 for a failed recipe. Rule 4's read-side sin,
delivered by a convention this package does not own.

**Rejected: pre-read every config key any step might touch, so nothing can raise mid-walk.**
`validate_config` already reads what it knows; a step's own reader is the authority on the shape
it needs (`_version_files`, `_pin_files`), and a second reader of each key up front is the
second answer this module's docstring refuses. Catching it at the step costs one `try` and keeps
one reader.

**The cost accepted:** a `ConfigError` at step 6 leaves the rows earlier not-true steps wrote in
the ledger. They stay, deliberately — each was a fact about the tree, the tree did not change, and
a machine that un-wrote its own account because a later key was malformed would be rewriting
history (D7's reasoning). And a callee's exit 2 now exits the belt at 1 rather than 2, which reads
as "one or more postconditions do not hold" — true, and the scoreboard's `unverifiable:` column
names which and the row says why.

## D12 — 2026-09-05 — The actions ARE the checks: a belt prints its entry conditions, then writes one status or refuses cleanly

**Chris, 2026-09-05:** *"This tool is essentially a reader/writer. It reads/writes the same
things, in the same places, over and over again. It just echoes state back — it doesn't DO
anything."* And on the belts: *"You say `close feature` and it goes `error: story xyz not
closed`. It doesn't do anything, no feature closed, just a clean error. It wants all stories
under it to be in any matching done state. Maybe they delete the offending stories, maybe they
close them all with other CLI commands. That's the conveyor. The actions ARE the checks. And a
`--force` flag does the action anyway."*

**The ruling.** Every belt — `close story`, `close feature`, `release`, `adopt` — is a printed
checklist derived from the config, followed by AT MOST ONE write: the status of the grain it was
asked about, set to the first state in that kind's `done` list. Every check runs and every
failing one prints, then: all true → the one write; any false → a clean error naming each
failing check and NO write, exit 1. `--force` performs the write over failing checks and the
ledger row says which checks were false. Nothing else is written, moved, bumped, retitled,
pushed or tagged by a belt; what the caller should do next is printed as words.

**What this supersedes.** D8 ("no belt step halts, the walk always finishes") keeps its read
half — every check still runs and reports — and loses its write half: the automatic steps that
performed status flips, version bumps, changelog retitles, pushes and tags are gone. A step is
now a check, or it is not a step.

**Rejected: keep the automatic steps and add `--dry-run`.** A belt that does eleven things
unless you remembered a flag is the opposite of a reader/writer, and every one of those eleven
is a place the machine decides what a move MEANS (rule 9).

**Rejected: a check that halts on the first failure.** One error per run is a loop of runs;
printing every failing condition at once is what makes the caller's next move obvious.

**The cost accepted.** The release is no longer one command from a clean tree to a tag: after
`release <version>` stamps the milestone done, bumping, retitling, pushing and tagging are the
caller's, printed as a list. That is the point: the machine reads and writes the PM tree and
says what it saw, and a human or an agent does the rest on purpose.
