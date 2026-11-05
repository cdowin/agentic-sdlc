# Stack pack: java

- Status: stub

Stub: no Java repo uses the kit yet, so the rules below are known but not tested, and there is no Config.

## Rules

| ID | Tool rule | Starter limit | False positives |
|---|---|---|---|
| CP-4 | the kit `ratchet` check (`magic-number`) and `MagicNumber` (Checkstyle) | the ratchet counts | constants in tests |
| CP-7 | `MethodLength` and `FileLength` (Checkstyle) | 40 lines per method, 300 per file | generated code |
| CP-8 | `CPD` (PMD) | not set | generated code |
