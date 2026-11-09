---
name: quality-setup
description: Use in a new repo before its first feature PR, or when a repo adopts the lenses. It finds the stack, measures main, turns the lens gates and the ratchet on at today's counts, adds the make targets and the CI step, and writes the repo overlay for the reviewer.
---

# quality-setup

## Why and when

A repo that turns on strict rules starts red. This skill turns them on at the counts of today, so
no rule starts red and every count can only go down. Run it once, in a new repo before its first
feature PR, and again when a repo adopts the lenses. A new repo runs it first: the agent runs
this skill as the first task, before the repo takes its first feature issue. No other skill changes.

## Run

Do the steps in order. Each step checks before it writes (see Idempotence).

1. Detect the stack from files: `package.json` and `tsconfig.json` is `node-ts`; `react` in
   the dependencies of `package.json` is `react-ts`; `pyproject.toml` or `requirements*.txt` is
   `python`; `pom.xml` or `build.gradle` is `java`; `Chart.yaml` or `*.tf` is `helm-terraform`.
   A repo may match more than 1 pack: run the steps for each.
2. Read `stacks/<pack>.md` in this skill folder. It names the lint tool and its config key. When
   the pack is still a stub, say so in the report and use the repo's own lint tool.
3. Measure main. Run `RATCHET_WRITE=1 CHECKS=ratchet sh checks/checks.sh` for the ratchet counts,
   then the stack's lint tool for its counts per rule. The first write run creates the counts file.
   Generated files: set `RATCHET_EXCLUDE` (an ERE of paths not measured, such as `\.gen\.ts$`).
4. Write the lint config at the measured counts, so no rule starts red. A rule with 0 findings
   is on at 0. A rule with findings is on at its count, or at warning level when the tool has
   no count limit. Never turn a rule off to get green.
   Onboard by tool kind:
   - A tool with a count limit: set it to today's count. This beats a file list.
   - A tool with warn level only: `--max-warnings` per package at today's count. Never 1 pool for
     correctness rules. A preset rule that is an error needs a warn mapping first.
   - A tool with neither: a per-file ignore exempts the whole file. Say so, list the files, and
     have a reviewer check new code there. This is weaker than a count limit.
5. Add the Makefile targets: `lint`, `validate` (lint plus the repo's tests), `ratchet` and
   `ratchet-lower` (the same with `RATCHET_WRITE=1`).
   `ratchet` runs `CHECKS=ratchet EVENT=push sh $(CHECKS_SH)`, with `CHECKS_SH ?= checks/checks.sh`.
   When the repo has no copy of `checks/checks.sh`, copy it from the kit first.
6. Add the CI step `uses: cdowin/agentic-sdlc/checks` with `checks: ratchet`. Use the version
   pin the repo already uses for its other kit checks. Do not invent a pin.
   No route to github.com actions: copy `checks/checks.sh` into the repo (header: source and
   version), set `CHECKS_SH`, and run `make ratchet` in an existing CI job.
7. Write the repo overlay: the reviewer loads `CONSTITUTION.md` and `.claude/review-lens.md`
   (see `../LENSES.md`). Read the existing file first. Add only the sections it lacks:
   - Purpose: 1 paragraph on what the repo is for.
   - Rules we enforce by gate: the lens rule IDs whose Check is `gate`, and the make target
     or CI step that enforces each.
   - Rules a reviewer judges: the lens rule IDs whose Check is `review`.
   - Ratchet: where the counts file is, and the rule: it only goes down. When a file is
     renamed, move its row by hand.
8. Report what the team must write itself: domain rules, the rules marked `review` that need
   local detail, and the exceptions.

## Idempotence

A second run changes no file. Each step checks first:

1. Detect: reads files only.
2. Read: reads files only.
3. Measure: write mode never adds a row and never raises one; it leaves a file with nothing to
   lower byte-identical.
4. Lint config: compare each rule with the measured count; write only a rule that differs.
5. Make targets: search the Makefile for each target name; add only a target that is absent.
6. CI step: search the workflow files for `cdowin/agentic-sdlc/checks` with `ratchet`; add it
   only when absent.
7. Overlay: search for each section heading; add only a heading that is absent.
8. Report: reads only.

## The ratchet

The check is `ratchet` of `checks/checks.sh`. It is opt in: put it in `CHECKS` yourself. The
counts file is `.quality-ratchet` (env `RATCHET_FILE`, action input `ratchet_file`). It has 1
row per line: `rule`, `path` and `count`, separated by tabs, with no header and no zero row,
sorted with `LC_ALL=C`.

It measures code files only (ts tsx js jsx mjs py java; tests and docs are skipped) with 2 rules:

- `magic-number` (CP-4): lines with a number above `RATCHET_MAX_PLAIN` (default 2); a hex
  literal counts. Comment lines, string and template-literal contents, and named constant lines
  (`MAX = 10`, `const maxRetries = 3`) do not count. A line counts once.
- `long-file` (CP-7): the lines of a file above `RATCHET_MAX_LINES` (default 300).

How to read it:

- `::error title=ratchet::<rule> <path> is <n>, the file allows <m>`: your change added
  findings. Remove the new ones. Never raise the file by hand.
- `::warning title=ratchet::<rule> <path> dropped from <m> to <n>`: the code got better.
  Lower the file.
- `::error ... is missing`: run this skill first.

To lower the file, run `make ratchet-lower` (or `RATCHET_WRITE=1 CHECKS=ratchet sh checks/checks.sh`) and commit it. Write
mode keeps the lower of the two counts, removes a row that reached 0, adds no row and never fails.
