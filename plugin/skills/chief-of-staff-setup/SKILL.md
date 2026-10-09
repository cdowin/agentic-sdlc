---
name: chief-of-staff-setup
description: Use when the chief of staff finds no work-intake skill, or the person asks to set up how work is tracked. Asks 3 questions and writes a starter work-intake skill for the workspace.
---

# Chief of staff setup

Write a starter `work-intake` skill from 3 answers. Ask all 3 in one message.

1. **Where does your work live?** An issue tracker (which one), a task list, files, or nowhere yet.
2. **Which repos or folders are in scope?**
3. **How do you want reports?** Length, format, and what to put first.

Then write `.claude/skills/work-intake/SKILL.md` in the workspace:

```
---
name: work-intake
description: Use when new work, a question or a finding arrives. Says where work lives and how to file it.
---

# Work intake

- Work lives in: <answer 1>.
- In scope: <answer 2>.
- A question is answered, not filed. Real work becomes one item with an outcome and a done-when.
- File each finding as an item. Do not drop it.
- Reports: <answer 3>.
```

Rules:

- Write only what the person said. Do not invent labels, fields or names.
- Show the file and ask before you save it.
- If a `work-intake` skill already exists, stop. Offer to edit it instead.
- Tell the person: add workspace rules to `CLAUDE.md`, and edit this skill at any time. Nobody edits the agent.
