---
id: 0.4.0/identity-lives-in-frontmatter/01-a-grain-reads-its-id-and-kind-from-its-own-frontmatter
feature: 0.4.0/identity-lives-in-frontmatter
milestone: "0.4.0"
name: id and kind come from frontmatter, and the path is not consulted
status: building
owner: claude
depends_on: []
---

# id and kind come from frontmatter, and the path is not consulted
A grain document says what it is. `id:` is a kind-prefixed slug and `kind:` is one of the kinds the
project declares, and neither is derived from where the file sits. The path still holds the files;
nothing interprets it.

This story makes the location UNINTERPRETED. `0.4.0/the-pools-are-the-tables` then moves it.

## Acceptance criteria

1. `kind:` is read from frontmatter. A `kind:` the project does not declare is **refused by name**,
   naming the kinds it does — a fact about the INPUT, so exit 2.
2. `id:` is read from frontmatter, and no code path derives an id from a path or joins an id onto
   one. A grain whose `id:` disagrees with its location is simply what it says.
3. A grain document with no `id:` or no `kind:` is reported by `check pm`, by path. It is not
   guessed at from the slot it sits in — that is the derivation this feature deletes.
4. **Slug uniqueness within a kind is a `check pm` FINDING** naming every file that shares a slug.
   The same slug in two different KINDS passes: uniqueness is per kind. Never a runtime lock and
   never auto-resolved (D4) — two agents on two branches produce a merge conflict a human can see
   rather than a duplicate id nobody can.
5. **V2 retires BY NAME.** It exists only to keep `id:` and the path in agreement, and there is no
   longer a duplication to police. A consumer whose `[pm] checks` still lists it is told where the
   rule went, through `RETIRED_CHECKS` — never "unknown rule", which reads as a typo and silently
   ungates.
6. The id grammar is a kind prefix plus a slug, and it is one grammar with one refusal matrix
   (SDLC § 5) — enumerated where the grammar lives, not per surface.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | unit | `test_pm_gate.py` — an unknown `kind:`, and each field absent | new; the gate roster is the pattern |
| 2 | unit | V2's cases INVERT: a grain whose id disagrees with its path is read by its id, not repaired | amend — they prove the opposite today, so they cannot pass for the old reason |
| 4 | unit | two grains of one kind sharing a slug (finding), and two kinds sharing one (silent) | new |
| 5 | unit | `test_pm_scaffold.py::test_a_retired_rule_is_not_a_silently_accepted_name` already holds the retired roster | amend — add V2 |
| 6 | unit | the grammar's own matrix, beside `segment_is_literal`'s | amend the grammar's matrix, per SDLC § 5's 2026-09-05 amendment |

## Out of scope

Where the files sit — `0.4.0/the-pools-are-the-tables`. Collapsing the resolvers — story 02. Any
binding field — `0.4.0/binding-is-a-field`.
