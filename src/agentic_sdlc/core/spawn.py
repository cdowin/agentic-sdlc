"""The one place this package starts a process.

The third of the family: `apply.py` owns the mutation, `walk.py` owns the
enumeration, and this owns the spawn — hard rule 2's chokepoint, so "boots
nothing" is a question with one file to ask. `run()` is `subprocess.run` with
the arguments these callers already pass and NOTHING added: no default timeout,
no decoding, no shell, no error handling. What is spawned, how long it may take
and what a failure means stay the caller's, because they are the caller's
question and not this module's. `tests/test_boundaries.py` forbids
`import subprocess` and the `os.*` spawn spellings everywhere else.

Two invariants live here rather than in a reviewer's memory:

  * **`subprocess` is imported as a MODULE and reached by attribute.**
    `tests/conftest.py` enforces the unit tier by rebinding `subprocess.Popen`,
    which every `run` constructs. A `from subprocess import Popen` here would
    hold its own reference, the rebinding would never reach it, and the guard
    would stop firing for the WHOLE suite with no symptom but a slower `make
    unit` — measured, not assumed. `from subprocess import run` survives it only
    because `run` looks `Popen` up as a module global at call time, which is an
    implementation detail of the stdlib and not a thing to rest a gate on, so
    `test_boundaries.py::OneSpawn` bans every `from subprocess import …`.
  * **`text` is the caller's, defaulting to bytes.** `pm/report.py` reads git's
    stdout as bytes deliberately — `text=True` applies newline translation and
    the locale's encoding, which is rule 3 one layer down — so a seam that
    normalised every result to `str` would corrupt it.
"""
from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# The failure vocabulary, re-exported so a caller can name what `run()` raises
# without importing `subprocess` for itself — which the allowlist forbids and
# which is the whole point of having one seam.
CalledProcessError = subprocess.CalledProcessError
SubprocessError = subprocess.SubprocessError
TimeoutExpired = subprocess.TimeoutExpired
CompletedProcess = subprocess.CompletedProcess


def run(argv: Sequence[str] | str, *,
        cwd: Path | str | None = None,
        capture_output: bool = False,
        text: bool = False,
        input: str | bytes | None = None,  # noqa: A002 — subprocess's own name
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
        shell: bool = False,
        check: bool = False) -> CompletedProcess[Any]:
    """Start one process and wait for it; every argument is the caller's.

    Each keyword is spelled out rather than passed through `**kwargs` so the
    seam is a readable list of what this package actually asks a process for,
    and a caller wanting a tenth one has to add it here. Every default is
    `subprocess.run`'s own, so a call that names none of them behaves exactly as
    the bare call it replaced: stdout and stderr are inherited, nothing is
    decoded, nothing times out, and a non-zero exit comes back in `returncode`.

    Raises whatever `subprocess.run` raises — `OSError` for a binary that is not
    there, `TimeoutExpired`, `CalledProcessError` under `check=True`. Catching
    them is the caller's, because only the caller knows whether a missing `git`
    is a finding, an exit code or a crash.
    """
    return subprocess.run(argv, cwd=cwd, capture_output=capture_output,
                          text=text, input=input, timeout=timeout, env=env,
                          shell=shell, check=check)
