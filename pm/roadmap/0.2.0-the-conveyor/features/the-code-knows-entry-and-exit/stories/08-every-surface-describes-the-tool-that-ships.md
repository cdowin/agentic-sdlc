---
id: 0.2.0/the-code-knows-entry-and-exit/08-every-surface-describes-the-tool-that-ships
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: README, CLAUDE.md, the agents, the seeds and the hooks describe the reader/writer that ships, and nothing else
status: done
owner:
depends_on: []
---

# README, CLAUDE.md, the agents, the seeds and the hooks describe the reader/writer that ships, and nothing else

**Chris, 2026-09-05:** *"Make sure README is updated, make sure CLAUDE.md is very clean. Make sure
the agents and claude and hooks are all clean too."*

## Acceptance criteria

- `README.md` says what the tool is in the first screen — a reader/writer over a PM tree: `pm` writes one status, `check` reads and echoes, a belt is its checks then one write (D12) — and every section after it is true against the tree: Install, Quickstart, Wiring (the two-line Makefile and `Makefile.tiers`), the verb table, the `devkit.toml` reference, Development. No engine, scene or Godot word survives; no `make` target or verb it names is missing from the tree.
- `CLAUDE.md` is the enforceable form and nothing else: the hard rules, where things live, the ladder, self-hosting, reporting — no history ("this used to…", "measured 2026-…"), no numbers that go stale, no second copy of the README. Under 150 lines. `agent-context-budget`'s four-question test decides every paragraph.
- The seed `installables/project-CLAUDE.md` is the consumer's CLAUDE.md in the same shape, and says the same ladder.
- Every agent under `.claude/agents/` is an installable or is deleted (`code-reviewer.md` is neither today); every roster agent's brief names `make check` / `make precommit` / `make pm ARGS=…` and no retired target, and `install-agents --diff` reports every one current.
- Every hook under `tools/hooks/` and its installable carry a `project config` header that names only targets this Makefile has; every comment in them describes the hook as it is.
- `.claude/rules/pm-execution.md` and `.claude/skills/*` are byte-current with their sources, and say D12.
- `[doc] scope` in `devkit.toml` covers `README.md`, `SDLC.md`, `docs/*.md` and `.claude/skills/**`, so `check doc` holds all of them from now on.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `check doc` over the widened scope; a grep for the retired words is a probe, not a test | amend tests/test_pm_gate.py's doc-scope case |
| 2 | n/a | `wc -l CLAUDE.md` and a read | the review |
| 3–6 | unit | `install-* --diff` all current | tests/test_install.py self-hosting cases, existing |
| 7 | unit | the scope is read from config | existing `check doc` config test |

## Out of scope

New doctrine. This story deletes and corrects; it adds no rule.

## Close

done: 95a4258 b81169a dbd9a49 e0538c6 3b347e4 fea01e8 — README 266 lines, CLAUDE.md 134, the seed and every agent, hook, rule and skill byte-current and free of retired words; check doc over ten docs
