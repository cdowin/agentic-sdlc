---
id: "ms-the-open-issues-close"
kind: milestone
name: The open issues close
status: done
depends_on: []
branch: milestone/2.3.0-the-open-issues-close
mode:
version: 2.3.0
changelog: The open issues close: release refuses a milestone on no plan, pm decide never reuses an id, install --force drops only dead header keys, check pm D15 catches a broken [verify] rung, and the git denylist refuses alias and include routes.
order:
  - "ft-release-and-install-tell-the-truth"
  - "ft-a-decision-id-is-never-reused"
  - "ft-a-fresh-init-locks"
  - "ft-the-denylist-sees-through-an-alias"
  - "ft-check-reads-the-verify-rungs"
  - "ft-small-shapes-hold"
  - "bg-install-force-drops-a-name-the-kept-header-reads"
  - "bg-install-carry-drops-an-indented-line-after-a-retired-name"
  - "bg-pm-decide-takes-its-prefix-from-a-prose-bullet"
  - "bg-denylist-alias-via-include-path-or-config-env"
---

# ms-the-open-issues-close — The open issues close

A triage on 2026-10-01 graded the 14 open issues against the code at 2.2.0. Three were obsolete
or fixed and are closed (#129, #104, #130); #118 folded into #128. This milestone takes the 8 that
are still true. Two are correctness bugs (#127 a false ok, #110 a duplicate id) and go first.
Still open and NOT here, each waiting on a decision: #116 (what the release CI gate asks), #108
(the carried review findings), #117 (nested dispatch attribution).

## Ship criterion

Each issue below is closed by a commit on this branch, with a test that fails without it:
#127, #110, #128, #109, #105, #103, #106, #107.

## Risks

- #128 changes what `install --force` writes into a consumer's hook header. A key the consumer
  set and the new file dropped goes away; it must be named on stderr, never silent.
- #105 widens a guard: a consumer's legitimate `git -c alias.*` call is refused after this.
