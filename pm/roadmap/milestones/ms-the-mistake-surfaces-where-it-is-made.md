---
id: "ms-the-mistake-surfaces-where-it-is-made"
kind: milestone
name: the mistake surfaces where it is made
status: planning
depends_on: []
branch: milestone/0.17.0-the-mistake-surfaces-where-it-is-made
mode: parallel
version: 0.17.0
changelog:
order:
  - "ft-the-allowlist-fails-closed"
  - "ft-a-green-run-is-bought-once"
  - "ft-ci-runs-what-the-laptop-runs"
  - "ft-the-tree-names-the-real-cause"
  - "ft-a-project-declares-its-required-lines"
  - "ft-a-close-reconciles-the-plans-ahead"
---

# ms-the-mistake-surfaces-where-it-is-made — the mistake surfaces where it is made

Found in consumer repos on 2026-09-28 and 2026-09-29. Each issue is one shape: a mistake made at
one step failed at a LATER step, or passed where it should fail, so the operator paid for it
twice. Issues #80, #84, #85, #87, #88, #89, #90, #91, #92, #93, #94, #95, #96.

## Ship criterion

- `cc-git-allowlist` blocks a merge source it cannot read and a `-c` location key (#85, #94).
- A push of commits the remote already has does not pay the gate; a batch of `close story`
  pays one green run, not one per story (#93, #95).
- A fresh `install-ci` writes Node 24 action majors, and a pinned shellcheck makes a local
  `check shell` pass mean a CI pass (#89, #90).
- `pm new` on a nested tree refuses by name, R5 names an unsequenced milestone, and `release`
  cannot write `done` over a tree its own next `make check` fails (#84, #87, #88).
- A project declares the body lines a grain must carry; `pm new` scaffolds them and the flip to
  work names a missing one (#80, #91, #96).
- A milestone that declares itself foundational cannot close without a forward-reconcile record
  (#92).
- `make milestone` green on this tree.

## Risks

- Two features change gate semantics (`a-green-run-is-bought-once`, `the-tree-names-the-real-cause`).
  Each needs a planted-drift probe (rule 4).
- `a-project-declares-its-required-lines` and `a-close-reconciles-the-plans-ahead` add config keys
  and a belt step: minor bump, seed and `test_config_seed.py` move with them (rule 5).
