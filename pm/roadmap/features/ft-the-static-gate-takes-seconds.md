---
id: ft-the-static-gate-takes-seconds
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: the static gate takes seconds
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the static gate takes seconds

Issue: #98. A consumer measured `make check` at ~94s wall (35 gates; ~370s serial), run three
times per edit (orchestrator, pre-commit, pre-push) plus once per `close story`. Measured here
on 2026-09-30: `uvx --from git+…@v0.17.0 agentic-sdlc` costs 0.95s per call at load 29; the
installed binary costs 0.06s. Target: `make check` under 10s on an unchanged tree for a
consumer, under 2s here; under 30s on a changed tree.

## Decided (do not re-plan)

- **Each static gate is reused by its input hash.** Every devkit gate `check all` runs declares
  the path prefixes it reads (pm: the roadmap dir + devkit.toml; doc: the doc roots; shell: the
  shell census; hooks: tools/hooks + the hook installables + settings; grain-shape: the roadmap
  dir). A PASS is recorded against the hash of exactly those inputs (+ this package's version
  and the gate's config section), using the SAME cache machinery `verify` uses
  (`verify/cache.py`; do not write a second one). A reused gate prints its normal PASS line
  with `; reused — green at <ts> on inputs <short>`. A FAIL is never reused.
- **`[gates] extra` targets may declare inputs**: `[gates.inputs] <target> = ["pm/", "tools/x.sh"]`,
  a GATE key (stock: none declared = the target always runs, exactly as today, rule 5). A
  declared target is reused the same way. The target's own script belongs in its inputs; the
  seed's comment says so. This is how a consumer's scans stop re-running on an unchanged tree.
- **Self-tests run when the hook changes.** `check hooks`' corpus replays are part of its gate,
  so input-hash reuse skips them on an unchanged `tools/hooks/`; CI (a fresh checkout, no local
  ledger) always runs them. `check hooks` must not replay a hook whose bytes did not change
  when the gate as a whole re-runs for another hook's change: per-hook reuse inside the gate.
- **One reuse across every caller.** Orchestrator, `prepare-commit-msg`/pre-commit, `pre-push`,
  the stop gate and the belts all call `make check`; the reuse lives beneath it, so they share
  it with no caller change. `ledger.local.jsonl` is the store, as for verify.
- **The pinned tool install is `ft-the-kit-ships-as-a-locked-wheel` (#101)**, not this feature.
- Probes (rule 4): an edit inside a gate's inputs re-runs that gate; an edit outside reuses it;
  a config change to the gate's section re-runs it; a devkit version change re-runs all; a
  planted FAIL is never reused; a gate with zero inputs FAILs the census as today.

## Ship criterion

- On this tree, a second `make check` with no change: under 2s, every gate `reused`.
- An edit under `docs/` re-runs `check doc` only.
- A consumer-shaped fixture with a declared `[gates.inputs]` target reuses it.

## Proof budget

  cases: ~6 (reuse, re-run on input edit, config edit, version change, FAIL not reused, extra target)
  tier: unit for the cache keys; one integration case for Makefile.devkit's local install
  lands in: tests for checks/, verify/cache.py, Makefile.devkit
  what already covers this: verify's rung cache; nothing caches `check`.
