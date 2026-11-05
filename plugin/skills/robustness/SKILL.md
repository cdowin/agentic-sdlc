---
name: robustness
description: Use when a change calls another system, reads input or runs unattended. Triggers - "timeout", "retry", "backoff", "idempotent", "shutdown", "health check", "resource leak", "silent failure". It lists the rules that keep code working when things fail.
---

# robustness: fail loud, recover safe

Other systems are slow, input is wrong and jobs run twice. Code must say what failed and leave no mess.

Draft: owner role tech lead reviews before 1.0.

## Lens

- Prefix: RB
- Owner: tech lead
- Trigger: a change to code that calls another system, reads input or runs unattended
- Packs: node-ts, python, java

## Rules

| ID | Rule | Severity | Check | Meaning | Pack rule |
|---|---|---|---|---|---|
| RB-1 | Every outbound call has a timeout | major | gate | No HTTP, database or queue call waits with no limit. | pack maps the timeout lint or client default check to RB-1 |
| RB-2 | Retries are bounded | major | review | A retry has a maximum count and backoff, and only repeats an idempotent call. | - |
| RB-3 | Failure is explicit | major | gate | No silent default. A promise is awaited or handled, and an error is raised or returned. | pack maps no-floating-promises to RB-3 |
| RB-4 | Wrong input is refused | major | review | Input of the wrong type or size gets a clear error, not a crash. | - |
| RB-5 | Resources close on every path | major | review | A file, connection or lock is closed on success and on error. | - |
| RB-6 | A job runs twice with the same result | major | review | A second run changes nothing more than the first. | - |
| RB-7 | Shutdown drains work | minor | review | On a stop signal the process finishes or hands back work in flight. | - |
| RB-8 | A health check says what is down | minor | review | The check names each dependency and its state. | - |

## In review

Cite the rule ID (`RB-2`). RB-1 and RB-3 are gate rules: skip them when CI runs the lint.

## Checklist

- [ ] RB-1 Outbound call has a timeout
- [ ] RB-2 Retries bounded
- [ ] RB-3 Failure explicit
- [ ] RB-4 Wrong input refused
- [ ] RB-5 Resources close on every path
- [ ] RB-6 Job is idempotent
- [ ] RB-7 Shutdown drains work
- [ ] RB-8 Health check says what is down
