---
id: st-gate-self-test-skips-timing-replays
kind: story
feature: ft-small-shapes-hold
milestone: "ms-the-open-issues-close"
name: The gate self-test's timing mutants replay one case, not the corpus
status: building
owner:
depends_on: []
changelog: none
---

# The gate self-test's timing mutants replay one case, not the corpus

https://github.com/cdowin/agentic-sdlc/issues/107.

## Acceptance criteria

1. `gdk_gate.sh`'s self-test gains `GDK_ST_ONLY=<case>`, or its `sleep 5` bounded case moves under
   `GDK_ST_SKIP_TIMING`, so the two timing mutants in `tests/test_gate_library.py` replay one case.
2. Both copies (`installables/gdk_gate.sh`, `tools/dev/gdk_gate.sh`) stay byte-identical.
3. The two mutant tests still FAIL their mutant; report their wall time before and after.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1-3 | integration | test_gate_library.py timing mutants | amend |
