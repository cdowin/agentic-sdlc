---
id: 0.20.0/generic-runners/consumers-delete-their-runners
feature: 0.20.0/generic-runners
milestone: "0.20.0"
name: consumer_a and consumer_b delete the runners they no longer own
status: ready
owner:
depends_on: []
---

# consumer_a and consumer_b delete the runners they no longer own

## Goal
consumer_a and consumer_b install the runners and delete their own; verdict lines byte-identical before/after.
## Steps
`agentic-sdlc install-runners --force` in each; delete `tools/dev/checks/parse.sh|lint.sh|warnings.sh` and `tools/dev/runners/*.sh` that the install replaced; Makefile targets point at the installed paths; `make precommit` (consumer_a) / `make check` (consumer_b); `make consumer-smoke`.
## Commit prefix
`feat(0.20.0/generic-runners/S3):`
## Size
s
