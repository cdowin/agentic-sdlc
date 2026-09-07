Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ft-identity-lives-in-frontmatter  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-07 — An undeclared kind: is a FINDING, not exit 2

**The story said exit 2; it ships as a finding at exit 1, and the story was wrong.**

Hard rule 9 draws the line at *is this reading what the project declared, or deciding what the
project should do*. A malformed DECLARATION is exit 2 — `[pm.states.epic]` naming a category that
does not exist is a config the tool cannot read. A grain document saying `kind: epic` is not a
declaration; it is **tree content**, and the tool can read it perfectly well. What it cannot do is
key on it.

The precedent settles it: **D4** reports a `status:` the project never declared as a FINDING at
exit 1, off the same shape of question, and has since 0.1. An undeclared `kind:` at exit 2 would
mean two facts of one kind answered with two different exit codes, and a consumer's hook reading
exit 2 as "your devkit.toml is broken" would be sent to the wrong file.

**Rejected:** exit 2, as the story asked. It would make one bad grain document — which a merge can
produce — abort every verb in the tree, including the ones that would show you which document it
was.

The line reads: `<path> declares kind 'epic', which this project does not have (milestone feature
story bug) — it was SKIPPED by this scan`. Reported by name, counted as skipped, exit 1.

## D2 — 2026-09-07 — An id is unique across the whole tree, not per kind

**The story said "uniqueness is per kind"; it ships as uniqueness across the tree.**

The story's reasoning was that ids are kind-prefixed (`ms-`, `ft-`, `st-`, `bg-`), so `ft-x` and
`st-x` can never collide and a per-kind rule loses nothing. That reasoning depends on a prefix the
tool does not mint: `pm new feature 0.1 alpha` stamps `id: 0.1/alpha`, with no prefix, because
**the filename and the id are the author's** — which is this milestone's own thesis. The migration
minted prefixes; `pm new` does not, and making it do so would be the tool having an opinion about
a name.

So two kinds CAN share an id, and `grain_index` is **one dict**. A collision there is not cosmetic:
`setdefault` keeps the first document read and every other one is addressable by nothing, which is
rule 4's first sin. A per-kind rule would pass over exactly that case.

**Rejected:** per-kind reporting, as the story asked. It is only safe under a prefix convention the
tool does not enforce, and a rule that is correct only while a convention holds is a rule that goes
silently wrong the day it does not.

`duplicate_ids` therefore reports any id claimed twice, across kinds included, naming every file
that claims it. Uniqueness stays a GATE FINDING and never a runtime lock — an allocator needs a
counter and a git repo has none (D4 on the milestone), so two agents on two branches produce a
merge conflict a human can see rather than a duplicate id nobody can.
