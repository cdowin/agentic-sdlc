---
id: 0.2.0/the-extraction-finishes/03-the-wheel-carries-only-what-has-a-reader
feature: 0.2.0/the-extraction-finishes
milestone: "0.2.0"
name: Nothing ships in the wheel that no code reads
status: planning
owner:
depends_on: []
---

# Nothing ships in the wheel that no code reads

`pip install` / `uvx` of this package delivers only files something imports or opens.

Measured at `29bc4b7`: `src/agentic_sdlc/data/classdb.json` is **129,490 bytes** of Godot
ClassDB with **zero readers** (`grep -rn classdb src tests` returns nothing) sitting inside the
wheel root, so it ships. `cli.py:121` `RETARGET_FLAG` has zero readers.
`tests/fixtures/kitchen_sink.tscn` and `tests/fixtures/tilemap.tscn` have zero readers.

## Acceptance criteria

1. `src/agentic_sdlc/data/` is gone, and a built wheel does not contain `classdb.json` — proven
   by building and listing the wheel, not by trusting the delete.
2. `RETARGET_FLAG` is gone.
3. The two orphaned `.tscn` fixtures are gone.
4. `tests/support/temp_repo()`: it has zero **callers** but is held alive by
   `tests/test_shell_mark.py:64`'s `SPAWNING_HELPERS` census, which the `shell` mark derivation
   reads. **Removing it means updating that census in the same change** — and the `shell` mark
   is derived, so a wrong census silently changes which modules run on three interpreters. If
   removal cannot be proven safe in one change, LEAVE IT and say so in the story's close
   evidence; a wrong `shell` mark is worth more than a tidy helper.
5. `pyproject.toml`'s `description` and `keywords` describe this package.

## Out of scope

- `devkit.toml`, `README.md`, `CLAUDE.md` — story 04.
- `cli.py`'s roster and docstring — stories 01 and 02. This story's only `cli.py` edit is the
  `RETARGET_FLAG` line, so it lands **after** 02.

## Files
Touch: `src/agentic_sdlc/data/` (delete), `pyproject.toml`, `tests/fixtures/*.tscn` (delete),
`tests/test_shell_mark.py`, `tests/support/__init__.py`, one line of `src/agentic_sdlc/cli.py`.
