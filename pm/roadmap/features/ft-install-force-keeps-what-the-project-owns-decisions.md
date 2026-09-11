Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ft-install-force-keeps-what-the-project-owns install --force keeps what the project owns — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-11 — install --force carries the existing project-config block into the new body

When the project-config block exists in both the installed file and the packaged body, `--force`
writes the packaged body with the installed block in its place, byte-for-byte, and prints one line
saying it kept the block. When either side has no block, `--force` writes the packaged file whole,
as before.

**Why this does not break rule 3.** The rule is that a write touches only what it was asked to touch,
and that an installer writes a whole file or refuses by path. This is still a whole-file write. What
changes is which bytes the kit claims. `config_block_span()` already draws that line: `--diff` and
`installables-current` both treat the block as the project's ("differs ONLY inside its project-config
header"). Overwriting it under `--force` is the inconsistency. The installer was the one reader that
disagreed with the other two about who owns those bytes. `body_of()`'s "no substitution and no
template" stays true of the PACKAGED body. The splice is not templating, because no value is computed;
the project's own bytes are carried across.

**Rejected: a `--keep-config` flag, with plain `--force` still lossy.** The lossy path would stay the
default, which is the one both consumer bumps took. A flag you have to know about is rule 11's failure
mode.

**Rejected: refusing a header-only difference under `--force`.** It is safe, but it leaves the
consumer hand-applying the body hunks, which is the chore the installer exists to remove.

Chris, 2026-09-11: go with the recommendation.

## D2 — 2026-09-11 — the markdown project-config block is the text fence, not the section

From the spec scout, B2 (`docs/reviews/2026-09-11-0.8.0-spec-review.md`). The markdown block grammar
(`install.py:486-487`) closes the block at the next `^## `, so in every agent brief lines ~15-38 are
"the project's". That span holds the kit's own first instruction ("Run `agentic-sdlc dispatch …`",
line 16 in 10 briefs), each role's intro paragraph and the `<!-- BEGIN role-verbs -->` marker. With D1's
carry, the vehicle feature's rewrite of those kit lines could never reach an existing consumer. The
ship criterion's first bullet (never `command not found`) and its second (the header byte-identical)
would contradict each other.

**For a markdown installable, the project-owned bytes are the ```` ```text ```` fence inside
`## Project config`: the fence and its contents, nothing else.** The heading, the dispatch sentence
and the prose in that section belong to the kit, and `--force` updates them. A brief with no such fence
has no project-owned block. The shell hooks' grammar is unchanged. `--diff`'s header-only verdict,
`installables-current` and the `--force` carry all read the ONE narrowed span, so they cannot
disagree.

**Rejected: keep the section span and print a line when a carried block differs from the packaged
one.** That is honest, but it leaves every existing consumer's dispatch sentence stale until each one
hand-merges. It is the chore this feature exists to remove, moved one level down.

**Cost, accepted:** a consumer who edited PROSE in the section, outside the fence, now reads as drift,
and `--force` replaces that prose. That is the correct reading: those values were never the
project's to keep. Values belong in the fence. The Project config heading's wording ("yours to edit
after install") is narrowed to say which part is yours.

Orchestrator decision under Chris's standing "go with the recommendations" for 0.8.0.

## D3 — 2026-09-11 — three edges the review found, settled

From `docs/reviews/2026-09-11-0.8.0-install-force-keeps-what-the-project-owns.md`, landed in `f01ab43`.

1. **A CRLF file's kept block is written LF, and the line says "line for line", not "byte for byte"
   (M5).** The packaged body is LF, and a file with mixed line endings is worse than either. The Ship
   criterion's "byte-identical, or the decision says why not" is this sentence. The kept VALUES are
   identical; only the terminators follow the packaged file.
2. **A hook header line that is not blank, a comment, an assignment or an array continuation means
   the file has no block (M4).** For example `[ -n "$CI" ] && X=1`. The belt then calls the file
   `differs`, and `--force` writes it whole, saying plainly `wrote`. Carrying a line the grammar cannot
   read would be computing, not carrying (D1). No shipped header, no header in this repo and no
   fixture has such a line.
3. **A kept header that lacks a name the packaged one declares still PASSES `installables-current`,
   and the line names the missing name (M6).** It is a named line, not a failure, because the project
   owns that block and may omit a key on purpose. A failure would push consumers to take the stock
   value in order to go green, which is the overwrite this feature removed.

Orchestrator decision under Chris's standing "go with the recommendations" for 0.8.0.
