---
id: 0.19.0/install-runners/sandbox-home-and-project-file
feature: 0.19.0/install-runners
milestone: "0.19.0"
name: A headless run gets a self-destroying HOME and project.godot comes back
status: done
owner: developer
depends_on: []
---

# A headless run gets a self-destroying HOME and project.godot comes back

## Goal

A headless run gets a per-run self-destroying sandbox HOME, and a `project.godot` the engine
re-serialised comes back unless the consumer deliberately edited it.

## Port from consumer_a `tools/dev/_common.sh` (`271baf4ec`)

`consumer_a_sandbox_home`, `consumer_a_on_exit` + `_consumer_a_run_exit_hooks`,
`_consumer_a_destroy_run_home`, `_consumer_a_reap_stale_run_homes`, `consumer_a_sandbox_tmpfile`,
`consumer_a_timeout_is_hang`, `consumer_a_run_bounded`, `_consumer_a_snapshot_project_file`,
`_consumer_a_normalize_project_file`, `consumer_a_restore_project_file` → `gdk_*`. The restore
compares normalised content against `git show HEAD:project.godot` and leaves a real edit alone,
printing one line either way. consumer_b's `consumer_b_sandbox_home` / `consumer_b_run_bounded` are the ancestor —
the ported shape must cover both callers.

## Gotcha

`cc-godot-sandbox.sh` (an installable) refuses a bare engine boot outside the sandbox function;
the function NAME it admits must be the new `gdk_sandbox_home`, with the consumer-prefixed names
gone — update the hook's admit list and its corpus in the same story.

## Verification

`make test`, `make gates`, `bash installables/cc-godot-sandbox.sh --self-test`.

## Commit prefix

`feat(0.19.0/install-runners/S2):`

## Size

m

## Done

done: 1b3ee28 — `_gdk_reap_stale_run_homes`, `_gdk_snapshot_project_file`,
`_gdk_normalize_project_file`, `gdk_restore_project_file`, `gdk_timeout_is_hang`;
hook roster defaults to `gdk_rebuild_import_cache` (blocked) with
`gdk_sandbox_home` as the named door (allowed), `SANDBOX_FUNCTION` kept as the
prefixed-name escape hatch. Corpus 13/13 stock, 15/15 armed; library self-test
29 cases, 3 mutants proven red; 741 passed, gates PASS.
