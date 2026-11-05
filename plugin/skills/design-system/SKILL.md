---
name: design-system
description: Use when you add or edit a UI component, a style or a design token. Triggers - "component", "token", "colour", "spacing", "z-index", "theme", "design system", "kit". It keeps a UI on shared components and tokens.
---

# design-system: one kit, one set of tokens

A UI built from shared components and tokens looks the same everywhere and changes in one place.

Draft: owner role UX designer reviews before 1.0.

## Lens

- Prefix: DS
- Owner: UX designer
- Trigger: a change that adds or edits a UI component, style or token
- Packs: react-ts

## Rules

| ID | Rule | Severity | Check | Meaning | Pack rule |
|---|---|---|---|---|---|
| DS-1 | Use a kit component for a job the kit does | major | gate | No one-off component for a job a kit component does. | pack maps ESLint no-restricted-imports to DS-1 |
| DS-2 | No hard-coded colour | major | gate | A colour comes from a token. No hex, rgb or hsl value outside the token file. | pack maps a no-hex-colour lint to DS-2 |
| DS-3 | No hard-coded spacing or font size | minor | review | Spacing and font size come from tokens, not from px or rem literals. | - |
| DS-4 | No hard-coded z-index | minor | review | A z-index comes from a named layer token. | - |
| DS-5 | A new component says why | major | review | The change says why no kit component serves. | - |
| DS-6 | States come from the kit | major | review | Hover, focus, disabled and error states use the kit styles, not a copy. | - |
| DS-7 | No duplicate of a kit component | major | review | No component with another name that does what a kit component does. | - |

## In review

Cite the rule ID (`DS-2`). DS-1 and DS-2 are gate rules: skip them when CI runs the lint. For DS-5 quote the line of the change that gives the reason.

## Checklist

- [ ] DS-1 Kit component used
- [ ] DS-2 No hard-coded colour
- [ ] DS-3 No hard-coded spacing or font size
- [ ] DS-4 No hard-coded z-index
- [ ] DS-5 New component says why
- [ ] DS-6 States from the kit
- [ ] DS-7 No kit duplicate
