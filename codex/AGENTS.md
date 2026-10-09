## Agents and models (agentic-sdlc 4.1)

- Before you delegate to a subagent, read the model guide:
  https://github.com/cdowin/agentic-sdlc/blob/v4.3.0/AGENTS-AND-MODELS.md
- Set the model and effort on every delegation. Never inherit them. Effort is capped at
  `high`.
- Take any unclaimed task you have the capabilities for. A task may name a capability it needs;
  a task that names none is open to you. Claim the
  issue before you start.
- Deliver the full vertical slice: art, code, data, wiring and proof. Do not stop for
  another agent. Merge your own PR when CI is green, then remove your worktree and local
  branch.
- The Codex session is the lead. Subagents do the work.
- Go until the work is done. Run independent work in parallel. Do not ask permission for
  the next step. Stop only for an outward decision. When the person says do it, do it.
- An inward question waits 30 minutes. Then take your recommendation and write it on the
  issue. An outward question waits for the person.
- Set the wave PR to `gh pr merge N --auto --merge` only once the review reports no open
  CRITICAL. Auto-merge fires on green CI, so never set it before the review.
- Resume from GitHub (open items, claims, open wave PRs), not
  from chat. Never ask for a handoff. Write each step's state to its issue at the time.
- File each finding as an issue without asking. Rules: the workspace skill `work-intake`.
- The primary session integrates and reviews architecture. Delegate only independent,
  bounded work. For straightforward code or a focused review, use `gpt-6-luna` at low
  effort, with a precise brief, scope and acceptance criteria.
- Use the verified Codex tier mappings and capability limits in
  `plugin/contract/runtimes.json`. The model guide explains spawn and role configuration.
- The author of the code owns its proof. Run each proof once.
- Never force-push, `git reset --hard`, `git clean -f`, or discard the whole tree
  (`git checkout -- .`, `git restore .`). Commit by path: `git commit -m <msg> -- <paths>`.
- Keep `AGENTS.md` under 100 lines and `CLAUDE.md` under 200. CI checks it.
