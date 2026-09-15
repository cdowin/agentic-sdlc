---
id: "ms-a-role-runs-on-its-declared-model"
kind: milestone
name: a role runs on the model it declares
status: planning
depends_on: []
branch:
mode:
version:
changelog:
---

# ms-a-role-runs-on-its-declared-model — a role runs on the model it declares

**PARKED — backlog, not planned (D9).** This file holds the design and the evidence, and the
milestone has no features. Revive it when a machine can run a local model with Claude Code's tool
loop at a wall-clock Chris will accept (see *Revive when*). The decisions are in
[the decisions log](ms-a-role-runs-on-its-declared-model-decisions.md), D1–D9.

A project declares which model each ROLE runs on, as an ordered fallback chain in `devkit.toml`.
Rote and documentation roles go to a free local model through Ollama, and the heavy coding roles
stay on Claude. The tool reads the declaration, routes each spawn by the role's name, walks the
chain when an entry is unavailable, and records which model actually ran. It never sniffs a prompt
to guess how hard the work is. States, gates and arrivals are declared, and now so are models.

## The declaration

```toml
[dispatch]
local_routing = true            # D8: absent = off; GDK_LOCAL_ROUTING=0|1 overrides per shell

[dispatch.models]               # D5: role = ordered chain; `default` covers unnamed roles
default              = ["claude"]
tech-writer          = ["ollama/qwen3:14b", "ollama/qwen3:8b", "claude-sonnet"]
doc-hygiene          = ["ollama/qwen3:8b"]
simplifier           = ["ollama/qwen3:8b"]
pm-operator          = ["ollama/qwen3:14b", "claude-sonnet"]
architect            = ["claude-opus"]
developer            = ["claude-opus"]          # D3: a second Claude entry is unreachable
verification-builder = ["claude-opus"]
```

This is Chris's table as written on 2026-09-14, with `developer` losing `claude-sonnet` (D3). The
`qwen3:14b` entries are inert on a 16 GB machine (probe 1) and are harmless there, because the
walk skips an entry that is unavailable.

## The framework, end to end

1. **Resolve** (`dispatch --route <role>`, D5/D8): the role's chain, or `default`'s. `ollama/*`
   entries are unavailable when `local_routing` is off, when the server does not answer
   `GET localhost:11434/api/tags` within 1s, or when it does not list the tag (D3). Take the first
   available entry. Print each skipped entry as one named line. An exhausted chain falls back to
   `default`, and says so.
2. **Route a Claude entry in-session** (`cc-model-route.sh`, D2/D6): allow the `Agent` spawn and
   set `updatedInput.model`. If the caller passed a model the table does not name, deny and name
   the declared one.
3. **Route an Ollama entry out of band** (D1): deny the in-session spawn, and put a rendered command
   in the reason for the orchestrator to run. The command is `claude -p` with
   `ANTHROPIC_BASE_URL=http://localhost:11434`, `--model <tag>`, `--strict-mcp-config`, an explicit
   `--tools` list, and the role's brief as the system prompt.
4. **Prove it held** (D7): the ledger records the model each run actually used. `pm ledger report`
   shows it, and `check pm` warns on a row whose model is not in its role's chain.

What was taken from Chuzom (github.com/Chuzom/Chuzom, MIT, studied and not vendored): the
`updatedInput.model` rewrite, and the `/api/tags` availability check. What was rejected: a hook
that runs the model itself (D1), tiers chosen by regexes over the prompt, answer-quality heuristics
(D3), and a quota gate built on Keychain credentials (D4).

## Evidence — four probes, 2026-09-14/15, 16 GB Apple Silicon, Ollama 0.34.0

Each probe ran one task in a scratch directory: in `notes.md`, fix `twoo` to `two` with Edit, then
create `done.txt`.

| # | model, context | Claude Code flags | result | wall-clock |
|---|---|---|---|---|
| # | model, context | Claude Code flags | prompt the model got (Ollama log) | result | wall-clock |
|---|---|---|---|---|---|
| 1 | qwen3:14b, 4096 (Ollama default) | defaults | **40,334 tokens, truncated to 2,050** | hung; `unrecognized_model`; no edit. 9.3 GB resident; **froze the machine** | killed at 400s |
| 2 | qwen3:8b, 32768 | defaults (all global MCP servers loaded) | **58,460 tokens, truncated to 16,386** | 1 turn, 0 tool calls; replied about sending Gmail | 285s |
| 3 | qwen3:8b, 32768 | `--bare --strict-mcp-config --disable-slash-commands --tools "Read,Edit,Write" --system-prompt "<one line>"` | ~1.7–2.1k per request, not truncated | **pass**: 5 turns, both edits correct. 7.7 GB on GPU | 239s |
| 4 | qwen3:8b, 32768 | probe 3 without `--bare`, `--setting-sources project`, two logging hooks | 3,462 tokens, not truncated | **fail**: one request generated for 4m56s, no tool call, no edit. The `SessionEnd` hook fired; `PreToolUse` never had a call to fire on | killed at 300s |

What the probes establish:

- **Direct requests work.** Ollama's Anthropic-compatible endpoint answers (`/v1/messages`, 23s
  cold, `/api/tags` 22ms).
- **Claude Code's default prompt is 40–58k tokens**, per Ollama's own truncation warnings. It
  cannot fit a default local context. A 14B model at the ~64k context it would need does not fit
  16 GB. Probes 1 and 2 failed on a cut-off prompt: the model never saw the task as written.
- **An 8B model can drive the tool loop when the prompt is stripped** to three tools and no MCP
  servers. That makes `--strict-mcp-config` plus an explicit `--tools` list a functional
  requirement as well as a safety one.
- **Hooks load without `--bare`, and the prompt stays small (3.5k)**, but probe 4 still failed: one
  generation ran for five minutes without calling a tool. Probe 3 passing and probe 4 failing is
  one run each. Whether the difference is the extra ~1.5k of non-bare prompt or 8B being unreliable
  is **not established**; that needs several runs of each, which this machine makes expensive.
- **About 48s per turn on 8B when it works.** A real `doc-hygiene` pass is guessed at 30–60 minutes
  of ~8 GB occupancy. That guess is not measured.

## Revive when

- a machine runs a model at least as capable as 8B through probe 3's command at a per-turn time
  Chris accepts, and
- probe 4 passes reliably, say 5 runs out of 5: the command with hooks firing completes, and the
  repo's real ledger courier (not probe 4's logging hook) files a row carrying the local model's
  name.

Then it gets a `version:` and a `branch:`, and four features:

- **The table is a declaration:** the grammar in `core/config.py`, plus `dispatch --route`.
- **A Claude role runs on its declared model:** `cc-model-route.sh` and the `updatedInput` rewrite.
- **An Ollama role runs out of band:** `core/probe.py`, the rule 2 amendment, and the rendered
  command. Its first story is a go/no-go re-run of probe 4 on the new machine.
- **The ledger shows whether routing held:** the model column and the `check pm` warning.

It would be a minor bump, since it adds a config key, a hook and an output shape.

## Ship criterion

`agentic-sdlc dispatch --route doc-hygiene` on a machine where Ollama is running prints the
`ollama/*` entry and the command. Running that command completes the role's task with the repo's
hooks firing, and `pm ledger report` shows the run on the local model. With `local_routing` off,
the same route prints the skip line and falls back to `default`.

## Risks

- **Wall-clock is the product risk**, not the mechanism: "free" means the machine is occupied.
  Measure it per role through the ledger's time-per-state before calling a role a fit for a local
  model.
- **Quality at 8B is unmeasured** beyond a trivial edit. A local model editing `CLAUDE.md` (the
  `doc-hygiene` role) with no Claude fallback is an assumption, not a result.
- **`updatedInput` on the `Agent` tool** has not been tested in this harness (D2).
- **Claude Code's behaviour against a non-Anthropic endpoint** is not a published contract.
  `unrecognized_model` is already a warning today, and could become an error.
