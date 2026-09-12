---
id: bg-the-hard-rule-numbers-are-an-api-nobody-states
kind: bug
milestone: "ms-the-tool-agrees-with-itself"
name: the hard-rule numbers are a public API and CLAUDE.md does not say so
status: open
caused_by:
changelog: none
---

# the hard-rule numbers are a public API and CLAUDE.md does not say so

Issue: #15, consequence 4, the last part of it that is not a feature.

## Symptom

`CLAUDE.md`'s eleven hard rules are cited by number across source, tests and hooks (`rule 4`,
`rule 9`, `rule 11`, …). That makes the numbering a public API. Renumbering or reordering the list
silently re-points every citation. Two grains have argued from this:
`bg-the-brief-undercounts-the-coupling-it-argues-from` measured the citations at about twice #15's
estimate of 600, and `bg-the-always-loaded-surface-states-properties-not-procedures` held the
numbers fixed because of it. Both are closed. **The file those citations point into still does not
say so**, so the next person to tidy the list has no signal (rule 11).

## Root cause

The constraint was recorded in the grains that obeyed it, never in the surface it constrains.

## Fix

Add one sentence under `## Hard rules` in `CLAUDE.md`: the numbers are cited across the tree, so the
list is append-only. A rule is trimmed inside itself and never renumbered, and a new rule takes the
next number. Re-measure the citation count with a command, and cite the number in the close, not in
the sentence, so the sentence cannot go stale.

Then close #15 on GitHub. Its consequences 1–3 shipped in 0.6.0 and 0.8.0 (see its comments). This
bug is consequence 4. The phase-specific preamble is the pool feature
`ft-a-phase-declares-what-it-hands-an-agent`, and the closing comment names it.
