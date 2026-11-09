---
name: chief-of-staff-setup
description: Use when the chief of staff finds no work-intake skill or no repo config, or the person asks to set up how work is tracked or to adopt the kit in a repo. Writes a starter work-intake skill, writes the repo config (the env block of .claude/settings.json) from the repo's CI, and checks the CI has the shape the loop needs.
---

# Chief of staff setup

2 parts: the work-intake skill (once per workspace) and the repo config (once per repo).

## Work intake

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

## Repo config

The repo config is the `env` block of the repo's `.claude/settings.json`; the kit reads no
config file. The README's "Repo config" table lists every key and its reader.

1. **Read the CI.** Open `.github/workflows/*.yml` and find the PR workflow, its lanes and the
   check branch protection requires (`gh api repos/<owner>/<repo>/rules/branches/<base>`).
2. **Check the shape.** The loop needs all of these:
   - triggers `pull_request: [opened, synchronize, reopened, ready_for_review]`, with
     `concurrency` that cancels an older run of the same ref;
   - a **fast** lane that runs on draft and ready PRs (no `draft != true` skip). Every push to
     the draft PR runs it;
   - a **heavy** lane, if any, with `if: github.event.pull_request.draft == false`: it runs once
     when the PR is marked ready. A check goes there only with a 1-line comment saying why it
     cannot be fast;
   - **1 aggregate required check** (`needs: [fast, heavy]`, `if: always()`, failing on a failed
     or cancelled lane), so branch protection names 1 check whatever the lanes hold. A reusable
     workflow such as `cdowin/.github/.github/workflows/studio-ci.yml` gives all of this.
   For each miss, say the change in 1 line. Do not edit the CI; a change to CI is the person's.
3. **Draft the env block** from the CI:
   - `LAND_CHECK`: the fast lane's command, or its narrowest part an agent can run in seconds;
   - `AGENTIC_SDLC_GATE_WIDE`: an ERE that matches the heavy lane's or the full suite's command;
   - `AGENTIC_SDLC_VERIFY`: the smoke command of the project's verify skill, if it has one;
   - `LAND_REGEN` and `LAND_GENERATED` only when the repo has generated files;
   - `REVIEW_DUE_EVERY`, `CI_FIX_MAX`, `WAIT_REPORTS_START`, `CLOUD_WORKER_START` and
     `AGENTIC_SDLC_RUNTIME` only when the person names a value; the defaults hold otherwise.
4. **Show the block and ask before you save it.** Merge it into the existing `env`; never drop
   a key that is there.
