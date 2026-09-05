---
id: 0.2.0/the-story-belt-knows-what-verifies-this-edit
milestone: "0.2.0"
name: A changed path resolves to the command that proves it
status: planning
reviewed:
risk: high
size: m
phase: 3
depends_on: ["0.2.0/the-middle-tier-splits"]
consumed_by: ["0.2.0/the-release-is-a-conveyor"]
labels: ["belts", "verify", "config", "economics"]
---

# A changed path resolves to the command that proves it

**Split out of `the-release-is-a-conveyor` on 2026-09-05.** That feature was `size: xl` carrying
four deliverables; this is the one `design-the-three-belts.md` calls *"the first thing to
solve, because it is what every other layer's economics rest on"*, and it does not survive being
the fourth item in an XL.

## Why — the 170x, and that it was a DISPATCH defect

Measured 2026-09-04: a full suite is **154 s**, a single module **0.9 s**. An agent fixing eleven
failures ran the full suite after each one — **31 minutes**. Re-checking the same five modules
afterwards took **13 seconds**.

The agent was not careless. **The dispatch said *"VERIFY: `pytest tests/ -q`"* and named nothing
else.** An agent given one command uses it as its inner loop, because nothing told it there was
another. `SDLC.md` §4 already says builders run scoped slices; it cannot say *which* slice,
because nothing in the toolchain knows.

Two consumers each invented an answer, locally, and neither is discoverable: one slices unit
tests by system directory (`unit SYS=<x>`), one reads a `## covers:` header out of integration
scenarios to pick tests from a diff. Right idea, invented twice, visible to nobody.

## The declaration

```toml
[verify]
wide = "make check test"           # the close. One command. Always defined.

[[verify.narrow]]                  # FORWARD: a glob with a named capture
paths = "src/agentic_sdlc/repo/pm/**"
run   = "python -m pytest tests/test_pm_*.py"

[[verify.narrow]]
paths = "tests/test_<name>.py"
run   = "python -m pytest tests/test_<name>.py"

[[verify.narrow]]                  # REVERSE: the test declares its own coverage
declares = "## covers:"
scan     = "tests/integration/**"
run      = "make scenario NAME=<stem>"
```

**Both directions ship; neither is chosen over the other.** Forward suits unit tests, where the
mapping is structural. Reverse suits integration, where only the test knows what it exercises
and no path rule could infer it.

## Three properties, each because leaving it out produces a silent lie

- **Captures deduplicate.** Five files under one captured directory produce ONE command, not
  five. Without this the narrow path re-runs the same slice per file and stops being narrow.
- **A miss is LOUD and falls back to wide.** A changed path matching no rule is named, and the
  wide command runs. **A narrow verifier that matches nothing and exits 0 is worse than no
  verifier** — it reports success for work it never checked. This is rule 4's read-side cardinal
  sin wearing a new hat, and it is the single most dangerous failure in the design.
- **The declaration is checkable.** A rule whose glob matches no tracked file, or whose `run`
  names a target that does not exist, is a finding — same posture as a stale allowlist entry. A
  rule set nobody validates rots into one that quietly matches nothing.

## The verb

```
agentic-sdlc verify --changed [--ref <git-ref>]   # what proves the diff
agentic-sdlc verify --plan    [--ref <git-ref>]   # print the commands, run nothing
agentic-sdlc verify --check                       # validate [verify] itself
```

`--plan` is what a dispatch prompt embeds, and it is why the verb is worth more than a make
target: **an orchestrator writing a dispatch can ask the repo what the narrow command is instead
of guessing**, and the answer stays true as the tree grows.

## It reports the ratio, and that is what makes the rule obvious

With `every-gate-reports-its-cost` recording durations, `--plan` prints narrow-vs-wide with real
numbers. **A 1.2x ratio does not justify a two-command dispatch; the measured 170x does.** The
ratio is what turns "run the narrow thing first" from advice into a fact an agent can act on.
Absent ledger data the verb prints the commands without a ratio and says the ratio is unknown —
never a guess.

## Ship criterion

1. `verify --changed` on a diff touching N files under one captured directory runs the slice
   **once**.
2. A changed path matching no rule prints that path and runs `wide`. A test proves the exit code
   and the named path, on a repo whose rules deliberately miss.
3. `verify --check` fails a rule whose glob matches zero tracked files and a rule whose `run`
   names a nonexistent target, each with the rule's own index in the message.
4. A repo with no `[verify]` section: `--changed` says so and exits 2 (config, not findings) —
   never a silent zero-command pass.
5. The refusal matrix per `SDLC.md` §5, since `paths`/`run`/`declares` are a new input surface:
   traversal, absolute paths, shell metacharacters in `run`, a capture that appears in `run` and
   not in `paths`, an empty rule list.

## Risks

1. **`run` is a shell command from config**, which is a wider grammar than `[gates] extra`'s
   make-goal. It is executed, so the refusal matrix is the feature, not a courtesy. The
   defensible line: `run` is passed to a shell deliberately (a project's verification IS a
   command line), so the guard is that it comes from a tracked file the repo owns — and
   `--plan` exists so a caller can read it before it runs.
2. **A capture grammar is a parser**, and this package has shipped a false PASS from a config
   value read carelessly before (`tuple(cfg.get(...))`, seven gates, v0.9.0). Every value goes
   through `core/config.py`.
3. **The reverse direction reads other people's files.** A `declares` scan over a tree with no
   matching header must be a loud zero-census, not an empty pass.
