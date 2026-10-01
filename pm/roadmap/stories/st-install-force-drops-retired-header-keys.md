---
id: st-install-force-drops-retired-header-keys
kind: story
feature: ft-release-and-install-tell-the-truth
milestone: "ms-the-open-issues-close"
name: install --force drops header keys the new file no longer declares
status: building
owner:
depends_on: []
changelog: install --force drops project-config header keys the new file no longer declares and names each one.
---

# install --force drops header keys the new file no longer declares

https://github.com/cdowin/agentic-sdlc/issues/128 (folds #118).

## Acceptance criteria

1. On `--force`, `install.py::carry_config_block` keeps only keys the packaged header declares;
   each dropped key prints one stderr line naming the key and the file.
2. `adopt`'s `installables-current` (`belts.py::_installables_current`) names a retired key as a
   difference.
3. A key the consumer kept that the new header still declares keeps the consumer's value.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | unit | test_install.py: an old pre-push header with PUSH_GATE | new |
| 2 | unit | test_adopt.py: the same header | new |
