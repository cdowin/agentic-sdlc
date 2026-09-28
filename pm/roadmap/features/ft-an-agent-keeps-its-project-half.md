---
id: ft-an-agent-keeps-its-project-half
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: an agent keeps its project half
status: done
reviewed: docs/reviews/2026-09-27-0.15.0-an-agent-keeps-its-project-half.md
depends_on: []
consumed_by: []
changelog: install-agents keeps each agent's closing ## Project section byte for byte under --force and refuses by path a file whose section breaks the grammar; the developer runs at effort high, the reviewer at medium with a 25-call budget, and review findings go to a new developer.
---

# an agent keeps its project half

A consumer runs the four agent definitions as FORKS, not installs: its copies carry no GENERATED
marker, and its `[adopt] ours` claims all four. The fork exists for one reason. An installed agent
has nowhere to keep project prose (domain expertise, an anti-pattern list), so `install-agents
--force` would erase it. Meanwhile the fork learned things the package never got, each measured on
real milestones. This feature gives the project half a place to live, and ports the generic half.

## Decided (do not re-plan)

- **A kept `## Project` section, by text rules only.** Chris, 2026-09-27 (D10, D12). No model
  reads or judges the section; `install.py` finds it with line matches, the way `_markdown_block`
  finds the `## Project config` fence today. The grammar, exact:
  - the section opens at the one line that is exactly `## Project` (trailing blanks allowed);
  - it runs to end of file, so it MUST be the last `## ` heading; `###` and deeper are allowed
    inside it;
  - there is exactly one such line in the file.
  `install-agents --force` replaces every byte before that line with the kit's text and keeps
  every byte from it to EOF. A file with no `## Project` line gets the stock section (one comment
  line saying what belongs there). A difference confined to the section, or to the config fence,
  is CURRENT.
- **The lint.** A file that breaks the grammar — two `## Project` lines, or a `## ` heading after
  it — is never merged by guess. `install-agents` (check mode) reports it as a finding naming the
  path, the line and the rule broken, exit 1. `install-agents --force` refuses THAT file by path
  and says why, and writes the others (rule 3). A near miss (`## project`, `## Project notes`,
  `##Project`) is not the section, and a check-mode finding names it as a near miss so it is never
  silent (rule 11).
- **Frontmatter is the kit's.** `--force` resets `model`, `effort`, `tools` and `description`; no
  `[agents.<role>]` key this milestone. Name the section and its grammar in `install-agents
  --help` and in the comment at the top of each agent (rule 11).
- **Effort defaults.** Chris, 2026-09-27 (D9). `developer` effort `high` ("the brief might be
  wrong"); `reviewer` effort `medium`, with the budget below. `architect` stays `high`,
  `tech-writer` stays `sonnet`/`medium`. `model: opus` stays: it resolves to the current Opus.
- **Fix two defects.** `architect.md` `## Project config` fence line 1 is a truncated fragment
  (`GDK_PRECOMMIT_TIERS)`): restore the per-change-gate key line. `developer.md` step 9 says fixes
  come back "on the same branch", but the loop merges a lane before review, so that branch is gone:
  replace it with D8 (below).
- **architect — port.** Land findings of 10 lines or fewer yourself, and send the rest as ONE
  developer dispatch. An edit under 50 lines is the orchestrator's and is never dispatched (was
  1–3 files). Report with a numbered NEEDS YOU first, numbers not adjectives, and what was NOT
  verified. At startup run `pm next` and read the milestone's handoff. Before the milestone
  close, sweep stashes, merged branches and dangling worktrees (`agent-worktree.sh list`).
- **developer — port.** One builder does a feature's stories in order; read three things up
  front (the dispatch, the feature, the first story) and the rest on demand; no repeated
  orientation or precommit per story. Batch new design decisions into one sheet and one question.
  Stop when a criterion would change what the user sees or contradict a recorded decision. A
  commit that deletes a name greps its callers first; a reviewer's word is not a caller grep.
  Close evidence and one changelog sentence per grain go in the REPORT. Regenerate derived files
  and commit them with their source; never hand-edit a generated file. The report ends with NEEDS
  YOU and NOT verified. **Testing core:** what earns a unit test; test the contract, not the
  internals; a test owns its state; a test asserts the live path.
- **reviewer — port.** A hard budget: 25 tool calls or fewer, read the range diff not whole
  files, a record of 40 lines or fewer. Verify a claim only when a wrong claim would break
  behaviour. Stop at the blunders: 2 CRITICAL + 3 MAJOR is a complete review. Report in 10 lines
  or fewer, with which finding to land first and the tool-call count. The record gets no commit of
  its own; it rides the orchestrator's close commit. For a bucket (#66), key each fenced verdict
  block with `feature: <id>` (#79, D6). The testing core above is also a review lens.
- **tech-writer — port.** Read the tree through the kit (`changelog`, `pm status`, `pm ledger
  show`); `ls`/`find`/`grep` for a fact the kit prints is a reject. Audit method: a stale spec is
  fixed; a code gap is a bug, never a spec rewrite that hides it; a spec says what is, not what
  was; prove a comment-only edit with a filtered `git diff`.
- **Leave out** anything that names a language, engine, product or person (rule 8). Pattern
  catalogs stay project text: they go in `## Project`.
- **Self-host.** Re-install this repo's `.claude/agents/` with `install-agents --force`.

## Ship criterion

- `install-agents --force` over an agent whose `## Project` section holds three lines keeps them
  byte for byte, and `install-agents` (check) reports it CURRENT.
- An agent with a `## ` heading after `## Project` is a finding in check mode (exit 1) and is
  refused by path under `--force`, and the other agents are still written. `## project` is named
  as a near miss.
- The installed `developer` is effort `high`; `reviewer` is effort `medium` and states the budget.
- `architect.md`'s fence has no truncated line; `developer.md` names the D8 finding return.

## Proof budget

  cases: 5
  tier: unit
  lands in: the existing install test module (the fence-kept case is the one to amend)
  what already covers this: the `## Project config` fence round-trip; amend it for the new section
