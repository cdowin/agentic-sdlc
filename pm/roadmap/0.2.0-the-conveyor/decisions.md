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
