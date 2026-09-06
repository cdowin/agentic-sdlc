"""pm — filesystem-backed milestone/feature/story/bug tracking.

Markdown with YAML frontmatter under `pm/roadmap/`; `status:` is the only
field written. `model.py` holds the invariants, `cli.py` the writes, and
`checks.pm` reads the same predicates — one definition, two readers.
"""
