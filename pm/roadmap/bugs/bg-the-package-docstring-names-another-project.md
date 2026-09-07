---
id: bg-the-package-docstring-names-another-project
kind: bug
milestone: ms-the-rule-reaches-the-work
name: the package docstring describes Godot scene introspection
status: closed
caused_by:
---

# the package docstring names another project

Found while bumping the version sites for the 0.5.0 release, which is the only reason anybody opened
the file. It has shipped in every release this package has cut.

## Symptom

`src/agentic_sdlc/__init__.py` is two lines, and the first one is about a different project:

    """agentic-sdlc — headless scene introspection + static repo gates for Godot 4.x."""
    __version__ = '0.5.0'

This package does no scene introspection and knows nothing about Godot. The sentence is copied from
`godot_devkit`, the sibling repo this one was extracted from. It is the module docstring, so it is
what `help(agentic_sdlc)` prints and what a reader sees first on opening the package.

`pyproject.toml` two directories up has the true description, and has had it the whole time — one
fact stored twice, in disagreement, with nothing that could say so out loud.

## Root cause

**Nothing reads it.** `check doc` holds this repo's prose to make-target and file-path claims —
that is why the always-loaded surfaces cannot drift — but its scope is markdown. A docstring is
prose that makes a claim about what the package IS, and it sits in a `.py` file, so no gate is
pointed at it.

The extraction from `godot_devkit` is the origin, and the four releases since are the actual defect:
the sentence survived a rename, a repackaging, and every review this tree has run.

## Fix

One line in `src/agentic_sdlc/__init__.py`, saying what the package is, in this repo's voice.

Two constraints on the edit:

  * `[release.version_files]` matches this file against `^__version__ = '(.*)'$`. The docstring is
    above it and the regex is anchored, so the shape of line 2 must not move.
  * Rule 6: the docstring is not an output line shape and nothing greps it, so rewriting it is not
    a contract change.

**The durable half is the gate, not the sentence.** A one-line fix that leaves nothing looking is a
fix that comes back — this is the second copy of `pyproject.toml`'s `description`, and 0.6.0's
northstar is that a document which cannot be checked against the tree is not a record. The cheapest
honest check: the package docstring and `[project] description` must name the same project, asserted
where `test_boundaries.py` already holds this package's shape to itself.
