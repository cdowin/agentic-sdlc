---
id: ft-a-template-grows-without-a-fork
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: a template grows without a fork
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a template grows without a fork

One issue: #78. A project that needs one more section in every feature and story template has
one route today. It copies the whole template set into `[pm] template_dir`, and from then on no
kit template change reaches it. The consumer paid 16 minutes and carries a drift risk on every
bump.

## Decided (do not re-plan)

- **#78 — `[pm.templates.<kind>] extra_sections`.** Chris, 2026-09-27 (D4). A list of section
  names per grain kind (`milestone`, `feature`, `story`, `bug`). Stock empty. It is a GATE-shaped
  key: an empty list behind it, seeded COMMENTED at `[]` (rule 5, `tests/test_config_seed.py`).
  Read through `core/config.py`: a list of non-empty single-line strings; a bare string, a
  non-string, or a name with a newline or a leading `#` is refused at exit 2 by name.
- **The seam is `templates.load`** (`repo/pm/templates/__init__.py`). After it reads the
  template (packaged or `template_dir`), it appends `## <name>` plus one blank line for each
  declared name, in declared order. A name the template already carries as a `## ` heading is
  not appended twice. So `pm new <kind>` and the slot scaffold both see the same text, and a
  second `new` is still a no-op (rule 3).
- **Existing grains are not touched.** The key shapes what `new` mints. No verb rewrites an old
  file to add a section.
- **Rule 11.** Name the key in the `template_dir` guidance message (`vocabulary.py`, the one that
  says "copy them out, then edit") as the lighter option, in `pm templates --help`, and in the
  seed comment.

## Ship criterion

- With `[pm.templates.feature] extra_sections = ["Patterns"]` and no `template_dir`,
  `pm new feature` mints a file whose last section is `## Patterns`.
- The same key over a `template_dir` template that already has `## Patterns` mints one heading,
  not two.
- `extra_sections = "Patterns"` (a bare string) exits 2 and names the key.

## Proof budget

  cases: 3
  tier: unit
  lands in: the existing templates / config seed / config value test modules
  what already covers this: search first (rule 10); the seed test covers the commented key
