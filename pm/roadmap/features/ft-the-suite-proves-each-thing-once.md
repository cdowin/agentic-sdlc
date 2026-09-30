---
id: ft-the-suite-proves-each-thing-once
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: the suite proves each thing once
status: done
reviewed: docs/reviews/2026-09-30-1.0.0-suite.md
depends_on: []
consumed_by: []
changelog: none
---

# the suite proves each thing once

Measured: the test tier is 866 test-seconds over 1807 cases. `test_check_hooks.py` is 310s for
30 cases: each runs the REAL `check hooks`, replaying every hook's full corpus (~10s each under
xdist). `test_hooks_payloads.py` is 125s for 84 cases; `test_makefile_gates.py` is 118s for 24
cases, `@the-real-repo` cases run real `make` against this repo (up to 27s). The unit tier is
14s, its slowest case 7.4s (`test_pm_flow.py::NoVocabularyLiteralSurvivesOutsideItsHome`).

## Decided (do not re-plan)

- **Prove the real corpus once; prove the gate's logic against a fixture.** `test_check_hooks`
  cases that test `check hooks`' JUDGEMENT (a broken symlink, a hook that dies, a hook that
  answers the flag and replays nothing, underscore files, worktree arming) run against a tiny
  fixture `tools/hooks/` of one-line hooks under `tests/fixtures/`. Exactly ONE case runs the real
  hooks' full `--self-test` replay (the proof that this repo's corpus passes).
- **`test_makefile_gates`: one real-repo case per claim.** A case parametrized over
  `@the-real-repo` and a fixture repo keeps the fixture; the real repo is proven by one case per
  distinct claim, or by `make check` itself when the gate already runs there. Name, in the
  commit message, the case that still proves each dropped real-repo parametrization.
- **`test_hooks_payloads`:** batch payloads per hook into one process where the hook reads a
  corpus (as `--self-test` does), instead of one process per payload. Keep one process-per-
  payload case per hook for the stdin path.
- **The unit tier's slowest case:** make `NoVocabularyLiteralSurvivesOutsideItsHome` scan once
  (a module-level cached index) rather than per vocabulary, or equivalent; same findings.
- **No case over 5s** in either tier on an idle laptop; list the ten slowest before and after in
  the report. Lower `devkit.toml [tests] budget` to the measured costs x1.5 (rule 10: "a tier
  that got slower is a finding" only bites when the ceiling is near the cost), and write the
  argument beside it as the file does. The case ceiling moves only if the count moves.
- Rule 10 governs every deletion: a case earns its place by gating something. Do not drop a
  claim; move it to the cheapest tier that can still fail on it, and prove that by planting the
  defect once.

## Ship criterion

- `make test` wall under 45s on an idle laptop; `make unit` under 10s; no case over 5s.
- Every dropped real-repo or real-corpus case names the case that still proves its claim.
- `[tests] budget` lowered, argued.

## Proof budget

  cases: net NEGATIVE; the fixture corpus is new, under tests/fixtures/
  tier: fixture trees; exactly one real-corpus replay
  lands in: tests/test_check_hooks.py, tests/test_makefile_gates.py, tests/test_hooks_payloads.py, tests/test_pm_flow.py, devkit.toml [tests]
  what already covers this: everything — this feature moves proof, it does not add it.
