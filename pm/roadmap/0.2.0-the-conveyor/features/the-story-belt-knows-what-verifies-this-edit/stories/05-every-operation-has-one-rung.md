---
id: 0.2.0/the-story-belt-knows-what-verifies-this-edit/05-every-operation-has-one-rung
feature: 0.2.0/the-story-belt-knows-what-verifies-this-edit
milestone: "0.2.0"
name: The ladder has three rungs and each names the composition that is it
status: done
owner:
depends_on: []
---

# The ladder has three rungs and each names the composition that is it

`agentic-sdlc verify --story | --feature | --milestone` answers *what proves this, at this
altitude* — and `--plan` prints all three with their measured costs, so a dispatch author can
see which is the loop and which is the close instead of guessing.

**Chris, 2026-09-05:** *"finishing a story or adopting a new devkit version shouldn't be a huge
milestone check. The checks should all have their place."*

## Why this story exists at all

Two gaps, both in `decisions.md` **D3**:

1. **The middle rung had no command.** `design-the-three-belts.md` names three belts;
   `[verify]` as designed declared two levels. The feature belt was described and unbuilt, and a
   ladder with a hole in the middle is a ladder where a story close reaches for `make
   milestone`.
2. **Two mechanisms answered one question** — `[verify] wide` and `make milestone`. Nothing tied
   them, so CI could run one while a dispatch quoted the other.

D3 rules that `[verify]` names **which rung a composition is**, and the Makefile stays the
authority on what that target runs. Do not re-open it; implement it.

## The config, after this story

```toml
[verify]
feature   = "make precommit"     # the range, one step wider. Once per feature.
milestone = "make milestone"     # everything, every interpreter. Once.

[[verify.narrow]]                # the story rung — rules, because the PATHS decide
paths = "src/agentic_sdlc/repo/pm/**"
run   = "python3 -m pytest tests/test_pm_*.py"
```

`wide` is **renamed** to `milestone`. It is a config key in a release that has not shipped, so
this is a rename and not a migration — but story 01 owns the reader, so coordinate rather than
edit its grammar from here.

## Acceptance criteria

1. `verify --story` (alias `--changed`), `--feature`, `--milestone` each run exactly the rung
   named, and **nothing above it**. A test asserts `--story` never invokes the `milestone`
   command — that is the 170x, as an assertion.
2. `verify --plan` prints all three rungs, in order, each with its command and its **measured**
   cost from the ledger where `every-gate-reports-its-cost` has recorded one, and the word
   `unknown` where it has not. **Never a guessed number** — a fabricated ratio is worse than no
   ratio, because it gets quoted.
3. A rung with no config entry is named and exits 2 — never a silent skip that reports success
   for a rung nobody ran. Same posture as story 01's missing `[verify]`.
4. `--feature` **does not claim to be range-scoped.** It runs the composition the project names.
   Scoping to a feature's commit range needs that feature's first commit, which is derivable
   from the ledger and is not derived in 0.2.0. The docstring says so in one line: a rung that
   claims a narrowing it does not perform is a false PASS with a scope on it.
5. The ladder table from D3 ships in `README.md` — one row per operation, one verb, one scope.
   That table is what a consumer reads to know a pin bump is not a milestone check.

## Out of scope

- The `[verify]` grammar and its refusals — story 01.
- The forward and reverse selectors — stories 02 and 03.
- `adopt`, which is not a rung: it is an operation on the toolchain, and it borrows the story
  rung's narrowing idea without having a grain to close (`0.2.0/adopt-is-a-conveyor`).
- Deriving a feature's commit range. Named in criterion 4 as the honest gap.

## Files

Touch: `src/agentic_sdlc/repo/verify/main.py`, `devkit.toml` (this repo self-hosts the three
rungs), `tests/test_verify_main.py`, `README.md` table (PROPOSED to the orchestrator).
Depends on stories 01–04 of this feature.

## Close

done: fb8fa2a 6e9388d — D3's ladder, and README carries the table. [verify] names WHICH RUNG
a composition is; the Makefile stays the authority on what it runs.
finding: cc0569d — 15 narrow rules named `python3 -m pytest` and bare python3 here has no
pytest. verify --check passed them; `close story` found it.
