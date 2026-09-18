---
id: "ms-the-filed-issues-are-answered"
kind: milestone
name: the filed issues are answered
status: done
depends_on: []
branch: milestone/0.14.0-the-filed-issues-are-answered
mode:
version: 0.14.0
changelog: **The filed issues are answered.** `make pm ARGS=…` takes names with `(`, `,` and quotes; a milestone branch under the agent prefix is refused; one lane over several stories is one ledger row; the dispatch preamble names the read verbs and the review grammar; `install-ci` reads `[pm] version_file`; and the loop reviews each lane as it merges.
order:
  - "ft-a-surface-says-what-it-means"
  - "ft-a-milestone-starts-and-a-lane-counts-once"
---

# 0.14.0 — the filed issues are answered

**A small fix release from the issues open on 2026-09-18.** Chris: *"one feature, maybe 2 … let's
just get these done."* Low ceremony: two lanes in parallel, `make unit` in each, one review pass.

    #60 #61 #63 #51  → ft-a-surface-says-what-it-means
    #52 #59 #49      → ft-a-milestone-starts-and-a-lane-counts-once
    #62              → not this package: `story_destination_scan.sh` is a consumer script (rule 8)

## Mode

PARALLEL, two lanes in `tools/dev/agent-worktree.sh` worktrees. The lanes share no file except
`README.md` and `devkit.toml`'s seed, which merge cleanly.

## Ship criterion

Every feature's criterion holds, `make milestone` is green, and each issue above is closed citing a
hash.

## Risks

- #60 changes an installed Makefile recipe every consumer runs; a regression there breaks `make pm`
  for everyone. Its test must run the real recipe once.
- #52 adds a gate key; the seed test holds its default.
