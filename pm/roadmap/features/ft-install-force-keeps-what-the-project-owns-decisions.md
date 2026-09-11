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
