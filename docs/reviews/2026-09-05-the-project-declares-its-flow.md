# Feature review — `0.2.0/the-project-declares-its-flow` — HOLD

Feature-level pass (SDLC.md §0, §6) over phase 6 of `0.2.0`, branch
`milestone/0.2.0-the-conveyor` at `f8e9e94`. The feature's code landed in two commits —
**`4e655e2`** (the reader, the two verbs, `render_seed`) and **`2b29b7b`** (the seed ships live,
`pm vocabulary`, the `config-updated` census) — and the feature file is still `status: planning`
with `reviewed:` empty and zero stories.

Adversarial by execution. Five scratch git repos under a temp directory, never this tree; the CLI
is `uv run -q --project /Users/cdowin/workspace/agentic-sdlc agentic-sdlc …` from each scratch
root. No `git` write command was run against this checkout and nothing under
`.claude/worktrees/` was read.

**The declaration is real and the refusals fire. Nothing reads the declaration.** The reader,
the validator, the seed, `render_seed()`, the two verbs and `pm vocabulary` all exist and behave
as the design describes when called directly. But `flow_of`, `holds`, `move_defect`,
`category_of` and `transition_target` have **zero callers outside `model.py`** — so the
no-fallback refusal that criterion 4 and milestone criterion 13 are written around never fires,
`init` never writes the section into a config it did not create, and the CHANGELOG, the refusal
string, `pm vocabulary`'s own output and one test all describe behaviour this release does not
have.

That is the additive seam working exactly as intended on the write side (no golden file moved,
no existing assertion changed) and failing on the read side (the criteria that say "refused",
"appends", "writes both" are unmet, and the tree says otherwise out loud).

## Blockers

### F1 (BLOCKER) — the no-fallback refusal has no caller: a tree with no `[pm.states.*]` runs every `pm` verb and `check pm` at exit 0

`model.flow_of` (`src/agentic_sdlc/repo/pm/model.py:718`) is the one refusal, and it is dead code
outside its own module:

```
$ grep -rn "flow_of\|move_defect\|category_of\|transition_target\|holds(" src/agentic_sdlc --include='*.py' | grep -v "repo/pm/model.py:"
src/agentic_sdlc/repo/pm/cli.py:1119:    `cfg.flows` directly and never goes through `model.flow_of`. `flow_of` is
```

One docstring mention. No call. Measured in a scratch repo whose `devkit.toml` was hand-written
with `[checks]` and `[pm]` and **no `[pm.states.*]` at all**:

| command | exit | output |
|---|---|---|
| `pm new milestone 0.1 First` | **0** | `[pm] created pm/roadmap/0.1-first/milestone.md` |
| `pm status` | **0** | `milestone 0.1        [planning]` |
| `pm list` | **0** | `[pm] 0 of 0 story/ies` |
| `pm validate` | **0** | `[pm] VALID — 1 grain(s), 0 ref(s)` |
| `pm milestone building 0.1` | **0** | `[pm] milestone 0.1: planning -> building` |
| `check pm` | **0** | `[check:pm] PASS — no PM-tree drift or integrity problems` |
| `check all` | **0** | every gate passed |

A verb that creates work, a verb that moves work and the gate that reads the tree all proceeded
on states the project never declared. `PmConfig.flows` was `{}` for every one of those runs and
no caller asked. Criterion 4 — *"A tree with no `[pm.states]` is refused by name"* — and milestone
criterion 13's *"a tree without it is refused by name"* are both unmet, measured.

The reader is not the problem: `_load_flows` (`model.py:519`) genuinely does not fall back, and
`cfg.flows == {}` is the absence rather than the seed. The gap is that nothing downstream ever
asks it a question.

### F2 (BLOCKER) — `init` has no append path; neither `init` nor `pm init` will write the section into a `devkit.toml` it did not create

Scratch repo with a hand-written `devkit.toml` (CRLF, `[checks]` + `[pm] review_dir`), sha
`c0b31402f01b54322976414d43ee2fbf18331007`:

```
$ agentic-sdlc init
[init] devkit.toml is yours — left alone (it differs from the template; `agentic-sdlc init --diff` shows how)
$ shasum devkit.toml
c0b31402f01b54322976414d43ee2fbf18331007  devkit.toml     # unchanged
$ grep -c "pm.states" devkit.toml
0
$ agentic-sdlc pm init          # writes .claude/, pm/roadmap/, .gitattributes
$ shasum devkit.toml
c0b31402f01b54322976414d43ee2fbf18331007  devkit.toml     # still unchanged
$ grep -c "pm.states" devkit.toml
0
```

`_write_seed` (`src/agentic_sdlc/repo/init.py:193-203`) reports the file as the project's and
returns; there is no `[pm.states.*]` branch beside `_write_gitignore`'s proven append shape
(`init.py:227-265`), which the feature record explicitly names as the model to copy. Every byte
is preserved — because nothing is written.

Criterion 2 (*"`init` run against an existing `devkit.toml` appends only the missing sections"*)
and milestone criterion 13's append half are unimplemented. Combined with F1 this is benign only
because F1 means the missing section costs the consumer nothing yet; the moment phase 7 wires
`flow_of` in, **every existing consumer is refused by a runtime that will not fall back, by a verb
that will not write the section, with nothing in between** — which is the exact sentence the
feature record wrote to justify putting the append path in this feature (`feature.md:71-73`).

### F3 (BLOCKER) — the refusal, `pm vocabulary` and a test all name `agentic-sdlc pm init` as the command that writes the section, and it does not

`model.py:733`:

```
Run `agentic-sdlc pm init` to write them; it appends to a devkit.toml it did not create and rewrites nothing.
```

Both clauses are false, measured in F2. `pm vocabulary` prints the same claim to a consumer's
terminal (`src/agentic_sdlc/repo/pm/cli.py:1206-1207`):

```
`agentic-sdlc pm init` writes exactly this,
appending to a devkit.toml it did not create:
```

and then indents `render_seed()` under it. The verb whose entire audience is the pin bump tells a
consumer to run a command that will leave the file untouched.

`tests/test_pm_flow.py:166` **locks the wrong string in**:

```python
assert 'agentic-sdlc pm init' in message
```

The builder knew. `tests/test_fixture_flows.py:32-38` says so in its own docstring: *"`agentic-sdlc
pm init` is a different verb from `agentic-sdlc init`, and it does NOT write the seed, though
`flow_of`'s refusal names it as the command that does … the case phase 7 has to make pass."*
Criterion 4 requires the refusal to print **the command that fixes it**; it prints one that does
not, and a test gates the wrong answer.

### F4 (BLOCKER) — the CHANGELOG states two behaviours this release does not have

`CHANGELOG.md:115` and `:121`, in the consumer-facing `### The project declares its flow` section:

| claim | measured |
|---|---|
| *"`init` writes both"* (`[pm.states.<kind>]` **and** `[pm.transitions.<kind>]`) | `installables/project-devkit.toml` has 16 uncommented lines, all `[pm.states.*]`. `render_seed()` emits no transitions table. Nothing writes one, ever. |
| *"Only the workflow verbs refuse a tree that has not declared a flow"* | No verb refuses. Seven commands measured at exit 0 in F1. |

`CHANGELOG.md` is what a consumer reads at a pin bump and CLAUDE.md makes it hand-maintained
precisely so it says what changed. Two of the three sentences describing the new section describe
something else.

## Non-blocking findings

### F5 (MAJOR) — the two state lists disagree in both directions, and the "state in no category" refusal does not exist at the CLI

`[pm] <kind>_states` and `[pm.states.<kind>]` are two scoreboards, and they contradict each other
today. Scratch repo, one `devkit.toml` edit each:

| declaration | `pm story <word> 0.1/thing/one` |
|---|---|
| `icebox` added to `[pm.states.story] todo`, absent from `[pm] story_states` | **exit 2** — `'icebox' is not a story status (planning ready building reviewing accepted packaging done)` |
| `limbo` added to `[pm] story_states`, in **no** `[pm.states.story]` category | **exit 0** — `[pm] story 0.1/thing/one: planning -> limbo` |

A state the project declared is refused; a state the project mapped to no category is accepted and
written to the file. Criterion 3's first clause — *"A state mapped to no category … exit 2"* — is
true inside `_flow_defect` for the cases the reader can see alone (unknown category, a state in
two categories, an empty category), and false for the case that requires the two lists to be
compared, because nothing compares them. This is D6's own worked example ("one shim, two call
sites, already out of step") reproduced with the new table as the second site. It dissolves in
phase 7 when `<kind>_states` is deleted; until then it ships.

### F6 (MAJOR) — `[pm.transitions.<kind>]` accepts a key that is not a published step, silently, and nothing reads the table anyway

```
$ printf '\n[pm.transitions.story]\nnot-a-real-step = "building"\n' >> devkit.toml
$ agentic-sdlc pm status   ; echo $?     # 0
$ agentic-sdlc check pm    ; echo $?     # 0
```

The feature record and `transition_target`'s docstring both state the key set is closed — *"a
project cannot invent a step"* — and `pm vocabulary` prints the registry under the words *"cannot
invent one"*. The reader validates the **value** (an undeclared target is exit 2, measured below)
and never the **key**. `model.load` refuses `[pm.scaffold.*]` eleven hundred lines earlier on
exactly this principle: *"a config key that silently does nothing is worse than one that errors,
because the author believes it took effect"* (`model.py:479-484`).

Compounding it: `grep -rn "transitions" src/agentic_sdlc/repo/conveyor/` returns **nothing**. No
belt step reads `[pm.transitions.*]`, so every transitions declaration in 0.2.0 is inert whether
its key is real or invented.

### F7 (MAJOR) — criterion 1's transitions half is unmet

Criterion 1: *"A fresh `agentic-sdlc pm init` writes `[pm.states.<kind>]` **and**
`[pm.transitions.<kind>]` as live TOML."*

The states half holds and holds well. Fresh scratch repo, `agentic-sdlc init`:

```
[init] wrote devkit.toml
$ grep -v '^\s*#\|^\s*$' devkit.toml         # 16 lines, all live
[pm.states.milestone] / [pm.states.feature] / [pm.states.story] / [pm.states.bug]
```

and `render_seed()` is a verbatim substring of the installable (asserted in-process:
`model.render_seed() in install.body_of('project-devkit.toml')` → `True`), so there is genuinely
one renderer. Second run: `[init] devkit.toml already current`, sha
`4bb978075562be5c7a2e67dd532afaad20e1246a` before and after — **byte-idempotent**.

No `[pm.transitions.<kind>]` is written by anything. `render_seed()` (`model.py:218-242`) loops
`FLOW_KINDS` emitting `[pm.states.<kind>]` only; the installable carries the transitions shape as
a comment at line 161; this repo's own `devkit.toml` declares none (`pm vocabulary` →
`[pm.transitions.story]` / `(this project declares none)`).

### F8 (MINOR) — `config-updated` asks the new sections but does not name them, so the pin-bump line is byte-identical across this release

Criterion 6 has two halves. The census half **landed** — A1 is fixed, `_config_readers()` is one
list of ten and the report derives from it:

```
broken [pm.transitions.story] story-done = "wombat"
  → Answer.no("1 of 10 section(s) hold a value 0.2.0 does not accept — [pm]: [pm.transitions.story] story-done = 'wombat', which [pm.states.story] does not declare …")
good config
  → Answer.yes("10 reader(s) accept this repo's devkit.toml; declared here: pm")
```

So the new sections **are** asked, through `model.load`. But they ride under the section name `pm`
and the pass line reads `declared here: … pm …` identically before and after the release, so
`config-updated` does not "name both new sections" to an operator bumping a pin. `pm vocabulary`
is the compensating surface and it does print the seed, which is why this is not a blocker.

### F9 (MINOR) — a fully renamed vocabulary does NOT get identical behaviour: `check pm` D5 stops measuring and says so

Milestone criterion 12. Scratch tree with all seven words renamed in `[pm.states.*]`, `[pm]
<kind>_states` and every grain file (`planning→icebox`, `building→in-dev`, `reviewing→crit`,
`accepted→blessed`, `packaging→boxing`, `done→shipped`, `obe→dropped`):

```
$ agentic-sdlc check pm
[check:pm] NOTE — D5 cannot place 'building' in [pm] story_states / feature_states, so it has no
split to compare a story against its feature across and is reporting nothing for this tree
[check:pm] PASS — no PM-tree drift or integrity problems; scanned 1 milestone(s), 1 feature(s), 1 story/ies, 0 bug(s), 0 ref(s)
```

Stock vocabulary emits no such line. A gate rule silently reduces its census to zero under a
renamed vocabulary — mitigated, and only mitigated, by the NOTE, which is the loud-failure posture
rule 4 asks for. It is the hardcoded `'building'` literal the flow declaration exists to remove,
and phase 7 owns it; criterion 12 is not met today.

There is also **no vendored fixture tree** with a renamed vocabulary. Criterion 12 asks for one
("proven on a fixture tree … vendored here per hard rule 8"); what exists is three unit cases over
`model.load()` strings (`tests/test_pm_flow.py:212,291,329`). Those are the cheaper tier and are
the right tier for what they assert — but they assert the reader, not behaviour.

### F10 (MINOR) — `tests/test_fixture_flows.py` justifies itself with a claim that is false today

Its docstring (`:4-6`): *"`model.flow_of` … exits 2 by name when a tree declared nothing, and the
engine's questions route through `model.holds`."* No question routes through `model.holds` (F1).
The census therefore asserts a precondition for a call that never happens: if a fixture builder
stopped declaring a flow today, nothing would fail. 239 lines of forward cover for phase 7, which
is a defensible thing to have — but the module's stated reason for existing has to say that, or
the next reader trusts it as a live guard.

### F11 (MINOR) — criterion 7's test does not exist

*"A test asserts no engine question changed."* I could not find one; `grep` for the claim across
`tests/test_pm_flow.py` returns only prose in the module docstring. The seam itself **is** intact,
measured from the commits rather than from a test: `4e655e2` deleted nothing from `tests/`, and
`2b29b7b`'s only deletions inside existing cases are its own new seed assertions being rewritten
(`assert flow.order == model.LIFECYCLE` → the `obe` form) plus unrelated `close`-belt edits. No
golden file moved. So the criterion's substance holds and its gate does not exist, which means
phase 7 has nothing to break.

### F12 (NIT) — `pm status` column width shifts under a renamed vocabulary

`[planning]` vs `[icebox  ]` in the feature row — the bracket is padded to the longest declared
word, so a renamed tree's output is not diff-identical to a stock one even where the semantics are.
Cosmetic; noted only because criterion 12 says "identical".

## What each criterion was judged by

| # | criterion | verdict | the measurement |
|---|---|---|---|
| 1 | `init` writes both tables live, reproducing `LIFECYCLE` | **partial** | fresh `init` in scratch: 16 live `[pm.states.*]` lines, `render_seed()` a verbatim substring of the installable; **no `[pm.transitions.*]` written by anything** (F7) |
| 2 | `init` appends missing sections to an existing config, byte-preserving, idempotent | **FAIL** | hand-written CRLF `devkit.toml`, sha unchanged after both `init` and `pm init`, `grep -c pm.states` = 0 (F2) |
| 3 | state in no category / in two, transition to an undeclared state → exit 2 naming the key | **partial** | in two → exit 2 both `pm status` and `check pm`; unknown category → exit 2; empty category → exit 2; transition to `"wombat"` → exit 2; wrong-typed target → exit 2; unknown grain kind → exit 2. **State in no category is exit 0 at the CLI** (F5); an invented step key is exit 0 (F6) |
| 4 | a tree with no `[pm.states]` refused by name, refusal prints the fixing command | **FAIL** | seven commands at exit 0 on a flow-less tree (F1); the command printed does not write the section (F3) |
| 5 | `pm vocabulary` prints categories, states and transitions; the old sentence is gone | **PASS** | `pm vocabulary` on this tree prints the three categories, all four kinds' state maps, `[pm.transitions.story] (this project declares none)`, the published step registry and `rules …`; the retired sentence survives only as a historical note at `cli.py:1110`. A renamed tree prints its own words (`tests/test_pm_flow.py:329`, run) |
| 6 | `config-updated` names both new sections, census = what it asked | **partial** | 10 asked / 10 named, A1 landed; a broken `[pm.transitions]` → `1 of 10 section(s)`; the two new sections are not separately named (F8) |
| 7 | a test asserts no engine question changed | **partial** | the seam holds (no golden moved, no existing assertion changed across `4e655e2` + `2b29b7b`); the test does not exist (F11) |
| M11 | the two verbs exist | **PASS** | `move_defect`, `holds`, `category_of`, `transition_target`, `flow_of` all present with tests (`tests/test_pm_flow.py::TestHolds`, `::TestMove`). D6 assigns the routing to phase 7, so "they exist" is the whole of what phase 6 owes |
| M12 | renaming every state word gives identical behaviour | **FAIL** | D5 emits `NOTE — D5 cannot place 'building' …` and reports nothing; no vendored renamed fixture tree (F9, F12) |
| M13 | `init` writes the flow and appends it; runtime reads every run, no fallback, refused by name with the fixing command | **FAIL** | writes: yes (states only). appends: no (F2). reads every run: the reader runs, nothing consumes it (F1). refused by name: no (F1). fixing command: wrong (F3) |

## Rule 4 and rule 5, asked directly

- **Rule 4, read side — is there a fallback silently supplying the engine's old opinion?**
  Not in the reader. `_load_flows` returns `{}` for an absent declaration and `PmConfig.flows`
  defaults to an empty dict, and a partial declaration is refused by name rather than half-honoured
  (`model.py:578-584`, exercised). The old opinion survives instead in the **unreplaced** path:
  `[pm] <kind>_states` + `also_done` + D5's `'building'` literal still answer every question, so
  a project that declares a flow and expects it to govern gets the shipped words anyway. That is
  the additive seam by design — but it is why F1's refusal must not be described as live.
- **Rule 5's split — does a GATE ship stock defaults and a WORKFLOW not?**
  Half-held. `check doc`, `check shell` and `check repo-hygiene` are untouched and run identically
  on a `devkit.toml`-less tree (measured: `check all` exit 0 in the flow-less scratch). The
  workflow half is not built: no workflow verb refuses. `check pm` is the awkward case and it is
  correctly on the gate side today — it passed on a flow-less tree — but the design has it reading
  categories in phase 7, at which point which side of the split it sits on needs a ruling.

## What was NOT verified

- **`make precommit`, `make test`, `make milestone` and the interpreter matrix were not run.** The
  slice was `tests/test_pm_flow.py tests/test_fixture_flows.py tests/test_init_verb.py
  tests/test_pm_scaffold.py` → **88 passed, 25 subtests, 14.30 s** on 3.11, my run. Nothing was run
  on any other interpreter.
- **`agentic-sdlc adopt` was never walked end to end.** `check_config_updated` was called directly
  in-process against two scratch configs; the other nine adopt steps were not exercised and the
  `pin-bumped` / `runner-targets-resolve` steps cannot pass in this repo anyway.
- **The `bug` kind's flow was only read, never driven.** I declared and refused `[pm.states.bug]`
  variants but never ran `pm bug` through a renamed bug vocabulary, so the claim that a bug's
  `open`/`fixed`/`closed` "stops being a special case" is untested by me.
- **`pm vocabulary --json` was not run.** I read the payload construction and ran the plain
  renderer; the JSON path is covered by `tests/test_pm_flow.py::TestVocabulary` in the slice above,
  which passed, but I did not diff a payload myself.
- **No CRLF byte-preservation assertion was possible for the append path**, because there is no
  append path (F2). The CRLF scratch config proved only that the file was left alone.
- **`install-*` verbs other than what `agentic-sdlc init` invokes were not exercised**, and I did
  not check whether any consumer-facing installable other than `project-devkit.toml` mentions the
  new section.
- **I did not re-derive the milestone's other criteria (1-10, 14)** — they belong to other features
  and the milestone review.
- **Nothing under `.claude/worktrees/` was read**, per the brief; if another agent is landing this
  feature there, this review describes `f8e9e94` and not that work.
- **`check doc` did not scan this record and its PASS is not evidence about it.** `DEFAULT_SCOPE`
  is `CLAUDE.md` + `.claude/rules/*.md` + `.claude/agents/*.md` and `docs/reviews/` is in
  `DEFAULT_EPHEMERAL` (`src/agentic_sdlc/repo/checks/doc.py:51,73`), so the run reported
  `5 doc(s) … 0 unresolved claims` over a census this file is not in. What was actually proven
  about the block below is `verdict.parse()` on this file: one block, `HOLD`, 12 findings, every
  severity and disposition accepted.
- **The feature file was not touched.** `pm/roadmap/0.2.0-the-conveyor/features/the-project-declares-its-flow/feature.md`
  is still `status: planning` with an empty `reviewed:` and no stories; this record is not yet
  pointed at from the tree, so `check pm` D1 has nothing to resolve here.

Reviewer's token cost: ~165k.

```
verdict: HOLD
| id | severity | disposition |
| F1 | BLOCKER | landed 32b20b1 |
| F2 | BLOCKER | landed ada37ae |
| F3 | BLOCKER | landed ada37ae |
| F4 | BLOCKER | landed ada37ae |
| F5 | MAJOR | open: dissolves when phase 7 deletes [pm] <kind>_states |
| F6 | MAJOR | rejected: superseded — [pm.transitions.<kind>] is deleted and a leftover table is refused by name (story 01, 1e01518) |
| F7 | MAJOR | rejected: superseded — nothing writes a transitions table any more; criterion 1's transitions half was retired with the key (story 01, 1e01518) |
| F8 | MINOR | open |
| F9 | MINOR | open: owned by phase 7 |
| F10 | MINOR | open |
| F11 | MINOR | open |
| F12 | NIT | open |
```
