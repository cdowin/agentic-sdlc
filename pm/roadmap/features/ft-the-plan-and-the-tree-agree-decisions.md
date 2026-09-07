Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# 0.3.0/the-plan-and-the-tree-agree The plan and the tree are cross-checked, and ROADMAP.md retires — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-06 — An unverifiable order entry is SKIPPED and REPORTED, never resolved by the resolver

Two feature reviews of this milestone pulled OPPOSITE ways on one question, which is what makes it
worth a decision rather than a fix.

`pm retire` deletes a finished milestone's record while its row survives in `order` on purpose —
that surviving row is the half of `ROADMAP.md` that was real. So after a retirement, an entry whose
work SHIPPED is byte-for-byte indistinguishable from one nobody has written yet: in both cases no
milestone claims the version.

- **Review F1** said an unverifiable entry must not be read as unshipped: doing so rolled the
  current release BACKWARD after a retire, and R5 then demanded a version regression.
- **Review B1** said an unverifiable entry must not be stepped over either: doing so answers with a
  release further down the plan than the tree can support.

**Both are right, and the tree cannot tell them apart.** Position does not separate them —
`last_shipped_index` also stops seeing the retired release, so "before the last shipped entry"
degrades the moment it is pruned.

**So the resolver SKIPS it and the GATE reports it.** `current_release` walks past an unverifiable
entry, and R1 names it UNBOUND on every run — the skip is never silent. That keeps `pm retire`,
the ledger and the release belt working for every tree that prunes, and puts the ambiguity where a
human can act on it instead of where an engine guesses at it.

Rejected: blocking on it (B1's literal fix). It breaks `retire` for everyone, to protect against a
tree that R1 is already reddening.

Rejected: resolving it by position. It reads correctly today and stops reading correctly the moment
the entry before it is retired, which is the same class of latent wrongness with a longer fuse.

Rejected: having `pm retire` drop the entry from `order`. Then nothing outlives the milestone, which
is exactly what retiring `ROADMAP.md` was careful not to lose.
