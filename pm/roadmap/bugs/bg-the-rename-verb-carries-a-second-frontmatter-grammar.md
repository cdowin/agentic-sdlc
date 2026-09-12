---
id: bg-the-rename-verb-carries-a-second-frontmatter-grammar
kind: bug
milestone: ms-the-tool-agrees-with-itself
name: pm rename parses frontmatter with its own key grammar and its own inline-list reader
status: closed
caused_by:
changelog: none
---

# the rename verb carries a second frontmatter grammar

Found by the feature review of `ft-the-module-says-what-it-does` (F3) and sharpened by the pass
that landed its findings. Filed rather than fixed: the fix is a write path, and the feature that
found it is a read-side feature.

## Symptom

`core/frontmatter.py` opens *"The one place this package reads and writes a frontmatter block."*
`src/agentic_sdlc/repo/pm/rename.py:72-127` assembles a document rewrite out of that module's
PRIVATE parts — `_split`, `_fence_bounds`, `_LIST_ITEM`, `_without_trailing_comment` — and that is
the lesser half. **It also carries its own grammar for the same syntax:**

    rename._KEY      re.compile(r'^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?P<rest>.*)$')
    frontmatter      `line.startswith(f'{key}:')`, in `field_in`

    rename._inline() parses `["a", "b"]` — an INLINE list, which
                     core/frontmatter.py has no reader for at all

So the tree has two answers to *"is this line a frontmatter key"* and exactly one answer to
*"is this an inline list"*, held by the module that is not supposed to be answering.

## Root cause

`rename` is the one verb that rewrites a document WHOLESALE rather than one line, and the storage
layer's public surface is built for the one-line case — `field_in`, `set_field`,
`set_list_field`. There was no public "rewrite this document's frontmatter" call, so the verb
reached past the surface and, where the surface had nothing at all (an inline list), wrote its own.

**Byte preservation is sound today** — `'\n'.join(_split(text))` is exact, and the feature review
put `pm set` through 10 hostile encodings byte-clean. This is not a rule-3 incident. It is a
fourth writer's machinery living outside the module that claims to be the only one, with a key
grammar free to drift from the owner's independently, and the two grammars already differ: a key
with a leading digit is a key to `frontmatter` and not to `rename`.

## Fix

Give `core/frontmatter.py` the call `rename` actually needs and delete the private reaches. The
shape is a document-level rewrite that takes the mapping of old id to new and preserves every
byte it was not asked to change — rule 3's own guarantee, stated once, in the module that owns it.
The inline-list reader goes with it: a format the tool accepts on input is the storage layer's to
parse, or it is not accepted.

**Price it first.** `rename.py` is the only caller, so the move is local; what is not local is
deciding whether the inline form is supported at all. `pm set` writes the block form; nothing this
package writes emits an inline list. If the answer is "we read what git or a human left behind",
that belongs in the storage layer's docstring as a stated input format.

## Out of scope

The other nine reaches into `frontmatter`'s privates —
`bg-the-storage-layers-privates-are-reached-from-outside-it`. Those are reaches; this one is a
second implementation.

## Close

Fixed in 1a55d18 (2026-09-12), by ft-frontmatter-has-one-grammar-and-one-way-in.
