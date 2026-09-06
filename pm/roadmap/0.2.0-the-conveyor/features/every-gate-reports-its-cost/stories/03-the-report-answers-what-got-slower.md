---
id: 0.2.0/every-gate-reports-its-cost/03-the-report-answers-what-got-slower
feature: 0.2.0/every-gate-reports-its-cost
milestone: "0.2.0"
name: pm ledger report says which gate got slower
status: done
owner:
depends_on: ["0.2.0/every-gate-reports-its-cost/01-the-ledger-holds-what-a-gate-cost"]
---

# pm ledger report says which gate got slower

<!-- What is observable when this ships. A story is an observation, not a task. -->

`pm ledger report` grows a sixth section beside `spend` / `yield` / `rework` / `escapes` /
`overhead`: one row per gate, and the number that answers *what got slower*. **This is the
feature's ship blocker, not its garnish** — its own risk 3 says telemetry nobody reads is
cost with no benefit, and the audit (§G.3) promoted the view to a blocker for exactly that
reason.

## The section

`SECTION_GATES = 'gates'`, titled `gate cost`, rendered by the same `report.build` both the
disk and the `--from <rev>` paths already run, so the live and historical answers cannot
diverge. One row per distinct `gate` value, ordered slowest-latest first:

| column | what |
|---|---|
| `gate` | the row's `gate` string, verbatim |
| `runs` | how many `kind: gate` rows carry it |
| `first_s` / `last_s` | the earliest and latest `duration_s` by `ts` |
| `delta_s` | `last_s - first_s`, signed — **the column that answers the question** |
| `census` | `first → last`, or `-` when either is absent |

## The two ways this section can lie, and what stops each

- **A gate with one run must still appear**, with `-` in `delta_s`. A gate omitted for
  having too little data reads as a gate that costs nothing, and the whole point of the
  feature is that `z-layer-scan` was suspected by name while `pm-shape-scan` ate 47 s.
- **A duration whose census moved is not comparable** (the feature's risk 2: the same gate
  is legitimately slower on a bigger tree). When `first`'s census and `last`'s census differ,
  or either is absent, `delta_s` is still printed but the row is MARKED, and the section's
  footer says how many rows carry the mark. Silently presenting an incomparable delta as a
  regression is how someone "optimises" a gate that is simply doing more.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/report.py` — the new section's constants and builder.
- `src/agentic_sdlc/repo/pm/cli.py` — the `ledger report` `USAGE` line only.
  **`cmd_ledger_record` belongs to story 01; this story does not touch it.**
- `tests/test_pm_ledger_report_gates.py` — new.
- `tests/fixtures/` — a vendored ledger fixture (rule 8: the data is committed here, never
  read from a tree outside this checkout).

## Files it must stay out of

`src/agentic_sdlc/repo/pm/ledger.py` (story 01), everything under
`src/agentic_sdlc/repo/installables/` (story 02), `src/agentic_sdlc/cli.py`, `pm/roadmap/`.

**`src/agentic_sdlc/repo/pm/cli.py` is shared with story 01. SERIAL: 01 lands, then 03.**

## Acceptance criteria

1. A vendored ledger with three `parse` rows at 8 s, 12 s and 30 s and one `lint` row at 2 s
   renders a `gates` section listing both, `parse` first, `delta_s` = `+22`, and `lint`'s
   `delta_s` = `-`. Proven by `tests/test_pm_ledger_report_gates.py` against
   `tests/fixtures/`.
2. **A milestone whose ledger has no `kind: gate` row prints the section with the existing
   `NO_DATA` marker — it does not omit the section.** A missing section is indistinguishable
   from a section with nothing in it, and only one of those is true. Proven by a test whose
   fixture holds only `status` and `dispatch` rows.
3. **The loud-failure case, and it is rule 4's read side.** A row whose `duration_s` is
   absent, non-integer, or negative, and a row whose `gate` key is missing, are each counted
   and NAMED in the section footer — never dropped into silence and never coerced to 0. A
   report that quietly discards half its input and prints a confident table is worse than one
   that crashes. Proven by a fixture carrying one of each malformed row, asserting the footer
   count and that the good rows still render.
4. Rows whose censuses differ between first and last carry the mark, and the footer counts
   them. Proven by a fixture where `parse` goes 8 s/120 files → 30 s/900 files.
5. `--json` carries the section under the same key with the same fields, including the
   incomparable mark, so a caller need not re-derive it from the text. Proven in the same
   test file.
6. The two greppable line shapes (`report.HEADING_PREFIX`, the summary) are unchanged for
   every existing section — the diff adds a section and edits none. Proven by
   `tests/test_pm_ledger_report_sections.py` passing unmodified. Hard rule 6: an output-shape
   change is a minor bump at minimum, and this story is not the place to spend one.
7. Slice command for the loop:
   `python3 -m pytest tests/test_pm_ledger_report_gates.py tests/test_pm_ledger_report_sections.py -q`.

## Out of scope

- Any ceiling, budget, threshold or colour. The feature file is explicit: this REPORTS, and
  "whether a ceiling is ever enforced is a separate decision with its own argument".
- The narrow-vs-wide ratio print. That is
  `0.2.0/the-story-belt-knows-what-verifies-this-edit`'s `verify --plan`; this section only
  has to make it DERIVABLE, which criterion 1's per-gate durations already do.
- Trend statistics beyond first/last — median, regression lines, sparklines. Two points and a
  signed delta answer the question that was asked.
- `pm ledger show`.

## Close

done: 6e9388d — pm ledger report's sixth section: runs, first/last ms, signed delta, census
beside it. A delta whose census moved is starred, because the same gate is legitimately
slower on a bigger tree.
