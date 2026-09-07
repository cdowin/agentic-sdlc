---
id: st-no-code-path-parses-a-version
feature: ft-a-milestone-declares-its-version
milestone: "ms-0.3.0"
name: no code path parses compares or increments a version string
status: done
owner:
depends_on: ["st-r5-grades-the-current-release"]
kind: story
---

# no code path parses compares or increments a version string

The claim to consumers is that `"1.1.1"` and `"cow"` are equally valid. That is a
consequence of ordering by position, and a comparator creeping back in would
break every tree whose versions are not semver — silently, by sorting wrong.
The behaviour is an ABSENCE, so the gate is source-shaped.

## Acceptance criteria

1. No shipped module imports a version comparator (`packaging`, `pkg_resources`,
   `distutils`, `LooseVersion`, `StrictVersion`, …).
2. No release helper splits a version into components or calls `int()` over one.
3. The gate FAILS on planted drift, and fails loudly when the surface it scans
   has collapsed (rule 4).

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_no_module_imports_a_version_comparator` | new — a source-shaped family exists in test_boundaries.py; this joins it |
| 2, 3 | unit | `test_the_release_helpers_never_split_a_version_into_components` | new; census floor + name-existence assertions keep the narrowing honest |

Probe run 2026-09-06: planting `[int(x) for x in order[0].split('.')]` in
`current_release` failed the gate with both offender lines; removing it re-greened.

## Out of scope

A repo-wide ban on `.split('.')` — that is how every module reads a dotted grain
id, and a gate nobody can keep green is a gate that gets deleted.

## Close

done: 4f1e07b — two source-shaped gates over the release surface, both proven against
a planted probe. The absence is the contract, so it is asserted directly.
