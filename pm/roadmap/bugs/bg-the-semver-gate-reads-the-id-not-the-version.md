---
id: bg-the-semver-gate-reads-the-id-not-the-version
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name: the semver gate reads the id, not the version
status: closed
caused_by:
changelog: The shipped `semver-gate.yml` now reads a milestone's `version:` field, falling back to its `id`, so a release PR whose milestone is named by slug is admitted — the success path had never fired for any layout the scaffold produces, and every consumer's release gate could refuse but never admit.
---

# the semver gate reads the id, not the version

**The success path of `semver-gate.yml` has never once fired, in any layout, for any release.**
Found by simulating it against this repo's own tree, one commit before opening 0.6.0's release PR —
which it would have refused.

## Symptom

The gate admits a release PR when the version in `[pm] version_file` is either a hotfix on main's
version or **the `id:` of a `done` milestone**. Run its own frontmatter reader over this tree:

    ms-0.1.0.md                     id=ms-0.1.0                    version=0.1.0    status=done
    ms-0.4.0.md                     id=ms-0.4.0                    version=0.4.0    status=done
    ms-a-move-is-an-event.md        id=ms-a-move-is-an-event       version=0.5.0    status=done
    ms-the-rule-reaches-the-work.md id=ms-the-rule-reaches-the-work version=0.6.0   status=building

`$PR` is `0.6.0`. No `id` here equals it — **not even `ms-0.4.0`**, whose id carries the digits, and
which is the closest any milestone this package ever scaffolded came to matching. The loop falls
through, `legit` stays empty, and the PR is refused with:

    ::error::0.6.0 is neither the id of a done milestone under pm/roadmap nor
    main's version (0.5.0) plus one hotfix component.

That message is unactionable by construction: the only way to satisfy it is to rename a milestone to
a bare version, which is exactly what `bg-the-milestone-scaffold-still-mints-the-version` retired
four grains earlier in this same milestone.

## Root cause

**A new writer met an old reader, and the test fixture was the old reader's alibi.**

`ft-a-milestone-declares-its-version` (0.3.0) moved the version onto a `version:` FIELD. The gate,
written after it, still asks `id`. That is the whole defect — one field name.

What kept it invisible is the more interesting half. `tests/test_ci_workflows.py` RUNS this script,
with thirteen rows covering any-length compare, non-numeric refusal, quote styles, body-vs-frontmatter
and a hotfix that must refuse. It is a good harness. **Every fixture in it writes `id: 0.90.3` — a
milestone whose id IS a version string, the layout `pm new milestone` stopped producing at 0.3.0.**
So the rows exercised the success path against a shape nothing writes any more, and reported it
green. The same class as `bg-a-proof-row-names-a-case-that-proves-half`, one layer out: not a test
that could not fail, a test that could only pass on a tree the tool no longer builds.

The gate is also the shipped installable `ci-semver-gate.yml`, so **every consumer that names a
milestone by slug — which is now the only thing `pm new milestone` will do — has a release gate that
can refuse but never admit.**

## Fix

The loop asks `version:` first and falls back to `id`, so a pre-0.3.0 tree that never migrated still
resolves; either match names WHICH field vouched for it, in the verdict and in the refusal:

    legit="the version of done milestone ms-the-rule-reaches-the-work"

`tests/test_ci_workflows.py::test_a_milestone_declaring_its_version_in_a_field_is_a_release` runs the
real script over the modern layout in both directions — `done` admits, `building` refuses — and
`test_the_id_still_declares_the_version_on_a_tree_that_predates_the_field` pins the fallback so
reading the new field did not retire the old shape out from under anyone.

Watched failing at HEAD with the exact refusal 0.6.0's own PR would have received.

## Out of scope

The rest of the workflow. The compare arithmetic, the hotfix grammar, the zero-scan refusal and the
frontmatter reader are all correct and all covered; one field name was wrong.
