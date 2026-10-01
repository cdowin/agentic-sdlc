---
id: st-a-verify-miss-names-what-changed
kind: story
feature: ft-a-rerun-names-its-cause
milestone: "ms-the-loop-proves-itself"
name: A verify cache miss prints each input that changed
status: planning
owner:
depends_on: []
changelog: On a cache miss, verify prints one changed: line per input that moved since the last PASS.
---

# A verify cache miss prints each input that changed

## Acceptance criteria

1. A receipt row holds a digest per input as well as the one tree digest.
2. On a miss, `verify` prints `changed: <path>` for each input whose digest differs, and
   `added:` or `removed:` for inputs that appeared or left, before the target runs.
3. A row written by 2.0.0 (no per-input digests) reads as a plain miss and prints nothing new.
4. A hit prints nothing new.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_verify_cache.py: record, edit one input, look up | new |
| 3 | unit | test_verify_cache.py: an old-shape row | new |
| 4 | unit | test_verify_cache.py hit case | existing |

Files: `src/agentic_sdlc/repo/verify/cache.py`, `verify/main.py`. Mind
bg-verdict-names-three-unrelated-things: name the new field after what it holds.

## Out of scope

A `--explain` flag. The lines print on every miss; a filter is the shell's job (rule 11).
