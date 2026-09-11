---
id: st-the-rendered-protocol-describes-the-check-that-runs
kind: story
feature: ft-the-shipped-words-match-the-shipped-tool
milestone: "ms-a-consumer-can-take-the-bump"
name: the rendered protocol describes the check that runs
status: done
owner: agent
depends_on: []
changelog: The rendered protocol describes release check `changelog-unreleased-nonempty` as what it reads — the `changelog:` field of every done grain — rather than the retired `## Unreleased` section; re-run `install-sdlc --force`.
---

# the rendered protocol describes the check that runs

Issue: #33.

`install-sdlc` renders `docs/sdlc-protocol.md` from the belt registry's descriptions, and consumers
are told to link it rather than restate it. Release check 3, `changelog-unreleased-nonempty`, is still
described (`conveyor/steps.py:1613-1614`, rendered at `docs/sdlc-protocol.md:37`) as *"the changelog's
`## Unreleased` section holds at least one bullet"*. Since 0.6.0 it grades every closed grain's
`changelog:` field. Keeping the step NAME is correct, because a step id is contract. The description
was never updated.

`_unreleased_span` (`steps.py:798-815`) has no caller anywhere in origin/main, tests included.

## Acceptance criteria

1. The description says what the check reads: every closed grain under the milestone answers
   `changelog:` with a sentence or `none`.
2. `_unreleased_span` is deleted.
3. A unit case fails when a registry description names a retired input (`## Unreleased`,
   `CHANGELOG.md`, `fix_milestone`) or no longer matches what its check reads. It is proven red by
   restoring the old description in a scratch copy.
4. `docs/sdlc-protocol.md` is re-installed with `install-sdlc --force`, and `installables-current` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 3 | unit | `tests/test_install_sdlc.py::test_every_registry_sentence_names_what_its_check_reads_and_nothing_retired` (moved from tests/test_conveyor_steps.py in 73a72ac to run in the unit tier; widened to all 23 checks in baf3f08) | new |
| 4 | unit | tests/test_install.py byte-current | yes |

## Semver

Patch: the rendered doc's text changes and the step id does not.

## Out of scope

`bg-the-release-belt-and-the-render-verb-disagree-about-changelog`, the neighbouring defect #33
names as "related but not the same". It is bound to this milestone as its own bug and ordered right
after this feature. It touches the same check, so the same builder should take it next.

## Close

done: b4e4606 (steps.py hunks), 61d6a52, 73a72ac — the changelog-unreleased-nonempty description says what it reads; `_unreleased_span` deleted; a unit case (moved to tests/test_install_sdlc.py) fails on a description naming a retired input.
