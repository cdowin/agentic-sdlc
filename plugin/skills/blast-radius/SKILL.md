---
name: blast-radius
description: Use when a change could break something far from its files, when a review finding is above minor, or when the plan marks a task risky. Find the 1 fact the change is safe because of and prove it by running code that calls the real function.
---

# Blast radius

A blast-radius check finds what a change breaks outside its diff, before the merge. It does not list the callers: grep does that in 1 second. It finds the break that grep does not show.

## Do not trust your own writeup

A writeup that sounds correct proves nothing. It reads the same when it is wrong. Do not hand back a writeup only. Find the 1 fact the safety of the change depends on, and prove that fact by running code.

## The ladder

Move each fact as far down this list as is cheap. Say where it stopped.

1. Said so. This has no value alone.
2. File:line. You point at the real line, or at the library source.
3. Walked the failure. You follow the bad case step by step and show that it does not reach.
4. Ran code. A script calls the real function and fails loud when you are wrong.
5. Reproduced in the running app.

Level 4 is usually 1 small script that imports the code the app ships and calls the function you doubt.

## Steps

1. Read the change. Read the diff, the symbols it adds, changes and deletes, and what it now does differently. Include the part the diff does not show.
2. Find the 1 fact. Most changes that look risky are safe because of 1 fact, for example "only the save loader reads this header". When that fact holds, most risks clear at once. Spend your time here, not on a long list of maybes.
3. Look where grep stops. Read the source of the library you call, at its pinned version. Find when code runs: timers, signals, teardown, frame order. Follow what a symbol search misses: a saved file, a wire format, a config value, another reader of the same bytes.
4. Be honest about each risk. Give each risk a real chance and a real cost. Cite a real file:line. A search that finds nothing is an answer too. Never invent a caller or an API.
5. Prove the fact. Write a script in a scratch directory outside the repo (mktemp -d). It calls the real code. Run it. Paste the command and its last output lines. Delete the script after.

## What to hand back

- **What it does.** What changed, with the part that is not obvious.
- **The fact and its level.** State the fact and the level it reached (1 to 5). Set proven only at level 4 or 5, with the proof. Else write unproven.
- **Risks.** Each risk with its claim and its evidence (file:line, or the command and its output).
- **Cleared.** What you checked and found fine, 1 line each.
- **Before you merge.** The cheapest test or repro that catches the real break, with your script.

The wave workflow uses the `blast` shape of `plugin/contract/sdlc.schema.json` for this result.

## How the wave uses it

1. Only on a task the plan marks risky and on a review finding above minor.
2. At most 1 check per task or finding. A risky task is not checked again on a rework round.
3. At most 4 checks per wave (x-limits.blast_radius_max). Critical findings go first.
4. The result goes to the reviewer and to the 2 skeptics of the finding. It replaces neither. The skeptics still reproduce the problem themselves.

## Examples

- Godot 4 game: a change to the save loader. The fact: "a save from the last release still loads". Proof at level 4: a GDScript that extends SceneTree, loads an old save file with the real loader, checks 3 fields and calls quit(1) on a wrong value. Run it with `godot --headless --script <file>`.
- TypeScript CLI: a change to the argument parser. The fact: "no flag the docs name changes meaning". Proof at level 4: a 10-line script that imports the real parser, parses each documented flag and exits 1 on a change. Run it with `npx tsx <file>`.

Adapted from pstack by Lauren Tan (MIT).
