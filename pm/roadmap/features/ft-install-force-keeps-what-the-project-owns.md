---
id: ft-install-force-keeps-what-the-project-owns
kind: feature
milestone: "ms-a-consumer-can-take-the-bump"
name: install --force keeps what the project owns
status: done
reviewed: docs/reviews/2026-09-11-0.8.0-install-force-keeps-what-the-project-owns.md
depends_on: []
consumed_by: []
changelog:
order:
  - "st-force-leaves-a-claimed-file-alone-and-takes-one-by-path"
  - "st-the-project-config-header-survives-force"
  - "st-the-withdrawal-census-never-reports-a-span-it-did-not-scan"
---

# install --force keeps what the project owns

Issues: #20 #29 (the same defect; #29 adds the `install-ci` and `install-hooks` cases), and #21 #28
(the same root cause; #28 adds that through the `make` vehicle the floor ALWAYS equals the ceiling).

`--force` is the only way to take a drifted installable, and it overwrites two things the package
already knows belong to the project:

- the files named in `[adopt] ours`. `install.py` never reads that list; only `conveyor/steps.py:574`
  `_ours_of` does;
- the project-config header. `install-hooks --diff` itself reports a file as differing "ONLY inside
  its project-config header".

One consumer's 0.7.0 bump hit both. `install-agents --force` made 824 insertions and 1,344 deletions
across 11 claimed agents. `PUSH_GATE`, `GATE_STATIC` and `WARM_DIRS` were reset to stock on two
successive bumps and restored from git both times. Taking the one new agent meant
`git show v0.7.0:…/pm-operator.md > …` by hand.

Its closing census also cannot fail in the order the adopt belt requires. The pin is bumped first
(`pin-bumped` checks that), then `installed_stamp()` reads the bumped pin as the floor, so
`retired_since()` compares v0.7.0 with v0.7.0 and prints "withdrawn nothing". The 0.6.0
`changelog-writer.md` retirement is exactly the row it exists to print, and it never prints it.

All three stories are `src/agentic_sdlc/repo/install.py`, so they run serially under one builder.
They share no file with the other features, so this feature can run in parallel with them.

## Ship criterion

On a scratch copy of a consumer with `[adopt] ours` claims and edited config headers,
`install-* --force` rewrites only unclaimed files and names each claimed file it skipped. Every header
is byte-identical afterwards, or the story's decision says why not. One installable can be taken by
path. The withdrawal line either names what the span withdrew or says it could not see the span. It
never says "withdrawn nothing" about a span it did not scan.

**Accepted means closed on GitHub:** #20, #29, #21 and #28 are each closed with a comment citing this
feature and its commit hash(es) (SDLC.md §2).

## Proof budget

  cases: 4–6
  tier: unit, against a temp tree (the installer's plan and write are functions; no process needed)
  lands in: tests/test_install.py
  what already covers this: the byte-current and header-only-diff cases. Nothing puts an
    `[adopt] ours` claim in front of `--force`, and nothing runs the census with floor == ceiling.
    That second one is rule 4's first sin: the case to add is the one that CAN print "withdrawn
    nothing" and must not.
