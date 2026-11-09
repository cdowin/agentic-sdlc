## Agents and models (agentic-sdlc)

- A Codex session is a builder. It follows the builder rules of the model guide and the report
  protocol: https://github.com/cdowin/agentic-sdlc/blob/v5.0.0/AGENTS-AND-MODELS.md
- Work one issue on its own branch. Your first act is the comment `WORKER STARTED branch=<branch>
  session=<URL or unknown>`. When done and green, post one `WORKER REPORT branch=<branch> head=<sha> passed`
  comment with the proof and a **Done when** section. When blocked or red, post `WORKER BLOCKED branch=<branch>`
  and one question, then stop. The brief or `plugin/bin/worker-tail.md` gives the exact text.
- Set the model and effort on every delegation. Never inherit them. Effort is capped at `high`.
  The verified Codex tier mappings and capability limits are in `plugin/contract/runtimes.json`.
- Open no pull request; a lander lands your branch. Commit by path:
  `git commit -m <msg> -- <paths>`. Never force-push, `git reset --hard`, `git clean -f`, or
  discard the whole tree (`git checkout -- .`, `git restore .`).
- The author of the code owns its proof. Run each proof once. Run only narrow tests (the proof and
  the fast check); CI runs the wide suite.
- File each finding outside your task as an issue, without asking.
- Keep `AGENTS.md` under 100 lines and `CLAUDE.md` under 200. CI checks it.
