Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ms-the-rule-reaches-the-work  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-07 — a parent does not close over unresolved children

**A grain nested in a parent must reach `done` before that parent closes.** Every kind, every level,
unconditionally. When a milestone is done, everything under it is done, recorded and durable: what
the record says it did is what is written and committed, and there is no third state where a grain
sits under a shipped release and nobody owes anything for it.

The tool is OPINIONATED here, and that is deliberate against rule 9. Rule 9 governs what a move
MEANS and what should happen next — the project declares its states and the tool reads them. This is
not that. This is what CONTAINMENT means, and containment is the one thing the tool already owns:
`[pm.contains]` is the tool's mapping, not the project's, and a parent that closes over an open child
makes its own census a lie, which is rule 4.

**Rejected: a per-grain opt-out field.** `fix_milestone:` was exactly this — a second field saying
"nested here, but not this milestone's problem". It is the reason the release gate could not fail for
four releases: the opt-out defaulted to opted-out, silently, and nothing said so. A field that
exempts a child from its parent is a second scoreboard wearing a smaller word, and 0.4.0 retired V6
for the same shape. Any future version of this idea — a `blocking: false`, a `deferred:` — is the
same rejection.

**Rejected: a parking-lot milestone.** Considered as the home for work you want to keep but not
commit to. It adds a container whose only purpose is to not be a container, and every grain in it
would need the same "does this one really gate?" question the field forced. **The pool already is
the parking lot**: bugs live in their own directory, and a bug that declares no `milestone:` is
unattached by construction.

**So the opt-out is the binding, and it is an act with a verb.** `pm remove <milestone> <bug>` clears
`milestone:`; the bug returns to the pool, gates nothing, and is COUNTED there — `N bug(s) attached
to no milestone`, silent at zero (rule 11). Declining to fix something now is a diff somebody can
read, not a field somebody has to remember to check.

The cost is a backfill: seven bugs are unresolved under `ms-0.3.0` and `ms-0.4.0`, both shipped. That
is the evidence the gap was real, and it is recorded on
`bg-a-bug-is-a-grain-nested-in-a-parent`.

## D2 — 2026-09-07 — a retired FIELD is drift, not a config error

`bg-a-bug-is-a-grain-nested-in-a-parent` specified `check pm` naming surviving `fix_milestone:` and
`caught_in:` **at exit 2** — "the way every retired key in this package is named". It ships as a D11
DRIFT finding at exit 1 instead.

Every retired thing named at exit 2 today is a CONFIG key in `[pm] checks`. Rule 9 draws the line
there and not by analogy: *a malformed declaration is refused at exit 2 — reading; a fact about the
tree is reported and the caller decides.* A retired field sitting in a bug document is a fact about
the tree, the same shape as D4's undeclared status, which is exit 1. Exit 2 would also make a
consumer's whole `check pm` unrunnable — no drift report at all, on any rule — until they had
hand-edited every legacy bug, and a gate that refuses to grade the other 364 things is worse than one
that names this among them.

**Rejected: both, on a flag.** A rule whose severity is configurable is a rule whose census cannot be
compared between two trees, and D9/D10's opt-IN is a different thing — those encode a flow a project
may not run. Every project runs containment.

**Also decided here: D3 RETIRES into D11 rather than sitting beside it.** D3 warned on one pair
(milestone over feature) and could not redden a gate; D11 asks the same question at every level and
fails. Keeping both would put two rules on one byte, which is the second scoreboard this milestone is
named for. `RETIRED_CHECKS['D3']` names where it went, so a consumer config still listing it is told
rather than silently ungated — the same treatment D8 got when it became R5.

## D3 — 2026-09-07 — the remote reader reads refs and never spawns

`ft-the-branch-exists-on-the-remote-from-the-first-commit` asks the pressure line to carry unpushed
commits — *"count and the oldest one's age"*. It ships as a REF COMPARISON with no count and no age.

The first implementation ran `git rev-list --count HEAD --not --remotes` and `git log --format=%ct`.
It worked, and the suite failed 235 cases in the `not shell` tier by nodeid, each saying *tried to
spawn a process*. That is correct and it is hard rule 2: `census` is called by every `pm` write and
by `check pm`, so a git call there puts a subprocess on the hot path of a verb whose whole contract
is that it boots nothing and is safe in parallel. **Rule 2 has no fast path**, and the tier
derivation is what noticed — prose would not have.

So `remote.py` reads `.git/HEAD`, `.git/refs/`, `.git/packed-refs` and `.git/config` as text. That
answers *published* and *in sync* exactly. It cannot answer HOW FAR ahead without walking the commit
graph, so **it does not answer it** — the same posture as `verify --plan` printing `unknown` rather
than a guess (rule 11).

**Rejected: compute the count only on the belts, and leave the census cheap.** Two readers of one
fact, disagreeing about precision, is the second scoreboard this milestone is named for.

**Rejected: cache the count.** Hard rule 2 forbids starting a cache, and a stale count is worse than
no count — it is rule 4's lie about the one thing this feature exists to tell the truth about.

The line lost some resolution and kept its job: *is this work anywhere but here.* Five hours of
0.5.0's commits were not lost for want of a NUMBER.

## D4 — 2026-09-07 — rule 1 names the surface its reason protects

Hard rule 1 said *"Stdlib only, forever… A consumer's hook must never break on a transitive
dependency."* **The reason is true for one half of the package and not the other, and the rule did
not say which** — so it read as a blanket technical claim, and every argument about it was had
against the wrong constraint.

**Where it holds absolutely:** `tools/hooks/cc-ledger-subagent.sh` and its siblings parse their
payload with bare `python3 -c` — a consumer's system interpreter, no managed environment. A
transitive dependency there is a broken commit on somebody else's machine. Non-negotiable.

**Where it does not:** the package itself runs through `uvx --from …` / `uv run`, which resolve
declared deps into an isolated env. Cold-start cost is real; *"a consumer's hook breaks"* is not the
thing that would happen.

**The audit — each candidate, and the rule that actually blocks it:**

| candidate | blocked by | why |
|---|---|---|
| PyYAML | rule 3 | reserialises; `pm` must preserve every other byte, line endings included |
| ruamel.yaml | rule 3 | round-trips comments, but guarantees SEMANTIC round-tripping, not byte-exact |
| a CLI framework (click, typer) | rule 6 | output line shapes are contract and consumers grep them |
| a validation library (pydantic) | nothing — and unnecessary | `check pm` already IS the validator |

**So the one live trade is rule 3's, not rule 1's.** Relaxing byte-exact to semantic preservation
would delete ~165 lines of hand-rolled frontmatter I/O in `model.py` — `set_list_field` alone is 70,
and it is the function that produced this milestone's scalar-vs-list defect
(`bg-pm-set-writes-a-scalar-its-own-gate-refuses`). **That trade is not taken here** and is recorded
so the next person argues it against rule 3, where it lives.

**Rule 1's NUMBER does not move and what it permits does not change.** Roughly 600 citations depend
on the ordinals; the constraint section of this milestone's brief forbids renumbering. Only the
sentence got more specific.

## D5 — 2026-09-08 — a warning fires only where an answer exists

**`check pm` U5 names a grain whose current state was arrived at with no disposition, so the
operator can go back and answer it.** Its own sentence is the instruction: *"re-running the move with
the answer its state declares records one, and `pm vocabulary` prints what each state asks."*

**Found on this tree, closing this milestone:** `devkit.toml` declares no `[pm.arrive.milestone.*]`
section at all, so `ms-the-rule-reaches-the-work` sat at `building` with nothing to answer and U5
named it anyway. `pm vocabulary` prints no fork for a milestone. Following the instruction is not
merely tedious, it is impossible — and the milestone being named is the one that shipped
`ft-a-warning-is-actionable-where-it-fires`, whose whole argument is that a warning nobody can act
on where they are standing is a defect rather than information. 351 of 359 warnings on a real
consumer tree, one layer in, on the surface that measures the others.

**The ruling: a state that declares no answers has nothing to be unanswered about.** `answer: none`
is then the COMPLETE record of that arrival, not a gap in it. U5 asks `[pm.arrive.<kind>.<state>]`
whether any answer is typed, and stays silent where none is.

**The rejected alternative: declare `[pm.arrive.milestone.*]` here and leave the rule alone.** It
would have made this tree green and left every consumer's tree wrong — the seed ships arrivals for
`feature` and `story` only, so a stock adoption hits this on its first milestone. It also inverts
which way the evidence points: the tree was not missing a declaration, the rule was asking a question
of a state that had never been given one. Turning a rule off is a `pm decide` (CLAUDE.md,
self-hosting); so is narrowing one, and this is the narrowing.

**What did NOT change:** U5 still names a grain, never a count, and still fires on a state that DOES
type answers — `test_a_state_that_asks_nothing_has_nothing_to_be_unanswered` differs from
`test_a_bare_move_is_allowed_and_NAMED` in exactly one thing, whether the state declares an answer,
and the two run on the same tree with the same missing row. The three cases that already covered U5
were themselves running on a fixture that declared no arrival at all, which is why nothing caught
this: **the rule was being proven on precisely the trees where it should have stayed quiet.**
