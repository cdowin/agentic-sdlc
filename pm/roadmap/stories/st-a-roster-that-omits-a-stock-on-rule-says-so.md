---
id: st-a-roster-that-omits-a-stock-on-rule-says-so
kind: story
feature: ft-a-gate-verdict-is-true-of-the-tree
milestone: "ms-a-consumer-can-take-the-bump"
name: a declared roster that omits a stock-on rule says so
status: planning
owner:
depends_on: []
changelog:
---

# a declared roster that omits a stock-on rule says so

Issue: #19.

A consumer whose `devkit.toml` declares `[pm] checks` explicitly, to opt into D9/D10 and R1–R6, gets
*"[pm] checks names D3, which was retired — became D11 in 0.6.0 … Containment is unconditional …
Remove it from the list."* Following that exactly prints `[check:pm] PASS`. On that consumer's tree
the PASS covered 117 bugs carrying `fix_milestone:`, 118 carrying `caught_in:`, and 24 `fixed` bugs
under a `done` milestone. Adding D11 turned it into 259 findings.

- `pm/vocabulary.py:427`, `checks = tup('checks', DEFAULT_CHECKS)`: a declared list REPLACES the stock roster.
- `checks/pm.py:989`, `if 'D11' not in enabled: return`, and the `RETIRED_FIELDS` loop (`:1017`) is
  inside the same function. D12 has the same gate at `:944`.
- The message (`vocabulary.py:1020/1045`) says remove D3 and never says add D11. It also says
  containment is "unconditional", which is false for an explicit roster.
- `adopt`'s `config-updated` (`conveyor/steps.py:1125`) only checks that readers ACCEPT the values.

## Acceptance criteria

1. A retired rule's message names its successor: *"replace D3 with D11"*, not only *"remove D3"*.
   The word "unconditional" goes unless it becomes true.
2. When a declared `[pm] checks` omits a rule that is stock-on, `check pm` prints one counted line
   naming each omitted rule (rule 11: absence is a named line). A counted line, not the exit code,
   because the project's roster is its declaration. **"Stock-on" means `DEFAULT_CHECKS`
   (`pm/vocabulary.py:206`), in so many words.**
3. The retired-field finding (`fix_milestone:`, `caught_in:`) no longer depends on D11 being enabled.
   The `RETIRED_FIELDS` loop (`checks/pm.py:1015-1021`) moves out of `_containment` and runs ungated,
   next to `stray_documents` (`:146-152`, "Never gated by `checks`"). **It stays exit 1, a DRIFT
   finding**, as `ms-the-rule-reaches-the-work` D2 decided: a retired field is drift, not a config
   error, and exit 2 would stop every other rule from running (`:109`, `:122`). The docstring's D11
   line (`:12-13`) moves with the loop. The finding's hint says to delete the line by hand, because no
   `pm` verb removes a field.
4. Deliberately broken probe: a scratch fixture with a pre-0.6.0 roster (no D11, no D12) and a retired
   field → **exit 1** naming the field, plus the omitted-rules line.

*(Amended from the spec scout's B1 and m3: the brief first said exit 2, contradicting 0.6.0 D2.)*

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | the retirement message case | amend |
| 2, 4 | unit | a roster-without-D11/D12 fixture | new, in the check pm tests |
| 3 | unit | the retired-field case with D11 disabled. Must fail at HEAD | amend |

## Semver

Minor: a new counted line, and a gate that now exits 1 on a tree it passed.

## Out of scope

Making D11 containment itself unconditional. It keeps its `KNOWN_CHECKS` toggle, and criterion 2
makes the toggle visible.
