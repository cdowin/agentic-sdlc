---
name: project-verify
description: Use when a project has no scripted way to launch, drive and capture proof of the real product (a Godot game, a TypeScript CLI, a book build), or when its project-local verify skill has drifted from the product. Creates or maintains `.claude/skills/verify-<app>/`.
---

# Project verify: launch it, drive it, keep the proof

## Why

1. A project-local verify skill gives every worker the same scripted way to prove behaviour on the real product.
2. The brief's oracle can name it. It also defines a "smoke" entry: the one command the regression lane runs.
3. It is language-agnostic. Godot 4, a TypeScript CLI and a book build are covered below.

## Create

1. Interview the repo, not the person. Find five things:
   - Surface: what a user touches.
   - Run command: how the product starts.
   - Drive method: how input reaches it.
   - Evidence: what proves the result.
   - Isolation: can 2 instances run side by side?
2. If the checkout does not build or start, fix it or report that first. Do not write a skill for a product that does not run.
3. Write `.claude/skills/verify-<app>/SKILL.md`. Frontmatter: `name: verify-<app>` and a `description` that names the app, the surface and when to use it.
4. The generated skill has these sections:
   - Launch: exact command, ready signal, teardown.
   - Doctor: one read-only check. Is this instance worth driving?
   - Drive: real commands and handles from this repo. Prefer stable handles over coordinates.
   - Evidence: what is captured and where.
   - Cleanup: kill only what you started, never by process name. Evidence survives cleanup.
   - Helpers: every script is executable and its call is shown in the body.
   - Smoke: one command that launches, drives 1 path and passes only when the log holds the sentinel line `VERIFY PASS` (see the Godot path). A missing sentinel is a fail, whatever the exit code.
5. Proof standards for the generated skill:
   - Drive the real user path, not internal setters.
   - Capture the action and the resulting state.
   - Verify side effects (files, output), not only what shows.
   - A dry-run mode may skip steps. Observe what it really skips.

## Seed the feature map

1. Write `.claude/skills/verify-<app>/features/README.md`: an index with one line per feature.
2. Write 1 file per user-facing feature. Cap: 5 to start. Add more later.
3. Each feature file has 4 H2 sections: `Sub-features`, `How to get to it (user POV)`, `Driving it`, `Gotchas`.

## Prove it before hand-over

1. Run the skill's own instructions once, end to end: launch, doctor, drive 1 feature, capture, cleanup.
2. Confirm the evidence file still exists after cleanup.
3. A generated skill that was never run is a draft. Say so.

## Godot 4 path

Confirm each flag below against the installed version in the Doctor step. If a flag is unknown on the installed build, run `godot --help`, use the nearest flag, and say so in the generated skill.

1. Headless run:
   - Scene: `godot --headless --path <project> <scene>`.
   - Script: `godot --headless --path <project> --script res://tools/verify_run.gd`.
   - The generated skill ships `verify_run.gd`. It extends `SceneTree`, loads the scene, steps frames, prints `VERIFY PASS` and then calls `quit(0)`. On a failed check it prints `VERIFY FAIL: <reason>` and calls `quit(1)`.
   - The sentinel line decides pass. Godot exits 0 when a `--script` file fails to parse, so the exit code alone is not proof. Run with `--log-file <log>` and a timeout, then check: `timeout 120 godot ... --log-file <log>; grep -q '^VERIFY PASS$' <log>`. A missing sentinel, a timeout or a `SCRIPT ERROR` line is a fail.
   - In a `SceneTree` script there is no `get_tree()` or `get_viewport()`. Use `process_frame`, `root` and `current_scene` directly.
   - Use the binary path pinned in the repo, not a machine path.
2. Scripted input:
   - Build an `InputEventKey`, `InputEventAction` or `InputEventMouseButton`.
   - Call `Input.parse_input_event(ev)` or `Input.action_press(name)`.
   - Then `await process_frame` (in a `SceneTree` script; `await get_tree().process_frame` in a `Node` script), or wait a fixed frame count, before you read state.
   - Drive the real input actions, not setters on game objects.
3. Capture:
   - Log: pass `--log-file <path>`. The script prints `print` and `push_error` lines. Grep them.
   - State: print one JSON line of the observed state (node property, score, scene name).
   - Screenshot: headless has no renderer, so use a rendered run. Either `godot --path <project> --write-movie <out>.png --fixed-fps 30 --quit-after <frames>` (Movie Maker mode writes frames), or call `root.get_texture().get_image().save_png(path)` from the `SceneTree` script in a non-headless run.
   - Prefer logs and state lines for pass or fail. Use the screenshot as supporting evidence.
4. Doctor:
   - The binary exists and `godot --version` matches the 4.x in `config/features`.
   - `project.godot` is present.
   - No stray godot process that we started.
5. Gotchas:
   - A run without `quit()` hangs. Always end with it, and set a timeout on the call.
   - The first run needs an import pass: `godot --headless --import --path <project>`. Without it, imported assets are missing.
   - If the game writes saves, use a scratch `user://` directory or a user-data-dir flag. Never touch real save data.

## Short paths

TypeScript CLI:
1. Build once. Run each drive as a child process with fixed args in a temp dir.
2. Capture stdout, stderr and the exit code as the transcript.
3. Assert on the exit code and the output. Check the files it wrote.
4. For an interactive CLI, use a PTY or a tmux session per drive.

Book build:
1. Build the manuscript with the project's build command into a scratch out dir. Use no network.
2. Evidence: the build exit code and the page or word count.
3. Evidence: a rendered page image or text extract of 1-2 pages.
4. Check that the expected front matter, back matter and cross-references exist.

## Maintain

Outcomes: clean (no change, no commit), changed (proven corrections), blocked (say what blocked).

Edit scope: only the verify skill's own directory. Never edit product code. If the map describes a behaviour the product no longer has, that is doc drift: fix the map. If the product regressed, that is a finding: report it and do not hide it.

1. Locate the target verify skill. If none exists, use Create instead.
2. Fix index hygiene: every feature file is in `features/README.md`, and every entry has a file.
3. Read the source per feature. Read-only. Cap: 5 parallel readers, 1 per feature. They never drive or edit.
4. Do the live pass with ONE agent:
   - Run Doctor first. Run it again after any failed drive.
   - Evidence survives cleanup. Nothing a drive started outlives it.
5. Triage each gap:
   - Doc drift: fix the map.
   - Harness gap: fix the helper or step, then re-drive.
   - Product gap: report only.
6. Mark a feature unreachable only with the concrete prerequisite and the route tried.
7. Ship the corrections as a commit on the issue branch. One commit per kept fix is fine. The wave PR carries it.

Adapted from pstack by Lauren Tan (MIT).
