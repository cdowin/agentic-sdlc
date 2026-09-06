---
id: 0.2.0/the-code-knows-entry-and-exit/09-the-whys-are-small
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Every why is one sentence, every record fits on a screen, and the caps hold it there
status: building
owner:
depends_on: []
---

# Every why is one sentence, every record fits on a screen, and the caps hold it there

**Chris, 2026-09-06:** *"Long essays and big milestone records are what we want to get away
from. Small whys, direct. Milestone records should be easy for an LLM to manage."* Telemetry
stays as code; prose is the weight.

Measured 2026-09-06: `src/` carries 7,126 lines of comments and docstrings against 8,943 of
code (0.80); the shell installables are 43% comment; story records median 87 lines (max 172),
feature 118 (max 202), milestone 202, decisions 478, review records median 282 (max 432).

## Acceptance criteria

- Under `src/`, comments and docstrings are under a third of the code lines. A docstring says
  what, in one to three lines; a comment says why, in one sentence; a ruling lives in
  `decisions.md` and history in `git log`, and neither is retold in code.
- The shell installables are under 20% comment lines, same rule.
- The stock `[grain_shape] caps` are story 60, feature 80, bug 50, milestone 120, decisions 300
  (each entry under 20 lines), and a `review` kind capped at 120 over `[pm] review_dir`;
  `devkit.toml` here takes the stock caps, and every record in this tree is under them.
- The story and feature templates carry no guidance longer than three lines per section.
- The reviewer contract asks for a record a screen long: verdict, blockers one line each, the
  criteria table, the parsed block.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | a prose/code census over `src/` and the installables with the ceiling | new, one function-call case beside the shell-mark census |
| 3 | unit | `check grain-shape` PASS on this tree at the stock caps; the `review` kind | amend tests/test_grain_shape.py |
| 4, 5 | n/a | the templates and the contract, read | the review |

## Out of scope

Deleting a why. A short why is the bar; a missing one is a finding.

## Close

done: 20e256d 4b55d50 e215cec 325a354 ad091f0 — src prose 0.80 → under a third of code, shell 42% → 18%, stock caps story 60 / feature 80 / bug 50 / milestone 120 / review 120, templates and the reviewer contract a screen; records already written keep their length by ruling
