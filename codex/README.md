# agentic-sdlc for Codex

## Install: 1 paste

Run this at the root of your repo. It adds the model-guide section to `AGENTS.md`, copies
3 hooks into `.codex/agentic-sdlc/`, and writes `.codex/hooks.json`. If you already have a
`.codex/hooks.json`, merge the entries by hand instead of the last command.

```sh
u=https://raw.githubusercontent.com/cdowin/agentic-sdlc/v3.0.0
mkdir -p .codex/agentic-sdlc
for h in git-denylist commit-pathspec context-budget; do
  curl -fsSL "$u/plugin/hooks/$h.sh" -o ".codex/agentic-sdlc/$h.sh"; done
curl -fsSL "$u/codex/AGENTS.md" >> AGENTS.md
cat > .codex/hooks.json <<'EOF'
{"hooks": {
  "PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": "sh \"$(git rev-parse --show-toplevel)/.codex/agentic-sdlc/git-denylist.sh\""},
    {"type": "command", "command": "sh \"$(git rev-parse --show-toplevel)/.codex/agentic-sdlc/commit-pathspec.sh\""}]}],
  "Stop": [{"hooks": [
    {"type": "command", "command": "sh \"$(git rev-parse --show-toplevel)/.codex/agentic-sdlc/context-budget.sh\""}]}]
}}
EOF
```

Codex asks you to review a new project hook before it runs it. Commit `.codex/` so every
session gets the hooks. The opt-in hooks read the same env vars as under Claude Code
(`AGENTIC_SDLC_COMMIT_PATHSPEC=1`).

## Which hooks Codex runs

| Hook | Codex | Why |
|---|---|---|
| `git-denylist` | Yes | Codex has `PreToolUse` for shell commands (matcher `Bash`). Its stdin has `tool_input.command`; exit 2 with a reason on stderr blocks the call, as in Claude Code. |
| `commit-pathspec` | Yes (opt-in) | Same `PreToolUse` path as `git-denylist`. |
| `context-budget` | Yes | Codex runs `Stop` hooks and shows `systemMessage` as a warning. |
| `write-confine` | No | Codex edits files with `apply_patch`. Its input is a patch, not a `file_path`, so the hook has no path to check. Use Codex's sandbox (`sandbox_mode`) to confine writes. |

The hooks are early warnings. The server is the guard: a protected-branch ruleset refuses
force-push and deletion of `main`, and the 3 CI checks run for every provider.

## What Codex does not get

- **Agents.** Codex custom agents are TOML files in `.codex/agents/`, not Claude agent
  files. The section in `AGENTS.md` carries the model rules instead.
- **The plugin.** `codex plugin marketplace add cdowin/agentic-sdlc` can read this repo's
  `.claude-plugin/marketplace.json` (a legacy location Codex still reads). The Codex docs
  do not say that Codex loads a Claude `plugin.json`, and we have not tested it. Use the
  paste above.

## Sources (read 2026-10-04)

- Hooks: https://learn.chatgpt.com/docs/hooks
- AGENTS.md: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Plugins and marketplaces: https://learn.chatgpt.com/docs/plugins
- Subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Skills: https://learn.chatgpt.com/docs/build-skills
- Models: https://learn.chatgpt.com/docs/models

`developers.openai.com/codex/*` redirects to these pages.
