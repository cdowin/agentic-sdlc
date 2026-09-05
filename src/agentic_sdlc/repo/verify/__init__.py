"""verify — what proves a change, read from `[verify]` in devkit.toml.

Under `repo/` and not `core/` because the family reads git, config and paths
and knows nothing about any file FORMAT: a rule set names globs over tracked
files and a command line, and that is the whole of its world. Nothing here may
import upward (`cli.py`) — `tests/test_boundaries.py` is the gate.

`rules.py` is the grammar: it turns the section into typed, indexed rules or
refuses with exit 2. It spawns nothing and reads no file, so the parse is safe
to run anywhere, including from `--plan`, whose entire point is printing the
commands WITHOUT running them.
"""
