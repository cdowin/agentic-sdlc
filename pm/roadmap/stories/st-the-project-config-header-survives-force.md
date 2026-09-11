---
id: st-the-project-config-header-survives-force
kind: story
feature: ft-install-force-keeps-what-the-project-owns
milestone: "ms-a-consumer-can-take-the-bump"
name: the project-config header survives --force
status: done
owner: agent
depends_on: []
changelog: `install-* --force` carries your project-config block into the new body byte for byte — a hook's `project config` header, or the ```text fence under an agent brief's `## Project config`, whose heading, dispatch sentence and prose are now the kit's and DO update — and names each `NAME=` or `key:` the packaged block declares that yours lacks; a difference only inside that block is current, exit 0.
---

# the project-config header survives --force

Issue: #20 (item 2).

`install-hooks --diff` reports `cc-stop-gate.sh`, `pre-push` and `agent-worktree.sh` as *"differs
ONLY inside its project-config header — the rest of the file is byte-current"*. Then `--force`
replaces the header anyway, because the header-only branch is skipped under force
(`install.py:~827`, `elif not force:`). One consumer's `PUSH_GATE`, `GATE_STATIC` and `WARM_DIRS`
were reset to stock on the 0.4.0 bump and again on the 0.7.0 bump, and restored from git both times.
The tool has both facts it needs: `config_block_span()` finds the block on both sides.

## Decided (feature D1)

`--force` carries the existing block into the packaged body by default, whenever the block exists on
both sides. It is still a whole-file write. The kit simply stops claiming bytes that `--diff` and
`installables-current` already treat as the project's. `--keep-config` and refuse-on-header-only are
rejected. The reasoning, and the boundary the review holds (carry bytes, compute nothing), is in
`ft-install-force-keeps-what-the-project-owns-decisions.md` D1.

## Acceptance criteria

1. On a hook whose header is edited and whose body is stale, `--force` writes the new body with the
   old header, byte-for-byte, and prints that it kept the header.
2. On a hook whose header block is MISSING on either side, `--force` writes the packaged file whole,
   exactly as before.
3. `installables-current` still treats a header-only difference as current (unchanged).
4. Idempotent.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 4 | unit | temp tree, edited header + stale body; header-less variant | amend the header-only-diff case |

## Semver

Minor: a new report line, and `--force` writes different bytes than it did.

## Amended — feature D2 (the markdown block is the text fence)

5. For a MARKDOWN installable, the carried block is ONLY the ```` ```text ```` fence inside
   `## Project config`. The heading, the dispatch sentence and the prose are the kit's. A brief with no
   such fence has no project-owned block. The shell hooks' grammar is unchanged.
6. `--diff`'s header-only verdict, `installables-current` and the `--force` carry all read the ONE
   span. Probe: a brief whose fence is edited AND whose dispatch sentence is stale → `--force` writes
   the new sentence and keeps the fence byte-for-byte. A brief edited only OUTSIDE the fence is drift,
   not header-only.
7. The self-host test (`test_this_repo_carries_the_roles_it_runs_byte_current`) accepts a fence-only
   difference, the way the hooks' self-host already accepts a header-only one. This repo's own
   installed agents are then current under the narrowed span.

## Close

done: b4e4606, 73a72ac — --force carries the project-config block byte for byte (D1), narrowed to the ```text fence for markdown (D2); a kept block names what it lacks; header-only without --force is exit 0.
