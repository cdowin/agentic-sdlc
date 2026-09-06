"""The consumer deny-list — maintainer configuration, deliberately uncommitted.

Three guards in this suite assert that a shipped file (the Makefile include,
the CI workflows, the hook corpus) names no consuming project: the bulk of the
drift between the two forked copies this kit was extracted from WAS the project
name, and a name in a shipped file is a fork wearing a library's name.

Those guards need the names to look for, and the names are the maintainer's own
repositories. This tree is public, so they live in the environment
(`AGENTIC_SDLC_CONSUMER_NAMES`, comma-separated) or in a `.consumer-names` file
at the repo root, one per line, `#` for a comment — gitignored, both of them.

When neither is configured the sweep has nothing to sweep FOR. Rule 4 forbids a
silent pass over an empty census, so `require()` SKIPS with the reason spelled
out rather than passing green over a list nobody supplied: a skip is on the
report, a vacuous pass is not.
"""
from __future__ import annotations

import functools
import os
from pathlib import Path

import pytest

ENV_VAR = 'AGENTIC_SDLC_CONSUMER_NAMES'
NAMES_FILE = Path(__file__).resolve().parents[2] / '.consumer-names'

WHY_EMPTY = (
    f'no consumer names configured, so this guard has nothing to sweep for. '
    f'Set {ENV_VAR}="name1,name2" or write one name per line into '
    f'{NAMES_FILE.name} at the repo root (both are gitignored — the names are '
    f'maintainer configuration and this tree is public).')


@functools.lru_cache(maxsize=1)
def consumer_names() -> tuple[str, ...]:
    """Every configured consumer name, lowercased. Empty when unconfigured.

    The environment wins over the file, so a CI secret can supply the list
    without a checkout carrying one.
    """
    raw = os.environ.get(ENV_VAR, '')
    if not raw and NAMES_FILE.exists():
        raw = ','.join(line.split('#', 1)[0].strip()
                       for line in NAMES_FILE.read_text(encoding='utf-8').splitlines())
    return tuple(sorted({part.strip().lower() for part in raw.split(',') if part.strip()}))


def require() -> tuple[str, ...]:
    """The names, or a DISCLOSED skip — never an empty loop reported as a pass."""
    names = consumer_names()
    if not names:
        pytest.skip(WHY_EMPTY)
    return names
