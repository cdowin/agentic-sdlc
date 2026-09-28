---
id: ft-the-allowlist-judges-the-repo-a-command-touches
kind: feature
milestone: "ms-the-rules-hold-everywhere"
name: the allowlist judges the repo a command touches
status: building
reviewed: docs/reviews/2026-09-28-0.16.0-allowlist.md
depends_on: []
consumed_by: []
changelog: The git allowlist judges `git -C ~/…` and `git clone <url> <dir>` by the repository they touch, allows check-ignore, check-attr and var, and a refusal of a command naming an outside path names the absolute `-C` route.
---

# the allowlist judges the repo a command touches

Issues: #81.

The scratch-probe exemption allows git against another repository when every `-C` target is
an absolute path outside this checkout. Two spellings missed it and the refusal hid it, so the
operator committed through the GitHub API instead.

## Decided (do not re-plan)

All in `src/agentic_sdlc/repo/installables/cc-git-allowlist.sh`; re-install with
`install-hooks --force`. bash 3.2, payload parsed with bare `python3 -c` (rule 1).

- **`~/` is absolute.** A `-C` or init target starting `~/` (or exactly `~`) is judged as
  `$HOME/…`. `$HOME/` already passes; keep it.
- **`clone` is judged by its destination.** `git clone [opts] <url> <dir>`: when `<dir>` is an
  absolute (or `~/`) path outside every checkout, it is a scratch probe and passes. A clone with
  no `<dir>` or a relative one is judged as today (blocked). Options that take a value
  (`--branch`, `-b`, `--depth`, `--reference`, `--origin`, `-o`, `--config`, `-c`,
  `--separate-git-dir`) are skipped when finding the positionals; `--separate-git-dir` and
  `--template` count as location flags and keep the block.
- **Three reads join the stock `ALLOW_SUBCOMMANDS`:** `check-ignore check-attr var`. Also update
  the header fallback line that repeats the stock value.
- **The refusal names the route.** When a blocked command's segment carries a path outside this
  checkout, or a `-C` whose target starts with `$`, the `instead:` line reads: `for another
  repository, spell its absolute path: git -C /abs/path <verb> …` (and, for `$`, that the hook
  reads the typed text so a variable is not expanded).
- Corpus rows in the hook's `--self-test` for each: `-C ~/x` passes, `clone <url> /abs/out`
  passes, `clone <url> rel` blocks, `check-ignore -v f` passes, and the two refusal texts.

## Ship criterion

- The five commands in #81's table replay to exit 0, 0, 0, 0, 0 (the fourth, the clone to an
  absolute path, now passes).
- `bash cc-git-allowlist.sh --self-test` passes with the new rows; `check hooks` green here.

## Proof budget

<!-- Roughly how many test cases this feature should cost, written before it is
     built and compared after. Name the tier and the existing module they land
     in; say what the suite already checks and why that is not enough. -->

  cases: 6 corpus rows, no new pytest case
  tier: the hook's own --self-test (replayed by check hooks)
  lands in: src/agentic_sdlc/repo/installables/cc-git-allowlist.sh
  what already covers this: the corpus holds the -C absolute rows; none for ~, clone or the refusal text.
