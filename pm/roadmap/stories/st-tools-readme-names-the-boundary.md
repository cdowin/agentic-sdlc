---
id: st-tools-readme-names-the-boundary
kind: story
feature: ft-tools-names-what-ships
milestone: "ms-the-loop-proves-itself"
name: tools/README.md names each shipped file and each dev-only file
status: building
owner:
depends_on: []
changelog: none
---

# tools/README.md names each shipped file and each dev-only file

## Acceptance criteria

1. `tools/README.md` has one line per file under `tools/`: the installer that writes it and its
   source under `src/agentic_sdlc/repo/installables/`, or `dev-only`.
2. A unit case fails when a file under `tools/` is not named in the README.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_install.py: every tools/ file is named in tools/README.md | new |

Check bg-the-sixth-installer-cannot-describe-itself; if the README fixes it, close it.

## Out of scope

Moving files between `tools/` and `tools/dev/`.
