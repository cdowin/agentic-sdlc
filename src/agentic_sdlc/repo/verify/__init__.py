"""verify — what proves a change, read from `[verify]` in devkit.toml.

`rules.py` parses the section, `select.py` picks commands for changed paths,
`declares.py` reads reverse declarations, `main.py` is the verb. Nothing here
imports `cli.py` (`tests/test_boundaries.py`).
"""
