Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# 0.3.0 the bump explains itself — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-06 — The bare-repo bug ships OPEN, named, with what is known and what to run next

`0.3.0/bugs/the-suite-can-flip-the-host-repo-to-bare` is **not fixed and ships open.**

Twice during this milestone the real checkout acquired `core.bare = true` and every git command in
the working tree began failing. No commits were lost either time and `git config core.bare false`
restored it whole, but a suite that can leave the host repository unusable is a hazard.

It was NARROWED rather than diagnosed. Each git-spawning module was run alone against this
checkout, hashing `.git/config` before and after: `test_conveyor_adopt`, `test_fresh_project`,
`test_check_hooks`, `test_hooks_payloads`, `test_makefile_gates`, `test_gate_roster` — none flips
it. All occurrences happened while SUBAGENTS were running their own test processes against this
same worktree, so a lock/rename race on `.git/config` is the shape that fits, and a serial run
cannot reproduce it.

**Shipping it open is the deliberate call.** Writing a cause that has not been established would be
worse than the open finding: the bug record would then say something false, which is rule 4's
second sin wearing a fix. What ships instead is what is KNOWN — the six modules ruled out, the
concurrency correlation, and a next step that reproduces under the condition that produces it.

Rejected: guessing at the interrupted-`git config` explanation and closing it. It is the leading
hypothesis and it is still a hypothesis.

Rejected: holding the milestone for it. It is a defect in the SUITE's interaction with a shared
worktree under parallel dispatch, not in anything this release ships to a consumer; no consumer runs
two agents against one checkout of this package. Holding eleven features for it would trade real
delivered value for an unbounded investigation.

## D2 — 2026-09-06 — 0.3.0 is MINOR and BREAKING, and rule 7 has no tier for a retired config VALUE

Hard rule 7: *patch = same interface; minor = a new verb, flag, config key or output shape; major =
a consumer Makefile or hook must change to survive.*

**Measured, not argued.** No verb, flag, `Makefile.devkit` target or installable was withdrawn:
HEAD's CLI surface is a strict superset of v0.2.0's, the target and installable sets are identical,
and a consumer's existing `ROADMAP.md` survives byte-identical (this release stops WRITING to it, it
does not delete it). So rule 7's major clause never literally fires — **no consumer Makefile and no
hook must change.**

**One thing does break.** A repo naming `D8` in `[pm] checks` — a config the v0.2.0 installable
itself invited — goes `check pm` exit 0 → **exit 2**, `check all` → 2, `adopt` → 1. Their
`make check` fails until they edit `devkit.toml`. That is rule 7's SURVIVAL test, landing on the
surface rule 5 calls the canonical consumer-owned one.

**Rule 7 has no tier for a retired config VALUE.** Its minor list is four ADDITIONS; an interface
that SHRANK is on neither list. The gap resolves on the number rather than the tier name: this
package is `0.x`, where the minor slot is how breaking is expressed, and calling this MAJOR means
`1.0.0` — asserting a stability this package does not intend, while `0.4.0` is already on the plan.

**So: 0.3.0, and the CHANGELOG says BREAKING at the D8 line**, because a consumer who reads only
the release note must not have to infer it from a sentence five lines in. The exit-2 message names
R5 and says where the rule went, which is the whole reason D8 was retired BY NAME rather than
silently dropped.

Carried to 0.4.0: rule 7 should gain a clause for a retired key or value, so the next one is not
argued from first principles.
