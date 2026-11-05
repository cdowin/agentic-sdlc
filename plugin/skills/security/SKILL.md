---
name: security
description: Use when a change touches authentication, authorization, input handling, secrets, transport or config. Triggers - "auth", "login", "token", "secret", "CORS", "SQL", "TLS", "CVE", "ingress", "injection". It lists the security rules a reviewer checks with evidence.
---

# security: safe by default

A change must not open a way in. Each rule is checked with a tool result, a file and line or a quote.

Draft: owner role security lead reviews before 1.0.

## Lens

- Prefix: SEC
- Owner: security lead
- Trigger: a change to authn, authz, input handling, secrets, transport or config
- Packs: node-ts, python, java, helm-terraform

## Rules

| ID | Rule | Severity | Check | Meaning | Pack rule |
|---|---|---|---|---|---|
| SEC-1 | Every route authenticates | critical | review | A route needs a signed-in caller unless the change lists it as public. | - |
| SEC-2 | Authorize by action | critical | review | A check tests an action, not a role name and not a field the client sends. | - |
| SEC-3 | Validate input at the boundary | major | review | Each request body, query and header passes a schema before use. | - |
| SEC-4 | Parameterised queries only | critical | gate | No query built by string concatenation with input. | pack maps the SAST rule for SQL injection to SEC-4 |
| SEC-5 | No secret in repo, log or image | critical | gate | No key, token or password in a file, a log line or an image layer. | pack maps the secret scan to SEC-5 |
| SEC-6 | TLS only | major | gate | No `http://` URL to another system. | pack maps the SAST or IaC rule for plain http to SEC-6 |
| SEC-7 | Config is safe by default | major | gate | No debug on, no wildcard CORS, no 0.0.0.0/0 ingress, no `latest` image tag. | pack maps the IaC scan to SEC-7 |
| SEC-8 | No known critical CVE | critical | gate | No dependency with a known critical CVE. | pack maps the dependency audit to SEC-8 |
| SEC-9 | Error text leaks nothing | major | review | A response or log line shows no stack trace, path or secret. | - |

## In review

Cite the rule ID (`SEC-2`). SEC-4 to SEC-8 are gate rules: skip them when CI runs the tool. Severity is critical for authn, authz and secrets.

## Checklist

- [ ] SEC-1 Every route authenticates
- [ ] SEC-2 Authorize by action
- [ ] SEC-3 Validate input at the boundary
- [ ] SEC-4 Parameterised queries only
- [ ] SEC-5 No secret in repo, log or image
- [ ] SEC-6 TLS only
- [ ] SEC-7 Config safe by default
- [ ] SEC-8 No known critical CVE
- [ ] SEC-9 Error text leaks nothing
