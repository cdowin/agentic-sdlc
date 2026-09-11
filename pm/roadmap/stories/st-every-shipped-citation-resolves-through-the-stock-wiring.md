---
id: st-every-shipped-citation-resolves-through-the-stock-wiring
kind: story
feature: ft-every-printed-command-runs-in-a-stock-consumer
milestone: "ms-a-consumer-can-take-the-bump"
name: every shipped citation resolves through the stock wiring
status: planning
owner:
depends_on: ["st-the-stock-wiring-has-one-vehicle-and-the-cli-prints-it"]
changelog:
---

# every shipped citation resolves through the stock wiring

Issue: #22 (the shipped prose, and the test that holds it).

About 109 backticked `agentic-sdlc <verb>` citations across 23 files under `installables/` and
`pm/guidance/` (measured on origin/main; #22 counted 106 across 20). The worst:

- `pm-operator.md:16`, the agent's first instruction: *"Run `agentic-sdlc dispatch --grain <id>
  --role <role>`"*, which is `command not found` in a stock consumer;
- every role brief's role-verbs block (`agentic-sdlc pm new|add|status|…`);
- `pm-execution.md`'s `agentic-sdlc close story <id>` and six more like it.

One consumer fixed `pm-operator` by writing the vehicle into its Project config block. That fixes one
agent and none of the rest.

**Sequencing:** after `st-the-stock-wiring-has-one-vehicle-and-the-cli-prints-it`, which fixes the
spelling. After `ft-the-shipped-words-match-the-shipped-tool`, which rewrites some of the same
sentences. This is a sweep, so it goes last.

## Acceptance criteria

1. Every shipped citation of a CLI verb uses the vehicle's spelling, or sits in a context that
   defines its own (the CI `.yml` files and `project-Makefile` may, so check each one before
   rewriting it).
2. A unit case scans every shipped text file for CLI-verb citations and resolves each one through the
   stock consumer wiring. It fails by file and line on any citation the wiring cannot reach, and FAILS
   when it scans zero files (rule 4). It extends the 0.6.0 role-verb citation test rather than adding
   a new module.
3. Deliberately broken probe: plant a bare `agentic-sdlc lesson` citation in a scratch copy of one
   brief, and the case goes red naming it.
4. Every affected installable is re-installed here, and `installables-current` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 2, 3 | unit | the citation census, with a planted-violation corpus | amend the 0.6.0 role-verb citation test |
| 4 | unit | tests/test_install.py byte-current | yes |

## Semver

Minor, together with the previous story (the installed text changes to name a new target).
