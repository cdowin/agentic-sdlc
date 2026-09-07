---
id: st-the-list-writer-preserves-every-other-byte
feature: ft-the-order-is-declared-and-appended
milestone: "ms-0.3.0"
name: a list-aware writer appends inserts and removes one entry
status: done
owner:
depends_on: []
kind: story
---

# a list-aware writer appends inserts and removes one entry

The one new primitive, and the piece the feature record says is NOT transitional:
every level uses it in 0.4.0. `order` is rewritten on every ship, insertion and
re-sequence, so byte fidelity is what it is for.

## Acceptance criteria

1. `set_list_field` rewrites the block list under a key and no other byte.
2. The file's own indent, quote character and line endings survive — a
   hand-edited plan is not reformatted underneath its author.
3. The write is idempotent.
4. A scalar on the key line is REFUSED, not rewritten as a block.
5. The key is minted when the plan has none; no frontmatter is refused.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_an_append_rewrites_only_the_list`, `test_insert_and_remove_move_one_entry_and_nothing_else` | new; extends `WriteFidelity`'s byte-comparison shape |
| 2 | unit | `test_a_crlf_plan_stays_crlf`, `test_the_files_own_indent_and_quoting_survive` | new — CRLF mirrors the existing scalar case |
| 3 | unit | `test_the_write_is_idempotent` | new |
| 4 | unit | `test_a_scalar_on_the_key_line_is_refused_and_nothing_is_written` | new |
| 5 | unit | `test_the_key_is_minted_when_the_plan_has_none`, `test_no_frontmatter_is_refused` | new |

## Out of scope

The verbs that call it — story 02.

## Close

done: 7c99862 — `set_list_field`, byte-honest: indent, quoting and line endings
come off the file rather than from the writer, so a re-sequence diffs as a MOVE.
