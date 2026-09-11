---
id: bg-check-doc-reads-into-quoted-prose
kind: bug
milestone: "ms-a-consumer-can-take-the-bump"
name: check doc reads a make target out of quoted prose and misses a span inside a blockquote
status: closed
caused_by: ft-a-gate-verdict-is-true-of-the-tree
changelog: `check doc` no longer reads `make <word>` out of prose quoted inside a code span (only an invocation at the span's start, after a shell separator, quote, prompt or `NAME=value` prefix), and it now reads a status call wrapped inside a `>` blockquote.
---

# check doc reads a make target out of quoted prose and misses a span inside a blockquote

Deferred from the gate-verdict review (`docs/reviews/2026-09-11-0.8.0-a-gate-verdict-is-true-of-the-tree.md`
m3, m4, n5) so the feature could close on its MAJORs. It is bound here, so it is fixed before 0.8.0
ships.

## Symptom

- **m4, a FAIL over no drift.** `MAKE_INVOCATION` (`checks/doc.py:40`) matches `\bmake\s+` anywhere in
  a span. The #26 paragraph reader now joins a span across a line break, so prose quoting GNU make's
  `No rule to make target` split over two lines reports ``unknown make target: `make target` ``. This
  repo's scope avoids it (README:367 was reflowed), but two files outside the scope show it
  (`ft-a-config-error-names-its-namespace.md:20`, this milestone's own `.md:61`), and so will a consumer
  whose `[doc] scope` covers prose like that. The regex was always this broad; the paragraph reader is
  what now reaches across lines with it.
- **m3, a PASS over drift.** A span wrapped inside a `>` blockquote joins as `pm feature > reviewing
  <id>`, which `_STATUS_FORM` does not match. It was missed before #26 too.
- **n5.** The per-line `CODE_SPAN` / `code_spans(line)` in `core/markdown.py` has no caller, but it
  shares its name with the paragraph reader in `checks/doc.py`. The #26 hole is one import away.

## Fix

- m4: read an invocation only at the start of a span or after a shell separator,
  `(?:^|[;&|(]\s*)make\s+…`.
- m3: strip the container marker (`^ {0,3}> ?`) from each line before the join, and break the
  paragraph wherever the quote depth changes.
- n5: delete the dead per-line reader.

Each fix gets the review's probe as a case that fails before the change.
