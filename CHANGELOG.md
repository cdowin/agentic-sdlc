# Changelog

## Unreleased

- **This repo is the agentic half of `godot-devkit`, extracted at that project's `v0.24.0`.** SDLC, CI,
  hooks, the PM tree, installables and release automation; no Godot knowledge of any kind. The split was
  the code's own — there were ZERO imports between `godot-devkit`'s `repo/` and `godot/` halves in either
  direction, and its checks had already sorted themselves by side with nobody enforcing it. The shared
  substrate (~440 lines of config + tracked-file walking) is DUPLICATED rather than extracted to a third
  package or depended upon across the boundary; if both kits stay config-forward and that surface grows,
  the answer becomes a published shared config utility.
- **Version restarts at 0.1.0 and the PM tree starts empty.** The inherited `0.24.0` was another
  artifact's number, and `godot-devkit`'s roadmap is that project's story. Its history stays there.
