---
id: bg-adopt-unarmed-reads-one-config
kind: bug
milestone: "ms-the-loop-proves-itself"
name: adopt unarmed ignores global and worktree git config
status: open
caused_by:
changelog:
---

# adopt-unarmed-reads-one-config

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-adopt-unarmed-reads-one-config` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR: `adopt` prints `[adopt] unarmed: git core.hooksPath is unset` and exits 1 when git DOES see `core.hooksPath = tools/hooks`. Probe: scratch consumer after `init`, hooksPath moved to `GIT_CONFIG_GLOBAL` or to `git config --worktree` (extensions.worktreeConfig) — `git config --get core.hooksPath` prints `tools/hooks`, adopt says unset. A false finding line (rule 4 shape).

## Root cause

`belts._unarmed` reads only `<common-dir>/config` via `_hooks_path`; it ignores global/system config, `config.worktree`, `include`/`includeIf`, and the `GIT_CONFIG_*` env. It also imports the private `verify.cache._common_dir` and `install._is_executable`.

## Fix

Read hooksPath the way git resolves it, or narrow the claim: when the local file does not set it, say `core.hooksPath is not set in .git/config` (a fact) instead of `is unset`. Add the worktree/global cases to the parametrized test.
