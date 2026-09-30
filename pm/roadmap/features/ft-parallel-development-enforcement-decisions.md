# Independent review — parallel development enforcement

The independent review found unsafe journal-lock path handling before its
read-only flock open. The check and regression are now landed in-place.

```text
verdict: SHIP
feature: ft-parallel-development-enforcement
| id | severity | disposition |
| L1 | MAJOR | landed in-place |
```

The hook now refuses Agent/Task dispatch when `[dispatch] guard = true` but no
Makefile is available to run the preflight; an unconfigured stock repo retains
its allow behavior. The dispatch fixture clears project/config caches before
its first read, so it evaluates the temporary PM tree under pytest.

Land validates transaction identity, frozen commit, immutable base, and saved
gate command before resuming. Failed phases preserve the lane; cleanup retains
dirty or unmerged branch work. The lock keeps a stable inode, refuses unsafe
paths, and uses a nonblocking read-only flock.

L1: Lock path validation did not reject an existing symlink before open; added
the symlink/non-file check and regression.

Focused evidence: 15 dispatch, hook, landing, and cleanup tests passed; both
installed and source hook self-tests passed. The bare-repository fixture now
initializes under its temporary cwd. No full gates or engine runs were part of
this review.
