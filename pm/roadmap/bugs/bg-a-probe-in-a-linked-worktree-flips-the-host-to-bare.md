---
id: bg-a-probe-in-a-linked-worktree-flips-the-host-to-bare
kind: bug
milestone: "ms-the-host-stays-a-checkout"
name: a probe's git init in a linked worktree flips the host to bare
status: closed
caused_by:
changelog: The git allowlist refuses a `git init` with no target or one aimed inside any checkout of this repository — the probe that set `core.bare = true` on the main checkout — and allows git whose `-C` points outside it, so a reviewer's scratch probe still runs; the reviewer and builder briefs build scratch repos with explicit `-C` paths.
---

# a probe's git init in a linked worktree flips the host to bare

## Symptom

On 2026-09-12, after 0.11.0 shipped, every git command in the main checkout failed with `fatal: this
operation must be run in a work tree`, because `.git/config` held `core.bare = true`. Linked
worktrees kept working, so nothing noticed until the main checkout was used again. 0.8.0 hit the
same state through `git bisect`.

## Root cause

It was not the test suite. `tests/conftest.py` scrubs git's environment and fails any session that
moves the host's `core.bare` (0.8.0). An AGENT's probe did it. The 0.11.0 reviewer built a scratch
copy with `git archive HEAD | tar -x -C <scratch>` and then ran, as separate `;` segments,
`git init -q 2>/dev/null; git add -A; git -c user.name=x … commit`. Its `cd <scratch>` failed, so
the commands ran in the linked worktree `ms-0.11`. **`git init` in a linked worktree re-initialises
the repository behind its `.git` file, and because that gitdir path does not end in `/.git`, git
writes `core.bare = true` into the COMMON config that every checkout shares.** The same probe left
the stray commit `f7b0fed` ("s", author `x`).

The 0.10.0 git allowlist (`cc-git-allowlist.sh`) refuses `init` outright, but it was not armed in
that session: the session's settings came from the 0.9.0 checkout. Refusing every `init` is also
wrong, because reviewers legitimately build scratch repositories.

## Fix

1. **Guard.** `cc-git-allowlist.sh` allows `git init` only with an explicit target outside every
   checkout of this repository (`git -C <dir> init …` or `git init … <dir>`, resolved against the
   payload's `cwd` and checked against `git worktree list` paths read as text, or simply refused
   when the target resolves inside the repo root or `WORKTREE_PARENT`). A bare `git init` acting on
   the cwd is refused, with the reason (it flips the shared `core.bare` when the cwd is a linked
   worktree) and the alternative (`git -C <scratch> init -q`). Corpus rows go both ways.
2. **Briefs.** `reviewer`, `verification-reviewer` and `verification-builder` build a scratch repo
   in ONE command with explicit paths (`mkdir -p S && git archive HEAD | tar -x -C S && git -C S init
   -q && git -C S add -A && git -C S -c user.name=probe -c user.email=probe@local commit -qm base`)
   and never `cd S;` followed by git.
**Not in this patch:** a `preflight` row naming a flipped `core.bare` would be a new output shape,
which is a minor bump (rule 7). It belongs in the next minor.

## Close

Fixed in bb81f46, hardened in 821ad26 after review (2026-09-12): 12 corpus rows replayed from a fake linked worktree; a real `git worktree add` probe left `core.bare = false`.
