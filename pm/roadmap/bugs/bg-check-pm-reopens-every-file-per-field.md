---
id: bg-check-pm-reopens-every-file-per-field
kind: bug
milestone: "ms-a-move-is-an-event"
name: `check pm` reopens every file per field — 2.1M opens, `make check` 8.4s → 87s
status: open
caught_in: "ms-a-move-is-an-event"
fix_milestone:
caused_by:
---

# `check pm` reopens every file per field

GitHub issue #6. Bumping a ~700-document consumer tree (381 grains) from v0.2.0 to v0.4.0 took
`make check` from **8.4s to 87s**, warm. One gate is all of it:

    check doc     0.7s
    check shell   4.6s
    check pm     76.9s
    check hooks   3.3s

`check budget` fails it against a 20s ceiling measured on this tree — the gate is doing its job, the
number is real.

## Profile

    189,895,836 function calls in 109.2s
      2,120,674   31.1s   {built-in method _io.open}
      1,581,730    2.5s   pm/model.py:924(field_of)
      2,120,670    1.3s   pm/model.py:882(read_raw)
      3,753,077   14.7s   {method 'split' of 'str'}

**~3,000 file opens per document.** `field_of(path, key)` calls `read_raw`, which opens and reads the
whole file, then `_fence_bounds` re-splits it — every call, no cache. A resolver answering one grain's
question by walking every grain makes that n².

Narrowing `[pm] checks` to a single rule family barely moves it (36-37s for any one family), so it is
the shared tree scan underneath every rule, not the rules 0.4.0 added. **Tree SIZE is the multiplier**
— which is why a consumer sees it and this package's own tree does not.

## Why it matters more than the seconds

`make check` is the narrowest rung, and the execution loop is explicit that writing the tree down is
meant to be CHEAP — `pm new`, an edit, `make check`, a commit — *"because a planning step that costs a
test suite is a planning step people batch up and stop doing."* At 87s it is slower than that
consumer's entire unit tier (1,479 tests), and `make precommit` went 124s → 196s. **The gate is now
the thing the doctrine warns about.**

## Fix

Memoising `read_raw` per path for the life of the process is the first cut. The real one is one
parsed frontmatter dict per document, read once, with the census and every resolver reading that
instead of re-opening and re-splitting per field.
