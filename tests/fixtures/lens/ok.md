---
name: lens-sample
description: A sample lens of the right shape. tests/run.sh breaks it 1 way per case.
---

# Sample lens

## Lens

- Prefix: SL
- Owner: tech lead
- Trigger: any change to code
- Packs: node-ts

## Rules

| ID | Rule | Severity | Check | Note |
|---|---|---|---|---|
| SL-1 | One rule | critical | gate | a tool checks it |
| SL-2 | A removed rule | retired | - | kept so the ID is never reused |
| SL-3 | Another rule | minor | review | a reader judges it |

## Checklist

- [ ] SL-1 One rule
- [ ] SL-3 Another rule

## Sources

- None.
