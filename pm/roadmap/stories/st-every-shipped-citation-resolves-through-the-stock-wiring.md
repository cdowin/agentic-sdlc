---
id: st-every-shipped-citation-resolves-through-the-stock-wiring
kind: story
feature: ft-every-printed-command-runs-in-a-stock-consumer
milestone: "ms-a-consumer-can-take-the-bump"
name: every shipped citation resolves through the stock wiring
status: building
owner: agent
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
