Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# 0.3.0/the-ledger-binds-to-the-current-release The ledger belongs to the current release, not to the one in-progress milestone — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-06 — The in-progress fallback stays, and the spec's 'still refuses' is narrowed

The ship criterion says *"A tree with no `order` yet still refuses, with a message naming
`pm order` — the one honest reason left."* Taken literally that refuses **every gate cost row on
every consumer that has not adopted the plan**, on the bump — a tree with a `building` milestone
and no `releases.md` records nothing where today it records fine. That is a breaking change
wearing a minor version, and it is milestone risk 1 in another costume: a rule that reddens every
fresh consumer is undone within a release.

**So the resolution is: the plan first, the single in-progress milestone as a fallback, and the
refusal only when neither answers.** The criterion's actual goal — *"never refused for want of an
in-progress milestone"* — is fully met: none and several both stop being refusals the moment a
plan exists, which is the bug this feature was filed for. What is narrowed is the second sentence,
and only for a tree that has no plan at all, where the fallback is exactly today's behaviour.

Rejected: refusing literally as written. It converts an existing, working path into a refusal for
a consumer who has done nothing wrong, to buy a purity the criterion did not ask for — the
criterion asked that a STATUS stop being the axis, and it has.

Rejected: dropping the refusal entirely. A tree with no plan and no milestone in progress has
genuinely nowhere to file a row, and saying so while naming `pm order` is the honest answer.
