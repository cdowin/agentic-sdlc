---
id: 0.2.0/every-gate-reports-its-cost/01-the-ledger-holds-what-a-gate-cost
feature: 0.2.0/every-gate-reports-its-cost
milestone: "0.2.0"
name: A gate run is a ledger row, and a malformed one is refused
status: done
owner:
depends_on: []
---

# A gate run is a ledger row, and a malformed one is refused

<!-- What is observable when this ships. A story is an observation, not a task. -->

`ledger.jsonl` gains a fourth row kind. `pm ledger record --gate <name> --verdict <v>
--duration-s <n> [--census <n>]` appends one line naming what a single gate run cost, and
every hostile spelling of those four values is refused with exit 2 and an empty write.

This is the SINK. Story 02 is the caller; nothing in the shell can be written until the row
shape and the verb exist, which is why this story is first and 02 depends on it.

## The row shape, pinned here so 02 and 03 build against one contract

```json
{"ts":"2026-09-05T14:02:11Z","kind":"gate","gate":"check","verdict":"PASS","duration_s":12,"census":228}
```

- `kind` is the new `ledger.KIND_GATE = 'gate'`, minted by a new `ledger.gate_row(...)`
  beside `status_row` / `decision_row`. It is NOT a `grain` row and carries no `grain` key —
  a gate is not a grain, and folding it into the spend table would make the existing report
  lie.
- **`census` is ABSENT when the gate could not report one.** Never `0`. `pm ledger record
  --grain` already rules that "a number not given is a key the row does not carry, never a
  zero" (`pm/cli.py` USAGE); a `0` census is the exact shape of this package's cardinal sin
  and it must not be spellable by omission.
- `duration_s` is an integer count of whole seconds. Absent when unknown, for the same
  reason.
- `gate` is the make target / gate tag as spelled by the caller. **Story 03 and
  `0.2.0/the-story-belt-knows-what-verifies-this-edit` both join on this string**, so it is a
  narrow grammar (below), not free text.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/ledger.py` — `KIND_GATE`, `gate_row`, the docstring's row-kind
  list.
- `src/agentic_sdlc/repo/pm/cli.py` — `cmd_ledger_record` gains the third form, plus its
  `USAGE` lines. **This is the only story in this feature that may edit
  `cmd_ledger_record`.**
- `tests/test_pm_ledger_gate.py` — new.

## Files it must stay out of

`src/agentic_sdlc/repo/pm/report.py` (story 03), every file under
`src/agentic_sdlc/repo/installables/` (story 02), `src/agentic_sdlc/cli.py`, and anything
under `pm/roadmap/`.

**`src/agentic_sdlc/repo/pm/cli.py` is shared with story 03** (which edits
`cmd_ledger_report` and one `USAGE` line). Those two are SERIAL: 01 lands, then 03.

## Acceptance criteria

1. `ledger.gate_row('check', 'PASS', 12, 228)` returns exactly
   `{ts, kind, gate, verdict, duration_s, census}` and nothing else; `gate_row('check',
   'PASS', 12, None)` omits `census` entirely rather than writing `0` or `null`.
   Proven by `tests/test_pm_ledger_gate.py`, asserting on `sorted(row)` — not on a
   membership check, which would pass on a row carrying extra keys.
2. `PYTHONPATH=src python3 -m agentic_sdlc.cli pm ledger record --gate check --verdict PASS
   --duration-s 12 --census 228` exits 0 and grows the building milestone's `ledger.jsonl`
   by exactly one line, **with every pre-existing byte unchanged** (byte-compare the prefix,
   not a line count — `append_row`'s append-only promise is the thing under test).
   Proven by `tests/test_pm_ledger_gate.py`.
3. **The loud-failure case.** In a repo with no PM tree, or with no `building` milestone,
   the verb writes nothing, prints on stderr which of the two it was, and exits 1. It never
   exits 0 with no row (a silent success for work it did not do) and never picks a milestone
   to write into. Proven by two cases in `tests/test_pm_ledger_gate.py` asserting exit 1,
   the stderr text, and that no `ledger.jsonl` was created anywhere under the scratch repo.
   *The fail-open promise in the feature's ship criterion 1 is the SHELL's, not this verb's —
   story 02 discards this exit code. A verb that lies about having recorded would make that
   fail-open unauditable.*
4. Every row of the refusal matrix below exits 2, names the offending value on stderr, and
   leaves `ledger.jsonl` byte-identical. Proven by a parametrized case per row in
   `tests/test_pm_ledger_gate.py`, each asserting the file's bytes before and after.
5. `tests/test_fuzz_inputs.py` still passes unchanged — the new flags inherit the standing
   refuse-or-contained-write floor rather than getting an exemption from it.

## Refusal matrix — `--gate`, `--verdict`, `--duration-s`, `--census`

`--gate` takes the same grammar `gates_extra.TARGET` already enforces
(`^[A-Za-z0-9][A-Za-z0-9._+-]*$`, at most 64 characters), because the value is a make-target
name that story 03 prints in a table and joins on. Each of these is one test case:

| input | why it must refuse |
|---|---|
| `--gate ''` | empty name — a row naming no gate is unattributable |
| `--gate 'lint scan'` | whitespace: two goals wearing one name |
| `--gate 'a;rm -rf /'`, `` --gate 'a`id`' ``, `--gate 'a$(id)'`, `--gate 'a\|b'`, `--gate 'a&b'` | shell metacharacters |
| `--gate '../../etc/passwd'`, `--gate '/etc/passwd'`, `--gate 'a/b'`, `--gate '~/x'` | traversal, absolute path, separators |
| `--gate '-fake-flag'` | a leading `-` posing as a flag |
| `--gate '.'`, `--gate '..'` | dot segments |
| `--gate 'x'*65` | over-long |
| `--gate $'a b'`, `--gate $'a\nb'` | line breakers: a forged SECOND ledger row. `ledger.LINE_BREAKERS` escapes U+2028/9 on write — assert the escape AND that the name is refused before it gets there |
| `--gate` with no value (end of argv) | must not adopt the next flag or the milestone id as the name |
| `--gate check --grain 0.2.0/x/y` | two mutually exclusive record forms in one call |
| `--verdict $'PASS\n{"kind":"gate"}'` | a newline in the verdict forges a second JSON line |
| `--verdict 'x'*257` | over-long free text in a durable log |
| `--duration-s -1`, `--duration-s 1.5`, `--duration-s ''`, `--duration-s '+5'`, `--duration-s '1e3'`, `--duration-s '0x10'`, `--duration-s ' 12 '` | not a non-negative decimal integer |
| `--census -1`, `--census abc`, `--census ''` | same grammar as `--duration-s` |
| `--gate check --verdict PASS` (no `--duration-s`) | a cost row with no cost is the write-only table risk 3 condemns — refuse rather than write a partial row |

**Adversarial cases against the docstrings.** `ledger.py`'s module docstring claims
append-only, never reads, never rewrites a byte. Generate against each claim: a ledger whose
last line has no trailing newline (the new row must not join it), a ledger containing a row
of an unknown future `kind` (must survive untouched), and a read-only `ledger.jsonl` (must
raise `OSError` up, per `append_row`'s stated contract, and be reported by criterion 3's
path rather than swallowed).

## Out of scope

- Anything under `src/agentic_sdlc/repo/installables/` — story 02.
- The report view — story 03.
- Ceilings, budgets, or a gate that reds on duration. The feature file is explicit: this
  REPORTS.
- A new `[ledger]` config section. Nothing here is configurable.

## Close

done: 6afa35d — the gate row, 68 refusal cases each asserting the ledger's bytes before and
after. MILLISECONDS, widened from seconds: 14 of 20 measured gates are sub-second, so an
integer-second row cannot resolve the cheap half of its own headline comparison.
finding: append_row joined a torn last line into one unparseable row. Fixed here.
