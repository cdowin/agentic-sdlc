---
id: 0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts/01-grain-prose-is-capped-by-the-kit-that-defines-the-grain
feature: 0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts
milestone: "0.2.0"
name: A PM tree's prose caps are checked by the package that defines the schema
status: reviewing
owner:
depends_on: []
---

# A PM tree's prose caps are checked by the package that defines the schema

`agentic-sdlc check grain-shape` reads the grain documents under `pm/roadmap/` and reports the
ones over their cap. Every consumer gets it on a pin bump; none has to author it.

**The evidence that settles ownership:** `pm_shape_scan.sh` is not in this kit's installables —
a consumer wrote it, to enforce **this** package's grain schema. The other consumer does not
have it at all. So a rule this package defines and documents in its own templates is enforced in
one tree of two, by accident of where a file was written.

**And the cost of the misplacement is measured.** That script runs **34.8 s** — half of that
consumer's entire gate set — because its `_doc_lines` spawns four subprocesses per file
(`wc`, `head`, `awk`, `head`) across 683 markdown files. Written here, in Python, it is one pass
and it is fast for everyone.

## Acceptance criteria

1. The check reads each grain document **once**, in-process. No subprocess per file. Its census
   line reports files scanned and the cap each kind was measured against.
2. Caps come from config with shipped defaults, per rule 5 — a repo with no `devkit.toml`
   behaves byte-identically to one declaring the defaults. A bad value is exit 2.
3. **A repo with no `pm/roadmap/` is a no-op that says so, not a failure.** Not every consumer
   has a PM tree, and this gate is headed for `[checks] all` where a failure would red every
   such repo at once (feature risk 2).
4. **It ships reporting-only, or ceilinged from config so a tree adopts at its own pace.** A
   prose-cap gate will find things in a tree that never had one; the 0.24.0 deprecation window
   is the posture to copy. Which of the two is chosen is a `pm decide` entry, with the rejected
   alternative.
5. A deliberately-broken probe: a scratch copy of a fixture tree with an over-cap document, and
   the gate FAILS on it. A zero-file census FAILS rather than passes. Both per rule 4 and the
   CLAUDE.md gate-semantics bar.
6. `check grain-shape --help` prints the module docstring, like every other gate.

## Out of scope

- Adding it to `[checks] all`. That is story 02, which owns the roster growth and its argument.
- Rewriting the consumer's script. It lives in another repo and it is not ours to edit.

## Files
Touch: `src/agentic_sdlc/repo/checks/grain_shape.py` (new), `src/agentic_sdlc/cli.py`
(`_check_module` + `KNOWN_GATES`), `tests/`, `README.md` table row, `CHANGELOG.md`.
**Depends on `0.2.0/the-extraction-finishes` story 01** — the roster census must exist before
the roster grows through it.

## Close

done: 6e9388d cc0569d 14dca39 — check grain-shape, one in-process pass: 44 documents in 0.09 s
here against 34.8 s for the consumer-authored script over 683.
M1 landed in cc0569d, not 14dca39 (K2): the census in both verdict lines and the kept-nothing-
while-unexamined FAIL are grain_shape.py, and `git log -- .../grain_shape.py` is 6e9388d +
cc0569d only. 14dca39 is walk.py — M2, the symlinked dir a walk never said it skipped.
K1 landed later in 2a23d84: an UNREADABLE dir now records a Skip too, so a mode-000 subtree
FAILs on a zero census instead of PASSing over it.
