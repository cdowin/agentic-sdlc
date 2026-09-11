---
id: st-the-project-config-header-survives-force
kind: story
feature: ft-install-force-keeps-what-the-project-owns
milestone: "ms-a-consumer-can-take-the-bump"
name: the project-config header survives --force
status: planning
owner:
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

## The decision this story needs before dispatch

**Rule 3 says an installer "writes a whole file or refuses by path", and `body_of()` says "there is
no substitution and no template".** Splicing the existing block into the new body is a whole-file
write whose bytes are not the packaged bytes. It needs `pm decide` on the feature before a builder
starts. The candidates:

1. `--force` splices the existing block when the block exists on both sides and the rest differs.
   This is the default, and it names what it kept.
2. A `--keep-config` flag does the splice, and plain `--force` stays lossy but WARNS that it reset a
   non-stock header.
3. No splice. `--force` refuses a file whose only difference is the header, and says to use `--diff`.

## Acceptance criteria

(Written for option 1. Re-cut if the decision picks another.)

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

Minor under options 1 and 2 (a new report line or flag). Option 3 is also minor, because `--force`
starts refusing something it used to write.
