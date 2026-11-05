# Stack pack: python

- Status: full

This pack maps each gate rule of the lenses to a tool rule of Python. It sets starter limits only. The ratchet (#374) sets the real limits from the repo. The same rule ID has the same intent as in the node-ts pack.

## Tools

- ruff: lints code. Reads `pyproject.toml`.
- pylint: size, nesting and duplicate checks that ruff lacks. Run with `--disable=all` and the 3 checks below. Reads `pyproject.toml`.
- gitleaks: finds secrets in files and history. Reads its built-in rules.
- Semgrep: finds a plain `http://` URL with a rule of our own. Reads `.semgrep.yml`.
- Checkov: scans Dockerfiles for unsafe defaults. Reads the command line.
- pip-audit: lists known CVEs of dependencies. Reads the project requirements.

## Rules

| ID | Tool rule | Starter limit | False positives |
|---|---|---|---|
| CP-7 | `PLR0915` (ruff) and `too-many-lines` (pylint) | 40 statements per function, 300 lines per file | generated code, long dispatch tables, a test file with many cases |
| CP-8 | `duplicate-code` (pylint) | 8 lines | generated code, test set-up that repeats on purpose |
| CQ-3 | `too-many-nested-blocks` (pylint) | 3 | a flat `match` with nested ifs in each case |
| CQ-4 | `PLR0913` (ruff) | 4 | a framework callback with a fixed signature |
| CQ-6 | `S110` (ruff) | no `except: pass` | a `pass` that is right, such as a closing hook: add a log line or `contextlib.suppress` |
| CQ-8 | `C901` (ruff) | 10 | a long but flat `if` chain over an enum |
| SEC-4 | `S608` (ruff) | no SQL built with `+`, `%`, `.format` or an f-string | a string that only looks like SQL, such as a log message |
| SEC-5 | `gitleaks detect` | no finding | a fake key in a test; allow it by path in `.gitleaksignore` |
| SEC-6 | `plain-http-url` (semgrep, our rule) | no `http://` URL except localhost | an XML namespace URI such as `http://www.w3.org/...` |
| SEC-7 | `CKV_DOCKER_7` (checkov) and `S201` (ruff) | no `latest` base image tag, no `debug=True` | a tag that is a name only, such as a local build stage |
| SEC-8 | `pip-audit` | no known advisory | pip-audit has no severity filter, so it flags low advisories too; ignore one by ID with a reason |
| RB-1 | `S113` (ruff) | every `requests` call has `timeout=` | a client that sets a default timeout on its session |
| RB-3 | `BLE001` (ruff) and `RUF006` (ruff) | no blind `except Exception`, no dangling task | a top-level handler that logs and re-raises |
| CP-4 | the kit `ratchet` check (`magic-number`) and `PLR2004` (ruff) | the ratchet counts | HTTP status codes, test values: name them or keep the count |

## Config

File: `pyproject.toml`
```toml
[tool.ruff.lint]
select = ["C901", "PLR0913", "PLR0915", "PLR2004", "S110", "S113", "S201", "S608", "BLE001", "RUF006"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 4
max-statements = 40

# Run: pylint --disable=all --enable=duplicate-code,too-many-lines,too-many-nested-blocks
[tool.pylint.format]
max-module-lines = 300

[tool.pylint.design]
max-nested-blocks = 3

[tool.pylint.similarities]
min-similarity-lines = 8
```

File: `.semgrep.yml`
```yaml
rules:
  - id: plain-http-url
    message: Use https. A plain http URL sends data in the clear.
    severity: ERROR
    languages: [generic]
    pattern-regex: 'http://'
    pattern-not-regex: 'http://(localhost|127\.0\.0\.1)'
```
