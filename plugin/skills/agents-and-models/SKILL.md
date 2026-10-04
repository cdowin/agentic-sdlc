---
name: agents-and-models
description: Use before you spawn, brief or dispatch any agent, subagent or session, or when asked which agent or which model (Haiku, Sonnet, Opus, Codex) fits a piece of work. Loads the agentic-sdlc model guide - Sonnet default, the Opus list, the developer step-up rule, effort cap, Claude or Codex.
---

# Agents and models

Read the guide before the first spawn of this session, then follow it:

```sh
curl -fsSL https://raw.githubusercontent.com/cdowin/agentic-sdlc/v3.0.0/AGENTS-AND-MODELS.md
```

(or `gh api repos/cdowin/agentic-sdlc/contents/AGENTS-AND-MODELS.md?ref=v3.0.0 -H "Accept: application/vnd.github.raw"`).

The guide is the single source; this skill does not copy it. If you cannot fetch it, set
the model on every spawn anyway, use Sonnet, and say in your report that you could not
read the guide.

The 6 agents of this plugin set their own model: `developer`, `simplifier`, `test-writer`
and `tech-writer` on Sonnet; `reviewer` and `architect` on Opus. Pass `model: opus` to a
developer when the guide's step-up rule applies.
