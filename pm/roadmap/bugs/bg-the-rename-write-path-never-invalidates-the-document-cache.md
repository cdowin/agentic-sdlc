---
id: bg-the-rename-write-path-never-invalidates-the-document-cache
kind: bug
milestone:
name: a document rewritten through apply.Plan stays in the parse cache, and a same-length rename defeats the stamp
status: open
caused_by:
changelog: none
---

# the rename write path never invalidates the document cache

Found by the feature review of `ft-the-module-says-what-it-does` (F4). Filed rather than fixed
after the landing pass priced both candidate fixes and found neither free — the reasoning is under
`## Fix`, and it is the part worth reading.

## Symptom

`core/frontmatter.py` caches parsed documents in `_DOCUMENTS`, and `forget_document` is called
from `write_raw` **alone** (`core/frontmatter.py:43`). `src/agentic_sdlc/repo/pm/rename.py:232`
does not write through `write_raw`: it stages through `out.plan.overwrite(path, swept, …)`.

So a renamed document's parse survives its own rewrite. The only thing standing between that and a
stale read is `_stamp`'s `(st_mtime_ns, st_size, st_ino, st_dev)` comparison — and **a rename
between two ids of the same length changes neither the size nor the inode.** On a filesystem with
coarse mtime granularity, a same-process read after the write serves bytes that have moved on.

Rule 4's second sin wearing a speedup, which is what the cache's own banner
(`core/frontmatter.py:79-82`) warns about in its own words.

## Root cause

**The invalidation hook was hung on one of the two write paths.** `write_raw` is the one-line
writer and it remembers; `apply.Plan.overwrite` is the whole-file writer and it does not, because
the cache was added for the reader and nobody asked which writers existed.

Narrow in practice: it needs a same-LENGTH rename, the same inode, and an mtime granularity coarse
enough to land both writes in one tick. Pre-existing, and unchanged by 0.7.0 — the code moved
modules and the behaviour did not.

## Fix, and why neither candidate was taken as a NIT

**Rejected: `apply.Plan` calling `forget_document` per overwritten path.** That is a core import
cycle — `core/frontmatter.py:16` imports `apply`, and `core/apply.py` imports nothing from the
package, deliberately. It would need a deferred import inside the mutation primitive, which is the
exact "we only do it lazily" shape `OneSpawn`'s corpus bans one module over.

**Candidate, and it needs pricing:** `apply.mutations()` (`apply.py:237`) is already the counter
`inventory.reading_tree` consults for this same invalidation question, so `frontmatter.document()`
consulting it is about four lines with no cycle. The cost is that it drops the WHOLE parse cache on
every write, and pricing that against the write-heavy verbs — `pm rename` over 700 documents, `pm
collapse` — is real work, not a NIT's.

That is why this is a grain: the defect is four lines, and knowing which four is a measurement.

## How to see it fail

A test needs to defeat the stamp deliberately: write a document, read it through
`frontmatter.document`, rewrite it through `apply.Plan.overwrite` with a same-length id, restore
the original `st_mtime_ns` with `os.utime`, then read again and assert the second read sees the new
bytes. It fails today.

## Out of scope

The cache itself. It exists because reading 700 documents four times cost the inner loop real
seconds, and the fix is invalidation, never removal.
