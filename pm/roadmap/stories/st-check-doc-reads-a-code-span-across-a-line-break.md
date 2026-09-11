---
id: st-check-doc-reads-a-code-span-across-a-line-break
kind: story
feature: ft-a-gate-verdict-is-true-of-the-tree
milestone: "ms-a-consumer-can-take-the-bump"
name: check doc reads a code span across a line break
status: building
owner: agent
depends_on: ["st-the-auto-loaded-rule-is-true-at-this-version"]
changelog: `check doc` reads a code span across the line breaks of its paragraph and pairs backticks the CommonMark way, so a wrapped status call, path or `make` target that used to pass is now a finding on the line the span starts on — `<!-- doc-scan:allow -->` on that line suppresses it.
---

# check doc reads a code span across a line break

Issue: #26.

`check doc`'s undeclared-state rule (`checks/doc.py:199-203`) runs `INLINE_CODE.findall(line)` one
line at a time. A code span that wraps a line never forms a span, so `pm feature` + newline +
`reviewing <id>` is invisible. That is exactly how the kit's own installed `pm-execution.md:109-110`
spells it. **The path rule (`:134-137`) and the make-target rule (`:147-151`) have the same hole.**
0.7.0 already solved this shape for `cite`: the grammar's whitespace may be a line break.

## Ordering

**This story lands after `st-the-auto-loaded-rule-is-true-at-this-version`.** Closing the hole flags
the installed rule's wrapped `pm feature reviewing` for every consumer with no `reviewing` feature
state, on a file they cannot edit without an `[adopt] ours` claim.

## Acceptance criteria

1. Code spans are found across the unfenced text of a paragraph, not per line, and a finding reports
   the line the span STARTS on.
2. All three span-based claims (undeclared state, path, make target) use the paragraph reader.
3. `doc-scan:allow` keeps its meaning. The builder decides and states whether it binds to the span's
   first line or any line it covers, and `pm-execution.md:111`'s existing allow still suppresses what
   it suppresses today.
4. Deliberately broken probe: `#26`'s two-file repro, with a feature ladder that has no `reviewing`,
   FAILS on `wrapped.md` as well as `unwrapped.md`.
5. `make check` on this repo passes: the paragraph reader finds no new false claim in our own docs,
   or each one it finds is fixed.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4 | unit | the wrapped/unwrapped pair. Must fail at HEAD | new, in the check doc tests |
| 2 | unit | a wrapped path and a wrapped make target | amend the existing path/target cases |
| 3 | unit | an allow marker on a wrapped span | amend the allow case |

## Semver

Minor: the gate now fails a tree it passed, the same call 0.7.0 made about its two gates.

## Amended from the spec scout (m2)

"Paragraph" is defined: a run of CONSECUTIVE non-fenced lines, broken at a blank line, a fence
boundary (`non_fenced_lines` drops fences, so a naive join would cross them), a heading, a list-item
start, a table row, and any gap in line numbers. A span may cross a line break inside a paragraph and
never crosses a break between two paragraphs.

## Close

done: 1a98b94 — spans read per paragraph, CommonMark backtick pairing, findings on the span's first line; #26's wrapped pair, a wrapped path and a wrapped target all FAIL; README:367 reflowed.
