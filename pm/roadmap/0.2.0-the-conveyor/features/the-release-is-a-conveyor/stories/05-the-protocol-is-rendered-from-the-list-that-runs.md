---
id: 0.2.0/the-release-is-a-conveyor/05-the-protocol-is-rendered-from-the-list-that-runs
feature: 0.2.0/the-release-is-a-conveyor
milestone: "0.2.0"
name: The protocol a consumer reads is rendered from the list that runs
status: done
owner:
depends_on: ["0.2.0/the-release-is-a-conveyor/02-the-step-list-is-the-projects", "0.2.0/the-release-is-a-conveyor/03-the-gate-cannot-run-before-the-review-landed"]
---

# The protocol a consumer reads is rendered from the list that runs

A consumer runs `agentic-sdlc install-sdlc` and gets a document describing **its own**
`[release] steps` and `[adopt] steps` — each step in order, its kind, its postcondition, and
what a human must do when the machine refuses. Change the config, re-run the verb, and the
document changes with it. There is nowhere left for the protocol to disagree with itself,
because there is only one copy of it and the machine owns it.

This is not a documentation chore. `the-release-is-a-conveyor` risk 2 names it as the feature's
own failure mode: *a hand-written doc DESCRIBING the steps recreates the drift immediately.*
The drift is not hypothetical — `SDLC.md` § *Close protocol* and
`.claude/skills/release/SKILL.md` disagreed with each other and with the code, in this repo,
this milestone.

## `install-sdlc` writes a WHOLE file it owns. It never splices into one it does not.

The tempting shape is to regenerate `SDLC.md`'s close-protocol section in place. That is a write
verb editing lines it was not asked to edit inside a file an author owns — rule 3, refused.

So: `install-sdlc` writes `docs/sdlc-protocol.md`, whole, the way every other `install-*` verb
writes a whole destination, with the same collision / `--force` / `--diff` contract. This repo's
`SDLC.md` § *Close protocol (ordered)* then becomes **a link to that file plus the rules that
are not steps** — the judgement-before-gate ruling, the forward-only rule, the "when a gate and
a judgement both bear on one decision" sentence. Guidance stays prose; the ordered list stops
being prose. Same for `.claude/skills/release/SKILL.md`: it shrinks to *run this verb*, plus
the bump-choice judgement (rule 7) that no step can make.

## What the audit's fifth-entry framing costs — the seams in `install.py`

`install-sdlc` is a fifth `PLANS` entry, and `cli.py:190` `install_commands()` derives the verb
roster from `PLANS`, so the route is free. Three things are not free, and each is a real edit
the builder must not discover late:

1. **`body_of()` is verbatim by contract** — *"There is no substitution and no template"*
   (`install.py:614`) — and `main()` builds its entries as `body_of(name)` at
   `install.py:681`. A generated body needs a resolver seam there: the plan entry names a
   producer, and `body_of` stays exactly what its docstring says it is for the four static
   verbs. Do not weaken `body_of`.
2. **`_NEXT_STEP` is keyed by command** (`install.py:302`) and read unguarded at
   `install.py:785`. A fifth verb with no entry is a `KeyError` on the success path.
3. **`USAGE`** (`install.py:214`) and `cli.py`'s installer list both enumerate the verbs in
   prose. `0.2.0/the-extraction-finishes/02-help-describes-what-ships` rewrites that list in
   phase 1 without knowing about this verb; adding it here is the reconciliation, and the
   report should say so.

**Ruling to make and record: does `agentic-sdlc init` compose `install-sdlc`?** `init.py`
composes the other four. It should — a fresh project with a conveyor and no document describing
it is the drift arriving on day one — but it is a decision, so it goes through `pm decide` on
the feature, not into the diff silently.

## Refusal matrix — the renderer and the verb (SDLC.md §5)

The renderer's input is config that story 02 already validates, so this matrix covers what
survives that and what the destination can be.

| input | expected |
|---|---|
| `[release] steps` names a step the registry does not have | exit 2 from story 02's reader, before a byte is rendered |
| a step whose name would open a markdown heading, list or table (`#`, `|`, `-`, backtick) | already refused by story 02's name grammar; a test proves the renderer cannot be made to emit broken markdown through the config |
| `[adopt]` absent entirely | renders the release half and says the adopt list is not configured — never an empty section that looks complete |
| both sections absent | renders the shipped defaults, byte-identically to declaring them (rule 5) |
| `docs/sdlc-protocol.md` exists and differs | the standard collision refusal, listing it, exit 1, nothing overwritten |
| the destination is a directory / not writable / its parent is a file | `destination_defect`'s existing sentence, naming the path |
| `--force` | replaces the whole file, as every other install verb does |
| an unknown flag | exit 2 with `USAGE` — the existing `main()` behaviour, asserted for the new verb |
| run twice with no config change | byte-identical output, `already current` on the second run |

## Acceptance criteria

1. `agentic-sdlc install-sdlc [--force] [--diff]` exists, routes through the existing
   `install.main` contract, and its `--diff`/collision/`--force`/exit-code behaviour is proven by
   the same test shapes `tests/test_install.py` already applies to the other four verbs.
2. **The rendered document is a function of config alone.** Two scratch repos with different
   `[release] steps` produce different documents; two with the same config produce byte-identical
   ones. `tests/test_install_sdlc.py`.
3. **Every configured step appears, and nothing else does.** A census assertion: the set of step
   names in the rendered document equals the configured list, in order. A step silently missing
   from the doc is the same class of defect as a gate silently leaving a roster.
4. Each rendered step carries its KIND and its postcondition, taken from the registry — not from
   a second table of prose in the renderer. A test asserts the renderer reads
   `release_steps`/`adopt_steps` and holds no per-step text of its own.
5. **Self-hosting.** This repo's `docs/sdlc-protocol.md` is byte-current against the renderer,
   asserted by a test — the same bar `tests/test_install.py` already holds the installed agent
   definitions to. `SDLC.md` § *Close protocol (ordered)* links to it and no longer enumerates
   the steps; `.claude/skills/release/SKILL.md` shrinks to the verb plus the judgements.
6. The adopt list renders beside the release list from the same source — `adopt-is-a-conveyor`
   ship criterion 4, satisfied here rather than duplicated there.
7. `agentic-sdlc check doc` and `check all` exit 0 on this repo afterwards, with `SDLC.md`'s new
   link resolving.
8. Every row of the refusal matrix is a test.

## Files this story may touch

- `src/agentic_sdlc/repo/conveyor/render.py` — NEW
- `src/agentic_sdlc/repo/install.py` — the `PLANS` entry, the body-resolver seam, `_NEXT_STEP`,
  `USAGE`
- `src/agentic_sdlc/repo/init.py` — only if the ruling above says `init` composes the verb
- `SDLC.md` — § *Close protocol (ordered)* only
- `.claude/skills/release/SKILL.md`
- `docs/sdlc-protocol.md` — NEW (this repo's own rendered copy)
- `CLAUDE.md` § *Releases* — one line, only if the `/release` sentence becomes wrong
- `tests/test_install_sdlc.py` — NEW; `tests/test_install.py` — the fifth-verb rows

## Files this story must stay out of

`conveyor/driver.py`, `conveyor/state.py`, `src/agentic_sdlc/cli.py` (story 01),
`conveyor/config.py`, `src/agentic_sdlc/core/config.py` (02), `conveyor/release_steps.py` (03) —
this story READS the registry and must not edit it, `conveyor/skip.py` and
`src/agentic_sdlc/repo/pm/ledger.py` (04).

**`src/agentic_sdlc/cli.py`'s docstring installer list is owned by
`0.2.0/the-extraction-finishes/02` in phase 1.** Report the needed line as PROPOSED text
(SDLC.md §2) rather than editing it here.

## Out of scope

- Generating `SDLC.md` §§1–5. Those are doctrine, not a step list, and generating doctrine is
  the over-encoding risk 1 names.
- A `--check` mode that fails a gate when the document is stale. That is a real want and it is
  a `check doc` rule, filed against a later milestone — not smuggled in here.
- Rendering anything from `[checks] all` or `[gates] extra`.

## Close

done: 6e9388d 8c1ba41 cc0569d — install-sdlc renders the protocol from the step lists, and
SDLC.md's Close protocol section is gone: it enumerated the steps, so the protocol had two
homes inside the document describing the milestone that exists to end that. All four lists
render since cc0569d.
