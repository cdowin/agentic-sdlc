---
id: st-the-project-config-header-survives-force
kind: story
feature: ft-install-force-keeps-what-the-project-owns
milestone: "ms-a-consumer-can-take-the-bump"
name: the project-config header survives --force
status: building
owner: agent
depends_on: []
changelog:
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
