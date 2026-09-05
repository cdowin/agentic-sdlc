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
