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
