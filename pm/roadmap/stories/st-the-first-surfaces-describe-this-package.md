---
id: st-the-first-surfaces-describe-this-package
feature: ft-the-extraction-finishes
milestone: "ms-0.2.0"
name: README, CLAUDE.md and the config describe the half that stayed
status: done
owner: builder-docs
depends_on: []
kind: story
---

# README, CLAUDE.md and the config describe the half that stayed

The three files a new adopter reads first describe **this** package. None of them mentions a
`.tscn`, a scene write verb, or a Godot autoload blind spot.

Each is verified present at `29bc4b7`:

| file | what is wrong |
|---|---|
| `README.md` | the install pin says **`@v0.24.0`** — that is `godot-devkit`'s tag; this package is at `0.1.0`. Plus the scene-introspection and scene-surgery command tables |
| `CLAUDE.md` | hard rule 2 and § *Where things live* describe `godot/` and the `.tscn` write verbs; § *Known gaps* is entirely the `refs` autoload blind spot |
| `devkit.toml` | `[uid]`/`[tres]`/`[props]` sections and prose about "four of the eight gates read `.tscn`/`.tres`" |

**`README.md` was not in the feature file's list and it is the most consequential of the three**
— a wrong pin is a copy-pasteable instruction that installs the wrong package.

## Acceptance criteria

1. `README.md`'s install pin names this package at a version this package has. The command
   tables list only shipped verbs; `check all`'s described default roster equals story 01's.
2. `CLAUDE.md` hard rule 2 states the rule this package actually holds — no engine, no
   `.godot/` cache state — without describing scene surgery. § *Where things live* describes
   `core/` and `repo/`; the `godot/` paragraph goes. § *Known gaps* loses the autoload entry.
   **Rule 2's "if that stops being true, it leaves" clause has now HAPPENED** — say so, in one
   line, rather than deleting the sentence: a rule that predicted its own exercise is worth
   more with the outcome attached.
3. `devkit.toml` carries only sections this package's gates read. `check all` and `check pm`
   still exit 0 on this tree afterwards — that is the self-hosting gate, and it is how this
   story is proven.
4. `make gates` passes. `check doc` reads these files and has an opinion about unresolved
   claims; a doc sweep that reddens it is not done.

## Out of scope

- `src/**` and `tests/**`. This story is prose and config only, so it runs **in parallel** with
  nothing else touching those two files.
- `HANDOFF.md` — it is the migration document and rule-8-exempt by name. Leave it.

## Files
Touch: `README.md`, `CLAUDE.md`, `devkit.toml`.
Stay out of: `src/`, `tests/`, `pm/`.

## Close

done: 69df2df — README's install pin said @v0.24.0, another package's tag on a copy-pasteable
line. CLAUDE.md rule 2's "if that stops being true, it leaves" clause is quoted with the
outcome attached rather than deleted. devkit.toml drops [uid]/[tres]/[props].
finding: 650dc45 — the stock init's own first `check shell` named the wrong cause.
