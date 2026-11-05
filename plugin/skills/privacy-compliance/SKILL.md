---
name: privacy-compliance
description: Use when a change stores, moves, shows or deletes personal or regulated data. Triggers - "personal data", "PII", "retention", "deletion", "audit trail", "GDPR", "consent", "data class", "purpose". It lists the privacy rules a reviewer checks with a named proof.
---

# privacy-compliance: know what you hold and why

Personal data needs a class, a purpose, a retention period, a way out and a trail. No stack pack gates these rules; a person checks them.

Draft: owner role compliance lead reviews before 1.0.

## Lens

- Prefix: PC
- Owner: compliance lead
- Trigger: a change that stores, moves, shows or deletes personal or regulated data
- Packs: none

## Rules

| ID | Rule | Severity | Check | Meaning | Pack rule |
|---|---|---|---|---|---|
| PC-1 | Each new field has a data class | major | review | The change names public, internal, personal or sensitive for each new field. | - |
| PC-2 | Retention is stated and enforced | major | review | The change gives a retention period and the job or rule that enforces it. | - |
| PC-3 | A deletion path exists and is tested | critical | review | A test deletes the data and shows it is gone. | - |
| PC-4 | Audit trail for personal data | critical | review | Each read or write records who, what and when. The actor cannot edit the record. | - |
| PC-5 | No personal data in a log, URL, fixture or test | critical | review | A grep of the diff finds no real name, email or id in those places. | - |
| PC-6 | Each field has a stated purpose | major | review | The change says why the field is held. A field with no purpose is removed. | - |
| PC-7 | Each control maps to a proof | major | review | The row names the proof: a test, a config check or a log query. | - |

## In review

Cite the rule ID (`PC-4`). For PC-7 name the test, config check or log query the reviewer ran or read.

## Checklist

- [ ] PC-1 Data class named
- [ ] PC-2 Retention stated and enforced
- [ ] PC-3 Deletion path tested
- [ ] PC-4 Audit trail
- [ ] PC-5 No personal data in log, URL, fixture or test
- [ ] PC-6 Purpose stated
- [ ] PC-7 Control mapped to proof
