---
id: st-every-shipped-citation-resolves-through-the-stock-wiring
kind: story
feature: ft-every-printed-command-runs-in-a-stock-consumer
milestone: "ms-a-consumer-can-take-the-bump"
name: every shipped citation resolves through the stock wiring
status: done
owner: agent
depends_on: ["st-the-stock-wiring-has-one-vehicle-and-the-cli-prints-it"]
changelog: Every command the shipped agent briefs, rules, skills, SDLC template, seed `devkit.toml` and project templates tell you to run is now spelled through the stock wiring — `make sdlc ARGS='…'` or `make pm ARGS='…'` — so it runs in a consumer with nothing else on PATH, and `check doc` reads those spellings as the status calls they are.
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

## Amended from the spec scout (C2, M3)

5. **`check doc` keeps seeing the swept spans (C2):** `_STATUS_FORM` (`checks/doc.py:173-174`)
   matches `make pm ARGS="<kind> <state> …"` and `make sdlc ARGS="pm <kind> <state> …"` as well as the
   bare form. Probe: plant `make pm ARGS="feature reviewing x"` in a scratch consumer with no
   `reviewing` feature state, and the gate FAILS. Without this, the sweep blinds the #26 fix and the
   0.6.0 status-form rule, and the gate prints PASS over drift. **This story therefore also touches
   `checks/doc.py`, after `st-check-doc-reads-a-code-span-across-a-line-break` lands.**
6. **The census scope, named (M3).** At HEAD there are 148 citations, 111 backticked; 142 of them are
   `agentic-sdlc <verb>` strings across 19 `.py` files.
   IN: backticked and unbackticked commands in shipped prose (`installables/`, `pm/guidance/`,
   `sdlc-template.md:10-13`, `doc-hygiene.md:23`), fenced and indented blocks, and every string the
   CLI renders for a person to RUN: hints, `next:`, RECORDING, STATIC GATES, `init`'s next steps.
   OUT: `usage:` synopses, `agentic-sdlc <verb>:` error prefixes, GENERATED headers and help bodies
   that NAME the CLI rather than instruct a run.
   The census regex is not backtick-bound. The two existing role-verb tests are rewritten, not amended,
   because after the sweep they match nothing.

## Close

done: 9840e91 — 102 shipped `agentic-sdlc <verb>` citations -> 0 (94 prose in 19 files, 3 quote fixes, 5 rendered strings); 156 left OUT by named class (headers, error prefixes, help bodies, usage, records); `tests/test_install.py::EveryShippedCitationResolvesThroughTheStockWiring` replaces the 0.6.0 role-verb pair (fails by file:line, fails on zero files, floors the vehicle-line count); `check doc` reads vehicle spans through `vehicle.argv_of` (C2). SHIPPED_ACTION values kept: each records what a belt itself ran. The install-day test now installs the gates with the agents, because the briefs cite make targets.
