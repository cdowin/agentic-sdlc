---
id: st-the-semver-gate-admits-the-next-hotfix
kind: story
feature: ft-a-gate-verdict-is-true-of-the-tree
milestone: "ms-a-consumer-can-take-the-bump"
name: the semver gate admits the next hotfix, not only the first
status: building
owner: agent
depends_on: []
changelog:
---

# the semver gate admits the next hotfix, not only the first

Issue: #27.

`installables/ci-semver-gate.yml:104-106` admits a hotfix only as main's version plus ONE APPENDED
component:

```sh
case "$PR" in "$MAIN".*) rest="${PR#"$MAIN".}"; … legit="hotfix $rest on main's $MAIN";; esac
```

`0.28.4 → 0.28.4.1` passes. `0.28.4.1 → 0.28.4.2` fails, because it does not start with `0.28.4.1.`,
and the done-milestone loop (`:120-146`) matches `version:` or id exactly. Successive hotfixes would
have to nest one component deeper each time. The consumer merged over the red check instead, which is
the gate being routed around.

## Acceptance criteria

1. Also admitted: main is already a hotfix of a done milestone's `version:`, and the PR's version has
   the same length, is identical except for the final component, and that component is greater.
   (`0.28.4.1 → 0.28.4.2` where `0.28.4` is done.)
2. Still refused: a bump that is neither a done milestone's version nor a hotfix under either rule,
   including skipping to `0.28.5` with no done `0.28.5`, and a decrement (`0.28.4.2 → 0.28.4.1`).
3. The admitted line names which rule admitted it (the appended or the incremented hotfix).
4. This repo's `.github/workflows/semver-gate.yml` is re-installed with `install-ci --force`, and
   `installables-current` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | per the existing semver-gate tests' tier (the block is shell) | a table of (main, PR, done versions) → verdict | amend. Search first |
| 4 | unit | tests/test_install.py byte-current | yes |

## Semver

Patch: the gate admits a legitimate input it wrongly refused, and nothing it admitted before is refused.
