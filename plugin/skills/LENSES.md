# Lenses

A lens is a skill that a reviewer loads to judge 1 aspect of a change. Every lens has the same
shape, so a team can read, run and write one. This file is the index: it lists each lens of the
kit and the change that loads it.

## The shape of a lens

A lens is a skill folder with a `SKILL.md`. It holds these 3 sections, with these exact headings:

1. `## Lens`: 4 lines, `- Prefix:`, `- Owner:`, `- Trigger:` and `- Packs:`. The prefix is 2 or 3
   capital letters, unique in the kit and the repo. The owner is the team role that keeps the
   lens current. The trigger says which change loads the lens. Packs names the stack packs of
   skill `quality-setup` that gate its rules, or `none`.
2. `## Rules`: 1 table. Its first 4 columns are `ID`, `Rule`, `Severity` and `Check`. More
   columns may follow.
   - ID: `<prefix>-<n>`, for example `CP-8`. An ID is stable. A removed rule keeps its row and
     its ID, with severity `retired` and check `-`. Never reuse an ID.
   - Severity: the default severity of a finding against the rule. `critical` blocks the change,
     `major` must be fixed or answered, `minor` is a note. A lens with its own per-finding scale
     says how that scale maps to these 3 words.
   - Check: `gate` when a tool of a stack pack checks the rule in CI, else `review`. The
     reviewer skips a gate rule when the repo's CI runs that tool, and checks it by hand when not.
3. `## Checklist`: the closing checklist, after the rules. 1 line `- [ ] <ID> <short name>` for
   each rule that is not retired. The reviewer scores each line pass, fail or n/a, with evidence.

Other sections (how to run the lens, sources, platform notes) are free. `tests/run.sh` checks
the shape of every lens in the table below.

## The lenses

| Lens | Prefix | Owner | Trigger | Packs |
|---|---|---|---|---|
| `code-patterns` | CP | tech lead | any change to code | node-ts, react-ts, python, java |
| `ui-patterns` | UI | UX designer | a change to a screen, menu, HUD, form or editor | react-ts |
| `visual-layout` | VL | UX designer | a change to how a page, slide or document looks: styles, markup, templates | react-ts |
| `usability-review` | UX | UX designer | a change to a task a person does on a page, tool, form or menu | none |
| `accessible-content` | AC | accessibility lead | a change to anything a person reads or uses on a screen: UI, HTML, PDF, slides | react-ts |
| `plain-language` | PL | technical writer | a change to text a person reads: docs, UI text, error messages, release notes | none |

Planned lenses (#371 adds each to this table when it fills the skill): `code-quality`,
`robustness`, `security`, `privacy-compliance`, `design-system`.

## How the reviewer loads lenses

1. Read this table. Load each lens whose trigger the change matches. Load `code-patterns` for
   any change to code.
2. Read each `.agents/skills/lens-*/SKILL.md` in the repo. A repo lens has the same shape. Load
   it when its trigger matches, the same as a kit lens.
3. Read the repo overlay: `CONSTITUTION.md` and `.claude/review-lens.md`, when they exist.
4. Each finding cites its rule ID (for example `CP-8`), or quotes the overlay line it breaks.

## How to write a repo lens

Make `.agents/skills/lens-<name>/SKILL.md` with the frontmatter of a skill and the 3 sections
above. Pick a prefix no kit lens uses. Write a rule only when a reviewer can check it with
evidence: a count, a quote, a file and line, or a tool result.
