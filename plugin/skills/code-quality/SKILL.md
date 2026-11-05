---
name: code-quality
description: Use when you write or review any code and want it readable and honest. Triggers - "naming", "flag parameter", "nesting", "too many parameters", "empty catch", "misleading name", "comment". It lists the quality rules that code-patterns does not cover.
---

# code-quality: code a reader trusts

Names, shape and error handling that a reader can trust. This lens adds to `code-patterns`; it does not repeat it.

Draft: owner role tech lead reviews before 1.0.

## Lens

- Prefix: CQ
- Owner: tech lead
- Trigger: any change to code
- Packs: node-ts, react-ts, python, java

## Rules

| ID | Rule | Severity | Check | Meaning | Pack rule |
|---|---|---|---|---|---|
| CQ-1 | A name says what the code does | minor | review | No `data`, `tmp`, `handle`, `doProcess` or `util` as the whole name. | - |
| CQ-2 | No flag parameter picks behaviour | minor | review | A boolean argument that switches a function between 2 jobs is 2 functions. | - |
| CQ-3 | Nesting is 3 levels or fewer | major | gate | A block inside 4 or more blocks is split or returns early. | pack maps ESLint max-depth to CQ-3 |
| CQ-4 | A function takes 4 parameters or fewer | minor | gate | More than 4 parameters become 1 named object. | pack maps ESLint max-params to CQ-4 |
| CQ-5 | A comment says why, not what | minor | review | A comment that repeats the next line is deleted. A comment gives a reason. | - |
| CQ-6 | No empty catch | major | gate | A caught error is handled, logged with context or rethrown. | pack maps ESLint no-empty to CQ-6 |
| CQ-7 | A name does not lie | major | review | A `get*` or `is*` function does not write. A `validate*` function does not fix. | - |
| CQ-8 | Complexity of a function is 10 or less | major | gate | Cyclomatic complexity above 10 is split. | pack maps ESLint complexity to CQ-8 |

## Covered by code-patterns

The reviewer loads `code-patterns` with this lens and cites the CP ID, not a CQ row:

- small functions and files: CP-7
- no magic numbers or strings: CP-4
- no dead code: CP-6
- no duplicates: CP-8

## In review

Cite the rule ID (`CQ-6`). CQ-3, CQ-4, CQ-6 and CQ-8 are gate rules: skip them when CI runs the tool.

## Checklist

- [ ] CQ-1 Names say what code does
- [ ] CQ-2 No flag parameter
- [ ] CQ-3 Nesting 3 or fewer
- [ ] CQ-4 4 parameters or fewer
- [ ] CQ-5 Comments say why
- [ ] CQ-6 No empty catch
- [ ] CQ-7 Names do not lie
- [ ] CQ-8 Complexity 10 or less
